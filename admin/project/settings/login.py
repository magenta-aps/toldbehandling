# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
import os

from told_common.util import strtobool

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

LOGIN_URL = "/admin/login"
LOGIN_REDIRECT_URL = "/admin"
SYSTEM_USER_PASSWORD = os.environ["SYSTEM_USER_PASSWORD"]
REQUIRE_2FA = bool(strtobool(os.environ.get("REQUIRE_2FA", "False")))

SESSION_COOKIE_PATH = "/admin"
SESSION_COOKIE_SAMESITE = "Strict"
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_NAME = "admin_sessionid"
SESSION_COOKIE_AGE = 604800  # One week, in seconds
