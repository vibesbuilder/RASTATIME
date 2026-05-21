# ADR-006 — No Mandatory Reverse Proxy for Phase 1

**Status:** Accepted  
**Date:** 2026-04-29  
**Deciders:** RASTATIME project  
**Relates to:** ADR-005 (NSSM service strategy), T17.1 (Waitress), T17.2

---

## Context

LibreTime's upstream deployment model uses **nginx** as a reverse proxy in
front of **gunicorn** (the WSGI application server).  nginx handles TLS
termination, static file serving, and request buffering.

RASTATIME has replaced gunicorn with **Waitress** (T17.1) — a pure-Python,
Windows-compatible WSGI server that listens directly on a TCP port.  The
question is: must a reverse proxy sit in front of Waitress in RASTATIME's
phase-1 deployment topology?

### Constraints

1. **Windows-first** — nginx has no official Windows binary for production
   use.  The community build is available but unsupported and not recommended
   for long-running services by the nginx project itself.
2. **Studio PC target** — the initial deployment target is a broadcast studio
   PC on a local network, not a publicly-exposed internet server.
3. **Minimal dependencies** — every additional process (nginx, IIS, Caddy)
   increases setup complexity, NSSM service count, and failure surface.
4. **NSSM lifecycle** — NSSM wraps Waitress as a single Windows service.
   Adding a reverse proxy means a second NSSM-managed service with startup
   ordering concerns.

### Options considered

| Option | TLS | Windows support | Complexity | Verdict |
|--------|-----|-----------------|------------|---------|
| **No proxy** — Waitress direct on `127.0.0.1:8000` | None (HTTP only) | Native | Minimal | ✅ Phase 1 |
| **IIS with ARR** (Application Request Routing) | Yes (via IIS cert) | Native | Medium — requires IIS feature install; complex XML config | Optional later |
| **Caddy** (Windows binary) | Yes (auto-ACME) | Good — signed binary, NSSM-friendly | Low — single binary; declarative Caddyfile | Recommended if TLS needed |
| **nginx** (community Windows build) | Yes | Poor — unsupported; known threading issues on Windows | Medium | Not recommended |
| **stunnel** in front of Waitress | Yes (TLS only) | OK | Low but limited | Not recommended |

---

## Decision

**RASTATIME phase 1 ships without a mandatory reverse proxy.**

Waitress binds to `127.0.0.1:8000` by default.  The API is accessed directly
over HTTP on the local machine or local network.

This decision is appropriate because:

1. **Studio-PC deployment** — the RASTATIME API is an internal service
   consumed by the web UI (served from the same machine) and by the playout
   and worker processes.  It is not a public internet service in phase 1.
2. **No TLS requirement in phase 1** — traffic stays on localhost or on a
   trusted studio LAN.  If TLS is later required (e.g., for a multi-room
   setup over a corporate WLAN), Caddy can be added as an optional component
   without architectural change.
3. **Waitress is production-safe** — Waitress has been used in production
   deployments for over a decade.  It handles keep-alive, pipelining, and
   chunked transfer encoding correctly.  Request buffering (protection against
   slow-client attacks) is built in.
4. **Simplest NSSM topology** — one Waitress service; no startup ordering
   between proxy and application.

### Binding recommendation

| Mode | Host | Rationale |
|------|------|-----------|
| Development | `127.0.0.1` | Localhost only; no network exposure |
| Single-machine production | `127.0.0.1` | Keeps API off the network; UI served from same host |
| LAN production (multi-client) | `0.0.0.0` | All interfaces; requires firewall rule to restrict access |

### If TLS is later required

**Caddy** is the recommended optional addition:

```
caddy reverse-proxy --from https://rastatime.local --to http://localhost:8000
```

- Caddy is a single signed executable for Windows.
- It supports automatic TLS via ACME (Let's Encrypt or internal CA).
- It wraps cleanly as an NSSM service.
- No changes to RASTATIME's Django or Waitress configuration are required.

A future ADR should document this if TLS is adopted.

---

## Consequences

**Positive:**
- Zero additional runtime dependencies for phase 1.
- Single NSSM service for the API; no startup dependency ordering.
- Operator setup is simpler: install Python, install deps, register one service.
- Consistent with the "minimal Windows footprint" principle from ADR-001.

**Negative / Trade-offs:**
- No TLS in phase 1 — acceptable for localhost and trusted-LAN deployments.
- Waitress serves static files through Django's `STATIC_URL` path, which is
  less efficient than nginx's `sendfile` — acceptable for internal studio use
  (low static file volume).
- Waitress does not support HTTP/2 — acceptable for the current API consumer
  set (Django UI, Python clients).

**Not in scope for this ADR:**
- Public internet deployment (requires TLS + appropriate security hardening).
- High-availability clustering (requires a load balancer in front of multiple
  Waitress instances).
- WebSocket support (not currently used; ASGI + Hypercorn would be needed).

---

## Follow-up required

- T22.1: NSSM install script for `rastatime-api` service wrapping Waitress.
- T23.1: Operator install guide must document the Waitress service, the
  binding address recommendation, and the optional Caddy upgrade path.
- Future ADR: if TLS or WebSockets become a requirement, document the chosen
  solution (Caddy or Hypercorn migration).
