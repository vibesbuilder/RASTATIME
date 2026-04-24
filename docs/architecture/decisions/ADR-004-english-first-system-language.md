# ADR-004 — English as the Canonical System Language

**Status:** Accepted  
**Date:** 2026-04-24  
**Deciders:** RASTATIME project

---

## Context

LibreTime inherits mixed naming conventions from its Airtime lineage. Some
identifiers, database fields, and config keys use inconsistent casing or
language. RASTATIME adds new subsystems (Line-In, Soundcard) that have no
upstream naming to inherit.

A clear language rule prevents mixed-language identifiers from accumulating
in the codebase, which would make the code harder to read, search, and
maintain for any contributor regardless of native language.

The primary operator base for phase 1 is German-speaking, but the technical
team and any future contributors must be able to work with the codebase
without requiring German language knowledge.

## Decision

**English is the canonical language for all system internals. German is a
UI translation layer only.**

English is mandatory for:
- source code identifiers (variables, functions, classes, modules, enums),
- filenames and directory names,
- API routes and endpoint names,
- database table and field names,
- migration names,
- configuration keys and environment variable names,
- log messages,
- internal architecture documentation (ADRs, FORK_NOTES, IMPLEMENTATION_PLAN).

German is permitted only in:
- frontend locale files (`frontend/locales/de/`),
- operator-facing documentation written for German-speaking users,
- user-visible UI strings surfaced through the i18n translation layer.

German must **never** appear in:
- database schemas,
- API payloads,
- Python/JavaScript/TypeScript identifiers,
- config file keys,
- git commit messages,
- code comments.

Phase 1 UI languages: **English (default)** and **German**.
No additional languages are in scope for phase 1.

## Consequences

**Positive:**
- Codebase is readable without German language knowledge.
- Grep, search, and refactoring tools work predictably.
- API and DB schema remain stable regardless of UI locale.
- Adding further UI languages later requires only locale file additions.

**Negative / Trade-offs:**
- German-speaking contributors must write code in English.
- Existing LibreTime identifiers that are already English are kept as-is.
  Only new RASTATIME additions are governed strictly by this rule.

**Enforcement:**
- Code review must reject any German-language identifier in code, DB, or API.
- No automated enforcement tooling is required in phase 1, but may be added.

**Follow-up required:**
- T20.1: set frontend default locale to English.
- T20.2: add German translation scaffolding under `frontend/locales/de/`.
