# RASTATIME Schema Baseline (T18.1)

**Date:** 2026-04-29  
**Django version:** 4.2.30  
**Migration graph nodes:** 63  
**Migration apps:** auth (12), contenttypes (2), legacy (45), linein (2), sessions (1), soundcard (1)

---

## Overview

RASTATIME inherits the full LibreTime relational schema and adds two new
tables of its own.  All schema changes are managed through Django migrations.

The LibreTime baseline is applied by `legacy.0001_initial`, which executes
raw PostgreSQL DDL from `backend/api/rastatime_api/legacy/migrations/sql/schema.sql`.
Subsequent `legacy.000N_*` migrations apply schema evolution patches from
upstream LibreTime.

RASTATIME-specific tables are created by the `soundcard` and `linein` apps,
each with their own Django-managed migration chain.

---

## Table Inventory

### LibreTime-preserved tables (via `legacy` migrations)

These tables are created by `legacy.0001_initial` and maintained by
`legacy.0003` through `legacy.0046`.  They preserve the upstream LibreTime
schema exactly; no RASTATIME-specific columns have been added to them.

| Table | Description |
|-------|-------------|
| `cc_files` | Media file library (audio assets) |
| `cc_track_types` | Track-type classifications (music, jingle, etc.) |
| `cc_show` | Broadcast show definitions |
| `cc_show_instances` | Individual show occurrences/airings |
| `cc_show_days` | Recurring day-of-week rules for shows |
| `cc_show_rebroadcast` | Rebroadcast schedule entries |
| `cc_show_hosts` | Show ↔ host user mappings |
| `cc_playlist` | Static playlists |
| `cc_playlistcontents` | Items within a playlist |
| `cc_block` | Dynamic blocks (smart-playlist rules) |
| `cc_blockcontents` | Items within a block |
| `cc_blockcriteria` | Selection criteria for dynamic blocks |
| `cc_pref` | Station-wide preference key/value store |
| `cc_schedule` | Playout schedule (what plays when) |
| `cc_subjs` | User accounts (LibreTime's custom user table) |
| `cc_subjs_token` | Session/API tokens for users |
| `cc_login_attempts` | Failed-login tracking |
| `cc_service_register` | Service registration (Liquidsoap heartbeats) |
| `cc_live_log` | Live broadcast log entries |
| `cc_webstream` | Webstream source definitions |
| `cc_webstream_metadata` | Metadata attached to webstreams |
| `cc_mount_name` | Icecast mount-point names |
| `cc_timestamp` | Listener-count polling timestamps |
| `cc_listener_count` | Listener count samples per mount |
| `cc_playout_history` | Historical playout log |
| `cc_playout_history_metadata` | Key/value metadata for playout history entries |
| `cc_playout_history_template` | Report template definitions |
| `cc_playout_history_template_field` | Fields within a report template |
| `third_party_track_references` | External service track-reference cache |
| `celery_tasks` | Celery async-task state tracking |
| `podcast` | Podcast feed definitions |
| `station_podcast` | Station's own podcast output |
| `imported_podcast` | External imported podcast sources |
| `podcast_episodes` | Individual episodes within a podcast |
| `sessions` | LibreTime session store (separate from Django's) |

**Total: 35 LibreTime-preserved tables**

---

### Django standard tables (via `auth`, `contenttypes`, `sessions` migrations)

| Table | App | Description |
|-------|-----|-------------|
| `auth_user` | auth | Django user model |
| `auth_group` | auth | Permission groups |
| `auth_permission` | auth | Individual permissions |
| `auth_user_groups` | auth | User ↔ group memberships |
| `auth_user_user_permissions` | auth | User ↔ permission assignments |
| `auth_group_permissions` | auth | Group ↔ permission assignments |
| `django_content_type` | contenttypes | Content-type registry |
| `django_session` | sessions | Django session store |
| `django_migrations` | (Django internal) | Applied migration log |

**Total: 9 Django standard tables**

---

### RASTATIME-new tables (via `soundcard`, `linein` migrations)

These tables do not exist in upstream LibreTime.  They are fully managed
by Django (`managed = True`) and created by RASTATIME-specific migrations.

| Table | Migration | Description |
|-------|-----------|-------------|
| `rastatime_soundcard_settings` | `soundcard.0001_initial` | Singleton soundcard routing settings: main output, preview output, line-in device IDs, missing device IDs |
| `rastatime_linein` | `linein.0001_initial` | One row per configured line-in input source; stores UUID, device stable-ID, channel mapping, priority |

**Total: 2 RASTATIME-new tables**

---

## Migration Chain Summary

```
auth         0001 → 0002 → ... → 0012   (12 migrations)
contenttypes 0001 → 0002               ( 2 migrations)
legacy       0001 → 0003 → ... → 0046  (45 migrations, no 0002)
linein       0001 → 0002               ( 2 migrations)
sessions     0001                      ( 1 migration)
soundcard    0001                      ( 1 migration)
                                       ─────────────
                                       63 total
```

> **Note on legacy numbering:** There is no `legacy.0002` migration.
> Numbering jumps from `0001_initial` to `0003_2_5_2`.  This is intentional
> and preserved from the upstream LibreTime migration history.

---

## Leaf Migrations (tips of each app's chain)

These are the "head" migrations that a fresh `migrate` run ends at.

| App | Leaf migration |
|-----|---------------|
| `auth` | `0012_alter_user_first_name_max_length` |
| `contenttypes` | `0002_remove_content_type_name` |
| `legacy` | `0046_add_override_intro_outro_playlists` |
| `linein` | `0002_alter_linein_priority` |
| `sessions` | `0001_initial` |
| `soundcard` | `0001_initial` |

---

## SQLite vs. PostgreSQL

The `legacy.0001_initial` migration executes raw PostgreSQL DDL
(`schema.sql`).  This SQL is **not compatible with SQLite** — it uses
PostgreSQL-specific constructs including:

- `DROP TABLE … CASCADE`
- `SERIAL` / `BIGSERIAL` column types
- PostgreSQL constraint deferral syntax

**Consequence:** `migrate` against a SQLite dev database will fail at
`legacy.0001_initial`.  All other migrations (`auth`, `contenttypes`,
`sessions`, `soundcard`, `linein`) are SQLite-compatible.

**Target database for T18.1 validation:** Windows PostgreSQL (psycopg2 or
psycopg3 backend).  The dev workflow uses SQLite for the non-legacy apps
only; the legacy schema requires a real PostgreSQL instance.

To run migrations against PostgreSQL in the dev settings module:

```powershell
$env:RASTATIME_USE_POSTGRES = "true"
.venv\Scripts\python.exe -m django migrate `
    --settings=rastatime_api.settings.dev `
    --pythonpath=backend\api
```

---

## Automated Validation

Migration baseline integrity is verified by:

```
tests/unit/api/test_migration_baseline.py   (12 tests)
```

Tests cover:
- File-presence: `schema.sql`, `data.sql`, linein migration count
- Content: RASTATIME table names referenced in migrations
- Graph integrity: node count, leaf nodes, legacy count, no duplicates
- Model drift: `makemigrations --check` returns 0

Run in the `backend/api` venv (Django required for 7 of the 12 tests):

```powershell
.venv\Scripts\pytest tests\unit\api\test_migration_baseline.py -v
```
