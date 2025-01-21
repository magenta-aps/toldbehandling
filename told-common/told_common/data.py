# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Context, Decimal
from enum import Enum
from functools import cached_property
from time import time
from typing import Callable, List, Optional, Union

from dataclasses_json import DataClassJsonMixin, config
from django.conf import settings
from django.core.files import File
from django.http import HttpRequest
from django.template.defaultfilters import floatformat
from django.utils.translation import gettext_lazy as _
from marshmallow import fields
from told_common.util import round_decimal


def format_decimal(decimal: Decimal) -> str:
    decimal_as_float = float(str(decimal))
    # if isinstance(decimal, str):
    #    decimal = float(decimal.replace(".", "").replace(",", "."))
    d = str(floatformat(text=decimal_as_float, arg=2)) + ""
    return d


def unformat_decimal(string: str) -> Optional[Decimal]:
    if string in (None, ""):
        return None
    string = str(string)

    if "." not in string:
        # Der er ingen punktum. Fortolk komma som decimalseparator
        return Decimal(string.replace(",", "."), context=Context(prec=2))

    elif "," not in string:
        # Der er ingen komma. Fortolk punktum som decimalseparator
        return Decimal(string, context=Context(prec=2))

    else:
        # Der er både punktum og komma. Fortolk komma som decimalseparator
        return Decimal(
            string.replace(".", "").replace(",", "."), context=Context(prec=2)
        )


def format_int(decimal: Union[Decimal, str]) -> int:
    return int(str(decimal).split(".")[0])


class ToldDataClass(DataClassJsonMixin):
    def items(self):
        for itemfield in dataclasses.fields(self):
            yield itemfield.name, getattr(self, itemfield.name)


@dataclass
class Vareafgiftssats(ToldDataClass):
    class Enhed(Enum):
        SAMMENSAT = "sam"
        LITER = "l"
        ANTAL = "ant"
        KILOGRAM = "kg"
        PROCENT = "pct"

    id: int
    afgiftstabel: int
    vareart_da: str
    vareart_kl: str
    afgiftsgruppenummer: int
    enhed: Enhed
    afgiftssats: Decimal
    har_privat_tillægsafgift_alkohol: bool = False
    kræver_indførselstilladelse: Optional[bool] = False
    synlig_privat: bool = False
    minimumsbeløb: Optional[Decimal] = None
    overordnet: Optional[int] = None
    segment_nedre: Optional[Decimal] = None
    segment_øvre: Optional[Decimal] = None
    subsatser: Optional[list] = None

    @cached_property
    def text(self) -> Optional[str]:
        afgiftssats = format_decimal(self.afgiftssats)
        segment_nedre = self.segment_nedre
        segment_øvre = self.segment_øvre

        if self.enhed == Vareafgiftssats.Enhed.SAMMENSAT and self.subsatser:
            return " + ".join([subsats.text for subsats in self.subsatser])

        if self.enhed == Vareafgiftssats.Enhed.LITER:
            if segment_øvre and segment_nedre:
                return _(
                    "{kr} kr. pr liter mellem {nedre} liter og {øvre} liter"
                ).format(
                    kr=afgiftssats,
                    nedre=format_decimal(segment_nedre),
                    øvre=format_decimal(segment_øvre),
                )
            if segment_øvre:
                return _("{kr} kr. pr liter under {øvre} liter").format(
                    kr=afgiftssats, øvre=format_decimal(segment_øvre)
                )
            if segment_nedre:
                return _("{kr} kr. pr liter over {nedre} liter").format(
                    kr=afgiftssats, nedre=format_decimal(segment_nedre)
                )
            return _("{kr} kr. pr liter").format(kr=afgiftssats)

        if self.enhed == Vareafgiftssats.Enhed.KILOGRAM:
            if segment_øvre and segment_nedre:
                return _("{kr} kr. pr kg mellem {nedre} kg og {øvre} kg").format(
                    kr=afgiftssats,
                    nedre=format_decimal(segment_nedre),
                    øvre=format_decimal(segment_øvre),
                )
            if segment_øvre:
                return _("{kr} kr. pr kg under {øvre} kg").format(
                    kr=afgiftssats, øvre=format_decimal(segment_øvre)
                )
            if segment_nedre:
                return _("{kr} kr. pr kg over {nedre} kg").format(
                    kr=afgiftssats, nedre=format_decimal(segment_nedre)
                )
            return _("{kr} kr. pr kg").format(kr=afgiftssats)

        if self.enhed == Vareafgiftssats.Enhed.ANTAL:
            if segment_øvre and segment_nedre:
                return _("{kr} kr. pr stk mellem {nedre} stk og {øvre} stk").format(
                    kr=afgiftssats,
                    nedre=format_int(segment_nedre),
                    øvre=format_int(segment_øvre),
                )
            if segment_øvre:
                return _("{kr} kr. pr stk under {øvre} stk").format(
                    kr=afgiftssats, øvre=format_int(segment_øvre)
                )
            if segment_nedre:
                return _("{kr} kr. pr stk over {nedre} stk").format(
                    kr=afgiftssats, nedre=format_int(segment_nedre)
                )
            return _("{kr} kr. pr stk").format(kr=afgiftssats)

        if self.enhed == Vareafgiftssats.Enhed.PROCENT:
            if segment_øvre and segment_nedre:
                return _("{pct}% af fakturabeløb mellem {nedre} og {øvre}").format(
                    pct=afgiftssats,
                    nedre=format_decimal(segment_nedre),
                    øvre=format_decimal(segment_øvre),
                )
            if segment_øvre:
                return _("{pct}% af fakturabeløb under {øvre}").format(
                    pct=afgiftssats, øvre=format_decimal(segment_øvre)
                )
            if segment_nedre:
                return _("{pct}% af fakturabeløb over {nedre}").format(
                    pct=afgiftssats, nedre=format_decimal(segment_nedre)
                )
            return _("{pct}% af fakturabeløb").format(pct=afgiftssats)
        return None

    def populate_subs(
        self, sub_getter: Callable[[int], Optional[List[Vareafgiftssats]]]
    ) -> None:
        if self.enhed == Vareafgiftssats.Enhed.SAMMENSAT:
            subs = sub_getter(self.id)
            if subs is not None and len(subs) > 0:
                self.subsatser = []
                for subsats in subs:
                    self.subsatser.append(subsats)


def encode_optional_isoformat(d: datetime) -> str | None:
    if d is None:
        return None
    return d.isoformat()


@dataclass
class Afgiftstabel(ToldDataClass):
    id: int
    kladde: bool = False
    gyldig_fra: Optional[datetime] = field(
        metadata=config(
            encoder=encode_optional_isoformat,
            decoder=datetime.fromisoformat,
            mm_field=fields.DateTime(format="iso"),
        ),
        default=None,
    )
    gyldig_til: Optional[datetime] = field(
        metadata=config(
            encoder=encode_optional_isoformat,
            decoder=datetime.fromisoformat,
            mm_field=fields.DateTime(format="iso"),
        ),
        default=None,
    )
    vareafgiftssatser: Optional[List[Vareafgiftssats]] = None


@dataclass
class Notat(ToldDataClass):
    id: int
    tekst: str
    afgiftsanmeldelse: Optional[int]
    privatafgiftsanmeldelse: Optional[int]
    index: int
    oprettet: Optional[datetime] = field(
        metadata=config(
            encoder=encode_optional_isoformat,
            decoder=datetime.fromisoformat,
            mm_field=fields.DateTime(format="iso"),
        ),
        default=None,
    )
    navn: Optional[str] = None


@dataclass
class Aktør(ToldDataClass):
    id: int
    navn: Optional[str]
    adresse: Optional[str]
    postnummer: Optional[int]
    by: Optional[str]
    postbox: Optional[str]
    telefon: Optional[str]
    cvr: Optional[int]
    stedkode: Optional[int] = None


@dataclass
class Afsender(Aktør):
    pass


@dataclass
class Modtager(Aktør):
    kreditordning: bool = False


@dataclass
class Speditør(DataClassJsonMixin):
    cvr: int
    navn: str


class Forsendelsestype(Enum):
    SKIB = "S"
    FLY = "F"


@dataclass
class PostForsendelse(ToldDataClass):
    id: int
    forsendelsestype: Forsendelsestype
    postforsendelsesnummer: str
    afsenderbykode: str
    afgangsdato: date = field(
        metadata=config(
            encoder=date.isoformat,
            decoder=date.fromisoformat,
            mm_field=fields.Date(format="iso"),
        ),
    )
    kladde: bool = False


@dataclass
class FragtForsendelse(ToldDataClass):
    id: int
    forsendelsestype: Forsendelsestype
    fragtbrevsnummer: str
    forbindelsesnr: str
    afgangsdato: date = field(
        metadata=config(
            encoder=date.isoformat,
            decoder=date.fromisoformat,
            mm_field=fields.Date(format="iso"),
        ),
    )
    kladde: bool = False
    fragtbrev: Optional[File] = None


@dataclass
class Varelinje(ToldDataClass):
    id: int
    afgiftsanmeldelse: int
    kladde: bool = False
    vareafgiftssats: Optional[int] = None
    afgiftsbeløb: Optional[Decimal] = None
    fakturabeløb: Optional[Decimal] = None
    mængde: Optional[Decimal] = None
    antal: Optional[int] = None


@dataclass
class Afgiftsanmeldelse(ToldDataClass):
    id: int
    afsender: Union[int, Afsender, None]
    modtager: Union[int, Modtager, None]
    fragtforsendelse: Union[int, FragtForsendelse, None]
    postforsendelse: Union[int, PostForsendelse, None]
    afgift_total: Decimal
    betalt: bool
    status: str
    dato: datetime = field(
        metadata=config(
            encoder=datetime.isoformat,
            decoder=datetime.fromisoformat,
            mm_field=fields.DateTime(format="iso"),
        ),
    )
    beregnet_faktureringsdato: date = field(
        metadata=config(
            encoder=date.isoformat,
            decoder=date.fromisoformat,
            mm_field=fields.Date(format="iso"),
        ),
    )
    leverandørfaktura_nummer: Optional[str] = None
    leverandørfaktura: Optional[File] = None
    indførselstilladelse: Optional[str] = None
    notater: Optional[List[Notat]] = None
    prismeresponses: Optional[List[PrismeResponse]] = None
    varelinjer: Optional[List[Varelinje]] = None
    oprettet_af: Optional[dict] = None
    oprettet_på_vegne_af: Optional[dict] = None
    toldkategori: Optional[str] = None
    fuldmagtshaver: Optional[Speditør] = None
    betales_af: Optional[str] = None
    tf3: Optional[bool] = False

    @property
    def indberetter(self) -> Optional[dict]:
        return self.oprettet_på_vegne_af or self.oprettet_af

    @property
    def afgift_sum(self):
        return sum(
            [
                varelinje.afgiftsbeløb
                for varelinje in self.varelinjer
                if varelinje.afgiftsbeløb or []
            ]
        )

    @property
    def forbindelsesnummer(self):
        if self.fragtforsendelse:
            return self.fragtforsendelse.forbindelsesnr

    @property
    def afgangsdato(self):
        if self.fragtforsendelse:
            return self.fragtforsendelse.afgangsdato
        if self.postforsendelse:
            return self.postforsendelse.afgangsdato


@dataclass
class HistoricAfgiftsanmeldelse(Afgiftsanmeldelse):
    history_username: Optional[str] = None
    history_date: Optional[datetime] = field(
        metadata=config(
            encoder=datetime.isoformat,
            decoder=datetime.fromisoformat,
            mm_field=fields.DateTime(format="iso"),
        ),
        default=None,
    )


@dataclass
class PrismeResponse(ToldDataClass):
    id: Optional[int]
    afgiftsanmeldelse: Union[int, Afgiftsanmeldelse]
    delivery_date: Optional[datetime] = field(
        metadata=config(
            encoder=encode_optional_isoformat,
            decoder=datetime.fromisoformat,
            mm_field=fields.DateTime(format="iso"),
        ),
        default=None,
    )
    rec_id: Optional[int] = None
    tax_notification_number: Optional[int] = None


@dataclass
class PrivatAfgiftsanmeldelse(ToldDataClass):
    id: int
    cpr: int
    anonym: bool
    navn: str
    adresse: str
    postnummer: int
    by: str
    telefon: str
    leverandørfaktura_nummer: str
    leverandørfaktura: File
    bookingnummer: str
    status: str
    indleveringsdato: date = field(
        metadata=config(
            encoder=date.isoformat,
            decoder=date.fromisoformat,
            mm_field=fields.Date(format="iso"),
        ),
    )
    # notater: Optional[List[Notat]]
    # prismeresponses: Optional[List[PrismeResponse]]
    oprettet: datetime = field(
        metadata=config(
            encoder=datetime.isoformat,
            decoder=datetime.fromisoformat,
            mm_field=fields.DateTime(format="iso"),
        ),
    )
    oprettet_af: dict
    payment_status: str
    indførselstilladelse: Optional[str] = None
    varelinjer: Optional[List[Varelinje]] = None
    notater: Optional[List[Notat]] = None

    @property
    def afgift_sum(self):
        return round_decimal(
            sum([varelinje.afgiftsbeløb for varelinje in self.varelinjer or []])
        )

    @property
    def tillægsafgift(self):
        return round_decimal(
            Decimal(settings.TILLÆGSAFGIFT_FAKTOR)
            * sum(
                [
                    varelinje.afgiftsbeløb
                    for varelinje in self.varelinjer or []
                    if varelinje.vareafgiftssats.har_privat_tillægsafgift_alkohol
                ]
            )
        )

    @property
    def ekspeditionsgebyr(self):
        return round_decimal(Decimal(settings.EKSPEDITIONSGEBYR))

    @property
    def afgift_total(self):
        return self.afgift_sum + self.tillægsafgift + self.ekspeditionsgebyr


@dataclass
class Indberetter(ToldDataClass):
    cvr: int


@dataclass
class JwtTokenInfo:
    access_token: str
    refresh_token: str
    access_token_timestamp: float = field(
        default_factory=time
    )  # default to timestamp at instance creation
    refresh_token_timestamp: float = field(default_factory=time)
    synchronized: bool = False

    @staticmethod
    def load(request: HttpRequest):
        try:
            return JwtTokenInfo(
                access_token=request.session["access_token"],
                access_token_timestamp=float(request.session["access_token_timestamp"]),
                refresh_token=request.session["refresh_token"],
                refresh_token_timestamp=float(
                    request.session["refresh_token_timestamp"]
                ),
                synchronized=True,
            )
        except KeyError:
            return None

    def save(self, request: HttpRequest, save_refresh_token: bool = False):
        if not self.synchronized:
            request.session["access_token"] = self.access_token
            request.session["access_token_timestamp"] = self.access_token_timestamp
            if save_refresh_token:
                request.session["refresh_token"] = self.refresh_token
                request.session["refresh_token_timestamp"] = (
                    self.refresh_token_timestamp
                )
            self.synchronized = True


@dataclass
class User(ToldDataClass):
    id: int
    username: str
    first_name: str
    last_name: str
    email: str
    is_superuser: bool
    groups: List[str]
    permissions: List[str]
    indberetter_data: Optional[Indberetter] = None
    jwt_token: Optional[JwtTokenInfo] = None
    twofactor_enabled: bool = False

    @property
    def cvr(self):
        if self.indberetter_data:
            return self.indberetter_data.cvr

    @property
    def is_authenticated(self):
        return self.jwt_token is not None

    @property
    def is_anonymous(self):
        return self.is_authenticated

    def get_username(self):
        return self.username


@dataclass
class TOTPDevice(ToldDataClass):
    user_id: int
    key: str
    tolerance: int
    t0: int
    step: int
    drift: int
    digits: int
    name: str
    confirmed: bool


@dataclass
class Toldkategori(ToldDataClass):
    kategori: str
    navn: str
    kræver_cvr: bool
