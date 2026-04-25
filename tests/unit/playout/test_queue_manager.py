"""
T8.2 validation — QueueManager.

Verifies that:
1.  active_content() returns IDLE on construction.
2.  fallback_is_active() returns False on construction.
3.  start_show(items, HARD) sets active_content() to SHOW.
4.  start_show(items, HARD) calls load_queue() then start() on the engine.
5.  start_show() clears the fallback-active flag before touching the engine.
6.  start_show(items, SOFT) from STOPPED falls back to HARD path.
7.  start_show(items, SOFT) from PLAYING splices without stop (clear_queue + append).
8.  end_show() calls engine.stop().
9.  end_show() with no fallback sets active_content() to IDLE.
10. end_show() with fallback configured sets active_content() to FALLBACK and
    starts the fallback (engine transitions to PLAYING).
11. Hard start_show() while fallback is playing stops fallback immediately.
12. Looping fallback restarts when the engine's queue is exhausted.
13. Non-looping fallback plays once; active_content() becomes IDLE afterward.
14. clear_fallback() prevents the fallback from restarting.
15. fallback_is_active() tracks the flag correctly across transitions.
16. start_show() with empty items raises ValueError.
17. V criterion (mock): full show + fallback cycle — show plays, ends, fallback
    starts automatically.
18. V criterion (mock): HARD show B interrupts show A mid-play; show B items
    play instead.
"""

import time
import threading
from typing import List

import pytest

from playout.engine_interface import QueueItem, TrackChangedEvent, PlayoutState
from playout.engine_mock import MockPlayoutEngine
from playout.fallback import FallbackQueue
from playout.queue_manager import ContentKind, QueueManager
from playout.scheduler import StartMode

# Short simulated track duration for fast tests
TICK = 0.05


def _item(item_id: str, duration: float = TICK * 10) -> QueueItem:
    """Create a test QueueItem with a given id and duration."""
    return QueueItem(
        id=item_id,
        uri=f"file:///{item_id}.mp3",
        title=f"Track {item_id}",
        duration=duration,
    )


def _fallback(*ids: str, loop: bool = True) -> FallbackQueue:
    """Create a FallbackQueue from id strings."""
    return FallbackQueue(items=[_item(i) for i in ids], loop=loop)


# ---------------------------------------------------------------------------
# Spy engine — records method calls for assertion
# ---------------------------------------------------------------------------

class _SpyEngine(MockPlayoutEngine):
    """Thin wrapper that records calls to key engine methods."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.calls: List[str] = []

    def load_queue(self, items):
        self.calls.append(f"load_queue({len(items)})")
        super().load_queue(items)

    def start(self):
        self.calls.append("start")
        super().start()

    def stop(self):
        self.calls.append("stop")
        super().stop()

    def clear_queue(self):
        self.calls.append("clear_queue")
        super().clear_queue()

    def append(self, item):
        self.calls.append(f"append({item.id})")
        super().append(item)


# ---------------------------------------------------------------------------
# 1–2  Construction state
# ---------------------------------------------------------------------------

def test_qm_idle_on_init():
    engine = MockPlayoutEngine()
    qm = QueueManager(engine)
    assert qm.active_content() == ContentKind.IDLE


def test_qm_fallback_not_active_on_init():
    engine = MockPlayoutEngine()
    qm = QueueManager(engine)
    assert qm.fallback_is_active() is False


# ---------------------------------------------------------------------------
# 3–5  HARD start
# ---------------------------------------------------------------------------

def test_qm_hard_start_sets_content_to_show():
    engine = _SpyEngine(default_track_duration=TICK)
    qm = QueueManager(engine)
    qm.start_show([_item("a")], StartMode.HARD)
    assert qm.active_content() == ContentKind.SHOW


def test_qm_hard_start_calls_load_queue_then_start():
    engine = _SpyEngine(default_track_duration=TICK)
    qm = QueueManager(engine)
    qm.start_show([_item("a"), _item("b")], StartMode.HARD)
    # load_queue must come before start; no stop or clear_queue
    assert "load_queue(2)" in engine.calls
    assert "start" in engine.calls
    load_idx = engine.calls.index("load_queue(2)")
    start_idx = engine.calls.index("start")
    assert load_idx < start_idx
    assert "stop" not in engine.calls
    assert "clear_queue" not in engine.calls


def test_qm_hard_start_clears_fallback_active_flag():
    """
    QUEUE_BEHAVIOR.md §4.1 HARD step 2: _fallback_active must be False
    before load_queue() is called so the track-change callback cannot
    spuriously restart the fallback while the engine is briefly STOPPED.
    """
    engine = _SpyEngine(default_track_duration=TICK)
    qm = QueueManager(engine)
    qm.set_fallback(_fallback("filler"))

    # Manually set flag as if fallback were running
    with qm._lock:
        qm._fallback_active = True

    qm.start_show([_item("show-a")], StartMode.HARD)

    assert qm.fallback_is_active() is False


# ---------------------------------------------------------------------------
# 6–7  SOFT start
# ---------------------------------------------------------------------------

def test_qm_soft_start_from_stopped_uses_hard_path():
    """Soft start on a stopped engine must fall back to HARD behaviour."""
    engine = _SpyEngine(default_track_duration=TICK)
    qm = QueueManager(engine)
    # Engine starts STOPPED
    assert engine.get_state() == PlayoutState.STOPPED

    qm.start_show([_item("x")], StartMode.SOFT)

    # Should behave exactly like HARD: load_queue then start
    assert "load_queue(1)" in engine.calls
    assert "start" in engine.calls
    assert qm.active_content() == ContentKind.SHOW


def test_qm_soft_start_splices_when_playing():
    """
    Soft start on a PLAYING engine must call clear_queue() + append() per
    item without calling stop() or load_queue().
    """
    engine = _SpyEngine(default_track_duration=TICK * 100)  # long first track
    qm = QueueManager(engine)

    # Start a long-running item so the engine is PLAYING when we splice
    engine.load_queue([_item("long", duration=TICK * 100)])
    engine.start()
    assert engine.get_state() == PlayoutState.PLAYING

    engine.calls.clear()  # reset spy so we only capture the splice calls

    qm.start_show([_item("s1"), _item("s2")], StartMode.SOFT)

    assert "clear_queue" in engine.calls
    assert "append(s1)" in engine.calls
    assert "append(s2)" in engine.calls
    # Must NOT have called stop or load_queue during the splice
    assert "stop" not in engine.calls
    assert "load_queue(2)" not in engine.calls
    assert qm.active_content() == ContentKind.SHOW

    engine.stop()  # clean up


# ---------------------------------------------------------------------------
# 8–10  end_show
# ---------------------------------------------------------------------------

def test_qm_end_show_stops_engine():
    engine = _SpyEngine(default_track_duration=TICK * 100)
    qm = QueueManager(engine)
    qm.start_show([_item("a")], StartMode.HARD)
    assert engine.get_state() == PlayoutState.PLAYING

    qm.end_show()
    assert engine.get_state() == PlayoutState.STOPPED


def test_qm_end_show_no_fallback_sets_idle():
    engine = MockPlayoutEngine(default_track_duration=TICK * 100)
    qm = QueueManager(engine)
    qm.start_show([_item("a")], StartMode.HARD)

    qm.end_show()

    assert qm.active_content() == ContentKind.IDLE
    assert qm.fallback_is_active() is False


def test_qm_end_show_triggers_fallback_and_sets_fallback_content():
    """
    QUEUE_BEHAVIOR.md §4.2 + §4.3: after end_show() with a configured
    fallback, content kind becomes FALLBACK and the engine restarts.
    """
    engine = MockPlayoutEngine(default_track_duration=TICK * 100)
    qm = QueueManager(engine)
    qm.set_fallback(_fallback("filler"))
    qm.start_show([_item("show")], StartMode.HARD)
    assert engine.get_state() == PlayoutState.PLAYING

    qm.end_show()

    # Give the daemon thread a moment to start the fallback
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        if engine.get_state() == PlayoutState.PLAYING:
            break
        time.sleep(0.01)

    assert qm.active_content() == ContentKind.FALLBACK
    assert qm.fallback_is_active() is True
    assert engine.get_state() == PlayoutState.PLAYING
    assert engine.get_current_item().id == "filler"

    engine.stop()


# ---------------------------------------------------------------------------
# 11  Show interrupts fallback
# ---------------------------------------------------------------------------

def test_qm_show_interrupts_fallback_hard():
    """
    QUEUE_BEHAVIOR.md §4.6 HARD: a HARD show start while fallback is playing
    stops the fallback immediately and clears _fallback_active.
    """
    engine = MockPlayoutEngine(default_track_duration=TICK * 100)
    qm = QueueManager(engine)
    qm.set_fallback(_fallback("filler"))

    # Simulate fallback running
    qm.end_show()  # no prior show; end_show just starts fallback
    # Actually need a prior start to end_show; use direct fallback trigger
    # instead: set flag + trigger manually
    with qm._lock:
        qm._fallback_active = True
        qm._content = ContentKind.FALLBACK
    engine.load_queue([_item("filler", duration=TICK * 100)])
    engine.start()

    assert qm.fallback_is_active() is True

    qm.start_show([_item("show-item")], StartMode.HARD)

    assert qm.fallback_is_active() is False
    assert qm.active_content() == ContentKind.SHOW
    assert engine.get_current_item().id == "show-item"

    engine.stop()


# ---------------------------------------------------------------------------
# 12  Looping fallback restart
# ---------------------------------------------------------------------------

def test_qm_fallback_loop_restarts():
    """
    QUEUE_BEHAVIOR.md §4.4: when loop=True and the engine's queue is
    exhausted while _fallback_active is True, the fallback restarts.
    """
    engine = MockPlayoutEngine(default_track_duration=TICK)
    qm = QueueManager(engine)
    qm.set_fallback(_fallback("fb1", loop=True))

    # Trigger one loop cycle: load a one-item fallback, let it exhaust, wait
    # for the restart triggered by _on_engine_track_change
    with qm._lock:
        qm._fallback_active = True
        qm._content = ContentKind.FALLBACK
    engine.load_queue([_item("fb1", duration=TICK)])
    engine.start()

    # After TICK the item ends → engine fires track_change(prev, None)
    # → QM restarts the fallback
    time.sleep(TICK * 2 + TICK * 5)  # generous margin

    # Engine should be PLAYING again (fallback restarted)
    assert engine.get_state() == PlayoutState.PLAYING
    assert qm.active_content() == ContentKind.FALLBACK

    engine.stop()


# ---------------------------------------------------------------------------
# 13  Non-looping fallback
# ---------------------------------------------------------------------------

def test_qm_non_looping_fallback_plays_once():
    """
    QUEUE_BEHAVIOR.md §4.5: when loop=False and the fallback is exhausted,
    the engine stops naturally and active_content() becomes IDLE.
    """
    engine = MockPlayoutEngine(default_track_duration=TICK)
    qm = QueueManager(engine)
    qm.set_fallback(_fallback("fb1", loop=False))

    with qm._lock:
        qm._fallback_active = True
        qm._content = ContentKind.FALLBACK
    engine.load_queue([_item("fb1", duration=TICK)])
    engine.start()

    # Wait for item to finish
    time.sleep(TICK * 2 + TICK * 5)

    assert engine.get_state() == PlayoutState.STOPPED
    # QM must have marked content as IDLE (no restart)
    assert qm.active_content() == ContentKind.IDLE


# ---------------------------------------------------------------------------
# 14  clear_fallback
# ---------------------------------------------------------------------------

def test_qm_clear_fallback_prevents_restart():
    """
    clear_fallback() must set _fallback_active=False so the next
    track-change event does not trigger a restart.
    """
    engine = MockPlayoutEngine(default_track_duration=TICK)
    qm = QueueManager(engine)
    qm.set_fallback(_fallback("fb1", loop=True))

    with qm._lock:
        qm._fallback_active = True
        qm._content = ContentKind.FALLBACK

    qm.clear_fallback()

    assert qm.fallback_is_active() is False
    # Manually fire a track-change(stop) event; fallback must not restart
    from playout.engine_interface import TrackChangedEvent
    from datetime import datetime, timezone

    qm._on_engine_track_change(
        TrackChangedEvent(
            previous_item=_item("fb1"),
            current_item=None,
            timestamp=datetime.now(tz=timezone.utc),
        )
    )

    time.sleep(TICK * 3)  # give any erroneous daemon thread time to start
    assert engine.get_state() == PlayoutState.STOPPED


# ---------------------------------------------------------------------------
# 15  fallback_is_active flag tracking
# ---------------------------------------------------------------------------

def test_qm_fallback_is_active_transitions():
    engine = MockPlayoutEngine(default_track_duration=TICK * 100)
    qm = QueueManager(engine)

    assert qm.fallback_is_active() is False

    qm.set_fallback(_fallback("filler"))
    qm.start_show([_item("s")], StartMode.HARD)
    # After start_show, fallback flag must be False
    assert qm.fallback_is_active() is False

    qm.end_show()
    # After end_show with configured fallback, flag should be True
    assert qm.fallback_is_active() is True

    # Clear resets flag
    qm.clear_fallback()
    assert qm.fallback_is_active() is False

    engine.stop()


# ---------------------------------------------------------------------------
# 16  Empty items raises ValueError
# ---------------------------------------------------------------------------

def test_qm_start_show_empty_items_raises():
    engine = MockPlayoutEngine()
    qm = QueueManager(engine)
    with pytest.raises(ValueError, match="at least one item"):
        qm.start_show([], StartMode.HARD)


# ---------------------------------------------------------------------------
# 17  V criterion: full show + fallback cycle
# ---------------------------------------------------------------------------

def test_qm_show_ends_fallback_starts_v_criterion():
    """
    V criterion (mock): start a show via QueueManager, call end_show(),
    verify the fallback starts automatically and the engine returns to
    PLAYING with the fallback item.
    """
    engine = MockPlayoutEngine(default_track_duration=TICK * 100)
    qm = QueueManager(engine)

    fb_item = _item("filler-v")
    qm.set_fallback(FallbackQueue(items=[fb_item], loop=False))

    show_items = [_item("show-v1"), _item("show-v2")]
    qm.start_show(show_items, StartMode.HARD)
    assert engine.get_state() == PlayoutState.PLAYING
    assert engine.get_current_item().id == "show-v1"
    assert qm.active_content() == ContentKind.SHOW

    # End the show manually (simulates end_at timer).
    # engine.stop() is called synchronously inside end_show(); the fallback
    # daemon thread starts immediately after, so the engine may already be
    # PLAYING again before we reach the next line.
    qm.end_show()

    # Fallback daemon thread starts in the background — wait for it
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        if engine.get_state() == PlayoutState.PLAYING:
            break
        time.sleep(0.01)

    assert engine.get_state() == PlayoutState.PLAYING, (
        "Fallback did not start within the timeout"
    )
    assert engine.get_current_item().id == "filler-v"
    assert qm.active_content() == ContentKind.FALLBACK
    assert qm.fallback_is_active() is True

    engine.stop()


# ---------------------------------------------------------------------------
# 18  V criterion: HARD show B interrupts show A
# ---------------------------------------------------------------------------

def test_qm_hard_show_b_interrupts_show_a_v_criterion():
    """
    V criterion (mock): show A is playing; HARD start of show B immediately
    replaces it.  Show B's first item plays; show A's items are gone.
    """
    engine = MockPlayoutEngine(default_track_duration=TICK * 100)
    qm = QueueManager(engine)

    show_a = [_item("a1", duration=TICK * 100), _item("a2", duration=TICK * 100)]
    show_b = [_item("b1", duration=TICK * 100), _item("b2", duration=TICK * 100)]

    qm.start_show(show_a, StartMode.HARD)
    assert engine.get_current_item().id == "a1"

    # HARD transition to show B — should interrupt A immediately
    qm.start_show(show_b, StartMode.HARD)

    assert engine.get_current_item().id == "b1"
    assert qm.active_content() == ContentKind.SHOW
    assert qm.fallback_is_active() is False

    engine.stop()
