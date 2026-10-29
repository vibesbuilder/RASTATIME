"""
T13.3 — Startup device availability check.

Called once at service start (or on-demand by the settings API) to
cross-reference the persisted :class:`~.settings_model.SoundcardSettings`
against the devices currently enumerated by the
:class:`~.interface.AudioDeviceManager`.

Design notes
------------
* **Never raises** — a missing device is a normal operational condition
  (USB audio interface unplugged overnight, driver update, etc.).
* Each missing device is logged at ``WARNING`` level so operators see a
  clear message in the service log without the service crashing.
* The result object (:class:`StartupCheckResult`) is a frozen dataclass
  that can be passed to the API layer and the UI to surface the degradation.
* The system continues in a *degraded* but functional state — missing
  outputs fall back silently to the OS default; missing line-ins simply
  do not activate.

Typical call site (service startup)::

    from audio.soundcard._startup import check_devices_at_startup
    from audio.soundcard import connect_device_manager

    mgr = WindowsAudioDeviceManager()
    connect_device_manager(mgr)

    settings = SoundcardSettings.get_settings().to_domain()
    result = check_devices_at_startup(settings, mgr)
    if result.has_any_missing:
        # degrade gracefully — log already emitted inside check
        ...
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from .interface import AudioDevice, AudioDeviceKind, AudioDeviceManager
from .settings_model import SoundcardSettings

if TYPE_CHECKING:
    pass   # no circular deps

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StartupCheckResult:
    """
    Result of a device availability check against the persisted settings.

    Each field carries the *configured* stable ID that is currently
    unavailable — i.e., absent from the device manager's live enumeration.
    A field is ``None`` / empty tuple when the corresponding device is
    either not configured or is present and available.

    Attributes
    ----------
    missing_output_id:
        The ``main_output_id`` that was configured but is not currently
        available, or ``None`` if the main output is present / unconfigured.
    missing_preview_id:
        The ``preview_output_id`` that was configured but is not currently
        available, or ``None`` if the preview output is present / unconfigured.
    missing_line_in_ids:
        Tuple of ``line_in_device_ids`` stable IDs that are configured but
        not currently available.  Empty when all line-ins are present.
    """

    missing_output_id:   Optional[str]
    missing_preview_id:  Optional[str]
    missing_line_in_ids: tuple[str, ...]

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def has_any_missing(self) -> bool:
        """``True`` if at least one configured device is currently unavailable."""
        return (
            self.missing_output_id  is not None
            or self.missing_preview_id is not None
            or bool(self.missing_line_in_ids)
        )

    @property
    def all_missing_ids(self) -> frozenset[str]:
        """
        Flat frozen set of every missing stable ID.

        Convenience accessor for the API layer, which serialises this as a
        sorted list so the UI can highlight specific entries.
        """
        ids: set[str] = set()
        if self.missing_output_id:
            ids.add(self.missing_output_id)
        if self.missing_preview_id:
            ids.add(self.missing_preview_id)
        ids.update(self.missing_line_in_ids)
        return frozenset(ids)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ids_in_list(devices: list[AudioDevice]) -> frozenset[str]:
    """Return the set of stable_ids from a device list."""
    return frozenset(d.stable_id for d in devices)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_devices_at_startup(
    settings: SoundcardSettings,
    manager: AudioDeviceManager,
    log: Optional[logging.Logger] = None,
) -> StartupCheckResult:
    """
    Cross-reference persisted soundcard settings against live device inventory.

    Logs a ``WARNING`` for each configured device that is not currently
    present in the manager's enumeration.  Logs ``INFO`` when all devices
    are available.  Never raises an exception.

    Parameters
    ----------
    settings:
        Pure domain model (loaded from the DB via
        :meth:`~rastatime_api.soundcard.models.SoundcardSettings.to_domain`
        or constructed directly in tests).
    manager:
        Live :class:`~.interface.AudioDeviceManager` whose
        :meth:`~.interface.AudioDeviceManager.list_outputs` /
        :meth:`~.interface.AudioDeviceManager.list_inputs` reflect the
        current hardware state.
    log:
        Optional logger override.  Defaults to this module's logger so
        log records appear under ``audio.soundcard._startup``.

    Returns
    -------
    StartupCheckResult
        Identifies which configured devices are unavailable.
        :attr:`~StartupCheckResult.has_any_missing` is ``False`` when all
        configured devices are present (the normal, healthy case).
    """
    _log = log if log is not None else logger

    available_outputs_list = manager.list_outputs()
    available_inputs_list  = manager.list_inputs()
    available_outputs: frozenset[str] = _ids_in_list(available_outputs_list)
    available_inputs:  frozenset[str] = _ids_in_list(available_inputs_list)

    # RASTATIME 2026-05-14 — B.4 #4 output side: lowercased friendly-name
    # set, used to detect "device renamed at the OS level but same
    # friendly name" cases where the saved stable_id no longer matches
    # but the device is in fact present (USB endpoint-GUID reshuffle).
    available_output_names: frozenset[str] = frozenset(
        (d.name or "").strip().lower() for d in available_outputs_list if d.name
    )

    # ---- main output ----------------------------------------------------
    missing_output_id: Optional[str] = None
    if settings.main_output_id is not None:
        if settings.main_output_id not in available_outputs:
            name_hint = (settings.main_output_name or "").strip().lower()
            if name_hint and name_hint in available_output_names:
                _log.info(
                    "Soundcard startup: main output '%s' no longer matches "
                    "by stable_id, but name-fallback found %r among the "
                    "active outputs.  Treating as present; operator should "
                    "re-save the picker so the new id is persisted.",
                    settings.main_output_id, settings.main_output_name,
                )
            else:
                missing_output_id = settings.main_output_id
                _log.warning(
                    "Soundcard startup: configured main output '%s' is not "
                    "available (device unplugged or driver removed; "
                    "name-fallback %r also did not match). "
                    "Falling back to OS default until reconfigured.",
                    settings.main_output_id, settings.main_output_name,
                )

    # ---- preview output -------------------------------------------------
    missing_preview_id: Optional[str] = None
    if settings.preview_output_id is not None:
        if settings.preview_output_id not in available_outputs:
            name_hint = (settings.preview_output_name or "").strip().lower()
            if name_hint and name_hint in available_output_names:
                _log.info(
                    "Soundcard startup: preview output '%s' no longer "
                    "matches by stable_id, but name-fallback found %r "
                    "among the active outputs.  Treating as present.",
                    settings.preview_output_id, settings.preview_output_name,
                )
            else:
                missing_preview_id = settings.preview_output_id
                _log.warning(
                    "Soundcard startup: configured preview output '%s' is "
                    "not available (name-fallback %r also did not match). "
                    "Preview monitoring disabled until reconfigured.",
                    settings.preview_output_id, settings.preview_output_name,
                )

    # ---- line-in inputs -------------------------------------------------
    missing_line_ins: list[str] = [
        sid
        for sid in settings.line_in_device_ids
        if sid not in available_inputs
    ]
    for sid in missing_line_ins:
        _log.warning(
            "Soundcard startup: configured line-in '%s' is not available. "
            "This line-in source will be inactive until reconfigured.",
            sid,
        )

    result = StartupCheckResult(
        missing_output_id=missing_output_id,
        missing_preview_id=missing_preview_id,
        missing_line_in_ids=tuple(missing_line_ins),
    )

    if not result.has_any_missing:
        _log.info("Soundcard startup: all configured devices are available.")

    return result
