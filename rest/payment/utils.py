# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

import re
from decimal import ROUND_HALF_EVEN, Decimal


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
