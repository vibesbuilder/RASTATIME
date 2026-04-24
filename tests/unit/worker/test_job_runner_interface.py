"""
T2.4 validation — JobRunner interface.

Verifies that:
1. JobRunner cannot be instantiated directly.
2. Incomplete subclasses cannot be instantiated.
3. A complete subclass can be instantiated and behaves correctly.
4. All types (JobStatus, JobInfo, JobResult, exceptions) work as expected.
"""

import pytest
from datetime import datetime, timezone

from backend.rastatime_worker.interface import (
    JobId,
    JobInfo,
    JobNameNotRegisteredError,
    JobNotFoundError,
    JobResult,
    JobRunner,
    JobStatus,
)


# ---------------------------------------------------------------------------
# JobStatus
# ---------------------------------------------------------------------------

def test_job_status_values():
    values = {s.value for s in JobStatus}
    assert values == {
        "pending", "running", "completed", "failed", "cancelled", "retrying"
    }


# ---------------------------------------------------------------------------
# JobInfo and JobResult
# ---------------------------------------------------------------------------

def test_job_info_defaults():
    info = JobInfo(
        job_id="j1",
        job_name="media_scan",
        status=JobStatus.PENDING,
        submitted_at=datetime.now(timezone.utc),
    )
    assert info.started_at is None
    assert info.finished_at is None
    assert info.retry_count == 0
    assert info.error_message is None
    assert info.kwargs == {}


def test_job_result_success():
    result = JobResult(job_id="j1", success=True, value=42)
    assert result.success is True
    assert result.value == 42
    assert result.error_message is None


def test_job_result_failure():
    result = JobResult(job_id="j2", success=False, error_message="timeout")
    assert result.success is False
    assert result.error_message == "timeout"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

def test_job_not_found_error():
    err = JobNotFoundError("j-999")
    assert err.job_id == "j-999"
    assert "j-999" in str(err)
    with pytest.raises(JobNotFoundError):
        raise err


def test_job_name_not_registered_error():
    err = JobNameNotRegisteredError("unknown_job")
    assert err.job_name == "unknown_job"
    assert "unknown_job" in str(err)
    with pytest.raises(JobNameNotRegisteredError):
        raise err


# ---------------------------------------------------------------------------
# Instantiation guards
# ---------------------------------------------------------------------------

def test_abstract_runner_cannot_be_instantiated():
    with pytest.raises(TypeError):
        JobRunner()  # type: ignore[abstract]


def test_incomplete_subclass_cannot_be_instantiated():
    class Incomplete(JobRunner):
        pass

    with pytest.raises(TypeError):
        Incomplete()


# ---------------------------------------------------------------------------
# Minimal concrete stub
# ---------------------------------------------------------------------------

class _StubRunner(JobRunner):
    def __init__(self):
        self._handlers: dict = {}
        self._jobs: dict = {}
        self._schedules: dict = {}
        self._running = False

    def register(self, job_name, handler, *, max_retries=0, retry_delay_seconds=60.0):
        self._handlers[job_name] = handler

    def registered_jobs(self):
        return list(self._handlers)

    def submit(self, job_name, **kwargs):
        if job_name not in self._handlers:
            raise JobNameNotRegisteredError(job_name)
        job_id = f"job-{len(self._jobs)}"
        self._jobs[job_id] = JobInfo(
            job_id=job_id,
            job_name=job_name,
            status=JobStatus.PENDING,
            submitted_at=datetime.now(timezone.utc),
            kwargs=kwargs,
        )
        return job_id

    def schedule(self, job_name, cron, *, schedule_id=None, **kwargs):
        if job_name not in self._handlers:
            raise JobNameNotRegisteredError(job_name)
        sid = schedule_id or f"sched-{len(self._schedules)}"
        self._schedules[sid] = JobInfo(
            job_id=sid,
            job_name=job_name,
            status=JobStatus.PENDING,
            submitted_at=datetime.now(timezone.utc),
            kwargs={"cron": cron, **kwargs},
        )
        return sid

    def unschedule(self, schedule_id):
        self._schedules.pop(schedule_id, None)

    def list_schedules(self):
        return list(self._schedules.values())

    def status(self, job_id):
        if job_id in self._jobs:
            return self._jobs[job_id]
        if job_id in self._schedules:
            return self._schedules[job_id]
        raise JobNotFoundError(job_id)

    def result(self, job_id):
        info = self.status(job_id)
        if info.status not in (JobStatus.COMPLETED, JobStatus.FAILED):
            raise RuntimeError(f"Job {job_id} is not yet in a terminal state")
        return JobResult(job_id=job_id, success=info.status == JobStatus.COMPLETED)

    def cancel(self, job_id):
        if job_id not in self._jobs and job_id not in self._schedules:
            raise JobNotFoundError(job_id)
        if job_id in self._jobs:
            self._jobs[job_id].status = JobStatus.CANCELLED

    def start(self):
        self._running = True

    def stop(self, *, timeout_seconds=10.0):
        self._running = False


# ---------------------------------------------------------------------------
# Stub behaviour tests
# ---------------------------------------------------------------------------

def test_stub_runner_can_be_instantiated():
    runner = _StubRunner()
    assert runner.registered_jobs() == []


def test_register_and_list():
    runner = _StubRunner()
    runner.register("media_scan", lambda: None)
    runner.register("podcast_fetch", lambda: None)
    assert set(runner.registered_jobs()) == {"media_scan", "podcast_fetch"}


def test_submit_returns_job_id():
    runner = _StubRunner()
    runner.register("import_file", lambda file: None)
    job_id = runner.submit("import_file", file="/tmp/track.mp3")
    assert isinstance(job_id, str)
    assert len(job_id) > 0


def test_submit_unregistered_raises():
    runner = _StubRunner()
    with pytest.raises(JobNameNotRegisteredError):
        runner.submit("nonexistent_job")


def test_status_after_submit():
    runner = _StubRunner()
    runner.register("cleanup", lambda: None)
    job_id = runner.submit("cleanup")
    info = runner.status(job_id)
    assert info.status == JobStatus.PENDING
    assert info.job_name == "cleanup"


def test_status_unknown_job_raises():
    runner = _StubRunner()
    with pytest.raises(JobNotFoundError):
        runner.status("does-not-exist")


def test_cancel_job():
    runner = _StubRunner()
    runner.register("export", lambda: None)
    job_id = runner.submit("export")
    runner.cancel(job_id)
    assert runner.status(job_id).status == JobStatus.CANCELLED


def test_cancel_unknown_job_raises():
    runner = _StubRunner()
    with pytest.raises(JobNotFoundError):
        runner.cancel("ghost-id")


def test_schedule_and_list():
    runner = _StubRunner()
    runner.register("podcast_check", lambda: None)
    sid = runner.schedule("podcast_check", "0 * * * *", schedule_id="hourly-podcasts")
    assert sid == "hourly-podcasts"
    schedules = runner.list_schedules()
    assert any(s.job_id == "hourly-podcasts" for s in schedules)


def test_schedule_stable_id_roundtrip():
    runner = _StubRunner()
    runner.register("media_scan", lambda: None)
    sid = runner.schedule("media_scan", "*/15 * * * *", schedule_id="media-scan-15m")
    assert runner.status(sid).job_id == "media-scan-15m"


def test_unschedule():
    runner = _StubRunner()
    runner.register("cleanup", lambda: None)
    sid = runner.schedule("cleanup", "0 3 * * *", schedule_id="nightly-cleanup")
    runner.unschedule("nightly-cleanup")
    assert not any(s.job_id == sid for s in runner.list_schedules())


def test_start_stop_lifecycle():
    runner = _StubRunner()
    runner.start()
    assert runner._running is True
    runner.stop()
    assert runner._running is False
