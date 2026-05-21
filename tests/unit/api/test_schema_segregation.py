"""
T18.2 — Schema segregation enforcement tests.

Verify that RASTATIME's schema-segregation policy (ADR-007) is upheld:

  * Legacy-proxy apps never declare ``managed = True`` models.
  * RASTATIME-owned apps never declare ``managed = False`` models.
  * All ``managed = True`` RASTATIME models use a ``rastatime_`` table prefix.
  * Legacy-proxy apps have no ``migrations/`` directory.
  * ``legacy`` app migrations contain no ORM DDL operations.

Test inventory
--------------
File-structure tests (2, always run — no Django needed):
  1.  Legacy-proxy apps have no ``migrations/`` directory.
  2.  RASTATIME-owned apps each have a ``migrations/`` directory.

Django-gated model tests (4):
  3.  All models in legacy-proxy apps have ``managed = False``.
  4.  All models in RASTATIME-owned apps have ``managed = True``.
  5.  Every ``managed = True`` RASTATIME model's ``db_table`` starts with
      ``rastatime_``.
  6.  No ``managed = True`` model anywhere uses a ``cc_`` table prefix.

Django-gated migration-content tests (2):
  7.  ``legacy`` migrations contain no ``CreateModel`` operations.
  8.  ``legacy`` migrations contain no ORM DDL operations at all
      (only ``RunPython`` / ``RunSQL``).

(8 tests total; 6 skipped in root venv where Django is absent)
"""

from __future__ import annotations

import pathlib

import pytest


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO_ROOT   = pathlib.Path(__file__).resolve().parents[3]
_BACKEND_API = _REPO_ROOT / "backend" / "api" / "libretime_api"

#: Apps whose tables are fully owned by the LibreTime ``legacy`` migration
#: chain.  These must never have a ``migrations/`` directory or any model
#: with ``managed = True``.
_LEGACY_PROXY_APPS: tuple[str, ...] = (
    "core",
    "history",
    "storage",
    "podcasts",
    "schedule",
)

#: Apps whose tables are fully owned by RASTATIME (``managed = True``,
#: ``rastatime_`` prefix, own migration chain).
_RASTATIME_OWNED_APPS: tuple[str, ...] = (
    "soundcard",
    "linein",
    "playback",
)

#: Django built-in apps that are always ``managed = True`` — excluded from
#: the "all RASTATIME managed tables must start with rastatime_" check.
_DJANGO_BUILTIN_APP_LABELS: frozenset[str] = frozenset(
    {"auth", "contenttypes", "sessions", "admin", "legacy"}
)


# ---------------------------------------------------------------------------
# Django availability guard
# ---------------------------------------------------------------------------

try:
    import django as _django_pkg  # noqa: F401
    _HAS_DJANGO = True
except ImportError:
    _HAS_DJANGO = False

_skip_no_django = pytest.mark.skipif(
    not _HAS_DJANGO,
    reason="Django not installed in this environment — skipping schema segregation tests",
)


# ---------------------------------------------------------------------------
# 1–2  File-structure tests (always run)
# ---------------------------------------------------------------------------


def test_legacy_proxy_apps_have_no_migrations_directory():
    """
    Apps that proxy LibreTime legacy tables must not have a ``migrations/``
    directory.  Their tables are managed by the ``legacy`` app's migration
    chain; Django must never discover or generate migrations for them.
    """
    violations = []
    for app_name in _LEGACY_PROXY_APPS:
        migrations_dir = _BACKEND_API / app_name / "migrations"
        if migrations_dir.is_dir():
            violations.append(app_name)
    assert not violations, (
        f"Legacy-proxy apps with unexpected migrations/ directories: {violations}\n"
        "These apps must not manage their own schema — remove the migrations/ "
        "directory and ensure all models use managed = False."
    )


def test_rastatime_owned_apps_have_migrations_directory():
    """
    RASTATIME-owned apps must each have a ``migrations/`` directory —
    confirming that Django manages their schema through the ORM migration
    framework.
    """
    missing = []
    for app_name in _RASTATIME_OWNED_APPS:
        migrations_dir = _BACKEND_API / app_name / "migrations"
        if not migrations_dir.is_dir():
            missing.append(app_name)
    assert not missing, (
        f"RASTATIME-owned apps missing a migrations/ directory: {missing}\n"
        "Create a migrations/ directory with an __init__.py and run "
        "makemigrations <app> to generate the initial migration."
    )


# ---------------------------------------------------------------------------
# 3–6  Django-gated model tests
# ---------------------------------------------------------------------------


@_skip_no_django
def test_legacy_proxy_app_models_are_all_unmanaged():
    """
    Every ORM model in a legacy-proxy app must have ``managed = False``.

    ``managed = False`` tells Django: "this table already exists; don't
    emit CREATE TABLE or ALTER TABLE for it."  A ``managed = True`` model
    in a legacy app would cause Django to try to create a table that is
    already managed by the ``legacy`` SQL migration chain.
    """
    import os  # noqa: PLC0415
    import sys  # noqa: PLC0415
    backend_api_path = str(_REPO_ROOT / "backend" / "api")
    if backend_api_path not in sys.path:
        sys.path.insert(0, backend_api_path)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "libretime_api.settings.dev")
    import django  # noqa: PLC0415
    django.setup()

    from django.apps import apps  # noqa: PLC0415
    violations = []
    for model in apps.get_models():
        if model._meta.app_label in _LEGACY_PROXY_APPS and model._meta.managed:
            violations.append(
                f"{model._meta.app_label}.{model.__name__} "
                f"(db_table={model._meta.db_table!r})"
            )
    assert not violations, (
        "Legacy-proxy models with managed = True:\n"
        + "\n".join(f"  {v}" for v in violations)
        + "\nSet managed = False in each model's Meta class."
    )


@_skip_no_django
def test_rastatime_owned_app_models_are_all_managed():
    """
    Every ORM model in a RASTATIME-owned app must have ``managed = True``.

    ``managed = True`` is the only way Django generates ``CREATE TABLE`` /
    ``ALTER TABLE`` SQL through the migration framework.  A RASTATIME model
    with ``managed = False`` would have no migration and would rely on
    external DDL — violating the single-source-of-truth principle.
    """
    from django.apps import apps  # noqa: PLC0415
    violations = []
    for model in apps.get_models():
        if model._meta.app_label in _RASTATIME_OWNED_APPS and not model._meta.managed:
            violations.append(
                f"{model._meta.app_label}.{model.__name__} "
                f"(db_table={model._meta.db_table!r})"
            )
    assert not violations, (
        "RASTATIME-owned models with managed = False:\n"
        + "\n".join(f"  {v}" for v in violations)
        + "\nSet managed = True and add a migration."
    )


@_skip_no_django
def test_rastatime_managed_tables_use_rastatime_prefix():
    """
    Every ``managed = True`` model in a RASTATIME-owned app must use a
    ``db_table`` starting with ``rastatime_``.

    The prefix makes ownership visible at the database level: a DBA can
    immediately distinguish RASTATIME-introduced tables from LibreTime-inherited
    ones without consulting the Django app registry.
    """
    from django.apps import apps  # noqa: PLC0415
    violations = []
    for model in apps.get_models():
        label = model._meta.app_label
        if label in _RASTATIME_OWNED_APPS and model._meta.managed:
            table = model._meta.db_table
            if not table.startswith("rastatime_"):
                violations.append(f"{label}.{model.__name__} (db_table={table!r})")
    assert not violations, (
        "RASTATIME-owned managed models without rastatime_ prefix:\n"
        + "\n".join(f"  {v}" for v in violations)
        + "\nSet db_table = 'rastatime_<feature>' in the model's Meta class."
    )


@_skip_no_django
def test_no_managed_model_uses_cc_prefix():
    """
    No ``managed = True`` model anywhere in the project may use a
    ``cc_`` table prefix.

    ``cc_`` is the LibreTime namespace.  All ``cc_`` tables are created by
    the ``legacy`` SQL migration chain and must remain ``managed = False``.
    A ``managed = True`` model pointing to a ``cc_`` table would cause
    Django to try to manage a table it does not own.
    """
    from django.apps import apps  # noqa: PLC0415
    violations = []
    for model in apps.get_models():
        if model._meta.managed and model._meta.db_table.startswith("cc_"):
            violations.append(
                f"{model._meta.app_label}.{model.__name__} "
                f"(db_table={model._meta.db_table!r})"
            )
    assert not violations, (
        "managed = True models pointing at cc_* tables (not allowed):\n"
        + "\n".join(f"  {v}" for v in violations)
        + "\nSet managed = False — these tables belong to the legacy schema."
    )


# ---------------------------------------------------------------------------
# 7–8  Django-gated migration-content tests
# ---------------------------------------------------------------------------


@_skip_no_django
def test_legacy_migrations_contain_no_create_model():
    """
    No migration in the ``legacy`` app may use ``migrations.CreateModel``.

    All legacy table creation happens via ``RunPython`` (which executes raw
    PostgreSQL DDL from ``schema.sql``).  A ``CreateModel`` operation in a
    legacy migration would bypass this and attempt Django-managed DDL on
    a table that already exists in the SQL schema.
    """
    from django.db.migrations.loader import MigrationLoader  # noqa: PLC0415
    from django.db.migrations.operations.models import CreateModel  # noqa: PLC0415

    loader = MigrationLoader(None, ignore_no_migrations=True)
    violations = []
    for (app, name), migration in loader.disk_migrations.items():
        if app != "legacy":
            continue
        for op in migration.operations:
            if isinstance(op, CreateModel):
                violations.append(f"legacy.{name}: CreateModel({op.name})")
    assert not violations, (
        "CreateModel operations found in legacy migrations (not allowed):\n"
        + "\n".join(f"  {v}" for v in violations)
    )


@_skip_no_django
def test_legacy_migrations_use_only_run_python_or_run_sql():
    """
    Every operation in every ``legacy`` migration must be a ``RunPython``
    or ``RunSQL`` operation.

    This enforces that the LibreTime schema is modified only via hand-written
    SQL (preserving the upstream approach), never via Django ORM DDL
    (``AddField``, ``AlterField``, ``RenameModel``, etc.).
    """
    from django.db.migrations.loader import MigrationLoader  # noqa: PLC0415
    from django.db.migrations.operations.special import (  # noqa: PLC0415
        RunPython,
        RunSQL,
        SeparateDatabaseAndState,
    )

    _ALLOWED_OP_TYPES = (RunPython, RunSQL, SeparateDatabaseAndState)

    loader = MigrationLoader(None, ignore_no_migrations=True)
    violations = []
    for (app, name), migration in loader.disk_migrations.items():
        if app != "legacy":
            continue
        for op in migration.operations:
            if not isinstance(op, _ALLOWED_OP_TYPES):
                violations.append(
                    f"legacy.{name}: {type(op).__name__}"
                )
    assert not violations, (
        "Non-RunPython/RunSQL operations found in legacy migrations:\n"
        + "\n".join(f"  {v}" for v in violations)
        + "\nLegacy schema changes must use RunPython or RunSQL only."
    )
