"""
RASTATIME 2026-10-28 - /api/v2/show-instances filters: the playout's
preflight scan lists the instances of the next 48 h (autoplaylist_missing).
"""

from datetime import datetime, timedelta, timezone

from django.conf import settings
from model_bakery import baker
from rest_framework.test import APITestCase


class TestShowInstanceFilters(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.path = "/api/v2/show-instances"
        cls.token = settings.CONFIG.general.api_key

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Api-Key {self.token}")

    def test_starts_range_and_modified_flag(self):
        now = datetime.now(tz=timezone.utc)
        inside = baker.make(
            "schedule.ShowInstance",
            starts_at=now + timedelta(hours=2),
            ends_at=now + timedelta(hours=3),
            modified=False,
        )
        baker.make(
            "schedule.ShowInstance",
            starts_at=now + timedelta(hours=2),
            ends_at=now + timedelta(hours=3),
            modified=True,
        )
        baker.make(
            "schedule.ShowInstance",
            starts_at=now + timedelta(days=5),
            ends_at=now + timedelta(days=5, hours=1),
            modified=False,
        )
        baker.make(
            "schedule.ShowInstance",
            starts_at=now - timedelta(days=1),
            ends_at=now - timedelta(hours=23),
            modified=False,
        )
        params = {
            "starts_after": now.isoformat(timespec="seconds"),
            "starts_before": (now + timedelta(hours=48)).isoformat(timespec="seconds"),
            "modified": "false",
        }
        response = self.client.get(self.path, params)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.json()], [inside.id])

    def test_without_filters_lists_everything(self):
        now = datetime.now(tz=timezone.utc)
        for days in (-1, 1, 5):
            baker.make(
                "schedule.ShowInstance",
                starts_at=now + timedelta(days=days),
                ends_at=now + timedelta(days=days, hours=1),
            )
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 3)
