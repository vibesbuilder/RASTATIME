"""
IcecastHealthChecker — Icecast mount health probe (UC-O8).

T10.4 decision note
-------------------
T9.2 capability matrix (Q1–Q8b) confirmed that libVLC's shout module is
sufficient for Icecast streaming on Windows.  The condition in T10.4
("add Icecast option if T9.2 showed libVLC insufficient") is therefore NOT
met — libVLC IS the Icecast source client.  The watchdog-based reconnect
introduced in T10.1 (LibVlcEgressManager) addresses the Q8a limitation
(shout does not fail fast on Windows).

What this module provides
-------------------------
:class:`IcecastHealthChecker` was previously implemented as a private
``_default_health_checker`` function inside ``_vlc_manager.py``.  T10.4
promotes it to a proper, independently testable class so that:

* Unit tests can mock ``urllib.request.urlopen`` and verify behaviour
  for the full range of Icecast JSON shapes (single source, source list,
  empty, network error, malformed JSON).
* The timeout is configurable.
* The callable interface (``__call__``) satisfies the ``HealthChecker``
  protocol used by :class:`~._vlc_manager.LibVlcEgressManager`.

Icecast /status-json.xsl schema
---------------------------------
The relevant fragment of the Icecast status JSON::

    {
      "icestats": {
        "source": [                  # list when >1 source, dict when =1
          {
            "listenurl": "http://ice.example.com:8000/live",
            ...
          }
        ]
      }
    }

A mount ``/live`` is considered *active* when any source's ``listenurl``
ends with ``/live``.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .interface import StreamOutput

logger = logging.getLogger(__name__)


class IcecastHealthChecker:
    """
    Poll an Icecast ``/status-json.xsl`` endpoint to verify that the source
    client (libVLC shout module) is still connected to a given mount.

    Used by :class:`~._vlc_manager.LibVlcEgressManager` as the default
    ``health_checker`` callable in the watchdog reconnect loop (UC-O8).

    Parameters
    ----------
    timeout:
        HTTP request timeout in seconds (default 5 s).  Applies to both
        connection and read phases (passed to ``urllib.request.urlopen``).

    Injectable for tests
    --------------------
    In unit tests, inject a plain lambda instead::

        mgr = LibVlcEgressManager(engine, health_checker=lambda o: True)
    """

    def __init__(self, timeout: float = 5.0) -> None:
        self._timeout = timeout

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def check(self, output: "StreamOutput") -> bool:
        """
        Return ``True`` if *output*'s mount has an active source on Icecast.

        Polls ``http://<output.url>:<output.port>/status-json.xsl`` and
        checks whether any ``icestats.source`` entry's ``listenurl`` ends
        with the normalised mount path.

        Returns ``False`` on any network error, JSON parse failure, or when
        the mount is not present.

        Parameters
        ----------
        output:
            The :class:`~.interface.StreamOutput` whose Icecast mount to
            check.  Only ``url``, ``port``, and ``mount`` are used.
        """
        mount = output.mount
        if not mount.startswith("/"):
            mount = f"/{mount}"

        url = f"http://{output.url}:{output.port}/status-json.xsl"
        try:
            with urllib.request.urlopen(url, timeout=self._timeout) as resp:
                data = json.loads(resp.read())
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "Icecast health check failed for %r (%s): %s",
                getattr(output, "id", output),
                url,
                exc,
            )
            return False

        sources = data.get("icestats", {}).get("source", [])
        # Icecast returns a dict (not list) when there is exactly 1 source
        if isinstance(sources, dict):
            sources = [sources]
        for src in sources:
            if src.get("listenurl", "").endswith(mount):
                return True
        return False

    def __call__(self, output: "StreamOutput") -> bool:
        """Callable interface — delegates to :meth:`check`."""
        return self.check(output)

    def __repr__(self) -> str:
        return f"IcecastHealthChecker(timeout={self._timeout!r})"
