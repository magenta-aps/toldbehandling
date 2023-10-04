# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _


class Forsendelse(models.Model):
    class Meta:
        abstract = True

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

    def save(self, *args, **kwargs):
        super().full_clean()
        super().save(*args, **kwargs)


class Postforsendelse(Forsendelse):
    class Meta:
        ordering = ["postforsendelsesnummer"]

    postforsendelsesnummer = models.CharField(
        max_length=20,
        db_index=True,
    )
    afsenderbykode = models.CharField(max_length=4, db_index=True)

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

    fragtbrevsnummer = models.CharField(
        max_length=20,
        db_index=True,
    )
    forbindelsesnr = models.CharField(max_length=100, db_index=True)

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
