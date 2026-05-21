"""
RASTATIME playout engine package.

Exports the abstract PlayoutEngine interface (ADR-002, T2.1), the
concrete VlcPlayoutEngine adapter (T5.1-T5.4) for local audio playback,
and FfmpegStreamer for Icecast streaming.

Architecture: VLC plays audio locally; FfmpegStreamer runs a parallel
FFmpeg subprocess that reads the same audio file and streams it to
Icecast via the built-in ``icecast://`` protocol.  See ffmpeg_streamer.py
for the rationale (VLC's sout/shout chain is broken on Windows).
"""
from .ffmpeg_streamer import FfmpegStreamer
from .interface import PlayoutEngine, PlayoutState
from .vlc_engine import VlcPlayoutEngine

__all__ = [
    "FfmpegStreamer",
    "PlayoutEngine",
    "PlayoutState",
    "VlcPlayoutEngine",
]
