# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
from project.settings.base import DEBUG, HOST_DOMAIN

CSP_DEFAULT_SRC = (
    "'self'",
    "localhost:8000" if DEBUG else HOST_DOMAIN,
    # origins used by NETs Payment JS SDK
    "test.checkout.dibspayment.eu" if DEBUG else "checkout.dibspayment.eu",
    "applepay.cdn-apple.com",
)
CSP_SCRIPT_SRC_ATTR = (
    "'self'",
    "localhost:8000" if DEBUG else HOST_DOMAIN,
    "cdnjs.cloudflare.com",
)
CSP_STYLE_SRC_ATTR = ("'self'",)
CSP_IMG_SRC = ("'self'", "data:")
