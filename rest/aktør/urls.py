from django.urls import path
from rest.api import api


urlpatterns = [path("", api.urls)]
