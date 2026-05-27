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
    # Connection
    assert 'host="localhost"' in out
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
    # Phase-C6: crossfade + amplify on the bus
    assert "crossfade(duration=2.0, bus)" in out
    assert 'amplify(override="replaygain_track_gain", 1., bus)' in out
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
    Explicit local_output_enabled=True renders output.portaudio wrapped
    in clock.assign_new (isolate from main clock to avoid the
    PortAudio-underflow-takes-down-Liquidsoap-process pathology found
    in the C4 reality-test) plus fallible=true (transient device
    hiccups don't kill the output forever).

    Note: Liquidsoap 2.4 dropped the `clock_safe=true` shortcut, so
    we use the standard clock.assign_new wrapper instead.
    """
    out = lc.render_rastatime_liq([_stream()], local_output_enabled=True)
    assert "output.portaudio(" in out
    assert 'clock.assign_new(id="portaudio_clock"' in out
    assert "fallible=true" in out
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
    # fallible+start=false: idle until Pypo calls recording.start
    assert "fallible=true" in active
    assert "start=false" in active
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
    assert "crossfade(duration=5.0, bus)" in out


def test_full_render_crossfade_disabled():
    """crossfade_duration=0 produces duration=0.0 (disables crossfade)."""
    out = lc.render_rastatime_liq([_stream()], crossfade_duration=0.0)
    # duration=0.0 means Liquidsoap performs no crossfade, but the
    # crossfade() operator still wraps the source — that's fine, it
    # becomes effectively a no-op pass-through.
    assert "crossfade(duration=0.0, bus)" in out


def test_full_render_crossfade_fractional():
    """Sub-second crossfade renders without losing precision."""
    out = lc.render_rastatime_liq([_stream()], crossfade_duration=1.25)
    assert "crossfade(duration=1.25, bus)" in out


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
        "${BUS_SOURCE_BLOCK}",
        "${ICECAST_OUTPUTS}",
    ):
        assert placeholder in text, (
            f"Template lost expected placeholder {placeholder}"
        )
