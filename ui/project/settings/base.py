# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

import os
import sys
from datetime import timedelta
from pathlib import Path

from told_common.util import strtobool

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
TESTING = len(sys.argv) > 1 and sys.argv[1] == "test"
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

DEBUG = bool(strtobool(os.environ.get("DJANGO_DEBUG", "False")))
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
VERSION = os.environ.get("COMMIT_TAG", "")

ALLOWED_HOSTS = ["*"]

HOST_DOMAIN = os.environ.get("HOST_DOMAIN", "http://akitsuut.aka.gl")

if os.environ.get("HOST_DOMAIN", False):
    CSRF_TRUSTED_ORIGINS = [os.environ["HOST_DOMAIN"]]
CSRF_COOKIE_SECURE = not DEBUG

ROOT_URLCONF = "project.urls"

WSGI_APPLICATION = "project.wsgi.application"

SYSTEM_USER_PASSWORD = os.environ["SYSTEM_USER_PASSWORD"]

MEDIA_ROOT = "/upload"
TF5_ROOT = "/tf5"

DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

APPEND_SLASH = True

REST_DOMAIN = os.environ["REST_DOMAIN"]

NINJA_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(seconds=60),
}

TILLÆGSAFGIFT_FAKTOR = 0.5
EKSPEDITIONSGEBYR = 250

TF5_ENABLED = bool(strtobool(os.environ.get("TF5_ENABLED", "True")))
