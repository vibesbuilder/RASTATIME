# BLOCKERS — T0.1: Import LibreTime Baseline
**Date:** 2026-04-24
**Status:** BLOCKED — decision required before proceeding

---

## 1. Current Repository Status

| Item | Status |
|---|---|
| `C:/RASTATIME/` exists | Yes |
| Git repository initialized | **No** — `git init` has not been run |
| LibreTime source present | **No** — only project docs present |
| Upstream tag selected | **Not specified** in any project document |
| Import strategy decided | **Not decided** |

Current files in `C:/RASTATIME/`:
- `AGENTS.md`
- `RASTATIME_ARCHITECTURE_DRAFT_v0.1.md`
- `IMPLEMENTATION_PLAN.md`
- `readme.txt`

---

## 2. Can T0.1 Proceed Now?

**No.** Three blockers must be resolved first.

---

## 3. Missing Prerequisites

### Blocker B1 — Upstream LibreTime version not selected
The architecture draft and AGENTS.md do not specify which LibreTime tag to import.
This must be an explicit user decision — not a silent assumption.

### Blocker B2 — Git import strategy not decided
Three strategies are viable. They have different trade-offs for traceability,
upstream tracking, and workflow. See §5 below.

### Blocker B3 — License acknowledgment
LibreTime is licensed under **GNU AGPL-3.0**.
A fork inherits this license obligation.
RASTATIME must include the AGPL-3.0 license text and comply with its terms.
This should be confirmed before the baseline commit.

---

## 4. Upstream LibreTime Tag/Version Candidates

Five most recent stable releases as of 2026-04-24:

| Tag | Release Date | Notable changes |
|---|---|---|
| **v4.5.0** | 2025-07-16 | Improved playout queue management; Liquidsoap fixes |
| v4.4.0 | 2025-05-29 | Nginx container config improvements |
| v4.3.0 | 2025-03-12 | FLAC support in web player |
| v4.2.0 | 2024-06-22 | Smartblock criteria with filename filtering |
| v4.1.0 | 2024-05-05 | Schedule event building in playout; cue point editor |

### Recommended candidate: **v4.2.0**

**Rationale:**
- Recent enough to have current features and bug fixes.
- Pre-dates later Liquidsoap-related changes in v4.4/v4.5 that RASTATIME will
  replace entirely — importing a version where those changes are less baked-in
  means less code to explicitly override.
- Avoids being on the bleeding edge of upstream, which may introduce instability
  not yet documented in LibreTime's own ecosystem.

**Alternative: v4.5.0** — if the user wants the most current domain logic and
UI features, accepting that more Liquidsoap integration will need to be removed.

**Decision required:** which tag does the user want to use as baseline?

---

## 5. Safest Import Strategy

Three options, ranked safest-first:

### Option A — Clone at tag → copy into RASTATIME folder structure (Recommended)
```
git clone --branch <TAG> --depth 1 https://github.com/libretime/libretime libretime-upstream
```
Then copy relevant source trees into `C:/RASTATIME/backend/`, `C:/RASTATIME/frontend/`,
commit as baseline.

**Pros:**
- No ongoing upstream tracking confusion.
- RASTATIME history is self-contained.
- Easy to audit: baseline commit is one clean import.
- No GitHub fork permissions required.

**Cons:**
- Upstream merges require manual cherry-pick if ever needed.

### Option B — GitHub fork (fork libretime/libretime into user account, clone that)
Standard GitHub fork workflow.

**Pros:**
- GitHub tracks fork relationship for PR/upstream awareness.
- Easy "upstream" remote for future cherry-picks.

**Cons:**
- Requires GitHub account with public fork.
- Fork is publicly visible as a LibreTime fork immediately.
- Adds remote-management overhead.

### Option C — `git init` + add libretime as upstream remote (shallow clone kept)
```
git init C:/RASTATIME
git remote add upstream https://github.com/libretime/libretime
git fetch upstream <TAG> --depth 1
```

**Pros:**
- Upstream remote stays configured.

**Cons:**
- More complex for contributors.
- Mixing project-prep files with upstream history is messy.

**Recommendation: Option A.** Smallest, most reversible, no external account
requirements, results in a clean single baseline commit.

---

## 6. Exact Files assistant Plans to Create or Modify in the Next Step

Once blockers are resolved, T0.1 will:

**Create:**
- `C:/RASTATIME/.git/` — repository initialized
- `C:/RASTATIME/backend/` — LibreTime api, playout, worker, analyzer, legacy subtrees
- `C:/RASTATIME/frontend/` — LibreTime UI source
- `C:/RASTATIME/FORK_NOTES.md` — upstream tag, rationale, Windows-first direction
- `C:/RASTATIME/docs/architecture/` — folder skeleton
- `C:/RASTATIME/LICENSE` — AGPL-3.0 (inherited from LibreTime)

**Modify:**
- `C:/RASTATIME/readme.txt` — updated to v0.1.0 with baseline import changelog entry

**Commit strategy:**
1. `git init`
2. Initial commit: project docs only (AGENTS.md, IMPLEMENTATION_PLAN.md, etc.)
3. Second commit: LibreTime source import (baseline — tagged `libretime-baseline-<TAG>`)
4. Third commit: FORK_NOTES.md + docs/architecture/ skeleton

---

## 7. Required User Decisions Before Proceeding

| # | Question | Options | Impact |
|---|---|---|---|
| D1 | Which LibreTime tag? | **v4.2.0** (recommended) / v4.5.0 / other | Determines baseline code volume and Liquidsoap depth |
| D2 | Import strategy? | **Option A** (recommended) / B / C | Determines upstream tracking model |
| D3 | AGPL-3.0 license compliance confirmed? | Yes / need legal review | Must be confirmed before commit |

---

## 8. Next Step After Decisions Are Made

Once D1–D3 are confirmed, assistant can execute T0.1 in one session:
1. `git init`
2. Stage and commit project docs as initial commit.
3. Clone LibreTime at the selected tag.
4. Copy source into `backend/` and `frontend/`.
5. Remove cloned temp directory.
6. Commit baseline import.
7. Create `FORK_NOTES.md`.
8. Create `docs/architecture/` folder skeleton.
9. Update `readme.txt` to v0.1.0.
10. Commit docs.
