from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Optional

from .._types import StreamProtocol, StreamState


@dataclass
class StreamOutput:
    """Persistent configuration for one outgoing stream output."""

    id: str
    name: str
    protocol: StreamProtocol
    url: str                      # e.g. "icecast.example.com"
    port: int = 8000
    mount: str = "/"
    username: str = ""
    password: str = ""
    bitrate: int = 128            # kbps
    codec: str = "mp3"
    enabled: bool = True
    metadata: dict = field(default_factory=dict)


@dataclass
class OutputStatus:
    """Runtime status of one outgoing stream output."""

    output_id: str
    state: StreamState
    listener_count: Optional[int] = None
    connected_since: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass
class OutputStateChangedEvent:
    """Fired when an output transitions between StreamStates."""

    output_id: str
    previous_state: StreamState
    current_state: StreamState
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    error_message: Optional[str] = None


class StreamEgressManager(ABC):
    """
    Engine-agnostic contract for managing outgoing stream outputs.

    In production, outgoing Icecast streaming is owned by Liquidsoap; this
    ABC plus its registry/serialization helpers back the read-only stream
    status API (``/api/v2/streams/outputs``).  The concrete libVLC egress
    manager was removed with the abandoned VLC engine (2026-05-31).
    """

    # --- Output registration ---

    @abstractmethod
    def add_output(self, output: StreamOutput) -> None:
        """Register a new stream output. Does not start streaming."""

    @abstractmethod
    def remove_output(self, output_id: str) -> None:
        """Unregister an output. Stops it first if currently active."""

    @abstractmethod
    def list_outputs(self) -> list[StreamOutput]:
        """Return all registered outputs regardless of state."""

    # --- Lifecycle ---

    @abstractmethod
    def start_output(self, output_id: str) -> None:
        """
        Begin streaming on the given output.
        Raises ValueError if output_id is not registered.
        """

    @abstractmethod
    def stop_output(self, output_id: str) -> None:
        """
        Stop streaming on the given output.
        Raises ValueError if output_id is not registered.
        """

    @abstractmethod
    def start_all(self) -> None:
        """Start all enabled outputs."""

    @abstractmethod
    def stop_all(self) -> None:
        """Stop all active outputs."""

    # --- Status ---

    @abstractmethod
    def get_output_status(self, output_id: str) -> OutputStatus:
        """
        Return the current runtime status for one output.
        Raises ValueError if output_id is not registered.
        """

    # --- Callbacks ---

    @abstractmethod
    def on_output_state_change(
        self, callback: Callable[[OutputStateChangedEvent], None]
    ) -> None:
        """
        Register a callback invoked whenever an output changes state.
        Multiple callbacks may be registered; all are called in order.
        """
