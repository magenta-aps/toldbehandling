from typing import Any, List, Optional

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


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
