from os import getenv
from urllib.parse import urlparse

# pylint: disable=unused-import
from ._internal import (
    API_VERSION,
    AUTH_PASSWORD_VALIDATORS,
    AUTH_USER_MODEL,
    DEBUG,
    DEFAULT_AUTO_FIELD,
    INSTALLED_APPS,
    LANGUAGE_CODE,
    LOCALE_PATHS,  # RASTATIME 2026-10-02 - defined in _internal, was never re-exported
    MIDDLEWARE,
    REST_FRAMEWORK,
    ROOT_URLCONF,
    SPECTACULAR_SETTINGS,
    STATIC_URL,
    TEMPLATES,
    TIME_ZONE,
    USE_I18N,
    USE_TZ,
    WSGI_APPLICATION,
    setup_logger,
)
from ._schema import Config

LIBRETIME_LOG_FILEPATH = getenv("LIBRETIME_LOG_FILEPATH")
LIBRETIME_CONFIG_FILEPATH = getenv("LIBRETIME_CONFIG_FILEPATH")

CONFIG = Config(LIBRETIME_CONFIG_FILEPATH)  # type: ignore[arg-type, misc]

SECRET_KEY = CONFIG.general.secret_key

# Create an 'origin' (scheme://host[:port]) from the public_url.
# RASTATIME 2026-10-04: the upstream slice ``public_url[: -len(path)]``
# dropped one character too many when the path was just "/"
# ("http://192.168.1.164" -> "http://192.168.1.16" with the LAN address of the
# time) - the CORS origin never
# matched.  urlparse gives the origin without guessing.
_public_parts = urlparse(str(CONFIG.general.public_url))
public_url_origin = f"{_public_parts.scheme}://{_public_parts.netloc}"

# RASTATIME 2026-10-04 (go-live stage 1): the API is reached through the
# Apache proxy (ProxyPreserveHost -> the public host name or the LAN
# address) and directly on the loopback by the services.  Accept exactly
# those hosts instead of "*"; RASTATIME_API_EXTRA_HOSTS (comma separated)
# adds more, e.g. a second LAN name.
_public_host = urlparse(str(public_url_origin)).hostname or ""
_internal_host = urlparse(CONFIG.general.internal_base_url()).hostname or ""
ALLOWED_HOSTS = sorted(
    {
        host
        for host in [_public_host, _internal_host, "localhost", "127.0.0.1", "[::1]"]
        + [h.strip() for h in getenv("RASTATIME_API_EXTRA_HOSTS", "").split(",")]
        if host
    }
)

# Django's CSRF check compares the Origin header against these; the API
# answers to the public https origin through the proxy.  Apache sets
# X-Forwarded-Proto on the TLS virtual host, so request.is_secure() and
# the secure cookie flags follow the real scheme.
CSRF_TRUSTED_ORIGINS = sorted({str(public_url_origin)} | set(CONFIG.general.allowed_cors_origins))
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

LOGGING = setup_logger(LIBRETIME_LOG_FILEPATH)

# CORS
# https://github.com/adamchainz/django-cors-headers

CORS_ALLOWED_ORIGINS = [public_url_origin] + CONFIG.general.allowed_cors_origins

# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": CONFIG.database.host,
        "PORT": CONFIG.database.port,
        "NAME": CONFIG.database.name,
        "USER": CONFIG.database.user,
        "PASSWORD": CONFIG.database.password,
    }
}


# Email
# https://docs.djangoproject.com/en/4.2/topics/email/

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

EMAIL_HOST = CONFIG.email.host
EMAIL_PORT = CONFIG.email.port
EMAIL_HOST_USER = CONFIG.email.user
EMAIL_HOST_PASSWORD = CONFIG.email.password
EMAIL_USE_SSL = CONFIG.email.encryption == "ssl/tls"  # implicit
EMAIL_USE_TLS = CONFIG.email.encryption == "starttls"  # explicit
EMAIL_TIMEOUT = CONFIG.email.timeout
EMAIL_SSL_KEYFILE = CONFIG.email.key_file
EMAIL_SSL_CERTFILE = CONFIG.email.cert_file

DEFAULT_FROM_EMAIL = CONFIG.email.from_email
