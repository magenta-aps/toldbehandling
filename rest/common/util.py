from datetime import timedelta

from django.utils.datetime_safe import date


def dato_næste_måned_start(dato: date) -> date:
    return date(
        dato.year + (1 if dato.month == 12 else 0),
        1 if dato.month == 12 else dato.month + 1,
        1,
    )


def dato_måned_slut(dato: date) -> date:
    return dato_næste_måned_start(dato) - timedelta(days=1)
