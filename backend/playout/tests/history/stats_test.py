from datetime import datetime
from typing import List
from unittest.mock import Mock, call

import pytest
from rastatime_shared.config import IcecastOutput, ShoutcastOutput
from lxml.etree import XMLSyntaxError
from requests.exceptions import HTTPError

from rastatime_playout.history.stats import AnyOutput, Stats, StatsCollector

from ..fixtures import icecast_stats, shoutcast_admin


@pytest.fixture(name="outputs")
def outputs_fixture():
    default_output = {
        "enabled": True,
        "mount": "main.ogg",
        "source_password": "hackme",
        "admin_password": "hackme",
        "audio": {"format": "ogg", "bitrate": 256},
    }
    return [
        IcecastOutput(**default_output),
        IcecastOutput(
            **{
                **default_output,
                "mount": "main.mp3",
                "audio": {"format": "mp3", "bitrate": 256},
            }
        ),
    ]


def test_stats_collector_collect_server_stats(
    requests_mock,
    outputs: List[AnyOutput],
):
    requests_mock.get(
        "http://localhost:8000/admin/stats.xml",
        content=icecast_stats.read_bytes(),
    )

    legacy_client = Mock()

    collector = StatsCollector(legacy_client)
    result = collector.collect_output_stats(outputs[0])
    assert result == {
        "main.ogg": Stats(listeners=2),
        "main.mp3": Stats(listeners=3),
    }

    legacy_client.assert_not_called()


def test_stats_collector_collect_server_stats_unauthorized(
    requests_mock,
    outputs: List[AnyOutput],
):
    requests_mock.get(
        "http://localhost:8000/admin/stats.xml",
        status_code=401,
    )

    legacy_client = Mock()

    collector = StatsCollector(legacy_client)
    with pytest.raises(HTTPError):
        collector.collect_output_stats(outputs[0])


def test_stats_collector_collect_server_stats_invalid_xml(
    requests_mock,
    outputs: List[AnyOutput],
):
    requests_mock.get(
        "http://localhost:8000/admin/stats.xml",
        content=b"""<?xml version="1.0"?><icestats><host>localhost</icestats>""",
    )

    legacy_client = Mock()

    collector = StatsCollector(legacy_client)
    with pytest.raises(XMLSyntaxError):
        collector.collect_output_stats(outputs[0])


def test_stats_collector_collect(
    requests_mock,
    outputs: List[AnyOutput],
):
    requests_mock.get(
        "http://localhost:8000/admin/stats.xml",
        content=icecast_stats.read_bytes(),
    )
    requests_mock.get(
        "http://shoutcast.com:8000/admin.cgi?sid=1&mode=viewxml",
        content=shoutcast_admin.read_bytes(),
    )

    legacy_client = Mock()
    default_output = {
        "source_password": "hackme",
        "admin_password": "hackme",
    }
    outputs.extend(
        [
            IcecastOutput(
                **{
                    **default_output,
                    "enabled": False,
                    "host": "example.com",
                    "mount": "disabled.ogg",
                    "audio": {"format": "ogg", "bitrate": 256},
                }
            ),
            ShoutcastOutput(
                **{
                    **default_output,
                    "enabled": True,
                    "kind": "shoutcast",
                    "host": "shoutcast.com",
                    "audio": {"format": "mp3", "bitrate": 256},
                }
            ),
        ]
    )

    collector = StatsCollector(legacy_client)
    collector.collect(outputs, _timestamp=datetime(2022, 8, 9, 11, 19, 7))

    legacy_client.assert_has_calls(
        [
            call.push_stream_stats(
                [
                    {
                        "timestamp": "2022-08-09 11:19:07",
                        "num_listeners": 2,
                        "mount_name": "main.ogg",
                    },
                    {
                        "timestamp": "2022-08-09 11:19:07",
                        "num_listeners": 3,
                        "mount_name": "main.mp3",
                    },
                    {
                        "timestamp": "2022-08-09 11:19:07",
                        "num_listeners": 1,
                        "mount_name": "shoutcast",
                    },
                ]
            )
        ]
    )


# ---- RASTATIME: outputs_from_stream_settings (cc_pref adapter) ----------


def test_outputs_from_stream_settings_maps_fields():
    from rastatime_playout.history.stats import outputs_from_stream_settings

    outputs = outputs_from_stream_settings([
        {
            "enable": "true", "output": "icecast", "host": "127.0.0.1",
            "port": "8000", "mount": "/rastatime", "user": "source",
            "pass": "sourcepw", "admin_user": "admin", "admin_pass": "adminpw",
            "type": "mp3", "bitrate": "320",
        }
    ])
    assert len(outputs) == 1
    out = outputs[0]
    assert out.kind == "icecast"
    assert out.enabled is True
    assert out.host == "127.0.0.1"
    assert out.port == 8000
    assert out.mount == "rastatime"  # leading slash stripped
    assert out.admin_user == "admin"
    assert out.admin_password == "adminpw"


def test_outputs_from_stream_settings_skips_missing_admin_pass():
    from rastatime_playout.history.stats import outputs_from_stream_settings

    outputs = outputs_from_stream_settings([
        {"mount": "/no-admin", "host": "127.0.0.1", "port": "8000"},
        {"mount": "/ok", "host": "127.0.0.1", "port": "8000",
         "admin_pass": "pw"},
    ])
    assert [o.mount for o in outputs] == ["ok"]


def test_outputs_from_stream_settings_skips_empty_mount_and_bad_port():
    from rastatime_playout.history.stats import outputs_from_stream_settings

    outputs = outputs_from_stream_settings([
        {"mount": "", "admin_pass": "pw"},
        {"mount": "/weird-port", "port": "notanint", "admin_pass": "pw"},
    ])
    assert len(outputs) == 1
    assert outputs[0].mount == "weird-port"
    assert outputs[0].port == 8000  # fallback


def test_stats_collector_accepts_mounted_output(requests_mock):
    """The duck-typed cc_pref adapter drives a full collect() round."""
    from rastatime_playout.history.stats import (
        StatsCollector,
        outputs_from_stream_settings,
    )

    outputs = outputs_from_stream_settings([
        {
            "enable": "true", "host": "127.0.0.1", "port": "8000",
            "mount": "/main.ogg", "admin_user": "admin",
            "admin_pass": "hackme", "type": "mp3",
        }
    ])
    requests_mock.get(
        "http://127.0.0.1:8000/admin/stats.xml",
        content=icecast_stats.read_bytes(),
    )

    legacy_client = Mock()
    collector = StatsCollector(legacy_client)
    collector.collect(outputs, _timestamp=datetime(2022, 8, 22, 20, 30))

    assert legacy_client.push_stream_stats.call_count == 1
    pushed = legacy_client.push_stream_stats.call_args[0][0]
    assert pushed[0]["mount_name"] == "main.ogg"


# ---- RASTATIME 2026-10-26: collection status per stream -----------------


def _status_calls(legacy_client):
    return [c.args[0] for c in legacy_client.update_stream_setting_table.call_args_list]


def _mounted(stream_id=None):
    from rastatime_playout.history.stats import outputs_from_stream_settings

    entry = {
        "host": "127.0.0.1", "port": "8000", "mount": "/main.ogg",
        "admin_user": "admin", "admin_pass": "hackme",
    }
    if stream_id is not None:
        entry["stream_id"] = stream_id
    return outputs_from_stream_settings([entry])


STATS_URL = "http://127.0.0.1:8000/admin/stats.xml"


def test_status_ok_is_reported_once(requests_mock):
    requests_mock.get(STATS_URL, content=icecast_stats.read_bytes())
    legacy_client = Mock()
    collector = StatsCollector(legacy_client)
    outputs = _mounted(stream_id=1)

    collector.collect(outputs, _timestamp=datetime(2026, 10, 26, 12, 0))
    collector.collect(outputs, _timestamp=datetime(2026, 10, 26, 12, 2))

    assert _status_calls(legacy_client) == [{1: "OK"}]
    assert legacy_client.push_stream_stats.call_count == 2


def test_status_auth_error_then_recovery(requests_mock):
    """The 2026-10-24 case: 401 during a password change, then fine again."""
    legacy_client = Mock()
    collector = StatsCollector(legacy_client)
    outputs = _mounted(stream_id=3)

    requests_mock.get(STATS_URL, status_code=401, reason="Authentication Required")
    collector.collect(outputs, _timestamp=datetime(2026, 10, 24, 10, 20, 53))
    collector.collect(outputs, _timestamp=datetime(2026, 10, 24, 10, 22, 53))
    requests_mock.get(STATS_URL, content=icecast_stats.read_bytes())
    collector.collect(outputs, _timestamp=datetime(2026, 10, 24, 10, 24, 53))

    calls = _status_calls(legacy_client)
    assert len(calls) == 2  # the error once, then the recovery
    kind, when, detail = calls[0][3].split("|", 2)
    assert (kind, when) == ("auth", "2026-10-24 10:20:53")
    assert "401" in detail
    assert calls[1] == {3: "OK"}


@pytest.mark.parametrize(
    "mock_kwargs, kind",
    [
        ({"exc": __import__("requests").exceptions.ConnectionError("refused")}, "unreachable"),
        ({"exc": __import__("requests").exceptions.ConnectTimeout("slow")}, "timeout"),
        ({"status_code": 500}, "http"),
        ({"content": b"<icestats><broken></icestats>"}, "invalid"),
    ],
)
def test_status_kinds(requests_mock, mock_kwargs, kind):
    requests_mock.get(STATS_URL, **mock_kwargs)
    legacy_client = Mock()
    StatsCollector(legacy_client).collect(
        _mounted(stream_id=2), _timestamp=datetime(2026, 10, 26, 12, 0)
    )
    (call_data,) = _status_calls(legacy_client)
    assert call_data[2].startswith(kind + "|2026-10-26 12:00:00|")


def test_status_retried_when_report_failed(requests_mock):
    """The v1 wrapper returns None on a failed request: report again."""
    requests_mock.get(STATS_URL, content=icecast_stats.read_bytes())
    legacy_client = Mock()
    legacy_client.update_stream_setting_table.side_effect = [None, Mock()]
    collector = StatsCollector(legacy_client)
    outputs = _mounted(stream_id=1)

    collector.collect(outputs, _timestamp=datetime(2026, 10, 26, 12, 0))
    collector.collect(outputs, _timestamp=datetime(2026, 10, 26, 12, 2))
    collector.collect(outputs, _timestamp=datetime(2026, 10, 26, 12, 4))

    assert _status_calls(legacy_client) == [{1: "OK"}, {1: "OK"}]


def test_status_uses_stream_number_not_position(requests_mock):
    """Stream 1 off, stream 3 on: the status belongs to stream 3."""
    requests_mock.get(STATS_URL, content=icecast_stats.read_bytes())
    legacy_client = Mock()
    StatsCollector(legacy_client).collect(
        _mounted(stream_id=3), _timestamp=datetime(2026, 10, 26, 12, 0)
    )
    assert _status_calls(legacy_client) == [{3: "OK"}]


def test_status_falls_back_to_position_without_stream_number(requests_mock):
    requests_mock.get(STATS_URL, content=icecast_stats.read_bytes())
    legacy_client = Mock()
    StatsCollector(legacy_client).collect(
        _mounted(), _timestamp=datetime(2026, 10, 26, 12, 0)
    )
    assert _status_calls(legacy_client) == [{1: "OK"}]
