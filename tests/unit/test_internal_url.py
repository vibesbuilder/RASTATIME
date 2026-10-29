"""
RASTATIME 2026-10-04 (go-live stage 1) - the backend services call the
legacy web application on THIS machine through ``general.internal_url``
(or RASTATIME_INTERNAL_URL, or http://127.0.0.1 plus the public_url path),
never through the public https address.
"""
from __future__ import annotations

import pytest

from rastatime_shared.config._models import GeneralConfig


def _general(**kwargs) -> GeneralConfig:
    base = {"public_url": "https://rastatime.example.org", "api_key": "k", "secret_key": "s"}
    base.update(kwargs)
    return GeneralConfig(**base)


def test_default_is_loopback(monkeypatch):
    monkeypatch.delenv("RASTATIME_INTERNAL_URL", raising=False)
    assert _general().internal_base_url() == "http://127.0.0.1"


def test_public_url_path_is_kept(monkeypatch):
    monkeypatch.delenv("RASTATIME_INTERNAL_URL", raising=False)
    g = _general(public_url="https://rastatime.example.org/radio/")
    assert g.internal_base_url() == "http://127.0.0.1/radio"


def test_configured_internal_url_wins_over_default(monkeypatch):
    monkeypatch.delenv("RASTATIME_INTERNAL_URL", raising=False)
    g = _general(internal_url="http://192.168.1.64/")
    assert g.internal_base_url() == "http://192.168.1.64"


def test_environment_override_wins_over_everything(monkeypatch):
    monkeypatch.setenv("RASTATIME_INTERNAL_URL", "http://127.0.0.1:8080/")
    g = _general(internal_url="http://192.168.1.64")
    assert g.internal_base_url() == "http://127.0.0.1:8080"


def test_internal_url_must_be_http_url():
    with pytest.raises(ValueError):
        _general(internal_url="not a url")


def test_playout_dj_auth_url_falls_back_to_loopback(monkeypatch, tmp_path):
    from rastatime_playout import __main__ as main

    path = tmp_path / "rastatime.conf"
    path.write_text("general:\n  public_url: https://rastatime.example.org/radio\n", encoding="utf-8")
    monkeypatch.setattr(main, "_CONFIG_FILE", str(path))
    monkeypatch.delenv("RASTATIME_DJ_AUTH_WEB_URL", raising=False)
    monkeypatch.delenv("RASTATIME_INTERNAL_URL", raising=False)
    assert main._dj_auth_web_url() == "http://127.0.0.1/radio"

    path.write_text(
        "general:\n  public_url: https://rastatime.example.org\n  internal_url: http://192.168.1.64\n",
        encoding="utf-8",
    )
    assert main._dj_auth_web_url() == "http://192.168.1.64"

    monkeypatch.setenv("RASTATIME_DJ_AUTH_WEB_URL", "http://127.0.0.1:81")
    assert main._dj_auth_web_url() == "http://127.0.0.1:81"
