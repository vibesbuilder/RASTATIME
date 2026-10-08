"""
T-OP-2 — Remove dead Linux-only package declarations.

Verify that gunicorn, uvicorn, celery and kombu no longer appear in any
requirements.txt or setup.py file in the backend.  These packages are
not installable or not needed on Windows:

  gunicorn  — Linux WSGI server; replaced by Waitress (T17.1)
  uvicorn   — ASGI server; was imported only by the deleted gunicorn.py
  celery    — Linux task queue; replaced by RastatimeWorker (T18.x)
  kombu     — Celery message transport; dead together with Celery

The Celery-based ``backend/worker`` package (libretime_worker) was deleted
outright in 11ce0cc; its replacement ``backend/rastatime_worker`` is a
plain package without requirements.txt / setup.py of its own, so the
worker checks assert that the dead package stays gone and that its
successor imports neither celery nor kombu (tests updated 2026-10-02).

Test inventory (10 tests, always run — no Django needed):
  1.  backend/api/requirements.txt does not contain gunicorn.
  2.  backend/api/requirements.txt does not contain uvicorn.
  3.  backend/worker (the dead Celery package) no longer exists.
  4.  backend/rastatime_worker imports neither celery nor kombu.
  5.  backend/playout/requirements.txt does not contain kombu.
  6.  backend/api/setup.py does not contain gunicorn.
  7.  backend/api/setup.py does not contain uvicorn.
  8.  backend/rastatime_worker ships no setup.py / requirements.txt that
      could reintroduce celery or kombu.
  9.  backend/playout/setup.py does not contain kombu.
 10.  No requirements.txt anywhere in backend/ contains any of the
      four dead packages.
"""

from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_BACKEND = _REPO / "backend"

_API_REQ     = _BACKEND / "api"     / "requirements.txt"
_PLAYOUT_REQ = _BACKEND / "playout" / "requirements.txt"
_API_SETUP    = _BACKEND / "api"     / "setup.py"
_PLAYOUT_SETUP= _BACKEND / "playout" / "setup.py"
_DEAD_WORKER  = _BACKEND / "worker"             # Celery worker, deleted in 11ce0cc
_WORKER_PKG   = _BACKEND / "rastatime_worker"   # its replacement

_DEAD = ("gunicorn", "uvicorn", "celery", "kombu")


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1–5  requirements.txt files
# ---------------------------------------------------------------------------

def test_api_requirements_no_gunicorn():
    """backend/api/requirements.txt must not list gunicorn (replaced by Waitress)."""
    assert "gunicorn" not in _read(_API_REQ), (
        "backend/api/requirements.txt still lists gunicorn"
    )


def test_api_requirements_no_uvicorn():
    """backend/api/requirements.txt must not list uvicorn (dead with gunicorn.py)."""
    assert "uvicorn" not in _read(_API_REQ), (
        "backend/api/requirements.txt still lists uvicorn"
    )


def test_dead_celery_worker_package_is_gone():
    """backend/worker (libretime_worker, Celery) was deleted in 11ce0cc and
    must not come back - RastatimeWorker lives in backend/rastatime_worker."""
    assert not _DEAD_WORKER.exists(), (
        "backend/worker reappeared - the Celery worker was removed in 11ce0cc"
    )


def test_rastatime_worker_imports_neither_celery_nor_kombu():
    """No module of backend/rastatime_worker may import celery or kombu."""
    offenders = [
        str(p.relative_to(_REPO))
        for p in _WORKER_PKG.rglob("*.py")
        if "celery" in _read(p) or "kombu" in _read(p)
    ]
    assert not offenders, (
        "backend/rastatime_worker still references celery/kombu: " + ", ".join(offenders)
    )


def test_playout_requirements_no_kombu():
    """backend/playout/requirements.txt must not list kombu."""
    assert "kombu" not in _read(_PLAYOUT_REQ), (
        "backend/playout/requirements.txt still lists kombu"
    )


# ---------------------------------------------------------------------------
# 6–9  setup.py files
# ---------------------------------------------------------------------------

def test_api_setup_no_gunicorn():
    """backend/api/setup.py must not declare gunicorn as a dependency."""
    assert "gunicorn" not in _read(_API_SETUP), (
        "backend/api/setup.py still declares gunicorn"
    )


def test_api_setup_no_uvicorn():
    """backend/api/setup.py must not declare uvicorn as a dependency."""
    assert "uvicorn" not in _read(_API_SETUP), (
        "backend/api/setup.py still declares uvicorn"
    )


def test_rastatime_worker_declares_no_celery_or_kombu():
    """backend/rastatime_worker has no packaging files of its own (it is
    installed with the API); should any appear, they must not declare
    celery or kombu."""
    for name in ("setup.py", "requirements.txt", "pyproject.toml"):
        path = _WORKER_PKG / name
        if not path.exists():
            continue
        text = _read(path)
        assert "celery" not in text, f"{path.name} declares celery"
        assert "kombu" not in text, f"{path.name} declares kombu"


def test_playout_setup_no_kombu():
    """backend/playout/setup.py must not declare kombu."""
    assert "kombu" not in _read(_PLAYOUT_SETUP), (
        "backend/playout/setup.py still declares kombu"
    )


# ---------------------------------------------------------------------------
# 10  No requirements.txt anywhere in backend/ contains dead packages
# ---------------------------------------------------------------------------

def test_no_requirements_txt_contains_dead_packages():
    """
    Every requirements.txt under backend/ must be free of gunicorn,
    uvicorn, celery, and kombu.  Catches any future requirements file
    that might reintroduce these packages.
    """
    violations = []
    for req in _BACKEND.rglob("requirements.txt"):
        text = req.read_text(encoding="utf-8")
        for pkg in _DEAD:
            if pkg in text:
                violations.append(f"{req.relative_to(_REPO)}: contains '{pkg}'")
    assert not violations, (
        "Dead packages found in requirements files:\n" + "\n".join(violations)
    )
