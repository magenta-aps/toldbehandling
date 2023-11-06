# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


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
        validators=(
            MinValueValidator(1000),
            MaxValueValidator(9999),
        ),
    )
    by = models.CharField(
        max_length=50,
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

    def __str__(self):
        return f"{self.__class__.__name__}(navn={self.navn}, cvr={self.cvr})"

    def save(self, *args, **kwargs):
        super().full_clean()
        super().save(*args, **kwargs)


class Afsender(Aktør):
    pass


class Modtager(Aktør):
    kreditordning = models.BooleanField(
        default=False,
    )
