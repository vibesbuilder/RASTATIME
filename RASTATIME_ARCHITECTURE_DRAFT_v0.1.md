
# RASTATIME — Architecture Draft
**Windows 11 LibreTime Fork with VLC/libVLC Main Playout Engine**  
Draft version: 0.1  
Date: 2026-04-23

---

## 1. Scope and Design Intent

RASTATIME is planned as a **functional fork of LibreTime**, not as a literal technical port of the current Linux deployment. The main goal is to preserve the **user-visible behavior and core radio automation feature set of LibreTime** while replacing Linux-bound runtime layers with components that run reliably on **Windows 11**.

This document is written in **English** on purpose:

- English is the canonical language for backend commands, identifiers, config keys, enums, API routes, logs, and internal architecture documentation.
- The frontend should be **English-first** as well.
- **German** is the only additional frontend language required in phase 1.

The target platform is a **Windows 11 studio machine**. RASTATIME should automatically start after reboot by running its required processes as Windows services via **NSSM** in the first implementation phase.

### 1.1 Functional Baseline

RASTATIME should copy the existing functional scope of LibreTime as far as feasible, including:

- schedule/calendar management
- show management
- playout and fallback behavior
- media library and playlists
- webstreams
- podcasts / ingestion
- history / logging / reports
- stream configuration
- user-visible operational workflows already known from LibreTime

### 1.2 Explicit Additional Features Beyond LibreTime

In addition to LibreTime compatibility, RASTATIME requires the following new Windows-focused capabilities:

1. **Line-In Sources**
   - Multiple local stereo line inputs from the Windows soundcard / audio interface
   - Dedicated **Line-In** menu entry
   - Add/edit dialog structurally similar to **Webstream**
   - Device/channel selection instead of URL entry

2. **Stereo Line-Out / Soundcard Routing**
   - Local playout must be routable to stereo outputs on the local soundcard
   - Under **Settings**, after **Streams**, add a new submenu:
     - **Settings**
       - Streams
       - **Soundcard**
   - The **Soundcard** submenu manages local input/output device selection

3. **Windows 11 Runtime**
   - No Linux-only service assumptions
   - Automatic service startup after reboot via **NSSM**
   - Windows-native install, update, and recovery workflow

### 1.3 Playout and Streaming Rule

RASTATIME must use **VLC / libVLC as the main playout engine**.

If **libVLC alone is not sufficient** for all required stream-ingress or stream-egress scenarios, **Icecast may be used as an auxiliary streaming layer** for:

- outgoing streams
- incoming network streams
- relay / mount based compatibility cases

However, even in that case:

> **libVLC remains the authoritative main playout engine.**

---

## 2. Source Basis and Design Inputs

This draft combines three kinds of source material:

### 2.1 User-Provided Internal Reference Documents

The previous STUDIO architecture documents are used here primarily as **style and structure references** for the desired output format and implementation breakdown:

- `STUDIO_ARCHITECTURE v2.1`
- `STUDIO_ARCHITECTURE v3.0`

These documents are especially useful for:
- chapter structure
- implementation sequencing
- configuration philosophy
- device settings concepts
- i18n conventions
- stepwise development planning

### 2.2 Primary External Product Sources

Primary product understanding should prefer the following sources in this order:

1. **LibreTime official docs**
2. **LibreTime official GitHub repository**
3. **LibreTime community forum**

Secondary context sources:

4. **AirTime documentation and forum archives**
5. existing AirTime/LibreTime widget discussions for calendar and now-playing behavior

### 2.3 Working Assumption

Where LibreTime and AirTime differ, **LibreTime is authoritative**.

AirTime material may be used only when:
- LibreTime documentation is incomplete,
- AirTime provides a more detailed explanation of inherited behavior,
- legacy widgets or feature semantics need historical clarification.

---

## 3. Feasibility Matrix: Porting the LibreTime / AirTime Stack to Windows 11

LibreTime today is operationally Linux-centric and assumes Linux paths, Linux service lifecycle, and Liquidsoap-centered audio/runtime structure. Therefore, RASTATIME should not be treated as a trivial 1:1 port.

The correct framing is:

- **Domain and feature fork:** yes
- **Runtime and deployment rewrite:** partially yes, and required

### 3.1 Component Feasibility Matrix

| Component | Current Role in LibreTime / AirTime | Windows 11 Feasibility | Target Strategy in RASTATIME | Decision |
|---|---|---:|---|---|
| **PostgreSQL** | Primary relational database | High | Keep | **Keep** |
| **RabbitMQ** | Broker / async infrastructure | High | Keep if still useful in the selected worker architecture | **Keep if beneficial** |
| **Django / Python app layer** | API, models, business logic, admin behavior | High | Keep and refactor where Linux assumptions exist | **Keep + Refactor** |
| **Legacy PHP layer** | Historical UI / migration / legacy features | Medium | Evaluate feature-by-feature; preserve only if still needed | **Selective keep / reduce** |
| **Liquidsoap** | Core playout, mixing, stream dispatch, inputs/outputs | Medium as software, but not aligned with project goal | Replace with libVLC-centered playout design | **Replace** |
| **libVLC / VLC** | New main playout engine | High | Introduce as primary playout core | **Adopt** |
| **Icecast** | Streaming server for public outputs and related workflows | High | Keep as optional auxiliary stream layer for ingress/egress | **Optional supporting component** |
| **Gunicorn** | UNIX-oriented app server | Low | Replace with Windows-suitable serving approach | **Replace** |
| **Celery** | Background workers / async task execution | Low for supported Windows usage | Replace with Windows-native background runner or alternative task layer | **Replace** |
| **nginx** | Reverse proxy / serving | Medium, but weak fit on Windows | Replace with a more Windows-appropriate serving model or simplify architecture | **Replace** |
| **Linux installer** | OS-level setup automation | Low | Replace completely with Windows installer / scripted bootstrap | **Replace** |
| **systemd / systemctl** | Service lifecycle and orchestration | Low | Replace completely with NSSM + Windows services | **Replace** |
| **Remote live inputs** | Network-based live contribution inputs | High at feature level | Re-implement via libVLC and/or Icecast-supporting stream ingress | **Keep functionally** |
| **Local soundcard output** | Hardware audio output | Partial in current LibreTime model | Expand into explicit Windows Soundcard module | **Replace / Extend** |
| **Multiple local line-ins** | Local hardware contribution inputs | Not present as first-class feature | New subsystem | **New** |

### 3.2 General Feasibility Conclusion

A Windows 11 fork is **feasible**, but not as a “compile and run” port.

The following areas are technically realistic to keep:

- core domain logic
- schedule/calendar semantics
- user workflows
- PostgreSQL
- much of the Python/Django layer
- optionally RabbitMQ
- optionally Icecast

The following areas must be re-architected:

- playout core
- audio I/O abstraction
- worker execution model
- Windows service lifecycle
- installer/bootstrap process
- soundcard input/output handling

Therefore the project should be positioned as:

> **A Windows-first functional fork of LibreTime with a new runtime substrate.**

---

## 4. Target Architecture and Replacement Strategy

### 4.1 Objective

RASTATIME should preserve LibreTime’s scheduling and operational behavior while replacing Linux-bound runtime layers with Windows-native or Windows-tolerant components.

The core design rule is:

> **Keep LibreTime behavior where possible. Replace Linux-bound execution layers where necessary. Extend only where Windows audio workflows require it.**

### 4.2 Architectural Principles

#### 4.2.1 Functional Fork, not Literal Port

RASTATIME is a **functional LibreTime fork**.

Target:
- preserve product behavior,
- preserve operator mental model,
- preserve workflows where sensible,

but do **not** preserve Linux implementation details merely for ideological parity.

#### 4.2.2 libVLC as Main Playout Engine

All primary playout actions must be controlled by **VLC / libVLC**:

- scheduled playout start
- scheduled playout stop
- queue control
- fallback/default playout
- current track state
- now-playing metadata
- local soundcard output routing
- playout event callbacks

If another component is introduced for streaming, it must not replace libVLC as the primary playout engine.

#### 4.2.3 Icecast as Optional Auxiliary Stream Layer

If libVLC does not provide sufficient reliability or flexibility for all stream ingress/egress scenarios, RASTATIME may use **Icecast** as an auxiliary component for:

- outgoing public streams
- outgoing relay/encoder mounts
- incoming remote live stream connections
- interoperability with legacy stream workflows

Icecast should be considered **secondary** to the main playout architecture.

#### 4.2.4 English-First System Language

Canonical language rules:

- backend code and commands: **English**
- config keys: **English**
- enum values: **English**
- API routes: **English**
- logs and architecture docs: **English**
- frontend default: **English**
- additional frontend language in phase 1: **German**

#### 4.2.5 Windows-First Runtime

The operating model assumes:

- Windows 11
- local studio deployment
- service start after reboot
- low-friction recovery after crashes
- no dependence on `systemctl`, Linux package managers, or Linux path conventions

### 4.3 Target Architecture Overview

```text
┌──────────────────────────────────────────────────────────────────────┐
│                        Windows 11 Studio PC                          │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                    RASTATIME Core Platform                     │  │
│  │                                                                │  │
│  │  ┌────────────────────┐    ┌───────────────────────────────┐   │  │
│  │  │ Web UI             │    │ API / Scheduling / Domain     │   │  │
│  │  │ EN default, DE     │◄──►│ Logic                         │   │  │
│  │  └────────────────────┘    └───────────────────────────────┘   │  │
│  │                                      │                         │  │
│  │                                      ▼                         │  │
│  │                        ┌───────────────────────────────┐       │  │
│  │                        │ Background Runner / Jobs      │       │  │
│  │                        │ imports, generation, tasks    │       │  │
│  │                        └───────────────────────────────┘       │  │
│  │                                      │                         │  │
│  │            ┌────────────────┐        │        ┌─────────────┐ │  │
│  │            │ PostgreSQL     │◄───────┼───────►│ RabbitMQ    │ │  │
│  │            │ persistent     │                 │ optional    │ │  │
│  │            │ application DB │                 │ broker      │ │  │
│  │            └────────────────┘                 └─────────────┘ │  │
│  │                                      │                         │  │
│  │                                      ▼                         │  │
│  │                    ┌──────────────────────────────────────┐     │  │
│  │                    │ Main Playout Core                   │     │  │
│  │                    │ VLC / libVLC                        │     │  │
│  │                    │ - queue                             │     │  │
│  │                    │ - scheduled playback                │     │  │
│  │                    │ - fallback/default playout          │     │  │
│  │                    │ - track change events               │     │  │
│  │                    └──────────────────────────────────────┘     │  │
│  │                           │                    │                │  │
│  │                           ▼                    ▼                │  │
│  │             ┌──────────────────────┐   ┌────────────────────┐  │  │
│  │             │ Soundcard I/O Layer  │   │ Optional Stream    │  │  │
│  │             │ - line-out           │   │ Gateway            │  │  │
│  │             │ - line-in sources    │   │ Icecast            │  │  │
│  │             │ - device mapping     │   │ - outgoing mounts  │  │  │
│  │             └──────────────────────┘   │ - incoming mounts  │  │  │
│  │                                        └────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│      Automatic startup after reboot via NSSM / Windows services      │
└──────────────────────────────────────────────────────────────────────┘
```

### 4.4 Replacement Strategy by Layer

| Current Layer | RASTATIME Target | Strategy | Decision |
|---|---|---|---|
| Schedule/calendar domain | Preserve behavior | Reuse conceptually | **Keep** |
| Playout engine (Liquidsoap) | libVLC playout runtime | Full replacement | **Replace** |
| Remote stream inputs | libVLC and/or Icecast ingress layer | Re-implement | **Replace implementation, keep function** |
| Stream outputs | libVLC where sufficient, Icecast where needed | Hybrid strategy | **Adapt** |
| Hardware audio output | Windows Soundcard module | Replace and extend | **Replace / Extend** |
| Local audio inputs | New Line-In subsystem | New subsystem | **New** |
| Async workers | Windows-compatible background runner | Replace | **Replace** |
| Linux service management | NSSM-managed Windows services | Replace | **Replace** |
| Web/API layer | Django/Python application layer | Refactor | **Keep + Refactor** |
| DB layer | PostgreSQL | Preserve | **Keep** |

### 4.5 Stream Handling Strategy

#### 4.5.1 Local Playout

Local on-air playout is always driven by **libVLC**.

#### 4.5.2 Outgoing Streams

Use the following priority:

1. **Preferred**: libVLC-driven output when stable and operationally sufficient
2. **Fallback / compatibility**: Icecast when:
   - mount-based output is preferable,
   - relay/server metadata handling is better through Icecast,
   - multiple public outputs are required,
   - operational separation between playout and public delivery is desired

#### 4.5.3 Incoming Remote Streams

Use the following priority:

1. direct stream handling if feasible in the selected playout/ingress architecture
2. Icecast-based ingress if this is more stable or more compatible with existing contribution tools

#### 4.5.4 Local Hardware Inputs

Local line inputs are not modeled as URLs.  
They are modeled as **first-class local audio sources**.

This requires:

- a new **Line-In** menu
- add/edit dialogs similar to **Webstream**
- device/channel selection
- persistent metadata for each local line input source

### 4.6 Soundcard Architecture

#### 4.6.1 Menu Structure

Under **Settings**, add:

- Streams
- **Soundcard**

#### 4.6.2 Soundcard Responsibilities

The Soundcard area manages:

- main playout output device
- optional preview / secondary output
- local stereo input devices
- logical naming of line inputs
- channel/device mapping
- future input/output test tools

#### 4.6.3 Abstraction Rule

Business logic must not depend directly on Windows device strings or unstable driver names.

A dedicated **Soundcard abstraction layer** must isolate:

- device enumeration
- persistence of selected devices
- internal stable identifiers
- mapping from logical channels to physical hardware

---

## 5. Detailed Implementation Sequence
### Step-by-Step Conversion Plan for assistant

This section intentionally breaks the project into **small, low-risk, assistant-friendly tasks**.  
Each task should be implementable, reviewable, and testable in isolation.

### 5.1 General Rules for the Build Process

1. Prefer **small pull requests / small commits**.
2. Do not change domain logic and runtime architecture in the same task if avoidable.
3. Keep the system bootable/runnable after each completed milestone whenever possible.
4. Introduce **abstractions first**, then switch implementations behind them.
5. Add Windows-specific code through **new adapters**, not through scattered inline conditionals.
6. Treat all Linux-specific runtime assumptions as technical debt to be isolated early.
7. Preserve LibreTime feature semantics before optimizing.

---

## 6. Phase 0 — Project Preparation

### 6.1 Create Fork and Freeze Baseline
**Goal:** establish a reproducible starting point.

Tasks:
1. Fork the LibreTime repository.
2. Create a dedicated branch naming convention:
   - `main`
   - `windows-port`
   - feature branches per task
3. Tag the baseline import commit.
4. Write a short `FORK_NOTES.md` describing:
   - source version/tag
   - current upstream version
   - known reasons for the fork
   - Windows-first direction
5. Record which LibreTime modules exist at baseline:
   - API
   - worker
   - playout
   - analyzer
   - legacy
   - stream-related services
6. Add a top-level `docs/architecture/` folder.

**Deliverable:** reproducible fork baseline.

### 6.2 Create Architecture Guardrails
**Goal:** avoid uncontrolled rewrites.

Tasks:
1. Add `docs/architecture/decisions/`.
2. Create initial ADRs:
   - ADR-001: Windows-first target
   - ADR-002: libVLC main playout engine
   - ADR-003: Icecast auxiliary only
   - ADR-004: English-first identifiers and UI default
   - ADR-005: NSSM for first service strategy
3. Add a `RATIONALE.md` summarizing why the fork is not a direct Linux port.

**Deliverable:** architecture decision baseline.

---

## 7. Phase 1 — Inventory and Isolation

### 7.1 Inventory Linux-Coupled Code Paths
**Goal:** identify what must be replaced before implementing Windows runtime.

Tasks:
1. Search for:
   - `systemctl`
   - `/etc/`
   - `/var/`
   - `/srv/`
   - `nginx`
   - `gunicorn`
   - `celery`
   - `liquidsoap`
   - ALSA / OSS / PortAudio assumptions
2. Create a matrix:
   - file/module
   - Linux dependency type
   - keep/refactor/delete status
3. Classify each item:
   - **domain logic**
   - **runtime binding**
   - **deployment script**
   - **audio-specific**
   - **legacy UI**

**Deliverable:** Windows migration inventory.

### 7.2 Build Runtime Interfaces Before Replacing Implementations
**Goal:** decouple the system from concrete Linux components.

Create explicit interfaces / service boundaries for:
1. playout engine
2. stream ingress manager
3. stream egress manager
4. audio device manager
5. background task runner
6. service lifecycle / health reporting

**Deliverable:** interface layer committed without behavior change.

---

## 8. Phase 2 — Windows Development Bootstrap

### 8.1 Get the Existing Codebase Running in a Minimal Windows Dev Mode
**Goal:** create a non-production Windows dev baseline.

Tasks:
1. Run database layer on Windows.
2. Run core application server in dev mode.
3. Disable or stub unsupported runtime modules temporarily.
4. Document current blockers in `WINDOWS_DEV_STATUS.md`.

**Deliverable:** partial Windows dev startup, even with playout disabled.

### 8.2 Add Local Developer Bootstrap Scripts
**Goal:** one-command-ish setup for contributors.

Tasks:
1. Create PowerShell bootstrap scripts:
   - `scripts/dev/bootstrap.ps1`
   - `scripts/dev/run-api.ps1`
   - `scripts/dev/run-worker.ps1`
2. Add environment validation:
   - Python version
   - PostgreSQL presence
   - VLC/libVLC presence
   - optional RabbitMQ presence
3. Add readable failure messages.

**Deliverable:** repeatable Windows dev bootstrap.

---

## 9. Phase 3 — Playout Abstraction First

### 9.1 Introduce a Playout Engine Interface
**Goal:** stop direct coupling to Liquidsoap-style execution.

Define an internal interface such as:

- start
- stop
- pause
- load queue
- append queue items
- clear queue
- get state
- get current item
- get remaining duration
- register track change callbacks
- register error callbacks
- select output device

**Deliverable:** implementation-neutral playout contract.

### 9.2 Add a Temporary Null / Mock Playout Engine
**Goal:** enable the rest of the system to compile and run while libVLC work is ongoing.

Tasks:
1. Implement a no-audio mock engine.
2. Simulate:
   - state
   - current item
   - queue behavior
   - next-track events
3. Wire it behind a config flag.

**Deliverable:** safe scaffolding for integration work.

---

## 10. Phase 4 — libVLC Core Integration

### 10.1 Create the libVLC Adapter
**Goal:** introduce the real main playout engine.

Tasks:
1. Add libVLC binding dependency.
2. Implement `LibVlcPlayoutEngine`.
3. Support:
   - file playback
   - playlist/queue playback
   - track change callbacks
   - playback state retrieval
   - stop / pause / resume
4. Keep the first version intentionally minimal:
   - no advanced routing yet
   - no optional stream encoding yet

**Deliverable:** basic playout engine using libVLC.

### 10.2 Connect Scheduler to the New Engine
**Goal:** prove real scheduled playback works.

Tasks:
1. Route playout dispatch through the playout interface.
2. Map current scheduling actions to:
   - soft start
   - hard start
   - stop current
   - load next queue
3. Verify:
   - scheduled playback starts
   - track metadata updates
   - fallback playout can start after show content ends

**Deliverable:** scheduled playback works through libVLC.

### 10.3 Move “Current Track” and “Now Playing” to Engine Callbacks
**Goal:** replace old playout event assumptions.

Tasks:
1. Subscribe to libVLC events.
2. Feed:
   - now-playing data
   - history/logging
   - dashboard updates
3. Normalize track event payloads so the rest of the system is engine-agnostic.

**Deliverable:** playout status pipeline based on libVLC callbacks.

---

## 11. Phase 5 — Default Rotation and Queue Semantics

### 11.1 Recreate LibreTime-Compatible Fallback Behavior
**Goal:** preserve operator expectations around scheduled playout and fallback.

Tasks:
1. define queue priority rules
2. define scheduled show queue behavior
3. define fallback/default rotation behavior
4. document exact switching rules

**Deliverable:** written behavior contract.

### 11.2 Implement Queue Manager
**Goal:** centralize queue logic outside raw libVLC calls.

Tasks:
1. create queue manager module
2. distinguish:
   - active show queue
   - fallback/default queue
3. expose:
   - refill checks
   - queue-empty actions
   - show-end transitions
4. add unit tests

**Deliverable:** deterministic queue orchestration layer.

---

## 12. Phase 6 — Streaming Architecture

### 12.1 Build a Stream Capability Matrix
**Goal:** decide what libVLC can do directly and where Icecast is needed.

Tasks:
1. list all stream-related LibreTime use cases:
   - outgoing public streams
   - multiple output streams
   - incoming live contribution streams
   - metadata propagation
   - reconnect behavior
2. test each use case against libVLC capabilities
3. classify each:
   - supported directly by libVLC
   - better handled by Icecast
   - needs custom bridge logic

**Deliverable:** implementation decision matrix.

### 12.2 Implement Outgoing Stream Layer
**Goal:** keep public streaming capability.

Tasks:
1. define stream output model
2. implement first output path
3. choose runtime:
   - direct libVLC if sufficient
   - Icecast-backed if better
4. expose output status in system UI/API

**Deliverable:** one working outgoing stream path.

### 12.3 Implement Incoming Remote Stream Layer
**Goal:** preserve live contribution features.

Tasks:
1. define input source model for remote streams
2. decide per source type:
   - direct ingestion
   - Icecast mount based ingress
3. add authentication/config persistence where required
4. connect switching logic to playout runtime

**Deliverable:** one working remote live input path.

---

## 13. Phase 7 — Soundcard and Local Line-In/Line-Out

### 13.1 Create Device Enumeration Service
**Goal:** introduce stable Windows audio hardware discovery.

Tasks:
1. create audio device service
2. list:
   - output devices
   - input devices
   - channel counts
   - stable internal identifiers
3. expose API endpoint(s)
4. cache the normalized device list if needed

**Deliverable:** device enumeration API.

### 13.2 Add Soundcard Settings Submenu
**Goal:** provide operator-level hardware mapping.

Tasks:
1. add **Settings → Soundcard**
2. add fields for:
   - main output
   - preview output (optional)
   - line-in devices
3. persist selected devices
4. handle “device missing after reboot” gracefully

**Deliverable:** configurable soundcard UI and persistence.

### 13.3 Add Line-In Domain Model
**Goal:** represent local line inputs as proper system entities.

Suggested fields:
- id
- name
- device_id
- channel_mapping
- enabled
- description
- priority / switching metadata (if needed later)

**Deliverable:** local line-in model + persistence.

### 13.4 Add Line-In UI
**Goal:** match the requested UX.

Tasks:
1. add **Line-In** menu entry
2. create list view
3. create add/edit dialog similar to **Webstream**
4. replace URL input with:
   - device selection
   - channel mapping
   - logical name
5. add enable/disable support

**Deliverable:** Line-In UI feature.

### 13.5 Add Actual Local Input Routing
**Goal:** make local hardware inputs usable in runtime.

Tasks:
1. define how a line-in is activated
2. define source priority vs scheduled playout
3. define fade/switch behavior
4. integrate with the stream/pllout source selection model

**Deliverable:** one working local line-in path.

---

## 14. Phase 8 — Worker and Background Task Replacement

### 14.1 Isolate All Background Jobs
**Goal:** remove hard dependency on the current unsupported worker model.

Tasks:
1. list background jobs:
   - media scan
   - podcast checks
   - import tasks
   - scheduled generation
   - cleanup
   - push/export tasks
2. separate short jobs from long-running jobs
3. identify retry behavior needs

**Deliverable:** worker workload inventory.

### 14.2 Implement Windows-Compatible Background Runner
**Goal:** replace Celery-centric assumptions.

Tasks:
1. create a Windows-friendly job runner process/service
2. define:
   - job registry
   - retry rules
   - logging
   - status reporting
3. port jobs one by one
4. keep broker integration optional, not mandatory, unless clearly beneficial

**Deliverable:** background runner operating without Celery dependency.

---

## 15. Phase 9 — Web/API Runtime Simplification

### 15.1 Remove UNIX-Only Serving Assumptions
**Goal:** stop depending on gunicorn/nginx-specific deployment expectations.

Tasks:
1. remove gunicorn-only deployment assumptions from docs and scripts
2. define Windows-oriented web serving strategy
3. keep first production model simple:
   - application server
   - optional reverse proxy only if really needed
4. update health endpoints

**Deliverable:** Windows-oriented serving model.

### 15.2 Keep URLs, API Semantics, and User Behavior Stable
**Goal:** minimize migration shock.

Tasks:
1. preserve existing route semantics where practical
2. preserve response shape unless there is a clear reason to change it
3. add compatibility shims when helpful

**Deliverable:** stable integration surface.

---

## 16. Phase 10 — Data, Metadata, and History

### 16.1 Preserve Core Domain Schema First
**Goal:** avoid accidental feature regressions.

Tasks:
1. keep show/media/history-related schema compatible where possible
2. add only the new tables/entities that are required for:
   - line-ins
   - soundcard mappings
   - Windows runtime settings
3. avoid unnecessary schema churn

**Deliverable:** controlled schema evolution.

### 16.2 Rebind History Logging to New Runtime Events
**Goal:** replace playout history generation tied to old engine assumptions.

Tasks:
1. define normalized playback event record
2. map libVLC callbacks to history events
3. map stream/live-switch events to history where relevant
4. verify exports/reports still work

**Deliverable:** playout history restored on new runtime.

---

## 17. Phase 11 — Frontend Language and UX Consolidation

### 17.1 Normalize UI Language
**Goal:** make English the canonical system wording.

Tasks:
1. set frontend default locale to English
2. keep German as the only additional locale in phase 1
3. align terminology across UI, docs, and API references

**Deliverable:** English-first UI baseline.

### 17.2 Add New Menus Without Breaking Familiar LibreTime Navigation
**Goal:** preserve user orientation.

Add or revise:
- Line-In
- Settings → Soundcard

Do not casually rename existing LibreTime concepts unless there is a real clarity gain.

**Deliverable:** feature-complete phase-1 menu structure.

---

## 18. Phase 12 — Windows Service and Operations Layer

### 18.1 Define Service Split
**Goal:** decide which processes become separate Windows services.

Candidate services:
- web/API service
- background runner
- playout runtime
- optional stream gateway / Icecast service
- optional broker service

**Deliverable:** service topology definition.

### 18.2 Add NSSM Service Definitions
**Goal:** enable auto-start after reboot.

Tasks:
1. create service install scripts
2. create service remove scripts
3. create service status helper scripts
4. define restart order and dependencies
5. document logs and recovery steps

**Deliverable:** repeatable Windows service setup.

### 18.3 Add Operator Documentation
**Goal:** make local maintenance practical.

Write:
- install guide
- upgrade guide
- backup guide
- crash recovery guide
- “audio device missing after reboot” guide
- “line-in stopped working” guide

**Deliverable:** minimum operational docs.

---

## 19. Phase 13 — Final Hardening

### 19.1 Kill Leftover Linux Assumptions
**Goal:** avoid hidden runtime breakage.

Tasks:
1. remove dead Linux-specific code
2. remove obsolete Liquidsoap references where no longer needed
3. remove obsolete deployment notes
4. clean environment variables and config defaults

**Deliverable:** Windows-first codebase.

### 19.2 Test Matrix
**Goal:** validate the fork as a product, not just as code.

Test areas:
- reboot recovery
- missing audio device handling
- scheduled playout
- fallback playout
- outgoing stream continuity
- incoming stream switching
- local line-in switching
- history/log integrity
- settings persistence
- language switching
- service restart behavior

**Deliverable:** release-readiness checklist.

---

## 20. Recommended Milestone Order

To keep assistant tasks small and coherent, use this milestone order:

1. **Fork baseline + ADRs**
2. **Linux dependency inventory**
3. **Windows dev bootstrap**
4. **Playout interface**
5. **Mock playout engine**
6. **libVLC basic playback**
7. **Scheduler → libVLC integration**
8. **Track callbacks / now-playing**
9. **Queue manager + fallback**
10. **Device enumeration**
11. **Soundcard settings**
12. **Line-In model + UI**
13. **Local line-in runtime**
14. **Outgoing stream capability matrix**
15. **Outgoing stream implementation**
16. **Incoming stream implementation**
17. **Background runner replacement**
18. **History/report rebinding**
19. **Windows service automation via NSSM**
20. **Hardening, docs, packaging**

This order minimizes cross-coupled changes and allows each milestone to build on stable abstractions.

---

## 21. Final Architectural Position

RASTATIME should be implemented as a:

> **Windows-first, LibreTime-compatible, libVLC-centered radio automation fork**

with the following non-negotiable rules:

1. **LibreTime is the functional baseline**
2. **libVLC is the mandatory main playout engine**
3. **Icecast is optional and auxiliary**
4. **Windows 11 is the primary runtime target**
5. **English is the canonical system language**
6. **German is the first optional frontend translation**
7. **NSSM is the first service-start strategy**
8. **Local Line-In and Soundcard routing are first-class Windows features**

---

## 22. External Reference Notes

These external references are the main evidence base for the technical direction of this draft:

- LibreTime official architecture docs
- LibreTime official configuration docs
- LibreTime user documentation for Streams / soundcard output / input streams
- LibreTime installer docs and Linux deployment assumptions
- LibreTime GitHub releases and repository
- official docs for PostgreSQL, RabbitMQ, Icecast, libVLC, Django, Celery, nginx, NSSM

This draft intentionally uses those sources to support a **Windows-first adaptation strategy**, not to imply that current upstream LibreTime already supports this target natively.

