# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
import base64
import json
import logging
import re
import time
from base64 import b64encode
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from functools import cached_property
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import unquote, urlencode

import requests
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.files import File
from django.core.files.uploadedfile import InMemoryUploadedFile, UploadedFile
from django.core.serializers.json import DjangoJSONEncoder
from requests import HTTPError, Session
from told_common.data import (
    Afgiftsanmeldelse,
    Afgiftstabel,
    FragtForsendelse,
    HistoricAfgiftsanmeldelse,
    JwtTokenInfo,
    Notat,
    PostForsendelse,
    PrismeResponse,
    PrivatAfgiftsanmeldelse,
    Speditør,
    Toldkategori,
    TOTPDevice,
    User,
    Vareafgiftssats,
    Varelinje,
)
from told_common.util import cast_or_none, filter_dict_none, opt_int

log = logging.getLogger(__name__)


class RestClientException(Exception):
    def __init__(self, status_code, content):
        self.status_code = status_code
        self.content = content

    @classmethod
    def from_http_error(cls, error: HTTPError):
        response = error.response
        try:
            content = response.json()
        except ValueError:
            content = response.content
        return cls(response.status_code, content)

    def __str__(self):
        return (
            f"Failure in REST API request; got http "
            f"{self.status_code} from API. Response: {self.content}"
        )


class ModelRestClient:
    def __init__(self, rest):
        self.rest = rest

    @staticmethod
    def set_file(data: dict, field: str):
        media_root = settings.MEDIA_ROOT  # type: ignore
        if data.get(field):
            try:
                data[field] = File(open(f"{media_root}{unquote(data[field])}", "rb"))
                return
            except FileNotFoundError:
                log.info(
                    f"Fil ikke fundet [id={data.get('id')}, felt={field}]: "
                    f"{media_root}{unquote(data[field])}"
                )
        data[field] = None


class AfsenderRestClient(ModelRestClient):
    @staticmethod
    def map(data: dict) -> Optional[dict]:
        return filter_dict_none(
            {
                key: data.get("afsender_" + key) or data.get(key)
                for key in (
                    "navn",
                    "adresse",
                    "postnummer",
                    "by",
                    "postbox",
                    "telefon",
                    "cvr",
                    "stedkode",
                )
            }
        )

    def get_or_create(self, ident: dict, data: Optional[dict] = None) -> int:
        if data is None:
            data = ident
        mapped: dict = {
            d: self.map(store) for d, store in (("ident", ident), ("data", data))
        }
        if "kladde" in data:
            mapped["data"]["kladde"] = data["kladde"]
        if mapped["ident"]:
            afsender_response = self.rest.get("afsender", mapped["ident"])
            if afsender_response["count"] > 0:
                return afsender_response["items"][0]["id"]
        resp = self.rest.post("afsender", mapped["data"])
        return resp["id"]

    def update(self, id: int, data: dict) -> int:
        mapped = self.map(data)
        self.rest.patch(f"afsender/{id}", mapped)
        return id


class ModtagerRestClient(ModelRestClient):
    @staticmethod
    def map(data: dict) -> Optional[dict]:
        return filter_dict_none(
            {
                key: data.get("modtager_" + key) or data.get(key)
                for key in (
                    "navn",
                    "adresse",
                    "postnummer",
                    "by",
                    "postbox",
                    "telefon",
                    "cvr",
                    "stedkode",
                )
            }
        )

    def get_or_create(self, ident: dict, data: Optional[dict] = None) -> int:
        if data is None:
            data = ident
        mapped: dict = {
            d: self.map(store) for d, store in (("ident", ident), ("data", data))
        }
        if "kladde" in data:
            mapped["data"]["kladde"] = data["kladde"]
        if mapped["ident"]:
            modtager_response = self.rest.get("modtager", mapped["ident"])
            if modtager_response["count"] > 0:
                return modtager_response["items"][0]["id"]
        resp = self.rest.post("modtager", mapped["data"])
        return resp["id"]

    def update(self, id: int, data: dict) -> int:
        mapped = self.map(data)
        self.rest.patch(f"modtager/{id}", mapped)
        return id


class PostforsendelseRestClient(ModelRestClient):
    @staticmethod
    def map(data: dict) -> Optional[dict]:
        fragttype = data["fragttype"]
        if fragttype in ("luftpost", "skibspost"):
            return filter_dict_none(
                {
                    "kladde": data.get("kladde", False),
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
            if data[x] != (
                getattr(existing, x)
                if isinstance(existing, PostForsendelse)
                else existing[x]
            ):
                return False
        return True

    def create(self, data: dict) -> Optional[int]:
        mapped = self.map(data)
        if mapped:
            response = self.rest.post("postforsendelse", mapped)
            return response["id"]
        return None

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
                    "kladde": data.get("kladde", False),
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
            if data[x] != (
                getattr(existing, x)
                if isinstance(existing, FragtForsendelse)
                else existing[x]
            ):
                return False
        if data.get("fragtbrev") is not None:
            return False
        return True

    def create(self, data: dict, file: Optional[UploadedFile]) -> Optional[int]:
        mapped = self.map(data, file)
        if mapped:
            if mapped.get("fragtbrev"):
                log.info(
                    "rest_client opretter Fragtforsendelse "
                    "med fragtbrev '%s' (%d bytes BASE64)",
                    mapped["fragtbrev_navn"],
                    len(mapped["fragtbrev"]),
                )
            response = self.rest.post("fragtforsendelse", mapped)
            return response["id"]
        return None

    def update(
        self,
        id,
        data: dict,
        file: Optional[UploadedFile] = None,
        existing: Union[dict, FragtForsendelse, None] = None,
    ) -> None:
        mapped = self.map(data, file)
        if mapped is None:
            log.info("rest_client sletter Fragtbrev %d", id)
            self.rest.delete(f"fragtforsendelse/{id}")
            return None
        elif existing is not None and self.compare(mapped, existing):
            # Data passer med eksisterende, opdatér ikke
            log.info("rest_client ændrer ikke Fragtbrev %d", id)
            pass
        else:
            # Håndterer opdatering af eksisterende
            if mapped.get("fragtbrev"):
                log.info(
                    "rest_client opdaterer Fragtforsendelse "
                    "%d med fragtbrev '%s' (%d bytes BASE64)",
                    id,
                    mapped["fragtbrev_navn"],
                    len(mapped["fragtbrev"]),
                )
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
        status: Optional[str] = None,
    ) -> dict:
        return {
            "leverandørfaktura_nummer": data.get("leverandørfaktura_nummer"),
            "indførselstilladelse": data.get("indførselstilladelse"),
            "afsender_id": afsender_id,
            "modtager_id": modtager_id,
            "postforsendelse_id": postforsendelse_id,
            "fragtforsendelse_id": fragtforsendelse_id,
            "toldkategori": data.get("toldkategori"),
            "leverandørfaktura": self.rest._uploadfile_to_base64str(leverandørfaktura),
            "leverandørfaktura_navn": (
                leverandørfaktura.name if leverandørfaktura else None
            ),
            "betales_af": data.get("betales_af"),
            "oprettet_på_vegne_af_id": opt_int(data.get("oprettet_på_vegne_af")),
            "kladde": data.get("kladde", False),
            "fuldmagtshaver_id": data.get("fuldmagtshaver") or None,
            "status": status,
            "tf3": data.get("tf3", False),
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
        if mapped.get("leverandørfaktura"):
            log.info(
                "rest_client opretter TF10 med leverandørfaktura %s (%d bytes BASE64)",
                mapped["leverandørfaktura_navn"],
                len(mapped["leverandørfaktura"]),
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
        status: Optional[str] = None,
    ):
        mapped = self.map(
            data,
            leverandørfaktura,
            afsender_id,
            modtager_id,
            postforsendelse_id,
            fragtforsendelse_id,
            status,
        )
        if force_write or (existing and not self.compare(mapped, existing)):
            if mapped.get("leverandørfaktura"):
                log.info(
                    "rest_client opdaterer TF10 %d med "
                    "leverandørfaktura %s (%d bytes BASE64)",
                    id,
                    mapped["leverandørfaktura_navn"],
                    len(mapped["leverandørfaktura"]),
                )
            self.rest.patch(f"afgiftsanmeldelse/{id}", mapped)
        return id

    def set_status(self, id: int, status: str):
        if status in ("ny", "godkendt", "afvist"):
            self.rest.patch(f"afgiftsanmeldelse/{id}", {"status": status})
        else:
            raise Exception("status skal være 'ny', 'godkendt' eller 'afvist'")

    def set_toldkategori(self, id: int, toldkategori: str):
        self.rest.patch(f"afgiftsanmeldelse/{id}", {"toldkategori": toldkategori})

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
            id = item["id"]
            item["varelinjer"] = None
            item["notater"] = None
            item["prismeresponses"] = None
            if include_varelinjer:
                item["varelinjer"] = self.rest.varelinje.list(afgiftsanmeldelse=id)
            if include_notater:
                item["notater"] = self.rest.notat.list(afgiftsanmeldelse=id)
            if include_prismeresponses:
                item["prismeresponses"] = self.rest.prismeresponse.list(
                    afgiftsanmeldelse=id
                )
        for item in data["items"]:
            self.set_file(item, "leverandørfaktura")
            if item.get("fragtforsendelse"):
                self.set_file(item["fragtforsendelse"], "fragtbrev")
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
            item["notater"] = self.rest.notat.list(afgiftsanmeldelse=id)
        if include_prismeresponses:
            item["prismeresponses"] = self.rest.prismeresponse.list(
                afgiftsanmeldelse=item["id"]
            )
        return Afgiftsanmeldelse.from_dict(item)

    def delete(self, id: int):
        return self.rest.delete(f"afgiftsanmeldelse/{id}")

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
        data["notater"] = self.rest.notat.list(
            afgiftsanmeldelse=id, afgiftsanmeldelse_history_index=history_index
        )
        data["prismeresponses"] = self.rest.prismeresponse.list(afgiftsanmeldelse=id)
        return HistoricAfgiftsanmeldelse.from_dict(data)


class PrivatAfgiftanmeldelseRestClient(ModelRestClient):
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
        return True

    def map(
        self,
        data: dict,
        leverandørfaktura: Optional[UploadedFile],
    ) -> dict:
        mapped = {
            key: data.get(key)
            for key in (
                "cpr",
                "navn",
                "adresse",
                "postnummer",
                "by",
                "telefon",
                "bookingnummer",
                "indleveringsdato",
                "leverandørfaktura_nummer",
                "indførselstilladelse",
                "anonym",
            )
        }
        mapped.update(
            {
                "leverandørfaktura": self.rest._uploadfile_to_base64str(
                    leverandørfaktura
                ),
                "leverandørfaktura_navn": (
                    leverandørfaktura.name if leverandørfaktura else None
                ),
            }
        )
        return mapped

    def create(
        self,
        data: dict,
        leverandørfaktura: UploadedFile,
    ):
        mapped = self.map(
            data,
            leverandørfaktura,
        )
        response = self.rest.post("privat_afgiftsanmeldelse", mapped)
        return response["id"]

    def update(
        self,
        id: int,
        data: dict,
        leverandørfaktura: Optional[UploadedFile] = None,
        existing: Optional[dict] = None,
        force_write: bool = False,
    ):
        mapped = self.map(
            data,
            leverandørfaktura,
        )
        if force_write or (existing and not self.compare(mapped, existing)):
            self.rest.patch(f"privat_afgiftsanmeldelse/{id}", mapped)
        return id

    def list(
        self,
        include_varelinjer=False,
        include_notater=False,
        **filter: Union[str, int, float, bool, List[Union[str, int, float, bool]]],
    ) -> Tuple[int, List[PrivatAfgiftsanmeldelse]]:
        data = self.rest.get("privat_afgiftsanmeldelse", filter)
        for item in data["items"]:
            id = item["id"]
            item["varelinjer"] = None
            item["notater"] = None
            item["prismeresponses"] = None
            if include_varelinjer:
                item["varelinjer"] = self.rest.varelinje.list(afgiftsanmeldelse=id)
            if include_notater:
                item["notater"] = self.rest.notat.list(privatafgiftsanmeldelse=id)

        for item in data["items"]:
            if item.get("leverandørfaktura"):
                self.set_file(item, "leverandørfaktura")
        return data["count"], [
            PrivatAfgiftsanmeldelse.from_dict(item) for item in data["items"]
        ]

    def get(
        self,
        id: int,
        include_varelinjer=False,
        include_notater=False,
    ):
        item = self.rest.get(f"privat_afgiftsanmeldelse/{id}")
        if item.get("leverandørfaktura"):
            self.set_file(item, "leverandørfaktura")
        item["varelinjer"] = None
        item["notater"] = None
        if include_varelinjer:
            item["varelinjer"] = self.rest.varelinje.list(privatafgiftsanmeldelse=id)
        if include_notater:
            item["notater"] = self.rest.notat.list(privatafgiftsanmeldelse=id)
        return PrivatAfgiftsanmeldelse.from_dict(item)

    def seneste_indførselstilladelse(self, cpr):
        return self.rest.get(
            f"privat_afgiftsanmeldelse/seneste_indførselstilladelse/{cpr}"
        )

    def annuller(self, id: int):
        self.rest.patch(f"privat_afgiftsanmeldelse/{id}", {"status": "annulleret"})

    # def list_history(self, id: int) -> Tuple[int, List[HistoricAfgiftsanmeldelse]]:
    #     data = self.rest.get(f"afgiftsanmeldelse/{id}/history")
    #     return data["count"], [
    #         HistoricAfgiftsanmeldelse.from_dict(
    #             {**item, "varelinjer": [], "notater": [], "prismeresponses": []}
    #         )
    #         for item in data["items"]
    #     ]
    #
    # def get_history_item(self, id: int, history_index: int):
    #     data = self.rest.get(f"afgiftsanmeldelse/{id}/history/{history_index}")
    #     data["varelinjer"] = self.rest.varelinje.list(
    #         afgiftsanmeldelse=id, afgiftsanmeldelse_history_index=history_index
    #     )
    #     data["notater"] = self.rest.notat.list(id, history_index)
    #     data["prismeresponses"] = self.rest.prismeresponse.list(afgiftsanmeldelse=id)
    #     return HistoricAfgiftsanmeldelse.from_dict(data)
    #


class VarelinjeRestClient(ModelRestClient):
    @staticmethod
    def map(
        data: dict,
        afgiftsanmeldelse_id: Optional[int] = None,
        privatafgiftsanmeldelse_id: Optional[int] = None,
    ) -> dict:
        if afgiftsanmeldelse_id is None and privatafgiftsanmeldelse_id is None:
            raise Exception("Skal specificere enten anmeldelse eller privatanmeldelse")
        return {
            "afgiftsanmeldelse_id": afgiftsanmeldelse_id,
            "privatafgiftsanmeldelse_id": privatafgiftsanmeldelse_id,
            "fakturabeløb": cast_or_none(str, data["fakturabeløb"]),
            "vareafgiftssats_id": opt_int(data["vareafgiftssats"]),
            "antal": data["antal"],
            "mængde": data["mængde"],
            "kladde": data.get("kladde", False),
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

    def create(
        self,
        data: dict,
        afgiftsanmeldelse_id: Optional[int] = None,
        privatafgiftsanmeldelse_id: Optional[int] = None,
    ):
        mapped = self.map(data, afgiftsanmeldelse_id, privatafgiftsanmeldelse_id)
        response = self.rest.post(
            "varelinje",
            mapped,
        )
        return response["id"]

    def update(
        self,
        id: int,
        data: dict,
        existing: dict,
        afgiftsanmeldelse_id: Optional[int] = None,
        privatafgiftsanmeldelse_id: Optional[int] = None,
    ):
        mapped = self.map(data, afgiftsanmeldelse_id, privatafgiftsanmeldelse_id)
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
            if item.vareafgiftssats:
                item.vareafgiftssats = self.rest.vareafgiftssats.get(
                    item.vareafgiftssats
                )
        return data

    def delete(self, id: int):
        self.rest.delete(f"varelinje/{id}")


class NotatRestClient(ModelRestClient):
    @staticmethod
    def map(
        data: dict,
        afgiftsanmeldelse_id: Optional[int] = None,
        privatafgiftsanmeldelse_id: Optional[int] = None,
    ) -> dict:
        if afgiftsanmeldelse_id is None and privatafgiftsanmeldelse_id is None:
            raise Exception(
                "Skal specificere enten afgiftsanmeldelse eller privatanmeldelse"
            )
        return {
            "afgiftsanmeldelse_id": afgiftsanmeldelse_id,
            "privatafgiftsanmeldelse_id": privatafgiftsanmeldelse_id,
            "tekst": str(data["tekst"]),
        }

    def create(
        self,
        data: dict,
        afgiftsanmeldelse_id: Optional[int] = None,
        privatafgiftsanmeldelse_id: Optional[int] = None,
    ):
        response = self.rest.post(
            "notat", self.map(data, afgiftsanmeldelse_id, privatafgiftsanmeldelse_id)
        )
        return response["id"]

    def delete(self, id: int):
        self.rest.delete(f"notat/{id}")

    def list(
        self, **filter: Union[str, int, float, bool, List[Union[str, int, float, bool]]]
    ):
        return [Notat.from_dict(x) for x in self.rest.get("notat", filter)["items"]]


class PrismeResponseRestClient(ModelRestClient):
    @staticmethod
    def map(data: PrismeResponse) -> dict:
        return {
            "afgiftsanmeldelse_id": (
                data.afgiftsanmeldelse.id
                if isinstance(data.afgiftsanmeldelse, Afgiftsanmeldelse)
                else data.afgiftsanmeldelse
            ),
            "delivery_date": data.delivery_date,
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
            for item in self.rest.get("afgiftstabel", filter)["items"]
        ]

    def create(self, data: dict) -> Optional[int]:
        response = self.rest.post("afgiftstabel", data)
        return response["id"]

    def update(
        self, id: int, data: dict, existing: Optional[dict] = None
    ) -> Optional[int]:
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


class UserRestClient(ModelRestClient):
    def this(self):
        return self.rest.get("user/this")

    def list(
        self,
        **filter: Union[str, int, float, bool, List[Union[str, int, float, bool]]],
    ) -> Tuple[int, List[User]]:
        data = self.rest.get("user", filter)
        return data["count"], [User.from_dict(item) for item in data["items"]]


class TotpDeviceRestClient(ModelRestClient):
    def create(
        self,
        data: dict,
    ):
        return self.rest.post("totpdevice", data)

    def get_for_user(self, user: User):
        return [
            TOTPDevice.from_dict(item)
            for item in self.rest.get("totpdevice", {"user": user.id})
        ]


class PaymentRestClient(ModelRestClient):
    def create(self, data: dict) -> dict:
        return self.rest.post("payment", data)

    def get(self, payment_id: int) -> dict:
        return self.rest.get(f"payment/{payment_id}")

    def get_by_declaration(self, declaration_id: int) -> dict:
        for payment in self.rest.get(f"payment?declaration={declaration_id}&full=true"):
            if payment["declaration"] == declaration_id:
                declaration = self.rest.get(f"afgiftsanmeldelse/{declaration_id}")
                return {
                    **payment,
                    "declaration": {
                        **declaration,
                        "afsender": self.rest.get(
                            f"afsender/{declaration['afsender']}"
                        ),
                        "modtager": self.rest.get(
                            f"modtager/{declaration['modtager']}"
                        ),
                    },
                }

        raise ObjectDoesNotExist(
            f"Payment with declaration_id {declaration_id} does not exist"
        )

    def refresh(self, payment_id: int) -> dict:
        return self.rest.post(f"payment/refresh/{payment_id}", {})


class StatistikRestClient(ModelRestClient):
    def list(
        self, **filter: Union[str, int, float, bool, List[Union[str, int, float, bool]]]
    ):
        return self.rest.get("statistik", filter)


class SpeditørRestClient(ModelRestClient):
    def list(
        self, **filter: Union[str, int, float, bool, List[Union[str, int, float, bool]]]
    ):
        return [
            Speditør.from_dict(item)
            for item in self.rest.get("speditør", filter)["items"]
        ]


class ToldkategoriRestClient(ModelRestClient):
    def list(self):
        return [Toldkategori.from_dict(item) for item in self.rest.get("toldkategori")]


class RestClient:
    domain = settings.REST_DOMAIN  # type: ignore

    def __init__(self, token: JwtTokenInfo):
        self.session: Session = requests.sessions.Session()
        self.token: JwtTokenInfo = token
        if self.token:
            self.session.headers = {
                "Authorization": f"Bearer {self.token.access_token}"
            }
        self.afsender = AfsenderRestClient(self)
        self.modtager = ModtagerRestClient(self)
        self.postforsendelse = PostforsendelseRestClient(self)
        self.fragtforsendelse = FragtforsendelseRestClient(self)
        self.afgiftanmeldelse = AfgiftanmeldelseRestClient(self)
        self.privat_afgiftsanmeldelse = PrivatAfgiftanmeldelseRestClient(self)
        self.varelinje = VarelinjeRestClient(self)
        self.afgiftstabel = AfgiftstabelRestClient(self)
        self.vareafgiftssats = VareafgiftssatsRestClient(self)
        self.notat = NotatRestClient(self)
        self.prismeresponse = PrismeResponseRestClient(self)
        self.eboks = EboksBeskedRestClient(self)
        self.user = UserRestClient(self)
        self.payment = PaymentRestClient(self)
        self.statistik = StatistikRestClient(self)
        self.speditør = SpeditørRestClient(self)
        self.totpdevice = TotpDeviceRestClient(self)
        self.toldkategori = ToldkategoriRestClient(self)

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

    @classmethod
    def check_twofactor(cls, user_id: int, twofactor_token: str):
        response = requests.post(
            f"{cls.domain}/api/2fa/check",
            json={"user_id": user_id, "twofactor_token": twofactor_token},
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()

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
    def get_system_rest_client(cls) -> "RestClient":
        password = settings.SYSTEM_USER_PASSWORD  # type: ignore
        return RestClient(RestClient.login("system", password))

    @classmethod
    def login_saml_user(cls, saml_data: dict) -> Tuple[Dict, JwtTokenInfo]:
        cpr = saml_data["cpr"]
        cvr = saml_data.get("cvr")
        client = cls.get_system_rest_client()

        # If email is provided, use that as username (which must be unique.)
        # If email is not provided, use the full name and CVR (if provided.)
        # We store this potential username in `non_email_username`.
        non_email_username = " ".join(
            filter(
                None,
                [
                    saml_data["firstname"],
                    saml_data["lastname"],
                    f"/ {cvr}" if cvr else None,
                ],
            )
        )

        if not saml_data.get("email"):
            # Check if a user already exists for the `non_email_username` (any suffix)
            count, other_users = client.user.list(
                username_startswith=non_email_username
            )
            if other_users and count > 0:
                # Other users exist with the same name (but have different suffixes.)
                # Find the highest suffix and add 1 to get the next available suffix.

                # Find "42" in "Name Surname (42)"
                pattern = re.compile(r"^.*\((?P<val>\d+)\)$")

                def find_suffix(username: str) -> int:
                    match = pattern.match(username)
                    if match is not None:
                        return int(match.group("val"))
                    else:
                        return 0

                highest_suffix = max(
                    [find_suffix(other_user.username) for other_user in other_users]
                )

                # Add suffix to `non_email_username`
                non_email_username = f"{non_email_username} ({highest_suffix + 1})"

        mapped_data = {
            "indberetter_data": {"cpr": cpr, "cvr": cvr},
            "first_name": saml_data["firstname"],
            "last_name": saml_data["lastname"],
            "email": saml_data.get("email") or "",
            "is_superuser": False,
            "groups": [],
        }
        cpr_key = str(int(cpr))
        cvr_key = "-"
        if cvr:
            mapped_data["groups"].append("ErhvervIndberettere")
            cvr_key = str(int(cvr))
        elif cpr:
            mapped_data["groups"].append("PrivatIndberettere")
        try:
            user = client.get(f"user/{cpr_key}/{cvr_key}")
        except RestClientException as e:
            if e.status_code == 404:
                user = client.post(
                    "user",
                    {
                        **mapped_data,
                        "username": saml_data.get("email") or non_email_username,
                    },
                )
            else:
                raise

        mapped_data["username"] = user["username"]
        if (
            mapped_data["first_name"] != user["first_name"]
            or mapped_data["last_name"] != user["last_name"]
            or mapped_data["email"] != user["email"]
            or str(cvr) != str(user["indberetter_data"]["cvr"])
        ):
            user = client.patch(f"user/{cpr_key}/{cvr_key}", mapped_data)

        try:
            # Only the system user can obtain this
            api_key = client.get(f"user/{cpr_key}/{cvr_key}/apikey")["api_key"]
            user["indberetter_data"]["api_key"] = api_key
        except RestClientException:
            pass
        token = JwtTokenInfo(
            access_token=user.pop("access_token"),
            refresh_token=user.pop("refresh_token"),
        )
        return user, token

    def get(
        self,
        path: str,
        params: Optional[dict] = None,
    ) -> dict:
        self.check_access_token_age()
        param_string = (
            ("?" + urlencode(params, doseq=True)) if params is not None else ""
        )
        try:
            response = self.session.get(f"{self.domain}/api/{path}{param_string}")
            response.raise_for_status()
            return response.json()
        except HTTPError as e:
            raise RestClientException.from_http_error(e)

    def post(self, path: str, data):
        self.check_access_token_age()
        try:
            response = self.session.post(
                f"{self.domain}/api/{path}",
                json.dumps(data, cls=DjangoJSONEncoder),
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            if response.status_code != 204:
                return response.json()
        except HTTPError as e:
            raise RestClientException.from_http_error(e)

    def patch(self, path: str, data):
        self.check_access_token_age()
        try:
            response = self.session.patch(
                f"{self.domain}/api/{path}",
                json.dumps(data, cls=DjangoJSONEncoder),
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            return response.json()
        except HTTPError as e:
            raise RestClientException.from_http_error(e)

    def delete(self, path: str):
        self.check_access_token_age()
        try:
            response = self.session.delete(
                f"{self.domain}/api/{path}",
            )
            response.raise_for_status()
            return response.json()
        except HTTPError as e:
            raise RestClientException.from_http_error(e)

    @staticmethod
    def _uploadfile_to_base64str(file: Optional[UploadedFile]) -> Optional[str]:
        if file is None:
            return None
        if type(file) is InMemoryUploadedFile and file.file:
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
    def varesatser(self) -> Dict[int, Vareafgiftssats]:
        return self.varesatser_fra(datetime.now(timezone.utc))

    @cached_property
    def varesatser_privat(self) -> Dict[int, Vareafgiftssats]:
        return self.varesatser_fra(datetime.now(timezone.utc), synlig_privat=True)

    def varesatser_fra(self, at: datetime, **filter) -> Dict[int, Vareafgiftssats]:
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
            return {
                key: Vareafgiftssats.from_dict(value)
                for key, value in self.get_all_items(
                    "vareafgiftssats", {"afgiftstabel": afgiftstabel["id"], **filter}
                ).items()
            }
        return {}

    def varesatser_all(
        self, filter_afgiftstabel=None, filter_varesats=None
    ) -> Dict[int, Vareafgiftssats]:
        if filter_afgiftstabel is None:
            filter_afgiftstabel = {}
        if filter_varesats is None:
            filter_varesats = {}
        afgiftstabeller = self.get(
            "afgiftstabel",
            {"kladde": False, **filter_afgiftstabel},
        )["items"]
        varesatser = {}
        for afgiftstabel in afgiftstabeller:
            varesatser.update(
                {
                    key: Vareafgiftssats.from_dict(value)
                    for key, value in self.get_all_items(
                        "vareafgiftssats",
                        {"afgiftstabel": afgiftstabel["id"], **filter_varesats},
                    ).items()
                }
            )
        return varesatser

    @cached_property
    def afsendere(self) -> Dict[int, dict]:
        return self.get_all_items("afsender")

    @cached_property
    def modtagere(self) -> Dict[int, dict]:
        return self.get_all_items("modtager")
