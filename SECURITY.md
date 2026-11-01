# Security Policy

RASTATIME is a Windows-first radio automation system that is normally run
by one operator on one studio machine, with the web interface and the
stream exposed through a reverse proxy.  Reports about anything that
lets a listener, a DJ or an unauthenticated visitor do more than they
should are welcome.

## Supported versions

| Version | Supported |
|---------|-----------|
| `master` (latest release tag `v*`) | yes |
| anything older | no — update first, see `docs/operator/UPGRADE.md` |

Before the first `v1.0.0` release every fix lands on `master` only.

## Reporting a vulnerability

Please **do not open a public issue** for a security problem.

Use GitHub's private vulnerability reporting on this repository
(**Security → Report a vulnerability**).  The report reaches the
maintainer only.  Include:

- the affected component (web interface, API, playout/Liquidsoap,
  analyzer, Icecast/stream, installer scripts) and the commit or release,
- what an attacker can do and from where (listener, DJ account, LAN,
  unauthenticated),
- steps to reproduce; a log excerpt helps, with passwords and API keys
  removed.

You will get an acknowledgement within seven days.  Fixes are published
as a normal commit on `master` with a `### Security` entry in
`CHANGELOG.md`; the report is credited there if you wish.

## What is in scope

- Authentication and roles of the web interface and the REST/v2 API
  (`docs/operator/ROLE_AUDIT_2026-10.md` describes the model).
- DJ login (Liquidsoap harbor → playout → web application) and the
  local-only endpoints behind it.
- Everything a listener can reach through the reverse proxy
  (`/stream/`, widgets, embeds).
- Default settings and installer scripts under `infra/` that would leave a
  fresh installation exposed.

Out of scope: upstream components that are installed separately (Apache,
PHP, PostgreSQL, RabbitMQ, Icecast, Liquidsoap, ffmpeg, Stereo Tool) —
report those to their projects; `docs/operator/COMPONENTS.md` explains
how RASTATIME tracks their updates.

## Hardening guides for operators

- `docs/operator/WINDOWS_24_7.md` — Windows hardening for a 24/7 machine
- `docs/operator/GO_LIVE_HTTPS.md` — HTTPS, reverse proxy, what is exposed
- `docs/operator/PASSWORD_ROTATION.md` — rotating every secret
- `docs/operator/TEST_PLAN.md` §A5 — brute-force protection checks
- `config/rastatime.conf.example` and `config/icecast.xml.example` —
  every placeholder secret must be replaced before the first start
