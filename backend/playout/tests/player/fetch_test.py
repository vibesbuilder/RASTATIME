from queue import Queue
from unittest.mock import MagicMock

from rastatime_playout.config import Config
from rastatime_playout.player.fetch import PypoFetch


def test_fetch_thread(config: Config):
    PypoFetch(
        Queue(),
        Queue(),
        Queue(),
        MagicMock(),
        MagicMock(),
        config,
        MagicMock(),
        MagicMock(),
    )
