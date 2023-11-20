from ninja import ModelSchema, Schema

from betaling.models import Payment


class PaymentModelSchema(ModelSchema):
    class Config:
        model = Payment
        model_fields = ["status", "total"]


class ErrorSchema(Schema):
    message: str
