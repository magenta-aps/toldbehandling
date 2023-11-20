# django payments views


from decimal import Decimal
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import TemplateView
from payments import RedirectNeeded, get_payment_model


class PaymentTestView(TemplateView):
    template_name = "test.html"

    def get(self, request, *args, **kwargs):
        action = request.GET.get('action')
        match action:
            case "create":
                payment = get_payment_model().objects.create(
                    variant="default",
                    description="Test payment",
                    total=Decimal(100),
                    tax=Decimal(25),
                    currency="DKK",
                    delivery=Decimal(10),
                    billing_first_name="Magenta Test",
                    billing_last_name="OpenSourceFTW",
                    billing_address_1="Silkeborgvej 260, 1. sal",
                    billing_address_2="",
                    billing_city="Aabyhoj",
                    billing_postcode="8230",
                    billing_country_code="DK",
                    customer_ip_address="127.0.0.1",
                )

                return redirect(f"/betaling/detaljer/{payment.id}")
        
        return super(PaymentTestView, self).get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get query-param "action"
        action = self.request.GET.get("action", None)
        if not action:
            return context

        match action:
            case "create":
                payment = get_payment_model().objects.create(
                    variant="default",
                    description="Test payment",
                    total=Decimal(100),
                    tax=Decimal(25),
                    currency="DKK",
                    delivery=Decimal(10),
                    billing_first_name="Magenta Test",
                    billing_last_name="OpenSourceFTW",
                    billing_address_1="Silkeborgvej 260, 1. sal",
                    billing_address_2="",
                    billing_city="Aabyhoj",
                    billing_postcode="8230",
                    billing_country_code="DK",
                    customer_ip_address="127.0.0.1",
                )

                # Redirect to payment details
                return redirect("betaling/detaljer", payment_id=payment.id)


class PaymentDetailsView(TemplateView):
    template_name = "details.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get payment & create form
        payment_id = 1
        payment = get_object_or_404(get_payment_model(), id=payment_id)
        try:
            # form = payment.get_form(data=self.context.request.POST or None)
            form = payment.get_form(data=self.request.POST or None)
            context["form"] = form
        except RedirectNeeded as redirect_to:
            return redirect(str(redirect_to))

        return context


# def payment_details(request, payment_id):
#     payment = get_object_or_404(get_payment_model(), id=payment_id)

#     try:
#         form = payment.get_form(data=request.POST or None)
#     except RedirectNeeded as redirect_to:
#         return redirect(str(redirect_to))

#     return TemplateResponse(
#         request,
#         'payment.html',
#         {'form': form, 'payment': payment}
#     )
