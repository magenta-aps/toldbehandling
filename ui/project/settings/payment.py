# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
import os

PAYMENT_PROVIDER_NETS_CHECKOUT_KEY = os.environ.get(
    "PAYMENT_PROVIDER_NETS_CHECKOUT_KEY", "checkout_key"
)

PAYMENT_PROVIDER_NETS_JS_SDK_URL = os.environ.get(
    "PAYMENT_PROVIDER_NETS_JS_SDK_URL",
    "https://checkout.dibspayment.eu/v1/checkout.js?v=1",
)
