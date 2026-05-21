from django.apps import AppConfig


class PreflightConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "libretime_api.preflight"
    verbose_name = "RASTATIME Pre-flight Warnings"
