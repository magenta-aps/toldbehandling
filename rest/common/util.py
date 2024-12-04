from datetime import timedelta

from common.models import Postnummer
from django.utils.datetime_safe import date


def dato_næste_måned_start(dato: date) -> date:
    return date(
        dato.year + (1 if dato.month == 12 else 0),
        1 if dato.month == 12 else dato.month + 1,
        1,
    )


def dato_måned_slut(dato: date) -> date:
    return dato_næste_måned_start(dato) - timedelta(days=1)


def get_postnummer(postnummer: int, by: str):
    objs = Postnummer.objects.filter(postnummer=postnummer)
    if not objs:
        raise Postnummer.DoesNotExist("Postnummer kunne ikke findes")

    by = by.lower().strip()
    for obj in objs:
        if by == obj.navn.lower().strip():
            return obj

    if objs.count() == 1:
        return obj
    else:
        raise Postnummer.DoesNotExist(f"Postnummer med bynavn '{by}' kunne ikke findes")
