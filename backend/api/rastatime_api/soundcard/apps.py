import logging
import sys

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class SoundcardConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "rastatime_api.soundcard"
    verbose_name = "RASTATIME Soundcard Settings"

    def ready(self) -> None:
        """
        Wire the process-level AudioDeviceManager singleton at startup
        so the ``/api/v2/audio/devices`` endpoint returns real device
        lists instead of empty arrays.

        Skipped on non-Windows hosts (the WindowsAudioDeviceManager
        reads HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\
        MMDevices\\Audio via ``winreg``, which is Windows-only stdlib).

        Skipped when running under ``manage.py migrate`` / ``makemigrations``
        / ``shell`` / ``test`` etc. — wiring a live registry-reading
        manager during a one-shot management command is unnecessary
        overhead and would log a misleading "ready" line in non-
        serving contexts.  We detect that via ``RUN_MAIN`` (set by
        Django's runserver autoreloader for the actual server process)
        and by inspecting ``sys.argv[1]``.
        """
        if sys.platform != "win32":
            logger.debug("Soundcard manager: skipping (non-Windows host)")
            return

        # Skip for the autoreloader's parent process and for transient
        # management commands.  The autoreloader child sets RUN_MAIN=true
        # before importing the app code, so we wire there.
        skip_commands = {
            "migrate",
            "makemigrations",
            "showmigrations",
            "sqlmigrate",
            "shell",
            "test",
            "collectstatic",
            "createsuperuser",
            "check",
            "diffsettings",
            "dumpdata",
            "loaddata",
        }
        argv1 = sys.argv[1] if len(sys.argv) > 1 else ""
        if argv1 in skip_commands:
            logger.debug(
                "Soundcard manager: skipping for management command %r",
                argv1,
            )
            return

        try:
            from audio.soundcard import connect_device_manager
            from audio.soundcard.windows_manager import WindowsAudioDeviceManager
        except ImportError as exc:
            logger.warning(
                "Soundcard manager: audio.soundcard not importable — "
                "/api/v2/audio/devices will return empty lists. %s",
                exc,
            )
            return

        try:
            mgr = WindowsAudioDeviceManager()
            connect_device_manager(mgr)
            # Probe once so the operator can see in the log how many
            # devices the Windows registry reports — useful when the
            # endpoint mysteriously returns "no devices".
            n_out = len(mgr.list_outputs())
            n_in = len(mgr.list_inputs())
            logger.info(
                "Soundcard manager registered (WindowsAudioDeviceManager): "
                "%d output(s), %d input(s) visible",
                n_out,
                n_in,
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning(
                "Soundcard manager: WindowsAudioDeviceManager init failed — "
                "/api/v2/audio/devices will return empty lists. %s",
                exc,
            )
