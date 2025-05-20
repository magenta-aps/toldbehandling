# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
import os

PAYMENT_PROVIDER_NETS = "nets"
PAYMENT_PROVIDER_NETS_HOST = os.environ.get(
    "PAYMENT_PROVIDER_NETS_HOST", "https://api.dibspayment.eu"
)
PAYMENT_PROVIDER_NETS_SECRET_KEY = os.environ.get(
    "PAYMENT_PROVIDER_NETS_SECRET_KEY", "secret_key"
)
PAYMENT_PROVIDER_NETS_TERMS_URL = os.environ.get(
    "PAYMENT_PROVIDER_NETS_TERMS_URL",
    (
        "https://www.sullissivik.gl/Emner/B_SKAT/Afgifter/"
        "Privat-indfoersel-af-oel-vin-og-spiritus-til-Groenland_Som-fragt"
    ),
)

PAYMENT_PROVIDER_BANK = "bank"

PAYMENT_PAYMENT_STATUS_CREATED = "created"
PAYMENT_PAYMENT_STATUS_RESERVED = "reserved"
PAYMENT_PAYMENT_STATUS_DECLINED = "declined"
PAYMENT_PAYMENT_STATUS_PAID = "paid"
