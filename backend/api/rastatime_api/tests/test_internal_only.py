"""
RASTATIME 2026-10-25 (role audit S3/S4) - the plain Django views outside
the DRF permission system answer internal callers only: a valid Api-Key, or
a direct call from this machine (loopback peer, no X-Forwarded-For - Apache
adds that header to everything it proxies from /api/v2/).
"""

import pytest
from django.conf import settings
from django.http import JsonResponse
from django.test import RequestFactory

from ..permissions import internal_only, is_internal_request

KEY = {"HTTP_AUTHORIZATION": "Api-Key " + str(settings.CONFIG.general.api_key)}


def _request(peer="127.0.0.1", forwarded=None, **extra):
    meta = {"REMOTE_ADDR": peer, **extra}
    if forwarded is not None:
        meta["HTTP_X_FORWARDED_FOR"] = forwarded
    return RequestFactory().get("/api/v2/audio/linein", **meta)


@pytest.mark.parametrize(
    "peer,forwarded,extra,expected",
    [
        ("127.0.0.1", None, {}, True),  # legacy PHP on 127.0.0.1:8765
        ("::1", None, {}, True),
        ("::ffff:127.0.0.1", None, {}, True),
        ("127.0.0.1", "203.0.113.7", {}, False),  # proxied by Apache, no key
        ("127.0.0.1", "192.168.1.20", {}, False),  # LAN browser through Apache
        ("127.0.0.1", "203.0.113.7", KEY, True),  # proxied with the Api-Key (playout)
        ("192.168.1.20", None, {}, False),  # not loopback
        ("127.0.0.1", "203.0.113.7", {"HTTP_AUTHORIZATION": "Api-Key wrong"}, False),
    ],
)
def test_is_internal_request(peer, forwarded, extra, expected):
    assert is_internal_request(_request(peer, forwarded, **extra)) is expected


def test_internal_only_decorator():
    @internal_only
    def view(request):
        return JsonResponse({"ok": True})

    assert view(_request()).status_code == 200
    refused = view(_request(forwarded="203.0.113.7"))
    assert refused.status_code == 403
    assert b"internal callers only" in refused.content


@pytest.mark.parametrize(
    "forwarded,expected_peer,internal",
    [
        (None, "127.0.0.1", True),  # legacy PHP direct on :8765
        ("127.0.0.1", "127.0.0.1", False),  # through Apache from this machine: needs the key
        ("192.168.1.20", "192.168.1.20", False),  # browser in the LAN
        ("203.0.113.7", "203.0.113.7", False),  # internet
        (
            "127.0.0.1, 203.0.113.7",
            "203.0.113.7",
            False,
        ),  # spoofed first hop, Apache appended the real one
    ],
)
def test_waitress_proxy_options_give_the_real_client(forwarded, expected_peer, internal):
    """The service's waitress options, applied by waitress's own middleware."""
    from waitress.proxy_headers import proxy_headers_middleware

    from ..waitress_serve import PROXY_OPTIONS

    seen = {}

    def app(environ, start_response):
        seen.update(environ)
        start_response("200 OK", [])
        return [b""]

    wrapped = proxy_headers_middleware(
        app,
        trusted_proxy=PROXY_OPTIONS["trusted_proxy"],
        trusted_proxy_count=PROXY_OPTIONS["trusted_proxy_count"],
        trusted_proxy_headers=PROXY_OPTIONS["trusted_proxy_headers"],
        clear_untrusted=PROXY_OPTIONS["clear_untrusted_proxy_headers"],
    )
    environ = {
        "REMOTE_ADDR": "127.0.0.1",
        "REQUEST_METHOD": "GET",
        "PATH_INFO": "/api/v2/audio/linein",
        "wsgi.url_scheme": "http",
        "SERVER_NAME": "127.0.0.1",
        "SERVER_PORT": "8765",
    }
    if forwarded is not None:
        environ["HTTP_X_FORWARDED_FOR"] = forwarded
    wrapped(environ, lambda *a, **k: None)
    assert seen["REMOTE_ADDR"] == expected_peer
    request = RequestFactory().get("/api/v2/audio/linein", REMOTE_ADDR=seen["REMOTE_ADDR"])
    if "HTTP_X_FORWARDED_FOR" in seen:
        request.META["HTTP_X_FORWARDED_FOR"] = seen["HTTP_X_FORWARDED_FOR"]
    assert is_internal_request(request) is internal


def test_song_request_ip_hash_ignores_forged_forwarded_for():
    from ..song_request_api import _hash_ip

    plain = RequestFactory().get("/", REMOTE_ADDR="203.0.113.7")
    forged = RequestFactory().get(
        "/", REMOTE_ADDR="203.0.113.7", HTTP_X_FORWARDED_FOR="198.51.100.1, 203.0.113.7"
    )
    other = RequestFactory().get("/", REMOTE_ADDR="203.0.113.8")
    assert _hash_ip(plain) == _hash_ip(forged)
    assert _hash_ip(plain) != _hash_ip(other)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path,method",
    [
        ("/api/v2/audio/linein", "get"),
        ("/api/v2/audio/linein", "post"),
        ("/api/v2/audio/linein/1", "delete"),
        ("/api/v2/audio/soundcard-settings", "post"),
        ("/api/v2/audio/devices", "get"),
        ("/api/v2/preflight/warnings", "get"),
        ("/api/v2/preflight/warnings/replace", "post"),
        ("/api/v2/streams/outputs", "get"),
    ],
)
def test_routes_refuse_proxied_calls_without_key(client, path, method):
    response = getattr(client, method)(path, HTTP_X_FORWARDED_FOR="203.0.113.7")
    assert response.status_code == 403


# RASTATIME 2026-10-28 - "Api-Key" without a value used to raise IndexError (500)
@pytest.mark.parametrize("header", ["Api-Key", "Api-Key ", "Api-Key a b"])
def test_malformed_api_key_header_is_a_refusal_not_an_error(header):
    from rest_framework.test import APIRequestFactory

    from rastatime_api.permissions import check_authorization_header

    request = APIRequestFactory().get("/api/v2/", HTTP_AUTHORIZATION=header)
    assert check_authorization_header(request) is False
