"""
RASTATIME 2026-09-10 — Liquidsoap is the only playout engine.

``RASTATIME_PLAYOUT_ENGINE`` is still honoured for installed service
environments, but the only accepted value is ``liquidsoap``; anything
else (the deleted ``mpv`` / ``vlc`` engines) aborts the start with a
critical log line instead of silently running a different setup.
"""
from __future__ import annotations

import logging

import pytest

from libretime_playout import __main__ as main


def test_unset_means_liquidsoap(monkeypatch):
    monkeypatch.delenv(main.PLAYOUT_ENGINE_ENV, raising=False)
    assert main._require_liquidsoap_engine() == "liquidsoap"


def test_liquidsoap_any_case_and_whitespace(monkeypatch):
    monkeypatch.setenv(main.PLAYOUT_ENGINE_ENV, "  LiquidSoap ")
    assert main._require_liquidsoap_engine() == "liquidsoap"


@pytest.mark.parametrize("value", ["mpv", "vlc", "MPV", "something"])
def test_other_engines_abort_with_a_critical_line(monkeypatch, caplog, value):
    monkeypatch.setenv(main.PLAYOUT_ENGINE_ENV, value)
    with caplog.at_level(logging.CRITICAL):
        with pytest.raises(SystemExit) as exc:
            main._require_liquidsoap_engine()
    assert exc.value.code == 1
    assert value.lower() in caplog.text
    assert "liquidsoap" in caplog.text.lower()
