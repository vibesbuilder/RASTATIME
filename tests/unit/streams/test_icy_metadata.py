"""
T10.2 — IcyMetadataPusher unit tests.

Verifies the Icecast HTTP metadata push mechanism without requiring a real
Icecast server.  All HTTP calls are intercepted via the injectable
``http_get`` parameter.

Test inventory
--------------
Song formatting (6):
 1.  artist + title → "Artist - Title".
 2.  Empty artist → "Title" (no leading " - ").
 3.  Empty title → idle_title returned.
 4.  Both empty → idle_title returned.
 5.  Long UTF-8 string truncated to 255 bytes (no partial code point).
 6.  Multi-byte UTF-8 boundary preserved after truncation.

push() HTTP semantics (6):
 7.  HTTP 200 → push() returns True.
 8.  HTTP 401 → push() returns False.
 9.  Network error (status 0) → push() returns False (no exception).
10.  URL contains /admin/metadata with correct mount, mode, and song params.
11.  Auth header is HTTP Basic with base64-encoded user:password.
12.  Custom username / password are encoded correctly.

push_idle() (2):
13.  push_idle() sends idle_title to Icecast.
14.  push_idle() returns True on HTTP 200.

Mount normalisation (2):
15.  Mount without leading "/" gets "/" prepended in the URL.
16.  Mount with leading "/" is not doubled.

Default auth (1):
17.  Blank username defaults to "admin" in Basic auth header.
"""

import base64
import urllib.parse
from typing import Optional

import pytest

from streams.egress import StreamOutput
from streams.egress._metadata import IcyMetadataPusher
from streams._types import StreamProtocol


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _output(
    url: str = "ice.local",
    port: int = 8000,
    mount: str = "/live",
    username: str = "admin",
    password: str = "hackme",
) -> StreamOutput:
    return StreamOutput(
        id="o1",
        name="Test",
        protocol=StreamProtocol.ICECAST,
        url=url,
        port=port,
        mount=mount,
        username=username,
        password=password,
        codec="mp3",
    )


class _FakeHttp:
    """Records HTTP calls and returns a configurable (status, body) pair."""

    def __init__(self, status: int = 200, body: str = "OK") -> None:
        self.calls: list[tuple[str, str]] = []   # (url, auth_header)
        self._status = status
        self._body = body

    def __call__(self, url: str, auth_header: str) -> tuple[int, str]:
        self.calls.append((url, auth_header))
        return self._status, self._body


def _pusher(
    output: Optional[StreamOutput] = None,
    idle_title: str = "RASTATIME",
    http: Optional[_FakeHttp] = None,
) -> tuple[IcyMetadataPusher, _FakeHttp]:
    http = http or _FakeHttp()
    out = output or _output()
    return IcyMetadataPusher(out, idle_title=idle_title, http_get=http), http


# ---------------------------------------------------------------------------
# 1–6  Song formatting
# ---------------------------------------------------------------------------

def test_format_artist_and_title():
    p, http = _pusher()
    p.push("Summer Nights", "DJ Cool")
    url, _ = http.calls[0]
    qs = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
    assert qs["song"] == ["DJ Cool - Summer Nights"]


def test_format_empty_artist_no_leading_dash():
    p, http = _pusher()
    p.push("Only Title", "")
    url, _ = http.calls[0]
    qs = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
    assert qs["song"] == ["Only Title"]


def test_format_empty_title_returns_idle_title():
    p, http = _pusher(idle_title="Radio XYZ")
    p.push("", "Some Artist")
    url, _ = http.calls[0]
    qs = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
    assert qs["song"] == ["Radio XYZ"]


def test_format_both_empty_returns_idle_title():
    p, http = _pusher(idle_title="Station Name")
    p.push("", "")
    url, _ = http.calls[0]
    qs = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
    assert qs["song"] == ["Station Name"]


def test_long_ascii_string_truncated_to_255_bytes():
    p, http = _pusher()
    long_title = "A" * 300  # 300 ASCII chars > 255 bytes
    p.push(long_title)
    url, _ = http.calls[0]
    qs = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
    song = qs["song"][0]
    assert len(song.encode("utf-8")) <= 255


def test_multibyte_utf8_truncation_preserves_boundary():
    """
    A string with multi-byte chars must not be cut mid-codepoint.
    '©' is 2 bytes in UTF-8; 'é' is 2 bytes; '€' is 3 bytes.
    """
    p, http = _pusher()
    # Build a string where the 255th byte lands inside a multi-byte char
    # 126 ASCII + 1 '€' (3 bytes) = 129 bytes; repeat until > 255 bytes
    title = "x" * 84 + "€" * 60  # 84 + 180 = 264 bytes
    p.push(title)
    url, _ = http.calls[0]
    qs = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
    song_bytes = qs["song"][0].encode("utf-8")
    # Must be valid UTF-8 (no broken code point) and ≤ 255 bytes
    assert len(song_bytes) <= 255
    song_bytes.decode("utf-8")  # must not raise


# ---------------------------------------------------------------------------
# 7–12  push() HTTP semantics
# ---------------------------------------------------------------------------

def test_push_http_200_returns_true():
    p, http = _pusher(http=_FakeHttp(status=200))
    assert p.push("Title") is True


def test_push_http_401_returns_false():
    p, http = _pusher(http=_FakeHttp(status=401, body="Unauthorized"))
    assert p.push("Title") is False


def test_push_network_error_returns_false():
    p, http = _pusher(http=_FakeHttp(status=0, body="Connection refused"))
    assert p.push("Title") is False


def test_push_url_contains_correct_params():
    p, http = _pusher(_output(mount="/main"))
    p.push("My Track", "Artist X")
    url, _ = http.calls[0]

    parsed = urllib.parse.urlsplit(url)
    qs = urllib.parse.parse_qs(parsed.query)

    assert parsed.path == "/admin/metadata"
    assert qs.get("mount") == ["/main"]
    assert qs.get("mode") == ["updinfo"]
    assert "song" in qs


def test_push_url_host_and_port():
    p, http = _pusher(_output(url="stream.radio.org", port=7654))
    p.push("Track")
    url, _ = http.calls[0]
    assert "stream.radio.org:7654" in url


def test_push_basic_auth_header_format():
    """Auth header is 'Basic base64(user:pass)'."""
    p, http = _pusher(_output(username="admin", password="secret"))
    p.push("Track")
    _, auth = http.calls[0]

    assert auth.startswith("Basic ")
    decoded = base64.b64decode(auth[len("Basic "):]).decode()
    assert decoded == "admin:secret"


def test_push_custom_credentials_encoded():
    p, http = _pusher(_output(username="dj", password="pa$$w0rd"))
    p.push("Track")
    _, auth = http.calls[0]
    decoded = base64.b64decode(auth[len("Basic "):]).decode()
    assert decoded == "dj:pa$$w0rd"


# ---------------------------------------------------------------------------
# 13–14  push_idle()
# ---------------------------------------------------------------------------

def test_push_idle_sends_idle_title():
    p, http = _pusher(idle_title="Cool FM")
    p.push_idle()
    url, _ = http.calls[0]
    qs = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
    assert qs["song"] == ["Cool FM"]


def test_push_idle_returns_true_on_200():
    p, http = _pusher(http=_FakeHttp(status=200))
    assert p.push_idle() is True


# ---------------------------------------------------------------------------
# 15–16  Mount normalisation
# ---------------------------------------------------------------------------

def test_mount_without_slash_gets_prepended():
    p, http = _pusher(_output(mount="live"))
    p.push("Track")
    url, _ = http.calls[0]
    qs = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
    assert qs["mount"] == ["/live"]


def test_mount_with_slash_not_doubled():
    p, http = _pusher(_output(mount="/stream"))
    p.push("Track")
    url, _ = http.calls[0]
    qs = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
    assert qs["mount"] == ["/stream"]
    assert "//stream" not in url


# ---------------------------------------------------------------------------
# 17  Default auth
# ---------------------------------------------------------------------------

def test_blank_username_defaults_to_admin():
    p, http = _pusher(_output(username="", password="pw"))
    p.push("Track")
    _, auth = http.calls[0]
    decoded = base64.b64decode(auth[len("Basic "):]).decode()
    assert decoded.startswith("admin:")
