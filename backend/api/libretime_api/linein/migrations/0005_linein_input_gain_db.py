# RASTATIME 2026-10-02 - per-line-in static input gain (dB).
#
# The line-in counterpart of cc_webstream.input_gain_db: the playout
# applies it on air as a linear amplify factor in Liquidsoap
# (``var.set linein.gain``), so a studio feed can be trimmed to the
# station loudness without touching the mixer.  Default 0.0 = unchanged,
# so existing rows need no backfill.
#
# Django 4.2 drops the column default again right after AddField.  On
# PostgreSQL we put it back: an API process still running the previous
# code (between this migration and its restart, or after a rollback)
# inserts rows without the column and would otherwise hit NOT NULL.

from django.db import migrations, models


def _keep_db_default(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(
            'ALTER TABLE "rastatime_linein" '
            'ALTER COLUMN "input_gain_db" SET DEFAULT 0.0'
        )


def _drop_db_default(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(
            'ALTER TABLE "rastatime_linein" '
            'ALTER COLUMN "input_gain_db" DROP DEFAULT'
        )


class Migration(migrations.Migration):

    dependencies = [
        ("linein", "0004_linein_device_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="linein",
            name="input_gain_db",
            field=models.FloatField(
                default=0.0,
                help_text=(
                    "Static input gain in dB applied on air (-20 to +20, "
                    "0 = unchanged)."
                ),
            ),
        ),
        migrations.RunPython(_keep_db_default, _drop_db_default),
    ]
