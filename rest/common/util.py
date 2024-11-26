from datetime import timedelta
from typing import Any, List, Optional

from common.models import Postnummer
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.datetime_safe import date


def dato_næste_måned_start(dato: date) -> date:
    return date(
        dato.year + (1 if dato.month == 12 else 0),
        1 if dato.month == 12 else dato.month + 1,
        1,
    )


def dato_måned_slut(dato: date) -> date:
    return dato_næste_måned_start(dato) - timedelta(days=1)


def send_email(
    subject: str,
    template: str,
    to: List[str],
    context: Optional[dict[str, Any]] = None,
    from_email: Optional[str] = None,
    bcc: Optional[List[str]] = None,
    cc: Optional[List[str]] = None,
    html_template: Optional[str] = None,
):
    msg = EmailMultiAlternatives(
        subject,
        render_to_string(template, context=context),
        from_email=from_email,
        to=to,
        bcc=bcc,
        cc=cc,
    )

    # Configure HTML template if specified
    if html_template:
        msg.attach_alternative(
            render_to_string(html_template, context=context), "text/html"
        )

    msg.send()


def get_postnummer(postnummer: int, by: str):
    objs = Postnummer.objects.filter(postnummer=postnummer)
    if not objs:
        raise Postnummer.DoesNotExist("Postnummer kunne ikke findes")

    by = by.lower().strip()
    for obj in objs:
        if by == obj.navn.lower().strip():
            return obj
    return obj if objs.count() == 1 else None
