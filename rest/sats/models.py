from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _


class Afgiftstabel(models.Model):
    class Meta:
        ordering = ["-gyldig_fra", "-gyldig_til"]

    gyldig_fra = models.DateField(
        auto_now_add=True,
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


class Vareafgiftssats(models.Model):
    class Meta:
        ordering = ["afgiftsgruppenummer"]
        constraints = (
            models.UniqueConstraint(
                fields=("afgiftstabel", "vareart"), name="vareart_constraint"
            ),
        )

    class Enhed(models.TextChoices):
        ANTAL = (
            "ant",
            _("Antal"),
        )
        KG = (
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
    vareart = models.CharField(
        max_length=300,
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
            Vareafgiftssats.Enhed.KG,
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
