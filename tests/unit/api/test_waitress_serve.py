"""
T17.1 — Waitress server entry-point unit tests.

Split into two groups:

Pure-Waitress tests (8) — no Django required; run in every environment:
  1.  Waitress package is installed and importable.
  2.  ``waitress.serve`` is a callable.
  3.  ``waitress.create_server`` is a callable.
  4.  Waitress version is 3.x or higher.
  5.  Default host is ``127.0.0.1``.
  6.  Default port is ``8000``.
  7.  Default thread count is ``4``.
  8.  Default Django settings module is the production settings string.

rastatime_api tests (8) — skipped when Django / rastatime_api is absent:
  9.  ``waitress_serve`` module is importable from ``rastatime_api``.
 10.  ``_parse_args()`` returns defaults when called with empty argv.
 11.  ``--host`` CLI flag overrides the default host.
 12.  ``--port`` CLI flag overrides the default port.
 13.  ``--threads`` CLI flag overrides the default thread count.
 14.  ``RASTATIME_API_HOST`` env var sets the host default.
 15.  ``RASTATIME_API_PORT`` env var sets the port default.
 16.  WSGI ``application`` object is a callable (Django WSGI app).

(16 tests total; 8 skipped in the root venv where Django is absent)
"""

from __future__ import annotations

import os

import pytest


# ---------------------------------------------------------------------------
# 1–8  Pure-Waitress tests — no Django required
# ---------------------------------------------------------------------------

def test_waitress_is_importable():
    """Waitress package must be installed in this environment (T17.1)."""
    import waitress  # noqa: PLC0415
    assert waitress is not None


def test_waitress_serve_is_callable():
    import waitress  # noqa: PLC0415
    assert callable(waitress.serve)


def test_waitress_create_server_is_callable():
    import waitress  # noqa: PLC0415
    assert callable(waitress.create_server)


def test_waitress_version_is_3_or_higher():
    from importlib.metadata import version  # noqa: PLC0415
    ver = version("waitress")
    major = int(ver.split(".")[0])
    assert major >= 3, f"Expected Waitress >= 3.0.0, got {ver}"


def test_default_host_is_localhost():
    from backend.rastatime_worker.jobs._base import JobResult  # noqa: PLC0415 — path sanity
    # We cannot import waitress_serve without Django; test the constant via
    # a source-read approach.  Verify the expected default is documented in
    # the module.
    import ast  # noqa: PLC0415
    import pathlib  # noqa: PLC0415
    src = (
        pathlib.Path(__file__).parents[3]
        / "backend" / "api" / "rastatime_api" / "waitress_serve.py"
    )
    tree = ast.parse(src.read_text(encoding="utf-8"))
    defaults = {
        node.targets[0].id: node.value.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and isinstance(node.value, (ast.Constant,))
    }
    assert defaults.get("_DEFAULT_HOST") == "127.0.0.1"


def test_default_port_is_8000():
    import ast, pathlib  # noqa: PLC0415,E401
    src = (
        pathlib.Path(__file__).parents[3]
        / "backend" / "api" / "rastatime_api" / "waitress_serve.py"
    )
    tree = ast.parse(src.read_text(encoding="utf-8"))
    defaults = {
        node.targets[0].id: node.value.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and isinstance(node.value, ast.Constant)
    }
    assert defaults.get("_DEFAULT_PORT") == 8765  # changed from 8000 in T-OP-3


def test_default_threads_is_4():
    import ast, pathlib  # noqa: PLC0415,E401
    src = (
        pathlib.Path(__file__).parents[3]
        / "backend" / "api" / "rastatime_api" / "waitress_serve.py"
    )
    tree = ast.parse(src.read_text(encoding="utf-8"))
    defaults = {
        node.targets[0].id: node.value.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and isinstance(node.value, ast.Constant)
    }
    assert defaults.get("_DEFAULT_THREADS") == 4


def test_default_settings_module_is_prod():
    import ast, pathlib  # noqa: PLC0415,E401
    src = (
        pathlib.Path(__file__).parents[3]
        / "backend" / "api" / "rastatime_api" / "waitress_serve.py"
    )
    tree = ast.parse(src.read_text(encoding="utf-8"))
    defaults = {
        node.targets[0].id: node.value.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and isinstance(node.value, ast.Constant)
    }
    assert defaults.get("_DEFAULT_SETTINGS") == "rastatime_api.settings.prod"


# ---------------------------------------------------------------------------
# Django-gated helpers
# ---------------------------------------------------------------------------

try:
    import django as _django_pkg  # noqa: F401
    _HAS_DJANGO = True
except ImportError:
    _HAS_DJANGO = False

_skip_no_django = pytest.mark.skipif(
    not _HAS_DJANGO,
    reason="Django not installed in this environment — skipping rastatime_api tests",
)


# ---------------------------------------------------------------------------
# 9–16  rastatime_api tests — skipped when Django absent
# ---------------------------------------------------------------------------

@_skip_no_django
def test_waitress_serve_module_importable():
    """The ``waitress_serve`` module must be importable from rastatime_api."""
    from rastatime_api import waitress_serve  # noqa: PLC0415,F401
    assert waitress_serve is not None


@_skip_no_django
def test_parse_args_returns_defaults():
    from rastatime_api.waitress_serve import _parse_args, _DEFAULT_HOST, _DEFAULT_PORT, _DEFAULT_THREADS  # noqa: PLC0415
    # Clear any env vars that could influence defaults.
    for var in ("RASTATIME_API_HOST", "RASTATIME_API_PORT", "RASTATIME_API_THREADS"):
        os.environ.pop(var, None)

    args = _parse_args([])
    assert args.host    == _DEFAULT_HOST
    assert args.port    == _DEFAULT_PORT
    assert args.threads == _DEFAULT_THREADS


@_skip_no_django
def test_parse_args_host_flag_overrides_default():
    from rastatime_api.waitress_serve import _parse_args  # noqa: PLC0415
    args = _parse_args(["--host", "0.0.0.0"])
    assert args.host == "0.0.0.0"


@_skip_no_django
def test_parse_args_port_flag_overrides_default():
    from rastatime_api.waitress_serve import _parse_args  # noqa: PLC0415
    args = _parse_args(["--port", "9000"])
    assert args.port == 9000


@_skip_no_django
def test_parse_args_threads_flag_overrides_default():
    from rastatime_api.waitress_serve import _parse_args  # noqa: PLC0415
    args = _parse_args(["--threads", "16"])
    assert args.threads == 16


@_skip_no_django
def test_parse_args_host_env_var(monkeypatch):
    from rastatime_api.waitress_serve import _parse_args  # noqa: PLC0415
    monkeypatch.setenv("RASTATIME_API_HOST", "192.168.1.10")
    args = _parse_args([])
    assert args.host == "192.168.1.10"


@_skip_no_django
def test_parse_args_port_env_var(monkeypatch):
    from rastatime_api.waitress_serve import _parse_args  # noqa: PLC0415
    monkeypatch.setenv("RASTATIME_API_PORT", "8080")
    args = _parse_args([])
    assert args.port == 8080


@_skip_no_django
def test_wsgi_application_is_callable():
    """The Django WSGI application must be a callable (PEP 3333)."""
    # Django is configured once for the whole tree in tests/unit/conftest.py.
    from rastatime_api.wsgi import application  # noqa: PLC0415
    assert callable(application)
