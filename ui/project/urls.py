from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import path, include

urlpatterns = [
    path("", include("ui.urls")),
]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
