import logging
from os import getenv

from libretime_shared.config import BaseConfig, GeneralConfig, RabbitMQConfig

# T-GH-2: Celery/kombu removed. Plain config only.
_log = logging.getLogger(__name__)


class Config(BaseConfig):
    general: GeneralConfig
    rabbitmq: RabbitMQConfig = RabbitMQConfig()


LIBRETIME_CONFIG_FILEPATH = getenv("LIBRETIME_CONFIG_FILEPATH")
config = Config(LIBRETIME_CONFIG_FILEPATH)  # type: ignore[arg-type, misc]
