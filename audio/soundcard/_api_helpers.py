"""
audio.soundcard._api_helpers — pure serialization helpers for the device API.

These functions convert :class:`~audio.soundcard.interface.AudioDevice` objects
into plain JSON-serialisable dicts.  They have no dependency on Django so they
can be unit-tested without Django installed.

Response shape
--------------
``GET /api/v2/audio/devices`` returns::

    {
        "outputs": [
            {
                "stable_id":    "9ab29437-d4ec-473d-9a94-1ad46a86e9ff",
                "name":         "DELL U2419HC",
                "kind":         "output",
                "channels":     2,
                "driver":       "WASAPI",
                "is_default":   false,
                "is_available": true
            },
            ...
        ],
        "inputs": [
            {
                "stable_id":    "0bcc4357-eafe-45b4-ba84-d810eab113fb",
                "name":         "Mikrofon",
                "kind":         "input",
                "channels":     16,
                "driver":       "WASAPI",
                "is_default":   false,
                "is_available": true
            },
            ...
        ]
    }

``kind`` values:   ``"output"`` | ``"input"``
``channels``:      integer ≥ 1
``is_default``:    ``true`` for the OS-designated default device
``is_available``:  ``true`` for devices currently present (always ``true``
                   from :meth:`list_outputs` / :meth:`list_inputs`, which
                   filter out unavailable endpoints)
"""

from __future__ import annotations

from .interface import AudioDevice, AudioDeviceManager


def serialize_device(device: AudioDevice) -> dict:
    """
    Convert one :class:`AudioDevice` to a JSON-serialisable dict.

    Parameters
    ----------
    device:
        Device object returned by
        :meth:`~AudioDeviceManager.list_outputs` or
        :meth:`~AudioDeviceManager.list_inputs`.

    Returns
    -------
    dict
        Plain dict with string-valued enum fields and native Python types.
    """
    return {
        "stable_id":    device.stable_id,
        "name":         device.name,
        "kind":         device.kind.value,       # "output" | "input"
        "channels":     device.channels,
        "driver":       device.driver,
        "is_default":   device.is_default,
        "is_available": device.is_available,
    }


def list_devices_response(manager: AudioDeviceManager) -> dict:
    """
    Build the full ``/api/v2/audio/devices`` response body.

    Calls :meth:`~AudioDeviceManager.list_outputs` and
    :meth:`~AudioDeviceManager.list_inputs` on *manager* and serialises
    each device with :func:`serialize_device`.

    Parameters
    ----------
    manager:
        Live device manager whose device inventory to expose.

    Returns
    -------
    dict
        ``{"outputs": [...], "inputs": [...]}`` — always present even if
        one or both lists are empty.
    """
    return {
        "outputs": [serialize_device(d) for d in manager.list_outputs()],
        "inputs":  [serialize_device(d) for d in manager.list_inputs()],
    }
