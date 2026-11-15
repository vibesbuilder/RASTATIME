"""
RASTATIME 2026-11-14 - energy and brightness (``storage/audio_features.py``,
``manage.py analyze_audio_features``): parsing, features, scale, and the
database pass (newest first, hand values stay, failures are kept, rescale).
2026-11-15 - tempo and key (stage 2): the worker protocol, the pass with
hand and tag values, failures and a dead worker; only track types with the
audio analysis are measured, and the values of the others can be cleared.
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


def _type(code, analyse):
    """A track type with "Analyze audio features" on or off (migration 0087)."""
    track_type = baker.make("storage.Library", code=code, name=code.title(), description="")
    with connection.cursor() as cur:
        cur.execute(
            "UPDATE cc_track_types SET analyze_audio_features = %s WHERE id = %s",
            [analyse, track_type.id],
        )
    return track_type


def _music_type():
    from rastatime_api.storage.models import Library

    return Library.objects.filter(code="tmus").first() or _type("tmus", True)


@pytest.fixture
def music(db):
    return _music_type()


def _track(media, name, lufs=-12.0, on_disk=True, **row):
    if on_disk:
        (media / "imported" / name).write_bytes(b"not audio - the runner is faked")
    if "library" not in row:
        row["library"] = _music_type()
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
    monkeypatch.setattr(af, "find_features_worker", lambda: None)  # tempo / key: own test
    out = StringIO()
    call_command("analyze_audio_features", stdout=out)
    assert out.getvalue().startswith("measured 1, failed 0, not written 0, waiting 0")
    out = StringIO()
    call_command("analyze_audio_features", stdout=out)
    assert out.getvalue() == ""


def test_only_tracks_of_an_analysed_type_are_measured(library, music):
    song = _track(library, "song.mp3", library=music)
    jingle = _track(library, "jingle.mp3", library=_type("tjin", False))
    untyped = _track(library, "untyped.mp3", library=None)

    assert _pass(library)["measured"] == 1
    assert _row(song.id)[2] and _row(jingle.id)[2] is None and _row(untyped.id)[2] is None
    assert _pass(library, ids=[jingle.id, untyped.id])["measured"] == 0  # --ids too
    with connection.cursor() as cur:
        assert af.remaining(cur) == 0

    # before migration 0087 the stock type with the code 'music' stands in
    with connection.cursor() as cur:
        cur.execute("ALTER TABLE cc_track_types DROP COLUMN analyze_audio_features")
    stock = _track(library, "stock.mp3", library=baker.make("storage.Library", code="music",
                                                             name="Music", description=""))  # fmt: skip
    assert _pass(library) == {"measured": 1, "failed": 0, "skipped": 0}
    assert _row(stock.id)[2] and _row(jingle.id)[2] is None


# ------------------------------------------------------------ tempo and key


def test_tempo_key_doc_rounds_the_bpm_and_refuses_nonsense():
    doc = af.tempo_key_doc(
        {"id": 1, "tempo": 127.94, "key": "8A", "beats": 63, "key_margin": 0.08, "x": 1},
        "librosa 1.0.0",
        now=0,
    )
    assert doc["bpm"] == 128 and doc["tempo"] == 127.9 and doc["key"] == "8A"
    assert doc["v"] == af.TK_VERSION and doc["src"] == "librosa 1.0.0" and doc["beats"] == 63
    assert "x" not in doc
    for answer in ({"error": "silent"}, {"tempo": 400, "key": "8A"}, {"tempo": 120, "key": "13A"},
                   {"tempo": 120, "key": "Am"}, {"key": "8A"}):  # fmt: skip
        with pytest.raises(af.MeasureError):
            af.tempo_key_doc(answer, "librosa")


class _FakeWorker:
    src = "librosa test"

    def __init__(self, answer):
        self.answer = answer
        self.jobs = []
        self.closed = False

    def analyse(self, file_id, path, start):
        self.jobs.append((file_id, start))
        result = self.answer(file_id)
        if isinstance(result, Exception):
            raise result
        return {"id": file_id, **result}

    def close(self):
        self.closed = True


def _tk_pass(media, answer, started=None, **kwargs):
    worker = _FakeWorker(answer)

    def start():
        if started is not None:
            started.append(1)
        return worker

    with connection.cursor() as cur:
        counts = af.run_tempo_key(cur, str(media), start_worker=start, **kwargs)
    return counts, worker


def _tk_row(file_id):
    with connection.cursor() as cur:
        cur.execute(
            "SELECT bpm, musical_key, audio_features FROM cc_files WHERE id = %s", [file_id]
        )
        bpm, key, doc = cur.fetchone()
    if isinstance(doc, str):
        doc = json.loads(doc)
    return bpm, key, (doc or {}).get("tk")


def test_tempo_key_follow_the_measurement_but_never_a_tag_or_a_hand_value(library):
    plain = _track(library, "plain.mp3")
    tagged = _track(library, "tagged.mp3", bpm=127)
    unknown = _track(library, "unknown.mp3", bpm=0)  # the legacy importer's "no BPM"
    keyed = _track(library, "keyed.mp3")
    later = _track(library, "later.mp3")
    _set(keyed.id, musical_key="5A")
    _pass(library)  # stage 1 first: tempo / key need its excerpt

    started = []
    counts, worker = _tk_pass(library, lambda _id: {"tempo": 128.4, "key": "8A"}, started)
    assert counts == {"measured": 5, "failed": 0, "skipped": 0} and worker.closed
    assert [job[0] for job in worker.jobs] == sorted(
        (t.id for t in (plain, tagged, unknown, keyed, later)), reverse=True
    )
    start_s = _row(plain.id)[2]["start_s"]
    assert dict(worker.jobs)[plain.id] == start_s
    bpm, key, tk = _tk_row(plain.id)
    assert (bpm, key, tk["tempo"], tk["bpm"], tk["src"]) == (128, "8A", 128.4, 128, "librosa test")
    assert _tk_row(tagged.id)[:2] == (127, "8A")
    assert _tk_row(unknown.id)[:2] == (128, "8A")
    assert _tk_row(keyed.id)[:2] == (128, "5A")

    assert _tk_pass(library, lambda _id: {"tempo": 1, "key": "1A"}, started)[0]["measured"] == 0
    assert len(started) == 1  # nothing pending: the worker is not even started

    _set(later.id, bpm=100, musical_key="3B")  # by hand after the measurement
    _tk_pass(library, lambda _id: {"tempo": 90.2, "key": "9B"}, ids=[plain.id, later.id, tagged.id])
    assert _tk_row(plain.id)[:2] == (90, "9B")
    assert _tk_row(later.id)[:2] == (100, "3B")
    assert _tk_row(tagged.id)[:2] == (127, "9B")

    # energy / brightness measured again or rescaled: the tempo / key result stays
    _pass(library, centroid=3000.0, ids=[plain.id])
    with connection.cursor() as cur:
        cur.execute(
            "UPDATE cc_files SET audio_features = jsonb_set(audio_features, '{scale}', '0') WHERE id = %s",
            [plain.id],
        )
        af.rescale(cur)
    assert _tk_row(plain.id)[2]["bpm"] == 90 and _row(plain.id)[2]["scale"] == af.SCALE_VERSION


def test_tempo_key_failures_wait_for_retry_and_a_dead_worker_ends_the_pass(library):
    unmeasured = _track(library, "raw.mp3", lufs=None)  # no stage-1 excerpt: not pending
    a = _track(library, "a.mp3")
    b = _track(library, "b.mp3")
    c = _track(library, "c.mp3")
    _pass(library)
    lines = []

    def answer(file_id):
        if file_id == c.id:
            return {"error": "silent"}
        return af.WorkerError("no answer within 120 s")

    counts, worker = _tk_pass(library, answer, log=lines.append)
    assert counts == {"measured": 0, "failed": 1, "skipped": 0} and worker.closed
    assert _tk_row(c.id)[2]["error"] == "silent" and _tk_row(c.id)[:2] == (None, None)
    assert _tk_row(b.id)[2] is None and _tk_row(a.id)[2] is None
    assert lines[-1] == "tempo / key: worker stopped - no answer within 120 s"

    counts, worker = _tk_pass(library, lambda _id: {"tempo": 100, "key": "8B"})
    assert counts["measured"] == 2 and c.id not in dict(worker.jobs)
    assert (
        _tk_pass(library, lambda _id: {"tempo": 100, "key": "8B"}, retry_failed=True)[0]["measured"]
        == 1
    )
    assert _tk_row(c.id)[:2] == (100, "8B")
    assert _tk_row(unmeasured.id)[2] is None

    with connection.cursor() as cur:
        assert af.remaining_tempo_key(cur) == 0


def test_tempo_key_dry_run_writes_nothing(library):
    track = _track(library, "a.mp3")
    _pass(library)
    lines = []
    counts, _worker = _tk_pass(
        library, lambda _id: {"tempo": 99.6, "key": "11B"}, dry_run=True, log=lines.append
    )
    assert counts["measured"] == 1 and lines == [f"id {track.id}: tempo 99.6 (bpm 100), key 11B"]
    assert _tk_row(track.id) == (None, None, None)


_PROTOCOL = """
import json, sys
mode = sys.argv[sys.argv.index("--ffmpeg") + 1]
if mode == "dies":
    sys.exit(3)
print(json.dumps({"ready": True, "v": 99 if mode == "old" else 1, "librosa": "9.9"}), flush=True)
if mode == "mute":
    sys.stdin.read()
for line in sys.stdin:
    job = json.loads(line)
    print(json.dumps({"id": job["id"], "tempo": 120.0 + job["start"], "key": "8A"}), flush=True)
"""


def test_the_worker_session_speaks_json_lines_and_times_out(tmp_path):
    import sys  # noqa: PLC0415

    script = tmp_path / "fake_worker.py"
    script.write_text(_PROTOCOL, encoding="utf-8")
    worker = af.TempoKeyWorker(sys.executable, str(script), "ok", ready_timeout=30)
    try:
        assert worker.src == "librosa 9.9"
        assert worker.analyse(7, "x.mp3", 1.5) == {"id": 7, "tempo": 121.5, "key": "8A"}
        assert worker.analyse(8, "y.mp3", 0.0)["tempo"] == 120.0
    finally:
        worker.close()
    with pytest.raises(af.WorkerError, match="worker ended"):
        af.TempoKeyWorker(sys.executable, str(script), "dies", ready_timeout=30)
    with pytest.raises(af.WorkerError, match="version 99"):
        af.TempoKeyWorker(sys.executable, str(script), "old", ready_timeout=30)
    worker = af.TempoKeyWorker(
        sys.executable, str(script), "mute", ready_timeout=30, job_timeout=0.5
    )
    try:
        with pytest.raises(af.WorkerError, match="no answer within"):
            worker.analyse(1, "x.mp3", 0.0)
    finally:
        worker.close()
    with pytest.raises(af.WorkerError, match="cannot start"):
        af.TempoKeyWorker(str(tmp_path / "no-python.exe"), str(script), "ok")


def test_the_command_runs_tempo_key_after_energy(library, monkeypatch):
    track = _track(library, "a.mp3")
    monkeypatch.setattr(af, "find_ffmpeg", lambda _dir=None: "ffmpeg")
    monkeypatch.setattr(af, "subprocess_runner", lambda _cmd: _output(_music()))
    monkeypatch.setattr(af, "find_features_worker", lambda: ("python", "tempo_key.py"))
    monkeypatch.setattr(
        af,
        "TempoKeyWorker",
        lambda *_a, **_k: _FakeWorker(lambda _id: {"tempo": 140.2, "key": "4A"}),
    )
    out = StringIO()
    call_command("analyze_audio_features", stdout=out)
    assert out.getvalue().splitlines() == [
        "measured 1, failed 0, not written 0, waiting 0",
        "tempo / key: measured 1, failed 0, not written 0, waiting 0",
    ]
    assert _tk_row(track.id)[:2] == (140, "4A")
    out = StringIO()
    call_command("analyze_audio_features", "--tempo-key-only", stdout=out)
    assert out.getvalue() == ""

    monkeypatch.setattr(af, "find_features_worker", lambda: None)
    out = StringIO()
    call_command("analyze_audio_features", "--tempo-key-only", stdout=out)
    assert "install-features-venv.ps1" in out.getvalue()


def test_clearing_the_unselected_types_keeps_hand_and_tag_values(library, music):
    song = _track(library, "song.mp3", library=music)
    spot = _track(library, "spot.mp3", library=music)
    hand = _track(library, "hand.mp3", library=music, bpm=140)  # BPM tag
    _pass(library)
    _tk_pass(library, lambda _id: {"tempo": 120.2, "key": "8A"})
    energy = _row(hand.id)[0] % 10 + 1
    _set(hand.id, energy=energy, musical_key="3B")  # by hand

    jingles = _type("tjin", False)
    with connection.cursor() as cur:
        cur.execute(
            "UPDATE cc_files SET track_type_id = %s WHERE id = ANY(%s)",
            [jingles.id, [spot.id, hand.id]],
        )
        assert af.clear_unselected(cur, dry_run=True)["tracks"] == 2
        assert _row(spot.id)[2] is not None
        counts = af.clear_unselected(cur)
    assert counts == {"tracks": 2, "kept_energy": 1, "kept_brightness": 0, "kept_bpm": 1,
                      "kept_key": 1}  # fmt: skip
    assert _row(spot.id) == (None, None, None) and _tk_row(spot.id) == (None, None, None)
    assert _row(hand.id) == (energy, None, None) and _tk_row(hand.id) == (140, "3B", None)
    assert _row(song.id)[2]["energy"] and _tk_row(song.id)[:2] == (120, "8A")
    with connection.cursor() as cur:
        assert af.clear_unselected(cur)["tracks"] == 0
        assert af.remaining(cur) == 0  # the cleared ones are not measured again
