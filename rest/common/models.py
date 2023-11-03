from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class IndberetterProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, null=False, related_name="indberetter_data"
    )
    cpr = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(101000000),
            MaxValueValidator(3112999999),
        ],
        db_index=True,
    )
    cvr = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(10000000), MaxValueValidator(99999999)],
        db_index=True,
    )


class Postnummer(models.Model):
    postnummer = models.PositiveSmallIntegerField(
        db_index=True,
        validators=(
            MinValueValidator(1000),
            MaxValueValidator(9999),
        ),
        null=False,
    )
    navn = models.CharField(
        max_length=100,
        null=False,
    )
    dage = models.PositiveSmallIntegerField(
        null=False,
        default=0,
    )
