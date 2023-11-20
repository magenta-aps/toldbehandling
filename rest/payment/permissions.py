
from project.util import RestPermission


class PaymentPermission(RestPermission):
    appname = "payment"
    modelname = "paymentnets"