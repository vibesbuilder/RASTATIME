"""
T16.3 — Background job implementation unit tests.

All 24 tests are pure Python — no Django, no Celery, no audio hardware.
Dependencies are injected as stubs or simple callables so that every job
can be exercised without the full application stack.

Test inventory
--------------
DeviceStartupCheckJob (4):
  1.  Returns JobResult when no manager is configured (graceful skip).
  2.  Returns success=True with no error_message when all devices present.
  3.  Returns success=True with "degraded" in error_message for missing device.
  4.  Returns success=False when the startup check raises unexpectedly.

NowPlayingPushJob (5):
  5.  Returns JobResult when neither state nor push_fn configured (skip).
  6.  Returns JobResult when push_fn is None (skip).
  7.  Does not call push_fn when nothing is playing.
  8.  Calls push_fn with to_dict() payload when a track is on air.
  9.  Does NOT call push_fn twice for the same track (de-duplication).

SchedulePollJob (4):
 10.  Returns JobResult when no client configured (skip).
 11.  Calls list_schedule() on the injected client.
 12.  Passes decoded schedule list to on_schedule_data callback.
 13.  Returns success=False when client raises.

PodcastFetchJob (3):
 14.  Returns JobResult when no client configured (skip).
 15.  Calls trigger_task_manager() on the injected client.
 16.  Returns success=False when client raises.

LibraryScanJob (3):
 17.  Returns JobResult when no client configured (skip).
 18.  Calls trigger_task_manager() on the injected client.
 19.  Returns success=False when client raises.

MediaCleanupJob (5):
 20.  Returns JobResult when no tmp_dir configured (skip).
 21.  Returns JobResult when tmp_dir does not exist (skip).
 22.  Removes files older than max_age_hours.
 23.  Leaves files newer than max_age_hours untouched.
 24.  Returns success=False when a file cannot be deleted.

(24 tests total, all pure Python)
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, call

import pytest

from backend.rastatime_worker.jobs._base import Job, JobResult, JobTrigger
from backend.rastatime_worker.jobs._inventory import (
    DeviceStartupCheckJob,
    LibraryScanJob,
    MediaCleanupJob,
    NowPlayingPushJob,
    PodcastFetchJob,
    SchedulePollJob,
)


# ---------------------------------------------------------------------------
# Stub helpers — AudioDeviceManager + SoundcardSettings
# ---------------------------------------------------------------------------

from audio.soundcard.interface import AudioDevice, AudioDeviceKind, AudioDeviceManager
from audio.soundcard.settings_model import SoundcardSettings


class StubDeviceManager(AudioDeviceManager):
    """
    Minimal AudioDeviceManager stub that returns a fixed device list.
    All abstract methods are implemented as no-ops so the ABC can be
    instantiated without a real audio driver.
    """

    def __init__(
        self,
        outputs: list[AudioDevice] | None = None,
        inputs: list[AudioDevice] | None = None,
    ) -> None:
        self._outputs = outputs or []
        self._inputs  = inputs  or []

    # ---- Enumeration (used by check_devices_at_startup) ------------------

    def list_outputs(self) -> list[AudioDevice]:
        return list(self._outputs)

    def list_inputs(self) -> list[AudioDevice]:
        return list(self._inputs)

    # ---- Remaining abstract methods — no-ops required by the ABC ---------

    def get_default_output(self) -> Optional[AudioDevice]:
        return None

    def get_default_input(self) -> Optional[AudioDevice]:
        return None

    def resolve_stable_id(self, stable_id: str) -> Optional[AudioDevice]:
        return None

    def lookup_by_stable_id(self, stable_id: str) -> Optional[AudioDevice]:
        return None

    def open_output(self, stable_id: str) -> None:
        pass

    def close_output(self, stable_id: str) -> None:
        pass

    def open_input(self, stable_id: str) -> None:
        pass

    def close_input(self, stable_id: str) -> None:
        pass


def _make_output(stable_id: str = "out_1") -> AudioDevice:
    return AudioDevice(
        stable_id=stable_id,
        name=f"Output {stable_id}",
        kind=AudioDeviceKind.OUTPUT,
        channels=2,
        driver="WASAPI",
    )


def _make_input(stable_id: str = "in_1") -> AudioDevice:
    return AudioDevice(
        stable_id=stable_id,
        name=f"Input {stable_id}",
        kind=AudioDeviceKind.INPUT,
        channels=2,
        driver="WASAPI",
    )


# ---------------------------------------------------------------------------
# Stub helpers — NowPlayingState
# ---------------------------------------------------------------------------

class _FakeItem:
    """Minimal QueueItem-like stub."""

    def __init__(self, item_id: str = "track_001") -> None:
        self.id    = item_id
        self.uri   = f"file:///music/{item_id}.mp3"
        self.title = f"Title {item_id}"
        self.artist = "Test Artist"
        self.duration = 180.0
        self.metadata = {}


class _FakeEntry:
    """Minimal NowPlayingEntry-like stub."""

    def __init__(self, item: _FakeItem | None = None) -> None:
        self.item = item

    @property
    def is_playing(self) -> bool:
        return self.item is not None

    def to_dict(self) -> dict:
        if self.item is None:
            return {"is_playing": False, "item": None, "started_at": None}
        return {
            "is_playing": True,
            "item": {"id": self.item.id, "title": self.item.title},
            "started_at": None,
        }


class _FakeState:
    """Minimal NowPlayingState stub."""

    def __init__(self, entry: _FakeEntry | None = None) -> None:
        self._entry = entry or _FakeEntry()

    def get(self) -> _FakeEntry:
        return self._entry


# ---------------------------------------------------------------------------
# Stub helpers — API client
# ---------------------------------------------------------------------------

class _StubApiClient:
    """Minimal API client stub recording calls."""

    def __init__(self, schedule: list | None = None) -> None:
        self._schedule         = schedule or []
        self.trigger_calls     = 0
        self.list_schedule_called = False

    def trigger_task_manager(self) -> None:
        self.trigger_calls += 1

    def list_schedule(self) -> "_StubResponse":
        self.list_schedule_called = True
        return _StubResponse(self._schedule)


class _StubResponse:
    def __init__(self, data: list) -> None:
        self._data = data

    def json(self) -> list:
        return self._data


class _RaisingApiClient:
    """API client that raises on every method call."""

    def trigger_task_manager(self) -> None:
        raise ConnectionError("server unreachable")

    def list_schedule(self):
        raise ConnectionError("server unreachable")


# ---------------------------------------------------------------------------
# 1–4  DeviceStartupCheckJob
# ---------------------------------------------------------------------------

def test_device_startup_skips_when_no_manager(monkeypatch):
    """Job must return a successful JobResult when no device manager is available.

    RASTATIME 2026-10-02 - pin the process-wide registry to "no manager":
    once Django is set up for the session (tests/unit/conftest.py),
    soundcard/apps.py registers the real device manager, and the job
    would go on to read the settings from the dev database instead of
    skipping.
    """
    import audio.soundcard._registry as _reg  # noqa: PLC0415
    monkeypatch.setattr(_reg, "default_manager", None)

    job    = DeviceStartupCheckJob()  # no deps injected
    result = job.run()
    assert isinstance(result, JobResult)
    assert result.success is True
    assert result.error_message is not None
    assert "skipped" in result.error_message.lower()


def test_device_startup_success_all_devices_present():
    """All configured devices available → success, no error_message."""
    settings = SoundcardSettings(
        main_output_id="out_1",
        preview_output_id=None,
        line_in_device_ids=[],
    )
    manager = StubDeviceManager(outputs=[_make_output("out_1")])
    job     = DeviceStartupCheckJob(manager=manager, settings=settings)
    result  = job.run()
    assert result.success is True
    assert result.error_message is None


def test_device_startup_degraded_when_device_missing():
    """Missing configured output → success=True but 'degraded' in error_message."""
    settings = SoundcardSettings(
        main_output_id="out_MISSING",
        preview_output_id=None,
        line_in_device_ids=[],
    )
    # Manager returns no outputs → configured device is absent.
    manager = StubDeviceManager(outputs=[])
    job     = DeviceStartupCheckJob(manager=manager, settings=settings)
    result  = job.run()
    assert result.success is True
    assert result.error_message is not None
    assert "degraded" in result.error_message.lower()
    assert "out_MISSING" in result.error_message


def test_device_startup_failure_on_unexpected_exception():
    """If check_devices_at_startup raises, job returns success=False."""

    class _BrokenManager(StubDeviceManager):
        def list_outputs(self):
            raise RuntimeError("driver crash")

    settings = SoundcardSettings(
        main_output_id="out_1",
        preview_output_id=None,
        line_in_device_ids=[],
    )
    manager = _BrokenManager()
    job     = DeviceStartupCheckJob(manager=manager, settings=settings)
    result  = job.run()
    assert result.success is False
    assert result.error_message is not None


# ---------------------------------------------------------------------------
# 5–9  NowPlayingPushJob
# ---------------------------------------------------------------------------

def test_now_playing_skips_when_no_state_and_no_push_fn():
    """No deps at all → JobResult(success=True, skipped)."""
    job    = NowPlayingPushJob()
    result = job.run()
    assert isinstance(result, JobResult)
    assert result.success is True
    assert "skipped" in (result.error_message or "").lower()


def test_now_playing_skips_when_push_fn_is_none():
    """State present but no push_fn → skipped."""
    state  = _FakeState(_FakeEntry(_FakeItem()))
    job    = NowPlayingPushJob(state=state, push_fn=None)
    result = job.run()
    assert result.success is True
    assert "skipped" in (result.error_message or "").lower()


def test_now_playing_does_not_push_when_idle():
    """Nothing playing → push_fn must not be called."""
    pushes: list[dict] = []
    state  = _FakeState(_FakeEntry(item=None))   # idle
    job    = NowPlayingPushJob(state=state, push_fn=pushes.append)
    result = job.run()
    assert result.success is True
    assert len(pushes) == 0


def test_now_playing_pushes_when_track_playing():
    """Track on air → push_fn called with the to_dict() payload."""
    pushes: list[dict] = []
    item   = _FakeItem("abc123")
    state  = _FakeState(_FakeEntry(item=item))
    job    = NowPlayingPushJob(state=state, push_fn=pushes.append)
    result = job.run()
    assert result.success is True
    assert len(pushes) == 1
    payload = pushes[0]
    assert payload["is_playing"] is True
    assert payload["item"]["id"] == "abc123"


def test_now_playing_no_duplicate_push_for_same_track():
    """push_fn must be called only once for the same track ID."""
    pushes: list[dict] = []
    item   = _FakeItem("abc123")
    state  = _FakeState(_FakeEntry(item=item))
    job    = NowPlayingPushJob(state=state, push_fn=pushes.append)

    job.run()   # first tick — should push
    job.run()   # second tick — same track, must NOT push again
    job.run()   # third tick — still same track

    assert len(pushes) == 1, "push_fn must be called only once per unique track"


# ---------------------------------------------------------------------------
# 10–13  SchedulePollJob
# ---------------------------------------------------------------------------

def test_schedule_poll_skips_when_no_client():
    """No API client → JobResult(success=True, skipped)."""
    job    = SchedulePollJob()
    result = job.run()
    assert isinstance(result, JobResult)
    assert result.success is True
    assert "skipped" in (result.error_message or "").lower()


def test_schedule_poll_calls_list_schedule():
    """When a client is injected, list_schedule() must be called."""
    client = _StubApiClient(schedule=[{"id": 1}, {"id": 2}])
    job    = SchedulePollJob(api_client=client)
    result = job.run()
    assert result.success is True
    assert client.list_schedule_called is True


def test_schedule_poll_delivers_items_to_callback():
    """Decoded schedule list must be passed to on_schedule_data callback."""
    received: list[list] = []
    schedule = [{"id": 10}, {"id": 20}]
    client   = _StubApiClient(schedule=schedule)
    job      = SchedulePollJob(
        api_client=client,
        on_schedule_data=received.append,
    )
    job.run()
    assert len(received) == 1
    assert received[0] == schedule


def test_schedule_poll_returns_failure_on_client_exception():
    """Client raising → JobResult(success=False, error_message set)."""
    job    = SchedulePollJob(api_client=_RaisingApiClient())
    result = job.run()
    assert result.success is False
    assert result.error_message is not None


# ---------------------------------------------------------------------------
# 14–16  PodcastFetchJob
# ---------------------------------------------------------------------------

def test_podcast_fetch_skips_when_no_client():
    job    = PodcastFetchJob()
    result = job.run()
    assert isinstance(result, JobResult)
    assert result.success is True
    assert "skipped" in (result.error_message or "").lower()


def test_podcast_fetch_triggers_task_manager():
    client = _StubApiClient()
    job    = PodcastFetchJob(api_client=client)
    result = job.run()
    assert result.success is True
    assert client.trigger_calls == 1


def test_podcast_fetch_returns_failure_on_exception():
    job    = PodcastFetchJob(api_client=_RaisingApiClient())
    result = job.run()
    assert result.success is False
    assert result.error_message is not None


# ---------------------------------------------------------------------------
# 17–19  LibraryScanJob
# ---------------------------------------------------------------------------

def test_library_scan_skips_when_no_client():
    job    = LibraryScanJob()
    result = job.run()
    assert isinstance(result, JobResult)
    assert result.success is True
    assert "skipped" in (result.error_message or "").lower()


def test_library_scan_triggers_task_manager():
    client = _StubApiClient()
    job    = LibraryScanJob(api_client=client)
    result = job.run()
    assert result.success is True
    assert client.trigger_calls == 1


def test_library_scan_returns_failure_on_exception():
    job    = LibraryScanJob(api_client=_RaisingApiClient())
    result = job.run()
    assert result.success is False
    assert result.error_message is not None


# ---------------------------------------------------------------------------
# 20–24  MediaCleanupJob
# ---------------------------------------------------------------------------

def test_media_cleanup_skips_when_no_tmp_dir():
    job    = MediaCleanupJob()
    result = job.run()
    assert isinstance(result, JobResult)
    assert result.success is True
    assert "skipped" in (result.error_message or "").lower()


def test_media_cleanup_skips_when_directory_missing(tmp_path):
    nonexistent = str(tmp_path / "no_such_dir")
    job    = MediaCleanupJob(tmp_dir=nonexistent)
    result = job.run()
    assert result.success is True
    assert "skipped" in (result.error_message or "").lower()


def test_media_cleanup_removes_old_files(tmp_path):
    """Files older than max_age_hours must be deleted."""
    old_file = tmp_path / "old.tmp"
    old_file.write_text("stale data")
    # Back-date the modification time by 48 hours.
    old_mtime = time.time() - 48 * 3600
    os.utime(old_file, (old_mtime, old_mtime))

    job    = MediaCleanupJob(tmp_dir=str(tmp_path), max_age_hours=24)
    result = job.run()

    assert result.success is True
    assert not old_file.exists(), "old file should have been removed"


def test_media_cleanup_leaves_fresh_files(tmp_path):
    """Files newer than max_age_hours must NOT be deleted."""
    fresh_file = tmp_path / "fresh.tmp"
    fresh_file.write_text("current data")
    # mtime defaults to now — no backdating needed.

    job    = MediaCleanupJob(tmp_dir=str(tmp_path), max_age_hours=24)
    result = job.run()

    assert result.success is True
    assert fresh_file.exists(), "fresh file must not be removed"


def test_media_cleanup_reports_failure_on_permission_error(tmp_path, monkeypatch):
    """If unlink() raises, job returns success=False with error_message."""
    old_file = tmp_path / "locked.tmp"
    old_file.write_text("locked")
    old_mtime = time.time() - 48 * 3600
    os.utime(old_file, (old_mtime, old_mtime))

    # Patch Path.unlink to raise PermissionError.
    original_unlink = Path.unlink

    def _raise_permission(self, missing_ok=False):
        raise PermissionError(f"access denied: {self}")

    monkeypatch.setattr(Path, "unlink", _raise_permission)

    job    = MediaCleanupJob(tmp_dir=str(tmp_path), max_age_hours=24)
    result = job.run()

    assert result.success is False
    assert result.error_message is not None
    assert "error" in result.error_message.lower()
