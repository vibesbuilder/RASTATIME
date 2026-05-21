# ADR-007 — RASTATIME Schema Segregation: New Tables Only for New Features

**Status:** Accepted  
**Date:** 2026-04-29  
**Deciders:** RASTATIME project  
**Relates to:** T18.1 (schema baseline), T18.2, ADR-006

---

## Context

RASTATIME inherits the full LibreTime relational schema — 35 `cc_*` tables
created by `legacy.0001_initial` via raw PostgreSQL DDL (`schema.sql`).
These tables are treated as a **read-only substrate**: RASTATIME reads from
and writes to them through Django ORM models, but does not alter their
structure through Django migrations.

As RASTATIME develops features that require persistent state beyond the
LibreTime schema (e.g., soundcard routing settings, line-in source
configuration), a policy is needed to govern how new tables are introduced.

### Forces

1. **Schema preservation** — the LibreTime schema must remain intact so that
   a side-by-side upgrade path from LibreTime stays possible.
2. **ORM migration hygiene** — Django's `migrate` should be the single source
   of truth for RASTATIME-owned tables; hand-written SQL should be minimised.
3. **Auditability** — it must be immediately obvious (from the table name and
   the app label) whether a table belongs to LibreTime or RASTATIME.
4. **Automated enforcement** — the policy must be checkable by the test suite
   without running a database.

---

## Decision

**RASTATIME never modifies legacy (`cc_*`) tables through Django migrations.**

New persistent state introduced by RASTATIME must follow these rules:

### Rule 1 — Separate app, separate migration chain

Every new RASTATIME-owned table lives in its own Django app (or a
RASTATIME-specific app), with its own `migrations/` directory and
`managed = True`.

✅ `soundcard` app → `rastatime_soundcard_settings`  
✅ `linein` app → `rastatime_linein`  

### Rule 2 — `rastatime_` table-name prefix

All `managed = True` models introduced by RASTATIME must use a
`db_table` value starting with `rastatime_`.

```python
class Meta:
    managed = True
    db_table = "rastatime_<feature>"   # ← required prefix
```

This makes the ownership boundary visible at the database level.

### Rule 3 — Legacy app models are `managed = False`

All ORM models in the LibreTime-inherited apps (`core`, `history`,
`storage`, `podcasts`, `schedule`, `legacy`) must declare `managed = False`.
They act as typed views over the existing LibreTime tables — Django never
generates DDL for them.

```python
class Meta:
    managed = False          # ← Django owns no DDL here
    db_table = "cc_files"    # ← LibreTime table; modified only via legacy migrations
```

### Rule 4 — Legacy migrations use only RunPython/RunSQL

Migrations in the `legacy` app must never contain Django ORM DDL operations
(`CreateModel`, `AddField`, `AlterField`, etc.).  They are allowed to use
`RunPython` and `RunSQL` only, preserving the raw-SQL approach inherited from
upstream LibreTime.

### Rule 5 — No `migrations/` directory in legacy-proxy apps

The apps `core`, `history`, `storage`, `podcasts`, and `schedule` must not
have a `migrations/` directory.  Their tables are created by the `legacy`
migration chain; Django should never discover migrations for them.

---

## Consequences

**Positive:**
- LibreTime schema is never accidentally modified by a `migrate` run.
- New RASTATIME tables are immediately identifiable by the `rastatime_` prefix.
- `showmigrations` output clearly separates LibreTime (legacy chain) from
  RASTATIME (soundcard, linein, …).
- The invariants are checkable offline (no DB needed) by the test suite.

**Negative / Trade-offs:**
- Adding a RASTATIME column to an existing `cc_*` table (e.g., adding
  `cc_files.rastatime_stable_id`) is explicitly prohibited by this ADR.
  Any such need requires a new join table with a `rastatime_` prefix instead.
- App count grows as features are added — one app per logical domain.

---

## Enforcement

The invariants are verified by:

```
tests/unit/api/test_schema_segregation.py   (8 tests)
```

Tests run offline (no database); Django-gated tests skip in the root venv.

To add a new RASTATIME-owned table, the checklist is:

1. Create (or reuse) a RASTATIME app with `managed = True`.
2. Set `db_table = "rastatime_<feature>"` in the model's `Meta`.
3. Run `makemigrations <app>` to generate the migration.
4. Update `_EXPECTED_NODE_COUNT` and `_EXPECTED_LEAF_NODES` in
   `tests/unit/api/test_migration_baseline.py`.
5. Run `tests/unit/api/test_schema_segregation.py` — all tests must pass.
