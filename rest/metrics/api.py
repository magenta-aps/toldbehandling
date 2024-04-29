from ninja_extra import api_controller, permissions, route
from ninja_jwt.authentication import JWTAuth


@api_controller(
    "/metrics",
    tags=["metrics"],
    permissions=[permissions.IsAuthenticated],
)
class MetricsAPI:
    @route.get("", auth=JWTAuth(), url_name="metrics_get_all")
    def get_all(self):
        return "test-asd"
