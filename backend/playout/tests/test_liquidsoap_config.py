"""
RASTATIME 2026-05-26 — Unit tests for liquidsoap_config render
(Seamless-Bus-Mix Phase C3).

Strategy
--------

The renderer is a pure-Python function on top of a template file.
Tests use the real bundled template (so we catch any breakage if
the template gets edited without thinking about the placeholders),
plus a couple of micro-templates inside the test for edge cases.

No Liquidsoap process is started — we only verify the rendered
text shape.  Phase C8 integration test will actually run
Liquidsoap against a rendered .liq.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from libretime_playout import liquidsoap_config as lc


# ---- Helpers ------------------------------------------------------------


def _stream(
    type_="mp3", host="localhost", port=8000, mount="rastatime",
    password="hackme", user="source", bitrate=128, samplerate=None,
    name="RASTATIME", description="Live stream",
):
    """Build a stream_output_N-shaped dict for tests."""
    out = {
        "type": type_, "host": host, "port": port, "mount": mount,
        "pass": password, "user": user, "bitrate": bitrate,
        "name": name, "description": description,
    }
    if samplerate is not None:
        out["samplerate"] = samplerate
    return out


# ---- _escape_liq_string -------------------------------------------------


def test_escape_simple_string_passes_through():
    assert lc._escape_liq_string("hello") == "hello"


def test_escape_doublequote():
    assert lc._escape_liq_string('he said "hi"') == 'he said \\"hi\\"'


def test_escape_backslash():
    assert lc._escape_liq_string(r"C:\foo\bar") == r"C:\\foo\\bar"


def test_escape_both():
    assert (
        lc._escape_liq_string(r'C:\path\with "quotes"')
        == r'C:\\path\\with \"quotes\"'
    )


# ---- _render_icecast_block ----------------------------------------------


def test_render_mp3_block_basic_shape():
    out = lc._render_icecast_block(_stream())
    # Encoder
    assert 'codec="libmp3lame"' in out
    assert 'b="128k"' in out
    # Samplerate default 44100 (matches Liquidsoap internal frame rate)
    assert "samplerate=44100" in out
    # Connection — "localhost" is normalized to 127.0.0.1 at render time
    # (Windows resolves localhost AAAA-first while Icecast listens
    # IPv4-only; the failed ::1 connect froze the clock on every ICY
    # metadata update — see _normalize_loopback_host).
    assert 'host="127.0.0.1"' in out
    assert "port=8000" in out
    assert 'user="source"' in out
    assert 'password="hackme"' in out
    assert 'mount="/rastatime"' in out
    # Phase-C3 operator-decision: indefinite retry on Icecast outage.
    # fallible=true allows Liquidsoap to keep the output alive across
    # disconnects and retry on its default back-off schedule.  (The
    # 2.4.x on_error callback for explicit retry-delay control has a
    # non-trivial record-typed signature that we leave unset for now.)
    assert "fallible=true" in out
    # The source name we wire up in the template:
    assert "  bus,\n" in out


def test_render_aac_block_uses_aac_codec():
    out = lc._render_icecast_block(_stream(type_="aac"))
    assert 'codec="aac"' in out
    assert 'format="adts"' in out


def test_render_ogg_block_uses_vorbis_codec():
    out = lc._render_icecast_block(_stream(type_="ogg"))
    assert 'codec="libvorbis"' in out
    assert 'format="ogg"' in out


def test_render_opus_block_uses_opus_codec_in_ogg():
    """Opus is libopus codec in an ogg container (matches FfmpegStreamer)."""
    out = lc._render_icecast_block(_stream(type_="opus"))
    assert 'codec="libopus"' in out
    assert 'format="ogg"' in out
    # Opus REJECTS 44100 — default cc_pref sample-rate becomes 48000
    # via the opus clamp.
    assert "samplerate=48000" in out
    assert "samplerate=44100" not in out


def test_render_opus_clamps_invalid_samplerate():
    """Opus with 22050 (FFmpeg-valid, libopus-invalid) → clamp to 48000."""
    out = lc._render_icecast_block(_stream(type_="opus", samplerate=22050))
    assert "samplerate=48000" in out
    assert "samplerate=22050" not in out


def test_render_opus_accepts_valid_samplerate():
    """Opus with 24000 (libopus-valid) → kept."""
    out = lc._render_icecast_block(_stream(type_="opus", samplerate=24000))
    assert "samplerate=24000" in out


def test_render_mp3_custom_samplerate_kept():
    """Non-opus codecs: caller-set samplerate is rendered verbatim."""
    out = lc._render_icecast_block(_stream(type_="mp3", samplerate=48000))
    assert "samplerate=48000" in out
    assert "samplerate=44100" not in out


def test_render_unknown_type_raises():
    with pytest.raises(ValueError) as exc:
        lc._render_icecast_block(_stream(type_="flac"))
    assert "flac" in str(exc.value)


def test_render_bitrate_substituted():
    out = lc._render_icecast_block(_stream(bitrate=192))
    assert 'b="192k"' in out
    assert 'b="128k"' not in out


def test_render_mount_leading_slash_normalised():
    """User pastes 'rastatime' OR '/rastatime' — both render to /rastatime."""
    a = lc._render_icecast_block(_stream(mount="rastatime"))
    b = lc._render_icecast_block(_stream(mount="/rastatime"))
    assert 'mount="/rastatime"' in a
    assert 'mount="/rastatime"' in b


def test_render_password_with_quotes_escaped():
    out = lc._render_icecast_block(
        _stream(password='secret"with"quotes')
    )
    assert 'password="secret\\"with\\"quotes"' in out


def test_render_name_with_backslash_escaped():
    out = lc._render_icecast_block(
        _stream(name=r"RASTATIME\Production")
    )
    assert r'name="RASTATIME\\Production"' in out


# ---- _render_icecast_outputs --------------------------------------------


def test_render_outputs_empty_list_comment_only():
    out = lc._render_icecast_outputs([])
    assert "no stream outputs configured" in out
    assert "output.icecast" not in out


def test_render_outputs_three_blocks_separated_by_blank_lines():
    blocks = lc._render_icecast_outputs([
        _stream(type_="mp3", mount="mp3-mount"),
        _stream(type_="aac", mount="aac-mount"),
        _stream(type_="ogg", mount="ogg-mount"),
    ])
    assert blocks.count("output.icecast(") == 3
    assert 'mount="/mp3-mount"' in blocks
    assert 'mount="/aac-mount"' in blocks
    assert 'mount="/ogg-mount"' in blocks


# ---- render_rastatime_liq (full template) -------------------------------


def test_full_render_defaults():
    """Render with default telnet/log settings — all placeholders consumed."""
    out = lc.render_rastatime_liq([_stream()])
    # Placeholders all substituted
    assert "${TELNET_HOST}" not in out
    assert "${TELNET_PORT}" not in out
    assert "${LOG_FILE}" not in out
    assert "${ICECAST_OUTPUTS}" not in out
    assert "${CROSSFADE_DURATION}" not in out
    assert "${LOCAL_OUTPUT_BLOCK}" not in out
    # Defaults applied
    assert '"127.0.0.1"' in out
    assert "telnet.port.set(1234)" in out
    assert '"C:/rastatime/logs/liquidsoap.log"' in out
    # Stream output rendered
    assert "output.icecast(" in out
    # Telnet server enabled — critical for the Python engine
    assert "settings.server.telnet.set(true)" in out
    # Silence fallback — critical for Icecast PUT persistence
    assert "fallback(" in out
    assert "blank(" in out
    # Phase-E 2026-05-29: crossfade moved to wrap scheduled ONLY, NOT
    # the whole bus.  Wrapping the bus crashes Liquidsoap with Error 7
    # when the switch contains self-syncing sources (input.harbor +
    # input.http together).  Crossfade still applies between
    # request.queue tracks (the only place track-level fades make
    # semantic sense); DJ + Webstream are continuous live audio and
    # don't need crossfading.
    assert "scheduled = crossfade(" in out
    assert "duration=2.0" in out
    assert "fade_in=0.0" in out
    assert "fade_out=0.0" in out
    # Replay-gain still applies to the whole bus (post-switch).
    assert 'amplify(override="replaygain_track_gain", 1., bus)' in out
    # Regression guard: no `bus = crossfade(` anywhere in the active
    # script — that was the broken Phase-D-era pattern.
    active = "\n".join(_active_lines(out))
    assert "bus = crossfade(" not in active
    # Default: local soundcard output is enabled via portaudio
    assert "output.portaudio(" in out


def test_full_render_local_output_disabled():
    """RASTATIME_LIQUIDSOAP_LOCAL_OUTPUT=false → no output.portaudio block."""
    out = lc.render_rastatime_liq([_stream()], local_output_enabled=False)
    # Marker comment shows the operator deliberately turned it off.
    assert "local output disabled" in out
    # And no active output.portaudio() call (template docs mention the
    # operator name in comments — only uncommented lines matter).
    for line in out.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        assert "output.portaudio(" not in stripped, (
            f"Unexpected active output.portaudio line: {line!r}"
        )


def test_full_render_local_output_enabled_explicitly():
    """
    Explicit local_output_enabled=True renders output.portaudio with the
    full bus-split: ``bus_for_portaudio = buffer(buffer=0.5, bus)`` as
    an asynchronous clock-crossing bridge, then ``output.portaudio``
    wrapped in ``clock.assign_new(id="portaudio_clock", …)``.

    Background: the C4-attempt ``clock.assign_new`` alone only
    RENAMED the main clock — all sources still shared one worker
    clock because they all referenced the same ``bus``.  The C5
    reality-test (2026-05-28) caught a PortAudio underflow that
    crashed the WHOLE Liquidsoap process mid-recording:

        [clock:2] Source output.portaudio failed while streaming:
            Failure("Portaudio error in write_stream: Output underflowed")!
        [main:3] Shutdown started!

    Real fix: ``buffer()`` between bus and portaudio is the
    canonical Liquidsoap clock-crossing bridge.  Local-soundcard
    underflow gets absorbed by the 500 ms async queue instead of
    crashing the subprocess.

    Note: Liquidsoap 2.4 dropped the ``clock_safe=true`` shortcut,
    so we use the standard clock.assign_new wrapper instead.
    """
    out = lc.render_rastatime_liq([_stream()], local_output_enabled=True)
    assert "output.portaudio(" in out
    assert 'clock.assign_new(id="portaudio_clock"' in out
    assert "fallible=true" in out
    # v2 bus-split (Phase-C5 follow-up 2026-05-28): buffer() with 2.0 s
    # absorption + clock.assign_new on the BUFFER itself (not just the
    # output).  RASTATIME 2026-09-05: sync="auto" — output.portaudio is
    # self-synced (blocking writes), sync="cpu" fought it and logged
    # "Latency is too high" every second whenever the output really
    # played; the buffer() bridge absorbs the drift to the main clock.
    assert "bus_for_portaudio = buffer(buffer=2.0, bus)" in out
    # The clock assign must reference bus_for_portaudio (the bridge):
    assert 'clock.assign_new(id="portaudio_clock", sync="auto", [' in out
    assert 'sync="cpu", [' not in out
    # bus_for_portaudio must appear in the clock-assign list AND as the
    # output.portaudio source argument.
    bus_pa_count = out.count("bus_for_portaudio")
    assert bus_pa_count >= 3, (
        f"Expected bus_for_portaudio to appear in: (1) the buffer assignment, "
        f"(2) the clock.assign_new list, (3) the output.portaudio source arg "
        f"— found {bus_pa_count} occurrence(s)."
    )
    # clock_safe was the 2.x-era parameter; it MUST NOT come back as a
    # regression because Liquidsoap 2.4 errors on it.
    assert "clock_safe" not in out


# ---- Phase-C5: output.file recording block -----------------------------


def test_full_render_has_recording_output_file_block():
    """
    Every render must include the per-show recording output.file block
    with id="recording" — that's the telnet hook Pypo's _on_show_record_*
    handlers use to start / stop / set-path the recording.
    """
    out = lc.render_rastatime_liq([_stream()])
    # Active code (not just template-doc comments)
    active = "\n".join(
        ln for ln in out.splitlines() if not ln.lstrip().startswith("#")
    )
    assert 'output.file(' in active
    assert 'id="recording"' in active
    # MP3@320kbps fixed per C5 decision 2026-05-27 (operator chose
    # 320k archive-grade over the historical 192/256 defaults).
    assert 'codec="libmp3lame"' in active
    assert 'b="320k"' in active
    # Filename via interactive.string + ref-deref so Pypo's
    # `var.set recording_path = "..."` telnet command takes effect.
    # (`var.get` only works on the telnet wire — in .liq script-code
    # it would error "Undefined variable var".)
    assert 'interactive.string(' in active
    assert '"recording_path"' in active
    assert 'recording_path()' in active
    # fallible=true: transient device hiccups don't kill the output.
    # NOTE: start=false was the original design but Liquidsoap-2.4.4
    # doesn't honour `recording.start` correctly with start=false
    # (no file ever opens).  C5 falls back to default start=true and
    # Pypo issues `recording.stop` right after engine init to silence
    # the initial sentinel-file write.
    assert "fallible=true" in active
    # Recording-source is the broadcast bus — same as listeners hear
    # (post-switch, post-crossfade, post-amplify).  Last positional arg.
    # We assert the bus name appears in the recording block by scoping
    # to the output.file(id="recording") slice.
    rec_idx = active.index('id="recording"')
    rec_block = active[rec_idx:rec_idx + 600]
    assert "  bus,\n" in rec_block


# ---- Phase-C4: input.harbor + switch -----------------------------------


def test_full_render_no_harbor_keeps_bus_scheduled():
    """Both harbor passwords unset → bus is plain scheduled, no input.harbor."""
    out = lc.render_rastatime_liq([_stream()])
    # No input.harbor (active) — only the doc-stub comment.
    for line in out.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        assert "input.harbor(" not in stripped, (
            f"Unexpected active input.harbor line: {line!r}"
        )
    # Bus is the direct scheduled assignment (no switch wrapper).
    assert "bus = scheduled" in out
    assert "no DJ-source harbor enabled" in out


def _active_lines(rendered: str):
    """Return rendered lines that aren't pure-comment (template-header docs)."""
    return [
        ln for ln in rendered.splitlines()
        if not ln.lstrip().startswith("#")
    ]


# ---- 24/7 hourly recording block (RASTATIME 2026-06-05) ----------------


def test_hourly_disabled_renders_stub():
    """enabled=False -> a comment stub, no active recorder."""
    out = lc._render_hourly_recording_block(enabled=False, folder="C:/r/247")
    assert 'id="recording_hourly"' not in out
    assert "disabled" in out.lower()


def test_hourly_enabled_without_folder_renders_stub():
    """enabled but empty folder -> stub (incomplete config is not active)."""
    out = lc._render_hourly_recording_block(enabled=True, folder="")
    assert 'id="recording_hourly"' not in out
    assert "disabled" in out.lower()


def test_hourly_enabled_basic_shape():
    """
    enabled + folder -> output.file(id="recording_hourly") on the bus,
    rotating via reopen_when, with the seg seeded (no boot-reopen).
    """
    out = lc._render_hourly_recording_block(
        enabled=True, folder="C:/rastatime/247", fmt="mp3", bitrate=192,
    )
    assert 'id="recording_hourly"' in out
    assert "reopen_when=rec247_reopen" in out
    # seg seeded with the CURRENT hour (not -1) so there is no spurious
    # reopen at boot that would split the first hour into two files.
    assert "rec247_seg = ref(int(gettimeofday() / 3600.))" in out
    # default 192 kbps MP3 (operator-chosen archive default).
    assert 'codec="libmp3lame"' in out
    assert 'b="192k"' in out
    # taps the broadcast bus (bit-identical to listeners).
    assert "  bus,\n" in out
    # per-day subfolder is created on reopen.
    assert "file.mkdir(" in out


def test_hourly_folder_backslashes_normalised_to_forward():
    """Windows path with backslashes -> forward slashes for Liquidsoap."""
    out = lc._render_hourly_recording_block(
        enabled=True, folder="C:\\rastatime\\247\\",
    )
    assert "C:/rastatime/247/" in out
    assert "\\rastatime" not in out


def test_hourly_bitrate_substituted():
    out = lc._render_hourly_recording_block(
        enabled=True, folder="C:/r", bitrate=256,
    )
    assert 'b="256k"' in out


def test_hourly_format_aac_uses_adts():
    out = lc._render_hourly_recording_block(enabled=True, folder="C:/r", fmt="aac")
    assert 'format="adts"' in out
    assert "-00.aac" in out


def test_hourly_format_ogg_uses_vorbis():
    out = lc._render_hourly_recording_block(enabled=True, folder="C:/r", fmt="ogg")
    assert 'codec="libvorbis"' in out
    assert "-00.ogg" in out


def test_hourly_format_opus_clamps_samplerate():
    out = lc._render_hourly_recording_block(
        enabled=True, folder="C:/r", fmt="opus", samplerate=44100,
    )
    assert 'codec="libopus"' in out
    assert "samplerate=48000" in out
    assert "-00.opus" in out


def test_hourly_unknown_format_raises():
    with pytest.raises(ValueError):
        lc._render_hourly_recording_block(enabled=True, folder="C:/r", fmt="flac")


def test_full_render_hourly_disabled_by_default_no_placeholder():
    """
    Default render: no enable flag -> stub, and the template placeholder
    must be fully substituted (a leaked ${...} would break Liquidsoap).
    """
    out = lc.render_rastatime_liq([_stream()])
    assert "${HOURLY_RECORDING_BLOCK}" not in out
    assert 'id="recording_hourly"' not in "\n".join(_active_lines(out))


def test_full_render_hourly_enabled_no_placeholder_and_present():
    out = lc.render_rastatime_liq(
        [_stream()],
        hourly_recording_enabled=True,
        hourly_recording_folder="C:/rastatime/247",
        hourly_recording_format="mp3",
        hourly_recording_bitrate=192,
    )
    assert "${HOURLY_RECORDING_BLOCK}" not in out
    active = "\n".join(_active_lines(out))
    assert 'id="recording_hourly"' in active
    # co-exists with the per-show recorder (both output.file on the bus).
    assert 'id="recording"' in active


def test_read_hourly_config_returns_safe_dict():
    """
    The cc_pref reader returns a complete dict with safe types even when
    the ORM is unavailable (it must never raise).
    """
    cfg = lc.read_hourly_recording_config_from_db()
    assert set(cfg) == {
        "enabled", "folder", "format", "bitrate", "retention_days",
    }
    assert isinstance(cfg["enabled"], bool)
    assert isinstance(cfg["bitrate"], int)
    assert isinstance(cfg["retention_days"], int)


def test_full_render_main_only_harbor():
    """Only main_password set → input.harbor for master_dj + switch(master, scheduled)."""
    out = lc.render_rastatime_liq(
        [_stream()],
        harbor_main_password="hackme-main",
    )
    active = "\n".join(_active_lines(out))
    assert 'master_dj = input.harbor' in active
    assert 'id="master_dj"' in active
    # Phase-C4 workaround: both mounts default to port 8001 because the
    # Liquidsoap-2.4 multi-port harbor bug only lets one of two distinct
    # ports come up.
    assert "port=8001" in active
    assert 'password="hackme-main"' in active
    # No show block in active code
    assert "show_dj = input.harbor" not in active
    # Switch wraps master and scheduled (no show arm)
    assert "bus = switch(" in active
    assert "source.is_ready(master_dj)" in active
    assert "source.is_ready(show_dj)" not in active


def test_full_render_show_only_harbor():
    """Only show_password set → only show_dj source + switch(show, scheduled)."""
    out = lc.render_rastatime_liq(
        [_stream()],
        harbor_show_password="hackme-show",
    )
    active = "\n".join(_active_lines(out))
    assert 'show_dj = input.harbor' in active
    # Phase-C4 workaround: show defaults to port 8001 too (shared with
    # master). Liquidsoap-2.4 multi-port harbor bug forced the merge.
    assert "port=8001" in active
    assert 'password="hackme-show"' in active
    assert "master_dj = input.harbor" not in active
    assert "source.is_ready(show_dj)" in active
    assert "source.is_ready(master_dj)" not in active


def test_full_render_both_harbor_mounts_share_port_by_default():
    """
    Both passwords set + default ports → both harbor mounts must
    share the same port (Phase-C4 workaround for Liquidsoap-2.4
    multi-port silent-fail bug).
    """
    out = lc.render_rastatime_liq(
        [_stream()],
        harbor_main_password="m",
        harbor_show_password="s",
    )
    active = "\n".join(_active_lines(out))
    # Both harbor blocks present
    assert "master_dj = input.harbor" in active
    assert "show_dj = input.harbor" in active
    # Both bound to port 8001 by default (NOT 8001 + 8002).
    # Count "port=8001" occurrences — should be 2 (one per harbor block).
    assert active.count("port=8001") == 2
    # And explicitly: NO port=8002 in the active code
    assert "port=8002" not in active


def test_full_render_both_harbor_passwords():
    """Both passwords → both input.harbor blocks + 3-arm switch."""
    out = lc.render_rastatime_liq(
        [_stream()],
        harbor_main_password="m-pw",
        harbor_show_password="s-pw",
    )
    assert 'master_dj = input.harbor' in out
    assert 'show_dj = input.harbor' in out
    # Order in the switch: master first (priority), show second,
    # scheduled fallback last.
    bus_idx = out.index("bus = switch(")
    bus_block = out[bus_idx:bus_idx + 500]
    master_pos = bus_block.index("master_dj")
    show_pos = bus_block.index("show_dj")
    scheduled_pos = bus_block.index("scheduled)")
    assert master_pos < show_pos < scheduled_pos


def test_full_render_switch_is_not_track_sensitive():
    """
    Operator-decision 2026-05-28 Phase-D Stück-B: when a DJ connects
    via input.harbor, the switch must take over IMMEDIATELY (not wait
    for the currently-playing scheduled track to end).  Trade-off:
    crossfade-shortens the current track for fast take-over.

    Regression guard: switch operator must be track_sensitive=false.
    Previously was track_sensitive=true which caused 0-N-minute
    delay between DJ-connect and audible take-over.
    """
    out = lc.render_rastatime_liq(
        [_stream()],
        harbor_main_password="m-pw",
        harbor_show_password="s-pw",
    )
    # The bus = switch(...) block must contain track_sensitive=false
    bus_idx = out.index("bus = switch(")
    bus_block = out[bus_idx:bus_idx + 500]
    assert "track_sensitive=false" in bus_block, (
        f"switch operator must be track_sensitive=false for immediate "
        f"DJ-take-over (operator decision 2026-05-28); got:\n{bus_block}"
    )
    assert "track_sensitive=true" not in bus_block


def test_full_render_harbor_password_escapes_special_chars():
    """Quote / backslash in harbor password is escaped for Liquidsoap parser."""
    out = lc.render_rastatime_liq(
        [_stream()],
        harbor_main_password=r'has"quote\and-back',
    )
    assert r'password="has\"quote\\and-back"' in out


def test_full_render_custom_harbor_ports():
    """
    Custom ports + mount names propagate.  Note: operator-explicit
    distinct ports bypass the C4 default-merge — the operator takes
    responsibility for the Liquidsoap-2.4 multi-harbor risk if they
    set different ports manually.
    """
    out = lc.render_rastatime_liq(
        [_stream()],
        harbor_main_password="x",
        harbor_main_port=9001,
        harbor_main_mount="custom-main",
        harbor_show_password="y",
        harbor_show_port=9002,
        harbor_show_mount="custom-show",
    )
    assert "port=9001" in out
    assert 'input.harbor(\n  "custom-main"' in out
    assert "port=9002" in out
    assert 'input.harbor(\n  "custom-show"' in out


def test_full_render_harbor_buffer_seconds():
    """harbor_buffer_seconds substituted in the buffer=... argument."""
    out = lc.render_rastatime_liq(
        [_stream()],
        harbor_main_password="x",
        harbor_buffer_seconds=3.5,
    )
    assert "buffer=3.5" in out


def test_full_render_custom_telnet_and_log():
    out = lc.render_rastatime_liq(
        [_stream()],
        telnet_host="192.168.1.50",
        telnet_port=4242,
        log_file="D:/logs/ls.log",
    )
    assert '"192.168.1.50"' in out
    assert "telnet.port.set(4242)" in out
    assert '"D:/logs/ls.log"' in out


def test_full_render_custom_crossfade_duration():
    """Custom crossfade duration appears in crossfade() call."""
    out = lc.render_rastatime_liq([_stream()], crossfade_duration=5.0)
    assert "duration=5.0" in out


def test_full_render_crossfade_disabled():
    """crossfade_duration=0 produces duration=0.0 (disables crossfade)."""
    out = lc.render_rastatime_liq([_stream()], crossfade_duration=0.0)
    # duration=0.0 means Liquidsoap performs no crossfade, but the
    # crossfade() operator still wraps the source — that's fine, it
    # becomes effectively a no-op pass-through.
    assert "duration=0.0" in out


def test_full_render_custom_crossfade_fade_seconds():
    """RASTATIME_LIQUIDSOAP_CROSSFADE_FADE_SECONDS controls fade_in/fade_out."""
    out = lc.render_rastatime_liq(
        [_stream()],
        crossfade_fade_seconds=0.5,
    )
    assert "fade_in=0.5" in out
    assert "fade_out=0.5" in out


def test_full_render_crossfade_fade_zero_hard_cuts():
    """fade_seconds=0 produces hard cuts between ALL tracks."""
    out = lc.render_rastatime_liq(
        [_stream()],
        crossfade_fade_seconds=0.0,
    )
    assert "fade_in=0.0" in out
    assert "fade_out=0.0" in out


def test_full_render_crossfade_fractional():
    """Sub-second crossfade renders without losing precision."""
    out = lc.render_rastatime_liq([_stream()], crossfade_duration=1.25)
    assert "duration=1.25" in out


# ---- _format_crossfade_duration -----------------------------------------


@pytest.mark.parametrize("value,expected", [
    (0,    "0.0"),
    (0.0,  "0.0"),
    (1,    "1.0"),
    (2.0,  "2.0"),
    (2.5,  "2.5"),
    (2.50, "2.5"),
    (1.25, "1.25"),
    (2.123456, "2.12"),  # rounds to 2 decimals
])
def test_format_crossfade_duration(value, expected):
    assert lc._format_crossfade_duration(value) == expected


def test_full_render_no_streams_keeps_telnet_intact():
    """Zero streams configured — telnet block still rendered correctly."""
    out = lc.render_rastatime_liq([])
    assert "settings.server.telnet.set(true)" in out
    assert "no stream outputs configured" in out
    # (We don't bother grepping that no `output.icecast(` is present
    #  in the rendered file — the template's documentation block
    #  legitimately mentions the operator name in a comment.  The
    #  meaningful guarantee is the comment marker check above:
    #  the empty-list branch of _render_icecast_outputs ran.)


def test_full_render_no_leftover_dollar_placeholders():
    """
    Guard against a future template edit adding a new ${X} placeholder
    that the renderer forgets to substitute — the resulting .liq would
    fail to parse (Liquidsoap doesn't natively understand ${X} syntax).
    """
    out = lc.render_rastatime_liq([_stream()])
    # No literal "${" sequences should survive rendering — every
    # placeholder must either be substituted or never have been written
    # with the dollar prefix in the first place (the doc-header uses
    # the dollar-free {X} form on purpose).
    assert "${" not in out, (
        "Leftover ${...} placeholder in rendered .liq — "
        "the renderer needs an extra .replace() call."
    )


def test_full_render_log_path_with_quotes_escaped():
    """Awkward log path with quote characters — must escape."""
    out = lc.render_rastatime_liq(
        [_stream()],
        log_file=r'C:/with"quote.log',
    )
    assert r'C:/with\"quote.log' in out


# ---- write_rastatime_liq ------------------------------------------------


def test_write_creates_file_and_reports_changed(tmp_path: Path):
    out = tmp_path / "rastatime.liq"
    changed = lc.write_rastatime_liq(out, [_stream()])
    assert changed is True
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "output.icecast(" in text


def test_write_unchanged_returns_false(tmp_path: Path):
    out = tmp_path / "rastatime.liq"
    lc.write_rastatime_liq(out, [_stream()])
    # Same inputs again → no change
    changed = lc.write_rastatime_liq(out, [_stream()])
    assert changed is False


def test_write_changed_input_returns_true(tmp_path: Path):
    out = tmp_path / "rastatime.liq"
    lc.write_rastatime_liq(out, [_stream(mount="first")])
    # Different stream → change
    changed = lc.write_rastatime_liq(out, [_stream(mount="second")])
    assert changed is True
    assert 'mount="/second"' in out.read_text(encoding="utf-8")


def test_write_no_bom(tmp_path: Path):
    """Liquidsoap parser tripped on BOM in Phase-0 setup — explicitly NO bom."""
    out = tmp_path / "rastatime.liq"
    lc.write_rastatime_liq(out, [_stream()])
    raw = out.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf"), "Rendered file must not have BOM"


def test_write_atomic_no_tmp_leftover(tmp_path: Path):
    """After a successful write the .tmp file must not be left around."""
    out = tmp_path / "rastatime.liq"
    lc.write_rastatime_liq(out, [_stream()])
    assert not (tmp_path / "rastatime.liq.tmp").exists()


# ---- Smoke test: rendered template still parses placeholder-free --------


def test_template_has_all_expected_placeholders():
    """
    Guard against a future template edit that drops a placeholder we
    still need.  If someone removes ${ICECAST_OUTPUTS} from the template
    without also removing the renderer's replace(), the rendered file
    would silently lose the Icecast configuration — this test catches that.
    """
    text = lc._DEFAULT_TEMPLATE_PATH.read_text(encoding="utf-8")
    for placeholder in (
        "${TELNET_HOST}",
        "${TELNET_PORT}",
        "${LOG_FILE}",
        "${CROSSFADE_DURATION}",
        "${LOCAL_OUTPUT_BLOCK}",
        "${HARBOR_INPUTS_BLOCK}",
        "${WEBSTREAM_INPUT_BLOCK}",
        "${LINEIN_INPUT_BLOCK}",
        "${BUS_SOURCE_BLOCK}",
        "${ICECAST_OUTPUTS}",
        "${HOURLY_RECORDING_BLOCK}",
    ):
        assert placeholder in text, (
            f"Template lost expected placeholder {placeholder}"
        )


# ---- Phase-E: webstream input.http block -------------------------------


def test_full_render_default_includes_webstream_input_block():
    """
    Default render (DEFAULT_WEBSTREAM_ENABLED=True) MUST include the
    input.http webstream source + the amplify-gain wrapper + the
    switch-arm.  Phase-E 2026-05-29 makes scheduled webstreams work
    via Liquidsoap; the renderer must produce all three pieces.
    """
    out = lc.render_rastatime_liq([_stream()])
    active = "\n".join(_active_lines(out))
    # RASTATIME 2026-09-08: a FRESH input.http per slot.  The bus arm is
    # a source.dynamic (id "webstream") that holds the current slot's
    # bridge, source.fail() between slots; webstream.start opens a new
    # input.http (start=true, numbered id) + a new bridge, webstream.stop
    # drops them.  A reused input.http hung 20-110 s on restart in four
    # of five production-like replica runs (Windows Duppy wake-up).
    assert 'webstream_raw = source.dynamic(id="webstream", self_sync=false,' in active
    assert "webstream_current = ref(source.fail())" in active
    assert 'input.http(id="webstream_in_#{n}", start=true, self_sync=false,' in active
    assert "start=false" not in active.split("linein")[0]      # no idle static input any more
    # max_buffer / timeout / poll_delay rendered with the defaults
    assert f"max_buffer={lc._format_crossfade_duration(lc.DEFAULT_WEBSTREAM_MAX_BUFFER_SECONDS)}" in active
    assert f"timeout={lc._format_crossfade_duration(lc.DEFAULT_WEBSTREAM_TIMEOUT_SECONDS)}" in active
    assert f"poll_delay={lc._format_crossfade_duration(lc.DEFAULT_WEBSTREAM_POLL_DELAY_SECONDS)}" in active
    # amplify-gain wrapper with interactive.float("webstream.gain", 1.0)
    # around the dynamic arm
    assert 'interactive.float("webstream.gain", 1.0)' in active
    assert "webstream = amplify({webstream_gain()}, webstream_raw)" in active
    # a fresh 5 s bridge (max 10 s) per slot - no stale audio from the
    # previous slot, and crossfade-compatible like before
    assert ('b = buffer(id="webstream_bridge_#{n}",\n'
            '      buffer=5.0, max=10.0, s)') in active
    assert "buffer=10.0,\n  max=20.0" not in active
    # PLAYOUT's telnet contract is registered by the template itself
    for cmd in ('"url"', '"start"', '"stop"', '"status"', '"ready"'):
        assert cmd in active, cmd
    assert "def webstream_start() =" in active and "def webstream_stop() =" in active
    assert "source.is_ready(webstream)" in active
    assert lc.DEFAULT_WEBSTREAM_TIMEOUT_SECONDS == 3.0
    assert lc.DEFAULT_WEBSTREAM_POLL_DELAY_SECONDS == 0.5
    assert "timeout=3.0," in active and "poll_delay=0.5," in active
    # Switch must include the webstream arm at priority between
    # DJ-sources and scheduled.
    bus_idx = active.index("bus = switch(")
    bus_block = active[bus_idx:bus_idx + 400]
    assert "source.is_ready(webstream)" in bus_block


def test_full_render_webstream_disabled_renders_stub_comment():
    """
    With webstream_enabled=False (legacy mpv/VLC paths) the renderer
    emits ONLY a comment stub for the webstream block — no
    webstream_raw + no webstream_gain + no switch-arm.

    Note: linein also uses input.http, so we disable both here to
    test the webstream-only-disabled stub semantics in isolation.
    """
    out = lc.render_rastatime_liq(
        [_stream()],
        webstream_enabled=False,
        linein_enabled=False,
    )
    active = "\n".join(_active_lines(out))
    # No active input.http for webstream (or linein, since both off here)
    assert "input.http(" not in active
    assert "webstream_raw" not in active
    assert "webstream_gain" not in active
    # Switch arm for webstream MUST NOT appear (would reference missing source)
    assert "source.is_ready(webstream)" not in active


def test_full_render_webstream_custom_buffer_timeout_poll():
    """Custom webstream tuning params propagate to the rendered input.http."""
    out = lc.render_rastatime_liq(
        [_stream()],
        webstream_max_buffer_seconds=15.0,
        webstream_timeout_seconds=5.0,
        webstream_poll_delay_seconds=1.5,
    )
    assert "max_buffer=15.0" in out
    assert "timeout=5.0" in out
    assert "poll_delay=1.5" in out


def test_full_render_webstream_switch_priority_below_dj_above_scheduled():
    """
    Switch-arm priority: master_dj > show_dj > webstream > linein > scheduled.
    Critical for live-radio semantics — DJ-takeover beats everything,
    webstream + linein beat silence-fallback.  (linein/webstream
    ordering is arbitrary; a single slot is never both at the same time.)
    """
    out = lc.render_rastatime_liq(
        [_stream()],
        harbor_main_password="m-pw",
        harbor_show_password="s-pw",
        # webstream + linein default to enabled
    )
    bus_idx = out.index("bus = switch(")
    bus_block = out[bus_idx:bus_idx + 800]
    master_pos = bus_block.index("master_dj")
    show_pos = bus_block.index("show_dj")
    webstream_pos = bus_block.index("webstream)")
    linein_pos = bus_block.index("linein)")
    scheduled_pos = bus_block.index("scheduled)")
    assert master_pos < show_pos < webstream_pos < linein_pos < scheduled_pos


def test_full_render_no_harbor_but_webstream_enabled_uses_switch():
    """
    No DJ sources but webstream enabled → switch still wraps (no fallback
    to the C3-era `bus = scheduled` direct assignment).
    """
    out = lc.render_rastatime_liq([_stream()])  # defaults: no harbor, webstream on
    active = "\n".join(_active_lines(out))
    # Must use the switch wrapper (not the bare bus = scheduled)
    assert "bus = switch(" in active
    # And the switch must reference both webstream + scheduled
    assert "source.is_ready(webstream)" in active
    bus_idx = active.index("bus = switch(")
    bus_block = active[bus_idx:bus_idx + 400]
    assert "scheduled)" in bus_block
    # NO master/show in this scenario
    assert "master_dj" not in active
    assert "show_dj" not in active


def test_full_render_no_harbor_no_webstream_bare_bus_scheduled():
    """
    No DJ sources AND webstream + linein disabled → bus = scheduled
    directly (no switch wrapper noise, matches C3-era behaviour for
    legacy deployments).
    """
    out = lc.render_rastatime_liq(
        [_stream()],
        webstream_enabled=False,
        linein_enabled=False,
    )
    active = "\n".join(_active_lines(out))
    assert "bus = scheduled" in active
    # And specifically no switch wrapper for the bus assignment
    # (other switch operators may exist in the template doc-area)
    for line in active.splitlines():
        if line.startswith("bus = "):
            assert "switch" not in line, (
                f"Bare bus= line should not wrap switch when no upstream "
                f"sources active; got: {line!r}"
            )


# ---- Phase-F-2: linein input.ffmpeg(format=dshow) block ---------------


def test_full_render_default_includes_linein_input_block():
    """
    Default render (DEFAULT_LINEIN_ENABLED=True) MUST include the
    input.ffmpeg(format="dshow") linein source + the server.register
    command block + switch-arm.  Phase-F-2 (2026-05-30) replaced the
    input.http + FfmpegLineinCapture approach with direct dshow capture.
    """
    out = lc.render_rastatime_liq([_stream()])
    active = "\n".join(_active_lines(out))
    assert "linein_raw = input.ffmpeg(" in active
    assert 'id="linein"' in active
    assert 'format="dshow"' in active
    assert "start=false" in active
    assert "self_sync=false" in active
    # Empty initial input spec (Pypo sets it via linein.set_url before start)
    assert '  "",' in active
    # audio_to_stereo fixes the polymorphic input.ffmpeg type for the switch
    assert "linein_dshow = audio_to_stereo(linein_raw)" in active
    # input.ffmpeg does NOT auto-register commands → manual server.register
    assert 'server.register(' in active
    assert 'namespace="linein"' in active
    assert '"set_url"' in active
    assert '"start"' in active
    assert '"stop"' in active
    assert '"status"' in active
    # RASTATIME 2026-08-31 — multichannel path: the fixed-URL
    # input.http companion source consuming /linein-capture, and the
    # fallback that folds both paths into the single `linein` arm.
    assert 'linein_http_raw = input.http(' in active
    assert 'id="linein_http"' in active
    assert '"http://127.0.0.1:8000/linein-capture",' in active
    assert "linein_http = audio_to_stereo(linein_http_raw)" in active
    assert (
        "linein = fallback(track_sensitive=false, [linein_dshow, linein_http])"
        in active
    )
    # The dshow source itself must NOT have turned into input.http
    assert "linein_raw = input.http(" not in active
    # Switch arm
    bus_idx = active.index("bus = switch(")
    bus_block = active[bus_idx:bus_idx + 500]
    assert "source.is_ready(linein)" in bus_block


def test_full_render_linein_disabled_renders_stub_comment():
    """
    With linein_enabled=False (legacy mpv/VLC paths) the renderer
    emits ONLY a comment stub — no input.ffmpeg + no switch-arm.
    """
    out = lc.render_rastatime_liq(
        [_stream()],
        linein_enabled=False,
    )
    active = "\n".join(_active_lines(out))
    # No active linein source or its server.register block
    assert "linein = input.ffmpeg(" not in active
    assert 'namespace="linein"' not in active
    # Switch arm for linein MUST NOT appear
    assert "source.is_ready(linein)" not in active


def test_full_render_linein_custom_max_buffer():
    """Custom max_buffer propagates to the rendered input.ffmpeg."""
    out = lc.render_rastatime_liq(
        [_stream()],
        linein_max_buffer_seconds=4.0,
    )
    assert "max_buffer=4.0" in out


def test_full_render_switch_includes_both_webstream_and_linein_by_default():
    """
    Default render (both webstream + linein enabled, no harbor) →
    switch wraps scheduled + webstream + linein.
    """
    out = lc.render_rastatime_liq([_stream()])
    active = "\n".join(_active_lines(out))
    bus_idx = active.index("bus = switch(")
    bus_block = active[bus_idx:bus_idx + 500]
    assert "source.is_ready(webstream)" in bus_block
    assert "source.is_ready(linein)" in bus_block
    # webstream before linein (priority order)
    assert bus_block.index("webstream)") < bus_block.index("linein)")


# ---- _normalize_loopback_host -------------------------------------------


def test_normalize_localhost_becomes_ipv4_loopback():
    assert lc._normalize_loopback_host("localhost") == "127.0.0.1"


def test_normalize_localhost_case_and_whitespace():
    assert lc._normalize_loopback_host(" LocalHost ") == "127.0.0.1"


def test_normalize_leaves_other_hosts_alone():
    assert lc._normalize_loopback_host("127.0.0.1") == "127.0.0.1"
    assert lc._normalize_loopback_host("icecast.example.org") == "icecast.example.org"
    assert lc._normalize_loopback_host("192.168.1.164") == "192.168.1.164"


def test_render_block_normalizes_localhost_host():
    out = lc._render_icecast_block(_stream(host="localhost"))
    assert 'host="127.0.0.1"' in out
    assert "localhost" not in out


def test_render_block_keeps_remote_host():
    out = lc._render_icecast_block(_stream(host="stream.example.org"))
    assert 'host="stream.example.org"' in out
