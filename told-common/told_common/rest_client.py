# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
import base64
import json
import time
from base64 import b64encode
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import cached_property
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import unquote, urlencode

import requests
from django.conf import settings
from django.core.files import File
from django.core.files.uploadedfile import InMemoryUploadedFile, UploadedFile
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpRequest
from requests import HTTPError, Session
from told_common.util import cast_or_none, filter_dict_none

from told_common.data import (  # isort: skip
    Afgiftsanmeldelse,
    Afgiftstabel,
    FragtForsendelse,
    HistoricAfgiftsanmeldelse,
    Notat,
    PostForsendelse,
    Vareafgiftssats,
    Varelinje,
    PrismeResponse,
)


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

    @staticmethod
    def set_file(data: dict, field: str):
        try:
            data[field] = File(
                open(f"{settings.MEDIA_ROOT}{unquote(data[field])}", "rb")
            )
        except FileNotFoundError:
            print(
                f"Fil ikke fundet [id={data.get('id')}, felt={field}]: "
                f"{settings.MEDIA_ROOT}{unquote(data[field])}"
            )
            data[field] = None


class AfsenderRestClient(ModelRestClient):
    def get_or_create(self, ident: dict, data: Optional[dict] = None) -> int:
        if data is None:
            data = ident
        mapped = {
            d: filter_dict_none(
                {
                    key: store.get("afsender_" + key) or store.get(key)
                    for key in (
                        "navn",
                        "adresse",
                        "postnummer",
                        "by",
                        "postbox",
                        "telefon",
                        "cvr",
                    )
                }
            )
            for d, store in (("ident", ident), ("data", data))
        }
        if mapped["ident"]:
            afsender_response = self.rest.get("afsender", mapped["ident"])
            if afsender_response["count"] > 0:
                return afsender_response["items"][0]["id"]
        resp = self.rest.post("afsender", mapped["data"])
        return resp["id"]

    def update(self, id: int, data: dict) -> int:
        mapped = {
            key: data.get("afsender_" + key) or data.get(key)
            for key in (
                "navn",
                "adresse",
                "postnummer",
                "by",
                "postbox",
                "telefon",
                "cvr",
            )
        }
        self.rest.patch(f"afsender/{id}", mapped)
        return id


class ModtagerRestClient(ModelRestClient):
    def get_or_create(self, ident: dict, data: Optional[dict] = None) -> int:
        if data is None:
            data = ident
        mapped = {
            d: filter_dict_none(
                {
                    key: store.get("modtager_" + key) or store.get(key)
                    for key in (
                        "navn",
                        "adresse",
                        "postnummer",
                        "by",
                        "postbox",
                        "telefon",
                        "cvr",
                    )
                }
            )
            for d, store in (("ident", ident), ("data", data))
        }
        if mapped["ident"]:
            modtager_response = self.rest.get("modtager", mapped["ident"])
            if modtager_response["count"] > 0:
                return modtager_response["items"][0]["id"]
        resp = self.rest.post("modtager", mapped["data"])
        return resp["id"]

    def update(self, id: int, data: dict) -> int:
        mapped = {
            key: data.get("modtager_" + key) or data.get(key)
            for key in (
                "navn",
                "adresse",
                "postnummer",
                "by",
                "postbox",
                "telefon",
                "cvr",
            )
        }
        self.rest.patch(f"modtager/{id}", mapped)
        return id


class PostforsendelseRestClient(ModelRestClient):
    @staticmethod
    def map(data: dict) -> Optional[dict]:
        fragttype = data["fragttype"]
        if fragttype in ("luftpost", "skibspost"):
            return filter_dict_none(
                {
                    "postforsendelsesnummer": data.get("fragtbrevnr", None),
                    "afsenderbykode": data.get("forbindelsesnr", None),
                    "forsendelsestype": "S" if fragttype == "skibspost" else "F",
                    "afgangsdato": data.get("afgangsdato", None),
                },
            )
        return None

    @staticmethod
    def compare(data: dict, existing: Union[dict, PostForsendelse]) -> bool:
        # Sammenligner output fra map_postforsendelse (input fra form)
        # med eksisterende data fra REST for at se om de stemmer overens.
        # False: data passer ikke, og der skal foretages en opdatering
        # True: data passer, og det er ikke nødvendigt at opdatere.
        for x in (
            "forsendelsestype",
            "postforsendelsesnummer",
            "afsenderbykode",
            "afgangsdato",
        ):
            if data[x] != getattr(existing, x) if hasattr(existing, x) else existing[x]:
                return False
        return True

    def create(self, data: dict) -> Optional[int]:
        mapped = self.map(data)
        if mapped:
            response = self.rest.post("postforsendelse", mapped)
            return response["id"]

    def update(
        self,
        id: int,
        data: dict,
        existing: Union[dict, PostForsendelse, None] = None,
    ) -> Optional[int]:
        mapped = self.map(data)
        if mapped is None:
            self.rest.delete(f"postforsendelse/{id}")
            return None
        elif existing is not None and self.compare(mapped, existing):
            # Data passer, spring opdatering over
            pass
        else:
            # Opdatér data
            self.rest.patch(f"postforsendelse/{id}", mapped)
        return id

    def get(self, id: int) -> PostForsendelse:
        return PostForsendelse.from_dict(self.rest.get(f"postforsendelse/{id}"))


class FragtforsendelseRestClient(ModelRestClient):
    @staticmethod
    def map(data: dict, file: Optional[UploadedFile]) -> Optional[dict]:
        fragttype = data["fragttype"]
        if fragttype in ("luftfragt", "skibsfragt"):
            return filter_dict_none(
                {
                    "fragtbrevsnummer": data.get("fragtbrevnr"),
                    "forsendelsestype": "S" if fragttype == "skibsfragt" else "F",
                    "forbindelsesnr": data.get("forbindelsesnr"),
                    "fragtbrev": RestClient._uploadfile_to_base64str(file),
                    "fragtbrev_navn": file.name if file else None,
                    "afgangsdato": data.get("afgangsdato"),
                },
            )
        return None

    @staticmethod
    def compare(data: dict, existing: Union[dict, FragtForsendelse]) -> bool:
        # Sammenligner output fra map_fragtforsendelse (input fra form)
        # med eksisterende data fra REST for at se om de stemmer overens.
        # False: data passer ikke, og der skal foretages en opdatering
        # True: data passer, og det er ikke nødvendigt at opdatere.
        for x in (
            "forsendelsestype",
            "fragtbrevsnummer",
            "forbindelsesnr",
            "afgangsdato",
        ):
            if data[x] != getattr(existing, x) if hasattr(existing, x) else existing[x]:
                return False
        if data.get("fragtbrev") is not None:
            return False
        return True

    def create(self, data: dict, file: Optional[UploadedFile]) -> Optional[int]:
        mapped = self.map(data, file)
        if mapped:
            response = self.rest.post("fragtforsendelse", mapped)
            return response["id"]

    def update(
        self,
        id,
        data: dict,
        file: Optional[UploadedFile] = None,
        existing: Union[dict, FragtForsendelse, None] = None,
    ) -> None:
        mapped = self.map(data, file)
        if mapped is None:
            self.rest.delete(f"fragtforsendelse/{id}")
            return None
        elif existing is not None and self.compare(mapped, existing):
            # Data passer med eksisterende, opdatér ikke
            pass
        else:
            # Håndterer opdatering af eksisterende
            self.rest.patch(f"fragtforsendelse/{id}", mapped)
        return id

    def get(self, id: int) -> FragtForsendelse:
        data = self.rest.get(f"fragtforsendelse/{id}")
        self.set_file(data, "fragtbrev")
        return FragtForsendelse.from_dict(data)


class AfgiftanmeldelseRestClient(ModelRestClient):
    @staticmethod
    def compare(data: dict, existing: dict) -> bool:
        # Sammenligner output fra map_anmeldelse (input fra form)
        # med eksisterende data fra REST for at se om de stemmer overens.
        # False: data passer ikke, og der skal foretages en opdatering
        # True: data passer, og det er ikke nødvendigt at opdatere.
        if data.get("leverandørfaktura"):
            return False
        if data.get("leverandørfaktura_nummer") != existing.get(
            "leverandørfaktura_nummer"
        ):
            return False
        for key in ("afsender", "modtager", "postforsendelse", "fragtforsendelse"):
            existing_sub = existing.get(key)  # existing[key] kan være None
            existing_id = existing_sub["id"] if existing_sub is not None else None
            if data[f"{key}_id"] != existing_id:
                return False
        return True

    def map(
        self,
        data: dict,
        leverandørfaktura: Optional[UploadedFile],
        afsender_id: Optional[int],
        modtager_id: Optional[int],
        postforsendelse_id: Optional[int],
        fragtforsendelse_id: Optional[int],
    ) -> dict:
        return {
            "leverandørfaktura_nummer": data.get("leverandørfaktura_nummer"),
            "indførselstilladelse": data.get("indførselstilladelse"),
            "afsender_id": afsender_id,
            "modtager_id": modtager_id,
            "postforsendelse_id": postforsendelse_id,
            "fragtforsendelse_id": fragtforsendelse_id,
            "leverandørfaktura": self.rest._uploadfile_to_base64str(leverandørfaktura),
            "leverandørfaktura_navn": leverandørfaktura.name
            if leverandørfaktura
            else None,
            "modtager_betaler": data["betales_af"] == "Modtager"
            if "betales_af" in data
            else None,
        }

    def create(
        self,
        data: dict,
        leverandørfaktura: UploadedFile,
        afsender_id: int,
        modtager_id: int,
        postforsendelse_id: Optional[int],
        fragtforsendelse_id: Optional[int],
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
        leverandørfaktura: Optional[UploadedFile] = None,
        afsender_id: Optional[int] = None,
        modtager_id: Optional[int] = None,
        postforsendelse_id: Optional[int] = None,
        fragtforsendelse_id: Optional[int] = None,
        existing: Optional[dict] = None,
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
        self.rest.patch(
            f"afgiftsanmeldelse/{id}", {"status": "godkendt" if godkendt else "afvist"}
        )

    def list(
        self,
        full=False,
        include_varelinjer=False,
        include_notater=False,
        include_prismeresponses=False,
        **filter: Union[str, int, float, bool, List[Union[str, int, float, bool]]],
    ) -> Tuple[int, List[Afgiftsanmeldelse]]:
        if full:
            data = self.rest.get("afgiftsanmeldelse/full", filter)
        else:
            data = self.rest.get("afgiftsanmeldelse", filter)
        for item in data["items"]:
            item["varelinjer"] = None
            item["notater"] = None
            item["prismeresponses"] = None
            if include_varelinjer:
                item["varelinjer"] = self.rest.varelinje.list(
                    afgiftsanmeldelse=item["id"]
                )
            if include_notater:
                item["notater"] = self.rest.notat.list(afgiftsanmeldelse=item["id"])
            if include_prismeresponses:
                item["prismeresponses"] = self.rest.prismeresponse.list(
                    afgiftsanmeldelse=item["id"]
                )
        for item in data["items"]:
            self.set_file(item, "leverandørfaktura")
        return data["count"], [
            Afgiftsanmeldelse.from_dict(item) for item in data["items"]
        ]

    def get(
        self,
        id: int,
        full=False,
        include_varelinjer=False,
        include_notater=False,
        include_prismeresponses=False,
    ):
        if full:
            item = self.rest.get(f"afgiftsanmeldelse/{id}/full")
        else:
            item = self.rest.get(f"afgiftsanmeldelse/{id}")
        self.set_file(item, "leverandørfaktura")
        if item.get("fragtforsendelse"):
            self.set_file(item["fragtforsendelse"], "fragtbrev")
        item["varelinjer"] = None
        item["notater"] = None
        item["prismeresponses"] = None
        if include_varelinjer:
            item["varelinjer"] = self.rest.varelinje.list(afgiftsanmeldelse=id)
        if include_notater:
            item["notater"] = self.rest.notat.list(id)
        if include_prismeresponses:
            item["prismeresponses"] = self.rest.prismeresponse.list(
                afgiftsanmeldelse=item["id"]
            )
        return Afgiftsanmeldelse.from_dict(item)

    def list_history(self, id: int) -> Tuple[int, List[HistoricAfgiftsanmeldelse]]:
        data = self.rest.get(f"afgiftsanmeldelse/{id}/history")
        return data["count"], [
            HistoricAfgiftsanmeldelse.from_dict(
                {**item, "varelinjer": [], "notater": [], "prismeresponses": []}
            )
            for item in data["items"]
        ]

    def get_history_item(self, id: int, history_index: int):
        data = self.rest.get(f"afgiftsanmeldelse/{id}/history/{history_index}")
        data["varelinjer"] = self.rest.varelinje.list(
            afgiftsanmeldelse=id, afgiftsanmeldelse_history_index=history_index
        )
        data["notater"] = self.rest.notat.list(id, history_index)
        data["prismeresponses"] = self.rest.prismeresponse.list(afgiftsanmeldelse=id)
        return HistoricAfgiftsanmeldelse.from_dict(data)


class VarelinjeRestClient(ModelRestClient):
    @staticmethod
    def map(data: dict, afgiftsanmeldelse_id: int) -> dict:
        return {
            "afgiftsanmeldelse_id": afgiftsanmeldelse_id,
            "fakturabeløb": cast_or_none(str, data["fakturabeløb"]),
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

    def list(
        self, **filter: Union[str, int, float, bool, List[Union[str, int, float, bool]]]
    ) -> List[Varelinje]:
        data = [
            Varelinje.from_dict(item)
            for item in self.rest.get("varelinje", filter)["items"]
        ]
        for item in data:
            item.vareafgiftssats = self.rest.vareafgiftssats.get(item.vareafgiftssats)
        return data

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


class PrismeResponseRestClient(ModelRestClient):
    @staticmethod
    def map(data: PrismeResponse) -> dict:
        return {
            "afgiftsanmeldelse_id": data.afgiftsanmeldelse.id
            if isinstance(data.afgiftsanmeldelse, Afgiftsanmeldelse)
            else data.afgiftsanmeldelse,
            "invoice_date": data.invoice_date,
            "rec_id": data.rec_id,
            "tax_notification_number": data.tax_notification_number,
        }

    def create(self, data: PrismeResponse):
        response = self.rest.post("prismeresponse", self.map(data))
        return response["id"]

    def delete(self, id: int):
        self.rest.delete(f"prismeresponse/{id}")

    def list(self, afgiftsanmeldelse: int) -> List[PrismeResponse]:
        params = {"afgiftsanmeldelse": afgiftsanmeldelse}
        return [
            PrismeResponse.from_dict(x)
            for x in self.rest.get("prismeresponse", params)["items"]
        ]


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

    def list(
        self, **filter: Union[str, int, float, bool, List[Union[str, int, float, bool]]]
    ):
        return [
            Afgiftstabel.from_dict(item)
            for item in self.rest.get("afgiftstabel", filter)
        ]

    def create(self, data: dict) -> Optional[int]:
        response = self.rest.post("afgiftstabel", data)
        return response["id"]

    def update(self, id: int, data: dict, existing: dict = None) -> Optional[int]:
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
    def create(self, data: dict) -> Optional[int]:
        response = self.rest.post("vareafgiftssats", data)
        return response["id"]

    def get_subsatser(self, parent_id: int) -> List[Vareafgiftssats]:
        response = self.list(overordnet=parent_id)
        subsatser = []
        cache = {}
        for subsats in response["items"]:
            subsats = Vareafgiftssats.from_dict(subsats)
            if subsats.id not in cache:
                cache[subsats.id] = subsats
            subsatser.append(subsats)
        return subsatser

    def get(self, id: int) -> Vareafgiftssats:
        sats = Vareafgiftssats.from_dict(self.rest.get(f"vareafgiftssats/{id}"))
        if sats.enhed == Vareafgiftssats.Enhed.SAMMENSAT:
            subs = self.list(overordnet=id)
            sats.populate_subs(
                lambda oid: [item for item in subs if item.overordnet == oid]
            )
        return sats

    def list(
        self,
        **filter: Union[str, int, float, bool, List[Union[str, int, float, bool]]],
    ) -> List[Vareafgiftssats]:
        satser = [
            Vareafgiftssats.from_dict(item)
            for item in self.rest.get("vareafgiftssats", filter)["items"]
        ]
        by_overordnet = defaultdict(list)
        for sats in satser:
            if sats.overordnet:
                by_overordnet[sats.overordnet].append(sats)
        for sats in satser:
            sats.populate_subs(lambda id: by_overordnet.get(id))
        return satser


class EboksBeskedRestClient(ModelRestClient):
    def create(self, data: dict) -> Optional[int]:
        data["pdf"] = base64.b64encode(data["pdf"]).decode("ASCII")
        response = self.rest.post("eboks", data)
        return response["id"]


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
        self.prismeresponse = PrismeResponseRestClient(self)
        self.eboks = EboksBeskedRestClient(self)

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
        cvr = saml_data.get("cvr")
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
                        "email": saml_data.get("email") or "",
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
        param_string = (
            ("?" + urlencode(params, doseq=True)) if params is not None else ""
        )
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
    def _uploadfile_to_base64str(file: Optional[UploadedFile]) -> Optional[str]:
        if file is None:
            return None
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
        return self.varesatser_fra(date.today())

    def varesatser_fra(self, at: date) -> Dict[int, dict]:
        datestring = at.isoformat()
        afgiftstabeller = self.get(
            "afgiftstabel",
            {
                "gyldig_fra__lte": datestring,
                "gyldig_til__gte": datestring,
                "kladde": False,
            },
        )
        # Det bør ikke kunne lade sig gøre med mere end 1
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
