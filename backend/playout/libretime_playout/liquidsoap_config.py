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

# Default fade-in / fade-out duration inside the crossfade operator
# (in seconds).  Liquidsoap's `crossfade()` defaults are fade_in=3.0
# and fade_out=3.0; with our `duration=1.0` config those would be
# clamped down to 1.0, but even 1.0 fade-in eats the first 1 s of a
# 3-5 s jingle (StationID), making short tracks barely audible.
#
# 0.0 s — HARD CUTS BETWEEN ALL TRACKS — is the Phase-D Stück-B
# operator-decision (2026-05-28).  Rationale: short jingles
# (StationIDs, 2-10 s) MUST play at 100 % of their original length
# for the station-identity to come through.  Any fade-in/fade-out
# zone shortens the audible portion and an even tiny 0.3 s fade
# halves the perceived loudness of a 3 s ID.
#
# Trade-off: music-to-music transitions become abrupt cuts instead
# of smooth crossfades.  The operator accepts this for now; the
# smarter "per-track fade decision based on track length" is in
# the BACKLOG (Phase-D-Polish — smarter short-track handling).
#
# Operator can tune via RASTATIME_LIQUIDSOAP_CROSSFADE_FADE_SECONDS
# env-var (e.g. 0.3 or 0.5 for a softer music transition, at the
# cost of shorter jingles).
DEFAULT_CROSSFADE_FADE_SECONDS = 0.0

# Whether to emit a Liquidsoap output to the local soundcard.  On the
# Windows-only RASTATIME deployment this is `output.wasapi`, defaulting
# to the OS-default audio endpoint.  Set RASTATIME_LIQUIDSOAP_LOCAL_OUTPUT=false
# for headless server installs that don't want a soundcard output.
DEFAULT_LOCAL_OUTPUT_ENABLED = True

# Phase-C4: default Liquidsoap-Harbor port for DJ-Master + DJ-Show
# sources.  Operator-decision from 2026-05-25 said port 8001 (Master) /
# 8002 (Show), matching libretime_shared's MainHarborInput/
# ShowHarborInput defaults.  But the C4 reality-test 2026-05-27 turned
# up a Liquidsoap-2.4.4 bug: two ``input.harbor`` calls with different
# ports silently let only ONE of the harbor servers fully come up
# (the second one's mount registers in the log but accepts no
# connections).  Workaround: register both mounts on the SAME port.
# Liquidsoap's harbor design natively supports multiple mountpaths on
# one port (like Icecast does with mount paths on port 8000).  So we
# bind both ``/main`` and ``/show`` to a single port (default 8001).
#
# Operator implication: BUTT/Mixxx/Traktor Show-source configs need
# port 8001 too — same port as Master, different mount.
DEFAULT_HARBOR_PORT = 8001
DEFAULT_HARBOR_MAIN_MOUNT = "main"
DEFAULT_HARBOR_SHOW_MOUNT = "show"

# Legacy aliases kept for back-compat with older Pypo deployments that
# still pass distinct main/show ports — both resolve to DEFAULT_HARBOR_PORT
# when no explicit value is given.  Renderer treats main + show ports
# as independent kwargs so an operator can keep them on different ports
# if they accept the 2.4 silent-fail risk.
DEFAULT_HARBOR_MAIN_PORT = DEFAULT_HARBOR_PORT
DEFAULT_HARBOR_SHOW_PORT = DEFAULT_HARBOR_PORT
# Buffer in seconds for input.harbor — soaks up small DJ-side
# disconnects (Wi-Fi blip, USB-soundcard switch) and harbor-side
# buffer-empty events that would otherwise cause source.is_ready() to
# flicker false→true and produce <1 s scheduled-track audio bleeding
# through during an active DJ session.
#
# 2026-05-25: initially set to 2 s as a starting point.
# 2026-05-28: increased to 5 s after Phase-D Stück-B live-test showed
# <1 s scheduled-track audio bleeding through while master_dj /
# show_dj were connected and producing audio.  The 5 s buffer
# tolerates short network spikes / encoder-side hiccups without
# the harbor source momentarily reporting not-ready.  Trade-off:
# +3 s additional DJ-to-air latency.
DEFAULT_HARBOR_BUFFER_SECONDS = 5.0


# ---------------------------------------------------------------------
# Phase-E — Scheduled Webstreams via input.http (RASTATIME 2026-05-29)
# ---------------------------------------------------------------------

# Whether to emit the webstream input.http block + switch-arm.  Defaults
# to True for the Liquidsoap engine path (the only one Phase-D ships
# with, and the only one Phase-E targets).  The Phase-D-deprecated
# mpv/VLC engine paths set this to False so the rendered .liq stays
# minimal — those code paths still handle webstreams via the legacy
# mpv adapter and never use the Liquidsoap webstream source.
DEFAULT_WEBSTREAM_ENABLED = True

# input.http max_buffer in seconds — how much audio Liquidsoap pre-
# fetches before it considers the source "ready".  Larger values
# tolerate longer network hiccups (e.g. brief CDN reconnects) but
# delay the moment source.is_ready flips true after a fresh
# webstream.start.  10 s is the operator-tested sweet-spot for the
# typical Internet-radio streams Phase-E targets — large enough to
# absorb a 5 s pause without source.is_ready flickering false.
DEFAULT_WEBSTREAM_MAX_BUFFER_SECONDS = 10.0

# input.http connect-timeout in seconds.  If the upstream HTTP server
# doesn't respond within this window, input.http retries after
# poll_delay seconds.  10 s matches Liquidsoap's own stdlib default;
# we expose it so the operator can shorten / lengthen for specific
# network conditions.
DEFAULT_WEBSTREAM_TIMEOUT_SECONDS = 10.0

# input.http reconnect-poll-delay in seconds.  When a connection drops
# (network blip, server-side restart, etc.) Liquidsoap retries every
# poll_delay seconds.  2 s is the stdlib default and gives a quick
# recovery without hammering the upstream server.
DEFAULT_WEBSTREAM_POLL_DELAY_SECONDS = 2.0


# ---------------------------------------------------------------------
# Phase-F — Scheduled Line-Inputs via input.http (RASTATIME 2026-05-29)
# ---------------------------------------------------------------------

# Whether to emit the linein input.http block + switch-arm.  Defaults
# to True for the Liquidsoap engine path.  The Phase-D-deprecated
# mpv/VLC engine paths set this to False — those code paths still
# handle line-inputs via the legacy mpv adapter + the existing
# FfmpegLineinCapture watchdog.
DEFAULT_LINEIN_ENABLED = True

# The local Icecast mount that FfmpegLineinCapture streams to.  Fixed
# at this URL because FfmpegLineinCapture has its own hard-coded
# listen URL — there is only ever one capture instance, with one
# operator-selected device active at a time, on this one mount.
# Liquidsoap's input.http connects to this URL when Pypo signals a
# scheduled line-input start.
DEFAULT_LINEIN_LISTEN_URL = "http://localhost:8000/linein-capture"

# Same buffer / timeout / poll-delay semantics as webstream — the
# capture stream is HTTP from localhost, so jitter should be much
# lower than from a public Internet webstream.  We keep the same
# defaults for consistency, but the renderer accepts overrides.
DEFAULT_LINEIN_MAX_BUFFER_SECONDS = 10.0
DEFAULT_LINEIN_TIMEOUT_SECONDS = 10.0
DEFAULT_LINEIN_POLL_DELAY_SECONDS = 2.0


# ---------------------------------------------------------------------
# Liquidsoap codec encoders per stream type
# ---------------------------------------------------------------------

# Validated on the operator's Liquidsoap 2.4.4 + FFmpeg build (Phase-A
# burn-in confirmed mp3 via libmp3lame); aac via FFmpeg's native AAC
# encoder; vorbis via libvorbis.  These are the same three formats the
# existing FfmpegStreamer can emit — keeps the operator's listener-side
# URLs unchanged when migrating from FFmpeg to Liquidsoap output.
_ENCODER_FOR_TYPE = {
    # FFmpeg-format string for output.icecast.  All four use the
    # %ffmpeg encoder so the binary build only needs FFmpeg libraries
    # (which the operator already validated in Phase A).  Matches the
    # cc_pref.stream_output_N "type" values FfmpegStreamer accepts
    # in the legacy mpv/VLC path — see _FFMPEG_CODEC_MAP in
    # ffmpeg_streamer.py for the parallel mapping.
    #
    # samplerate=… is mandatory: Liquidsoap's internal frame
    # samplerate defaults to 44100 Hz, but Opus's libopus encoder
    # REJECTS anything that isn't 8/12/16/24/48 kHz, and the AAC
    # encoder is happier at 44.1 / 48 kHz too.  FFmpeg does the
    # resampling automatically when this encoder samplerate differs
    # from Liquidsoap's PCM input rate.
    "mp3":  '%ffmpeg(format="mp3",  %audio(codec="libmp3lame", b="${BITRATE}k", samplerate=${SAMPLERATE}))',
    "aac":  '%ffmpeg(format="adts", %audio(codec="aac",        b="${BITRATE}k", samplerate=${SAMPLERATE}))',
    "ogg":  '%ffmpeg(format="ogg",  %audio(codec="libvorbis",  b="${BITRATE}k", samplerate=${SAMPLERATE}))',
    "opus": '%ffmpeg(format="ogg",  %audio(codec="libopus",    b="${BITRATE}k", samplerate=${SAMPLERATE}))',
}

# Samplerates accepted by libopus (Hz).  Anything else gets clamped to
# 48000 with a warning at render time — same policy as FfmpegStreamer's
# legacy mpv/VLC path uses (see _OPUS_VALID_SAMPLERATES in
# ffmpeg_streamer.py).
_OPUS_VALID_SAMPLERATES = {8000, 12000, 16000, 24000, 48000}

# Default samplerate when the cc_pref row doesn't carry one.  44100 Hz
# matches Liquidsoap's internal frame samplerate so no resampling is
# needed for mp3/aac/ogg-vorbis.  Opus gets clamped to 48000.
DEFAULT_SAMPLERATE = 44100


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
    try:
        samplerate = int(stream.get("samplerate") or DEFAULT_SAMPLERATE)
    except (TypeError, ValueError):
        samplerate = DEFAULT_SAMPLERATE

    # Opus is picky about samplerates — clamp invalid rates to 48000
    # with a warning, same policy FfmpegStreamer uses.  Other codecs
    # accept anything FFmpeg knows about (most modern rates), so we
    # don't second-guess them.
    if stream_type == "opus" and samplerate not in _OPUS_VALID_SAMPLERATES:
        logger.warning(
            "Stream samplerate %d Hz not supported by libopus; "
            "clamping to 48000 Hz for mount %r",
            samplerate, stream.get("mount", "?"),
        )
        samplerate = 48000

    encoder = (
        _ENCODER_FOR_TYPE[stream_type]
        .replace("${BITRATE}", str(bitrate))
        .replace("${SAMPLERATE}", str(samplerate))
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
    # `fallible=true` allows the output to fail on Icecast unavailable
    # — Liquidsoap then auto-reconnects on its own internal back-off
    # schedule (3 s default in 2.4.x), giving us the operator-requested
    # "indefinite retry" behaviour from C3 Q2 even without an explicit
    # callback.  We intentionally do NOT pass `on_error` because
    # Liquidsoap 2.4 changed its signature to a record-typed callback
    # (`(restart_in : _, ...) -> _`) whose exact form is non-trivial
    # to render correctly across operator's burn-in build versions;
    # the default retry is good enough for production.  (Phase-C8
    # follow-up: nail down the 2.4.x on_error signature and re-add a
    # custom 5 s back-off if operator wants tighter control.)
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


def _render_local_output_block(enabled: bool) -> str:
    """
    Render the local soundcard output block.  When enabled, emits a
    Liquidsoap ``output.portaudio`` call that plays the bus to the
    OS-default audio endpoint via PortAudio (cross-platform; on
    Windows that's a WASAPI/DirectSound device).  When disabled,
    emits a single comment line so the operator can grep + see it
    was deliberately turned off (avoiding "the line just vanished"
    confusion).

    Why portaudio and not wasapi: the Phase-C8 reality-test
    2026-05-26 showed the savonet Liquidsoap 2.4.4 Windows build
    does NOT ship ``output.wasapi`` — ``--list-functions | Select-String
    "^output\\."`` only listed ``output.portaudio``, ``output.ao``,
    ``output.audio_video`` and ``output.external`` as local audio
    sinks.  portaudio is the most natural choice for a Windows-only
    deployment.

    Why fallible=true: if the audio endpoint disappears at runtime
    (USB device unplugged, audio service restart) we want Liquidsoap
    to log and retry, not crash the whole subprocess and drop the
    Icecast PUTs.

    Why the buffer + clock.assign_new wrap (RASTATIME 2026-05-28 —
    Phase-C5 follow-up — echter Bus-Split, BACKLOG-Fix vorgezogen):

    The C5 reality-test (2026-05-28 01-:25 show-record test) caught
    a PortAudio underflow that took the WHOLE Liquidsoap process
    down mid-recording (killed all three Icecast PUTs AND the
    output.file recording with it):

        [clock:2] Source output.portaudio failed while streaming:
            Failure("Portaudio error in write_stream: Output underflowed")!
        [main:3] Shutdown started!

    NSSM auto-restarted with ~5 s downtime, but the half-written
    recording file was lost (post-restart state is sentinel default).

    Root cause: the first-attempt ``clock.assign_new`` (Phase-C4)
    only RENAMED the clock — all sources still shared the same
    actual worker clock because they all referenced the same ``bus``
    variable.  Liquidsoap's source-graph dependency analysis pulls
    sources into a common clock when they have a common upstream.

    Real fix: use ``buffer()`` to create an asynchronous bridge
    between ``bus`` (main clock) and ``output.portaudio`` (its own
    clock).  ``buffer`` is the canonical Liquidsoap pattern for a
    clock-crossing audio bridge: it queues up to ``buffer`` seconds
    of audio that the downstream output reads independently of the
    upstream's tick rate.  When PortAudio underflows the buffer
    absorbs it; only the local soundcard hears a small dropout, the
    Icecast PUTs + recording stay rock-solid.

    Trade-off: 0.5 s of audio latency on the local monitor speakers
    relative to the Icecast/recording timeline.  Acceptable for
    operator-monitoring purposes (you can still hear "is the
    stream going?"; you just hear it 500 ms late).

    First fix-attempt ``clock_safe=true`` on output.portaudio
    didn't work — Liquidsoap 2.4.4 removed that parameter
    (Error 6: "no argument labeled clock_safe").

    We need ``ignore(...)`` around the clock.assign_new because
    Liquidsoap 2.4 returns the (re-clocked) source list from
    assign_new — without ignore, the parser warns about an
    unused value at top-level.
    """
    if enabled:
        return (
            "# Echter Bus-Split fuer PortAudio (Phase-C5 follow-up v2 2026-05-28).\n"
            "# v1 (clock.assign_new just on output.portaudio) didn't work --\n"
            "# Liquidsoap greedily merges clocks via shared-upstream and\n"
            "# optimised the buffer() into a no-op.  C5 reality-test 01:15:10\n"
            "# still crashed with PortAudio underflow, dragging all outputs\n"
            "# (icecast x3 + recording) down with it.\n"
            "# v2 fix: assign the BUFFER itself to portaudio_clock (not the\n"
            "# output).  The buffer is the source that has two clock-sides;\n"
            "# putting it in a separate clock forces Liquidsoap to instantiate\n"
            "# the bridge.  sync=cpu drives the portaudio_clock from wall-time\n"
            "# instead of from any audio source, decoupling it from the main\n"
            "# pipeline's tick rate.  Buffer bumped to 2.0 s to absorb longer\n"
            "# CPU/disk stalls (the C5 crash was ~10 s after Show-start, at\n"
            "# track-decode peak).  Trade-off: lokales Monitor-Speaker laeuft\n"
            "# 2 s hinter Stream/Recording.\n"
            "bus_for_portaudio = buffer(buffer=2.0, bus)\n"
            "ignore(clock.assign_new(id=\"portaudio_clock\", sync=\"cpu\", [\n"
            "  bus_for_portaudio,\n"
            "]))\n"
            "output.portaudio(\n"
            "  fallible=true,\n"
            "  bus_for_portaudio,\n"
            ")\n"
        )
    return (
        "# (local output disabled via RASTATIME_LIQUIDSOAP_LOCAL_OUTPUT=false)\n"
    )


def _render_harbor_inputs_block(
    *,
    main_password: Optional[str],
    show_password: Optional[str],
    main_port: int,
    show_port: int,
    main_mount: str,
    show_mount: str,
    buffer_seconds: float,
) -> str:
    """
    Render the Liquidsoap ``input.harbor`` block(s) for the DJ-Master
    and DJ-Show sources.  Each side is rendered independently — the
    operator can enable just Master, just Show, both, or neither.

    Wenn beide Passwörter unset sind, returnt diese Funktion einen
    comment-only stub.  Der Bus-Source-Render-Helper (siehe
    :func:`_render_bus_source_block`) sieht das gleiche Flag und
    wählt entsprechend zwischen `bus = scheduled` und dem switch.

    icy=true sagt input.harbor, dass es ICY-Metadata vom DJ-Client
    akzeptieren soll (Track-Title + Artist die BUTT/Mixxx schickt).
    buffer=2. soakt typische Wi-Fi-Mikro-Disconnects.

    Each block tagged with id="master_dj" / id="show_dj" so the
    Pypo-side source-switcher (Phase C4 Teil 2) can poll
    ``master_dj.status`` / ``show_dj.status`` via telnet.
    """
    parts = []
    if main_password:
        parts.append(
            "master_dj = input.harbor(\n"
            f'  "{_escape_liq_string(main_mount)}",\n'
            f"  id=\"master_dj\",\n"
            f"  port={int(main_port)},\n"
            f'  password="{_escape_liq_string(main_password)}",\n'
            f"  buffer={_format_crossfade_duration(buffer_seconds)},\n"
            "  icy=true,\n"
            ")\n"
        )
    if show_password:
        parts.append(
            "show_dj = input.harbor(\n"
            f'  "{_escape_liq_string(show_mount)}",\n'
            f"  id=\"show_dj\",\n"
            f"  port={int(show_port)},\n"
            f'  password="{_escape_liq_string(show_password)}",\n'
            f"  buffer={_format_crossfade_duration(buffer_seconds)},\n"
            "  icy=true,\n"
            ")\n"
        )
    if not parts:
        return (
            "# (no DJ-source harbor enabled — stream.harbor.{main,show}_password\n"
            "#  are unset in libretime.conf; bus stays on the scheduled queue)\n"
        )
    return "\n".join(parts)


def _render_webstream_input_block(
    *,
    enabled: bool,
    max_buffer_seconds: float = DEFAULT_WEBSTREAM_MAX_BUFFER_SECONDS,
    timeout_seconds: float = DEFAULT_WEBSTREAM_TIMEOUT_SECONDS,
    poll_delay_seconds: float = DEFAULT_WEBSTREAM_POLL_DELAY_SECONDS,
) -> str:
    """
    Render the ``input.http`` block for scheduled webstreams (Phase E).

    When ``enabled`` is True, emits a Liquidsoap ``input.http`` source
    initialised with ``start=false`` (no HTTP connection at boot) and
    an empty URL.  Pypo's :meth:`LiquidsoapPlayoutEngine.webstream_start`
    drives the runtime cycle:

        webstream.set_url <url>          # set URL via input.http method
        webstream.gain.set <linear>      # set per-stream amplify factor
        webstream.start                  # establish HTTP connection

    The source goes ``source.is_ready=true`` once max_buffer worth of
    audio is queued; the switch operator in :func:`_render_bus_source_block`
    flips the bus to webstream at that moment.  ``webstream.stop`` at
    show-end tears the connection down and the switch falls through to
    scheduled.

    A separate ``amplify`` wrapper applies the per-webstream input gain
    (cc_webstream.input_gain_db) as a linear factor controlled via the
    ``webstream.gain`` interactive variable.  Pypo converts dB→linear
    in Python (10 ** (dB/20)) before pushing the value, so the
    Liquidsoap side stays a simple multiplication.  Default 1.0 = unity.

    When ``enabled`` is False (legacy mpv/VLC engine paths), emits a
    single comment line — keeps the bus chain unchanged for non-Liquidsoap
    deployments and prevents the switch-arm from referencing a missing
    source.

    Why ``start=false`` and not eagerly connecting: idle bandwidth and
    CPU cost for a permanent HTTP connection that's only needed during
    scheduled webstream shows.  Start-on-demand is also kinder to the
    upstream server (no Liquidsoap-side reconnect loop on a stream
    nobody is actively listening to).
    """
    if not enabled:
        return (
            "# (webstream input.http disabled — Liquidsoap engine not\n"
            "#  active; legacy mpv/VLC handles webstreams via separate path)\n"
        )
    # self_sync=false + buffer() wrapper are BOTH required for crossfade
    # compatibility.  Phase-E 2026-05-29 reality-test discovered:
    #
    # 1. self_sync=false ALONE is not enough.  Liquidsoap's crossfade
    #    operator still rejects input.http with "Error 7: Invalid value:
    #    This source may control its own latency and cannot be used with
    #    this operator." at startup (compile-time source-graph check
    #    based on the input.http Funktionssignatur, not the actual
    #    runtime parameter).
    #
    # 2. buffer() wrapper provides an asynchronous clock-bridge between
    #    input.http's HTTP-stream clock and the main bus clock — same
    #    canonical pattern as the PortAudio bus-split in
    #    _render_local_output_block.  This makes the source consumable
    #    by crossfade.
    #
    # Cost: ~5 s additional latency from webstream-source-audio to
    # listener (was 2 s pre-polish — bumped to 5 s after Phase-E
    # reality-test caught a ~2 s "Haker" 12 s into the show when both
    # input.http's max_buffer AND the clock-bridge buffer underran
    # within seconds of each other, briefly flipping the switch off
    # webstream).  Acceptable trade-off for live-radio scheduled
    # webstreams; the listener-side player adds ~10 s buffer of its
    # own so the effective initial-show-delay is dominated by that.
    #
    # max_buffer (10 s default) of input.http absorbs upstream-server
    # jitter; buffer (5 s) absorbs the clock-bridge tick-drift and the
    # initial-connect cold-buffer rebuild.
    return (
        "webstream_raw = input.http(\n"
        '  id="webstream",\n'
        "  start=false,\n"
        "  self_sync=false,\n"
        f"  max_buffer={_format_crossfade_duration(max_buffer_seconds)},\n"
        f"  timeout={_format_crossfade_duration(timeout_seconds)},\n"
        f"  poll_delay={_format_crossfade_duration(poll_delay_seconds)},\n"
        '  "",\n'
        ")\n"
        "\n"
        "# Per-webstream input-gain wrapper — Pypo sets the linear factor\n"
        "# via `var.set webstream.gain = <factor>` before `webstream.start`.\n"
        "# 1.0 = unity (no gain change); cc_webstream.input_gain_db is\n"
        "# converted to linear in Pypo (10 ** (dB/20)) before push.\n"
        "#\n"
        "# buffer(buffer=5.0, ...) is the asynchronous clock-bridge that\n"
        "# decouples input.http's HTTP-stream clock from the main bus.\n"
        "# Without it, crossfade() at the end of the source-graph rejects\n"
        "# the chain with Error 7 (see _render_webstream_input_block\n"
        "# docstring for the full reasoning).  5 s buffer absorbs the\n"
        "# initial-connect cold-buffer rebuild without producing the\n"
        "# 'Buffer emptied, start buffering' → switch-flip-off-webstream\n"
        "# 'Haker' that Phase-E reality-test 2026-05-29 18:40 observed\n"
        "# (~12 s into BBC stream).\n"
        'webstream_gain = interactive.float("webstream.gain", 1.0)\n'
        "webstream = amplify({webstream_gain()}, buffer(buffer=5.0, webstream_raw))\n"
    )


def _render_linein_input_block(
    *,
    enabled: bool,
    listen_url: str = DEFAULT_LINEIN_LISTEN_URL,
    max_buffer_seconds: float = DEFAULT_LINEIN_MAX_BUFFER_SECONDS,
    timeout_seconds: float = DEFAULT_LINEIN_TIMEOUT_SECONDS,
    poll_delay_seconds: float = DEFAULT_LINEIN_POLL_DELAY_SECONDS,
) -> str:
    """
    Render the ``input.http`` block for scheduled line-inputs (Phase F).

    The URL is hard-coded to FfmpegLineinCapture's local Icecast mount
    (``http://localhost:8000/linein-capture`` by default).  Unlike the
    webstream block (Phase E), the URL is fixed at render time — Pypo
    does NOT change it per-show because there is only one capture
    instance active at a time.

    Pypo's _on_linein_start (in Liquidsoap mode) starts both the
    FfmpegLineinCapture Python subprocess (with the device GUID from
    the schedule item) AND sends the telnet ``linein.start`` command;
    on show-end ``linein.stop`` + FfmpegLineinCapture stop.

    No gain wrapper here — :class:`LineinEvent` deliberately has no
    ``input_gain_db`` field (line-input level is controlled at the
    operator's audio mixer or in FfmpegLineinCapture's encode pipeline,
    not per-show in the schedule).  Future operator-requested
    per-line-input gain could be added analog to the webstream
    pattern.

    See ``_render_webstream_input_block`` for the full reasoning on
    why ``self_sync=false`` + ``buffer()`` wrapper are BOTH required
    for crossfade compatibility (compile-time source-graph latency
    check + clock-bridge).
    """
    if not enabled:
        return (
            "# (linein input.http disabled — Liquidsoap engine not\n"
            "#  active; legacy mpv/VLC handles line-inputs via separate path)\n"
        )
    return (
        "linein_raw = input.http(\n"
        '  id="linein",\n'
        "  start=false,\n"
        "  self_sync=false,\n"
        f"  max_buffer={_format_crossfade_duration(max_buffer_seconds)},\n"
        f"  timeout={_format_crossfade_duration(timeout_seconds)},\n"
        f"  poll_delay={_format_crossfade_duration(poll_delay_seconds)},\n"
        f'  "{_escape_liq_string(listen_url)}",\n'
        ")\n"
        "\n"
        "# buffer(buffer=5.0, ...) is the asynchronous clock-bridge that\n"
        "# decouples input.http's HTTP-stream clock from the main bus.\n"
        "# Same reasoning as the webstream block.  Localhost HTTP-stream\n"
        "# jitter is much lower than public Internet streams, but the\n"
        "# 5 s buffer absorbs the initial-connect cold-buffer rebuild\n"
        "# without the switch-flip-off 'Haker' symptom observed in\n"
        "# Phase-E live-tests.\n"
        "linein = buffer(buffer=5.0, linein_raw)\n"
    )


def _render_bus_source_block(
    *,
    main_enabled: bool,
    show_enabled: bool,
    webstream_enabled: bool = DEFAULT_WEBSTREAM_ENABLED,
    linein_enabled: bool = DEFAULT_LINEIN_ENABLED,
) -> str:
    """
    Render the ``bus = ...`` assignment that picks the active source.

    Switch-arm layout (in priority order):
      master_dj         (if main_enabled)
      show_dj           (if show_enabled)
      webstream         (if webstream_enabled — Liquidsoap engine path)
      linein            (if linein_enabled — Liquidsoap engine path)
      scheduled         (always — final fallback)

    When NO upstream switching candidates are enabled (no harbor, no
    webstream, no linein), falls back to the C3-era simple assignment
    ``bus = scheduled`` so the switch operator doesn't show up as a
    noise line in `--check` output.

    Priority rationale (Phase-E/F 2026-05-29):
      * DJ-Sources stay topmost — operator-live always wins
      * Webstream-Show goes ABOVE scheduled — when a webstream show is
        active, the scheduled fallback (silence) must not drown it out
      * Line-Input-Show goes ABOVE scheduled, BELOW webstream — same
        argument; ordering between webstream + linein is arbitrary
        (a single schedule slot is never both at the same time)
      * Scheduled is the catch-all silence + per-show track playback

    RASTATIME 2026-05-28 — Phase-D Stück-B operator decision:
    ``track_sensitive=false`` for immediate DJ-take-over.

    Trade-off: when a DJ connects, the currently-playing scheduled
    track gets cut short via the crossfade transition (1.0 s default
    in current config).  This is what the operator wants for live
    news / emergency / impatient-DJ scenarios.  The alternative
    (``track_sensitive=true``) waits for the current scheduled
    track to end before switching — Live-Radio-Standard, but
    introduces a 0–N-minute delay between DJ-connect and audible
    take-over (where N = scheduled track length).

    ``source.is_ready()`` flips automatically when input.harbor sees
    the DJ-client (dis)connect, or when input.http for webstream
    finishes buffering / disconnects.  With ``track_sensitive=false``
    the switch reacts on the very next bus frame.
    """
    arms = []
    if main_enabled:
        arms.append("({source.is_ready(master_dj)}, master_dj)")
    if show_enabled:
        arms.append("({source.is_ready(show_dj)}, show_dj)")
    if webstream_enabled:
        arms.append("({source.is_ready(webstream)}, webstream)")
    if linein_enabled:
        arms.append("({source.is_ready(linein)}, linein)")
    arms.append("({true}, scheduled)")

    if (
        not main_enabled and not show_enabled
        and not webstream_enabled and not linein_enabled
    ):
        # No upstream switching candidate at all — keep the C3-era
        # simple assignment so the switch operator doesn't show up as a
        # noise line in `--check` output and so the bus chain is
        # identical for legacy single-source users.
        return "bus = scheduled\n"

    return (
        "bus = switch(\n"
        "  track_sensitive=false,\n"
        "  [\n"
        + "".join(f"    {arm},\n" for arm in arms)
        + "  ]\n"
        ")\n"
    )


def render_rastatime_liq(
    stream_outputs: List[Dict],
    *,
    telnet_host: str = DEFAULT_TELNET_HOST,
    telnet_port: int = DEFAULT_TELNET_PORT,
    log_file: str = DEFAULT_LOG_FILE,
    crossfade_duration: float = DEFAULT_CROSSFADE_DURATION,
    crossfade_fade_seconds: float = DEFAULT_CROSSFADE_FADE_SECONDS,
    local_output_enabled: bool = DEFAULT_LOCAL_OUTPUT_ENABLED,
    harbor_main_password: Optional[str] = None,
    harbor_show_password: Optional[str] = None,
    harbor_main_port: int = DEFAULT_HARBOR_MAIN_PORT,
    harbor_show_port: int = DEFAULT_HARBOR_SHOW_PORT,
    harbor_main_mount: str = DEFAULT_HARBOR_MAIN_MOUNT,
    harbor_show_mount: str = DEFAULT_HARBOR_SHOW_MOUNT,
    harbor_buffer_seconds: float = DEFAULT_HARBOR_BUFFER_SECONDS,
    webstream_enabled: bool = DEFAULT_WEBSTREAM_ENABLED,
    webstream_max_buffer_seconds: float = DEFAULT_WEBSTREAM_MAX_BUFFER_SECONDS,
    webstream_timeout_seconds: float = DEFAULT_WEBSTREAM_TIMEOUT_SECONDS,
    webstream_poll_delay_seconds: float = DEFAULT_WEBSTREAM_POLL_DELAY_SECONDS,
    linein_enabled: bool = DEFAULT_LINEIN_ENABLED,
    linein_listen_url: str = DEFAULT_LINEIN_LISTEN_URL,
    linein_max_buffer_seconds: float = DEFAULT_LINEIN_MAX_BUFFER_SECONDS,
    linein_timeout_seconds: float = DEFAULT_LINEIN_TIMEOUT_SECONDS,
    linein_poll_delay_seconds: float = DEFAULT_LINEIN_POLL_DELAY_SECONDS,
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

    harbor_block = _render_harbor_inputs_block(
        main_password=harbor_main_password,
        show_password=harbor_show_password,
        main_port=harbor_main_port,
        show_port=harbor_show_port,
        main_mount=harbor_main_mount,
        show_mount=harbor_show_mount,
        buffer_seconds=harbor_buffer_seconds,
    )
    webstream_block = _render_webstream_input_block(
        enabled=webstream_enabled,
        max_buffer_seconds=webstream_max_buffer_seconds,
        timeout_seconds=webstream_timeout_seconds,
        poll_delay_seconds=webstream_poll_delay_seconds,
    )
    linein_block = _render_linein_input_block(
        enabled=linein_enabled,
        listen_url=linein_listen_url,
        max_buffer_seconds=linein_max_buffer_seconds,
        timeout_seconds=linein_timeout_seconds,
        poll_delay_seconds=linein_poll_delay_seconds,
    )
    bus_block = _render_bus_source_block(
        main_enabled=bool(harbor_main_password),
        show_enabled=bool(harbor_show_password),
        webstream_enabled=webstream_enabled,
        linein_enabled=linein_enabled,
    )

    rendered = (
        template
        .replace("${TELNET_HOST}", _escape_liq_string(telnet_host))
        .replace("${TELNET_PORT}", str(int(telnet_port)))
        .replace("${LOG_FILE}", _escape_liq_string(log_file))
        .replace(
            "${CROSSFADE_DURATION}",
            _format_crossfade_duration(crossfade_duration),
        )
        .replace(
            "${CROSSFADE_FADE_SECONDS}",
            _format_crossfade_duration(crossfade_fade_seconds),
        )
        .replace(
            "${LOCAL_OUTPUT_BLOCK}",
            _render_local_output_block(local_output_enabled),
        )
        .replace("${HARBOR_INPUTS_BLOCK}", harbor_block)
        .replace("${WEBSTREAM_INPUT_BLOCK}", webstream_block)
        .replace("${LINEIN_INPUT_BLOCK}", linein_block)
        .replace("${BUS_SOURCE_BLOCK}", bus_block)
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
    crossfade_fade_seconds: float = DEFAULT_CROSSFADE_FADE_SECONDS,
    local_output_enabled: bool = DEFAULT_LOCAL_OUTPUT_ENABLED,
    harbor_main_password: Optional[str] = None,
    harbor_show_password: Optional[str] = None,
    harbor_main_port: int = DEFAULT_HARBOR_MAIN_PORT,
    harbor_show_port: int = DEFAULT_HARBOR_SHOW_PORT,
    harbor_main_mount: str = DEFAULT_HARBOR_MAIN_MOUNT,
    harbor_show_mount: str = DEFAULT_HARBOR_SHOW_MOUNT,
    harbor_buffer_seconds: float = DEFAULT_HARBOR_BUFFER_SECONDS,
    webstream_enabled: bool = DEFAULT_WEBSTREAM_ENABLED,
    webstream_max_buffer_seconds: float = DEFAULT_WEBSTREAM_MAX_BUFFER_SECONDS,
    webstream_timeout_seconds: float = DEFAULT_WEBSTREAM_TIMEOUT_SECONDS,
    webstream_poll_delay_seconds: float = DEFAULT_WEBSTREAM_POLL_DELAY_SECONDS,
    linein_enabled: bool = DEFAULT_LINEIN_ENABLED,
    linein_listen_url: str = DEFAULT_LINEIN_LISTEN_URL,
    linein_max_buffer_seconds: float = DEFAULT_LINEIN_MAX_BUFFER_SECONDS,
    linein_timeout_seconds: float = DEFAULT_LINEIN_TIMEOUT_SECONDS,
    linein_poll_delay_seconds: float = DEFAULT_LINEIN_POLL_DELAY_SECONDS,
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
        crossfade_fade_seconds=crossfade_fade_seconds,
        local_output_enabled=local_output_enabled,
        harbor_main_password=harbor_main_password,
        harbor_show_password=harbor_show_password,
        harbor_main_port=harbor_main_port,
        harbor_show_port=harbor_show_port,
        harbor_main_mount=harbor_main_mount,
        harbor_show_mount=harbor_show_mount,
        harbor_buffer_seconds=harbor_buffer_seconds,
        webstream_enabled=webstream_enabled,
        webstream_max_buffer_seconds=webstream_max_buffer_seconds,
        webstream_timeout_seconds=webstream_timeout_seconds,
        webstream_poll_delay_seconds=webstream_poll_delay_seconds,
        linein_enabled=linein_enabled,
        linein_listen_url=linein_listen_url,
        linein_max_buffer_seconds=linein_max_buffer_seconds,
        linein_timeout_seconds=linein_timeout_seconds,
        linein_poll_delay_seconds=linein_poll_delay_seconds,
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
    render.add_argument(
        "--local-output", dest="local_output_enabled",
        action="store_true", default=DEFAULT_LOCAL_OUTPUT_ENABLED,
        help="Enable output.wasapi to OS-default soundcard (default).",
    )
    render.add_argument(
        "--no-local-output", dest="local_output_enabled",
        action="store_false",
        help="Skip the soundcard output (headless server install).",
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
            local_output_enabled=args.local_output_enabled,
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
