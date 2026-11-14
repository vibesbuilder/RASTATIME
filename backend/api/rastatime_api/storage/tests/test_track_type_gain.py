"""RASTATIME 2026-11-13 - fixed gain per track type (legacy migration 0083)."""

from django.conf import settings
from django.db import connection
from model_bakery import baker
from rest_framework.test import APITestCase

from ..._fixtures import AUDIO_FILENAME
from .. import track_type_gain
from ..track_type_gain import _parse_gain


def test_parse_gain_clamps_and_tolerates_garbage():
    assert _parse_gain("-7.50") == -7.5
    assert _parse_gain(3) == 3.0
    assert _parse_gain("99") == 30.0
    assert _parse_gain("-99") == -30.0
    assert _parse_gain(None) == 0.0
    assert _parse_gain("abc") == 0.0
    assert _parse_gain("nan") == 0.0


def test_fixed_gain_for_without_a_track_type_is_none():
    assert track_type_gain.fixed_gain_for(None) is None
    assert track_type_gain.fixed_gain_for(0) is None


class TestFixedGainOfTheFileSerializer(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.token = settings.CONFIG.general.api_key

    def setUp(self):
        track_type_gain.clear_cache()
        self.client.credentials(HTTP_AUTHORIZATION=f"Api-Key {self.token}")

    def tearDown(self):
        track_type_gain.clear_cache()

    def _file(self, library=None):
        return baker.make(
            "storage.File",
            mime="audio/mp3",
            filepath=AUDIO_FILENAME,
            library=library,
        )

    def test_measuring_type_and_no_type_report_null(self):
        measuring = baker.make("storage.Library", code="mus1", name="Test Music", description="")
        for file in (self._file(measuring), self._file()):
            response = self.client.get(f"/api/v2/files/{file.id}")
            self.assertEqual(response.status_code, 200)
            self.assertIsNone(response.json()["track_type_fixed_gain_db"])

    def test_type_with_the_analysis_off_reports_its_fixed_gain(self):
        spots = baker.make("storage.Library", code="spt1", name="Test Spots", description="")
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE cc_track_types SET analyze_loudness = FALSE, fixed_gain_db = %s "
                "WHERE id = %s",
                ["-6.5", spots.id],
            )
        file = self._file(spots)
        response = self.client.get(f"/api/v2/files/{file.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["track_type_fixed_gain_db"], -6.5)

        # switching the analysis back on drops the fixed gain again
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE cc_track_types SET analyze_loudness = TRUE WHERE id = %s", [spots.id]
            )
        track_type_gain.clear_cache()
        response = self.client.get(f"/api/v2/files/{file.id}")
        self.assertIsNone(response.json()["track_type_fixed_gain_db"])
