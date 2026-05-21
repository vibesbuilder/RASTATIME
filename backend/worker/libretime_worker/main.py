import logging
import time
from pathlib import Path
from typing import Optional

import click
from libretime_shared.cli import cli_logging_options
from libretime_shared.config import DEFAULT_ENV_PREFIX

# T-GH-2: Celery removed. The worker now runs as a simple idle heartbeat loop.
# Podcast downloads and task triggering are invoked directly via HTTP by the API.

_log = logging.getLogger(__name__)


@click.command(context_settings={"auto_envvar_prefix": DEFAULT_ENV_PREFIX})
@cli_logging_options()
def cli(log_level: str, log_filepath: Optional[Path]):
    """
    Run the RASTATIME worker.

    Note: Celery was removed in T-GH-2. This process runs as a heartbeat stub.
    Background tasks (podcast downloads, task manager) are triggered directly
    by the API server via HTTP instead of via a message queue.
    """
    _log.info(
        "libretime-worker: starting (Celery removed in T-GH-2, heartbeat mode)."
    )
    count = 0
    while True:
        time.sleep(60)
        count += 1
        _log.info("libretime-worker: heartbeat #%d", count)
