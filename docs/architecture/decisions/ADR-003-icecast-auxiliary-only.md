# ADR-003 — Icecast as Optional Auxiliary Stream Layer Only

**Status:** Accepted  
**Date:** 2026-04-24  
**Deciders:** RASTATIME project

---

## Context

LibreTime uses Liquidsoap as both the playout engine and the stream encoder/
dispatcher. Liquidsoap feeds Icecast for public stream output. Since Liquidsoap
is being replaced (ADR-002), the stream dispatch role must be re-evaluated.

Two components can handle streaming in RASTATIME:
1. **libVLC** — can encode and push streams directly (Shoutcast/Icecast sinks
   via `sout` modules).
2. **Icecast** — a dedicated streaming server, handles multiple mounts,
   listener management, relay, and metadata propagation.

The risk of making Icecast mandatory is that it adds an additional process
to manage on Windows, with its own startup, crash recovery, and configuration.
The risk of excluding Icecast entirely is that libVLC's streaming reliability
for multi-mount or relay scenarios is unproven at the time of this decision.

## Decision

**Icecast is optional and auxiliary. libVLC is always the primary playout authority.**

Icecast may be introduced if and only if a specific streaming use case cannot
be satisfied reliably by libVLC alone. Qualifying use cases include:
- outgoing public internet streams requiring multiple simultaneous mounts,
- relay / mount-based streaming for compatibility with legacy contribution tools,
- incoming remote live contributions that are more stable via Icecast ingress,
- scenarios where operational separation between playout and public delivery
  is required.

Even when Icecast is present:
- Icecast is a downstream consumer of libVLC's audio output, not a replacement.
- Playout scheduling and queue control remain with libVLC.
- Icecast does not have authority over what plays — it only receives and relays.

The decision of whether to use Icecast for a given stream scenario is deferred
to Phase 6 (T9.1–T9.2), after empirical testing of libVLC stream capabilities.

## Consequences

**Positive:**
- Minimal initial complexity — no mandatory Icecast process in phase 1.
- Icecast can be added per-deployment if needed without changing the core.
- libVLC handles the common studio-to-stream case without extra processes.

**Negative / Trade-offs:**
- If libVLC streaming proves insufficient (reliability, metadata, multi-mount),
  Icecast integration work becomes required rather than optional.
- Icecast on Windows requires its own NSSM service definition (T22.1).

**Follow-up required:**
- T9.1–T9.2: stream capability matrix — test libVLC against all stream use cases,
  classify which require Icecast.
- T10.4: implement Icecast-backed output only if T9.2 shows it is needed.
