from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class PlayoutState(Enum):
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class QueueItem:
    id: str
    uri: str
    title: str = ""
    artist: str = ""
    duration: Optional[float] = None  # seconds; None if unknown
    metadata: dict = field(default_factory=dict)


@dataclass
class TrackChangedEvent:
    previous_item: Optional[QueueItem]
    current_item: Optional[QueueItem]
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass
class PlayoutError:
    code: str
    message: str
    item: Optional[QueueItem] = None
