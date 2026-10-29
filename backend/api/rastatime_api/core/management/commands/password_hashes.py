"""
RASTATIME 2026-10-27 - how the user passwords are stored.

Until 2026-10-27 ``cc_subjs.pass`` held unsalted md5 hashes; since then
new and re-hashed passwords are bcrypt, and every account migrates on its
next successful login (web login, DJ dial-in or API).  This command tells
the operator which accounts still carry the old hash.

    manage.py password_hashes
"""

from django.core.management.base import BaseCommand

from ...models import User
from ...models.user import is_bcrypt_hash, is_legacy_md5_hash


class Command(BaseCommand):
    help = "List how each user's password is stored (bcrypt / legacy md5 / none)."

    def handle(self, *args, **options):
        out = self.stdout.write
        counts = {"bcrypt": 0, "legacy md5": 0, "none": 0}
        for user in User.objects.order_by("username"):
            stored = user.password or ""
            if is_bcrypt_hash(stored):
                kind = "bcrypt"
            elif is_legacy_md5_hash(stored):
                kind = "legacy md5"
            else:
                kind = "none"
            counts[kind] += 1
            out(f"  {kind:10s}  {user.username}  ({user.role})")
        out(
            f"{counts['bcrypt']} bcrypt, {counts['legacy md5']} legacy md5 "
            f"(migrate on the next login), {counts['none']} without a usable password"
        )
