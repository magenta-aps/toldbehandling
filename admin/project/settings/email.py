# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

import os

from told_common.util import strtobool

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
DEFAULT_FROM_EMAIL = "noreply@nanoq.gl"
EMAIL_NOTIFICATIONS_ENABLED = bool(
    strtobool(os.environ.get("EMAIL_NOTIFICATIONS_ENABLED", "False"))
)

EMAIL_HOST = os.environ.get("EMAIL_HOST", None)
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 25))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", None)
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", None)
EMAIL_USE_TLS = bool(strtobool(os.environ.get("EMAIL_USE_TLS", "False")))
EMAIL_USE_SSL = bool(strtobool(os.environ.get("EMAIL_USE_SSL", "False")))
