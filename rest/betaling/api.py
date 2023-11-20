from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from ninja_extra import api_controller, permissions, route
from ninja_jwt.authentication import JWTAuth
from payments import RedirectNeeded, get_payment_model
from betaling.schemas import PaymentModelSchema

from project.util import RestPermission

# Permissions


class BetalingPermission(RestPermission):
    appname = "betaling"
    modelname = "betaling"


# Controllers


@api_controller(
    "/betaling",
    tags=["Betaling"],
    permissions=[permissions.IsAuthenticated & BetalingPermission],
)
class BetalingApiController:
    @route.get(
        "/details/{int:payment_id}",
        auth=JWTAuth,
        url_name="betaling_api_details",
        response={200: PaymentModelSchema},
    )
    def details(self, payment_id: int):
        payment = get_object_or_404(get_payment_model(), id=payment_id)

        try:
            form = payment.get_form(data=self.context.request.POST or None)
        except RedirectNeeded as redirect_to:
            return redirect(str(redirect_to))

        return TemplateResponse(
            self.context.request, "payment.html", {"form": form, "payment": payment}
        )

    @route.post("", auth=JWTAuth, url_name="betaling_api_create", response={201: None})
    def create_payment(self):
        pass
