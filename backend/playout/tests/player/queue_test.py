from queue import Queue
from unittest.mock import MagicMock

from rastatime_playout.player.queue import PypoLiqQueue


def test_queue_thread():
    PypoLiqQueue(Queue(), MagicMock())
