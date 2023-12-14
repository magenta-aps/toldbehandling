# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from told_common import views as common_views


class TF10FormCreateView(common_views.TF10FormCreateView):
    extend_template = "ui/layout.html"


class TF10ListView(common_views.TF10ListView):
    actions_template = "ui/tf10/actions.html"
    extend_template = "ui/layout.html"

    def get_context_data(self, **context):
        return super().get_context_data(**{**context, "can_create": True})


class TF10FormUpdateView(common_views.TF10FormUpdateView):
    extend_template = "ui/layout.html"
