# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
from datetime import timedelta

from aktør.models import Afsender, Modtager
from common.models import Postnummer
from common.util import dato_måned_slut
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from forsendelse.models import Fragtforsendelse, Postforsendelse
from sats.models import Vareafgiftssats
from simple_history.models import HistoricalRecords, HistoricForeignKey


def afgiftsanmeldelse_upload_to(instance, filename):
    return f"leverandørfakturaer/{instance.pk}/{filename}"


class Afgiftsanmeldelse(models.Model):
    class Meta:
        ordering = ["id"]

    history = HistoricalRecords()
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
        null=True,
        blank=True,
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

    @property
    def beregnet_faktureringsdato(self):
        return self.beregn_faktureringsdato(self)

    @staticmethod
    def beregn_faktureringsdato(afgiftsanmeldelse):
        # Splittet fordi historisk model ikke har ovenstående property
        forsendelse = (
            afgiftsanmeldelse.fragtforsendelse or afgiftsanmeldelse.postforsendelse
        )
        afgangsdato = forsendelse.afgangsdato
        måned_slut = dato_måned_slut(afgangsdato)
        postnummer = afgiftsanmeldelse.modtager.postnummer
        try:
            ekstra_dage = Postnummer.objects.get(postnummer=postnummer).dage
        except Postnummer.DoesNotExist:
            ekstra_dage = 0
        return måned_slut + timedelta(days=ekstra_dage)


class Varelinje(models.Model):
    class Meta:
        ordering = ["vareafgiftssats"]

    history = HistoricalRecords()
    afgiftsanmeldelse = HistoricForeignKey(
        Afgiftsanmeldelse,
        on_delete=models.CASCADE,
    )
    vareafgiftssats = models.ForeignKey(
        Vareafgiftssats,
        on_delete=models.CASCADE,
    )
    mængde = models.DecimalField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        decimal_places=2,
        max_digits=12,
    )
    antal = models.PositiveIntegerField(
        null=True,
        blank=True,
    )  # DecimalField?
    fakturabeløb = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
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


class Notat(models.Model):
    user = models.ForeignKey(
        User,
        null=True,
        on_delete=models.SET_NULL,
    )
    tekst = models.TextField()
    oprettet = models.DateTimeField(auto_now_add=True)
    afgiftsanmeldelse = models.ForeignKey(
        Afgiftsanmeldelse,
        on_delete=models.CASCADE,
    )
    index = models.PositiveSmallIntegerField(
        null=False,
        default=0,
    )


# Vis alle gældende notater i view
# Historisk: vis ikke fremtidige notater


class PrismeResponse(models.Model):
    afgiftsanmeldelse = models.ForeignKey(
        Afgiftsanmeldelse,
        on_delete=models.CASCADE,
        null=False,
    )
    rec_id = models.BigIntegerField(null=False)
    tax_notification_number = models.BigIntegerField(null=False)
    invoice_date = models.DateTimeField(null=False)
