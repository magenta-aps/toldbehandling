# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
from csp.constants import NONCE, SELF
from project.settings.base import DEBUG, HOST_DOMAIN

CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": [
            SELF,
            "localhost:8000" if DEBUG else HOST_DOMAIN,
            "cdnjs.cloudflare.com",
        ],
        "script-src": [
            SELF,
            "localhost:8000" if DEBUG else HOST_DOMAIN,
            "cdnjs.cloudflare.com",
            NONCE,
        ],
        "img-src": [SELF, "data:"],
    },
}
