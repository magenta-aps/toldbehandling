# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db import models
from django.db.models import CheckConstraint, Q
from django.db.models.signals import post_save
from django.utils.translation import gettext_lazy as _


class Afgiftstabel(models.Model):
    class Meta:
        ordering = ["-gyldig_fra", "-gyldig_til"]
        constraints = [
            CheckConstraint(
                check=Q(kladde=True) | Q(gyldig_fra__isnull=False),
                name="kladde_or_has_gyldig_fra",
            )
        ]

    gyldig_fra = models.DateField(
        null=True,
        blank=True,
    )
    gyldig_til = models.DateField(
        null=True,
        blank=True,
    )
    kladde = models.BooleanField(
        default=True,
    )

    def __str__(self):
        fra = self.gyldig_fra
        til = self.gyldig_til
        kladde = self.kladde
        return f"Afgiftstabel(gyldig_fra={fra}, gyldig_til={til}, kladde={kladde})"

    def save(self, *args, **kwargs):
        super().full_clean()
        super().save(*args, **kwargs)

    @staticmethod
    def on_update(sender, instance: Afgiftstabel, **kwargs):
        # En afgiftstabel har (måske) fået ændret sin `gyldig_fra`
        # Opdatér `gyldig_til` på alle tabeller som er påvirkede
        # (tidl. prev, ny prev, tabellen selv)
        # Det er nemmest og sikrest at loope over hele banden,
        # så vi er sikre på at ramme alle
        update_fields = kwargs.get("update_fields")
        if not update_fields or "gyldig_fra" in update_fields:
            gyldig_til = None
            for item in Afgiftstabel.objects.filter(kladde=False).order_by(
                "-gyldig_fra"
            ):
                # Loop over alle tabeller fra sidste til første
                if item.gyldig_til != gyldig_til:
                    item.gyldig_til = gyldig_til
                    # Sæt kun `gyldig_til`, så vi forhindrer rekursion
                    item.save(update_fields=("gyldig_til",))
                gyldig_til = item.gyldig_fra - timedelta(days=1)


post_save.connect(
    Afgiftstabel.on_update, sender=Afgiftstabel, dispatch_uid="afgiftstabel_update"
)


class Vareafgiftssats(models.Model):
    class Meta:
        ordering = ["afgiftsgruppenummer"]
        constraints = (
            models.UniqueConstraint(
                fields=("afgiftstabel", "vareart_da"), name="vareart_constraint_da"
            ),
            models.UniqueConstraint(
                fields=("afgiftstabel", "vareart_kl"), name="vareart_constraint_kl"
            ),
        )

    class Enhed(models.TextChoices):
        ANTAL = (
            "ant",
            _("Antal"),
        )
        KILOGRAM = (
            "kg",
            _("Kilogram"),
        )
        LITER = (
            "l",
            _("Liter"),
        )
        PROCENT = (
            "pct",
            _("Procent af fakturabeløb"),
        )
        SAMMENSAT = ("sam", _("Sammensat"))

    afgiftstabel = models.ForeignKey(
        Afgiftstabel,
        on_delete=models.CASCADE,
    )
    vareart_da = models.CharField(
        max_length=300,
    )
    vareart_kl = models.CharField(
        max_length=300,
        default="",  # Hvis vi merger migrations, skal disse to linjer fjernes
        blank=True,
    )
    afgiftsgruppenummer = models.PositiveIntegerField()
    enhed = models.CharField(
        max_length=3,
        choices=Enhed.choices,
        default=Enhed.ANTAL,
    )
    afgiftssats = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )
    kræver_indførselstilladelse = models.BooleanField(
        default=False,
    )
    minimumsbeløb = models.DecimalField(
        null=True,
        blank=True,
        default=None,
        max_digits=10,
        decimal_places=2,
    )
    har_privat_tillægsafgift_alkohol = models.BooleanField(default=False)

    # Ved sammensatte afgifter kan disse felter benyttes til at lave forskellig
    # afgift på forskellige dele af importen
    #
    # F.eks. x% afgift på de første 100.000 kr i fakturabeløbet, og y% på beløb
    # derover.
    #
    # Det vil fungere som at en sats er "overordnet" de andre (de peger på
    # den), og alle de underordnede beregner tilsammen afgiften.
    #

    overordnet = models.ForeignKey(
        "Vareafgiftssats",
        null=True,
        blank=True,
        default=None,
        on_delete=models.CASCADE,
        related_name="underordnede",
    )
    segment_nedre = models.DecimalField(
        null=True,
        blank=True,
        default=None,
        max_digits=10,
        decimal_places=2,
        verbose_name="Nedre grænse for mængden der skal beregnes afgift ud fra",
    )
    segment_øvre = models.DecimalField(
        null=True,
        blank=True,
        default=None,
        max_digits=10,
        decimal_places=2,
        verbose_name="Øvre grænse for mængden der skal beregnes afgift ud fra",
    )
    synlig_privat = models.BooleanField(
        default=False,
        verbose_name="Vareafgiftssatsen kan bruges af private",
    )

    def __str__(self):
        nummer = self.afgiftsgruppenummer
        sats = self.afgiftssats
        enhed = Vareafgiftssats.Enhed(self.enhed).label
        return (
            f"Vareafgiftssats(afgiftsgruppenummer={nummer}, afgiftssats={sats}, "
            + f"enhed={enhed})"
        )

    def save(self, *args, **kwargs):
        super().full_clean()
        super().save(*args, **kwargs)

    _quantization_source = Decimal("0.01")

    def beregn_afgift(self, varelinje) -> Decimal:
        if self.enhed in (
            Vareafgiftssats.Enhed.KILOGRAM,
            Vareafgiftssats.Enhed.LITER,
        ):
            return (varelinje.mængde * self.afgiftssats).quantize(
                Vareafgiftssats._quantization_source
            )
        if self.enhed in (Vareafgiftssats.Enhed.ANTAL,):
            return (varelinje.antal * self.afgiftssats).quantize(
                Vareafgiftssats._quantization_source
            )
        if self.enhed == Vareafgiftssats.Enhed.PROCENT:
            fakturabeløb: Decimal = varelinje.fakturabeløb
            if self.segment_øvre:
                fakturabeløb = fakturabeløb.min(self.segment_øvre)
            if self.segment_nedre:
                fakturabeløb = Decimal(fakturabeløb - self.segment_nedre).max(0)
            return (fakturabeløb * Decimal(0.01) * self.afgiftssats).quantize(
                Vareafgiftssats._quantization_source
            )
        if self.enhed == Vareafgiftssats.Enhed.SAMMENSAT:
            return sum(
                [
                    subsats.beregn_afgift(varelinje)
                    for subsats in self.underordnede.all()
                ]
            )
