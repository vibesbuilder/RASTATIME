"""
RASTATIME-PLAYOUT — Liquidsoap playout entry point.

Replaces the LibreTime playout daemon with a Windows-native scheduler
that:

  1. Polls RASTATIME-API (health gate) before entering the main loop.
  2. Reads Icecast output stream settings from ``cc_pref`` via Django ORM
     and renders rastatime.liq for the RASTATIME-LIQUIDSOAP service.
  3. Connects the LiquidsoapPlayoutEngine to that service over telnet
     (Liquidsoap owns local playback, the Icecast outputs, the DJ harbors
     and the recording).
  4. Polls the schedule API every POLL_INTERVAL seconds and arms per-item
     timers to start/stop playback at the scheduled wall-clock times.

Health gate (required by NSSM install script and SERVICE_TOPOLOGY §2.3):
  ``http://127.0.0.1:8765/health`` must return HTTP 200 within
  RASTATIME_API_HEALTH_TIMEOUT seconds (default 120 s).

Environment variables (all optional — defaults match the standard install):
  RASTATIME_API_HEALTH_URL     : API health check URL
  RASTATIME_API_HEALTH_TIMEOUT : seconds to wait for the API (default 120)
  RASTATIME_SCHEDULE_POLL      : schedule refresh interval in seconds (default 120)
  LIBRETIME_CONFIG_FILEPATH    : path to libretime.conf
  DJANGO_SETTINGS_MODULE       : Django settings module
  RASTATIME_PLAYOUT_ENGINE     : "liquidsoap" (the only engine since 2026-09-10;
                                 any other value aborts startup)
  RASTATIME_LIQUIDSOAP_HOST    : Liquidsoap telnet host (default 127.0.0.1)
  RASTATIME_LIQUIDSOAP_PORT    : Liquidsoap telnet port (default 1234)
  RASTATIME_LIQUIDSOAP_CONFIG_PATH
                               : where to render rastatime.liq
                                 (default C:/Tools/liquidsoap/rastatime.liq)
  RASTATIME_LIQUIDSOAP_LOG_PATH
                               : the rendered log.file.path (default
                                 C:/rastatime/logs/liquidsoap.log).  The
                                 file sink is OFF since 2026-09-18 (stdout
                                 + NSSM rotation is the one sink); the
                                 path only matters when an operator flips
                                 log.file.set(true) for a debug session.
  RASTATIME_LIQUIDSOAP_CROSSFADE_SECONDS
                               : FALLBACK crossfade duration for the .liq
                                 (since 2026-09-04 the primary source is
                                 Settings -> General "Default Crossfade
                                 Duration"; this env var is used only when
                                 that cc_pref key is missing/invalid;
                                 default 2.0; 0 = hard cut between tracks
                                 and "ducking" at input switches)

Invoked as:  python -m libretime_playout
"""

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, NamedTuple
from urllib.parse import urlparse

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Runtime configuration (from environment)
# ---------------------------------------------------------------------------
_HEALTH_URL = os.environ.get(
    "RASTATIME_API_HEALTH_URL", "http://127.0.0.1:8765/health"
)
_HEALTH_TIMEOUT = int(os.environ.get("RASTATIME_API_HEALTH_TIMEOUT", "120"))
_POLL_INTERVAL = int(os.environ.get("RASTATIME_SCHEDULE_POLL", "120"))
_CONFIG_FILE = os.environ.get(
    "LIBRETIME_CONFIG_FILEPATH", r"C:\rastatime\config\libretime.conf"
)

# RASTATIME_API_URL lets the playout service connect to the Django API
# on its direct local port (8765) independently of config.general.public_url,
# which may point to a reverse proxy or the PHP frontend at a different port.
# Derived from the health gate URL by stripping "/health".
_API_URL_DEFAULT = _HEALTH_URL.removesuffix("/health").removesuffix("/")


# ---------------------------------------------------------------------------
# Health gate
# ---------------------------------------------------------------------------

def _wait_for_api(url: str = _HEALTH_URL, timeout: int = _HEALTH_TIMEOUT) -> bool:
    """
    Poll ``url`` with exponential backoff until HTTP 200 or ``timeout`` seconds.

    Returns True on success, False on timeout (playout continues anyway, but
    the first schedule fetch may also fail).
    """
    logger.info("Health gate: polling %s (timeout %ds) …", url, timeout)
    deadline = time.monotonic() + timeout
    delay = 2.0

    while time.monotonic() < deadline:
        try:
            resp = requests.get(url, timeout=4)
            if resp.status_code == 200:
                logger.info("Health gate: API healthy (HTTP 200).")
                return True
            logger.debug("Health gate: HTTP %d — retrying …", resp.status_code)
        except requests.exceptions.RequestException as exc:
            logger.debug("Health gate: %s — retrying …", exc)

        sleep_for = min(delay, deadline - time.monotonic())
        if sleep_for > 0:
            time.sleep(sleep_for)
        delay = min(delay * 2.0, 30.0)

    logger.warning(
        "Health gate: API did not respond within %ds. "
        "Playout will attempt to start anyway.",
        timeout,
    )
    return False


# ---------------------------------------------------------------------------
# Django bootstrap (for reading cc_pref stream settings)
# ---------------------------------------------------------------------------

def _setup_django() -> bool:
    """Bootstrap Django ORM so we can query cc_pref."""
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE", "libretime_api.settings.prod"
    )
    # Django's prod.py reads LIBRETIME_CONFIG_FILEPATH from the environment
    # when building its Config.  Make sure it resolves to the same file we
    # loaded above, even if the env var wasn't set by the NSSM service wrapper.
    os.environ.setdefault("LIBRETIME_CONFIG_FILEPATH", _CONFIG_FILE)
    try:
        import django  # type: ignore[import-untyped]
        django.setup()
        logger.debug("Django ORM ready.")
        return True
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning(
            "Django setup failed — stream output settings will not be read: %s", exc
        )
        return False


# ---------------------------------------------------------------------------
# Read Icecast stream outputs from cc_pref
# ---------------------------------------------------------------------------

def _resolve_crossfade_seconds() -> float:
    """
    RASTATIME 2026-09-04 - the house crossfade duration.  Primary source
    is Settings -> General "Default Crossfade Duration (s)" (cc_pref
    ``default_crossfade_duration``); the env var
    RASTATIME_LIQUIDSOAP_CROSSFADE_SECONDS is the fallback for a
    missing/invalid key.  Since 2026-09-27 this is the TRACK crossfade
    (between two tracks of one show); input switches and show boundaries
    follow :func:`_resolve_show_crossfade_seconds`.  A UI change is
    applied by the settings restart (fingerprint) or the next PLAYOUT +
    LIQUIDSOAP restart.
    """
    try:
        crossfade = float(
            os.environ.get(
                "RASTATIME_LIQUIDSOAP_CROSSFADE_SECONDS",
                str(_LIQUIDSOAP_DEFAULT_CROSSFADE),
            )
        )
    except ValueError as exc:
        logger.critical(
            "RASTATIME_LIQUIDSOAP_CROSSFADE_SECONDS must be a float: %s", exc,
        )
        sys.exit(1)
    pref_crossfade = _read_pref_crossfade_duration()
    if pref_crossfade is not None:
        logger.info(
            "Crossfade duration %.2f s from Settings -> General "
            "(cc_pref default_crossfade_duration)%s",
            pref_crossfade, " - input switches use ducking" if pref_crossfade == 0 else "",
        )
        return pref_crossfade
    logger.info(
        "Crossfade duration %.2f s from env/default (cc_pref key missing "
        "or invalid)", crossfade,
    )
    return crossfade


def _read_pref_crossfade_duration() -> Optional[float]:
    """
    RASTATIME 2026-09-04 - ``cc_pref.default_crossfade_duration`` (the
    Settings -> General field "Default Track Crossfade Duration") as a
    float, or None when the key is missing, empty, negative or not a
    number -- the caller then keeps the env/default value.  Same ORM path
    as :func:`_read_stream_outputs`.
    """
    return _read_pref_seconds("default_crossfade_duration")


def _resolve_loudness_limiter() -> Tuple[str, Optional[float]]:
    """
    RASTATIME 2026-09-28 - Settings -> Streams -> Loudness Normalization:
    ``(mode, ceiling)`` where ``ceiling`` is the true-peak ceiling (dBTP)
    when the mode is EBU R128 and None otherwise (no limiter rendered).
    """
    try:
        from libretime_api.core.models import Preference  # type: ignore[import-untyped]
        prefs = Preference.get_stream_preferences()
        mode = str(getattr(prefs, "loudness_mode", "off") or "off")
        ceiling = float(getattr(prefs, "loudness_true_peak_dbtp", -1.0))
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("Could not read the loudness settings from DB: %s", exc)
        return "off", None
    return mode, (ceiling if mode == "r128" else None)


def _resolve_stereotool():
    """
    RASTATIME 2026-10-02 - Settings -> Streams -> Output Processing: the
    Stereo Tool settings from cc_pref, read through the ORM (the licence
    key never travels over the HTTP API).  Off when unreadable.
    """
    from libretime_playout.liquidsoap_config import (  # noqa: PLC0415
        StereoToolSettings, stereotool_settings_from_prefs,
    )
    try:
        from libretime_api.core.models import Preference  # type: ignore[import-untyped]
        entries = dict(
            Preference.site.filter(key__startswith="stereotool_").values_list("key", "value")
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("Could not read the Stereo Tool settings from DB: %s", exc)
        return StereoToolSettings()
    return stereotool_settings_from_prefs(entries)


def _stereotool_fingerprint(settings) -> list:
    """The settings as the fingerprint sees them - the key only as a hash."""
    import hashlib  # noqa: PLC0415
    key = hashlib.sha1(settings.license_key.encode("utf-8")).hexdigest()[:12] if settings.license_key else ""  # noqa: S324
    return [settings.enabled, settings.library_file, settings.preset_file, key]


def _read_pref_seconds(key: str) -> Optional[float]:
    try:
        from libretime_api.core.models import Preference  # type: ignore[import-untyped]
        raw = dict(Preference.site.values_list("key", "value")).get(key)
        if raw is None or str(raw).strip() == "":
            return None
        value = float(str(raw).strip())
        if value < 0:
            logger.warning("cc_pref %s=%r is negative - ignored", key, raw)
            return None
        return value
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("Could not read %s from DB: %s", key, exc)
        return None


def _build_live_text_writer():
    """RASTATIME 2026-09-28 - the Live Text Info writer (Settings -> General)."""
    from libretime_playout.live_text import (  # noqa: PLC0415
        LiveTextWriter,
        default_web_dir,
        read_live_text_config_from_db,
    )

    writer = LiveTextWriter(read_live_text_config_from_db, web_dir=default_web_dir())
    cfg = read_live_text_config_from_db()
    if cfg is not None and cfg.enabled:
        logger.info(
            "Live Text Info: enabled (format %d, web %s, file %r, ftp %s) -> %s",
            cfg.label_format, "on" if cfg.web_enabled else "off", cfg.file_path or "-",
            "on" if cfg.ftp.enabled else "off", writer.web_file,
        )
    else:
        logger.info("Live Text Info: disabled (Settings -> General).")
    return writer


def _build_tunein_pusher():
    """RASTATIME 2026-09-28 - the TuneIn pusher (Settings -> TuneIn Settings)."""
    from libretime_playout.tunein import (  # noqa: PLC0415
        TuneInPusher,
        read_tunein_config_from_db,
    )

    pusher = TuneInPusher(read_tunein_config_from_db)
    cfg = read_tunein_config_from_db()
    if cfg is not None and cfg.enabled:
        logger.info(
            "TuneIn now-playing pushes: enabled for station %s (%s).",
            cfg.station_id or "?", "credentials complete" if cfg.complete() else "credentials INCOMPLETE",
        )
    else:
        logger.info("TuneIn now-playing pushes: disabled (Settings -> TuneIn Settings).")
    return pusher


def _resolve_dj_fade_seconds() -> float:
    """
    RASTATIME 2026-09-28 - Settings -> Streams "Switch Transition Fade (s)"
    (cc_pref ``default_transition_fade``, start value 1 s); env
    RASTATIME_LIQUIDSOAP_DJ_FADE_SECONDS is the fallback for a missing key.
    Shapes the DJ hand-over in the bus: a connecting DJ is on air at once
    while the programme fades out under it over this many seconds; when
    the DJ hands back, the DJ fades out over the same time and the
    programme is at full level at once.  Until 2026-09-28 the field had
    no effect (both DJ arms were a 50 ms hand-over).
    """
    try:
        fallback = float(
            os.environ.get(
                "RASTATIME_LIQUIDSOAP_DJ_FADE_SECONDS",
                str(_LIQUIDSOAP_DEFAULT_DJ_FADE),
            )
        )
    except ValueError as exc:
        logger.critical("RASTATIME_LIQUIDSOAP_DJ_FADE_SECONDS must be a float: %s", exc)
        sys.exit(1)
    pref = _read_pref_seconds("default_transition_fade")
    if pref is not None:
        logger.info(
            "DJ hand-over fade %.2f s from Settings -> Streams "
            "(cc_pref default_transition_fade)", pref,
        )
        return pref
    logger.info(
        "DJ hand-over fade %.2f s from env/default (cc_pref key missing or invalid)",
        fallback,
    )
    return fallback


def _resolve_show_crossfade_seconds() -> float:
    """
    RASTATIME 2026-09-27 - Settings -> General "Default Show Crossfade
    Duration (s)" (cc_pref ``default_show_crossfade_duration``, start
    value 1 s); env RASTATIME_LIQUIDSOAP_SHOW_CROSSFADE_SECONDS is the
    fallback for a missing key.  At a show boundary the old show's last
    track fades out over this many seconds while the new show's first
    track starts at full level at once; every input switch (track <->
    webstream <-> line-in) uses the same shape and value.
    """
    try:
        fallback = float(
            os.environ.get(
                "RASTATIME_LIQUIDSOAP_SHOW_CROSSFADE_SECONDS",
                str(_LIQUIDSOAP_DEFAULT_SHOW_CROSSFADE),
            )
        )
    except ValueError as exc:
        logger.critical(
            "RASTATIME_LIQUIDSOAP_SHOW_CROSSFADE_SECONDS must be a float: %s", exc,
        )
        sys.exit(1)
    pref = _read_pref_seconds("default_show_crossfade_duration")
    if pref is not None:
        logger.info(
            "Show crossfade duration %.2f s from Settings -> General "
            "(cc_pref default_show_crossfade_duration)", pref,
        )
        return pref
    logger.info(
        "Show crossfade duration %.2f s from env/default (cc_pref key missing "
        "or invalid)", fallback,
    )
    return fallback


def _read_stream_outputs() -> List[Dict]:
    """
    Return a list of enabled stream output dicts from ``cc_pref``.

    Each dict contains: host, port, mount, pass, user, type, bitrate,
    channels, enable ("true").  Disabled streams are excluded.
    """
    try:
        from libretime_api.core.models import Preference  # type: ignore[import-untyped]

        all_entries: Dict[str, str] = dict(
            Preference.site.values_list("key", "value")
        )
        outputs: List[Dict] = []
        for n in range(1, 4):
            raw = all_entries.get(f"stream_output_{n}")
            if not raw:
                continue
            try:
                data = json.loads(raw)
                if str(data.get("enable", "")).lower() == "true":
                    outputs.append(data)
                    logger.debug("Found enabled stream output %d: %s", n, data)
            except (json.JSONDecodeError, AttributeError) as exc:
                logger.warning("Could not parse stream_output_%d: %s", n, exc)
        return outputs

    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("Could not read stream outputs from DB: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Load libretime.conf (for API base_url and api_key)
# ---------------------------------------------------------------------------

def _load_config():
    """Load Config from libretime.conf; exit(1) if the file is missing."""
    from libretime_playout.config import Config  # type: ignore[import-untyped]

    config_path = Path(_CONFIG_FILE)
    if not config_path.exists():
        logger.critical(
            "Config file not found: %s\n"
            "Set LIBRETIME_CONFIG_FILEPATH or create C:\\rastatime\\config\\libretime.conf",
            _CONFIG_FILE,
        )
        sys.exit(1)

    try:
        cfg = Config(config_path)
        logger.info("Config loaded from %s", config_path)
        return cfg
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.critical("Failed to parse config %s: %s", config_path, exc)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Liquidsoap engine — render rastatime.liq at startup (Phase C7)
# ---------------------------------------------------------------------------

_LIQUIDSOAP_DEFAULT_CONFIG_PATH = "C:/Tools/liquidsoap/rastatime.liq"
_LIQUIDSOAP_DEFAULT_LOG_PATH = "C:/rastatime/logs/liquidsoap.log"
# RASTATIME 2026-09-09 - standby source for the Icecast fallback mounts
_LIQUIDSOAP_DEFAULT_STANDBY_PATH = "C:/Tools/liquidsoap/standby.liq"
_ICECAST_DEFAULT_CONFIG_PATH = "C:/rastatime/config/icecast.xml"
_LIQUIDSOAP_DEFAULT_CROSSFADE = 2.0
# RASTATIME 2026-09-27 - Default Show Crossfade Duration (Settings -> General)
_LIQUIDSOAP_DEFAULT_SHOW_CROSSFADE = 1.0
# RASTATIME 2026-09-28 - Settings -> Streams "Switch Transition Fade" (DJ hand-over)
_LIQUIDSOAP_DEFAULT_DJ_FADE = 1.0


def _read_harbor_credentials() -> tuple:
    """
    Read ``stream.harbor.main_password`` / ``show_password`` from
    libretime.conf.  Returns (main_password, show_password) — either
    field is an empty string if missing.  Same direct-YAML-read
    pattern as :func:`_read_config_yaml`.

    These passwords drive Phase-C4 ``input.harbor`` in rastatime.liq:
    when set, the renderer emits the DJ-Master / DJ-Show source blocks
    + the switch operator; when both unset, the bus stays on the
    scheduled queue (= C3 behaviour).
    """
    try:
        import yaml  # noqa: PLC0415

        with open(_CONFIG_FILE, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
        section = (raw.get("stream") or {}).get("harbor") or {}
        return (
            str(section.get("main_password") or ""),
            str(section.get("show_password") or ""),
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning(
            "Could not read stream.harbor.* from %s: %s",
            _CONFIG_FILE, exc,
        )
        return ("", "")


def _read_config_yaml() -> dict:
    """libretime.conf as a dict ({} when unreadable; the caller logs)."""
    import yaml  # noqa: PLC0415

    with open(_CONFIG_FILE, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _local_icecast_source_credentials(stream_outputs) -> Optional[Tuple[str, str]]:
    """Source user/password of the local Icecast, taken from the first
    enabled Icecast stream output that points at this machine (Settings ->
    Streams).  The Line-In capture pushes its ``/linein-capture`` mount with
    these credentials, so rotating the Icecast source password in the UI
    and icecast.xml is enough (RASTATIME 2026-10-04, go-live stage 0).
    None when no such output exists (the capture keeps its module default).
    """
    local_hosts = {"localhost", "127.0.0.1", "::1", ""}
    candidates = []
    for out in stream_outputs or []:
        if str(out.get("output", "icecast")).lower() != "icecast":
            continue
        if str(out.get("enable", "true")).lower() not in ("true", "1", "yes"):
            continue
        if str(out.get("host", "")).strip().lower() not in local_hosts:
            continue
        password = str(out.get("pass", "") or "")
        if not password:
            continue
        candidates.append((str(out.get("port", "")), str(out.get("user", "") or "source"), password))
    if not candidates:
        return None
    # prefer the output on the capture's own port (8000), else any local one
    candidates.sort(key=lambda c: 0 if c[0] == "8000" else 1)
    return candidates[0][1], candidates[0][2]


def _read_harbor_inputs(stream_outputs) -> Tuple[int, str, int, str]:
    """
    RASTATIME 2026-09-10 - the harbor ports and mounts come from
    ``stream.inputs.main`` / ``stream.inputs.show`` in libretime.conf,
    exactly what Settings -> Streams shows as Master/Show Source Port
    and Mount ("UI wird zur Wahrheit").  Returns
    ``(main_port, main_mount, show_port, show_mount)``.

    Safety net: a port that an Icecast output already uses (or 8000)
    cannot host the harbor - Liquidsoap would fail to bind and die;
    such a value is replaced by the default with a loud warning.
    """
    from libretime_playout.liquidsoap_config import (  # noqa: PLC0415
        DEFAULT_HARBOR_MAIN_MOUNT, DEFAULT_HARBOR_PORT, DEFAULT_HARBOR_SHOW_MOUNT,
    )
    taken = {8000}
    for out in stream_outputs or []:
        try:
            taken.add(int(out.get("port")))
        except (TypeError, ValueError, AttributeError):
            pass
    try:
        inputs = (_read_config_yaml().get("stream") or {}).get("inputs") or {}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("Could not read stream.inputs from %s: %s", _CONFIG_FILE, exc)
        inputs = {}

    def one(name, default_mount):
        section = inputs.get(name) or {}
        mount = str(section.get("mount") or default_mount).strip().strip("/") or default_mount
        try:
            port = int(section.get("port") or DEFAULT_HARBOR_PORT)
        except (TypeError, ValueError):
            port = DEFAULT_HARBOR_PORT
        if port in taken:
            logger.warning(
                "stream.inputs.%s.port=%d is an Icecast port - the Liquidsoap harbor "
                "cannot bind it; using %d instead.  Set it to %d in libretime.conf so "
                "Settings -> Streams shows what DJs must use.",
                name, port, DEFAULT_HARBOR_PORT, DEFAULT_HARBOR_PORT,
            )
            port = DEFAULT_HARBOR_PORT
        return port, mount

    main_port, main_mount = one("main", DEFAULT_HARBOR_MAIN_MOUNT)
    show_port, show_mount = one("show", DEFAULT_HARBOR_SHOW_MOUNT)
    return main_port, main_mount, show_port, show_mount


DJ_AUTH_WEB_URL_ENV = "RASTATIME_DJ_AUTH_WEB_URL"


def _dj_auth_web_url() -> str:
    """Base URL of the legacy web application that answers
    check-live-stream-auth: ``RASTATIME_DJ_AUTH_WEB_URL``, else the
    internal address (``RASTATIME_INTERNAL_URL`` / ``general.internal_url``
    / ``http://127.0.0.1`` plus the path of ``general.public_url``) -
    RASTATIME 2026-10-04, go-live stage 1: the check never leaves this
    machine, whatever the public https address is."""
    override = os.environ.get(DJ_AUTH_WEB_URL_ENV, "").strip()
    if override:
        return override
    internal = os.environ.get("RASTATIME_INTERNAL_URL", "").strip()
    if internal:
        return internal.rstrip("/")
    try:
        general = _read_config_yaml().get("general") or {}
        configured = str(general.get("internal_url") or "").strip()
        if configured:
            return configured.rstrip("/")
        public = str(general.get("public_url") or "").strip()
        path = urlparse(public).path.rstrip("/") if public else ""
        return "http://127.0.0.1" + path
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("Could not read general.* from %s: %s", _CONFIG_FILE, exc)
        return "http://127.0.0.1"


def _resolve_local_output_device() -> Tuple[Optional[int], str, str, Optional[str]]:
    """
    Resolve the operator's **Main Output** setting to a PortAudio
    device index for ``output.portaudio``.

    RASTATIME 2026-09-05 — the fourth element is the exact PortAudio
    device *name* when the resolver judged rendering by name safe
    (``ResolvedOutput.by_name``); the renderer then emits
    ``device_name=`` and the index is only a comment.  See
    ``portaudio_output.with_name_selection`` for why.

    RASTATIME 2026-09-03 — before this, Settings → Local Machine →
    Main Output had no effect on the Liquidsoap local monitor: the
    value was stored and pushed to playout, but
    ``LiquidsoapPlayoutEngine.set_audio_device`` is a no-op, and the
    .liq was rendered without any device argument.  The setting
    promised something it did not deliver.

    Returns ``(device_index, label, endpoint_id)``.  The endpoint id is
    the Windows stable id we actually resolved, echoed into the .liq
    so the Settings page can tell "saved" from "active".  A ``None``
    index means "render
    without a device argument", i.e. keep the previous OS-default
    behaviour — the safe fallback for every failure mode here
    (no setting, unresolvable name, nothing openable).

    Never raises: a monitor-device problem must not stop the playout
    service from starting.
    """
    try:
        from libretime_api.soundcard.models import SoundcardSettings  # noqa: PLC0415
        row = SoundcardSettings.get_settings()
        stable_id = (row.main_output_id or "").strip()
        name = (row.main_output_name or "").strip()
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning(
            "Could not read the Main Output setting (%s) — the local "
            "monitor falls back to the OS-default endpoint.", exc,
        )
        return (None, "", "", None)

    if not stable_id and not name:
        logger.info(
            "No Main Output configured — local monitor uses the "
            "OS-default endpoint."
        )
        return (None, "", "", None)

    # Older rows may carry only the GUID; recover the friendly name via
    # the device manager, because PortAudio matches on names, not on
    # Windows endpoint IDs.
    if not name and stable_id:
        try:
            import audio.soundcard._registry as _reg  # noqa: PLC0415
            from audio.soundcard.interface import AudioDeviceKind  # noqa: PLC0415
            mgr = _reg.default_manager
            if mgr is not None:
                dev = mgr.find_device_by_id_or_name(
                    stable_id, "", AudioDeviceKind.OUTPUT
                )
                if dev is not None:
                    name = dev.name
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.debug("Main Output name lookup failed: %s", exc)

    if not name:
        logger.warning(
            "Main Output %r has no friendly name stored — cannot match it "
            "against PortAudio.  Re-save the Main Output picker in "
            "Settings → Local Machine.  Falling back to the OS-default "
            "endpoint.", stable_id,
        )
        return (None, "", "", None)

    try:
        from libretime_playout.engine.portaudio_output import (  # noqa: PLC0415
            resolve_output_device,
        )
        resolved = resolve_output_device(name)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning(
            "Main Output resolve raised %s — falling back to the "
            "OS-default endpoint.", exc,
        )
        return (None, "", "", None)

    if resolved is None:
        return (None, "", "", None)
    return (resolved.index, resolved.label, stable_id, resolved.by_name)


class _LiquidsoapRenderError(RuntimeError):
    """Raised by :func:`_render_rastatime_liq` after logging the cause."""


class RenderOutcome(NamedTuple):
    """
    What :func:`_render_rastatime_liq_outcome` produced.

    ``main_output_mode`` is one of the ``liquidsoap_service.MAIN_OUTPUT_*``
    strings: ``name`` (``device_name=``, index-independent), ``index``
    (``device_id=N``, only valid for the device list it was taken from)
    or ``default`` (no device argument).  Automatic restarts refuse the
    ``index`` mode - see :func:`_render_rastatime_liq_at_startup` and
    ``PlayoutScheduler._maybe_nightly_restart`` (RASTATIME 2026-09-07).
    """

    changed: bool
    main_output_mode: str
    # RASTATIME 2026-10-02 - Stereo Tool on the bus in this render; a fresh
    # instance that does not stay up afterwards is restarted without it
    # (PlayoutScheduler._settle_after_restart).
    stereotool_active: bool = False


# Where the internal HTTP listener binds (source_switcher.start_listener)
# and, since option d (2026-09-09), where the harbor callbacks rendered
# into rastatime.liq POST DJ connect/disconnect events.
_LISTENER_HOST = "127.0.0.1"
_LISTENER_PORT = 8770

# RASTATIME 2026-09-09 - input.harbor network timeout in seconds (how
# fast a DJ who merely closes the connection is noticed; a client silent
# for longer is dropped).  Default 5 = the harbor buffer; floor 1.
HARBOR_TIMEOUT_ENV = "RASTATIME_HARBOR_TIMEOUT_SECONDS"


def _harbor_timeout_seconds() -> float:
    from libretime_playout.liquidsoap_config import (  # noqa: PLC0415
        DEFAULT_HARBOR_TIMEOUT_SECONDS,
    )
    raw = os.environ.get(HARBOR_TIMEOUT_ENV, "").strip()
    if not raw:
        return DEFAULT_HARBOR_TIMEOUT_SECONDS
    try:
        value = float(raw)
    except ValueError:
        logger.warning(
            "%s=%r is not a number - using %.0f s",
            HARBOR_TIMEOUT_ENV, raw, DEFAULT_HARBOR_TIMEOUT_SECONDS,
        )
        return DEFAULT_HARBOR_TIMEOUT_SECONDS
    if value < 1.0:
        logger.warning("%s=%r is below 1 s - using 1 s", HARBOR_TIMEOUT_ENV, raw)
        return 1.0
    return value


def _render_rastatime_liq(stream_outputs: List[Dict]) -> bool:
    """Compatibility wrapper: the ``changed`` flag of
    :func:`_render_rastatime_liq_outcome`."""
    return _render_rastatime_liq_outcome(stream_outputs).changed


LOCAL_OUTPUT_ADAPTIVE_ENV = "RASTATIME_LIQUIDSOAP_LOCAL_OUTPUT_ADAPTIVE"


def _local_output_adaptive_enabled() -> bool:
    """
    RASTATIME 2026-09-14: the monitor bridge compensates the drift between
    the Main Output's sample clock and Liquidsoap's main clock with
    ``buffer.adaptative`` (default on).  ``false``/``0``/``no``/``off``
    renders the plain ``buffer()`` again; ``mksafe`` + ``fallible=false``
    keep the output open either way.
    """
    raw = os.environ.get(LOCAL_OUTPUT_ADAPTIVE_ENV, "true").strip().lower()
    return raw not in ("false", "0", "no", "off")


# RASTATIME 2026-10-18 - format of the show recording encoder in the LAST
# rendered rastatime.liq; the scheduler names the recording files after it.
_RENDERED_SHOW_RECORDING_FORMAT = "mp3"


def _rendered_show_recording_extension() -> str:
    from libretime_playout.liquidsoap_config import (  # noqa: PLC0415
        show_recording_extension,
    )

    return show_recording_extension(_RENDERED_SHOW_RECORDING_FORMAT)


def _render_settings_fingerprint() -> Optional[str]:
    """
    RASTATIME 2026-09-16 - a hash of the operator settings that are baked
    into rastatime.liq: the 24/7 recording (enabled, folder, format,
    bitrate), the Main Output device, the crossfade duration and the stream
    outputs.  The scheduler compares it on every refresh with the value of
    the last render and lets the planned-restart path re-render and restart
    LIQUIDSOAP when it changed (quiet moment or next track boundary), so an
    operator no longer restarts services by hand after Save.  Only cheap
    database reads - no device probe.  None when the ORM is unavailable.
    """
    import hashlib  # noqa: PLC0415
    import json  # noqa: PLC0415

    try:
        from libretime_api.soundcard.models import SoundcardSettings  # noqa: PLC0415
        from libretime_playout.liquidsoap_config import (  # noqa: PLC0415
            read_hourly_recording_config_from_db,
            read_show_recording_config_from_db,
        )
        row = SoundcardSettings.get_settings()
        payload = {
            "hourly": read_hourly_recording_config_from_db(),
            "show_recording": read_show_recording_config_from_db(),
            "main_output": [row.main_output_id or "", row.main_output_name or ""],
            "crossfade": _resolve_crossfade_seconds(),
            "show_crossfade": _resolve_show_crossfade_seconds(),
            "dj_fade": _resolve_dj_fade_seconds(),
            "streams": _read_stream_outputs(),
            "loudness": list(_resolve_loudness_limiter()),
            "stereotool": _stereotool_fingerprint(_resolve_stereotool()),
        }
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.debug("render settings fingerprint unavailable: %s", exc)
        return None
    return hashlib.sha1(  # noqa: S324 - not security, a change detector
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def _render_rastatime_liq_outcome(stream_outputs: List[Dict]) -> RenderOutcome:
    """
    Render ``rastatime.liq`` from the operator-configured environment +
    ``cc_pref`` stream outputs.  Idempotent: writes only when content
    actually changed; returns that ``changed`` flag together with how
    the Main Output was addressed.

    RASTATIME 2026-09-05: split out of the startup wrapper so the
    scheduler's nightly quiet-window restart can re-render right before
    it restarts LIQUIDSOAP (fresh device resolution, fresh cc_pref).
    Every failure is logged here and then raised as
    :class:`_LiquidsoapRenderError`; the startup wrapper turns that
    into ``sys.exit(1)``, the nightly caller into a log line.
    """
    from libretime_playout.liquidsoap_service import (  # noqa: PLC0415
        MAIN_OUTPUT_BY_INDEX,
        MAIN_OUTPUT_BY_NAME,
        MAIN_OUTPUT_DEFAULT,
    )
    from libretime_playout.liquidsoap_config import (  # noqa: PLC0415
        DEFAULT_LINEIN_HTTP_MAX_BUFFER_SECONDS,
        read_hourly_recording_config_from_db,
        read_show_recording_config_from_db,
        icecast_mounts_without_fallback,
        write_rastatime_liq,
        write_standby_liq,
    )

    config_path = Path(
        os.environ.get(
            "RASTATIME_LIQUIDSOAP_CONFIG_PATH",
            _LIQUIDSOAP_DEFAULT_CONFIG_PATH,
        )
    )
    log_path = os.environ.get(
        "RASTATIME_LIQUIDSOAP_LOG_PATH",
        _LIQUIDSOAP_DEFAULT_LOG_PATH,
    )
    telnet_host = os.environ.get("RASTATIME_LIQUIDSOAP_HOST", "127.0.0.1")
    try:
        telnet_port = int(os.environ.get("RASTATIME_LIQUIDSOAP_PORT", "1234"))
    except ValueError as exc:
        logger.critical(
            "RASTATIME_LIQUIDSOAP_PORT must be an integer: %s", exc
        )
        raise _LiquidsoapRenderError(str(exc)) from exc
    crossfade = _resolve_crossfade_seconds()
    show_crossfade = _resolve_show_crossfade_seconds()
    dj_fade = _resolve_dj_fade_seconds()
    # RASTATIME 2026-09-03 - linein_http start-up buffer, env-overridable
    # so it can be tuned against the 1.0 default (start gap + end-of-slot
    # latency vs.
    # under-run safety) without a rebuild.  Clamped to a sane floor: a
    # sub-0.2 s buffer invites glitches even on a loopback hop.
    try:
        linein_http_max_buffer = float(
            os.environ.get(
                "RASTATIME_LIQUIDSOAP_LINEIN_HTTP_MAX_BUFFER_SECONDS",
                str(DEFAULT_LINEIN_HTTP_MAX_BUFFER_SECONDS),
            )
        )
    except ValueError as exc:
        logger.critical(
            "RASTATIME_LIQUIDSOAP_LINEIN_HTTP_MAX_BUFFER_SECONDS must be "
            "a float: %s", exc,
        )
        raise _LiquidsoapRenderError(str(exc)) from exc
    if linein_http_max_buffer < 0.2:
        logger.warning(
            "RASTATIME_LIQUIDSOAP_LINEIN_HTTP_MAX_BUFFER_SECONDS=%.3f is "
            "below the 0.2 s floor; using 0.2 s.", linein_http_max_buffer,
        )
        linein_http_max_buffer = 0.2
    # 2026-09-27: RASTATIME_LIQUIDSOAP_CROSSFADE_FADE_SECONDS (Phase-D
    # fade zones inside crossfade()) is retired - the track crossfade is
    # now a real crossfade of the operator's duration, the show crossfade
    # has its own value; see liquidsoap_config._render_crossfade_block.
    if os.environ.get("RASTATIME_LIQUIDSOAP_CROSSFADE_FADE_SECONDS"):
        logger.warning(
            "RASTATIME_LIQUIDSOAP_CROSSFADE_FADE_SECONDS is set but no longer "
            "used (track/show crossfade come from Settings -> General)."
        )
    local_output_enabled = (
        os.environ.get("RASTATIME_LIQUIDSOAP_LOCAL_OUTPUT", "true").lower()
        not in ("false", "0", "no", "off")
    )
    # RASTATIME 2026-09-14 - monitor bridge with drift compensation
    # (buffer.adaptative) unless the machine setting turns it off.
    local_output_adaptive = _local_output_adaptive_enabled()
    if local_output_enabled:
        logger.info(
            "Liquidsoap local output: %s bridge, output kept open with mksafe (%s=%s).",
            "adaptive" if local_output_adaptive else "plain buffer()",
            LOCAL_OUTPUT_ADAPTIVE_ENV,
            "true" if local_output_adaptive else "false",
        )

    # Phase-C4: DJ-Source harbor passwords aus libretime.conf.
    # Wenn unset, rendert der Renderer die input.harbor-Blöcke nicht
    # (= C3-Stand, nur scheduled queue auf dem Bus).
    harbor_main_pwd, harbor_show_pwd = _read_harbor_credentials()
    harbor_main_port, harbor_main_mount, harbor_show_port, harbor_show_mount = (
        _read_harbor_inputs(stream_outputs)
    )
    logger.info(
        "Liquidsoap harbors: main %s:%d, show %s:%d (stream.inputs in libretime.conf, "
        "as shown under Settings -> Streams).",
        harbor_main_mount, harbor_main_port, harbor_show_mount, harbor_show_port,
    )
    if harbor_main_pwd or harbor_show_pwd:
        logger.info(
            "Liquidsoap input.harbor enabled: main=%s show=%s",
            "yes" if harbor_main_pwd else "no",
            "yes" if harbor_show_pwd else "no",
        )

    # Parent dir must exist — we don't auto-create it because the
    # operator's NSSM-install script makes the standard tree, and
    # rendering into an unexpected location is a config-error worth
    # surfacing loudly.
    if not config_path.parent.exists():
        logger.critical(
            "Liquidsoap config target directory does not exist: %s\n"
            "Set RASTATIME_LIQUIDSOAP_CONFIG_PATH to the correct .liq "
            "path, or create the directory with the install script.",
            config_path.parent,
        )
        raise _LiquidsoapRenderError(f"missing directory {config_path.parent}")

    # RASTATIME 2026-06-05 — 24/7 hourly archive recorder config (cc_pref,
    # set in Settings -> Local Machine).  Default disabled -> renders a
    # comment stub, leaving the live stream untouched.
    hourly = read_hourly_recording_config_from_db()
    if hourly["enabled"] and hourly["folder"]:
        logger.info(
            "24/7 hourly recording enabled: folder=%s format=%s %dk",
            hourly["folder"], hourly["format"], hourly["bitrate"],
        )
    # RASTATIME 2026-10-18 - per-show recording encoder (Settings -> Local
    # Machine -> Show Recording), MP3 320k unless the operator chose otherwise.
    show_rec = read_show_recording_config_from_db()
    logger.info(
        "Show recording encoder: format=%s %dk", show_rec["format"], show_rec["bitrate"],
    )

    # Main Output (Settings -> Local Machine) -> PortAudio device index.
    # Resolved here, at render time, because output.portaudio takes the
    # device as a script argument; a later change therefore needs a
    # PLAYOUT restart (the UI offers a button for it).
    if local_output_enabled:
        (
            local_output_device_id,
            local_output_device_label,
            local_output_endpoint_id,
            local_output_device_name,
        ) = _resolve_local_output_device()
    else:
        local_output_device_id, local_output_device_label = (None, "")
        local_output_endpoint_id = ""
        local_output_device_name = None
    if local_output_device_name:
        main_output_mode = MAIN_OUTPUT_BY_NAME
    elif local_output_device_id is not None:
        main_output_mode = MAIN_OUTPUT_BY_INDEX
    else:
        main_output_mode = MAIN_OUTPUT_DEFAULT

    from libretime_playout.icy_metadata import (  # noqa: PLC0415
        IcyPreferences, read_icy_preferences_from_db,
    )
    icy = read_icy_preferences_from_db() or IcyPreferences()
    # RASTATIME 2026-09-28 - EBU R128 stage 1: the bus limiter only in R128 mode
    loudness_mode, loudness_ceiling = _resolve_loudness_limiter()
    logger.info(
        "Loudness Normalization: %s%s (Settings -> Streams).",
        loudness_mode,
        f", true-peak ceiling {loudness_ceiling:.1f} dBTP (bus limiter)"
        if loudness_ceiling is not None else "",
    )
    # RASTATIME 2026-10-02 - output processing (Stereo Tool), optional
    from libretime_playout.liquidsoap_config import stereotool_render_active  # noqa: PLC0415
    stereotool = _resolve_stereotool()
    stereotool_active = stereotool_render_active(stereotool)
    if stereotool.enabled:
        logger.info(
            "Output processing: Stereo Tool %s (library %s, preset %s, licence %s) "
            "(Settings -> Streams).",
            "ACTIVE" if stereotool_active else "enabled but NOT active - see the warning above",
            stereotool.library_file or "-", stereotool.preset_file or "-",
            "set" if stereotool.license_key else "not set",
        )
    else:
        logger.info("Output processing: Stereo Tool off (Settings -> Streams).")
    logger.info(
        "ICY metadata: Stream Label format %d, off-air text %r, station %r "
        "(Settings -> Streams / General).",
        icy.label_format, icy.offair_text, icy.station_name,
    )

    try:
        changed = write_rastatime_liq(
            config_path,
            stream_outputs,
            telnet_host=telnet_host,
            telnet_port=telnet_port,
            log_file=log_path,
            crossfade_duration=crossfade,
            show_crossfade_duration=show_crossfade,
            dj_fade_seconds=dj_fade,
            local_output_enabled=local_output_enabled,
            local_output_device_id=local_output_device_id,
            local_output_device_label=local_output_device_label,
            local_output_endpoint_id=local_output_endpoint_id,
            local_output_device_name=local_output_device_name,
            local_output_adaptive=local_output_adaptive,
            linein_http_max_buffer_seconds=linein_http_max_buffer,
            harbor_main_password=harbor_main_pwd or None,
            harbor_show_password=harbor_show_pwd or None,
            hourly_recording_enabled=hourly["enabled"],
            hourly_recording_folder=hourly["folder"],
            hourly_recording_format=hourly["format"],
            hourly_recording_bitrate=hourly["bitrate"],
            show_recording_format=show_rec["format"],
            show_recording_bitrate=show_rec["bitrate"],
            source_event_url=f"http://{_LISTENER_HOST}:{_LISTENER_PORT}/source-event",
            harbor_timeout_seconds=_harbor_timeout_seconds(),
            # RASTATIME 2026-09-10 - ports/mounts as shown in Settings -> Streams,
            # logins checked by PLAYOUT (/dj-auth -> legacy web application).
            harbor_main_port=harbor_main_port,
            harbor_main_mount=harbor_main_mount,
            harbor_show_port=harbor_show_port,
            harbor_show_mount=harbor_show_mount,
            dj_auth_url=f"http://{_LISTENER_HOST}:{_LISTENER_PORT}/dj-auth",
            # RASTATIME 2026-09-13 - rendered defaults of the ICY metadata
            # values; the scheduler pushes changes over telnet afterwards.
            icy_label_format=icy.label_format,
            icy_offair_text=icy.offair_text,
            icy_station_name=icy.station_name,
            # RASTATIME 2026-09-28 - EBU R128 stage 1: limiter when the mode is R128
            loudness_limiter_ceiling=loudness_ceiling,
            # RASTATIME 2026-10-02 - output processing (Stereo Tool), optional
            stereotool=stereotool,
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.critical(
            "Failed to render Liquidsoap config %s: %s",
            config_path, exc,
        )
        raise _LiquidsoapRenderError(str(exc)) from exc

    if changed:
        logger.info("Rendered %s (content changed).", config_path)
    else:
        logger.info(
            "Liquidsoap config %s already up-to-date — no restart "
            "needed.",
            config_path,
        )
    # RASTATIME 2026-09-09 - the standby source for the Icecast fallback
    # mounts is rendered from the same stream outputs (same encoders).
    # It runs as RASTATIME-STANDBY and only needs a restart when this
    # file changes, i.e. when the stream outputs change.
    standby_path = Path(
        os.environ.get("RASTATIME_LIQUIDSOAP_STANDBY_PATH", _LIQUIDSOAP_DEFAULT_STANDBY_PATH)
    )
    # the recorder's file extension follows what was just rendered
    global _RENDERED_SHOW_RECORDING_FORMAT  # noqa: PLW0603
    _RENDERED_SHOW_RECORDING_FORMAT = str(show_rec["format"])
    standby_audio = os.environ.get("RASTATIME_STANDBY_AUDIO", "").strip() or None
    try:
        standby_changed = write_standby_liq(
            standby_path, stream_outputs, audio_file=standby_audio,
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("Could not render the standby source %s: %s", standby_path, exc)
    else:
        if standby_changed:
            logger.warning(
                "Rendered %s (content changed).  RESTART the RASTATIME-STANDBY "
                "NSSM service so the fallback mounts carry the new encoders "
                "(no listener is affected by that restart).", standby_path,
            )
    # The standby side follows the stream outputs by itself; Icecast's
    # fallback blocks do not.  Say so loudly when a public mount has none.
    icecast_xml = Path(os.environ.get("RASTATIME_ICECAST_CONFIG_PATH", _ICECAST_DEFAULT_CONFIG_PATH))
    uncovered = icecast_mounts_without_fallback(icecast_xml, stream_outputs)
    if uncovered is None:
        logger.warning(
            "Cannot check the Icecast fallback mounts (%s unreadable) - listeners "
            "of mounts without <fallback-mount> are disconnected by a planned "
            "restart.", icecast_xml,
        )
    elif uncovered:
        logger.warning(
            "Icecast mount(s) without a standby fallback in %s: %s - add a "
            "<mount type=\"normal\"> block with <fallback-mount>%s-standby</fallback-mount> "
            "and <fallback-override>1</fallback-override>, then restart RASTATIME-ICECAST; "
            "until then a planned restart disconnects their listeners.",
            icecast_xml, ", ".join(uncovered), uncovered[0],
        )
    return RenderOutcome(
        changed=changed, main_output_mode=main_output_mode,
        stereotool_active=stereotool_active,
    )


def _render_rastatime_liq_at_startup(stream_outputs: List[Dict]) -> bool:
    """
    Startup wrapper around :func:`_render_rastatime_liq`.

    A render failure is loud (``sys.exit(1)``) because the engine that
    follows won't have a Liquidsoap to talk to if the script is
    unbuildable.

    RASTATIME 2026-09-05 — boot race: LIQUIDSOAP starts in parallel
    with PLAYOUT and loads the *previous* ``rastatime.liq``.  When this
    render changed the file inside the boot window, PLAYOUT restarts
    LIQUIDSOAP itself (nothing is on air that early).  Outside the
    window the operator keeps the manual rule: PLAYOUT first, then
    LIQUIDSOAP.  See ``liquidsoap_service`` for the 2026-09-05 evidence.
    """
    try:
        outcome = _render_rastatime_liq_outcome(stream_outputs)
    except _LiquidsoapRenderError:
        sys.exit(1)
    if not outcome.changed:
        return False

    from libretime_playout.liquidsoap_service import (  # noqa: PLC0415
        MAIN_OUTPUT_BY_INDEX,
        boot_restart_enabled,
        restart_liquidsoap_service,
        system_uptime_seconds,
        within_boot_window,
    )

    uptime = system_uptime_seconds()
    if boot_restart_enabled() and within_boot_window(uptime):
        if outcome.main_output_mode == MAIN_OUTPUT_BY_INDEX:
            # RASTATIME 2026-09-07: an index is only valid for the device
            # list it was taken from; restarting LIQUIDSOAP into an index
            # render is what crash-looped it on the 09-06/09-07 nightly
            # restarts.  Keep the running instance, tell the operator.
            logger.error(
                "rastatime.liq changed %.0f s after boot, but the Main Output "
                "is rendered by PortAudio index (no name-safe entry right "
                "now: display asleep, device renamed, or a non-MME/WASAPI "
                "match) - NOT restarting RASTATIME-LIQUIDSOAP automatically.  "
                "Check Settings -> Local Machine -> Main Output, then restart "
                "PLAYOUT and LIQUIDSOAP manually in a quiet moment.",
                uptime or 0.0,
            )
            return True
        logger.warning(
            "rastatime.liq changed %.0f s after boot — restarting "
            "RASTATIME-LIQUIDSOAP so it loads this render instead of the "
            "stale one it started with (boot race).",
            uptime or 0.0,
        )
        if not restart_liquidsoap_service("boot window: fresh render"):
            logger.error(
                "Automatic restart failed.  RESTART the RASTATIME-LIQUIDSOAP "
                "NSSM service manually:   nssm restart RASTATIME-LIQUIDSOAP"
            )
            return True
        return False

    # RASTATIME 2026-09-16 - outside the boot window the scheduler applies
    # the fresh render itself (quiet moment or next track boundary).
    logger.warning(
        "Rendered rastatime.liq (content changed).  The playout will restart "
        "RASTATIME-LIQUIDSOAP in the next quiet moment (or at the next track "
        "boundary); to force it now:   nssm restart RASTATIME-LIQUIDSOAP"
    )
    return True


PLAYOUT_ENGINE_ENV = "RASTATIME_PLAYOUT_ENGINE"


def _require_liquidsoap_engine() -> str:
    """
    RASTATIME 2026-09-10 - Liquidsoap is the only playout engine (the
    mpv engine was deleted).  ``RASTATIME_PLAYOUT_ENGINE`` is still
    honoured for installed service environments: unset or
    ``liquidsoap`` is fine, anything else aborts the start with a
    critical log line instead of silently running a different setup
    than the operator configured.
    """
    kind = (os.environ.get(PLAYOUT_ENGINE_ENV) or "liquidsoap").strip().lower()
    if kind != "liquidsoap":
        logger.critical(
            "%s=%r is not supported - Liquidsoap is the only playout engine "
            "since 2026-09-10 (the mpv engine was deleted).  Set "
            "%s=liquidsoap or remove the variable.",
            PLAYOUT_ENGINE_ENV, kind, PLAYOUT_ENGINE_ENV,
        )
        sys.exit(1)
    return kind


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("RASTATIME-PLAYOUT: starting.")

    # 1. Health gate — block until the API is up (or timeout)
    _wait_for_api()

    # 2. Load libretime.conf
    config = _load_config()

    # 3. Bootstrap Django ORM (non-fatal if it fails)
    django_ok = _setup_django()

    # 4. Read Icecast stream settings from cc_pref
    stream_outputs: List[Dict] = []
    render_restart_pending = False
    if django_ok:
        stream_outputs = _read_stream_outputs()
        if stream_outputs:
            logger.info(
                "Found %d enabled Icecast stream output(s) - "
                "Liquidsoap streams them from the internal bus (output.icecast).",
                len(stream_outputs),
            )
        else:
            logger.info("No stream outputs configured in cc_pref.")
    else:
        logger.info("Django unavailable — local playback only (no Icecast egress).")

    # 5. Initialise the playout engine.
    #
    # RASTATIME 2026-09-10 - Liquidsoap is the only engine: the mpv engine
    # and its FfmpegStreamer Icecast companions were deleted (BACKLOG
    # "Legacy-mpv-Code-Delete").  RASTATIME_PLAYOUT_ENGINE is still read
    # so an installed service environment keeps working, but the only
    # accepted value is "liquidsoap" - anything else is a configuration
    # error that must not be papered over at startup.
    _require_liquidsoap_engine()

    try:
        from libretime_playout.engine.liquidsoap_engine import LiquidsoapPlayoutEngine  # noqa: PLC0415

        # RASTATIME 2026-05-26 — Phase C7.  Render the production
        # rastatime.liq from the cc_pref stream-output rows + the
        # operator-configured paths.  Idempotent (rewrites only
        # when content actually changed).  RASTATIME 2026-09-16: a
        # changed render is applied by the scheduler in the next quiet
        # moment (boot window: at once), see _maybe_settings_restart.
        render_restart_pending = _render_rastatime_liq_at_startup(stream_outputs)

        engine = LiquidsoapPlayoutEngine()
        logger.info(
            "Playout engine: Liquidsoap (telnet target %s:%d).",
            engine._telnet._host, engine._telnet._port,
        )
    except RuntimeError as exc:
        logger.critical("Liquidsoap engine failed to initialise: %s", exc)
        logger.critical(
            "Ensure Liquidsoap is running and its telnet server is "
            "reachable at RASTATIME_LIQUIDSOAP_HOST / _PORT (default "
            "127.0.0.1:1234)."
        )
        sys.exit(1)

    # 6. Initialise API client
    # Use RASTATIME_API_URL (defaults to the local Django API port derived
    # from the health gate URL) instead of config.general.public_url, which
    # may point to the PHP frontend at a different port.
    api_url = os.environ.get("RASTATIME_API_URL", _API_URL_DEFAULT)
    logger.info("API client base URL: %s", api_url)
    from libretime_api_client.v2 import ApiClient  # noqa: PLC0415
    api_client = ApiClient(
        base_url=api_url,
        api_key=config.general.api_key,
    )

    # v1 API client — needed for the legacy notify-media-item-start-play
    # endpoint, which drives the dashboard "On Air" indicator.  This
    # endpoint lives in the PHP frontend (Zend_Controller_Action), NOT
    # in Django on port 8765.  RASTATIME 2026-10-04 (go-live stage 1): it
    # talks to the legacy app on THIS machine (general.internal_url /
    # RASTATIME_INTERNAL_URL / http://127.0.0.1), never through the public
    # https address.
    legacy_url = config.general.internal_base_url()
    from libretime_api_client.v1 import BaseApiClient as ApiClientV1  # noqa: PLC0415
    api_client_v1 = ApiClientV1(
        base_url=legacy_url,
        api_key=config.general.api_key,
    )
    logger.info("Legacy v1 API client base URL: %s (public_url %s)", legacy_url, config.general.public_url)

    # 6b. Listener-stats collector (BACKLOG "Analytics: Listener Stats
    # sammeln keine Daten", fixed 2026-08-30).  Upstream started this
    # thread only in the orphaned main.py — the active entry point never
    # did, so cc_listener_count stayed empty forever.  The outputs are
    # rebuilt from cc_pref on every poll cycle; libretime.conf's
    # stream.outputs list is empty
    # on RASTATIME deployments and must not be used.  Pushes go through
    # the v1 client to the PHP /api/push-stream-stats endpoint, which
    # inserts into cc_listener_count.
    if django_ok:
        from libretime_playout.history.stats import (  # noqa: PLC0415
            StatsCollectorThread,
            outputs_from_stream_settings,
        )

        stats_thread = StatsCollectorThread(
            config=config,
            legacy_client=api_client_v1,
            outputs_provider=lambda: outputs_from_stream_settings(
                _read_stream_outputs()
            ),
        )
        stats_thread.start()
        logger.info("Listener-stats collector started (poll every 120 s).")
    else:
        logger.warning(
            "Django ORM unavailable — listener-stats collector NOT started."
        )

    # 7. Initialise PlayoutScheduler
    # RASTATIME: pass storage path for direct file access (avoids API download
    # issues with X-Accel-Redirect on Windows/Waitress).
    storage_path = str(config.storage.path) if hasattr(config, 'storage') else None
    if storage_path:
        logger.info("Storage path for direct file access: %s", storage_path)

    from libretime_playout.playout_scheduler import PlayoutScheduler  # noqa: PLC0415
    from libretime_playout.icy_metadata import read_icy_preferences_from_db  # noqa: PLC0415
    # Stream-output changes (Settings → Streams) reach the air only via a
    # re-render of rastatime.liq + a LIQUIDSOAP restart (planned restart
    # or operator); the scheduler has no hot-reload of its own since the
    # FfmpegStreamer path was deleted (2026-09-10).

    # RASTATIME 2026-09-05 - nightly quiet-window restart of LIQUIDSOAP
    # (memory-leak safety net).  The re-render before the restart needs
    # the ORM for cc_pref.
    from libretime_playout.liquidsoap_service import NightlyRestartPolicy  # noqa: PLC0415
    nightly_policy = NightlyRestartPolicy.from_env()
    render_for_restart = (
        (lambda: _render_rastatime_liq_outcome(_read_stream_outputs()))
        if django_ok else None
    )
    if nightly_policy is not None and nightly_policy.enabled:
        logger.info(
            "Nightly Liquidsoap restart window starts at %s local time "
            "(%s to change, 'off' to disable).",
            nightly_policy.start.strftime("%H:%M"),
            "RASTATIME_LIQUIDSOAP_NIGHTLY_RESTART",
        )

    live_text_writer = _build_live_text_writer() if django_ok else None
    scheduler = PlayoutScheduler(
        engine=engine,
        api_client=api_client,
        api_client_v1=api_client_v1,
        storage_path=storage_path,
        render_liquidsoap=render_for_restart,
        # RASTATIME 2026-09-16 - settings baked into the .liq are applied by
        # the playout itself (re-render + LIQUIDSOAP restart in a quiet moment).
        render_settings_fingerprint=(_render_settings_fingerprint if django_ok else None),
        render_restart_pending=render_restart_pending,
        # RASTATIME 2026-10-18 - recording file extension of the rendered encoder
        recording_extension=_rendered_show_recording_extension,
        nightly_restart=nightly_policy,
        # RASTATIME 2026-09-27 - input switches + show boundaries follow the
        # SHOW crossfade; the track crossfade shapes in-show transitions.
        input_transition_seconds=_resolve_show_crossfade_seconds(),
        track_crossfade_seconds=_resolve_crossfade_seconds(),
        # RASTATIME 2026-09-13 - Stream Label / Off Air Metadata / station
        # name re-read every refresh (ORM), pushed over telnet on change.
        read_icy_preferences=(read_icy_preferences_from_db if django_ok else None),
        # RASTATIME 2026-09-28 - TuneIn now-playing pushes owned by the playout
        # (settings re-read from cc_pref before every push).
        tunein=(_build_tunein_pusher() if django_ok else None),
        # RASTATIME 2026-09-28 - Live Text Info (now-playing text file)
        live_text=live_text_writer,
        # RASTATIME 2026-10-04 - the Line-In capture pushes with the local
        # Icecast's source credentials from Settings -> Streams (no more
        # hard-coded "admin"); go-live stage 0, secrets rotation.
        linein_icecast_credentials=(
            _local_icecast_source_credentials(_read_stream_outputs()) if django_ok else None
        ),
    )
    logger.info("Webstream watchdog: inside Liquidsoap (frame counter, rendered into rastatime.liq).")
    # RASTATIME 2026-09-04 - a previous Pypo may have died mid-prepare
    # with a bus gate closed; open both before the first refresh.
    # RASTATIME 2026-09-06 - the constructor tried once (recording
    # sentinel stop + gates); when Liquidsoap was not up yet (manual
    # restart order, boot-window restart, nightly restart) a daemon
    # thread keeps trying until telnet answers.
    scheduler.reset_gates()
    scheduler.ensure_liquidsoap_initial_state()

    # 7b. Restore the operator-selected audio output device.
    # SoundcardSettings is the singleton table written by
    # /api/v2/audio/soundcard-settings.  We read it directly via the
    # Django ORM so the engine starts on the right soundcard from the
    # first track onwards — without this, the engine would start on the
    # OS-default endpoint and only switch later when the Frontend
    # POSTs the setting again.
    if django_ok:
        saved_output: Optional[str] = None
        saved_output_name: str = ""
        try:
            from libretime_api.soundcard.models import SoundcardSettings  # noqa: PLC0415
            _row = SoundcardSettings.get_settings()
            saved_output = _row.main_output_id or None
            # RASTATIME 2026-05-14 — friendly-name fallback for when the
            # saved endpoint GUID no longer resolves after a USB
            # re-enumeration / driver update.  Mirror of the linein
            # fallback (see playout_scheduler._resolve_linein_device).
            saved_output_name = (_row.main_output_name or "").strip()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning(
                "Could not read SoundcardSettings.main_output_id "
                "(falling back to OS-default audio device): %s", exc,
            )

        if saved_output:
            # Try fallback-resolve via the AudioDeviceManager: if the
            # saved GUID doesn't resolve, try the saved friendly name.
            resolved_id: Optional[str] = saved_output
            try:
                import audio.soundcard._registry as _reg  # noqa: PLC0415
                from audio.soundcard.interface import AudioDeviceKind  # noqa: PLC0415
                mgr = _reg.default_manager
                if mgr is not None:
                    dev = mgr.find_device_by_id_or_name(
                        saved_output, saved_output_name, AudioDeviceKind.OUTPUT,
                    )
                    if dev is None:
                        resolved_id = None
                        logger.warning(
                            "Saved main_output_id %r and main_output_name %r "
                            "both fail to resolve — falling back to OS-default "
                            "audio device.",
                            saved_output, saved_output_name,
                        )
                    elif dev.stable_id != saved_output.strip().lower():
                        logger.warning(
                            "Saved main_output_id %r no longer resolves; "
                            "name-fallback matched %r (stable_id=%s).  "
                            "Operator should re-save the Main Output picker "
                            "so future starts use the new id directly.",
                            saved_output, dev.name, dev.stable_id,
                        )
                        resolved_id = dev.stable_id
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning(
                    "Audio-output resolve raised %s; using saved id %r as-is.",
                    exc, saved_output,
                )

            if resolved_id:
                logger.info(
                    "Restoring audio output device from saved settings: %s",
                    resolved_id,
                )
                engine.set_audio_device(resolved_id)
            else:
                logger.info(
                    "No usable audio output device — using OS-default endpoint."
                )
        else:
            logger.info(
                "No saved audio output device — using OS-default endpoint."
            )

    # 8a. Pre-flight scanner — looks 48h ahead every 15 min and writes
    # operator-visible warnings (currently: missing Line-In devices) to
    # the rastatime_preflight_warning table.  See preflight.py for the
    # full contract.  Instantiated BEFORE the source-switcher listener
    # so we can hand it through as the /reload-schedule co-trigger —
    # PHP frontend save → both scheduler.refresh() AND a fresh preflight
    # scan, so dashboard warnings appear within seconds of a show edit.
    from libretime_playout.preflight import PreflightChecker  # noqa: PLC0415
    preflight = PreflightChecker(api_client=api_client)

    # 8b. Source switcher — Master DJ > Show DJ > Scheduled.  The HTTP
    # listener receives Icecast event-binding webhooks on
    # http://127.0.0.1:8770/source-event and drives the scheduler's
    # switch_audio_source() method.  See source_switcher.py and the
    # <event-bindings> blocks in icecast.xml for the full wiring.
    from libretime_playout.dj_auth import DjAuthenticator  # noqa: PLC0415
    from libretime_playout.source_switcher import (  # noqa: PLC0415
        SourceSwitcher,
        reconcile_interval_from_env,
        start_listener,
    )
    switcher = SourceSwitcher(switch_callback=scheduler.switch_audio_source)
    scheduler.set_source_switcher(switcher)
    switcher_server = start_listener(
        switcher,
        scheduler=scheduler,   # /reload-schedule needs the scheduler too
        preflight=preflight,   # …and the preflight scanner for instant rescan
        host=_LISTENER_HOST,
        port=_LISTENER_PORT,
        # Option d (2026-09-09): the harbor callbacks report DJ events;
        # the telnet reconciler only verifies (RASTATIME_DJ_RECONCILE_SECONDS).
        reconcile_interval_s=reconcile_interval_from_env(),
        # RASTATIME 2026-09-10 - /dj-auth: the harbors ask PLAYOUT, PLAYOUT
        # asks the web application (Settings / show Live Stream Input).
        dj_auth=DjAuthenticator(_dj_auth_web_url()),
        # RASTATIME 2026-09-28 - /live-text feeds the Live Text writer (must be
        # passed here: start_listener sets every handler attribute itself)
        live_text=live_text_writer,
    )
    logger.info(
        "DJ logins are checked against the web application at %s.",
        _dj_auth_web_url() or "<unset>",
    )

    # 8b. RASTATIME 2026-06-05 — Record-per-Hour cue sidecars (stage 5).
    # Wire the CueWriter BEFORE the first refresh so on-air callbacks can
    # mark from the start.  No-op while the 24/7 recorder is disabled.
    from libretime_playout.cue_writer import CueWriter  # noqa: PLC0415
    from libretime_playout.liquidsoap_config import (  # noqa: PLC0415
        read_hourly_recording_config_from_db as _read_247_cfg,
    )
    scheduler.set_cue_writer(CueWriter(_read_247_cfg))

    # 9. Initial schedule fetch
    scheduler.refresh()

    # 9b. Now that the listener is up, kick off the periodic pre-flight
    # timer chain.  Its first scan fires ~10 s later — by then the
    # scheduler has already done one refresh, so the lookahead view of
    # the schedule is consistent across both subsystems.
    try:
        preflight.start()
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning(
            "PreflightChecker failed to start (dashboard warnings won't "
            "appear): %s", exc,
        )

    # 9c. RASTATIME 2026-06-05 — 24/7 recording retention.  Daemon thread
    # that prunes archive day-folders older than the operator-configured
    # window.  Re-reads cc_pref each cycle; a complete no-op while the
    # recorder is disabled / retention_days is 0.
    from libretime_playout.liquidsoap_config import (  # noqa: PLC0415
        read_hourly_recording_config_from_db,
    )
    from libretime_playout.recording_retention import (  # noqa: PLC0415
        RecordingRetentionThread,
    )
    retention_thread = RecordingRetentionThread(
        read_hourly_recording_config_from_db
    )
    try:
        retention_thread.start()
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("Recording retention thread failed to start: %s", exc)

    # 10. Main poll loop
    logger.info(
        "RASTATIME-PLAYOUT: running. "
        "Schedule refreshes every %ds. "
        "Press Ctrl+C to stop.",
        _POLL_INTERVAL,
    )
    last_refresh = time.monotonic()

    try:
        while True:
            time.sleep(10)
            elapsed = time.monotonic() - last_refresh
            if elapsed >= _POLL_INTERVAL:
                scheduler.refresh()
                last_refresh = time.monotonic()

    except (KeyboardInterrupt, SystemExit):
        logger.info("RASTATIME-PLAYOUT: shutdown requested.")

    finally:
        logger.info("RASTATIME-PLAYOUT: shutting down …")
        try:
            switcher_server.shutdown()
        except Exception:  # pylint: disable=broad-exception-caught
            pass
        try:
            preflight.stop()
        except Exception:  # pylint: disable=broad-exception-caught
            pass
        try:
            retention_thread.stop()
        except Exception:  # pylint: disable=broad-exception-caught
            pass
        scheduler.shutdown()
        engine.close()
        logger.info("RASTATIME-PLAYOUT: stopped.")


if __name__ == "__main__":
    main()
