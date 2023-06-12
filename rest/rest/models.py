from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class Aktør(models.Model):
    class Meta:
        abstract = True
        ordering = ["navn"]

    navn = models.CharField(
        max_length=100,
        db_index=True,
    )
    adresse = models.CharField(
        max_length=100,
    )
    postnummer = models.PositiveSmallIntegerField(
        db_index=True,
    )
    by = models.CharField(
        max_length=20,
        db_index=True,
    )
    postbox = models.CharField(
        max_length=10,
        null=True,
        blank=True,
    )
    telefon = models.CharField(
        max_length=12,
    )
    cvr = models.IntegerField(
        validators=(
            MinValueValidator(10000000),
            MaxValueValidator(99999999),
        ),
        unique=True,
        null=True,
        blank=True,
        db_index=True,
    )

    def __str__(self):
        return f"{self.__class__.__name__}(navn={self.navn}, cvr={self.cvr})"


class Afsender(Aktør):
    pass


class Modtager(Aktør):
    kreditordning = models.BooleanField(
        default=False,
    )


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


class Post(Forsendelse):
    class Meta:
        ordering = ["postforsendelsesnummer"]

    postforsendelsesnummer = models.CharField(
        max_length=20,
        db_index=True,
    )

    def __str__(self):
        return f"Post(postforsendelsesnummer={self.postforsendelsesnummer}, forsendelsestype={Forsendelse.Forsendelsestype(self.forsendelsestype).label})"


def fragtbrev_upload_to(instance, filename):
    return f"fragtbreve/{instance.afgiftsanmeldelse.pk}/{filename}"  # Relative to MEDIA_ROOT in settings.py


class Fragt(Forsendelse):
    class Meta:
        ordering = ["fragtbrevsnummer"]

    fragtbrevsnummer = models.CharField(
        max_length=20,
        db_index=True,
    )
    fragtbrev = models.FileField(
        upload_to=fragtbrev_upload_to,
    )

    def __str__(self):
        return f"Fragt(fragtbrevsnummer={self.fragtbrevsnummer}, forsendelsestype={Forsendelse.Forsendelsestype(self.forsendelsestype).label})"


def afgiftsanmeldelse_upload_to(instance, filename):
    return f"leverandørfakturaer/{instance.pk}/{filename}"  # Relative to MEDIA_ROOT in settings.py


class Afgiftsanmeldelse(models.Model):
    class Meta:
        ordering = ["dato"]

    anmeldelsesnummer = models.PositiveBigIntegerField(
        primary_key=True,
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
        Fragt,
        null=True,
        related_name="afgiftsanmeldelse",
        on_delete=models.SET_NULL,
    )
    postforsendelse = models.OneToOneField(
        Post,
        null=True,
        related_name="afgiftsanmeldelse",
        on_delete=models.SET_NULL,
    )
    leverandørfaktura_nummer = models.CharField(
        max_length=20,
        db_index=True,
    )
    leverandørfaktura = models.FileField(
        upload_to=afgiftsanmeldelse_upload_to,
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
    )
    betalt = models.BooleanField(
        default=False,
    )
    dato = models.DateField(
        auto_now_add=True,
        db_index=True,
    )

    def clean(self):
        if self.fragtforsendelse is None and self.postforsendelse is None:
            raise ValidationError(
                _("Fragtforsendelse og postforsendelse må ikke begge være None")
            )

    def __str__(self):
        return f"Afgiftsanmeldelse(anmeldelsesnummer={self.anmeldelsesnummer})"


class Afgiftstabel(models.Model):
    class Meta:
        ordering = ["-gyldig_fra", "-gyldig_til"]

    gyldig_fra = models.DateField(
        auto_now_add=True,
    )
    gyldig_til = models.DateField(
        null=True,
    )
    kladde = models.BooleanField(
        default=True,
    )

    def __str__(self):
        return f"Afgiftstabel(gyldig_fra={self.gyldig_fra}, gyldig_til={self.gyldig_til}, kladde={self.kladde})"


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


class Varelinje(models.Model):
    class Meta:
        ordering = ["afgiftssats"]

    afgiftsanmeldelse = models.ForeignKey(
        Afgiftsanmeldelse,
        on_delete=models.CASCADE,
    )
    afgiftssats = models.ForeignKey(
        Vareafgiftssats,
        on_delete=models.CASCADE,
    )
    kvantum = models.PositiveIntegerField()  # DecimalField?
    fakturabeløb = models.DecimalField(
        max_digits=16,
        decimal_places=2,
    )
    afgiftsbeløb = models.DecimalField(
        max_digits=16,
        decimal_places=2,
    )

    def __str__(self):
        return f"Varelinje(afgiftssats={self.afgiftssats}, fakturabeløb={self.fakturabeløb})"
