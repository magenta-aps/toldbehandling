import base64
from typing import Optional
from uuid import uuid4

from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from forsendelse.models import Postforsendelse, Fragtforsendelse
from ninja import ModelSchema, FilterSchema, Query
from ninja_extra import api_controller, route, permissions
from ninja_extra.pagination import paginate
from ninja_extra.schemas import NinjaPaginationResponseSchema
from ninja_jwt.authentication import JWTAuth
from project.util import RestPermission


# Django-ninja har endnu ikke understøttelse for PATCH med filer i multipart/form-data
# Se https://github.com/vitalik/django-ninja/pull/397
# Derfor gør vi det så alle skrivninger (POST og PATCH) kommer til at foregå med application/json
# og fildata liggende som Base64-strenge i json-værdier
# Hvis det kommer på plads, og vi ønsker at bruge multipart/form-data, skal In-skemaerne ændres til
# ikke at have filfeltet med, og metoderne der håndterer post og patch skal modtage filen som et File(...) argument:
#
# @foo_router.post("/", auth=JWTAuth())
# def create_foo(self, payload: FooIn, filfeltnavn: ninja.File(...)):
#     item = Foo.objects.create(**payload.dict(), filfeltnavn=filfeltnavn)
#


class PostforsendelseIn(ModelSchema):
    class Config:
        model = Postforsendelse
        model_fields = ["forsendelsestype", "postforsendelsesnummer"]


class PartialPostforsendelseIn(ModelSchema):
    class Config:
        model = Postforsendelse
        model_fields = ["forsendelsestype", "postforsendelsesnummer"]
        model_fields_optional = "__all__"


class PostforsendelseOut(ModelSchema):
    class Config:
        model = Postforsendelse
        model_fields = ["id", "forsendelsestype", "postforsendelsesnummer"]


class PostforsendelseFilterSchema(FilterSchema):
    forsendelsestype: Optional[str]
    postforsendelsesnummer: Optional[str]


class PostforsendelsePermission(RestPermission):
    appname = "forsendelse"
    modelname = "postforsendelse"


@api_controller(
    "/postforsendelse",
    tags=["Postforsendelse"],
    permissions=[permissions.IsAuthenticated & PostforsendelsePermission],
)
class PostforsendelseAPI:
    @route.post("/", auth=JWTAuth(), url_name="postforsendelse_create")
    def create_postforsendelse(self, payload: PostforsendelseIn):
        item = Postforsendelse.objects.create(**payload.dict())
        return {"id": item.id}

    @route.get(
        "/{id}",
        response=PostforsendelseOut,
        auth=JWTAuth(),
        url_name="postforsendelse_get",
    )
    def get_postforsendelse(self, id: int):
        return get_object_or_404(Postforsendelse, id=id)

    @route.get(
        "/",
        response=NinjaPaginationResponseSchema[PostforsendelseOut],
        auth=JWTAuth(),
        url_name="postforsendelse_list",
    )
    @paginate()  # https://eadwincode.github.io/django-ninja-extra/tutorial/pagination/
    def list_postforsendelser(self, filters: PostforsendelseFilterSchema = Query(...)):
        # https://django-ninja.rest-framework.com/guides/input/filtering/
        return list(filters.filter(Postforsendelse.objects.all()))
        """
        return list(Post.objects.filter(
            filters.get_filter_expression() & Q("mere filtrering fra vores side")
        ))
        """

    @route.patch("/{id}", auth=JWTAuth(), url_name="postforsendelse_update")
    def update_postforsendelse(self, id: int, payload: PartialPostforsendelseIn):
        item = get_object_or_404(Postforsendelse, id=id)
        for attr, value in payload.dict().items():
            setattr(item, attr, value)
        item.save()
        return {"success": True}


class FragtforsendelseIn(ModelSchema):
    fragtbrev: str = None  # Base64

    class Config:
        model = Fragtforsendelse
        model_fields = ["forsendelsestype", "fragtbrevsnummer"]


class PartialFragtforsendelseIn(ModelSchema):
    fragtbrev: str = None  # Base64

    class Config:
        model = Fragtforsendelse
        model_fields = ["forsendelsestype", "fragtbrevsnummer"]
        model_fields_optional = "__all__"


class FragtforsendelseOut(ModelSchema):
    class Config:
        model = Fragtforsendelse
        model_fields = ["id", "forsendelsestype", "fragtbrevsnummer", "fragtbrev"]


class FragtforsendelseFilterSchema(FilterSchema):
    forsendelsestype: Optional[str]
    fragtbrevsnummer: Optional[str]


class FragtforsendelsePermission(RestPermission):
    appname = "forsendelse"
    modelname = "fragtforsendelse"


@api_controller(
    "/fragtforsendelse",
    tags=["Fragtforsendelse"],
    permissions=[permissions.IsAuthenticated & FragtforsendelsePermission],
)
class FragtforsendelseAPI:
    @route.post("/", auth=JWTAuth(), url_name="fragtforsendelse_create")
    def create_fragtforsendelse(
        self,
        payload: FragtforsendelseIn,
    ):
        data = payload.dict()
        fragtbrev = data.pop("fragtbrev", None)
        item = Fragtforsendelse.objects.create(**data)
        if fragtbrev is not None:
            item.fragtbrev = ContentFile(
                base64.b64decode(fragtbrev), name=str(uuid4()) + ".pdf"
            )
            item.save()
        return {"id": item.id}

    @route.get(
        "/{id}",
        response=FragtforsendelseOut,
        auth=JWTAuth(),
        url_name="fragtforsendelse_get",
    )
    def get_fragtforsendelse(self, id: int):
        return get_object_or_404(Fragtforsendelse, id=id)

    @route.get(
        "/",
        response=NinjaPaginationResponseSchema[FragtforsendelseOut],
        auth=JWTAuth(),
        url_name="fragtforsendelse_list",
    )
    @paginate()  # https://eadwincode.github.io/django-ninja-extra/tutorial/pagination/
    def list_fragtforsendelser(
        self, filters: FragtforsendelseFilterSchema = Query(...)
    ):
        # https://django-ninja.rest-framework.com/guides/input/filtering/
        return list(filters.filter(Fragtforsendelse.objects.all()))
        """
        return list(Fragt.objects.filter(
            filters.get_filter_expression() & Q("mere filtrering fra vores side")
        ))
        """

    @route.patch("/{id}", auth=JWTAuth(), url_name="fragtforsendelse_update")
    def update_fragtforsendelse(self, id: int, payload: PartialFragtforsendelseIn):
        item = get_object_or_404(Fragtforsendelse, id=id)
        data = payload.dict()
        fragtbrev = data.pop("fragtbrev", None)
        for attr, value in data.items():
            setattr(item, attr, value)
        if fragtbrev is not None:
            item.fragtbrev = ContentFile(
                base64.b64decode(fragtbrev), name=str(uuid4()) + ".pdf"
            )
        item.save()
        return {"success": True}
