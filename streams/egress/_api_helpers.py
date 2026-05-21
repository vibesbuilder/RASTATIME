"""
streams.egress._api_helpers — pure serialization helpers for the status API.

These functions convert :class:`~streams.egress.interface.StreamOutput` /
:class:`~streams.egress.interface.OutputStatus` objects into plain
JSON-serialisable dicts.  They have no dependency on Django so they can be
unit-tested without Django installed.

Response shape (per output)
---------------------------
::

    {
        "output_id":       "main-mp3",
        "name":            "Main MP3 Stream",
        "protocol":        "icecast",
        "url":             "ice.example.com",
        "port":            8000,
        "mount":           "/live",
        "codec":           "mp3",
        "bitrate":         128,
        "enabled":         true,
        "state":           "active",
        "connected_since": "2026-04-26T14:30:00+00:00",
        "error_message":   null
    }

``state`` values: "idle" | "connecting" | "active" | "disconnected" | "error"
``protocol`` values: "icecast" | "shoutcast"
``connected_since`` is ISO 8601 UTC when state is ACTIVE, null otherwise.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from .interface import OutputStatus, StreamEgressManager, StreamOutput

if TYPE_CHECKING:
    pass


def serialize_output_status(output: StreamOutput, status: OutputStatus) -> dict:
    """
    Merge one :class:`StreamOutput` config + its :class:`OutputStatus` snapshot
    into a single JSON-serialisable dict.

    Parameters
    ----------
    output:
        Static configuration (name, protocol, url, …).
    status:
        Live runtime snapshot (state, connected_since, error_message, …).

    Returns
    -------
    dict
        Plain dict with string-valued enum fields and ISO-8601 timestamps.
    """
    return {
        "output_id": output.id,
        "name": output.name,
        "protocol": output.protocol.value,
        "url": output.url,
        "port": output.port,
        "mount": output.mount,
        "codec": output.codec,
        "bitrate": output.bitrate,
        "enabled": output.enabled,
        "state": status.state.value,
        "connected_since": (
            status.connected_since.isoformat()
            if status.connected_since is not None
            else None
        ),
        "error_message": status.error_message,
    }


def list_output_statuses(manager: StreamEgressManager) -> list[dict]:
    """
    Serialise all outputs from *manager* to a list of dicts.

    Tolerates a :exc:`ValueError` from :meth:`~StreamEgressManager.get_output_status`
    (output removed between ``list_outputs()`` and ``get_output_status()`` calls
    — rare race condition, silently skipped).

    Parameters
    ----------
    manager:
        Live egress manager whose outputs to enumerate.

    Returns
    -------
    list[dict]
        One dict per output, in ``list_outputs()`` order.
    """
    result: list[dict] = []
    for output in manager.list_outputs():
        try:
            status = manager.get_output_status(output.id)
        except ValueError:
            continue  # output removed mid-iteration; skip gracefully
        result.append(serialize_output_status(output, status))
    return result


def get_single_output_status(
    manager: StreamEgressManager, output_id: str
) -> Optional[dict]:
    """
    Serialise one output from *manager*.

    Returns
    -------
    dict or None
        Serialised status dict, or ``None`` if *output_id* is not registered.
    """
    try:
        status = manager.get_output_status(output_id)
    except ValueError:
        return None

    output = next(
        (o for o in manager.list_outputs() if o.id == output_id), None
    )
    if output is None:
        return None

    return serialize_output_status(output, status)
