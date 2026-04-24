"""
Development settings for RASTATIME.

Does NOT require a config file (LIBRETIME_CONFIG_FILEPATH).
Uses PostgreSQL with defaults that match LibreTime's out-of-the-box values;
override any field via RASTATIME_DB_* environment variables.

Never use this settings module in production.
"""

from os import getenv

from ._internal import (
    API_VERSION,
    AUTH_PASSWORD_VALIDATORS,
    AUTH_USER_MODEL,
    DEFAULT_AUTO_FIELD,
    INSTALLED_APPS,
    MIDDLEWARE,
    REST_FRAMEWORK,
    ROOT_URLCONF,
    SPECTACULAR_SETTINGS,
    STATIC_URL,
    TEMPLATES,
    WSGI_APPLICATION,
    setup_logger,
)

DEBUG = True

# Fixed dev-only secret — never use in production
SECRET_KEY = "rastatime-dev-insecure-secret-key-change-before-any-real-use"  # noqa: S105

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

LOGGING = setup_logger(None)

# CORS — allow everything in dev
CORS_ALLOW_ALL_ORIGINS = True

# Database — PostgreSQL with LibreTime defaults; override via env vars
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": getenv("RASTATIME_DB_HOST", "localhost"),
        "PORT": getenv("RASTATIME_DB_PORT", "5432"),
        "NAME": getenv("RASTATIME_DB_NAME", "libretime"),
        "USER": getenv("RASTATIME_DB_USER", "libretime"),
        "PASSWORD": getenv("RASTATIME_DB_PASSWORD", "libretime"),
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Print emails to console instead of sending
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
