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
from django.core.serializers.json import DjangoJSONEncoder
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


class ModelRestClient:
    def __init__(self, rest):
        self.rest = rest


class AfsenderRestClient(ModelRestClient):
    def get_or_create(self, data: dict) -> int:
        afsender_cvr = data["afsender_cvr"]
        if afsender_cvr:
            afsender_response = self.rest.get("afsender", {"cvr": afsender_cvr})
            if afsender_response["count"] > 0:
                return afsender_response["items"][0]["id"]
        resp = self.rest.post(
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


class ModtagerRestClient(ModelRestClient):
    def get_or_create(self, data: dict) -> int:
        modtager_cvr = data["modtager_cvr"]
        if modtager_cvr:
            modtager_response = self.rest.get("modtager", {"cvr": modtager_cvr})
            if modtager_response["count"] > 0:
                return modtager_response["items"][0]["id"]
        resp = self.rest.post(
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


class PostforsendelseRestClient(ModelRestClient):
    @staticmethod
    def map(data: dict) -> Union[dict, None]:
        fragttype = data["fragttype"]
        if fragttype in ("luftpost", "skibspost"):
            return {
                "postforsendelsesnummer": data["fragtbrevnr"],
                "forsendelsestype": "S" if fragttype == "skibspost" else "F",
            }
        return None

    @staticmethod
    def compare(data: dict, existing: dict) -> bool:
        # Sammenligner output fra map_postforsendelse (input fra form)
        # med eksisterende data fra REST for at se om de stemmer overens.
        # False: data passer ikke, og der skal foretages en opdatering
        # True: data passer, og det er ikke nødvendigt at opdatere.
        for x in ("forsendelsestype", "postforsendelsesnummer"):
            if data[x] != existing[x]:
                return False
        return True

    def create(self, data: dict) -> Union[int, None]:
        # TODO: Hvad med Forbindelsesnr/afsenderbykode?
        # De fremgår af formularen, men er ikke at finde i modellen
        mapped = self.map(data)
        if mapped:
            response = self.rest.post("postforsendelse", mapped)
            return response["id"]

    def update(self, id: int, data: dict, existing: dict) -> Union[int, None]:
        # TODO: Hvad med Forbindelsesnr/afsenderbykode?
        # De fremgår af formularen, men er ikke at finde i modellen
        mapped = self.map(data)
        if mapped is None:
            self.rest.delete(f"postforsendelse/{id}")
            return None
        elif self.compare(mapped, existing):
            # Data passer, spring opdatering over
            pass
        else:
            # Opdatér data
            self.rest.patch(f"postforsendelse/{id}", mapped)
        return id


class FragtforsendelseRestClient(ModelRestClient):
    @staticmethod
    def map(data: dict, file: Union[UploadedFile, None]) -> Union[dict, None]:
        fragttype = data["fragttype"]
        if fragttype in ("luftfragt", "skibsfragt"):
            return {
                "fragtbrevsnummer": data["fragtbrevnr"],
                "forsendelsestype": "S" if fragttype == "skibsfragt" else "F",
                "fragtbrev": RestClient._uploadfile_to_base64str(file)
                if file
                else None,
                "fragtbrev_navn": file.name if file else None,
            }
        return None

    @staticmethod
    def compare(data: dict, existing: dict) -> bool:
        # Sammenligner output fra map_fragtforsendelse (input fra form)
        # med eksisterende data fra REST for at se om de stemmer overens.
        # False: data passer ikke, og der skal foretages en opdatering
        # True: data passer, og det er ikke nødvendigt at opdatere.
        for x in ("forsendelsestype", "fragtbrevsnummer"):
            if data[x] != existing[x]:
                return False
        if data["fragtbrev"] is not None:
            return False
        return True

    def create(self, data: dict, file: Union[UploadedFile, None]) -> Union[int, None]:
        fragttype = data["fragttype"]
        if fragttype in ("luftfragt", "skibsfragt"):
            response = self.rest.post(
                "fragtforsendelse",
                {
                    "fragtbrevsnummer": data["fragtbrevnr"],
                    "forsendelsestype": "S" if fragttype == "skibsfragt" else "F",
                    "fragtbrev": self.rest._uploadfile_to_base64str(file)
                    if file
                    else None,
                    "fragtbrev_navn": file.name if file else None,
                },
            )
            return response["id"]

    def update(
        self, id, data: dict, file: Union[UploadedFile, None], existing: dict
    ) -> None:
        mapped = self.map(data, file)
        if mapped is None:
            self.rest.delete(f"fragtforsendelse/{id}")
            return None
        elif self.compare(mapped, existing):
            # Data passer med eksisterende, opdatér ikke
            pass
        else:
            # Håndterer opdatering af eksisterende
            self.rest.patch(f"fragtforsendelse/{id}", mapped)
        return id


class AfgiftanmeldelseRestClient(ModelRestClient):
    @staticmethod
    def compare(data: dict, existing: dict) -> bool:
        # Sammenligner output fra map_anmeldelse (input fra form)
        # med eksisterende data fra REST for at se om de stemmer overens.
        # False: data passer ikke, og der skal foretages en opdatering
        # True: data passer, og det er ikke nødvendigt at opdatere.
        if data["leverandørfaktura"]:
            return False
        if data["leverandørfaktura_nummer"] != existing["leverandørfaktura_nummer"]:
            return False
        for key in ("afsender", "modtager", "postforsendelse", "fragtforsendelse"):
            existing_sub = existing.get(key, None)  # existing[key] kan være None
            existing_id = existing_sub["id"] if existing_sub is not None else None
            if data[f"{key}_id"] != existing_id:
                return False
        return True

    def map(
        self,
        data: dict,
        leverandørfaktura: Union[UploadedFile, None],
        afsender_id: int,
        modtager_id: int,
        postforsendelse_id: Union[int, None],
        fragtforsendelse_id: Union[int, None],
    ) -> dict:
        return {
            "leverandørfaktura_nummer": data["leverandørfaktura_nummer"],
            "indførselstilladelse": data["modtager_indførselstilladelse"],
            "afsender_id": afsender_id,
            "modtager_id": modtager_id,
            "postforsendelse_id": postforsendelse_id,
            "fragtforsendelse_id": fragtforsendelse_id,
            "leverandørfaktura": self.rest._uploadfile_to_base64str(leverandørfaktura)
            if leverandørfaktura
            else None,
            "leverandørfaktura_navn": leverandørfaktura.name
            if leverandørfaktura
            else None,
        }

    def create(
        self,
        data: dict,
        leverandørfaktura: UploadedFile,
        afsender_id: int,
        modtager_id: int,
        postforsendelse_id: Union[int, None],
        fragtforsendelse_id: Union[int, None],
    ):
        mapped = self.map(
            data,
            leverandørfaktura,
            afsender_id,
            modtager_id,
            postforsendelse_id,
            fragtforsendelse_id,
        )
        response = self.rest.post("afgiftsanmeldelse", mapped)
        return response["id"]

    def update(
        self,
        id: int,
        data: dict,
        leverandørfaktura: Union[UploadedFile, None],
        afsender_id: int,
        modtager_id: int,
        postforsendelse_id: Union[int, None],
        fragtforsendelse_id: Union[int, None],
        existing: dict,
    ):
        mapped = self.map(
            data,
            leverandørfaktura,
            afsender_id,
            modtager_id,
            postforsendelse_id,
            fragtforsendelse_id,
        )
        if not self.compare(mapped, existing):
            self.rest.patch(f"afgiftsanmeldelse/{id}", mapped)
        return id


class VarelinjeRestClient(ModelRestClient):
    @staticmethod
    def map(data: dict, afgiftsanmeldelse_id: int) -> dict:
        return {
            "afgiftsanmeldelse_id": afgiftsanmeldelse_id,
            "fakturabeløb": str(data["fakturabeløb"]),
            "vareafgiftssats_id": int(data["vareafgiftssats"]),
            "antal": data["antal"],
            "mængde": data["mængde"],
        }

    @staticmethod
    def compare(data: dict, existing: dict) -> bool:
        # Sammenligner output fra map_anmeldelse (input fra form)
        # med eksisterende data fra REST for at se om de stemmer overens.
        # False: data passer ikke, og der skal foretages en opdatering
        # True: data passer, og det er ikke nødvendigt at opdatere.
        for key in ("fakturabeløb", "vareafgiftssats_id", "antal", "mængde"):
            if data[key] != existing[key]:
                return False
        return True

    def create(self, data: dict, afgiftsanmeldelse_id: int):
        response = self.rest.post("varelinje", self.map(data, afgiftsanmeldelse_id))
        return response["id"]

    def update(self, id: int, data: dict, existing: dict, afgiftsanmeldelse_id: int):
        mapped = self.map(data, afgiftsanmeldelse_id)
        if not self.compare(mapped, existing):
            self.rest.patch(f"varelinje/{id}", mapped)
        return id

    def delete(self, id):
        self.rest.delete(f"varelinje/{id}")


class AfgiftstabelRestClient(ModelRestClient):
    @staticmethod
    def compare(data: dict, existing: dict) -> bool:
        # Sammenligner output fra map_postforsendelse (input fra form)
        # med eksisterende data fra REST for at se om de stemmer overens.
        # False: data passer ikke, og der skal foretages en opdatering
        # True: data passer, og det er ikke nødvendigt at opdatere.
        for x in ("gyldig_fra", "gyldig_til", "kladde"):
            if data[x] != existing[x]:
                return False
        return True

    def create(self, data: dict) -> Union[int, None]:
        response = self.rest.post("afgiftstabel", data)
        return response["id"]

    def update(self, id: int, data: dict, existing: dict = None) -> Union[int, None]:
        if existing is not None and self.compare(data, existing):
            # Data passer, spring opdatering over
            pass
        else:
            # Opdatér data
            self.rest.patch(f"afgiftstabel/{id}", data)
        return id

    def delete(self, id: int) -> None:
        self.rest.delete(f"afgiftstabel/{id}")


class VareafgiftssatsRestClient(ModelRestClient):
    def create(self, data: dict) -> Union[int, None]:
        response = self.rest.post("vareafgiftssats", data)
        return response["id"]


class RestClient:
    domain = settings.REST_DOMAIN

    def __init__(self, token: JwtTokenInfo):
        self.session: Session = requests.session()
        self.token: JwtTokenInfo = token
        self.session.headers = {"Authorization": f"Bearer {self.token.access_token}"}
        self.afsender = AfsenderRestClient(self)
        self.modtager = ModtagerRestClient(self)
        self.postforsendelse = PostforsendelseRestClient(self)
        self.fragtforsendelse = FragtforsendelseRestClient(self)
        self.afgiftanmeldelse = AfgiftanmeldelseRestClient(self)
        self.varelinje = VarelinjeRestClient(self)
        self.afgiftstabel = AfgiftstabelRestClient(self)
        self.vareafgiftssats = VareafgiftssatsRestClient(self)

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
            json.dumps(data, cls=DjangoJSONEncoder),
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()

    def patch(self, path: str, data):
        self.check_access_token_age()
        response = self.session.patch(
            f"{self.domain}/api/{path}",
            json.dumps(data, cls=DjangoJSONEncoder),
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()

    def delete(self, path: str):
        self.check_access_token_age()
        response = self.session.delete(
            f"{self.domain}/api/{path}",
        )
        response.raise_for_status()
        return response.json()

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

    @cached_property
    def varesatser(self) -> Dict[int, dict]:
        data = self.get("vareafgiftssats")
        return {item["id"]: item for item in data["items"]}
