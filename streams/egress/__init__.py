from ._archive import ArchiveOutput
from ._connection import StreamConnection
from ._health import IcecastHealthChecker
from ._metadata import IcyMetadataPusher
from ._registry import connect_egress_manager
from ._sout import SoutBuilder
from ._vlc_manager import LibVlcEgressManager
from .interface import OutputStateChangedEvent, OutputStatus, StreamEgressManager, StreamOutput

__all__ = [
    # ABC
    "StreamEgressManager",
    # Config / status data classes
    "StreamOutput",
    "OutputStatus",
    "OutputStateChangedEvent",
    # Concrete classes (T10.1)
    "StreamConnection",
    "IcyMetadataPusher",
    "SoutBuilder",
    "LibVlcEgressManager",
    # Process-level singleton wiring (T10.3)
    "connect_egress_manager",
    # T10.4 — Icecast health checker + file archive output
    "IcecastHealthChecker",
    "ArchiveOutput",
]
