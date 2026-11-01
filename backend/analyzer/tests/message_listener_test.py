"""
RASTATIME 2026-10-14 - the analyzer's RabbitMQ listener: a long import
must not lose the connection (heartbeat), and a redelivered import whose
file was already filed must not be reported as failed.
"""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from rastatime_analyzer import message_listener
from rastatime_analyzer.message_listener import HEARTBEAT_SECONDS, MessageListener


class FakeChannel:
    def __init__(self):
        self.acked = []
        self.nacked = []

    def basic_ack(self, delivery_tag):
        self.acked.append(delivery_tag)

    def basic_nack(self, delivery_tag, multiple, requeue):
        self.nacked.append(delivery_tag)


def _listener() -> MessageListener:
    listener = MessageListener.__new__(MessageListener)  # no connection
    listener.config = SimpleNamespace(
        general=SimpleNamespace(
            internal_base_url=lambda: "http://localhost",
            api_key="key",
        ),
        rabbitmq=SimpleNamespace(host="localhost", port=5672, vhost="/", user="u", password="p"),
    )
    return listener


def _body(path: Path, **options) -> bytes:
    return json.dumps(
        {
            "file_id": 42,
            "tmp_file_path": str(path),
            "import_directory": "imported",
            "original_filename": path.name,
            "options": options,
        }
    ).encode()


def _frame(redelivered: bool):
    return SimpleNamespace(delivery_tag=7, routing_key="", redelivered=redelivered)


def test_redelivered_import_of_a_filed_file_is_acked_without_a_report(tmp_path: Path, monkeypatch):
    def must_not_run(*_args, **_kwargs):
        raise AssertionError("must not run")

    monkeypatch.setattr(MessageListener, "spawn_analyzer_process", must_not_run)
    monkeypatch.setattr(message_listener.StatusReporter, "report_success", must_not_run)
    monkeypatch.setattr(message_listener.StatusReporter, "report_failure", must_not_run)
    channel = FakeChannel()

    _listener().msg_received_callback(
        channel, _frame(redelivered=True), None, _body(tmp_path / "42-gone.wav")
    )

    assert channel.acked == [7]
    assert channel.nacked == []


@pytest.mark.parametrize("redelivered, exists", [(False, False), (True, True)])
def test_other_messages_are_processed(tmp_path: Path, monkeypatch, redelivered, exists):
    path = tmp_path / "42-song.wav"
    if exists:
        path.write_bytes(b"RIFF")
    runs = []
    reports = []
    monkeypatch.setattr(
        MessageListener,
        "spawn_analyzer_process",
        staticmethod(lambda *args: runs.append(args) or {"import_status": 0}),
    )
    monkeypatch.setattr(
        message_listener.StatusReporter,
        "report_success",
        lambda url, key, metadata: reports.append((url, metadata)),
    )
    channel = FakeChannel()

    _listener().msg_received_callback(channel, _frame(redelivered), None, _body(path))

    assert len(runs) == 1
    assert reports == [("http://localhost/rest/media/42", {"import_status": 0})]
    assert channel.acked == [7]


def test_redelivered_loudness_measurement_is_not_skipped(tmp_path: Path, monkeypatch):
    runs = []
    monkeypatch.setattr(
        MessageListener,
        "spawn_analyzer_process",
        staticmethod(lambda *args: runs.append(args) or {}),
    )
    channel = FakeChannel()

    _listener().msg_received_callback(
        channel,
        _frame(redelivered=True),
        None,
        _body(tmp_path / "missing.mp3", loudness_only=True),
    )

    assert len(runs) == 1  # unchanged behaviour: it fails quietly in the pipeline
    assert channel.acked == [7]


def test_connection_asks_for_a_long_heartbeat(monkeypatch):
    seen = {}

    class FakeConnection:
        def __init__(self, parameters):
            seen["heartbeat"] = parameters.heartbeat

        def channel(self):
            return SimpleNamespace(
                exchange_declare=lambda **_kw: None,
                queue_declare=lambda **_kw: None,
                queue_bind=lambda **_kw: None,
                basic_consume=lambda *_a, **_kw: None,
            )

    monkeypatch.setattr(message_listener.pika, "BlockingConnection", FakeConnection)

    _listener().connect_to_messaging_server()

    assert seen["heartbeat"] == HEARTBEAT_SECONDS >= 1800
