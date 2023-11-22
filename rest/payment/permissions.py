# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0


from project.util import RestPermission


class PaymentPermission(RestPermission):
    appname = "payment"
    modelname = "paymentnets"
