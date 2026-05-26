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
    password="hackme", user="source", bitrate=128,
    name="RASTATIME", description="Live stream",
):
    """Build a stream_output_N-shaped dict for tests."""
    return {
        "type": type_, "host": host, "port": port, "mount": mount,
        "pass": password, "user": user, "bitrate": bitrate,
        "name": name, "description": description,
    }


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
    # Connection
    assert 'host="localhost"' in out
    assert "port=8000" in out
    assert 'user="source"' in out
    assert 'password="hackme"' in out
    assert 'mount="/rastatime"' in out
    # Phase-C3 operator-decision: indefinite retry 5 s
    assert "restart_delay=5." in out
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
        "${ICECAST_OUTPUTS}",
    ):
        assert placeholder in text, (
            f"Template lost expected placeholder {placeholder}"
        )
