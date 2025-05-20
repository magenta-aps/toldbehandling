# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
import os

import django.conf.locale
from project.settings.base import BASE_DIR

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
