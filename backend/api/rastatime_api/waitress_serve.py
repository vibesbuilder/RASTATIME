"""
T17.1 — Waitress production WSGI server entry point.

Replaces the gunicorn/uvicorn-based serving from upstream LibreTime with
`Waitress <https://docs.pylonsproject.org/projects/waitress/>`_ — a
pure-Python, Windows-compatible, zero-C-dependency WSGI server.

Why Waitress
------------
* **Pure Python** — no compiler, no Unix headers; installs on Windows via pip.
* **Stable Windows record** — used in production by Pyramid and other WSGI
  frameworks on Windows Server.
* **WSGI** — the Django WSGI application (``rastatime_api.wsgi``) works
  unchanged; no ASGI required for the current feature set.
* **Thread-per-request model** — configurable thread count; no event loop
  complexity.
* **Single-process** — compatible with NSSM service lifecycle management
  (ADR-005).

Replacement summary
-------------------
Upstream LibreTime used ``gunicorn + UvicornWorker`` (see ``gunicorn.py``).
Both tools are Linux-centric: gunicorn's process-forking model does not work
on Windows and uvicorn's ASGI extras are not needed here.  Waitress provides
identical WSGI semantics with full Windows support.

Usage
-----
**Development** (with debug settings, via run-api.ps1)::

    python -m rastatime_api.waitress_serve --host 127.0.0.1 --port 8000

**Production** (via NSSM-hosted ``serve-api.ps1``)::

    $env:DJANGO_SETTINGS_MODULE = "rastatime_api.settings.prod"
    $env:RASTATIME_CONFIG_FILEPATH = "C:\\rastatime\\config\\rastatime.conf"
    python -m rastatime_api.waitress_serve --host 0.0.0.0 --port 8000 --threads 8

Configuration precedence
------------------------
CLI flag > environment variable > built-in default.

Environment variables
---------------------
``RASTATIME_API_HOST``
    Bind address.  Default: ``127.0.0.1``.
``RASTATIME_API_PORT``
    Bind port.  Default: ``8000``.
``RASTATIME_API_THREADS``
    Number of Waitress worker threads.  Default: ``4``.
``DJANGO_SETTINGS_MODULE``
    Django settings module.  Default: ``rastatime_api.settings.prod``.
``RASTATIME_CONFIG_FILEPATH``
    Path to the LibreTime/RASTATIME config file (required by prod settings).
"""

from __future__ import annotations

import argparse
import logging
import os
import sys


logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Built-in defaults
# ---------------------------------------------------------------------------

_DEFAULT_HOST    = "127.0.0.1"
_DEFAULT_PORT    = 8765
_DEFAULT_THREADS = 4
_DEFAULT_SETTINGS = "rastatime_api.settings.prod"


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """
    Parse command-line arguments.

    Environment variables are read at parse time so that they can be
    overridden by CLI flags.  This mirrors the behaviour of most production
    WSGI servers (uwsgi, gunicorn).

    Parameters
    ----------
    argv:
        Argument list.  ``None`` uses ``sys.argv[1:]``.

    Returns
    -------
    argparse.Namespace
        Parsed arguments with attributes ``host``, ``port``, ``threads``.
    """
    parser = argparse.ArgumentParser(
        prog="python -m rastatime_api.waitress_serve",
        description="RASTATIME API — Waitress production WSGI server (T17.1)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("RASTATIME_API_HOST", _DEFAULT_HOST),
        help="Bind address (env: RASTATIME_API_HOST)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("RASTATIME_API_PORT", _DEFAULT_PORT)),
        help="Bind port (env: RASTATIME_API_PORT)",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=int(os.environ.get("RASTATIME_API_THREADS", _DEFAULT_THREADS)),
        help="Waitress worker threads (env: RASTATIME_API_THREADS)",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Serve entry point
# ---------------------------------------------------------------------------

def serve(
    host: str = _DEFAULT_HOST,
    port: int = _DEFAULT_PORT,
    threads: int = _DEFAULT_THREADS,
) -> None:
    """
    Start the Waitress WSGI server and block until it exits.

    This function never returns under normal operation — it blocks until
    the process receives a termination signal (Ctrl+C in dev; NSSM stop in
    production).

    Django settings and the WSGI application are imported lazily so that:

    * The module is importable in test environments where the full
      application is not yet configured.
    * The ``DJANGO_SETTINGS_MODULE`` environment variable can be set by the
      caller *before* this function is invoked.

    Parameters
    ----------
    host:
        Network interface to bind to.  Use ``127.0.0.1`` (default) to
        serve locally only, or ``0.0.0.0`` to accept connections from
        the local network.
    port:
        TCP port to listen on.
    threads:
        Number of Waitress worker threads.  Each thread handles one
        concurrent request; tune to match expected concurrency.
    """
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", _DEFAULT_SETTINGS)

    # --- configure logging before importing Django ---------------------------
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )

    logger.info(
        "RASTATIME API: starting Waitress on %s:%d with %d thread(s).",
        host, port, threads,
    )
    logger.info(
        "DJANGO_SETTINGS_MODULE = %s",
        os.environ["DJANGO_SETTINGS_MODULE"],
    )
    logger.info("Health endpoint: http://%s:%d/health", host, port)
    logger.info(
        "Swagger UI: http://%s:%d/api/v2/schema/swagger-ui", host, port
    )

    # --- lazy imports -------------------------------------------------------
    import waitress                           # noqa: PLC0415
    from rastatime_api.wsgi import application  # noqa: PLC0415

    waitress.serve(application, host=host, port=port, threads=threads, **PROXY_OPTIONS)


# RASTATIME 2026-10-25 (role audit S3/S4) - the local Apache is the one
# trusted proxy.  Waitress 2+ drops X-Forwarded-For from untrusted peers
# (clear_untrusted_proxy_headers), so every request Apache proxied from
# /api/v2/ looked like a direct call from 127.0.0.1 - internal_only could
# not tell a browser on the internet from the legacy PHP, and the song
# requests saw one IP for every listener.  Trusting 127.0.0.1 for
# X-Forwarded-For only (last hop = the address Apache saw) makes
# REMOTE_ADDR the real client; X-Forwarded-Proto stays untrusted so the
# URLs in API responses do not change.
PROXY_OPTIONS = {
    "trusted_proxy": "127.0.0.1",
    "trusted_proxy_count": 1,
    "trusted_proxy_headers": {"x-forwarded-for"},
    "clear_untrusted_proxy_headers": True,
}


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    """
    Entry point when invoked as ``python -m rastatime_api.waitress_serve``.

    Parses CLI arguments and delegates to :func:`serve`.
    """
    args = _parse_args(argv)
    serve(host=args.host, port=args.port, threads=args.threads)


if __name__ == "__main__":
    main()
