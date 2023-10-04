# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from typing import Optional

from aktør.models import Afsender, Modtager
from django.core.exceptions import ValidationError
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from ninja import FilterSchema, Query, Field, ModelSchema
from ninja_extra import api_controller, route
from ninja_extra import permissions
from ninja_extra.pagination import paginate
from ninja_extra.schemas import NinjaPaginationResponseSchema
from ninja_jwt.authentication import JWTAuth
from project.util import RestPermission, json_dump


class AfsenderIn(ModelSchema):
    class Config:
        model = Afsender
        model_fields = [
            "navn",
            "adresse",
            "postnummer",
            "by",
            "postbox",
            "telefon",
            "cvr",
        ]
        model_fields_optional = [
            "postbox",
            "cvr",
        ]


class PartialAfsenderIn(ModelSchema):
    class Config:
        model = Modtager
        model_fields = [
            "navn",
            "adresse",
            "postnummer",
            "by",
            "postbox",
            "telefon",
            "cvr",
        ]
        model_fields_optional = "__all__"


class AfsenderOut(ModelSchema):
    class Config:
        model = Afsender
        model_fields = [
            "id",
            "navn",
            "adresse",
            "postnummer",
            "by",
            "postbox",
            "telefon",
            "cvr",
        ]


class AfsenderFilterSchema(FilterSchema):
    navn: Optional[str] = Field(q="navn__icontains")
    adresse: Optional[str] = Field(q="adresse__icontains")
    postnummer: Optional[int]
    by: Optional[str] = Field(q="by__icontains")
    postbox: Optional[str]
    telefon: Optional[str]
    cvr: Optional[int]


class AfsenderPermission(RestPermission):
    appname = "aktør"
    modelname = "afsender"


@api_controller(
    "/afsender",
    tags=["Afsender"],
    permissions=[permissions.IsAuthenticated & AfsenderPermission],
)
class AfsenderAPI:
    @route.post("", auth=JWTAuth(), url_name="afsender_create")
    def create_afsender(self, payload: AfsenderIn):
        try:
            item = Afsender.objects.create(**payload.dict())
            return {"id": item.id}
        except ValidationError as e:
            return HttpResponseBadRequest(
                json_dump(e.message_dict), content_type="application/json"
            )

    @route.get("/{id}", response=AfsenderOut, auth=JWTAuth(), url_name="afsender_get")
    def get_afsender(self, id: int):
        return get_object_or_404(Afsender, id=id)

    @route.get(
        "",
        response=NinjaPaginationResponseSchema[AfsenderOut],
        auth=JWTAuth(),
        url_name="afsender_list",
    )
    @paginate()  # https://eadwincode.github.io/django-ninja-extra/tutorial/pagination/
    def list_afsendere(self, filters: AfsenderFilterSchema = Query(...)):
        # https://django-ninja.rest-framework.com/guides/input/filtering/
        return list(filters.filter(Afsender.objects.all()))
        """
        return list(Afsender.objects.filter(
            filters.get_filter_expression() & Q("mere filtrering fra vores side")
        ))
        """

    @route.patch("/{id}", auth=JWTAuth(), url_name="afsender_update")
    def update_afsender(
        self,
        id: int,
        payload: PartialAfsenderIn,
    ):
        item = get_object_or_404(Afsender, id=id)
        data = payload.dict()
        for attr, value in data.items():
            if value is not None:
                setattr(item, attr, value)
        item.save()
        return {"success": True}


class ModtagerIn(ModelSchema):
    class Config:
        model = Modtager
        model_fields = [
            "navn",
            "adresse",
            "postnummer",
            "by",
            "postbox",
            "telefon",
            "cvr",
            "kreditordning",
            "indførselstilladelse",
        ]
        model_fields_optional = [
            "postbox",
            "cvr",
        ]


class PartialModtagerIn(ModelSchema):
    class Config:
        model = Modtager
        model_fields = [
            "navn",
            "adresse",
            "postnummer",
            "by",
            "postbox",
            "telefon",
            "cvr",
            "kreditordning",
            "indførselstilladelse",
        ]
        model_fields_optional = "__all__"


class ModtagerOut(ModelSchema):
    class Config:
        model = Modtager
        model_fields = [
            "id",
            "navn",
            "adresse",
            "postnummer",
            "by",
            "postbox",
            "telefon",
            "cvr",
            "kreditordning",
            "indførselstilladelse",
        ]


class ModtagerFilterSchema(FilterSchema):
    navn: Optional[str] = Field(q="navn__icontains")
    adresse: Optional[str] = Field(q="adresse__icontains")
    postnummer: Optional[int]
    by: Optional[str] = Field(q="by__icontains")
    postbox: Optional[str]
    telefon: Optional[str]
    cvr: Optional[int]
    kreditordning: Optional[bool]
    indførselstilladelse: Optional[int]


class ModtagerPermission(RestPermission):
    appname = "aktør"
    modelname = "modtager"


@api_controller(
    "/modtager",
    tags=["Modtager"],
    permissions=[permissions.IsAuthenticated & ModtagerPermission],
)
class ModtagerAPI:
    @route.post("", auth=JWTAuth(), url_name="modtager_create")
    def create_modtager(self, payload: ModtagerIn):
        try:
            item = Modtager.objects.create(**payload.dict())
            return {"id": item.id}
        except ValidationError as e:
            return HttpResponseBadRequest(
                json_dump(e.message_dict), content_type="application/json"
            )

    @route.get("/{id}", response=ModtagerOut, auth=JWTAuth(), url_name="modtager_get")
    def get_modtager(self, id: int):
        return get_object_or_404(Modtager, id=id)

    @route.get(
        "",
        response=NinjaPaginationResponseSchema[ModtagerOut],
        auth=JWTAuth(),
        url_name="modtager_list",
    )
    @paginate()
    def list_modtagere(self, filters: ModtagerFilterSchema = Query(...)):
        # https://django-ninja.rest-framework.com/guides/input/filtering/
        return list(filters.filter(Modtager.objects.all()))
        """
        return list(Modtager.objects.filter(
            filters.get_filter_expression() & Q("mere filtrering fra vores side")
        ))
        """

    @route.patch("/{id}", auth=JWTAuth(), url_name="modtager_update")
    def update_modtager(
        self,
        id: int,
        payload: PartialModtagerIn,
    ):
        item = get_object_or_404(Modtager, id=id)
        data = payload.dict()
        for attr, value in data.items():
            if value is not None:
                setattr(item, attr, value)
        item.save()
        return {"success": True}
