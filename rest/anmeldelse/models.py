# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from aktør.models import Afsender, Modtager
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from forsendelse.models import Fragtforsendelse, Postforsendelse
from sats.models import Vareafgiftssats


def afgiftsanmeldelse_upload_to(instance, filename):
    return f"leverandørfakturaer/{instance.pk}/{filename}"


class Afgiftsanmeldelse(models.Model):
    class Meta:
        ordering = ["id"]

    oprettet_af = models.ForeignKey(
        User,
        related_name="afgiftsanmeldelser",
        on_delete=models.SET_NULL,  # Vi kan slette brugere og beholde deres anmeldelser
        null=True,
    )
    afsender = models.ForeignKey(
        Afsender,
        related_name="afgiftsanmeldelser",
        on_delete=models.CASCADE,
    )
    modtager = models.ForeignKey(
        Modtager,
        related_name="afgiftsanmeldelser",
        on_delete=models.CASCADE,
    )
    fragtforsendelse = models.OneToOneField(
        Fragtforsendelse,
        null=True,
        blank=True,
        related_name="afgiftsanmeldelse",
        on_delete=models.SET_NULL,
    )
    postforsendelse = models.OneToOneField(
        Postforsendelse,
        null=True,
        blank=True,
        related_name="afgiftsanmeldelse",
        on_delete=models.SET_NULL,
    )
    leverandørfaktura_nummer = models.CharField(
        max_length=20,
        db_index=True,
    )
    leverandørfaktura = models.FileField(
        upload_to=afgiftsanmeldelse_upload_to,
        null=True,
        blank=True,
    )
    modtager_betaler = models.BooleanField(
        default=False,
    )
    indførselstilladelse = models.CharField(
        max_length=20,
        db_index=True,
    )
    afgift_total = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        null=True,
        blank=True,
    )
    betalt = models.BooleanField(
        default=False,
    )
    dato = models.DateField(
        auto_now_add=True,
        db_index=True,
    )
    godkendt = models.BooleanField(
        null=True,
        blank=True,
        default=None,
    )

    def clean(self):
        if self.fragtforsendelse is None and self.postforsendelse is None:
            raise ValidationError(
                _("Fragtforsendelse og postforsendelse må ikke begge være None")
            )

    def __str__(self):
        return f"Afgiftsanmeldelse(id={self.id})"

    def save(self, *args, **kwargs):
        super().full_clean()
        super().save(*args, **kwargs)


class Varelinje(models.Model):
    class Meta:
        ordering = ["vareafgiftssats"]

    afgiftsanmeldelse = models.ForeignKey(
        Afgiftsanmeldelse,
        on_delete=models.CASCADE,
    )
    vareafgiftssats = models.ForeignKey(
        Vareafgiftssats,
        on_delete=models.CASCADE,
    )
    mængde = models.PositiveIntegerField(
        null=True,
        blank=True,
    )  # DecimalField?
    antal = models.PositiveIntegerField(
        null=True,
        blank=True,
    )  # DecimalField?
    fakturabeløb = models.DecimalField(
        max_digits=16, decimal_places=2, validators=[MinValueValidator(0)]
    )
    afgiftsbeløb = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )

    def __str__(self):
        return (
            f"Varelinje(vareafgiftssats={self.vareafgiftssats}, "
            + f"fakturabeløb={self.fakturabeløb})"
        )

    def save(self, *args, **kwargs):
        super().full_clean()
        self.beregn_afgift()
        super().save(*args, **kwargs)

    def beregn_afgift(self) -> None:
        self.afgiftsbeløb = self.vareafgiftssats.beregn_afgift(self)
