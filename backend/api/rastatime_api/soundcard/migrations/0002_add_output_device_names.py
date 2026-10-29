# RASTATIME 2026-05-14 — B.4 #4 UUID-Wechsel nach Reboot, output-side.
#
# Symmetric to rastatime_linein.device_name (linein migration 0004): the
# same Windows-USB endpoint-GUID instability that affects line-in
# capture also affects audio OUTPUT devices.  After a reboot the saved
# ``main_output_id`` may no longer resolve to an active output device
# even though the same physical speakers / headset / DAC is still
# plugged in — Windows just reassigned a fresh GUID under it.
#
# Store the OS-reported friendly name at save time so the playout's
# startup-resolver can fall back to a name-match in that case (same
# helper as line-in: WindowsAudioDeviceManager.find_device_by_id_or_name).
#
# Default ``""`` so existing rows don't need a backfill; the operator
# re-saving the Main Output picker once populates the column.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("soundcard", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="soundcardsettings",
            name="main_output_name",
            field=models.CharField(
                max_length=255,
                blank=True,
                default="",
                help_text=(
                    "OS-reported friendly name of the main audio output "
                    "endpoint at save time.  Used as a fallback when "
                    "main_output_id no longer resolves (USB endpoint-GUID "
                    "re-enumeration after reboot)."
                ),
            ),
        ),
        migrations.AddField(
            model_name="soundcardsettings",
            name="preview_output_name",
            field=models.CharField(
                max_length=255,
                blank=True,
                default="",
                help_text=(
                    "OS-reported friendly name of the preview / monitor "
                    "output endpoint at save time.  Used as a fallback "
                    "when preview_output_id no longer resolves."
                ),
            ),
        ),
    ]
