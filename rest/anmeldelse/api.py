# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
# mypy: disable-error-code="call-arg, attr-defined"

import base64
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple
from uuid import uuid4

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
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db.models import Q, QuerySet, Sum
from django.db.models.expressions import F, Value
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from forsendelse.api import FragtforsendelseOut, PostforsendelseOut
from ninja import Field, FilterSchema, ModelSchema, Query
from ninja_extra import api_controller, permissions, route
from ninja_extra.exceptions import PermissionDenied
from ninja_extra.pagination import paginate
from ninja_extra.schemas import NinjaPaginationResponseSchema
from payment.models import Payment
from project.util import RestPermission, json_dump
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

    class Config:
        model = Afgiftsanmeldelse
        model_fields = [
            "leverandørfaktura_nummer",
            "betales_af",
            "indførselstilladelse",
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
    toldkategori: Optional[str] = None
    kladde: Optional[bool] = False
    fuldmagtshaver_id: Optional[int] = None
    status: Optional[str] = None

    class Config:
        model = Afgiftsanmeldelse
        model_fields = [
            "leverandørfaktura_nummer",
            "betales_af",
            "indførselstilladelse",
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
            "indførselstilladelse",
            "afgift_total",
            "betalt",
            "dato",
            "status",
            "oprettet_af",
            "oprettet_på_vegne_af",
            "toldkategori",
            "fuldmagtshaver",
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
    id: Optional[List[int]] = Field(q="id__in")
    afsender: Optional[int]
    modtager: Optional[int]
    fragtforsendelse: Optional[int]
    postforsendelse: Optional[int]
    leverandørfaktura_nummer: Optional[str] = Field(
        q="leverandørfaktura_nummer__iexact"
    )
    # leverandørfaktura = models.FileField(
    #     upload_to=afgiftsanmeldelse_upload_to,
    # )
    betales_af: Optional[str]
    indførselstilladelse: Optional[str]
    betalt: Optional[bool]
    status: Optional[str]
    fuldmagtshaver: Optional[int]
    fuldmagtshaver_isnull: Optional[bool] = Field(q="fuldmagtshaver__isnull")
    dato_efter: Optional[date] = Field(q="dato__gte")
    dato_før: Optional[date] = Field(q="dato__lt")
    vareart: Optional[str] = Field(q="varelinje__vareafgiftssats__vareart_da")
    afsenderbykode_or_forbindelsesnr: Optional[str] = Field(
        q=[
            "postforsendelse__afsenderbykode__iexact",
            "fragtforsendelse__forbindelsesnr__iexact",
        ]
    )
    postforsendelsesnummer_or_fragtbrevsnummer: Optional[str] = Field(
        q=[
            "postforsendelse__postforsendelsesnummer__iexact",
            "fragtforsendelse__fragtbrevsnummer__iexact",
        ]
    )
    notat: Optional[str] = Field(q="notat__tekst__icontains")


class AfgiftsanmeldelsePermission(RestPermission):
    appname = "anmeldelse"
    modelname = "afgiftsanmeldelse"


@api_controller(
    "/afgiftsanmeldelse",
    tags=["Afgiftsanmeldelse"],
    permissions=[permissions.IsAuthenticated & AfgiftsanmeldelsePermission],
)
class AfgiftsanmeldelseAPI:
    allowed_statuses_delete = ["ny", "kladde"]

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
        data = payload.dict(exclude_unset=True)
        if payload.status in ("godkendt", "afvist", "afsluttet"):
            if not self.check_perm("anmeldelse.approve_reject_anmeldelse"):
                raise PermissionDenied
        leverandørfaktura = data.pop("leverandørfaktura", None)
        leverandørfaktura_navn = data.pop("leverandørfaktura_navn", None) or (
            str(uuid4()) + ".pdf"
        )
        kladde = data.pop("kladde", False)

        if not kladde and item.status == "kladde":
            data["status"] = "ny"
        for attr, value in data.items():
            if value is not None:
                setattr(item, attr, value)
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
        item.save()
        return {"success": True}

    @route.delete(
        "/{id}",
        auth=get_auth_methods(),
        url_name="afgiftsanmeldelse_delete",
    )
    def delete(self, id: int):
        """Delete afgiftsanmeldelse. Only allowed if status is 'ny' or 'kladde'.

        NOTE: Normally DELETE returns 204, but since our existing code returns 200
        + a dict with a success key, we do the same here.
        """
        item = get_object_or_404(Afgiftsanmeldelse, id=id)
        self.check_user(item)

        if item.status not in self.allowed_statuses_delete:
            raise PermissionDenied(
                "You are not allowed to delete 'afgiftsanmeldelser' "
                f"with status: {item.status}"
            )

        item.delete()
        return {"success": True}

    def check_perm(self, permission):
        return self.context.request.user.has_perm(permission)

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
        )

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
            as_of = datetime.now()
        anmeldelse = anmeldelse.history.as_of(as_of)
        return anmeldelse, as_of

    @staticmethod
    def get_historical_count(id: int):
        anmeldelse = Afgiftsanmeldelse.objects.get(id=id)
        return anmeldelse.history.count()


class PrivatAfgiftsanmeldelseIn(ModelSchema):
    leverandørfaktura: Optional[str] = None  # Base64
    leverandørfaktura_navn: Optional[str] = None

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
    leverandørfaktura: Optional[str] = None  # Base64
    leverandørfaktura_navn: Optional[str] = None

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
    id: Optional[List[int]] = Field(q="id__in")
    cpr: Optional[int]
    navn: Optional[str] = Field(q="navn__icontains")
    adresse: Optional[str] = Field(q="adresse__icontains")
    postnummer: Optional[int]
    by: Optional[str] = Field(q="by__icontains")
    telefon: Optional[str] = Field(q="telefon__icontains")
    leverandørfaktura_nummer: Optional[str] = Field(
        q="leverandørfaktura_nummer__icontains"
    )
    indførselstilladelse: Optional[str] = Field(q="indførselstilladelse__icontains")
    indleveringsdato_efter: Optional[date] = Field(q="indleveringsdato__gte")
    indleveringsdato_før: Optional[date] = Field(q="indleveringsdato__lt")
    oprettet_efter: Optional[date] = Field(q="oprettet__gte")
    oprettet_før: Optional[date] = Field(q="oprettet__lt")
    vareart: Optional[str] = Field(q="varelinje__vareafgiftssats__vareart_da")
    status: Optional[str]
    anonym: Optional[bool]
    notat: Optional[str] = Field(q="notat__tekst__icontains")


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
    )
    def get_latest(self, cpr: int):
        anmeldelse = (
            PrivatAfgiftsanmeldelse.objects.filter(cpr=cpr)
            .order_by("-oprettet")
            .first()
        )
        if anmeldelse:
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
            as_of = datetime.now()
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
    afgiftsanmeldelse: Optional[int]
    privatafgiftsanmeldelse: Optional[int]
    vareafgiftssats: Optional[int]
    mængde: Optional[Decimal]
    antal: Optional[int]
    fakturabeløb: Optional[Decimal]
    afgiftsbeløb: Optional[Decimal]
    kladde: Optional[bool]


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
            if "vareafgiftssats_afgiftsgruppenummer" in data:
                vareafgiftssats_afgiftsgruppenummer = data.pop(
                    "vareafgiftssats_afgiftsgruppenummer"
                )
                vareafgiftssats_id = self.get_varesats_id_by_kode(
                    data.get("afgiftsanmeldelse_id"),
                    data.get("privatafgiftsanmeldelse_id"),
                    vareafgiftssats_afgiftsgruppenummer,
                )
                if vareafgiftssats_id:
                    data["vareafgiftssats_id"] = vareafgiftssats_id
            item = Varelinje.objects.create(**data)
        except ValidationError as e:
            return HttpResponseBadRequest(
                json_dump(e.message_dict), content_type="application/json"
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
                afgiftsanmeldelse: PrivatAfgiftsanmeldelse = (
                    PrivatAfgiftsanmeldelse.objects.get(id=privatafgiftsanmeldelse_id)
                )
                dato = afgiftsanmeldelse.indleveringsdato
            if dato:
                return Vareafgiftssats.objects.get(
                    afgiftsgruppenummer=kode,
                    afgiftstabel__gyldig_fra__lte=dato,
                    afgiftstabel__gyldig_til__gte=dato,
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
    afgiftsanmeldelse: Optional[int]
    privatafgiftsanmeldelse: Optional[int]


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
            except Afgiftsanmeldelse.DoesNotExist:
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
    afgiftsanmeldelse: Optional[int]


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
    startdato: Optional[date] = Field(
        None,
        q=[
            "privatafgiftsanmeldelse__indleveringsdato__gte",
            "afgiftsanmeldelse__dato__gte",
        ],
    )
    slutdato: Optional[date] = Field(
        None,
        q=[
            "privatafgiftsanmeldelse__indleveringsdato__lte",
            "afgiftsanmeldelse__dato__lte",
        ],
    )

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
