"""
T19.2 — PlaybackEventPersister: bridge from in-memory history to the DB.

``PlaybackEventPersister`` registers as a completion subscriber on a
:class:`~.PlayoutHistoryLogger` and converts each completed
:class:`~.HistoryEntry` into a :class:`~.PlaybackEvent` domain record,
then calls a configurable *write function* to persist it.

The write function is injected at construction time so the persister has
no hard dependency on Django or the ORM layer — it can be tested in
isolation with a simple list-append stub.

Typical production wiring
--------------------------
::

    from playout.now_playing import default_logger
    from playout.now_playing._persister import PlaybackEventPersister
    from libretime_api.playback.models import PlaybackEvent as OrmEvent

    persister = PlaybackEventPersister(write_fn=OrmEvent.create_from_domain)
    persister.attach(default_logger)

    # … engine.on_track_change(default_logger.on_track_change) …
    # Every time a track finishes, persister writes a row to DB.

No-op usage (development / fallback)
--------------------------------------
::

    persister = PlaybackEventPersister()   # write_fn is None → silent skip

Thread safety
-------------
The ``_on_completed`` callback is invoked on the engine's event thread.
The write function must be safe to call from any thread (Django's ORM
methods are thread-safe when called with per-thread DB connections).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from ._history import HistoryEntry, PlayoutHistoryLogger
    from .playback_event import PlaybackEvent

logger = logging.getLogger(__name__)


class PlaybackEventPersister:
    """
    Subscribes to :class:`~.PlayoutHistoryLogger` completion events and
    persists each completed :class:`~.HistoryEntry` as a
    :class:`~.PlaybackEvent` via an injected write function.

    Parameters
    ----------
    write_fn:
        Callable with signature ``(event: PlaybackEvent) -> None`` that
        persists the domain record.  When *None* (the default) completed
        entries are silently skipped — useful during development or when
        the DB is not yet connected.
    """

    def __init__(
        self,
        write_fn: Optional[Callable[["PlaybackEvent"], None]] = None,
    ) -> None:
        self._write_fn = write_fn

    # ------------------------------------------------------------------
    # Wiring
    # ------------------------------------------------------------------

    def attach(self, history_logger: "PlayoutHistoryLogger") -> None:
        """
        Register this persister as a completion subscriber on *history_logger*.

        After ``attach()``, every completed :class:`~.HistoryEntry` produced
        by the logger will be converted and persisted (if a write function
        is configured).

        Parameters
        ----------
        history_logger:
            The :class:`~.PlayoutHistoryLogger` whose completions to
            subscribe to.  Typically ``playout.now_playing.default_logger``.
        """
        history_logger.on_entry_completed(self._on_completed)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_completed(self, entry: "HistoryEntry") -> None:
        """
        Called by the history logger when a :class:`~.HistoryEntry` is
        finalised.  Converts the entry to a :class:`~.PlaybackEvent` and
        invokes the write function.

        Exceptions from the write function are caught and logged so that
        a DB error never disrupts playout.
        """
        if self._write_fn is None:
            logger.debug(
                "PlaybackEventPersister: no write_fn configured; "
                "skipping history entry for item %r",
                getattr(entry.item, "id", "?"),
            )
            return

        try:
            from .playback_event import PlaybackEvent  # lazy — no circular dep
            event = PlaybackEvent.from_history_entry(entry)
            self._write_fn(event)
            logger.debug(
                "PlaybackEventPersister: persisted event %s "
                "(source=%s, duration=%.1fs)",
                event.event_id,
                event.source_type,
                event.duration_played or 0.0,
            )
        except Exception:  # noqa: BLE001
            logger.exception(
                "PlaybackEventPersister: failed to persist history entry "
                "for item %r",
                getattr(entry.item, "id", "?"),
            )
