from enum import Enum


class StreamProtocol(Enum):
    ICECAST = "icecast"
    SHOUTCAST = "shoutcast"


class StreamState(Enum):
    IDLE = "idle"
    CONNECTING = "connecting"
    ACTIVE = "active"
    DISCONNECTED = "disconnected"
    ERROR = "error"
