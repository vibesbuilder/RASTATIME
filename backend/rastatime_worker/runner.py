"""
T16.2 — Windows-compatible background task runner.

Replaces the Celery-based ``libretime_worker`` with a lightweight,
dependency-free runner built entirely on Python's standard library
(:mod:`threading`, :mod:`logging`).

Design
------
``BackgroundRunner`` manages two classes of jobs from a
:class:`~backend.rastatime_worker.jobs.JobRegistry`:

STARTUP jobs (:attr:`~backend.rastatime_worker.jobs.JobTrigger.STARTUP`)
    Each is executed exactly once in a daemon thread immediately when
    :meth:`BackgroundRunner.start` is called.

INTERVAL jobs (:attr:`~backend.rastatime_worker.jobs.JobTrigger.INTERVAL`)
    Each fires in a :class:`threading.Timer` daemon thread every
    :attr:`~backend.rastatime_worker.jobs.Job.interval_seconds`.
    After each execution the timer is rescheduled so the *next* fire is
    ``interval_seconds`` **after the previous run completed** — "fire and
    wait" semantics that prevent overlapping runs.

Concurrency model
-----------------
* Every job execution runs in its own daemon thread.
* A job is **not re-entrant**: the timer is not rescheduled until the
  previous call to :meth:`~backend.rastatime_worker.jobs.Job.run` returns.
* Daemon threads mean the OS process can exit cleanly even if a job is
  in mid-flight.

Error resilience
----------------
* The runner wraps every ``job.run()`` call in a broad ``try/except``.
  :meth:`~backend.rastatime_worker.jobs.Job.run` is *supposed* to catch its
  own exceptions (contract from T16.1), but the runner guards as a safety
  net.  A job that raises does not stop the runner or affect other jobs.
* Successful results are logged at ``INFO``; failed results at ``WARNING``.

Shutdown
--------
Calling :meth:`BackgroundRunner.stop` sets a :class:`threading.Event` that
all pending timers check before rescheduling.  All pending
:class:`threading.Timer` objects are cancelled immediately.  Jobs currently
executing in daemon threads run to completion naturally; the runner does not
join them (they are daemon threads and will be reaped by the OS on process
exit if they haven't finished by then).

Typical production usage::

    from backend.rastatime_worker.runner import BackgroundRunner

    runner = BackgroundRunner()   # uses default_registry
    runner.start()
    # ... service runs ...
    runner.stop()

Test usage (isolated registry with fast timers)::

    from backend.rastatime_worker.jobs._registry import JobRegistry
    from backend.rastatime_worker.runner import BackgroundRunner

    reg = JobRegistry()
    reg.register(MyFastJob())     # interval_seconds=0.05
    runner = BackgroundRunner(registry=reg)
    runner.start()
    time.sleep(0.2)
    runner.stop()
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

from .jobs._base import Job, JobResult, JobTrigger
from .jobs._registry import JobRegistry, default_registry

logger = logging.getLogger(__name__)


class BackgroundRunner:
    """
    Lightweight background task runner using :mod:`threading`.

    Parameters
    ----------
    registry:
        The :class:`~backend.rastatime_worker.jobs.JobRegistry` to draw
        jobs from.  Defaults to
        :data:`~backend.rastatime_worker.jobs._registry.default_registry`
        (pre-populated by
        :mod:`~backend.rastatime_worker.jobs._inventory`).
    """

    def __init__(self, registry: Optional[JobRegistry] = None) -> None:
        self._registry: JobRegistry = (
            registry if registry is not None else default_registry
        )
        self._stop_event  = threading.Event()
        self._lock        = threading.Lock()
        self._timers: dict[str, threading.Timer] = {}
        self._running     = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """
        Start the background runner.

        * Runs all :attr:`~backend.rastatime_worker.jobs.JobTrigger.STARTUP`
          jobs once in daemon threads.
        * Schedules all
          :attr:`~backend.rastatime_worker.jobs.JobTrigger.INTERVAL` jobs to
          fire after their ``interval_seconds``.

        Raises
        ------
        RuntimeError
            If :meth:`start` is called on an already-running instance.
            Call :meth:`stop` before calling :meth:`start` again.
        """
        if self._running:
            raise RuntimeError(
                "BackgroundRunner.start() called on an already-running instance. "
                "Call stop() first."
            )

        self._stop_event.clear()
        self._running = True
        logger.info("BackgroundRunner starting.")

        # --- STARTUP jobs ------------------------------------------------
        for job in self._registry.by_trigger(JobTrigger.STARTUP):
            thread = threading.Thread(
                target=self._run_startup_job,
                args=(job,),
                daemon=True,
                name=f"rastatime-worker-startup-{job.name}",
            )
            thread.start()
            logger.debug("STARTUP job '%s' dispatched.", job.name)

        # --- INTERVAL jobs -----------------------------------------------
        for job in self._registry.by_trigger(JobTrigger.INTERVAL):
            self._schedule_interval(job)
            logger.debug(
                "INTERVAL job '%s' scheduled (every %.1fs).",
                job.name, job.interval_seconds,
            )

        logger.info(
            "BackgroundRunner started: %d STARTUP, %d INTERVAL job(s).",
            len(self._registry.by_trigger(JobTrigger.STARTUP)),
            len(self._registry.by_trigger(JobTrigger.INTERVAL)),
        )

    def stop(self) -> None:
        """
        Stop the background runner.

        Signals the stop event, cancels all pending interval timers, and
        marks the runner as not running.  Safe to call before :meth:`start`
        (no-op) and safe to call more than once (idempotent).

        Jobs currently executing in daemon threads run to completion; the
        runner does not wait for them.
        """
        if not self._running:
            return  # not started yet — safe no-op

        logger.info("BackgroundRunner stopping.")
        self._stop_event.set()

        with self._lock:
            timers = list(self._timers.values())
            self._timers.clear()

        for timer in timers:
            timer.cancel()

        self._running = False
        logger.info("BackgroundRunner stopped. %d timer(s) cancelled.", len(timers))

    def is_running(self) -> bool:
        """Return ``True`` between :meth:`start` and :meth:`stop`."""
        return self._running

    def pending_job_names(self) -> list[str]:
        """
        Return the names of INTERVAL jobs that have a pending timer.

        A job's name is present here between successive runs (i.e. while its
        :class:`threading.Timer` is armed but has not yet fired).  During
        execution the timer is removed and re-added after the run completes.
        """
        with self._lock:
            return list(self._timers.keys())

    # ------------------------------------------------------------------
    # Internal — STARTUP execution
    # ------------------------------------------------------------------

    def _run_startup_job(self, job: Job) -> None:
        """Execute a STARTUP job and log its result.  Called in a daemon thread."""
        logger.debug("STARTUP job '%s' starting.", job.name)
        try:
            result = job.run()
            self._log_result(result)
        except Exception:  # noqa: BLE001
            logger.exception(
                "Unhandled exception in STARTUP job '%s' — job skipped.", job.name
            )

    # ------------------------------------------------------------------
    # Internal — INTERVAL scheduling
    # ------------------------------------------------------------------

    def _schedule_interval(self, job: Job) -> None:
        """
        Arm a :class:`threading.Timer` to fire *job* after its interval.

        No-op if the stop event is already set (runner is shutting down).
        """
        if self._stop_event.is_set():
            return

        interval = job.interval_seconds
        if interval is None or interval <= 0:
            logger.error(
                "INTERVAL job '%s' has invalid interval_seconds=%r — not scheduled.",
                job.name, interval,
            )
            return

        timer = threading.Timer(
            interval,
            self._fire_interval_job,
            args=(job,),
        )
        timer.daemon = True
        timer.name   = f"rastatime-worker-interval-{job.name}"

        with self._lock:
            self._timers[job.name] = timer

        timer.start()

    def _fire_interval_job(self, job: Job) -> None:
        """
        Execute *job* and reschedule it.  Called by the :class:`threading.Timer`.

        * Removes the fired timer from ``_timers``.
        * Runs ``job.run()``, catching all exceptions.
        * Reschedules via :meth:`_schedule_interval` (which is a no-op if the
          stop event is set, preventing further firings after :meth:`stop`).
        """
        if self._stop_event.is_set():
            return

        # Remove the firing timer from the dict before running — a new one
        # will be added by _schedule_interval after the job completes.
        with self._lock:
            self._timers.pop(job.name, None)

        logger.debug("INTERVAL job '%s' starting.", job.name)
        try:
            result = job.run()
            self._log_result(result)
        except Exception:  # noqa: BLE001
            logger.exception(
                "Unhandled exception in INTERVAL job '%s' — will reschedule.", job.name
            )
        finally:
            # Reschedule unconditionally (stop_event check is inside _schedule_interval)
            self._schedule_interval(job)

    # ------------------------------------------------------------------
    # Internal — result logging
    # ------------------------------------------------------------------

    def _log_result(self, result: JobResult) -> None:
        """Log a job result at the appropriate level."""
        if result.success:
            logger.info(
                "Job '%s' succeeded (%.3fs).",
                result.job_name, result.duration_seconds,
            )
        else:
            logger.warning(
                "Job '%s' FAILED: %s (%.3fs).",
                result.job_name,
                result.error_message or "no message",
                result.duration_seconds,
            )
