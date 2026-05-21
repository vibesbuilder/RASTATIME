"""
audio.soundcard._registry — process-level AudioDeviceManager singleton.

Mirrors the pattern of ``streams.egress._registry``:
a module-level ``default_manager`` variable that is ``None`` until
:func:`connect_device_manager` is called at application startup.

Usage (production)
------------------
At application startup, after the device manager is constructed, call::

    from audio.soundcard import connect_device_manager
    connect_device_manager(WindowsAudioDeviceManager())

The Django view at ``/api/v2/audio/devices`` then reads live device lists
from that manager via ``audio.soundcard._registry.default_manager``.

Usage (tests)
-------------
Inject a stub manager via the module attribute::

    import audio.soundcard._registry as _reg
    _reg.default_manager = _StubManager()

Always restore ``None`` in teardown to avoid cross-test contamination.

Multi-process note
------------------
When the playout engine and the API server run as separate OS processes
the singleton stays ``None`` in the API process.  A future task may add a
shared transport.  For a single-process dev server, :func:`connect_device_manager`
is sufficient.
"""

from __future__ import annotations

from typing import Optional

from .interface import AudioDeviceManager


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

default_manager: Optional[AudioDeviceManager] = None
"""
The process-level :class:`~audio.soundcard.interface.AudioDeviceManager`.

``None`` until :func:`connect_device_manager` is called.
Do NOT import this name directly — always access it as a module attribute::

    import audio.soundcard._registry as _reg
    mgr = _reg.default_manager   # reads the current live value
"""


def connect_device_manager(mgr: AudioDeviceManager) -> None:
    """
    Set the process-level device manager singleton.

    Replaces any previously registered manager.  Safe to call multiple
    times (e.g. during testing or service restart).

    Parameters
    ----------
    mgr:
        A concrete :class:`~audio.soundcard.interface.AudioDeviceManager`
        implementation (e.g. :class:`~audio.soundcard.WindowsAudioDeviceManager`).
    """
    global default_manager
    default_manager = mgr
