# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
import re

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import CheckConstraint, Q
from django.utils.datetime_safe import date
from django.utils.translation import gettext_lazy as _


class Forsendelse(models.Model):
    class Meta:
        abstract = True
        constraints = [
            CheckConstraint(
                check=Q(afgangsdato__isnull=False) | Q(kladde=True),
                name="aktuel_har_afgangsdato",
            )
        ]

    class Forsendelsestype(models.TextChoices):
        SKIB = "S", _("Skib")
        FLY = "F", _("Fly")

    forsendelsestype = models.CharField(
        max_length=1,
        choices=Forsendelsestype.choices,
        default=Forsendelsestype.SKIB,
    )
    oprettet_af = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,  # Vi kan slette brugere & beholde deres forsendelser
        null=True,
    )
    afgangsdato = models.DateField(null=True, blank=True, default=date.today)
    kladde = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        super().full_clean()
        super().save(*args, **kwargs)


class Postforsendelse(Forsendelse):
    class Meta:
        ordering = ["postforsendelsesnummer"]
        constraints = [
            CheckConstraint(
                check=Q(postforsendelsesnummer__isnull=False) | Q(kladde=True),
                name="aktuel_har_postforsendelsesnummer",
            ),
            CheckConstraint(
                check=Q(afsenderbykode__isnull=False) | Q(kladde=True),
                name="aktuel_har_afsenderbykode",
            ),
        ]

    postforsendelsesnummer = models.CharField(
        max_length=20,
        db_index=True,
        blank=True,
        null=True,
    )
    afsenderbykode = models.CharField(
        max_length=4,
        db_index=True,
        blank=True,
        null=True,
    )

    def __str__(self):
        nummer = self.postforsendelsesnummer
        slags = Forsendelse.Forsendelsestype(self.forsendelsestype).label
        afsenderbykode = self.afsenderbykode
        return (
            f"Postforsendelse(postforsendelsesnummer={nummer}, "
            + f"forsendelsestype={slags}, "
            + f"afsenderbykode={afsenderbykode})"
        )


def fragtbrev_upload_to(instance, filename):
    return (
        f"fragtbreve/{instance.pk}/{filename}"  # Relative to MEDIA_ROOT in settings.py
    )


class Fragtforsendelse(Forsendelse):
    class Meta:
        ordering = ["fragtbrevsnummer"]
        constraints = [
            CheckConstraint(
                check=Q(fragtbrevsnummer__isnull=False) | Q(kladde=True),
                name="aktuel_har_fragtbrevsnummer",
            ),
            CheckConstraint(
                check=Q(forbindelsesnr__isnull=False) | Q(kladde=True),
                name="aktuel_har_forbindelsesnr",
            ),
        ]

    fragtbrevsnummer = models.CharField(
        max_length=20,
        db_index=True,
        null=True,
        blank=True,
    )
    forbindelsesnr = models.CharField(
        max_length=100,
        db_index=True,
        null=True,
        blank=True,
    )

    fragtbrev = models.FileField(
        upload_to=fragtbrev_upload_to,
        null=True,
        blank=True,
    )

    def __str__(self):
        nummer = self.fragtbrevsnummer
        slags = Forsendelse.Forsendelsestype(self.forsendelsestype).label
        forbindelsesnr = self.forbindelsesnr
        return (
            f"Fragtforsendelse(fragtbrevsnummer={nummer}, "
            f"forsendelsestype={slags}, "
            f"forbindelsesnr={forbindelsesnr})"
        )

    def clean(self):
        super().clean()
        if self.kladde:
            return
        if self.forsendelsestype == Forsendelse.Forsendelsestype.SKIB:
            if not re.match(
                r"[a-zA-Z]{3} \d{3}$",
                self.forbindelsesnr if self.forbindelsesnr is not None else "",
            ):
                raise ValidationError(
                    "Ved skibsfragt skal forbindelsesnummer bestå "
                    "af tre bogstaver, mellemrum og tre cifre"
                )
            if not re.match(
                r"^[a-zA-Z]{5}\d{7}$",
                self.fragtbrevsnummer if self.fragtbrevsnummer is not None else "",
            ):
                raise ValidationError(
                    "Ved skibsfragt skal fragtbrevnr bestå af "
                    "fem bogstaver efterfulgt af syv cifre"
                )
        if self.forsendelsestype == Forsendelse.Forsendelsestype.FLY:
            if not re.match(
                r"^\d{3}$",
                self.forbindelsesnr if self.forbindelsesnr is not None else "",
            ):
                raise ValidationError(
                    "Ved luftfragt skal forbindelsesnummer bestå af tre cifre"
                )
            if not re.match(
                r"^\d{8}$",
                self.fragtbrevsnummer if self.fragtbrevsnummer is not None else "",
            ):
                raise ValidationError(
                    "Ved luftfragt skal fragtbrevnummer bestå af otte cifre"
                )
