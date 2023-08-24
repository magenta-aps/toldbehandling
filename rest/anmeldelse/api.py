import base64
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from anmeldelse.models import Afgiftsanmeldelse, Varelinje
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from ninja import FilterSchema, Query, ModelSchema
from ninja_extra import api_controller, route, permissions
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
    postforsendelse: int = None
    fragtforsendelse: int = None
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
            item = Afgiftsanmeldelse.objects.create(**data)
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

    @route.get(
        "/{id}",
        response=AfgiftsanmeldelseOut,
        auth=JWTAuth(),
        url_name="afgiftsanmeldelse_get",
    )
    def get_afgiftsanmeldelse(self, id: int):
        return get_object_or_404(Afgiftsanmeldelse, id=id)

    @route.get(
        "",
        response=NinjaPaginationResponseSchema[AfgiftsanmeldelseOut],
        auth=JWTAuth(),
        url_name="afgiftsanmeldelse_list",
    )
    @paginate()  # https://eadwincode.github.io/django-ninja-extra/tutorial/pagination/
    def list_afgiftsanmeldelser(
        self, filters: AfgiftsanmeldelseFilterSchema = Query(...)
    ):
        # https://django-ninja.rest-framework.com/guides/input/filtering/
        return list(filters.filter(Afgiftsanmeldelse.objects.all()))
        """
        return list(Afgiftsanmeldelse.objects.filter(
            filters.get_filter_expression() & Q("mere filtrering fra vores side")
        ))
        """

    @route.patch("/{id}", auth=JWTAuth(), url_name="afgiftsanmeldelse_update")
    def update_afgiftsanmeldelse(
        self,
        id: int,
        payload: PartialAfgiftsanmeldelseIn,
    ):
        item = get_object_or_404(Afgiftsanmeldelse, id=id)
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


class VarelinjeIn(ModelSchema):
    fakturabeløb: str
    afgiftsanmeldelse_id: int = None
    afgiftssats_id: int = None

    class Config:
        model = Varelinje
        model_fields = ["kvantum"]


class PartialVarelinjeIn(ModelSchema):
    class Config:
        model = Varelinje
        model_fields = ["afgiftsanmeldelse", "afgiftssats", "kvantum", "fakturabeløb"]
        model_fields_optional = "__all__"


class VarelinjeOut(ModelSchema):
    class Config:
        model = Varelinje
        model_fields = [
            "id",
            "afgiftsanmeldelse",
            "afgiftssats",
            "kvantum",
            "fakturabeløb",
            "afgiftsbeløb",
        ]


class VarelinjeFilterSchema(FilterSchema):
    afgiftsanmeldelse: Optional[int]
    afgiftssats: Optional[int]
    kvantum: Optional[int]
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
        return get_object_or_404(Varelinje, id=id)

    @route.get(
        "",
        response=NinjaPaginationResponseSchema[VarelinjeOut],
        auth=JWTAuth(),
        url_name="varelinje_list",
    )
    @paginate()  # https://eadwincode.github.io/django-ninja-extra/tutorial/pagination/
    def list_varelinjer(self, filters: VarelinjeFilterSchema = Query(...)):
        # https://django-ninja.rest-framework.com/guides/input/filtering/
        return list(filters.filter(Varelinje.objects.all()))
        """
        return Varelinje.objects.filter(
            filters.get_filter_expression() & Q("mere filtrering fra vores side")
        )
        """

    @route.patch("/{id}", auth=JWTAuth(), url_name="varelinje_update")
    def update_varelinje(self, id: int, payload: PartialVarelinjeIn):
        item = get_object_or_404(Varelinje, id=id)
        for attr, value in payload.dict().items():
            if value is not None:
                setattr(item, attr, value)
        item.save()
        return {"success": True}
