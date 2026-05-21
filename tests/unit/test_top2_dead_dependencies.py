"""
T-OP-2 — Remove dead Linux-only package declarations.

Verify that gunicorn, uvicorn, celery and kombu no longer appear in any
requirements.txt or setup.py file in the backend.  These packages are
not installable or not needed on Windows:

  gunicorn  — Linux WSGI server; replaced by Waitress (T17.1)
  uvicorn   — ASGI server; was imported only by the deleted gunicorn.py
  celery    — Linux task queue; replaced by RastatimeWorker (T18.x)
  kombu     — Celery message transport; dead together with Celery

Test inventory (10 tests, always run — no Django needed):
  1.  backend/api/requirements.txt does not contain gunicorn.
  2.  backend/api/requirements.txt does not contain uvicorn.
  3.  backend/worker/requirements.txt does not contain celery.
  4.  backend/worker/requirements.txt does not contain kombu.
  5.  backend/playout/requirements.txt does not contain kombu.
  6.  backend/api/setup.py does not contain gunicorn.
  7.  backend/api/setup.py does not contain uvicorn.
  8.  backend/worker/setup.py does not contain celery or kombu.
  9.  backend/playout/setup.py does not contain kombu.
 10.  No requirements.txt anywhere in backend/ contains any of the
      four dead packages.
"""

from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_BACKEND = _REPO / "backend"

_API_REQ     = _BACKEND / "api"     / "requirements.txt"
_WORKER_REQ  = _BACKEND / "worker"  / "requirements.txt"
_PLAYOUT_REQ = _BACKEND / "playout" / "requirements.txt"
_API_SETUP    = _BACKEND / "api"     / "setup.py"
_WORKER_SETUP = _BACKEND / "worker"  / "setup.py"
_PLAYOUT_SETUP= _BACKEND / "playout" / "setup.py"

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


def test_worker_requirements_no_celery():
    """backend/worker/requirements.txt must not list celery (replaced by RastatimeWorker)."""
    assert "celery" not in _read(_WORKER_REQ), (
        "backend/worker/requirements.txt still lists celery"
    )


def test_worker_requirements_no_kombu():
    """backend/worker/requirements.txt must not list kombu (Celery transport, dead)."""
    assert "kombu" not in _read(_WORKER_REQ), (
        "backend/worker/requirements.txt still lists kombu"
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


def test_worker_setup_no_celery_or_kombu():
    """backend/worker/setup.py must not declare celery or kombu."""
    text = _read(_WORKER_SETUP)
    assert "celery" not in text, "backend/worker/setup.py still declares celery"
    assert "kombu"  not in text, "backend/worker/setup.py still declares kombu"


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
