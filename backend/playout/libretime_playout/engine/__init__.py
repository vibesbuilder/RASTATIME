"""
RASTATIME playout engine package.

Exports the abstract PlayoutEngine interface (ADR-002, T2.1) and
FfmpegStreamer for Icecast streaming.  Concrete engines are imported
lazily by ``__main__`` based on ``RASTATIME_PLAYOUT_ENGINE``: Liquidsoap
(production, since Phase-C5 2026-05-28) or mpv (legacy fallback).

Architecture: in production Liquidsoap owns both local playback and the
Icecast PUTs.  In the legacy mpv fallback path, FfmpegStreamer runs a
parallel FFmpeg subprocess that reads the same audio file and streams it
to Icecast via the built-in ``icecast://`` protocol (see ffmpeg_streamer.py).
"""
from .ffmpeg_streamer import FfmpegStreamer
from .interface import PlayoutEngine, PlayoutState

__all__ = [
    "FfmpegStreamer",
    "PlayoutEngine",
    "PlayoutState",
]
