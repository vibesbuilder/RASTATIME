# TEST_PLAN.md — RASTATIME Acceptance Checklist, Recurring Checks, Rehearsal Tools

**Status:** Accepted (BACKLOG point 14, operator go 2026-10-06)
**Date:** 2026-10-06
**Scope:** the production machine (192.168.1.64, `https://radio.example.org`)

Three parts: **A** the acceptance checklist to run after any larger change
(and once before the first "real" broadcast day), **B** the recurring
checks that keep the station honest, **C** the rehearsal tools with their
calls.  Every row names the expected result and where to look; "assistant"
means the check can be done read-only from the machine, "operator" means
ears, hands or an external device are needed.

Rules while testing (ASSISTANT.local.md, 17b): rehearse on **temporary
instances** of a test show (e.g. show 534 "testautoloading"), never on a
real one; tag before a live change (`git tag live-YYYY-MM-DD`); migrations
only with a fresh backup (03:30 run) and outside show boundaries.

---

## A. Acceptance checklist

### A1 Services and boot

| # | Check | How | Expected |
|---|---|---|---|
| A1.1 | All services running | `Get-Service RASTATIME-*, postgresql-x64-17, RabbitMQ` | 10 × Running, start type Automatic |
| A1.2 | Boot without hands | restart in a quiet window, do not touch the keyboard (WINDOWS_24_7 §7) | `studio` signed in automatically, all services Running within ~2 min, Tascam resolved **by name** in `playout-stdout.log` ("rendered by name"), preflight "no warnings active" |
| A1.3 | Playout health gate | `playout-stdout.log` after a start | `Health gate: API healthy`, `Liquidsoap config ... up-to-date` or a rendered + restarted Liquidsoap, telnet connected |
| A1.4 | Internal URL | `playout-stdout.log` | `Legacy v1 API client base URL: http://127.0.0.1`, `DJ logins are checked ... http://127.0.0.1` |
| A1.5 | Loopback binds | `netstat -an` listeners | 5432, 5672, 8765, 1234, 8770 only on 127.0.0.1 / ::1; 80, 443, 8000, 8001 on 0.0.0.0 |

### A2 Schedule and playout

| # | Check | How | Expected |
|---|---|---|---|
| A2.1 | Show starts on time | a file show at a full minute; `grep "PLAY " playout-stdout.log` | first PLAY within 0.1 s of the row start |
| A2.2 | Track crossfade | two music tracks; `crossfade_rehearsal.py` or ears | overlap = house crossfade (3 s), no gap, no cut; jingles (`No Fade`) butt to butt |
| A2.3 | Show boundary | file show → next show; log `show/old` | successor takes over at the boundary (`takes over from ... predecessor has 0.0 s left`), no silence |
| A2.4 | Autoloading fill | `ap_fill_test.php --live 534 "<local start>" 10` | intro → outro → playlist, "free at the end" ≤ 4 s, never overbooked, instance deleted afterwards |
| A2.5 | Show move keeps layout | `move_probe.php 534 "<local start>" 10 600` | 0 mismatches, round trip identical |
| A2.6 | Webstream slot | a show with a webstream row | `PLAY (web stream)` at the row start, `bus_show` set, released at the slot end, ICY title on the mount (`watch_window.py`) |
| A2.7 | Line-In slot | a show with a Line-In row, signal at the Tascam | audible within 2 s of the start (0.15 s when pre-warmed), `/linein-capture` mounted, released at the end |
| A2.8 | Cue points | Library → Cue Points on a jingle; `cue_dryrun.php` | cue-out ≤ length, future rows follow the change |
| A2.9 | Loudness | a quiet and a loud track back to back | both at −23 LUFS ± 1 on the stream (Stereo Tool meter or ears) |
| A2.10 | Planned Liquidsoap restart | wait for the window or set `RASTATIME_LIQUIDSOAP_RESTART_EVERY_DAYS`; log | restart "in a quiet moment / at a track boundary", catch-up seek, listeners stay on the standby mounts |
| A2.11 | Remaining time in the show builder | `remaining_probe.php --live 534 "<local start>" 60 music:12,jingle,music:12,jingle,music:12,jingle,remaining` | "free at the end" within ~1 s, each 12-minute block 720 s on air (station IDs at 12:00 / 24:xx / 36:xx), `time_filled` = the laid-out length, `getSecondsRemaining()` = the footer's free time, never overbooked |

### A3 DJ dial-in (Master / Show source)

| # | Check | How | Expected |
|---|---|---|---|
| A3.1 | Host login during the show | BUTT, `radio.example.org:8001`, mount `show`, UI login of a host | `dj-auth: ... accepted`, `scheduled -> show` within ms, audio after the 5-s harbor buffer |
| A3.2 | Too early | same login before the show | refused, log `rejected (no-show, not counted)` — **never** blocked |
| A3.3 | Wrong password ×5 | within 10 min | `address blocked for 15 min`, System Status → Blocked addresses lists it, Unblock clears it |
| A3.4 | Clean disconnect | BUTT disconnect | timeout 5.00 s → `Resume scheduled ... at +N s` |
| A3.5 | Hard disconnect | kill BUTT | `ECONNRESET` → resume within ~1 s, audio back after the buffer |
| A3.6 | Master source | Settings → Streams master credentials, mount `main` | accepted, `scheduled -> master` |

### A4 Streams, HTTPS, outside world

| # | Check | How | Expected |
|---|---|---|---|
| A4.1 | Three mounts | `https://radio.example.org/stream/rastatime`, `-aac`, `-ogg` from a mobile network | 200, audio, ICY title |
| A4.2 | UI from outside | login, Calendar, Library (API page) | works with the padlock; `http://` redirects |
| A4.3 | LAN | `http://192.168.1.64/` and `https://radio.example.org/` from a LAN PC | both work (gateway resolves the name) |
| A4.4 | Icecast internals hidden | `https://.../stream/status-json.xsl`, `/stream/admin/...` | 403 |
| A4.5 | Certificate | `openssl s_client` or the browser | Let's Encrypt, > 30 days left; renewal log `logs\cert-renewal.log` after 2026-11-29 |
| A4.6 | Widgets | `https://.../embed/player`, `embed/weekly-program` | render, stream URLs carry the https name |
| A4.7 | Sensitive paths | `/.git/config`, `/.env`, `/config/libretime.conf` over https | login redirect, never content |

### A5 Protection

| # | Check | How | Expected |
|---|---|---|---|
| A5.1 | Web login brake | 11 wrong logins from one address (e.g. from the machine itself, then unblock) | 10 × "Wrong username or password", 11th: **429**, `Retry-After`, "Too many failed login attempts ..." |
| A5.2 | Unblock | System Status → Blocked addresses → Unblock, or `rt-blocks.ps1 -Unblock <ip>` | entry gone on every layer |
| A5.5 | Allow list | System Status → Blocked addresses → **Allow** on a blocked address; then 11 wrong logins and 5 wrong DJ passwords from it; `rt-firewall-watch.ps1 -DryRun` | unblocked everywhere and listed under Allowed addresses; never braked, throttled or a watcher candidate (`skipped … allowed address` in the log); **Remove** puts it back under the brakes |
| A5.3 | Firewall watcher | `rt-firewall-watch.ps1 -DryRun -WindowMinutes 1440` | lists the scanners of the day; real runs in `logs\firewall-watch.log` every 5 min |
| A5.4 | Secrets | `libretime.conf`, `icecast.xml`, Streams outputs, UI admins | no default values (classification script: all "custom"); passwords in `libretime.conf` quoted |

### A6 Data safety

| # | Check | How | Expected |
|---|---|---|---|
| A6.1 | Nightly backup | `D:\backups`, `logs\backup-auto.log` | today's ZIP + media mirror synced, exit 0 |
| A6.2 | Restore drill (quarterly) | newest ZIP from `D:\backups` into the scratch database `rastatime_restore` per `docs\operator\BACKUP.md` §7.4 (no service stopped, live database untouched) | `pg_restore` without errors, schema version = live, counts plausible, today's shows present; scratch database dropped |
| A6.3 | Storage root | Settings → Local Machine | `D:/stor`, preflight `storage_root_unavailable` quiet |
| A6.4 | Log growth | `log_growth.py` or `logs\` sizes | ≈ 1.5 MB/day, janitor task 03:50 rotating |

---

## B. Recurring checks

| When | What | Where |
|---|---|---|
| **Daily** (morning) | backup of the night, exit 0 | `logs\backup-auto.log`, `D:\backups` |
| Daily | playout clean overnight: no `Traceback`, planned restart if due | `logs\playout-stdout.log` |
| Daily | blocked addresses: anything legitimate caught? | System Status → Blocked addresses |
| **Weekly** | Liquidsoap memory banner (`2048 MB` evening value is normal, restart every 7 days resets) | Liquidsoap log, Task Manager |
| Weekly | firewall watcher log: blocks of the week, false positives | `logs\firewall-watch.log` |
| Weekly | certificate days left (> 30) | browser padlock / `openssl s_client` |
| Weekly | Windows Update: install pending updates by hand in the maintenance window after 03:30 | Settings → Windows Update, then WINDOWS_24_7 §3 |
| **Monthly** | A1.2 boot test in a quiet window | WINDOWS_24_7 §7 |
| Monthly | disk space C: and D: (> 100 GB free) | System Status → Disk Space |
| Monthly | DJ dial-in from outside (A3.1, A3.4) with a real client | BUTT |
| **Quarterly** | restore drill (A6.2) | BACKUP.md |
| Quarterly | review of past shows: delete what is no longer needed (operator decision 2026-10-03) | Calendar |
| **Before each renewal date** (first 2026-11-29) | certificate renewed, Apache restarted by the script | `logs\cert-renewal.log` |

---

## C. Rehearsal tools

All under `C:\Temp\optd\` unless noted; run from `C:\RASTATIME` with the
project interpreter (`.venv\Scripts\python.exe`) or `C:\Tools\PHP\php.exe`.
They never touch real shows - temporary instances are deleted again.

PowerShell scripts from a plain shell need
`powershell -NoProfile -ExecutionPolicy Bypass -File <script>` (the
machine's execution policy is Restricted; the scheduled tasks already pass
the flag).  First full run of the assistant part of A: 2026-10-06 13:00–13:15,
all green, see BACKLOG "Live-Readiness".  First restore drill (A6.2):
2026-10-07, ZIP of 03:30 into `rastatime_restore` in 1 s, schema 64, all
counts identical to live, scratch database dropped - passed.

| Tool | Call | What it proves |
|---|---|---|
| `ap_fill_test.php` | `php ap_fill_test.php --plan <instance> <intro\|0> <outro\|0> <auto\|0>` (read-only) / `--live <show_id> "<local start>" <minutes> [--keep]` | exact autoloading fill, free tail, never overbooked |
| `remaining_probe.php` | `php remaining_probe.php --live <show_id> "<local start>" <minutes> <blocks> [--bare <block>] [--keep]` (`music:<min>`, `jingle`, `remaining` = temporary blocks, or block ids) | the show builder's remaining time with a playlist of smart blocks: laid-out fill, `time_filled`, a block dragged in after the last row |
| `move_probe.php` | `php move_probe.php <show_id> "<local start>" <minutes> <secs>` | moving a show keeps microseconds and crossfade layout |
| `crossfade_rehearsal.py` | `python crossfade_rehearsal.py` (see header for the show ids) | show-boundary crossfade shapes, queue-ahead, hand-over times |
| `shift_rehearsal.py` | `python shift_rehearsal.py` | show shift + filler on an overbooked show |
| `cue_dryrun.php` | `php cue_dryrun.php` | cue-point detection and propagation, rolled back |
| `xf_layout_dryrun.php` / `xf_relayout.php` | `php xf_layout_dryrun.php <instance>` | per-pair crossfade layout of an instance (dry / apply) |
| `ws_length_apply.php` | `php ws_length_apply.php <stream_id>` | webstream length into future rows, reports rows past the show end |
| `watch_window.py` | `python watch_window.py <start> <end>` | ICY titles on the mounts during a show window |
| `dj_client.py` | `python dj_client.py 8001 show <password> 20` | a scripted DJ source against the harbor (auth + switch) |
| `log_growth.py` | `python log_growth.py` | log growth per day |
| `cue_check.py` | `python cue_check.py <hour>` | 24/7 recording cue sidecars |
| `infra\scripts\rt-blocks.ps1` (repo) | `.\rt-blocks.ps1` / `-Unblock <ip\|user:login>` | blocked addresses on every layer, plus the allow list |
| `infra\scripts\rt-firewall-watch.ps1` (repo) | `.\rt-firewall-watch.ps1 -DryRun [-WindowMinutes N]` | what the watcher would block |
| `infra\scripts\apache-cert-renewed.ps1` (repo) | run elevated | config test + Apache restart (the renewal step) |
| `scripts\backup-auto.ps1` (repo) | registered task "RASTATIME-Backup" | nightly backup |
| `frontend\legacy\scripts\po2mo.py` (repo) | `python po2mo.py --all` | compile the four catalogues after a string change (Apache restart to pick up) |
| Unit tests | `.venv\Scripts\python.exe -m pytest tests/unit -q --basetemp=<scratch>` (PYTHONPATH `backend/api;backend/shared;.`) and `-m pytest backend/playout/tests -q` (add `backend/playout`) | 739 / 55+ passed; `--basetemp` is required on this machine |

Secrets are never printed by any of these tools; the database password
is read from `libretime.conf` into the environment for the call only.
