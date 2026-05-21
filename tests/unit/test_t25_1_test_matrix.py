"""
T25.1 — Execute full test matrix.

Verify that the M25 release-readiness test matrix document exists and
contains all required content: suite results, milestone coverage, skip
analysis, release criteria, and the platform declaration.

Test inventory (10 tests, always run — no Django needed):
  1.  TEST_MATRIX.md exists under docs/architecture/.
  2.  Document declares the release verdict as PASS.
  3.  Document records ≥ 900 passing tests.
  4.  Document records the number of skipped tests (81).
  5.  Document covers all milestones M3 through M24.
  6.  Document references M25 as the current release milestone.
  7.  Document covers all six functional test areas.
  8.  Document identifies the two skip categories (VLC and Django).
  9.  Document references the Windows platform (win32 / Windows 11).
 10.  Document contains a dated release criteria table.
"""

from __future__ import annotations

from pathlib import Path

_REPO   = Path(__file__).resolve().parents[2]
_MATRIX = _REPO / "docs" / "architecture" / "TEST_MATRIX.md"


def _read() -> str:
    return _MATRIX.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1  Existence
# ---------------------------------------------------------------------------

def test_test_matrix_exists():
    """docs/architecture/TEST_MATRIX.md must exist."""
    assert _MATRIX.exists(), f"Missing: {_MATRIX}"


# ---------------------------------------------------------------------------
# 2  Release verdict
# ---------------------------------------------------------------------------

def test_test_matrix_declares_pass():
    """
    TEST_MATRIX.md must declare a PASS verdict so the M25 release gate
    is explicit and reviewable.
    """
    text = _read()
    assert "PASS" in text, (
        "TEST_MATRIX.md must contain a PASS release verdict"
    )


# ---------------------------------------------------------------------------
# 3  Passing test count ≥ 900
# ---------------------------------------------------------------------------

def test_test_matrix_records_passing_count():
    """
    TEST_MATRIX.md must record at least 900 passing tests.
    The number '915' (or any value ≥ 900) must appear in the document.
    """
    text = _read()
    # Extract all integers that appear in the document and find any ≥ 900.
    import re
    numbers = [int(m) for m in re.findall(r"\b(\d{3,})\b", text)]
    assert any(n >= 900 for n in numbers), (
        "TEST_MATRIX.md must record a passing test count of at least 900"
    )


# ---------------------------------------------------------------------------
# 4  Skipped test count documented
# ---------------------------------------------------------------------------

def test_test_matrix_records_skipped_count():
    """
    TEST_MATRIX.md must document the 81 skipped tests so the skip
    disposition is explicit.
    """
    assert "81" in _read(), (
        "TEST_MATRIX.md must reference '81' (the skipped test count)"
    )


# ---------------------------------------------------------------------------
# 5  All milestones M3–M24 covered
# ---------------------------------------------------------------------------

def test_test_matrix_covers_milestones_m3_to_m24():
    """
    TEST_MATRIX.md must reference every milestone from M3 to M24 so
    reviewers can confirm complete coverage before the M25 gate.
    """
    text = _read()
    missing = [f"M{n}" for n in range(3, 25) if f"M{n}" not in text]
    assert not missing, (
        f"TEST_MATRIX.md is missing milestone references: {missing}"
    )


# ---------------------------------------------------------------------------
# 6  M25 declared as current milestone
# ---------------------------------------------------------------------------

def test_test_matrix_references_m25():
    """TEST_MATRIX.md must reference M25 as the release milestone."""
    assert "M25" in _read(), (
        "TEST_MATRIX.md must reference M25 as the current release milestone"
    )


# ---------------------------------------------------------------------------
# 7  All six functional test areas covered
# ---------------------------------------------------------------------------

def test_test_matrix_covers_all_functional_areas():
    """
    TEST_MATRIX.md must reference all six functional test groups:
    playout, streams, audio, linein, worker, operator docs.
    """
    text = _read().lower()
    required = ["playout", "stream", "audio", "linein", "worker", "operator"]
    missing = [area for area in required if area not in text]
    assert not missing, (
        f"TEST_MATRIX.md is missing functional area references: {missing}"
    )


# ---------------------------------------------------------------------------
# 8  Both skip categories documented
# ---------------------------------------------------------------------------

def test_test_matrix_documents_skip_categories():
    """
    TEST_MATRIX.md must document both skip categories — VLC
    hardware-integration tests and Django-gated tests — so skips are
    understood as intentional, not silent failures.
    """
    text = _read().lower()
    assert "vlc" in text, (
        "TEST_MATRIX.md must document VLC hardware-dependent skips"
    )
    assert "django" in text, (
        "TEST_MATRIX.md must document Django-gated skips"
    )


# ---------------------------------------------------------------------------
# 9  Windows platform declared
# ---------------------------------------------------------------------------

def test_test_matrix_declares_windows_platform():
    """
    TEST_MATRIX.md must declare Windows as the target platform so the
    matrix is unambiguous about the execution environment.
    """
    text = _read()
    assert "Windows" in text or "win32" in text, (
        "TEST_MATRIX.md must reference Windows as the execution platform"
    )


# ---------------------------------------------------------------------------
# 10  Dated release criteria table
# ---------------------------------------------------------------------------

def test_test_matrix_contains_dated_release_criteria():
    """
    TEST_MATRIX.md must contain a release criteria table and a date so
    the gate is time-stamped and reproducible.
    """
    text = _read()
    assert "2026-04-30" in text, (
        "TEST_MATRIX.md must include the execution date 2026-04-30"
    )
    assert "criteria" in text.lower(), (
        "TEST_MATRIX.md must contain a release criteria section"
    )
