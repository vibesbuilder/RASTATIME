"""
RASTATIME 2026-11-22 - ffprobe output across ffmpeg versions, without ffmpeg:
the COMM key spellings of 9.0 and 9.1 and the packet totals parser behind
the raw ADTS length.
"""

import subprocess
from pathlib import Path

import pytest
from rastatime_analyzer.pipeline import _ffmpeg, analyze_metadata


def _probe_tags(monkeypatch, format_tags: dict) -> dict:
    data = {
        "format": {"format_name": "wav", "tags": format_tags},
        "streams": [{"codec_type": "audio", "sample_rate": "44100"}],
    }
    monkeypatch.setattr(analyze_metadata, "ffprobe_json", lambda *_a, **_k: data)
    probe = analyze_metadata._probe_with_ffprobe(Path("x.wav"))
    assert probe is not None
    return probe[2]


@pytest.mark.parametrize(
    "format_tags, expected",
    [
        ({"comment": "Plain"}, "Plain"),  # ffmpeg 9.0
        ({"comment-eng": "Eng"}, "Eng"),  # ffmpeg 9.1
        ({"COMMENT-DEU": "Deu"}, "Deu"),  # keys are lower-cased first
        ({"comment-deu": "Deu", "comment-eng": "Eng"}, "Deu"),  # first wins
        ({"comment-eng": "Eng", "comment": "Plain"}, "Plain"),  # plain key wins
        # 9.1 "comment-<description>-<language>" (9.0: the description alone)
        ({"comment-iTunNORM-eng": " 0000 1111", "comment-eng": "Real"}, "Real"),
        ({"comment-Notes-eng": "With description"}, None),
        ({"iTunNORM": " 0000 1111"}, None),
    ],
)
def test_comment_key_of_both_ffmpeg_versions(monkeypatch, format_tags, expected):
    tags = _probe_tags(monkeypatch, format_tags)

    assert tags.get("comment") == expected


def test_language_comment_fills_the_three_comment_fields(monkeypatch):
    _probe_tags(monkeypatch, {"comment-eng": "Wav Comment"})
    metadata: dict = {}

    probe = analyze_metadata._probe_with_ffprobe(Path("x.wav"))
    analyze_metadata._fill_from_ffprobe(Path("x.wav"), metadata, probe)

    assert metadata["comment"] == metadata["comments"] == metadata["description"]
    assert metadata["comment"] == "Wav Comment"


def _fake_ffprobe(monkeypatch, stdout: str, returncode: int = 0):
    def run(cmd, **_kwargs):
        return subprocess.CompletedProcess(cmd, returncode, stdout.encode("ascii"), b"")

    monkeypatch.setattr(_ffmpeg.subprocess, "run", run)


def test_packet_totals_sum_durations_and_sizes(monkeypatch):
    # 1024 samples at 44.1 kHz in ffprobe's ADTS time base, three packets
    _fake_ffprobe(
        monkeypatch,
        "packet,655360,200\npacket,655360,300\npacket,655360,500\nstream,1/28224000\n",
    )

    seconds, size = _ffmpeg.probe_packet_totals("x.aac")

    assert seconds == pytest.approx(3 * 1024 / 44100)
    assert size == 1000


@pytest.mark.parametrize(
    "stdout, returncode",
    [
        ("packet,N/A,200\nstream,1/28224000\n", 0),  # a packet without duration
        ("packet,655360,200\nstream,0/1\n", 0),  # no usable time base
        ("packet,655360,200\n", 0),  # no stream line
        ("stream,1/28224000\n", 0),  # no packets
        ("", 1),  # ffprobe failed
    ],
)
def test_packet_totals_give_up_rather_than_guess(monkeypatch, stdout, returncode):
    _fake_ffprobe(monkeypatch, stdout, returncode)

    assert _ffmpeg.probe_packet_totals("x.aac") is None


def test_packet_totals_without_ffprobe(monkeypatch):
    def missing(*_args, **_kwargs):
        raise FileNotFoundError("ffprobe")

    monkeypatch.setattr(_ffmpeg.subprocess, "run", missing)

    assert _ffmpeg.probe_packet_totals("x.aac") is None


@pytest.mark.parametrize("name, expected", [("aac", True), ("AAC", True), ("mov,mp4,m4a", False)])
def test_raw_adts_format_name(name, expected):
    assert _ffmpeg.is_raw_adts_format(name) is expected
