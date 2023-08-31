import json
import time
from base64 import b64encode
from dataclasses import dataclass, field
from datetime import timedelta
from functools import cached_property
from typing import Union, Dict, List
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile, InMemoryUploadedFile
from django.http import HttpResponse, HttpRequest
from requests import Session


@dataclass
class JwtTokenInfo:
    access_token: str
    refresh_token: str
    access_token_timestamp: float = field(
        default_factory=time.time
    )  # default to timestamp at instance creation
    refresh_token_timestamp: float = field(default_factory=time.time)
    synchronized: bool = False

    def set_cookies(self, response: HttpResponse, set_refresh_token: bool = False):
        response.set_cookie("access_token", self.access_token)
        response.set_cookie("access_token_timestamp", self.access_token_timestamp)
        if set_refresh_token:
            response.set_cookie("refresh_token", self.refresh_token)
            response.set_cookie("refresh_token_timestamp", self.refresh_token_timestamp)
        self.synchronized = True

    @staticmethod
    def from_cookies(request: HttpRequest):
        return JwtTokenInfo(
            access_token=request.COOKIES["access_token"],
            access_token_timestamp=float(request.COOKIES["access_token_timestamp"]),
            refresh_token=request.COOKIES["refresh_token"],
            refresh_token_timestamp=float(request.COOKIES["refresh_token_timestamp"]),
            synchronized=True,
        )

    def synchronize(
        self, response: HttpResponse, synchronize_refresh_token: bool = False
    ):
        if not self.synchronized:
            self.set_cookies(response, synchronize_refresh_token)


class RestClient:
    domain = settings.REST_DOMAIN

    def __init__(self, token: JwtTokenInfo):
        self.session: Session = requests.session()
        self.token: JwtTokenInfo = token
        self.session.headers = {"Authorization": f"Bearer {self.token.access_token}"}

    def check_access_token_age(self):
        max_age = getattr(settings, "NINJA_JWT", {}).get(
            "ACCESS_TOKEN_LIFETIME", None
        ) or timedelta(seconds=300)
        if int(time.time() - self.token.access_token_timestamp) > (
            max_age.seconds - 10
        ):
            # Access token has expired or will expire within 10 seconds
            self.refresh_login()

    @classmethod
    def login(cls, username: str, password: str) -> JwtTokenInfo:
        response = requests.post(
            f"{cls.domain}/api/token/pair",
            json={"username": username, "password": password},
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        data = response.json()
        return JwtTokenInfo(access_token=data["access"], refresh_token=data["refresh"])

    def refresh_login(self):
        response = requests.post(
            f"{self.domain}/api/token/refresh",
            data=json.dumps({"refresh": self.token.refresh_token}),
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        data = response.json()
        self.token.access_token = data["access"]
        self.token.access_token_timestamp = time.time()
        self.token.synchronized = False  # Set cookies on next response
        self.session.headers = {"Authorization": f"Bearer {self.token.access_token}"}

    def get(
        self,
        path: str,
        params: Dict[
            str, Union[str, int, float, bool, List[Union[str, int, float, bool]]]
        ] = None,
    ) -> dict:
        self.check_access_token_age()
        param_string = ("?" + urlencode(params)) if params is not None else ""
        response = self.session.get(f"{self.domain}/api/{path}{param_string}")
        response.raise_for_status()
        return response.json()

    def post(self, path: str, data):
        self.check_access_token_age()
        response = self.session.post(
            f"{self.domain}/api/{path}",
            json.dumps(data),
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()

    def patch(self, path: str, data):
        self.check_access_token_age()
        response = self.session.patch(
            f"{self.domain}/api/{path}",
            json.dumps(data),
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()

    def get_or_create_afsender(self, data: dict) -> int:
        afsender_cvr = data["afsender_cvr"]
        if afsender_cvr:
            afsender_response = self.get("afsender", {"cvr": afsender_cvr})
            if afsender_response["count"] > 0:
                return afsender_response["items"][0]["id"]
        resp = self.post(
            "afsender",
            {
                key: data["afsender_" + key]
                for key in (
                    "navn",
                    "adresse",
                    "postnummer",
                    "by",
                    "postbox",
                    "telefon",
                    "cvr",
                )
            },
        )
        return resp["id"]

    def get_or_create_modtager(self, data: dict) -> int:
        modtager_cvr = data["modtager_cvr"]
        if modtager_cvr:
            modtager_response = self.get("modtager", {"cvr": modtager_cvr})
            if modtager_response["count"] > 0:
                return modtager_response["items"][0]["id"]
        resp = self.post(
            "modtager",
            {
                key: data["modtager_" + key]
                for key in (
                    "navn",
                    "adresse",
                    "postnummer",
                    "by",
                    "postbox",
                    "telefon",
                    "cvr",
                    "indførselstilladelse",
                )
            },
        )
        return resp["id"]

    def create_postforsendelse(self, data: dict) -> Union[int, None]:
        # TODO: Hvad med Forbindelsesnr/afsenderbykode?
        # De fremgår af formularen, men er ikke at finde i modellen
        fragttype = data["fragttype"]
        if fragttype in ("luftpost", "skibspost"):
            response = self.post(
                "postforsendelse",
                {
                    "postforsendelsesnummer": data["fragtbrevnr"],
                    "forsendelsestype": "S" if fragttype == "skibspost" else "F",
                },
            )
            return response["id"]

    @staticmethod
    def _uploadfile_to_base64str(file: UploadedFile) -> str:
        if type(file) is InMemoryUploadedFile:
            # InmemoryUploadedFile giver alle data i første chunk
            file.file.seek(0)
            return b64encode(file.read()).decode("ascii")
        else:
            # Base64 encoding skal modtage et multiple af 3 bytes i alle chunks
            # der ikke er det sidste, for at undgå padding (suffix '=') i
            # strengen. Vi kan ikke have en padded streng midt i vores join I
            # praksis er der dog normalt tale om en InMemoryUploadedFile, som
            # giver os alle data i ét chunk

            return "".join(
                [b64encode(chunk).decode("ascii") for chunk in file.chunks(48 * 1024)]
            )

    def create_fragtforsendelse(
        self, data: dict, file: Union[UploadedFile, None]
    ) -> Union[int, None]:
        fragttype = data["fragttype"]
        if fragttype in ("luftfragt", "skibsfragt"):
            response = self.post(
                "fragtforsendelse",
                {
                    "fragtbrevsnummer": data["fragtbrevnr"],
                    "forsendelsestype": "S" if fragttype == "skibsfragt" else "F",
                    "fragtbrev": self._uploadfile_to_base64str(file) if file else None,
                    "fragtbrev_navn": file.name if file else None,
                },
            )
            return response["id"]

    def create_anmeldelse(
        self,
        request: HttpRequest,
        data: dict,
        afsender_id: int,
        modtager_id: int,
        postforsendelse_id: Union[int, None],
        fragtforsendelse_id: Union[int, None],
    ):
        response = self.post(
            "afgiftsanmeldelse",
            {
                "leverandørfaktura_nummer": data["leverandørfaktura_nummer"],
                "indførselstilladelse": data["modtager_indførselstilladelse"],
                "afsender_id": afsender_id,
                "modtager_id": modtager_id,
                "postforsendelse_id": postforsendelse_id,
                "fragtforsendelse_id": fragtforsendelse_id,
                "leverandørfaktura": self._uploadfile_to_base64str(
                    request.FILES["leverandørfaktura"]
                ),
                "leverandørfaktura_navn": request.FILES["leverandørfaktura"].name,
            },
        )
        return response["id"]

    def create_varelinjer(self, data: List[dict], afgiftsanmeldelse_id: int):
        response_ids = []
        for subdata in data:
            if subdata:
                varesats = self.varesatser[int(subdata["vareart"])]
                response = self.post(
                    "varelinje",
                    {
                        "afgiftsanmeldelse_id": afgiftsanmeldelse_id,
                        "fakturabeløb": str(subdata["fakturabeløb"]),
                        "afgiftssats_id": subdata["vareart"],
                        "kvantum": subdata["antal"]
                        if varesats["enhed"] == "ant"
                        else subdata["mængde"],
                    },
                )
                response_ids.append(response["id"])
        return response_ids

    @cached_property
    def varesatser(self) -> Dict[int, dict]:
        data = self.get("vareafgiftssats")
        return {item["id"]: item for item in data["items"]}
