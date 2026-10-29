"""
RASTATIME 2026-09-10 - DjAuthenticator (PLAYOUT -> legacy
check-live-stream-auth) and the /dj-auth listener endpoint.
"""
from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import MagicMock
from urllib.parse import urlparse

import pytest

from rastatime_playout import source_switcher as ss
from rastatime_playout.dj_auth import CHECK_PATH, DjAuthenticator


def _session(status=200, header="1", exc=None):
    session = MagicMock()
    if exc is not None:
        session.post.side_effect = exc
    else:
        session.post.return_value = SimpleNamespace(
            status_code=status,
            headers={"icecast-auth-user": header} if header is not None else {},
        )
    return session


def test_accepted_master_login_posts_to_the_legacy_endpoint():
    session = _session()
    auth = DjAuthenticator("http://192.168.1.64/", session=session)
    assert auth.check("master", "chef", "secret", "192.168.1.7") == "ok"
    session.post.assert_called_once()
    url = session.post.call_args.args[0]
    assert url == "http://192.168.1.64" + CHECK_PATH
    assert session.post.call_args.kwargs["data"] == {
        "djtype": "master", "username": "chef", "password": "secret",
    }


def test_show_login_maps_to_djtype_dj():
    session = _session()
    DjAuthenticator("http://web", session=session).check("show", "host", "pw")
    assert session.post.call_args.kwargs["data"]["djtype"] == "dj"


def test_rejected_login():
    assert DjAuthenticator("http://web", session=_session(401, None)).check(
        "master", "chef", "wrong",
    ) == "denied"
    # 200 without the icecast-auth-user header is a rejection too
    assert DjAuthenticator("http://web", session=_session(200, None)).check(
        "master", "chef", "wrong",
    ) == "denied"


def test_unreachable_web_application_is_an_error_not_a_denial():
    auth = DjAuthenticator("http://web", session=_session(exc=ConnectionError("down")))
    assert auth.check("master", "chef", "secret") == "error"
    assert DjAuthenticator("http://web", session=_session(500, None)).check(
        "show", "host", "pw",
    ) == "error"
    assert DjAuthenticator("", session=_session()).check("master", "a", "b") == "error"


def test_unknown_source_and_empty_credentials_are_denied_without_a_request():
    session = _session()
    auth = DjAuthenticator("http://web", session=session)
    assert auth.check("bogus", "a", "b") == "denied"
    assert auth.check("master", "", "b") == "denied"
    assert auth.check("master", "a", "") == "denied"
    session.post.assert_not_called()


def test_password_never_appears_in_the_log(caplog):
    with caplog.at_level(logging.DEBUG, logger="rastatime_playout.dj_auth"):
        DjAuthenticator("http://web", session=_session()).check("master", "chef", "s3cr3t", "1.2.3.4")
        DjAuthenticator("http://web", session=_session(401, None)).check("show", "host", "s3cr3t")
        DjAuthenticator("http://web", session=_session(exc=OSError("x"))).check("show", "host", "s3cr3t")
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert "s3cr3t" not in text
    assert "chef" in text and "1.2.3.4" in text


# ---- /dj-auth endpoint -------------------------------------------------------------


@pytest.fixture
def handler(monkeypatch):
    h = ss._EventHandler.__new__(ss._EventHandler)
    sent = []
    h._send = lambda code, body: sent.append((code, body))
    h.headers = {}
    h.rfile = MagicMock()
    return h, sent


def _post(h, body: str):
    h.headers = {"Content-Length": str(len(body.encode()))}
    h.rfile.read.return_value = body.encode()


def test_dj_auth_endpoint_reads_the_form_body_and_maps_verdicts(handler, monkeypatch):
    h, sent = handler
    checker = MagicMock()
    monkeypatch.setattr(ss._EventHandler, "dj_auth", checker)
    for verdict, code in (("ok", 200), ("denied", 403), ("error", 503)):
        checker.check.return_value = verdict
        _post(h, "source=show&user=dj%20one&password=p%26w&address=192.168.1.7")
        h._handle_dj_auth(urlparse("/dj-auth"))
        assert sent[-1] == (code, verdict)
    checker.check.assert_called_with("show", "dj one", "p&w", "192.168.1.7")


def test_dj_auth_endpoint_without_authenticator_answers_error(handler, monkeypatch):
    h, sent = handler
    monkeypatch.setattr(ss._EventHandler, "dj_auth", None)
    _post(h, "source=master&user=a&password=b")
    h._handle_dj_auth(urlparse("/dj-auth"))
    assert sent == [(503, "error")]


def test_dj_auth_endpoint_query_parameters_also_work(handler, monkeypatch):
    h, sent = handler
    checker = MagicMock()
    checker.check.return_value = "ok"
    monkeypatch.setattr(ss._EventHandler, "dj_auth", checker)
    h._handle_dj_auth(urlparse("/dj-auth?source=master&user=x&password=y"))
    assert sent == [(200, "ok")]
    checker.check.assert_called_with("master", "x", "y", "")


def test_start_listener_wires_the_authenticator(monkeypatch):
    monkeypatch.setattr(ss, "_liquidsoap_state_poll_loop", lambda *a, **k: None)
    checker = object()
    server = ss.start_listener(
        ss.SourceSwitcher(switch_callback=lambda _s: None),
        host="127.0.0.1", port=0, dj_auth=checker,
    )
    try:
        assert ss._EventHandler.dj_auth is checker
    finally:
        server.shutdown()
        server.server_close()
        monkeypatch.setattr(ss._EventHandler, "dj_auth", None)
        monkeypatch.setattr(ss._EventHandler, "switcher", None)
