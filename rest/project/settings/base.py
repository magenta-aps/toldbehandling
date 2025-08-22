# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

import json
import os
import sys
from pathlib import Path

from project.util import strtobool

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
TESTING = len(sys.argv) > 1 and sys.argv[1] == "test"
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

DEBUG = bool(strtobool(os.environ.get("DJANGO_DEBUG", "False")))
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")

HOST_DOMAIN = os.environ.get("HOST_DOMAIN", "http://akitsuut.aka.gl")

ALLOWED_HOSTS = json.loads(os.environ.get("ALLOWED_HOSTS", "[]"))
CSRF_TRUSTED_ORIGINS = json.loads(os.environ.get("CSRF_ORIGINS", "[]"))

ROOT_URLCONF = "project.urls"

WSGI_APPLICATION = "project.wsgi.application"

GRAPH_MODELS = {
    "app_labels": ["aktør", "anmeldelse", "forsendelse", "sats"],
}

TILLAEGSAFGIFT_FAKTOR = 0.5
EKSPEDITIONSGEBYR = 250

PROMETHEUS_PUSHGATEWAY_HOST = os.environ.get(
    "PROMETHEUS_PUSHGATEWAY", "pushgateway:9091"
)

LOGIN_URL = "two_factor:login"
LOGIN_REDIRECT_URL = "admin:index"
