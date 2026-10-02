"""
Django bootstrap for the root unit-test tree (RASTATIME 2026-10-02).

The root venv carries Django and pytest-django but no
``DJANGO_SETTINGS_MODULE``: pytest-django reads that setting before any
conftest below the root loads, so it configures nothing, and every test
that guards only on "Django importable" died with ``ImproperlyConfigured``
(19 of them).  Three ``tests/unit/api`` modules set the dev settings ad
hoc *inside* a test, which made the outcome depend on collection order -
the modules sorted before them failed, the ones after them passed, and
the leaked setup (``soundcard/apps.py`` registers the real device
manager) tripped an unrelated worker test.

This conftest configures Django once, at collection, with the dev
settings: they need no config file and no database server (an SQLite
file that the tests never touch).  The ``django_db``-marked tests
(``tests/unit/api`` and ``tests/unit/audio``) are skipped explicitly -
the dev SQLite holds no migrated schema, and a unit run must not create
a test database on the live PostgreSQL.  They run from ``backend/api``,
whose pyproject selects the testing settings.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "libretime_api.settings.dev")

try:
    import django

    django.setup()
except ImportError:  # no Django at all: the modules skip themselves
    pass


def pytest_collection_modifyitems(items):
    needs_db = pytest.mark.skip(
        reason="needs a migrated test database - run from backend/api "
        "(testing settings), not from the repo root",
    )
    for item in items:
        if item.get_closest_marker("django_db") is not None:
            item.add_marker(needs_db)
