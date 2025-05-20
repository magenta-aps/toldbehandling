# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

import os

from told_common.util import opt_int

PRISME = {
    "wsdl_file": os.environ.get("PRISME_WSDL", ""),
    "auth": {
        "basic": {
            "username": os.environ.get("PRISME_USERNAME", ""),
            "domain": os.environ.get("PRISME_DOMAIN", ""),
            "password": os.environ.get("PRISME_PASSWORD", ""),
        }
    },
    "area": os.environ.get("PRISME_AREA", ""),
}
if "PRISME_SOCKS_PROXY" in os.environ:
    PRISME["proxy"] = {"socks": os.environ["PRISME_SOCKS_PROXY"]}
PRISME_MOCK_HTTP_ERROR = opt_int(os.environ.get("PRISME_MOCK_HTTP_ERROR") or None)
