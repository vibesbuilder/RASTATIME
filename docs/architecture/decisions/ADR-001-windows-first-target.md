# ADR-001 — Windows 11 as Primary Runtime Target

**Status:** Accepted  
**Date:** 2026-04-24  
**Deciders:** RASTATIME project

---

## Context

LibreTime is designed and deployed as a Linux-native application. Its installer,
service lifecycle, filesystem paths, and audio backend all assume a Linux
environment. A studio machine running Windows 11 cannot run LibreTime as-is.

The target deployment is a **Windows 11 studio PC** operated by a radio station.
The operator uses Windows for all other studio software (DAW, playout hardware
drivers, monitoring tools). Requiring a Linux VM or dual-boot is not acceptable
as a primary deployment model.

## Decision

**RASTATIME targets Windows 11 as its primary and only supported runtime in phase 1.**

All implementation decisions must be valid for Windows 11 first. Linux
compatibility is not a design constraint. Cross-platform elegance is not an
optimization target if it conflicts with Windows-first delivery.

Specifically:
- No dependency on `systemd`, `systemctl`, or Linux-only service tooling.
- No Linux-only filesystem path conventions (`/etc`, `/var`, `/srv`, `/usr`).
- No Linux-only shell scripts as the primary runtime mechanism.
- Windows-native service management (see ADR-005).
- Windows-native audio I/O (see ADR-002).
- Windows-compatible web serving and worker execution.

## Consequences

**Positive:**
- Clear platform scope — no ambiguity about which environment to test.
- Studio operators can install directly on their existing Windows 11 machine.
- Audio hardware driver support is native to the platform.

**Negative / Trade-offs:**
- Linux deployment is not supported in phase 1.
- Contributors working on Linux must use a Windows VM for runtime testing.
- Some LibreTime code paths require rewriting rather than porting.

**Follow-up required:**
- All Linux-specific code paths must be inventoried (T1.1) and classified for
  replacement, isolation, or deletion.
- Linux-only installer/deployment scripts are preserved in `infra/upstream/`
  as reference only.
