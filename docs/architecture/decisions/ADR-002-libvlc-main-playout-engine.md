# ADR-002 — libVLC as the Mandatory Main Playout Engine

**Status:** Accepted; **superseded in practice** by the 2026-05 Liquidsoap cutover (Liquidsoap 2.4.4 is the production playout engine; mpv/libVLC remain legacy fallback code pending deletion)  
**Date:** 2026-04-24  
**Deciders:** RASTATIME project

---

## Context

LibreTime uses **Liquidsoap** as its primary playout engine. Liquidsoap handles
scheduled playback, queue management, stream encoding, and fallback behavior.
It is designed for Linux and assumes a Linux audio stack (ALSA/PortAudio).
Liquidsoap is not a viable option for a Windows-first deployment.

RASTATIME requires a playout engine that:
- runs reliably on Windows 11,
- supports file playback, queue-based playout, and audio device selection,
- provides event callbacks (track change, end of media, playback state),
- can output to Windows audio devices (soundcard line-out),
- is actively maintained and has a usable Python binding.

## Decision

**VLC / libVLC is the mandatory main playout engine for RASTATIME.**

libVLC is used for:
- scheduled playout start and stop,
- queue playback and queue control,
- fallback / default rotation,
- current track state and now-playing metadata,
- local soundcard output routing,
- playout event callbacks (track change, end of media, error).

The Python binding used is `python-vlc`.

**No other component may replace libVLC as the primary playout authority.**
If an auxiliary streaming component (Icecast) is introduced, it does not
acquire playout authority — libVLC remains in control.

All playout actions in the codebase must go through the `PlayoutEngine`
abstract interface. The libVLC implementation is one concrete adapter behind
that interface. This allows the mock engine (T4.1) and any future adapter to
be swapped without changing business logic.

## Consequences

**Positive:**
- VLC runs natively on Windows 11 with full WASAPI/DirectSound support.
- libVLC supports file playback, network streams, and audio device selection.
- `python-vlc` provides a stable Python binding.
- libVLC is actively maintained and widely deployed.

**Negative / Trade-offs:**
- Liquidsoap's advanced DSP features (crossfades, smart transitions) are not
  available. Crossfade and transition logic must be reimplemented if required.
- libVLC's scheduling precision differs from Liquidsoap's. Hard real-time
  guarantees are not provided by libVLC at the Python binding level.
- The `python-vlc` binding requires the libVLC DLLs to be present at runtime.
  Bitness must match (64-bit Python + 64-bit VLC).

**Open question:**
- Minimum supported VLC version to be documented in a follow-up ADR or
  in the bootstrap script (T3.1).

**Follow-up required:**
- T2.1: define `PlayoutEngine` abstract interface.
- T4.1: implement `MockPlayoutEngine` for development without audio.
- T5.1–T5.4: implement `LibVlcPlayoutEngine`.
- T3.1: probe script to verify libVLC presence and version at bootstrap.
