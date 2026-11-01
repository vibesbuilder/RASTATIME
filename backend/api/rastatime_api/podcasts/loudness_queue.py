"""
RASTATIME 2026-10-24 - queue the analyzer's loudness measurement for a
podcast episode the API downloaded itself.

``download_episode`` writes the file and the ``cc_files`` row without the
analyzer, so the episode had no EBU R128 values and the playout fell back
to an approximation (``file_gain_db``: ReplayGain shifted to the target,
and podcast rows carry no ReplayGain either).  This publishes the same
``loudness_only`` message the Settings button "Measure loudness" sends
(``Application_Model_RabbitMq::SendLoudnessMeasurementToAnalyzer``); the
analyzer measures the file and writes the three loudness keys back through
``/rest/media/<id>``.

A failure is logged and reported, never raised: the download itself has
succeeded by then and the operator can still press "Measure loudness".
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

EXCHANGE = "airtime-uploads"
EXCHANGE_TYPE = "topic"
CONNECT_TIMEOUT_SECONDS = 5.0


def loudness_message(file_id: int, absolute_path: str) -> dict:
    """The analyzer's message shape (message_listener.msg_received_callback)."""
    return {
        "file_id": int(file_id),
        "tmp_file_path": str(absolute_path),
        "import_directory": "",
        "original_filename": Path(absolute_path).name,
        "options": {"loudness_only": True},
    }


def queue_loudness_measurement(file_id: int, absolute_path: str) -> bool:
    """Publish the loudness-only job; True when the broker accepted it."""
    # pylint: disable=import-outside-toplevel
    try:
        import pika
        from django.conf import settings

        rabbit = settings.CONFIG.rabbitmq
        params = pika.ConnectionParameters(
            host=rabbit.host,
            port=rabbit.port,
            virtual_host=rabbit.vhost,
            credentials=pika.PlainCredentials(rabbit.user, rabbit.password),
            socket_timeout=CONNECT_TIMEOUT_SECONDS,
            blocked_connection_timeout=CONNECT_TIMEOUT_SECONDS,
        )
        connection = pika.BlockingConnection(params)
        try:
            channel = connection.channel()
            channel.exchange_declare(exchange=EXCHANGE, exchange_type=EXCHANGE_TYPE, durable=True)
            channel.basic_publish(
                exchange=EXCHANGE,
                routing_key="",
                body=json.dumps(loudness_message(file_id, absolute_path)),
                properties=pika.BasicProperties(content_type="text/plain", delivery_mode=2),
            )
        finally:
            connection.close()
        logger.info("podcast file %d: loudness measurement queued", file_id)
        return True
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning(
            "podcast file %d: loudness measurement not queued (%s) - "
            "use Settings -> Streams -> Measure loudness",
            file_id,
            exc,
        )
        return False
