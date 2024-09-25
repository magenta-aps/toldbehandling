# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from django import template
from django.template.defaultfilters import register
from django.utils.translation import gettext_lazy as _
from django_stubs_ext import StrPromise
from told_common.data import Vareafgiftssats


@register.filter
def enhedsnavn(item: Vareafgiftssats.Enhed) -> StrPromise:
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


@register.tag(name="nonced")
def nonced(parser, token):
    nodelist = parser.parse(("endnonced",))
    parser.delete_first_token()
    return NonceInsertionNode(nodelist)


class NonceInsertionNode(template.Node):
    def __init__(self, nodelist, **kwargs):
        self.nodelist = nodelist

    def render(self, context):
        output = self.nodelist.render(context)
        request = context.get("request")
        if hasattr(request, "csp_nonce"):
            output = output.replace("<script ", f'<script nonce="{request.csp_nonce}" ')
        return output
