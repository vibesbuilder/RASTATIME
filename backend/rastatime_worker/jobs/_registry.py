"""
T16.1 — Background job registry.

Mirrors the pattern of :mod:`audio.soundcard._registry` and
:mod:`audio.linein._registry`: a module-level ``default_registry`` that is
populated at import time by :mod:`~backend.rastatime_worker.jobs._inventory`.

The registry is the authoritative list of all jobs that the background runner
(:mod:`backend.rastatime_worker.runner`, T16.2) will execute.  At startup the
runner queries the registry to build its STARTUP job list and its INTERVAL
job schedule.

Usage (runner)::

    from backend.rastatime_worker.jobs._registry import default_registry
    from backend.rastatime_worker.jobs._base import JobTrigger

    for job in default_registry.by_trigger(JobTrigger.STARTUP):
        job.run()

    for job in default_registry.by_trigger(JobTrigger.INTERVAL):
        schedule_periodic(job, every=job.interval_seconds)

Usage (tests)::

    from backend.rastatime_worker.jobs._registry import JobRegistry
    from backend.rastatime_worker.jobs._base import JobTrigger

    reg = JobRegistry()   # fresh, isolated registry — does not share state
    reg.register(my_job)
    assert reg.get("my_job") is my_job
"""

from __future__ import annotations

from typing import Optional

from ._base import Job, JobTrigger

# ---------------------------------------------------------------------------
# JobRegistry
# ---------------------------------------------------------------------------


class JobRegistry:
    """
    Registry of :class:`~._base.Job` instances.

    Jobs are keyed by their :attr:`~._base.Job.name`.  Registering a job with
    a duplicate name replaces the previous entry (last writer wins).

    The module-level :data:`default_registry` is pre-populated by
    :mod:`~backend.rastatime_worker.jobs._inventory`.  Tests should create
    their own isolated ``JobRegistry()`` instances to avoid shared state.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, job: Job) -> None:
        """
        Register *job* in this registry.

        If a job with the same :attr:`~._base.Job.name` already exists it is
        silently replaced.

        Parameters
        ----------
        job:
            A concrete :class:`~._base.Job` instance.
        """
        self._jobs[job.name] = job

    def unregister(self, name: str) -> bool:
        """
        Remove the job identified by *name*.

        Returns ``True`` if a job was removed, ``False`` if *name* was not
        registered.

        Parameters
        ----------
        name:
            The :attr:`~._base.Job.name` of the job to remove.
        """
        if name in self._jobs:
            del self._jobs[name]
            return True
        return False

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def get(self, name: str) -> Optional[Job]:
        """
        Return the registered job with *name*, or ``None`` if not found.

        Parameters
        ----------
        name:
            The :attr:`~._base.Job.name` to look up.
        """
        return self._jobs.get(name)

    def all(self) -> list[Job]:
        """
        Return a snapshot list of all registered jobs.

        The order reflects registration order (Python 3.7+ dict insertion
        order is guaranteed).
        """
        return list(self._jobs.values())

    def by_trigger(self, trigger: JobTrigger) -> list[Job]:
        """
        Return all jobs whose :attr:`~._base.Job.trigger` matches *trigger*.

        Parameters
        ----------
        trigger:
            The :class:`~._base.JobTrigger` to filter by.
        """
        return [j for j in self._jobs.values() if j.trigger == trigger]

    def names(self) -> list[str]:
        """Return a snapshot list of all registered job names."""
        return list(self._jobs.keys())

    def __len__(self) -> int:
        return len(self._jobs)

    def __contains__(self, name: str) -> bool:
        return name in self._jobs


# ---------------------------------------------------------------------------
# Module-level default registry (populated by _inventory.py on import)
# ---------------------------------------------------------------------------

default_registry = JobRegistry()
"""
The process-level job registry.

Pre-populated with all known jobs when
:mod:`backend.rastatime_worker.jobs._inventory` is imported.
The background runner reads this registry at startup.

Test code should create fresh :class:`JobRegistry` instances to avoid
shared state.
"""
