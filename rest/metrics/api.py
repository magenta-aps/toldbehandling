from django.http import HttpResponse
from ninja_extra import api_controller, permissions, route
from ninja_jwt.authentication import JWTAuth
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest


@api_controller(
    "/metrics",
    tags=["metrics"],
    permissions=[permissions.IsAuthenticated],
)
class MetricsAPI:
    @route.get("", auth=JWTAuth(), url_name="metrics_get_all")
    def get_all(self):
        return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)
