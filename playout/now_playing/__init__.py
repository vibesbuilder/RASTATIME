"""
playout.now_playing — in-process now-playing state and history logger.

Public API
----------
``NowPlayingState``
    Tracks which ``QueueItem`` is on air right now.

``NowPlayingEntry``
    Snapshot returned by ``NowPlayingState.get()``.

``PlayoutHistoryLogger``
    Ring-buffer of completed track plays.

``HistoryEntry``
    One record in the history log.

``connect_engine(engine, state, logger)``
    Convenience function to wire state and logger to an engine's
    ``on_track_change`` callback in one call.

Module-level singletons
-----------------------
``default_state`` and ``default_logger`` are process-level singletons
intended for single-process deployments (e.g. dev mode, tests, or a
combined playout + API server).  Multi-process deployments should create
their own instances and use a shared store (Redis, etc.) as the transport.
"""

from ._history import HistoryEntry, PlayoutHistoryLogger
from ._persister import PlaybackEventPersister
from ._state import NowPlayingEntry, NowPlayingState
from .linein_mapper import LineInEventMapper
from .playback_event import PlaybackEvent, PlaybackSourceType, infer_source_type

from ..engine_interface import PlayoutEngine as _PlayoutEngine

__all__ = [
    "NowPlayingEntry",
    "NowPlayingState",
    "HistoryEntry",
    "PlayoutHistoryLogger",
    "PlaybackEventPersister",
    "LineInEventMapper",
    "PlaybackEvent",
    "PlaybackSourceType",
    "infer_source_type",
    "connect_engine",
    "default_state",
    "default_logger",
]

# ---------------------------------------------------------------------------
# Module-level singletons (single-process / dev use)
# ---------------------------------------------------------------------------

default_state: NowPlayingState = NowPlayingState()
default_logger: PlayoutHistoryLogger = PlayoutHistoryLogger()


def connect_engine(
    engine: _PlayoutEngine,
    state: NowPlayingState = default_state,
    logger: PlayoutHistoryLogger = default_logger,
) -> None:
    """
    Wire *state* and *logger* to *engine*'s ``on_track_change`` callback.

    Parameters
    ----------
    engine:
        Any ``PlayoutEngine`` implementation (``VlcPlayoutEngine``,
        ``MockPlayoutEngine``, etc.).
    state:
        ``NowPlayingState`` to update on each track change.
        Defaults to the module-level ``default_state`` singleton.
    logger:
        ``PlayoutHistoryLogger`` to update on each track change.
        Defaults to the module-level ``default_logger`` singleton.
    """
    engine.on_track_change(state.on_track_change)
    engine.on_track_change(logger.on_track_change)
