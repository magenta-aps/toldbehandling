# SPDX-FileCopyrightText: 2024 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from split_settings.tools import include

include(
    "base.py",
    "apps.py",
    "middleware.py",
    "database.py",
    "cache.py",
    "csp.py",
    "templates.py",
    "locale.py",
    "login.py",
    "logging.py",
    "staticfiles.py",
    "payment.py",
)
