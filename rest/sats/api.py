from decimal import Decimal
from typing import Optional

from django.shortcuts import get_object_or_404
from ninja import ModelSchema, FilterSchema, Query
from ninja_extra import api_controller, route, permissions
from ninja_extra.pagination import paginate
from ninja_extra.schemas import NinjaPaginationResponseSchema
from ninja_jwt.authentication import JWTAuth
from project.util import RestPermission
from sats.models import Afgiftstabel, Vareafgiftssats


class AfgiftstabelIn(ModelSchema):
    class Config:
        model = Afgiftstabel
        model_fields = ["gyldig_til", "kladde"]


class PartialAfgiftstabelIn(ModelSchema):
    class Config:
        model = Afgiftstabel
        model_fields = ["gyldig_til", "kladde"]
        model_fields_optional = "__all__"


class AfgiftstabelOut(ModelSchema):
    class Config:
        model = Afgiftstabel
        model_fields = ["id", "gyldig_fra", "gyldig_til", "kladde"]


class AfgiftstabelFilterSchema(FilterSchema):
    gyldig_fra: Optional[str]
    gyldig_til: Optional[str]
    kladde: Optional[bool]


class AfgiftstabelPermission(RestPermission):
    appname = "sats"
    modelname = "afgiftstabel"


@api_controller(
    "/afgiftstabel",
    tags=["Afgiftstabel"],
    permissions=[permissions.IsAuthenticated & AfgiftstabelPermission],
)
class AfgiftstabelAPI:
    @route.post("", auth=JWTAuth(), url_name="afgiftstabel_create")
    def create_afgiftstabel(self, payload: AfgiftstabelIn):
        item = Afgiftstabel.objects.create(**payload.dict())
        return {"id": item.id}

    @route.get(
        "/{id}", response=AfgiftstabelOut, auth=JWTAuth(), url_name="afgiftstabel_get"
    )
    def get_afgiftstabel(self, id: int):
        return get_object_or_404(Afgiftstabel, id=id)

    @route.get(
        "",
        response=NinjaPaginationResponseSchema[AfgiftstabelOut],
        auth=JWTAuth(),
        url_name="afgiftstabel_list",
    )
    @paginate()  # https://eadwincode.github.io/django-ninja-extra/tutorial/pagination/
    def list_afgiftstabeller(self, filters: AfgiftstabelFilterSchema = Query(...)):
        # https://django-ninja.rest-framework.com/guides/input/filtering/
        return list(filters.filter(Afgiftstabel.objects.all()))
        """
        return list(Afgiftstabel.objects.filter(
            filters.get_filter_expression() & Q("mere filtrering fra vores side")
        ))
        """

    @route.patch("/{id}", auth=JWTAuth(), url_name="afgiftstabel_update")
    def update_afgiftstabel(self, id: int, payload: PartialAfgiftstabelIn):
        item = get_object_or_404(Afgiftstabel, id=id)
        for attr, value in payload.dict().items():
            setattr(item, attr, value)
        item.save()
        return {"success": True}


class VareafgiftssatsIn(ModelSchema):
    afgiftstabel_id: int

    class Config:
        model = Vareafgiftssats
        model_fields = [
            "vareart",
            "afgiftsgruppenummer",
            "enhed",
            "afgiftssats",
        ]


class PartialVareafgiftssatsIn(ModelSchema):
    afgiftstabel_id: int = None

    class Config:
        model = Vareafgiftssats
        model_fields = [
            "vareart",
            "afgiftsgruppenummer",
            "enhed",
            "afgiftssats",
            "kræver_indførselstilladelse",
            "minimumsbeløb",
            "overordnet",
            "segment_nedre",
            "segment_øvre",
        ]
        model_fields_optional = "__all__"


class VareafgiftssatsOut(ModelSchema):
    class Config:
        model = Vareafgiftssats
        model_fields = [
            "id",
            "afgiftstabel",
            "vareart",
            "afgiftsgruppenummer",
            "enhed",
            "afgiftssats",
            "kræver_indførselstilladelse",
            "minimumsbeløb",
            "overordnet",
            "segment_nedre",
            "segment_øvre",
        ]


class VareafgiftssatsFilterSchema(FilterSchema):
    afgiftstabel: Optional[int]
    vareart: Optional[str]
    afgiftsgruppenummer: Optional[int]
    enhed: Optional[str]
    afgiftssats: Optional[Decimal]
    kræver_indførselstilladelse: Optional[bool]
    minimumsbeløb: Optional[Decimal]
    overordnet: Optional[int]
    segment_nedre: Optional[Decimal]
    segment_øvre: Optional[Decimal]


class VareafgiftssatsPermission(RestPermission):
    appname = "sats"
    modelname = "vareafgiftssats"


@api_controller(
    "/vareafgiftssats",
    tags=["Vareafgiftssats"],
    permissions=[permissions.IsAuthenticated & VareafgiftssatsPermission],
)
class VareafgiftssatsAPI:
    @route.post("", auth=JWTAuth(), url_name="vareafgiftssats_create")
    def create_vareafgiftssats(self, payload: VareafgiftssatsIn):
        item = Vareafgiftssats.objects.create(**payload.dict())
        return {"id": item.id}

    @route.get(
        "/{id}",
        response=VareafgiftssatsOut,
        auth=JWTAuth(),
        url_name="vareafgiftssats_get",
    )
    def get_vareafgiftssats(self, id: int):
        return get_object_or_404(Vareafgiftssats, id=id)

    @route.get(
        "",
        response=NinjaPaginationResponseSchema[VareafgiftssatsOut],
        auth=JWTAuth(),
        url_name="vareafgiftssats_list",
    )
    @paginate()  # https://eadwincode.github.io/django-ninja-extra/tutorial/pagination/
    def list_vareafgiftssatser(self, filters: VareafgiftssatsFilterSchema = Query(...)):
        # https://django-ninja.rest-framework.com/guides/input/filtering/
        return list(filters.filter(Vareafgiftssats.objects.all()))
        """
        return list(Vareafgiftssats.objects.filter(
            filters.get_filter_expression() & Q("mere filtrering fra vores side")
        ))
        """

    @route.patch("/{id}", auth=JWTAuth(), url_name="vareafgiftssats_update")
    def update_vareafgiftssats(self, id: int, payload: PartialVareafgiftssatsIn):
        item = get_object_or_404(Vareafgiftssats, id=id)
        for attr, value in payload.dict().items():
            setattr(item, attr, value)
        item.save()
        return {"success": True}