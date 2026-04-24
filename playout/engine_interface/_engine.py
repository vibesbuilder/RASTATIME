from abc import ABC, abstractmethod
from typing import Callable, Optional

from ._types import PlayoutError, PlayoutState, QueueItem, TrackChangedEvent


class PlayoutEngine(ABC):
    """
    Engine-agnostic contract for all RASTATIME playout adapters.

    Concrete implementations: LibVlcPlayoutEngine, MockPlayoutEngine.
    All playout actions in the system must go through this interface.
    """

    # --- Transport controls ---

    @abstractmethod
    def start(self) -> None:
        """Start playback of the current queue from the beginning."""

    @abstractmethod
    def stop(self) -> None:
        """Stop playback. Position is reset; queue is preserved."""

    @abstractmethod
    def pause(self) -> None:
        """Pause playback at the current position."""

    @abstractmethod
    def resume(self) -> None:
        """Resume playback from the paused position."""

    # --- Queue management ---

    @abstractmethod
    def load_queue(self, items: list[QueueItem]) -> None:
        """
        Replace the current queue with items.
        Does not start playback automatically.
        """

    @abstractmethod
    def append(self, item: QueueItem) -> None:
        """Append a single item to the end of the queue."""

    @abstractmethod
    def clear_queue(self) -> None:
        """
        Remove all pending items from the queue.
        Does not stop the currently playing item.
        """

    # --- State queries ---

    @abstractmethod
    def get_state(self) -> PlayoutState:
        """Return the current engine state."""

    @abstractmethod
    def get_current_item(self) -> Optional[QueueItem]:
        """Return the item currently being played, or None if stopped."""

    @abstractmethod
    def get_remaining_duration(self) -> Optional[float]:
        """
        Return seconds remaining in the current item.
        Returns None if unknown or not playing.
        """

    # --- Callbacks ---

    @abstractmethod
    def on_track_change(
        self, callback: Callable[[TrackChangedEvent], None]
    ) -> None:
        """
        Register a callback invoked when the current track changes.
        Multiple callbacks may be registered; all are called in order.
        """

    @abstractmethod
    def on_error(self, callback: Callable[[PlayoutError], None]) -> None:
        """
        Register a callback invoked on a playout error.
        Multiple callbacks may be registered; all are called in order.
        """

    # --- Device selection ---

    @abstractmethod
    def select_output_device(self, device_id: str) -> None:
        """
        Select the audio output device by its stable internal ID.
        device_id comes from the AudioDeviceManager (T12.1).
        """
