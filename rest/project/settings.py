# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

"""
Django settings for rest project.

Generated by 'django-admin startproject' using Django 4.2.1.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""
import json
import os
from pathlib import Path

from project.util import strtobool

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

DEBUG = bool(strtobool(os.environ.get("DJANGO_DEBUG", "False")))
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")

HOST_DOMAIN = os.environ.get("HOST_DOMAIN", "http://akitsuut.aka.gl")

ALLOWED_HOSTS = json.loads(os.environ.get("ALLOWED_HOSTS", "[]"))


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_extensions",
    "common",
    "aktør",
    "anmeldelse",
    "forsendelse",
    "sats",
    "payment",
    "ninja_extra",
    "ninja_jwt",
    "simple_history",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    # "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
]

ROOT_URLCONF = "project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "project.wsgi.application"


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": os.environ["POSTGRES_DB"],
        "USER": os.environ["POSTGRES_USER"],
        "PASSWORD": os.environ["POSTGRES_PASSWORD"],
        "HOST": os.environ["POSTGRES_HOST"],
    },
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "da-DK"
TIME_ZONE = "America/Godthab"
USE_I18N = True
USE_L10N = True
USE_TZ = True
THOUSAND_SEPARATOR = "."
DECIMAL_SEPARATOR = ","


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = "/static"


# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Uploaded files
MEDIA_ROOT = "/upload/"
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024

GRAPH_MODELS = {
    "app_labels": ["aktør", "anmeldelse", "forsendelse", "sats"],
}

EBOKS = {
    "mock": bool(strtobool(os.environ.get("EBOKS_MOCK", "False"))),
    "content_type_id": "",
}

# If mock is set ignore the rest of the settings.
if not EBOKS["mock"]:
    # Otherwise failfast if a single setting is missing.
    EBOKS.update(
        {
            "client_certificate": os.environ["EBOKS_CLIENT_CERTIFICATE"],
            "client_private_key": os.environ["EBOKS_CLIENT_CERTIFICATE_KEY"],
            "verify": os.environ["EBOKS_VERIFY"],
            "client_id": os.environ["EBOKS_CLIENT_ID"],
            "system_id": os.environ["EBOKS_SYSTEM_ID"],
            "content_type_id": os.environ["EBOKS_CONTENT_TYPE_ID"],
            "host": os.environ["EBOKS_HOST"],
        }
    )

# Payments

PAYMENT_PROVIDER_NETS = "nets"
PAYMENT_PROVIDER_NETS_HOST = os.environ.get(
    "PAYMENT_PROVIDER_NETS_HOST", "https://api.dibspayment.eu"
)
PAYMENT_PROVIDER_NETS_SECRET_KEY = os.environ.get(
    "PAYMENT_PROVIDER_NETS_SECRET_KEY", "secret_key"
)
PAYMENT_PROVIDER_NETS_TERMS_URL = os.environ.get(
    "PAYMENT_PROVIDER_NETS_TERMS_URL", "https://groendland.dk/terms"
)

PAYMENT_PROVIDER_BANK = "bank"

# Logging

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
    },
    "formatters": {
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "gunicorn": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["gunicorn"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["gunicorn"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

log_filename = "/rest.log"
if os.path.isfile(log_filename) and ENVIRONMENT != "development":
    LOGGING["handlers"]["file"] = {
        "class": "logging.FileHandler",  # eller WatchedFileHandler
        "filename": log_filename,
        "formatter": "simple",
    }
    LOGGING["root"] = {
        "handlers": ["gunicorn", "file"],
        "level": "INFO",
    }
    LOGGING["loggers"]["django"]["handlers"].append("file")


TILLAEGSAFGIFT_FAKTOR = 0.5
EKSPEDITIONSGEBYR = 250
