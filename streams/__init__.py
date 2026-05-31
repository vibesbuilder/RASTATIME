"""
streams — outgoing and incoming audio stream management for RASTATIME.

Public surface
--------------
* :mod:`streams.egress` — outgoing stream outputs (Icecast, SHOUTcast).
* :data:`StreamProtocol`, :data:`StreamState` — shared enum types.

(The ``streams.ingress`` package — incoming remote stream sources — was
removed with the abandoned libVLC engine on 2026-05-31; DJ / web / line-in
sources are handled by Liquidsoap's ``input.harbor`` / ``input.http`` /
``input.ffmpeg`` in the production engine.)
"""

from ._types import StreamProtocol, StreamState

__all__ = [
    "StreamProtocol",
    "StreamState",
]
