"""
RASTATIME 2026-11-14 - energy and brightness (``storage/audio_features.py``,
``manage.py analyze_audio_features``): parsing, features, scale, and the
database pass (newest first, hand values stay, failures are kept, rescale).
"""

from __future__ import annotations

import json
from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.db import connection
from model_bakery import baker

from rastatime_api.storage import audio_features as af
from rastatime_api.storage import root as sr


def _output(frames: list[dict[str, float]]) -> str:
    """ffmpeg ``ametadata=print`` text for the given per-frame values."""
    lines = []
    for n, f in enumerate(frames):
        lines.append(f"frame:{n}    pts:{n * af.FRAME}    pts_time:{n * af.FRAME_S:.6f}")
        for key in ("centroid", "flatness", "flux", "rolloff"):
            if key in f:
                lines.append(f"lavfi.aspectralstats.1.{key}={f[key]}")
        if "RMS_level" in f:
            lines.append(f"lavfi.astats.1.RMS_level={f['RMS_level']}")
    return "\n".join(lines) + "\n"


def _music(
    n: int = 640, centroid: float = 2100.0, flux: float = 0.019, flatness: float = 0.34
) -> list[dict]:
    frames = []
    for i in range(n):
        beat = i % 11 == 0  # an attack every ~0.5 s
        frames.append(
            {
                "centroid": centroid,
                "rolloff": centroid * 2.2,
                "flux": flux * (6.0 if beat else 0.8),
                "flatness": flatness,
                "RMS_level": -20.0 if beat else -24.0,
            }
        )
    return frames


# ---------------------------------------------------------------- pure parts


def test_parse_frames_reads_the_metadata_and_drops_incomplete_frames():
    text = _output(
        [{"centroid": 2500.4, "flux": 0.03, "flatness": 0.4, "rolloff": 5000, "RMS_level": -17.6}]
    )
    text += "frame:1    pts:1024    pts_time:0.046\nlavfi.aspectralstats.1.centroid=nan\n"
    frames = af.parse_frames(text)
    assert frames == [
        {"centroid": 2500.4, "flatness": 0.4, "flux": 0.03, "rolloff": 5000.0, "RMS_level": -17.6}
    ]


def test_parse_frames_skips_minus_infinity_of_digital_silence():
    text = _output([{"centroid": 0.0, "RMS_level": float("-inf")}])
    assert af.parse_frames(text) == []


@pytest.mark.parametrize(
    ("length", "cuein", "cueout", "expected"),
    [
        (240.0, None, None, 105.0),  # middle of the track
        (240.0, 10.0, 200.0, 90.0),  # middle of the cue range
        (20.0, None, None, 0.0),  # shorter than the excerpt
        (240.0, 30.0, 20.0, 120.0),  # cue out before cue in: whole track from cue in
    ],
)
def test_excerpt_start(length, cuein, cueout, expected):
    assert af.excerpt_start(length, cuein, cueout) == pytest.approx(expected)


def test_ffmpeg_command_brings_the_track_to_the_on_air_level_inside_the_graph():
    cmd = af.ffmpeg_command("ffmpeg", "D:/stor/a.mp3", 105.0, af.gain_db(-9.5))
    graph = cmd[cmd.index("-af") + 1]
    assert graph.startswith(
        "aresample=22050,aformat=sample_fmts=flt:channel_layouts=mono,volume=-13.50dB,"
    )
    assert cmd[cmd.index("-ss") + 1] == "105.00" and cmd[cmd.index("-t") + 1] == "30"
    assert "-ar" not in cmd and "-ac" not in cmd  # would act after the filters


def test_onset_rate_counts_the_attacks():
    flux = [0.01] * 600
    for i in range(0, 600, 20):  # one peak every 20 frames = 0.93 s
        flux[i] = 0.08
    assert af.onset_rate(flux) == pytest.approx(30 / (600 * af.FRAME_S), rel=0.05)


def test_summarize_weights_by_level_and_refuses_silence():
    raw = af.summarize(_music(centroid=2000.0))
    assert raw["centroid_hz"] == pytest.approx(2000.0)
    assert raw["onsets_s"] > 1.0 and raw["frames"] == 640
    silent = [{"centroid": 3000.0, "flux": 0.0, "flatness": 0.9, "RMS_level": -90.0}] * 640
    with pytest.raises(af.MeasureError):
        af.summarize(silent)


def test_energy_score_is_zero_at_the_reference_and_rises_with_activity():
    ref = {k: v[0] for k, v in af.ENERGY_REFERENCE.items()}
    assert af.energy_score(ref, ref["lufs"], ref["lra"]) == 0.0
    busier = dict(ref, flux=ref["flux"] * 2)
    calmer = dict(ref)
    assert af.energy_score(busier, ref["lufs"], ref["lra"]) > 0
    assert af.energy_score(calmer, ref["lufs"], 15.0) < 0  # wide loudness range
    assert af.energy_score(ref, ref["lufs"], None) == 0.0  # unknown range counts as typical


def test_to_level_maps_the_edges_to_one_through_ten():
    edges = af.ENERGY_EDGES
    assert af.to_level(edges[0] - 1, edges) == 1
    assert af.to_level(edges[0], edges) == 1
    assert af.to_level(edges[4] + 0.001, edges) == 6
    assert af.to_level(edges[-1] + 5, edges) == 10
    assert len(edges) == 9 and list(edges) == sorted(edges)
    assert len(af.BRIGHTNESS_EDGES_HZ) == 9 and list(af.BRIGHTNESS_EDGES_HZ) == sorted(
        af.BRIGHTNESS_EDGES_HZ
    )


def test_measure_builds_the_document():
    seen = []

    def runner(cmd):
        seen.append(cmd)
        return _output(_music(centroid=3000.0))

    doc = af.measure(
        "x.mp3", 240.0, None, None, -10.0, 5.0, ffmpeg="ff", runner=runner, now=1_800_000_000
    )
    assert seen and seen[0][0] == "ff"
    assert doc["v"] == af.FEATURE_VERSION and doc["scale"] == af.SCALE_VERSION
    assert doc["at"] == "2027-01-15T08:00:00Z" and doc["start_s"] == 105.0
    assert doc["brightness"] == 10  # 3000 Hz lies above the last edge
    assert 1 <= doc["energy"] <= 10 and doc["energy"] == af.to_level(
        doc["energy_score"], af.ENERGY_EDGES
    )


# ---------------------------------------------------------------- database


@pytest.fixture
def library(tmp_path, monkeypatch, db):
    media = tmp_path / "media"
    (media / "imported").mkdir(parents=True)
    monkeypatch.setattr(sr, "config_root", lambda: sr.normalize(str(media)))
    sr.invalidate()
    sr.set_storage_root_setting(None)
    yield media
    sr.invalidate()


def _track(media, name, lufs=-12.0, on_disk=True, **row):
    if on_disk:
        (media / "imported" / name).write_bytes(b"not audio - the runner is faked")
    return baker.make(
        "storage.File",
        filepath=f"imported/{name}",
        exists=True,
        import_status=0,
        mime="audio/mp3",
        length=timedelta(minutes=4),
        loudness_lufs=lufs,
        loudness_range_lu=5.0,
        **row,
    )


def _row(file_id):
    with connection.cursor() as cur:
        cur.execute(
            "SELECT energy, brightness, audio_features FROM cc_files WHERE id = %s", [file_id]
        )
        energy, brightness, doc = cur.fetchone()
    if isinstance(doc, str):
        doc = json.loads(doc)
    return energy, brightness, doc


def _set(file_id, **values):
    with connection.cursor() as cur:
        for column, value in values.items():
            cur.execute(f"UPDATE cc_files SET {column} = %s WHERE id = %s", [value, file_id])


def _pass(media, centroid=2100.0, **kwargs):
    with connection.cursor() as cur:
        return af.run(
            cur,
            str(media),
            ffmpeg="ffmpeg",
            runner=lambda _cmd: _output(_music(centroid=centroid)),
            **kwargs,
        )


def test_a_pass_measures_new_tracks_newest_first_and_keeps_failures(library):
    old = _track(library, "old.mp3")
    new = _track(library, "new.mp3")
    gone = _track(library, "gone.mp3", on_disk=False)
    no_loudness = _track(library, "raw.mp3", lufs=None)

    counts = _pass(library, limit=2)
    assert counts == {"measured": 1, "failed": 1, "skipped": 0}  # gone (newest), then new
    assert _row(old.id) == (None, None, None)

    energy, brightness, doc = _row(new.id)
    assert (energy, brightness) == (doc["energy"], doc["brightness"]) and 1 <= energy <= 10
    assert _row(gone.id)[2]["error"] == "file not found"

    assert _pass(library)["measured"] == 1  # old; gone is not tried again
    assert _row(no_loudness.id) == (None, None, None)
    assert _pass(library) == {"measured": 0, "failed": 0, "skipped": 0}
    assert _pass(library, retry_failed=True)["failed"] == 1


def test_a_value_set_by_hand_survives_measuring_again_and_rescaling(library):
    hand = _track(library, "hand.mp3")
    auto = _track(library, "auto.mp3")
    before = _track(library, "before.mp3")
    _set(before.id, energy=2)  # by hand before the first measurement
    _pass(library, centroid=1500.0)
    _set(hand.id, energy=9)  # by hand after it

    _pass(library, centroid=3000.0, ids=[hand.id, auto.id, before.id])
    assert _row(hand.id)[0] == 9 and _row(hand.id)[1] == 10  # brightness follows
    assert _row(auto.id)[1] == 10 and _row(auto.id)[0] == _row(auto.id)[2]["energy"]
    assert _row(before.id)[0] == 2

    _set(hand.id, brightness=None)  # cleared by hand = no value
    with connection.cursor() as cur:
        cur.execute(
            "UPDATE cc_files SET audio_features = jsonb_set(audio_features, '{scale}', '0') WHERE id = ANY(%s)",
            [[hand.id, auto.id]],
        )
        counts = af.rescale(cur)
    assert counts["changed"] == 2
    assert _row(hand.id)[:2] == (9, None)
    assert _row(auto.id)[2]["scale"] == af.SCALE_VERSION


def test_dry_run_writes_nothing(library):
    track = _track(library, "a.mp3")
    lines = []
    with connection.cursor() as cur:
        counts = af.run(cur, str(library), ffmpeg="ffmpeg", runner=lambda _c: _output(_music()), dry_run=True,
                        log=lines.append)  # fmt: skip
    assert counts["measured"] == 1 and lines[0].startswith(f"id {track.id}: energy ")
    assert _row(track.id) == (None, None, None)


def test_the_command_reports_and_stays_quiet_when_idle(library, monkeypatch):
    _track(library, "a.mp3")
    monkeypatch.setattr(af, "find_ffmpeg", lambda _dir=None: "ffmpeg")
    monkeypatch.setattr(af, "subprocess_runner", lambda _cmd: _output(_music()))
    out = StringIO()
    call_command("analyze_audio_features", stdout=out)
    assert out.getvalue().startswith("measured 1, failed 0, not written 0, waiting 0")
    out = StringIO()
    call_command("analyze_audio_features", stdout=out)
    assert out.getvalue() == ""
