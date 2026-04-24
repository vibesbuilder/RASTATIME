# RATIONALE — Why RASTATIME Is Not a Direct Linux Port

**Date:** 2026-04-24  
**Relates to:** `RASTATIME_ARCHITECTURE_DRAFT_v0.1.md` §3, §4

---

## The Core Position

RASTATIME is a **functional fork of LibreTime**, not a literal technical port
of the LibreTime Linux deployment stack.

The distinction matters:

- A **literal port** would try to run every LibreTime component on Windows,
  replacing only what is strictly necessary to compile and start.
- A **functional fork** preserves operator-visible behavior and domain logic
  while replacing the runtime substrate with components that actually work
  on the target platform.

RASTATIME takes the functional fork approach because a literal port is not
viable. This document explains why.

---

## Why a Literal Port Is Not Viable

### 1. Liquidsoap Is the Wrong Engine for Windows

Liquidsoap is LibreTime's core playout engine. It handles scheduled playback,
queue management, stream encoding, and fallback behavior. Liquidsoap assumes:

- A Linux audio stack (ALSA or PortAudio in Linux configuration)
- A Linux process lifecycle (started and monitored via systemd)
- A UNIX-style inter-process communication model

Liquidsoap can be installed on Windows, but it is not a supported or reliable
deployment target for production use. Its Windows behavior is untested by the
upstream project. Debugging audio routing on Windows via Liquidsoap's
configuration language (`.liq` scripts) is not practical for a studio operator.

**Decision:** Replace Liquidsoap with libVLC as the main playout engine.
See ADR-002.

### 2. The Service Layer Is Linux-Specific

LibreTime assumes `systemd` for:
- automatic startup after boot
- restart-on-crash for each service
- dependency ordering between services (database → worker → playout → API)
- log routing via journald

`systemd` does not exist on Windows. Windows service management requires
either the Windows Service Control Manager (SCM) directly, or a wrapper tool.
Translating each `systemd` unit file to a Windows service definition is
mechanical but requires a different toolset.

**Decision:** Use NSSM as a service wrapper for all persistent processes.
See ADR-005.

### 3. The Worker Runtime Has Windows Incompatibilities

LibreTime uses Celery with a process-based worker model (prefork pool by
default). Python's `multiprocessing` module — which underpins Celery's prefork
pool — has significant behavioral differences on Windows compared to Linux:

- `fork()` is not available on Windows; `spawn()` is used instead.
- `spawn()` requires all top-level code to be guarded by `if __name__ == "__main__"`.
- Celery's default worker concurrency mode (prefork) is not recommended on Windows
  and requires explicit fallback to `solo` or `eventlet`/`gevent` modes.
- Beat scheduling (celerybeat) has known reliability issues on Windows.

Running Celery on Windows is possible but is explicitly marked as
"not recommended for production" in Celery's own documentation.

**Decision:** Replace Celery with a Windows-native background runner.
See IMPLEMENTATION_PLAN.md Phase 8 (T16.1–T16.3).

### 4. The Web Serving Layer Has Unix Assumptions

LibreTime uses Gunicorn as its WSGI server. Gunicorn is a Unix-only tool:
its worker model depends on `fork()`. It does not run on Windows at all.
The standard deployment places Gunicorn behind nginx, which is available
on Windows but is not natively integrated with Windows service management.

**Decision:** Replace Gunicorn with a Windows-compatible WSGI server
(e.g. Waitress). Reverse proxy is optional. See Phase 9 (T17.1–T17.2).

### 5. Linux Filesystem Paths Are Hardcoded Throughout

LibreTime references Linux paths in many places:
- Configuration defaults: `/etc/libretime/`, `/etc/airtime/`
- Log paths: `/var/log/libretime/`
- Media storage: `/srv/airtime/`
- Installed files: `/usr/share/airtime/`

These paths are not valid on Windows. They appear in Python config defaults,
shell scripts, installer logic, and documentation. Running LibreTime on Windows
without addressing these would cause failures at startup and at every
path-dependent operation.

**Decision:** Abstract all path handling through a central configuration layer.
Linux-specific paths are classified as technical debt in T1.1.

### 6. Audio I/O Is Platform-Specific

LibreTime's audio backend assumptions (ALSA on Linux, optionally PortAudio)
do not translate to Windows. Windows audio uses WASAPI (Windows Audio Session
API) or DirectSound. libVLC handles this abstraction internally, making it the
right layer to own all audio I/O decisions on Windows.

Local soundcard output and local line-in sources (new RASTATIME features) are
inherently platform-specific and require Windows-native device enumeration.

**Decision:** All audio I/O goes through libVLC's Windows audio modules.
A new Soundcard abstraction layer handles device enumeration and mapping.
See Phase 7 (T12.1–T15.2) and ADR-002.

---

## What Is Preserved

The functional fork approach does **not** mean rebuilding everything from scratch.
The following LibreTime components are largely preserved:

| Component | Preservation approach |
|---|---|
| PostgreSQL database | Kept as-is; runs on Windows |
| Django / Python API layer | Kept and refactored; Linux assumptions removed |
| Domain model (shows, schedule, playlists, media, history) | Preserved semantically |
| Calendar and scheduling logic | Preserved |
| Webstreams concept | Preserved |
| Podcast ingestion model | Preserved |
| User/auth model | Preserved (reviewed for Windows-specific adjustments) |
| Media library concepts | Preserved |
| History and reporting | Preserved; rebind to new event sources |
| RabbitMQ (broker) | Conditionally preserved if still beneficial |

---

## What This Means in Practice

The correct mental model for RASTATIME is:

> Take LibreTime's **product behavior** and **operator workflows**.  
> Run them on a **new runtime substrate** that works on Windows 11.  
> Extend the product with **Windows-first features** that LibreTime lacks
> (local Line-In sources, Soundcard settings).

This is not a rewrite. The domain logic, scheduling semantics, and user-facing
workflows remain the LibreTime baseline. The execution environment underneath
them is replaced where necessary.

---

## Summary of Replacement Decisions

| LibreTime component | Problem on Windows | RASTATIME decision |
|---|---|---|
| Liquidsoap | Not production-viable on Windows | Replace with libVLC (ADR-002) |
| systemd / systemctl | Does not exist on Windows | Replace with NSSM (ADR-005) |
| Celery (prefork) | Fork-based model unreliable on Windows | Replace with Windows-native runner |
| Gunicorn | Unix-only; no Windows support | Replace with Waitress or equivalent |
| Linux filesystem paths | Invalid on Windows | Abstract via config layer |
| ALSA/PortAudio audio backend | Linux-specific | Replace with libVLC Windows audio modules |
| Linux installer scripts | Not applicable on Windows | Replace with PowerShell bootstrap + NSSM scripts |
