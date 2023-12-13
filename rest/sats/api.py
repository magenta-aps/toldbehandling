# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
from datetime import date
from decimal import Decimal
from typing import Optional

from common.api import get_auth_methods
from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import FilterSchema, ModelSchema, Query
from ninja_extra import api_controller, permissions, route
from ninja_extra.pagination import paginate
from ninja_extra.schemas import NinjaPaginationResponseSchema
from project.util import RestPermission
from sats.models import Afgiftstabel, Vareafgiftssats


class AfgiftstabelIn(ModelSchema):
    class Config:
        model = Afgiftstabel
        model_fields = ["gyldig_fra", "kladde"]


class PartialAfgiftstabelIn(ModelSchema):
    class Config:
        model = Afgiftstabel
        model_fields = ["gyldig_fra", "kladde"]
        model_fields_optional = "__all__"


class AfgiftstabelOut(ModelSchema):
    class Config:
        model = Afgiftstabel
        model_fields = ["id", "gyldig_fra", "gyldig_til", "kladde"]


class AfgiftstabelFilterSchema(FilterSchema):
    gyldig_fra__gt: Optional[str]
    gyldig_fra__lt: Optional[str]
    gyldig_fra__gte: Optional[str]
    gyldig_fra__lte: Optional[str]
    gyldig_til__gt: Optional[str]
    gyldig_til__lt: Optional[str]
    gyldig_til__gte: Optional[str]
    gyldig_til__lte: Optional[str]
    kladde: Optional[bool]

    def filter_gyldig_fra__lt(self, value: str) -> Q:
        if value is None:
            return Q()
        return Q(gyldig_fra__lt=date.fromisoformat(value)) | Q(gyldig_fra__isnull=True)

    def filter_gyldig_fra__lte(self, value: str) -> Q:
        if value is None:
            return Q()
        return Q(gyldig_fra__lte=date.fromisoformat(value)) | Q(gyldig_fra__isnull=True)

    def filter_gyldig_til__gt(self, value: str) -> Q:
        if value is None:
            return Q()
        return Q(gyldig_til__gt=date.fromisoformat(value)) | Q(gyldig_til__isnull=True)

    def filter_gyldig_til__gte(self, value: str) -> Q:
        if value is None:
            return Q()
        return Q(gyldig_til__gte=date.fromisoformat(value)) | Q(gyldig_til__isnull=True)


class AfgiftstabelPermission(RestPermission):
    appname = "sats"
    modelname = "afgiftstabel"


@api_controller(
    "/afgiftstabel",
    tags=["Afgiftstabel"],
    permissions=[permissions.IsAuthenticated & AfgiftstabelPermission],
)
class AfgiftstabelAPI:
    @route.post("", auth=get_auth_methods(), url_name="afgiftstabel_create")
    def create_afgiftstabel(self, payload: AfgiftstabelIn):
        item = Afgiftstabel.objects.create(**payload.dict())
        return {"id": item.id}

    @route.get(
        "/{id}",
        response=AfgiftstabelOut,
        auth=get_auth_methods(),
        url_name="afgiftstabel_get",
    )
    def get_afgiftstabel(self, id: int):
        return get_object_or_404(Afgiftstabel, id=id)

    @route.get(
        "",
        response=NinjaPaginationResponseSchema[AfgiftstabelOut],
        auth=get_auth_methods(),
        url_name="afgiftstabel_list",
    )
    @paginate()  # https://eadwincode.github.io/django-ninja-extra/tutorial/pagination/
    def list_afgiftstabeller(
        self,
        filters: AfgiftstabelFilterSchema = Query(...),
        sort: str = None,
        order: str = None,
    ):
        # https://django-ninja.rest-framework.com/guides/input/filtering/
        qs = filters.filter(Afgiftstabel.objects.all())
        order_by = self.map_sort(sort, order)
        if order_by:
            qs = qs.order_by(order_by, "id")
        return list(qs)
        """
        return list(Afgiftstabel.objects.filter(
            filters.get_filter_expression() & Q("mere filtrering fra vores side")
        ))
        """

    @staticmethod
    def map_sort(sort, order):
        if sort is not None:
            if hasattr(Afgiftstabel, sort):
                return ("-" if order == "desc" else "") + sort
        return None

    @route.patch("/{id}", auth=get_auth_methods(), url_name="afgiftstabel_update")
    def update_afgiftstabel(self, id: int, payload: PartialAfgiftstabelIn):
        item = get_object_or_404(Afgiftstabel, id=id)
        for attr, value in payload.dict().items():
            setattr(item, attr, value)
        item.save()
        return {"success": True}

    @route.delete("/{id}", auth=get_auth_methods(), url_name="afgiftstabel_delete")
    def delete_afgiftstabel(self, id: int):
        item = get_object_or_404(Afgiftstabel, id=id)
        item.delete()
        return {"success": True}


class VareafgiftssatsIn(ModelSchema):
    afgiftstabel_id: int
    overordnet_id: int = None

    class Config:
        model = Vareafgiftssats
        model_fields = [
            "vareart_da",
            "vareart_kl",
            "afgiftsgruppenummer",
            "enhed",
            "afgiftssats",
            "kræver_indførselstilladelse",
            "minimumsbeløb",
            "segment_nedre",
            "segment_øvre",
            "synlig_privat",
        ]
        model_fields_optional = [
            "kræver_indførselstilladelse",
            "minimumsbeløb",
            "segment_nedre",
            "segment_øvre",
            "synlig_privat",
        ]


class PartialVareafgiftssatsIn(ModelSchema):
    afgiftstabel_id: int = None
    overordnet_id: Optional[int] = None

    class Config:
        model = Vareafgiftssats
        model_fields = [
            "vareart_da",
            "vareart_kl",
            "afgiftsgruppenummer",
            "enhed",
            "afgiftssats",
            "kræver_indførselstilladelse",
            "minimumsbeløb",
            "segment_nedre",
            "segment_øvre",
            "synlig_privat",
        ]
        model_fields_optional = "__all__"


class VareafgiftssatsOut(ModelSchema):
    class Config:
        model = Vareafgiftssats
        model_fields = [
            "id",
            "afgiftstabel",
            "vareart_da",
            "vareart_kl",
            "afgiftsgruppenummer",
            "enhed",
            "afgiftssats",
            "kræver_indførselstilladelse",
            "minimumsbeløb",
            "overordnet",
            "segment_nedre",
            "segment_øvre",
            "synlig_privat",
        ]


class VareafgiftssatsFilterSchema(FilterSchema):
    afgiftstabel: Optional[int]
    vareart_da: Optional[str]
    vareart_kl: Optional[str]
    afgiftsgruppenummer: Optional[int]
    enhed: Optional[str]
    afgiftssats: Optional[Decimal]
    kræver_indførselstilladelse: Optional[bool]
    minimumsbeløb: Optional[Decimal]
    overordnet: Optional[int]
    segment_nedre: Optional[Decimal]
    segment_øvre: Optional[Decimal]
    synlig_privat: Optional[bool]


class VareafgiftssatsPermission(RestPermission):
    appname = "sats"
    modelname = "vareafgiftssats"


@api_controller(
    "/vareafgiftssats",
    tags=["Vareafgiftssats"],
    permissions=[permissions.IsAuthenticated & VareafgiftssatsPermission],
)
class VareafgiftssatsAPI:
    @route.post("", auth=get_auth_methods(), url_name="vareafgiftssats_create")
    def create_vareafgiftssats(self, payload: VareafgiftssatsIn):
        item = Vareafgiftssats.objects.create(**payload.dict())
        return {"id": item.id}

    @route.get(
        "/{id}",
        response=VareafgiftssatsOut,
        auth=get_auth_methods(),
        url_name="vareafgiftssats_get",
    )
    def get_vareafgiftssats(self, id: int):
        return get_object_or_404(Vareafgiftssats, id=id)

    @route.get(
        "",
        response=NinjaPaginationResponseSchema[VareafgiftssatsOut],
        auth=get_auth_methods(),
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

    @route.patch("/{id}", auth=get_auth_methods(), url_name="vareafgiftssats_update")
    def update_vareafgiftssats(self, id: int, payload: PartialVareafgiftssatsIn):
        item = get_object_or_404(Vareafgiftssats, id=id)
        for attr, value in payload.dict().items():
            setattr(item, attr, value)
        item.save()
        return {"success": True}
