"""
RASTATIME 2026-11-01 - the silencedetect log prefix.

Newer ffmpeg builds log the filter instance as ``[Parsed_silencedetect_1 @
0x...]`` (the index follows the position in the filter chain, the highpass
sits in front).  The upstream pattern matched ``[silencedetect @ ...]`` only,
so every import since the ffmpeg update silently got cuein 0 and cueout =
length.  Both spellings must parse.
"""

import pytest
from rastatime_analyzer.pipeline._ffmpeg import _SILENCE_DETECT_RE


@pytest.mark.parametrize(
    "line,kind,value",
    [
        ("[silencedetect @ 0x55d1c0] silence_start: 0.000729167", "start", 0.000729167),
        (
            "[silencedetect @ 0x55d1c0] silence_end: 1.401729 | silence_duration: 1.401",
            "end",
            1.401729,
        ),
        ("[Parsed_silencedetect_1 @ 000002c27f192200] silence_start: 8.514646", "start", 8.514646),
        (
            "[Parsed_silencedetect_0 @ 000002c27f192200] silence_end: 15 | silence_duration: 0.42",
            "end",
            15.0,
        ),
        ("[Parsed_silencedetect_1 @ 0x1] silence_start: -0.0001", "start", -0.0001),
    ],
)
def test_silencedetect_line_parses(line, kind, value):
    match = _SILENCE_DETECT_RE.search(line)
    assert match is not None
    assert match.group(1) == kind
    assert float(match.group(2)) == pytest.approx(value)


def test_other_filter_lines_are_ignored():
    assert _SILENCE_DETECT_RE.search("[Parsed_highpass_0 @ 0x1] silence_start: 1.0") is None
    assert _SILENCE_DETECT_RE.search("[silencedetect @ 0x1] something else") is None
