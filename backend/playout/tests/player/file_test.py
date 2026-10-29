from queue import Queue
from unittest.mock import MagicMock

from rastatime_playout.player.file import PypoFile


def test_file_thread():
    PypoFile(
        Queue(),
        MagicMock(),
    )
