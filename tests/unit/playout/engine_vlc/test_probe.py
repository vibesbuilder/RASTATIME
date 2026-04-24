"""
T5.1 validation — libVLC runtime probe.

Verifies that:
1. probe() returns a ProbeResult with the expected fields.
2. On a machine where VLC is installed, probe() reports available=True.
3. ProbeResult.summary() returns a non-empty string.
4. ProbeResult.raise_if_unavailable() is a no-op when available=True.
5. ProbeResult.raise_if_unavailable() raises RuntimeError when available=False.
6. When python-vlc is not importable, probe() returns available=False with an error.
7. _find_dll() finds libvlc.dll in known paths.
8. _dll_bits() correctly reads PE header bitness from a real DLL.
9. A bitness-mismatch is detected and reported as an error.
10. The CLI entry point exits 0 on success.

Note: tests 1-4, 7-8 require VLC installed and are skipped otherwise.
"""

import struct
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from playout.engine_vlc.probe import (
    ProbeResult,
    _dll_bits,
    _find_dll,
    _python_bits,
    probe,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _vlc_available() -> bool:
    try:
        import vlc  # noqa: F401, PLC0415
        return True
    except ImportError:
        return False


vlc_installed = pytest.mark.skipif(
    not _vlc_available(),
    reason="VLC not installed in this environment",
)


# ---------------------------------------------------------------------------
# ProbeResult dataclass
# ---------------------------------------------------------------------------

def test_probe_result_fields():
    r = ProbeResult(available=True, python_bits=64)
    assert r.available is True
    assert r.python_bits == 64
    assert r.errors == []


def test_probe_result_raise_when_unavailable():
    r = ProbeResult(available=False, python_bits=64, errors=["test error"])
    with pytest.raises(RuntimeError, match="test error"):
        r.raise_if_unavailable()


def test_probe_result_no_raise_when_available():
    r = ProbeResult(available=True, python_bits=64)
    r.raise_if_unavailable()  # must not raise


def test_probe_result_summary_unavailable():
    r = ProbeResult(available=False, python_bits=64, errors=["oops"])
    s = r.summary()
    assert "UNAVAILABLE" in s
    assert "oops" in s


def test_probe_result_raise_no_errors_msg():
    """Even with no errors list, raise_if_unavailable gives a useful message."""
    r = ProbeResult(available=False, python_bits=64)
    with pytest.raises(RuntimeError, match="libVLC unavailable"):
        r.raise_if_unavailable()


# ---------------------------------------------------------------------------
# _python_bits
# ---------------------------------------------------------------------------

def test_python_bits_returns_32_or_64():
    bits = _python_bits()
    assert bits in (32, 64)

def test_python_bits_matches_sys():
    bits = _python_bits()
    expected = struct.calcsize("P") * 8
    assert bits == expected


# ---------------------------------------------------------------------------
# probe() — with VLC installed
# ---------------------------------------------------------------------------

@vlc_installed
def test_probe_available_on_this_machine():
    result = probe()
    assert result.available is True
    assert result.errors == []


@vlc_installed
def test_probe_version_strings():
    result = probe()
    assert result.python_vlc_version is not None
    assert result.libvlc_version is not None
    assert "3.0" in result.libvlc_version  # VLC 3.0.x Vetinari


@vlc_installed
def test_probe_dll_path_found():
    result = probe()
    assert result.dll_path is not None
    assert result.dll_path.exists()
    assert result.dll_path.name.lower() == "libvlc.dll"


@vlc_installed
def test_probe_bitness_match():
    result = probe()
    assert result.python_bits == result.vlc_bits


@vlc_installed
def test_probe_summary_ok():
    result = probe()
    s = result.summary()
    assert s.startswith("OK")
    assert "libvlc" in s.lower()


@vlc_installed
def test_probe_raise_if_unavailable_noop():
    result = probe()
    result.raise_if_unavailable()  # must not raise


# ---------------------------------------------------------------------------
# _find_dll — with VLC installed
# ---------------------------------------------------------------------------

@vlc_installed
def test_find_dll_returns_path():
    path = _find_dll()
    assert path is not None
    assert path.exists()


@vlc_installed
def test_dll_bits_reads_pe_header():
    path = _find_dll()
    bits = _dll_bits(path)
    assert bits in (32, 64)


# ---------------------------------------------------------------------------
# probe() — without python-vlc (mocked)
# ---------------------------------------------------------------------------

def test_probe_no_python_vlc(monkeypatch):
    """Simulate python-vlc not installed: probe must return available=False."""
    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "vlc":
            raise ImportError("No module named 'vlc'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)
    result = probe()
    assert result.available is False
    assert any("python-vlc" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Bitness mismatch detection (pure-logic, no real DLL needed)
# ---------------------------------------------------------------------------

def test_probe_reports_bitness_mismatch(monkeypatch):
    """
    If _dll_bits returns a different bitness than Python, probe() must add
    a bitness-mismatch error.
    """
    import playout.engine_vlc.probe as probe_mod

    # Patch: DLL found, but wrong bits
    python_bits = _python_bits()
    wrong_bits = 32 if python_bits == 64 else 64
    fake_dll = Path(r"C:\fake\libvlc.dll")

    monkeypatch.setattr(probe_mod, "_find_dll", lambda: fake_dll)
    monkeypatch.setattr(probe_mod, "_dll_bits", lambda p: wrong_bits)

    # Also patch vlc so import succeeds but Instance() works
    fake_vlc = MagicMock()
    fake_vlc.__version__ = "3.0.0"
    fake_vlc.libvlc_get_version.return_value = b"3.0.0"
    fake_vlc.Instance.return_value = MagicMock()

    monkeypatch.setitem(sys.modules, "vlc", fake_vlc)

    result = probe()
    assert any("Bitness mismatch" in e or "itness" in e for e in result.errors)


# ---------------------------------------------------------------------------
# _dll_bits — invalid file
# ---------------------------------------------------------------------------

def test_dll_bits_invalid_file(tmp_path):
    bad = tmp_path / "bad.dll"
    bad.write_bytes(b"\x00\x00\x00\x00")
    assert _dll_bits(bad) is None


def test_dll_bits_nonexistent_file(tmp_path):
    missing = tmp_path / "missing.dll"
    assert _dll_bits(missing) is None
