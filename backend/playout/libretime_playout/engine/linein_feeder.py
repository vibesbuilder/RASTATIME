"""
linein_feeder — multichannel Line-In capture front-end for RASTATIME.

RASTATIME 2026-08-31 (BACKLOG "Line-In: Kanal-Auswahl auf
Multi-Input-Devices").

Why this exists
---------------
:class:`~.ffmpeg_linein_capture.FfmpegLineinCapture` reads the input
device through FFmpeg's ``dshow`` demuxer.  That path is fine for
plain stereo devices, but on multichannel interfaces the DirectShow
capture pin only ever offers mono/stereo — measured on the Tascam
US-16x08: ``-list_options`` shows ``ch=1``/``ch=2`` only, and
``-channels 16`` is rejected.  The interface's 16 real inputs are
unreachable through dshow, so "capture studio B on inputs 5/6" was
impossible.

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

    found = find_input_device(device_name, max(mapping) + 1, sd)
    if found is None:
        print(
            f"linein_feeder: no {HOST_API_SUBSTRING} input device matching "
            f"{device_name!r} with >= {max(mapping) + 1} channels",
            file=sys.stderr,
        )
        return 3

    dev_idx, n_channels, pa_name = found
    print(
        f"linein_feeder: capturing dev[{dev_idx}] {pa_name!r} "
        f"({n_channels} ch @ {rate} Hz) -> stereo from channels "
        f"{[c + 1 for c in mapping]}",
        file=sys.stderr,
    )

    out = sys.stdout.buffer
    overflows = 0
    try:
        stream = sd.RawInputStream(
            samplerate=rate,
            channels=n_channels,
            dtype="int16",
            device=dev_idx,
            blocksize=0,  # let PortAudio choose its internal buffering
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"linein_feeder: cannot open capture: {exc}", file=sys.stderr)
        return 4

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
