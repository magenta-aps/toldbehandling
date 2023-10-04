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
