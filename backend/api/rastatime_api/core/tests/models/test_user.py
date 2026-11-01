import hashlib

from rest_framework.test import APITestCase

from ....permission_constants import GROUPS
from ...models import Role, User
from ...models.user import is_bcrypt_hash, is_legacy_md5_hash, verify_password


class TestUserManager(APITestCase):
    def test_create_user(self):
        user = User.objects.create_user(
            role=Role.HOST,
            username="test",
            password="test",
            email="test@example.com",
            first_name="test",
            last_name="user",
        )
        db_user = User.objects.get(pk=user.pk)
        self.assertEqual(db_user.username, user.username)

    def test_create_superuser(self):
        user = User.objects.create_superuser(
            username="test",
            password="test",
            email="test@example.com",
            first_name="test",
            last_name="user",
        )
        db_user = User.objects.get(pk=user.pk)
        self.assertEqual(db_user.username, user.username)
        self.assertEqual(db_user.role, Role.ADMIN)


class TestUser(APITestCase):
    def test_guest_get_group_perms(self):
        user = User.objects.create_user(
            role=Role.GUEST,
            username="test",
            password="test",
            email="test@example.com",
            first_name="test",
            last_name="user",
        )

        permissions = user.get_group_permissions()
        # APIRoot permission hardcoded in the check as it isn't a Permission object
        str_perms = [p.codename for p in permissions] + ["view_apiroot"]
        self.assertCountEqual(str_perms, GROUPS[Role.GUEST.value])


# RASTATIME 2026-10-27 - bcrypt instead of unsalted md5, legacy md5 accepted
# once and replaced on the first successful check.
class TestUserPasswordHashing(APITestCase):
    def _user(self, password="test"):
        return User.objects.create_user(
            role=Role.HOST,
            username="hasher",
            password=password,
            email="hasher@example.com",
            first_name="h",
            last_name="u",
        )

    def test_set_password_stores_bcrypt(self):
        user = self._user("Sommer!2026")
        self.assertTrue(is_bcrypt_hash(user.password))
        self.assertTrue(user.password.startswith("$2b$12$"))
        self.assertTrue(user.check_password("Sommer!2026"))
        self.assertFalse(user.check_password("sommer!2026"))

    def test_php_prefix_is_verified(self):
        user = self._user("x")
        user.password = "$2y$" + user.password[4:]  # what password_hash() writes
        self.assertTrue(verify_password("x", user.password))
        self.assertTrue(user.check_password("x"))

    def test_legacy_md5_is_accepted_and_upgraded(self):
        user = self._user("whatever")
        User.objects.filter(pk=user.pk).update(password=hashlib.md5(b"OldPass1").hexdigest())
        user = User.objects.get(pk=user.pk)
        self.assertTrue(is_legacy_md5_hash(user.password))
        self.assertFalse(user.check_password("wrong"))
        self.assertTrue(is_legacy_md5_hash(User.objects.get(pk=user.pk).password))
        self.assertTrue(user.check_password("OldPass1"))
        stored = User.objects.get(pk=user.pk).password
        self.assertTrue(is_bcrypt_hash(stored))
        self.assertTrue(verify_password("OldPass1", stored))

    def test_empty_password_is_unusable(self):
        user = self._user("x")
        User.objects.filter(pk=user.pk).update(password="")
        user = User.objects.get(pk=user.pk)
        self.assertFalse(user.has_usable_password())
        self.assertFalse(user.check_password(""))
        self.assertFalse(user.check_password("x"))
