"""
Initial migration: create ``rastatime_soundcard_settings`` table.

This is the first RASTATIME-native table — fully managed by Django
(``managed = True``), separate from the legacy LibreTime schema that
lives in the ``libretime_api.legacy`` app.

Schema
------
rastatime_soundcard_settings
  id                 BIGINT PRIMARY KEY  (singleton: always row 1)
  main_output_id     VARCHAR(64)         stable ID of main output or ''
  preview_output_id  VARCHAR(64)         stable ID of preview output or ''
  line_in_device_ids JSONB               ordered list of line-in stable IDs
  updated_at         TIMESTAMPTZ         auto-updated on every save
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies: list = []

    operations = [
        migrations.CreateModel(
            name="SoundcardSettings",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "main_output_id",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text=(
                            "Stable ID of the primary audio output device. "
                            "Empty means 'use OS default'."
                        ),
                        max_length=64,
                    ),
                ),
                (
                    "preview_output_id",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text=(
                            "Stable ID of the optional monitor / cue output. "
                            "Empty means no preview output configured."
                        ),
                        max_length=64,
                    ),
                ),
                (
                    "line_in_device_ids",
                    models.JSONField(
                        default=list,
                        help_text=(
                            "Ordered list of stable IDs of configured "
                            "line-in input devices."
                        ),
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        help_text="Timestamp of the last settings save.",
                    ),
                ),
            ],
            options={
                "verbose_name": "Soundcard Settings",
                "verbose_name_plural": "Soundcard Settings",
                "db_table": "rastatime_soundcard_settings",
                "managed": True,
            },
        ),
    ]
