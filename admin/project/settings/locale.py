# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

import os

from project.settings.base import BASE_DIR

LANGUAGE_CODE = "da-DK"
LANGUAGES = [
    ("da", "Dansk"),
    ("kl", "Kalaallisut"),
]
LOCALE_PATHS = [os.path.join(BASE_DIR, "locale")]
LOCALE_MAP = {"da": "da-DK", "kl": "kl-GL"}

TIME_ZONE = "America/Godthab"
USE_I18N = True
USE_L10N = True
USE_TZ = True
USE_THOUSAND_SEPARATOR = True
THOUSAND_SEPARATOR = "."
DECIMAL_SEPARATOR = ","
