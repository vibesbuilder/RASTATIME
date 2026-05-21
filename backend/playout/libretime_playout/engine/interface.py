"""
PlayoutEngine abstract interface (ADR-002, T2.1).

All playout actions in RASTATIME must go through this interface.
The libVLC implementation (VlcPlayoutEngine) is the mandatory Windows
adapter; a MockPlayoutEngine (T4.1) can be used for tests.
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional


class PlayoutState(str, Enum):
    STOPPED = "stopped"
    PLAYING = "playing"
    ERROR = "error"


class PlayoutEngine(ABC):
    """Abstract playout engine interface (ADR-002)."""

    @abstractmethod
    def play(
        self,
        uri: str,
        *,
        cue_in: float = 0.0,
        cue_out: Optional[float] = None,
        media_options: Optional[List[str]] = None,
        gain_db: Optional[float] = None,
    ) -> None:
        """
        Start playing a URI.

        uri              : local file path or HTTP URL
        cue_in           : seconds from the start of the file to begin
                            playback
        cue_out          : seconds from the start of the file to stop
                            playback (None = natural end)
        media_options    : engine-specific per-media options (e.g. for
                            libVLC ``[":http-user=…", ":http-pwd=…",
                            ":network-caching=500"]`` — auth credentials
                            and caching tweaks that don't fit in the URI
                            itself).  Engines that don't have a
                            per-media-option concept may ignore them.
        gain_db          : RASTATIME 2026-05-16 — generic per-event dB
                            offset.  Source of the value depends on the
                            event type; the scheduler computes it:
                              * File events: precomputed ReplayGain sum
                                (cc_files.replay_gain +
                                cc_pref.replay_gain_modifier).
                              * Webstream events: cc_webstream.input_gain_db.
                              * Live sources (Master/Show, Linein): None.
                            ``None`` or 0.0 means no gain processing.
                            Engines implement via a volume / gain audio
                            filter; the scheduler always passes either
                            a value or ``None`` so a previous event's
                            gain does not leak into the current
                            ``play()`` call.
        """

    @abstractmethod
    def stop(self) -> None:
        """Hard-stop any currently playing content immediately."""

    @abstractmethod
    def get_state(self) -> PlayoutState:
        """Return the current playback state."""

    @abstractmethod
    def close(self) -> None:
        """Release all resources held by this engine."""

    def set_audio_device(self, device_id: Optional[str]) -> None:
        """
        Re-route local audio playback to the given output device.

        ``device_id`` is the engine-specific identifier of the OS audio
        endpoint to play to.  ``None`` (or empty) means "OS default".

        For libmpv on Windows the format is ``wasapi/{<GUID>}`` —
        :class:`MpvPlayoutEngine` converts a RASTATIME stable-ID
        (normalised GUID without braces) into that format internally,
        so the scheduler can pass the bare stable-ID straight through.

        Default implementation is a no-op + warning — engines that
        don't support live audio-device switching just keep playing
        on their current output.
        """
        import logging
        logging.getLogger(__name__).warning(
            "set_audio_device(%r) called but engine does not implement "
            "live audio-device switching — playback stays on the "
            "previously selected device.", device_id,
        )
