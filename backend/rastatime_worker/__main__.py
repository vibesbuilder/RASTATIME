"""
RASTATIME worker entry point.

Usage:
    python -m rastatime_worker           # from repo root with PYTHONPATH set
    python -m rastatime_worker --help

RASTATIME 2026-11-03 - archiving stage 2: the worker is no placeholder any
more.  It processes the upload jobs to cba.media (``archive_jobs``) every
POLL_INTERVAL seconds and fetches the CBA topic list once a day.  It needs
the API's Django settings (the service sets DJANGO_SETTINGS_MODULE,
RASTATIME_CONFIG_FILEPATH and a PYTHONPATH with backend\\api); without them,
or before migration 0075, it logs why and keeps idling instead of crash-
looping, and tries again every SETUP_RETRY seconds.  Uploads never touch
the playout: stopping this service only pauses them.
"""

import argparse
import logging
import signal
import sys
import time

from .interface import JobRunner  # noqa: F401 — verifies import is clean

logger = logging.getLogger("rastatime_worker")

IDLE_INTERVAL = 600  # seconds between heartbeat log lines
POLL_INTERVAL = 15  # seconds between looks at the job table
SETUP_RETRY = 60  # seconds before trying Django / the tables again


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m rastatime_worker",
        description="RASTATIME background worker (archive uploads to cba.media)",
    )
    parser.add_argument(
        "--idle-interval",
        type=float,
        default=IDLE_INTERVAL,
        metavar="SECONDS",
        help=f"Heartbeat log interval in seconds (default: {IDLE_INTERVAL})",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=POLL_INTERVAL,
        metavar="SECONDS",
        help=f"Seconds between looks at the upload jobs (default: {POLL_INTERVAL})",
    )
    return parser


def _setup_django() -> bool:
    try:
        import django  # noqa: PLC0415

        django.setup()
        return True
    except Exception as exc:  # noqa: BLE001 - logged, retried
        logger.error(
            "Django could not be set up (%s: %s) - archive uploads paused",
            exc.__class__.__name__,
            exc,
        )
        return False


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )

    logger.info("RASTATIME worker starting")
    logger.info("Jobs      : archive uploads to cba.media, CBA topic list")
    logger.info("idle")  # V: must appear within 2s of start

    running = True

    def _handle_stop(signum, frame):  # noqa: ANN001
        nonlocal running
        logger.info("Stop signal received (%s), shutting down...", signum)
        running = False

    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)

    ready = False  # Django set up and the tables of migration 0075 present
    next_setup = time.monotonic()
    next_poll = time.monotonic()
    next_beat = time.monotonic() + args.idle_interval
    done = 0

    while running:
        now = time.monotonic()
        if not ready and now >= next_setup:
            next_setup = now + SETUP_RETRY
            if _setup_django():
                from . import archive_jobs  # noqa: PLC0415

                try:
                    if archive_jobs.tables_ready():
                        ready = True
                        recovered = archive_jobs.recover_interrupted()
                        if recovered:
                            logger.warning(
                                "%d interrupted archive job(s) re-checked after the restart",
                                recovered,
                            )
                        logger.info(
                            "Archive uploads ready (limit %d kbit/s)", archive_jobs.upload_kbit()
                        )
                    else:
                        logger.warning(
                            "Archive tables missing (legacy migration 0075) - uploads paused"
                        )
                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        "Database not reachable (%s) - uploads paused", exc.__class__.__name__
                    )
        if ready and now >= next_poll:
            next_poll = now + args.poll_interval
            from django.db import close_old_connections  # noqa: PLC0415

            from . import archive_jobs  # noqa: PLC0415

            close_old_connections()
            try:
                archive_jobs.refresh_categories()
                while running:
                    state = archive_jobs.run_once()
                    if state is None:
                        break
                    done += 1
            except Exception:  # noqa: BLE001 - e.g. the database restarted
                logger.exception("Archive poll failed - retrying in %s s", args.poll_interval)
                close_old_connections()
        if time.monotonic() >= next_beat:
            next_beat += args.idle_interval
            logger.info("idle (%d archive job(s) processed since start)", done)
        time.sleep(0.25)  # wake at most every 250 ms to stay responsive

    logger.info("Worker stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
