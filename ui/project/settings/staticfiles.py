# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
from .base import DEBUG, TESTING

STATIC_URL = "/static/"
STATIC_ROOT = "/static"

STORAGES = {
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if TESTING
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}

STATICFILES_DIRS = [
    "/app/told-common/told_common/static/",  # For pipeline tests
    "/app/told_common/static/",
]
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "compressor.finders.CompressorFinder",
]

COMPRESS_PRECOMPILERS = (("text/x-scss", "django_libsass.SassCompiler"),)
COMPRESS_CACHE_BACKEND = "default"
COMPRESS_OFFLINE = not (DEBUG or TESTING)
COMPRESS_OFFLINE_CONTEXT = "project.settings.staticfiles.offline_context"

LIBSASS_OUTPUT_STYLE = "compressed"
LIBSASS_ADDITIONAL_INCLUDE_PATHS = [
    "/app/told-common/told_common/static/bootstrap/scss/",  # For pipeline tests
    "/app/told_common/static/bootstrap/scss/",
]


def offline_context():
    extend_templates = ("told_common/layout.html", "ui/layout.html", "ui/print.html")
    for extend_template in extend_templates:
        yield {"STATIC_URL": STATIC_URL, "extend_template": extend_template}
