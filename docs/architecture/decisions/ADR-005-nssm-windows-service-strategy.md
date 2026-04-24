# ADR-005 — NSSM as the First Windows Service Strategy

**Status:** Accepted  
**Date:** 2026-04-24  
**Deciders:** RASTATIME project

---

## Context

LibreTime uses `systemd` units to manage service lifecycle on Linux: automatic
startup after reboot, restart on crash, dependency ordering, and log routing.
`systemd` is not available on Windows.

RASTATIME must start automatically after a Windows 11 reboot and recover from
process crashes without manual operator intervention. The solution must be:
- usable without writing a custom Windows service in C/C++,
- scriptable (install/uninstall via PowerShell),
- capable of managing arbitrary executables (Python, Node, binaries),
- able to define restart behavior and log routing,
- freely available.

Candidates considered:
- **NSSM** (Non-Sucking Service Manager): wraps any executable as a Windows
  service; scriptable; widely used; free.
- **WinSW** (Windows Service Wrapper): XML-configured; requires .NET.
- **SC.exe** (Windows built-in): low-level; no restart-on-crash without
  additional configuration; harder to script cleanly.
- **Task Scheduler**: not a service manager; not suitable for persistent
  background processes.

## Decision

**NSSM is the service wrapper for phase 1.**

Each RASTATIME runtime process that must run persistently is registered as
a Windows service via NSSM. Candidate services (final list in T21.1):
- web/API server
- background runner (worker)
- playout runtime
- optional: Icecast stream server (if adopted per ADR-003)
- optional: RabbitMQ broker (if retained)

NSSM service definitions are managed via PowerShell scripts in `infra/nssm/`.
Scripts cover: install, remove, status/health check.

**This decision covers phase 1 only.** If NSSM proves insufficient (e.g. for
MSI packaging, enterprise deployment, or signed service requirements), it may
be replaced in a later phase — but a replacement requires a new ADR.

## Consequences

**Positive:**
- Any executable (Python script, binary) can be wrapped without code changes.
- Restart-on-crash is built in and configurable per service.
- Install and remove are scriptable — reproducible setup.
- No .NET dependency; NSSM is a standalone executable.

**Negative / Trade-offs:**
- NSSM must be downloaded and installed separately (not a Windows inbox tool).
- NSSM is not a Microsoft-signed tool; some enterprise environments may block it.
  This is acceptable for a studio PC deployment in phase 1.
- Dependency ordering between services requires scripted startup sequencing,
  not declarative unit files as in systemd.

**Deployment requirement:**
- NSSM executable must be present on the target machine before running service
  install scripts. Bootstrap script (T3.1) must check for NSSM presence.

**Follow-up required:**
- T21.1: define the final service split (which processes become services).
- T22.1–T22.3: create NSSM install, remove, and status scripts.
- T3.1: add NSSM presence check to `bootstrap.ps1`.
