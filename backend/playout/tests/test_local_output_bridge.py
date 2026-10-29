"""
RASTATIME 2026-09-14 - the local PortAudio output (Main Output) is opened
once per process and never stopped: ``mksafe`` behind the bridge buffer and
``fallible=false`` on ``output.portaudio``.  The bridge compensates the
device clock drift with ``buffer.adaptative``; the machine setting
``RASTATIME_LIQUIDSOAP_LOCAL_OUTPUT_ADAPTIVE=false`` renders the plain
``buffer()`` again.

Background: with ``fallible=true`` every underrun of the 2 s bridge stopped
the output and re-opened the device with the device list from Liquidsoap's
start.  The studio display's audio endpoint comes and goes, so the re-open
killed the engine four times between 2026-09-07 and 2026-09-14 ("device ID
out of range") and on 2026-09-10 silently opened another device (about 30 h
without Liquidsoap audio on the Tascam).  ``liquidsoap --check`` does not
notice a missing ``mksafe`` - only the start does - so the render is guarded
here; ``C:/Temp/optd/bridge_probe.py`` is the runtime check.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from rastatime_playout import __main__ as main
from rastatime_playout import liquidsoap_config as lc

LIQUIDSOAP_EXE = Path("C:/Tools/liquidsoap/liquidsoap.exe")
TASCAM = "Tascam-Lautsprecher (US-16x08)"
MKSAFE_SOURCE = '  mksafe(id="portaudio_safe", bus_for_portaudio),'


def _stream(**over):
    out = {
        "type": "mp3", "host": "localhost", "port": 8000, "mount": "rastatime",
        "pass": "hackme", "user": "source", "bitrate": 128,
        "name": "RASTATIME", "description": "Live stream",
    }
    out.update(over)
    return out


def _active(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if not ln.lstrip().startswith("#")]


def _portaudio_call(text: str) -> list[str]:
    """The active lines of the ``output.portaudio(...)`` call."""
    lines = _active(text)
    start = next(i for i, ln in enumerate(lines) if ln.startswith("output.portaudio("))
    end = next(i for i in range(start, len(lines)) if lines[i] == ")")
    return lines[start:end + 1]


def _block(**kw):
    return lc._render_local_output_block(
        True, None, TASCAM + " [Windows WASAPI]", "ep-1", TASCAM, **kw,
    )


# ---- rendered block ------------------------------------------------------


def test_default_bridge_is_adaptive_with_a_tight_speed_limit():
    active = _active(_block())
    assert (
        'bus_for_portaudio = buffer.adaptative(id="portaudio_buffer", '
        "fallible=true, buffer=2.0, limit=1.001, bus)"
    ) in active
    assert not any(ln.startswith("bus_for_portaudio = buffer(") for ln in active)
    assert lc.DEFAULT_LOCAL_OUTPUT_ADAPTIVE is True
    # 0.1 % speed change at most - far below what anyone can hear
    assert 1.0 < lc.LOCAL_OUTPUT_ADAPTIVE_LIMIT <= 1.001


def test_plain_bridge_when_adaptive_is_off():
    active = _active(_block(adaptive=False))
    assert "bus_for_portaudio = buffer(buffer=2.0, bus)" in active
    assert not any("buffer.adaptative" in ln for ln in active)


@pytest.mark.parametrize("adaptive", [True, False])
def test_output_never_stops_mksafe_and_not_fallible(adaptive):
    call = _portaudio_call(_block(adaptive=adaptive))
    assert "  fallible=false," in call
    assert not any("fallible=true" in ln for ln in call)
    # the source argument - the last line before the closing paren - is mksafe
    assert call[-2] == MKSAFE_SOURCE


@pytest.mark.parametrize("adaptive", [True, False])
def test_bridge_stays_on_its_own_clock(adaptive):
    joined = "\n".join(_active(_block(adaptive=adaptive)))
    assert (
        'ignore(clock.assign_new(id="portaudio_clock", sync="auto", [\n'
        "  bus_for_portaudio,\n"
        "]))"
    ) in joined


def test_device_selection_by_name_is_unchanged():
    block = _block()
    assert "# rastatime-main-output: ep-1" in block
    assert f'  device_name="{TASCAM}",' in _portaudio_call(block)


def test_index_fallback_is_kept_open_as_well():
    call = _portaudio_call(lc._render_local_output_block(True, 18, "Tascam [WASAPI]", "ep-2"))
    assert "  device_id=18," in call
    assert call[-2] == MKSAFE_SOURCE


def test_disabled_output_renders_no_bridge():
    block = lc._render_local_output_block(False, None, "", "", TASCAM)
    assert not any("output.portaudio(" in ln for ln in _active(block))
    assert "bus_for_portaudio" not in block


# ---- render / write pass the switch through ------------------------------


def test_full_render_default_is_adaptive():
    out = lc.render_rastatime_liq([_stream()], local_output_device_name=TASCAM)
    assert 'buffer.adaptative(id="portaudio_buffer"' in out
    assert _portaudio_call(out)[-2] == MKSAFE_SOURCE


def test_full_render_passes_adaptive_false():
    out = lc.render_rastatime_liq(
        [_stream()], local_output_device_name=TASCAM, local_output_adaptive=False,
    )
    active = _active(out)
    assert "bus_for_portaudio = buffer(buffer=2.0, bus)" in active
    assert not any("buffer.adaptative" in ln for ln in active)
    assert _portaudio_call(out)[-2] == MKSAFE_SOURCE


def test_write_passes_adaptive_false(tmp_path):
    path = tmp_path / "rastatime.liq"
    lc.write_rastatime_liq(
        path, [_stream()], local_output_device_name=TASCAM, local_output_adaptive=False,
    )
    assert "bus_for_portaudio = buffer(buffer=2.0, bus)" in _active(path.read_text(encoding="utf-8"))


# ---- machine setting -----------------------------------------------------


def test_setting_unset_means_adaptive(monkeypatch):
    monkeypatch.delenv(main.LOCAL_OUTPUT_ADAPTIVE_ENV, raising=False)
    assert main._local_output_adaptive_enabled() is True


@pytest.mark.parametrize("value", ["false", "0", "no", "off", " OFF ", "False"])
def test_setting_off_values(monkeypatch, value):
    monkeypatch.setenv(main.LOCAL_OUTPUT_ADAPTIVE_ENV, value)
    assert main._local_output_adaptive_enabled() is False


@pytest.mark.parametrize("value", ["true", "1", "yes", "on"])
def test_setting_other_values_keep_adaptive(monkeypatch, value):
    monkeypatch.setenv(main.LOCAL_OUTPUT_ADAPTIVE_ENV, value)
    assert main._local_output_adaptive_enabled() is True


# ---- type check with the installed engine --------------------------------


@pytest.mark.skipif(not LIQUIDSOAP_EXE.exists(), reason="liquidsoap.exe not installed")
@pytest.mark.parametrize("adaptive", [True, False])
def test_full_render_typechecks(tmp_path, adaptive):
    liq = tmp_path / f"bridge_{'adaptive' if adaptive else 'plain'}.liq"
    liq.write_text(
        lc.render_rastatime_liq(
            [_stream()], local_output_device_name=TASCAM, local_output_adaptive=adaptive,
        ),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [str(LIQUIDSOAP_EXE), "--check", str(liq)],
        capture_output=True, text=True, timeout=180,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
