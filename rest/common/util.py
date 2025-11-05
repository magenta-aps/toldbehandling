from datetime import date, timedelta
from typing import Any

from common.models import Postnummer


def coerce_num_to_str(value: Any) -> Any:
    if isinstance(value, (int, float)):
        return str(value)
    return value


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
    if objs.count() == 1:
        return objs.first()
    if by is not None:
        obj = objs.filter(navn__iexact=by.lower().strip()).first()
        if obj is not None:
            return obj
    raise Postnummer.DoesNotExist(f"Postnummer med bynavn '{by}' kunne ikke findes")
