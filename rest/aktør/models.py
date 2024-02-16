# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import CheckConstraint, Q

from rest.common.models import Postnummer


class Aktør(models.Model):
    class Meta:
        abstract = True
        ordering = ["navn"]

    navn = models.CharField(
        max_length=100,
        db_index=True,
        null=True,
        blank=True,
    )
    adresse = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )
    postnummer = models.PositiveIntegerField(
        db_index=True,
        validators=(
            MinValueValidator(1000),
            MaxValueValidator(99999999),
        ),
        null=True,
        blank=True,
    )
    postnummer_ref = models.ForeignKey(
        Postnummer,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    eksplicit_stedkode = models.PositiveSmallIntegerField(
        validators=(
            MinValueValidator(1),
            MaxValueValidator(999),
        ),
        null=True,
        blank=True,
    )
    by = models.CharField(
        max_length=50,
        db_index=True,
        null=True,
        blank=True,
    )
    postbox = models.CharField(
        max_length=10,
        null=True,
        blank=True,
    )
    telefon = models.CharField(
        max_length=12,
        null=True,
        blank=True,
    )
    cvr = models.PositiveIntegerField(
        validators=(
            MinValueValidator(10000000),
            MaxValueValidator(99999999),
        ),
        unique=False,
        null=True,
        blank=True,
        db_index=True,
    )
    kladde = models.BooleanField(
        default=False,
    )

    def __str__(self):
        return f"{self.__class__.__name__}(navn={self.navn}, cvr={self.cvr})"

    def save(self, *args, **kwargs):
        super().full_clean()
        if self.postnummer is None and self.postnummer_ref is not None:
            self.postnummer_ref = None
        elif self.postnummer_ref is None or self.postnummer_ref.postnummer != self.postnummer:
            self.postnummer_ref = Postnummer.objects.filter(postnummer=self.postnummer).first()
        super().save(*args, **kwargs)


class Afsender(Aktør):
    class Meta:
        constraints = [
            CheckConstraint(
                check=Q(navn__isnull=False) | Q(kladde=True),
                name="aktuel_afsender_har_navn",
            ),
            CheckConstraint(
                check=Q(adresse__isnull=False) | Q(kladde=True),
                name="aktuel_afsender_har_adresse",
            ),
            CheckConstraint(
                check=Q(postnummer__isnull=False) | Q(kladde=True),
                name="aktuel_afsender_har_postnummer",
            ),
            CheckConstraint(
                check=Q(by__isnull=False) | Q(kladde=True),
                name="aktuel_afsender_har_by",
            ),
        ]


class Modtager(Aktør):
    class Meta:
        constraints = [
            CheckConstraint(
                check=Q(navn__isnull=False) | Q(kladde=True),
                name="aktuel_modtager_har_navn",
            ),
            CheckConstraint(
                check=Q(adresse__isnull=False) | Q(kladde=True),
                name="aktuel_modtager_har_adresse",
            ),
            CheckConstraint(
                check=Q(postnummer__isnull=False) | Q(kladde=True),
                name="aktuel_modtager_har_postnummer",
            ),
            CheckConstraint(
                check=Q(by__isnull=False) | Q(kladde=True),
                name="aktuel_modtager_har_by",
            ),
        ]

    kreditordning = models.BooleanField(
        default=False,
    )


class Speditør(models.Model):
    cvr = models.PositiveIntegerField(
        primary_key=True,
        validators=(
            MinValueValidator(10000000),
            MaxValueValidator(99999999),
        ),
        unique=True,
        null=False,
        blank=False,
    )
    navn = models.CharField(max_length=100, null=False, blank=False, unique=True)
