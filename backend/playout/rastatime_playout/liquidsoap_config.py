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

      python -m rastatime_playout.liquidsoap_config render \\
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
from typing import Dict, List, Mapping, NamedTuple, Optional, Tuple

logger = logging.getLogger(__name__)

from .icy_metadata import (  # noqa: E402
    DEFAULT_ICY_FORMAT,
    DEFAULT_OFFAIR_TEXT,
    DEFAULT_STATION_NAME,
)


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
DEFAULT_CROSSFADE_FADE_SECONDS = 0.0  # kept for older callers; no longer rendered

# RASTATIME 2026-09-27 - Show-boundary crossfade.  Two operator values
# (Settings -> General): the TRACK crossfade (between tracks of one show,
# a real crossfade: old fades out while new fades in over D seconds) and
# the SHOW crossfade (at a show boundary: the old show fades out over D
# seconds while the first track of the new show starts at full level at
# once; the same value shapes every input switch in the bus block).
# `cross` buffers BUFFER = max(track, show, floor) seconds of the ending
# track; the transition function trims that tail per shape.
DEFAULT_SHOW_CROSSFADE_DURATION = 1.0
# RASTATIME 2026-09-28 - Settings -> Streams "Switch Transition Fade"
# (cc_pref default_transition_fade, start value 1 s): the DJ hand-over.
# A connecting DJ is on air at once, the programme fades out under it
# over this many seconds; when the DJ hands back, the DJ fades out
# over the same time and the programme is at full level at once.
DEFAULT_DJ_FADE_SECONDS = 1.0
CROSSFADE_BUFFER_FLOOR_SECONDS = 0.5


def crossfade_buffer_seconds(track_seconds: float, show_seconds: float) -> float:
    """Seconds the cross operator buffers from the end of every track."""
    return max(
        CROSSFADE_BUFFER_FLOOR_SECONDS,
        float(track_seconds or 0.0),
        float(show_seconds or 0.0),
    )

# Whether to emit a Liquidsoap output to the local soundcard.  On the
# Windows-only RASTATIME deployment this is `output.wasapi`, defaulting
# to the OS-default audio endpoint.  Set RASTATIME_LIQUIDSOAP_LOCAL_OUTPUT=false
# for headless server installs that don't want a soundcard output.
DEFAULT_LOCAL_OUTPUT_ENABLED = True
# RASTATIME 2026-09-14 - the monitor bridge compensates the device clock
# drift (buffer.adaptative, at most 0.1 % speed change); the machine setting
# RASTATIME_LIQUIDSOAP_LOCAL_OUTPUT_ADAPTIVE=false renders the plain buffer().
DEFAULT_LOCAL_OUTPUT_ADAPTIVE = True
LOCAL_OUTPUT_BUFFER_SECONDS = 2.0
LOCAL_OUTPUT_ADAPTIVE_LIMIT = 1.001

# Phase-C4: default Liquidsoap-Harbor port for DJ-Master + DJ-Show
# sources.  Operator-decision from 2026-05-25 said port 8001 (Master) /
# 8002 (Show), matching rastatime_shared's MainHarborInput/
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

# RASTATIME 2026-09-09 - DJ connect/disconnect events (option d).  The
# harbor sources call back into PLAYOUT's HTTP listener the moment a DJ
# connects or drops, so PLAYOUT no longer polls ``master_dj.status`` /
# ``show_dj.status`` over telnet every 5 s (every telnet command leaks
# ~87 KB on the Windows build; the poll alone was ~150 MB/h).  None
# renders no callbacks (PLAYOUT then relies on its periodic reconcile).
DEFAULT_SOURCE_EVENT_URL = "http://127.0.0.1:8770/source-event"
# RASTATIME 2026-09-28 - Live Text Info: Liquidsoap POSTs the "now playing"
# line (Live Text Format) to the playout listener on every metadata packet.
DEFAULT_LIVE_TEXT_URL = "http://127.0.0.1:8770/live-text"
DEFAULT_SOURCE_EVENT_TIMEOUT_SECONDS = 2.0

# RASTATIME 2026-09-09 - input.harbor network timeout.  The Windows build
# does not notice a DJ client that merely closes its socket until this
# timeout expires (Liquidsoap default 30 s); PLAYOUT pushes no tracks
# while it believes a DJ is live, so the bus fell back to an empty queue
# for up to 25 s after a hang-up.  5 s matches the harbor buffer: the
# state flips when the buffered audio runs out.  A client silent for
# longer is dropped and has to reconnect (BUTT does that on its own).
# Replica 2026-09-09: timeout=5 -> disconnect reported after 5.06 s.
DEFAULT_HARBOR_TIMEOUT_SECONDS = 5.0

# RASTATIME 2026-09-10 - DJ logins are checked by PLAYOUT ("UI wird zur
# Wahrheit"): the harbor's auth callback POSTs user/password to this URL,
# PLAYOUT asks the legacy web application (Settings -> Streams -> Master
# Source; the show's Live Stream Input).  None renders no callback: the
# static harbor password from rastatime.conf is the only check then.
DEFAULT_DJ_AUTH_URL = "http://127.0.0.1:8770/dj-auth"
DEFAULT_DJ_AUTH_TIMEOUT_SECONDS = 3.0


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

# input.http connect/read timeout in seconds.  If the upstream HTTP
# server doesn't respond (or stops sending) within this window,
# input.http gives the connection up and retries after poll_delay
# seconds.  RASTATIME 2026-09-05 ("Option 1", operator-go): 10 s
# (the stdlib default) -> 3 s.  The cloud DEVA stream stalls silently
# a few seconds after a fresh connection; with 10 s the recovery took
# 20-50 s of dead air (11:36: 52 s).  A stream that really needs
# more than 3 s to answer is not usable for a scheduled slot anyway.
DEFAULT_WEBSTREAM_TIMEOUT_SECONDS = 3.0

# input.http reconnect-poll-delay in seconds.  When a connection drops
# (network blip, server-side restart, etc.) Liquidsoap retries every
# poll_delay seconds.  RASTATIME 2026-09-05: 2 s (stdlib default) ->
# 0.5 s, part of the recovery budget below.
DEFAULT_WEBSTREAM_POLL_DELAY_SECONDS = 0.5

# Clock-bridge pre-buffer between input.http and the bus, in seconds,
# and the bridge's hard maximum.  RASTATIME 2026-09-06: back to 5 s /
# 10 s.  The 2026-09-05 bump to 10 s / 20 s ("Option 1") was a mistake:
# a bigger bridge does not bridge the cloud DEVA's stalls (they last far
# longer than any sane buffer) and it doubled the window in which a
# DIFFERENT stream's buffered tail plays at the slot start ("wrong
# stream for N seconds").  Recovery from a stall is now handled by the
# scheduler webstream watchdog (a clean stop+start), not by a fat
# buffer.  5 s is the Phase-E-proven minimum that avoids the cold-start
# "Haker" without over-buffering.
DEFAULT_WEBSTREAM_BRIDGE_SECONDS = 5.0
DEFAULT_WEBSTREAM_BRIDGE_MAX_SECONDS = 10.0

# RASTATIME 2026-09-07 - the webstream watchdog lives inside Liquidsoap:
# a counter on the bus's per-frame callback (streaming thread, 50 frames
# per second at frame.duration 0.02 s) checks source.is_ready(webstream)
# every CHECK_FRAMES frames and reconnects after STARVE_CHECKS not-ready
# checks that follow a ready one.  Measured 2026-09-07 in a replica:
# the frame counter costs nothing, a thread.run.recurrent timer ~31 KB
# per tick and the scheduler's telnet poll 66-87 KB per command (the
# Windows Unix.select leak) - ~157 MB per webstream hour in production.
DEFAULT_WEBSTREAM_WATCHDOG_CHECK_FRAMES = 100      # 2 s at 50 frames/s
DEFAULT_WEBSTREAM_WATCHDOG_STARVE_CHECKS = 2       # -> reconnect after ~4 s


# ---------------------------------------------------------------------
# Phase-F-2 — Scheduled Line-Inputs via input.ffmpeg(format="dshow")
# (RASTATIME 2026-05-30)
# ---------------------------------------------------------------------
#
# Phase-F-2 replaces the Phase-F approach (input.http consuming the
# FfmpegLineinCapture local Icecast mount) with input.ffmpeg opening
# the Windows dshow audio device DIRECTLY via Liquidsoap's in-process
# libavdevice — no external ffmpeg subprocess, no HTTP hop.
#
# Spike-verified 2026-05-30:
#   * input.ffmpeg(format="dshow", start=false, self_sync=false, "")
#     opens a dshow device on demand (pcm_s16le 44100Hz 2ch).
#   * input.ffmpeg does NOT auto-register its set_url/start/stop/status
#     server-commands (unlike input.http), so the template registers
#     them manually via server.register under the "linein" namespace.
#   * Runtime device-switch works: `linein.set_url <dshow-spec>` then
#     `linein.start` → "connected <spec>".  This is what input.portaudio
#     could NOT do (no set_device at runtime).
#
# Pypo sends the dshow alternative-name spec (built from the schedule
# item's device GUID via _stable_id_to_dshow_audio) as the set_url
# argument at show-start, then linein.start; linein.stop at show-end.

# Whether to emit the linein input.ffmpeg block + switch-arm.  Defaults
# to True for the Liquidsoap engine path.  The Phase-D-deprecated
# mpv/VLC engine paths set this to False — those still handle
# line-inputs via the legacy mpv adapter.
DEFAULT_LINEIN_ENABLED = True

# input.ffmpeg max_buffer (seconds) — how much dshow audio is pre-
# buffered before the source reports ready.  Much lower than the
# webstream value (10 s) because a local sound card has near-zero
# jitter (no network in the path), and a live mic wants minimal
# added latency.  2 s absorbs the cold-start buffer-fill without a
# noticeable on-air delay.
DEFAULT_LINEIN_MAX_BUFFER_SECONDS = 2.0

# RASTATIME 2026-08-31 — multichannel line-in path (BACKLOG "Line-In:
# Kanal-Auswahl auf Multi-Input-Devices"), widened 2026-09-03.  Pypo
# runs FfmpegLineinCapture with the sounddevice/MME feeder for EVERY
# channel_mapping now, plain stereo included, pushing the selected pair
# to the local /linein-capture Icecast mount; Liquidsoap consumes that
# mount through a second, fixed-URL input.http source.  The direct-dshow
# source below survives only for legacy rows with no stored device
# name: it addresses the device by endpoint GUID, which DirectShow does
# not recognise, and went out silent on the Tascam.  127.0.0.1
# deliberately, not localhost (Phase-E lesson: OCaml resolves
# localhost AAAA-first and Icecast is IPv4-only).
DEFAULT_LINEIN_HTTP_URL = "http://127.0.0.1:8000/linein-capture"

# RASTATIME 2026-09-03 - lowered 4.0 -> 1.5 to cut the line-in start
# gap.  input.http becomes ready (and the switch takes it) only once
# this many real seconds of audio are buffered, so it was the biggest
# single contributor to the ~7 s dead-air on a scheduled line-in start
# (measured 14:20 show: mount alive at +1.8 s, switch at +7.0 s).  The
# hop is a loopback-local Icecast mount fed at a constant 1x rate, so
# jitter is minimal and a small buffer is safe.  Env-overridable
# (RASTATIME_LIQUIDSOAP_LINEIN_HTTP_MAX_BUFFER_SECONDS) without a rebuild.
#
# RASTATIME 2026-09-03, second pass: raised 1.5 -> 2.0 on operator
# request after a ~1 s dropout was heard mid-show.  Measurement showed
# that dropout came from a catch-up re-arm, not an under-run (see the
# catch-up guard in playout_scheduler).
#
# RASTATIME 2026-09-04, third pass: 2.0 -> 1.0.  The buffer is not only
# start-gap: whatever input.http holds is permanent END-TO-END LATENCY
# of the line-in path -- what is spoken at studio time t reaches the
# stream at t + L, and at the slot end the last L seconds are still in
# the pipe and get cut off with the source.  The operator heard the
# last ~6 s of a line-in show vanish (16:07-16:12 show, counting
# seconds into the mic).  This hop is loopback Icecast at a constant
# 1x rate; 1.0 s is ample jitter cover there.  Env-overridable as
# before, floor 0.2 s in __main__.
DEFAULT_LINEIN_HTTP_MAX_BUFFER_SECONDS = 1.0

# RASTATIME 2026-09-04 - container format of the /linein-capture mount,
# passed to input.http as ``format=`` so FFmpeg skips its format
# AUTODETECTION.  Measured on the live mount (four isolated listeners,
# 16:56): autodetect needs ~5 s before the decoder is ready -- a
# listener joins an Icecast mount mid-stream with no header in sight,
# so libavformat scans up to its probe budget first -- while a forced
# "mp3" is ready after ~1 s.  Those 5 s were the dominant term of BOTH
# the line-in start gap AND the permanent end-to-end latency (the last
# ~6 s of a line-in show never reached the stream).  The value is a
# property of our own capture pipeline (FfmpegLineinCapture muxes with
# ``-f mp3``), not of the device, hence a constant.  Probe-size /
# analyzeduration int_args were measured too and only made it worse
# (2 s) -- keep it to the format.
LINEIN_HTTP_FORMAT = "mp3"

# RASTATIME 2026-09-04 - input transitions on the bus switch ("Paket 2").
#
# The bus switch used to be a hard cut: whichever arm's predicate turned
# true was on air from the next frame, and the previous source was gone
# with it -- including the ~2 s of a line-in still sitting in its
# buffer, i.e. the presenter's last words.  Two things change:
#
#   * GATES.  ``webstream_live`` / ``linein_live`` are interactive bools
#     the predicates AND with ``source.is_ready``.  Pypo can now connect
#     and buffer a source BEFORE its slot (gate closed) and put it on air
#     at the slot start by flipping the gate -- no start gap -- and take
#     it off air at the slot end with the gate instead of killing it.
#     Default ``true`` = today's behaviour for a Pypo that never touches
#     the gates.
#   * TRANSITIONS.  Switching between the webstream / line-in / scheduled
#     arms goes through ``bus_transition``: with a crossfade duration
#     D > 0 the old source fades out over D while the new fades in
#     (add + fade.out/fade.in); with D = 0 it is "ducking" -- the new
#     source starts at full level immediately and the old one fades out
#     UNDER it over DEFAULT_INPUT_DUCK_FADE_SECONDS.  Either way the old
#     source keeps being pulled during the fade, so a line-in's buffered
#     tail is heard instead of lost.  Verified 2026-09-04 in an isolated
#     run (two sines, gate flipped over telnet, spectral analysis of the
#     recording): both shapes act at the flip, not at transition_length.
#     The DJ arms (master/show) keep the instant hand-over.
#
# D is the operator's Settings -> General "Default Crossfade Duration"
# (cc_pref default_crossfade_duration, read by __main__ at render time;
# 0 = ducking, > 0 = crossfade of that length).  The same value drives
# the queue's track-to-track crossfade, so there is ONE house crossfade.
DEFAULT_INPUT_DUCK_FADE_SECONDS = 1.0

# RASTATIME 2026-09-03 - the http companion polls this often while
# trying to (re)connect.  0.5 s (vs the 2.0 s webstream default) lets
# an input.http armed IN PARALLEL with the feeder grab the mount within
# half a second of the feeder publishing it, instead of waiting up to a
# full webstream poll cycle.  Cheap on a loopback hop.
DEFAULT_LINEIN_HTTP_POLL_DELAY_SECONDS = 0.5


# ---------------------------------------------------------------------
# Liquidsoap codec encoders per stream type
# ---------------------------------------------------------------------

# Validated on the operator's Liquidsoap 2.4.4 + FFmpeg build (Phase-A
# burn-in confirmed mp3 via libmp3lame); aac via FFmpeg's native AAC
# encoder; vorbis via libvorbis.  These are the same three formats the
# former FfmpegStreamer emitted — the operator's listener-side URLs
# stayed unchanged when the output moved from FFmpeg to Liquidsoap.
_ENCODER_FOR_TYPE = {
    # FFmpeg-format string for output.icecast.  All four use the
    # %ffmpeg encoder so the binary build only needs FFmpeg libraries
    # (which the operator already validated in Phase A).  Matches the
    # cc_pref.stream_output_N "type" values of Settings → Streams.
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
# 48000 with a warning at render time.
_OPUS_VALID_SAMPLERATES = {8000, 12000, 16000, 24000, 48000}

# Default samplerate when the cc_pref row doesn't carry one.  44100 Hz
# matches Liquidsoap's internal frame samplerate so no resampling is
# needed for mp3/aac/ogg-vorbis.  Opus gets clamped to 48000.
DEFAULT_SAMPLERATE = 44100

# File extension per stream type for output.file recording targets.
# (output.icecast uses mount paths, not extensions; output.file needs a
# real on-disk extension matching the container the encoder writes.)
_FILE_EXT_FOR_TYPE = {
    "mp3": "mp3",
    "aac": "aac",   # %ffmpeg(format="adts") = raw AAC stream
    "ogg": "ogg",
    "opus": "opus",
}

# RASTATIME 2026-06-05 — 24/7 hourly archive recorder defaults.  192 kbps
# MP3 is the operator-chosen default (compliance / catch-up archive; lower
# than the 320 k per-show recording to save disk — ~14 GB/week vs ~24 GB).
DEFAULT_HOURLY_RECORDING_FORMAT = "mp3"
DEFAULT_HOURLY_RECORDING_BITRATE = 192

# RASTATIME 2026-10-18 - per-show recording encoder (Settings -> Local
# Machine -> Show Recording).  MP3 320k was fixed since 2026-05-27; the
# operator asked for the same choice the 24/7 recorder offers.
DEFAULT_SHOW_RECORDING_FORMAT = "mp3"
DEFAULT_SHOW_RECORDING_BITRATE = 320


def show_recording_extension(fmt: str) -> str:
    """File extension of a per-show recording in format ``fmt`` (mp3 fallback)."""
    return _FILE_EXT_FOR_TYPE.get(str(fmt or "").lower(), _FILE_EXT_FOR_TYPE["mp3"])


def _render_show_recording_encoder(
    fmt: str = DEFAULT_SHOW_RECORDING_FORMAT,
    bitrate: int = DEFAULT_SHOW_RECORDING_BITRATE,
    samplerate: int = DEFAULT_SAMPLERATE,
) -> str:
    """
    The ``%ffmpeg(...)`` encoder of ``output.file(id="recording")``.
    Unknown formats fall back to MP3 (a wrong cc_pref value must not
    leave the station without a recorder); Opus is clamped to 48 kHz.
    """
    fmt = str(fmt or DEFAULT_SHOW_RECORDING_FORMAT).lower()
    if fmt not in _ENCODER_FOR_TYPE:
        logger.warning(
            "Unsupported show recording format %r - rendering mp3 instead", fmt,
        )
        fmt = "mp3"
    try:
        bitrate = int(bitrate)
    except (TypeError, ValueError):
        bitrate = DEFAULT_SHOW_RECORDING_BITRATE
    if bitrate <= 0:
        bitrate = DEFAULT_SHOW_RECORDING_BITRATE
    try:
        samplerate = int(samplerate or DEFAULT_SAMPLERATE)
    except (TypeError, ValueError):
        samplerate = DEFAULT_SAMPLERATE
    if fmt == "opus" and samplerate not in _OPUS_VALID_SAMPLERATES:
        samplerate = 48000
    return (
        _ENCODER_FOR_TYPE[fmt]
        .replace("${BITRATE}", str(bitrate))
        .replace("${SAMPLERATE}", str(samplerate))
    )


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


def _normalize_loopback_host(host: str) -> str:
    """
    Map ``localhost`` to ``127.0.0.1`` in rendered output targets.

    On Windows ``localhost`` resolves AAAA-first (``::1``) while Icecast
    2.4.4 listens IPv4-only — every ICY metadata update the icecast
    outputs send at track start then burns ~5 s in the IPv6 connect
    attempt and freezes the Liquidsoap main clock (one freeze per ICY
    mount, so ~10 s with mp3+aac).  During webstream shows those
    catchups drain the 5 s input bridge buffer and produce the
    switch ping-pong from the Phase-E reality-test 2026-05-29.
    Proven empirically 2026-08-29 (testbed T9/T10): identical graph,
    25/25 track:catchup correlation on ``localhost`` vs 0 catchups in
    26 tracks on ``127.0.0.1``.
    """
    return "127.0.0.1" if host.strip().lower() == "localhost" else host


def _live_text_report_lines(live_text_url: Optional[str]) -> List[str]:
    """``livetext_report(m)``: POST the Live Text line to PLAYOUT (or a no-op)."""
    if not live_text_url:
        return ["def livetext_report(_) = () end"]
    url = _escape_liq_string(live_text_url)
    return [
        "def livetext_report(m) =",
        "  if livetext_enabled() then",
        "    label = label_for(livetext_format(), m)",
        '    if label != "" then',
        "      thread.run(fun () ->",
        "        try",
        f'          ignore(http.post(timeout=2.0, data=label, "{url}"))',
        "        catch err do",
        '          log(level=3, label="rastatime.livetext", "POST failed: #{err}")',
        "        end)",
        "    end",
        "  end",
        "end",
    ]


def _render_icy_metadata_block(
    label_format: int = DEFAULT_ICY_FORMAT,
    offair_text: str = DEFAULT_OFFAIR_TEXT,
    station_name: str = DEFAULT_STATION_NAME,
    live_text_url: Optional[str] = DEFAULT_LIVE_TEXT_URL,
) -> str:
    """
    RASTATIME 2026-09-13 - the ``${ICY_METADATA_BLOCK}``: four telnet-
    settable values and the ``icy_label`` function every output.icecast
    block uses as ``icy_song``.

    ``icy_label`` sees ONE metadata packet at a time (that is how
    output.icecast calls it), so a harbor or webstream packet that only
    carries a title takes the show from ``bus_show``, which the scheduler
    keeps at the show on air.  Formats (Settings -> Streams, Stream
    Label): 0 Artist - Title, 1 Show - Artist - Title, 2 Station name -
    Show name.  A packet flagged ``off_air`` (the silence fallback, see
    the template) always yields the Off Air Metadata text.
    """
    fmt = int(label_format) if int(label_format) in (0, 1, 2) else DEFAULT_ICY_FORMAT
    lines = [
        "# ---------------------------------------------------------------------",
        "# RASTATIME 2026-09-13 - ICY metadata (Settings -> Streams)",
        "# ---------------------------------------------------------------------",
        "#",
        "# What listeners see in their player.  Four telnet-settable values;",
        "# PLAYOUT pushes the first three on every schedule refresh when they",
        "# change (no restart) and bus_show at every show change:",
        "#   var.set icy_format = 1          var.set offair_text = Back soon",
        "#   var.set station_name = Name     var.set bus_show = Show name",
        "# (interactive.set takes the raw text after '=', no quotes.)",
        f'icy_format = interactive.int("icy_format", {fmt})',
        f'offair_text = interactive.string("offair_text", "{_escape_liq_string(offair_text)}")',
        f'station_name = interactive.string("station_name", "{_escape_liq_string(station_name)}")',
        'bus_show = interactive.string("bus_show", "")',
        "",
        "# label_for: the label for one metadata packet in format fmt (\"\" = leave",
        "# the packet alone).  Only the fields of THAT",
        "# packet are known - a harbor packet with just a title takes the show",
        "# from bus_show().  Formats: 0 Artist - Title, 1 Show - Artist - Title,",
        "# 2 Station name - Show name; an off_air packet always shows the text;",
        "# a packet without any of these fields leaves the title alone (null).",
        "# 2026-09-28: a live source without artist/title (DJ sending no metadata,",
        "# webstream without titles, line-in) shows 'Station name - Show name' in",
        "# every format (operator decision; before: the bare show name).",
        "def label_for(fmt, m) =",
        '  title = m["title"]',
        '  artist = m["artist"]',
        '  show = if m["show_name"] != "" then m["show_name"] else bus_show() end',
        "  # packets without any of our fields (blank's empty track start,",
        "  # transition internals, replays) must not touch the title -> null",
        '  known = title != "" or artist != "" or m["show_name"] != "" or m["off_air"] == "true" or m["icy_hide"] == "true"',
        "  label =",
        "    if not known then",
        '      ""',
        '    elsif m["off_air"] == "true" then',
        "      offair_text()",
        "    # RASTATIME 2026-10-14 - track without stream metadata (icy_forward):",
        "    # Station name - Show name in every format, like a live source",
        "    # without artist / title",
        '    elsif m["icy_hide"] == "true" then',
        '      if show != "" then "#{station_name()} - #{show}" else station_name() end',
        "    elsif fmt == 2 then",
        '      if show != "" then "#{station_name()} - #{show}" else station_name() end',
        "    else",
        "      parts = if fmt == 1 then [show, artist, title] else [artist, title] end",
        '      parts = list.filter(fun (p) -> p != "", parts)',
        "      if list.length(parts) > 0 then",
        '        string.concat(separator=" - ", parts)',
        "      else",
        '        if show != "" then "#{station_name()} - #{show}" else station_name() end',
        "      end",
        "    end",
        "  label",
        "end",
        "# icy_label: the Stream Label (Settings -> Streams) for the outputs",
        "def icy_label(m) =",
        "  label_for(icy_format(), m)",
        "end",
        "",
        "# RASTATIME 2026-09-28 - Live Text Info (Settings -> General): the same",
        "# line in its own format, POSTed to PLAYOUT on every metadata packet",
        "# (dedup happens there).  var.set livetext_enabled / livetext_format.",
        'livetext_enabled = interactive.bool("livetext_enabled", false)',
        'livetext_format = interactive.int("livetext_format", 0)',
        *_live_text_report_lines(live_text_url),
        "",
        "# icy_rewrite: applied to the bus (metadata.map, see the template).  The",
        "# label replaces the packet's title and the artist is cleared, so every",
        "# consumer - ICY on mp3/aac, in-band Ogg comments, recording tags - shows",
        "# exactly the Stream Label.  Why not icy_song alone: output.icecast hands",
        "# that hook only the standard fields (title, artist, genre, ...), never",
        "# show_name / off_air (replica probe 2026-09-13).",
        "def icy_rewrite(m) =",
        "  label = icy_label(m)",
        '  if label == "" then [] else [("title", label), ("artist", "")] end',
        "end",
        "",
        "# output.icecast hook: the rewritten title is the ICY song (null = keep).",
        "def icy_song_title(m) =",
        '  if m["title"] == "" then null else m["title"] end',
        "end",
        "",
        "server.register(",
        '  namespace="icy", description="ICY metadata settings in effect",',
        '  "status",',
        '  fun (_) -> "format=#{icy_format()} offair=\\"#{offair_text()}\\" station=\\"#{station_name()}\\" show=\\"#{bus_show()}\\""',
        ")",
    ]
    return "\n".join(lines) + "\n"


def _render_icecast_block(
    stream: Dict,
    *,
    station_name: str = DEFAULT_STATION_NAME,
    icy_song: Optional[str] = "icy_song_title",
) -> str:
    """
    Render one output.icecast(...) block from a stream_output_N dict.

    Required keys (silently skipped if missing): type, host, port,
    mount, pass.  Optional: user, name, description, genre, url,
    bitrate, channels.  ``icy_song`` names the Liquidsoap function
    that turns a metadata packet into the ICY title (the bus already
    carries the Stream Label as title, see icy_rewrite; None = Liquidsoap
    default, used by the standby script which has no ICY block).

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
    # with a warning.  Other codecs
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

    host = _escape_liq_string(
        _normalize_loopback_host(str(stream.get("host", "localhost")))
    )
    port = int(stream.get("port", 8000))
    mount_raw = str(stream.get("mount", "stream")).lstrip("/")
    mount = "/" + _escape_liq_string(mount_raw)
    password = _escape_liq_string(str(stream.get("pass", "")))
    user = _escape_liq_string(str(stream.get("user", "source") or "source"))
    # RASTATIME 2026-09-13 - an empty Name / Description in Settings ->
    # Streams showed up as "Unspecified name" on Icecast; fall back to
    # the station name.  Genre and URL are rendered when set (they never
    # were before), and icy_song hands the ICY title to icy_label.
    name = _escape_liq_string(str(stream.get("name") or station_name))
    description = _escape_liq_string(
        str(stream.get("description") or f"{station_name} live stream")
    )
    genre = _escape_liq_string(str(stream.get("genre") or "").strip())
    url = _escape_liq_string(str(stream.get("url") or "").strip())
    extra = ""
    if genre:
        extra += f'  genre="{genre}",\n'
    if url:
        extra += f'  url="{url}",\n'
    if icy_song:
        extra += f"  icy_song={icy_song},\n"

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
        f"{extra}"
        "  fallible=true,\n"
        "  bus,\n"
        f")  # mount {mount} type={stream_type} {bitrate}k\n"
    )


def _render_icecast_outputs(
    stream_outputs: List[Dict],
    *,
    station_name: str = DEFAULT_STATION_NAME,
    icy_song: Optional[str] = "icy_song_title",
) -> str:
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
    blocks = [
        _render_icecast_block(s, station_name=station_name, icy_song=icy_song)
        for s in stream_outputs
    ]
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


def _render_local_output_block(
    enabled: bool,
    device_id: Optional[int] = None,
    device_label: str = "",
    endpoint_id: str = "",
    device_name: Optional[str] = None,
    adaptive: bool = DEFAULT_LOCAL_OUTPUT_ADAPTIVE,
) -> str:
    """
    Render the local soundcard output block.  When enabled, emits a
    Liquidsoap ``output.portaudio`` call that plays the bus to the
    audio endpoint via PortAudio.  When disabled, emits a single
    comment line so the operator can grep + see it was deliberately
    turned off (avoiding "the line just vanished" confusion).

    RASTATIME 2026-09-05 — ``device_name`` wins over ``device_id``.
    PortAudio indices are not stable on the studio machine (endpoints
    appear late after boot and come and go); between PLAYOUT's probe
    and Liquidsoap's open the list shifted and the live instance played
    the Main Output to the wrong jack for hours, while a later restart
    with the stale index would have killed the process at device-open
    (NSSM restart loop).  ``output.portaudio(device_name=...)`` matches
    the exact PortAudio name at Liquidsoap's own start, so the index
    drift cannot bite.  The resolver only offers a name when the entry
    it selects is known to play (see ``portaudio_output.with_name_selection``);
    otherwise we keep the index.

    ``device_id`` is a **PortAudio device index**, resolved from the
    operator's Main-Output setting by
    :func:`~.engine.portaudio_output.resolve_output_device`.  When it
    is ``None`` we omit the argument and PortAudio falls back to the
    OS-default endpoint — the pre-2026-09-03 behaviour.

    RASTATIME 2026-09-03: before this, the argument was never emitted
    at all, so Settings → Local Machine → **Main Output** had no
    effect on the local monitor for the Liquidsoap engine (the value
    was stored and then dropped by a no-op ``set_audio_device``).
    ``device_label`` is only rendered as a comment so an operator
    reading rastatime.liq can see *which* endpoint the index means —
    indices are not stable across re-plugs, the label is the human
    anchor.

    Why portaudio and not wasapi: the Phase-C8 reality-test
    2026-05-26 showed the savonet Liquidsoap 2.4.4 Windows build
    does NOT ship ``output.wasapi`` — ``--list-functions | Select-String
    "^output\\."`` only listed ``output.portaudio``, ``output.ao``,
    ``output.audio_video`` and ``output.external`` as local audio
    sinks.  portaudio is the most natural choice for a Windows-only
    deployment.

    Why mksafe + fallible=false (RASTATIME 2026-09-14): with
    ``fallible=true`` every underrun of the bridge buffer stopped the
    output and re-opened the device once the buffer had refilled.
    PortAudio enumerates the devices once per process, so the re-open
    used the device list from Liquidsoap's start.  The studio display's
    audio endpoint comes and goes with the display; a changed list either
    killed the process ("device ID out of range", four crashes between
    2026-09-07 and 2026-09-14) or silently opened another device
    (2026-09-10 21:38, about 30 h without Liquidsoap audio on the Tascam).
    ``mksafe`` plays silence while the bridge refills, so the output never
    stops and the device is opened exactly once per process.
    ``fallible=false`` turns a missing ``mksafe`` into a start error
    ("That source is fallible") instead of a silent regression -
    ``liquidsoap --check`` does not see it, only the start does.  A device
    that really vanishes still fails the write; NSSM then restarts the
    engine with a fresh device list.

    Why buffer.adaptative (default, RASTATIME 2026-09-14): the Tascam's
    sample clock runs about 50 ppm faster than the main clock, so the
    plain 2 s bridge ran dry every 10-12 h - a gap of about 2 s on the
    monitor path even without the re-open.  ``buffer.adaptative``
    resamples by at most ``LOCAL_OUTPUT_ADAPTIVE_LIMIT`` (0.1 %, far below
    audibility) to hold the level.  It is flagged experimental in 2.4.4,
    hence ``adaptive=False`` (machine setting
    ``RASTATIME_LIQUIDSOAP_LOCAL_OUTPUT_ADAPTIVE=false``) renders the plain
    ``buffer()`` again - with ``mksafe`` either way.

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
        if device_name:
            safe_label = str(device_label).replace("\n", " ").strip()
            safe_ep = "".join(
                c for c in str(endpoint_id) if c.isalnum() or c in "-_"
            )
            quoted = (
                str(device_name).replace("\\", "\\\\").replace('"', '\\"')
                .replace("\n", " ")
            )
            device_line = (
                f"  # rastatime-main-output: {safe_ep or 'unknown'}\n"
                f"  # Main Output (Settings -> Local Machine): {safe_label}\n"
                "  # selected by exact PortAudio name at Liquidsoap start:\n"
                "  # immune to the index drift (RASTATIME 2026-09-05)\n"
                f'  device_name="{quoted}",\n'
            )
        elif device_id is None:
            device_line = (
                # The marker line below is machine-read by the
                # Settings page so it can show which output is
                # REALLY active; "os-default" means the operator
                # pick was unusable or unset.
                "  # rastatime-main-output: os-default\n"
                "  # no device= -> PortAudio uses the OS-default endpoint\n"
            )
        else:
            safe_label = str(device_label).replace("\n", " ").strip()
            safe_ep = "".join(
                c for c in str(endpoint_id) if c.isalnum() or c in "-_"
            )
            device_line = (
                f"  # rastatime-main-output: {safe_ep or 'unknown'}\n"
                f"  # Main Output (Settings -> Local Machine): {safe_label}\n"
                f"  device_id={int(device_id)},\n"
            )
        if adaptive:
            bridge_line = (
                "bus_for_portaudio = buffer.adaptative(id=\"portaudio_buffer\", "
                f"fallible=true, buffer={LOCAL_OUTPUT_BUFFER_SECONDS:.1f}, "
                f"limit={LOCAL_OUTPUT_ADAPTIVE_LIMIT}, bus)\n"
            )
        else:
            bridge_line = (
                "# RASTATIME_LIQUIDSOAP_LOCAL_OUTPUT_ADAPTIVE=false: plain bridge\n"
                f"bus_for_portaudio = buffer(buffer={LOCAL_OUTPUT_BUFFER_SECONDS:.1f}, bus)\n"
            )
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
            "# the bridge.  Buffer bumped to 2.0 s to absorb longer\n"
            "# CPU/disk stalls (the C5 crash was ~10 s after Show-start, at\n"
            "# track-decode peak).  Trade-off: lokales Monitor-Speaker laeuft\n"
            "# 2 s hinter Stream/Recording.\n"
            "# RASTATIME 2026-09-05: sync=\"auto\" instead of sync=\"cpu\".\n"
            "# output.portaudio is self-synced (blocking writes pace the clock\n"
            "# at the device's sample clock); with sync=cpu the clock ALSO tried\n"
            "# to hold wall-time and logged \"Latency is too high\" every second\n"
            "# (3,560/h) whenever the output really played.  auto lets the device\n"
            "# pace the clock; the buffer() bridge above absorbs the drift to the\n"
            "# main clock, which is exactly what it is for.\n"
            "# RASTATIME 2026-09-14: the output is opened once and never stopped.\n"
            "# With fallible=true an underrun stopped it and re-opened the device\n"
            "# with the device list from Liquidsoap's start; the display audio\n"
            "# endpoint comes and goes, so the re-open crashed the engine or\n"
            "# silently opened another device.  mksafe plays silence while the\n"
            "# bridge refills, fallible=false turns a missing mksafe into a start\n"
            "# error, buffer.adaptative compensates the device clock drift.\n"
            + bridge_line +
            "ignore(clock.assign_new(id=\"portaudio_clock\", sync=\"auto\", [\n"
            "  bus_for_portaudio,\n"
            "]))\n"
            "output.portaudio(\n"
            "  fallible=false,\n"
            + device_line +
            "  mksafe(id=\"portaudio_safe\", bus_for_portaudio),\n"
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
    source_event_url: Optional[str] = DEFAULT_SOURCE_EVENT_URL,
    source_event_timeout_seconds: float = DEFAULT_SOURCE_EVENT_TIMEOUT_SECONDS,
    timeout_seconds: float = DEFAULT_HARBOR_TIMEOUT_SECONDS,
    dj_auth_url: Optional[str] = DEFAULT_DJ_AUTH_URL,
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
    Pypo-side source-switcher (Phase C4 Teil 2) can verify
    ``master_dj.status`` / ``show_dj.status`` via telnet.

    RASTATIME 2026-09-09 (option d): when ``source_event_url`` is set,
    every rendered harbor gets ``on_connect``/``on_disconnect``
    callbacks that POST ``?source=master|show&status=on|off`` to
    PLAYOUT's listener from a detached task (``thread.run``), so the
    switcher learns about a DJ within milliseconds and only verifies
    over telnet instead of polling every 5 s.
    """
    parts = []
    # RASTATIME 2026-09-10: with a dj_auth_url the harbor's auth callback
    # decides (PLAYOUT -> legacy check-live-stream-auth); the static
    # password is passed along as the fallback for an unreachable PLAYOUT.
    main_auth = (
        f'  auth=rastatime_dj_auth("master", "{_escape_liq_string(main_password or "")}"),\n'
        if dj_auth_url else ""
    )
    show_auth = (
        f'  auth=rastatime_dj_auth("show", "{_escape_liq_string(show_password or "")}"),\n'
        if dj_auth_url else ""
    )
    if main_password:
        parts.append(
            "master_dj = input.harbor(\n"
            f'  "{_escape_liq_string(main_mount)}",\n'
            f"  id=\"master_dj\",\n"
            f"  port={int(main_port)},\n"
            f'  password="{_escape_liq_string(main_password)}",\n'
            f"  buffer={_format_crossfade_duration(buffer_seconds)},\n"
            "  icy=true,\n"
            f"  timeout={_format_crossfade_duration(timeout_seconds)},\n"
            f"{main_auth}"
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
            f"  timeout={_format_crossfade_duration(timeout_seconds)},\n"
            f"{show_auth}"
            ")\n"
        )
    if dj_auth_url and parts:
        parts.insert(0, _render_dj_auth_function(dj_auth_url))
    if not parts:
        return (
            "# (no DJ-source harbor enabled — stream.harbor.{main,show}_password\n"
            "#  are unset in rastatime.conf; bus stays on the scheduled queue)\n"
        )
    if source_event_url:
        parts.append(
            _render_harbor_source_events(
                main_enabled=bool(main_password),
                show_enabled=bool(show_password),
                url=source_event_url,
                timeout_seconds=source_event_timeout_seconds,
            )
        )
    return "\n".join(parts)


def _render_dj_auth_function(
    url: str, timeout_seconds: float = DEFAULT_DJ_AUTH_TIMEOUT_SECONDS,
) -> str:
    """
    Render ``rastatime_dj_auth(kind, static_password)``: the harbor's
    ``auth`` callback (RASTATIME 2026-09-10).  Every login attempt is
    POSTed to PLAYOUT (form body, localhost); ``ok`` accepts, anything
    else rejects, and only an unreachable PLAYOUT falls back to the
    static harbor password (user ``source``).  The password never
    appears in a log line.
    """
    timeout = _format_crossfade_duration(timeout_seconds)
    target = _escape_liq_string(url)
    lines = [
        "# RASTATIME 2026-09-10 - DJ logins are checked by PLAYOUT (Settings ->",
        "# Streams -> Master Source; the show's Live Stream Input).  The static",
        "# harbor password from rastatime.conf only counts while PLAYOUT is",
        "# unreachable.  Passwords never reach the log.",
        "def rastatime_dj_auth(kind, static_password) =",
        "  fun (login) ->",
        "    begin",
        "      verdict =",
        "        try",
        "          string.trim(http.post(timeout=" + timeout + ",",
        '            headers=[("Content-Type", "application/x-www-form-urlencoded")],',
        '            data="source=#{kind}&user=#{url.encode(login.user)}"',
        '              ^ "&password=#{url.encode(login.password)}"',
        '              ^ "&address=#{url.encode(login.address)}",',
        '            "' + target + '"))',
        "        catch err do",
        '          log(level=2, label="rastatime.dj_auth",',
        '            "#{kind}: PLAYOUT request failed (#{err})")',
        '          ""',
        "        end",
        "      # A refused connection does not raise: http.post returns an empty",
        "      # body.  Decide on the body - PLAYOUT answers ok / denied / error.",
        '      if verdict == "ok" then',
        '        log(level=3, label="rastatime.dj_auth",',
        '          "#{kind}: accepted user \'#{login.user}\' from #{login.address}")',
        "        true",
        '      elsif verdict == "denied" then',
        '        log(level=3, label="rastatime.dj_auth",',
        '          "#{kind}: rejected user \'#{login.user}\' from #{login.address}")',
        "        false",
        "      else",
        '        ok = login.user == "source" and login.password == static_password',
        '        log(level=3, label="rastatime.dj_auth",',
        '          "#{kind}: PLAYOUT unreachable or failing (\'#{verdict}\') - static check for \'#{login.user}\': #{ok}")',
        "        ok",
        "      end",
        "    end",
        "end",
    ]
    return "\n".join(lines) + "\n"


def _render_harbor_source_events(
    *,
    main_enabled: bool,
    show_enabled: bool,
    url: str,
    timeout_seconds: float = DEFAULT_SOURCE_EVENT_TIMEOUT_SECONDS,
) -> str:
    """
    Render the harbor ``on_connect``/``on_disconnect`` callbacks that
    report DJ connects and drops to PLAYOUT (option d, 2026-09-09).

    The callbacks are registered ``synchronous=true`` so the order of a
    quick connect/disconnect pair is preserved, but the HTTP POST
    itself runs in a detached ``thread.run`` task: a slow or absent
    listener (PLAYOUT restarting) must never stall the harbor
    connection handler.  Failures are logged, never raised - PLAYOUT's
    periodic telnet reconcile is the safety net.
    """
    timeout = _format_crossfade_duration(timeout_seconds)
    target = _escape_liq_string(url)
    lines = [
        "# RASTATIME 2026-09-09 - DJ connect/disconnect events -> PLAYOUT (option d).",
        "# Each harbor reports its source client to PLAYOUT's listener; PLAYOUT",
        "# then verifies once over telnet instead of polling every 5 s (the",
        "# poll leaked ~150 MB/h on the Windows build).  The POST runs in a",
        "# detached task so a slow listener never stalls the harbor handler.",
        "def rastatime_source_event(src, status) =",
        "  thread.run(fun () ->",
        "    try",
        f"      ignore(http.post(timeout={timeout}, data=\"\",",
        f"        \"{target}?source=#{{src}}&status=#{{status}}\"))",
        "    catch err do",
        "      log(level=3, label=\"rastatime.source_event\",",
        "        \"POST #{src}/#{status} failed: #{err}\")",
        "    end)",
        "end",
        "# Telnet marker for PLAYOUT: this render posts harbor events.  PLAYOUT",
        "# keeps its old 5-s status poll while an older render is loaded.",
        "server.register(namespace=\"rastatime\", "
        "description=\"Harbor source events rendered (option d)\",",
        "  \"source_events\", fun (_) -> \"on\")",
    ]
    for enabled, source_id, name in (
        (main_enabled, "master_dj", "master"),
        (show_enabled, "show_dj", "show"),
    ):
        if not enabled:
            continue
        lines.append(
            f"{source_id}.on_connect(synchronous=true, "
            f"fun (_) -> rastatime_source_event(\"{name}\", \"on\"))"
        )
        lines.append(
            f"{source_id}.on_disconnect(synchronous=true, "
            f"fun () -> rastatime_source_event(\"{name}\", \"off\"))"
        )
    return "\n".join(lines) + "\n"


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
    bridge = _format_crossfade_duration(DEFAULT_WEBSTREAM_BRIDGE_SECONDS)
    bridge_max = _format_crossfade_duration(DEFAULT_WEBSTREAM_BRIDGE_MAX_SECONDS)
    return (
        "# RASTATIME 2026-09-08 - a FRESH input.http (with its own clock bridge)\n"
        "# per slot.  A reused input.http reconnects through one Duppy async\n"
        "# task whose wake-up is unreliable on this Windows build under normal\n"
        "# load: in four of five production-like replica runs a start hung\n"
        "# 20-110 s in 'starting'/'polling' (Phase D 2026-09-08: 48 s and 97 s\n"
        "# live, one slot never came on air), while the FIRST start of a fresh\n"
        "# source was fast in 9/9 cycles.  A fresh bridge also means no stale\n"
        "# audio from the previous slot at the slot start.  PLAYOUT keeps its\n"
        "# telnet contract: webstream.url [<url>], .start, .stop, .status,\n"
        "# .ready, .watchdog and var.set webstream.gain.\n"
        'webstream_gain = interactive.float("webstream.gain", 1.0)\n'
        'webstream_url = ref("")\n'
        "webstream_seq = ref(0)\n"
        'webstream_active_url = ref("")\n'
        "webstream_started = ref(false)\n"
        "webstream_current = ref(source.fail())\n"
        "webstream_stopper = ref(fun () -> ())\n"
        'webstream_status_fn = ref(fun () -> "stopped")\n'
        'webstream_current_name = ref("")\n'
        "webstream_reaper = ref(fun () -> ())\n"
        "webstream_zombies = ref([])\n"
        "webstream_reaped = ref(0)\n"
        "# The bus arm: whatever the current slot's bridge is (source.fail()\n"
        "# between slots, so the switch falls through exactly as before).\n"
        'webstream_raw = source.dynamic(id="webstream", self_sync=false,\n'
        "  track_sensitive=false, {webstream_current()})\n"
        "webstream = amplify({webstream_gain()}, webstream_raw)\n"
        "\n"
        "def webstream_stop() =\n"
        "  if webstream_started() then\n"
        "    f = webstream_stopper()\n"
        "    f()\n"
        "    status_fn = webstream_status_fn()\n"
        '    if status_fn() != "stopped" then\n'
        "      # input.http loses a stop while it polls a dead server (the\n"
        "      # connect task overwrites Stopping with Starting after each\n"
        "      # failed attempt): the dropped input would reconnect on its own\n"
        "      # and hold a listener slot for nothing.  The reaper below stops\n"
        "      # it for good once it reports connected (2026-09-08 22:23).\n"
        "      webstream_zombies.set(list.append(webstream_zombies(),\n"
        "        [(webstream_current_name(), status_fn, webstream_reaper())]))\n"
        "    end\n"
        "  end\n"
        "  webstream_started.set(false)\n"
        '  webstream_active_url.set("")\n'
        "  webstream_current.set(source.fail())\n"
        "  webstream_stopper.set(fun () -> ())\n"
        '  webstream_status_fn.set(fun () -> "stopped")\n'
        '  "Done"\n'
        "end\n"
        "\n"
        "def webstream_reap() =\n"
        "  if list.length(webstream_zombies()) > 0 then\n"
        "    webstream_zombies.set(list.filter(fun (z) -> begin\n"
        "      let (name, status_fn, reap_fn) = z\n"
        "      st = status_fn()\n"
        '      if st == "stopped" then\n'
        "        false\n"
        '      elsif string.contains(prefix="connected", st) then\n'
        '        log(level=2, label="webstream_watchdog",\n'
        '            "dropped input #{name} reconnected on its own - reaping (start+stop)")\n'
        "        reap_fn()\n"
        "        webstream_reaped.set(webstream_reaped() + 1)\n"
        "        true\n"
        "      else\n"
        "        true\n"
        "      end\n"
        "    end, webstream_zombies()))\n"
        "  end\n"
        "end\n"
        "\n"
        "def webstream_start() =\n"
        "  url = webstream_url()\n"
        '  if url == "" then\n'
        '    "ERROR: no url set - send webstream.url <url> first"\n'
        "  elsif webstream_started() and webstream_active_url() == url then\n"
        '    "already started"\n'
        "  else\n"
        "    if webstream_started() then ignore(webstream_stop()) end\n"
        "    webstream_seq.set(webstream_seq() + 1)\n"
        "    n = webstream_seq()\n"
        '    s = input.http(id="webstream_in_#{n}", start=true, self_sync=false,\n'
        f"      max_buffer={_format_crossfade_duration(max_buffer_seconds)},\n"
        f"      timeout={_format_crossfade_duration(timeout_seconds)},\n"
        f"      poll_delay={_format_crossfade_duration(poll_delay_seconds)},\n"
        "      url)\n"
        '    b = buffer(id="webstream_bridge_#{n}",\n'
        f"      buffer={bridge}, max={bridge_max}, s)\n"
        "    webstream_stopper.set(fun () -> s.stop())\n"
        "    webstream_status_fn.set(fun () -> s.status())\n"
        '    webstream_current_name.set("webstream_in_#{n}")\n'
        "    # start+stop on a source that reconnected after being dropped:\n"
        "    # start is a no-op while connected, stop then really disconnects\n"
        "    webstream_reaper.set(fun () -> begin\n"
        "      s.start()\n"
        "      s.stop()\n"
        "    end)\n"
        "    webstream_active_url.set(url)\n"
        "    webstream_started.set(true)\n"
        "    webstream_current.set(b)\n"
        '    "Done"\n'
        "  end\n"
        "end\n"
        "\n"
        'server.register(namespace="webstream", usage="url [<url>]",\n'
        '  description="Get, or set, the URL the next webstream.start opens (a fresh input per start)",\n'
        '  "url", fun (arg) -> if arg == "" then webstream_url() else\n'
        "    webstream_url.set(arg)\n"
        '    "Done"\n'
        "  end)\n"
        'server.register(namespace="webstream", description="Open a fresh input for the current URL (no-op if that URL is already playing)",\n'
        '  "start", fun (_) -> webstream_start())\n'
        'server.register(namespace="webstream", description="Stop and drop the current input; the bus arm falls through",\n'
        '  "stop", fun (_) -> webstream_stop())\n'
        'server.register(namespace="webstream", description="Status of the current input (stopped / starting / polling / connected <url>)",\n'
        '  "status", fun (_) -> begin\n'
        "    f = webstream_status_fn()\n"
        "    f()\n"
        "  end)\n"
        'server.register(namespace="webstream", description="Webstream source producing audio right now (watchdog probe)",\n'
        '  "ready", fun (_) -> string(source.is_ready(webstream)))\n'
    )


def _render_webstream_watchdog_block(
    *,
    webstream_enabled: bool,
    check_frames: int = DEFAULT_WEBSTREAM_WATCHDOG_CHECK_FRAMES,
    starve_checks: int = DEFAULT_WEBSTREAM_WATCHDOG_STARVE_CHECKS,
) -> str:
    """
    Render the in-process webstream watchdog (RASTATIME 2026-09-07).

    Placed right after the final ``bus`` definition: ``bus.on_frame``
    runs in the streaming thread on every frame, so counting frames
    there and checking ``source.is_ready(webstream)`` every
    ``check_frames`` frames never touches the Duppy scheduler - the
    thread whose ``Unix.select`` leaks ~5-50 KB per call on the
    savonet Windows build.  The scheduler-side watchdog of 2026-09-06
    did the same check over telnet (~87 KB per poll in production,
    ~157 MB per webstream hour); a ``thread.run.recurrent`` timer
    would still cost ~31 KB per tick.  Measured in a 15-min replica
    run on 2026-09-07: the frame counter is flat.

    Semantics are the scheduler watchdog's: only while the input is
    started; a not-ready right after start (buffer-up, or right after
    our own reconnect) does not count; ``starve_checks`` not-ready
    checks after a ready one -> clean ``stop`` + ``start`` of the
    input, run from a one-shot ``thread.run`` (the streaming thread
    must not block on socket teardown).  A DJ on air hides the bus
    from the bridge, which then stays full and ready - no false
    alarm.  ``webstream.watchdog`` (telnet) reports the counters.

    Without a webstream input a comment stub is rendered.  The PLAYOUT
    fallback (``RASTATIME_WEBSTREAM_WATCHDOG=scheduler``, a reaper-only
    hook here) was removed on 2026-09-15 after a quiet week.
    """
    if not webstream_enabled:
        return (
            "# ---------------------------------------------------------------------\n"
            "# RASTATIME 2026-09-07 - in-process webstream watchdog: disabled\n"
            "# (no webstream input is rendered)\n"
            "# ---------------------------------------------------------------------\n"
        )
    check_frames = max(1, int(check_frames))
    starve_checks = max(1, int(starve_checks))
    return (
        "# ---------------------------------------------------------------------\n"
        "# RASTATIME 2026-09-07 - in-process webstream watchdog\n"
        "# ---------------------------------------------------------------------\n"
        "# input.http does not notice a silent mid-stream stall (the cloud DEVA\n"
        "# failure mode of 2026-09-06).  This watchdog counts the bus's frames\n"
        f"# in the streaming thread and, every {check_frames} frames\n"
        f"# ({check_frames * 0.02:.0f} s), checks source.is_ready(webstream) while the input is\n"
        f"# started.  After {starve_checks} not-ready checks that follow a ready one it\n"
        "# reconnects (stop + start) from a one-shot thread.  No telnet, no timer:\n"
        "# both leak memory on the Windows build (Unix.select), this does not\n"
        "# (measured 2026-09-07).  Counters: telnet `webstream.watchdog`.\n"
        "webstream_wd_frames = ref(0)\n"
        "webstream_wd_checks = ref(0)\n"
        "webstream_wd_seen_ready = ref(false)\n"
        "webstream_wd_starved = ref(0)\n"
        "webstream_wd_reconnects = ref(0)\n"
        "\n"
        "def webstream_wd_reconnect() =\n"
        "  webstream_wd_reconnects.set(webstream_wd_reconnects() + 1)\n"
        '  log(level=2, label="webstream_watchdog",\n'
        f'      "upstream stalled ({starve_checks} not-ready checks after being ready) - "\n'
        '      ^ "reconnecting: stop + start")\n'
        "  ignore(webstream_stop())\n"
        "  ignore(webstream_start())\n"
        "end\n"
        "\n"
        "def webstream_wd_check() =\n"
        "  webstream_wd_checks.set(webstream_wd_checks() + 1)\n"
        "  webstream_reap()\n"
        "  linein_http_reap()\n"
        "  if webstream_started() then\n"
        "    if source.is_ready(webstream) then\n"
        "      webstream_wd_seen_ready.set(true)\n"
        "      webstream_wd_starved.set(0)\n"
        "    elsif webstream_wd_seen_ready() then\n"
        "      webstream_wd_starved.set(webstream_wd_starved() + 1)\n"
        f"      if webstream_wd_starved() >= {starve_checks} then\n"
        "        webstream_wd_seen_ready.set(false)\n"
        "        webstream_wd_starved.set(0)\n"
        "        thread.run(webstream_wd_reconnect)\n"
        "      end\n"
        "    end\n"
        "  else\n"
        "    webstream_wd_seen_ready.set(false)\n"
        "    webstream_wd_starved.set(0)\n"
        "  end\n"
        "end\n"
        "\n"
        "bus.on_frame(synchronous=true, fun () -> begin\n"
        "  webstream_wd_frames.set(webstream_wd_frames() + 1)\n"
        f"  if webstream_wd_frames() mod {check_frames} == 0 then webstream_wd_check() end\n"
        "end)\n"
        "\n"
        'server.register(namespace="webstream",\n'
        '  description="In-process watchdog counters (checks, reconnects, state)",\n'
        '  "watchdog", fun (_) ->\n'
        '    "checks=#{webstream_wd_checks()} reconnects=#{webstream_wd_reconnects()} "\n'
        '    ^ "started=#{webstream_started()} ready=#{source.is_ready(webstream)} "\n'
        '    ^ "seen_ready=#{webstream_wd_seen_ready()} starved=#{webstream_wd_starved()} "\n'
        '    ^ "zombies=#{list.length(webstream_zombies())} reaped=#{webstream_reaped()}")\n'
    )


def _render_linein_input_block(
    *,
    enabled: bool,
    max_buffer_seconds: float = DEFAULT_LINEIN_MAX_BUFFER_SECONDS,
    http_url: str = DEFAULT_LINEIN_HTTP_URL,
    http_max_buffer_seconds: float = DEFAULT_LINEIN_HTTP_MAX_BUFFER_SECONDS,
    http_poll_delay_seconds: float = DEFAULT_LINEIN_HTTP_POLL_DELAY_SECONDS,
) -> str:
    """
    Render the ``input.ffmpeg(format="dshow")`` block for scheduled
    line-inputs (Phase-F-2, 2026-05-30).

    Opens a Windows dshow audio device DIRECTLY via Liquidsoap's
    in-process libavdevice — no external ffmpeg subprocess, no HTTP
    hop (this replaces the Phase-F input.http + FfmpegLineinCapture
    approach).

    ``start=false`` keeps the source idle (no device opened) until
    Pypo issues the runtime sequence:

        linein.set_url <dshow-spec>   # e.g. audio=@device_cm_{..}\\wave_{..}
        linein.start
          ... show plays ...
        linein.stop

    The dshow-spec is the device's alternative-name form, built by
    Pypo from the schedule item's device GUID (_stable_id_to_dshow_audio).
    Runtime device-switch works (set_url with a different spec) — the
    key capability input.portaudio lacked.

    Why server.register: input.ffmpeg (unlike input.http) does NOT
    auto-expose its set_url / start / stop / status methods as telnet
    commands.  Spike 2026-05-30 confirmed the methods exist on the
    source object but aren't registered under the source-id namespace.
    So we register them manually under the "linein" namespace.

    ``self_sync=false`` hands clock control to Liquidsoap's main clock
    (the dshow card is the audio source but we don't want it driving
    the whole pipeline's tick rate).  No buffer() wrapper needed here:
    the linein source feeds the switch directly (NOT through crossfade,
    which only wraps the scheduled source since the Phase-E fix), and
    the switch tolerates self_sync=false sources.  Skipping the buffer
    keeps live-mic latency minimal.

    RASTATIME 2026-10-02 - an ``amplify`` around the arm applies the
    per-line-in input gain (``rastatime_linein.input_gain_db``), same
    pattern as the webstream arm: the scheduler pushes the linear
    factor with ``var.set linein.gain`` whenever a line-in goes on air;
    default 1.0 = unity.

    When ``enabled`` is False (legacy mpv/VLC paths), emits a comment
    stub.
    """
    if not enabled:
        return (
            "# (linein input.ffmpeg disabled — Liquidsoap engine not\n"
            "#  active; legacy mpv/VLC handles line-inputs via separate path)\n"
        )
    return (
        "linein_raw = input.ffmpeg(\n"
        '  id="linein",\n'
        "  format=\"dshow\",\n"
        "  start=false,\n"
        "  self_sync=false,\n"
        f"  max_buffer={_format_crossfade_duration(max_buffer_seconds)},\n"
        '  "",\n'
        ")\n"
        "\n"
        "# audio_to_stereo fixes the content type to audio=pcm(stereo).\n"
        "# input.ffmpeg returns a polymorphic source('a) (audio+video\n"
        "# capable); without this the switch() below rejects the arm\n"
        "# with a type mismatch against the other (audio-only) sources.\n"
        "linein_dshow = audio_to_stereo(linein_raw)\n"
        "\n"
        "# input.ffmpeg does NOT auto-register its runtime controls as\n"
        "# telnet commands (unlike input.http).  Register them manually\n"
        "# under the \"linein\" namespace so Pypo can drive the dshow\n"
        "# device at show-start/-end.  Commands act on linein_raw (the\n"
        "# input.ffmpeg source that has set_url/start/stop/status; the\n"
        "# audio_to_stereo wrapper doesn't expose them).  Spike-verified\n"
        "# 2026-05-30.\n"
        'server.register(\n'
        '  namespace="linein", description="Set the dshow input spec",\n'
        '  "set_url", fun (spec) -> begin linein_raw.set_url(spec); "Done" end\n'
        ")\n"
        'server.register(\n'
        '  namespace="linein", description="Start the dshow capture",\n'
        '  "start", fun (_) -> begin linein_raw.start(); "Done" end\n'
        ")\n"
        'server.register(\n'
        '  namespace="linein", description="Stop the dshow capture",\n'
        '  "stop", fun (_) -> begin linein_raw.stop(); "Done" end\n'
        ")\n"
        'server.register(\n'
        '  namespace="linein", description="dshow capture status",\n'
        '  "status", fun (_) -> linein_raw.status()\n'
        ")\n"
        "\n"
        "# RASTATIME 2026-08-31 — multichannel line-in path (BACKLOG\n"
        '# "Line-In: Kanal-Auswahl auf Multi-Input-Devices"), widened to\n'
        "# every mapping on 2026-09-03.  Pypo starts FfmpegLineinCapture\n"
        "# with its sounddevice/MME feeder (selected channels -> stereo\n"
        "# mp3 on the local /linein-capture mount) and Liquidsoap\n"
        "# consumes the mount through this second source.  The\n"
        "# direct-dshow source above is now only the fallback for legacy\n"
        "# rows with no stored device name.  URL is fixed at render time.\n"
        "# RASTATIME 2026-10-21 - a FRESH input.http per line-in slot, the\n"
        "# webstream lesson of 2026-09-08: the reused source did not reconnect\n"
        "# on its second start after a stop (the switch fell to\n"
        "# silence_fallback for the whole slot on 2026-10-20 21:12 and\n"
        "# 2026-10-21 08:42 although the feeder streamed).  PLAYOUT keeps its\n"
        "# telnet contract: linein_http.start / .stop (+ .status).\n"
        "linein_http_seq = ref(0)\n"
        "linein_http_started = ref(false)\n"
        "linein_http_current = ref(source.fail())\n"
        "linein_http_stopper = ref(fun () -> ())\n"
        'linein_http_status_fn = ref(fun () -> "stopped")\n'
        'linein_http_current_name = ref("")\n'
        "linein_http_reaper = ref(fun () -> ())\n"
        "linein_http_zombies = ref([])\n"
        'linein_http_raw = source.dynamic(id="linein_http", self_sync=false,\n'
        "  track_sensitive=false, {linein_http_current()})\n"
        "linein_http = audio_to_stereo(linein_http_raw)\n"
        "\n"
        "def linein_http_stop() =\n"
        "  if linein_http_started() then\n"
        "    f = linein_http_stopper()\n"
        "    f()\n"
        "    status_fn = linein_http_status_fn()\n"
        '    if status_fn() != "stopped" then\n'
        "      # a stop lost while polling the (gone) mount: reaped once the\n"
        "      # input reports connected again, like the webstream zombies\n"
        "      linein_http_zombies.set(list.append(linein_http_zombies(),\n"
        "        [(linein_http_current_name(), status_fn, linein_http_reaper())]))\n"
        "    end\n"
        "  end\n"
        "  linein_http_started.set(false)\n"
        "  linein_http_current.set(source.fail())\n"
        "  linein_http_stopper.set(fun () -> ())\n"
        '  linein_http_status_fn.set(fun () -> "stopped")\n'
        '  "Done"\n'
        "end\n"
        "\n"
        "def linein_http_reap() =\n"
        "  if list.length(linein_http_zombies()) > 0 then\n"
        "    linein_http_zombies.set(list.filter(fun (z) -> begin\n"
        "      let (name, status_fn, reap_fn) = z\n"
        "      st = status_fn()\n"
        '      if st == "stopped" then\n'
        "        false\n"
        '      elsif string.contains(prefix="connected", st) then\n'
        '        log(level=2, label="linein_http",\n'
        '            "dropped input #{name} reconnected on its own - reaping (start+stop)")\n'
        "        reap_fn()\n"
        "        true\n"
        "      else\n"
        "        true\n"
        "      end\n"
        "    end, linein_http_zombies()))\n"
        "  end\n"
        "end\n"
        "\n"
        "def linein_http_start() =\n"
        "  if linein_http_started() then ignore(linein_http_stop()) end\n"
        "  linein_http_seq.set(linein_http_seq() + 1)\n"
        "  n = linein_http_seq()\n"
        '  s = input.http(id="linein_http_in_#{n}", start=true, self_sync=false,\n'
        "    # format forced: skips FFmpeg's ~5 s autodetect on the mount\n"
        f'    format="{LINEIN_HTTP_FORMAT}",\n'
        f"    max_buffer={_format_crossfade_duration(http_max_buffer_seconds)},\n"
        f"    poll_delay={_format_crossfade_duration(http_poll_delay_seconds)},\n"
        f'    "{http_url}")\n'
        "  linein_http_stopper.set(fun () -> s.stop())\n"
        "  linein_http_status_fn.set(fun () -> s.status())\n"
        '  linein_http_current_name.set("linein_http_in_#{n}")\n'
        "  linein_http_reaper.set(fun () -> begin\n"
        "    s.start()\n"
        "    s.stop()\n"
        "  end)\n"
        "  linein_http_started.set(true)\n"
        "  linein_http_current.set(s)\n"
        '  "Done"\n'
        "end\n"
        "\n"
        'server.register(namespace="linein_http", description="Open a fresh input for the /linein-capture mount",\n'
        '  "start", fun (_) -> linein_http_start())\n'
        'server.register(namespace="linein_http", description="Stop and drop the current input; the arm falls through",\n'
        '  "stop", fun (_) -> linein_http_stop())\n'
        'server.register(namespace="linein_http", description="Status of the current input (stopped / starting / polling / connected <url>)",\n'
        '  "status", fun (_) -> begin\n'
        "    f = linein_http_status_fn()\n"
        "    f()\n"
        "  end)\n"
        "\n"
        "# One switch arm serves both paths: Pypo only ever starts one\n"
        "# of the two sources per show, so a track-insensitive fallback\n"
        "# simply forwards whichever is up.\n"
        "# RASTATIME 2026-10-02 - per-line-in input gain (rastatime_linein.\n"
        "# input_gain_db): PLAYOUT sets the linear factor with\n"
        "# var.set linein.gain whenever a line-in goes on air.\n"
        'linein_gain = interactive.float("linein.gain", 1.0)\n'
        "linein = amplify({linein_gain()},\n"
        "  fallback(track_sensitive=false, [linein_dshow, linein_http]))\n"
    )


def _render_hourly_recording_block(
    *,
    enabled: bool,
    folder: str,
    fmt: str = DEFAULT_HOURLY_RECORDING_FORMAT,
    bitrate: int = DEFAULT_HOURLY_RECORDING_BITRATE,
    samplerate: int = DEFAULT_SAMPLERATE,
) -> str:
    """
    Render the 24/7 hourly archive recorder block (RASTATIME 2026-06-05).

    A second ``output.file`` on the ``bus`` that runs continuously and
    rotates to a new file at each clock-hour boundary via ``reopen_when``
    — independent of shows, so it captures what per-show recording misses
    (AutoDJ filler, silence, unscheduled content, emergencies).

    ``enabled`` False or empty ``folder`` -> a comment stub, so the live
    stream is unaffected until the operator turns it on in Settings ->
    Local Machine.

    Filename re-evaluated at each (re)open ->
        <folder>/<YYYY-MM-DD>/<YYYY-MM-DD HH>-00.<ext>
    in the system local timezone (operator-visible wall-clock).  The
    per-day subfolder is created on reopen via file.mkdir.

    ``rec247_seg`` is seeded with the current hour so there is NO spurious
    reopen at boot — a -1 sentinel would split the first hour into two
    files (Phase-1 reality-test 2026-06-05 confirmed the quirk + fix).

    Raises ValueError for an unsupported ``fmt`` so a misconfiguration is
    loud at render time rather than a silently missing recorder.
    """
    fmt = str(fmt or DEFAULT_HOURLY_RECORDING_FORMAT).lower()
    folder = str(folder or "").strip()

    if not enabled or not folder:
        return (
            "# (24/7 hourly recording disabled — enable it AND set a folder\n"
            "#  in Settings -> Local Machine to turn it on)\n"
        )

    if fmt not in _ENCODER_FOR_TYPE:
        raise ValueError(
            f"Unsupported 24/7 recording format {fmt!r} — "
            f"must be one of {sorted(_ENCODER_FOR_TYPE)}"
        )

    try:
        bitrate = int(bitrate)
    except (TypeError, ValueError):
        bitrate = DEFAULT_HOURLY_RECORDING_BITRATE

    try:
        samplerate = int(samplerate or DEFAULT_SAMPLERATE)
    except (TypeError, ValueError):
        samplerate = DEFAULT_SAMPLERATE
    if fmt == "opus" and samplerate not in _OPUS_VALID_SAMPLERATES:
        logger.warning(
            "24/7 recording samplerate %d Hz not supported by libopus; "
            "clamping to 48000 Hz", samplerate,
        )
        samplerate = 48000

    encoder = (
        _ENCODER_FOR_TYPE[fmt]
        .replace("${BITRATE}", str(bitrate))
        .replace("${SAMPLERATE}", str(samplerate))
    )
    ext = _FILE_EXT_FOR_TYPE[fmt]

    # Liquidsoap path: forward slashes (its parser prefers them on
    # Windows), no trailing slash, escaped for the string literal.
    folder_liq = _escape_liq_string(folder.replace("\\", "/").rstrip("/"))

    return (
        "# 24/7 hourly archive recorder (continuous, rotates on the hour).\n"
        "# rec247_seg seeded with the current hour -> no spurious reopen at\n"
        "# boot.  The filename fn creates the per-day subfolder on reopen.\n"
        "# time() not gettimeofday(): the latter is deprecated in 2.4 and\n"
        "# this predicate runs per frame - the deprecation WARNING flooded\n"
        "# the logs at ~530 MB/day (found 2026-09-18).\n"
        "rec247_seg = ref(int(time() / 3600.))\n"
        "def rec247_reopen() =\n"
        "  cur = int(time() / 3600.)\n"
        "  if cur != rec247_seg() then\n"
        "    rec247_seg := cur\n"
        "    true\n"
        "  else\n"
        "    false\n"
        "  end\n"
        "end\n"
        "def rec247_path() =\n"
        '  day = time.string("%Y-%m-%d")\n'
        '  hh  = time.string("%H")\n'
        f'  base = "{folder_liq}/#{{day}}/#{{day}} #{{hh}}-00"\n'
        "  d = path.dirname(base)\n"
        "  if not file.exists(d) then ignore(file.mkdir(d)) end\n"
        "  # RASTATIME 2026-09-16: never open an existing hour file - the ffmpeg\n"
        "  # muxer truncates it even in append mode (measured).  A restart\n"
        "  # inside the hour continues in <hour>-00.2.<ext>, .3. ...; the cue\n"
        "  # sidecar lists the parts.\n"
        "  def candidate(n) =\n"
        f'    if n == 1 then "#{{base}}.{ext}" else "#{{base}}.#{{n}}.{ext}" end\n'
        "  end\n"
        "  n = ref(1)\n"
        "  while file.exists(candidate(n())) do n := n() + 1 end\n"
        "  candidate(n())\n"
        "end\n"
        "output.file(\n"
        '  id="recording_hourly",\n'
        "  reopen_when=rec247_reopen,\n"
        "  reopen_delay={120.},\n"
        "  fallible=true,\n"
        f"  {encoder},\n"
        "  {rec247_path()},\n"
        "  bus,\n"
        ")\n"
    )


def _render_loudness_block(ceiling_dbtp: Optional[float]) -> str:
    """
    RASTATIME 2026-09-28 - EBU R128 stage 1: the peak safety after the
    per-track gain.  Rendered only when Settings -> Streams -> Loudness
    Normalization is "EBU R128" (``ceiling_dbtp`` = the true-peak ceiling);
    otherwise the bus is untouched, exactly as before.  ``limit`` is
    Liquidsoap's compressor at ratio 20 with a 5 ms attack - a sample-peak
    limiter, which with a -23 LUFS target leaves ample headroom; the ceiling
    is an interactive float so the scheduler can move it over telnet.
    """
    if ceiling_dbtp is None:
        return "# loudness limiter: off (Loudness Normalization is not EBU R128)\n"
    ceiling = max(-20.0, min(0.0, float(ceiling_dbtp)))
    return (
        "# RASTATIME 2026-09-28 - EBU R128: peak safety after the per-track gain.\n"
        "# The ceiling follows Settings -> Streams (True Peak Ceiling); a change\n"
        "# is applied by the settings restart or `var.set loudness_ceiling`.\n"
        f'loudness_ceiling = interactive.float("loudness_ceiling", {ceiling:.1f})\n'
        'bus = limit(id="loudness_limit", threshold=loudness_ceiling, attack=5., release=80., ratio=20., bus)\n'
    )


# RASTATIME 2026-10-02 - output processing with Stereo Tool (optional, off
# by default).  Liquidsoap's `stereotool()` operator loads the Stereo Tool
# library (DLL) and runs the whole bus through it right before the
# outputs: loudness control to the broadcast standard, multiband, final
# limiter - the sound the distribution partners measure.  The settings
# live in cc_pref (Settings -> Streams -> Output Processing); a station
# without a licence simply leaves it off.
#
# Safety: `liquidsoap --check` does NOT notice a missing or broken library
# (bench 2026-10-02: check rc 0, the start fails with "File not found") and
# a Liquidsoap that dies at start is a crash loop under NSSM.  So the block
# is rendered only when the library file exists, and the scheduler sets
# STEREOTOOL_LOCKOUT when the fresh instance does not stay up after a start
# with Stereo Tool - every later render in this process is without it and
# the preflight warns (see STEREOTOOL_STATE).
STEREOTOOL_LOCKOUT: Dict[str, object] = {"active": False, "reason": ""}
#: what the last render did with Stereo Tool - read by the preflight scan
STEREOTOOL_STATE: Dict[str, object] = {"enabled": False, "active": False, "problem": ""}


class StereoToolSettings(NamedTuple):
    enabled: bool = False
    library_file: str = ""
    preset_file: str = ""
    license_key: str = ""


def stereotool_settings_from_prefs(entries: Mapping[str, object]) -> StereoToolSettings:
    """``cc_pref`` rows (key -> value) to settings; unknown / empty = off."""
    raw = str(entries.get("stereotool_enabled") or "").strip().lower()
    return StereoToolSettings(
        enabled=raw in ("1", "true", "yes", "on"),
        library_file=str(entries.get("stereotool_library") or "").strip(),
        preset_file=str(entries.get("stereotool_preset") or "").strip(),
        license_key=str(entries.get("stereotool_license_key") or "").strip(),
    )


def _liq_path(path: str) -> str:
    """A Windows path as a Liquidsoap string literal (forward slashes)."""
    return path.replace("\\", "/").replace('"', '\\"')


def _render_stereotool_block(settings: Optional[StereoToolSettings]) -> Tuple[str, bool]:
    """
    The Stereo Tool block for the bus, and whether it is active.  Off,
    locked out after a crash, or a missing library file render a comment
    (the bus stays as it is) and are recorded in STEREOTOOL_STATE.
    """
    settings = settings or StereoToolSettings()
    STEREOTOOL_STATE.update(enabled=settings.enabled, active=False, problem="")
    if not settings.enabled:
        return "# output processing (Stereo Tool): off\n", False
    if STEREOTOOL_LOCKOUT.get("active"):
        reason = str(STEREOTOOL_LOCKOUT.get("reason") or "a crash after a start with Stereo Tool")
        STEREOTOOL_STATE["problem"] = f"locked out until the next PLAYOUT restart: {reason}"
        logger.error("Stereo Tool is enabled but locked out (%s) - rendering without it.", reason)
        return f"# output processing (Stereo Tool): LOCKED OUT - {reason}\n", False
    if not settings.library_file or not os.path.isfile(settings.library_file):
        STEREOTOOL_STATE["problem"] = (
            f"library file not found: {settings.library_file or '(empty)'}"
        )
        logger.warning(
            "Stereo Tool is enabled but the library file %r does not exist - "
            "rendering without it (Settings -> Streams -> Output Processing).",
            settings.library_file,
        )
        return (
            f"# output processing (Stereo Tool): library file not found "
            f"({_liq_path(settings.library_file or '(empty)')}) - OFF\n",
            False,
        )
    if settings.preset_file and not os.path.isfile(settings.preset_file):
        logger.warning(
            "Stereo Tool preset file %r does not exist - starting with the "
            "library's defaults.", settings.preset_file,
        )
    args = [f'library_file="{_liq_path(settings.library_file)}"']
    if settings.license_key:
        args.append(f'license_key="{_liq_path(settings.license_key)}"')
    if settings.preset_file and os.path.isfile(settings.preset_file):
        args.append(f'preset="{_liq_path(settings.preset_file)}"')
    STEREOTOOL_STATE["active"] = True
    return (
        "# RASTATIME 2026-10-02 - output processing: Stereo Tool on the whole bus\n"
        "# (after the per-track gain and the loudness limiter, before the ICY\n"
        "# rewrite and every output: Icecast, 24/7 recording, Main Output).\n"
        "# Settings -> Streams -> Output Processing; a change is applied by the\n"
        "# planned restart.  Licence and preset come from the settings.\n"
        f'bus = stereotool(id="stereotool", {", ".join(args)}, bus)\n',
        True,
    )


def stereotool_render_active(settings: Optional[StereoToolSettings]) -> bool:
    """Would a render with ``settings`` put Stereo Tool on the bus?"""
    return _render_stereotool_block(settings)[1]


def _render_crossfade_block(
    track_seconds: float = DEFAULT_CROSSFADE_DURATION,
    show_seconds: float = DEFAULT_SHOW_CROSSFADE_DURATION,
) -> str:
    """
    RASTATIME 2026-09-27 - render ``scheduled_x = cross(...)`` around the
    request queue plus the transition function.

    Shapes, selected by the interactive string ``rt_cross`` that PLAYOUT
    sets right before it pushes (natural end) or skips (overbook):

      track       in-show, natural end: old fades out over its LAST
                  TRACK seconds, new fades in over TRACK - the rows
                  overlap by TRACK in the schedule, so the new track
                  starts at its row start.  With TRACK = 0 the tail
                  plays out and the new track follows (sequence).
      show        show boundary, natural end: the old show's last track
                  fades out over its last SHOW seconds, the new show's
                  first track follows at the old track's end.
      track_skip  in-show skip (rare - the row layout was off): old
                  fades from NOW over TRACK, new fades in over TRACK.
      show_skip   overbook at a show boundary: the new show's first
                  track starts at full level at once, the old track
                  fades out UNDER it over SHOW seconds.
      instant     50 ms hand-over (silent or empty partner, or asked for).

    "No Fade during Crossover" (``rt_nofade`` = old | new | both | -, set
    together with the shape): the flagged track keeps its full level
    while the other one fades - the overlap stays.  An unfaded OLD track
    plays its tail out (natural shapes) or is cut with a 50 ms ramp
    (skip shapes: it has to end now); an unfaded NEW track comes in at
    full level (50 ms ramp).  "No fade" on the old track is a 1 ms
    fade.out with a delay the tail never reaches: fade.out starts at the
    delay OR when the remaining time is down to its duration, whichever
    comes first, and stays silent afterwards (bench 2026-09-27).

    The ending track's tail is BUFFER = max(TRACK, SHOW, floor) seconds
    (cross pre-buffers it, so a skip also has a tail - as long as the
    track has played longer than BUFFER; measured 2026-09-27).  Natural
    shapes wait ``BUFFER - D`` before fading (fade.out delay + a blank in
    front of the new track); skip shapes trim the tail with
    max_duration.  A silent or empty partner always hands over at once.

    Overlap per transition (2026-09-29): the in-show shapes read the
    overlap ``d`` from the interactive float ``rt_dur`` (seconds; 0 = the
    old track plays out and the new one follows at its end; -1 = the house
    track crossfade rendered here).  PLAYOUT sends the smaller of the two
    tracks' values (crossfade per track type, 0 for "Exclude from
    Crossover"); the legacy scheduler lays the rows out with the same
    overlap, so a track starts at its row start.

    Metadata (bench 2026-09-28): ``add`` forwards only the FIRST source's
    metadata and ``cross`` replays the ending track's metadata on its
    buffered tail.  The new track is therefore the first element of every
    ``add`` and the tail is wrapped in ``source.drop.metadata`` - otherwise the
    stream title and the Live Text showed the previous track until the
    next transition (regression of the 2026-09-27 shapes).
    """
    track = max(0.0, float(track_seconds))
    show = max(0.0, float(show_seconds))
    buf = crossfade_buffer_seconds(track, show)
    f = _format_crossfade_duration
    nofade = "0.001"  # a 1 ms fade.out = the track keeps its level to the end
    never = "999999.0"  # a fade.out delay the tail never reaches; the remaining-based start still fades the last ms

    # natural show shape: the old track fades over its last SHOW seconds and
    # the new one FOLLOWS (no overlap - the boundary is the old track's end)
    if show < 0.05:
        show_natural = "    sequence([old_s, new.source])\n"
    else:
        show_natural = (
            "    sequence([fade.out(duration=s_out, delay=s_delay, old_s), new.source])\n"
        )
    if show < 0.05:
        show_skip = "    rt_instant(old_s, new.source)\n"
    else:
        show_skip = (
            "    add(normalize=false, [fade.in(duration=0.05, new.source),\n"
            "                          fade.out(duration=s_cut, max_duration(s_cut, old_s))])\n"
        )
    # RASTATIME 2026-09-29 - the in-show shapes take the overlap of THIS
    # transition from rt_dur (crossfade per track type / Exclude from
    # Crossover): d seconds, 0 = the old track plays out and the new one
    # follows, -1 = the house value rendered here.
    track_natural = (
        "    if d < 0.05 then\n"
        "      sequence([old_s, new.source])\n"
        "    elsif wait < 0.01 then\n"
        "      add(normalize=false, [fade.in(duration=t_in, new.source),\n"
        "                            fade.out(duration=t_out, delay=t_delay, old_s)])\n"
        "    else\n"
        "      add(normalize=false, [sequence([blank(duration=wait), fade.in(duration=t_in, new.source)]),\n"
        "                            fade.out(duration=t_out, delay=t_delay, old_s)])\n"
        "    end\n"
    )
    track_skip = (
        "    if d < 0.05 then\n"
        "      rt_instant(old_s, new.source)\n"
        "    else\n"
        "      add(normalize=false, [fade.in(duration=t_in, new.source),\n"
        "                            fade.out(duration=t_cut, max_duration(t_cut, old_s))])\n"
        "    end\n"
    )
    return (
        "# rt_cross: shape of the NEXT queue transition, set by PLAYOUT over telnet\n"
        "#   var.set rt_cross = track | show | track_skip | show_skip | instant\n"
        "# rt_nofade: which side is flagged 'No Fade during Crossover' (old | new | both | -)\n"
        "# rt_dur: overlap of the NEXT in-show transition in seconds (0 = none, -1 = house value)\n"
        'rt_cross = interactive.string("rt_cross", "track")\n'
        'rt_nofade = interactive.string("rt_nofade", "-")\n'
        'rt_dur = interactive.float("rt_dur", -1.0)\n'
        f"# track crossfade {f(track)} s, show crossfade {f(show)} s, tail buffer {f(buf)} s\n"
        "def rt_instant(old_s, new_s) =\n"
        "  add(normalize=false, [fade.in(duration=0.05, new_s), fade.out(duration=0.05, old_s)])\n"
        "end\n"
        "def rt_transition(old, new) =\n"
        "  mode = rt_cross()\n"
        "  nofade = rt_nofade()\n"
        '  old_nf = nofade == "old" or nofade == "both"\n'
        '  new_nf = nofade == "new" or nofade == "both"\n'
        "  rem = source.remaining(old.source)\n"
        "  # 2026-09-28: add() forwards the metadata of the FIRST source only, and\n"
        "  # cross replays the ending track's metadata on its buffered tail - with\n"
        "  # the tail in front the stream title and the Live Text lagged one track.\n"
        "  # The new track goes first in every add, the tail carries no metadata.\n"
        "  old_s = source.drop.metadata(old.source)\n"
        f"  buf = {f(buf)}\n"
        "  d0 = rt_dur()\n"
        f"  d1 = if d0 < 0. then {f(track)} else d0 end\n"
        "  d = if d1 > buf then buf else d1 end\n"
        "  wait = buf - d\n"
        "  fd = if d < 0.05 then 0.05 else d end\n"
        '  log(level=3, label="rt_cross", "#{mode}/#{nofade}/#{d}: #{old.metadata[\\"title\\"]} -> '
        '#{new.metadata[\\"title\\"]} (tail #{rem} s)")\n'
        "  t_in = if new_nf then 0.05 else fd end\n"
        f"  t_out = if old_nf then {nofade} else fd end\n"
        f"  s_out = if old_nf then {nofade} else {f(max(show, 0.05))} end\n"
        "  t_cut = if old_nf then 0.05 else fd end\n"
        f"  s_cut = if old_nf then 0.05 else {f(max(show, 0.05))} end\n"
        f"  t_delay = if old_nf then {never} else wait end\n"
        f"  s_delay = if old_nf then {never} else {f(max(0.0, buf - show))} end\n"
        "  ignore(t_in) ignore(t_out) ignore(s_out) ignore(t_cut) ignore(s_cut) ignore(t_delay) ignore(s_delay) ignore(wait)\n"
        # 2026-10-01: no `old.db_level < -50.` shortcut any more.  It skipped
        # the whole buffered tail of a track that ends quietly (BUFFER
        # seconds, not just the silence): the successor started up to 3 s
        # before its row and the rest of the show ran early - the 12:00
        # relay's intro lost 2.4 s.  With the R128 gain on the queue a
        # fade-out crosses -50 dB often; the rows own the timeline.
        '  if mode == "instant" or rem < 0.15 then\n'
        "    rt_instant(old_s, new.source)\n"
        '  elsif mode == "show_skip" then\n'
        + show_skip
        + '  elsif mode == "track_skip" then\n'
        + track_skip
        + '  elsif mode == "show" then\n'
        + show_natural
        + "  else\n"
        + track_natural
        + "  end\n"
        + "end\n"
        # RASTATIME 2026-09-29 - the per-track gain (ReplayGain / EBU R128,
        # annotate replaygain_track_gain) is applied HERE, on the queue, in
        # front of cross.  amplify(override=...) takes the value at a track
        # start; on the bus the transitions deliver metadata but no track
        # mark, so every track of a continuous run played with the gain of
        # the FIRST one (bench 2026-09-29: C annotated -4 dB played at A's
        # -10 dB).  On the queue every request starts a track, and the two
        # sides of a crossfade each carry their own gain.
        + "# per-track gain (ReplayGain / EBU R128) on the queue, before the crossfade\n"
        + 'scheduled_g = amplify(id="track_gain", override="replaygain_track_gain", 1., scheduled_q)\n'
        + f'scheduled_x = cross(id="scheduled_x", duration={f(buf)}, rt_transition, scheduled_g)\n'
    )


def _render_bus_source_block(
    *,
    main_enabled: bool,
    show_enabled: bool,
    webstream_enabled: bool = DEFAULT_WEBSTREAM_ENABLED,
    linein_enabled: bool = DEFAULT_LINEIN_ENABLED,
    transition_seconds: float = DEFAULT_CROSSFADE_DURATION,
    duck_fade_seconds: float = DEFAULT_INPUT_DUCK_FADE_SECONDS,
    dj_fade_seconds: float = DEFAULT_DJ_FADE_SECONDS,
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
    # (arm, transition) pairs -- transitions is index-aligned with the
    # arm list, so both are built together.  DJ arms hand over instantly;
    # the programme arms go through bus_transition (see the module
    # comment at DEFAULT_INPUT_DUCK_FADE_SECONDS).
    # RASTATIME 2026-09-28 - three shapes, all "new at once, old fades out
    # under it" and therefore the same source type (the 2.4.4 typer wants
    # a homogeneous transition list): bus_dj (Switch Transition Fade) for
    # a DJ taking over, bus_transition (Show Crossfade) for the programme
    # arms.  A programme arm that takes over FROM a DJ (hand-back) also
    # uses bus_dj - the wrapper looks at the outgoing source's id.
    dj_shape, faded = "bus_dj", "bus_transition"
    from_dj = 'source.id(old) == "master_dj" or source.id(old) == "show_dj"'
    has_dj = bool(main_enabled or show_enabled)  # no DJ arms: plain shapes, no DJ ids in the script
    transitions: List[str] = []
    # RASTATIME 2026-09-13 - every arm gets a thin wrapper around the
    # shared shape: live arms insert one metadata packet with the show on
    # air (show_name from bus_show) so the ICY title changes at once, the
    # scheduled arm marks the silence off-air when the queue is empty.
    # The packet is inserted on the transition's OWN source (the add of
    # the two fades): a replica probe showed that an insert on the arm
    # (an operator such as amplify) or on the source under it never
    # reaches the bus, while the transition source carries it at once.
    wrappers: List[str] = []

    def _arm(name: str, source: str, shape: str) -> str:
        pick = (
            f"  s = {shape}(old, new)\n" if shape == dj_shape or not has_dj
            else f"  s = if {from_dj} then bus_dj(old, new) else {shape}(old, new) end\n"
        )
        return (
            f"def {name}(old, new) =  # {source}\n"
            + pick
            + '  s.insert_metadata([("show_name", bus_show())])\n'
            "  s\n"
            "end\n"
        )

    if main_enabled:
        arms.append("({source.is_ready(master_dj)}, master_dj)")
        transitions.append("bus_arm_master")
        wrappers.append(_arm("bus_arm_master", "master_dj", dj_shape))
    if show_enabled:
        arms.append("({source.is_ready(show_dj)}, show_dj)")
        transitions.append("bus_arm_show")
        wrappers.append(_arm("bus_arm_show", "show_dj", dj_shape))
    if webstream_enabled:
        arms.append("({webstream_live() and source.is_ready(webstream)}, webstream)")
        transitions.append("bus_arm_webstream")
        wrappers.append(_arm("bus_arm_webstream", "webstream", faded))
    if linein_enabled:
        arms.append("({linein_live() and source.is_ready(linein)}, linein)")
        transitions.append("bus_arm_linein")
        wrappers.append(_arm("bus_arm_linein", "linein", faded))
    arms.append("({true}, scheduled)")
    transitions.append("bus_arm_scheduled")
    wrappers.append(
        "def bus_arm_scheduled(old, new) =\n"
        + (f"  s = if {from_dj} then bus_dj(old, new) else {faded}(old, new) end\n" if has_dj
           else f"  s = {faded}(old, new)\n")
        + "  # queue empty: the silence arm goes on air -> Off Air Metadata\n"
        "  if not source.is_ready(scheduled_q) then\n"
        '    s.insert_metadata([("off_air", "true"), ("title", offair_text())])\n'
        "  end\n"
        "  s\n"
        "end\n"
    )

    if (
        not main_enabled and not show_enabled
        and not webstream_enabled and not linein_enabled
    ):
        # No upstream switching candidate at all — keep the C3-era
        # simple assignment so the switch operator doesn't show up as a
        # noise line in `--check` output and so the bus chain is
        # identical for legacy single-source users.
        return "bus = scheduled\n"

    # RASTATIME 2026-09-27 - `transition_seconds` is the Default SHOW
    # Crossfade Duration.  One shape for every input switch: the incoming
    # source is at full level at once (50 ms click-free ramp, which also
    # keeps both add() elements the same source type), the outgoing one
    # fades out UNDER it over D seconds (0 -> a 50 ms cut).  The old
    # "crossfade when D > 0" branch (both fade over D) is gone: the
    # operator wants the new source audible immediately at a boundary.
    d = max(0.0, float(transition_seconds))
    fade_len = d if d >= 0.05 else 0.05
    dj = max(0.0, float(dj_fade_seconds))
    dj_len = dj if dj >= 0.05 else 0.05
    del duck_fade_seconds  # accepted for older callers, no longer shapes anything
    transition_fn = (
        "# input switch (Default Show Crossfade Duration): new source at\n"
        "# full level at once, old fades out UNDER it\n"
        "def bus_transition(old, new) =\n"
        f"  add(normalize=false, [fade.out(duration={_format_crossfade_duration(fade_len)}, old),\n"
        "                        fade.in(duration=0.05, new)])\n"
        "end\n"
        "# DJ hand-over / hand-back (Settings -> Streams, Switch Transition Fade):\n"
        "# the DJ is on air at once and the programme fades out under it; when the\n"
        "# DJ leaves, the DJ fades out and the programme is at full level at once\n"
        "def bus_dj(old, new) =\n"
        f"  add(normalize=false, [fade.out(duration={_format_crossfade_duration(dj_len)}, old),\n"
        "                        fade.in(duration=0.05, new)])\n"
        "end\n"
    )
    shape = (
        f"new at once, old fades out over {_format_crossfade_duration(fade_len)} s; "
        f"DJ hand-over {_format_crossfade_duration(dj_len)} s"
    )
    return (
        "# RASTATIME 2026-09-04 - gates: Pypo pre-connects a source with its\n"
        "# gate closed (no early on-air) and flips it at the slot start /\n"
        "# end.  Default true = plain is_ready behaviour.  Telnet:\n"
        "#   var.set webstream_live = false   /   var.set linein_live = true\n"
        'webstream_live = interactive.bool("webstream_live", true)\n'
        'linein_live = interactive.bool("linein_live", true)\n'
        "\n"
        f"# input transitions: {shape}\n"
        "# DJ arms: an effectively instant hand-over (50 ms).  It has to be\n"
        "# the SAME shape as bus_transition (add of two fades): a transition\n"
        "# list must be homogeneous, and a raw `new` picks up the fade methods\n"
        "# through the list -- 2.4.4 rejected the mixed list at load (live\n"
        "# outage 2026-09-04 19:26; DJ arms were never in the verify render).\n"
        "def bus_instant(old, new) =\n"
        "  add(normalize=false, [fade.out(duration=0.05, old), fade.in(duration=0.05, new)])\n"
        "end\n"
        + transition_fn
        + "\n"
        + "".join(wrappers)
        + "\n"
        "bus = switch(\n"
        "  track_sensitive=false,\n"
        f"  transition_length={_format_crossfade_duration(max(fade_len, dj_len) + 0.5)},\n"
        "  transitions=[\n"
        + "".join(f"    {t},\n" for t in transitions)
        + "  ],\n"
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
    show_crossfade_duration: float = DEFAULT_SHOW_CROSSFADE_DURATION,
    dj_fade_seconds: float = DEFAULT_DJ_FADE_SECONDS,
    crossfade_fade_seconds: float = DEFAULT_CROSSFADE_FADE_SECONDS,  # ignored since 2026-09-27
    local_output_enabled: bool = DEFAULT_LOCAL_OUTPUT_ENABLED,
    local_output_device_id: Optional[int] = None,
    local_output_device_label: str = "",
    local_output_endpoint_id: str = "",
    local_output_device_name: Optional[str] = None,
    local_output_adaptive: bool = DEFAULT_LOCAL_OUTPUT_ADAPTIVE,
    harbor_main_password: Optional[str] = None,
    harbor_show_password: Optional[str] = None,
    harbor_main_port: int = DEFAULT_HARBOR_MAIN_PORT,
    harbor_show_port: int = DEFAULT_HARBOR_SHOW_PORT,
    harbor_main_mount: str = DEFAULT_HARBOR_MAIN_MOUNT,
    harbor_show_mount: str = DEFAULT_HARBOR_SHOW_MOUNT,
    harbor_buffer_seconds: float = DEFAULT_HARBOR_BUFFER_SECONDS,
    source_event_url: Optional[str] = DEFAULT_SOURCE_EVENT_URL,
    harbor_timeout_seconds: float = DEFAULT_HARBOR_TIMEOUT_SECONDS,
    dj_auth_url: Optional[str] = DEFAULT_DJ_AUTH_URL,
    webstream_enabled: bool = DEFAULT_WEBSTREAM_ENABLED,
    webstream_max_buffer_seconds: float = DEFAULT_WEBSTREAM_MAX_BUFFER_SECONDS,
    webstream_timeout_seconds: float = DEFAULT_WEBSTREAM_TIMEOUT_SECONDS,
    webstream_poll_delay_seconds: float = DEFAULT_WEBSTREAM_POLL_DELAY_SECONDS,
    linein_enabled: bool = DEFAULT_LINEIN_ENABLED,
    linein_max_buffer_seconds: float = DEFAULT_LINEIN_MAX_BUFFER_SECONDS,
    linein_http_max_buffer_seconds: float = DEFAULT_LINEIN_HTTP_MAX_BUFFER_SECONDS,
    linein_http_poll_delay_seconds: float = DEFAULT_LINEIN_HTTP_POLL_DELAY_SECONDS,
    hourly_recording_enabled: bool = False,
    hourly_recording_folder: str = "",
    hourly_recording_format: str = DEFAULT_HOURLY_RECORDING_FORMAT,
    hourly_recording_bitrate: int = DEFAULT_HOURLY_RECORDING_BITRATE,
    hourly_recording_samplerate: int = DEFAULT_SAMPLERATE,
    show_recording_format: str = DEFAULT_SHOW_RECORDING_FORMAT,
    show_recording_bitrate: int = DEFAULT_SHOW_RECORDING_BITRATE,
    show_recording_samplerate: int = DEFAULT_SAMPLERATE,
    icy_label_format: int = DEFAULT_ICY_FORMAT,
    icy_offair_text: str = DEFAULT_OFFAIR_TEXT,
    icy_station_name: str = DEFAULT_STATION_NAME,
    live_text_url: Optional[str] = DEFAULT_LIVE_TEXT_URL,
    loudness_limiter_ceiling: Optional[float] = None,
    stereotool: Optional[StereoToolSettings] = None,
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

    icecast_blocks = _render_icecast_outputs(
        stream_outputs, station_name=icy_station_name,
    )
    icy_block = _render_icy_metadata_block(
        icy_label_format, icy_offair_text, icy_station_name,
        live_text_url=live_text_url,
    )

    harbor_block = _render_harbor_inputs_block(
        main_password=harbor_main_password,
        show_password=harbor_show_password,
        main_port=harbor_main_port,
        show_port=harbor_show_port,
        main_mount=harbor_main_mount,
        show_mount=harbor_show_mount,
        buffer_seconds=harbor_buffer_seconds,
        source_event_url=source_event_url,
        timeout_seconds=harbor_timeout_seconds,
        dj_auth_url=dj_auth_url,
    )
    webstream_block = _render_webstream_input_block(
        enabled=webstream_enabled,
        max_buffer_seconds=webstream_max_buffer_seconds,
        timeout_seconds=webstream_timeout_seconds,
        poll_delay_seconds=webstream_poll_delay_seconds,
    )
    webstream_watchdog_block = _render_webstream_watchdog_block(
        webstream_enabled=webstream_enabled,
    )
    linein_block = _render_linein_input_block(
        enabled=linein_enabled,
        max_buffer_seconds=linein_max_buffer_seconds,
        http_max_buffer_seconds=linein_http_max_buffer_seconds,
        http_poll_delay_seconds=linein_http_poll_delay_seconds,
    )
    bus_block = _render_bus_source_block(
        main_enabled=bool(harbor_main_password),
        show_enabled=bool(harbor_show_password),
        webstream_enabled=webstream_enabled,
        linein_enabled=linein_enabled,
        # RASTATIME 2026-09-27 - input switches follow the SHOW crossfade
        transition_seconds=show_crossfade_duration,
        # RASTATIME 2026-09-28 - DJ hand-over follows Settings -> Streams
        dj_fade_seconds=dj_fade_seconds,
    )
    hourly_block = _render_hourly_recording_block(
        enabled=hourly_recording_enabled,
        folder=hourly_recording_folder,
        fmt=hourly_recording_format,
        bitrate=hourly_recording_bitrate,
        samplerate=hourly_recording_samplerate,
    )
    show_encoder = _render_show_recording_encoder(
        fmt=show_recording_format,
        bitrate=show_recording_bitrate,
        samplerate=show_recording_samplerate,
    )

    rendered = (
        template
        .replace("${TELNET_HOST}", _escape_liq_string(telnet_host))
        .replace("${TELNET_PORT}", str(int(telnet_port)))
        .replace("${LOG_FILE}", _escape_liq_string(log_file))
        .replace(
            "${CROSSFADE_BLOCK}",
            _render_crossfade_block(crossfade_duration, show_crossfade_duration),
        )
        .replace(
            "${LOCAL_OUTPUT_BLOCK}",
            _render_local_output_block(
                local_output_enabled,
                local_output_device_id,
                local_output_device_label,
                local_output_endpoint_id,
                local_output_device_name,
                adaptive=local_output_adaptive,
            ),
        )
        .replace("${HARBOR_INPUTS_BLOCK}", harbor_block)
        .replace("${WEBSTREAM_INPUT_BLOCK}", webstream_block)
        .replace("${LINEIN_INPUT_BLOCK}", linein_block)
        .replace("${BUS_SOURCE_BLOCK}", bus_block)
        .replace("${WEBSTREAM_WATCHDOG_BLOCK}", webstream_watchdog_block)
        .replace("${ICY_METADATA_BLOCK}", icy_block)
        .replace("${LOUDNESS_BLOCK}", _render_loudness_block(loudness_limiter_ceiling))
        .replace("${STEREOTOOL_BLOCK}", _render_stereotool_block(stereotool)[0])
        .replace("${ICECAST_OUTPUTS}", icecast_blocks)
        .replace("${HOURLY_RECORDING_BLOCK}", hourly_block)
        .replace("${SHOW_RECORDING_ENCODER}", show_encoder)
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
    show_crossfade_duration: float = DEFAULT_SHOW_CROSSFADE_DURATION,
    dj_fade_seconds: float = DEFAULT_DJ_FADE_SECONDS,
    crossfade_fade_seconds: float = DEFAULT_CROSSFADE_FADE_SECONDS,  # ignored since 2026-09-27
    local_output_enabled: bool = DEFAULT_LOCAL_OUTPUT_ENABLED,
    local_output_device_id: Optional[int] = None,
    local_output_device_label: str = "",
    local_output_endpoint_id: str = "",
    local_output_device_name: Optional[str] = None,
    local_output_adaptive: bool = DEFAULT_LOCAL_OUTPUT_ADAPTIVE,
    harbor_main_password: Optional[str] = None,
    harbor_show_password: Optional[str] = None,
    harbor_main_port: int = DEFAULT_HARBOR_MAIN_PORT,
    harbor_show_port: int = DEFAULT_HARBOR_SHOW_PORT,
    harbor_main_mount: str = DEFAULT_HARBOR_MAIN_MOUNT,
    harbor_show_mount: str = DEFAULT_HARBOR_SHOW_MOUNT,
    harbor_buffer_seconds: float = DEFAULT_HARBOR_BUFFER_SECONDS,
    source_event_url: Optional[str] = DEFAULT_SOURCE_EVENT_URL,
    harbor_timeout_seconds: float = DEFAULT_HARBOR_TIMEOUT_SECONDS,
    dj_auth_url: Optional[str] = DEFAULT_DJ_AUTH_URL,
    webstream_enabled: bool = DEFAULT_WEBSTREAM_ENABLED,
    webstream_max_buffer_seconds: float = DEFAULT_WEBSTREAM_MAX_BUFFER_SECONDS,
    webstream_timeout_seconds: float = DEFAULT_WEBSTREAM_TIMEOUT_SECONDS,
    webstream_poll_delay_seconds: float = DEFAULT_WEBSTREAM_POLL_DELAY_SECONDS,
    linein_enabled: bool = DEFAULT_LINEIN_ENABLED,
    linein_max_buffer_seconds: float = DEFAULT_LINEIN_MAX_BUFFER_SECONDS,
    linein_http_max_buffer_seconds: float = DEFAULT_LINEIN_HTTP_MAX_BUFFER_SECONDS,
    linein_http_poll_delay_seconds: float = DEFAULT_LINEIN_HTTP_POLL_DELAY_SECONDS,
    hourly_recording_enabled: bool = False,
    hourly_recording_folder: str = "",
    hourly_recording_format: str = DEFAULT_HOURLY_RECORDING_FORMAT,
    hourly_recording_bitrate: int = DEFAULT_HOURLY_RECORDING_BITRATE,
    hourly_recording_samplerate: int = DEFAULT_SAMPLERATE,
    show_recording_format: str = DEFAULT_SHOW_RECORDING_FORMAT,
    show_recording_bitrate: int = DEFAULT_SHOW_RECORDING_BITRATE,
    show_recording_samplerate: int = DEFAULT_SAMPLERATE,
    icy_label_format: int = DEFAULT_ICY_FORMAT,
    icy_offair_text: str = DEFAULT_OFFAIR_TEXT,
    icy_station_name: str = DEFAULT_STATION_NAME,
    live_text_url: Optional[str] = DEFAULT_LIVE_TEXT_URL,
    loudness_limiter_ceiling: Optional[float] = None,
    stereotool: Optional[StereoToolSettings] = None,
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
        show_crossfade_duration=show_crossfade_duration,
        dj_fade_seconds=dj_fade_seconds,
        crossfade_fade_seconds=crossfade_fade_seconds,
        local_output_enabled=local_output_enabled,
        local_output_device_id=local_output_device_id,
        local_output_device_label=local_output_device_label,
        local_output_endpoint_id=local_output_endpoint_id,
        local_output_device_name=local_output_device_name,
        local_output_adaptive=local_output_adaptive,
        harbor_main_password=harbor_main_password,
        harbor_show_password=harbor_show_password,
        harbor_main_port=harbor_main_port,
        harbor_show_port=harbor_show_port,
        harbor_main_mount=harbor_main_mount,
        harbor_show_mount=harbor_show_mount,
        harbor_buffer_seconds=harbor_buffer_seconds,
        source_event_url=source_event_url,
        harbor_timeout_seconds=harbor_timeout_seconds,
        dj_auth_url=dj_auth_url,
        webstream_enabled=webstream_enabled,
        webstream_max_buffer_seconds=webstream_max_buffer_seconds,
        webstream_timeout_seconds=webstream_timeout_seconds,
        webstream_poll_delay_seconds=webstream_poll_delay_seconds,
        linein_enabled=linein_enabled,
        linein_max_buffer_seconds=linein_max_buffer_seconds,
        linein_http_max_buffer_seconds=linein_http_max_buffer_seconds,
        linein_http_poll_delay_seconds=linein_http_poll_delay_seconds,
        hourly_recording_enabled=hourly_recording_enabled,
        hourly_recording_folder=hourly_recording_folder,
        hourly_recording_format=hourly_recording_format,
        hourly_recording_bitrate=hourly_recording_bitrate,
        hourly_recording_samplerate=hourly_recording_samplerate,
        show_recording_format=show_recording_format,
        show_recording_bitrate=show_recording_bitrate,
        show_recording_samplerate=show_recording_samplerate,
        icy_label_format=icy_label_format,
        icy_offair_text=icy_offair_text,
        icy_station_name=icy_station_name,
        live_text_url=live_text_url,
        loudness_limiter_ceiling=loudness_limiter_ceiling,
        stereotool=stereotool,
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
# RASTATIME 2026-09-09 - standby source for the Icecast fallback mounts
# ---------------------------------------------------------------------

DEFAULT_STANDBY_MOUNT_SUFFIX = "-standby"
DEFAULT_STANDBY_LOG_FILE = "C:/rastatime/logs/liquidsoap-standby.log"


def standby_mount(mount: str, suffix: str = DEFAULT_STANDBY_MOUNT_SUFFIX) -> str:
    """``/rastatime`` -> ``/rastatime-standby`` (the Icecast fallback mount)."""
    mount = mount if mount.startswith("/") else "/" + mount
    return mount + suffix


def render_standby_liq(
    stream_outputs: List[Dict],
    *,
    audio_file: Optional[str] = None,
    log_file: str = DEFAULT_STANDBY_LOG_FILE,
    mount_suffix: str = DEFAULT_STANDBY_MOUNT_SUFFIX,
) -> str:
    """
    Render ``standby.liq``: a second, tiny Liquidsoap that streams silence
    (or ``audio_file`` in a loop) to one fallback mount per configured
    stream output, with the SAME encoders as the main render.

    Why (RASTATIME 2026-09-09): the planned restart of RASTATIME-LIQUIDSOAP
    drops its Icecast sources for 1-2 s.  Without a fallback Icecast
    disconnects every listener of those mounts.  With
    ``<fallback-mount>/rastatime-standby</fallback-mount>`` and
    ``<fallback-override>1</fallback-override>`` in icecast.xml, Icecast
    moves the listeners to the standby mount and back once the main
    source returns - nobody is disconnected, they hear the standby
    content for a moment.  The standby process has no telnet server and
    nothing that polls, so it does not grow (the Windows ``Unix.select``
    leak needs scheduler wake-ups) and is never restarted on purpose.

    The encoders must match the main outputs (same codec / rate /
    bitrate) or listener players choke on the switch - hence the same
    ``_render_icecast_outputs`` with the mounts retargeted.
    """
    standby_outputs = []
    for out in stream_outputs:
        out = dict(out)
        out["mount"] = standby_mount(str(out.get("mount", "")), mount_suffix)
        name = str(out.get("name") or "").strip()
        out["name"] = (name + " (standby)") if name else "standby"
        standby_outputs.append(out)
    if audio_file:
        source = (
            "# a station bed / loop; mksafe falls back to silence if the file is unreadable\n"
            f'bus = mksafe(single(id="standby_loop", "{_escape_liq_string(audio_file)}"))\n'
        )
    else:
        source = 'bus = blank(id="standby_silence")\n'
    return (
        "# =====================================================================\n"
        "# standby.liq - RASTATIME standby source (rendered, do not edit)\n"
        "#\n"
        "# Streams silence (or a configured loop) to the Icecast fallback mounts\n"
        "# so listeners are not disconnected while RASTATIME-LIQUIDSOAP restarts.\n"
        "# Rendered by rastatime_playout.liquidsoap_config.render_standby_liq from\n"
        "# the same stream outputs as rastatime.liq.  Runs as RASTATIME-STANDBY.\n"
        "# =====================================================================\n"
        "settings.init.allow_root.set(true)\n"
        "settings.log.level.set(3)\n"
        "settings.log.stdout.set(false)\n"
        "settings.log.file.set(true)\n"
        f'settings.log.file.path.set("{_escape_liq_string(log_file)}")\n'
        "settings.server.telnet.set(false)\n"
        "\n"
        + source
        + "\n"
        # no ICY block in the standby script -> Liquidsoap's default title
        + _render_icecast_outputs(standby_outputs, icy_song=None)
    )


def write_standby_liq(
    output_path: Path,
    stream_outputs: List[Dict],
    *,
    audio_file: Optional[str] = None,
    log_file: str = DEFAULT_STANDBY_LOG_FILE,
) -> bool:
    """Atomically write ``standby.liq``; True when the content changed."""
    rendered = render_standby_liq(stream_outputs, audio_file=audio_file, log_file=log_file)
    previous: Optional[str] = None
    if output_path.exists():
        try:
            previous = output_path.read_text(encoding="utf-8")
        except OSError:
            previous = None
    if previous == rendered:
        return False
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    tmp_path.write_text(rendered, encoding="utf-8", newline="\n")
    os.replace(tmp_path, output_path)
    return True


def icecast_mounts_without_fallback(
    icecast_xml: Path,
    stream_outputs: List[Dict],
    *,
    mount_suffix: str = DEFAULT_STANDBY_MOUNT_SUFFIX,
) -> Optional[List[str]]:
    """
    Which configured public mounts have NO ``<fallback-mount>`` to their
    standby mount in ``icecast.xml``?

    The standby side follows the stream outputs automatically (PLAYOUT
    re-renders standby.liq), but Icecast's fallback blocks are static
    config: a renamed or added stream output needs a matching
    ``<mount type="normal">`` block and an Icecast restart, otherwise its
    listeners are disconnected by the next planned restart.  Returns the
    list of uncovered mounts, ``[]`` when all are covered, ``None`` when
    the file cannot be read or parsed (the caller logs that).
    """
    import xml.etree.ElementTree as ET  # noqa: PLC0415

    try:
        root = ET.parse(icecast_xml).getroot()
    except (OSError, ET.ParseError):
        return None
    covered = {}
    for mount in root.iter("mount"):
        name = (mount.findtext("mount-name") or "").strip()
        fallback = (mount.findtext("fallback-mount") or "").strip()
        if name and fallback:
            covered[name] = fallback
    missing: List[str] = []
    for out in stream_outputs:
        mount = str(out.get("mount", "")).strip()
        if not mount:
            continue
        mount = mount if mount.startswith("/") else "/" + mount
        if covered.get(mount) != standby_mount(mount, mount_suffix):
            missing.append(mount)
    return missing


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
        from rastatime_api.core.models import Preference  # type: ignore[import-untyped]

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


def read_hourly_recording_config_from_db() -> Dict:
    """
    Load the 24/7 hourly recording settings from cc_pref.  Returns a dict
    with safe defaults (recorder disabled) when the ORM is unavailable or
    the keys are unset, so a missing config never raises.

    cc_pref keys (written by Settings -> Local Machine, frontend
    Application_Model_Preference::*Local247Recording*):

      local_247_recording_enabled         "true" / "false"
      local_247_recording_folder          absolute path ("" = unset)
      local_247_recording_format          mp3 / aac / ogg / opus
      local_247_recording_bitrate         int kbps
      local_247_recording_retention_days  int (used by the cleanup task,
                                           NOT by the .liq render)

    Shared by Pypo's startup render (rastatime_playout.__main__) and the
    manual ``render`` CLI below so both produce an identical .liq.
    """
    disabled = {
        "enabled": False,
        "folder": "",
        "format": DEFAULT_HOURLY_RECORDING_FORMAT,
        "bitrate": DEFAULT_HOURLY_RECORDING_BITRATE,
        "retention_days": 0,
    }
    try:
        from rastatime_api.core.models import Preference  # type: ignore[import-untyped]

        entries: Dict[str, str] = dict(
            Preference.site.values_list("key", "value")
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("Could not read 24/7 recording config from DB: %s", exc)
        return disabled

    enabled = (
        str(entries.get("local_247_recording_enabled", "")).strip().lower()
        == "true"
    )
    folder = (entries.get("local_247_recording_folder") or "").strip()
    fmt = (
        entries.get("local_247_recording_format")
        or DEFAULT_HOURLY_RECORDING_FORMAT
    ).strip().lower()
    try:
        bitrate = int(
            entries.get("local_247_recording_bitrate")
            or DEFAULT_HOURLY_RECORDING_BITRATE
        )
    except (TypeError, ValueError):
        bitrate = DEFAULT_HOURLY_RECORDING_BITRATE
    try:
        retention_days = int(
            entries.get("local_247_recording_retention_days") or 0
        )
    except (TypeError, ValueError):
        retention_days = 0

    return {
        "enabled": enabled,
        "folder": folder,
        "format": fmt,
        "bitrate": bitrate,
        "retention_days": retention_days,
    }


def read_show_recording_config_from_db() -> Dict[str, object]:
    """
    RASTATIME 2026-10-18 - per-show recording encoder from cc_pref
    (``local_recording_format`` mp3/aac/ogg/opus, ``local_recording_bitrate``
    kbps; Settings -> Local Machine -> Show Recording).  Defaults MP3 320k
    when unset or unreadable.  Part of the settings fingerprint, so a change
    re-renders and restarts LIQUIDSOAP in the next quiet moment.
    """
    defaults = {
        "format": DEFAULT_SHOW_RECORDING_FORMAT,
        "bitrate": DEFAULT_SHOW_RECORDING_BITRATE,
    }
    try:
        from rastatime_api.core.models import Preference  # type: ignore[import-untyped]

        entries: Dict[str, str] = dict(
            Preference.site.filter(
                key__in=["local_recording_format", "local_recording_bitrate"]
            ).values_list("key", "value")
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("Could not read the show recording config from DB: %s", exc)
        return defaults
    fmt = (entries.get("local_recording_format") or "").strip().lower()
    if fmt not in _ENCODER_FOR_TYPE:
        fmt = DEFAULT_SHOW_RECORDING_FORMAT
    try:
        bitrate = int(entries.get("local_recording_bitrate") or 0)
    except (TypeError, ValueError):
        bitrate = 0
    if bitrate <= 0:
        bitrate = DEFAULT_SHOW_RECORDING_BITRATE
    return {"format": fmt, "bitrate": bitrate}


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
            "DJANGO_SETTINGS_MODULE", "rastatime_api.settings"
        )
        django.setup()
        return True
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("Django ORM bootstrap failed: %s", exc)
        return False


def main(argv: Optional[List[str]] = None) -> int:
    """
    CLI entry-point.  Usage::

        python -m rastatime_playout.liquidsoap_config render \\
            --out C:/Tools/liquidsoap/rastatime.liq \\
            [--telnet-host 127.0.0.1] [--telnet-port 1234] \\
            [--log-file C:/rastatime/logs/liquidsoap.log]

    Reads stream outputs from cc_pref (via the Django ORM) and writes
    the rendered .liq file.  Exits 0 on success (with stdout message
    saying whether the file changed), non-zero on error.
    """
    parser = argparse.ArgumentParser(
        prog="python -m rastatime_playout.liquidsoap_config",
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
    render.add_argument(
        "--no-local-output-adaptive", dest="local_output_adaptive",
        action="store_false", default=DEFAULT_LOCAL_OUTPUT_ADAPTIVE,
        help="Plain buffer() instead of buffer.adaptative for the soundcard bridge.",
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
        hourly = read_hourly_recording_config_from_db()
        changed = write_rastatime_liq(
            args.out,
            stream_outputs,
            telnet_host=args.telnet_host,
            telnet_port=args.telnet_port,
            log_file=args.log_file,
            crossfade_duration=args.crossfade_duration,
            local_output_enabled=args.local_output_enabled,
            local_output_adaptive=args.local_output_adaptive,
            hourly_recording_enabled=hourly["enabled"],
            hourly_recording_folder=hourly["folder"],
            hourly_recording_format=hourly["format"],
            hourly_recording_bitrate=hourly["bitrate"],
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
