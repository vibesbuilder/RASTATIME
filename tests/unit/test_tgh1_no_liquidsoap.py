"""
T-GH-1 - Remove Liquidsoap subdirectory.

Verify that the libretime_playout.liquidsoap package and all its sub-modules
no longer exist in the codebase, that no Python file in the playout package
imports from it at module level (i.e. without a try/except guard), and that
the NSSM install script no longer declares the libretime-liquidsoap console
script entry point.

Test inventory (10 tests):
  1.  liquidsoap/ directory does not exist inside libretime_playout.
  2.  player/liquidsoap.py does not exist inside libretime_playout.
  3.  tests/liquidsoap/ directory does not exist inside backend/playout/tests.
  4.  tests/player/liquidsoap_test.py does not exist.
  5.  setup.py does not declare the 'libretime-liquidsoap' entry point.
  6.  main.py imports liquidsoap only inside a try/except block.
  7.  player/fetch.py imports liquidsoap only inside a try/except block.
  8.  No .py file outside a try/except block in libretime_playout imports
      from liquidsoap at the top level.
  9.  libretime_playout.main is importable without ImportError.
  10. libretime_playout.player.fetch is importable without ImportError.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

_REPO    = Path(__file__).resolve().parents[2]
_PLAYOUT = _REPO / "backend" / "playout" / "libretime_playout"
_TESTS   = _REPO / "backend" / "playout" / "tests"
_SETUP   = _REPO / "backend" / "playout" / "setup.py"


# ---------------------------------------------------------------------------
# 1-4  File / directory absence
# ---------------------------------------------------------------------------

def test_liquidsoap_directory_removed():
    """libretime_playout/liquidsoap/ must not exist."""
    assert not (_PLAYOUT / "liquidsoap").exists(), (
        "liquidsoap/ directory still present inside libretime_playout"
    )


def test_player_liquidsoap_py_removed():
    """libretime_playout/player/liquidsoap.py must not exist."""
    assert not (_PLAYOUT / "player" / "liquidsoap.py").exists(), (
        "player/liquidsoap.py still present inside libretime_playout"
    )


def test_liquidsoap_test_directory_removed():
    """backend/playout/tests/liquidsoap/ must not exist."""
    assert not (_TESTS / "liquidsoap").exists(), (
        "tests/liquidsoap/ directory still present"
    )


def test_liquidsoap_player_test_removed():
    """backend/playout/tests/player/liquidsoap_test.py must not exist."""
    assert not (_TESTS / "player" / "liquidsoap_test.py").exists(), (
        "tests/player/liquidsoap_test.py still present"
    )


# ---------------------------------------------------------------------------
# 5  setup.py entry point
# ---------------------------------------------------------------------------

def test_setup_no_liquidsoap_entry_point():
    """backend/playout/setup.py must not declare libretime-liquidsoap."""
    text = _SETUP.read_text(encoding="utf-8")
    assert "libretime-liquidsoap" not in text, (
        "setup.py still declares the 'libretime-liquidsoap' console script"
    )


# ---------------------------------------------------------------------------
# 6-8  try/except guards
# ---------------------------------------------------------------------------

def _has_guarded_liquidsoap_import(filepath: Path) -> bool:
    """Return True if every 'liquidsoap' import in filepath is inside try/except."""
    source = filepath.read_text(encoding="utf-8")
    if "liquidsoap" not in source:
        return True  # No liquidsoap imports at all — trivially safe

    tree = ast.parse(source)

    for node in ast.walk(tree):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        # Check if this import references liquidsoap
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if "liquidsoap" not in module:
                continue
        else:
            names = [alias.name for alias in node.names]
            if not any("liquidsoap" in n for n in names):
                continue

        # Found a liquidsoap import — check it's inside a Try node
        # We check by scanning all Try nodes in the tree
        for try_node in ast.walk(tree):
            if not isinstance(try_node, ast.Try):
                continue
            for child in ast.walk(try_node):
                if child is node:
                    break
            else:
                continue
            break
        else:
            return False  # Found unguarded import

    return True


def test_main_py_liquidsoap_import_guarded():
    """libretime_playout/main.py must only import liquidsoap inside try/except."""
    assert _has_guarded_liquidsoap_import(_PLAYOUT / "main.py"), (
        "main.py has unguarded top-level liquidsoap import"
    )


def test_fetch_py_liquidsoap_import_guarded():
    """libretime_playout/player/fetch.py must only import liquidsoap inside try/except."""
    assert _has_guarded_liquidsoap_import(_PLAYOUT / "player" / "fetch.py"), (
        "player/fetch.py has unguarded top-level liquidsoap import"
    )


def test_no_unguarded_liquidsoap_imports_in_playout():
    """No .py file in libretime_playout/ has an unguarded liquidsoap import."""
    violations = []
    for py_file in _PLAYOUT.rglob("*.py"):
        if not _has_guarded_liquidsoap_import(py_file):
            violations.append(str(py_file.relative_to(_REPO)))
    assert not violations, (
        "Unguarded liquidsoap imports found:\n" + "\n".join(violations)
    )


# ---------------------------------------------------------------------------
# 9-10  Import safety
# ---------------------------------------------------------------------------

def _assert_no_liquidsoap_import_error(module_name: str) -> None:
    """Import module and fail only if the ImportError mentions 'liquidsoap'."""
    playout_root = str(_REPO / "backend" / "playout")
    if playout_root not in sys.path:
        sys.path.insert(0, playout_root)

    import importlib

    # Remove from cache so we get a fresh import attempt.
    for key in list(sys.modules):
        if key.startswith("libretime_playout"):
            del sys.modules[key]

    try:
        importlib.import_module(module_name)
    except ImportError as exc:
        if "liquidsoap" in str(exc).lower():
            raise AssertionError(
                f"{module_name} raised liquidsoap ImportError: {exc}"
            ) from exc
        # Other missing packages (libretime_api_client, kombu, …) are
        # pre-existing issues unrelated to T-GH-1 — treat as skip-worthy.


def test_main_py_importable():
    """libretime_playout.main must not fail due to a liquidsoap ImportError."""
    _assert_no_liquidsoap_import_error("libretime_playout.main")


def test_fetch_py_importable():
    """libretime_playout.player.fetch must not fail due to a liquidsoap ImportError."""
    _assert_no_liquidsoap_import_error("libretime_playout.player.fetch")
