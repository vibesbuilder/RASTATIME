"""
RASTATIME-WORKER — Windows-compatible entry point.

On Linux this module would start a Celery worker.  On Windows, Celery is
not available (T-OP-2 removed it from the requirements), so this entry
point runs a lightweight idle loop that keeps the NSSM service alive and
logs its status.

Invoked as:  python -m libretime_worker
"""

import logging
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("RASTATIME-WORKER: starting (Windows stub mode).")
    logger.info(
        "Celery-based tasks are disabled on Windows.  "
        "Background jobs (podcast downloads, task-manager triggers) "
        "are not active in this deployment."
    )
    logger.info("Worker idle loop running — NSSM will restart on exit.")

    # Heartbeat loop — logs once per minute so NSSM can see the process is alive.
    heartbeat_interval = 60  # seconds
    count = 0
    try:
        while True:
            time.sleep(heartbeat_interval)
            count += 1
            logger.info("RASTATIME-WORKER: heartbeat #%d (uptime %dm)", count, count)
    except (KeyboardInterrupt, SystemExit):
        logger.info("RASTATIME-WORKER: shutdown requested.")
        sys.exit(0)


if __name__ == "__main__":
    main()
