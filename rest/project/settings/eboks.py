# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
import os

from project.util import strtobool

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
