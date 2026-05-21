"""
backend.rastatime_worker.jobs — Background job abstractions and inventory.

T16.1 public API
----------------
``JobTrigger``
    Enum: STARTUP / INTERVAL / EVENT.

``JobResult``
    Frozen dataclass — outcome of a single ``Job.run()`` call.

``Job``
    Abstract base class for all background jobs.

``JobRegistry``
    Registry of :class:`Job` instances keyed by name.

``default_registry``
    Module-level singleton pre-populated with all known jobs.
    Populated by importing :mod:`._inventory`.

Concrete job classes (stubs — implemented in T16.3):
    ``DeviceStartupCheckJob``, ``SchedulePollJob``, ``NowPlayingPushJob``,
    ``PodcastFetchJob``, ``LibraryScanJob``, ``MediaCleanupJob``.
"""

from ._base import Job, JobResult, JobTrigger
from ._registry import JobRegistry, default_registry
from ._inventory import (
    DeviceStartupCheckJob,
    LibraryScanJob,
    MediaCleanupJob,
    NowPlayingPushJob,
    PodcastFetchJob,
    SchedulePollJob,
)

__all__ = [
    # Primitives
    "JobTrigger",
    "JobResult",
    "Job",
    # Registry
    "JobRegistry",
    "default_registry",
    # Concrete stubs
    "DeviceStartupCheckJob",
    "SchedulePollJob",
    "NowPlayingPushJob",
    "PodcastFetchJob",
    "LibraryScanJob",
    "MediaCleanupJob",
]
