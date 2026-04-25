"""
VlcEventBridge — libVLC MediaPlayer event adapter.

Translates raw VLC C-land events into clean Python callbacks and extracts
available media metadata for each "playing" transition.  The bridge does
not manage playout state; it is a thin, independently testable adapter.

VLC fires events on its own internal thread.  All callbacks registered
via ``on_playing`` / ``on_end_reached`` / ``on_error`` / ``on_media_changed``
are invoked on that thread.  Callers that need thread-safety must synchronise
themselves, and must NOT make VLC API calls from within these callbacks
(risk of deadlock — spawn a fresh daemon thread instead).

Subscribed events
-----------------
``MediaPlayerMediaChanged``
    New media has been loaded into the player.  Metadata is not yet
    available; VLC has not necessarily parsed the file at this point.

``MediaPlayerPlaying``
    VLC has started (or resumed) actual playback.  Media parse results are
    usually available by this point; ``extract_vlc_meta`` is called here.

``MediaPlayerEndReached``
    The current item finished playing naturally.

``MediaPlayerEncounteredError``
    VLC hit a fatal error on the current item.

Metadata extraction
-------------------
``extract_vlc_meta(media)`` reads the following fields from a
``vlc.Media`` object (absent keys mean VLC returned no value):

    title, artist, album, genre, track_number, year, description
        Strings from the embedded tag block (ID3, Vorbis, etc.).

    duration_ms
        Integer milliseconds as reported by VLC.  Only included when
        VLC returns a value ≥ 0 (−1 means "unknown").

Public API
----------
::

    from playout.engine_vlc.events import VlcEventBridge, extract_vlc_meta

    bridge = VlcEventBridge(player)
    bridge.on_playing(lambda meta: print("playing", meta))
    bridge.on_end_reached(lambda: print("ended"))
    bridge.on_error(lambda: print("error"))
    bridge.attach()

    # … later …
    bridge.detach()
"""

from __future__ import annotations

import logging
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Type alias — dict produced by extract_vlc_meta
VlcMeta = Dict[str, object]

# String meta keys and their corresponding vlc.Meta enum members (by name).
# Resolved lazily so the module can be imported without python-vlc installed.
_META_ATTR_NAMES = {
    "title":        "Title",
    "artist":       "Artist",
    "album":        "Album",
    "genre":        "Genre",
    "track_number": "TrackNumber",
    "year":         "Date",
    "description":  "Description",
}


def extract_vlc_meta(media) -> VlcMeta:
    """
    Extract available metadata from a ``vlc.Media`` object.

    Parameters
    ----------
    media:
        A ``vlc.Media`` instance, or *None*.

    Returns
    -------
    dict
        Present keys (string values, non-empty only):
        ``title``, ``artist``, ``album``, ``genre``,
        ``track_number``, ``year``, ``description``.
        Integer key ``duration_ms`` present when VLC reports ≥ 0 ms.
        Returns an empty dict when *media* is ``None`` or no data
        is available.
    """
    if media is None:
        return {}

    try:
        import vlc as _vlc
    except ImportError:
        return {}

    result: VlcMeta = {}

    for key, attr in _META_ATTR_NAMES.items():
        try:
            meta_id = getattr(_vlc.Meta, attr)
            val = media.get_meta(meta_id)
            if val:
                result[key] = val
        except Exception:  # noqa: BLE001
            pass

    try:
        dur = media.get_duration()  # ms; −1 if unknown
        if dur >= 0:
            result["duration_ms"] = int(dur)
    except Exception:  # noqa: BLE001
        pass

    return result


class VlcEventBridge:
    """
    Subscribes to a libVLC ``MediaPlayer``'s event manager and translates
    raw VLC events into named Python callbacks.

    Parameters
    ----------
    player:
        A ``vlc.MediaPlayer`` instance whose events to monitor.

    Callbacks
    ---------
    ``on_playing(meta: VlcMeta)``
        VLC started (or resumed) playback.  *meta* is the result of
        ``extract_vlc_meta`` on the current media — may be empty for
        formats VLC cannot parse tags from.

    ``on_end_reached()``
        VLC finished the current item naturally (end-of-file).

    ``on_error()``
        VLC encountered a fatal error on the current item.

    ``on_media_changed()``
        VLC loaded new media (tags not yet available).

    Thread safety
    -------------
    All callbacks are invoked on VLC's internal event thread.  Do **not**
    call VLC API methods from within them — use a daemon thread instead
    (see ``VlcPlayoutEngine._on_vlc_end`` for the pattern).

    Example
    -------
    ::

        bridge = VlcEventBridge(player)
        bridge.on_playing(lambda meta: logger.info("now playing: %s", meta))
        bridge.on_end_reached(lambda: print("track ended"))
        bridge.attach()
        # … player.play() …
        bridge.detach()
    """

    def __init__(self, player) -> None:
        self._player = player
        self._playing_cbs:       List[Callable[[VlcMeta], None]] = []
        self._end_cbs:           List[Callable[[], None]] = []
        self._error_cbs:         List[Callable[[], None]] = []
        self._media_changed_cbs: List[Callable[[], None]] = []
        self._attached: bool = False

    # ------------------------------------------------------------------
    # Callback registration
    # ------------------------------------------------------------------

    def on_playing(self, cb: Callable[[VlcMeta], None]) -> None:
        """Register *cb* to be called with ``VlcMeta`` when playback starts."""
        self._playing_cbs.append(cb)

    def on_end_reached(self, cb: Callable[[], None]) -> None:
        """Register *cb* to be called when the current item finishes."""
        self._end_cbs.append(cb)

    def on_error(self, cb: Callable[[], None]) -> None:
        """Register *cb* to be called when VLC encounters a media error."""
        self._error_cbs.append(cb)

    def on_media_changed(self, cb: Callable[[], None]) -> None:
        """Register *cb* to be called when VLC loads new media."""
        self._media_changed_cbs.append(cb)

    # ------------------------------------------------------------------
    # Attach / detach
    # ------------------------------------------------------------------

    def attach(self) -> None:
        """
        Subscribe to all relevant VLC ``MediaPlayer`` events.

        Idempotent: calling ``attach()`` more than once has no effect.
        """
        if self._attached:
            return
        import vlc

        em = self._player.event_manager()
        em.event_attach(
            vlc.EventType.MediaPlayerMediaChanged, self._vlc_media_changed
        )
        em.event_attach(vlc.EventType.MediaPlayerPlaying,    self._vlc_playing)
        em.event_attach(vlc.EventType.MediaPlayerEndReached, self._vlc_end_reached)
        em.event_attach(
            vlc.EventType.MediaPlayerEncounteredError, self._vlc_error
        )
        self._attached = True
        logger.debug("VlcEventBridge: attached to player %r", self._player)

    def detach(self) -> None:
        """
        Unsubscribe from all VLC events registered by ``attach()``.

        Idempotent: calling ``detach()`` when not attached is a no-op.
        """
        if not self._attached:
            return
        import vlc

        em = self._player.event_manager()
        # python-vlc event_detach only accepts the event type (removes all
        # handlers for that type); no callback argument is supported.
        em.event_detach(vlc.EventType.MediaPlayerMediaChanged)
        em.event_detach(vlc.EventType.MediaPlayerPlaying)
        em.event_detach(vlc.EventType.MediaPlayerEndReached)
        em.event_detach(vlc.EventType.MediaPlayerEncounteredError)
        self._attached = False
        logger.debug("VlcEventBridge: detached from player %r", self._player)

    # ------------------------------------------------------------------
    # VLC event handlers — run on VLC's internal event thread
    # ------------------------------------------------------------------

    def _vlc_media_changed(self, event) -> None:
        logger.debug("VLC event: MediaPlayerMediaChanged")
        for cb in list(self._media_changed_cbs):
            try:
                cb()
            except Exception:  # noqa: BLE001
                logger.exception(
                    "VlcEventBridge: error in on_media_changed callback"
                )

    def _vlc_playing(self, event) -> None:
        logger.debug("VLC event: MediaPlayerPlaying")
        try:
            media = self._player.get_media()
            meta: VlcMeta = extract_vlc_meta(media)
        except Exception:  # noqa: BLE001
            meta = {}
        for cb in list(self._playing_cbs):
            try:
                cb(meta)
            except Exception:  # noqa: BLE001
                logger.exception("VlcEventBridge: error in on_playing callback")

    def _vlc_end_reached(self, event) -> None:
        logger.debug("VLC event: MediaPlayerEndReached")
        for cb in list(self._end_cbs):
            try:
                cb()
            except Exception:  # noqa: BLE001
                logger.exception(
                    "VlcEventBridge: error in on_end_reached callback"
                )

    def _vlc_error(self, event) -> None:
        logger.debug("VLC event: MediaPlayerEncounteredError")
        for cb in list(self._error_cbs):
            try:
                cb()
            except Exception:  # noqa: BLE001
                logger.exception("VlcEventBridge: error in on_error callback")
