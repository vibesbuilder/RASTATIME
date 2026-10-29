from django.apps import AppConfig


class LegacyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "rastatime_api.legacy"
    verbose_name = "RASTATIME Legacy (LibreTime schema)"
