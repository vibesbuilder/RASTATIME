"""streams.egress — outgoing stream outputs (status-API surface).

After the VLC-era cleanup (2026-05-31) only the live status-API surface
remains: the ``StreamEgressManager`` ABC + config/status dataclasses
(``interface``), the process-level singleton registry (``_registry``), and
the pure serialization helpers (``_api_helpers``).  The concrete libVLC
egress manager and its helpers (``_vlc_manager``, ``_sout``,
``_connection``, ``_metadata``, ``_health``, ``_archive``) were removed
together with the abandoned VLC engine.
"""
from ._registry import connect_egress_manager
from .interface import (
    OutputStateChangedEvent,
    OutputStatus,
    StreamEgressManager,
    StreamOutput,
)

__all__ = [
    # ABC
    "StreamEgressManager",
    # Config / status data classes
    "StreamOutput",
    "OutputStatus",
    "OutputStateChangedEvent",
    # Process-level singleton wiring (T10.3)
    "connect_egress_manager",
]
