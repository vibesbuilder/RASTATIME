from rest_framework.test import APITestCase

from libretime_api.core.models import Role, User


# RASTATIME 2026-10-25 - the installation account "admin" cannot be deleted
class TestUserDeleteProtection(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.operator = User.objects.create_superuser(
            username="operator",
            password="test",
            email="operator@example.com",
            first_name="op",
            last_name="erator",
        )
        # the installation seed (legacy data.sql) already carries "admin"
        cls.protected = User.objects.filter(username="admin").first() or User.objects.create_user(
            role=Role.ADMIN,
            username="admin",
            password="test",
            email="admin@example.com",
            first_name="ad",
            last_name="min",
        )
        cls.dj = User.objects.create_user(
            role=Role.HOST,
            username="dj",
            password="test",
            email="dj@example.com",
            first_name="d",
            last_name="j",
        )

    def setUp(self):
        self.client.login(username="operator", password="test")

    def test_admin_account_is_refused(self):
        response = self.client.delete(f"/api/v2/users/{self.protected.pk}")
        self.assertEqual(response.status_code, 403)
        self.assertTrue(User.objects.filter(pk=self.protected.pk).exists())

    def test_other_account_is_deleted(self):
        response = self.client.delete(f"/api/v2/users/{self.dj.pk}")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(User.objects.filter(pk=self.dj.pk).exists())
