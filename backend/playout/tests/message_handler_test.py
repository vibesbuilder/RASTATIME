from queue import Queue

import pytest

# RASTATIME 2026-10-22: message_handler is the upstream RabbitMQ consumer
# of the pypo entry point (main.py).  RASTATIME-PLAYOUT starts through
# ``python -m libretime_playout`` (__main__.py) and takes schedule and
# source events over its HTTP listener instead, so kombu is neither
# installed on the studio machine nor in setup.py; without this guard
# the whole file errors at collection time.
pytest.importorskip("kombu", reason="kombu is not installed (upstream RabbitMQ path, unused by RASTATIME-PLAYOUT)")

from libretime_playout.config import Config  # noqa: E402
from libretime_playout.message_handler import MessageListener  # noqa: E402


def test_message_listener(config: Config):
    MessageListener(config, Queue())
