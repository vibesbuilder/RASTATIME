"""
RASTATIME 2026-11-15 - tempo and key per track (audio features, stage 2).

Runs in its own virtual environment (`.venv-features`, requirements.txt next
to this file) so the production environment stays free of numpy / numba.
The API's `analyze_audio_features` command starts it as a subprocess and
talks JSON lines over stdin / stdout:

    -> {"ready": true, "v": 1, "librosa": "1.0.0"}          once, after warm-up
    <- {"id": 42, "path": "D:/stor/a.mp3", "start": 92.4}
    -> {"id": 42, "tempo": 127.9, "beats": 63, "key": "8A", ...}
       or {"id": 42, "error": "..."}

The worker only reads the files: ffmpeg decodes 30 s from `start` at
22050 Hz mono (the excerpt stage 1 measures).  Tempo is the beat tracker's
tempo refined by a straight-line fit through the beat times (the tracker
alone works on a ~5 % grid); its octave is kept as measured.  Key is the
best Krumhansl-Kessler profile against the mean chroma, written as a
Camelot code ("8A" = A minor).

usage: python -I tempo_key.py --ffmpeg C:/ffmpeg/bin/ffmpeg.exe
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ.setdefault(_var, "1")

import numpy as np  # noqa: E402

VERSION = 1
SAMPLE_RATE = 22050
EXCERPT_S = 30.0
MIN_AUDIO_S = 10.0
MIN_BEATS_FOR_FIT = 8
FFMPEG_TIMEOUT_S = 60

PITCHES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
# Krumhansl-Kessler key profiles, index 0 = tonic
MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def camelot(pitch_class: int, minor: bool) -> str:
    """Camelot code of a key: C major = 8B, A minor = 8A, one step = a fifth."""
    number = ((5 if minor else 8) + 7 * pitch_class) % 12 or 12
    return f"{number}{'A' if minor else 'B'}"


def fitted_tempo(beat_times) -> float:
    """Tempo from a straight line through the beat times (0.0 below 8 beats)."""
    beats = np.asarray(beat_times, dtype=float)
    if len(beats) < MIN_BEATS_FOR_FIT:
        return 0.0
    slope = float(np.polyfit(np.arange(len(beats)), beats, 1)[0])
    return 60.0 / slope if slope > 0 else 0.0


def key_from_chroma(chroma_mean) -> dict:
    """Best and second-best key profile for a 12-bin mean chroma vector."""
    scores = []
    for pitch_class in range(12):
        for minor, profile in ((False, MAJOR_PROFILE), (True, MINOR_PROFILE)):
            corr = float(np.corrcoef(chroma_mean, np.roll(profile, pitch_class))[0, 1])
            scores.append((corr if np.isfinite(corr) else -1.0, pitch_class, minor))
    scores.sort(reverse=True)
    best, second = scores[0], scores[1]
    return {
        "key": camelot(best[1], best[2]),
        "key_corr": round(best[0], 3),
        "key_margin": round(best[0] - second[0], 3),
        "key_second": camelot(second[1], second[2]),
    }


def decode(ffmpeg: str, path: str, start: float):
    cmd = [
        ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-threads", "1",
        "-ss", f"{max(0.0, start):.3f}", "-t", f"{EXCERPT_S:.3f}", "-i", path,
        "-af", f"aresample={SAMPLE_RATE},aformat=sample_fmts=flt:channel_layouts=mono",
        "-f", "f32le", "-",
    ]  # fmt: skip
    flags = 0
    if os.name == "nt":
        flags = subprocess.BELOW_NORMAL_PRIORITY_CLASS | subprocess.CREATE_NO_WINDOW
    done = subprocess.run(
        cmd, capture_output=True, timeout=FFMPEG_TIMEOUT_S, creationflags=flags, check=False
    )
    if done.returncode != 0:
        raise RuntimeError("ffmpeg: " + done.stderr.decode("utf-8", "replace").strip()[:160])
    return np.frombuffer(done.stdout, dtype=np.float32)


def analyse(librosa, samples) -> dict:
    if len(samples) < SAMPLE_RATE * MIN_AUDIO_S:
        raise RuntimeError("too short")
    if float(np.max(np.abs(samples))) < 1e-3:
        raise RuntimeError("silent")
    onset = librosa.onset.onset_strength(y=samples, sr=SAMPLE_RATE)
    grid_tempo, beat_times = librosa.beat.beat_track(
        onset_envelope=onset, sr=SAMPLE_RATE, units="time"
    )
    grid_tempo = float(np.atleast_1d(grid_tempo)[0])
    tempo = fitted_tempo(beat_times) or grid_tempo
    if not 30.0 <= tempo <= 300.0:
        raise RuntimeError("no steady beat")
    chroma = librosa.feature.chroma_cqt(y=samples, sr=SAMPLE_RATE)
    result = {
        "tempo": round(tempo, 1),
        "tempo_grid": round(grid_tempo, 1),
        "beats": int(len(beat_times)),
    }
    result.update(key_from_chroma(np.mean(chroma, axis=1)))
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--ffmpeg", default="ffmpeg")
    args = parser.parse_args(argv)

    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    sys.stdin.reconfigure(encoding="utf-8")
    import librosa  # pylint: disable=import-outside-toplevel

    # first call compiles the numba kernels: pay it before the ready line
    noise = np.random.default_rng(0).standard_normal(SAMPLE_RATE * 12).astype(np.float32) * 0.1
    try:
        analyse(librosa, noise)
    except RuntimeError:
        pass  # noise has no steady beat; the kernels are compiled all the same
    print(json.dumps({"ready": True, "v": VERSION, "librosa": librosa.__version__}), flush=True)

    for line in sys.stdin:
        if not line.strip():
            continue
        job = {}
        try:
            job = json.loads(line)
            out = {"id": job["id"]}
            out.update(analyse(librosa, decode(args.ffmpeg, job["path"], float(job["start"]))))
        except Exception as exc:  # pylint: disable=broad-exception-caught
            out = {"id": job.get("id"), "error": str(exc).strip()[:200] or type(exc).__name__}
        print(json.dumps(out), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
