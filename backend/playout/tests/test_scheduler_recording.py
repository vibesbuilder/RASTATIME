"""
RASTATIME 2026-05-28 — Unit tests for PlayoutScheduler's per-show
recording hooks (Phase-C5 Teil 2c + Teil 2d cleanup).

Recording is owned by Liquidsoap: driven by
``engine.recording_start(path)`` / ``engine.recording_stop()`` over
the same telnet that drives play/stop on the LiquidsoapPlayoutEngine.

The legacy FfmpegRecorder + mpv/VLC engine recording path was deleted
in C5 Teil 2d (2026-05-28); the mpv engine itself on 2026-09-10.

We build a minimal PlayoutScheduler with mocked dependencies and call
``_on_show_record_start`` / ``_on_show_record_end`` with synthetic
events — asserting:

  * In Liquidsoap mode, ``engine.recording_start`` / ``_stop`` are
    called with the correct path conversions (Windows backslash →
    forward slash) and no lifecycle thread is spawned.
  * Failure modes (no folder, bad show_name, telnet down) are logged
    and silently skipped, not raised — the show plays normally even
    when the recording fails to start.
  * Constructor in Liquidsoap mode sends the initial sentinel-
    silencing ``recording.stop``.
  * Shutdown in Liquidsoap mode calls ``engine.recording_stop()``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from rastatime_playout.engine.liquidsoap_engine import LiquidsoapPlayoutEngine
from rastatime_playout.player.events import EventKind, ShowRecordEvent

# ---- Helpers -----------------------------------------------------------


def _make_show_record_event(
    *,
    type_: EventKind = EventKind.SHOW_RECORD_START,
    show_id: int = 42,
    show_name: str = "Morning Show",
    starts_at: datetime = datetime(2026, 5, 28, 9, 0),
    duration_seconds: int = 3600,
) -> ShowRecordEvent:
    """Build a ShowRecordEvent for testing without going through the API."""
    from datetime import timedelta

    end_at = starts_at + timedelta(seconds=duration_seconds)
    return ShowRecordEvent(
        type=type_,
        start=starts_at,
        end=end_at,
        show_id=show_id,
        show_name=show_name,
        show_starts_at=starts_at,
    )


# ---- Fixtures -----------------------------------------------------------


@pytest.fixture
def liquidsoap_scheduler(tmp_path):
    """
    PlayoutScheduler with a mocked
    LiquidsoapPlayoutEngine (so engine.recording_start / _stop exist on
    the mock per spec=).  api_client.session.get returns a recording-
    folder pointing at tmp_path so build_output_path produces a real
    Path under the test's tmp directory.
    """
    from rastatime_playout.playout_scheduler import PlayoutScheduler

    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    api_client = MagicMock()

    # Mock the API client to return our tmp_path as the recording folder.
    api_resp = MagicMock()
    api_resp.status_code = 200
    api_resp.json.return_value = {"folder": str(tmp_path)}
    api_client.session.get.return_value = api_resp

    sched = PlayoutScheduler(
        engine=engine,
        api_client=api_client,
    )
    return sched, engine, tmp_path


# ---- Constructor behaviour ---------------------------------------------


def test_constructor_liquidsoap_silences_sentinel_via_engine_recording_stop(
    liquidsoap_scheduler,
):
    """Constructor sends one recording_stop to silence the boot sentinel."""
    _sched, engine, _ = liquidsoap_scheduler
    engine.recording_stop.assert_called_once_with()


def test_constructor_liquidsoap_tolerates_engine_recording_stop_failure(tmp_path):
    """
    Initial recording_stop may fail (Liquidsoap not ready yet at startup
    race); the constructor must NOT raise — sentinel-file silencing is
    best-effort.
    """
    from rastatime_playout.playout_scheduler import PlayoutScheduler

    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    engine.recording_stop.side_effect = ConnectionError("liquidsoap not up yet")
    api_client = MagicMock()

    PlayoutScheduler(
        engine=engine,
        api_client=api_client,
    )
    engine.recording_stop.assert_called_once_with()


# ---- _on_show_record_start happy path -----------------------------------


def test_liquidsoap_record_start_calls_engine_with_forward_slash_path(
    liquidsoap_scheduler,
):
    """Happy path: engine.recording_start called with forward-slash path."""
    sched, engine, _ = liquidsoap_scheduler

    event = _make_show_record_event(
        show_id=42,
        show_name="Morning Show",
        starts_at=datetime(2026, 5, 28, 9, 0),
    )

    # Reset the constructor-time call so we only see the show-record call.
    engine.recording_stop.reset_mock()
    engine.recording_start.reset_mock()

    sched._on_show_record_start("evt-key-1", event)

    engine.recording_start.assert_called_once()
    called_path = engine.recording_start.call_args[0][0]
    # Forward-slash form only (no Windows backslashes on the wire).
    assert "\\" not in called_path
    assert "/" in called_path
    # Show name appears verbatim (sanitised to keep spaces).
    assert "Morning Show" in called_path
    # MP3 extension.
    assert called_path.endswith(".mp3")
    # Date prefix derived from show_starts_at (year sanity-check; full
    # local-TZ formatting is tested in ffmpeg_recorder.build_output_path).
    assert "2026" in called_path


def test_liquidsoap_record_start_creates_parent_directory(liquidsoap_scheduler):
    """The per-day subdirectory must be created (output.file does not auto-mkdir)."""
    sched, engine, _ = liquidsoap_scheduler
    event = _make_show_record_event(
        show_id=1,
        show_name="X",
        starts_at=datetime(2026, 5, 28, 14, 0),
    )
    engine.recording_stop.reset_mock()
    engine.recording_start.reset_mock()

    sched._on_show_record_start("k", event)

    called_path = engine.recording_start.call_args[0][0]
    # Convert back to Windows path form so pathlib can stat the parent.
    parent_dir = Path(called_path.replace("/", "\\")).parent
    assert parent_dir.exists() and parent_dir.is_dir()


def test_liquidsoap_record_start_does_not_spawn_lifecycle_thread(liquidsoap_scheduler):
    """
    No FfmpegRecorder lifecycle thread is needed in the Liquidsoap path —
    Liquidsoap's output.file has no HTTP-source-warmup-404 to retry around
    and no mid-show watchdog respawn (the bus-tap can't network-flap).
    """
    sched, engine, _ = liquidsoap_scheduler
    engine.recording_stop.reset_mock()
    engine.recording_start.reset_mock()

    with patch("rastatime_playout.playout_scheduler.threading.Thread") as mock_thread:
        event = _make_show_record_event()
        sched._on_show_record_start("k", event)

    mock_thread.assert_not_called()
    engine.recording_start.assert_called_once()


# ---- _on_show_record_start failure modes -------------------------------


def test_liquidsoap_record_start_skips_when_no_folder_configured(
    liquidsoap_scheduler,
):
    """If the API returns an empty folder, skip the engine call."""
    sched, engine, _ = liquidsoap_scheduler

    api_resp = MagicMock()
    api_resp.status_code = 200
    api_resp.json.return_value = {"folder": ""}
    sched._api_client.session.get.return_value = api_resp

    engine.recording_stop.reset_mock()
    engine.recording_start.reset_mock()

    event = _make_show_record_event()
    sched._on_show_record_start("k", event)

    engine.recording_start.assert_not_called()


def test_liquidsoap_record_start_skips_when_api_returns_error(
    liquidsoap_scheduler,
):
    """If the API call fails (e.g. 500), skip engine call gracefully."""
    sched, engine, _ = liquidsoap_scheduler

    api_resp = MagicMock()
    api_resp.status_code = 500
    sched._api_client.session.get.return_value = api_resp

    engine.recording_stop.reset_mock()
    engine.recording_start.reset_mock()

    event = _make_show_record_event()
    sched._on_show_record_start("k", event)

    engine.recording_start.assert_not_called()


def test_liquidsoap_record_start_handles_telnet_failure_gracefully(
    liquidsoap_scheduler,
):
    """
    If engine.recording_start raises ConnectionError (telnet down,
    Liquidsoap crashed), log and swallow — no scheduler-level crash.
    """
    sched, engine, _ = liquidsoap_scheduler
    engine.recording_stop.reset_mock()
    engine.recording_start.reset_mock()
    engine.recording_start.side_effect = ConnectionError("telnet down")

    event = _make_show_record_event()
    # Must NOT raise.
    sched._on_show_record_start("k", event)

    engine.recording_start.assert_called_once()


# ---- _on_show_record_end behaviour --------------------------------------


def test_liquidsoap_record_end_calls_engine_recording_stop(liquidsoap_scheduler):
    """End handler calls engine.recording_stop in Liquidsoap mode."""
    sched, engine, _ = liquidsoap_scheduler
    engine.recording_stop.reset_mock()

    event = _make_show_record_event(type_=EventKind.SHOW_RECORD_END)
    sched._on_show_record_end("k", event)

    engine.recording_stop.assert_called_once_with()


def test_liquidsoap_record_end_handles_telnet_failure_gracefully(
    liquidsoap_scheduler,
):
    """ConnectionError on stop must not propagate (logged + swallowed)."""
    sched, engine, _ = liquidsoap_scheduler
    engine.recording_stop.reset_mock()
    engine.recording_stop.side_effect = ConnectionError("telnet gone")

    event = _make_show_record_event(type_=EventKind.SHOW_RECORD_END)
    # Must NOT raise.
    sched._on_show_record_end("k", event)

    engine.recording_stop.assert_called_once_with()


def test_liquidsoap_record_end_does_not_spawn_post_roll_timer(liquidsoap_scheduler):
    """
    Liquidsoap-bus-tap recording has no HTTP-source-buffering lag — the
    legacy FfmpegRecorder's 1 s post-roll Timer is unnecessary here.
    """
    sched, engine, _ = liquidsoap_scheduler
    engine.recording_stop.reset_mock()

    with patch("rastatime_playout.playout_scheduler.threading.Timer") as mock_timer:
        event = _make_show_record_event(type_=EventKind.SHOW_RECORD_END)
        sched._on_show_record_end("k", event)

    mock_timer.assert_not_called()
    engine.recording_stop.assert_called_once_with()


# ---- Shutdown behaviour -------------------------------------------------


def test_liquidsoap_shutdown_calls_engine_recording_stop(liquidsoap_scheduler):
    """Shutdown in Liquidsoap mode routes recording-stop through the engine."""
    sched, engine, _ = liquidsoap_scheduler
    engine.recording_stop.reset_mock()

    sched.shutdown()

    engine.recording_stop.assert_called_once_with()


def test_liquidsoap_shutdown_tolerates_engine_recording_stop_failure(
    liquidsoap_scheduler,
):
    """If recording_stop raises during shutdown, the rest of shutdown still completes."""
    sched, engine, _ = liquidsoap_scheduler
    engine.recording_stop.reset_mock()
    engine.recording_stop.side_effect = RuntimeError("nope")

    # Must NOT raise — shutdown logs + continues.
    sched.shutdown()

    engine.recording_stop.assert_called_once_with()


# ---- RASTATIME 2026-10-18 - recording extension follows the rendered encoder


def test_show_record_start_uses_rendered_extension(tmp_path):
    """The file name takes the extension of the encoder Liquidsoap runs with."""
    from datetime import datetime

    from rastatime_playout.playout_scheduler import PlayoutScheduler

    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    api_client = MagicMock()
    api_resp = MagicMock()
    api_resp.status_code = 200
    api_resp.json.return_value = {"folder": str(tmp_path), "format": "mp3"}
    api_client.session.get.return_value = api_resp
    sched = PlayoutScheduler(
        engine=engine,
        api_client=api_client,
        recording_extension=lambda: "opus",
    )
    event = _make_show_record_event(
        show_id=7,
        show_name="Morning Show",
        starts_at=datetime(2026, 10, 18, 10, 0),
    )
    sched._on_show_record_start("evt-key-opus", event)
    engine.recording_start.assert_called_once()
    called_path = engine.recording_start.call_args[0][0]
    assert called_path.endswith(".opus")


def test_recording_extension_lookup_failure_falls_back_to_mp3(tmp_path):
    from rastatime_playout.playout_scheduler import PlayoutScheduler

    def boom():
        raise RuntimeError("no render yet")

    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    sched = PlayoutScheduler(
        engine=engine,
        api_client=MagicMock(),
        recording_extension=boom,
    )
    assert sched._recording_file_extension() == "mp3"


# ---- RASTATIME 2026-10-19 - file name carries seconds (operator wish)


def test_build_output_path_has_seconds(tmp_path):
    from datetime import datetime, timezone

    from rastatime_playout.recording_path import build_output_path

    starts = datetime(2026, 10, 19, 10, 5, 7, tzinfo=UTC)
    out = build_output_path(tmp_path, starts, "A & B / C", extension="opus")
    local = starts.astimezone()
    assert out.name == local.strftime("%Y-%m-%d %H-%M-%S") + " - A & B _ C.opus"
    assert out.parent.name == local.strftime("%Y-%m-%d")


# ---- RASTATIME 2026-10-19: copy show recordings into the library ----------


def _recording_scheduler(tmp_path, with_v1=True):
    """Scheduler with a mocked engine, a recording folder at tmp_path and
    (optionally) a legacy v1 client whose notify_recording_finished is a mock."""
    from rastatime_playout.playout_scheduler import PlayoutScheduler

    engine = MagicMock(spec=LiquidsoapPlayoutEngine)
    api_client = MagicMock()
    api_resp = MagicMock()
    api_resp.status_code = 200
    api_resp.json.return_value = {"folder": str(tmp_path)}
    api_client.session.get.return_value = api_resp
    v1 = MagicMock() if with_v1 else None
    sched = PlayoutScheduler(engine=engine, api_client=api_client, api_client_v1=v1)
    sched._recording_settle_poll_seconds = 0.01
    sched._recording_settle_max_seconds = 0.5
    sched._recording_report_retry_seconds = 0.01
    return sched, engine, v1


def _join_report_threads():
    import threading

    for t in threading.enumerate():
        if t.name.startswith("recording-finished-"):
            t.join(timeout=5)


def test_record_events_carry_the_instance_id():
    """generate_show_record_events puts cc_show_instances.id on both events."""
    from rastatime_playout.player.schedule import generate_show_record_events

    events = {}
    generate_show_record_events(
        events,
        {"id": 4711, "starts_at": "2026-10-19T08:07:00", "ends_at": "2026-10-19T08:15:00"},
        {"id": 212, "name": "Event Calendar"},
    )
    assert len(events) == 2
    assert {e.instance_id for e in events.values()} == {4711}
    assert {e.type for e in events.values()} == {
        EventKind.SHOW_RECORD_START,
        EventKind.SHOW_RECORD_END,
    }


def test_record_end_reports_the_closed_file_to_legacy(tmp_path):
    """start remembers (instance, path); end stops, waits for a stable file
    and POSTs recording-finished with the instance id and the path."""
    sched, engine, v1 = _recording_scheduler(tmp_path)
    start = _make_show_record_event(
        show_id=212, show_name="Event Calendar", starts_at=datetime(2026, 10, 19, 8, 7)
    )
    start.instance_id = 4711
    sched._on_show_record_start("k-start", start)
    assert sched._open_show_recording is not None
    inst, path = sched._open_show_recording
    assert inst == 4711
    assert path.name.endswith(" - Event Calendar.mp3")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * 100)

    end = _make_show_record_event(
        type_=EventKind.SHOW_RECORD_END,
        show_id=212,
        show_name="Event Calendar",
        starts_at=datetime(2026, 10, 19, 8, 7),
    )
    end.instance_id = 4711
    sched._on_show_record_end("k-end", end)
    _join_report_threads()

    engine.recording_stop.assert_called()
    v1.notify_recording_finished.assert_called_once()
    kwargs = v1.notify_recording_finished.call_args.kwargs
    assert kwargs["instance_id"] == 4711
    assert kwargs["path"] == str(path)
    assert sched._open_show_recording is None


def test_record_end_retries_the_report_three_times(tmp_path):
    sched, engine, v1 = _recording_scheduler(tmp_path)
    v1.notify_recording_finished.side_effect = ConnectionError("legacy down")
    sched._open_show_recording = (99, tmp_path / "r.mp3")
    (tmp_path / "r.mp3").write_bytes(b"abc")
    end = _make_show_record_event(type_=EventKind.SHOW_RECORD_END)
    end.instance_id = 99
    sched._on_show_record_end("k-end", end)
    _join_report_threads()
    assert v1.notify_recording_finished.call_count == 3


def test_record_end_without_open_recording_or_client_is_quiet(tmp_path):
    """A PLAYOUT restarted mid-show knows no path; no v1 client -> no report."""
    sched, engine, v1 = _recording_scheduler(tmp_path)
    end = _make_show_record_event(type_=EventKind.SHOW_RECORD_END)
    end.instance_id = 5
    sched._on_show_record_end("k-end", end)  # nothing open
    _join_report_threads()
    v1.notify_recording_finished.assert_not_called()

    sched2, engine2, _ = _recording_scheduler(tmp_path, with_v1=False)
    sched2._open_show_recording = (5, tmp_path / "x.mp3")
    sched2._on_show_record_end("k-end", end)  # no client: no crash
    assert sched2._open_show_recording is None


def test_record_start_failure_leaves_no_open_recording(tmp_path):
    sched, engine, v1 = _recording_scheduler(tmp_path)
    engine.recording_start.side_effect = ConnectionError("telnet down")
    start = _make_show_record_event()
    start.instance_id = 1
    sched._on_show_record_start("k", start)
    assert sched._open_show_recording is None
