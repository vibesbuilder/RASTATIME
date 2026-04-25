"""
QueueManager — centralised queue-decision logic for RASTATIME playout.

This module owns the decision of *what* to play next (show vs. fallback vs.
silence) according to the three-level priority model defined in
``docs/architecture/QUEUE_BEHAVIOR.md`` (T8.1):

    Priority 1 (highest): live input       — reserved (T12+)
    Priority 2:           scheduled show   — managed here
    Priority 3 (lowest):  fallback/filler  — managed here

The ``PlayoutScheduler`` (T8.3) calls ``start_show()`` / ``end_show()`` at the
appropriate wall-clock instants; ``QueueManager`` translates those events into
engine commands, applying the HARD/SOFT transition rules defined in §4 of the
queue-behavior contract.

Threading
---------
All mutations to ``_fallback``, ``_fallback_active``, and ``_content`` are
protected by ``_lock``.  Engine calls are always made *outside* the lock to
avoid deadlocks with engine-internal callbacks.
"""

from __future__ import annotations

import logging
import threading
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from ..engine_interface import PlayoutEngine, PlayoutState, QueueItem, TrackChangedEvent

if TYPE_CHECKING:
    from ..fallback import FallbackQueue
    from ..scheduler import StartMode

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ContentKind
# ---------------------------------------------------------------------------

class ContentKind(str, Enum):
    """
    Logical source of the currently active playout content (intent-based).

    IDLE
        Engine is stopped; no show or fallback is playing.
    SHOW
        A scheduled show was started via ``start_show()``.
    FALLBACK
        Fallback/filler content is playing via ``_trigger_fallback()``.

    The value tracks what ``QueueManager`` *intended* to start, not the raw
    engine state.  For example, immediately after ``end_show()`` and before the
    fallback daemon thread fires, the value is already ``FALLBACK`` if a
    fallback is configured.
    """

    IDLE = "idle"
    SHOW = "show"
    FALLBACK = "fallback"


# ---------------------------------------------------------------------------
# QueueManager
# ---------------------------------------------------------------------------

class QueueManager:
    """
    Central arbiter for RASTATIME playout queue decisions.

    Conforms to the contract in ``docs/architecture/QUEUE_BEHAVIOR.md``
    (T8.1).  The ``PlayoutScheduler`` (T8.3) drives this class at wall-clock
    boundaries; ``QueueManager`` issues ``load_queue()``, ``start()``, and
    ``stop()`` commands to the engine and manages the fallback lifecycle.

    Parameters
    ----------
    engine:
        The playout backend.  Any
        :class:`~playout.engine_interface.PlayoutEngine` implementation is
        accepted (``MockPlayoutEngine`` or ``VlcPlayoutEngine``).
    """

    def __init__(self, engine: PlayoutEngine) -> None:
        self._engine = engine
        self._lock = threading.Lock()

        # Fallback state
        self._fallback: Optional["FallbackQueue"] = None
        self._fallback_active: bool = False

        # Content-kind tracking (intent, not raw engine state)
        self._content: ContentKind = ContentKind.IDLE

        # Register for engine callbacks so we can react to queue exhaustion
        engine.on_track_change(self._on_engine_track_change)

    # ------------------------------------------------------------------
    # Public API — show lifecycle
    # ------------------------------------------------------------------

    def start_show(self, items: List[QueueItem], mode: "StartMode") -> None:
        """
        Start a scheduled show.

        Parameters
        ----------
        items:
            Ordered track list for the show.  Must not be empty.
        mode:
            ``StartMode.HARD`` or ``StartMode.SOFT``
            (see ``QUEUE_BEHAVIOR.md`` §4.1).

        Raises
        ------
        ValueError
            If *items* is empty.
        """
        from ..scheduler import StartMode  # local import — avoids circular dep

        if not items:
            raise ValueError("start_show() requires at least one item")

        if mode == StartMode.HARD:
            self._hard_start(items)
        else:
            self._soft_start(items)

    def end_show(self) -> None:
        """
        Terminate the current show immediately (hard stop).

        Per ``QUEUE_BEHAVIOR.md`` §4.2, ``engine.stop()`` is always a hard
        stop regardless of the show's original ``start_mode``.  If a fallback
        is configured, it starts automatically in a daemon thread.
        """
        self._engine.stop()

        with self._lock:
            fb = self._fallback
            if fb and not fb.is_empty():
                self._fallback_active = True
                self._content = ContentKind.FALLBACK
            else:
                self._content = ContentKind.IDLE

        if fb and not fb.is_empty():
            threading.Thread(target=self._trigger_fallback, daemon=True).start()
            logger.info("Fallback triggered after show ended")

    # ------------------------------------------------------------------
    # Public API — fallback configuration
    # ------------------------------------------------------------------

    def set_fallback(self, fallback: "FallbackQueue") -> None:
        """
        Configure filler content that plays when no show is active.

        The new configuration takes effect at the next ``_trigger_fallback()``
        call (i.e. the next ``end_show()`` or the next looping restart).
        Any currently playing fallback items continue until the current loop
        cycle ends.

        Parameters
        ----------
        fallback:
            A :class:`~playout.fallback.FallbackQueue` holding the filler
            items.  Must not be empty (enforced by ``FallbackQueue``).
        """
        with self._lock:
            self._fallback = fallback
        logger.debug("Fallback configured: %r", fallback)

    def clear_fallback(self) -> None:
        """
        Remove the fallback configuration and stop auto-restart.

        The currently playing fallback item finishes naturally (the engine's
        queue still holds it) but the fallback does **not** restart.
        Per ``QUEUE_BEHAVIOR.md`` §5, ``_fallback_active`` is cleared
        immediately so the next track-change event does not trigger a restart.
        """
        with self._lock:
            self._fallback = None
            self._fallback_active = False
        logger.debug("Fallback cleared")

    def fallback_is_active(self) -> bool:
        """Return *True* if the fallback flag is currently set."""
        with self._lock:
            return self._fallback_active

    # ------------------------------------------------------------------
    # Public API — state query
    # ------------------------------------------------------------------

    def active_content(self) -> ContentKind:
        """
        Return the logical kind of content currently active (intent-based).

        See :class:`ContentKind` for the meaning of each value.
        """
        with self._lock:
            return self._content

    # ------------------------------------------------------------------
    # Internal — start-mode implementations
    # ------------------------------------------------------------------

    def _hard_start(self, items: List[QueueItem]) -> None:
        """
        Stop immediately, replace queue, start (QUEUE_BEHAVIOR.md §4.1 HARD).

        Sets ``_fallback_active = False`` *before* calling ``load_queue()`` to
        prevent the engine's track-change callback from spuriously restarting
        the fallback during the brief STOPPED state between show items.
        """
        with self._lock:
            self._fallback_active = False
            self._content = ContentKind.SHOW
        self._engine.load_queue(items)
        self._engine.start()
        logger.debug("Hard-started show (%d item(s))", len(items))

    def _soft_start(self, items: List[QueueItem]) -> None:
        """
        Splice show items after current track; fall back to HARD if stopped.

        Per ``QUEUE_BEHAVIOR.md`` §4.1 SOFT: if the engine is already STOPPED,
        behave exactly like HARD mode.  Otherwise clear pending queue items
        (keeping the current track) and append the show items so they play
        immediately after the current track ends.
        """
        with self._lock:
            self._fallback_active = False
            self._content = ContentKind.SHOW

        state = self._engine.get_state()
        if state == PlayoutState.STOPPED:
            logger.debug("Soft-start: engine stopped, using HARD path")
            self._engine.load_queue(items)
            self._engine.start()
        else:
            self._engine.clear_queue()
            for item in items:
                self._engine.append(item)
            logger.debug(
                "Soft-start: spliced %d item(s) after current track", len(items)
            )

    # ------------------------------------------------------------------
    # Internal — fallback lifecycle
    # ------------------------------------------------------------------

    def _trigger_fallback(self) -> None:
        """
        Load the fallback queue and start playback.

        Always called in a daemon thread — never on the engine's callback
        thread and never while holding ``_lock``.
        """
        with self._lock:
            fb = self._fallback
        if not fb or fb.is_empty():
            return
        try:
            self._engine.load_queue(fb.items)
            self._engine.start()
            logger.info("Fallback playback started (%d item(s))", len(fb))
        except Exception:  # noqa: BLE001
            logger.exception("Error starting fallback playback")

    def _on_engine_track_change(self, event: TrackChangedEvent) -> None:
        """
        Engine callback: handle queue-exhaustion events.

        Fires whenever the current track changes.

        * ``current_item`` is not None → a new track started; nothing to do.
        * ``current_item`` is None (queue exhausted):

          - Fallback active + ``loop=True``:  restart fallback from the top
            (``QUEUE_BEHAVIOR.md`` §4.4).
          - Fallback active + ``loop=False``: non-looping fallback played
            once and stopped naturally; mark content as IDLE (§4.5).
          - Fallback not active: ignore.
        """
        if event.current_item is not None:
            return  # a new track started — nothing to do

        with self._lock:
            active = self._fallback_active
            fb = self._fallback

        if not active or not fb:
            return

        if fb.loop and not fb.is_empty():
            # Restart the fallback list from the top
            threading.Thread(target=self._trigger_fallback, daemon=True).start()
        else:
            # Non-looping fallback exhausted — engine stopped naturally
            with self._lock:
                self._content = ContentKind.IDLE
