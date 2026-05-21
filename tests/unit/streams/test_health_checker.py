"""
T10.4 — IcecastHealthChecker unit tests.

Verifies the Icecast ``/status-json.xsl`` health probe without a real server.
All HTTP calls are intercepted via ``unittest.mock.patch``.

Test inventory
--------------
Mount-active detection (4):
 1.  Single-source dict with matching listenurl → True.
 2.  Multi-source list with one matching listenurl → True.
 3.  Source list where no listenurl matches the mount → False.
 4.  Empty source list → False.

Error handling (2):
 5.  Network error (urllib raises OSError) → False (no exception propagated).
 6.  Malformed JSON response → False (no exception propagated).

Mount normalisation (1):
 7.  Mount without leading "/" gets "/" prepended before comparison.

Callable interface (1):
 8.  __call__ delegates to check() — checker(output) == checker.check(output).
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from streams._types import StreamProtocol
from streams.egress._health import IcecastHealthChecker
from streams.egress.interface import StreamOutput


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _output(mount: str = "/live") -> StreamOutput:
    return StreamOutput(
        id="o1",
        name="Test",
        protocol=StreamProtocol.ICECAST,
        url="ice.local",
        port=8000,
        mount=mount,
        username="source",
        password="pw",
        codec="mp3",
    )


def _fake_resp(data: dict) -> MagicMock:
    """Mock urllib.request.urlopen return value (context manager)."""
    resp = MagicMock()
    resp.read.return_value = json.dumps(data).encode()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def _icecast_json(sources) -> dict:
    """Build a minimal Icecast status JSON with the given source(s)."""
    return {"icestats": {"source": sources}}


def _listenurl(mount: str = "/live", host: str = "ice.local", port: int = 8000) -> str:
    return f"http://{host}:{port}{mount}"


# ---------------------------------------------------------------------------
# 1–4  Mount-active detection
# ---------------------------------------------------------------------------

def test_single_source_dict_matching_mount_returns_true():
    """Icecast returns a dict (not list) when there is exactly one source."""
    checker = IcecastHealthChecker()
    data = _icecast_json({"listenurl": _listenurl("/live")})

    with patch("urllib.request.urlopen", return_value=_fake_resp(data)):
        assert checker.check(_output("/live")) is True


def test_multi_source_list_one_match_returns_true():
    checker = IcecastHealthChecker()
    data = _icecast_json([
        {"listenurl": _listenurl("/other")},
        {"listenurl": _listenurl("/live")},
    ])

    with patch("urllib.request.urlopen", return_value=_fake_resp(data)):
        assert checker.check(_output("/live")) is True


def test_no_matching_mount_returns_false():
    checker = IcecastHealthChecker()
    data = _icecast_json([
        {"listenurl": _listenurl("/stream1")},
        {"listenurl": _listenurl("/stream2")},
    ])

    with patch("urllib.request.urlopen", return_value=_fake_resp(data)):
        assert checker.check(_output("/live")) is False


def test_empty_source_list_returns_false():
    checker = IcecastHealthChecker()
    data = _icecast_json([])

    with patch("urllib.request.urlopen", return_value=_fake_resp(data)):
        assert checker.check(_output("/live")) is False


# ---------------------------------------------------------------------------
# 5–6  Error handling
# ---------------------------------------------------------------------------

def test_network_error_returns_false_no_exception():
    checker = IcecastHealthChecker()

    with patch("urllib.request.urlopen", side_effect=OSError("Connection refused")):
        result = checker.check(_output("/live"))  # must not raise

    assert result is False


def test_malformed_json_returns_false_no_exception():
    checker = IcecastHealthChecker()

    bad_resp = MagicMock()
    bad_resp.read.return_value = b"<html>not json</html>"
    bad_resp.__enter__ = lambda s: s
    bad_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=bad_resp):
        result = checker.check(_output("/live"))  # must not raise

    assert result is False


# ---------------------------------------------------------------------------
# 7  Mount normalisation
# ---------------------------------------------------------------------------

def test_mount_without_leading_slash_is_normalised():
    """Mount "live" (no slash) must compare as "/live"."""
    checker = IcecastHealthChecker()
    data = _icecast_json({"listenurl": _listenurl("/live")})

    with patch("urllib.request.urlopen", return_value=_fake_resp(data)):
        # Pass mount without leading slash
        assert checker.check(_output("live")) is True


# ---------------------------------------------------------------------------
# 8  Callable interface
# ---------------------------------------------------------------------------

def test_call_delegates_to_check():
    """checker(output) must equal checker.check(output)."""
    checker = IcecastHealthChecker()
    data = _icecast_json({"listenurl": _listenurl("/live")})

    with patch("urllib.request.urlopen", return_value=_fake_resp(data)):
        via_call = checker(_output("/live"))

    with patch("urllib.request.urlopen", return_value=_fake_resp(data)):
        via_check = checker.check(_output("/live"))

    assert via_call == via_check
    assert via_call is True
