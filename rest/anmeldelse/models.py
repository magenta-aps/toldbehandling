# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
from datetime import date, timedelta
from decimal import Decimal

from aktør.models import Afsender, Modtager, Speditør
from common.models import Postnummer
from common.util import dato_måned_slut
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import CheckConstraint, Q
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from forsendelse.models import Fragtforsendelse, Postforsendelse
from sats.models import Vareafgiftssats
from simple_history.models import HistoricalRecords, HistoricForeignKey


def afgiftsanmeldelse_upload_to(instance, filename):
    return f"leverandørfakturaer/{instance.pk}/{filename}"


def privatafgiftsanmeldelse_upload_to(instance, filename):
    return f"privatfakturaer/{instance.pk}/{filename}"


class Afgiftsanmeldelse(models.Model):
    class Meta:
        ordering = ["id"]
        constraints = [
            CheckConstraint(
                check=Q(afsender__isnull=False) | Q(status="kladde"),
                name="aktuel_har_afsender",
            ),
            CheckConstraint(
                check=Q(modtager__isnull=False) | Q(status="kladde"),
                name="aktuel_har_modtager",
            ),
            CheckConstraint(
                check=Q(leverandørfaktura_nummer__isnull=False) | Q(status="kladde"),
                name="aktuel_har_leverandørfaktura_nummer",
            ),
            CheckConstraint(
                check=Q(leverandørfaktura__isnull=False) | Q(status="kladde"),
                name="aktuel_har_leverandørfaktura",
            ),
        ]

    BETALES_AF_BLANK = None
    BETALES_AF_AFSENDER = "afsender"
    BETALES_AF_MODTAGER = "modtager"
    BETALES_AF_INDBERETTER = "indberetter"
    BETALES_AF_CHOICES = {
        BETALES_AF_BLANK: "Blank",
        BETALES_AF_AFSENDER: "Afsender",
        BETALES_AF_MODTAGER: "Modtager",
        BETALES_AF_INDBERETTER: "Indberetter",
    }

    history = HistoricalRecords()
    oprettet_af = models.ForeignKey(
        User,
        related_name="afgiftsanmeldelser",
        on_delete=models.SET_NULL,  # Vi kan slette brugere og beholde deres anmeldelser
        null=True,
    )
    oprettet_på_vegne_af = models.ForeignKey(
        User,
        related_name="afgiftsanmeldelser_på_vegne_af",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    afsender = models.ForeignKey(
        Afsender,
        related_name="afgiftsanmeldelser",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    modtager = models.ForeignKey(
        Modtager,
        related_name="afgiftsanmeldelser",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
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
        null=True,
        blank=True,
    )
    leverandørfaktura = models.FileField(
        upload_to=afgiftsanmeldelse_upload_to,
        null=True,
        blank=True,
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
        null=False,
        blank=False,
        default=Decimal("0.00"),
    )
    betalt = models.BooleanField(
        default=False,
    )
    dato = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )
    status = models.CharField(
        choices=(
            ("kladde", "kladde"),
            ("ny", "ny"),
            ("afvist", "afvist"),
            ("godkendt", "godkendt"),
            ("afsluttet", "afsluttet"),
        ),
        default="ny",
    )
    toldkategori = models.CharField(
        max_length=3,
        verbose_name=_("Toldkategori"),
        null=True,
        blank=True,
    )
    fuldmagtshaver = models.ForeignKey(
        Speditør,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    betales_af = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=BETALES_AF_CHOICES.items(),
        default=BETALES_AF_BLANK,
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

    def beregn_afgift_total(self) -> bool:
        old_value = self.afgift_total
        self.afgift_total = sum(
            [
                varelinje.afgiftsbeløb
                for varelinje in self.varelinje_set.all()
                if varelinje.afgiftsbeløb
            ]
        )
        return self.afgift_total != old_value

    @property
    def beregnet_faktureringsdato(self):
        return self.beregn_faktureringsdato(self)

    @staticmethod
    def beregn_faktureringsdato(afgiftsanmeldelse) -> date:
        # Splittet fordi historisk model ikke har ovenstående property
        forsendelse = (
            afgiftsanmeldelse.fragtforsendelse or afgiftsanmeldelse.postforsendelse
        )
        afgangsdato = forsendelse.afgangsdato
        måned_slut = dato_måned_slut(afgangsdato)
        postnummer = afgiftsanmeldelse.modtager.postnummer
        if afgiftsanmeldelse.toldkategori == "76":
            ekstra_dage = 14  # 59830
        else:
            try:
                ekstra_dage = Postnummer.objects.get(postnummer=postnummer).dage
            except Postnummer.DoesNotExist:
                ekstra_dage = 0
        return måned_slut + timedelta(days=ekstra_dage)


class PrivatAfgiftsanmeldelse(models.Model):
    history = HistoricalRecords()
    oprettet = models.DateTimeField(auto_now_add=True)
    oprettet_af = models.ForeignKey(
        User,
        related_name="private_afgiftsanmeldelser",
        on_delete=models.SET_NULL,  # Vi kan slette brugere og beholde deres anmeldelser
        null=True,
    )
    oprettet_på_vegne_af = models.ForeignKey(
        User,
        related_name="private_afgiftsanmeldelser_på_vegne_af",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    cpr = models.BigIntegerField(
        verbose_name=_("CPR-nummer"),
        db_index=True,
        validators=(
            MinValueValidator(101000000),
            MaxValueValidator(3112999999),
        ),
        null=False,
        blank=False,
    )
    anonym = models.BooleanField(
        default=False,
        db_index=True,
    )
    navn = models.CharField(
        max_length=100,
        db_index=True,
        null=False,
        blank=False,
    )
    adresse = models.CharField(
        max_length=100,
        null=False,
        blank=False,
    )
    postnummer = models.PositiveSmallIntegerField(
        db_index=True,
        validators=(
            MinValueValidator(1000),
            MaxValueValidator(9999),
        ),
        null=False,
        blank=False,
    )
    by = models.CharField(
        max_length=50,
        db_index=True,
        null=False,
        blank=False,
    )
    telefon = models.CharField(
        max_length=12,
        null=False,
        blank=False,
    )

    bookingnummer = models.CharField(
        max_length=128,
        verbose_name=_("Bookingnummer udstedt af speditør"),
        null=False,
        blank=False,
    )
    leverandørfaktura_nummer = models.CharField(
        max_length=20,
        verbose_name=_("Varefakturanummer udstedt af forhandler"),
        null=False,
        blank=False,
    )
    indførselstilladelse = models.CharField(
        max_length=20,
        verbose_name=_("Nummer på senest udstedte indførselstilladelse"),
        null=True,
        blank=True,
    )
    indleveringsdato = models.DateField()
    leverandørfaktura = models.FileField(
        upload_to=privatafgiftsanmeldelse_upload_to,
        null=True,
        blank=True,
    )
    status = models.CharField(
        choices=(
            ("ny", "ny"),
            ("annulleret", "annulleret"),  # Borger har self annulleret
            ("afvist", "afvist"),
            ("godkendt", "godkendt"),
            ("afsluttet", "afsluttet"),
        ),
        default="ny",
    )


class Varelinje(models.Model):
    class Meta:
        ordering = ["vareafgiftssats"]
        constraints = [
            CheckConstraint(
                check=Q(afgiftsanmeldelse__isnull=False)
                | Q(privatafgiftsanmeldelse__isnull=False),
                name="afgiftsanmeldelse_has_one",
            ),
            CheckConstraint(
                check=Q(afgiftsanmeldelse__isnull=True)
                | Q(privatafgiftsanmeldelse__isnull=True),
                name="afgiftsanmeldelse_only_one",
            ),
            CheckConstraint(
                check=Q(vareafgiftssats__isnull=False) | Q(kladde=True),
                name="aktuel_har_vareafgiftssats",
            ),
        ]

    history = HistoricalRecords()
    afgiftsanmeldelse = HistoricForeignKey(
        Afgiftsanmeldelse,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        default=None,
    )
    privatafgiftsanmeldelse = HistoricForeignKey(
        PrivatAfgiftsanmeldelse,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        default=None,
    )
    vareafgiftssats = models.ForeignKey(
        Vareafgiftssats,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    mængde = models.DecimalField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        decimal_places=3,
        max_digits=13,
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
    kladde = models.BooleanField(default=False)

    def __str__(self):
        return (
            f"Varelinje(vareafgiftssats={self.vareafgiftssats}, "
            + f"fakturabeløb={self.fakturabeløb})"
        )

    def save(self, *args, **kwargs):
        super().full_clean()
        self.beregn_afgift()
        super().save(*args, **kwargs)
        if self.afgiftsanmeldelse:
            changed = self.afgiftsanmeldelse.beregn_afgift_total()
            if changed:
                self.afgiftsanmeldelse.save(update_fields=("afgift_total",))

    def beregn_afgift(self) -> None:
        if self.vareafgiftssats:
            self.afgiftsbeløb = self.vareafgiftssats.beregn_afgift(self)


class Notat(models.Model):
    class Meta:
        constraints = [
            CheckConstraint(
                check=Q(afgiftsanmeldelse__isnull=False)
                | Q(privatafgiftsanmeldelse__isnull=False),
                name="notat_has_one_anmeldelse",
            ),
            CheckConstraint(
                check=Q(afgiftsanmeldelse__isnull=True)
                | Q(privatafgiftsanmeldelse__isnull=True),
                name="notat_only_one_anmeldelse",
            ),
        ]

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
        null=True,
        blank=True,
        default=None,
    )
    privatafgiftsanmeldelse = models.ForeignKey(
        PrivatAfgiftsanmeldelse,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        default=None,
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
    delivery_date = models.DateTimeField(null=False)


@receiver(post_save, sender=PrismeResponse, dispatch_uid="on_add_prismeresponse")
def on_add_prismeresponse(
    sender, instance, created, raw, using, update_fields, **kwargs
):
    if created:
        instance.afgiftsanmeldelse.status = "afsluttet"
        instance.afgiftsanmeldelse.save()


@receiver(post_delete, sender=PrismeResponse, dispatch_uid="on_delete_prismeresponse")
def on_delete_prismeresponse(sender, instance, **kwargs):
    if not instance.afgiftsanmeldelse.prismeresponse_set.exists():
        instance.afgiftsanmeldelse.status = "godkendt"
        instance.afgiftsanmeldelse.save()
