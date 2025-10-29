# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
# mypy: disable-error-code="call-arg, attr-defined"

import base64
import logging
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Annotated, List, Optional, Tuple
from uuid import uuid4

import django.utils.timezone as tz
from aktør.api import AfsenderOut, ModtagerOut, SpeditørOut
from anmeldelse.models import (
    Afgiftsanmeldelse,
    Notat,
    PrismeResponse,
    PrivatAfgiftsanmeldelse,
    Toldkategori,
    Varelinje,
)
from common.api import UserOut, get_auth_methods
from common.models import IndberetterProfile
from common.util import coerce_num_to_str
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db.models import Q, QuerySet, Sum
from django.db.models.expressions import F, Value
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.utils import timezone
from forsendelse.api import FragtforsendelseOut, PostforsendelseOut
from ninja import Field, FilterSchema, ModelSchema, Query
from ninja_extra import api_controller, permissions, route
from ninja_extra.exceptions import PermissionDenied
from ninja_extra.pagination import paginate
from ninja_extra.schemas import NinjaPaginationResponseSchema
from payment.models import Payment
from project.util import RestPermission, json_dump
from pydantic import BeforeValidator, root_validator
from sats.models import Vareafgiftssats

log = logging.getLogger(__name__)


class AfgiftsanmeldelseIn(ModelSchema):
    afsender_id: int
    modtager_id: int
    postforsendelse_id: Optional[int] = None
    fragtforsendelse_id: Optional[int] = None
    leverandørfaktura: Optional[str] = None  # Base64
    leverandørfaktura_navn: Optional[str] = None
    oprettet_på_vegne_af_id: Optional[int] = None
    kladde: Optional[bool] = False
    fuldmagtshaver_id: Optional[int] = None
    tf3: Optional[bool] = False
    leverandørfaktura_nummer: Annotated[
        Optional[str], BeforeValidator(coerce_num_to_str)
    ] = None
    indførselstilladelse_alkohol: Annotated[
        Optional[str], BeforeValidator(coerce_num_to_str)
    ] = None
    indførselstilladelse_tobak: Annotated[
        Optional[str], BeforeValidator(coerce_num_to_str)
    ] = None
    toldkategori: Annotated[Optional[str], BeforeValidator(coerce_num_to_str)] = None
    # Deprecated input parameter
    indførselstilladelse: Annotated[
        Optional[str],
        Field(
            deprecated=(
                "This field is deprecated as of version 1.91.1."
                "Use indførselstilladelse_alkohol or indførselstilladelse_tobak instead"
            )
        ),
        BeforeValidator(coerce_num_to_str),
    ] = None

    class Config:
        model = Afgiftsanmeldelse
        model_fields = [
            "leverandørfaktura_nummer",
            "betales_af",
            "indførselstilladelse_alkohol",
            "indførselstilladelse_tobak",
            "betalt",
            "toldkategori",
        ]


class PartialAfgiftsanmeldelseIn(ModelSchema):
    afsender_id: Optional[int] = None
    modtager_id: Optional[int] = None
    postforsendelse_id: Optional[int] = None
    fragtforsendelse_id: Optional[int] = None
    leverandørfaktura: Optional[str] = None  # Base64
    leverandørfaktura_navn: Optional[str] = None
    betales_af: Optional[str] = None
    kladde: Optional[bool] = False
    fuldmagtshaver_id: Optional[int] = None
    status: Optional[str] = None
    tf3: Optional[bool] = None
    leverandørfaktura_nummer: Annotated[
        Optional[str], BeforeValidator(coerce_num_to_str)
    ] = None
    indførselstilladelse_alkohol: Annotated[
        Optional[str], BeforeValidator(coerce_num_to_str)
    ] = None
    indførselstilladelse_tobak: Annotated[
        Optional[str], BeforeValidator(coerce_num_to_str)
    ] = None
    toldkategori: Annotated[Optional[str], BeforeValidator(coerce_num_to_str)] = None
    # Deprecated input parameter
    indførselstilladelse: Annotated[
        Optional[str],
        Field(
            deprecated=(
                "This field is deprecated as of version 1.91.1."
                "Use indførselstilladelse_alkohol or indførselstilladelse_tobak instead"
            )
        ),
        BeforeValidator(coerce_num_to_str),
    ] = None

    class Config:
        model = Afgiftsanmeldelse
        model_fields = [
            "leverandørfaktura_nummer",
            "betales_af",
            "indførselstilladelse_alkohol",
            "indførselstilladelse_tobak",
            "betalt",
            "status",
            "toldkategori",
        ]
        model_fields_optional = "__all__"


class AfgiftsanmeldelseOut(ModelSchema):
    oprettet_af: Optional[UserOut]
    oprettet_på_vegne_af: Optional[UserOut]
    fuldmagtshaver: Optional[SpeditørOut]

    class Config:
        model = Afgiftsanmeldelse
        model_fields = [
            "id",
            "afsender",
            "modtager",
            "fragtforsendelse",
            "postforsendelse",
            "leverandørfaktura_nummer",
            "leverandørfaktura",
            "betales_af",
            "indførselstilladelse_alkohol",
            "indførselstilladelse_tobak",
            "afgift_total",
            "betalt",
            "dato",
            "status",
            "oprettet_af",
            "oprettet_på_vegne_af",
            "toldkategori",
            "fuldmagtshaver",
            "tf3",
        ]

    beregnet_faktureringsdato: str

    @staticmethod
    def resolve_beregnet_faktureringsdato(obj: Afgiftsanmeldelse):
        if hasattr(obj, "beregnet_faktureringsdato"):
            beregnet_faktureringsdato = obj.beregnet_faktureringsdato
        else:
            beregnet_faktureringsdato = Afgiftsanmeldelse.beregn_faktureringsdato(obj)
        return beregnet_faktureringsdato.isoformat()


class AfgiftsanmeldelseFullOut(AfgiftsanmeldelseOut):
    afsender: AfsenderOut
    modtager: ModtagerOut
    fragtforsendelse: Optional[FragtforsendelseOut]
    postforsendelse: Optional[PostforsendelseOut]
    fuldmagtshaver: Optional[SpeditørOut]


class AfgiftsanmeldelseHistoryOut(AfgiftsanmeldelseOut):
    history_username: Optional[str]
    history_date: datetime

    @staticmethod
    def resolve_history_username(historical_afgiftsanmeldelse):
        return (
            historical_afgiftsanmeldelse.history_user
            and historical_afgiftsanmeldelse.history_user.username
        )


class AfgiftsanmeldelseHistoryFullOut(AfgiftsanmeldelseFullOut):
    history_username: Optional[str]
    history_date: datetime

    @staticmethod
    def resolve_history_username(historical_afgiftsanmeldelse):
        return (
            historical_afgiftsanmeldelse.history_user
            and historical_afgiftsanmeldelse.history_user.username
        )


class AfgiftsanmeldelseFilterSchema(FilterSchema):
    id: Annotated[Optional[List[int]], Field(None, q="__in")]
    afsender: Annotated[Optional[int], Field(None)]
    modtager: Annotated[Optional[int], Field(None)]
    fragtforsendelse: Annotated[Optional[int], Field(None)]
    postforsendelse: Annotated[Optional[int], Field(None)]
    leverandørfaktura_nummer: Annotated[
        Optional[str], Field(None, q="leverandørfaktura_nummer__iexact")
    ]
    # leverandørfaktura = models.FileField(
    #     upload_to=afgiftsanmeldelse_upload_to,
    # )
    betales_af: Annotated[Optional[str], Field(None)]
    indførselstilladelse_alkohol: Annotated[Optional[str], Field(None)]
    indførselstilladelse_tobak: Annotated[Optional[str], Field(None)]
    betalt: Annotated[Optional[bool], Field(None)]
    status: Annotated[Optional[str], Field(None)]
    fuldmagtshaver: Annotated[Optional[int], Field(None)]
    fuldmagtshaver_isnull: Annotated[
        Optional[bool], Field(None, q="fuldmagtshaver__isnull")
    ]
    dato_efter: Annotated[Optional[date], Field(None, q="dato__gte")]
    dato_før: Annotated[Optional[date], Field(None, q="dato__lt")]
    vareart: Annotated[
        Optional[str], Field(None, q="varelinje__vareafgiftssats__vareart_da")
    ]
    afsenderbykode_or_forbindelsesnr: Annotated[
        Optional[str],
        Field(
            None,
            q=[
                "postforsendelse__afsenderbykode__iexact",
                "fragtforsendelse__forbindelsesnr__iexact",
            ],
        ),
    ]
    postforsendelsesnummer_or_fragtbrevsnummer: Annotated[
        Optional[str],
        Field(
            None,
            q=[
                "postforsendelse__postforsendelsesnummer__iexact",
                "fragtforsendelse__fragtbrevsnummer__iexact",
            ],
        ),
    ]
    notat: Annotated[Optional[str], Field(None, q="notat__tekst__icontains")]
    toldkategori: Annotated[Optional[List[str]], Field(None)]
    tf3: Annotated[Optional[bool], Field(None)]

    def filter_toldkategori(self, value: List[str]) -> Q | None:
        if value is None:
            return None
        include_none = "no_category" in value
        if include_none:
            value.remove("no_category")
            return Q(toldkategori__in=value) | Q(toldkategori__isnull=True)
        else:
            return Q(toldkategori__in=value)


class AfgiftsanmeldelsePermission(RestPermission):
    appname = "anmeldelse"
    modelname = "afgiftsanmeldelse"


@api_controller(
    "/afgiftsanmeldelse",
    tags=["Afgiftsanmeldelse"],
    permissions=[permissions.IsAuthenticated & AfgiftsanmeldelsePermission],
)
class AfgiftsanmeldelseAPI:
    @route.post("", auth=get_auth_methods(), url_name="afgiftsanmeldelse_create")
    def create(
        self,
        payload: AfgiftsanmeldelseIn,
    ):
        try:
            data = payload.dict()
            leverandørfaktura = data.pop("leverandørfaktura", None)
            leverandørfaktura_navn = data.pop("leverandørfaktura_navn", None) or (
                str(uuid4()) + ".pdf"
            )
            kladde = data.pop("kladde", False)
            if kladde:
                data["status"] = "kladde"

            if "betales_af" in data and data["betales_af"] == "":
                data["betales_af"] = None
            # TODO: delete once https://redmine.magenta.dk/issues/67184 is done
            if (
                data["indførselstilladelse_alkohol"] is None
                and data["indførselstilladelse_tobak"] is None
                and data["indførselstilladelse"] is not None
            ):
                data["indførselstilladelse_alkohol"] = data["indførselstilladelse"]
                data["indførselstilladelse_tobak"] = data["indførselstilladelse"]
            if "indførselstilladelse" in data:
                del data["indførselstilladelse"]

            item = Afgiftsanmeldelse.objects.create(
                **data, oprettet_af=self.context.request.user
            )
            if leverandørfaktura is not None:
                item.leverandørfaktura = ContentFile(
                    base64.b64decode(leverandørfaktura), name=leverandørfaktura_navn
                )
                log.info(
                    "Rest API opretter TF10 med leverandørfaktura '%s' (%d bytes)",
                    leverandørfaktura_navn,
                    item.leverandørfaktura.size,
                )
                item.save()
            else:
                log.info("Rest API opretter TF10 uden leverandørfaktura")
            return {"id": item.id}
        except ValidationError as e:
            return HttpResponseBadRequest(
                json_dump(e.message_dict), content_type="application/json"
            )

    # List afgiftsanmeldelser. Relaterede objekter refereres med deres id
    @route.get(
        "",
        response=NinjaPaginationResponseSchema[AfgiftsanmeldelseOut],
        auth=get_auth_methods(),
        url_name="afgiftsanmeldelse_list",
    )
    @paginate()  # https://eadwincode.github.io/django-ninja-extra/tutorial/pagination/
    def list(
        self,
        filters: AfgiftsanmeldelseFilterSchema = Query(...),
        sort: Optional[str] = None,
        order: Optional[str] = None,
    ):
        qs = self.filter_user(Afgiftsanmeldelse.objects.all())
        # https://django-ninja.rest-framework.com/guides/input/filtering/
        qs = filters.filter(qs)
        if filters.status != "slettet":
            qs = qs.exclude(status="slettet")
        order_by = self.map_sort(sort, order)
        if order_by:
            qs = qs.order_by(order_by, "id")
        return list(qs)

    # List afgiftsanmeldelser. Relaterede objekter nestes i hvert item
    @route.get(
        "full",
        response=NinjaPaginationResponseSchema[AfgiftsanmeldelseFullOut],
        auth=get_auth_methods(),
        url_name="afgiftsanmeldelse_list_full",
    )
    @paginate()  # https://eadwincode.github.io/django-ninja-extra/tutorial/pagination/
    def list_full(
        self,
        filters: AfgiftsanmeldelseFilterSchema = Query(...),
        sort: Optional[str] = None,
        order: Optional[str] = None,
    ):
        qs = self.filter_user(Afgiftsanmeldelse.objects.all())
        # https://django-ninja.rest-framework.com/guides/input/filtering/
        qs = filters.filter(qs)
        if filters.status != "slettet":
            qs = qs.exclude(status="slettet")
        order_by = self.map_sort(sort, order)
        if order_by:
            qs = qs.order_by(order_by, "id")
        return list(qs)

    @route.get(
        "/{id}",
        response=AfgiftsanmeldelseOut,
        auth=get_auth_methods(),
        url_name="afgiftsanmeldelse_get",
    )
    def get(self, id: int):
        item = get_object_or_404(Afgiftsanmeldelse, id=id)
        self.check_user(item)
        return item

    @route.get(
        "/{id}/full",
        response=AfgiftsanmeldelseFullOut,
        auth=get_auth_methods(),
        url_name="afgiftsanmeldelse_get_full",
    )
    def get_full(self, id: int):
        item = get_object_or_404(Afgiftsanmeldelse, id=id)
        self.check_user(item)
        return item

    @route.get(
        "/{id}/history",
        response=NinjaPaginationResponseSchema[AfgiftsanmeldelseHistoryOut],
        auth=get_auth_methods(),
        url_name="afgiftsanmeldelse_get_history",
    )
    @paginate()  # https://eadwincode.github.io/django-ninja-extra/tutorial/pagination/
    def get_history(self, id: int):
        item = get_object_or_404(Afgiftsanmeldelse, id=id)
        self.check_user(item)
        return list(item.history.order_by("history_date"))

    @route.get(
        "/{id}/history/{index}",
        response=AfgiftsanmeldelseHistoryFullOut,
        auth=get_auth_methods(),
        url_name="afgiftsanmeldelse_get_history_item",
    )
    def get_afgiftsanmeldelse_history_item(self, id: int, index: int):
        item = get_object_or_404(Afgiftsanmeldelse, id=id)
        self.check_user(item)
        return item.history.order_by("history_date")[index]

    @staticmethod
    def map_sort(sort, order):
        if sort is not None:
            if hasattr(Afgiftsanmeldelse, sort):
                if sort in ("afsender", "modtager"):
                    sort += "__navn"
            elif sort == "forbindelsesnummer":
                sort = "fragtforsendelse__forbindelsesnr"
            else:
                return None
            return ("-" if order == "desc" else "") + sort
        return None

    @route.patch("/{id}", auth=get_auth_methods(), url_name="afgiftsanmeldelse_update")
    def update(
        self,
        id: int,
        payload: PartialAfgiftsanmeldelseIn,
    ):
        item = get_object_or_404(Afgiftsanmeldelse, id=id)
        self.check_user(item)

        if payload.status in ("godkendt", "afvist", "afsluttet"):
            if not self.check_perm("anmeldelse.approve_reject_anmeldelse"):
                raise PermissionDenied

        data = payload.dict(exclude_unset=True)
        # TODO: delete once https://redmine.magenta.dk/issues/67184 is done
        if (
            "indførselstilladelse_alkohol" not in data
            and "indførselstilladelse_tobak" not in data
            and "indførselstilladelse" in data
        ):
            data["indførselstilladelse_alkohol"] = data["indførselstilladelse"]
            data["indførselstilladelse_tobak"] = data["indførselstilladelse"]
        if "indførselstilladelse" in data:
            del data["indførselstilladelse"]

        # Draft double-check
        kladde = data.pop("kladde", False)
        if not kladde and item.status == "kladde":
            data["status"] = "ny"

        # Assign the payload values to the item
        for attr, value in data.items():
            if value is not None:
                setattr(item, attr, value)

        # Handle invoices - after payload-handling
        leverandørfaktura = data.pop("leverandørfaktura", None)
        leverandørfaktura_navn = data.pop("leverandørfaktura_navn", None) or (
            str(uuid4()) + ".pdf"
        )

        if leverandørfaktura is not None:
            item.leverandørfaktura = ContentFile(
                base64.b64decode(leverandørfaktura), name=leverandørfaktura_navn
            )
            log.info(
                "Rest API opdaterer TF10 %d med leverandørfaktura '%s' (%d bytes)",
                id,
                leverandørfaktura_navn,
                item.leverandørfaktura.size,
            )
        else:
            log.info("Rest API opdaterer TF10 %d uden at sætte leverandørfaktura", id)
            if item.leverandørfaktura:
                log.info(
                    "Der findes allerede leverandørfaktura '%s' (%d bytes)",
                    item.leverandørfaktura.name,
                    item.leverandørfaktura.size,
                )
            else:
                log.info("Der findes ikke en eksisterende leverandørfaktura")

        # Persist data & return
        item.save()
        return {"success": True}

    @route.delete(
        "/{id}",
        auth=get_auth_methods(),
        url_name="afgiftsanmeldelse_delete",
    )
    def delete(self, id: int):
        """Delete afgiftsanmeldelse.
        Only allowed if status is 'ny' or 'kladde', unless user is an admin.

        NOTE: Normally DELETE returns 204, but since our existing code returns 200
        + a dict with a success key, we do the same here.
        """
        item = get_object_or_404(Afgiftsanmeldelse, id=id)
        self.check_user(item)

        if item.status not in self.get_allowed_statuses_delete():
            raise PermissionDenied(
                "You are not allowed to delete 'afgiftsanmeldelser' "
                f"with status: {item.status}"
            )

        item.delete()
        return {"success": True}

    def check_perm(self, permission):
        return self.context.request.user.has_perm(permission)

    def get_or_none(self, classmodel, **kwargs):
        try:
            return classmodel.objects.get(**kwargs)
        except classmodel.DoesNotExist:
            return None

    def get_allowed_statuses_delete(self) -> List[str]:
        user = self.context.request.user
        if (
            self.get_or_none(Group, name="Toldmedarbejdere") in user.groups.all()
            or user.is_staff
        ):
            return ["ny", "kladde", "afvist", "godkendt"]
        else:
            return ["ny", "kladde"]

    def filter_user(self, qs: QuerySet) -> QuerySet:
        user = self.context.request.user
        if self.check_perm("anmeldelse.view_all_anmeldelse"):
            return qs
        if self.check_perm("anmeldelse.view_approved_anmeldelse"):
            # Hvis brugeren må se alle godkendte, filtrer på dem
            return qs.filter(status__in=("godkendt", "afsluttet"))
        # Hvis brugeren hverken må se alle eller godkendte, filtrér på opretteren
        try:
            cvr = user.indberetter_data.cvr
        except IndberetterProfile.DoesNotExist:
            return qs.none()
        if cvr is None:
            return qs.none()
        return qs.filter(
            Q(oprettet_af__indberetter_data__cvr=cvr)
            | Q(oprettet_på_vegne_af__indberetter_data__cvr=cvr)
            | Q(fuldmagtshaver__cvr=cvr)
        ).exclude(status="slettet")

    def check_user(self, item: Afgiftsanmeldelse):
        if not self.filter_user(Afgiftsanmeldelse.objects.filter(id=item.id)).exists():
            raise PermissionDenied

    @staticmethod
    def get_historical(id: int, index: int) -> Tuple[Afgiftsanmeldelse, datetime]:
        anmeldelse = Afgiftsanmeldelse.objects.get(id=id)
        historiske_anmeldelser = anmeldelse.history.order_by("history_date")
        if index < 0 or index >= historiske_anmeldelser.count():
            raise Http404
        next = historiske_anmeldelser[index].next_record
        if next:  # next er None hvis vi har fat i den seneste version
            as_of = next.history_date - timedelta(microseconds=1)
        else:
            as_of = timezone.now()
        anmeldelse = anmeldelse.history.as_of(as_of)
        return anmeldelse, as_of

    @staticmethod
    def get_historical_count(id: int):
        anmeldelse = Afgiftsanmeldelse.objects.get(id=id)
        return anmeldelse.history.count()


class PrivatAfgiftsanmeldelseIn(ModelSchema):
    bookingnummer: Annotated[str, BeforeValidator(coerce_num_to_str)]
    telefon: Annotated[str, BeforeValidator(coerce_num_to_str)]
    leverandørfaktura: Optional[str] = None  # Base64
    leverandørfaktura_navn: Optional[str] = None
    leverandørfaktura_nummer: Annotated[
        Optional[str], BeforeValidator(coerce_num_to_str)
    ] = None
    indførselstilladelse: Annotated[
        Optional[str], BeforeValidator(coerce_num_to_str)
    ] = None

    class Config:
        model = PrivatAfgiftsanmeldelse
        model_fields = [
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
        ]


class PartialPrivatAfgiftsanmeldelseIn(ModelSchema):
    bookingnummer: Annotated[Optional[str], BeforeValidator(coerce_num_to_str)] = None
    telefon: Annotated[Optional[str], BeforeValidator(coerce_num_to_str)] = None
    leverandørfaktura: Optional[str] = None  # Base64
    leverandørfaktura_navn: Optional[str] = None
    leverandørfaktura_nummer: Annotated[
        Optional[str], BeforeValidator(coerce_num_to_str)
    ] = None
    indførselstilladelse: Annotated[
        Optional[str], BeforeValidator(coerce_num_to_str)
    ] = None

    class Config:
        model = PrivatAfgiftsanmeldelse
        model_fields = [
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
            "status",
        ]
        model_fields_optional = "__all__"


class PrivatAfgiftsanmeldelseOut(ModelSchema):
    oprettet_af: Optional[UserOut]
    payment_status: Optional[str]

    class Config:
        model = PrivatAfgiftsanmeldelse
        model_fields = [
            "id",
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
            "leverandørfaktura",
            "oprettet",
            "oprettet_af",
            "status",
            "anonym",
        ]

    @staticmethod
    def resolve_payment_status(obj: PrivatAfgiftsanmeldelse):
        qs = Payment.objects.filter(declaration=obj)
        if qs.exists():
            if qs.filter(status="paid").exists():
                return "paid"
            first = qs.first()
            if first:
                return first.status
        return "created"


class PrivatAfgiftsanmeldelseFilterSchema(FilterSchema):
    id: Annotated[Optional[List[int]], Field(None, q="id__in")]
    cpr: Annotated[Optional[int], Field(None)]
    navn: Annotated[Optional[str], Field(None, q="navn__icontains")]
    adresse: Annotated[Optional[str], Field(None, q="adresse__icontains")]
    postnummer: Annotated[Optional[int], Field(None)]
    by: Annotated[Optional[str], Field(None, q="by__icontains")]
    telefon: Annotated[Optional[str], Field(None, q="telefon__icontains")]
    leverandørfaktura_nummer: Annotated[
        Optional[str], Field(None, q="leverandørfaktura_nummer__icontains")
    ]
    indførselstilladelse: Annotated[
        Optional[str], Field(None, q="indførselstilladelse__icontains")
    ]
    indleveringsdato_efter: Annotated[
        Optional[date], Field(None, q="indleveringsdato__gte")
    ]
    indleveringsdato_før: Annotated[
        Optional[date], Field(None, q="indleveringsdato__lt")
    ]
    oprettet_efter: Annotated[Optional[date], Field(None, q="oprettet__gte")]
    oprettet_før: Annotated[Optional[date], Field(None, q="oprettet__lt")]
    vareart: Annotated[
        Optional[str], Field(None, q="varelinje__vareafgiftssats__vareart_da")
    ]
    status: Annotated[Optional[str], Field(None)]
    anonym: Annotated[Optional[bool], Field(None)]
    notat: Annotated[Optional[str], Field(None, q="notat__tekst__icontains")]


class PrivatAfgiftsanmeldelsePermission(RestPermission):
    appname = "anmeldelse"
    modelname = "privatafgiftsanmeldelse"


@api_controller(
    "/privat_afgiftsanmeldelse",
    tags=["PrivatAfgiftsanmeldelse"],
    permissions=[permissions.IsAuthenticated & PrivatAfgiftsanmeldelsePermission],
)
class PrivatAfgiftsanmeldelseAPI:
    @route.post("", auth=get_auth_methods(), url_name="privat_afgiftsanmeldelse_create")
    def create(
        self,
        payload: PrivatAfgiftsanmeldelseIn,
    ):
        try:
            data = payload.dict()
            leverandørfaktura = data.pop("leverandørfaktura")
            leverandørfaktura_navn = data.pop("leverandørfaktura_navn", None) or (
                str(uuid4()) + ".pdf"
            )
            item = PrivatAfgiftsanmeldelse.objects.create(
                **data, oprettet_af=self.context.request.user
            )

            item.leverandørfaktura = ContentFile(
                base64.b64decode(leverandørfaktura), name=leverandørfaktura_navn
            )
            item.save()
            return {"id": item.id}
        except ValidationError as e:
            return HttpResponseBadRequest(
                json_dump(e.message_dict), content_type="application/json"
            )

    @route.get(
        "/{id}",
        response=PrivatAfgiftsanmeldelseOut,
        auth=get_auth_methods(),
        url_name="privat_afgiftsanmeldelse_get",
    )
    def get(self, id: int):
        item = get_object_or_404(PrivatAfgiftsanmeldelse, id=id)
        self.check_user(item)
        return item

    @route.get(
        "",
        response=NinjaPaginationResponseSchema[PrivatAfgiftsanmeldelseOut],
        auth=get_auth_methods(),
        url_name="privat_afgiftsanmeldelse_list",
    )
    @paginate()  # https://eadwincode.github.io/django-ninja-extra/tutorial/pagination/
    def list(
        self,
        filters: PrivatAfgiftsanmeldelseFilterSchema = Query(...),
        sort: Optional[str] = None,
        order: Optional[str] = None,
    ):
        qs = self.filter_user(PrivatAfgiftsanmeldelse.objects.all())
        # https://django-ninja.rest-framework.com/guides/input/filtering/
        qs = filters.filter(qs)
        order_by = self.map_sort(sort, order)
        if order_by:
            qs = qs.order_by(order_by, "id")
        return list(qs)

    def filter_user(self, qs: QuerySet) -> QuerySet:
        user = self.context.request.user
        if user.has_perm("anmeldelse.view_all_privatafgiftsanmeldelse"):
            return qs
        return qs.filter(Q(oprettet_af=user) | Q(oprettet_på_vegne_af=user))

    def check_user(self, item: PrivatAfgiftsanmeldelse):
        if not self.filter_user(
            PrivatAfgiftsanmeldelse.objects.filter(id=item.id)
        ).exists():
            raise PermissionDenied

    @staticmethod
    def map_sort(sort, order):
        if sort is not None:
            if hasattr(PrivatAfgiftsanmeldelse, sort):
                return ("-" if order == "desc" else "") + sort
        return None

    @route.get(
        "seneste_indførselstilladelse/{cpr}",
        auth=get_auth_methods(),
        url_name="privat_afgiftsanmeldelse_latest",
    )
    def get_latest(self, cpr: int):
        anmeldelse = (
            PrivatAfgiftsanmeldelse.objects.filter(cpr=cpr)
            .order_by("-oprettet")
            .first()
        )
        if anmeldelse:
            self.check_user(anmeldelse)
            return anmeldelse.pk
        return None

    @route.patch(
        "/{id}", auth=get_auth_methods(), url_name="privatafgiftsanmeldelse_update"
    )
    def update(
        self,
        id: int,
        payload: PartialPrivatAfgiftsanmeldelseIn,
    ):
        item = get_object_or_404(PrivatAfgiftsanmeldelse, id=id)
        self.check_user(item)
        data = payload.dict(exclude_unset=True)
        leverandørfaktura = data.pop("leverandørfaktura", None)
        for attr, value in data.items():
            if value is not None:
                setattr(item, attr, value)
        if leverandørfaktura is not None:
            item.leverandørfaktura = ContentFile(
                base64.b64decode(leverandørfaktura), name=str(uuid4()) + ".pdf"
            )
        item.save()
        return {"success": True}

    @staticmethod
    def get_historical(id: int, index: int) -> Tuple[PrivatAfgiftsanmeldelse, datetime]:
        anmeldelse = PrivatAfgiftsanmeldelse.objects.get(id=id)
        historiske_anmeldelser = anmeldelse.history.order_by("history_date")
        if index < 0 or index >= historiske_anmeldelser.count():
            raise Http404
        next = historiske_anmeldelser[index].next_record
        if next:  # next er None hvis vi har fat i den seneste version
            as_of = next.history_date - timedelta(microseconds=1)
        else:
            as_of = timezone.now()
        anmeldelse = anmeldelse.history.as_of(as_of)
        return anmeldelse, as_of

    @staticmethod
    def get_historical_count(id: int):
        anmeldelse = PrivatAfgiftsanmeldelse.objects.get(id=id)
        return anmeldelse.history.count()


class VarelinjeIn(ModelSchema):
    fakturabeløb: Optional[str] = None
    afgiftsanmeldelse_id: Optional[int] = None
    privatafgiftsanmeldelse_id: Optional[int] = None
    vareafgiftssats_id: Optional[int] = None

    vareafgiftssats_afgiftsgruppenummer: Optional[int] = None

    class Config:
        model = Varelinje
        model_fields = ["mængde", "antal", "kladde", "fakturabeløb"]
        model_fields_optional = ["mængde", "antal", "kladde", "fakturabeløb"]

    @root_validator(pre=False, skip_on_failure=True)
    def enhed_must_have_corresponding_field(cls, values):
        if values.get("kladde") is not True:
            vareafgiftssats_id: int | None = values.get("vareafgiftssats_id")
            vareafgiftssats_afgiftsgruppenummer = values.get(
                "vareafgiftssats_afgiftsgruppenummer"
            )
            id = None
            if vareafgiftssats_afgiftsgruppenummer not in (None, 0):
                try:
                    id = VarelinjeAPI.get_varesats_id_by_kode(
                        values.get("afgiftsanmeldelse_id"),
                        values.get("privatafgiftsanmeldelse_id"),
                        vareafgiftssats_afgiftsgruppenummer,
                    )
                except Http404:
                    pass
                if id is None or type(id) is not int:
                    raise ValidationError(
                        {
                            "vareafgiftssats_afgiftsgruppenummer": "Did not "
                            "find a valid varesats based on "
                            "vareafgiftssats_afgiftsgruppenummer "
                            f"{vareafgiftssats_afgiftsgruppenummer}"
                        }
                    )
                enhed = Vareafgiftssats.objects.get(id=id).enhed
            elif vareafgiftssats_id not in (None, 0):
                id = vareafgiftssats_id
                try:
                    enhed = Vareafgiftssats.objects.get(id=id).enhed
                except Vareafgiftssats.DoesNotExist:
                    raise ValidationError(
                        {"vareafgiftssats_id": f"object with id {id} does not exist"}
                    )
            else:
                raise ValidationError(
                    {
                        "__all__": "Must specify either vareafgiftssats_id or "
                        "vareafgiftssats_afgiftsgruppenummer"
                    }
                )

            if enhed == Vareafgiftssats.Enhed.ANTAL and values.get("antal") is None:
                raise ValidationError({"__all__": "Must set antal"})
            if (
                enhed == Vareafgiftssats.Enhed.PROCENT
                and values.get("fakturabeløb") is None
            ):
                raise ValidationError({"__all__": "Must set fakturabeløb"})
            if (
                enhed
                in (
                    Vareafgiftssats.Enhed.KILOGRAM,
                    Vareafgiftssats.Enhed.LITER,
                )
                and values.get("mængde") is None
            ):
                raise ValidationError({"__all__": "Must set mængde"})
        return values


class PartialVarelinjeIn(ModelSchema):
    afgiftsanmeldelse_id: Optional[int] = None
    vareafgiftssats_id: Optional[int] = None

    class Config:
        model = Varelinje
        model_fields = [
            "mængde",
            "antal",
            "fakturabeløb",
            "kladde",
        ]
        model_fields_optional = "__all__"


class VarelinjeOut(ModelSchema):
    class Config:
        model = Varelinje
        model_fields = [
            "id",
            "afgiftsanmeldelse",
            "privatafgiftsanmeldelse",
            "vareafgiftssats",
            "mængde",
            "antal",
            "fakturabeløb",
            "afgiftsbeløb",
            "kladde",
        ]


class VarelinjeFilterSchema(FilterSchema):
    afgiftsanmeldelse: Optional[int] = None
    privatafgiftsanmeldelse: Optional[int] = None
    vareafgiftssats: Optional[int] = None
    mængde: Optional[Decimal] = None
    antal: Optional[int] = None
    fakturabeløb: Optional[Decimal] = None
    afgiftsbeløb: Optional[Decimal] = None
    kladde: Optional[bool] = None


class VarelinjePermission(RestPermission):
    appname = "anmeldelse"
    modelname = "varelinje"


@api_controller(
    "/varelinje",
    tags=["Varelinje"],
    permissions=[permissions.IsAuthenticated & VarelinjePermission],
)
class VarelinjeAPI:
    @route.post("", auth=get_auth_methods(), url_name="varelinje_create")
    def create(self, payload: VarelinjeIn):
        try:
            data = payload.dict()
            vareafgiftssats_afgiftsgruppenummer = data.pop(
                "vareafgiftssats_afgiftsgruppenummer"
            )
            if vareafgiftssats_afgiftsgruppenummer:
                vareafgiftssats_id = self.get_varesats_id_by_kode(
                    data.get("afgiftsanmeldelse_id"),
                    data.get("privatafgiftsanmeldelse_id"),
                    vareafgiftssats_afgiftsgruppenummer,
                )
                if vareafgiftssats_id:
                    data["vareafgiftssats_id"] = vareafgiftssats_id
            item = Varelinje.objects.create(**data)
        except ValidationError as e:  # pragma: no cover
            # Actually tested in test_create__validation_exception,
            # but because of mocking, coverage doesn't pick it up
            return HttpResponseBadRequest(  # pragma: no cover
                json_dump(e.message_dict),
                content_type="application/json",  # pragma: no cover
            )
        return {"id": item.id}

    @staticmethod
    def get_varesats_id_by_kode(
        afgiftsanmeldelse_id: Optional[int],
        privatafgiftsanmeldelse_id: Optional[int],
        kode: int,
    ):
        dato = None
        try:
            if afgiftsanmeldelse_id:
                afgiftsanmeldelse: Afgiftsanmeldelse = Afgiftsanmeldelse.objects.get(
                    id=afgiftsanmeldelse_id
                )
                dato = afgiftsanmeldelse.afgangsdato
            elif privatafgiftsanmeldelse_id:
                privatafgiftsanmeldelse: PrivatAfgiftsanmeldelse = (
                    PrivatAfgiftsanmeldelse.objects.get(id=privatafgiftsanmeldelse_id)
                )
                dato = privatafgiftsanmeldelse.indleveringsdato

            if dato:
                dato = datetime.combine(dato, time.min, tz.get_default_timezone())
                return Vareafgiftssats.objects.get(
                    Q(
                        afgiftsgruppenummer=kode,
                        afgiftstabel__gyldig_fra__lte=dato,
                        afgiftstabel__kladde=False,
                    )
                    & (
                        Q(afgiftstabel__gyldig_til__gte=dato)
                        | Q(afgiftstabel__gyldig_til__isnull=True)
                    )
                ).id
        except (
            Afgiftsanmeldelse.DoesNotExist,
            PrivatAfgiftsanmeldelse.DoesNotExist,
            Vareafgiftssats.DoesNotExist,
        ):
            raise Http404

    @route.get(
        "/{id}",
        response=VarelinjeOut,
        auth=get_auth_methods(),
        url_name="varelinje_get",
    )
    def get(self, id: int):
        item = get_object_or_404(Varelinje, id=id)
        self.check_user(item)
        return item

    @route.get(
        "",
        response=NinjaPaginationResponseSchema[VarelinjeOut],
        auth=get_auth_methods(),
        url_name="varelinje_list",
    )
    @paginate()  # https://eadwincode.github.io/django-ninja-extra/tutorial/pagination/
    def list(
        self,
        filters: VarelinjeFilterSchema = Query(...),
        afgiftsanmeldelse_history_index: Optional[int] = None,
    ):
        # https://django-ninja.rest-framework.com/guides/input/filtering/
        if filters.afgiftsanmeldelse and afgiftsanmeldelse_history_index is not None:
            # Historik-opslag: Find varelinjer for en
            # given version af en afgiftsanmeldelse
            try:
                anmeldelse, as_of = AfgiftsanmeldelseAPI.get_historical(
                    filters.afgiftsanmeldelse, afgiftsanmeldelse_history_index
                )
                # `anmeldelse` er nu et historik-objekt
                qs = anmeldelse.varelinje_set.all()
            except Afgiftsanmeldelse.DoesNotExist:
                qs = Varelinje.objects.none()
        else:
            qs = Varelinje.objects.all()
        qs = qs.filter(
            filters.get_filter_expression()
        )  # Inkluderer evt. filtrering på anmeldelse-id
        return list(qs)

    @route.patch("/{id}", auth=get_auth_methods(), url_name="varelinje_update")
    def update(self, id: int, payload: PartialVarelinjeIn):
        item = get_object_or_404(Varelinje, id=id)
        self.check_user(item)
        for attr, value in payload.dict(exclude_unset=True).items():
            if value is not None:
                setattr(item, attr, value)
        item.save()
        return {"success": True}

    @route.delete("/{id}", auth=get_auth_methods(), url_name="varelinje_delete")
    def delete(self, id: int):
        item = get_object_or_404(Varelinje, id=id)
        self.check_user(item)
        item.delete()
        return {"success": True}

    def filter_user(self, qs: QuerySet) -> QuerySet:
        user = self.context.request.user
        if user.has_perm("anmeldelse.view_all_anmeldelse"):
            return qs
        q = qs.none()
        for a, c in (
            ("afgiftsanmeldelse", "cvr"),
            ("privatafgiftsanmeldelse", "cpr"),
        ):
            try:
                nr = getattr(user.indberetter_data, c)
            except IndberetterProfile.DoesNotExist:
                pass
            else:
                if nr is not None:
                    q |= qs.filter(
                        Q(**{f"{a}__oprettet_af__indberetter_data__{c}": nr})
                        | Q(**{f"{a}__oprettet_på_vegne_af__indberetter_data__{c}": nr})
                    )
                    if c == "cvr":
                        q |= qs.filter(afgiftsanmeldelse__fuldmagtshaver__cvr=nr)
        return q

    def check_user(self, item: Varelinje):
        if not self.filter_user(Varelinje.objects.filter(id=item.id)).exists():
            raise PermissionDenied


class NotatIn(ModelSchema):
    tekst: str
    afgiftsanmeldelse_id: Optional[int] = None
    privatafgiftsanmeldelse_id: Optional[int] = None

    class Config:
        model = Notat
        model_fields = ["tekst"]


class NotatOut(ModelSchema):
    navn: Optional[str] = None

    class Config:
        model = Notat
        model_fields = [
            "id",
            "afgiftsanmeldelse",
            "privatafgiftsanmeldelse",
            "oprettet",
            "tekst",
            "index",
        ]

    @staticmethod
    def resolve_navn(item):
        if item.user:
            return " ".join(filter(None, [item.user.first_name, item.user.last_name]))


class NotatFilterSchema(FilterSchema):
    afgiftsanmeldelse: Optional[int] = None
    privatafgiftsanmeldelse: Optional[int] = None


class NotatPermission(RestPermission):
    appname = "anmeldelse"
    modelname = "notat"


@api_controller(
    "/notat",
    tags=["Notat"],
    permissions=[permissions.IsAuthenticated & NotatPermission],
)
class NotatAPI:
    @route.post("", auth=get_auth_methods(), url_name="notat_create")
    def create_notat(self, payload: NotatIn):
        if payload.afgiftsanmeldelse_id:
            index = (
                AfgiftsanmeldelseAPI.get_historical_count(payload.afgiftsanmeldelse_id)
                - 1
            )
        elif payload.privatafgiftsanmeldelse_id:
            index = (
                PrivatAfgiftsanmeldelseAPI.get_historical_count(
                    payload.privatafgiftsanmeldelse_id
                )
                - 1
            )
        item = Notat.objects.create(
            **payload.dict(),
            user=self.context.request.user,
            index=index,
        )
        return {"id": item.id}

    @route.get(
        "/{id}", response=NotatOut, auth=get_auth_methods(), url_name="notat_get"
    )
    def get_notat(self, id: int):
        item = get_object_or_404(Notat, id=id)
        self.check_user(item)
        return item

    @route.get(
        "",
        response=NinjaPaginationResponseSchema[NotatOut],
        auth=get_auth_methods(),
        url_name="notat_list",
    )
    @paginate()  # https://eadwincode.github.io/django-ninja-extra/tutorial/pagination/
    def list_notater(
        self,
        filters: NotatFilterSchema = Query(...),
        afgiftsanmeldelse_history_index: Optional[int] = None,
    ):
        # https://django-ninja.rest-framework.com/guides/input/filtering/
        if filters.afgiftsanmeldelse and afgiftsanmeldelse_history_index is not None:
            # Historik-opslag: Find notater for en given version af en afgiftsanmeldelse
            try:
                anmeldelse, as_of = AfgiftsanmeldelseAPI.get_historical(
                    filters.afgiftsanmeldelse, afgiftsanmeldelse_history_index
                )
                # # Find notater som de så ud lige før den næste version
                # qs = anmeldelse.notat_set.filter(oprettet__lte=as_of)
                qs = anmeldelse.notat_set.filter(
                    index__lte=afgiftsanmeldelse_history_index
                )
            except Afgiftsanmeldelse.DoesNotExist:
                qs = Notat.objects.none()
        if (
            filters.privatafgiftsanmeldelse
            and afgiftsanmeldelse_history_index is not None
        ):
            # Historik-opslag: Find notater for en given version
            # af en privatafgiftsanmeldelse
            try:
                privatanmeldelse, as_of = PrivatAfgiftsanmeldelseAPI.get_historical(
                    filters.privatafgiftsanmeldelse, afgiftsanmeldelse_history_index
                )
                # # Find notater som de så ud lige før den næste version
                # qs = anmeldelse.notat_set.filter(oprettet__lte=as_of)
                qs = privatanmeldelse.notat_set.filter(
                    index__lte=afgiftsanmeldelse_history_index
                )
            except PrivatAfgiftsanmeldelse.DoesNotExist:
                qs = Notat.objects.none()
        else:
            qs = Notat.objects.all()
        # Inkluderer evt. filtrering på anmeldelse-id
        qs = qs.filter(filters.get_filter_expression())
        return list(qs)

    @route.delete("/{id}", auth=get_auth_methods(), url_name="notat_delete")
    def delete_notat(self, id: int):
        item = get_object_or_404(Notat, id=id)
        self.check_user(item)
        item.delete()
        return {"success": True}

    def filter_user(self, qs: QuerySet) -> QuerySet:
        user = self.context.request.user
        if user.has_perm("anmeldelse.view_all_anmeldelse"):
            return qs
        q = qs.none()
        for a, c in (
            ("afgiftsanmeldelse", "cvr"),
            ("privatafgiftsanmeldelse", "cpr"),
        ):
            try:
                nr = getattr(user.indberetter_data, c)
            except IndberetterProfile.DoesNotExist:
                pass
            else:
                if nr is not None:
                    q |= qs.filter(
                        Q(**{f"{a}__oprettet_af__indberetter_data__{c}": nr})
                        | Q(**{f"{a}__oprettet_på_vegne_af__indberetter_data__{c}": nr})
                    )
                    if c == "cvr":
                        q |= qs.filter(afgiftsanmeldelse__fuldmagtshaver__cvr=nr)
        return q

    def check_user(self, item: Notat):
        if not self.filter_user(Notat.objects.filter(id=item.id)).exists():
            raise PermissionDenied


class PrismeResponseIn(ModelSchema):
    afgiftsanmeldelse_id: Optional[int] = None

    class Config:
        model = PrismeResponse
        model_fields = ["rec_id", "tax_notification_number", "delivery_date"]


class PrismeResponseOut(ModelSchema):
    class Config:
        model = PrismeResponse
        model_fields = [
            "id",
            "afgiftsanmeldelse",
            "rec_id",
            "tax_notification_number",
            "delivery_date",
        ]


class PrismeResponseFilterSchema(FilterSchema):
    afgiftsanmeldelse: Optional[int] = None


class PrismeResponsePermission(RestPermission):
    appname = "anmeldelse"
    modelname = "prismeresponse"


@api_controller(
    "/prismeresponse",
    tags=["PrismeResponse"],
    permissions=[permissions.IsAuthenticated],
)
class PrismeResponseAPI:
    @route.post("", auth=get_auth_methods(), url_name="prismeresponse_create")
    def create_prismeresponse(self, payload: PrismeResponseIn):
        item = PrismeResponse.objects.create(
            **payload.dict(),
        )
        return {"id": item.id}

    @route.get(
        "/{id}",
        response=PrismeResponseOut,
        auth=get_auth_methods(),
        url_name="prismeresponse_get",
    )
    def get_prismeresponse(self, id: int):
        item = get_object_or_404(PrismeResponse, id=id)
        return item

    @route.get(
        "",
        response=NinjaPaginationResponseSchema[PrismeResponseOut],
        auth=get_auth_methods(),
        url_name="prismeresponse_list",
    )
    @paginate()  # https://eadwincode.github.io/django-ninja-extra/tutorial/pagination/
    def list_prismeresponse(
        self,
        filters: PrismeResponseFilterSchema = Query(...),
    ):
        # https://django-ninja.rest-framework.com/guides/input/filtering/
        # Inkluderer evt. filtrering på anmeldelse-id
        qs = PrismeResponse.objects.filter(filters.get_filter_expression()).order_by(
            "delivery_date"
        )
        return list(qs)


class StatistikFilterSchema(FilterSchema):
    anmeldelsestype: Optional[str] = None
    startdato: Annotated[
        Optional[date],
        Field(
            None,
            q=[
                "privatafgiftsanmeldelse__indleveringsdato__gte",
                "afgiftsanmeldelse__dato__gte",
            ],
        ),
    ]
    slutdato: Annotated[
        Optional[date],
        Field(
            None,
            q=[
                "privatafgiftsanmeldelse__indleveringsdato__lte",
                "afgiftsanmeldelse__dato__lte",
            ],
        ),
    ]

    def filter_anmeldelsestype(self, value: str):
        if value == "tf5":
            return Q(privatafgiftsanmeldelse__isnull=False)
        if value == "tf10":
            return Q(afgiftsanmeldelse__isnull=False)


@api_controller(
    "/statistik",
    tags=["Statistik"],
    permissions=[permissions.IsAuthenticated],
)
class StatistikAPI:
    @route.get(
        "",
        auth=get_auth_methods(),
        url_name="statistik_get",
    )
    def get(self, filters: StatistikFilterSchema = Query(...)):
        varelinjer = (
            Varelinje.objects.select_related("vareafgiftssats")
            .filter(filters.get_filter_expression())
            .filter(
                Q(afgiftsanmeldelse__status="afsluttet")
                | Q(privatafgiftsanmeldelse__status="afsluttet")
            )
        )

        stats = list(
            varelinjer.values("vareafgiftssats__afgiftsgruppenummer")
            .annotate(
                sum_afgiftsbeløb=Sum("afgiftsbeløb", default=0),
                sum_mængde=Sum("mængde", default=0),
                sum_antal=Sum("antal", default=0),
                afgiftsgruppenummer=F("vareafgiftssats__afgiftsgruppenummer"),
                vareart_da=F("vareafgiftssats__vareart_da"),
                vareart_kl=F("vareafgiftssats__vareart_kl"),
                enhed=F("vareafgiftssats__enhed"),
            )
            .filter(afgiftsgruppenummer__isnull=False)
        )
        for stat in stats:
            del stat["vareafgiftssats__afgiftsgruppenummer"]

        stats_unused = (
            Vareafgiftssats.objects.filter(
                afgiftstabel__kladde=False,
                afgiftstabel__gyldig_til__isnull=True,
                overordnet__isnull=True,
            )
            .exclude(
                afgiftsgruppenummer__in=(stat["afgiftsgruppenummer"] for stat in stats),
            )
            .values("afgiftsgruppenummer", "vareart_da", "vareart_kl", "enhed")
            .annotate(
                sum_afgiftsbeløb=Value(Decimal("0.00")),
                sum_mængde=Value(Decimal("0.00")),
                sum_antal=Value(0),
            )
        )
        stats_list = sorted(
            list(stats) + list(stats_unused), key=lambda x: x["afgiftsgruppenummer"]
        )
        return {"count": len(stats_list), "items": stats_list}


class ToldkategoriOut(ModelSchema):
    class Config:
        model = Toldkategori
        model_fields = [
            "kategori",
            "navn",
            "kræver_cvr",
        ]


@api_controller(
    "/toldkategori",
    tags=["Toldkategori"],
    permissions=[permissions.IsAuthenticated],
)
class ToldkategoriAPI:
    @route.get(
        "",
        auth=get_auth_methods(),
        url_name="toldkategori_get",
        response=List[ToldkategoriOut],
    )
    def list(self):
        return Toldkategori.objects.all()
