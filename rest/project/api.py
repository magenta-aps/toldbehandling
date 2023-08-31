from aktør.api import AfsenderAPI, ModtagerAPI
from anmeldelse.api import AfgiftsanmeldelseAPI, VarelinjeAPI
from forsendelse.api import PostforsendelseAPI, FragtforsendelseAPI
from ninja_extra import NinjaExtraAPI
from ninja_jwt.controller import NinjaJWTDefaultController
from project.util import ORJSONRenderer
from sats.api import AfgiftstabelAPI, VareafgiftssatsAPI

api = NinjaExtraAPI(title="Toldbehandling", renderer=ORJSONRenderer(), csrf=False)
api.register_controllers(NinjaJWTDefaultController)
api.register_controllers(AfsenderAPI, ModtagerAPI)
api.register_controllers(AfgiftsanmeldelseAPI, VarelinjeAPI)
api.register_controllers(PostforsendelseAPI, FragtforsendelseAPI)
api.register_controllers(AfgiftstabelAPI, VareafgiftssatsAPI)
