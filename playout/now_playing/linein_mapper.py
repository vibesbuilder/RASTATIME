"""
T19.2 — LineInEventMapper: map line-in activation events to PlaybackEvent records.

Line-in sources are not driven by the VLC playout engine and therefore do not
produce :class:`~playout.engine_interface.TrackChangedEvent` objects.  Instead,
line-in state changes (activate / deactivate) are signalled explicitly by the
operator or by automation code that controls the routing layer.

``LineInEventMapper`` bridges those signals into the normalized
:class:`~playout.now_playing.playback_event.PlaybackEvent` format and
persists completed events via an injected write function.

Lifecycle
---------
1. Operator activates a line-in source →
   call :meth:`~LineInEventMapper.on_linein_started`.
2. Operator deactivates the source →
   call :meth:`~LineInEventMapper.on_linein_stopped`.
3. The mapper writes a completed :class:`~.PlaybackEvent` with
   ``source_type="linein"`` and the actual ``duration_played``.

Multiple simultaneous line-ins are tracked independently.

Typical production wiring
--------------------------
::

    from playout.now_playing.linein_mapper import LineInEventMapper
    from libretime_api.playback.models import PlaybackEvent as OrmEvent

    mapper = LineInEventMapper(write_fn=OrmEvent.create_from_domain)
    mapper.on_linein_started(
        linein_id="uuid-...",
        name="Drum Kit",
        device_id="stable-device-id",
    )
    # ... later ...
    mapper.on_linein_stopped("uuid-...")

URI convention
--------------
Line-in events use the URI scheme ``linein://<device_id>``.  This ensures
:func:`~playout.now_playing.playback_event.infer_source_type` correctly
classifies the event as ``"linein"`` without needing extra parameters.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class _PendingLineIn:
    """In-progress line-in event — started but not yet stopped."""
    linein_id:  str
    name:       str
    device_id:  str
    event_id:   str
    started_at: datetime


class LineInEventMapper:
    """
    Maps line-in activation / deactivation signals to
    :class:`~playout.now_playing.playback_event.PlaybackEvent` records.

    Parameters
    ----------
    write_fn:
        Callable with signature ``(event: PlaybackEvent) -> None`` that
        persists the domain record.  When *None* (the default) completed
        events are silently skipped — useful during development.
    """

    def __init__(
        self,
        write_fn: Optional[Callable] = None,
    ) -> None:
        self._write_fn = write_fn
        self._pending: Dict[str, _PendingLineIn] = {}

    # ------------------------------------------------------------------
    # Public API — called by routing / operator code
    # ------------------------------------------------------------------

    def on_linein_started(
        self,
        linein_id: str,
        name: str,
        device_id: str,
        started_at: Optional[datetime] = None,
    ) -> None:
        """
        Signal that a line-in source has become active.

        Parameters
        ----------
        linein_id:
            The domain UUID of the line-in source (from ``LineIn.id``).
        name:
            Human-readable label (e.g. ``"Drum Kit"``).
        device_id:
            Stable ID of the audio input endpoint.
        started_at:
            UTC datetime of activation.  Defaults to ``datetime.now(UTC)``
            when *None*.
        """
        if started_at is None:
            started_at = datetime.now(tz=timezone.utc)

        if linein_id in self._pending:
            logger.warning(
                "LineInEventMapper: on_linein_started called for %r "
                "but it is already active — ignoring duplicate start",
                linein_id,
            )
            return

        self._pending[linein_id] = _PendingLineIn(
            linein_id=linein_id,
            name=name,
            device_id=device_id,
            event_id=str(uuid.uuid4()),
            started_at=started_at,
        )
        logger.debug(
            "LineInEventMapper: started line-in %r (%s) at %s",
            name, linein_id, started_at.isoformat(),
        )

    def on_linein_stopped(
        self,
        linein_id: str,
        ended_at: Optional[datetime] = None,
    ) -> None:
        """
        Signal that a line-in source has been deactivated.

        Finalises the pending entry and writes a completed
        :class:`~playout.now_playing.playback_event.PlaybackEvent` via
        the write function.  If *linein_id* was never started (or was
        already stopped), the call is a no-op.

        Parameters
        ----------
        linein_id:
            The domain UUID of the line-in source.
        ended_at:
            UTC datetime of deactivation.  Defaults to ``datetime.now(UTC)``
            when *None*.
        """
        pending = self._pending.pop(linein_id, None)
        if pending is None:
            logger.debug(
                "LineInEventMapper: on_linein_stopped called for unknown "
                "or already-stopped linein_id %r — ignoring",
                linein_id,
            )
            return

        if ended_at is None:
            ended_at = datetime.now(tz=timezone.utc)

        if self._write_fn is None:
            logger.debug(
                "LineInEventMapper: no write_fn configured; "
                "skipping completed line-in event for %r",
                linein_id,
            )
            return

        try:
            from .playback_event import PlaybackEvent  # lazy import
            event = PlaybackEvent(
                event_id=pending.event_id,
                source_type="linein",
                item_id=pending.linein_id,
                title=pending.name,
                artist="",
                uri=f"linein://{pending.device_id}",
                started_at=pending.started_at,
                ended_at=ended_at,
            )
            self._write_fn(event)
            logger.debug(
                "LineInEventMapper: persisted line-in event %s "
                "(name=%r, duration=%.1fs)",
                event.event_id,
                pending.name,
                event.duration_played or 0.0,
            )
        except Exception:  # noqa: BLE001
            logger.exception(
                "LineInEventMapper: failed to persist event for %r",
                linein_id,
            )

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    def active_linein_ids(self) -> list[str]:
        """Return the IDs of all currently active (started but not stopped) line-ins."""
        return list(self._pending.keys())

    def is_active(self, linein_id: str) -> bool:
        """Return *True* if *linein_id* is currently active."""
        return linein_id in self._pending
