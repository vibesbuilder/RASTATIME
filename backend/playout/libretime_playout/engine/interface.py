"""
PlayoutEngine abstract interface (ADR-002, T2.1).

All playout actions in RASTATIME must go through this interface.
The only implementation is LiquidsoapPlayoutEngine (production since
Phase-C5, 2026-05-28); the mpv engine was deleted on 2026-09-10.
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional


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
        metadata: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Start playing a URI.

        uri              : local file path or HTTP URL
        cue_in           : seconds from the start of the file to begin
                            playback
        cue_out          : seconds from the start of the file to stop
                            playback (None = natural end)
        media_options    : engine-specific per-media options (kept on
                            the interface for compatibility; the
                            Liquidsoap engine has no per-media-option
                            concept and ignores them).
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
        metadata         : RASTATIME 2026-05-26 — optional dict of ICY-
                            metadata fields the engine should attach to
                            the current track on its way to Icecast.
                            Common keys: ``title``, ``artist``, ``album``,
                            ``show_name``.  None or empty dict means "use
                            whatever metadata the URI naturally carries"
                            (filename for files, ICY-stream header for
                            webstreams).

                            The LiquidsoapPlayoutEngine wires it into
                            Liquidsoap's ``annotate:`` envelope, and
                            Liquidsoap then propagates the metadata to
                            all output.icecast blocks natively.
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

    def wait_until_stopped(self, timeout: float) -> bool:
        """
        Block up to ``timeout`` seconds waiting for playback to end
        naturally (end-of-file, error, or an explicit :meth:`stop`).
        Returns ``True`` if the engine is STOPPED within the timeout,
        ``False`` otherwise.

        RASTATIME 2026-05-25 — Seamless-Bus-Mix Phase 1.  The playout
        scheduler calls this just before hard-stopping the engine at
        next-track time so that a short track (4–10 s) can flush its
        last frames first.

        Default implementation polls :meth:`get_state` once.  The
        Liquidsoap engine returns immediately: the .liq pipeline has
        gapless transitions between queue items natively.
        """
        return self.get_state() == PlayoutState.STOPPED

    def set_audio_device(self, device_id: Optional[str]) -> None:
        """
        Re-route local audio playback to the given output device.

        ``device_id`` is the engine-specific identifier of the OS audio
        endpoint to play to.  ``None`` (or empty) means "OS default".

        The scheduler passes the RASTATIME stable-ID (normalised
        endpoint GUID without braces) straight through; an engine maps
        it to its own device naming.

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
