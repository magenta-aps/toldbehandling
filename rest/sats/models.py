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
        return f"Afgiftstabel(gyldig_fra={self.gyldig_fra}, gyldig_til={self.gyldig_til}, kladde={self.kladde})"

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
            models.UniqueConstraint(
                fields=("afgiftstabel", "afgiftsgruppenummer"),
                name="afgiftsgruppenummer_constraint",
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
        PROCENT = "pct", _("Procent af fakturabeløb")

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

    def __str__(self):
        return f"Vareafgiftssats(afgiftsgruppenummer={self.afgiftsgruppenummer}, afgiftssats={self.afgiftssats}, enhed={Vareafgiftssats.Enhed(self.enhed).label})"

    def save(self, *args, **kwargs):
        super().full_clean()
        super().save(*args, **kwargs)
