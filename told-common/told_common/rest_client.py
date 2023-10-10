# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

import json
import time
from base64 import b64encode
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import cached_property
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile, UploadedFile
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpRequest
from requests import HTTPError, Session
from told_common.data import Afgiftstabel, Notat, Vareafgiftssats


@dataclass
class JwtTokenInfo:
    access_token: str
    refresh_token: str
    access_token_timestamp: float = field(
        default_factory=time.time
    )  # default to timestamp at instance creation
    refresh_token_timestamp: float = field(default_factory=time.time)
    synchronized: bool = False

    @staticmethod
    def load(request: HttpRequest):
        return JwtTokenInfo(
            access_token=request.session["access_token"],
            access_token_timestamp=float(request.session["access_token_timestamp"]),
            refresh_token=request.session["refresh_token"],
            refresh_token_timestamp=float(request.session["refresh_token_timestamp"]),
            synchronized=True,
        )

    def save(self, request: HttpRequest, save_refresh_token: bool = False):
        if not self.synchronized:
            request.session["access_token"] = self.access_token
            request.session["access_token_timestamp"] = self.access_token_timestamp
            if save_refresh_token:
                request.session["refresh_token"] = self.refresh_token
                request.session[
                    "refresh_token_timestamp"
                ] = self.refresh_token_timestamp
            self.synchronized = True


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
                "afsenderbykode": data["forbindelsesnr"],
                "forsendelsestype": "S" if fragttype == "skibspost" else "F",
            }
        return None

    @staticmethod
    def compare(data: dict, existing: dict) -> bool:
        # Sammenligner output fra map_postforsendelse (input fra form)
        # med eksisterende data fra REST for at se om de stemmer overens.
        # False: data passer ikke, og der skal foretages en opdatering
        # True: data passer, og det er ikke nødvendigt at opdatere.
        for x in ("forsendelsestype", "postforsendelsesnummer", "afsenderbykode"):
            if data[x] != existing[x]:
                return False
        return True

    def create(self, data: dict) -> Union[int, None]:
        mapped = self.map(data)
        if mapped:
            response = self.rest.post("postforsendelse", mapped)
            return response["id"]

    def update(self, id: int, data: dict, existing: dict) -> Union[int, None]:
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
                "forbindelsesnr": data["forbindelsesnr"],
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
        for x in ("forsendelsestype", "fragtbrevsnummer", "forbindelsesnr"):
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
                    "forbindelsesnr": data["forbindelsesnr"],
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
        force_write: bool = False,
    ):
        mapped = self.map(
            data,
            leverandørfaktura,
            afsender_id,
            modtager_id,
            postforsendelse_id,
            fragtforsendelse_id,
        )
        if force_write or not self.compare(mapped, existing):
            self.rest.patch(f"afgiftsanmeldelse/{id}", mapped)
        return id

    def set_godkendt(self, id: int, godkendt: bool):
        self.rest.patch(f"afgiftsanmeldelse/{id}", {"godkendt": godkendt})


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

    def list(self, afgiftsanmeldelse_id: int):
        return self.rest.get("varelinje", {"afgiftsanmeldelse": afgiftsanmeldelse_id})[
            "items"
        ]

    def delete(self, id):
        self.rest.delete(f"varelinje/{id}")


class NotatRestClient(ModelRestClient):
    @staticmethod
    def map(data: dict, afgiftsanmeldelse_id: int) -> dict:
        return {
            "afgiftsanmeldelse_id": afgiftsanmeldelse_id,
            "tekst": str(data["tekst"]),
        }

    def create(self, data: dict, afgiftsanmeldelse_id: int):
        response = self.rest.post("notat", self.map(data, afgiftsanmeldelse_id))
        return response["id"]

    def delete(self, id):
        self.rest.delete(f"notat/{id}")

    def list(self, afgiftsanmeldelse_id, afgiftsanmeldelse_history_index=None):
        params = {"afgiftsanmeldelse": afgiftsanmeldelse_id}
        if afgiftsanmeldelse_history_index is not None:
            params["afgiftsanmeldelse_history_index"] = afgiftsanmeldelse_history_index
        return [Notat.from_dict(x) for x in self.rest.get("notat", params)["items"]]


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

    def get(self, id: int) -> Afgiftstabel:
        return Afgiftstabel.from_dict(self.rest.get(f"afgiftstabel/{id}"))

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

    def list(self, afgiftstabel: int) -> List[Vareafgiftssats]:
        satser = [
            Vareafgiftssats.from_dict(result)
            for result in self.rest.get(
                "vareafgiftssats", {"afgiftstabel": afgiftstabel}
            )["items"]
        ]
        by_overordnet = defaultdict(list)
        for sats in satser:
            if sats.overordnet:
                by_overordnet[sats.overordnet].append(sats)
        for sats in satser:
            sats.populate_subs(lambda id: by_overordnet.get(id))
        return satser


class RestClient:
    domain = settings.REST_DOMAIN

    def __init__(self, token: JwtTokenInfo):
        self.session: Session = requests.sessions.Session()
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
        self.notat = NotatRestClient(self)

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
        self.token.synchronized = False
        self.session.headers = {"Authorization": f"Bearer {self.token.access_token}"}

    @classmethod
    def login_saml_user(cls, saml_data: dict) -> Tuple[Dict, JwtTokenInfo]:
        cpr = saml_data["cpr"]
        cvr = saml_data.get("cvr", None)
        client = RestClient(RestClient.login("admin", "admin"))
        try:
            user = client.get(f"user/cpr/{int(cpr)}")
        except HTTPError as e:
            if e.response.status_code == 404:
                user = client.post(
                    "user",
                    {
                        "indberetter_data": {"cpr": cpr, "cvr": cvr},
                        "username": " / ".join(filter(None, [cpr, cvr])),
                        "first_name": saml_data["firstname"],
                        "last_name": saml_data["lastname"],
                        "email": saml_data["email"],
                        "is_superuser": False,
                        "groups": ["Indberettere"],
                    },
                )
            else:
                raise
        token = JwtTokenInfo(
            access_token=user.pop("access_token"),
            refresh_token=user.pop("refresh_token"),
        )
        return user, token

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

    def get_all_items(
        self, route: str, filter: Optional[Dict[str, Any]] = None
    ) -> Dict[int, dict]:
        limit = 100
        offset = 0
        items = []
        if filter is None:
            filter = {}

        data = self.get(route, {**filter, "limit": limit, "offset": offset})
        items.extend(data["items"])
        while len(data["items"]) == limit:
            offset += limit
            data = self.get(route, {**filter, "limit": limit, "offset": offset})
            items.extend(data["items"])

        return {item["id"]: item for item in items}

    @cached_property
    def varesatser(self) -> Dict[int, dict]:
        today = date.today().isoformat()
        afgiftstabeller = self.get(
            "afgiftstabel",
            {"gyldig_fra__lte": today, "gyldig_til__gte": today, "kladde": False},
        )
        if afgiftstabeller["count"] == 1:
            afgiftstabel = afgiftstabeller["items"][0]
            return self.get_all_items(
                "vareafgiftssats", {"afgiftstabel": afgiftstabel["id"]}
            )
        return {}

    @cached_property
    def afsendere(self) -> Dict[int, dict]:
        return self.get_all_items("afsender")

    @cached_property
    def modtagere(self) -> Dict[int, dict]:
        return self.get_all_items("modtager")
