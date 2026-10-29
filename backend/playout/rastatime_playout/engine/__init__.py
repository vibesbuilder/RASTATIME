"""
RASTATIME playout engine package.

Exports the abstract PlayoutEngine interface (ADR-002, T2.1).  The only
implementation is :class:`~rastatime_playout.engine.liquidsoap_engine.LiquidsoapPlayoutEngine`
(production since Phase-C5, 2026-05-28); ``__main__`` imports it lazily.
The mpv engine and its FfmpegStreamer Icecast companions were deleted on
2026-09-10 (BACKLOG "Legacy-mpv-Code-Delete").

Architecture: Liquidsoap owns local playback, the Icecast outputs, the DJ
harbors and the recording; this package only talks to it over telnet.
The remaining subprocess module, ``ffmpeg_linein_capture``, is the MME
feeder that publishes a scheduled line-in on the local /linein-capture
mount for Liquidsoap's ``input.http`` companion source.
"""
from .interface import PlayoutEngine, PlayoutState

__all__ = [
    "PlayoutEngine",
    "PlayoutState",
]
