from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

# Opaque identifier for a submitted job instance.
JobId = str


class JobStatus(Enum):
    PENDING = "pending"      # queued, not yet started
    RUNNING = "running"      # currently executing
    COMPLETED = "completed"  # finished successfully
    FAILED = "failed"        # finished with an error
    CANCELLED = "cancelled"  # cancelled before or during execution
    RETRYING = "retrying"    # failed, scheduled for retry


@dataclass
class JobInfo:
    """Runtime metadata for one submitted job instance."""

    job_id: JobId
    job_name: str
    status: JobStatus
    submitted_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    retry_count: int = 0
    error_message: Optional[str] = None
    kwargs: dict = field(default_factory=dict)


@dataclass
class JobResult:
    """Outcome of a completed or failed job instance."""

    job_id: JobId
    success: bool
    value: Any = None                  # return value on success
    error_message: Optional[str] = None


class JobNotFoundError(Exception):
    """Raised when a job_id is not known to the runner."""

    def __init__(self, job_id: JobId) -> None:
        self.job_id = job_id
        super().__init__(f"Job '{job_id}' not found")


class JobNameNotRegisteredError(Exception):
    """Raised when submitting or scheduling an unregistered job name."""

    def __init__(self, job_name: str) -> None:
        self.job_name = job_name
        super().__init__(f"No handler registered for job '{job_name}'")


class JobRunner(ABC):
    """
    Engine-agnostic contract for background task execution.

    Replaces Celery (Phase 8 / T16.2). Concrete implementation:
    WindowsJobRunner (APScheduler-based or custom loop).
    Message broker is optional — the runner must operate without
    RabbitMQ if broker is not configured.

    Handlers are registered by name. Callers submit or schedule jobs
    by name, not by passing callables directly. This avoids the
    multiprocessing pickling issues that make Celery unreliable
    on Windows (see LINUX_INVENTORY.md §2 and RATIONALE.md §3).
    """

    # --- Handler registration ---

    @abstractmethod
    def register(
        self,
        job_name: str,
        handler: Callable[..., Any],
        *,
        max_retries: int = 0,
        retry_delay_seconds: float = 60.0,
    ) -> None:
        """
        Register a named job handler.

        job_name    — unique identifier used when submitting/scheduling.
        handler     — callable executed when the job runs; receives
                      kwargs passed at submit/schedule time.
        max_retries — number of automatic retries on failure (0 = no retry).
        retry_delay_seconds — wait between retries.

        Calling register() twice with the same job_name replaces the
        previous registration.
        """

    @abstractmethod
    def registered_jobs(self) -> list[str]:
        """Return the names of all currently registered job handlers."""

    # --- One-shot submission ---

    @abstractmethod
    def submit(self, job_name: str, **kwargs: Any) -> JobId:
        """
        Enqueue a one-shot job for immediate execution.

        Returns a JobId that can be used to query status or cancel.
        Raises JobNameNotRegisteredError if job_name is not registered.
        """

    # --- Recurring schedule ---

    @abstractmethod
    def schedule(
        self,
        job_name: str,
        cron: str,
        *,
        schedule_id: Optional[str] = None,
        **kwargs: Any,
    ) -> JobId:
        """
        Register a recurring job execution on a cron schedule.

        cron        — standard 5-field cron expression (minute hour dom month dow).
        schedule_id — optional stable ID; auto-generated if omitted.
                      Use a stable ID to safely re-schedule on restart.
        kwargs      — passed to the handler on every execution.

        Returns the schedule_id (stable across restarts if provided).
        Raises JobNameNotRegisteredError if job_name is not registered.
        """

    @abstractmethod
    def unschedule(self, schedule_id: JobId) -> None:
        """
        Remove a recurring schedule.
        Silent no-op if schedule_id does not exist.
        """

    @abstractmethod
    def list_schedules(self) -> list[JobInfo]:
        """Return metadata for all active recurring schedules."""

    # --- Status and results ---

    @abstractmethod
    def status(self, job_id: JobId) -> JobInfo:
        """
        Return current metadata for a job instance or schedule.
        Raises JobNotFoundError if job_id is unknown.
        """

    @abstractmethod
    def result(self, job_id: JobId) -> JobResult:
        """
        Return the result of a completed job instance.
        Raises JobNotFoundError if job_id is unknown.
        Raises RuntimeError if the job is not yet in a terminal state.
        """

    # --- Cancellation ---

    @abstractmethod
    def cancel(self, job_id: JobId) -> None:
        """
        Cancel a pending or running job instance.
        Silent no-op if the job is already in a terminal state.
        Raises JobNotFoundError if job_id is unknown.
        """

    # --- Lifecycle ---

    @abstractmethod
    def start(self) -> None:
        """Start the runner (begin processing the queue, activate schedules)."""

    @abstractmethod
    def stop(self, *, timeout_seconds: float = 10.0) -> None:
        """
        Stop the runner gracefully.
        Waits up to timeout_seconds for running jobs to finish.
        """
