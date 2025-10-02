# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
# mypy: disable-error-code="call-arg, attr-defined"
import base64
import logging
from typing import Annotated, Optional
from uuid import uuid4

from common.api import get_auth_methods
from common.models import IndberetterProfile
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db.models import QuerySet
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from forsendelse.models import Fragtforsendelse, Postforsendelse
from ninja import Field, FilterSchema, ModelSchema, Query
from ninja_extra import api_controller, permissions, route
from ninja_extra.exceptions import PermissionDenied
from ninja_extra.pagination import paginate
from ninja_extra.schemas import NinjaPaginationResponseSchema
from project.util import RestPermission, json_dump

log = logging.getLogger(__name__)
# Django-ninja har endnu ikke understøttelse for PATCH med filer i multipart/form-data
# Se https://github.com/vitalik/django-ninja/pull/397
# Derfor laver vi alle skrivninger (POST og PATCH)  med application/json
# og fildata liggende som Base64-strenge i json-værdier.
#
# Hvis det kommer på plads, og vi ønsker at bruge multipart/form-data, skal
# In-skemaerne ændres til ikke at have filfeltet med, og metoderne der
# håndterer post og patch skal modtage filen som et File(...) argument:
#
# @foo_router.post("/", auth=get_auth_methods())
# def create_foo(self, payload: FooIn, filfeltnavn: ninja.File(...)):
#     item = Foo.objects.create(**payload.dict(), filfeltnavn=filfeltnavn)
#


class PostforsendelseIn(ModelSchema):
    class Config:
        model = Postforsendelse
        model_fields = [
            "forsendelsestype",
            "postforsendelsesnummer",
            "afsenderbykode",
            "afgangsdato",
            "kladde",
        ]


class PartialPostforsendelseIn(ModelSchema):
    class Config:
        model = Postforsendelse
        model_fields = [
            "forsendelsestype",
            "postforsendelsesnummer",
            "afsenderbykode",
            "afgangsdato",
            "kladde",
        ]
        model_fields_optional = "__all__"


class PostforsendelseOut(ModelSchema):
    class Config:
        model = Postforsendelse
        model_fields = [
            "id",
            "forsendelsestype",
            "postforsendelsesnummer",
            "afsenderbykode",
            "afgangsdato",
            "kladde",
        ]


class PostforsendelseFilterSchema(FilterSchema):
    forsendelsestype: Optional[str] = None
    postforsendelsesnummer: Optional[str] = None
    afsenderbykode: Optional[str] = None
    afgangsdato: Optional[str] = None
    afgangsdato__før: Annotated[Optional[str], Field(None, q="afgangsdato__lt")]
    afgangsdato__efter: Annotated[Optional[str], Field(None, q="afgangsdato__gte")]


class PostforsendelsePermission(RestPermission):
    appname = "forsendelse"
    modelname = "postforsendelse"


@api_controller(
    "/postforsendelse",
    tags=["Postforsendelse"],
    permissions=[permissions.IsAuthenticated & PostforsendelsePermission],
)
class PostforsendelseAPI:
    @route.post("", auth=get_auth_methods(), url_name="postforsendelse_create")
    def create_postforsendelse(self, payload: PostforsendelseIn):
        try:
            item = Postforsendelse.objects.create(
                **payload.dict(), oprettet_af=self.context.request.user
            )
        except ValidationError as e:
            return HttpResponseBadRequest(
                json_dump(e.message_dict), content_type="application/json"
            )
        return {"id": item.id}

    @route.get(
        "/{id}",
        response=PostforsendelseOut,
        auth=get_auth_methods(),
        url_name="postforsendelse_get",
    )
    def get_postforsendelse(self, id: int):
        item = get_object_or_404(Postforsendelse, id=id)
        self.check_user(item)
        return item

    @route.get(
        "",
        response=NinjaPaginationResponseSchema[PostforsendelseOut],
        auth=get_auth_methods(),
        url_name="postforsendelse_list",
    )
    @paginate()  # https://eadwincode.github.io/django-ninja-extra/tutorial/pagination/
    def list_postforsendelser(self, filters: PostforsendelseFilterSchema = Query(...)):
        # https://django-ninja.rest-framework.com/guides/input/filtering/
        return list(filters.filter(self.filter_user(Postforsendelse.objects.all())))
        """
        return list(Post.objects.filter(
            filters.get_filter_expression() & Q("mere filtrering fra vores side")
        ))
        """

    @route.patch("/{id}", auth=get_auth_methods(), url_name="postforsendelse_update")
    def update_postforsendelse(self, id: int, payload: PartialPostforsendelseIn):
        item = get_object_or_404(Postforsendelse, id=id)
        self.check_user(item)
        for attr, value in payload.dict(exclude_unset=True).items():
            if value is not None:
                setattr(item, attr, value)
        item.save()
        return {"success": True}

    @route.delete("/{id}", auth=get_auth_methods(), url_name="postforsendelse_delete")
    def delete_postforsendelse(self, id: int):
        item = get_object_or_404(Postforsendelse, id=id)
        self.check_user(item)
        item.delete()
        return {"success": True}

    def filter_user(self, qs: QuerySet) -> QuerySet:
        user = self.context.request.user
        if user.has_perm("forsendelse.view_all_postforsendelser"):
            return qs
        q = qs.none()
        try:
            cvr = getattr(user.indberetter_data, "cvr")
        except IndberetterProfile.DoesNotExist:
            pass
        else:
            if cvr is not None:
                q |= qs.filter(
                    afgiftsanmeldelse__oprettet_af__indberetter_data__cvr=cvr
                )
                q |= qs.filter(
                    afgiftsanmeldelse__oprettet_på_vegne_af__indberetter_data__cvr=cvr
                )
                q |= qs.filter(afgiftsanmeldelse__fuldmagtshaver__cvr=cvr)
        return q

    def check_user(self, item: Postforsendelse):
        if not self.filter_user(Postforsendelse.objects.filter(id=item.id)).exists():
            raise PermissionDenied


class FragtforsendelseIn(ModelSchema):
    fragtbrev: Optional[str] = None  # Base64
    fragtbrev_navn: Optional[str] = None

    class Config:
        model = Fragtforsendelse
        model_fields = [
            "forsendelsestype",
            "fragtbrevsnummer",
            "forbindelsesnr",
            "afgangsdato",
            "kladde",
        ]
        model_fields_optional = "__all__"


class PartialFragtforsendelseIn(ModelSchema):
    fragtbrev: Optional[str] = None  # Base64
    fragtbrev_navn: Optional[str] = None

    class Config:
        model = Fragtforsendelse
        model_fields = [
            "forsendelsestype",
            "fragtbrevsnummer",
            "forbindelsesnr",
            "afgangsdato",
            "kladde",
        ]
        model_fields_optional = "__all__"


class FragtforsendelseOut(ModelSchema):
    class Config:
        model = Fragtforsendelse
        model_fields = [
            "id",
            "forsendelsestype",
            "fragtbrevsnummer",
            "fragtbrev",
            "forbindelsesnr",
            "afgangsdato",
            "kladde",
        ]


class FragtforsendelseFilterSchema(FilterSchema):
    forsendelsestype: Optional[str] = None
    fragtbrevsnummer: Optional[str] = None
    forbindelsesnr: Optional[str] = None
    afgangsdato: Optional[str] = None
    afgangsdato__før: Annotated[Optional[str], Field(None, q="afgangsdato__lt")]
    afgangsdato__efter: Annotated[Optional[str], Field(None, q="afgangsdato__gte")]
    kladde: Optional[bool] = None


class FragtforsendelsePermission(RestPermission):
    appname = "forsendelse"
    modelname = "fragtforsendelse"


@api_controller(
    "/fragtforsendelse",
    tags=["Fragtforsendelse"],
    permissions=[permissions.IsAuthenticated & FragtforsendelsePermission],
)
class FragtforsendelseAPI:
    @route.post("", auth=get_auth_methods(), url_name="fragtforsendelse_create")
    def create_fragtforsendelse(
        self,
        payload: FragtforsendelseIn,
    ):
        data = payload.dict()
        fragtbrev = data.pop("fragtbrev", None)
        fragtbrev_navn = data.pop("fragtbrev_navn", None) or (str(uuid4()) + ".pdf")
        try:
            item = Fragtforsendelse.objects.create(
                **data, oprettet_af=self.context.request.user
            )
        except ValidationError as e:
            return HttpResponseBadRequest(
                json_dump(e.message_dict), content_type="application/json"
            )
        if fragtbrev is not None:
            item.fragtbrev = ContentFile(
                base64.b64decode(fragtbrev), name=fragtbrev_navn
            )
            log.info(
                "Rest API opretter Fragtforsendelse %d med fragtbrev %s (%d bytes)",
                item.id,
                fragtbrev_navn,
                item.fragtbrev.size,
            )
            item.save()
        else:
            log.info(
                "Rest API opretter Fragtforsendelse %d uden at sætte fragtbrev", item.id
            )
        return {"id": item.id}

    @route.get(
        "/{id}",
        response=FragtforsendelseOut,
        auth=get_auth_methods(),
        url_name="fragtforsendelse_get",
    )
    def get_fragtforsendelse(self, id: int):
        item = get_object_or_404(Fragtforsendelse, id=id)
        self.check_user(item)
        return item

    @route.get(
        "",
        response=NinjaPaginationResponseSchema[FragtforsendelseOut],
        auth=get_auth_methods(),
        url_name="fragtforsendelse_list",
    )
    @paginate()  # https://eadwincode.github.io/django-ninja-extra/tutorial/pagination/
    def list_fragtforsendelser(
        self, filters: FragtforsendelseFilterSchema = Query(...)
    ):
        # https://django-ninja.rest-framework.com/guides/input/filtering/
        return list(filters.filter(self.filter_user(Fragtforsendelse.objects.all())))
        """
        return list(Fragt.objects.filter(
            filters.get_filter_expression() & Q("mere filtrering fra vores side")
        ))
        """

    @route.patch("/{id}", auth=get_auth_methods(), url_name="fragtforsendelse_update")
    def update_fragtforsendelse(self, id: int, payload: PartialFragtforsendelseIn):
        item = get_object_or_404(Fragtforsendelse, id=id)
        self.check_user(item)
        data = payload.dict(exclude_unset=True)
        fragtbrev = data.pop("fragtbrev", None)
        fragtbrev_navn = data.pop("fragtbrev_navn", None) or (str(uuid4()) + ".pdf")
        for attr, value in data.items():
            if value is not None:
                setattr(item, attr, value)
        if fragtbrev is not None:
            item.fragtbrev = ContentFile(
                base64.b64decode(fragtbrev), name=fragtbrev_navn
            )
            log.info(
                "Rest API opdaterer Fragtforsendelse %d med fragtbrev %s (%d bytes)",
                item.id,
                fragtbrev_navn,
                item.fragtbrev.size,
            )
        else:
            log.info(
                "Rest API opdaterer Fragtforsendelse %d uden at sætte fragtbrev",
                item.id,
            )
        item.save()
        return {"success": True}

    @route.delete("/{id}", auth=get_auth_methods(), url_name="fragtforsendelse_delete")
    def delete_fragtforsendelse(self, id: int):
        item = get_object_or_404(Fragtforsendelse, id=id)
        self.check_user(item)
        log.info("Rest API sletter Fragtforsendelse %d", id)
        item.delete()
        return {"success": True}

    def filter_user(self, qs: QuerySet) -> QuerySet:
        user = self.context.request.user
        if user.has_perm("forsendelse.view_all_fragtforsendelser"):
            return qs
        q = qs.none()
        try:
            cvr = getattr(user.indberetter_data, "cvr")
        except IndberetterProfile.DoesNotExist:
            pass
        else:
            if cvr is not None:
                q |= qs.filter(
                    afgiftsanmeldelse__oprettet_af__indberetter_data__cvr=cvr
                )
                q |= qs.filter(
                    afgiftsanmeldelse__oprettet_på_vegne_af__indberetter_data__cvr=cvr
                )
                q |= qs.filter(afgiftsanmeldelse__fuldmagtshaver__cvr=cvr)
        return q

    def check_user(self, item: Fragtforsendelse):
        if not self.filter_user(Fragtforsendelse.objects.filter(id=item.id)).exists():
            raise PermissionDenied
