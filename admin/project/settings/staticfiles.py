# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
STATIC_URL = "/admin/static/"
STATIC_ROOT = "/admin/static"

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

STATICFILES_DIRS = ["/app/told-common/told_common/static/"]
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "compressor.finders.CompressorFinder",
]
COMPRESS_PRECOMPILERS = (("text/x-scss", "django_libsass.SassCompiler"),)
LIBSASS_OUTPUT_STYLE = "compressed"
LIBSASS_ADDITIONAL_INCLUDE_PATHS = [
    "/app/told-common/told_common/static/bootstrap/scss/"
]
