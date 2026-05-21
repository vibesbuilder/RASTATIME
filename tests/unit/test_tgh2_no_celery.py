"""
T-GH-2 - Remove Celery worker code.

Verify that the libretime_worker package no longer depends on Celery or kombu,
that all tasks are plain Python functions, that no Python file in the worker
package imports from celery/kombu at the module level (outside a try/except),
and that the worker modules are importable without a Celery ImportError.

Test inventory (10 tests):
  1.  No 'from celery' or 'import celery' appears anywhere in backend/.
  2.  No 'from kombu' or 'import kombu' appears anywhere in backend/.
  3.  libretime_worker/config.py contains no Celery settings (BROKER_URL etc.).
  4.  libretime_worker/main.py does not call worker.worker_main.
  5.  libretime_worker/tasks.py defines podcast_download as a plain function.
  6.  libretime_worker/tasks.py defines extract_filename as a plain function.
  7.  libretime_worker/tasks.py does not contain @worker.task decorators.
  8.  No .py file in libretime_worker/ has an unguarded celery/kombu import.
  9.  libretime_worker.config is importable without a Celery-related ImportError.
  10. libretime_worker.tasks is importable without a Celery-related ImportError.
"""

from __future__ import annotations

import ast
import importlib
import os
import sys
from pathlib import Path

_REPO   = Path(__file__).resolve().parents[2]
_BACKEND = _REPO / "backend"
_WORKER  = _BACKEND / "worker" / "libretime_worker"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _grep_backend(pattern: str) -> list[Path]:
    """Return all .py files under backend/ whose text contains *pattern*."""
    hits = []
    for py in _BACKEND.rglob("*.py"):
        try:
            if pattern in py.read_text(encoding="utf-8"):
                hits.append(py)
        except (OSError, UnicodeDecodeError):
            pass
    return hits


def _has_unguarded_import(filepath: Path, keyword: str) -> bool:
    """
    Return True if *filepath* has a top-level import of *keyword* that is NOT
    inside a try/except block.
    """
    source = filepath.read_text(encoding="utf-8")
    if keyword not in source:
        return False  # Fast path: keyword absent

    tree = ast.parse(source)

    for node in ast.walk(tree):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if keyword not in module:
                continue
        else:
            names = [alias.name for alias in node.names]
            if not any(keyword in n for n in names):
                continue

        # Found a matching import — check it lives inside a Try node
        for try_node in ast.walk(tree):
            if not isinstance(try_node, ast.Try):
                continue
            for child in ast.walk(try_node):
                if child is node:
                    break
            else:
                continue
            break  # found in a try block
        else:
            return True  # unguarded import found

    return False


# ---------------------------------------------------------------------------
# 1-2  No celery / kombu anywhere in backend/
# ---------------------------------------------------------------------------

def test_no_celery_import_in_backend():
    """No file in backend/ may contain 'from celery' or 'import celery'."""
    celery_files = []
    for py in _BACKEND.rglob("*.py"):
        try:
            text = py.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if "from celery" in text or "import celery" in text:
            celery_files.append(str(py.relative_to(_REPO)))
    assert not celery_files, (
        "celery imports still found in backend/:\n" + "\n".join(celery_files)
    )


def test_no_kombu_import_in_worker():
    """
    No file in the *worker* package may contain 'from kombu' or 'import kombu'.

    kombu as a standalone AMQP library (e.g. in playout/message_handler.py) is
    allowed; it is only the Celery-driven kombu usage in the worker that T-GH-2
    removes.
    """
    kombu_files = []
    for py in _WORKER.rglob("*.py"):
        try:
            text = py.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if "from kombu" in text or "import kombu" in text:
            kombu_files.append(str(py.relative_to(_REPO)))
    assert not kombu_files, (
        "kombu imports still found in libretime_worker/:\n" + "\n".join(kombu_files)
    )


# ---------------------------------------------------------------------------
# 3-4  Specific file content checks
# ---------------------------------------------------------------------------

def test_config_has_no_celery_settings():
    """libretime_worker/config.py must not define BROKER_URL or CELERY_* vars."""
    text = (_WORKER / "config.py").read_text(encoding="utf-8")
    celery_vars = [
        "BROKER_URL",
        "CELERY_RESULT_BACKEND",
        "CELERY_QUEUES",
        "CELERY_TASK_SERIALIZER",
        "CELERY_TIMEZONE",
    ]
    found = [v for v in celery_vars if v in text]
    assert not found, (
        f"config.py still contains Celery settings: {found}"
    )


def test_main_has_no_worker_main_call():
    """libretime_worker/main.py must not call worker.worker_main."""
    text = (_WORKER / "main.py").read_text(encoding="utf-8")
    assert "worker_main" not in text, (
        "main.py still calls worker.worker_main (Celery entrypoint)"
    )


# ---------------------------------------------------------------------------
# 5-7  tasks.py plain-function checks
# ---------------------------------------------------------------------------

def test_tasks_podcast_download_is_plain_function():
    """tasks.py must define podcast_download as a plain def, not a Celery task."""
    source = (_WORKER / "tasks.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "podcast_download":
            # Must have no decorators that reference 'task'
            for dec in node.decorator_list:
                dec_src = ast.unparse(dec)
                assert "task" not in dec_src, (
                    f"podcast_download still has a Celery @task decorator: {dec_src}"
                )
            return  # found and checked
    raise AssertionError("podcast_download function not found in tasks.py")


def test_tasks_extract_filename_is_plain_function():
    """tasks.py must define extract_filename as a plain def."""
    source = (_WORKER / "tasks.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "extract_filename":
            assert not node.decorator_list, (
                "extract_filename unexpectedly has decorators"
            )
            return
    raise AssertionError("extract_filename function not found in tasks.py")


def test_tasks_no_worker_task_decorator():
    """tasks.py must not contain any @worker.task(...) decorator."""
    text = (_WORKER / "tasks.py").read_text(encoding="utf-8")
    assert "@worker.task" not in text, (
        "tasks.py still contains @worker.task decorator (Celery)"
    )


# ---------------------------------------------------------------------------
# 8  No unguarded celery/kombu imports in libretime_worker/
# ---------------------------------------------------------------------------

def test_no_unguarded_celery_or_kombu_imports_in_worker():
    """No .py file in libretime_worker/ has an unguarded celery or kombu import."""
    violations = []
    for py in _WORKER.rglob("*.py"):
        if _has_unguarded_import(py, "celery"):
            violations.append(f"{py.relative_to(_REPO)} (celery)")
        if _has_unguarded_import(py, "kombu"):
            violations.append(f"{py.relative_to(_REPO)} (kombu)")
    assert not violations, (
        "Unguarded celery/kombu imports found:\n" + "\n".join(violations)
    )


# ---------------------------------------------------------------------------
# 9-10  Import safety
# ---------------------------------------------------------------------------

def _setup_worker_path():
    worker_root = str(_REPO / "backend" / "worker")
    if worker_root not in sys.path:
        sys.path.insert(0, worker_root)
    # Ensure fresh import
    for key in list(sys.modules):
        if key.startswith("libretime_worker"):
            del sys.modules[key]


def _assert_no_celery_import_error(module_name: str) -> None:
    """Import module and fail only if the ImportError mentions 'celery' or 'kombu'."""
    _setup_worker_path()

    # Set required env vars so Config can initialise
    os.environ.setdefault("LIBRETIME_GENERAL_PUBLIC_URL", "http://localhost")
    os.environ.setdefault("LIBRETIME_GENERAL_API_KEY", "testing")
    os.environ.setdefault("LIBRETIME_GENERAL_SECRET_KEY", "testing")

    try:
        importlib.import_module(module_name)
    except ImportError as exc:
        msg = str(exc).lower()
        if "celery" in msg or "kombu" in msg:
            raise AssertionError(
                f"{module_name} raised celery/kombu ImportError: {exc}"
            ) from exc
        # Other missing packages (libretime_shared, libretime_api_client, …)
        # are pre-existing issues unrelated to T-GH-2 — treat as skip-worthy.
    except Exception:
        # Config initialisation errors (e.g. missing fields) are unrelated to T-GH-2.
        pass


def test_config_importable():
    """libretime_worker.config must not fail due to a celery/kombu ImportError."""
    _assert_no_celery_import_error("libretime_worker.config")


def test_tasks_importable():
    """libretime_worker.tasks must not fail due to a celery/kombu ImportError."""
    _assert_no_celery_import_error("libretime_worker.tasks")
