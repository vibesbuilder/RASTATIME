"""
IcyMetadataPusher — real-time metadata update for Icecast streams.

Uses the Icecast HTTP admin API to push now-playing metadata whenever a
new track starts.  This is the recommended method for all stream types:

* MP3 / SHOUTcast: Icecast accepts the ``/admin/metadata`` endpoint and
  translates it to ICY in-stream metadata for listeners.
* OGG Vorbis / Opus: Icecast also supports metadata injection via this
  endpoint even for OGG streams (the header is re-sent on the next segment
  boundary).

Why HTTP API instead of libshout ``shout_set_metadata()``?
----------------------------------------------------------
libshout's ``shout_set_metadata()`` is a C function not directly exposed
by python-vlc.  The Icecast HTTP API achieves the same result without
any ctypes wrangling and is trivially unit-testable via an injectable
HTTP callable.

Endpoint reference
------------------
``GET /admin/metadata?mount=<mount>&mode=updinfo&song=<url-encoded-title>``
with HTTP Basic authentication (admin user / admin password).

ICY metadata constraints (from the Shoutcast / ICY spec)
---------------------------------------------------------
* Maximum useful length: 255 bytes (× 16 = 4080 raw bytes in the ICY frame,
  but most clients truncate display at ~255 characters).
* Unicode: UTF-8 encoded; Icecast ≥ 2.4 handles it correctly.
* When the engine is idle (fallback or silence), metadata should be set to
  the station name, not left empty.
"""

from __future__ import annotations

import logging
import urllib.parse
import urllib.request
from base64 import b64encode
from typing import Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .interface import StreamOutput

logger = logging.getLogger(__name__)

# Maximum ICY metadata length (bytes, UTF-8 encoded)
_ICY_MAX_BYTES = 255

# Type alias for the injectable HTTP getter
# Signature: (url: str, auth_header: str) -> tuple[int, str]  (status, body)
HttpGetter = Callable[[str, str], tuple[int, str]]


def _default_http_get(url: str, auth_header: str) -> tuple[int, str]:
    """
    Default HTTP GET implementation using urllib.

    Returns (status_code, response_body).
    """
    req = urllib.request.Request(url, headers={"Authorization": auth_header})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, str(exc.reason)
    except OSError as exc:
        # Connection refused, timeout, etc.
        return 0, str(exc)


class IcyMetadataPusher:
    """
    Pushes now-playing metadata to an Icecast server via the HTTP admin API.

    Parameters
    ----------
    output:
        The :class:`~streams.egress.interface.StreamOutput` configuration
        (host, port, mount, username, password are read from here).
    idle_title:
        Metadata title to push when the engine is idle (no track playing).
        Defaults to ``"RASTATIME"``.
    http_get:
        Injectable HTTP GET callable — signature
        ``(url: str, auth_header: str) -> (status: int, body: str)``.
        Defaults to ``urllib``-based implementation.
        Use a mock in unit tests.
    """

    def __init__(
        self,
        output: "StreamOutput",
        idle_title: str = "RASTATIME",
        http_get: Optional[HttpGetter] = None,
    ) -> None:
        self._output = output
        self._idle_title = idle_title
        self._http_get: HttpGetter = http_get or _default_http_get

        # Pre-compute auth header (Basic auth with Icecast admin credentials)
        user = output.username or "admin"
        password = output.password or ""
        credentials = b64encode(f"{user}:{password}".encode()).decode()
        self._auth_header = f"Basic {credentials}"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def push(self, title: str, artist: str = "") -> bool:
        """
        Push track metadata to Icecast.

        Formats ``artist`` and ``title`` as ``"Artist - Title"``
        (or just ``"Title"`` if artist is blank), truncates to
        :data:`_ICY_MAX_BYTES` bytes, and sends to Icecast.

        Parameters
        ----------
        title:
            Track title (required; may be empty string to trigger idle label).
        artist:
            Artist name (optional).

        Returns
        -------
        bool
            ``True`` if Icecast returned HTTP 200; ``False`` otherwise.
            Failures are logged at WARNING level but not re-raised.
        """
        song = self._format_song(title, artist)
        return self._send(song)

    def push_idle(self) -> bool:
        """
        Push the configured idle title (station name) to Icecast.

        Called when no track is playing (end of show, fallback silence).
        """
        return self._send(self._idle_title)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _format_song(self, title: str, artist: str) -> str:
        """
        Format artist + title as a single ICY song string.

        Rules
        -----
        * Non-empty artist → ``"Artist - Title"``
        * Empty artist → ``"Title"``
        * Result truncated to :data:`_ICY_MAX_BYTES` bytes (UTF-8).
        * Empty title → returns :attr:`_idle_title`.
        """
        if not title:
            return self._idle_title

        song = f"{artist} - {title}" if artist else title

        # Truncate to ICY byte limit while preserving valid UTF-8
        encoded = song.encode("utf-8")
        if len(encoded) > _ICY_MAX_BYTES:
            # Truncate bytes then decode back, ignoring the last partial char
            song = encoded[:_ICY_MAX_BYTES].decode("utf-8", errors="ignore")

        return song

    def _send(self, song: str) -> bool:
        """
        Send the metadata update to Icecast via HTTP GET.

        Endpoint::

            GET http://host:port/admin/metadata
                ?mount=<mount>&mode=updinfo&song=<url-encoded-song>

        Returns True on HTTP 200, False otherwise.
        """
        mount = self._output.mount
        if not mount.startswith("/"):
            mount = f"/{mount}"

        params = urllib.parse.urlencode({
            "mount": mount,
            "mode": "updinfo",
            "song": song,
        })
        url = f"http://{self._output.url}:{self._output.port}/admin/metadata?{params}"

        status, body = self._http_get(url, self._auth_header)

        if status == 200:
            logger.debug(
                "Metadata pushed to %s%s: %r", self._output.url, mount, song
            )
            return True

        logger.warning(
            "Metadata push failed for %s%s: HTTP %d — %s",
            self._output.url, mount, status, body[:120],
        )
        return False
