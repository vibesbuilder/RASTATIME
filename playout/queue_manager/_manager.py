"""
QueueManager — centralised queue-decision logic for RASTATIME playout.

This module owns the decision of *what* to play next (show vs. fallback vs.
silence vs. live line-in) according to the four-level priority model defined
in ``docs/architecture/QUEUE_BEHAVIOR.md`` (T8.1):

    Priority 1 (highest): live line-in     — T15.2 (this file)
    Priority 2:           scheduled show   — managed here
    Priority 3:           fallback/filler  — managed here
    Priority 4 (lowest):  silence/idle     — managed here

The ``PlayoutScheduler`` (T8.3) calls ``start_show()`` / ``end_show()`` at the
appropriate wall-clock instants; ``QueueManager`` translates those events into
engine commands, applying the HARD/SOFT transition rules defined in §4 of the
queue-behavior contract.

Line-in integration (T15.2)
---------------------------
``go_to_line_in(linein, runtime)`` activates Priority-1 source selection:

1. Any active line-in is deactivated first.
2. ``_fallback_active`` is cleared **before** ``engine.stop()`` so that the
   engine's ``on_track_change`` callback (which fires during ``stop()``)
   does not spuriously restart the fallback.
3. ``runtime.activate(linein)`` is called; on failure the system falls back
   to FALLBACK (if configured) or IDLE — it never crashes.

``end_line_in()`` restores normal playout after a line-in session:

* The line-in is deactivated via its runtime.
* If a fallback is configured, it starts in a daemon thread.
* Otherwise the engine stays stopped (IDLE).

Both methods are safe to call from any thread.

Threading
---------
All mutations to ``_fallback``, ``_fallback_active``, ``_content``,
``_active_linein_id``, and ``_active_linein_runtime`` are protected by
``_lock``.  Engine calls and runtime calls are always made *outside* the lock
to avoid deadlocks with engine-internal callbacks.
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
    from audio.linein.domain import LineIn as LineInDomain
    from audio.linein._runtime import ActivationResult, LineInRuntime

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ContentKind
# ---------------------------------------------------------------------------

class ContentKind(str, Enum):
    """
    Logical source of the currently active playout content (intent-based).

    IDLE
        Engine is stopped; no show, fallback, or line-in is active.
    SHOW
        A scheduled show was started via ``start_show()``.
    FALLBACK
        Fallback/filler content is playing via ``_trigger_fallback()``.
    LINE_IN
        A live line-in source is active at Priority 1 (T15.2).
        The engine is stopped; audio flows through the
        :class:`~audio.linein._runtime.LineInRuntime`.

    The value tracks what ``QueueManager`` *intended* to start, not the raw
    engine state.
    """

    IDLE     = "idle"
    SHOW     = "show"
    FALLBACK = "fallback"
    LINE_IN  = "line_in"


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

    Line-in integration (T15.2) is provided via :meth:`go_to_line_in` and
    :meth:`end_line_in`.

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
        self._fallback: Optional[FallbackQueue] = None
        self._fallback_active: bool = False

        # Content-kind tracking (intent, not raw engine state)
        self._content: ContentKind = ContentKind.IDLE

        # T15.2: Line-in state
        self._active_linein_id: Optional[str] = None
        self._active_linein_runtime: Optional[LineInRuntime] = None

        # Register for engine callbacks so we can react to queue exhaustion
        engine.on_track_change(self._on_engine_track_change)

    # ------------------------------------------------------------------
    # Public API — show lifecycle
    # ------------------------------------------------------------------

    def start_show(self, items: List[QueueItem], mode: StartMode) -> None:
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

    def set_fallback(self, fallback: FallbackQueue) -> None:
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
    # Public API — state queries
    # ------------------------------------------------------------------

    def active_content(self) -> ContentKind:
        """
        Return the logical kind of content currently active (intent-based).

        See :class:`ContentKind` for the meaning of each value.
        """
        with self._lock:
            return self._content

    def active_linein_id(self) -> Optional[str]:
        """
        Return the domain UUID of the currently active Line-In source.

        Returns
        -------
        Optional[str]
            The :attr:`~audio.linein.domain.LineIn.id` of the active line-in
            when ``active_content() == ContentKind.LINE_IN``, otherwise
            ``None``.
        """
        with self._lock:
            return self._active_linein_id

    # ------------------------------------------------------------------
    # Public API — T15.2 line-in integration
    # ------------------------------------------------------------------

    def go_to_line_in(
        self,
        linein: LineInDomain,
        runtime: LineInRuntime,
    ) -> ActivationResult:
        """
        Switch to a Line-In source at Priority 1 (highest), preempting any
        currently active content.

        Sequence
        --------
        1. If another line-in is active it is deactivated first.
        2. ``_fallback_active`` is cleared *before* ``engine.stop()`` so that
           the engine's ``on_track_change`` callback does not spuriously
           restart the fallback.
        3. The engine is stopped (hard preempt).
        4. ``runtime.activate(linein)`` is called.
        5. On failure: the system reverts to FALLBACK (if configured) or IDLE
           and returns the failure result — it never raises.
        6. On success: ``active_content()`` returns ``LINE_IN`` and
           ``active_linein_id()`` returns ``linein.id``.

        Parameters
        ----------
        linein:
            The :class:`~audio.linein.domain.LineIn` source to activate.
        runtime:
            The :class:`~audio.linein._runtime.LineInRuntime` engine that
            manages the physical device lifecycle.

        Returns
        -------
        ActivationResult
            ``success=True`` when the line-in is live.
            ``success=False`` (with ``error_message``) on device failure.
        """
        # --- Step 1: deactivate any existing line-in (idempotent swap) ------
        with self._lock:
            prev_runtime = self._active_linein_runtime
            prev_id      = self._active_linein_id

        if prev_runtime is not None and prev_id is not None:
            prev_runtime.deactivate(prev_id)

        # --- Step 2: clear fallback flag BEFORE engine.stop() ---------------
        # This prevents _on_engine_track_change from spuriously restarting the
        # fallback when stop() fires the "current_item=None" callback.
        with self._lock:
            self._fallback_active = False

        # --- Step 3: hard-stop the engine -----------------------------------
        self._engine.stop()

        # --- Step 4: attempt activation -------------------------------------
        result = runtime.activate(linein)

        # --- Step 5: handle failure -----------------------------------------
        if not result.success:
            with self._lock:
                fb = self._fallback
                self._active_linein_id      = None
                self._active_linein_runtime = None
                if fb and not fb.is_empty():
                    self._fallback_active = True
                    self._content = ContentKind.FALLBACK
                else:
                    self._content = ContentKind.IDLE
            logger.warning(
                "Line-in activation failed for '%s' (device: %s): %s",
                linein.name, linein.device_id, result.error_message,
            )
            if fb and not fb.is_empty():
                threading.Thread(
                    target=self._trigger_fallback, daemon=True
                ).start()
            return result

        # --- Step 6: record success -----------------------------------------
        with self._lock:
            self._content               = ContentKind.LINE_IN
            self._active_linein_id      = linein.id
            self._active_linein_runtime = runtime

        logger.info(
            "Line-in activated: '%s' (device: %s, id: %s)",
            linein.name, linein.device_id, linein.id,
        )
        return result

    def end_line_in(self) -> None:
        """
        Deactivate the currently active Line-In source and resume normal playout.

        If not in ``LINE_IN`` mode this is a safe no-op.

        After deactivation
        ------------------
        * If a fallback is configured it starts in a daemon thread
          (``active_content()`` becomes ``FALLBACK``).
        * Otherwise the engine stays stopped (``active_content()`` is ``IDLE``).
        """
        with self._lock:
            if self._content != ContentKind.LINE_IN:
                return  # nothing to do

            runtime  = self._active_linein_runtime
            linein_id = self._active_linein_id
            self._active_linein_id      = None
            self._active_linein_runtime = None
            fb = self._fallback

            if fb and not fb.is_empty():
                self._fallback_active = True
                self._content = ContentKind.FALLBACK
            else:
                self._content = ContentKind.IDLE

        # Deactivate OUTSIDE the lock to avoid deadlock with runtime internals
        if runtime is not None and linein_id is not None:
            runtime.deactivate(linein_id)
            logger.info("Line-in deactivated: %s", linein_id)

        if fb and not fb.is_empty():
            threading.Thread(target=self._trigger_fallback, daemon=True).start()
            logger.info("Fallback started after line-in ended")
        else:
            logger.info("Line-in ended, engine idle")

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

          - Content is LINE_IN: the engine stopped as part of a line-in
            transition; the fallback must NOT be restarted (it will be
            managed explicitly by ``end_line_in()``).
          - Fallback active + ``loop=True``:  restart fallback from the top
            (``QUEUE_BEHAVIOR.md`` §4.4).
          - Fallback active + ``loop=False``: non-looping fallback played
            once and stopped naturally; mark content as IDLE (§4.5).
          - Fallback not active: ignore.
        """
        if event.current_item is not None:
            return  # a new track started — nothing to do

        with self._lock:
            active  = self._fallback_active
            fb      = self._fallback
            content = self._content

        # During LINE_IN mode the engine is stopped intentionally — don't
        # interpret queue exhaustion as a signal to start the fallback.
        if content == ContentKind.LINE_IN:
            return

        if not active or not fb:
            return

        if fb.loop and not fb.is_empty():
            # Restart the fallback list from the top
            threading.Thread(target=self._trigger_fallback, daemon=True).start()
        else:
            # Non-looping fallback exhausted — engine stopped naturally
            with self._lock:
                self._content = ContentKind.IDLE
