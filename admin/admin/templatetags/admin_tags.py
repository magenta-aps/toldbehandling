# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from django.template.defaultfilters import register
from django.utils.translation import gettext_lazy as _
from told_common.data import Vareafgiftssats


@register.filter
def enhedsnavn(item: Vareafgiftssats.Enhed) -> str:
    if item == Vareafgiftssats.Enhed.KILOGRAM:
        return _("kilogram")
    if item == Vareafgiftssats.Enhed.LITER:
        return _("liter")
    if item == Vareafgiftssats.Enhed.ANTAL:
        return _("antal")
    if item == Vareafgiftssats.Enhed.PROCENT:
        return _("procent")
    if item == Vareafgiftssats.Enhed.SAMMENSAT:
        return _("sammensat")
