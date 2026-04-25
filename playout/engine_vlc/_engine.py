"""
VlcPlayoutEngine — libVLC-backed implementation of PlayoutEngine.

Architecture
------------
One ``vlc.Instance`` and one ``vlc.MediaPlayer`` are created at construction
and reused for the lifetime of the engine.  Items in the queue are played
sequentially: when VLC fires ``MediaPlayerEndReached`` the engine loads the
next item and calls ``play()`` from a new daemon thread (calling ``play()``
directly from the VLC callback thread can deadlock on some platforms).

Thread-safety
-------------
All mutations to ``_state``, ``_queue``, and ``_current_index`` are protected
by a single ``threading.RLock``.  VLC media-player calls (``set_media``,
``play``, ``pause``, ``stop``) and callback dispatch happen *outside* the lock.

Inter-track gap (known limitation)
-----------------------------------
A brief silence of typically 50–200 ms occurs between consecutive queue items.
The gap is caused by three sequential steps that happen after VLC fires
``MediaPlayerEndReached``:

1. A new Python daemon thread is spawned (~1–5 ms).
2. ``media_new()`` + ``set_media()`` load the next URI into the player (~5–50 ms).
3. VLC opens and buffers the new file before the first audio sample plays
   (~20–150 ms for local WAV/MP3; larger for network streams).

Planned improvement (post-T5.3): use ``libvlc_media_list_player`` or pre-load
the next media object during playback of the current item.  For the current
phase this gap is acceptable for scheduled-show boundaries where millisecond
precision is not required.

Requirements
------------
* VLC >= 3.0 installed (64-bit, matching Python bitness).
* ``python-vlc`` package installed (``pip install python-vlc``).
"""

import logging
import threading
from typing import Callable, Optional

from ..engine_interface import (
    PlayoutError,
    PlayoutState,
    QueueItem,
    TrackChangedEvent,
)
from ..engine_interface._engine import PlayoutEngine
from .events import VlcEventBridge

logger = logging.getLogger(__name__)

# VLC default instance arguments (suppress GUI and verbose output)
_VLC_DEFAULT_ARGS = [
    "--no-video-title-show",
    "--quiet",
    "--intf",
    "dummy",
]


class VlcPlayoutEngine(PlayoutEngine):
    """
    libVLC-backed playout engine.

    State machine
    -------------
    Valid transitions::

        STOPPED ──start()──► PLAYING ──pause()──► PAUSED
           ▲                    │                    │
           │                    │ stop()        resume()
           │                    ▼                    │
           └──────────────── STOPPED ◄───────────────┘
                               ▲
                ERROR ──stop()─┘   (start() from ERROR restarts from item 0)

    Idempotent calls (no state change, no error):
        start()  while PLAYING or PAUSED
        pause()  while PAUSED, STOPPED, or ERROR
        resume() while PLAYING, STOPPED, or ERROR
        stop()   while STOPPED

    Parameters
    ----------
    vlc_args:
        Extra arguments forwarded to ``vlc.Instance()``.  The default set
        already includes ``--quiet`` and ``--intf dummy``.  Pass
        ``["--aout=dummy"]`` in tests to suppress audio output.
    """

    def __init__(self, vlc_args: Optional[list] = None) -> None:
        # Probe first — gives a clear, actionable error if VLC is absent.
        from .probe import probe  # noqa: PLC0415

        probe().raise_if_unavailable()

        import vlc  # noqa: PLC0415

        self._vlc = vlc
        all_args = _VLC_DEFAULT_ARGS + (vlc_args or [])
        self._instance = vlc.Instance(*all_args)
        self._player = self._instance.media_player_new()

        # Internal state (protected by _lock)
        self._lock = threading.RLock()
        self._state: PlayoutState = PlayoutState.STOPPED
        self._queue: list[QueueItem] = []
        self._current_index: int = -1

        # Registered callbacks
        self._track_change_cbs: list[Callable[[TrackChangedEvent], None]] = []
        self._error_cbs: list[Callable[[PlayoutError], None]] = []

        # VLC event bridge — translates raw VLC events into Python callbacks
        self._bridge = VlcEventBridge(self._player)
        self._bridge.on_end_reached(self._on_vlc_end)
        self._bridge.on_error(self._on_vlc_error)
        self._bridge.on_playing(self._on_vlc_playing)
        self._bridge.attach()

    # ------------------------------------------------------------------
    # Transport
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start playback from the first item in the queue."""
        first_item: Optional[QueueItem] = None

        with self._lock:
            if self._state in (PlayoutState.PLAYING, PlayoutState.PAUSED):
                return
            if not self._queue:
                return
            self._current_index = 0
            self._state = PlayoutState.PLAYING
            first_item = self._queue[0]

        # VLC operations and callbacks outside the lock
        self._vlc_load(first_item.uri)
        self._player.play()
        logger.info("Started: %s", first_item.id)
        self._fire_track_change(None, first_item)

    def stop(self) -> None:
        """Stop playback and reset position."""
        prev: Optional[QueueItem] = None

        with self._lock:
            if self._state == PlayoutState.STOPPED:
                return
            prev = self._current_item_unsafe()
            self._state = PlayoutState.STOPPED
            self._current_index = -1

        # stop() must NOT be called from a VLC callback thread.
        # Here it is always called from user code, so it is safe.
        try:
            self._player.stop()
        except Exception:  # noqa: BLE001
            pass  # Already stopped or VLC in inconsistent state

        if prev is not None:
            logger.info("Stopped: %s", prev.id)
            self._fire_track_change(prev, None)

    def pause(self) -> None:
        """
        Pause at the current position.

        Idempotent: calling pause() while already PAUSED is a no-op.
        Calling pause() while STOPPED or in ERROR state is a no-op.
        """
        with self._lock:
            if self._state != PlayoutState.PLAYING:
                return
            self._state = PlayoutState.PAUSED

        # set_pause(True) is explicit and non-toggling (safer than pause())
        self._player.set_pause(True)

    def resume(self) -> None:
        """
        Resume playback from the paused position.

        Idempotent: calling resume() while already PLAYING is a no-op.
        Calling resume() while STOPPED or in ERROR state is a no-op.
        """
        with self._lock:
            if self._state != PlayoutState.PAUSED:
                return
            self._state = PlayoutState.PLAYING

        self._player.set_pause(False)

    # ------------------------------------------------------------------
    # Queue management
    # ------------------------------------------------------------------

    def load_queue(self, items: list[QueueItem]) -> None:
        """Replace the queue; stops playback if currently active."""
        was_active: bool = False
        prev: Optional[QueueItem] = None

        with self._lock:
            was_active = self._state in (PlayoutState.PLAYING, PlayoutState.PAUSED)
            prev = self._current_item_unsafe() if was_active else None
            self._queue = list(items)
            self._current_index = -1
            self._state = PlayoutState.STOPPED

        if was_active:
            try:
                self._player.stop()
            except Exception:  # noqa: BLE001
                pass
            if prev is not None:
                self._fire_track_change(prev, None)

    def append(self, item: QueueItem) -> None:
        """Append one item to the end of the queue."""
        with self._lock:
            self._queue.append(item)

    def clear_queue(self) -> None:
        """Remove all pending items; the currently playing item is kept."""
        with self._lock:
            current = self._current_item_unsafe()
            if current is not None:
                self._queue = [current]
                self._current_index = 0
            else:
                self._queue = []
                self._current_index = -1

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    def get_state(self) -> PlayoutState:
        with self._lock:
            return self._state

    def get_current_item(self) -> Optional[QueueItem]:
        with self._lock:
            return self._current_item_unsafe()

    def get_remaining_duration(self) -> Optional[float]:
        with self._lock:
            if self._state not in (PlayoutState.PLAYING, PlayoutState.PAUSED):
                return None

        # Read VLC time values outside the lock (non-blocking)
        time_ms = self._player.get_time()    # current position, ms
        length_ms = self._player.get_length()  # total duration, ms

        if time_ms >= 0 and length_ms > 0:
            return max(0.0, (length_ms - time_ms) / 1000.0)

        # Fall back to item metadata duration
        with self._lock:
            item = self._current_item_unsafe()
        if item is not None and item.duration is not None:
            return item.duration  # upper bound; position unknown
        return None

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def on_track_change(
        self, callback: Callable[[TrackChangedEvent], None]
    ) -> None:
        self._track_change_cbs.append(callback)

    def on_error(self, callback: Callable[[PlayoutError], None]) -> None:
        self._error_cbs.append(callback)

    # ------------------------------------------------------------------
    # Device selection
    # ------------------------------------------------------------------

    def select_output_device(self, device_id: str) -> None:
        """
        Select audio output device.  Best-effort: silently ignored if the
        device_id is not recognised by VLC.
        """
        try:
            # None → use the current audio output module
            self._player.audio_output_device_set(None, device_id)
        except Exception:  # noqa: BLE001
            logger.debug("select_output_device(%r) ignored by VLC", device_id)

    # ------------------------------------------------------------------
    # Resource cleanup
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Release VLC resources.  Call when the engine is no longer needed."""
        self._bridge.detach()
        try:
            self._player.stop()
        except Exception:  # noqa: BLE001
            pass
        try:
            self._player.release()
        except Exception:  # noqa: BLE001
            pass
        try:
            self._instance.release()
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------
    # Bridge callbacks — invoked by VlcEventBridge on VLC's event thread
    # ------------------------------------------------------------------

    def _on_vlc_end(self) -> None:
        """Bridge callback: current item finished naturally."""
        # Must NOT call _player.play() or _player.stop() here directly
        # — doing so from the VLC event thread can deadlock.
        threading.Thread(target=self._advance_track, daemon=True).start()

    def _on_vlc_error(self) -> None:
        """Bridge callback: VLC encountered a media error."""
        item: Optional[QueueItem]
        with self._lock:
            item = self._current_item_unsafe()
            self._state = PlayoutState.ERROR
        error = PlayoutError(
            code="vlc_error",
            message="VLC encountered a media error",
            item=item,
        )
        logger.error("VLC error on item %s", item.id if item else "unknown")
        self._fire_error(error)

    def _on_vlc_playing(self, meta: dict) -> None:
        """
        Bridge callback: VLC started (or resumed) playback.

        Enriches the current ``QueueItem`` in-place with metadata extracted
        by the bridge from VLC's media object:

        * ``item.title`` and ``item.artist`` are filled if currently empty
          and VLC reports non-empty values.
        * ``item.metadata["vlc"]`` is updated with remaining fields
          (``album``, ``genre``, ``duration_ms``, etc.).

        Called on VLC's event thread; mutations happen under ``_lock``.
        """
        if not meta:
            return
        with self._lock:
            item = self._current_item_unsafe()
            if item is None:
                return
            # Non-destructive: only fill empty first-class fields
            if not item.title and meta.get("title"):
                item.title = str(meta["title"])
            if not item.artist and meta.get("artist"):
                item.artist = str(meta["artist"])
            # Remaining keys go into metadata["vlc"] dict
            vlc_extra = {
                k: v for k, v in meta.items() if k not in ("title", "artist")
            }
            if vlc_extra:
                item.metadata["vlc"] = vlc_extra
        logger.debug(
            "VLC metadata for %r: %s",
            item.id if item else "?",
            meta,
        )

    # ------------------------------------------------------------------
    # Queue advance — runs in a daemon thread spawned by _on_vlc_end
    # ------------------------------------------------------------------

    def _advance_track(self) -> None:
        """
        Load and play the next queue item, or stop if the queue is done.

        Called in a fresh daemon thread spawned by ``_on_vlc_end``.  VLC
        media-player operations are performed *outside* the lock to avoid
        re-entrant locking and potential deadlocks.

        Inter-track gap: the time between this function being called and the
        first audio sample of the next item is typically 50–200 ms on local
        files (see module docstring for details).
        """
        prev_item: Optional[QueueItem]
        next_item: Optional[QueueItem]
        next_uri: Optional[str] = None

        with self._lock:
            if self._state != PlayoutState.PLAYING:
                return  # stop() or load_queue() already ran

            prev_item = self._current_item_unsafe()
            self._current_index += 1

            if self._current_index >= len(self._queue):
                self._state = PlayoutState.STOPPED
                self._current_index = -1
                next_item = None
            else:
                next_item = self._queue[self._current_index]
                next_uri = next_item.uri

        # VLC operations outside the lock
        if next_uri is not None:
            self._vlc_load(next_uri)
            self._player.play()
            logger.info("Advanced to: %s", next_item.id if next_item else "?")

        self._fire_track_change(prev_item, next_item)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _current_item_unsafe(self) -> Optional[QueueItem]:
        """Return current item; must be called with _lock held."""
        if 0 <= self._current_index < len(self._queue):
            return self._queue[self._current_index]
        return None

    def _vlc_load(self, uri: str) -> None:
        """Create a VLC media object from *uri* and set it on the player."""
        media = self._instance.media_new(uri)
        self._player.set_media(media)

    def _fire_track_change(
        self,
        previous: Optional[QueueItem],
        current: Optional[QueueItem],
    ) -> None:
        event = TrackChangedEvent(previous_item=previous, current_item=current)
        for cb in list(self._track_change_cbs):
            try:
                cb(event)
            except Exception:  # noqa: BLE001
                pass

    def _fire_error(self, error: PlayoutError) -> None:
        for cb in list(self._error_cbs):
            try:
                cb(error)
            except Exception:  # noqa: BLE001
                pass
