import base64
from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from aktør.api import AfsenderOut, ModtagerOut
from anmeldelse.models import Afgiftsanmeldelse, Varelinje
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db.models import QuerySet
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from forsendelse.api import FragtforsendelseOut, PostforsendelseOut
from ninja import FilterSchema, Query, ModelSchema, Field
from ninja_extra import api_controller, route, permissions
from ninja_extra.exceptions import PermissionDenied
from ninja_extra.pagination import paginate
from ninja_extra.schemas import NinjaPaginationResponseSchema
from ninja_jwt.authentication import JWTAuth
from project.util import RestPermission, json_dump


class AfgiftsanmeldelseIn(ModelSchema):
    afsender_id: int
    modtager_id: int
    postforsendelse_id: int = None
    fragtforsendelse_id: int = None
    leverandørfaktura: str = None  # Base64
    leverandørfaktura_navn: str = None

    class Config:
        model = Afgiftsanmeldelse
        model_fields = [
            "leverandørfaktura_nummer",
            "modtager_betaler",
            "indførselstilladelse",
            "betalt",
        ]


class PartialAfgiftsanmeldelseIn(ModelSchema):
    afsender_id: int = None
    modtager_id: int = None
    postforsendelse_id: int = None
    fragtforsendelse_id: int = None
    leverandørfaktura: str = None  # Base64
    leverandørfaktura_navn: str = None

    class Config:
        model = Afgiftsanmeldelse
        model_fields = [
            "leverandørfaktura_nummer",
            "modtager_betaler",
            "indførselstilladelse",
            "betalt",
            "godkendt",
        ]
        model_fields_optional = "__all__"


class AfgiftsanmeldelseOut(ModelSchema):
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
            "modtager_betaler",
            "indførselstilladelse",
            "afgift_total",
            "betalt",
            "dato",
            "godkendt",
        ]


class AfgiftsanmeldelseFullOut(AfgiftsanmeldelseOut):
    afsender: AfsenderOut
    modtager: ModtagerOut
    fragtforsendelse: Optional[FragtforsendelseOut]
    postforsendelse: Optional[PostforsendelseOut]


class AfgiftsanmeldelseFilterSchema(FilterSchema):
    id: Optional[int]
    afsender: Optional[int]
    modtager: Optional[int]
    fragtforsendelse: Optional[int]
    postforsendelse: Optional[int]
    leverandørfaktura_nummer: Optional[str]
    # leverandørfaktura = models.FileField(
    #     upload_to=afgiftsanmeldelse_upload_to,
    # )
    modtager_betaler: Optional[bool]
    indførselstilladelse: Optional[str]
    betalt: Optional[bool]
    godkendt: Optional[bool]
    godkendt_is_null: Optional[bool] = Field(
        q="godkendt__isnull",
    )
    dato_efter: Optional[date] = Field(q="dato__gte")
    dato_før: Optional[date] = Field(q="dato__lt")
    vareart: Optional[str] = Field(q="varelinje__vareafgiftssats__vareart")
    afsenderbykode_or_forbindelsesnr: Optional[str] = Field(
        q=[
            "postforsendelse__afsenderbykode",
            "fragtforsendelse__forbindelsesnr",
        ]
    )
    postforsendelsesnummer_or_fragtbrevsnummer: Optional[str] = Field(
        q=[
            "postforsendelse__postforsendelsesnummer",
            "fragtforsendelse__fragtbrevsnummer",
        ]
    )


class AfgiftsanmeldelsePermission(RestPermission):
    appname = "anmeldelse"
    modelname = "afgiftsanmeldelse"


@api_controller(
    "/afgiftsanmeldelse",
    tags=["Afgiftsanmeldelse"],
    permissions=[permissions.IsAuthenticated & AfgiftsanmeldelsePermission],
)
class AfgiftsanmeldelseAPI:
    @route.post("", auth=JWTAuth(), url_name="afgiftsanmeldelse_create")
    def create_afgiftsanmeldelse(
        self,
        payload: AfgiftsanmeldelseIn,
    ):
        try:
            data = payload.dict()
            leverandørfaktura = data.pop("leverandørfaktura", None)
            leverandørfaktura_navn = data.pop("leverandørfaktura_navn", None) or (
                str(uuid4()) + ".pdf"
            )
            item = Afgiftsanmeldelse.objects.create(
                **data, oprettet_af=self.context.request.user
            )
            if leverandørfaktura is not None:
                item.leverandørfaktura = ContentFile(
                    base64.b64decode(leverandørfaktura), name=leverandørfaktura_navn
                )
                item.save()
            return {"id": item.id}
        except ValidationError as e:
            return HttpResponseBadRequest(
                json_dump(e.message_dict), content_type="application/json"
            )

    # List afgiftsanmeldelser. Relaterede objekter refereres med deres id
    @route.get(
        "",
        response=NinjaPaginationResponseSchema[AfgiftsanmeldelseOut],
        auth=JWTAuth(),
        url_name="afgiftsanmeldelse_list",
    )
    @paginate()  # https://eadwincode.github.io/django-ninja-extra/tutorial/pagination/
    def list_afgiftsanmeldelser(
        self,
        filters: AfgiftsanmeldelseFilterSchema = Query(...),
        sort: str = None,
        order: str = None,
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
        auth=JWTAuth(),
        url_name="afgiftsanmeldelse_list_full",
    )
    @paginate()  # https://eadwincode.github.io/django-ninja-extra/tutorial/pagination/
    def list_afgiftsanmeldelser_full(
        self,
        filters: AfgiftsanmeldelseFilterSchema = Query(...),
        sort: str = None,
        order: str = None,
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
        auth=JWTAuth(),
        url_name="afgiftsanmeldelse_get",
    )
    def get_afgiftsanmeldelse(self, id: int):
        item = get_object_or_404(Afgiftsanmeldelse, id=id)
        self.check_user(item)
        return item

    @route.get(
        "/{id}/full",
        response=AfgiftsanmeldelseFullOut,
        auth=JWTAuth(),
        url_name="afgiftsanmeldelse_get_full",
    )
    def get_afgiftsanmeldelse_full(self, id: int):
        item = get_object_or_404(Afgiftsanmeldelse, id=id)
        self.check_user(item)
        return item

    @staticmethod
    def map_sort(sort, order):
        if sort is not None:
            if hasattr(Afgiftsanmeldelse, sort):
                if sort in ("afsender", "modtager"):
                    sort += "__navn"
                return ("-" if order == "desc" else "") + sort
        return None

    @route.patch("/{id}", auth=JWTAuth(), url_name="afgiftsanmeldelse_update")
    def update_afgiftsanmeldelse(
        self,
        id: int,
        payload: PartialAfgiftsanmeldelseIn,
    ):
        item = get_object_or_404(Afgiftsanmeldelse, id=id)
        self.check_user(item)
        data = payload.dict()
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

    def filter_user(self, qs: QuerySet) -> QuerySet:
        user = self.context.request.user
        if not user.has_perm("anmeldelse.view_all_anmeldelse"):
            qs = qs.filter(oprettet_af=user)
        return qs

    def check_user(self, item: Afgiftsanmeldelse):
        user = self.context.request.user
        if not (
            user.has_perm("anmeldelse.view_all_anmeldelse") or item.oprettet_af == user
        ):
            raise PermissionDenied


class VarelinjeIn(ModelSchema):
    fakturabeløb: str
    afgiftsanmeldelse_id: int = None
    vareafgiftssats_id: int = None

    class Config:
        model = Varelinje
        model_fields = ["mængde", "antal"]


class PartialVarelinjeIn(ModelSchema):
    afgiftsanmeldelse_id: int = None
    vareafgiftssats_id: int = None

    class Config:
        model = Varelinje
        model_fields = [
            "mængde",
            "antal",
            "fakturabeløb",
        ]
        model_fields_optional = "__all__"


class VarelinjeOut(ModelSchema):
    class Config:
        model = Varelinje
        model_fields = [
            "id",
            "afgiftsanmeldelse",
            "vareafgiftssats",
            "mængde",
            "antal",
            "fakturabeløb",
            "afgiftsbeløb",
        ]


class VarelinjeFilterSchema(FilterSchema):
    afgiftsanmeldelse: Optional[int]
    vareafgiftssats: Optional[int]
    mængde: Optional[int]
    antal: Optional[int]
    fakturabeløb: Optional[Decimal]
    afgiftsbeløb: Optional[Decimal]


class VarelinjePermission(RestPermission):
    appname = "anmeldelse"
    modelname = "varelinje"


@api_controller(
    "/varelinje",
    tags=["Varelinje"],
    permissions=[permissions.IsAuthenticated & VarelinjePermission],
)
class VarelinjeAPI:
    @route.post("", auth=JWTAuth(), url_name="varelinje_create")
    def create_varelinje(self, payload: VarelinjeIn):
        item = Varelinje.objects.create(**payload.dict())
        return {"id": item.id}

    @route.get("/{id}", response=VarelinjeOut, auth=JWTAuth(), url_name="varelinje_get")
    def get_varelinje(self, id: int):
        item = get_object_or_404(Varelinje, id=id)
        self.check_user(item)
        return item

    @route.get(
        "",
        response=NinjaPaginationResponseSchema[VarelinjeOut],
        auth=JWTAuth(),
        url_name="varelinje_list",
    )
    @paginate()  # https://eadwincode.github.io/django-ninja-extra/tutorial/pagination/
    def list_varelinjer(self, filters: VarelinjeFilterSchema = Query(...)):
        # https://django-ninja.rest-framework.com/guides/input/filtering/
        return list(filters.filter(self.filter_user(Varelinje.objects.all())))
        """
        return Varelinje.objects.filter(
            filters.get_filter_expression() & Q("mere filtrering fra vores side")
        )
        """

    @route.patch("/{id}", auth=JWTAuth(), url_name="varelinje_update")
    def update_varelinje(self, id: int, payload: PartialVarelinjeIn):
        item = get_object_or_404(Varelinje, id=id)
        self.check_user(item)
        for attr, value in payload.dict().items():
            if value is not None:
                setattr(item, attr, value)
        item.save()
        return {"success": True}

    @route.delete("/{id}", auth=JWTAuth(), url_name="varelinje_delete")
    def delete_varelinje(self, id):
        item = get_object_or_404(Varelinje, id=id)
        self.check_user(item)
        item.delete()
        return {"success": True}

    def filter_user(self, qs: QuerySet) -> QuerySet:
        user = self.context.request.user
        if not user.has_perm("anmeldelse.view_all_anmeldelse"):
            qs = qs.filter(afgiftsanmeldelse__oprettet_af=user)
        return qs

    def check_user(self, item: Varelinje):
        user = self.context.request.user
        if not (
            user.has_perm("anmeldelse.view_all_anmeldelse")
            or item.afgiftsanmeldelse is None
            or item.afgiftsanmeldelse.oprettet_af == user
        ):
            raise PermissionDenied
