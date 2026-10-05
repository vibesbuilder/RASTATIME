"""
RASTATIME 2026-09-10 - the harbor ports and mounts come from
stream.inputs.* in libretime.conf (what Settings -> Streams shows), with a
safety net against Icecast's ports; the legacy web URL for the DJ login
check comes from general.public_url or RASTATIME_DJ_AUTH_WEB_URL.
"""
from __future__ import annotations

import pytest

from libretime_playout import __main__ as main


def _conf(monkeypatch, tmp_path, text):
    path = tmp_path / "libretime.conf"
    path.write_text(text, encoding="utf-8")
    monkeypatch.setattr(main, "_CONFIG_FILE", str(path))
    return path


def test_inputs_from_config(monkeypatch, tmp_path):
    _conf(monkeypatch, tmp_path, (
        "general:\n  public_url: http://192.168.1.64\n"
        "stream:\n  inputs:\n"
        "    main:\n      mount: main\n      port: 8001\n"
        "    show:\n      mount: /show\n      port: 8001\n"
    ))
    assert main._read_harbor_inputs([{"port": 8000}]) == (8001, "main", 8001, "show")
    # RASTATIME 2026-10-04 (go-live stage 1): the check stays on this machine
    assert main._dj_auth_web_url() == "http://127.0.0.1"


def test_icecast_port_is_refused_with_a_warning(monkeypatch, tmp_path, caplog):
    _conf(monkeypatch, tmp_path, (
        "stream:\n  inputs:\n"
        "    main:\n      mount: main\n      port: 8000\n"
        "    show:\n      mount: show\n      port: 8002\n"
    ))
    with caplog.at_level("WARNING", logger="libretime_playout.__main__"):
        result = main._read_harbor_inputs([{"port": 8002}])
    assert result == (8001, "main", 8001, "show")
    assert sum("cannot bind" in r.getMessage() for r in caplog.records) == 2


def test_missing_section_uses_defaults(monkeypatch, tmp_path):
    _conf(monkeypatch, tmp_path, "general:\n  public_url: http://x\n")
    assert main._read_harbor_inputs([]) == (8001, "main", 8001, "show")


def test_unreadable_config_uses_defaults(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "_CONFIG_FILE", str(tmp_path / "missing.conf"))
    assert main._read_harbor_inputs([]) == (8001, "main", 8001, "show")
    assert main._dj_auth_web_url() == "http://127.0.0.1"


def test_env_overrides_the_web_url(monkeypatch, tmp_path):
    _conf(monkeypatch, tmp_path, "general:\n  public_url: http://192.168.1.64\n")
    monkeypatch.setenv(main.DJ_AUTH_WEB_URL_ENV, "http://127.0.0.1:8080")
    assert main._dj_auth_web_url() == "http://127.0.0.1:8080"


# RASTATIME 2026-10-04 (go-live stage 0) - the Line-In capture takes the
# local Icecast's source credentials from the stream outputs.
def test_linein_credentials_prefer_local_output_on_8000():
    outputs = [
        {"output": "icecast", "enable": "true", "host": "stream.example.org", "port": "8000", "user": "src", "pass": "remote"},
        {"output": "icecast", "enable": "true", "host": "127.0.0.1", "port": "8010", "user": "source", "pass": "other"},
        {"output": "icecast", "enable": "true", "host": "localhost", "port": "8000", "user": "source", "pass": "s3cret"},
    ]
    assert main._local_icecast_source_credentials(outputs) == ("source", "s3cret")


def test_linein_credentials_skip_disabled_and_empty():
    outputs = [
        {"output": "icecast", "enable": "false", "host": "127.0.0.1", "port": "8000", "user": "source", "pass": "off"},
        {"output": "icecast", "enable": "true", "host": "127.0.0.1", "port": "8000", "user": "source", "pass": ""},
        {"output": "shoutcast", "enable": "true", "host": "127.0.0.1", "port": "8000", "user": "source", "pass": "sc"},
    ]
    assert main._local_icecast_source_credentials(outputs) is None
    assert main._local_icecast_source_credentials([]) is None
