from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, model_validator
from rastatime_shared.config import (
    BaseConfig,
    GeneralConfig,
    RabbitMQConfig,
    StreamConfig,
)

CACHE_DIR = Path.cwd() / "scheduler"
RECORD_DIR = Path.cwd() / "recorder"

PUSH_INTERVAL: float = 2.0
POLL_INTERVAL: float = 400.0


class PlayoutConfig(BaseModel):
    liquidsoap_host: str = "localhost"
    liquidsoap_port: int = 1234

    record_file_format: Literal["mp3", "ogg"] = "ogg"  # record_file_type
    record_bitrate: int = 256
    record_samplerate: int = 44100
    record_channels: int = 2
    record_sample_size: int = 16


class LiquidsoapConfig(BaseModel):
    server_listen_address: str = "127.0.0.1"
    server_listen_port: int = 1234

    harbor_listen_address: list[str] = ["0.0.0.0"]

    harbor_ssl_certificate: Optional[str] = None
    harbor_ssl_private_key: Optional[str] = None
    harbor_ssl_password: Optional[str] = None

    @model_validator(mode="after")
    def _validate_harbor_ssl(self):
        if self.harbor_ssl_certificate is not None and self.harbor_ssl_private_key is None:
            raise ValueError("missing 'harbor_ssl_private_key' value")

        if self.harbor_ssl_certificate is None and self.harbor_ssl_private_key is not None:
            raise ValueError("missing 'harbor_ssl_certificate' value")

        return self


# RASTATIME 2026-05-27 — Seamless-Bus-Mix Phase C4 (DJ-Sources via
# input.harbor).  Pypo-lokales value-object für die Liquidsoap-Harbor-
# Source-Passwörter.  Wird NICHT in die Pydantic-Config eingehängt —
# stattdessen liest ``__main__._read_harbor_credentials()`` die Werte
# direkt aus dem YAML (gleiche Pattern wie ``_read_harbor_inputs``).
#
# Operator setzt in rastatime.conf::
#
#     stream:
#       harbor:
#         main_password: <BUTT/Mixxx source password for /main>
#         show_password: <BUTT/Mixxx source password for /show>
#
# Wenn beide leer / None bleiben, rendert der Liquidsoap-Config-
# Renderer die input.harbor-Blöcke NICHT — der Bus bleibt auf der
# reinen scheduled-source, identisch zum C3-Stand.  So kann der
# Operator stufenweise migrieren.
class HarborInputCredentials(BaseModel):
    """
    Source-Passwörter für die Liquidsoap input.harbor-Mounts.

    Werden aus ``stream.harbor`` in rastatime.conf gelesen.  Beide
    Felder sind optional — wenn None / leer, wird die jeweilige
    Harbor-Mount NICHT in rastatime.liq gerendert.
    """

    main_password: Optional[str] = None
    show_password: Optional[str] = None


class Config(BaseConfig):
    general: GeneralConfig
    rabbitmq: RabbitMQConfig = RabbitMQConfig()
    playout: PlayoutConfig = PlayoutConfig()
    liquidsoap: LiquidsoapConfig = LiquidsoapConfig()
    stream: StreamConfig = StreamConfig()
