RASTATIME — readme.txt
=======================

Version: 0.1.1
Date: 2026-04-24

Summary
-------
T0.2 complete: ADR-001 through ADR-005 created under
docs/architecture/decisions/. Covers Windows-first target, libVLC
as main playout engine, Icecast as auxiliary only, English-first
system language, and NSSM as phase 1 service strategy.

Changelog
---------
0.1.1 (2026-04-24)
    - Task T0.2 complete: 5 Architecture Decision Records created.
    - ADR-001: Windows 11 as primary runtime target.
    - ADR-002: libVLC as mandatory main playout engine.
    - ADR-003: Icecast as optional auxiliary stream layer.
    - ADR-004: English as canonical system language; German UI-only.
    - ADR-005: NSSM as phase 1 Windows service strategy.
    - .gitkeep removed from docs/architecture/decisions/ (now has real files).

0.1.0 (2026-04-24)
    - Task T0.1 complete: LibreTime 4.5.0 baseline imported.
    - git init; .gitattributes for Windows line endings.
    - backend/: api, api-client, analyzer, playout, shared, worker.
    - frontend/legacy/: PHP/JS UI layer.
    - infra/upstream/: Linux/Docker reference files (not for production).
    - docs/upstream/: LibreTime docs reference.
    - LICENSE: AGPL-3.0 at repository root.
    - FORK_NOTES.md: upstream tag, rationale, import mapping.
    - docs/architecture/: folder skeleton with decisions/, diagrams/.
    - docs/dev/, docs/operator/: placeholder folders.
    - playout/, audio/, streams/, tests/: empty placeholder folders.
    - BLOCKERS_T0.1.md resolved (remains in repo as record).

0.0.3 (2026-04-24)
    - Created BLOCKERS_T0.1.md: blocker report for T0.1.
    - Documents three blockers: git init, version selection, import strategy.
    - Recommends LibreTime v4.2.0 + Option A (clone-then-copy).
    - No source code changes.

0.0.2 (2026-04-24)
    - Added IMPLEMENTATION_PLAN.md (derived from AGENTS.md +
      RASTATIME_ARCHITECTURE_DRAFT_v0.1.md).
    - No source code changes.

0.0.1 (2026-04-23)
    - Initial project docs: AGENTS.md,
      RASTATIME_ARCHITECTURE_DRAFT_v0.1.md.
