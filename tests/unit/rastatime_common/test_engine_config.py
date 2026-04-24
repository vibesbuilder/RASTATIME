"""
T4.2 validation — engine selection config.

Verifies that:
1. PlayoutEngineKind has MOCK and LIBVLC values.
2. get_playout_engine_kind() defaults to MOCK.
3. get_playout_engine_kind() reads RASTATIME_PLAYOUT_ENGINE from the env.
4. get_playout_engine_kind() is case-insensitive.
5. get_playout_engine_kind() raises ValueError for unrecognised values.
6. create_playout_engine(MOCK) returns a MockPlayoutEngine instance.
7. create_playout_engine(LIBVLC) raises ImportError (engine_vlc not yet built).
8. create_playout_engine() reads kind from the environment when None.
9. kwargs are forwarded to the mock engine constructor.
"""

import os
import pytest

from rastatime_common.config import (
    PlayoutEngineKind,
    create_playout_engine,
    get_playout_engine_kind,
)
from playout.engine_interface import PlayoutEngine, PlayoutState
from playout.engine_mock import MockPlayoutEngine


# ---------------------------------------------------------------------------
# PlayoutEngineKind enum
# ---------------------------------------------------------------------------

def test_kind_values_exist():
    assert PlayoutEngineKind.MOCK.value == "mock"
    assert PlayoutEngineKind.LIBVLC.value == "libvlc"


def test_kind_is_str_enum():
    """PlayoutEngineKind is a str enum — values compare equal to plain strings."""
    assert PlayoutEngineKind.MOCK == "mock"
    assert PlayoutEngineKind.LIBVLC == "libvlc"


# ---------------------------------------------------------------------------
# get_playout_engine_kind
# ---------------------------------------------------------------------------

def test_default_is_mock(monkeypatch):
    monkeypatch.delenv("RASTATIME_PLAYOUT_ENGINE", raising=False)
    assert get_playout_engine_kind() == PlayoutEngineKind.MOCK


def test_env_selects_mock(monkeypatch):
    monkeypatch.setenv("RASTATIME_PLAYOUT_ENGINE", "mock")
    assert get_playout_engine_kind() == PlayoutEngineKind.MOCK


def test_env_selects_libvlc(monkeypatch):
    monkeypatch.setenv("RASTATIME_PLAYOUT_ENGINE", "libvlc")
    assert get_playout_engine_kind() == PlayoutEngineKind.LIBVLC


def test_env_is_case_insensitive(monkeypatch):
    monkeypatch.setenv("RASTATIME_PLAYOUT_ENGINE", "MOCK")
    assert get_playout_engine_kind() == PlayoutEngineKind.MOCK

    monkeypatch.setenv("RASTATIME_PLAYOUT_ENGINE", "LibVLC")
    assert get_playout_engine_kind() == PlayoutEngineKind.LIBVLC


def test_env_strips_whitespace(monkeypatch):
    monkeypatch.setenv("RASTATIME_PLAYOUT_ENGINE", "  mock  ")
    assert get_playout_engine_kind() == PlayoutEngineKind.MOCK


def test_invalid_env_raises_value_error(monkeypatch):
    monkeypatch.setenv("RASTATIME_PLAYOUT_ENGINE", "portaudio")
    with pytest.raises(ValueError, match="RASTATIME_PLAYOUT_ENGINE"):
        get_playout_engine_kind()


# ---------------------------------------------------------------------------
# create_playout_engine — MOCK
# ---------------------------------------------------------------------------

def test_create_mock_engine_explicit(monkeypatch):
    monkeypatch.delenv("RASTATIME_PLAYOUT_ENGINE", raising=False)
    engine = create_playout_engine(PlayoutEngineKind.MOCK)
    assert isinstance(engine, MockPlayoutEngine)
    assert isinstance(engine, PlayoutEngine)
    assert engine.get_state() == PlayoutState.STOPPED


def test_create_mock_engine_from_env(monkeypatch):
    monkeypatch.setenv("RASTATIME_PLAYOUT_ENGINE", "mock")
    engine = create_playout_engine()  # kind=None → reads env
    assert isinstance(engine, MockPlayoutEngine)


def test_create_mock_engine_forwards_kwargs(monkeypatch):
    monkeypatch.delenv("RASTATIME_PLAYOUT_ENGINE", raising=False)
    engine = create_playout_engine(PlayoutEngineKind.MOCK, default_track_duration=99.0)
    assert isinstance(engine, MockPlayoutEngine)
    # Verify the kwarg was forwarded: duration used by _item_duration for None-duration items
    assert engine._default_track_duration == 99.0


# ---------------------------------------------------------------------------
# create_playout_engine — LIBVLC (not yet implemented)
# ---------------------------------------------------------------------------

def test_create_libvlc_engine_raises_import_error():
    """
    engine_vlc does not exist yet (Phase 4). The factory must raise
    ImportError with a helpful message rather than an AttributeError or crash.
    """
    with pytest.raises(ImportError, match="playout.engine_vlc"):
        create_playout_engine(PlayoutEngineKind.LIBVLC)
