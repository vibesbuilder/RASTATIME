# RASTATIME 2026-05-14 — B.4 #4 UUID-Wechsel nach Reboot.
#
# Windows USB-audio endpoint GUIDs (saved as ``device_id``) are not
# guaranteed stable across reboots — observed empirically with a Jabra
# USB headset.  Driver/port re-enumeration can reassign the GUID, which
# leaves the playout's preflight check warning ``linein_device_unavailable``
# even though the physical device is still plugged in.
#
# To recover automatically, we now also persist the OS-reported friendly
# name (e.g. ``"Mikrofon (Jabra Speak 410 USB)"``) at save time, so the
# resolver can fall back to a name-match when the saved GUID no longer
# resolves.  Default ``""`` so existing rows don't need a backfill — the
# fallback simply has nothing to match against until the operator
# re-saves the device picker once.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("linein", "0003_linein_length"),
    ]

    operations = [
        migrations.AddField(
            model_name="linein",
            name="device_name",
            field=models.CharField(
                max_length=255,
                blank=True,
                default="",
                help_text=(
                    "OS-reported friendly name of the audio input endpoint at "
                    "save time.  Used as a fallback when device_id no longer "
                    "resolves (USB endpoint-GUID re-enumeration after reboot)."
                ),
            ),
        ),
    ]
