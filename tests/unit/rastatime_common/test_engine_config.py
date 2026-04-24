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
# create_playout_engine — LIBVLC
# ---------------------------------------------------------------------------

def _vlc_available() -> bool:
    try:
        from playout.engine_vlc.probe import probe  # noqa: PLC0415
        return probe().available
    except Exception:
        return False


def test_create_libvlc_engine_when_vlc_installed():
    """When VLC is installed, factory returns a VlcPlayoutEngine."""
    if not _vlc_available():
        pytest.skip("VLC not installed in this environment")
    from playout.engine_vlc import VlcPlayoutEngine  # noqa: PLC0415
    engine = create_playout_engine(PlayoutEngineKind.LIBVLC, vlc_args=["--aout=dummy"])
    assert isinstance(engine, VlcPlayoutEngine)
    engine.close()


def test_create_libvlc_engine_raises_import_error_when_vlc_missing(monkeypatch):
    """When playout.engine_vlc cannot be imported, factory raises ImportError."""
    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "playout.engine_vlc" or name.startswith("playout.engine_vlc"):
            raise ImportError("No module named 'playout.engine_vlc'")
        return real_import(name, *args, **kwargs)

    # Also remove from sys.modules cache so the mock import takes effect
    import sys
    cached = {k: v for k, v in sys.modules.items() if "playout.engine_vlc" in k}
    for k in cached:
        monkeypatch.delitem(sys.modules, k, raising=False)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    with pytest.raises(ImportError, match="playout.engine_vlc"):
        create_playout_engine(PlayoutEngineKind.LIBVLC)
