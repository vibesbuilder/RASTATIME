from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Literal, Optional, Union

from dateutil.parser import isoparse
from pydantic import BaseModel, BeforeValidator, Field, parse_obj_as
from typing_extensions import Annotated

from ..config import CACHE_DIR
from ..utils import mime_guess_extension

EVENT_KEY_FORMAT = "%Y-%m-%d-%H-%M-%S"


# RASTATIME 2026-09-10 - event keys are ``<timestamp>#<tag>``; the tag
# names the event type and the schedule row / show instance it belongs
# to (``file-4711``, ``ws-play-4711``, ``linein-4711``,
# ``record-start-12``, ``kick_out-12``).  Until now a key was the bare
# timestamp plus an insertion-order suffix (``_0``, ``_1``) on
# collisions, so the keys of the survivors moved whenever an event left
# the fetch window (2026-09-04: the same running slot came back as
# ``..._0`` and, a refresh later, as ``...`` - a 9-s hole).  Keys stay
# chronologically sortable: equal-length timestamp before the ``#``.
EVENT_KEY_SEPARATOR = "#"


def event_key_to_datetime(value: Union[str, datetime]) -> datetime:
    if isinstance(value, str):
        # tolerate a ``#tag`` (2026-09-10) or a legacy ``_N`` suffix
        stamp = value.split(EVENT_KEY_SEPARATOR, 1)[0].split("_", 1)[0]
        value = datetime.strptime(stamp, EVENT_KEY_FORMAT)
    return value


def datetime_to_event_key(value: Union[str, datetime]) -> str:
    if isinstance(value, datetime):
        value = value.strftime(EVENT_KEY_FORMAT)
    return value


def make_event_key(value: Union[str, datetime], tag: str) -> str:
    """``<timestamp>#<tag>`` - the key of an event with identity."""
    return f"{datetime_to_event_key(value)}{EVENT_KEY_SEPARATOR}{tag}"


def event_isoparse(value: str) -> datetime:
    return isoparse(value).replace(tzinfo=None).replace(microsecond=0)


class EventKind(str, Enum):
    FILE = "file"
    ACTION = "event"
    WEB_STREAM_BUFFER_START = "stream_buffer_start"
    WEB_STREAM_OUTPUT_START = "stream_output_start"
    WEB_STREAM_BUFFER_END = "stream_buffer_end"
    WEB_STREAM_OUTPUT_END = "stream_output_end"
    # RASTATIME 2026-05-12 — Phase B: Line-In as a scheduled audio source.
    # A LINEIN_START fires at the scheduled slot start; the scheduler is
    # also responsible for stopping the capture at end (no dedicated
    # *_END event needed since teardown is symmetric with FileEvent).
    LINEIN_START = "linein_start"
    # RASTATIME 2026-05-17 — Phase B: Record-per-Show feature
    # (ARCHITECTURE Section 23.13).  SHOW_RECORD_START fires at the
    # show's scheduled start when cc_show.record = true; the matching
    # SHOW_RECORD_END fires at the show's scheduled end.  Independent
    # from FILE / WEB_STREAM / LINEIN / Master-Show source events —
    # the recorder reads the active Icecast output mountpoint, which
    # naturally captures whichever source happens to be on air at
    # any given moment during the show.
    SHOW_RECORD_START = "show_record_start"
    SHOW_RECORD_END = "show_record_end"


EventKeyDatetime = Annotated[datetime, BeforeValidator(event_key_to_datetime)]


class BaseEvent(BaseModel):
    start: EventKeyDatetime
    end: EventKeyDatetime

    @property
    def start_key(self) -> str:
        return datetime_to_event_key(self.start)

    @property
    def end_key(self) -> str:
        return datetime_to_event_key(self.end)

    def ended(self) -> bool:
        return datetime.utcnow() > self.end


class FileEvent(BaseEvent):
    type: Literal[EventKind.FILE]

    # Schedule
    row_id: int
    uri: Optional[str] = None
    id: int

    # Show data
    show_name: str

    # File
    fade_in: float
    fade_out: float
    cue_in: float
    cue_out: float

    track_title: Optional[str] = None
    artist_name: Optional[str] = None

    mime: str
    replay_gain: Optional[float] = None
    filesize: int

    # RASTATIME 2026-09-27 - crossfade shape decisions: the show instance
    # (a change of instance between two tracks = a show boundary) and the
    # track's "No Fade during Crossover" flag (the track keeps its level
    # while the other one fades).  Optional so older fixtures and cached
    # schedules still parse.
    instance_id: Optional[int] = None
    no_fade_crossfade: bool = False
    # RASTATIME 2026-09-29 - crossfade per track type + "Exclude from
    # Crossover": the type's overlap in seconds (None = house value) and
    # the per-track exception (never overlaps a neighbour).
    crossfade_seconds: Optional[float] = None
    exclude_crossfade: bool = False

    file_ready: bool = False

    @property
    def file_ext(self) -> str:
        return mime_guess_extension(self.mime)

    @property
    def local_filepath(self) -> Path:
        return CACHE_DIR / f"{self.id}{self.file_ext}"


class WebStreamEvent(BaseEvent):
    type: Literal[
        EventKind.WEB_STREAM_BUFFER_START,
        EventKind.WEB_STREAM_OUTPUT_START,
        EventKind.WEB_STREAM_BUFFER_END,
        EventKind.WEB_STREAM_OUTPUT_END,
    ]

    # Schedule
    row_id: int
    uri: str
    id: int

    # Show data
    show_name: str

    # RASTATIME 2026-05-16 - per-webstream static input gain (dB).
    # Sourced from cc_webstream.input_gain_db via the REST API.  The
    # playout scheduler forwards this to the engine's webstream_start
    # `gain_db`, which Liquidsoap applies as a linear amplify factor.
    # None or 0 = unity gain (default upstream behaviour).
    input_gain_db: Optional[float] = None


class LineinEvent(BaseEvent):
    """
    A scheduled Line-In Library item.

    Created from a ``cc_schedule`` row whose ``linein_id`` is non-NULL.
    Carries the device's stable ID (a Windows audio endpoint GUID, e.g.
    ``"0fb30b0b-c875-432b-a48f-dbb5208995c9"``) so the playout can wire
    FFmpeg's ``-f dshow -i audio="@device_cm_{...}\\wave_{<GUID>}"``
    capture from the right microphone without any extra lookup.

    Phase B fields are deliberately minimal — the device GUID and a
    display name are all the playout side needs to start a capture.
    """

    type: Literal[EventKind.LINEIN_START]

    # Schedule
    row_id: int
    id: int  # rastatime_linein.id (DB pk)

    # Show data
    show_name: str

    # Line-In specifics
    device_id: str
    """
    Stable ID of the Windows audio input endpoint (normalised GUID
    without braces).  Combined into FFmpeg's dshow alternative-name
    syntax at capture time.
    """

    name: str
    """Operator-given label, e.g. ``"Studio Mic Left"``."""

    device_name: str = ""
    """
    RASTATIME 2026-05-14 — B.4 #4 UUID-Wechsel nach Reboot.

    OS-reported friendly name of the audio input endpoint at save time
    (e.g. ``"Mikrofon (Jabra Speak 410 USB)"``).  Used as a fallback in
    :meth:`PlayoutScheduler._resolve_linein_device` when the saved
    ``device_id`` (USB endpoint GUID) no longer resolves to an active
    device — a known Windows USB-audio quirk where the WASAPI GUID can
    shift after reboots or driver / port re-enumerations.  Empty
    string for legacy rows without a stored name; the resolver then
    behaves as before (no fallback, preflight warns).
    """

    channel_mapping: List[int] = [0, 1]
    """
    RASTATIME 2026-08-31 — BACKLOG "Line-In: Kanal-Auswahl auf
    Multi-Input-Devices".

    0-based input channels to capture from the device (from
    ``rastatime_linein.channel_mapping``): ``[0, 1]`` = plain stereo
    (default, proven dshow path); any other pair or a single channel
    routes through the sounddevice/MME feeder so multichannel
    interfaces (e.g. the 16-input Tascam US-16x08) can serve one
    studio per input pair.
    """


class ActionEventKind(str, Enum):
    SWITCH_OFF = "switch_off"
    KICK_OUT = "kick_out"


class ActionEvent(BaseEvent):
    type: Literal[EventKind.ACTION]
    # TODO: user ActionEventKind enum
    event_type: str


class ShowRecordEvent(BaseEvent):
    """
    RASTATIME 2026-05-17 — Phase B: Record-per-Show.

    Emitted by the schedule builder once per show-instance for shows
    where ``cc_show.record == true``: one SHOW_RECORD_START at
    ``show.starts_at`` and one matching SHOW_RECORD_END at
    ``show.ends_at``.

    Independent from FILE / WEB_STREAM / LINEIN / Master-Show source
    events; the recorder reads the active Icecast output mountpoint,
    which naturally captures whichever source happens to be on air at
    any given moment during the show.

    Carries the metadata the recorder needs to build the output
    filename:
      * ``show_id``     — used to keep separate-show concurrent recordings apart
      * ``show_name``   — used in the filename (sanitized of NTFS-illegal
                          chars but spaces/Umlauts retained)
      * ``starts_at``   — used to build the YYYY-MM-DD HH-MM filename prefix
                          (re-derived from ``start`` for SHOW_RECORD_END so
                          stop() finds the right recorder by show_id)
    """

    type: Literal[
        EventKind.SHOW_RECORD_START,
        EventKind.SHOW_RECORD_END,
    ]

    show_id: int
    show_name: str
    show_starts_at: EventKeyDatetime


AnyEvent = Annotated[
    Union[
        FileEvent,
        WebStreamEvent,
        LineinEvent,
        ActionEvent,
        ShowRecordEvent,
    ],
    Field(discriminator="type"),
]


def parse_any_event(value: dict) -> AnyEvent:
    return parse_obj_as(AnyEvent, value)  # type: ignore


FileEvents = Dict[str, FileEvent]
Events = Dict[str, AnyEvent]
