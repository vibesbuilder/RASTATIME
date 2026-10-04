# GO_LIVE_HTTPS.md — Internet Reachability via HTTPS (Way A)

**Status:** In progress (operator decision 2026-10-04, BACKLOG "Internet-
Erreichbarkeit via HTTPS — Weg A")
**Date:** 2026-10-04
**Goal:** `https://rastatime.example.org` serves the planner UI and the
listener stream from the studio machine itself (fixed public IP); the DJ
dial-in stays plain HTTP on port 8001 (operator decision).

The stages build on each other.  **Nothing is forwarded on the router
before stage 0 is complete.**  Commands marked *elevated* run in a
PowerShell started "as administrator"; everything that changes a secret
or a system setting is done by the operator, assistant verifies read-only.

---

## Stage 0 — Prerequisites (secrets, binds, firewall)

### 0.1 Inventory (2026-10-04, values never printed)

| Secret | Where it lives | Found | Action |
|---|---|---|---|
| UI account `admin` (type A) | `cc_subjs` | **default password** | change in the UI (Settings → Users) or disable; `opuser` is the second admin |
| Database `rastatime` | PostgreSQL role + `libretime.conf` `database.password` | **example default** | rotate (0.2) |
| RabbitMQ user `rastatime` | broker + `libretime.conf` `rabbitmq.password` | **example default**; `guest` (administrator) still exists | rotate, delete `guest` (0.3) |
| Icecast source / relay / admin | `config/icecast.xml` + Settings → Streams outputs 1–3 (`pass`, `admin_pass`) + rendered `rastatime.liq` / `standby.liq` + Line-In capture | **5-character defaults** | rotate (0.4) |
| Harbor fallback passwords | `libretime.conf` `stream.harbor.main_password` / `show_password` (only used while PLAYOUT is unreachable) | **8-character default** | rotate (0.4) |
| `general.api_key`, `general.secret_key` | `libretime.conf` | custom (42 / 62 chars) | keep |
| `stream.internal_listener` | `libretime.conf` | custom | keep |
| Master Source password (Settings → Streams) | `cc_pref live_stream_master_password` | custom | keep (username is short — fine) |

Code change that belongs to this stage (`backend/playout`): the Line-In
capture (`/linein-capture` mount) used a hard-coded `source`/`admin`; it
now takes the local Icecast's source credentials from the first enabled
local stream output (Settings → Streams), so rotating the Icecast password
needs no code edit.  Active after the next PLAYOUT restart.

### 0.2 Database password

Quiet window (the services lose the database for a few seconds).

1. New password (long, random; letters and digits are enough — no `'`,
   `\`, and nothing that YAML reads as syntax at the start: `!`, `&`, `*`,
   `%`, `@`, `` ` ``, `#`, `{`, `[`).  **Always write the value in double
   quotes in `libretime.conf`** (`password: "…"`); an unquoted `!…` broke
   the whole file on 2026-10-04 (every service down, the value echoed into
   two log files by the YAML parser).
2. As PostgreSQL superuser (pgAdmin or `psql -U postgres`):
   ```sql
   ALTER USER rastatime WITH PASSWORD '<new>';
   ```
   The role may change its own password — no superuser needed:
   `psql -h localhost -U rastatime -d rastatime -c "ALTER USER rastatime WITH PASSWORD '<new>';"`
   (prompts for the current one from `libretime.conf`).
3. `config/libretime.conf` → `database.password: "<new>"` — quoted (the
   legacy PHP reads the file on every request — no Apache restart).  If a
   service ends up *Paused* after failed starts, use
   `nssm restart <service>` instead of `Restart-Service`.
4. In the same window, bind PostgreSQL to localhost — 0.5 — then restart
   `postgresql-x64-17`, afterwards `RASTATIME-API`, `RASTATIME-PLAYOUT`,
   `RASTATIME-WORKER`, `RASTATIME-ANALYZER` (elevated):
   ```powershell
   Restart-Service postgresql-x64-17
   Restart-Service RASTATIME-API, RASTATIME-WORKER, RASTATIME-ANALYZER
   Restart-Service RASTATIME-PLAYOUT
   ```
5. Check: UI loads, `logs/playout-stdout.log` shows `Health gate: API
   healthy`, no `password authentication failed` in `logs/api-stderr.log`.

### 0.3 RabbitMQ

```powershell
# elevated; sbin of the installed server version
cd "C:\Program Files\RabbitMQ Server\rabbitmq_server-*\sbin"
.\rabbitmqctl.bat change_password rastatime "<new>"
.\rabbitmqctl.bat delete_user guest
```
Then `config/libretime.conf` → `rabbitmq.password: <new>` and restart
`RASTATIME-API`, `RASTATIME-PLAYOUT`, `RASTATIME-WORKER`,
`RASTATIME-ANALYZER`.  Check: uploading a file still gets analysed
(`logs/analyzer-stdout.log`), a schedule change reaches the playout
(`PushSchedule` → `refreshing schedule`).

### 0.4 Icecast and harbor passwords

Off-air for ~30–60 s (Icecast and Liquidsoap restart) — quiet window.

1. New source password, new admin password (relay = source is fine).
2. `config/icecast.xml`: `<source-password>`, `<relay-password>`,
   `<admin-password>`, `<master-password>`.
3. UI → Settings → Streams → outputs 1–3: *Password* = new source
   password, *Admin password* = new admin password; Save.
4. `config/libretime.conf` → `stream.harbor.main_password` /
   `show_password`: new random values (these only count as fallback).
5. Restart in this order (elevated):
   ```powershell
   Restart-Service RASTATIME-ICECAST
   Restart-Service RASTATIME-PLAYOUT      # re-renders rastatime.liq + standby.liq, restarts LIQUIDSOAP itself when the .liq changed
   Restart-Service RASTATIME-STANDBY
   ```
6. Check: `logs/playout-stdout.log` → `Liquidsoap config ... changed`
   and a Liquidsoap restart; Icecast status page lists the three mounts
   with the standby fallbacks; `logs/liquidsoap-stdout.log` has no
   `401`/`Unauthorized`; a Line-In show (or `ffmpeg_linein_capture`
   health check) still mounts `/linein-capture`; listener stats keep
   arriving (`history.stats`, admin password).

### 0.5 Bind the internal services to localhost

- **PostgreSQL** — `C:\Program Files\PostgreSQL\17\data\postgresql.conf`:
  `listen_addresses = 'localhost'` (pg_hba already allows only
  127.0.0.1/::1; this closes the socket itself).  Restart with 0.2.
- **RabbitMQ** — create `C:\ProgramData\RabbitMQ\rabbitmq.conf`:
  ```
  listeners.tcp.default = 127.0.0.1:5672
  ```
  Restart the `RabbitMQ` service; verify with
  `rabbitmq-diagnostics listeners` (AMQP must show `127.0.0.1` only).  If
  the file is ignored (`rabbitmq-diagnostics status` → "Config files"
  empty), set the system environment variable
  `RABBITMQ_CONFIG_FILE=C:\ProgramData\RabbitMQ\rabbitmq.conf` and run
  `rabbitmq-service.bat reinstall`.
- **Django API** — the UI reaches it through Apache (`/api/v2`,
  `/api-auth`) and the legacy PHP through `localhost:8765`; nothing on the
  LAN needs the port directly.  Elevated:
  ```powershell
  $nssm = "C:\Tools\nssm\nssm.exe"   # adjust to the nssm.exe path
  & $nssm set RASTATIME-API AppParameters "-m libretime_api.waitress_serve --host 127.0.0.1 --port 8765 --threads 8"
  & $nssm set RASTATIME-API AppEnvironmentExtra "DJANGO_SETTINGS_MODULE=libretime_api.settings.prod" "LIBRETIME_CONFIG_FILEPATH=C:\rastatime\config\libretime.conf" "RASTATIME_API_HOST=127.0.0.1" "RASTATIME_API_PORT=8765" "RASTATIME_API_THREADS=8" "PYTHONPATH=C:\rastatime\backend\api;C:\rastatime\backend\shared;C:\rastatime"
  Restart-Service RASTATIME-API
  ```
  Verify: `netstat -an | findstr 8765` shows `127.0.0.1:8765` only; the
  Library, Line-In and Local Machine pages still work.
- Already local: Liquidsoap telnet `127.0.0.1:1234`, playout listener
  `127.0.0.1:8770`.

### 0.6 Windows Firewall (elevated)

Inbound rules today: explicit `RASTATIME Web HTTP` (80), `RASTATIME Web
HTTPS` (443), `RASTATIME DJ Harbor Master` (8001), `RASTATIME DJ Harbor
Show` (8002, obsolete — both harbors are on 8001), program rules "any
port" for Apache, Erlang, epmd and two liquidsoap builds (one in
`C:\temp\liq245`, stale).  Tidy up:
```powershell
Remove-NetFirewallRule -DisplayName "RASTATIME DJ Harbor Show"
Get-NetFirewallRule -DisplayName "Erlang","epmd" | Remove-NetFirewallRule
Get-NetFirewallRule -DisplayName "liquidsoap" | Where-Object { ($_ | Get-NetFirewallApplicationFilter).Program -like "C:\temp\*" } | Remove-NetFirewallRule
```
Keep: 80, 443, 8001, the Apache program rule, the `C:\tools\liquidsoap`
rule (harbor).  Icecast 8000 has no inbound rule — in-house listeners
get the stream through Apache from stage 1 on.

### 0.7 Verification (assistant, read-only)

`netstat -an` listeners: 5432, 5672, 8765 on 127.0.0.1 only; secrets
re-classified as custom (same script as the inventory, values hidden);
`guest` gone from `rabbitmqctl list_users`; the `admin` row in `cc_subjs`
no longer matches `md5('admin')`; one Line-In show mounts
`/linein-capture` with the new password; firewall rule list.

---

## Stage 1 — Code (RASTATIME)

- `general.public_url` → `https://rastatime.example.org`; playout,
  analyzer and worker get an internal base (`http://127.0.0.1`) for the
  legacy v1 API and the DJ-auth check (`RASTATIME_DJ_AUTH_WEB_URL`
  exists; the v1 client needs the same split).
- Django `ALLOWED_HOSTS` = hostname, `192.168.1.164`, `localhost`;
  `CSRF_TRUSTED_ORIGINS` = the HTTPS origin.
- Apache terminates TLS itself, so PHP sees `HTTPS` natively (secure
  cookies); add HTTP→HTTPS redirect and HSTS.
- Stream proxy `/stream/<mount>` → `http://127.0.0.1:8000/<mount>`
  (no buffering, ICY headers through); widgets / embed codes / the
  player use the HTTPS stream URL.

## Stage 2 — Infrastructure (operator)

DNS A record → fixed public IP; router forwards TCP 80, 443 → 192.168.1.164
and TCP 8001 (DJ dial-in, plain); `win-acme` as a service (Let's Encrypt,
HTTP-01 on port 80, auto-renewal); Apache `httpd-ssl.conf` (assistant
provides it); hairpin NAT or split DNS so the public name also works in
the LAN.

## Stage 3 — Acceptance from outside

From a mobile network: UI login, the three stream mounts, BUTT dial-in on
`rastatime.example.org:8001`, widgets on the station website, HTTP→HTTPS
redirect, HSTS header, SSL Labs grade, and the public name from inside
the LAN.
