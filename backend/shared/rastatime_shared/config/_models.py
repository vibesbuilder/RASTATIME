import os
import sys
from enum import Enum
from typing import Annotated, Literal, Optional, Union
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator

from ._fields import AnyHttpUrlStr, AnyUrlStr, StrNoLeadingSlash, StrNoTrailingSlash

# GeneralConfig
########################################################################################


# pylint: disable=too-few-public-methods
class GeneralConfig(BaseModel):
    public_url: AnyHttpUrlStr
    api_key: str
    secret_key: str

    # RASTATIME 2026-10-04 (go-live stage 1): the address the backend
    # services use to call the legacy web application on THIS machine
    # (analyzer import callback, playout v1 client, DJ login check).
    # ``public_url`` is the outside face (https://...); it may not even
    # resolve back to this host from inside the LAN.  Optional - see
    # :meth:`internal_base_url` for the fallback chain.
    internal_url: Optional[AnyHttpUrlStr] = None

    timezone: str = "UTC"

    allowed_cors_origins: list[AnyHttpUrlStr] = []

    def internal_base_url(self) -> str:
        """Base URL for calls to the legacy web app from this machine,
        without a trailing slash: ``RASTATIME_INTERNAL_URL`` (environment)
        > ``general.internal_url`` > ``http://127.0.0.1`` plus the path of
        ``public_url`` (an installation under a sub-path keeps it)."""
        override = os.environ.get("RASTATIME_INTERNAL_URL", "").strip()
        if override:
            return override.rstrip("/")
        if self.internal_url:
            return str(self.internal_url).rstrip("/")
        path = (getattr(self.public_url, "path", "") or "").rstrip("/")
        return "http://127.0.0.1" + path

    @field_validator("timezone")
    @classmethod
    def _validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exception:
            raise ValueError(f"invalid timezone '{value}'") from exception

        return value


# StorageConfig
########################################################################################


# pylint: disable=too-few-public-methods
class StorageConfig(BaseModel):
    # Windows-appropriate default; upstream Linux default kept for non-Windows envs.
    path: StrNoTrailingSlash = (
        r"C:\rastatime\media" if sys.platform == "win32" else "/srv/libretime"
    )


# DatabaseConfig
########################################################################################


# pylint: disable=too-few-public-methods
class DatabaseConfig(BaseModel):
    host: str = "localhost"
    port: int = 5432
    name: str = "rastatime"
    user: str = "rastatime"
    password: str = "rastatime"

    @property
    def url(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


# RabbitMQConfig
########################################################################################


# pylint: disable=too-few-public-methods
class RabbitMQConfig(BaseModel):
    host: str = "localhost"
    port: int = 5672
    user: str = "rastatime"
    password: str = "rastatime"
    vhost: str = "/rastatime"

    @property
    def url(self) -> str:
        return f"amqp://{self.user}:{self.password}@{self.host}:{self.port}/{self.vhost}"


# StreamConfig
########################################################################################


class BaseInput(BaseModel):
    enabled: bool = True
    public_url: Optional[AnyUrlStr] = None


class InputKind(str, Enum):
    HARBOR = "harbor"


class HarborInput(BaseInput):
    kind: Literal[InputKind.HARBOR] = InputKind.HARBOR
    mount: StrNoLeadingSlash
    port: int
    secure: bool = False


class MainHarborInput(HarborInput):
    mount: str = "main"
    port: int = 8001


class ShowHarborInput(HarborInput):
    mount: str = "show"
    port: int = 8002


class Inputs(BaseModel):
    main: HarborInput = MainHarborInput()
    show: HarborInput = ShowHarborInput()


class AudioChannels(str, Enum):
    STEREO = "stereo"
    MONO = "mono"


class BaseAudio(BaseModel):
    channels: AudioChannels = AudioChannels.STEREO
    bitrate: int

    @field_validator("bitrate")
    @classmethod
    def _validate_bitrate(cls, value: int) -> int:
        # Once the liquidsoap script generation supports it, fine tune
        # the bitrate validation for each format
        bitrates = (32, 48, 64, 96, 128, 160, 192, 224, 256, 320)
        if value not in bitrates:
            raise ValueError(f"invalid bitrate {value}, must be one of {bitrates}")
        return value


class AudioFormat(str, Enum):
    AAC = "aac"
    MP3 = "mp3"
    OGG = "ogg"
    OPUS = "opus"


class AudioAAC(BaseAudio):
    format: Literal[AudioFormat.AAC] = AudioFormat.AAC


class AudioMP3(BaseAudio):
    format: Literal[AudioFormat.MP3] = AudioFormat.MP3


class AudioOGG(BaseAudio):
    format: Literal[AudioFormat.OGG] = AudioFormat.OGG
    enable_metadata: Optional[bool] = False


class AudioOpus(BaseAudio):
    format: Literal[AudioFormat.OPUS] = AudioFormat.OPUS


class IcecastOutput(BaseModel):
    kind: Literal["icecast"] = "icecast"
    enabled: bool = False
    public_url: Optional[AnyUrlStr] = None

    host: str = "localhost"
    port: int = 8000
    mount: StrNoLeadingSlash
    source_user: str = "source"
    source_password: str
    admin_user: str = "admin"
    admin_password: Optional[str] = None

    audio: Annotated[
        Union[AudioAAC, AudioMP3, AudioOGG, AudioOpus],
        Field(discriminator="format"),
    ]

    name: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    genre: Optional[str] = None

    mobile: bool = False


class ShoutcastOutput(BaseModel):
    kind: Literal["shoutcast"] = "shoutcast"
    enabled: bool = False
    public_url: Optional[AnyUrlStr] = None

    host: str = "localhost"
    port: int = 8000
    source_user: str = "source"
    source_password: str
    admin_user: str = "admin"
    admin_password: Optional[str] = None

    audio: Annotated[
        Union[AudioAAC, AudioMP3],
        Field(discriminator="format"),
    ]

    name: Optional[str] = None
    website: Optional[str] = None
    genre: Optional[str] = None

    mobile: bool = False


# T-GH-4: Linux audio backends (ALSA, AO, OSS, PortAudio, PulseAudio) removed.
# RASTATIME runs on Windows only; WASAPI is the sole system output backend.
class SystemOutput(str, Enum):
    WASAPI = "wasapi"


class BaseSystemOutput(BaseModel):
    enabled: bool = False


class WASAPISystemOutput(BaseSystemOutput):
    kind: Literal[SystemOutput.WASAPI] = SystemOutput.WASAPI
    # Optional: pin to a specific Windows audio endpoint by stable_id.
    # Leave None to use the OS default output device.
    device: Optional[str] = None


# Type alias kept for call-site compatibility; only one backend remains.
AnySystemOutput = WASAPISystemOutput


# pylint: disable=too-few-public-methods
class Outputs(BaseModel):
    icecast: list[IcecastOutput] = Field([], max_length=3)
    shoutcast: list[ShoutcastOutput] = Field([], max_length=1)
    system: list[AnySystemOutput] = Field([], max_length=1)

    @property
    def merged(self) -> list[Union[IcecastOutput, ShoutcastOutput]]:
        return self.icecast + self.shoutcast


# pylint: disable=too-few-public-methods
class StreamConfig(BaseModel):
    """Stream configuration model."""

    inputs: Inputs = Inputs()
    outputs: Outputs = Outputs()  # type: ignore[call-arg]
