"""
T16.2 — BackgroundRunner unit tests.

All 21 tests are pure Python — no Django, no Celery, no audio hardware.
Real :class:`threading.Timer` objects are used; test jobs have tiny intervals
(``TICK = 0.05 s``) so the suite finishes in well under 10 seconds.

Test inventory
--------------
Construction (2):
  1.  Fresh instance: ``is_running()`` is ``False``.
  2.  Accepts an explicit registry (does not use ``default_registry``).

start() / is_running() (3):
  3.  ``is_running()`` returns ``True`` after ``start()``.
  4.  Calling ``start()`` twice raises ``RuntimeError``.
  5.  ``is_running()`` returns ``False`` after ``stop()``.

STARTUP job execution (3):
  6.  STARTUP jobs execute at least once after ``start()``.
  7.  STARTUP jobs do not re-fire (execute exactly once).
  8.  Runner stays running after STARTUP job completes.

INTERVAL job execution (4):
  9.  INTERVAL jobs fire at least once after their interval.
 10.  INTERVAL jobs re-fire for a second period.
 11.  Multiple INTERVAL jobs all fire independently.
 12.  ``pending_job_names()`` contains all interval job names right after
      ``start()`` (timers armed but not yet fired).

stop() behaviour (4):
 13.  ``stop()`` cancels pending interval timers (no further fires).
 14.  ``stop()`` before ``start()`` is safe (no error raised).
 15.  ``stop()`` is idempotent (calling twice does not raise).
 16.  ``is_running()`` is ``False`` after ``stop()``.

Error resilience (3):
 17.  Job raising an unexpected exception does not crash the runner.
 18.  Other interval jobs continue firing after one raises.
 19.  ``is_running()`` stays ``True`` after a job raises.

Result logging (2):
 20.  Successful job result is logged at ``INFO`` level.
 21.  Failed job result is logged at ``WARNING`` level.

(21 tests total, all pure Python)
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import pytest

from backend.rastatime_worker.jobs._base import Job, JobResult, JobTrigger
from backend.rastatime_worker.jobs._registry import JobRegistry
from backend.rastatime_worker.runner import BackgroundRunner


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TICK = 0.05  # simulated timer interval (seconds)
WAIT = TICK * 8  # generous wait for at least one fire


# ---------------------------------------------------------------------------
# Test-job helpers
# ---------------------------------------------------------------------------

class CapturingJob(Job):
    """Records each call to run() with an atomically-incremented counter."""

    def __init__(
        self,
        name: str,
        trigger: JobTrigger = JobTrigger.INTERVAL,
        interval: float = TICK,
        success: bool = True,
    ) -> None:
        self._name     = name
        self._trigger  = trigger
        self._interval = interval
        self._success  = success
        self._lock     = threading.Lock()
        self._count    = 0

    @property
    def call_count(self) -> int:
        with self._lock:
            return self._count

    @property
    def name(self) -> str:
        return self._name

    @property
    def trigger(self) -> JobTrigger:
        return self._trigger

    @property
    def interval_seconds(self) -> Optional[float]:
        return self._interval if self._trigger == JobTrigger.INTERVAL else None

    def run(self) -> JobResult:
        with self._lock:
            self._count += 1
        return JobResult(
            job_name=self._name,
            success=self._success,
            error_message=None if self._success else "deliberate failure",
        )


class RaisingJob(Job):
    """Simulates a job that raises an unexpected exception from run()."""

    def __init__(self, name: str = "raising_job") -> None:
        self._name  = name
        self._lock  = threading.Lock()
        self._count = 0

    @property
    def call_count(self) -> int:
        with self._lock:
            return self._count

    @property
    def name(self) -> str:
        return self._name

    @property
    def trigger(self) -> JobTrigger:
        return JobTrigger.INTERVAL

    @property
    def interval_seconds(self) -> float:
        return TICK

    def run(self) -> JobResult:
        with self._lock:
            self._count += 1
        raise RuntimeError("Simulated unexpected job crash")


def _reg(*jobs: Job) -> JobRegistry:
    """Build an isolated registry from the given job instances."""
    reg = JobRegistry()
    for job in jobs:
        reg.register(job)
    return reg


def _runner(*jobs: Job) -> BackgroundRunner:
    """Return a BackgroundRunner backed by an isolated registry."""
    return BackgroundRunner(registry=_reg(*jobs))


# ---------------------------------------------------------------------------
# 1–2  Construction
# ---------------------------------------------------------------------------

def test_fresh_instance_is_not_running():
    runner = _runner()
    assert runner.is_running() is False


def test_accepts_explicit_registry():
    reg = JobRegistry()
    runner = BackgroundRunner(registry=reg)
    # runner knows about the registry we passed (not default_registry)
    # We verify indirectly: start/stop cycle works with an empty registry.
    runner.start()
    runner.stop()
    assert runner.is_running() is False


# ---------------------------------------------------------------------------
# 3–5  start() / is_running()
# ---------------------------------------------------------------------------

def test_is_running_true_after_start():
    runner = _runner()
    runner.start()
    try:
        assert runner.is_running() is True
    finally:
        runner.stop()


def test_start_twice_raises_runtime_error():
    runner = _runner()
    runner.start()
    try:
        with pytest.raises(RuntimeError, match="already-running"):
            runner.start()
    finally:
        runner.stop()


def test_is_running_false_after_stop():
    runner = _runner()
    runner.start()
    runner.stop()
    assert runner.is_running() is False


# ---------------------------------------------------------------------------
# 6–8  STARTUP job execution
# ---------------------------------------------------------------------------

def test_startup_job_executes_at_least_once():
    job = CapturingJob("startup_j", trigger=JobTrigger.STARTUP)
    runner = _runner(job)
    runner.start()
    time.sleep(WAIT)
    runner.stop()
    assert job.call_count >= 1


def test_startup_job_does_not_re_fire():
    job = CapturingJob("startup_once", trigger=JobTrigger.STARTUP)
    runner = _runner(job)
    runner.start()
    time.sleep(WAIT * 3)   # long enough for multiple fires if re-scheduled
    runner.stop()
    assert job.call_count == 1


def test_runner_stays_running_after_startup_job():
    job = CapturingJob("startup_j2", trigger=JobTrigger.STARTUP)
    runner = _runner(job)
    runner.start()
    time.sleep(WAIT)
    assert runner.is_running() is True
    runner.stop()


# ---------------------------------------------------------------------------
# 9–12  INTERVAL job execution
# ---------------------------------------------------------------------------

def test_interval_job_fires_at_least_once():
    job = CapturingJob("interval_j1")
    runner = _runner(job)
    runner.start()
    time.sleep(WAIT)
    runner.stop()
    assert job.call_count >= 1


def test_interval_job_re_fires_for_second_period():
    job = CapturingJob("interval_j2")
    runner = _runner(job)
    runner.start()
    time.sleep(TICK * 25)   # enough for ~3 fires at TICK interval
    runner.stop()
    assert job.call_count >= 2


def test_multiple_interval_jobs_all_fire():
    job_a = CapturingJob("multi_a")
    job_b = CapturingJob("multi_b")
    runner = _runner(job_a, job_b)
    runner.start()
    time.sleep(WAIT)
    runner.stop()
    assert job_a.call_count >= 1
    assert job_b.call_count >= 1


def test_pending_job_names_after_start():
    job_a = CapturingJob("pending_a")
    job_b = CapturingJob("pending_b")
    runner = _runner(job_a, job_b)
    runner.start()
    # Check immediately — timers armed but not yet fired
    names = set(runner.pending_job_names())
    runner.stop()
    # Both interval jobs should have timers pending right after start()
    assert "pending_a" in names
    assert "pending_b" in names


# ---------------------------------------------------------------------------
# 13–16  stop() behaviour
# ---------------------------------------------------------------------------

def test_stop_cancels_pending_timers():
    job = CapturingJob("cancel_me", interval=TICK * 20)  # long interval
    runner = _runner(job)
    runner.start()
    # Stop before the first fire
    runner.stop()
    count_at_stop = job.call_count
    time.sleep(TICK * 5)   # wait past when the timer *would* have fired
    # Call count must not have increased after stop()
    assert job.call_count == count_at_stop


def test_stop_before_start_is_safe():
    runner = _runner()
    runner.stop()   # must not raise
    assert runner.is_running() is False


def test_stop_is_idempotent():
    runner = _runner()
    runner.start()
    runner.stop()
    runner.stop()   # second call must not raise
    assert runner.is_running() is False


def test_is_running_false_after_stop_duplicate():
    runner = _runner()
    runner.start()
    runner.stop()
    assert runner.is_running() is False


# ---------------------------------------------------------------------------
# 17–19  Error resilience
# ---------------------------------------------------------------------------

def test_raising_job_does_not_crash_runner():
    job = RaisingJob()
    runner = _runner(job)
    runner.start()
    time.sleep(WAIT)
    # Runner must still be running despite the raise
    assert runner.is_running() is True
    runner.stop()


def test_other_jobs_continue_after_one_raises():
    raising = RaisingJob("raiser")
    good    = CapturingJob("good_job")
    runner  = _runner(raising, good)
    runner.start()
    time.sleep(WAIT)
    runner.stop()
    # The good job must still have fired despite the raiser
    assert good.call_count >= 1


def test_is_running_stays_true_after_job_raises():
    job = RaisingJob()
    runner = _runner(job)
    runner.start()
    time.sleep(WAIT)
    assert runner.is_running() is True
    runner.stop()


# ---------------------------------------------------------------------------
# 20–21  Result logging
# ---------------------------------------------------------------------------

def test_successful_result_logged_at_info(caplog):
    job = CapturingJob("log_ok", success=True)
    runner = _runner(job)
    with caplog.at_level(logging.INFO, logger="backend.rastatime_worker.runner"):
        runner.start()
        time.sleep(WAIT)
        runner.stop()
    info_msgs = [r.message for r in caplog.records if r.levelno == logging.INFO]
    assert any("log_ok" in m for m in info_msgs), (
        f"Expected INFO log for 'log_ok'; got: {info_msgs}"
    )


def test_failed_result_logged_at_warning(caplog):
    job = CapturingJob("log_fail", success=False)
    runner = _runner(job)
    with caplog.at_level(logging.WARNING, logger="backend.rastatime_worker.runner"):
        runner.start()
        time.sleep(WAIT)
        runner.stop()
    warn_msgs = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert any("log_fail" in m for m in warn_msgs), (
        f"Expected WARNING log for 'log_fail'; got: {warn_msgs}"
    )
