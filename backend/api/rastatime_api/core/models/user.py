import re

import bcrypt
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, Permission
from django.db import models

from ...permission_constants import GROUPS
from .role import Role

# RASTATIME 2026-10-27 - bcrypt instead of unsalted md5.  The legacy PHP
# side writes "$2y$" (password_hash), this side "$2b$" (python bcrypt); both
# verify both.  A 32-character hex value is the pre-2026-10-27 md5.  It was
# accepted and re-hashed on the first match until 2026-11-11; every account
# had migrated by then, so it never matches any more (CodeQL
# py/weak-sensitive-data-hashing).  is_legacy_md5_hash only remains so that
# `manage.py password_hashes` can name accounts that need a new password
# (e.g. after restoring an old backup).
BCRYPT_ROUNDS = 12
_BCRYPT_RE = re.compile(r"^\$2[aby]\$\d{2}\$[./0-9A-Za-z]{53}$")
_MD5_RE = re.compile(r"^[0-9a-fA-F]{32}$")


def is_bcrypt_hash(stored: str) -> bool:
    return bool(stored) and _BCRYPT_RE.match(stored) is not None


def is_legacy_md5_hash(stored: str) -> bool:
    return bool(stored) and _MD5_RE.match(stored) is not None


def hash_password(raw_password: str) -> str:
    return bcrypt.hashpw(raw_password.encode("utf-8"), bcrypt.gensalt(BCRYPT_ROUNDS)).decode(
        "ascii"
    )


def verify_password(raw_password: str, stored: str) -> bool:
    """bcrypt only; an empty, legacy md5 or otherwise unusable value never matches."""
    if not is_bcrypt_hash(stored):
        return False
    try:
        return bcrypt.checkpw(raw_password.encode("utf-8"), stored.encode("ascii"))
    except ValueError:
        return False


class UserManager(BaseUserManager):
    # pylint: disable=too-many-positional-arguments
    def create_user(self, role, username, password, email, first_name, last_name):
        user = self.model(
            role=role,
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    # pylint: disable=too-many-positional-arguments
    def create_superuser(self, username, password, email, first_name, last_name):
        return self.create_user(
            Role.ADMIN,
            username,
            password,
            email,
            first_name,
            last_name,
        )

    def get_by_natural_key(self, username):
        return self.get(username=username)


class User(AbstractBaseUser):
    role = models.CharField(
        max_length=1,
        choices=Role.choices,
        db_column="type",
    )

    username = models.CharField(unique=True, max_length=255, db_column="login")
    password = models.CharField(max_length=255, db_column="pass")
    email = models.CharField(max_length=1024, blank=True, null=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)

    login_attempts = models.IntegerField(
        blank=True,
        null=True,
        db_column="login_attempts",
    )
    # RASTATIME 2026-10-06 - time of the last failed login (legacy
    # migration 0064, brute-force brake in the PHP LoginController)
    login_attempt_at = models.DateTimeField(
        blank=True,
        null=True,
        db_column="login_attempt_at",
    )
    last_login = models.DateTimeField(
        blank=True,
        null=True,
        db_column="lastlogin",
    )
    last_failed_login = models.DateTimeField(
        blank=True,
        null=True,
        db_column="lastfail",
    )

    skype = models.CharField(
        max_length=1024,
        blank=True,
        null=True,
        db_column="skype_contact",
    )
    jabber = models.CharField(
        max_length=1024,
        blank=True,
        null=True,
        db_column="jabber_contact",
    )
    phone = models.CharField(
        max_length=1024,
        blank=True,
        null=True,
        db_column="cell_phone",
    )

    class Meta:
        managed = False
        db_table = "cc_subjs"

    USERNAME_FIELD = "username"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["role", "email", "first_name", "last_name"]
    objects = UserManager()

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def get_short_name(self):
        return self.first_name

    def set_password(self, raw_password):
        if not raw_password:
            self.set_unusable_password()
        else:
            self.password = hash_password(raw_password)

    def is_staff(self):
        return self.role == Role.ADMIN

    def check_password(self, raw_password):
        if not self.has_usable_password():
            return False
        return verify_password(raw_password, self.password or "")

    def has_usable_password(self):
        # only bcrypt counts; Django's own "!" marker, the empty placeholder
        # of header-auth accounts and a legacy md5 do not
        return is_bcrypt_hash(self.password or "")

    # The following methods have to be re-implemented here, as PermissionsMixin
    # assumes that the User class has a 'group' attribute, which RASTATIME does
    # not currently provide. Once Django starts managing the Database
    # (managed = True), then this can be replaced with
    # django.contrib.auth.models.PermissionMixin.

    def is_superuser(self):
        return self.role == Role.ADMIN

    # pylint: disable=unused-argument
    def get_user_permissions(self, obj=None):
        """
        Users do not have permissions directly, only through groups
        """
        return []

    def get_group_permissions(self, obj=None):
        permissions = GROUPS[self.role]
        if obj is not None:
            obj_name = obj.__class__.__name__.lower()
            permissions = [perm for perm in permissions if obj_name in perm]
        # get permissions objects
        query = models.Q()
        for perm in permissions:
            query = query | models.Q(codename=perm)
        return list(Permission.objects.filter(query))

    def get_all_permissions(self, obj=None):
        return self.get_user_permissions(obj) + self.get_group_permissions(obj)

    def has_perm(self, perm, obj=None):
        if self.is_superuser():
            return True
        if not perm:
            return False
        permissions = self.get_all_permissions(obj)
        try:
            permission = Permission.objects.get(codename=perm)
            return permission in permissions
        except Permission.DoesNotExist:
            return False

    def has_perms(self, perm_list, obj=None):
        result = True
        for permission in perm_list:
            result = result and self.has_perm(permission, obj)
        return result
