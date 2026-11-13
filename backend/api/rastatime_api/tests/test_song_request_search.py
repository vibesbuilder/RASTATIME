"""RASTATIME 2026-11-13 - public song request catalogue: the search box of the
widget (Widgets -> Song Request) relies on the query path and on the cap the
response reports."""

from django.core.cache import cache
from django.db import connection
from model_bakery import baker
from rest_framework.test import APITestCase

from rastatime_api import song_request_api

URL = "/api/v2/song-requests/search"


def _requestable(file, value=True):
    with connection.cursor() as cursor:
        cursor.execute("UPDATE cc_files SET requestable = %s WHERE id = %s", [value, file.id])


class TestSongRequestSearch(APITestCase):
    @classmethod
    def setUpTestData(cls):
        playable = {"exists": True, "disabled": False}
        cls.alpha = baker.make(
            "storage.File", artist_name="Alpha Band", track_title="Morning", **playable
        )
        cls.zulu = baker.make(
            "storage.File", artist_name="Zulu Choir", track_title="Night Song", **playable
        )
        cls.hidden = baker.make(
            "storage.File", artist_name="Zulu Outside", track_title="Night", **playable
        )
        cls.gone = baker.make(
            "storage.File",
            artist_name="Zulu Gone",
            track_title="Night",
            exists=False,
            disabled=False,
        )
        for f in (cls.alpha, cls.zulu, cls.gone):
            _requestable(f)

    def setUp(self):
        cache.clear()  # per-IP throttle state

    def test_listing_without_query_reports_the_listing_cap(self):
        resp = self.client.get(URL)
        assert resp.status_code == 200
        assert resp.json()["limit"] == song_request_api.AVAILABLE_LIMIT
        ids = [r["id"] for r in resp.json()["results"]]
        # artist order; not requestable / missing on disk left out
        assert ids == [self.alpha.id, self.zulu.id]

    def test_query_searches_the_whole_pool_with_the_search_cap(self):
        resp = self.client.get(URL, {"q": "zulu"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["limit"] == song_request_api.SEARCH_LIMIT == 50
        assert [r["id"] for r in body["results"]] == [self.zulu.id]
        assert body["results"][0]["artist"] == "Zulu Choir"

    def test_query_matches_the_title_too(self):
        resp = self.client.get(URL, {"q": "night"})
        assert [r["id"] for r in resp.json()["results"]] == [self.zulu.id]

    def test_one_character_lists_the_pool(self):
        resp = self.client.get(URL, {"q": "z"})
        assert resp.json()["limit"] == song_request_api.AVAILABLE_LIMIT
        assert len(resp.json()["results"]) == 2

    def test_search_is_public(self):
        self.client.credentials()  # no API key, no session
        assert self.client.get(URL, {"q": "al"}).status_code == 200
