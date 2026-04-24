# AGENTS.md — RASTATIME

## Project identity

RASTATIME is a **Windows-first functional fork of LibreTime**.

The goal is **not** to create a generic radio automation system from scratch and **not** to port Airtime directly.  
LibreTime is the functional baseline. Airtime may be used only as a **secondary historical reference** when older architecture, widgets, or undocumented behavior need clarification.

## Primary goals

1. Preserve the **core user-visible functionality and workflows of LibreTime** as far as practical.
2. Replace Linux-bound runtime layers with **Windows 11 compatible implementations**.
3. Use **VLC / libVLC as the mandatory main playout engine**.
4. Allow **Icecast only as an auxiliary stream layer** if libVLC alone is insufficient for incoming and/or outgoing streaming.
5. Keep the system **English-first** in code, config, API design, internal docs, and default UI wording.
6. Support **German as the only additional UI language** in phase 1.
7. Favor **small, reversible, low-risk implementation steps**.

---

## Non-goals

Do **not**:
- turn the project into a Linux-first system
- reintroduce Liquidsoap as the primary playout engine
- introduce Airtime-specific legacy behavior unless required to preserve LibreTime-compatible functionality
- redesign the product beyond the architecture draft without explicitly marking the change as a recommendation
- make large speculative refactors without a clear need
- introduce unnecessary complexity early

---

## Source-of-truth order

When reasoning about architecture and implementation, use this priority order:

1. `RASTATIME_ARCHITECTURE_DRAFT_v0.1.md`
2. Additional project architecture documents created for RASTATIME
3. LibreTime official documentation
4. LibreTime official repository
5. LibreTime community forum / discussions
6. Airtime documentation / forum only for historical gaps or widget behavior

If sources conflict:
- prefer the **project architecture draft** for target-state decisions
- prefer **official LibreTime sources** for current-state behavior
- treat Airtime as reference only, not as the primary implementation target

---

## Platform rules

### Target platform
- Primary target: **Windows 11**
- Development and runtime decisions must be valid for Windows 11 first

### Service startup
- The system must be able to start automatically after reboot
- Use **NSSM** as the initial Windows service wrapper unless explicitly changed in architecture docs

### Linux assumptions
Assume Linux-specific service/deployment behavior is **not portable by default**.

Do not introduce or depend on:
- `systemd`
- `systemctl`
- Linux-only path conventions
- Linux-only shell scripts as the primary runtime mechanism
- UNIX-only servers when a Windows-safe alternative is required

If Linux-specific code is encountered:
- isolate it
- document it
- replace or abstract it

---

## Core architecture rules

### Functional baseline
Preserve these concepts where possible:
- shows
- scheduling
- playlists
- webstreams
- calendar behavior
- media library behavior
- playout history and reporting
- core radio automation workflows

### Main playout engine
**libVLC / VLC is mandatory as the main playout engine.**

Use libVLC for:
- queue playback
- scheduled playout
- fallback/default rotation
- playback state
- now-playing state
- local soundcard output where feasible

Do not replace libVLC as the main engine unless the architecture draft is explicitly revised.

### Auxiliary streaming
**Icecast is optional and auxiliary only.**

Icecast may be introduced if needed for:
- outgoing internet streams
- relay/mount-based streaming
- incoming network streams
- compatibility scenarios where libVLC alone is insufficient

But:
- Icecast must not become the main playout engine
- Playout authority must remain centered on libVLC

### New RASTATIME-specific features
RASTATIME includes Windows-first features that may not exist in LibreTime as first-class features, especially:
- multiple local **Stereo Line-In** sources
- **Soundcard** settings submenu
- explicit local input/output device mapping
- Windows-native service startup model

Treat these as required target features, not optional experiments.

---

## Language and naming rules

### Canonical language
Use **English** as the canonical language for:
- code
- filenames
- folder names
- classes
- functions
- variables
- enums
- API routes
- database fields
- migration names
- config keys
- internal documentation
- default UI labels

### UI languages
Phase 1 UI languages:
- English (default)
- German

German must be implemented as a translation layer only.

### Avoid
- mixed German/English identifiers
- German database field names
- German API paths
- ambiguous abbreviations unless already well-established in the project

---

## Implementation style

### Work in very small steps
Prefer:
- small atomic commits
- reversible edits
- narrow implementation slices
- minimal viable scaffolding first
- validation after each meaningful change

Avoid:
- giant all-in-one rewrites
- changing many subsystems at once unless required
- mixing architecture redesign with feature delivery in one step

### Before coding
For each task:
1. state the objective
2. identify affected modules/files
3. identify prerequisites
4. note risks or ambiguities

### After coding
Always:
1. summarize what changed
2. list validation steps performed or still needed
3. note open issues
4. update `readme.txt` with version, changes, and changelog when code or architecture is changed

---

## File and repository conventions

### Documentation
Important project docs should remain in Markdown.

Prefer these files:
- `README.md`
- `AGENTS.md`
- `IMPLEMENTATION_PLAN.md`
- `ARCHITECTURE.md` or versioned architecture docs
- `readme.txt` for concise change tracking required by the project workflow

### readme.txt requirement
Whenever code or architecture changes are made, update or create `readme.txt` with:
- version
- summary of changes
- changelog

Do not skip this.

### Suggested top-level orientation
Use a repo structure that clearly separates:
- backend
- frontend
- playout
- audio/soundcard abstractions
- worker/background jobs
- infrastructure/service scripts
- docs
- tests

---

## Replacement guidance by subsystem

### Safe to keep conceptually
Usually keep conceptually:
- scheduling logic
- show model
- playlist concepts
- media metadata concepts
- history/reporting concepts
- calendar semantics

### Usually requires replacement or abstraction
Usually replace or heavily abstract:
- Liquidsoap-centric playout
- Celery execution model if Windows-incompatible
- Gunicorn if UNIX-only assumptions matter
- nginx if Windows limitations are problematic
- Linux deployment scripts
- Linux service units
- Linux audio backend assumptions

### Sound and streaming
For audio and streaming decisions:
- prefer the smallest Windows-safe architecture
- keep playout and streaming concerns separate where possible
- isolate hardware-specific logic behind abstractions
- avoid hardcoding device details into business logic

---

## Decision policy

When a choice is unclear:
1. choose the **smallest reversible implementation**
2. prefer explicit abstractions over hidden coupling
3. prefer Windows-safe solutions
4. preserve LibreTime-compatible behavior where practical
5. document ambiguity instead of pretending certainty

When tempted to add a new feature:
- do it only if required by the architecture draft
- otherwise mark it clearly as a recommendation, not an implicit requirement

---

## Testing expectations

For each implementation slice, define lightweight validation where possible:
- unit tests for isolated business logic
- integration tests for API behavior
- smoke tests for startup/runtime wiring
- manual validation steps for audio/device/stream behavior where automation is not yet practical

Do not leave validation entirely implicit.

---

## What to optimize for

Optimize for:
- correctness
- reversibility
- clear structure
- Windows operability
- architectural alignment with RASTATIME goals
- assistant-friendly implementation slices

Do not optimize early for:
- premature micro-performance tuning
- speculative generalization
- multi-platform elegance if it conflicts with Windows-first delivery

---

## Working mode for assistant

When asked to implement something:
- first check alignment with the architecture draft
- then propose or follow a small implementation slice
- then implement
- then validate
- then update documentation and `readme.txt`

If a requested change conflicts with the architecture draft:
- flag the conflict explicitly
- suggest the smallest compliant path forward

If the architecture draft is incomplete:
- make the smallest safe assumption
- document it clearly
- avoid broad speculative expansion
