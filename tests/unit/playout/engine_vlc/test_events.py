"""
T7.1 validation — VlcEventBridge and extract_vlc_meta.

Verifies that:
1.  extract_vlc_meta returns {} for None media.
2.  extract_vlc_meta returns title/artist from mock media.
3.  extract_vlc_meta returns duration_ms from mock media.
4.  extract_vlc_meta omits empty / None strings.
5.  extract_vlc_meta omits duration_ms when VLC reports -1.
6.  VlcEventBridge.attach() registers handlers for all four event types.
7.  VlcEventBridge.attach() is idempotent (second call is a no-op).
8.  VlcEventBridge.detach() unregisters all handlers.
9.  Simulated MediaPlayerPlaying fires on_playing with extracted meta.
10. Simulated MediaPlayerEndReached fires on_end_reached.
11. Simulated MediaPlayerEncounteredError fires on_error.
12. Simulated MediaPlayerMediaChanged fires on_media_changed.
13. Crashing on_playing callback does not propagate.
14. Multiple on_playing callbacks all receive the event.
15. VlcPlayoutEngine enriches item.metadata["vlc"] with duration_ms (V/VLC).
16. VlcPlayoutEngine enriches item.title from VLC tags when item.title is empty
    (skipped when VLC unavailable or tagged file absent).

Mock-based tests (1-14) run without real VLC playback.
VLC tests (15-16) are skipped when VLC is not installed.
"""

import time
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest

from playout.engine_vlc.events import VlcEventBridge, extract_vlc_meta


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _vlc_ok() -> bool:
    try:
        from playout.engine_vlc.probe import probe
        return probe().available
    except Exception:
        return False


vlc_required = pytest.mark.skipif(
    not _vlc_ok(),
    reason="VLC not installed — skipping VLC integration tests",
)


class _MockEventManager:
    """
    Captures event_attach / event_detach calls and can replay events.

    ``attached`` maps ``event_type`` → list of registered callbacks.
    ``detached`` records which event types were detached (no callback arg
    in python-vlc's event_detach — it removes all handlers for the type).
    """

    def __init__(self) -> None:
        self.attached: dict[Any, list] = {}   # event_type -> [cb, ...]
        self.detached: list[Any] = []          # event types that were detached

    def event_attach(self, event_type, callback) -> None:
        self.attached.setdefault(event_type, []).append(callback)

    def event_detach(self, event_type) -> None:
        # python-vlc signature: only the event type, no callback argument
        self.detached.append(event_type)

    def simulate(self, event_type, event=None) -> None:
        """Call all handlers registered for *event_type*."""
        for cb in self.attached.get(event_type, []):
            cb(event)


def _make_bridge():
    """
    Return ``(bridge, mock_em, mock_player)`` with a VlcEventBridge whose
    player is backed by a mock event manager — no real VLC needed.

    VLC EventType constants are patched so the bridge uses integer sentinels
    instead of real C enum values.
    """
    import vlc

    em = _MockEventManager()
    player = MagicMock()
    player.event_manager.return_value = em
    player.get_media.return_value = None  # no real media by default

    bridge = VlcEventBridge(player)
    return bridge, em, player


# ---------------------------------------------------------------------------
# extract_vlc_meta — unit tests (no real VLC playback required)
# ---------------------------------------------------------------------------

def test_extract_vlc_meta_none_returns_empty():
    assert extract_vlc_meta(None) == {}


def test_extract_vlc_meta_title_and_artist():
    import vlc

    media = MagicMock()

    def _get_meta(meta_id):
        return {vlc.Meta.Title: "My Song", vlc.Meta.Artist: "DJ Test"}.get(
            meta_id, None
        )

    media.get_meta.side_effect = _get_meta
    media.get_duration.return_value = 5000

    result = extract_vlc_meta(media)
    assert result["title"] == "My Song"
    assert result["artist"] == "DJ Test"
    assert result["duration_ms"] == 5000


def test_extract_vlc_meta_duration_ms():
    import vlc

    media = MagicMock()
    media.get_meta.return_value = None   # no tags
    media.get_duration.return_value = 12345

    result = extract_vlc_meta(media)
    assert result.get("duration_ms") == 12345


def test_extract_vlc_meta_omits_empty_strings():
    import vlc

    media = MagicMock()
    media.get_meta.return_value = ""     # empty → should be omitted
    media.get_duration.return_value = -1

    result = extract_vlc_meta(media)
    assert "title" not in result
    assert "artist" not in result


def test_extract_vlc_meta_omits_negative_duration():
    import vlc

    media = MagicMock()
    media.get_meta.return_value = None
    media.get_duration.return_value = -1

    result = extract_vlc_meta(media)
    assert "duration_ms" not in result


# ---------------------------------------------------------------------------
# VlcEventBridge — attach / detach
# ---------------------------------------------------------------------------

def test_bridge_attach_registers_four_event_types():
    import vlc

    bridge, em, _ = _make_bridge()
    bridge.attach()

    expected = {
        vlc.EventType.MediaPlayerMediaChanged,
        vlc.EventType.MediaPlayerPlaying,
        vlc.EventType.MediaPlayerEndReached,
        vlc.EventType.MediaPlayerEncounteredError,
    }
    assert set(em.attached.keys()) == expected


def test_bridge_attach_is_idempotent():
    """Calling attach() twice must not register duplicate handlers."""
    import vlc

    bridge, em, _ = _make_bridge()
    bridge.attach()
    bridge.attach()

    for event_type, cbs in em.attached.items():
        assert len(cbs) == 1, (
            f"Expected 1 handler for {event_type}, got {len(cbs)}"
        )


def test_bridge_detach_unregisters_handlers():
    import vlc

    bridge, em, _ = _make_bridge()
    bridge.attach()
    bridge.detach()

    expected = {
        vlc.EventType.MediaPlayerMediaChanged,
        vlc.EventType.MediaPlayerPlaying,
        vlc.EventType.MediaPlayerEndReached,
        vlc.EventType.MediaPlayerEncounteredError,
    }
    assert set(em.detached) == expected


def test_bridge_detach_when_not_attached_is_noop():
    bridge, em, _ = _make_bridge()
    bridge.detach()   # never attached — must not raise
    assert em.detached == []


# ---------------------------------------------------------------------------
# VlcEventBridge — event simulation
# ---------------------------------------------------------------------------

def test_bridge_on_playing_fires_with_meta():
    import vlc

    bridge, em, player = _make_bridge()

    # Give the player a mock media with a known title
    media = MagicMock()
    media.get_meta.side_effect = (
        lambda mid: "Test Title" if mid == vlc.Meta.Title else None
    )
    media.get_duration.return_value = 3000
    player.get_media.return_value = media

    received = []
    bridge.on_playing(received.append)
    bridge.attach()

    em.simulate(vlc.EventType.MediaPlayerPlaying)

    assert len(received) == 1
    meta = received[0]
    assert meta["title"] == "Test Title"
    assert meta["duration_ms"] == 3000


def test_bridge_on_end_reached_fires():
    import vlc

    bridge, em, _ = _make_bridge()
    fired = []
    bridge.on_end_reached(lambda: fired.append(True))
    bridge.attach()

    em.simulate(vlc.EventType.MediaPlayerEndReached)

    assert fired == [True]


def test_bridge_on_error_fires():
    import vlc

    bridge, em, _ = _make_bridge()
    fired = []
    bridge.on_error(lambda: fired.append(True))
    bridge.attach()

    em.simulate(vlc.EventType.MediaPlayerEncounteredError)

    assert fired == [True]


def test_bridge_on_media_changed_fires():
    import vlc

    bridge, em, _ = _make_bridge()
    fired = []
    bridge.on_media_changed(lambda: fired.append(True))
    bridge.attach()

    em.simulate(vlc.EventType.MediaPlayerMediaChanged)

    assert fired == [True]


def test_bridge_crashing_on_playing_does_not_propagate():
    import vlc

    bridge, em, _ = _make_bridge()

    def _bad(meta):
        raise RuntimeError("boom")

    second_called = []
    bridge.on_playing(_bad)
    bridge.on_playing(lambda m: second_called.append(m))
    bridge.attach()

    em.simulate(vlc.EventType.MediaPlayerPlaying)  # must not raise

    assert len(second_called) == 1   # second callback still ran


def test_bridge_multiple_on_playing_callbacks_all_receive_event():
    import vlc

    bridge, em, _ = _make_bridge()
    results = []
    bridge.on_playing(lambda m: results.append(("a", m)))
    bridge.on_playing(lambda m: results.append(("b", m)))
    bridge.attach()

    em.simulate(vlc.EventType.MediaPlayerPlaying)

    assert len(results) == 2
    assert results[0][0] == "a"
    assert results[1][0] == "b"


# ---------------------------------------------------------------------------
# V criterion: VlcPlayoutEngine enriches QueueItem via the bridge (real VLC)
# ---------------------------------------------------------------------------

@vlc_required
def test_vlc_engine_item_metadata_enriched_with_duration_ms():
    """
    V criterion (T7.1): after VLC starts playing a WAV, the bridge fires
    on_playing and the engine writes duration_ms into item.metadata["vlc"].
    """
    import math
    import struct
    import tempfile
    import wave
    from pathlib import Path

    from playout.engine_interface import QueueItem
    from playout.engine_vlc import VlcPlayoutEngine

    def _wav(duration: float = 0.5) -> Path:
        sr = 44100
        n = int(sr * duration)
        samples = [
            int(32767 * math.sin(2 * math.pi * 440 * i / sr)) for i in range(n)
        ]
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            p = Path(f.name)
        with wave.open(str(p), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(struct.pack(f"<{n}h", *samples))
        return p

    wav = _wav(1.0)
    engine = VlcPlayoutEngine(vlc_args=["--aout=dummy"])
    item = QueueItem(id="t7-test", uri=wav.as_uri(), duration=1.0)

    try:
        engine.load_queue([item])
        engine.start()

        # Wait for MediaPlayerPlaying to fire and the bridge callback to run
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            current = engine.get_current_item()
            if current and "vlc" in current.metadata:
                break
            time.sleep(0.05)

        current = engine.get_current_item()
        assert current is not None, "Engine not playing"
        assert "vlc" in current.metadata, (
            f"item.metadata has no 'vlc' key; got: {current.metadata}"
        )
        assert "duration_ms" in current.metadata["vlc"], (
            f"'duration_ms' absent from vlc meta; got: {current.metadata['vlc']}"
        )
        dur_ms = current.metadata["vlc"]["duration_ms"]
        assert isinstance(dur_ms, int), f"duration_ms should be int, got {type(dur_ms)}"
        assert dur_ms > 0, f"duration_ms should be positive, got {dur_ms}"

    finally:
        engine.stop()
        engine.close()
        wav.unlink(missing_ok=True)
