"""RASTATIME 2026-11-13 - Auto DJ buffer tracks (§23.107): schedule field + status."""

from datetime import UTC, datetime, timedelta

from django.conf import settings
from django.utils import dateparse
from model_bakery import baker
from rest_framework.test import APITestCase

from ..buffer import MARGIN_SECONDS, buffer_status


def _pref(key, value):
    baker.make("core.Preference", key=key, value=value, user=None)


class TestBufferRows(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.token = settings.CONFIG.general.api_key
        now = datetime.now(tz=UTC)
        cls.show = baker.make(
            "schedule.ShowInstance",
            starts_at=now - timedelta(minutes=5),
            ends_at=now + timedelta(minutes=5),
        )
        playable = {"mime": "audio/mp3", "exists": True, "hidden": False, "disabled": False}
        cls.bed = baker.make("storage.File", length=timedelta(minutes=4), **playable)
        cls.song = baker.make("storage.File", length=timedelta(minutes=3), **playable)
        cls.playlist = baker.make("schedule.Playlist", name="Buffer")
        baker.make(
            "schedule.PlaylistContent",
            playlist=cls.playlist,
            kind=0,
            file=cls.bed,
            length=timedelta(minutes=4),
        )
        # the buffer row: starts 30 s before the show end, runs 3.5 min past it
        cls.buffer_row = baker.make(
            "schedule.Schedule",
            instance=cls.show,
            file=cls.bed,
            starts_at=cls.show.ends_at - timedelta(seconds=30),
            ends_at=cls.show.ends_at + timedelta(minutes=3, seconds=30),
            cue_in=timedelta(seconds=0.4),
            cue_out=timedelta(minutes=4),
        )
        # an ordinary row that also overbooks - never a buffer row
        cls.song_row = baker.make(
            "schedule.Schedule",
            instance=cls.show,
            file=cls.song,
            starts_at=cls.show.starts_at,
            ends_at=cls.show.starts_at + timedelta(minutes=3),
            cue_in=timedelta(0),
            cue_out=timedelta(minutes=3),
        )
        # the buffer file inside the show (it ends before the show end)
        cls.inner_row = baker.make(
            "schedule.Schedule",
            instance=cls.show,
            file=cls.bed,
            starts_at=cls.show.starts_at + timedelta(minutes=3),
            ends_at=cls.show.starts_at + timedelta(minutes=7),
            cue_in=timedelta(0),
            cue_out=timedelta(minutes=4),
        )

    def _rows(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Api-Key {self.token}")
        response = self.client.get("/api/v2/schedule")
        self.assertEqual(response.status_code, 200)
        return {row["id"]: row for row in response.json()}

    def test_fade_mode_marks_only_the_overrunning_buffer_row(self):
        _pref("auto_dj_buffer_playlist_id", str(self.playlist.id))
        _pref("auto_dj_buffer_end_mode", "fade")
        _pref("auto_dj_buffer_fade_seconds", "2.5")
        rows = self._rows()
        self.assertEqual(rows[self.buffer_row.id]["buffer_fade_out"], 2.5)
        self.assertIsNone(rows[self.song_row.id]["buffer_fade_out"])
        self.assertIsNone(rows[self.inner_row.id]["buffer_fade_out"])
        # capped at the show end, the cue out keeps the cue in
        self.assertEqual(
            dateparse.parse_duration(rows[self.buffer_row.id]["cue_out"]),
            timedelta(seconds=30.4),
        )

    def test_fade_is_bounded_by_the_crossfade_buffer(self):
        _pref("auto_dj_buffer_playlist_id", str(self.playlist.id))
        _pref("auto_dj_buffer_end_mode", "fade")
        _pref("auto_dj_buffer_fade_seconds", "9")
        self.assertEqual(self._rows()[self.buffer_row.id]["buffer_fade_out"], 3.0)

    def test_cut_mode_and_no_buffer_playlist_send_null(self):
        _pref("auto_dj_buffer_playlist_id", str(self.playlist.id))
        _pref("auto_dj_buffer_end_mode", "cut")
        self.assertIsNone(self._rows()[self.buffer_row.id]["buffer_fade_out"])

    def test_no_preferences_at_all(self):
        self.assertIsNone(self._rows()[self.buffer_row.id]["buffer_fade_out"])

    def test_status_inactive_without_auto_dj(self):
        _pref("auto_dj_buffer_playlist_id", str(self.playlist.id))
        self.assertEqual(buffer_status(), {"active": False})

    def test_status_counts_tracks_that_outlast_the_max_gap(self):
        _pref("auto_dj_enabled", "true")
        _pref("auto_dj_fill_any_show", "true")
        _pref("auto_dj_buffer_playlist_id", str(self.playlist.id))
        _pref("auto_dj_buffer_max_gap", "60")
        status = buffer_status()
        self.assertTrue(status["active"])
        self.assertTrue(status["playlist_exists"])
        self.assertEqual(status["required_seconds"], 60 + MARGIN_SECONDS)
        self.assertEqual((status["tracks"], status["usable"]), (1, 1))
        self.assertEqual(status["longest_seconds"], 240.0)

    def test_status_no_usable_track_when_the_gap_is_longer(self):
        _pref("auto_dj_enabled", "true")
        _pref("auto_dj_fill_any_show", "true")
        _pref("auto_dj_buffer_playlist_id", str(self.playlist.id))
        _pref("auto_dj_buffer_max_gap", "300")
        status = buffer_status()
        self.assertEqual((status["tracks"], status["usable"]), (1, 0))

    def test_status_endpoint(self):
        _pref("auto_dj_enabled", "true")
        _pref("auto_dj_fill_any_show", "true")
        _pref("auto_dj_buffer_playlist_id", "999999")
        self.client.credentials(HTTP_AUTHORIZATION=f"Api-Key {self.token}")
        response = self.client.get("/api/v2/auto-dj/buffer")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["active"])
        self.assertFalse(body["playlist_exists"])
        self.assertEqual(body["tracks"], 0)
