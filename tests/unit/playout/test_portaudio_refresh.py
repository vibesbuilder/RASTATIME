"""
RASTATIME 2026-09-07 - PortAudio re-enumeration before resolving the Main
Output.  A long-running PLAYOUT resolved against the device list from its
own start; while the studio display slept its HD-Audio endpoint was gone,
the indices had shifted, and the nightly restart crash-looped Liquidsoap
(``refresh_device_list``).
"""
from __future__ import annotations

import sys

from rastatime_playout.engine.portaudio_output import (
    refresh_device_list,
    resolve_output_device,
)


class _Fresh:
    def __init__(self):
        self.calls = []

    def _terminate(self):
        self.calls.append("terminate")

    def _initialize(self):
        self.calls.append("initialize")

    def query_hostapis(self):
        return []

    def query_devices(self):
        return []


def test_refresh_calls_terminate_then_initialize():
    sd = _Fresh()
    assert refresh_device_list(sd) is True
    assert sd.calls == ["terminate", "initialize"]


def test_refresh_is_a_noop_for_stand_ins_without_hooks():
    class _Plain:
        pass

    assert refresh_device_list(_Plain()) is False


def test_refresh_survives_a_failing_terminate(caplog):
    class _Broken(_Fresh):
        def _terminate(self):
            raise RuntimeError("PortAudio busy")

    sd = _Broken()
    assert refresh_device_list(sd) is False
    assert sd.calls == ["initialize"]          # re-init attempted so queries keep working
    assert any("re-enumeration failed" in r.message for r in caplog.records)


def test_resolve_refreshes_before_enumerating(monkeypatch):
    sd = _Fresh()
    monkeypatch.setitem(sys.modules, "sounddevice", sd)
    assert resolve_output_device("Tascam-Lautsprecher") is None    # empty list -> OS default
    assert sd.calls[:2] == ["terminate", "initialize"]
