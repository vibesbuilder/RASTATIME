"""
Initial migration: create ``rastatime_linein`` table.

T14.1 — Line-In domain model.  This is the first RASTATIME line-in
table, fully managed by Django (``managed = True``), separate from the
legacy LibreTime schema.

Schema
------
rastatime_linein
  id              BIGINT PRIMARY KEY  (auto-increment)
  linein_id       VARCHAR(36) UNIQUE  stable UUID from the domain model
  name            VARCHAR(128)        human-readable label
  device_id       VARCHAR(64)         stable ID of the audio input endpoint
  channel_mapping JSONB               list of 0-based int channel indices
  enabled         BOOLEAN             default TRUE
  description     TEXT                default ''
  priority        INT                 default 0
  created_at      TIMESTAMPTZ         auto-set on first save
  updated_at      TIMESTAMPTZ         auto-set on every save
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies: list = []

    operations = [
        migrations.CreateModel(
            name="LineIn",
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
                    "linein_id",
                    models.CharField(
                        db_index=True,
                        help_text=(
                            "UUID that uniquely identifies this line-in entity."
                        ),
                        max_length=36,
                        unique=True,
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text=(
                            "Human-readable display name "
                            "(e.g. 'Drum Kit', 'Interview Mic')."
                        ),
                        max_length=128,
                    ),
                ),
                (
                    "device_id",
                    models.CharField(
                        help_text=(
                            "Stable ID of the underlying Windows audio input "
                            "endpoint. Matches AudioDevice.stable_id from the "
                            "device manager."
                        ),
                        max_length=64,
                    ),
                ),
                (
                    "channel_mapping",
                    models.JSONField(
                        default=list,
                        help_text=(
                            "0-based channel indices to capture "
                            "(e.g. [0, 1] = stereo channels 1 & 2; "
                            "[0] = mono channel 1)."
                        ),
                    ),
                ),
                (
                    "enabled",
                    models.BooleanField(
                        default=True,
                        help_text=(
                            "Whether this line-in is active "
                            "and available for routing."
                        ),
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text=(
                            "Optional operator notes about this "
                            "line-in source."
                        ),
                    ),
                ),
                (
                    "priority",
                    models.IntegerField(
                        default=0,
                        help_text=(
                            "Routing priority. Higher integer wins when "
                            "multiple line-ins compete for the same playout slot."
                        ),
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Timestamp when this line-in was first saved.",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        help_text="Timestamp of the last update.",
                    ),
                ),
            ],
            options={
                "verbose_name": "Line-In Source",
                "verbose_name_plural": "Line-In Sources",
                "db_table": "rastatime_linein",
                "ordering": ["-priority", "name"],
                "managed": True,
            },
        ),
    ]
