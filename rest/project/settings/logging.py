# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
import os

from project.settings.base import ENVIRONMENT, TESTING
from project.util import strtobool

LOGGING: dict = {
    "version": 1,
    "disable_existing_loggers": True,
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
    },
    "formatters": {
        "simple": {
            "format": "[{asctime}] [{levelname}] {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# Logging to files (legacy)
disable_file_logging = strtobool(os.environ.get("DISABLE_FILE_LOGGING", "False"))
log_filename = "/rest.log"
if not disable_file_logging:
    if os.path.isfile(log_filename) and ENVIRONMENT != "development":
        LOGGING["handlers"]["file"] = {
            "class": "logging.FileHandler",  # eller WatchedFileHandler
            "formatter": "simple",
            "filename": log_filename,
        }

        LOGGING["root"]["handlers"].append("file")
        LOGGING["loggers"]["django"]["handlers"].append("file")

if TESTING:
    import logging

    logging.disable(logging.CRITICAL)
