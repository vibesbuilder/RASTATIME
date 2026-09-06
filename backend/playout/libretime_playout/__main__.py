"""
RASTATIME-PLAYOUT — Liquidsoap (production) / libmpv (legacy) playout entry point.

Replaces the LibreTime / Liquidsoap playout daemon with a Windows-native
scheduler that:

  1. Polls RASTATIME-API (health gate) before entering the main loop.
  2. Reads Icecast output stream settings from ``cc_pref`` via Django ORM.
  3. Creates a local-playback engine (Liquidsoap in production; mpv legacy)
     for soundcard audio output.
  4. Creates FFmpeg streamers for Icecast output (one per enabled stream).
  5. Polls the schedule API every POLL_INTERVAL seconds and arms per-item
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
  RASTATIME_PLAYOUT_ENGINE     : "liquidsoap" (production, set via NSSM) | "mpv" (legacy default)
  RASTATIME_MPV_PATH           : directory containing libmpv-2.dll
                                 (default search: C:\\Tools\\mpv,
                                 C:\\Program Files\\mpv)
  RASTATIME_MPV_LOG_LEVEL      : mpv log verbosity (default "warn")
  RASTATIME_LIQUIDSOAP_HOST    : Liquidsoap telnet host (default 127.0.0.1)
  RASTATIME_LIQUIDSOAP_PORT    : Liquidsoap telnet port (default 1234)
  RASTATIME_LIQUIDSOAP_CONFIG_PATH
                               : where to render rastatime.liq
                                 (default C:/Tools/liquidsoap/rastatime.liq)
  RASTATIME_LIQUIDSOAP_LOG_PATH
                               : where Liquidsoap writes its log
                                 (default C:/rastatime/logs/liquidsoap.log)
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
from typing import Dict, List, Optional, Tuple

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
    missing/invalid key.  Drives the queue's track crossfade, the bus
    input transitions (0 = ducking) and the scheduler's drain time.  A
    UI change takes effect at the next PLAYOUT + LIQUIDSOAP restart
    ("Apply now" in Settings -> Local Machine).
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
    Settings -> General field) as a float, or None when the key is
    missing, empty, negative or not a number -- the caller then keeps
    the env/default value.  Same ORM path as :func:`_read_stream_outputs`.
    """
    try:
        from libretime_api.core.models import Preference  # type: ignore[import-untyped]
        raw = dict(Preference.site.values_list("key", "value")).get(
            "default_crossfade_duration"
        )
        if raw is None or str(raw).strip() == "":
            return None
        value = float(str(raw).strip())
        if value < 0:
            logger.warning(
                "cc_pref default_crossfade_duration=%r is negative - ignored", raw
            )
            return None
        return value
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("Could not read default_crossfade_duration from DB: %s", exc)
        return None


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
_LIQUIDSOAP_DEFAULT_CROSSFADE = 2.0


def _read_harbor_credentials() -> tuple:
    """
    Read ``stream.harbor.main_password`` / ``show_password`` from
    libretime.conf.  Returns (main_password, show_password) — either
    field is an empty string if missing.  Same direct-YAML-read
    pattern as :func:`_read_internal_listener_credentials`.

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


def _render_rastatime_liq(stream_outputs: List[Dict]) -> bool:
    """
    Render ``rastatime.liq`` from the operator-configured environment +
    ``cc_pref`` stream outputs.  Idempotent: writes only when content
    actually changed; returns that ``changed`` flag.

    RASTATIME 2026-09-05: split out of the startup wrapper so the
    scheduler's nightly quiet-window restart can re-render right before
    it restarts LIQUIDSOAP (fresh device resolution, fresh cc_pref).
    Every failure is logged here and then raised as
    :class:`_LiquidsoapRenderError`; the startup wrapper turns that
    into ``sys.exit(1)``, the nightly caller into a log line.
    """
    from libretime_playout.liquidsoap_config import (  # noqa: PLC0415
        DEFAULT_LINEIN_HTTP_MAX_BUFFER_SECONDS,
        read_hourly_recording_config_from_db,
        write_rastatime_liq,
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
    # Phase-D Stück-B (2026-05-28): fade_in / fade_out inside crossfade,
    # configurable so the operator can tune short-track audibility vs.
    # music-transition smoothness without a code-change.  Default 0.3 s
    # is short enough to give 3-5 s jingles most of their audio back
    # while still being noticeable as a smooth music-to-music transition.
    from libretime_playout.liquidsoap_config import (  # noqa: PLC0415
        DEFAULT_CROSSFADE_FADE_SECONDS as _DEFAULT_CROSSFADE_FADE,
    )
    try:
        crossfade_fade = float(
            os.environ.get(
                "RASTATIME_LIQUIDSOAP_CROSSFADE_FADE_SECONDS",
                str(_DEFAULT_CROSSFADE_FADE),
            )
        )
    except ValueError as exc:
        logger.critical(
            "RASTATIME_LIQUIDSOAP_CROSSFADE_FADE_SECONDS must be a float: %s",
            exc,
        )
        raise _LiquidsoapRenderError(str(exc)) from exc
    local_output_enabled = (
        os.environ.get("RASTATIME_LIQUIDSOAP_LOCAL_OUTPUT", "true").lower()
        not in ("false", "0", "no", "off")
    )

    # Phase-C4: DJ-Source harbor passwords aus libretime.conf.
    # Wenn unset, rendert der Renderer die input.harbor-Blöcke nicht
    # (= C3-Stand, nur scheduled queue auf dem Bus).
    harbor_main_pwd, harbor_show_pwd = _read_harbor_credentials()
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

    try:
        changed = write_rastatime_liq(
            config_path,
            stream_outputs,
            telnet_host=telnet_host,
            telnet_port=telnet_port,
            log_file=log_path,
            crossfade_duration=crossfade,
            crossfade_fade_seconds=crossfade_fade,
            local_output_enabled=local_output_enabled,
            local_output_device_id=local_output_device_id,
            local_output_device_label=local_output_device_label,
            local_output_endpoint_id=local_output_endpoint_id,
            local_output_device_name=local_output_device_name,
            linein_http_max_buffer_seconds=linein_http_max_buffer,
            harbor_main_password=harbor_main_pwd or None,
            harbor_show_password=harbor_show_pwd or None,
            hourly_recording_enabled=hourly["enabled"],
            hourly_recording_folder=hourly["folder"],
            hourly_recording_format=hourly["format"],
            hourly_recording_bitrate=hourly["bitrate"],
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
    return changed


def _render_rastatime_liq_at_startup(stream_outputs: List[Dict]) -> None:
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
        changed = _render_rastatime_liq(stream_outputs)
    except _LiquidsoapRenderError:
        sys.exit(1)
    if not changed:
        return

    from libretime_playout.liquidsoap_service import (  # noqa: PLC0415
        boot_restart_enabled,
        restart_liquidsoap_service,
        system_uptime_seconds,
        within_boot_window,
    )

    uptime = system_uptime_seconds()
    if boot_restart_enabled() and within_boot_window(uptime):
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
        return

    logger.warning(
        "Rendered rastatime.liq (content changed).  RESTART the "
        "RASTATIME-LIQUIDSOAP NSSM service so it picks up the new "
        ".liq:   nssm restart RASTATIME-LIQUIDSOAP"
    )


def _read_internal_listener_credentials() -> tuple:
    """
    Read the RASTATIME-specific ``stream.internal_listener`` credentials
    from libretime.conf.

    These are not part of the Pydantic schema used by ``_load_config``
    so we re-parse the YAML directly.  Used by PlayoutScheduler to log in
    to /main and /show as a listener when relaying live DJ audio to
    the public outputs.

    Returns (user, password) — both empty strings if the section is
    missing or unreadable.
    """
    try:
        import yaml  # noqa: PLC0415

        with open(_CONFIG_FILE, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
        section = (raw.get("stream") or {}).get("internal_listener") or {}
        user = str(section.get("user") or "")
        password = str(section.get("password") or "")
        return (user, password)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning(
            "Could not read stream.internal_listener from %s: %s",
            _CONFIG_FILE, exc,
        )
        return ("", "")


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
    if django_ok:
        stream_outputs = _read_stream_outputs()
        if stream_outputs:
            logger.info(
                "Found %d enabled Icecast stream output(s) — "
                "FFmpeg will stream to Icecast alongside local playback.",
                len(stream_outputs),
            )
        else:
            logger.info("No stream outputs configured in cc_pref.")
    else:
        logger.info("Django unavailable — local playback only (no Icecast egress).")

    # 5. Initialise the local-playback engine.
    #
    # Default is mpv (libmpv 0.41+) since libVLC 3.x on Windows chokes
    # on Icecast's icy-* reply headers when reading URL-auth-gated
    # mounts like /main and /show — it falls back to icyx://, drops
    # the Authorization header, and emits "playback error" while
    # staying silent.  mpv has none of those quirks and is actively
    # maintained.
    #
    # RASTATIME 2026-05-25/26 — Seamless-Bus-Mix Phase C7: third option
    # 'liquidsoap' fully wired (C1-C3+C6).  Setting
    # RASTATIME_PLAYOUT_ENGINE=liquidsoap triggers a one-shot render of
    # rastatime.liq from the operator's cc_pref settings, then connects
    # the LiquidsoapPlayoutEngine to a long-running Liquidsoap NSSM
    # service over telnet (default 127.0.0.1:1234).  Default stays
    # 'mpv'; switching is a deliberate operator action.  C4 (DJ-sources
    # via input.harbor) and C5 (recording via output.file) are not yet
    # active in the rendered .liq — both are scheduled for a separate
    # Phase-C iteration.
    engine_kind = os.environ.get("RASTATIME_PLAYOUT_ENGINE", "mpv").lower()

    # RASTATIME 2026-05-28 — Phase-D: Liquidsoap is the production
    # engine.  Legacy mpv and VLC engine modes are DEPRECATED — they
    # will be removed once Phase-E (Webstreams → Liquidsoap
    # input.http) and Phase-F (Line-Inputs → Liquidsoap input.wasapi)
    # are done.  Until then mpv stays around as the fallback for
    # those two not-yet-ported schedule-item types.  Recording
    # already requires Liquidsoap since C5 Teil 2d (FfmpegRecorder
    # deleted).  Operator-decision 2026-05-28.
    if engine_kind == "mpv":
        logger.warning(
            "DEPRECATED: RASTATIME_PLAYOUT_ENGINE=mpv is now legacy. "
            "Liquidsoap (RASTATIME_PLAYOUT_ENGINE=liquidsoap) is the "
            "production engine since Phase-C5 (2026-05-28); mpv remains "
            "only as a fallback and will be removed in a later cleanup. "
            "Recording already requires the Liquidsoap engine.",
        )

    try:
        if engine_kind == "mpv":
            from libretime_playout.engine.mpv_engine import MpvPlayoutEngine  # noqa: PLC0415
            engine = MpvPlayoutEngine()
            logger.info("Local-playback engine: mpv (libmpv) [DEPRECATED]")
        elif engine_kind == "liquidsoap":
            from libretime_playout.engine.liquidsoap_engine import LiquidsoapPlayoutEngine  # noqa: PLC0415

            # RASTATIME 2026-05-26 — Phase C7.  Render the production
            # rastatime.liq from the cc_pref stream-output rows + the
            # operator-configured paths.  Idempotent (rewrites only
            # when content actually changed); operator must restart
            # the RASTATIME-LIQUIDSOAP NSSM service to pick up changes
            # — we deliberately do NOT bounce the service ourselves
            # because doing so silently would mask configuration bugs
            # (the operator wants the dry-run-then-confirm cycle on
            # production-credential changes).
            _render_rastatime_liq_at_startup(stream_outputs)

            engine = LiquidsoapPlayoutEngine()
            logger.info(
                "Local-playback engine: Liquidsoap (Phase-C2+C3+C6 fully wired). "
                "Telnet target %s:%d.",
                engine._telnet._host, engine._telnet._port,
            )
        else:
            logger.critical(
                "Unknown RASTATIME_PLAYOUT_ENGINE=%r — must be 'mpv' or 'liquidsoap'.",
                engine_kind,
            )
            sys.exit(1)
    except RuntimeError as exc:
        logger.critical("%s engine failed to initialise: %s", engine_kind.upper(), exc)
        if engine_kind == "mpv":
            logger.critical(
                "Ensure libmpv-2.dll is at C:\\Tools\\mpv\\ (or set "
                "RASTATIME_MPV_PATH) and python-mpv is installed in the "
                "playout venv."
            )
        elif engine_kind == "liquidsoap":
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
    # in Django on port 8765.  It must therefore point at the public
    # frontend URL (config.general.public_url, e.g. http://192.168.1.192).
    public_url = str(config.general.public_url).rstrip("/")
    from libretime_api_client.v1 import BaseApiClient as ApiClientV1  # noqa: PLC0415
    api_client_v1 = ApiClientV1(
        base_url=public_url,
        api_key=config.general.api_key,
    )
    logger.info("Legacy v1 API client base URL: %s", public_url)

    # 6b. Listener-stats collector (BACKLOG "Analytics: Listener Stats
    # sammeln keine Daten", fixed 2026-08-30).  Upstream started this
    # thread only in the orphaned main.py — the active entry point never
    # did, so cc_listener_count stayed empty forever.  The outputs are
    # rebuilt from cc_pref on every poll cycle (same hot-reload idea as
    # read_streams below); libretime.conf's stream.outputs list is empty
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
    # If Django ORM is up, pass _read_stream_outputs as a callable so the
    # scheduler can hot-reload stream-output settings on every refresh —
    # users can change Stream 1/2/3 in the Frontend and the running playout
    # picks up the changes within one poll cycle, no service restart.
    read_streams = _read_stream_outputs if django_ok else None
    # RASTATIME 2026-05-26 — Seamless-Bus-Mix Phase C7 follow-up.
    # When the Liquidsoap engine is active, Liquidsoap owns the
    # Icecast PUTs entirely (one persistent stream per mount in the
    # rendered rastatime.liq).  Tell the scheduler NOT to spawn the
    # legacy FfmpegStreamer subprocesses — they would fight Liquidsoap
    # for the same mounts and lose with 403 "mount taken".
    streaming_handled_externally = (engine_kind == "liquidsoap")

    # RASTATIME 2026-09-05 - nightly quiet-window restart of LIQUIDSOAP
    # (memory-leak safety net).  Only with the Liquidsoap engine, and the
    # re-render before the restart needs the ORM for cc_pref.
    from libretime_playout.liquidsoap_service import NightlyRestartPolicy  # noqa: PLC0415
    nightly_policy = (
        NightlyRestartPolicy.from_env() if engine_kind == "liquidsoap" else None
    )
    render_for_restart = (
        (lambda: _render_rastatime_liq(_read_stream_outputs()))
        if (django_ok and engine_kind == "liquidsoap") else None
    )
    if nightly_policy is not None and nightly_policy.enabled:
        logger.info(
            "Nightly Liquidsoap restart window starts at %s local time "
            "(%s to change, 'off' to disable).",
            nightly_policy.start.strftime("%H:%M"),
            "RASTATIME_LIQUIDSOAP_NIGHTLY_RESTART",
        )

    scheduler = PlayoutScheduler(
        engine=engine,
        api_client=api_client,
        api_client_v1=api_client_v1,
        storage_path=storage_path,
        stream_outputs=stream_outputs,
        render_liquidsoap=render_for_restart,
        nightly_restart=nightly_policy,
        read_stream_outputs=read_streams,
        streaming_handled_externally=streaming_handled_externally,
        input_transition_seconds=_resolve_crossfade_seconds(),
    )
    # RASTATIME 2026-09-04 - a previous Pypo may have died mid-prepare
    # with a bus gate closed; open both before the first refresh.
    # RASTATIME 2026-09-06 - the constructor tried once (recording
    # sentinel stop + gates); when Liquidsoap was not up yet (manual
    # restart order, boot-window restart, nightly restart) a daemon
    # thread keeps trying until telnet answers.
    scheduler.reset_gates()
    scheduler.ensure_liquidsoap_initial_state()

    # Listener credentials for relaying /main and /show into the
    # public outputs.  Without these the icecast-listener-allow
    # endpoint will reject our listen request with 401.
    listener_user, listener_pass = _read_internal_listener_credentials()
    if listener_user and listener_pass:
        logger.info(
            "Listener credentials configured for /main and /show (user=%s)",
            listener_user,
        )
    else:
        logger.warning(
            "stream.internal_listener.user / .password missing from "
            "libretime.conf — Master / Show relays will fail with 401."
        )
    scheduler.set_listener_credentials(listener_user, listener_pass)

    # 7b. Restore the operator-selected audio output device.
    # SoundcardSettings is the singleton table written by
    # /api/v2/audio/soundcard-settings.  We read it directly via the
    # Django ORM so the engine starts on the right soundcard from the
    # first track onwards — without this, mpv would default to the
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
    from libretime_playout.source_switcher import (  # noqa: PLC0415
        SourceSwitcher,
        start_listener,
    )
    switcher = SourceSwitcher(switch_callback=scheduler.switch_audio_source)
    scheduler.set_source_switcher(switcher)
    switcher_server = start_listener(
        switcher,
        scheduler=scheduler,   # /reload-schedule needs the scheduler too
        preflight=preflight,   # …and the preflight scanner for instant rescan
        host="127.0.0.1",
        port=8770,
        engine_kind=engine_kind,  # Phase-C4 Teil 2: picks Icecast vs Liquidsoap-telnet reconciler
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
