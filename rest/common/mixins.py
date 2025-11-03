# SPDX-FileCopyrightText: 2025 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class ConcurrentUpdateMixin(models.Model):
    version = models.IntegerField(default=0)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # Ensure version is updated even with update_fields
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            update_fields = set(update_fields)
            update_fields.add("version")
            kwargs["update_fields"] = tuple(update_fields)

        super().save(*args, **kwargs)

    @staticmethod
    def pre_save(sender, instance, *args, **kwargs):
        if not instance.pk:
            return
        current = sender.objects.get(pk=instance.pk)

        if instance.version and current.version != instance.version:
            raise ValidationError(
                _(
                    (
                        "Objektet er blevet opdateret af "
                        "en anden bruger siden du åbnede den."
                    )
                ),
                code="concurrent_update",
            )
        instance.version += 1
