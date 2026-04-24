from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class AudioDeviceKind(Enum):
    OUTPUT = "output"
    INPUT = "input"


@dataclass
class AudioDevice:
    """
    Represents one audio endpoint discovered on the host system.

    Business logic must always reference devices by stable_id, never by
    name or raw_id. Names and raw_ids change across driver updates and
    reboots; stable_id is derived from a persistent platform identifier
    (e.g. a hash of the Windows audio endpoint GUID).
    """

    stable_id: str            # persistent identifier — safe for DB storage and config
    name: str                 # human-readable display name (for UI only)
    kind: AudioDeviceKind
    channels: int             # e.g. 2 for stereo, 8 for multichannel interface
    driver: str               # audio API used (e.g. "WASAPI", "DirectSound")
    is_default: bool = False  # True if this is the OS default for its kind
    is_available: bool = True # False if the device was removed since last enumeration
    raw_id: str = ""          # platform-specific raw identifier (debug/logging only)
    metadata: dict = field(default_factory=dict)


class DeviceUnavailableError(Exception):
    """Raised when an operation targets a device that is no longer present."""

    def __init__(self, device_id: str) -> None:
        self.device_id = device_id
        super().__init__(f"Audio device '{device_id}' is not available")


class AudioDeviceManager(ABC):
    """
    Engine-agnostic contract for Windows audio device discovery and selection.

    Concrete implementation: WindowsAudioDeviceManager (Phase 7 / T12.1).
    Isolates all platform-specific device enumeration behind this interface
    so that business logic (soundcard settings, line-in routing) never
    depends directly on Windows device strings or driver names.

    Stable IDs returned by list_outputs / list_inputs are the canonical
    reference used in persisted settings and runtime routing decisions.
    """

    # --- Enumeration ---

    @abstractmethod
    def list_outputs(self) -> list[AudioDevice]:
        """
        Return all currently available audio output devices.
        Unavailable devices (removed since last boot) are not included.
        """

    @abstractmethod
    def list_inputs(self) -> list[AudioDevice]:
        """
        Return all currently available audio input devices.
        Unavailable devices (removed since last boot) are not included.
        """

    @abstractmethod
    def get_default_output(self) -> Optional[AudioDevice]:
        """Return the OS-designated default output device, or None."""

    @abstractmethod
    def get_default_input(self) -> Optional[AudioDevice]:
        """Return the OS-designated default input device, or None."""

    # --- Stable ID resolution ---

    @abstractmethod
    def resolve_stable_id(self, raw_id: str, kind: AudioDeviceKind) -> str:
        """
        Derive a stable internal ID from a platform-specific raw device ID.

        The stable ID is suitable for persistence in config/DB. It must
        remain consistent across reboots and minor driver updates.
        Raises DeviceUnavailableError if raw_id cannot be resolved.
        """

    @abstractmethod
    def lookup_by_stable_id(
        self, stable_id: str, kind: AudioDeviceKind
    ) -> Optional[AudioDevice]:
        """
        Find a device by its stable ID.
        Returns None if the device is no longer available (e.g. unplugged).
        Does not raise — callers handle the None / unavailable case.
        """

    # --- Selection ---

    @abstractmethod
    def open_output(self, stable_id: str) -> None:
        """
        Select the output device with the given stable ID as the active output.
        Raises DeviceUnavailableError if the device is not currently present.
        """

    @abstractmethod
    def open_input(self, stable_id: str) -> None:
        """
        Select the input device with the given stable ID as an active input.
        Raises DeviceUnavailableError if the device is not currently present.
        Multiple inputs may be open simultaneously (one per Line-In source).
        """

    @abstractmethod
    def close_output(self, stable_id: str) -> None:
        """Release the output device selection. Silent no-op if not open."""

    @abstractmethod
    def close_input(self, stable_id: str) -> None:
        """Release an input device. Silent no-op if not open."""
