"""
WindowsAudioDeviceManager — Windows Core Audio device enumeration.

Architecture
------------
Two-layer design for testability:

* :class:`_DeviceEnumerator` (Protocol) — injectable data source.
  Decouples the manager from the OS so unit tests can inject a fake.

* :class:`WinRegDeviceEnumerator` — real implementation.
  Reads ``HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\MMDevices\\Audio``
  via :mod:`winreg` (stdlib, Windows-only).  No COM / ``comtypes`` required.

* :class:`WindowsAudioDeviceManager` — implements the ABC.
  Converts raw endpoint data into :class:`~.interface.AudioDevice` objects and
  tracks which devices are currently "open" for playout or capture.

Stable IDs
----------
The Windows audio endpoint GUID (the registry subkey name, e.g.
``{9ab29437-d4ec-473d-9a94-1ad46a86e9ff}``) is normalised to a
brace-stripped, lowercased string and used as the stable ID.

This identifier survives reboots and minor driver updates.  It must only
change if the physical device is removed and a different device takes its
slot (which would change the GUID).

Channel count
-------------
Parsed from ``PKEY_AudioEngine_DeviceFormat``
(``{f19f064d-082c-4e27-bc73-6882a1bb8e4c},0``).  The value is a binary
blob whose first 8 bytes are a Windows-internal header; bytes [8:10] are
``wFormatTag`` and bytes [10:12] are ``nChannels`` of the WAVEFORMATEX
structure.  Falls back to 2 (stereo) if the property is absent or
malformed.

Default device
--------------
Detecting the OS-default endpoint without COM requires ``comtypes`` or
raw IMMDeviceEnumerator COM vtable calls.  :class:`WinRegDeviceEnumerator`
therefore returns ``None`` from :meth:`get_default_guid` and all
:class:`~.interface.AudioDevice` objects have ``is_default=False``.
:meth:`WindowsAudioDeviceManager.get_default_output` /
:meth:`get_default_input` return ``None`` in this mode.

Inject a custom enumerator that provides the default GUID if you need
default detection (e.g. via ``comtypes.CoCreateInstance``).

Selection tracking
------------------
:meth:`open_output` / :meth:`open_input` / :meth:`close_output` /
:meth:`close_input` maintain an in-memory selection — no hardware
interaction occurs.  Actual libVLC routing is wired in T13 / T15.
Multiple inputs may be open simultaneously (one per Line-In source).
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable

from .interface import AudioDevice, AudioDeviceKind, AudioDeviceManager, DeviceUnavailableError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Registry constants (Windows Core Audio MMDevice paths)
# ---------------------------------------------------------------------------

_REG_BASE    = r"SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio"
_REG_RENDER  = _REG_BASE + r"\Render"
_REG_CAPTURE = _REG_BASE + r"\Capture"

_PKEY_FRIENDLY_NAME   = "{a45c254e-df1c-4efd-8020-67d146a850e0},2"
_PKEY_DEVICE_FORMAT   = "{f19f064d-082c-4e27-bc73-6882a1bb8e4c},0"
_DEVICE_STATE_ACTIVE  = 0x00000001

# Byte offset of nChannels inside the WAVEFORMATEX blob stored in the
# PKEY_AudioEngine_DeviceFormat property.  Bytes [0:8] are a Windows-
# internal header; WAVEFORMATEX starts at byte 8.
# WAVEFORMATEX layout: wFormatTag[2], nChannels[2], nSamplesPerSec[4], ...
_WFEX_CHANNELS_OFFSET = 10   # [10:12] = nChannels


# ---------------------------------------------------------------------------
# Raw endpoint data class
# ---------------------------------------------------------------------------

@dataclass
class _RawEndpoint:
    """
    Minimal raw device information from the OS enumerator.

    Fields
    ------
    guid:
        Registry subkey name, e.g. ``{9ab29437-d4ec-473d-9a94-1ad46a86e9ff}``.
        This is the Windows audio endpoint GUID — the basis for stable IDs.
    name:
        Human-readable device name (FriendlyName from Properties subkey).
    channels:
        Number of audio channels (1=mono, 2=stereo, 16=multichannel interface).
    is_active:
        ``True`` if DEVICE_STATE_ACTIVE (device is present and not disabled).
    driver:
        Audio API string, e.g. ``"WASAPI"``.
    """

    guid: str
    name: str
    channels: int
    is_active: bool
    driver: str = "WASAPI"


# ---------------------------------------------------------------------------
# Device enumerator protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class _DeviceEnumerator(Protocol):
    """
    Injectable source of raw audio endpoint data.

    ``list_raw(kind)`` returns ALL endpoints (active and inactive) so the
    manager can decide which to expose and which to skip.
    ``get_default_guid(kind)`` returns the Windows-default endpoint GUID, or
    ``None`` if detection is not supported / unavailable.
    """

    def list_raw(self, kind: AudioDeviceKind) -> list[_RawEndpoint]: ...
    def get_default_guid(self, kind: AudioDeviceKind) -> Optional[str]: ...


# ---------------------------------------------------------------------------
# Real enumerator — reads Windows registry via winreg
# ---------------------------------------------------------------------------

class WinRegDeviceEnumerator:
    """
    Read Windows audio endpoints from the MMDevice registry hive.

    Registry path: ``HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion
    \\MMDevices\\Audio\\{Render|Capture}``.

    Each subkey is an endpoint GUID.  Active devices have
    ``DeviceState == 0x00000001``.  Channel count is parsed from the
    ``PKEY_AudioEngine_DeviceFormat`` binary property.

    Default device detection requires COM and is not implemented here;
    :meth:`get_default_guid` always returns ``None``.

    .. note::

        ``winreg`` is a stdlib module available only on Windows.
        Importing this class on non-Windows platforms will raise
        :class:`ImportError`.
    """

    def list_raw(self, kind: AudioDeviceKind) -> list[_RawEndpoint]:
        """Return all registered endpoints for *kind* (active and inactive)."""
        import winreg  # stdlib, Windows-only — imported lazily for testability

        path = _REG_RENDER if kind == AudioDeviceKind.OUTPUT else _REG_CAPTURE
        result: list[_RawEndpoint] = []
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as root:
                index = 0
                while True:
                    try:
                        guid = winreg.EnumKey(root, index)
                        raw = self._read_endpoint(path, guid)
                        if raw is not None:
                            result.append(raw)
                        index += 1
                    except OSError:
                        break  # no more subkeys
        except OSError:
            logger.warning(
                "WinRegDeviceEnumerator: cannot open MMDevice registry path %r", path
            )
        return result

    def get_default_guid(self, kind: AudioDeviceKind) -> Optional[str]:
        """
        Return the default endpoint GUID.

        Always returns ``None`` — default detection requires COM
        (``IMMDeviceEnumerator::GetDefaultAudioEndpoint``).
        Inject a subclass or alternative enumerator to provide this.
        """
        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_endpoint(self, base_path: str, guid: str) -> Optional[_RawEndpoint]:
        import winreg  # noqa: PLC0415

        sub_path   = f"{base_path}\\{guid}"
        props_path = f"{sub_path}\\Properties"

        try:
            # 1. Device state
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, sub_path) as sub:
                try:
                    state, _ = winreg.QueryValueEx(sub, "DeviceState")
                except FileNotFoundError:
                    state = 0
            is_active = (state == _DEVICE_STATE_ACTIVE)

            # 2. FriendlyName + channel count from Properties subkey
            friendly_name = guid   # safe fallback if Properties absent
            channels      = 2      # stereo fallback

            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, props_path) as props:
                    try:
                        friendly_name, _ = winreg.QueryValueEx(
                            props, _PKEY_FRIENDLY_NAME
                        )
                    except FileNotFoundError:
                        pass

                    try:
                        raw_fmt, _ = winreg.QueryValueEx(props, _PKEY_DEVICE_FORMAT)
                        if isinstance(raw_fmt, bytes) and len(raw_fmt) > _WFEX_CHANNELS_OFFSET + 1:
                            ch = int.from_bytes(
                                raw_fmt[_WFEX_CHANNELS_OFFSET : _WFEX_CHANNELS_OFFSET + 2],
                                "little",
                            )
                            if ch > 0:
                                channels = ch
                    except FileNotFoundError:
                        pass

            except OSError:
                pass  # Properties subkey absent — use fallbacks

            return _RawEndpoint(
                guid=guid,
                name=str(friendly_name),
                channels=channels,
                is_active=is_active,
            )

        except OSError:
            logger.debug(
                "WinRegDeviceEnumerator: cannot read endpoint %r", guid
            )
            return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_guid(guid: str) -> str:
    """
    Normalise a Windows audio endpoint GUID to a stable ID string.

    Strips surrounding ``{`` ``}`` braces (if present) and lowercases the
    result.  Idempotent: already-normalised IDs pass through unchanged.

    Examples
    --------
    >>> _normalize_guid("{9AB29437-D4EC-473D-9A94-1AD46A86E9FF}")
    '9ab29437-d4ec-473d-9a94-1ad46a86e9ff'
    >>> _normalize_guid("9ab29437-d4ec-473d-9a94-1ad46a86e9ff")
    '9ab29437-d4ec-473d-9a94-1ad46a86e9ff'
    """
    return guid.strip("{}").lower()


# ---------------------------------------------------------------------------
# WindowsAudioDeviceManager
# ---------------------------------------------------------------------------

class WindowsAudioDeviceManager(AudioDeviceManager):
    """
    Windows Core Audio implementation of :class:`AudioDeviceManager`.

    Parameters
    ----------
    enumerator:
        Injectable :class:`_DeviceEnumerator`.  Defaults to
        :class:`WinRegDeviceEnumerator` (reads the Windows registry).
        Supply a fake in unit tests to avoid needing a real audio stack.

    Stable IDs
    ----------
    Each device is identified by its Windows audio endpoint GUID,
    normalised via :func:`_normalize_guid` (lowercase, no braces).
    Example: ``"9ab29437-d4ec-473d-9a94-1ad46a86e9ff"``.

    Open/close semantics
    --------------------
    ``open_output`` / ``open_input`` record the selection in memory.
    ``close_output`` / ``close_input`` clear it.  No hardware I/O occurs.
    At most one output may be open at a time; multiple inputs may be open
    simultaneously (one per Line-In source, per UC-I2 / T15 design).
    """

    def __init__(
        self,
        enumerator: Optional[_DeviceEnumerator] = None,
    ) -> None:
        self._enumerator: _DeviceEnumerator = (
            enumerator if enumerator is not None else WinRegDeviceEnumerator()
        )
        self._lock = threading.Lock()
        self._active_output_id: Optional[str] = None
        self._active_input_ids: set[str] = set()

    # ------------------------------------------------------------------
    # Internal: build an AudioDevice from a _RawEndpoint
    # ------------------------------------------------------------------

    @staticmethod
    def _build_device(
        raw: _RawEndpoint,
        kind: AudioDeviceKind,
        default_sid: Optional[str],
    ) -> AudioDevice:
        sid = _normalize_guid(raw.guid)
        return AudioDevice(
            stable_id=sid,
            name=raw.name,
            kind=kind,
            channels=raw.channels,
            driver=raw.driver,
            is_default=(sid == default_sid),
            is_available=raw.is_active,
            raw_id=raw.guid,
        )

    def _default_sid(self, kind: AudioDeviceKind) -> Optional[str]:
        guid = self._enumerator.get_default_guid(kind)
        return _normalize_guid(guid) if guid is not None else None

    # ------------------------------------------------------------------
    # AudioDeviceManager — enumeration
    # ------------------------------------------------------------------

    def list_outputs(self) -> list[AudioDevice]:
        """Return all currently active audio output devices."""
        raws = self._enumerator.list_raw(AudioDeviceKind.OUTPUT)
        default_sid = self._default_sid(AudioDeviceKind.OUTPUT)
        return [
            self._build_device(r, AudioDeviceKind.OUTPUT, default_sid)
            for r in raws
            if r.is_active
        ]

    def list_inputs(self) -> list[AudioDevice]:
        """Return all currently active audio input devices."""
        raws = self._enumerator.list_raw(AudioDeviceKind.INPUT)
        default_sid = self._default_sid(AudioDeviceKind.INPUT)
        return [
            self._build_device(r, AudioDeviceKind.INPUT, default_sid)
            for r in raws
            if r.is_active
        ]

    def get_default_output(self) -> Optional[AudioDevice]:
        """
        Return the OS-designated default output device.

        Returns ``None`` when the enumerator cannot determine the default
        (e.g. :class:`WinRegDeviceEnumerator` without COM).
        """
        default_sid = self._default_sid(AudioDeviceKind.OUTPUT)
        if default_sid is None:
            return None
        return self.lookup_by_stable_id(default_sid, AudioDeviceKind.OUTPUT)

    def get_default_input(self) -> Optional[AudioDevice]:
        """
        Return the OS-designated default input device.

        Returns ``None`` when the enumerator cannot determine the default.
        """
        default_sid = self._default_sid(AudioDeviceKind.INPUT)
        if default_sid is None:
            return None
        return self.lookup_by_stable_id(default_sid, AudioDeviceKind.INPUT)

    # ------------------------------------------------------------------
    # AudioDeviceManager — stable ID resolution
    # ------------------------------------------------------------------

    def resolve_stable_id(self, raw_id: str, kind: AudioDeviceKind) -> str:
        """
        Normalise *raw_id* to a stable ID, verifying the device is active.

        Parameters
        ----------
        raw_id:
            A Windows endpoint GUID (with or without braces, any case).
        kind:
            ``OUTPUT`` or ``INPUT``.

        Returns
        -------
        str
            Normalised stable ID.

        Raises
        ------
        DeviceUnavailableError
            If no active device with the given GUID exists.
        """
        sid = _normalize_guid(raw_id)
        if self.lookup_by_stable_id(sid, kind) is None:
            raise DeviceUnavailableError(raw_id)
        return sid

    def lookup_by_stable_id(
        self, stable_id: str, kind: AudioDeviceKind
    ) -> Optional[AudioDevice]:
        """
        Find an active device by its stable ID.

        Returns ``None`` if the device is unavailable (unplugged, disabled).
        Does not raise.
        """
        devices = (
            self.list_outputs()
            if kind == AudioDeviceKind.OUTPUT
            else self.list_inputs()
        )
        for dev in devices:
            if dev.stable_id == stable_id:
                return dev
        return None

    def find_device_by_id_or_name(
        self,
        saved_stable_id: str,
        saved_name_hint: str,
        kind: AudioDeviceKind,
    ) -> Optional[AudioDevice]:
        """
        Resolve a saved device reference with a name-based fallback.

        RASTATIME 2026-05-14 — B.4 #4 UUID-Wechsel nach Reboot.

        Behaviour
        ---------
        1. If ``saved_stable_id`` is non-empty and lookup_by_stable_id
           finds an active matching device, return that device (fast
           path, no fallback used).
        2. Otherwise, if ``saved_name_hint`` is non-empty, scan the
           currently-active devices of *kind* and return the first one
           whose ``name`` matches case-insensitively after trimming.
           This catches the common Windows USB-audio quirk where the
           endpoint GUID changes across reboots but the OS friendly
           name stays stable.
        3. If neither produces a match, return ``None``.

        Callers can detect whether the name-fallback was used by
        comparing ``returned_device.stable_id`` against the original
        ``saved_stable_id`` — they will differ exactly when the
        fallback path was taken.

        Returns
        -------
        Optional[AudioDevice]
            The resolved device, or ``None`` if no match found.
        """
        # Step 1 — try saved stable_id first.
        if saved_stable_id:
            try:
                normalised = _normalize_guid(saved_stable_id)
            except ValueError:
                normalised = saved_stable_id  # use as-is if not GUID-shaped
            dev = self.lookup_by_stable_id(normalised, kind)
            if dev is not None:
                return dev

        # Step 2 — fall back to friendly-name match.
        hint = (saved_name_hint or "").strip().lower()
        if not hint:
            return None

        devices = (
            self.list_outputs()
            if kind == AudioDeviceKind.OUTPUT
            else self.list_inputs()
        )
        for dev in devices:
            if (dev.name or "").strip().lower() == hint:
                return dev

        return None

    # ------------------------------------------------------------------
    # AudioDeviceManager — selection
    # ------------------------------------------------------------------

    def open_output(self, stable_id: str) -> None:
        """
        Select *stable_id* as the active output device.

        Raises :class:`DeviceUnavailableError` if the device is not present.
        Only one output may be active at a time; calling this with a new ID
        replaces the previous selection.
        """
        if self.lookup_by_stable_id(stable_id, AudioDeviceKind.OUTPUT) is None:
            raise DeviceUnavailableError(stable_id)
        with self._lock:
            self._active_output_id = stable_id
        logger.info("Audio output opened: %s", stable_id)

    def open_input(self, stable_id: str) -> None:
        """
        Add *stable_id* to the set of active input devices.

        Raises :class:`DeviceUnavailableError` if the device is not present.
        Multiple inputs may be open simultaneously.
        """
        if self.lookup_by_stable_id(stable_id, AudioDeviceKind.INPUT) is None:
            raise DeviceUnavailableError(stable_id)
        with self._lock:
            self._active_input_ids.add(stable_id)
        logger.info("Audio input opened: %s", stable_id)

    def close_output(self, stable_id: str) -> None:
        """Deselect the output device. Silent no-op if not currently open."""
        with self._lock:
            if self._active_output_id == stable_id:
                self._active_output_id = None
        logger.debug("Audio output closed: %s", stable_id)

    def close_input(self, stable_id: str) -> None:
        """Remove *stable_id* from active inputs. Silent no-op if not open."""
        with self._lock:
            self._active_input_ids.discard(stable_id)
        logger.debug("Audio input closed: %s", stable_id)

    # ------------------------------------------------------------------
    # Introspection (not part of ABC — used by tests and T13/T15)
    # ------------------------------------------------------------------

    def get_active_output_id(self) -> Optional[str]:
        """Return the stable ID of the currently open output, or ``None``."""
        with self._lock:
            return self._active_output_id

    def get_active_input_ids(self) -> set[str]:
        """Return the set of stable IDs of all currently open inputs."""
        with self._lock:
            return set(self._active_input_ids)
