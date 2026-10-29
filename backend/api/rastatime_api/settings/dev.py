"""
Development settings for RASTATIME.

Does NOT require a config file (RASTATIME_CONFIG_FILEPATH).

Database strategy:
  Default: SQLite (no server needed, starts immediately).
  PostgreSQL: set RASTATIME_USE_POSTGRES=true plus optional RASTATIME_DB_*
              overrides (host/port/name/user/password).

Never use this settings module in production.
"""

from os import getenv
from pathlib import Path

from ._internal import (
    API_VERSION,
    AUTH_PASSWORD_VALIDATORS,
    AUTH_USER_MODEL,
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

DEBUG = True

# RASTATIME feature flags
# Set to True on Windows to disable Linux-only runtime code paths.
# Checked by any module that wraps Liquidsoap, Celery, or gunicorn.
RASTATIME_WINDOWS_MODE = True

# Fixed dev-only secret — never use in production
SECRET_KEY = "rastatime-dev-insecure-secret-key-change-before-any-real-use"  # noqa: S105

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

LOGGING = setup_logger(None)

# CORS — allow everything in dev
CORS_ALLOW_ALL_ORIGINS = True

# Database
# SQLite is the default so the dev server starts without any external service.
# Set RASTATIME_USE_POSTGRES=true to switch to PostgreSQL instead.
_USE_POSTGRES = getenv("RASTATIME_USE_POSTGRES", "false").lower() == "true"

if _USE_POSTGRES:
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
else:
    # SQLite: file lives at backend/api/rastatime-dev.sqlite3 (git-ignored)
    _DEV_DB = Path(__file__).resolve().parent.parent.parent / "rastatime-dev.sqlite3"
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(_DEV_DB),
        }
    }

# Print emails to console instead of sending
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
