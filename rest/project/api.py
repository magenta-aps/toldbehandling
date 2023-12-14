# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from aktør.api import AfsenderAPI, ModtagerAPI
from common.api import EboksBeskedAPI, UserAPI
from forsendelse.api import FragtforsendelseAPI, PostforsendelseAPI
from ninja_extra import NinjaExtraAPI
from ninja_jwt.controller import NinjaJWTDefaultController
from project.util import ORJSONRenderer
from sats.api import AfgiftstabelAPI, VareafgiftssatsAPI

from anmeldelse.api import (  # isort: skip
    AfgiftsanmeldelseAPI,
    PrivatAfgiftsanmeldelseAPI,
    NotatAPI,
    PrismeResponseAPI,
    VarelinjeAPI,
)

api = NinjaExtraAPI(title="Toldbehandling", renderer=ORJSONRenderer(), csrf=False)
api.register_controllers(NinjaJWTDefaultController)
api.register_controllers(AfsenderAPI, ModtagerAPI)
api.register_controllers(
    AfgiftsanmeldelseAPI,
    PrivatAfgiftsanmeldelseAPI,
    VarelinjeAPI,
    NotatAPI,
    PrismeResponseAPI,
)
api.register_controllers(PostforsendelseAPI, FragtforsendelseAPI)
api.register_controllers(AfgiftstabelAPI, VareafgiftssatsAPI)
api.register_controllers(UserAPI, EboksBeskedAPI)
