"""
liquidsoap_config — render the production rastatime.liq from
template + cc_pref settings.

RASTATIME 2026-05-26 — Seamless-Bus-Mix Phase C3.

The template (`backend/playout/config/rastatime.liq.template`) carries
a few placeholders that the operator's actual deployment fills in:

    ${TELNET_HOST}, ${TELNET_PORT}    Where Liquidsoap's command
                                       server listens.  The Python
                                       LiquidsoapPlayoutEngine talks
                                       to exactly this socket.
    ${LOG_FILE}                        Where Liquidsoap writes its
                                       per-line log.
    ${ICECAST_OUTPUTS}                 Rendered output.icecast(...)
                                       blocks, one per enabled
                                       stream_output_N entry in
                                       cc_pref.

This module:

  * `render_rastatime_liq(stream_outputs, *, telnet_host, telnet_port,
    log_file)`  — pure-Python rendering function (no I/O); takes the
    same list of stream-output dicts that `__main__._read_stream_outputs`
    produces and returns the rendered `.liq` source as a string.

  * `write_rastatime_liq(...)` — convenience wrapper that writes the
    rendered text atomically to disk, returning True if the file
    content changed compared to a previous run (so the caller can log
    "NSSM-restart required to pick up changes").

  * `main(argv)` — CLI entry-point so the operator can manually
    re-render with::

      python -m libretime_playout.liquidsoap_config render \\
          --out C:/Tools/liquidsoap/rastatime.liq

Why a render step and not env-var substitution at .liq load time?
We need the FULL output.icecast(...) block per enabled stream, with
the right codec / bitrate / mount / credentials.  Liquidsoap's
`environment.get` only substitutes scalar strings — it can't
conditionally synthesise a code block per Icecast mountpoint, and
hardcoding three blocks with three placeholder credentials would
either leak unused mounts (operator only configured 1) or silently
skip configured ones (operator configured 4).  A Python render step
adapts to whatever the operator has actually enabled in cc_pref.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# Template lives next to this module's config directory.
# In the repo: backend/playout/config/rastatime.liq.template
# In a deployed install the config dir typically ships next to the
# package so this same path works via importlib.resources fallback.
_DEFAULT_TEMPLATE_PATH = (
    Path(__file__).resolve().parent.parent / "config" / "rastatime.liq.template"
)

# Defaults match LiquidsoapTelnetClient + the Phase-A burn-in setup.
DEFAULT_TELNET_HOST = "127.0.0.1"
DEFAULT_TELNET_PORT = 1234
DEFAULT_LOG_FILE = "C:/rastatime/logs/liquidsoap.log"
# Default crossfade duration in seconds — matches the historical
# cc_pref.default_crossfade_seconds operator default.  Operator can
# override via the CLI / Pypo render-step, or set to 0. to disable
# crossfades entirely.
DEFAULT_CROSSFADE_DURATION = 2.0


# ---------------------------------------------------------------------
# Liquidsoap codec encoders per stream type
# ---------------------------------------------------------------------

# Validated on the operator's Liquidsoap 2.4.4 + FFmpeg build (Phase-A
# burn-in confirmed mp3 via libmp3lame); aac via FFmpeg's native AAC
# encoder; vorbis via libvorbis.  These are the same three formats the
# existing FfmpegStreamer can emit — keeps the operator's listener-side
# URLs unchanged when migrating from FFmpeg to Liquidsoap output.
_ENCODER_FOR_TYPE = {
    # FFmpeg-format string for output.icecast.  All three use the
    # %ffmpeg encoder so the binary build only needs FFmpeg libraries
    # (which the operator already validated in Phase A).
    "mp3":  '%ffmpeg(format="mp3", %audio(codec="libmp3lame", b="${BITRATE}k"))',
    "aac":  '%ffmpeg(format="adts", %audio(codec="aac", b="${BITRATE}k"))',
    "ogg":  '%ffmpeg(format="ogg", %audio(codec="libvorbis", b="${BITRATE}k"))',
}


# ---------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------


def _escape_liq_string(value: str) -> str:
    """
    Escape a Python string for inclusion in a Liquidsoap double-quoted
    string literal.  Liquidsoap's parser handles ``\\\\`` and ``\\"``;
    we only need to escape those two — single quotes pass through, line
    breaks should not occur in legitimate config values.
    """
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _render_icecast_block(stream: Dict) -> str:
    """
    Render one output.icecast(...) block from a stream_output_N dict.

    Required keys (silently skipped if missing): type, host, port,
    mount, pass.  Optional: user, name, description, bitrate, channels.

    Raises ValueError if ``type`` is not one of mp3 / aac / ogg, so
    the operator gets a loud failure rather than a silent omission.
    """
    stream_type = str(stream.get("type", "")).lower()
    if stream_type not in _ENCODER_FOR_TYPE:
        raise ValueError(
            f"Unsupported stream type {stream_type!r} — "
            f"must be one of {sorted(_ENCODER_FOR_TYPE)}"
        )

    bitrate = int(stream.get("bitrate", 128))
    encoder = _ENCODER_FOR_TYPE[stream_type].replace(
        "${BITRATE}", str(bitrate)
    )

    host = _escape_liq_string(str(stream.get("host", "localhost")))
    port = int(stream.get("port", 8000))
    mount_raw = str(stream.get("mount", "stream")).lstrip("/")
    mount = "/" + _escape_liq_string(mount_raw)
    password = _escape_liq_string(str(stream.get("pass", "")))
    user = _escape_liq_string(str(stream.get("user", "source") or "source"))
    name = _escape_liq_string(str(stream.get("name", "RASTATIME")))
    description = _escape_liq_string(
        str(stream.get("description", "RASTATIME live stream"))
    )

    # Render as a multi-line block matching Liquidsoap's stdlib style.
    # `restart_delay=5.` + `fallible=true` give us the operator-
    # requested indefinite-retry-with-5 s-backoff (per C3 Q2 decision).
    # The trailing comment names the mount so operator-side grep
    # against the rendered .liq is easy.
    return (
        "output.icecast(\n"
        f"  {encoder},\n"
        f'  host="{host}",\n'
        f"  port={port},\n"
        f'  user="{user}",\n'
        f'  password="{password}",\n'
        f'  mount="{mount}",\n'
        f'  name="{name}",\n'
        f'  description="{description}",\n'
        "  restart_delay=5.,\n"
        "  fallible=true,\n"
        "  bus,\n"
        f")  # mount {mount} type={stream_type} {bitrate}k\n"
    )


def _render_icecast_outputs(stream_outputs: List[Dict]) -> str:
    """
    Render all output.icecast(...) blocks back-to-back, separated by
    blank lines.  Empty list → returns a single comment line noting
    that no outputs are configured (Liquidsoap still runs, just
    doesn't actually emit anywhere — useful for telnet-only dev).
    """
    if not stream_outputs:
        return (
            "# (no stream outputs configured in cc_pref — "
            "Liquidsoap will run idle.  Pypo logs a warning at "
            "startup.)\n"
        )
    blocks = [_render_icecast_block(s) for s in stream_outputs]
    return "\n".join(blocks)


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------


def _format_crossfade_duration(value: float) -> str:
    """
    Format a crossfade-duration float for Liquidsoap.  Liquidsoap
    requires a trailing dot for floats — ``2`` is invalid, ``2.`` is
    fine.  We always include at least one fractional digit so the
    rendered file is unambiguously a float literal.

    Examples::

        >>> _format_crossfade_duration(0)
        '0.0'
        >>> _format_crossfade_duration(2.0)
        '2.0'
        >>> _format_crossfade_duration(2.5)
        '2.5'
        >>> _format_crossfade_duration(2.123456)
        '2.12'
    """
    rounded = round(float(value), 2)
    # Drop trailing zeros past one decimal but keep at least .0 so the
    # output is always recognisably a float literal.
    text = f"{rounded:.2f}"
    if text.endswith("0") and not text.endswith(".00"):
        text = text.rstrip("0")
    if text.endswith("."):
        text = text + "0"
    if text.endswith(".00"):
        text = text[:-2] + "0"
    return text


def render_rastatime_liq(
    stream_outputs: List[Dict],
    *,
    telnet_host: str = DEFAULT_TELNET_HOST,
    telnet_port: int = DEFAULT_TELNET_PORT,
    log_file: str = DEFAULT_LOG_FILE,
    crossfade_duration: float = DEFAULT_CROSSFADE_DURATION,
    template_path: Optional[Path] = None,
) -> str:
    """
    Render the production rastatime.liq from the template + the given
    stream-output configurations.

    Returns the full .liq source as a string.  No I/O — use
    :func:`write_rastatime_liq` for the file-write convenience wrapper.

    Parameters
    ----------
    stream_outputs : list of dict
        One dict per Icecast stream to emit; same shape as the
        ``stream_output_N`` JSON in cc_pref.  Required keys per
        entry: ``type`` (mp3/aac/ogg), ``host``, ``port``, ``mount``,
        ``pass``.  Optional: ``user``, ``name``, ``description``,
        ``bitrate``.
    telnet_host : str
        Where Liquidsoap's command server should bind.  127.0.0.1
        for safety unless the operator needs cross-host telnet (which
        they don't — RASTATIME is single-host).
    telnet_port : int
        Telnet port — must match LiquidsoapTelnetClient's port.
    log_file : str
        Path Liquidsoap writes its per-line log to.  Forward slashes
        even on Windows (Liquidsoap's path parser is happier with them).
    crossfade_duration : float
        Seconds of crossfade between consecutive request.queue items.
        Default 2.0 matches the historical operator preference.  Set
        to 0. to disable crossfades.  Phase-C7 will read this from
        cc_pref.default_crossfade_seconds at Pypo start.
    template_path : Path, optional
        Override the bundled template (mostly for tests).
    """
    template_path = template_path or _DEFAULT_TEMPLATE_PATH
    template = template_path.read_text(encoding="utf-8")

    icecast_blocks = _render_icecast_outputs(stream_outputs)

    rendered = (
        template
        .replace("${TELNET_HOST}", _escape_liq_string(telnet_host))
        .replace("${TELNET_PORT}", str(int(telnet_port)))
        .replace("${LOG_FILE}", _escape_liq_string(log_file))
        .replace(
            "${CROSSFADE_DURATION}",
            _format_crossfade_duration(crossfade_duration),
        )
        .replace("${ICECAST_OUTPUTS}", icecast_blocks)
    )
    return rendered


def write_rastatime_liq(
    output_path: Path,
    stream_outputs: List[Dict],
    *,
    telnet_host: str = DEFAULT_TELNET_HOST,
    telnet_port: int = DEFAULT_TELNET_PORT,
    log_file: str = DEFAULT_LOG_FILE,
    crossfade_duration: float = DEFAULT_CROSSFADE_DURATION,
    template_path: Optional[Path] = None,
) -> bool:
    """
    Render and atomically write rastatime.liq to ``output_path``.

    Returns True if the rendered content differs from the existing
    file at ``output_path`` (or the file did not exist), False if the
    content is byte-identical — useful so the caller can log
    "NSSM-restart required" only when something actually changed.

    Atomic-write strategy: write to ``<path>.tmp`` then os.replace.
    This keeps a partial write from leaving a broken .liq behind in
    the (unlikely) event of a power-loss mid-render.

    Writes UTF-8 without BOM — Liquidsoap's parser tripped over BOM
    bytes during the Phase-0 burn-in setup, so we explicitly avoid them.
    """
    rendered = render_rastatime_liq(
        stream_outputs,
        telnet_host=telnet_host,
        telnet_port=telnet_port,
        log_file=log_file,
        crossfade_duration=crossfade_duration,
        template_path=template_path,
    )

    previous: Optional[str] = None
    if output_path.exists():
        try:
            previous = output_path.read_text(encoding="utf-8")
        except OSError:
            previous = None

    if previous == rendered:
        return False  # nothing changed, no NSSM-restart needed

    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    tmp_path.write_text(rendered, encoding="utf-8", newline="\n")
    os.replace(tmp_path, output_path)
    return True


# ---------------------------------------------------------------------
# CLI — for manual re-rendering by the operator
# ---------------------------------------------------------------------


def _read_stream_outputs_from_db() -> List[Dict]:
    """
    Load the cc_pref ``stream_output_N`` rows (same shape Pypo reads).
    Returns [] if the Django ORM is unavailable — caller decides what
    to do.

    Kept here (mirrors `__main__._read_stream_outputs`) so this module
    can be used standalone by the CLI without dragging in Pypo bootstrap.
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
            except (json.JSONDecodeError, AttributeError) as exc:
                logger.warning(
                    "Could not parse stream_output_%d: %s", n, exc
                )
        return outputs
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("Could not read stream outputs from DB: %s", exc)
        return []


def _setup_django_if_available() -> bool:
    """
    Bring up just enough of the Django ORM for
    `_read_stream_outputs_from_db` to work.  Mirrors `__main__._setup_django`
    but lighter — no API health-check, just the Django config.

    Returns True on success, False otherwise.
    """
    try:
        import django  # type: ignore[import-untyped]  # noqa: PLC0415

        os.environ.setdefault(
            "DJANGO_SETTINGS_MODULE", "libretime_api.settings"
        )
        django.setup()
        return True
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("Django ORM bootstrap failed: %s", exc)
        return False


def main(argv: Optional[List[str]] = None) -> int:
    """
    CLI entry-point.  Usage::

        python -m libretime_playout.liquidsoap_config render \\
            --out C:/Tools/liquidsoap/rastatime.liq \\
            [--telnet-host 127.0.0.1] [--telnet-port 1234] \\
            [--log-file C:/rastatime/logs/liquidsoap.log]

    Reads stream outputs from cc_pref (via the Django ORM) and writes
    the rendered .liq file.  Exits 0 on success (with stdout message
    saying whether the file changed), non-zero on error.
    """
    parser = argparse.ArgumentParser(
        prog="python -m libretime_playout.liquidsoap_config",
        description="Render rastatime.liq from template + cc_pref settings.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    render = sub.add_parser(
        "render", help="Render rastatime.liq from template + DB."
    )
    render.add_argument(
        "--out", required=True, type=Path,
        help="Path to write the rendered .liq (e.g. C:/Tools/liquidsoap/rastatime.liq).",
    )
    render.add_argument(
        "--telnet-host", default=DEFAULT_TELNET_HOST,
        help=f"Liquidsoap telnet bind addr (default {DEFAULT_TELNET_HOST}).",
    )
    render.add_argument(
        "--telnet-port", type=int, default=DEFAULT_TELNET_PORT,
        help=f"Liquidsoap telnet port (default {DEFAULT_TELNET_PORT}).",
    )
    render.add_argument(
        "--log-file", default=DEFAULT_LOG_FILE,
        help=f"Liquidsoap log-file path (default {DEFAULT_LOG_FILE}).",
    )
    render.add_argument(
        "--crossfade-duration", type=float,
        default=DEFAULT_CROSSFADE_DURATION,
        help=(
            f"Crossfade duration in seconds between request.queue items "
            f"(default {DEFAULT_CROSSFADE_DURATION}, 0 disables)."
        ),
    )

    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if args.cmd == "render":
        if not _setup_django_if_available():
            logger.error(
                "Django ORM unavailable — cannot read cc_pref.  "
                "Make sure DJANGO_SETTINGS_MODULE is reachable and the "
                "DB is up."
            )
            return 2
        stream_outputs = _read_stream_outputs_from_db()
        logger.info(
            "Read %d enabled stream output(s) from cc_pref.",
            len(stream_outputs),
        )
        changed = write_rastatime_liq(
            args.out,
            stream_outputs,
            telnet_host=args.telnet_host,
            telnet_port=args.telnet_port,
            log_file=args.log_file,
            crossfade_duration=args.crossfade_duration,
        )
        if changed:
            logger.info(
                "Wrote %s (content changed — restart the "
                "RASTATIME-LIQUIDSOAP NSSM service to apply).",
                args.out,
            )
        else:
            logger.info(
                "%s already up-to-date — no NSSM restart needed.",
                args.out,
            )
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
