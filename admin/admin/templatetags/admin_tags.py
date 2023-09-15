from django.template.defaultfilters import register
from django.utils.translation import gettext_lazy as _

from admin.data import Vareafgiftssats


@register.filter
def enhedsnavn(item: Vareafgiftssats.Enhed) -> str:
    if item == Vareafgiftssats.Enhed.KG:
        return _("kilogram")
    if item == Vareafgiftssats.Enhed.LITER:
        return _("liter")
    if item == Vareafgiftssats.Enhed.ANTAL:
        return _("antal")
    if item == Vareafgiftssats.Enhed.PROCENT:
        return _("procent")
    if item == Vareafgiftssats.Enhed.SAMMENSAT:
        return _("sammensat")
