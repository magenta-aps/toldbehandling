# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from aktør.api import AfsenderAPI, ModtagerAPI, SpeditørAPI
from anmeldelse.api import (
    AfgiftsanmeldelseAPI,
    NotatAPI,
    PrismeResponseAPI,
    PrivatAfgiftsanmeldelseAPI,
    StatistikAPI,
    VarelinjeAPI,
)
from common.api import EboksBeskedAPI, UserAPI
from forsendelse.api import FragtforsendelseAPI, PostforsendelseAPI
from ninja_extra import NinjaExtraAPI
from ninja_jwt.controller import NinjaJWTDefaultController
from otp.api import TOTPDeviceAPI, TwoFactorLoginAPI
from payment.api import PaymentAPI
from project.util import ORJSONRenderer
from sats.api import AfgiftstabelAPI, VareafgiftssatsAPI

api = NinjaExtraAPI(title="Toldbehandling", renderer=ORJSONRenderer(), csrf=False)
api.register_controllers(NinjaJWTDefaultController)
api.register_controllers(AfsenderAPI, ModtagerAPI, SpeditørAPI)
api.register_controllers(
    AfgiftsanmeldelseAPI,
    PrivatAfgiftsanmeldelseAPI,
    VarelinjeAPI,
    NotatAPI,
    PrismeResponseAPI,
    StatistikAPI,
)
api.register_controllers(PostforsendelseAPI, FragtforsendelseAPI)
api.register_controllers(AfgiftstabelAPI, VareafgiftssatsAPI)
api.register_controllers(UserAPI, EboksBeskedAPI)
api.register_controllers(PaymentAPI)
api.register_controllers(TOTPDeviceAPI, TwoFactorLoginAPI)
