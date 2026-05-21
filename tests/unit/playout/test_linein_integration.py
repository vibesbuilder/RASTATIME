"""
T15.2 — Line-In / playout source selection integration tests.

Verifies that :class:`~playout.queue_manager.QueueManager` correctly
integrates the Priority-1 line-in source with its existing SHOW / FALLBACK /
IDLE content flow.

All 22 tests are pure Python — no Django, no real audio hardware.
``MockPlayoutEngine`` and ``StubLineInRuntime`` are used throughout.

Test inventory
--------------
ContentKind extension (2):
  1.  ``ContentKind.LINE_IN`` has value ``"line_in"``.
  2.  ``ContentKind.LINE_IN`` is distinct from IDLE, SHOW, FALLBACK.

go_to_line_in() — success path (5):
  3.  Returns ``ActivationResult`` with ``success=True`` when runtime succeeds.
  4.  ``active_content()`` returns ``LINE_IN`` after successful activation.
  5.  Engine is in STOPPED state after ``go_to_line_in()``.
  6.  ``active_linein_id()`` returns the line-in domain UUID after activation.
  7.  Fallback does NOT start after a successful ``go_to_line_in()``.

go_to_line_in() — failure path (3):
  8.  Returns ``ActivationResult`` with ``success=False`` when runtime fails.
  9.  ``active_content()`` returns IDLE after failed activation (no fallback).
 10.  ``active_content()`` returns FALLBACK after failed activation (fallback
      configured); fallback playback begins.

go_to_line_in() — source swap (2):
 11.  Second call deactivates the first line-in from the runtime.
 12.  Second call activates the new line-in and updates ``active_linein_id()``.

end_line_in() (6):
 13.  No-op when not in LINE_IN mode (no exception raised).
 14.  ``active_content()`` returns IDLE after ``end_line_in()`` (no fallback).
 15.  ``active_content()`` returns FALLBACK after ``end_line_in()`` (fallback
      configured); fallback playback begins.
 16.  ``active_linein_id()`` returns ``None`` after ``end_line_in()``.
 17.  ``end_line_in()`` calls ``runtime.deactivate()`` with the correct ID.
 18.  ``end_line_in()`` is a no-op when called twice.

active_linein_id() (2):
 19.  Returns ``None`` on a fresh QueueManager.
 20.  Returns the correct ID while in LINE_IN mode.

Track-change guard during LINE_IN mode (2):
 21.  Queue-exhaustion event during LINE_IN mode does NOT start the fallback.
 22.  ``active_content()`` stays LINE_IN after a spurious exhaustion event.
"""

from __future__ import annotations

import time
import threading
from typing import List

import pytest

from playout.engine_interface import QueueItem, PlayoutState
from playout.engine_mock import MockPlayoutEngine
from playout.fallback import FallbackQueue
from playout.queue_manager import ContentKind, QueueManager
from playout.scheduler import StartMode

from audio.linein.domain import LineIn
from audio.linein._runtime import ActivationResult, StubLineInRuntime


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TICK = 0.05  # simulated track duration (seconds)


def _item(item_id: str = "t1", duration: float = TICK * 10) -> QueueItem:
    return QueueItem(id=item_id, uri=f"file:///{item_id}.mp3", duration=duration)


def _fallback_q(*ids: str, loop: bool = True) -> FallbackQueue:
    return FallbackQueue(items=[_item(i) for i in ids], loop=loop)


def _engine() -> MockPlayoutEngine:
    return MockPlayoutEngine(default_track_duration=TICK)


def _qm(engine: MockPlayoutEngine | None = None) -> QueueManager:
    return QueueManager(engine or _engine())


def _linein(
    linein_id: str = "li-uuid-001",
    name: str = "Drum Kit",
    device_id: str = "dev-usb-1",
    channels: tuple[int, ...] = (0, 1),
) -> LineIn:
    return LineIn(
        id=linein_id,
        name=name,
        device_id=device_id,
        channel_mapping=channels,
        enabled=True,
    )


# ---------------------------------------------------------------------------
# 1–2  ContentKind extension
# ---------------------------------------------------------------------------

def test_content_kind_line_in_value():
    assert ContentKind.LINE_IN.value == "line_in"


def test_content_kind_line_in_distinct():
    others = {ContentKind.IDLE, ContentKind.SHOW, ContentKind.FALLBACK}
    assert ContentKind.LINE_IN not in others


# ---------------------------------------------------------------------------
# 3–7  go_to_line_in() — success path
# ---------------------------------------------------------------------------

def test_go_to_line_in_returns_success_result():
    qm      = _qm()
    runtime = StubLineInRuntime()
    li      = _linein()
    result  = qm.go_to_line_in(li, runtime)
    assert isinstance(result, ActivationResult)
    assert result.success is True


def test_go_to_line_in_sets_active_content_to_line_in():
    qm      = _qm()
    runtime = StubLineInRuntime()
    qm.go_to_line_in(_linein(), runtime)
    assert qm.active_content() == ContentKind.LINE_IN


def test_go_to_line_in_engine_is_stopped():
    engine  = _engine()
    qm      = QueueManager(engine)
    # Start a show so the engine is playing
    qm.start_show([_item()], StartMode.HARD)
    runtime = StubLineInRuntime()
    qm.go_to_line_in(_linein(), runtime)
    assert engine.get_state() == PlayoutState.STOPPED


def test_go_to_line_in_active_linein_id_set():
    qm      = _qm()
    runtime = StubLineInRuntime()
    li      = _linein(linein_id="specific-uuid")
    qm.go_to_line_in(li, runtime)
    assert qm.active_linein_id() == "specific-uuid"


def test_go_to_line_in_fallback_does_not_start(monkeypatch):
    """After a successful go_to_line_in, fallback must not start."""
    engine  = _engine()
    qm      = QueueManager(engine)
    qm.set_fallback(_fallback_q("filler"))

    # Start the fallback so it's configured and active
    qm.end_show()  # triggers fallback after idle show
    time.sleep(TICK * 3)  # let fallback start

    runtime = StubLineInRuntime()
    qm.go_to_line_in(_linein(), runtime)

    # Give any daemon threads a moment to fire (there should be none)
    time.sleep(TICK * 3)
    assert qm.active_content() == ContentKind.LINE_IN
    assert engine.get_state() == PlayoutState.STOPPED


# ---------------------------------------------------------------------------
# 8–10  go_to_line_in() — failure path
# ---------------------------------------------------------------------------

def test_go_to_line_in_failure_returns_failure_result():
    qm      = _qm()
    runtime = StubLineInRuntime()
    li      = _linein(linein_id="bad-id")
    runtime.set_fail("bad-id")
    result  = qm.go_to_line_in(li, runtime)
    assert result.success is False
    assert result.failed  is True


def test_go_to_line_in_failure_no_fallback_gives_idle():
    qm      = _qm()
    runtime = StubLineInRuntime()
    li      = _linein(linein_id="bad-id")
    runtime.set_fail("bad-id")
    qm.go_to_line_in(li, runtime)
    assert qm.active_content() == ContentKind.IDLE


def test_go_to_line_in_failure_with_fallback_gives_fallback():
    engine  = _engine()
    qm      = QueueManager(engine)
    qm.set_fallback(_fallback_q("f1"))

    runtime = StubLineInRuntime()
    li      = _linein(linein_id="bad-id")
    runtime.set_fail("bad-id")
    qm.go_to_line_in(li, runtime)

    # Allow fallback daemon thread to start
    deadline = time.monotonic() + 1.0
    while qm.active_content() != ContentKind.FALLBACK and \
            time.monotonic() < deadline:
        time.sleep(TICK)

    assert qm.active_content() == ContentKind.FALLBACK


# ---------------------------------------------------------------------------
# 11–12  go_to_line_in() — source swap
# ---------------------------------------------------------------------------

def test_go_to_line_in_swap_deactivates_previous():
    qm      = _qm()
    runtime = StubLineInRuntime()
    li_a    = _linein(linein_id="li-a")
    li_b    = _linein(linein_id="li-b")

    qm.go_to_line_in(li_a, runtime)
    assert runtime.is_active("li-a")

    qm.go_to_line_in(li_b, runtime)
    # Previous line-in must have been deactivated
    assert not runtime.is_active("li-a")


def test_go_to_line_in_swap_activates_new():
    qm      = _qm()
    runtime = StubLineInRuntime()
    li_a    = _linein(linein_id="li-a")
    li_b    = _linein(linein_id="li-b")

    qm.go_to_line_in(li_a, runtime)
    qm.go_to_line_in(li_b, runtime)

    assert runtime.is_active("li-b")
    assert qm.active_linein_id() == "li-b"


# ---------------------------------------------------------------------------
# 13–18  end_line_in()
# ---------------------------------------------------------------------------

def test_end_line_in_when_not_in_line_in_mode_is_noop():
    qm = _qm()
    # Must not raise
    qm.end_line_in()
    assert qm.active_content() == ContentKind.IDLE


def test_end_line_in_no_fallback_gives_idle():
    qm      = _qm()
    runtime = StubLineInRuntime()
    qm.go_to_line_in(_linein(), runtime)
    qm.end_line_in()
    assert qm.active_content() == ContentKind.IDLE


def test_end_line_in_with_fallback_gives_fallback():
    engine  = _engine()
    qm      = QueueManager(engine)
    qm.set_fallback(_fallback_q("f1"))

    runtime = StubLineInRuntime()
    qm.go_to_line_in(_linein(), runtime)
    qm.end_line_in()

    # Allow daemon thread to start fallback
    deadline = time.monotonic() + 1.0
    while qm.active_content() != ContentKind.FALLBACK and \
            time.monotonic() < deadline:
        time.sleep(TICK)

    assert qm.active_content() == ContentKind.FALLBACK


def test_end_line_in_clears_active_linein_id():
    qm      = _qm()
    runtime = StubLineInRuntime()
    qm.go_to_line_in(_linein(linein_id="gone"), runtime)
    qm.end_line_in()
    assert qm.active_linein_id() is None


def test_end_line_in_deactivates_runtime():
    qm      = _qm()
    runtime = StubLineInRuntime()
    li      = _linein(linein_id="li-x")
    qm.go_to_line_in(li, runtime)
    assert runtime.is_active("li-x")

    qm.end_line_in()
    assert not runtime.is_active("li-x")


def test_end_line_in_twice_is_noop():
    qm      = _qm()
    runtime = StubLineInRuntime()
    qm.go_to_line_in(_linein(), runtime)
    qm.end_line_in()
    # Second call — must not raise
    qm.end_line_in()
    assert qm.active_content() == ContentKind.IDLE


# ---------------------------------------------------------------------------
# 19–20  active_linein_id()
# ---------------------------------------------------------------------------

def test_active_linein_id_none_initially():
    assert _qm().active_linein_id() is None


def test_active_linein_id_set_while_line_in_active():
    qm      = _qm()
    runtime = StubLineInRuntime()
    li      = _linein(linein_id="my-uuid")
    qm.go_to_line_in(li, runtime)
    assert qm.active_linein_id() == "my-uuid"


# ---------------------------------------------------------------------------
# 21–22  Track-change guard during LINE_IN mode
# ---------------------------------------------------------------------------

def test_track_exhaustion_in_line_in_mode_does_not_start_fallback():
    """
    Queue exhaustion while LINE_IN active must NOT trigger the fallback.

    We simulate this by directly invoking the internal callback with a
    "current_item=None" event, as the MockPlayoutEngine does when stop() fires.
    """
    from playout.engine_interface import TrackChangedEvent

    engine  = _engine()
    qm      = QueueManager(engine)
    qm.set_fallback(_fallback_q("f1"))

    runtime = StubLineInRuntime()
    qm.go_to_line_in(_linein(), runtime)

    # Simulate a spurious queue-exhaustion callback (e.g. from a late timer)
    qm._on_engine_track_change(
        TrackChangedEvent(previous_item=_item("t1"), current_item=None)
    )
    # Give any daemon thread a chance to fire (there should be none)
    time.sleep(TICK * 3)

    assert engine.get_state() == PlayoutState.STOPPED
    assert not qm.fallback_is_active()


def test_active_content_stays_line_in_after_spurious_exhaustion():
    from playout.engine_interface import TrackChangedEvent

    engine  = _engine()
    qm      = QueueManager(engine)
    qm.set_fallback(_fallback_q("f1"))

    runtime = StubLineInRuntime()
    qm.go_to_line_in(_linein(), runtime)

    qm._on_engine_track_change(
        TrackChangedEvent(previous_item=_item("t1"), current_item=None)
    )
    time.sleep(TICK * 3)

    assert qm.active_content() == ContentKind.LINE_IN
