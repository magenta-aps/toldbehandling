# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

import re
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Iterable

from anmeldelse.models import Varelinje
from django.conf import settings


def convert_keys_to_camel_case(data):
    """
    Recursively converts the keys in a dictionary to camel case.

    Args:
        data (dict or list or any): The data to be processed.

    Returns:
        dict or list or any: The processed data with keys converted to camel case.
    """
    if isinstance(data, dict):
        new_data = {}
        for key, value in data.items():
            new_key = "".join(
                word.capitalize() if i > 0 else word
                for i, word in enumerate(key.split("_"))
            )
            new_data[new_key] = convert_keys_to_camel_case(value)
        return new_data
    elif isinstance(data, list):
        return [convert_keys_to_camel_case(item) for item in data]
    else:
        return data


def convert_keys_to_snake_case(data):
    """
    Recursively converts the keys of a dictionary from camel case to snake case.

    Args:
        data (dict or list or any): The data to be processed.

    Returns:
        dict or list or any: The processed data with keys converted to snake case.
    """

    def camel_to_snake(name):
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    if isinstance(data, dict):
        new_data = {}
        for key, value in data.items():
            new_key = camel_to_snake(key)
            new_data[new_key] = convert_keys_to_snake_case(value)
        return new_data
    elif isinstance(data, list):
        return [convert_keys_to_snake_case(item) for item in data]
    else:
        return data


def round_decimal(d: Decimal, rounding: str = ROUND_HALF_EVEN):
    return Decimal(d.quantize(Decimal(".01"), rounding=rounding))


def generate_payment_item_from_varelinje(
    varelinje: Varelinje, currency_multiplier: int = 100
):
    if not varelinje.vareafgiftssats or not varelinje.vareafgiftssats.enhed:
        raise AttributeError(
            (
                "varelinje.vareafgiftssats or varelinje.vareafgiftssats.enhed "
                "is not defined"
            )
        )

    quantity = (
        float(varelinje.mængde)  # type: ignore[arg-type]
        if varelinje.vareafgiftssats.enhed in ["kg", "liter", "l", "sam"]
        else float(varelinje.antal)  # type: ignore[arg-type]
    )

    varelinje_name = varelinje.vareafgiftssats.vareart_da
    unit = varelinje.vareafgiftssats.enhed
    unit_price = float(varelinje.vareafgiftssats.afgiftssats * currency_multiplier)

    tax_rate = 0  # DKK is 25 * 100, but greenland is 0
    tax_amount = unit_price * quantity * tax_rate / 10000
    net_total_amount = unit_price * quantity
    gross_total_amount = net_total_amount + tax_amount

    return {
        "reference": varelinje.vareafgiftssats.afgiftsgruppenummer,
        "name": varelinje_name,
        "quantity": quantity,
        "unit": unit,
        "unit_price": int(unit_price),
        "tax_rate": tax_rate,
        "tax_amount": int(tax_amount),
        "gross_total_amount": int(gross_total_amount),
        "net_total_amount": int(net_total_amount),
    }


def create_nets_payment_item(
    name: str,
    price: float | Decimal,
    unit: str = "ant",
    quantity: int = 1,
    reference="",
    currency_multiplier: int = 100,
):
    unit_price = float(price * currency_multiplier)

    tax_rate = 0  # DKK is 25 * 100, but greenland is 0
    tax_amount = unit_price * quantity * tax_rate / 10000

    net_total_amount = unit_price * quantity
    gross_total_amount = net_total_amount + tax_amount

    return {
        "reference": reference,
        "name": name,
        "quantity": quantity,
        "unit": unit,
        "unit_price": unit_price,
        "tax_rate": tax_rate,
        "tax_amount": tax_amount,
        "gross_total_amount": int(gross_total_amount),
        "net_total_amount": int(net_total_amount),
    }


def get_payment_fees(varelinjer: Iterable[Varelinje], currency_multiplier: int = 100):
    afgiftsbeløb: list[Decimal] = [
        varelinje.afgiftsbeløb
        for varelinje in varelinjer or []
        if varelinje.afgiftsbeløb
        and varelinje.vareafgiftssats
        and varelinje.vareafgiftssats.har_privat_tillægsafgift_alkohol
    ]

    tillaegsafgift = round_decimal(
        Decimal(settings.TILLAEGSAFGIFT_FAKTOR) * Decimal(sum(afgiftsbeløb))
    )

    # OBS: logic copied from "told_common/util.py::round_decimal", but since rest
    # dont have access to told_common tools anymore, its needs to be copied here
    ekspeditionsgebyr = Decimal(
        Decimal(settings.EKSPEDITIONSGEBYR).quantize(
            Decimal(".01"), rounding=ROUND_HALF_EVEN
        )
    )

    return {
        "tillægsafgift": create_nets_payment_item(
            "Tillægsafgift",
            tillaegsafgift,
            reference="tillægsafgift",
            currency_multiplier=currency_multiplier,
        ),
        "ekspeditionsgebyr": create_nets_payment_item(
            "Ekspeditionsgebyr",
            ekspeditionsgebyr,
            reference="ekspeditionsgebyr",
            currency_multiplier=currency_multiplier,
        ),
    }
