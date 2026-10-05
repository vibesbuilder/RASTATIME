# GO_LIVE_HTTPS.md — Internet Reachability via HTTPS (Way A)

**Status:** In progress (operator decision 2026-10-04, BACKLOG "Internet-
Erreichbarkeit via HTTPS — Weg A")
**Date:** 2026-10-04
**Goal:** `https://radio.example.org` serves the planner UI and the
listener stream from the studio machine itself (fixed public IP); the DJ
dial-in stays plain HTTP on port 8001 (operator decision).

The stages build on each other.  **Nothing is forwarded on the router
before stage 0 is complete.**  Commands marked *elevated* run in a
PowerShell started "as administrator"; everything that changes a secret
or a system setting is done by the operator, assistant verifies read-only.

---

## Stage 0 — Prerequisites (secrets, binds, firewall) — DONE 2026-10-04 17:40

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
5. Restart in this order (elevated), **not while an item is on air** —
   the playout defers the Liquidsoap restart to the next file-to-file
   boundary while something plays, and until then the main instance
   knocks at Icecast with the old password (`401`, public mounts empty):
   ```powershell
   Restart-Service RASTATIME-ICECAST -Force          # STANDBY depends on it and restarts with it
   & "C:\Tools\nssm\nssm.exe" restart RASTATIME-PLAYOUT      # re-renders rastatime.liq + standby.liq
   & "C:\Tools\nssm\nssm.exe" restart RASTATIME-LIQUIDSOAP   # apply now (nssm prints "Unexpected status SERVICE_START_PENDING" - harmless, the service is up)
   Restart-Service RASTATIME-STANDBY
   ```
   Off-air from the Icecast restart until the main instance reconnects
   (2026-10-04: 17:12:54 → 17:15:52, prolonged by a running webstream
   slot; ~40 s when done in a quiet moment).
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

## Stage 1 — Code (RASTATIME) — DONE 2026-10-04

Built and committed (see CHANGELOG "Go-Live Stufe 1"); nothing of it
changes behaviour until stage 2 sets `public_url`, except the listener
URL and the two Apache includes below.

- **`general.internal_url`** (new, optional, all three config schemas):
  the address the backend services use to call the legacy web app on
  this machine.  Fallback chain `RASTATIME_INTERNAL_URL` (environment) >
  `general.internal_url` > `http://127.0.0.1` + path of `public_url`.
  Used by the playout (legacy v1 client = "On Air" light, DJ login
  check), the analyzer (import callback) and the notify/legacy entry
  points.  `public_url` is the outside face only.
- **Listener URL** `<public_url>/stream/<mount>` for outputs on the local
  Icecast (`StreamSetting`); player, widgets, embed codes follow.
  Apache must hand `/stream/` to Icecast - include
  `infra/apache/rastatime-stream-proxy.conf` **now** in `httpd.conf`
  (after the existing ProxyPass lines) and restart Apache; until then the
  in-UI player and the widgets point at a 404.
- **ACME challenge directory** `infra/apache/rastatime-acme.conf`
  (Alias `/.well-known/acme-challenge/` → `C:\RASTATIME\acme`, rewrite
  off) - include it now as well, create `C:\RASTATIME\acme`; win-acme
  (stage 2) validates through it.
- **TLS virtual host** `infra/apache/rastatime-https.conf` (443, TLS 1.2/
  1.3, HTTP/2, HSTS, `X-Forwarded-Proto`, the same proxies, http → https
  redirect for the public name only, LAN by IP untouched).  Include it in
  stage 2 once the certificate files exist (`C:\RASTATIME\certs\
  radio.example.org-chain.pem` / `-key.pem`) and `mod_ssl`,
  `mod_socache_shmcb`, `mod_http2` are loaded.
- **Django**: `ALLOWED_HOSTS` = public host, internal host, localhost,
  127.0.0.1, `[::1]` (+ `RASTATIME_API_EXTRA_HOSTS`); `CSRF_TRUSTED_ORIGINS`
  = public origin (+ allowed CORS origins); `SECURE_PROXY_SSL_HEADER`,
  `USE_X_FORWARDED_HOST`.  Fixed on the way: the upstream CORS origin was
  cut one character short (`http://192.168.1.16`).
- Legacy PHP: Apache terminates TLS natively, so `$_SERVER['HTTPS']` and
  the secure session cookie just work; nothing to change.

Operator actions for stage 1: add the two `Include` lines, create
`C:\RASTATIME\acme`, restart `RASTATIME-APACHE`, restart
`RASTATIME-PLAYOUT` and `RASTATIME-ANALYZER` (internal URL), then check
`http://192.168.1.64/stream/rastatime` plays and the dashboard player works.

## Stage 2 — Infrastructure (operator)

Stage 1 is active since 2026-10-05 09:30 (`/stream/` proxy and ACME alias
included, verified).  Order matters: the certificate needs DNS and port
80 first, `public_url` is switched last.

### 2.0 Decisions of 2026-10-05 (public IP shared with the NAS)

- The studio's public IP already serves `cloud.example.org` (Synology
  NAS: DSM on 443, the live-studio webstream on 3001, VNC forwards to
  PCs).  Nobody needs the NAS from outside any more, the webstream
  becomes a Line-In → the router forwards **80/443 to the NAS are
  removed**; 80, 443 and 8001 go to RASTATIME (192.168.1.64).  The VNC
  forwards stay as they are.
- NAS certificate without ports 80/443: either none (DSM in the LAN
  with its self-signed one) or Synology DDNS (`xyz.synology.me`, DSM
  fetches the certificate without open ports); DNS-01 via `acme.sh`
  (world4you module, portal scraping) only as a last resort.
- Public name **`radio.example.org`** (A record, not a CNAME to
  `cloud.…`, no AAAA).  The Synology-as-reverse-proxy variant was
  evaluated and rejected by the operator (no dependency on another
  device); the PC-as-proxy-for-the-NAS variant likewise.
- Plan B if the machine ever has to sit behind another TLS proxy: the
  proxy terminates TLS and forwards to `http://192.168.1.64:80`; Apache
  then needs only `SetEnvIf X-Forwarded-Proto https HTTPS=on` +
  `mod_remoteip`, `public_url` stays.

### 2.1 DNS and router

1. A record `radio.example.org` → the studio's fixed public IP
   (TTL 300 while testing).  Check from outside: `nslookup
   radio.example.org 8.8.8.8`.
2. Router port forwards (TCP) to 192.168.1.64: **80** (ACME + redirect),
   **443** (UI + streams), **8001** (DJ dial-in, plain HTTP by decision).
   Nothing else - not 8000, not 8765, not 5900.
3. **Hairpin NAT / split DNS test** (decides 2.4): from a LAN machine open
   `http://radio.example.org/` - if it shows the RASTATIME login,
   the router hairpins and the LAN can use the public name.  If not,
   add a local DNS override (Fritz!Box/pfSense "host override":
   `radio.example.org` → 192.168.1.64) - after 2.4 every stream URL
   carries the public name, also for in-house listeners and the UI
   player.

### 2.2 Apache modules (elevated editor on httpd.conf)

Uncomment / add in `C:\Tools\Apache24\conf\httpd.conf`:
```
LoadModule ssl_module modules/mod_ssl.so
LoadModule socache_shmcb_module modules/mod_socache_shmcb.so
LoadModule http2_module modules/mod_http2.so
```
(`mod_headers`, `mod_rewrite`, `mod_proxy`, `mod_proxy_http` are already
loaded.)  Do **not** include `rastatime-https.conf` yet - it references
the certificate files.  `httpd.exe -t`, `Restart-Service RASTATIME-APACHE`.

### 2.3 Certificate with win-acme

1. Download the latest win-acme (x64, pluggable) from
   <https://www.win-acme.com/> to `C:\Tools\win-acme\`.
2. Create `C:\RASTATIME\certs`.
3. Elevated PowerShell - one command, registers the renewal task as well:
   ```powershell
   cd C:\Tools\win-acme
   .\wacs.exe --source manual --host radio.example.org `
     --validation filesystem --webroot C:\RASTATIME\acme `
     --store pemfiles --pemfilespath C:\RASTATIME\certs `
     --installation script --script "powershell.exe" `
     --scriptparameters "-NoProfile -ExecutionPolicy Bypass -File C:\RASTATIME\infra\scripts\apache-cert-renewed.ps1" `
     --accepttos --emailaddress technik@example.org
   ```
   Result: `C:\RASTATIME\certs\radio.example.org-chain.pem` and
   `-key.pem` (plus `-crt.pem`, `-chain-only.pem`), a scheduled task
   "win-acme renew" that renews ~every 60 days and runs the restart
   script (`logs\cert-renewal.log`).
4. Only then add to httpd.conf, after the two existing includes:
   ```
   Include "C:/RASTATIME/infra/apache/rastatime-https.conf"
   ```
   `httpd.exe -t` → `Syntax OK`, `Restart-Service RASTATIME-APACHE`.
5. Check from outside (mobile network): `https://radio.example.org/`
   shows the login with a valid padlock; `http://` redirects to https;
   `https://radio.example.org/stream/rastatime` plays.

### 2.4 Switch the public URL (last)

Only after 2.1 step 3 is settled (public name works from the LAN).
`config/libretime.conf`:
```yaml
general:
  public_url: https://radio.example.org
```
Then restart `RASTATIME-API` (ALLOWED_HOSTS / CSRF read the file at
start), `RASTATIME-PLAYOUT` and `RASTATIME-ANALYZER` (their internal
calls stay on 127.0.0.1, nothing else changes for them); the legacy PHP
reads the file per request.  From now on the player, the widgets, the
embed codes and the e-mails carry `https://radio.example.org/…`.
Rollback = the old value + the same restarts.

## Stage 3 — Acceptance from outside

From a mobile network: UI login, the three stream mounts, BUTT dial-in on
`radio.example.org:8001`, widgets on the station website, HTTP→HTTPS
redirect, HSTS header, SSL Labs grade, and the public name from inside
the LAN.
