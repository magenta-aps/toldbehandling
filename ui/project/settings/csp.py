# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
from csp.constants import SELF
from project.settings.base import DEBUG, HOST_DOMAIN

CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": [
            SELF,
            "localhost:8000" if DEBUG else HOST_DOMAIN,
            # origins used by NETs Payment JS SDK
            "test.checkout.dibspayment.eu" if DEBUG else "checkout.dibspayment.eu",
            "applepay.cdn-apple.com",
        ],
        "script-src": [
            SELF,
            "localhost:8000" if DEBUG else HOST_DOMAIN,
            "cdnjs.cloudflare.com",
        ],
        "img-src": [SELF, "data:"],
    }
}
