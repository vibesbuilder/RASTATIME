import logging
from os import getenv

# RASTATIME: kombu and the config file are not available on Windows.
# Guard all Celery/RabbitMQ dependencies so this module is safe to import.
# Set RASTATIME_WORKER_AVAILABLE to check availability before calling worker code.
_log = logging.getLogger(__name__)

try:
    from kombu import Exchange, Queue
    from libretime_shared.config import BaseConfig, GeneralConfig, RabbitMQConfig

    class Config(BaseConfig):
        general: GeneralConfig
        rabbitmq: RabbitMQConfig = RabbitMQConfig()

    LIBRETIME_CONFIG_FILEPATH = getenv("LIBRETIME_CONFIG_FILEPATH")
    config = Config(LIBRETIME_CONFIG_FILEPATH)  # type: ignore[arg-type, misc]

    # Celery amqp settings
    BROKER_URL = config.rabbitmq.url
    CELERY_RESULT_BACKEND = "amqp"  # Use RabbitMQ as the celery backend
    CELERY_RESULT_PERSISTENT = True  # Persist through a broker restart
    CELERY_TASK_RESULT_EXPIRES = 900  # Expire task results after 15 minutes
    CELERY_RESULT_EXCHANGE = "celeryresults"  # Default exchange - needed due to php-celery
    CELERY_QUEUES = (
        Queue("celery", exchange=Exchange("celery"), routing_key="celery"),
        Queue("podcast", exchange=Exchange("podcast"), routing_key="podcast"),
        Queue(exchange=Exchange("celeryresults"), auto_delete=True),
    )
    CELERY_EVENT_QUEUE_EXPIRES = 900  # RabbitMQ x-expire after 15 minutes

    # Celery task settings
    CELERY_TASK_SERIALIZER = "json"
    CELERY_RESULT_SERIALIZER = "json"
    CELERY_ACCEPT_CONTENT = ["json"]
    CELERY_TIMEZONE = config.general.timezone

    RASTATIME_WORKER_AVAILABLE = True

except (ImportError, Exception) as _e:
    RASTATIME_WORKER_AVAILABLE = False
    config = None  # type: ignore[assignment]
    Exchange = Queue = None  # type: ignore[assignment, misc]
    BROKER_URL = None
    CELERY_RESULT_BACKEND = None
    CELERY_RESULT_PERSISTENT = None
    CELERY_TASK_RESULT_EXPIRES = None
    CELERY_RESULT_EXCHANGE = None
    CELERY_QUEUES = ()
    CELERY_EVENT_QUEUE_EXPIRES = None
    CELERY_TASK_SERIALIZER = "json"
    CELERY_RESULT_SERIALIZER = "json"
    CELERY_ACCEPT_CONTENT = ["json"]
    CELERY_TIMEZONE = "UTC"
    _log.warning(
        "libretime_worker: Celery/RabbitMQ dependencies not available (%s). "
        "Worker is disabled (RASTATIME Windows mode).",
        _e,
    )
