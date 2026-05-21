from .interface import AudioDevice, AudioDeviceKind, AudioDeviceManager, DeviceUnavailableError
from ._registry import connect_device_manager
from .settings_model import SoundcardSettings
from .windows_manager import WinRegDeviceEnumerator, WindowsAudioDeviceManager, _normalize_guid
from ._startup import StartupCheckResult, check_devices_at_startup

__all__ = [
    "AudioDeviceManager",
    "AudioDevice",
    "AudioDeviceKind",
    "DeviceUnavailableError",
    # T12.1 — Windows implementation
    "WindowsAudioDeviceManager",
    "WinRegDeviceEnumerator",
    "_normalize_guid",
    # T12.2 — API registry
    "connect_device_manager",
    # T13.1 — Soundcard settings domain model
    "SoundcardSettings",
    # T13.3 — Startup device availability check
    "StartupCheckResult",
    "check_devices_at_startup",
]
