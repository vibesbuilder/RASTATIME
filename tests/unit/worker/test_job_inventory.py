"""
T16.1 — Background job inventory unit tests.

All 22 tests are pure Python — no Django, no Celery, no audio hardware.

Test inventory
--------------
JobTrigger (2):
  1.  Has exactly three members: STARTUP, INTERVAL, EVENT.
  2.  Values are distinct non-empty strings.

JobResult (5):
  3.  ``failed`` is the inverse of ``success``.
  4.  ``success=False`` sets ``failed=True``.
  5.  ``error_message`` defaults to ``None``.
  6.  ``job_name`` and ``duration_seconds`` are preserved.
  7.  Frozen — mutating any field raises.

Job ABC (3):
  8.  Cannot instantiate ``Job`` directly (abstract).
  9.  Subclass missing ``run()`` cannot be instantiated.
 10.  Subclass missing ``name`` cannot be instantiated.

JobRegistry (6):
 11.  Empty registry has length 0.
 12.  ``register()`` adds the job; ``len()`` increases.
 13.  ``get()`` returns the registered job by name.
 14.  ``get()`` returns ``None`` for an unknown name.
 15.  ``by_trigger()`` returns only jobs with the matching trigger.
 16.  ``unregister()`` removes a job and returns ``True``; unknown name
      returns ``False``.

Job stubs — metadata (6):
 17.  All stub job names are non-empty, unique strings.
 18.  All INTERVAL stubs have ``interval_seconds > 0``.
 19.  STARTUP stubs have ``interval_seconds is None``.
 20.  ``run()`` raises ``NotImplementedError`` for every stub.
 21.  All stubs are present in ``default_registry``.
 22.  ``default_registry`` contains at least one STARTUP job and at least
      three INTERVAL jobs.

(22 tests total, all pure Python)
"""

from __future__ import annotations

import pytest

from backend.rastatime_worker.jobs._base import Job, JobResult, JobTrigger
from backend.rastatime_worker.jobs._registry import JobRegistry
from backend.rastatime_worker.jobs._inventory import (
    DeviceStartupCheckJob,
    LibraryScanJob,
    MediaCleanupJob,
    NowPlayingPushJob,
    PodcastFetchJob,
    SchedulePollJob,
    _ALL_JOBS,
)
from backend.rastatime_worker.jobs._registry import default_registry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_job(
    name: str = "test_job",
    trigger: JobTrigger = JobTrigger.INTERVAL,
    interval: float = 10.0,
) -> Job:
    """Return a minimal concrete Job for registry tests."""

    class _MinimalJob(Job):
        @property
        def name(self) -> str:
            return name

        @property
        def trigger(self) -> JobTrigger:
            return trigger

        @property
        def interval_seconds(self):
            return interval if trigger == JobTrigger.INTERVAL else None

        def run(self) -> JobResult:
            return JobResult(job_name=self.name, success=True)

    return _MinimalJob()


# ---------------------------------------------------------------------------
# 1–2  JobTrigger
# ---------------------------------------------------------------------------

def test_job_trigger_has_three_members():
    members = {t.name for t in JobTrigger}
    assert members == {"STARTUP", "INTERVAL", "EVENT"}


def test_job_trigger_values_are_distinct_strings():
    values = [t.value for t in JobTrigger]
    assert len(values) == len(set(values))
    assert all(isinstance(v, str) and v for v in values)


# ---------------------------------------------------------------------------
# 3–7  JobResult
# ---------------------------------------------------------------------------

def test_job_result_failed_is_inverse_of_success_true():
    r = JobResult(job_name="x", success=True)
    assert r.failed is False


def test_job_result_failed_is_inverse_of_success_false():
    r = JobResult(job_name="x", success=False)
    assert r.failed is True


def test_job_result_error_message_defaults_to_none():
    r = JobResult(job_name="x", success=True)
    assert r.error_message is None


def test_job_result_fields_preserved():
    r = JobResult(job_name="my_job", success=False,
                  error_message="oops", duration_seconds=1.23)
    assert r.job_name == "my_job"
    assert r.error_message == "oops"
    assert r.duration_seconds == pytest.approx(1.23)


def test_job_result_is_frozen():
    r = JobResult(job_name="x", success=True)
    with pytest.raises((AttributeError, TypeError)):
        r.success = False          # type: ignore[misc]


# ---------------------------------------------------------------------------
# 8–10  Job ABC
# ---------------------------------------------------------------------------

def test_job_abc_cannot_be_instantiated():
    with pytest.raises(TypeError):
        Job()                      # type: ignore[abstract]


def test_job_subclass_missing_run_cannot_be_instantiated():
    class NoRun(Job):
        @property
        def name(self) -> str:
            return "no_run"

        @property
        def trigger(self) -> JobTrigger:
            return JobTrigger.INTERVAL

    with pytest.raises(TypeError):
        NoRun()                    # type: ignore[abstract]


def test_job_subclass_missing_name_cannot_be_instantiated():
    class NoName(Job):
        @property
        def trigger(self) -> JobTrigger:
            return JobTrigger.INTERVAL

        def run(self) -> JobResult:
            return JobResult(job_name="x", success=True)

    with pytest.raises(TypeError):
        NoName()                   # type: ignore[abstract]


# ---------------------------------------------------------------------------
# 11–16  JobRegistry
# ---------------------------------------------------------------------------

def test_registry_empty_initially():
    reg = JobRegistry()
    assert len(reg) == 0
    assert reg.all() == []


def test_registry_register_increases_length():
    reg = JobRegistry()
    reg.register(_minimal_job("a"))
    assert len(reg) == 1


def test_registry_get_returns_registered_job():
    reg = JobRegistry()
    job = _minimal_job("my_job")
    reg.register(job)
    assert reg.get("my_job") is job


def test_registry_get_unknown_name_returns_none():
    reg = JobRegistry()
    assert reg.get("does_not_exist") is None


def test_registry_by_trigger_filters_correctly():
    reg = JobRegistry()
    reg.register(_minimal_job("a", JobTrigger.INTERVAL))
    reg.register(_minimal_job("b", JobTrigger.STARTUP))
    reg.register(_minimal_job("c", JobTrigger.INTERVAL))

    interval_jobs = reg.by_trigger(JobTrigger.INTERVAL)
    startup_jobs  = reg.by_trigger(JobTrigger.STARTUP)

    assert len(interval_jobs) == 2
    assert len(startup_jobs)  == 1
    assert all(j.trigger == JobTrigger.INTERVAL for j in interval_jobs)


def test_registry_unregister_removes_and_returns_true():
    reg = JobRegistry()
    reg.register(_minimal_job("del_me"))
    assert reg.unregister("del_me") is True
    assert reg.get("del_me") is None


def test_registry_unregister_unknown_returns_false():
    reg = JobRegistry()
    assert reg.unregister("ghost") is False


# ---------------------------------------------------------------------------
# 17–22  Job stubs — metadata & default_registry
# ---------------------------------------------------------------------------

_STUB_CLASSES = [
    DeviceStartupCheckJob,
    SchedulePollJob,
    NowPlayingPushJob,
    PodcastFetchJob,
    LibraryScanJob,
    MediaCleanupJob,
]

_STUB_INSTANCES = [cls() for cls in _STUB_CLASSES]


def test_stub_names_are_unique_non_empty_strings():
    names = [j.name for j in _STUB_INSTANCES]
    assert all(isinstance(n, str) and n for n in names), "all names must be non-empty strings"
    assert len(names) == len(set(names)), "all names must be unique"


def test_interval_stubs_have_positive_interval_seconds():
    interval_jobs = [j for j in _STUB_INSTANCES if j.trigger == JobTrigger.INTERVAL]
    assert interval_jobs, "at least one INTERVAL stub must exist"
    for j in interval_jobs:
        assert j.interval_seconds is not None, f"{j.name}: interval_seconds is None"
        assert j.interval_seconds > 0, f"{j.name}: interval_seconds must be > 0"


def test_startup_stubs_have_none_interval_seconds():
    startup_jobs = [j for j in _STUB_INSTANCES if j.trigger == JobTrigger.STARTUP]
    assert startup_jobs, "at least one STARTUP stub must exist"
    for j in startup_jobs:
        assert j.interval_seconds is None, (
            f"{j.name}: STARTUP job must have interval_seconds=None"
        )


def test_stub_run_returns_job_result():
    """
    T16.3 — all run() implementations return JobResult (no longer raise).

    With no dependencies injected (no-arg construction) every job skips
    gracefully and returns a JobResult.  success=True is expected for
    graceful-skip returns.
    """
    for j in _STUB_INSTANCES:
        result = j.run()
        assert isinstance(result, JobResult), (
            f"{j.name}.run() must return JobResult, got {type(result)!r}"
        )


def test_all_stubs_present_in_default_registry():
    for j in _STUB_INSTANCES:
        assert j.name in default_registry, (
            f"'{j.name}' is not registered in default_registry"
        )


def test_default_registry_has_startup_and_interval_jobs():
    startup  = default_registry.by_trigger(JobTrigger.STARTUP)
    interval = default_registry.by_trigger(JobTrigger.INTERVAL)

    assert len(startup)  >= 1, "expected at least one STARTUP job in default_registry"
    assert len(interval) >= 3, "expected at least three INTERVAL jobs in default_registry"
