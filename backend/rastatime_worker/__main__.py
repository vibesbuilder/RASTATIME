"""
RASTATIME worker entry point.

Usage:
    python -m rastatime_worker           # from repo root with PYTHONPATH set
    python -m rastatime_worker --help

In dev mode this runs a stub loop that logs "idle" every IDLE_INTERVAL seconds.
A real JobRunner implementation (APScheduler-based) will replace this in Phase 8.
"""

import argparse
import logging
import signal
import sys
import time

from .interface import JobRunner  # noqa: F401 — verifies import is clean

logger = logging.getLogger("rastatime_worker")

IDLE_INTERVAL = 5  # seconds between idle heartbeat log lines


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m rastatime_worker",
        description="RASTATIME background worker (dev stub)",
    )
    parser.add_argument(
        "--idle-interval",
        type=float,
        default=IDLE_INTERVAL,
        metavar="SECONDS",
        help=f"Heartbeat log interval in seconds (default: {IDLE_INTERVAL})",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )

    logger.info("RASTATIME worker starting")
    logger.info("Mode      : dev stub (no real handlers registered)")
    logger.info("Runner    : none (JobRunner ABC not yet instantiated)")
    logger.info("Interface : rastatime_worker.interface.JobRunner loaded OK")
    logger.info("idle")  # V: must appear within 2s of start

    running = True

    def _handle_stop(signum, frame):  # noqa: ANN001
        nonlocal running
        logger.info("Stop signal received (%s), shutting down...", signum)
        running = False

    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)

    interval = args.idle_interval
    next_tick = time.monotonic() + interval

    while running:
        now = time.monotonic()
        sleep_for = max(0.0, next_tick - now)
        time.sleep(min(sleep_for, 0.25))  # wake at most every 250 ms to stay responsive
        if time.monotonic() >= next_tick:
            if running:
                logger.info("idle")
            next_tick += interval

    logger.info("Worker stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
