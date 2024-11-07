import os
from typing import Callable

from django.urls import reverse_lazy
from told_common.util import strtobool

LOGIN_SESSION_DATA_KEY = "saml_user"
LOGIN_PROVIDER_CLASS = os.environ.get("LOGIN_PROVIDER_CLASS") or None
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = reverse_lazy("logged-out")  # Where to go after logout
LOGIN_URL = "/login/"
LOGIN_NAMESPACE = "login"

# Session keys to delete on logout
LOGIN_SESSION_KEYS = ["user", "access_token", "refresh_token"]
LOGIN_TIMEOUT_URL = reverse_lazy("login-timeout")
LOGIN_REPEATED_URL = reverse_lazy("login-repeat")
LOGIN_ASSURANCE_LEVEL_URL = reverse_lazy("login-assurance-level")
LOGIN_WHITELISTED_URLS = [
    "/favicon.ico",
    "/_ht/",
    LOGIN_URL,
    LOGIN_TIMEOUT_URL,
    LOGIN_REPEATED_URL,
    LOGOUT_REDIRECT_URL,
    LOGIN_ASSURANCE_LEVEL_URL,
]
MITID_TEST_ENABLED = bool(strtobool(os.environ.get("MITID_TEST_ENABLED", "False")))
SESSION_EXPIRE_SECONDS = int(os.environ.get("SESSION_EXPIRE_SECONDS") or 1800)
LOGIN_BYPASS_ENABLED = bool(strtobool(os.environ.get("LOGIN_BYPASS_ENABLED", "False")))

POPULATE_DUMMY_SESSION: bool | Callable
if LOGIN_BYPASS_ENABLED:

    def POPULATE_DUMMY_SESSION():  # noqa
        return {
            "cpr": "0111111111",
            "cvr": "12345678",
            "firstname": "Dummybruger",
            "lastname": "Testersen",
            "email": "",
        }

else:
    POPULATE_DUMMY_SESSION = False


CACHES: dict = {
    "default": {
        "BACKEND": "django.core.cache.backends.memcached.PyMemcacheCache",
        "LOCATION": os.environ["CACHE_ENDPOINT"],
    },
    "saml": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "saml_cache",
        "TIMEOUT": 7200,
    },
}


SAML = {
    "enabled": bool(strtobool(os.environ.get("SAML_ENABLED", "False"))),
    "debug": 1,
    "entityid": os.environ.get("SAML_SP_ENTITY_ID"),
    "idp_entity_id": os.environ.get("SAML_IDP_ENTITY_ID"),
    "name": os.environ.get("SAML_SP_NAME") or "Toldbehandling",
    "description": os.environ.get("SAML_SP_DESCRIPTION") or "Toldregistrering",
    "verify_ssl_cert": False,
    "metadata_remote": os.environ.get("SAML_IDP_METADATA"),
    # Til metadata-fetch mellem containere
    "metadata_remote_container": os.environ.get("SAML_IDP_METADATA_CONTAINER"),
    "metadata": {"local": ["/var/cache/told/idp_metadata.xml"]},  # IdP Metadata
    "service": {
        "sp": {
            "name": os.environ.get("SAML_SP_NAME") or "Told",
            "hide_assertion_consumer_service": False,
            "endpoints": {
                "assertion_consumer_service": [
                    (
                        os.environ.get("SAML_SP_LOGIN_CALLBACK_URI"),
                        "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                    )
                ],
                "single_logout_service": [
                    (
                        os.environ.get("SAML_SP_LOGOUT_CALLBACK_URI"),
                        "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                    ),
                ],
            },
            "required_attributes": [
                "https://data.gov.dk/model/core/eid/professional/orgName",
                "https://data.gov.dk/model/core/specVersion",
                "https://data.gov.dk/concept/core/nsis/loa",
                "https://data.gov.dk/model/core/eid/cprNumber",
                "https://data.gov.dk/model/core/eid/firstName",
                "https://data.gov.dk/model/core/eid/lastName",
                "https://data.gov.dk/model/core/eid/email",
            ],
            "optional_attributes": [
                "https://data.gov.dk/model/core/eid/professional/cvr",
            ],
            "name_id_format": [
                "urn:oasis:names:tc:SAML:2.0:nameid-format:persistent",
            ],
            "signing_algorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
            "authn_requests_signed": True,
            "want_assertions_signed": True,
            "want_response_signed": False,
            "allow_unsolicited": True,
            "logout_responses_signed": True,
        }
    },
    "key_file": os.environ.get("SAML_SP_KEY"),
    "cert_file": os.environ.get("SAML_SP_CERTIFICATE"),
    "encryption_keypairs": [
        {
            "key_file": os.environ.get("SAML_SP_KEY"),
            "cert_file": os.environ.get("SAML_SP_CERTIFICATE"),
        },
    ],
    "xmlsec_binary": "/usr/bin/xmlsec1",
    "delete_tmpfiles": True,
    "organization": {
        "name": [("Skattestyrelsen", "da")],
        "display_name": ["Skattestyrelsen"],
        "url": [("https://nanoq.gl", "da")],
    },
    "contact_person": [
        {
            "given_name": os.environ["SAML_CONTACT_TECHNICAL_NAME"],
            "email_address": os.environ["SAML_CONTACT_TECHNICAL_EMAIL"],
            "type": "technical",
        },
        {
            "given_name": os.environ["SAML_CONTACT_SUPPORT_NAME"],
            "email_address": os.environ["SAML_CONTACT_SUPPORT_EMAIL"],
            "type": "support",
        },
    ],
    "preferred_binding": {
        "attribute_consuming_service": [
            "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
        ],
        "single_logout_service": [
            "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
        ],
    },
}
