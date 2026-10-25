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
        ("127.0.0.1", None, {}, True),            # legacy PHP on 127.0.0.1:8765
        ("::1", None, {}, True),
        ("::ffff:127.0.0.1", None, {}, True),
        ("127.0.0.1", "203.0.113.7", {}, False),  # proxied by Apache, no key
        ("127.0.0.1", "192.168.1.20", {}, False),     # LAN browser through Apache
        ("127.0.0.1", "203.0.113.7", KEY, True),  # proxied with the Api-Key (playout)
        ("192.168.1.20", None, {}, False),            # not loopback
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
