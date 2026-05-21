"""
T16.1 — Background job abstractions.

Defines the three primitives that every RASTATIME background job must provide:

``JobTrigger``
    *When* should the job run: once at startup, on a fixed interval, or in
    response to an external event.

``JobResult``
    Immutable outcome of a single job execution.  Always returned — never
    raised — so callers can log and continue without try/except chains.

``Job``
    Abstract base class.  Concrete subclasses declare their ``name``,
    ``trigger``, and ``interval_seconds``, and implement ``run()``.

Design notes
------------
* **Never raises** — ``run()`` must catch all exceptions and return a
  ``JobResult(success=False, error_message=str(exc))``.  The runner must
  still guard with a broad try/except in case of implementation mistakes.
* **No Django dependency** — this module is importable in the root venv and
  in unit tests without a running application server.
* **No Celery dependency** — the explicit goal of Milestone M16 is to replace
  Celery with a lightweight Windows-native runner (T16.2).

Usage (typical concrete job)::

    from backend.rastatime_worker.jobs._base import Job, JobResult, JobTrigger

    class SchedulePollJob(Job):
        name             = "schedule_poll"
        trigger          = JobTrigger.INTERVAL
        interval_seconds = 30.0

        def run(self) -> JobResult:
            import time
            started = time.monotonic()
            try:
                _do_poll()
                return JobResult(
                    job_name=self.name,
                    success=True,
                    duration_seconds=time.monotonic() - started,
                )
            except Exception as exc:
                return JobResult(
                    job_name=self.name,
                    success=False,
                    error_message=str(exc),
                    duration_seconds=time.monotonic() - started,
                )
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# JobTrigger
# ---------------------------------------------------------------------------

class JobTrigger(str, Enum):
    """
    Describes *when* a background job should be executed.

    STARTUP
        Run exactly once when the background runner process starts.
        Use for one-shot initialisation tasks (device checks, warm-ups).
    INTERVAL
        Run repeatedly every :attr:`~Job.interval_seconds` seconds.
        The first execution fires ``interval_seconds`` after the runner
        starts, not immediately at startup.
    EVENT
        Run in response to an external trigger (API call, message queue
        message, OS signal).  The runner delivers a call to :meth:`Job.run`
        when the event fires; the job itself does not implement any polling.
    """

    STARTUP  = "startup"
    INTERVAL = "interval"
    EVENT    = "event"


# ---------------------------------------------------------------------------
# JobResult
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class JobResult:
    """
    Immutable outcome of a single :meth:`Job.run` execution.

    Every job execution produces exactly one ``JobResult``.  On success
    ``error_message`` is ``None``; on failure it carries the exception
    message or a human-readable explanation.

    Attributes
    ----------
    job_name:
        The :attr:`~Job.name` of the job that produced this result.
    success:
        ``True`` when the job completed without errors.
    error_message:
        Human-readable explanation of the failure; ``None`` on success.
    started_at:
        UTC timestamp of when the job started (set automatically).
    duration_seconds:
        Wall-clock time elapsed during :meth:`Job.run`, in seconds.
        ``0.0`` if not measured.
    """

    job_name:         str
    success:          bool
    error_message:    Optional[str] = None
    started_at:       datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    duration_seconds: float = 0.0

    @property
    def failed(self) -> bool:
        """``True`` when the job did *not* succeed (inverse of ``success``)."""
        return not self.success


# ---------------------------------------------------------------------------
# Job — abstract base class
# ---------------------------------------------------------------------------

class Job(ABC):
    """
    Abstract base class for all RASTATIME background jobs.

    Concrete subclasses must declare their ``name``, ``trigger``, and
    (for INTERVAL jobs) ``interval_seconds`` as class-level attributes, and
    must implement :meth:`run`.

    Contract
    --------
    * :meth:`run` **must never raise**.  It catches all exceptions internally
      and returns a :class:`JobResult` with ``success=False``.
    * :meth:`run` **must be thread-safe** — the runner may call it from a
      worker thread.
    * A job instance is **not re-entrant**: the runner will not call
      :meth:`run` again until the previous call returns.
    """

    # --- Metadata — override in subclasses ---------------------------------

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique job identifier used in logs, the registry, and the UI.

        Must be a non-empty, lowercase, underscore-separated ASCII string
        (e.g. ``"schedule_poll"``).
        """

    @property
    @abstractmethod
    def trigger(self) -> JobTrigger:
        """How/when this job should be triggered by the runner."""

    @property
    def interval_seconds(self) -> Optional[float]:
        """
        For :attr:`~JobTrigger.INTERVAL` jobs: the target period in seconds.

        Returns ``None`` for :attr:`~JobTrigger.STARTUP` and
        :attr:`~JobTrigger.EVENT` jobs.  Subclasses override this for
        ``INTERVAL`` jobs.
        """
        return None

    @property
    def description(self) -> str:
        """
        One-line human-readable description of what this job does.

        Optional.  Used in admin UIs and log summaries.  Defaults to the
        empty string; subclasses may override.
        """
        return ""

    # --- Execution ---------------------------------------------------------

    @abstractmethod
    def run(self) -> JobResult:
        """
        Execute the job and return its outcome.

        Implementations must:

        * Catch **all** exceptions and encode them as
          ``JobResult(success=False, error_message=...)``.
        * Record ``duration_seconds`` (wall-clock time of :meth:`run`).
        * Never block indefinitely — respect a reasonable timeout.

        Returns
        -------
        JobResult
            The outcome of this execution.
        """
