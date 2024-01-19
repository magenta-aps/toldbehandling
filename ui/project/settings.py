# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

"""
Django settings for ui project.

Generated by 'django-admin startproject' using Django 4.2.1.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""

import os
from datetime import timedelta
from pathlib import Path

import django.conf.locale
from told_common.util import strtobool

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

DEBUG = bool(strtobool(os.environ.get("DJANGO_DEBUG", "False")))
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")

ALLOWED_HOSTS = ["*"]

HOST_DOMAIN = os.environ.get("HOST_DOMAIN", "http://akitsuut.aka.gl")

if os.environ.get("HOST_DOMAIN", False):
    CSRF_TRUSTED_ORIGINS = [os.environ["HOST_DOMAIN"]]

# Application definition

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "told_common",
    "ui",
    "django_mitid_auth",
    "django_bootstrap_icons",
    "mitid_test",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django_mitid_auth.middleware.LoginManager",
    "django.middleware.locale.LocaleMiddleware",
    # "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_session_timeout.middleware.SessionTimeoutMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
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
            "libraries": {
                "common_tags": "told_common.templatetags.common_tags",
            },
        },
    },
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
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
    "loggers": {
        "weasyprint": {
            "handlers": ["gunicorn"],
            "level": "ERROR",
            "propagate": False,
        },
        "fontTools": {
            "handlers": ["gunicorn"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}

log_filename = "/log/ui.log"
if os.path.isfile(log_filename):
    LOGGING["handlers"]["file"] = {
        "filters": ["require_debug_false"],
        "class": "logging.FileHandler",  # eller WatchedFileHandler
        "filename": log_filename,
        "formatter": "simple",
    }
    LOGGING["root"] = {
        "handlers": ["gunicorn", "file"],
        "level": "INFO",
    }

WSGI_APPLICATION = "project.wsgi.application"

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

SYSTEM_USER_PASSWORD = os.environ["SYSTEM_USER_PASSWORD"]

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "da"
LANGUAGES = [
    ("da", "Dansk"),
    ("kl", "Kalaallisut"),
]
LANGUAGE_COOKIE_NAME = "Sullissivik.Portal.Lang"
LANGUAGE_COOKIE_DOMAIN = os.environ["LANGUAGE_COOKIE_DOMAIN"]
LOCALE_PATHS = [os.path.join(BASE_DIR, "locale")]
# LOCALE_MAP = {"da": "da-DK", "kl": "kl-GL"}

# Add custom languages not provided by Django
django.conf.locale.LANG_INFO["kl"] = {
    "bidi": False,
    "code": "kl",
    "name": "Greenlandic",
    "name_local": "Kalaallisut",
}

TIME_ZONE = "America/Godthab"
USE_I18N = True
USE_L10N = True
USE_TZ = True
USE_THOUSAND_SEPARATOR = True
DECIMAL_SEPARATOR = ","
THOUSAND_SEPARATOR = "."


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = "/static"
MEDIA_ROOT = "/upload"
TF5_ROOT = "/tf5"

DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

APPEND_SLASH = True

REST_DOMAIN = os.environ["REST_DOMAIN"]

NINJA_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(seconds=20),
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "default_cache",
    },
}

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}


# Når SAML-IdP'en POSTer til os, skal vi modtage vores session-cookie fra browseren
# https://docs.djangoproject.com/en/4.2/ref/settings/#session-cookie-samesite
SESSION_COOKIE_SAMESITE = "None"
SESSION_COOKIE_SECURE = True


TILLÆGSAFGIFT_FAKTOR = 0.5
EKSPEDITIONSGEBYR = 250

from .login_settings import *  # noqa

PAYMENT_PROVIDER_NETS_CHECKOUT_KEY = os.environ.get(
    "PAYMENT_PROVIDER_NETS_CHECKOUT_KEY", "checkout_key"
)

TF5_ENABLED = bool(strtobool(os.environ.get("TF5_ENABLED", "True")))
