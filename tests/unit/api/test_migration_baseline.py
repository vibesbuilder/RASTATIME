"""
T18.1 — Migration baseline tests.

Verify that:
  * The Django migration graph loads cleanly and has the expected shape.
  * No model drift exists (``makemigrations --check`` returns 0).
  * RASTATIME-specific migration artefacts are in place.
  * Legacy schema SQL files are present on disk.

Test inventory
--------------
File-presence tests (3, always run — no Django needed):
  1.  ``legacy/migrations/sql/schema.sql`` exists on disk.
  2.  ``legacy/migrations/sql/data.sql`` exists on disk.
  3.  ``linein`` has exactly 5 migration files (0001 … 0005).

Content-assertion tests (2, always run — no Django needed):
  4.  ``soundcard`` migration references ``rastatime_soundcard_settings`` table.
  5.  ``linein`` migration(s) reference ``rastatime_linein`` table.

Migration graph tests (6, Django-gated):
  6.  Migration graph loads without error (``MigrationLoader(None)``).
  7.  Migration graph has exactly ``_EXPECTED_NODE_COUNT`` nodes.
  8.  Leaf-node set matches ``_EXPECTED_LEAF_NODES`` exactly.
  9.  ``legacy`` app has exactly ``_EXPECTED_LEGACY_COUNT`` migrations.
 10.  RASTATIME apps (``soundcard``, ``linein``) appear in the graph.
 11.  No node key appears more than once (no duplicate (app, name) pairs).

Model-migration consistency (1, Django-gated):
 12.  ``makemigrations --check`` returns exit code 0 (no model drift).

(12 tests total; Django is configured by tests/unit/conftest.py)
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Repository root is 3 directories above this file:
#   tests/unit/api/test_migration_baseline.py
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_BACKEND_API = _REPO_ROOT / "backend" / "api"
_LEGACY_MIGRATIONS = _BACKEND_API / "rastatime_api" / "legacy" / "migrations"
_LINEIN_MIGRATIONS = _BACKEND_API / "rastatime_api" / "linein" / "migrations"
_SOUNDCARD_MIGRATIONS = _BACKEND_API / "rastatime_api" / "soundcard" / "migrations"


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
    reason="Django not installed in this environment — skipping migration graph tests",
)

# ---------------------------------------------------------------------------
# Expected migration graph shape
# ---------------------------------------------------------------------------

#: Leaf (tip) migrations that must exist after all migrations are applied.
#: Updated whenever a new leaf migration is added to any app.
#: 2026-10-02 baseline: legacy tip 0063 (crossfade / loudness / song
#: request / show-template work since 0047), linein tip 0005 (input
#: gain), and the song_request app with its 0001_initial.
_EXPECTED_LEAF_NODES: frozenset[tuple[str, str]] = frozenset(
    {
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("legacy", "0079_webstream_bridge"),
        ("linein", "0005_linein_input_gain_db"),
        ("playback", "0001_initial"),
        ("preflight", "0001_initial"),
        ("sessions", "0001_initial"),
        ("song_request", "0001_initial"),
        ("soundcard", "0002_add_output_device_names"),
    }
)

#: Total node count across the full migration graph (2026-11-03, legacy 0076:
#: 0074 publishing / archiving stage 1, 0075 archiving stage 2, 0076 stage 3):
#: 75 legacy + 5 linein + 2 soundcard + playback, preflight and
#: song_request (1 each) + Django's own auth (12), contenttypes (2) and
#: sessions (1).
_EXPECTED_NODE_COUNT = 103

#: Number of legacy migrations (0001 … 0079 without 0002, see below).
_EXPECTED_LEGACY_COUNT = 78


# ---------------------------------------------------------------------------
# 1–3  File-presence tests (always run)
# ---------------------------------------------------------------------------


def test_legacy_schema_sql_exists():
    """Legacy baseline: ``schema.sql`` must be present alongside 0001_initial."""
    assert (_LEGACY_MIGRATIONS / "sql" / "schema.sql").is_file(), (
        "legacy/migrations/sql/schema.sql not found — "
        "the LibreTime baseline schema is missing."
    )


def test_legacy_data_sql_exists():
    """Legacy baseline: ``data.sql`` must be present alongside 0001_initial."""
    assert (_LEGACY_MIGRATIONS / "sql" / "data.sql").is_file(), (
        "legacy/migrations/sql/data.sql not found — "
        "the LibreTime seed-data SQL is missing."
    )


def test_linein_has_five_migration_files():
    """``linein`` must have exactly 5 numbered migration files.

    History:
      * 0001 — initial
      * 0002 — alter linein priority
      * 0003 — add length (RASTATIME 2026-05-12, Library integration)
      * 0004 — add device_name (RASTATIME 2026-05-14, B.4 #4 USB-GUID fallback)
      * 0005 — add input_gain_db (RASTATIME 2026-10-02, per-line-in input gain)
    """
    migration_files = [
        p for p in _LINEIN_MIGRATIONS.iterdir()
        if p.suffix == ".py"
        and not p.name.startswith("_")
        and p.name != "__init__.py"
    ]
    assert len(migration_files) == 5, (
        f"Expected 5 linein migrations, found {len(migration_files)}: "
        f"{sorted(p.name for p in migration_files)}"
    )


# ---------------------------------------------------------------------------
# 4–5  Content-assertion tests (always run)
# ---------------------------------------------------------------------------


def test_soundcard_migration_references_rastatime_table():
    """
    The soundcard 0001_initial migration must reference ``rastatime_soundcard_settings``.
    Ensures no accidental table rename has been committed without a matching
    migration update.
    """
    mig = _SOUNDCARD_MIGRATIONS / "0001_initial.py"
    assert mig.is_file(), "soundcard 0001_initial migration not found"
    content = mig.read_text(encoding="utf-8")
    assert "rastatime_soundcard_settings" in content, (
        "soundcard/migrations/0001_initial.py does not reference "
        "'rastatime_soundcard_settings' — possible table rename without migration update."
    )


def test_linein_migrations_reference_rastatime_table():
    """
    At least one linein migration must reference ``rastatime_linein``.
    Ensures the RASTATIME line-in table name is stable.
    """
    all_content = "".join(
        p.read_text(encoding="utf-8")
        for p in _LINEIN_MIGRATIONS.iterdir()
        if p.suffix == ".py" and not p.name.startswith("_")
    )
    assert "rastatime_linein" in all_content, (
        "No linein migration references 'rastatime_linein' — "
        "possible table rename without migration update."
    )


# ---------------------------------------------------------------------------
# 6–11  Migration graph tests (Django-gated)
# ---------------------------------------------------------------------------


@_skip_no_django
def test_migration_graph_loads_without_error():
    """
    ``MigrationLoader(None)`` must complete without raising.

    This is the first gate: if Django cannot parse or import any migration
    file, this test fails and reveals which file is broken.
    """
    # Django is configured once for the whole tree in tests/unit/conftest.py
    # (dev settings); setting it up here made the result order-dependent.
    from django.db.migrations.loader import MigrationLoader  # noqa: PLC0415
    loader = MigrationLoader(None, ignore_no_migrations=True)
    assert loader.graph is not None


@_skip_no_django
def test_migration_graph_has_expected_node_count():
    """
    The migration graph must have exactly ``_EXPECTED_NODE_COUNT`` nodes.

    A failing count indicates a migration was added or removed without
    updating this baseline.  Update ``_EXPECTED_NODE_COUNT`` after any
    intentional change.
    """
    from django.db.migrations.loader import MigrationLoader  # noqa: PLC0415
    loader = MigrationLoader(None, ignore_no_migrations=True)
    count = len(loader.graph.nodes)
    assert count == _EXPECTED_NODE_COUNT, (
        f"Migration graph has {count} nodes; expected {_EXPECTED_NODE_COUNT}. "
        "If you added a migration, update _EXPECTED_NODE_COUNT in this file."
    )


@_skip_no_django
def test_migration_leaf_nodes_are_correct():
    """
    Leaf nodes (tip of each app's migration chain) must match ``_EXPECTED_LEAF_NODES``.

    A failing assertion means either a new migration was added (update
    ``_EXPECTED_LEAF_NODES``) or a leaf was accidentally removed/squashed.
    """
    from django.db.migrations.loader import MigrationLoader  # noqa: PLC0415
    loader = MigrationLoader(None, ignore_no_migrations=True)
    actual = frozenset(loader.graph.leaf_nodes())
    assert actual == _EXPECTED_LEAF_NODES, (
        "Leaf nodes mismatch.\n"
        f"  Extra   : {sorted(actual - _EXPECTED_LEAF_NODES)}\n"
        f"  Missing : {sorted(_EXPECTED_LEAF_NODES - actual)}"
    )


@_skip_no_django
def test_legacy_app_has_expected_migration_count():
    """
    The ``legacy`` app must have exactly ``_EXPECTED_LEGACY_COUNT`` migrations.

    Note: there is no ``legacy.0002`` — numbering jumps from 0001 to 0003.
    This is intentional and preserved from upstream LibreTime.
    """
    from collections import Counter  # noqa: PLC0415
    from django.db.migrations.loader import MigrationLoader  # noqa: PLC0415
    loader = MigrationLoader(None, ignore_no_migrations=True)
    counts = Counter(app for app, _ in loader.graph.nodes)
    actual = counts.get("legacy", 0)
    assert actual == _EXPECTED_LEGACY_COUNT, (
        f"legacy app has {actual} migrations in the graph; "
        f"expected {_EXPECTED_LEGACY_COUNT}."
    )


@_skip_no_django
def test_rastatime_apps_appear_in_migration_graph():
    """
    RASTATIME-specific apps (``soundcard``, ``linein``) must both appear
    as migration graph nodes.  These are the new tables added by RASTATIME
    on top of the LibreTime schema baseline.
    """
    from django.db.migrations.loader import MigrationLoader  # noqa: PLC0415
    loader = MigrationLoader(None, ignore_no_migrations=True)
    apps_in_graph = {app for app, _ in loader.graph.nodes}
    for app in ("soundcard", "linein"):
        assert app in apps_in_graph, (
            f"App '{app}' has no migration nodes in the graph — "
            "its migration directory may be missing or empty."
        )


@_skip_no_django
def test_migration_node_keys_are_unique():
    """
    Every (app, migration_name) pair in the graph must be unique.

    Duplicate keys would indicate a squash file that wasn't cleaned up,
    or a hand-written migration with a colliding name.
    """
    from django.db.migrations.loader import MigrationLoader  # noqa: PLC0415
    from collections import Counter  # noqa: PLC0415
    loader = MigrationLoader(None, ignore_no_migrations=True)
    counts = Counter(loader.graph.nodes.keys())
    duplicates = {k: v for k, v in counts.items() if v > 1}
    assert not duplicates, f"Duplicate migration node keys: {duplicates}"


# ---------------------------------------------------------------------------
# 12  Model-migration consistency (Django-gated)
# ---------------------------------------------------------------------------


@_skip_no_django
def test_no_pending_migrations():
    """
    ``manage.py makemigrations --check`` must exit 0.

    Exit code 1 means a model change exists that has no corresponding
    migration.  This test catches model drift before it reaches review.

    Runs ``sys.executable`` so it uses whichever Python is running the
    current test session — guaranteeing the same package set.
    """
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "django",
            "makemigrations",
            "--check",
            "--dry-run",
            f"--settings=rastatime_api.settings.dev",
            f"--pythonpath={_BACKEND_API}",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, (
        "makemigrations --check detected unapplied model changes:\n"
        + result.stdout
        + result.stderr
    )
