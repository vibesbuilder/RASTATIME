from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Optional

from .._types import StreamProtocol, StreamState


@dataclass
class StreamSource:
    """Persistent configuration for one incoming remote stream source."""

    id: str
    name: str
    protocol: StreamProtocol
    url: str                      # e.g. "icecast.example.com" or full stream URL
    port: int = 8000
    mount: str = "/"
    username: str = ""
    password: str = ""
    priority: int = 0             # higher value = higher priority when multiple sources active
    enabled: bool = True
    metadata: dict = field(default_factory=dict)


@dataclass
class SourceStatus:
    """Runtime status of one incoming stream source."""

    source_id: str
    state: StreamState
    is_active: bool = False       # True if this source is currently routed to playout
    connected_since: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass
class SourceStateChangedEvent:
    """Fired when a source transitions between StreamStates."""

    source_id: str
    previous_state: StreamState
    current_state: StreamState
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    error_message: Optional[str] = None


class StreamIngressManager(ABC):
    """
    Engine-agnostic contract for managing incoming remote stream sources.

    Concrete implementations: LibVlcIngressManager, IcecastIngressManager.
    Which implementation is used depends on the stream capability matrix
    result (T9.2 / ADR-003).
    """

    # --- Source registration ---

    @abstractmethod
    def register_source(self, source: StreamSource) -> None:
        """Register a new remote stream source. Does not activate it."""

    @abstractmethod
    def unregister_source(self, source_id: str) -> None:
        """Unregister a source. Deactivates it first if currently active."""

    @abstractmethod
    def list_sources(self) -> list[StreamSource]:
        """Return all registered sources regardless of state."""

    # --- Activation ---

    @abstractmethod
    def activate_source(self, source_id: str) -> None:
        """
        Route this source to the playout pipeline.
        Only one source may be active at a time; activating a new source
        deactivates the current one.
        Raises ValueError if source_id is not registered.
        """

    @abstractmethod
    def deactivate_source(self, source_id: str) -> None:
        """
        Stop routing this source to playout and return to scheduled content.
        Raises ValueError if source_id is not registered.
        """

    # --- Status ---

    @abstractmethod
    def get_active_source(self) -> Optional[StreamSource]:
        """Return the currently active source, or None if no live input is active."""

    @abstractmethod
    def get_source_status(self, source_id: str) -> SourceStatus:
        """
        Return the current runtime status for one source.
        Raises ValueError if source_id is not registered.
        """

    # --- Callbacks ---

    @abstractmethod
    def on_source_state_change(
        self, callback: Callable[[SourceStateChangedEvent], None]
    ) -> None:
        """
        Register a callback invoked whenever a source changes state.
        Multiple callbacks may be registered; all are called in order.
        """
