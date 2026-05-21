"""
T16.3 — Background job implementations.

All six jobs declared here are fully implemented and self-contained.
Each job follows the same defensive pattern:

1. **Dependency injection** — every external collaborator (device manager,
   API client, now-playing state, etc.) is accepted as a keyword-only
   constructor argument that defaults to ``None``.
2. **Graceful skip** — if a required dependency is ``None`` the job returns
   ``JobResult(success=True, error_message="skipped: …")`` rather than
   raising.  A skip is not a failure.
3. **Late-binding fallback** — where a process-level singleton exists
   (``audio.soundcard._registry.default_manager``,
   ``playout.now_playing.default_state``) the job imports it lazily inside
   ``run()`` so that:
   * The module can be imported without those packages being installed.
   * Tests can inject stubs directly without touching global state.
4. **Never raises** — every ``run()`` body is wrapped in a broad
   ``try/except Exception``.  All errors are encoded as
   ``JobResult(success=False, error_message=str(exc))``.
5. **Timing** — ``duration_seconds`` is measured with ``time.monotonic()``
   around the core work, not around the skip/guard checks.

Production wiring
-----------------
The ``_ALL_JOBS`` list at the bottom of this module constructs each job
with **no** arguments (all dependencies ``None``).  These stubs are
registered in :data:`~backend.rastatime_worker.jobs._registry.default_registry`
and will gracefully skip until production startup code wires up the real
dependencies::

    from backend.rastatime_worker.jobs._registry import default_registry
    from backend.rastatime_worker.jobs._inventory import NowPlayingPushJob

    # Replace the stub instance with a wired-up one:
    default_registry.unregister("now_playing_push")
    default_registry.register(NowPlayingPushJob(
        state=real_now_playing_state,
        push_fn=real_push,
    ))

Job catalogue
-------------
STARTUP jobs (run once at service start):

  DeviceStartupCheckJob
      Cross-references persisted soundcard settings against the live device
      inventory (wraps ``audio.soundcard._startup.check_devices_at_startup``).

INTERVAL jobs (run periodically):

  SchedulePollJob
      Polls ``GET /api/v2/schedule`` via an injected API client; delivers the
      raw schedule list to an optional ``on_schedule_data`` callback.

  NowPlayingPushJob
      Reads the current ``NowPlayingState`` and pushes the on-air dict to
      an injected ``push_fn`` callable whenever the playing track changes.

  PodcastFetchJob
      Triggers the legacy PHP task manager (``GET /api/v1/version``) so the
      PHP layer handles podcast episode fetching on its own schedule.

  LibraryScanJob
      Same trigger-task-manager mechanism, causing the PHP layer to initiate
      a library rescan.

  MediaCleanupJob
      Scans a configured temporary directory and removes files whose
      modification time is older than ``max_age_hours`` (default 24 h).
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Callable, Optional

from ._base import Job, JobResult, JobTrigger
from ._registry import default_registry

if TYPE_CHECKING:
    # These types appear only in constructor signatures; importing them at
    # runtime is not required and may fail when the packages are absent.
    from audio.soundcard.interface import AudioDeviceManager
    from audio.soundcard.settings_model import SoundcardSettings
    from playout.now_playing._state import NowPlayingState


# ---------------------------------------------------------------------------
# STARTUP jobs
# ---------------------------------------------------------------------------

class DeviceStartupCheckJob(Job):
    """
    Cross-reference persisted soundcard settings against the live device
    inventory at service start.

    Wraps :func:`audio.soundcard._startup.check_devices_at_startup`.  A
    missing device is **not** a fatal error: the result is still
    ``success=True`` with the missing IDs reported in ``error_message`` so
    operators can investigate without the service crashing.

    Trigger:  STARTUP (once)

    Parameters
    ----------
    manager:
        An :class:`~audio.soundcard.interface.AudioDeviceManager` to use for
        device enumeration.  Defaults to
        ``audio.soundcard._registry.default_manager`` (resolved lazily at
        ``run()`` time).
    settings:
        A :class:`~audio.soundcard.settings_model.SoundcardSettings` domain
        object.  Defaults to a Django ORM lookup at ``run()`` time; skips
        gracefully if Django is unavailable.
    """

    def __init__(
        self,
        *,
        manager: "Optional[AudioDeviceManager]" = None,
        settings: "Optional[SoundcardSettings]" = None,
    ) -> None:
        self._manager  = manager
        self._settings = settings

    # ---- Metadata --------------------------------------------------------

    @property
    def name(self) -> str:
        return "device_startup_check"

    @property
    def trigger(self) -> JobTrigger:
        return JobTrigger.STARTUP

    @property
    def description(self) -> str:
        return (
            "Check audio device availability at service start. "
            "Logs warnings for any configured devices that are not present."
        )

    # ---- Execution -------------------------------------------------------

    def run(self) -> JobResult:
        started = time.monotonic()
        try:
            # --- resolve device manager ----------------------------------
            manager = self._manager
            if manager is None:
                try:
                    import audio.soundcard._registry as _reg  # noqa: PLC0415
                    manager = _reg.default_manager
                except Exception:  # noqa: BLE001
                    manager = None

            if manager is None:
                return JobResult(
                    job_name=self.name,
                    success=True,
                    error_message="skipped: no AudioDeviceManager configured",
                    duration_seconds=time.monotonic() - started,
                )

            # --- resolve soundcard settings -------------------------------
            settings = self._settings
            if settings is None:
                try:
                    from libretime_api.soundcard.models import (  # noqa: PLC0415
                        SoundcardSettings as _ORM,
                    )
                    settings = _ORM.get_settings().to_domain()
                except Exception as exc:  # noqa: BLE001
                    return JobResult(
                        job_name=self.name,
                        success=False,
                        error_message=f"could not load soundcard settings: {exc}",
                        duration_seconds=time.monotonic() - started,
                    )

            # --- run the check --------------------------------------------
            from audio.soundcard._startup import (  # noqa: PLC0415
                check_devices_at_startup,
            )
            check_result = check_devices_at_startup(settings, manager)

            error_message: Optional[str] = None
            if check_result.has_any_missing:
                missing = sorted(check_result.all_missing_ids)
                error_message = f"degraded: missing device(s) {missing}"

            return JobResult(
                job_name=self.name,
                success=True,
                error_message=error_message,
                duration_seconds=time.monotonic() - started,
            )

        except Exception as exc:  # noqa: BLE001
            return JobResult(
                job_name=self.name,
                success=False,
                error_message=str(exc),
                duration_seconds=time.monotonic() - started,
            )


# ---------------------------------------------------------------------------
# INTERVAL jobs
# ---------------------------------------------------------------------------

class SchedulePollJob(Job):
    """
    Poll the LibreTime API for upcoming show schedule entries.

    Calls :meth:`api_client.list_schedule()` and, if an
    ``on_schedule_data`` callback is provided, passes the decoded list to it
    so the caller can feed new entries to the
    :class:`~playout.scheduler.PlayoutScheduler`.

    Trigger:  INTERVAL, every 30 seconds

    Parameters
    ----------
    api_client:
        Any object with a ``list_schedule()`` method returning a response
        whose ``.json()`` decodes to a list of schedule dicts.  If ``None``
        the job skips gracefully.
    on_schedule_data:
        Optional ``Callable[[list], None]`` invoked with the decoded schedule
        list after every successful fetch.
    """

    def __init__(
        self,
        *,
        api_client: Optional[Any] = None,
        on_schedule_data: Optional[Callable[[list], None]] = None,
    ) -> None:
        self._client           = api_client
        self._on_schedule_data = on_schedule_data

    # ---- Metadata --------------------------------------------------------

    @property
    def name(self) -> str:
        return "schedule_poll"

    @property
    def trigger(self) -> JobTrigger:
        return JobTrigger.INTERVAL

    @property
    def interval_seconds(self) -> float:
        return 30.0

    @property
    def description(self) -> str:
        return (
            "Poll GET /api/v2/schedule for upcoming shows and feed them to "
            "the PlayoutScheduler."
        )

    # ---- Execution -------------------------------------------------------

    def run(self) -> JobResult:
        started = time.monotonic()
        try:
            if self._client is None:
                return JobResult(
                    job_name=self.name,
                    success=True,
                    error_message="skipped: no API client configured",
                    duration_seconds=time.monotonic() - started,
                )

            response = self._client.list_schedule()
            items: list = []
            if hasattr(response, "json"):
                payload = response.json()
                if isinstance(payload, list):
                    items = payload
            elif isinstance(response, list):
                items = response

            if self._on_schedule_data is not None:
                self._on_schedule_data(items)

            return JobResult(
                job_name=self.name,
                success=True,
                duration_seconds=time.monotonic() - started,
            )

        except Exception as exc:  # noqa: BLE001
            return JobResult(
                job_name=self.name,
                success=False,
                error_message=str(exc),
                duration_seconds=time.monotonic() - started,
            )


class NowPlayingPushJob(Job):
    """
    Push the current on-air track to an external sink whenever the track
    changes.

    Reads :class:`~playout.now_playing.NowPlayingState` (injected or resolved
    from ``playout.now_playing.default_state``) and calls ``push_fn`` with
    the serialised :meth:`~playout.now_playing.NowPlayingEntry.to_dict`
    payload.  A ``push_fn`` is **not** called again for the same track ID to
    avoid spamming the API on every 5-second tick.

    Trigger:  INTERVAL, every 5 seconds

    Parameters
    ----------
    state:
        A :class:`~playout.now_playing.NowPlayingState` instance.  If
        ``None`` the job falls back to ``playout.now_playing.default_state``
        (resolved lazily); skips if that is also unavailable.
    push_fn:
        ``Callable[[dict], None]`` — receives the
        :meth:`~playout.now_playing.NowPlayingEntry.to_dict` payload.  If
        ``None`` the job skips gracefully.
    """

    def __init__(
        self,
        *,
        state: "Optional[NowPlayingState]" = None,
        push_fn: Optional[Callable[[dict], None]] = None,
    ) -> None:
        self._state          = state
        self._push_fn        = push_fn
        self._last_pushed_id: Optional[str] = None

    # ---- Metadata --------------------------------------------------------

    @property
    def name(self) -> str:
        return "now_playing_push"

    @property
    def trigger(self) -> JobTrigger:
        return JobTrigger.INTERVAL

    @property
    def interval_seconds(self) -> float:
        return 5.0

    @property
    def description(self) -> str:
        return "Push NowPlayingState to push_fn every 5 seconds when the track changes."

    # ---- Execution -------------------------------------------------------

    def run(self) -> JobResult:
        started = time.monotonic()
        try:
            # --- resolve state -------------------------------------------
            state = self._state
            if state is None:
                try:
                    import playout.now_playing as _np  # noqa: PLC0415
                    state = _np.default_state
                except Exception:  # noqa: BLE001
                    state = None

            if state is None or self._push_fn is None:
                return JobResult(
                    job_name=self.name,
                    success=True,
                    error_message="skipped: no state or push_fn configured",
                    duration_seconds=time.monotonic() - started,
                )

            entry = state.get()

            if not entry.is_playing:
                # Nothing on air — nothing to push.
                return JobResult(
                    job_name=self.name,
                    success=True,
                    duration_seconds=time.monotonic() - started,
                )

            current_id = str(entry.item.id) if entry.item is not None else None

            if current_id == self._last_pushed_id:
                # Same track as last push — skip to avoid API spam.
                return JobResult(
                    job_name=self.name,
                    success=True,
                    duration_seconds=time.monotonic() - started,
                )

            self._push_fn(entry.to_dict())
            self._last_pushed_id = current_id

            return JobResult(
                job_name=self.name,
                success=True,
                duration_seconds=time.monotonic() - started,
            )

        except Exception as exc:  # noqa: BLE001
            return JobResult(
                job_name=self.name,
                success=False,
                error_message=str(exc),
                duration_seconds=time.monotonic() - started,
            )


class PodcastFetchJob(Job):
    """
    Trigger the legacy PHP task manager so it handles podcast episode fetching.

    Calls :meth:`api_client.trigger_task_manager()` which pings
    ``GET /api/v1/version``; this causes the LibreTime PHP backend to run
    its internal task-manager loop (including podcast RSS polling).

    Trigger:  INTERVAL, every 3600 seconds (1 hour)

    Parameters
    ----------
    api_client:
        Any object with a ``trigger_task_manager()`` method.  If ``None``
        the job skips gracefully.
    """

    def __init__(self, *, api_client: Optional[Any] = None) -> None:
        self._client = api_client

    # ---- Metadata --------------------------------------------------------

    @property
    def name(self) -> str:
        return "podcast_fetch"

    @property
    def trigger(self) -> JobTrigger:
        return JobTrigger.INTERVAL

    @property
    def interval_seconds(self) -> float:
        return 3600.0

    @property
    def description(self) -> str:
        return (
            "Trigger the legacy PHP task manager so it fetches new podcast "
            "episodes from all configured RSS feeds."
        )

    # ---- Execution -------------------------------------------------------

    def run(self) -> JobResult:
        started = time.monotonic()
        try:
            if self._client is None:
                return JobResult(
                    job_name=self.name,
                    success=True,
                    error_message="skipped: no API client configured",
                    duration_seconds=time.monotonic() - started,
                )

            self._client.trigger_task_manager()

            return JobResult(
                job_name=self.name,
                success=True,
                duration_seconds=time.monotonic() - started,
            )

        except Exception as exc:  # noqa: BLE001
            return JobResult(
                job_name=self.name,
                success=False,
                error_message=str(exc),
                duration_seconds=time.monotonic() - started,
            )


class LibraryScanJob(Job):
    """
    Trigger the legacy PHP task manager so it initiates a media library rescan.

    Uses the same ``trigger_task_manager()`` mechanism as
    :class:`PodcastFetchJob`; the PHP backend's task manager handles library
    scanning internally.

    Trigger:  INTERVAL, every 3600 seconds (1 hour)

    Parameters
    ----------
    api_client:
        Any object with a ``trigger_task_manager()`` method.  If ``None``
        the job skips gracefully.
    """

    def __init__(self, *, api_client: Optional[Any] = None) -> None:
        self._client = api_client

    # ---- Metadata --------------------------------------------------------

    @property
    def name(self) -> str:
        return "library_scan"

    @property
    def trigger(self) -> JobTrigger:
        return JobTrigger.INTERVAL

    @property
    def interval_seconds(self) -> float:
        return 3600.0

    @property
    def description(self) -> str:
        return (
            "Trigger the legacy PHP task manager to initiate a media library "
            "rescan for new or modified files."
        )

    # ---- Execution -------------------------------------------------------

    def run(self) -> JobResult:
        started = time.monotonic()
        try:
            if self._client is None:
                return JobResult(
                    job_name=self.name,
                    success=True,
                    error_message="skipped: no API client configured",
                    duration_seconds=time.monotonic() - started,
                )

            self._client.trigger_task_manager()

            return JobResult(
                job_name=self.name,
                success=True,
                duration_seconds=time.monotonic() - started,
            )

        except Exception as exc:  # noqa: BLE001
            return JobResult(
                job_name=self.name,
                success=False,
                error_message=str(exc),
                duration_seconds=time.monotonic() - started,
            )


class MediaCleanupJob(Job):
    """
    Remove orphaned temporary files from a configurable staging directory.

    Scans ``tmp_dir`` for files whose modification time is older than
    ``max_age_hours`` (default 24 h) and deletes them.  Files that cannot be
    deleted (permission errors, race conditions) are counted but do not abort
    the rest of the cleanup; the result still reports ``success=False`` if any
    removal failed.

    Trigger:  INTERVAL, every 3600 seconds (1 hour)

    Parameters
    ----------
    tmp_dir:
        Path to the directory to scan.  If ``None`` the job skips gracefully.
    max_age_hours:
        Files older than this many hours are removed.  Default: 24.
    """

    def __init__(
        self,
        *,
        tmp_dir: Optional[str] = None,
        max_age_hours: int = 24,
    ) -> None:
        self._tmp_dir       = tmp_dir
        self._max_age_hours = max_age_hours

    # ---- Metadata --------------------------------------------------------

    @property
    def name(self) -> str:
        return "media_cleanup"

    @property
    def trigger(self) -> JobTrigger:
        return JobTrigger.INTERVAL

    @property
    def interval_seconds(self) -> float:
        return 3600.0

    @property
    def description(self) -> str:
        return (
            "Remove orphaned temporary files from failed analyzer runs and "
            "expired import staging directories."
        )

    # ---- Execution -------------------------------------------------------

    def run(self) -> JobResult:
        started = time.monotonic()
        try:
            if self._tmp_dir is None:
                return JobResult(
                    job_name=self.name,
                    success=True,
                    error_message="skipped: no tmp_dir configured",
                    duration_seconds=time.monotonic() - started,
                )

            from pathlib import Path  # noqa: PLC0415

            tmp_path = Path(self._tmp_dir)
            if not tmp_path.is_dir():
                return JobResult(
                    job_name=self.name,
                    success=True,
                    error_message=(
                        f"skipped: tmp_dir '{self._tmp_dir}' does not exist"
                    ),
                    duration_seconds=time.monotonic() - started,
                )

            cutoff   = time.time() - self._max_age_hours * 3600
            removed  = 0
            errors: list[str] = []

            for entry in tmp_path.iterdir():
                try:
                    if entry.is_file() and entry.stat().st_mtime < cutoff:
                        entry.unlink()
                        removed += 1
                except Exception as exc:  # noqa: BLE001
                    errors.append(str(exc))

            if errors:
                return JobResult(
                    job_name=self.name,
                    success=False,
                    error_message=(
                        f"removed {removed} file(s); "
                        f"{len(errors)} deletion error(s): {errors[0]}"
                    ),
                    duration_seconds=time.monotonic() - started,
                )

            return JobResult(
                job_name=self.name,
                success=True,
                duration_seconds=time.monotonic() - started,
            )

        except Exception as exc:  # noqa: BLE001
            return JobResult(
                job_name=self.name,
                success=False,
                error_message=str(exc),
                duration_seconds=time.monotonic() - started,
            )


# ---------------------------------------------------------------------------
# All known jobs — instantiated and registered in default_registry.
# All use no-arg construction (dependencies default to None → graceful skip).
# ---------------------------------------------------------------------------

_ALL_JOBS: list[Job] = [
    DeviceStartupCheckJob(),
    SchedulePollJob(),
    NowPlayingPushJob(),
    PodcastFetchJob(),
    LibraryScanJob(),
    MediaCleanupJob(),
]

for _job in _ALL_JOBS:
    default_registry.register(_job)
