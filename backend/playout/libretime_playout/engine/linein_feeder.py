"""
linein_feeder — multichannel Line-In capture front-end for RASTATIME.

RASTATIME 2026-08-31 (BACKLOG "Line-In: Kanal-Auswahl auf
Multi-Input-Devices").

Why this exists
---------------
:class:`~.ffmpeg_linein_capture.FfmpegLineinCapture` used to read the
input device through FFmpeg's ``dshow`` demuxer.  On multichannel
interfaces the DirectShow capture pin only ever offers mono/stereo —
measured on the Tascam US-16x08: ``-list_options`` shows
``ch=1``/``ch=2`` only, and ``-channels 16`` is rejected.  The
interface's 16 real inputs are unreachable through dshow, so "capture
studio B on inputs 5/6" was impossible.

A second dshow defect showed up on 2026-09-03 and cost a test show its
audio: we address the device as
``audio=@device_cm_{...}\\wave_{<guid>}``, built from the Windows
audio *endpoint* GUID stored on the line-in row, but DirectShow
enumerates its own device GUIDs and does not know that one.  ffmpeg
answered "Could not find audio only device" and the slot went out
silent.  Since this feeder resolves devices by friendly name instead,
it now serves plain stereo too, not just the exotic mappings.

Probing every Windows host API against the US-16x08 gave:

  ================  ==========================================
  WASAPI shared     capped at the endpoint *mix format* (2 ch)
  WASAPI exclusive  rejected by the driver (invalid channels)
  DirectSound       opens 16 ch but delivers digital silence
  WDM-KS            no blocking-read support in PortAudio
  **MME**           **16 real, independent channels** (verified
                    by per-lane bit-comparison of ADC noise)
  ================  ==========================================

So this feeder captures via **MME** (PortAudio through the
``sounddevice`` package), extracts the channels selected by the
line-in's ``channel_mapping``, and writes interleaved 16-bit
little-endian **stereo** PCM to stdout.  FfmpegLineinCapture pipes
that into ``ffmpeg -f s16le -i pipe:0`` in place of the dshow input;
everything downstream (encoder, Icecast push, watchdog) is unchanged.
MME's extra buffering latency (~0.1-0.2 s) is irrelevant inside the
~0.5-0.8 s monitor chain.

Run as a subprocess (never in the playout main process — a PortAudio
driver fault must not take Pypo down with it)::

    python -m libretime_playout.engine.linein_feeder \
        --device-name "Mikrofon (US-16x08)" --mapping 4,5 --rate 48000

Exit codes: 0 clean shutdown (stdout consumer went away), 2 bad
arguments / sounddevice missing, 3 device not found, 4 capture open
failed, 5 capture died mid-run.
"""

from __future__ import annotations

import argparse
import array
import logging
import sys
from typing import List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

#: Host API used for capture.  See the module docstring for why MME is
#: the only Windows API that demonstrably delivers all channels of a
#: multichannel interface without touching system settings.
HOST_API_SUBSTRING = "MME"

#: Frames per read; 1/10 s at 48 kHz.  Small enough to keep the added
#: pipe latency negligible, large enough to keep Python-loop overhead
#: irrelevant.
DEFAULT_BLOCKSIZE = 4800


def extract_frames(
    raw: bytes, n_channels: int, mapping: Sequence[int]
) -> bytes:
    """
    Extract ``mapping`` from interleaved s16le frames, return s16le stereo.

    ``mapping`` with two entries ``(a, b)`` selects those channels as
    left/right.  A single entry ``(a,)`` duplicates that channel to
    both stereo lanes (dual mono).  A ragged tail (partial frame at
    the end of ``raw``) is dropped.

    Pure function — unit-testable without any audio hardware.
    """
    if n_channels < 1:
        raise ValueError(f"n_channels must be >= 1, got {n_channels}")
    if len(mapping) not in (1, 2):
        raise ValueError(f"mapping must have 1 or 2 entries, got {mapping!r}")
    for ch in mapping:
        if not 0 <= ch < n_channels:
            raise ValueError(
                f"mapping channel {ch} out of range for {n_channels}-channel input"
            )

    samples = array.array("h")
    samples.frombytes(raw[: len(raw) - (len(raw) % (2 * n_channels))])
    n_frames = len(samples) // n_channels

    left_src = mapping[0]
    right_src = mapping[1] if len(mapping) == 2 else mapping[0]

    out = array.array("h", bytes(4 * n_frames))  # n_frames stereo frames
    out[0::2] = samples[left_src::n_channels]
    out[1::2] = samples[right_src::n_channels]
    if sys.byteorder != "little":  # pragma: no cover - Windows is LE
        out.byteswap()
    return out.tobytes()


def find_input_device(
    device_name: str, min_channels: int, sd
) -> Optional[Tuple[int, int, str]]:
    """
    Locate the MME input device for ``device_name``.

    Matches the OS friendly name we persisted at save time
    (``rastatime_linein.device_name``) against PortAudio's device
    names, exact first, then substring in either direction — MME
    truncates long names to 31 characters, so ``"Mikrofon (US-16x08)"``
    may enumerate as ``"Mikrofon (US-16x08 Audio)"`` or a clipped
    variant.  Only devices with at least ``min_channels`` inputs
    qualify.

    Returns ``(device_index, max_input_channels, portaudio_name)`` or
    ``None``.
    """
    apis = sd.query_hostapis()
    rows: List[Tuple[int, int, str]] = []
    for idx, dev in enumerate(sd.query_devices()):
        if HOST_API_SUBSTRING not in apis[dev["hostapi"]]["name"]:
            continue
        if dev["max_input_channels"] < min_channels:
            continue
        rows.append((idx, dev["max_input_channels"], dev["name"]))

    wanted = device_name.strip().lower()
    for idx, max_in, name in rows:  # pass 1: exact
        if name.strip().lower() == wanted:
            return (idx, max_in, name)
    for idx, max_in, name in rows:  # pass 2: substring either way
        got = name.strip().lower()
        if wanted and (wanted in got or got in wanted):
            return (idx, max_in, name)
    # pass 3: tolerate a trailing ")"-suffix variation — drivers append
    # words inside the final parenthesis per API ("Mikrofon (US-16x08)"
    # vs "Mikrofon (US-16x08 Audio)"), which plain substring matching
    # misses because of the closing bracket.
    wanted_core = wanted.rstrip(")").strip()
    for idx, max_in, name in rows:
        got_core = name.strip().lower().rstrip(")").strip()
        if wanted_core and (wanted_core in got_core or got_core in wanted_core):
            return (idx, max_in, name)
    return None


def parse_mapping(text: str) -> Tuple[int, ...]:
    """Parse ``"4,5"`` into ``(4, 5)``; raises ValueError on junk."""
    try:
        mapping = tuple(int(tok.strip()) for tok in text.split(",") if tok.strip())
    except ValueError as exc:
        raise ValueError(f"invalid --mapping {text!r}") from exc
    if len(mapping) not in (1, 2) or any(ch < 0 for ch in mapping):
        raise ValueError(f"invalid --mapping {text!r}")
    return mapping


def _open_candidates(device_name: str, mapping: Sequence[int], rate: int, sd):
    """
    Yield ``((device_index, open_channels), label)`` candidates, best
    first, all at the GIVEN rate — the rate is owned by the caller
    (FfmpegLineinCapture tells ffmpeg the same value per attempt and
    retries with a different one if every candidate fails).

    RASTATIME 2026-09-01: under the LocalSystem service session the MME
    open that works interactively can fail with PaErrorCode -9999
    ("invalid parameter"), so the feeder no longer trusts a single
    combination.  Candidates:

      1. MME with the device's full channel count (interactive-proven),
      2. MME with the smallest even channel count covering the mapping
         (session-0 WinMM may accept 4 ch where it refuses 16),
      3. any WASAPI endpoint for the device whose mix format carries
         enough channels — the 2-ch mix cap seen interactively is a
         per-session setting, the service session may expose the full
         format (WASAPI shared only opens at its mix rate, so this
         candidate simply fails on a rate mismatch and costs nothing).

    DirectSound is deliberately absent: it opens 16 ch but delivers
    digital silence (measured 2026-08-31).
    """
    min_ch = max(mapping) + 1
    cover_ch = min_ch + (min_ch % 2)  # round up to even
    wanted = device_name.strip().lower()
    core = wanted.rstrip(")").strip()
    apis = sd.query_hostapis()
    for idx, dev in enumerate(sd.query_devices()):
        if dev["max_input_channels"] < min_ch:
            continue
        name = dev["name"].strip().lower()
        got_core = name.rstrip(")").strip()
        if not (
            name == wanted
            or wanted in name
            or name in wanted
            or (core and (core in got_core or got_core in core))
        ):
            continue
        api = apis[dev["hostapi"]]["name"]
        if HOST_API_SUBSTRING in api:
            yield (idx, dev["max_input_channels"]), f"MME all-ch@{rate}"
            if cover_ch < dev["max_input_channels"]:
                yield (idx, cover_ch), f"MME {cover_ch}ch@{rate}"
        elif "WASAPI" in api:
            yield (idx, dev["max_input_channels"]), f"WASAPI@{rate}"


def run(
    device_name: str,
    mapping: Sequence[int],
    rate: int,
    blocksize: int = DEFAULT_BLOCKSIZE,
) -> int:
    """Capture loop.  Returns the process exit code."""
    try:
        import sounddevice as sd  # deferred: keep --help usable without it
    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"linein_feeder: sounddevice unavailable: {exc}", file=sys.stderr)
        return 2

    stream = None
    n_channels = 0
    tried = []
    for (dev_idx, dev_channels), label in _open_candidates(
        device_name, mapping, rate, sd
    ):
        try:
            stream = sd.RawInputStream(
                samplerate=rate,
                channels=dev_channels,
                dtype="int16",
                device=dev_idx,
                blocksize=0,  # let PortAudio choose its internal buffering
            )
            n_channels = dev_channels
            print(
                f"linein_feeder: capturing dev[{dev_idx}] via {label} "
                f"({dev_channels} ch) -> stereo from channels "
                f"{[c + 1 for c in mapping]}",
                file=sys.stderr,
            )
            break
        except Exception as exc:  # pylint: disable=broad-exception-caught
            tried.append(f"{label}: {exc}")
            stream = None

    if stream is None:
        if not tried:
            print(
                f"linein_feeder: no input device matching {device_name!r} "
                f"with >= {max(mapping) + 1} channels",
                file=sys.stderr,
            )
            return 3
        print(
            "linein_feeder: cannot open capture; tried -> "
            + " | ".join(tried),
            file=sys.stderr,
        )
        return 4

    out = sys.stdout.buffer
    overflows = 0

    try:
        with stream:
            while True:
                data, overflowed = stream.read(blocksize)
                if overflowed:
                    overflows += 1
                    if overflows in (1, 10) or overflows % 100 == 0:
                        print(
                            f"linein_feeder: input overflow #{overflows} "
                            "(samples dropped by the OS)",
                            file=sys.stderr,
                        )
                out.write(extract_frames(bytes(data), n_channels, mapping))
                out.flush()
    except (BrokenPipeError, OSError):
        # Consumer (ffmpeg) closed the pipe — normal shutdown path.
        return 0
    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"linein_feeder: capture died: {exc}", file=sys.stderr)
        return 5


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="linein_feeder",
        description="Capture selected channels of a multichannel input "
        "device (MME) and write s16le stereo PCM to stdout.",
    )
    parser.add_argument(
        "--device-name",
        required=True,
        help="OS friendly name of the input endpoint (rastatime_linein.device_name)",
    )
    parser.add_argument(
        "--mapping",
        required=True,
        help="comma-separated 0-based channel indices, 1 or 2 entries (e.g. 4,5)",
    )
    parser.add_argument("--rate", type=int, default=48000)
    parser.add_argument("--blocksize", type=int, default=DEFAULT_BLOCKSIZE)
    args = parser.parse_args(argv)

    try:
        mapping = parse_mapping(args.mapping)
    except ValueError as exc:
        print(f"linein_feeder: {exc}", file=sys.stderr)
        return 2

    return run(args.device_name, mapping, args.rate, args.blocksize)


if __name__ == "__main__":
    sys.exit(main())
