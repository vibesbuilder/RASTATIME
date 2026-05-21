"""
streams — outgoing and incoming audio stream management for RASTATIME.

Public surface
--------------
* :mod:`streams.egress` — outgoing stream outputs (Icecast, SHOUTcast).
* :mod:`streams.ingress` — incoming remote stream sources (DJ, web, line-in).
* :data:`StreamProtocol`, :data:`StreamState` — shared enum types.
"""

from ._types import StreamProtocol, StreamState

__all__ = [
    "StreamProtocol",
    "StreamState",
]
