# RASTATIME — Feature Backlog

> Evaluierte aber noch nicht implementierte Features, sortiert
> nach Status.  Wird über Sessions hinweg gepflegt.
>
> **Status-Marker:**
> - 🟢 **GO** — Operator hat oder gibt Go; Vorbedingungen erfüllt
> - 🟡 **DEFER** — empfohlen aber zu späterem Zeitpunkt (oder mit Vorbedingungen)
> - 🔴 **HOLD** — nicht empfohlen oder grundsätzliche Vorklärung nötig
> - 💡 **IDEA** — Future-Idee, noch nicht evaluiert

---

## 🎯 Aktive Backlog-Items (warten auf Operator-Go)

Diese sind technisch evaluiert, empfohlen, und können starten sobald
der Operator das Signal gibt.

### ✅ Line-In: Kanal-Auswahl auf Multi-Input-Devices (DONE 2026-08-31, `e91ae9b`)

**Status:** Implementiert nach Operator-Go 2026-08-31 — Code + Tests +
Doku committet (`e91ae9b` Feature, `e003f08` Manual/Architecture).
**Wichtige Abweichung vom Evaluierungs-Plan:** Der PoC (Schritt 1)
widerlegte die WASAPI-shared-Annahme — das Windows-Mix-Format des
Tascam-Endpoints steht auf Stereo und PortAudio deckelt hart;
exclusive lehnt der Treiber ab, DirectSound liefert Stille, WDM-KS
kann kein Blocking-Read.  **MME** liefert nachweislich alle 16
echten Kanäle (Per-Lane-Bitvergleich des ADC-Rauschens) und wurde
der Feeder-Modus.  Zweite Abweichung: Der Live-Pfad ist die
Liquidsoap-Engine (F-2, dshow direkt in-process) — dafür kam eine
zweite Source `input.http(id="linein_http")` auf den lokalen
`/linein-capture`-Mount hinzu (Phase-F-Muster), per `fallback` in
denselben Switch-Arm gefaltet; Stereo `1/2` bleibt unverändert auf
dshow-direkt.
**Verifiziert:** Feeder live gegen das Tascam (16 ch @ 48 kHz, Kanäle
5/6 → Stereo); UI-Picker live (Tascam → 24 Optionen, Jabra → „Mono
1"); playout-Suite 295 passed, audio-unit 196 passed.
**Offen (Deploy + Abnahme):**
1. **PLAYOUT-Dienst-Neustart** (rendert rastatime.liq mit
   linein_http; kurze On-Air-Unterbrechung → Operator wählt den
   Moment).  Bis dahin: Multichannel-Pfad inaktiv, Stereo-Betrieb
   unverändert.
2. Operator legt die Studio-Line-Ins an (ein Line-In pro Paar) und
   fährt einen Hörtest über eine geplante Line-In-Show auf einem
   Paar > 1/2.
3. Alt-Zeilen einmal neu speichern (device_name-Pflicht für den
   Feeder; ohne Namen fällt der Pfad laut loggend auf dshow 1/2
   zurück).

Ursprüngliche Evaluierung (2026-08-31, als Referenz):
**Anforderung:** Am US-16x08 hängen mehrere Studios (ein Stereo- bzw.
zwei Mono-Inputs pro Studio).  Ein Line-In soll nicht nur das Device,
sondern auch **welche Kanäle** (Stereo-Paar oder Mono-Kanal) wählen.

**Befund (Ist-Zustand, live verifiziert):**
- Windows exponiert das US-16x08 als **einen** 16-Kanal-WASAPI-
  Endpoint („Mikrofon", channels: 16) — keine Per-Paar-Devices.
  Device-Manager liest die Kanalzahl bereits aus (WAVEFORMATEX).
- Das Feature ist **halb gebaut**: `rastatime_linein.channel_mapping`
  (DB + Domain-Validierung + API) und sogar das UI-Feld „Channel
  Mapping" (Komma-Indizes, `0,1`) existieren — aber die Capture
  (`FfmpegLineinCapture`, dshow) **wendet das Mapping nie an**.
- Und sie **kann es dort auch nicht**: der Tascam-dshow-Pin bietet
  laut `-list_options` **max. 2 Kanäle** (= fix Inputs 1+2); `-channels
  16` wird abgelehnt.  Die 16 Kanäle sind nur via WASAPI erreichbar;
  der ffmpeg-Build hat kein WASAPI-Input (nur dshow/openal).

**Lösungsweg (Option A, empfohlen):** Kleiner Python-**WASAPI-Feeder**
(sounddevice/PortAudio, shared mode) öffnet den 16ch-Endpoint,
extrahiert die `channel_mapping`-Kanäle (Paar → Stereo, ein Kanal →
Dual-Mono) und pipet s16le-PCM an ffmpeg-stdin; ffmpeg encodiert
unverändert weiter nach `/linein-capture`.  Bestehender
Watchdog-Pfad bleibt wirksam (Feeder-Stall → ffmpeg-`time=`-Freeze;
Device-Verlust → PortAudio-Error → Pipe-EOF → bestehende
Restart-Logik).  **2-Kanal-Devices bleiben auf dem bewährten
dshow-Pfad** — der Feeder greift nur bei >2-Kanal-Devices.
UI: Textfeld → Picker („Input 1/2", „3/4", …, „Mono 5", gespeist aus
`channels` der Device-API).
**Verworfen:** Tascam-Mixer-Routing (nur global, nicht pro Studio),
Liquidsoap-Umbau (bricht Phase-B-Design), virtuelle Audio-Kabel
(Fremd-Infra im Sendepfad).

**Aufwand:** Feeder ~150–250 LoC + Capture-Anpassung + UI-Picker
~100–150 LoC + Tests + Manual (4 Sprachen); neue Dependency
`sounddevice` (pip-only, bündelt PortAudio-DLL).  ~1.5–2.5 Tage.
**Vorbedingung / Schritt 1 nach Go:** 15-min-PoC — sounddevice
installieren, 1-s-16ch-WASAPI-Capture gegen das Tascam als harte
Machbarkeitsbestätigung (shared-mode-Format-Frage), erst dann bauen.

**Modus-Frage (Operator 2026-08-31, „ASIO oder WDM?"):** Klarstellung:
das „WASAPI" im Device-Picker ist nur das Enumerations-Label
(MMDevice); die heutige Capture läuft über **DirectShow/WDM** — genau
der Pfad mit dem 2-Kanal-Deckel.  Entschieden: **kein
Operator-sichtbarer Modus-Schalter**, sondern Automatik — ≤2ch-Device
→ bewährter dshow-Pfad, >2ch-Device → WASAPI-**shared**-Feeder
(Endpoint bleibt für andere Apps frei); versteckter
Config/Env-Fallback shared↔exclusive nur, falls der PoC
Format-Probleme im shared mode zeigt.  **ASIO verworfen:** (1) nicht
in ffmpeg und nicht in Standard-PortAudio/sounddevice-Wheels
(Steinberg-SDK nicht redistributierbar → eigener Build wäre zu
pflegen), (2) Single-Client — RASTATIME würde das Interface für jede
andere ASIO-Nutzung sperren, plus WDM/ASIO-Samplerate-Kopplung der
Tascam-Treiber, (3) kein Nutzen: der ms-Latenzvorteil verpufft in der
~0.5–0.8-s-Kette (Encoder + Icecast + Monitor).  MME/DirectSound
(ebenfalls 2ch) und WDM-KS (fragilster PortAudio-Backend, nur
Notnagel) bringen nichts.
**Nachtrag nach PoC (selber Tag):** Zwei Annahmen dieses Absatzes
waren falsch — WASAPI shared ist real aufs 2ch-Mix-Format gedeckelt,
und MME meldet nicht 2ch, sondern liefert **alle 16 echten Kanäle**.
Der Feeder-Modus wurde daher MME (siehe ✅-Status oben); die
Automatik-Entscheidung (kein Operator-Schalter, ≤2ch→dshow) und das
ASIO-No-Go bleiben unverändert gültig.

### ✅ Listener-Statistik zeigt keine Daten (DONE 2026-08-30, `00ce768`)

**Status:** Behoben — Sammel-Kette komplett, E2E live bewiesen.
**Ursache (deckte sich mit dem 🟡-Defer-Eintrag unten):** Der
`StatsCollectorThread` existierte, wurde aber nur im verwaisten
`main.py` gestartet — der aktive Entry-Point `__main__.py` kannte ihn
nicht → `cc_listener_count` blieb leer, beide Analytics-Views
korrekterweise ohne Daten.  Zusätzlich wäre die Output-Quelle
(`libretime.conf outputs:`) seit dem Phase-D-Cutover leer gewesen.
**Fix:** Collector-Start in `__main__.py` (120-s-Poll); Poll-Liste
kommt jetzt via `outputs_from_stream_settings()` aus den live
`cc_pref stream_output_N`-Settings (Admin-Creds inklusive; Einträge
ohne Admin-Passwort werden mit Warnung übersprungen).  4 neue Tests.
**E2E-Beweis:** 2 Test-Listener (mp3/aac) erschienen im nächsten
Zyklus als exakt 1/1/0 in `cc_listener_count`.
**Browser-Check (2026-08-30, 18:20):** Chart rendert mit allen drei
Mounts in der Legende; `get-data` liefert live Punkte im
2-Minuten-Takt (letzter Punkt ≤ 2 min alt).  **Show Listener Stats**
funktioniert wie designt: Tabelle füllt erst nach Filter-Klick und
lässt Shows ohne Datenpunkte im Sendefenster weg — Sammlung begann
17:42 (Playout-Neustart mit dem Patch), daher erscheinen Shows ab
der 08:07-Sendung am 2026-08-31.  Rest-Check: dann einmal
draufschauen.
**Doku:** neues Manual-Kapitel ANALYTICS (EN/DE/FR/ES, `96cc252`).

### ✅ Migration: Backup→Restore-Durchlauf auf der alten Maschine validiert (2026-06-16)

**Status:** ERLEDIGT 2026-06-16 — isolierter Trockenlauf gefahren (Temp-DB +
Temp-Pfade, Live-DB nur gelesen, danach aufgeräumt). **Ergebnis: bestanden** —
DB-Round-Trip 47/47 Tabellen identisch (0 `pg_restore`-Fehler), Pfad-Rewrite
307/307 + idempotent, 307/307 Medien-Dateien auf Disk vorhanden, `libretime.conf`
parst. **Dabei gefundene MIGRATION.md-Fehler korrigiert** (Commit `70bb994`):
eine DB statt zwei (`libretime` = totes Leftover), Pfad-Rewrite auf
`rastatime.cc_files` statt `libretime.cc_music_dirs` (Tabelle existiert nicht),
`cc_music_dirs`/`storage_path`-Schritte gestrichen, Config-Pfad `\config\` statt
`\etc\`, neuer §4.8 für die neue IP. Nächster Schritt: echter Umzug.

**(Historie der Vorbedingung — erfüllt:)** vor dem echten Umzug auf die
neue Maschine den kompletten Backup→Restore-Weg **einmal auf der alten
Maschine durchspielen**, um `docs/operator/BACKUP.md` (Full-Backup) +
`docs/operator/MIGRATION.md` Phase A/C (Restore) als reproduzierbar zu
beweisen, bevor man sich beim Cutover darauf verlässt.
**Operator-Wert:** Hoch — Migration ist betriebskritisch; ein validierter
Restore ist die Versicherung gegen einen fehlgeschlagenen Umzug.

**Vorbedingung / Durchführung:** in **isolierte Ziele** restoren, damit die
alte Maschine als Rollback-Quelle unangetastet bleibt:
- DB-Dumps in **temporäre DB-Namen** (z.B. `rastatime_restore_test`) statt
  der Live-DB restoren.
- Medien-/Config-Restore in **temporäre Pfade** statt der Live-Pfade.
- Verifizieren: Track-Count DB vs. Dateien, 3 Stichproben abspielbar (analog
  MIGRATION.md §4.5), Config-Parsing; danach Test-Artefakte aufräumen.

**Parameter für den echten Lauf (2026-06-16):** neue Maschine bekommt **neue
IP/Hostname** (nicht „gleiche IP") → MIGRATION.md §6.3 + `public_url` +
Icecast + Firewall + externe Stream-/Embed-URLs entsprechend anpassen.
Station derzeit **nicht live** → Downtime unkritisch, kein Low-Traffic-Fenster
nötig.

### ✅ Podcast-Downloads: ACL sperrt den studio-User aus — BEHOBEN 2026-08-27

**Status:** ERLEDIGT 2026-08-27. **Root Cause bestätigt:** `download.py`
lud in den %TEMP% des Dienstkontos (`NamedTemporaryFile` ohne `dir=`) und
`shutil.move` = Same-Volume-Rename **behält die Quell-ACL** (NTFS) — die
restriktive SYSTEM-Temp-ACL wanderte so in die Library. **Fix:** Temp-Datei
wird jetzt direkt im Ziel-Ordner geboren (`NamedTemporaryFile(dir=import_dir,
prefix="podcast_tmp_")`) und per `os.replace` im selben Ordner umbenannt —
erbt die Library-ACL ab Erstellung, kein icacls nötig. Regressionstests
`podcasts/tests/test_download.py` (Temp-Dir-Spy + Failure-Cleanup, 2 passed);
E2E-verifiziert auf der Live-Library (`studio:(I)(F)` vererbt). BACKUP.md
trägt jetzt die elevated-Warnung + Robocopy-Log-Prüfschritt. Bestand auf der
neuen Maschine war bereits sauber (Transfer vererbte ACLs neu); alte Maschine
bleibt unangetastet (Rollback-Box). `download.py` war die einzige
NamedTemporaryFile-Stelle im Backend.
**(Ursprünglicher Befund zur Historie:)** gefunden 2026-06-17 beim
Medien-Transfer zur neuen Maschine.
**Symptom:** Die per Podcast-Feature heruntergeladenen Episoden
(`media/imported/2/podcast_ep*.mp3`, **33 Stück, in `cc_files` referenziert**)
haben eine Windows-ACL **ohne** `studio`/`Benutzer` — `studio` kann sie nicht
einmal lesen (`icacls` → „Zugriff verweigert"). Normale Tracks haben
`VORDEFINIERT\Benutzer:(I)(RX)`. Der Downloader läuft offenbar als
SYSTEM/Dienstkonto und setzt eine restriktive, nicht vererbte ACL.

**Auswirkung:**
- **Playout funktioniert** (Liquidsoap-Dienst läuft als SYSTEM/Admin, darf lesen).
- **Aber jedes Backup/Robocopy als `studio` überspringt diese Dateien
  stillschweigend** — betrifft `docs/operator/BACKUP.md` (Full-Backup) **und**
  den Migrations-Medien-Copy (32 Dateien / 2,86 GB fielen beim ersten
  LAN-Robocopy aus, exit ≥8).

**Fixes:**
1. **Sofort (Migration):** Medien-Robocopy **elevated** laufen lassen
   (Administratoren haben `(F)`) → kopiert die fehlenden Podcasts.
2. **Dauerhaft:** Quell-ACL korrigieren — `icacls … /reset` (Vererbung vom
   Eltern-Ordner → `Benutzer:(RX)`) und/oder den Podcast-Downloader so
   anpassen, dass er die ACL nicht restriktiv setzt.
3. **BACKUP.md** muss den Medien-Robocopy elevated empfehlen **oder** auf
   nicht-lesbare Dateien prüfen — sonst stille Backup-Lücke.

### ✅ INSTALL.md / MIGRATION.md auf den realen Liquidsoap-Stack nachziehen — DONE 2026-08-27

**Status:** ERLEDIGT 2026-08-27. Umfang wuchs beim agenten-gestützten
Voll-Audit von 2 auf **16 Dateien**: INSTALL.md (7-Dienste-Topologie, §2.0
Windows-Prep/SAC/statische IP, RabbitMQ+VC-Redist+Liquidsoap+Icecast+FFmpeg
als Prereqs, YAML-Config, venv-Sequenz inkl. psycopg2 + editierbare Pakete,
Step 9a–9h mit Engine-Env + .liq-Render, Checkliste), MIGRATION.md (ANALYZER
in allen Listen, Recordings-Ordner-Trio, AV-Liste, §4.7-Alternative ohne
NSSM-Dumps, neuer §4.9 .liq-Render, 8765-Healthcheck), INSTALL_APACHE.md
(VC-Redist, Module, ZF1-Rewrite inkl. HTTP_AUTHORIZATION, /api/v2-Proxy),
BACKUP.md (7-Dienste-Env-Export, elevated-Warnung, Robocopy-Log-Check,
`rastatime` statt `rastatime_user`), RESTART_ORDER.md + SERVICE_TOPOLOGY.md
(Voll-Umbau auf 7 Dienste), UPGRADE.md, CRASH_RECOVERY.md, DEVICE_MISSING.md,
LINE_IN_BROKEN.md, README.md, LIQUIDSOAP_CUTOVER.md (Hist.-Hinweis),
Manual RECORD_PER_SHOW (EN/DE/FR/ES Pfad), ADR-002/-006 (Superseded-Notes).
Code-seitig: `bootstrap.ps1` Required/Optional-Tausch (RabbitMQ required,
VLC optional; funktional getestet, Exit 0) + `install-api.ps1`-Header 8765.
Adversarial verifiziert (3-Agent-Pass gegen Skripte + Live-System).
**Nachtrag 2026-08-27 — beide Infra-Folge-Fixes ERLEDIGT:**
`status.ps1` kennt jetzt alle **7** Dienste (inkl. HTTP-Proben für API
:8765/health, Apache :80, Icecast :8000; Port-Tabelle + Install-Hints
korrigiert; live getestet — 7× Running, 3× HTTP 200) und die
„prüfe die anderen drei separat"-Workarounds sind wieder aus INSTALL/
RESTART_ORDER/CRASH_RECOVERY/README entfernt.  `run-api.ps1` Default-Port
8000 → **8766** (Operator-Entscheid; kollidiert weder mit Icecast 8000
noch mit dem Produktions-API-Dienst 8765 — Dev-Server lief im Test
parallel zum vollen Stack), WINDOWS_DEV_STATUS.md nachgezogen.
**(Ursprüngliche Befundliste zur Historie:)**

1. **API-Port ist 8765, nicht 8000.** `install-api.ps1` bindet Waitress auf
   Param-Default `$ApiPort = 8765` (Header-Kommentar „8000" ist tot);
   `install-playout.ps1` pollt `http://127.0.0.1:8765/health` + setzt
   `RASTATIME_API_URL=http://127.0.0.1:8765`. **Port 8000 gehört Icecast.**
   → INSTALL.md §9a und MIGRATION.md §5 (`…:8000/health`) korrigieren auf 8765.
2. **RabbitMQ fehlt als Voraussetzung.** `install-analyzer.ps1` + die PHP-Uploads
   brauchen RabbitMQ (Queue `analyzer`, vhost `/rastatime`, Port 5672) + Erlang.
   Steht in **keiner** Prereq-Liste (INSTALL.md §2, MIGRATION.md §3.3). → ergänzen.
3. **Echte Topologie = 7 Dienste:** `API, WORKER, PLAYOUT, ANALYZER, APACHE,
   ICECAST` (in `infra\nssm\`) **+ LIQUIDSOAP** (eigenes Skript). INSTALL.md nennt
   4 (libVLC-Ära), MIGRATION.md 6 (vergisst **ANALYZER**). → beide angleichen.

**Nebenpunkte:** INSTALL.md §9c `-VlcPluginPath` existiert im echten
`install-playout.ps1` nicht mehr (libVLC-Reste); `RASTATIME_PLAYOUT_ENGINE=
liquidsoap` wird von `install-playout.ps1` **nicht** gesetzt (muss separat als
AppEnvironmentExtra ans PLAYOUT-Service, sonst Default-Engine); `libretime.conf.
template` heißt real `libretime.conf.example`.

**Weitere Funde beim echten Install 2026-08-26:**
- `psycopg2` wird von keinem backend-Paket als Dependency deklariert —
  venv-Aufbau nach INSTALL.md ergibt einen API-Stack ohne DB-Treiber
  (`pip install psycopg2-binary` manuell nötig). → in backend/api
  pyproject.toml deklarieren oder in INSTALL.md §4 aufnehmen.
- INSTALL.md Step 7: `manage.py` liegt unter `backend\api\libretime_api\
  manage.py` (nicht `backend\api\manage.py`); `collectstatic` ist mit den
  prod-Settings gar nicht lauffähig (kein `STATIC_ROOT` gesetzt) und im
  Deployment auch nicht nötig → Schritt streichen/korrigieren.
- INSTALL.md nennt VLC/libVLC als Pflicht + `python-vlc` in requirements.txt —
  seit dem Liquidsoap-Cutover obsolet (Neue Maschine läuft ohne VLC).
- `infra\scripts\dev\bootstrap.ps1` prüft VLC als *required* und RabbitMQ
  als *optional* — für den Produktiv-Stack genau invertiert.
- Icecast: Live-Config (`config/icecast.xml`) ist auf **2.4.4**-Semantik
  gebaut (`stream_auth`, `mount_add/remove`); `install-icecast.ps1`-Default
  (`C:\Program Files\Icecast\bin\icecast.exe`) + MIGRATION.md-AV-Liste
  (`Icecast2.exe`) passen nicht zum realen Layout `C:\Tools\Icecast\bin\
  icecast.exe` (Betriebsort auf alter wie neuer Maschine).
- MIGRATION.md §2.2(5)/§4.6 + §3.2-AV-Liste nennen den Recordings-Pfad
  `C:\Users\studio\Music\Recording` — seit dem Record-per-Hour-Umbau
  (2026-06-06) real: `Music\Show Recordings` + `Music\Permanent Recordings`
  (+ `Music\Import` als Local-Import-Quelle); Pfade kommen aus `cc_pref`
  (`local_recording_folder`, `local_247_recording_folder`,
  `local_import_folder`).
- Apache-Host-Setup: die produktive `httpd.conf` (Rewrite-Front-Controller,
  `/api/v2`-ProxyPass, **`RewriteRule ^ - [E=HTTP_AUTHORIZATION:...]`** für
  fcgid) war nie im Repo/Doc — INSTALL_APACHE.md um die drei Blöcke ergänzen
  (bei der Migration 2026-08-26 aus der alten Maschine rekonstruiert).

**Operator-Wert:** Mittel — kein Live-Risiko, aber jeder künftige Install/Umzug
läuft sonst gegen falsche Ports/fehlende Prereqs. **Aufwand:** ~1–2 h Doku in
EN (+ DE/FR/ES falls Manual betroffen). **Vorbedingung:** Migration durch — die
realen Schritte werden beim echten Install dieser Maschine ohnehin verifiziert,
danach 1:1 in die Docs übernehmen.

### 🟡 Backup/Restore via UI (Settings-Submenü)

**Status:** Defer — A + B empfohlen & gut machbar (architektur-angepasst),
C bewusst schlank.  Start erst nach Grundsatz-Entscheidung (Scheduler) +
Operator-Go.  **Nicht für HW-Wechsel nötig** — das CLI-Backup aus
`docs/operator/BACKUP.md` deckt die Migration vollständig ab.
**Evaluiert:** 2026-05-31.
**Operator-Wert:** Hoch (Auto-Backup) bis mittel (Manual).  Backup ist
betriebskritisch; eine UI senkt die Hürde ggü. CLI.  Restore-via-UI: gering.

**Vom Operator vorgeschlagen:** Settings-Submenü „Backup/Restore", 3 Sektionen:
- **A) Auto-Backup:** Activate-Checkbox + Häufigkeit (alle X Tage) + Include-Media.
- **B) Manual Backup:** Button + Include-Media + „Speicherort-Fenster".
- **C) Restore:** Button + Include-Media + „Backup-Auswahl-Fenster".

**Zentraler Architektur-Konflikt (Browser ≠ Server-Dateisystem):** Ein
Browser kann **keinen OS-Dateidialog auf dem Server** öffnen (auch nicht
Single-Machine, Security-Sandbox).  „Speicherort/Backup wählen" geht nur via
(a) Browser-Download/-Upload oder (b) server-seitig konfigurierter Zielordner
+ Backup-Liste.  Die Media Library (100+ GB) sprengt jeden Browser-Transfer
→ Media-Backup **muss server-seitig** (robocopy) bleiben, nie über den Browser.

**Empfohlenes (angepasstes) Design:**
- Server-seitiger **Backup-Zielordner** (Settings-Feld, z.B. `D:\rastatime-backups`)
  statt OS-Dialog; UI **listet** vorhandene Backups (löst Speicherort + Auswahl).
- **DB + Config** (klein, MB): ZIP, optional als Browser-Download.
  **Media** (groß): immer server-seitig via `robocopy /MIR` — das ist
  **inkrementell gratis** (nur Geändertes), erfüllt den Operator-Wunsch ohne
  eigenes Change-Tracking.
- Backup-Job läuft server-seitig; UI **pollt Status** (`cc_pref`
  last_run/last_status — Muster „Local Import Scan" existiert bereits).
- **C) Restore bewusst schlank:** UI = Backup-Browser (Liste + Metadaten) +
  Schritt-für-Schritt-Anleitung (BACKUP.md §7).  **Kein** 1-Klick-DB-Restore
  aus dem laufenden Web-UI (privilegiert + disruptiv: Dienste stoppen, DB als
  Superuser droppen/neu anlegen — das System zieht sich den Teppich unter den
  Füßen weg).  Echter Restore bleibt CLI/offline (oder dediziertes Offline-Script).

**Bausteine vorhanden (Präzedenzfälle):** Settings-Page-Muster „Local Machine"
(nav-Eintrag in `navigation.php` + `PreferenceController`-Action + plain
`.phtml`, kein Zend_Form nötig + JS + `cc_pref`/`rastatime_*`-Django-Model).
Datei-Download an Browser (`FileResponse(as_attachment=True)`, Windows-Branch
in `storage/views/file.py`).  Status-Polling (`local_import_last_status`).

**Net-new / Lücken:**
- **Auto-Backup-Scheduler — größte Lücke:** `rastatime_worker` ist aktuell ein
  Stub; der echte `BackgroundRunner` (Interval-Runner) existiert + ist getestet,
  aber **nicht verdrahtet**.  Kein APScheduler/cron im Code.
- Upload-Limits (PHP/Django) nicht gepinnt (nur Linux-Artefakte 512M; Django
  Default 2.5 MB) — nur relevant bei Restore-via-Upload, das wir ohnehin nicht
  empfehlen.
- Async-Job/Progress-Infra: nur synchron-blockierend vorhanden.

**Aufwand:** B (Manual, DB+Config, Download) ~1–2 Tage; + Media (server-seitig)
~+1–2 Tage; A (Auto inkl. Scheduler) ~2–4 Tage; C (schlank) ~0,5–1 Tag.
Voll: **~1–2 Wochen**.

**Vorbedingungen / offene Grundsatz-Entscheidungen (vor Start klären):**
1. **Auto-Backup-Scheduler:** Windows Task Scheduler (robust, idle-box-tauglich,
   BACKUP.md nutzt es bereits) **[empfohlen]** vs. `BackgroundRunner` aktivieren
   (in-app, mehr Arbeit, berührt den frisch umgestellten Worker-Dienst).
2. **Speicherort-Modell:** server-seitiger Zielordner + Backup-Liste bestätigen.
3. **Restore-Scope:** schlank (Backup-Browser + Anleitung) bestätigen.

**Risiko Live-Betrieb:** A + B niedrig (additive, server-seitige Features).
C (echter Restore) hoch — daher bewusst ausgeklammert.
**Randnotiz:** Tote `cc_backup`-Tabelle (Airtime-Erbe) nicht wiederverwendbar;
kann mit dem Storage-Cleanup mitentfernt werden.

### 🟢 Show-Shift: nachfolgende Show schiebt sich bei Overbook

**Status:** Go, mit Vorbedingung (Scheduler-Tests erst).
**Evaluiert:** 2026-05-22.
**Operator-Wert:** Sehr hoch — echtes Live-Radio-Problem (Musik überzieht, News wird mitten im Wort gecuttet).
**Differenzierung:** Echter Unterschied ggü. Airtime / LibreTime.

**Features:**
- Neue Checkbox in Edit/New Show: "Start der Show verschieben zulassen"
- Bei Overbook der Vorshow + shiftable nachfolgender Show: Tracks der Overbook-Show zu Ende, danach geschobener Start
- Optionale Phase 2: Auto-Befüllungs-Rebuild bei autoloading-playlist nach Shift

**Aufwand:** ~3750 LoC, ~5-7 Wochen.
**Vorbedingung:** Scheduler-Test-Suite ausbauen (~1500 LoC Tests vorab).
**Risiko Live-Betrieb:** Hoch ohne Tests — eine fehlerhafte Shift bringt Show zur falschen Zeit auf Sendung.
**Empfohlene Ausrollung:** Feature-Flag, opt-in pro Show; 30 Tage Beobachtung; dann Default.

### ✅ Record-per-Hour (Vorstufe für 7-Tage-Catchup) — DONE 2026-06-06

**Status:** ✅ **IMPLEMENTIERT 2026-06-06** — neu auf die Phase-C5-
Liquidsoap-Aufnahme-Architektur aufgesetzt (**nicht** der ursprüngliche
FFmpeg-Tap-Plan unten, der seit dem FfmpegRecorder-Delete obsolet war):
zweiter Liquidsoap-`output.file` auf dem Bus mit stündlicher
`reopen_when`-Rotation; Format/Bitrate/Retention/Enable per Settings-UI
(eigener „24/7 Recording Folder", „Recording Folder" → „Show Recording
Folder" umbenannt); Pypo-Retention-Daemon; Cue-Sidecars (`.cues.json`).
Commits `80c3dbf` (Recorder) + `0127ff0` (Retention) + `7b9a8bc`/`84c5c34`
(UI) + `9b3d857` (Cue) + `58515c8`/`7ae8c64`/`75310e1`/`8abd631`
(Doku EN/DE/FR/ES).  Live-verifiziert (11-h-Lauf, nahtlose Übergänge).
Das **7-Tage-Catchup-Frontend** (nutzt die Sidecars) bleibt offen.
Original-Evaluierung unten zur Historie:

**Evaluiert:** 2026-05-22.
**Operator-Wert:** Hoch — Compliance, Catchup, Notfall-Backup.

**Features:**
- FFmpeg-Segment-Mux mit `-segment_atclocktime` für Stunden-Grenzen
- Neuer NSSM-Service `RASTATIME-RECORDER`
- Settings → Local Machine: Folder-Path + Enable + Retention-Days
- Optional: Show-Cue-Markers als JSON-Sidecar
- Co-Existenz mit Record-per-Show (beide tappen Icecast unabhängig)

**Aufwand:** ~1750 LoC, ~2 Wochen.
**Vorbedingung:** Keine.
**Risiko Live-Betrieb:** Niedrig — paralleler Prozess.
**Folgeprojekt:** 7-Tage-Catchup-Frontend nutzt diese Chunks als Input.

### 🟢 Seamless Bus-Mix — Output-Stack-Politur

**Status:** Go in zwei Phasen.  Phase 1 sofort (Tail-Cut-Bug),
Phase 2 später (Architektur-Eingriff für persistente Icecast-PUT-
Verbindung).
**Evaluiert:** 2026-05-25.
**Operator-Wert:** Sehr hoch — direkte Hörer-Erfahrung.

**Drei beobachtete Symptome am aktuellen Output-Stack**
(mpv → 3× FfmpegStreamer → Icecast PUT, hard stop+start bei
jedem Track-/Show-Wechsel):

| # | Symptom | Lösungsklasse |
|---|---|---|
| 1 | Listener-Player muss bei Track-/Show-Change neu verbinden, Stream-Dauer-Counter resetted | Architektur — persistente Icecast-PUT-Verbindung nötig |
| 2 | Track-Ende um 1–2 s abgeschnitten, besonders bei kurzen Files (4–10 s) und vor Webstream-Items | Bug — Stop-Trigger hängt an Scheduler-Clock statt mpv's `end-file`-Event |
| 3 | 1–2 s Stille beim Wechsel zu Webstreams | Folge aus #1 — verschwindet wenn persistente Verbindung steht |

**Phase 1 (sofort, 2–3 Tage) — Option D: Tail-Cut-Bug-Fix**
- Im `playout_scheduler.py::_on_file_start` (analog für webstream
  / linein) hängt der Hard-Stop des laufenden mpv an einer
  scheduler-clock-basierten Timer-Berechnung.  Bei kurzen Files
  ist die Cue-Out-Zeit ggü. mpv's Decode-Latenz pessimistisch
  → die letzten Frames werden abgeschnitten.
- Fix: Trigger an mpv's `end-file`-Event (reason=0) hängen +
  Timeout-Fallback wenn das Event ausbleibt.  Falls der nächste
  Track-Slot noch nicht erreicht ist, wartet der Scheduler.
- Aufwand: ~150 LoC + Live-Test.
- Risiko: niedrig (isolierter Pypo-Code-Pfad, easy revert).

**Phase 2 (in Arbeit ab 2026-05-25) — Variante A: Voll-Migration
mpv → Liquidsoap als alleiniges Audio-Backend**

Operator-Entscheidung 2026-05-25: nach 3 Phase-1-Fix-Iterationen
(cb20df6, 2b2a787, 952ec3b) bleibt der Tail-Cut bei einigen
kurzen Tracks bestehen.  Plus die Phase-2-Probleme (Listener-
Reconnect, Stille beim Webstream-Wechsel) sind durch keinen
Workaround im mpv-Stack zu lösen.  Statt zusätzlicher Pflege-
Schleifen am Custom-Stack: Voll-Migration zu Liquidsoap als
Audio-Backend (Subprocess hinter Pypo-Scheduler).  Eliminiert
~1500 LoC Custom-Code (mpv_engine, FfmpegStreamer × 3,
Crossfade-Berechnung in PHP, mein Tail-Cut-Wait-Hack), bringt
~700 LoC neuen Adapter-Code dazu → netto –800 LoC.

**Was Liquidsoap nativ kann (löst all diese Probleme):**
- Persistent Icecast-PUT × 3 Mountpoints (Listener-Reconnect-
  Problem weg)
- Gapless transitions zwischen Tracks (Tail-Cut weg, kein
  Wait-Hack mehr nötig)
- Crossfade nativ (PHP-Scheduler-Crossfade-Berechnung obsolet)
- ICY-Metadata-Push automatisch beim Track-Wechsel (notify-
  media-started-Hack obsolet)
- Source-Switching master_dj / live_dj / scheduled via
  `switch(...)` (eigener SourceSwitcher obsolet)
- Replay-Gain via `amplify(override="replaygain_track_gain")`
- Cue-Points nativ via `cue_cut(...)`

**Was Python-seitig bleibt:**
- Pypo-Scheduler (Timer, Schedule-Sync mit Frontend-API)
- FfmpegRecorder (per-show Recording)
- FfmpegLineinCapture (Windows-dshow → localhost:8000/linein-
  capture → von Liquidsoap als input.http konsumiert)
- Library-Cache (Download-Pipeline vom Frontend)
- LiquidsoapEngine-Adapter (neuer Python-Wrapper, ~300 LoC,
  Telnet/Socket-Client für Server-Commands)

**Phasen-Plan (Tasks #88–#92, Gesamt 6–8 Wochen kalendarisch):**

- **Phase 0** (Operator-Aktion, 1 Tag): ✅ DONE 2026-05-25.
  Liquidsoap 2.4.4 Windows-Build läuft stabil; `%ffmpeg(...)`
  encoder als Production-Format identifiziert.
- **Phase A** (~1 Woche): 4h Burn-In mit MP3-Stream läuft seit
  2026-05-25 (reduziert von 18h auf 4h auf Operator-Wunsch nach
  ersten stabilen ~77 MB-Snapshots).  Mit dem verkürzten Test
  bleiben subtile Memory-Leaks (~5–10 MB/h) unentdeckt, werden
  aber in Phase D A/B-Test gegen mpv über Tage sichtbar.
- **Phase B** (~2 Wochen): `LiquidsoapEngine` Python-Adapter +
  Telnet-Client + NSSM-Service.  Feature-Flag
  `RASTATIME_PLAYOUT_ENGINE=liquidsoap` als env-var (statt
  Frontend-Preference — env-var-Pattern existiert schon im
  Code für `vlc`-Fallback).
- **Phase C** (~3–4 Wochen, hochgesetzt von 2–3 wegen
  Recording-Migration): Migration aller Source-Typen + DJ-Source-
  Receiver-Wechsel + Recording-Migration zu Liquidsoap.
- **Phase D** (~2 Wochen): Live-A/B auf Test-Mount, Bug-Fix,
  Doku in 4 Sprachen, Cutover als operator-explicit Aktion.

**Operator-Entscheidungen 2026-05-25 (Phase-B-Kickoff):**

| Frage | Entscheidung | Konsequenz |
|---|---|---|
| Liquidsoap-Process-Lifecycle | Eigener NSSM-Service `RASTATIME-LIQUIDSOAP` | NSSM-Install-Script in `backend/playout/config/nssm-install-liquidsoap.ps1`.  Operator startet/stoppt Liquidsoap unabhängig von Pypo. |
| DJ-Source-Receiver (Master / Show) | Liquidsoap `input.harbor` | Operator-DJ-Software muss in Phase C auf neuen Liquidsoap-Port (8001 master / 8002 show) umstellen.  Verzichtet auf Icecast `/source` für DJ.  Native crossfade zwischen DJ und Scheduled. |
| Recording-Migration | Wird mit nach Liquidsoap migriert | FfmpegRecorder entfällt in Phase D.  `output.file` mit metadata-driven filename + `reopen_when` macht das per-show Recording.  Phase C wird größer (3–4 Wochen statt 2–3). |

**Rollback-Plan:** Feature-Flag `audio_backend` erlaubt jederzeit
Fallback zu mpv ohne Service-Reinstall — nur Preference-Toggle
+ Service-Restart.

**Risiko Live-Betrieb:** mittel.  Output-Pipeline-Eingriff geht
direkt an die Hörer.  Gestaffelter Rollout: Phase 0/A/B sind
unsichtbar (testen nur), Phase C/D unter Feature-Flag, finaler
Cutover erst nach 1–2 Wochen A/B-Vergleich.

**Bei Voll-Migration werden obsolet** (wird in Phase D entfernt):
- `mpv_engine.py` (~450 LoC)
- `ffmpeg_streamer.py` (~500 LoC)
- `Scheduler::calculateCrossfades` (PHP, ~300 LoC)
- `_stop_streamers` Parallel-Stops (eigener Hotfix 2b2a787,
  obsolet weil ffmpeg nicht mehr unsere Sache ist)
- Tail-Flush-Wait (Commits cb20df6 + 952ec3b, obsolet weil
  Liquidsoap gapless macht)

### 🟡 Storage-Struktur-Bereinigung (Root → D:\stor + owner-id weg)

**Status:** ERNEUT DEFER (Operator-Entscheid 2026-08-26 bei der Migration):
die neue Maschine hat **keine zweite SSD/D:** — Medien bleiben unter
`C:\RASTATIME\media`, MIGRATION.md §4.4/§4.5 wurden übersprungen (kein
MediaService-Patch, kein cc_files-Rewrite; 340/340 DB-Pfade auf Disk
verifiziert). **Neue Vorbedingung:** D:-Laufwerk nachrüsten — Operator
erhält die zusätzliche Festplatte laut eigener Aussage in den Tagen nach
dem 2026-08-26; danach als eigenes Wartungsfenster nach §4.4/§4.5
durchziehen (Doku bleibt gültig; Reihenfolge: Platte als D: formatieren →
Dienste stoppen → §4.4 a–c Code/Conf/DB → §4.5 robocopy-Flatten →
3-Track-Verifikation → Dienste starten).
**(Ursprünglicher Plan unten zur Historie:)**
**Status (alt):** Geplant für die Hardware-Migration nächste Woche.
**Evaluiert:** 2026-05-29 (Operator-Wunsch "kosmetische Dinge").
**Operator-Entscheidung 2026-05-29:** in die Hardware-Migration
integrieren statt isoliert auf der Live-Maschine (Daten-Migration,
nicht kosmetisch).

**Zwei Wünsche, beide an der Storage-Struktur:**
1. **Root-Folder weg vom Projektordner.**  Aktuell
   `C:/rastatime/media` (= libretime.conf storage.path, im Repo-Baum).
   Ziel: `D:\stor` auf SSD-B der neuen Maschine.
2. **owner-id-Unterordner `imported/2/` wegsparen.**  Die `2` ist die
   User-ID des importierenden Operators (`MediaService.php` Z.35
   `'/imported/' . $fileOwnerId`).  Bei Single-Operator überflüssig.
   Ziel: `D:\stor\imported\<artist>\<album>\...` ohne owner-id-Ebene.

**Warum nicht jetzt isoliert:** beides ist Daten-Migration
(cc_files.filepath + cc_music_dirs.directory umschreiben + Files
physisch verschieben).  Auf der Live-Maschine = Sendeausfall-Risiko
bei unvollständiger Migration.  Bei der Hardware-Migration werden die
Files eh alle verschoben → risikofrei + keine Doppelarbeit.

**Vollständig dokumentiert in `docs/operator/MIGRATION.md` §4.4 + §4.5:**
- Code-Patch MediaService.php (owner-id-Segment raus)
- libretime.conf storage.path → D:/stor
- DB-Transaktion: cc_music_dirs.directory + cc_pref + regexp_replace
  auf cc_files.filepath (`imported/<digits>/` → `imported/`)
- robocopy-Flattening beim Restore
- Verifikation (3 Tracks abspielen vor Go-Live)

**Side-Fund 2026-05-29:** MIGRATION.md hatte einen falschen
Storage-Pfad (`C:\rastatime\stor` existiert nicht, echt ist
`C:\rastatime\media`) — beim Audit gefunden + korrigiert (sonst hätte
das Media-Backup die Library verfehlt).

**Offen bei der Migration:** show-images + auto-dj-logos behalten
vorerst ihre `imported/<owner-id>/`-Subtrees (selten, klein); optionale
DB-Spalten-Bereinigung dokumentiert aber nicht Pflicht.

**Aufwand:** Teil der Migration (kein separater Aufwand); Code-Patch
~3 Zeilen, DB-Transaktion ~10 Zeilen SQL.
**Risiko:** Niedrig im Migrations-Kontext (geplanter Wartungs-Stopp +
Verifikations-Schritt vor Go-Live).

### 🟢 Legacy-mpv-Code-Delete (Phase E + F beide funktional verifiziert)

**Status:** Go nach 1 Woche stabilem Live-Betrieb.
**Evaluiert:** 2026-05-29.  Phase E + F Code-DONE + Live-Test
beide erfolgreich (Phase E: BBC-Webstream am 2026-05-29 18:40,
Phase F: Line-Input am 2026-05-29 spätabends).

**Polish-Items (deferred zur Hardware-Migration):**
- Phase-E + Phase-F: kleine Haker während Webstream/Line-Input —
  Operator-Hypothese: CPU-bound auf i3-1315U.  Test auf neuer
  Lenovo M70s Gen 5/6 ohne Bottleneck.

**Was zu löschen ist (~2800 LoC):**
- `backend/playout/libretime_playout/engine/mpv_engine.py` (~450 LoC)
- `backend/playout/libretime_playout/engine/ffmpeg_streamer.py` (~500 LoC)
- `backend/playout/libretime_playout/engine/vlc_engine.py` (falls obsolet)
- `backend/playout/libretime_playout/engine/ffmpeg_linein_capture.py`
  (~806 LoC) — **ABER VORHER** den reinen Helper
  `_stable_id_to_dshow_audio` (dshow-Spec aus Device-GUID) in ein
  neutrales Modul herauslösen (z.B. `engine/dshow_device.py`): der
  Liquidsoap-Pfad seit Phase F-2 (`input.ffmpeg(dshow)`) importiert
  diesen Helper und würde sonst brechen.  Operator-Entscheid
  2026-05-30: FfmpegLineinCapture-Löschung an diesen mpv-Cleanup
  gekoppelt (statt Einzel-Löschung).
- Pypo-Scheduler-Branches `_on_*_start` mpv/VLC-Pfade + die
  `_linein_capture`-Konstruktion/Watchdog-Verdrahtung in
  `playout_scheduler.__init__` + Legacy-Line-In-Pfade
  (`_on_linein_start`/`_on_stop`/Resume) (~250 LoC)
- DeprecationWarning + env-var-Fallback (`RASTATIME_PLAYOUT_ENGINE=
  mpv|vlc`) in `__main__.py`
- Plus zugehörige Tests (`test_ffmpeg_streamer_*`, `test_mpv_*`;
  `test_scheduler_linein.py` Legacy-Pfad-Tests anpassen, der
  FfmpegLineinCapture-Mock im Liquidsoap-Pfad entfällt)

**Side-Effect**: ffmpeg.exe-Dependency extern komplett weg — seit
Phase F-2 nutzt nur noch der Legacy-mpv-Line-In-Pfad
FfmpegLineinCapture; mit dem mpv-Delete fällt auch das letzte externe
Subprozess-Spawning weg.  liquidsoap-internal libavcodec/format bleibt.

**Aufwand:** ~3-4 h inkl. Helper-Umzug + Tests-Updates + voller
Regression-Check.
**Vorbedingung:** Neue Hardware in Betrieb + 1 Woche Stabil-Lauf
mit Phase-E + Phase-F aktiv (deferred zur Hardware-Migration).
**Risiko Live-Betrieb:** Niedrig — wir löschen nur Code-Pfade die
nicht mehr aktiv sind (`streaming_handled_externally=True` ist seit
Phase-D Cutover fest).


### ✅ Phase-E Polish: Webstream-Buffer + Switch-Verhalten — ROOT CAUSE BEHOBEN 2026-08-30

**Status:** ERLEDIGT 2026-08-30 (`428805e` + cc_pref-Update) — und die
Ursache war **weder Buffer noch Switch noch Hardware**: Auf Windows löst
`localhost` AAAA-first (`::1`) auf, Icecast 2.4.4 lauscht nur IPv4 —
jeder **ICY-Metadata-Update-Call** der Icecast-Outputs (pro Trackstart,
für mp3+aac-Mount) verbrannte ~5 s im IPv6-Connect und fror die
Liquidsoap-**Hauptclock** ein (~10 s gestapelt). Bei Webstream-Shows
fraß jeder Freeze-Catchup den 5-s-Brückenpuffer → Switch-Flip → neuer
Trackstart → nächster Freeze = der 11-s-Ping-Pong (Symptome 1+3).
Datei-Shows hatten dieselben Freezes an jedem Trackwechsel (4–9/Show).
Symptom 2 (Mount-Abriss): seit Cutover 0× — Alt-Hardware-Artefakt.
**Beweiskette** (autonom, 0 On-Air-Impact, Testbett auf /polish-test):
3-Tage-Log-Korrelation (Webstream 50–86, Datei 4–9, Leerlauf 0 Catchups)
→ Quelle sekundengenau glatt (320 kbit/s) → T1/T2/T5/T7 isoliert sauber
→ **T9 host=localhost: 25 Tracks = 25 Catchups (1:1)** →
**T10 host=127.0.0.1: 26 Tracks = 0 Catchups**.
**Fix:** (a) `cc_pref stream_output_1..3` host → `127.0.0.1`;
(b) Renderer-Härtung `_normalize_loopback_host()` in
`liquidsoap_config.py` (+6 Tests, 81/81 grün). Live seit 2026-08-30
17:16 (Referenz: 17:07-Show 9 min vor dem Fix hatte noch 12 Catchups).
**Rest-Validierung:** Show-Fenster 2026-08-31 (08:07 Datei / 12:07 +
17:07 Webstream lokal) müssen ~0 Catchups zeigen —
`Select-String C:\RASTATIME\logs\liquidsoap-stdout.log -Pattern '2026/08/31.*catchup'`.
**(Ursprüngliche Symptom-Analyse unten zur Historie:)**
**Evaluiert:** 2026-05-29 (Phase-E Live-Tests).

**Beobachtete Symptome im Live-Test 19:00-19:09:**

1. **Regelmäßige kleine Haker** während Webstream läuft —
   möglicherweise input.http buffer-underrun bei Network-Jitter,
   ODER CPU-Bottleneck auf der aktuellen i3-1315U-Hardware.
2. **Mountpoint /rastatime verschwand kurz** während kurzer
   Scheduled-Tracks — Icecast PUT-Verbindung abriss (sollte mit
   Liquidsoap eigentlich persistent sein). Möglicherweise PortAudio-
   underflow → Liquidsoap-Cascade.
3. **Falscher Track (Intro BBC News kurz) wurde mittendrin im
   Webstream hörbar** — wenn webstream.is_ready=false (Buffer leer)
   flippt der switch kurz zu scheduled; wenn dort noch ein Track in
   der queue hängt, kommt er als Schnipsel raus.

**Hypothesen:**
- Initial-Buffer von 5 s (post-fix) reicht möglicherweise immer noch
  nicht bei Network-Jitter oder CPU-Last-Spitzen.
- Switch-Flip bei kurzem Buffer-Underrun ist zu aggressiv —
  bräuchte Debounce (z.B. minimum 3 s nicht-ready bevor wegschalten).
- Scheduled queue sollte beim webstream.start geleert werden (Pypo
  ruft `engine.stop()` was deferred-stop ist; eventuell racy bei
  back-to-back Track→Webstream-Übergängen).

**Diagnose-Plan (nach Hardware-Migration):**
1. Burn-In auf neuer Maschine (i5-14400 oder Core Ultra 5 225) ohne
   CPU-Bottleneck — wenn Haker weg → Hardware war Ursache, fertig.
2. Wenn Haker noch da: Buffer 5s → 10s erhöhen, Live-Test.
3. Wenn Haker noch da: Switch-Debounce via `source.available(...)`
   wrapper testen.
4. Mountpoint-Verschwinden: PortAudio-Logs prüfen, ggf. buffer-Größe
   für PortAudio-Bus-Split erhöhen.

**Aufwand:** ~4-8 h für Diagnose + Polish-Iterationen.
**Vorbedingung:** Hardware-Migration durch (Lenovo ThinkCentre M70s
mit dezenter CPU).
**Risiko Live-Betrieb:** Niedrig — Code-Pfad steht, nur Tuning.

**Workaround heute:** Phase-E funktioniert, mit den o.g. kleinen
Haker-Symptomen. Akzeptabel für die nächsten Tage bis Hardware kommt.


### 💡 Internet-Erreichbarkeit (Public Stream + optional Remote-UI)

**Status:** Idea (Operator-Frage 2026-08-26, noch nicht evaluiert — Operator
wollte zunächst nur eine Erklärung).
**Kern:** Router-Forwards minimal halten (nur Stream; UI/DJ besser via VPN),
DynDNS/Domain + A-Record, `public_url` auf öffentliche URL (erfordert
Hairpin-NAT oder Split-DNS für LAN-Zugriff), TLS via Reverse-Proxy (Mixed-
Content: HTTPS-Website blockt HTTP-Stream → auch Icecast hinter TLS).
**Harte Vorbedingung:** Secrets-Härtung — `api_key`/`secret_key`
(change-before-production), Icecast source/relay/admin = `admin` (inkl.
`cc_pref stream_output_*`), Harbor `changeme`, `internal_listener`-Default;
PostgreSQL/RabbitMQ niemals forwarden. Bei Interesse formale Evaluierung
nach Konvention (6 Punkte).

### 💡 Icecast 2.4.4 → 2.5.x Upgrade (Future)

**Status:** Idea — bewusst NICHT in der Hardware-Migration 2026-08 gemacht
(Operator-Entscheid: 2.4.4 wie alte Maschine, kein Versionssprung im Umzug).
Die Live-`icecast.xml` ist empirisch auf 2.4-Semantik abgestimmt: Source-Auth
via `<authentication type="url">` + `stream_auth`, DJ-Connect/Disconnect via
`mount_add`/`mount_remove` direkt an den Playout-Listener :8770. Icecast 2.5
ersetzt diese Optionen durch `event-bindings` — Upgrade erfordert Portierung
der Auth-/Notify-Verdrahtung + Livetest des kompletten DJ-Pfads (Master/Show
connect, Source-Switch, Watchdog). 2.5.0-win64-Installer lag bereits vor
(`C:\_install\icecast_win64_2.5.0.exe`). **Vorbedingung:** stabiler Betrieb
nach Migration + eigenes Wartungsfenster mit Rollback (2.4.4-Baum unter
`C:\Tools\Icecast` sichern).

### 💡 Phase-E ICY-Metadata-Forwarding (Future-Polish)

**Status:** Idea — nice-to-have, nicht eilig.
**Evaluiert:** 2026-05-29.

Aktuell setzt Pypo per `var.set webstream.gain = X` den Stream-Gain,
aber die LIVE-ICY-Metadata vom Webstream (z.B. BBC's aktueller Track-
Title) wird nicht an Hörer durchgereicht. Die Hörer sehen weiterhin
die Pypo-Schedule-Metadata (Show-Name), nicht die Stream-internen
Title-Updates.

input.http hat `on_metadata` callback → könnte via Liquidsoap-Script
in Bus-metadata gepumpt werden. Aufwand: ~50-100 LoC Template + Test.

### 🟢 Widgets — drei Wellen

**Status:** Go in Wellen statt Big-Bang.  In Arbeit.
**Evaluiert:** 2026-05-22.
**Operator-Wert:** Hoch — Widgets sind die Public-Face der Station.
**Risiko Live-Betrieb:** Niedrig (isoliert vom Stream).

**Welle 1 (~1 Woche):**
- ✅ **DONE** Current Show + Current Track Widget mit Restzeit (Section 23.22, Commits 64a0b15 + Polish a5452c6)
- ✅ **DONE** Widget-Polish 2026-05-22: 300 px Breitencap, `?overflow=ellipsis|marquee`, operator-konfigurierbare Empty-State-Labels via neuem Submenu **Widgets → Current Show/Track**
- ✅ **DONE** Next Shows / Latest Shows Widget mit Show-Filter via `?show_id=N` (Stable über Recurring-Instanzen) und `?show=Name` als Fallback. Shared template + JSON-Endpoint, ASC/DESC-Ordering, `modified_instance=TRUE`-Filterung wie internes Dashboard. Settings-Submenu **Widgets → Next/Latest Shows** mit Show-Picker-Dropdown + 2 Empty-State-Labels + Preview + Embed-Code-Generator.
- ✅ **DONE** On-Air-Today Widget mit Header-Band, Time-Range + Show-Name pro Zeile, current-Row bold, Show-Links (target="_blank"). Code-Default 6 Zeilen (`ON_AIR_TODAY_DEFAULT_LIMIT`), URL-Override `?limit=N` (1..20), optionaler `?day=YYYY-MM-DD` für historische/zukünftige Tagesübersichten. Station-Kalendertag hart gedeckelt — nie morgige Shows. Settings-Submenu **Widgets → On Air Today** mit 1 Empty-State-Label + Preview + Embed-Code.

**Welle 2 (~1.5 Wochen):**
- ✅ **DONE** Weekly Schedule modernisiert (Wave-1-Style): ±N-Wochen-Navigation (`?week_offset`), Link-Embedding mit `?link=plain|underline` (default plain), LibreTime-Branding raus, optionales BG-Bild via `?bg=URL`, `?theme=auto|dark|light`, vollständiger Vanilla-JS-Stack ohne jQuery/Handlebars. Settings-Submenu **Widgets → Weekly Schedule** mit Label + Preview + Embed-Code.
- ✅ **DONE** Multi-View Schedule Widget (`/embed/multi-view-schedule`) basierend auf FullCalendar 6.1.10 (lokal gehostet, kein CDN). Day / 2-Day / Week Views umschaltbar (`?view=` + in-widget Buttons). Show-Slots aus `cc_show.background_color`, Klick → Modal mit Description + URL-Button. Auto-Scroll zur now-Linie. ~5min Cache-Default. Settings-Submenu **Widgets → Multi-View Schedule**.

**Welle 3 (~1 Woche):**
- ✅ **DONE** Track History Widget (`/embed/track-history`) für letzte 7 Tage mit HTML5-Date-Picker + Now-Button + Pagesize-Dropdown (10/20/50/100), Time-Filter, Load-More-Pagination, Klick → Modal mit Show-Kontext + "Played in the show:"-Label. Webstream-Inklusion via LEFT JOIN + Metadata-COALESCE. Source: `cc_playout_history` LEFT JOIN `cc_files` LEFT JOIN `cc_show_instances → cc_show` mit Fallback auf `cc_playout_history_metadata`. Exclude-Short-Tracks Filter (Preference + URL-Override). Settings-Submenu **Widgets → Track History**.

**Aufwand gesamt:** ~1700 LoC + ~400 LoC Doku.

---

### ✅ Line-In Metadaten in Track History (DONE 2026-05-22 v17)

**Status:** DONE — vereinfachte Variante umgesetzt.
Operator-Wunsch: nur den Line-Input-Namen loggen, keine
echten Stream-Metadaten.

**Was wurde gebaut:**
- `HistoryService::insertLineInLog()` + `endLineInLog()`
  — schreiben/schließen `cc_playout_history`-Rows mit
  `file_id = NULL` + Metadaten-Keys `track_title` /
  `artist_name`.
- `DashboardController::switchSourceAction` Hook — bei
  ON/OFF eines `master_dj` oder `live_dj` Source-Switches
  wird der History-Eintrag automatisch geschrieben /
  geschlossen.
- `widget_line_input_label` Preference (default "Line
  Input"), operator-editierbar unter Settings → Widgets
  → Track History.
- Track History Widget + Analytics Playout History
  Dashboard zeigen die Einträge automatisch (das LEFT
  JOIN + COALESCE-Pattern war schon da von der
  Webstream-Inklusion).

**Was wurde explizit NICHT gebaut** (war im ursprünglichen
Plan, aber Operator hat es verworfen):
- Liquidsoap-Skript-Modifikation zum Auslesen echter
  Line-In-Metadaten — Operator wollte das nicht, das
  Label-only Logging reicht ihm.
- Differenzierte Settings-Labels für master_dj vs
  live_dj — beide nutzen das gleiche `track_title`, im
  `artist_name` steht der raw source identifier
  ("Master Source" / "Show Source") falls eine spätere
  UI-Erweiterung sie unterscheiden möchte.

**Bekannte Grenzen:**
- Greift nur bei Source-Switches **via Dashboard-UI**.
  Direkter Liquidsoap-Source-Connect ohne Operator-
  Eingriff (z.B. ein DJ verbindet sich direkt zum
  Icecast-Source-Endpoint) löst den Hook nicht aus —
  würde Liquidsoap-/Pypo-Bridge-Erweiterung erfordern.
  Operator-Workflow ist aber typischerweise via
  Dashboard, daher in der Praxis kaum relevant.

**Folge-Iteration v18 (2026-05-23)** — die obige
Grenze ist für den häufigsten Fall (Show ohne
Scheduled Items, Liquidsoap auto-switcht auf
master_dj) inzwischen geschlossen, ebenso die analoge
Lücke für Webstream-als-Show-Inhalt:
- **Webstream als Show-Inhalt** —
  `HistoryService::insertPlayedItem()` schreibt jetzt
  auch für `cc_schedule`-Items mit `stream_id` einen
  synthetischen Block-Eintrag (vorher `early return`).
- **Live-Show ohne Items** —
  `HistoryService::ensureLiveShowLogged()` als
  opportunistischer Side-Effect in
  `ApiController::liveInfoAction(V2)` schreibt idem-
  potent einen Eintrag mit `artist_name = "Live Show"`.
- Übrig bleibt nur: ein DJ verbindet sich direkt zum
  Icecast-Source-Endpoint, ohne dass ein Show-Slot
  existiert UND ohne dass ein Operator den Dashboard-
  Switch betätigt — sehr seltener Praxisfall.

**Hotfix v18.1 (2026-05-23)** — v18 hatte die dritte
cc_schedule-FK-Spalte übersehen.  RastaTime-spezifisch
hat `cc_schedule` neben `file_id` und `stream_id` auch
`linein_id` (Migration 0047, Line-In-Library Phase A).
- **Line-In als Show-Inhalt** —
  `insertPlayedItem()` hat jetzt einen `linein_id`-
  Branch, liest `cc_schedule.linein_id` per Raw-SQL
  (Propel-Klasse kennt die Spalte nicht), looked
  `rastatime_linein.name` für Title/Artist und schreibt
  einen synthetischen Block-Eintrag.  Auch ein
  `Logging::debug` für jeden insertPlayedItem-Aufruf
  und ein `Logging::warn` für unerwartete Schedule-
  Row-Shapes — Diagnose-Trace falls in Zukunft eine
  weitere Variante auftaucht.

### ✅ AutoDj max-show-duration 12 h → 24 h (DONE 2026-05-23 v18)

**Status:** DONE.
Operator-Verdacht (2026-05-23) bestätigt: die ursprüngliche
12 h-Obergrenze aus `AutoDjService::MAX_SHOW_DURATION_SECS`
(Q2 vom 2026-05-21) war für lange Live-Events und Overnight-
Blöcke zu knapp.  Cap auf 24 h gehoben, Kommentare in
AutoDjService.php nachgezogen.  Kein Architektur-Eingriff,
keine Migration nötig — nur ein Konstanten-Bump.

---

## 🛠️ Technical Debt / Refactor-Backlog

### 🟡 JavaScript-Stack-Modernisierung (Hybrid/Vanilla-First — Re-Eval 2026-05-31)

**Status:** In Arbeit — Strategie geklärt (Operator 2026-05-31: **Hybrid,
Vanilla-First**), **Stufe 0 (Quick Wins) gestartet**.  Ersetzt die grobe
Erst-Eval 2026-05-22, deren Bestandsaufnahme an mehreren Stellen falsch war
(s. Korrekturen).
**Re-evaluiert:** 2026-05-31 (verifizierte Inventur des realen Stacks, Agent).
**Operator-Wert:** Security (jQuery-CVE), Wartbarkeit, EOL-Hygiene.
**Relativierung:** Frontend ist Operator-only (authentifiziert, intern, nicht
öffentlich) → das XSS-CVE ist real, aber kein anonymer Angriffsvektor; stärkerer
Treiber ist Wartbarkeit.

**Strategie (Operator-Entscheid 2026-05-31): Hybrid, Vanilla-First.**
- **Default** jeder Ablösung: modernes ES6+ (fetch, querySelector, native
  `<dialog>`/`<audio>`) + moderne Libs als **vendored Bundle** (kein npm/Build —
  genau wie FullCalendar 6 bereits eingebunden ist).  Einbindung wie gehabt über
  Zend `headScript()`.
- **Build-Pipeline** (Vite+Vue+TS) NUR, falls eine Komponente stark
  reaktiv/zustandsbehaftet ist UND in Vanilla unverhältnismäßig viel Boilerplate
  erzeugt → dann erst **eigener ADR + Operator-Go**.  Einziger plausibler
  Kandidat: Podcast-Editor — aber klein genug für Vanilla.

**Verifizierte Bestandsaufnahme (2026-05-31) — es gibt KEINE Build-Pipeline:**
kein package.json / Bundler / TS / Linter / node_modules; alle Libs
hand-vendored `.min.js`, statisch via `headScript()`; `assets.json` ist nur ein
MD5-Cache-Buster.

| Library | Version | Status | Footprint | Schwierigkeit |
|---|---|---|---|---|
| jQuery | 1.8.3 (global) + 1.10.2 (nur Embed-Player) | veraltet, CVE-2020-11023 | 47/53 app-JS + alle Plugins | am härtesten (Substrat) |
| DataTables | 1.9.4 (2012) | veraltet | 28 Sites/12 Dateien, server-side, 2 geforkte Plugins | sehr hart |
| FullCalendar (Schedule) | 1.5.4 (2012) | EOL | 3 Dateien, drag/resize, **zeitzonen-gepatcht** | hart + fragil |
| FullCalendar (Embed) | 6.1.10 (2023) | modern (RASTATIME) | 1 Datei | schon modern |
| qtip2 | nightly 2012 | EOL | 22 Sites/11 Dateien, flach | mittel |
| AngularJS | 1.4.5 | EOL 2022 | **2 JS / 4 Views** (nur Podcast) | eher leicht (isoliert) |
| jPlayer | 2.7.0 (2014) | archiviert | 2 Dateien / 3 Sites + toter Flash-Fallback | leicht (native `<audio>`) |
| Bootstrap (JS) | 2.x (2012) | uralt | global, Modals | mittel |
| plupload | 1.5.4 | alt | 1 Datei (Dropzone koexistiert) | leicht |
| div. (jQuery UI 1.8.24, Underscore 1.5.1, Handlebars, Flot, blockUI, **Tipsy** = 2. Tooltip-Lib, contextMenu, datetimepicker, sprintf, colorpicker) | 2011-2013 | alt | versch. | versch. |
| wavesurfer 4.6.0 (2024), dayjs, FC6, Embed-Widgets | aktuell | modern (RASTATIME) | — | schon modern |

**Korrekturen ggü. Erst-Eval 2026-05-22:**
- jQuery 1.8.3 + 1.10.2 laden **nicht** parallel auf einer Seite (1.10.2 nur im
  Embed-Player, eigene Seite) → „Quick-Win Doppel-Load" war gegenstandslos.
- AngularJS in **4** Views (nicht 7), nur Podcast/Publish.
- **Zwei** FullCalendars (alt 1.5.4 Schedule + neu 6.1.10 Embed), nicht „~1.6".
- Stack viel größer als die 6 Libs (Bootstrap-JS 2.x, jQuery UI, 2 Tooltip-Libs …).
- Fork hat bereits moderne Inseln (Embed-Widgets = Vanilla JS, FC6, wavesurfer 4.6).

**Stufenplan (alles Vanilla-First, risiko-aufsteigend):**
- **Stufe 0 — Quick Wins (🟢 niedrig, ✅ ABGESCHLOSSEN 2026-06-01):**
  - ✅ **0a DONE** (`324ca80`): AngularJS nicht mehr global — nur noch per-page
    (Podcast/Showbuilder laden `angular.min.js` selbst vor `podcast.js`).
  - ✅ **0b DONE** (`38c4525`): Tooltip-Dedupe — Tipsy (2. Tooltip-Lib, nur 1
    Nutzung in `user.js`) global raus, die eine Stelle auf qtip2 migriert
    (qtip2 bleibt, eingebauter `.ui-tooltip-tipsy`-Stil → Optik 1:1).
  - ✅ **0c DONE** (`9792349`): jPlayer→native `<audio>` für die Audio-Preview
    (= jPlayer Teil 1/3, s.u.).
- **✅ jPlayer-Ablösung KOMPLETT (2026-06-01):** alle 3 Nutzer auf natives
  `<audio>` migriert, dann die Lib (2.7.0, 2014) global entfernt:
  - ✅ **Teil 1/3:** Audio-Preview (`9792349`).
  - ✅ **Teil 2/3:** Dashboard-Stream-Player (`b2b11b4`) — inkl.
    `reachableStreamUrl()`-Fix (localhost→`window.location` für Remote-Hörer).
  - ✅ **Teil 3/3:** Radio-Page Podcast-Player (`86a4ef0`), custom Skin behalten
    + nativ angesteuert. Live-Stream-Player (Embed/Muses) bekam denselben
    localhost-Fix (`bd5d9ca`).
  - ✅ **Lib entfernt** (`9fa39e8`): `js/jplayer/*` (13 Dateien), globaler Load,
    totes Header-Div, 7 `assets.json`-Einträge. Verifiziert, kein 500.
- **Player-Follow-ups:**
  - ✅ **Player-Design wie bei LibreTime wiederhergestellt** (`6312961` +
    `69ab09a`, 2026-06-01) — Preview + Dashboard-Stream haben wieder einen
    custom jPlayer/LibreTime-Skin (dunkle Leiste, orange Balken, CSS-Buttons,
    an natives `<audio>` gebunden, ohne jQuery-UI/Bootstrap/Sprite). Radio-Page
    behielt ihr Skin bereits (Teil 3/3).
  - ⬜ **Preview für „Scheduled Line-Input" hinzufügen** — der neue
    `preview_audio.js`/`AudiopreviewController` kennt bisher nur audioclip +
    stream; ein geplanter Line-Input-Slot hat noch keine Preview-Quelle.
- **✅ Stufe 1 — isolierte EOL ABGESCHLOSSEN (2026-06-01):**
  - ✅ **AngularJS 1.4.5 → Vanilla/jQuery KOMPLETT** — die einzigen 3 Controller
    (Publish, Podcast, StationPodcast) / 4 Views auf vanilla migriert, dann die
    Lib + Loads entfernt.  Commits: `6b79128` (Publish-Pilot), `ede7c12`
    (Podcast+Station), `62fbe18` (Lib raus), `b30326e` (My-Podcast ins
    Hauptmenü).  Strategie: Low-Diff (Controller-Bodies fast unverändert, nur
    `$http`→`$.ajax` + Form-Glue + Bootstrap), ~750 Z. DataTables unberührt.
  - ✅ **qtip2 → Floating UI KOMPLETT** — ~31 Tooltips über 14 Dateien auf den
    eigenen `rtTooltip`-Wrapper (Floating UI vendored) migriert, dann qtip2-Lib
    (~3.800 Z.) + Load + assets.json entfernt.  Commits: `f07c53c`
    (Wrapper+Pilot), `4cba934` (Rest, qtip-Kompat-Schicht), `d63394f` (Lib raus).
    (Realer Footprint war ~31/14, nicht die geschätzten 22/11.)
- **Stufe 2 — harte Kerne, EINZELN m. Fallback (🟡, IN ARBEIT):**
  - ✅ **FullCalendar 1.5 → 6 (Schedule) — FC6 ist Default seit 2026-06-01**
    (`8ce8ec1` a1 Shell, `5abaab5` a2 Rich-Rendering, `169106d` b1 Klick-
    Interaktionen, `688e466` b2 Drag/Resize, `81d8c8d` c1 Default-Flip).  FC6
    6.1.10 (vanilla, kein jQuery) ersetzt den geforkten EOL-FC1.5.4.  **Zeitzonen-
    Patch gelöst** (= Hauptrisiko 1 unten): naive Stationszeit-Strings + FC6
    `timeZone:'local'` + natives `now` auf Stationszeit — derselbe Ansatz wie das
    Embed-Widget, kein Lib-Handpatch mehr.  Verifiziert: 3 Views, Stationszeit,
    Status-Icons + Fill-Bar, Grid-Dropdown (1/5/10/15/30/60m), Create + **alle
    Recurrence-Rhythmen** (weekly+Wochentage, every 2/3/4 weeks, monthly day-of-
    month, monthly day-of-week, 5. Donnerstag), ContextMenu, Drag/Resize,
    Sperrlogik.  FC1.5-Fork bleibt als Rollback (`?fc6=0`) + Safety-Net.
    - ⬜ **🟡 DEFER — FC1.5-Fork entfernen** (`js/fullcalendar/` inkl. Fork-
      Zeitzonen-Patches, `css/fullcalendar.css`, FC1.5-Branch in
      `createFullCalendar()`, toter Code `viewDisplay`/`eventRender`/
      `eventAfterRender`/`dayClick`/`eventDrop`/`eventResize`, ScheduleController-
      Load, assets.json-Einträge, Flag-Logik).  **Vorbedingung:** FC6 hat sich im
      echten Livebetrieb über eine Bewährungsphase stabil gezeigt (Operator gibt
      Signal).  Bis dahin Sofort-Rollback behalten.
    - ✅ **Kalender-Design-Politur DONE (2026-06-01, `be429da`)**: neues
      `css/schedule-fc6.css` (dark "LibreTime"-Theme — graue Tagesleiste, dunkle
      Zellen + Grid-Linien, graue Toolbar-Buttons, Brand-Orange Now-Linie, kein
      gelber Today-Tint, dezente Event-Kanten, Fill-Bar-Fix für Kurz-Events) +
      No-Leading-Zero-Uhrzeiten ("8:00").  Scoped auf `#schedule_calendar` →
      Rollback/Embed unberührt.  Operator-verifiziert.
    - ⬜ **💡 User-Manual-Screenshots** (Schedule-Kapitel, alle 4 Sprachen)
      auf den FC6-Look aktualisieren — Bedienung unverändert, daher niedrige
      Prio; sinnvoll gebündelt mit der FC1.5-Fork-Entfernung.
  - 🔄 **jQuery 1.8 → 3.7 — jq3 ist Default seit 2026-06-05 (Stufe 5a); nur noch
    5b-Cleanup offen.** `?jq3=0` bleibt der Rollback (wie FC6). Resume-Details:
    - **Flag:** `?jq3=1` setzt Session-Cookie `rt_jq3`, `?jq3=0` löscht; Helper
      `PageLayoutInitPlugin::rtUseJquery3()`. Weitere Helfer: `rtJqueryUiThemeCss()`
      (redmond 1.8.8 vs `css/redmond-1.13/`) + `rtDataTablesCore()` (DT 1.9 vs
      `js/datatables-1.13/`).
    - **DONE (committet, operator-verifiziert auf jq3):**
      - `841141a` 26× `.live()`→`.on()` + `$(window).load`→`.on` (safe auf 1.8).
      - `7e673d9` jQuery 3.7.1 + jquery-migrate 3.5.2 + jQuery UI 1.13.3 vendored
        + Flag (PageLayoutInit + IndexController).
      - `9afafc9` `$.browser`-Shim (`js/libs/jquery-browser-shim.js` — blockUI/
        jquery.ui.timepicker.js/contextMenu lasen `$.browser.msie`) + jQuery-UI-
        1.13-redmond-Theme (`css/redmond-1.13/`, CSS+13 Bilder) + Grau-Umfärbung.
      - `d9eba9e` DataTables 1.9→**1.13** Core (1.13 behält Legacy-Hungarian-
        Optionen + Server-Side-`sEcho/aaData` → **Backend + Init unverändert**).
        builder.js `fnStateLoadParams` `abVisCols`-Guard (1.13 änderte State-Format).
      - `abdacd0` Fork-Foundation: ColReorder 1.6.2 + Buttons 2.4.2 (+colVis)
        vendored; Table-Widget lädt sie auf jq3 statt der alten ColVis/colReorder.
      - **Verifiziert läuft auf jq3:** User/Tracktype-Tabellen, Dialoge, Kalender
        (FC6+Add-Show+Overlap), Kontextmenü, Settings/Streams, Showbuilder-Tabs+
        -Timeline.
    - **PENDING (Reihenfolge):**
      1. **DataTables-Fork-Init-Umbau** (der große Brocken):
         - ✅ **library.js (Library-Tabelle) DONE (2026-06-03/04, `f51a3c6` +
           Styling-Commit).** Wurzel-Bug: die 38-Spalten-Tabelle, verschachtelt im
           `<"dataTables_scrolling">`-sDom-Wrapper, bricht den 1.13-Init **still**
           ab (Tabelle wird beim DOM-Build detached, kein Fehler/Alert/Warning).
           Fix: `t` bare im sDom + Scroll-Container **post-init** wrappen; der
           Buttons-`B`-sDom-Buchstabe bricht den Init genauso → colvis
           **programmatisch** nach dem Init (`collectionLayout:'fixed'` = zentriertes
           Panel, da Inline-Collection vom `overflow:hidden` geclippt würde);
           ColReorder via `R`; Flex-Layout für Suche→Toolbar→Tabelle→Footer-
           Reihenfolge; Toolbar-Buttons via `.library_toolbar`-Fallback (das
           jQuery-UI-`.fg-toolbar` gibt's auf DT 1.13 nicht mehr); moderne Buttons/
           ColReorder-CSS via `AirtimeTableView::injectTableCssDependencies()` +
           `body.rt-jq3`-Styling (Suche/Button/Pagination/Checkbox-Dropdown).
         - ✅ **builder.js (Showbuilder rechtes Panel / „Scheduled Shows") DONE
           (2026-06-04, `cb84741`).** Wurzel-Bug: DT 1.13 baut die verschachtelten
           `<"sb-padded"<"H"C>>` / leeren `<"F">`-sDom-Slots nicht (H/F sind
           reservierte sDom-Buchstaben → nur der *innere* Div entsteht), und das
           jQuery-UI-`.fg-toolbar` fehlt → Timerange + Select/Trim/Remove/Jump/
           Cancel/Columns waren weg.  Fix: jq3-conditional sDom mit dem library-
           erprobten flachen `<"H"<"sb_toolbar"C>>`-Muster + Toolbar-Fallback auf
           `.sb_toolbar` + programmatischer Buttons-colvis (Icon-only) + operator-
           getunte Layout-Offsets (28/59/90 px).  Plus: `$menu` von global auf
           lokal gezogen (das `$menu = undefined` am Funktionsende clobberte sonst
           das geteilte Library-`$menu` → Library-Toolbar-Buttons verschwanden).
         - ✅ **colvis-„Columns"-Dropdown unter den Button verankert (beide Panels)
           DONE (2026-06-04, `6a4adad`).** Neuer `js/airtime/common/colvisanchor.js`
           (`$.fn.rtColvisAnchor`, Floating UI: bottom-end + flip + shift +
           autoUpdate, MutationObserver-Teardown).  `collectionLayout:'fixed'`
           zentrierte das Panel mittig (Workaround gegen `overflow:hidden`-Clipping);
           der Anchor setzt es jetzt direkt unter den Button (zentriert bleibt der
           Graceful-Fallback, falls Floating UI fehlt).  Inline-`!important` via
           `setProperty` schlägt das `!important` der Fallback-CSS.  Beide colvis-
           Buttons jetzt Icon-only (gedrängte Toolbar).
         - ✅ **podcast.js / Table-Widget DONE (2026-06-05, `5f3d85d`).** Beide
           Widget-Tabellen (Podcast-Liste `#podcast_table` + Podcast-Episoden)
           laufen über das geteilte `AIRTIME.widgets.Table`; ein Fix im Widget
           (`table.js`) repariert beide: jq3-conditional sDom (bare `t` + Post-
           Init-`.dataTables_scrolling`-Wrap + echter `<"dataTables_footer">`-Div,
           da `F` reserviert), programmatischer Buttons-colvis nach den Toolbar-
           Buttons, Flex-Spalten-Layout (`.rt-jq3-widget`-Marker), und Initial-
           `fnDraw()` auf jq3 (deferLoading=1 wird auf 1.13 honoriert → server-
           side-Liste blieb sonst leer bis zum ersten Sortieren).  **Kein State-
           Strip nötig** (die Podcast-Tabellen nutzen kein `bStateSave` — mein
           früherer Hinweis war eine falsche Extrapolation).  **Plus** Scoping-
           Fix der Right-Panel-CSS: `.sb-content .btn-toolbar .btn-group{top:59px}`
           + `#show_builder .dataTables_scrolling{top:90px}` leakten in die
           Podcast-Tabellen (auch unter `.sb-content`/`#show_builder`) → auf den
           `.sb_toolbar`-Slot eingegrenzt + Widget-Scrolling-Override.
         - ✅ **playouthistory/historytable.js DONE (2026-06-05, `faf249d`).**
           Die 3 Analytics-Tabellen (Log Sheet / File Summary / Show Summary)
           rendern auf jq3.  Mehrere Versions-Gap-Bugs: (a) der Tabellen-Build
           lief im jQuery-UI-`show`-Tab-Event, das UI 1.10+ in `activate`
           umbenannt hat (feuert nicht mehr, auch nicht für den initialen Tab) →
           `activate` + manueller Initial-Build; (b) `dtModern` hing an
           `$.fn.dataTable.Buttons`, aber die Seite lädt nur den DT-Core (kein
           Buttons) → Check via `versionCheck("1.10")`; (c) jq3-sDom (bare `t` +
           `<"dataTables_footer">` + `.history_toolbar`-Slot, Length-Menü in den
           Footer) + Post-Init-Wrap; (d) Show-Summary-Accordion:
           `accordion("destroy")` vor Init wirft auf UI 1.13 → Guard auf
           `.ui-accordion`.
         - ✅ **showlistenerstat.js + Flot-Grafik DONE (2026-06-05, `9deac05`).**
           **Show Listener Stats** (Tabelle): jq3-sDom (bare `t`, `T`/TableTools
           raus, `<"dataTables_footer">`-Wrapper), Post-Init-Wrap, `dtModern` via
           `versionCheck` (Seite lädt kein Buttons); plus `.blur(validateTimeRange())`
           → `.blur(validateTimeRange)` (das `()` band den Rückgabe-Wert als
           Handler → jQuery-3-`apply`-Fehler).  **Listener Stats** (Grafik):
           Flot 0.7 (jQuery-3-inkompatibel) → **Flot 0.8.3** vendored (+ neues
           `jquery.flot.time.js` für `mode:"time"`).  Beide rendern auf jq3
           (DataTable + Flot-Canvas verifiziert); sind nur leer, weil aktuell
           keine Listener-Stats vorliegen (→ separates 🔴-Item oben).
         - ✅ **Übrige Seiten-Verifikation (Schritt 4) DONE (2026-06-05).** Sweep
           über die restlichen Seiten auf jq3 (Drag-Reorder, Slider, Autocomplete,
           Template-Reorder, Prefs, Users, Smartblock-Generate, Radio-Seite) sauber.
           Einziger Fund: **Datei-Upload 500** — als vorbestehender Backend-/PHP-8-
           Bug entlarvt (REST-CSRF-Feldname `csrf` vs gelesenes `csrf_token`; bei
           multipart zusätzlich `null['csrf_token']`-Crash auf PHP 8), **nicht**
           jq3-verursacht (Legacy identisch).  Fix `1f66224` (ACL-Plugin akzeptiert
           `csrf`|`csrf_token` + Null-Guard für nicht-JSON-Bodies), verifiziert auf
           `?jq3=1` **und** `?jq3=0`.
      2. ✅ **Advanced/Per-Column-Library-Filter DONE (2026-06-04, `62923e3`).**
         Der geforkte 2012er `columnFilter` (nur DT-1.9-API) war auf jq3
         übersprungen → Panel da, Felder tot.  Neuer `wireModernColumnFilter()`
         befüllt die vorhandenen `#advanced_search`-Slots + verdrahtet `fnFilter`
         (Text→ILIKE, numerisch/Länge/Datum→`from~to`-Range, Track-Typ→exakt),
         Spalten-Index reorder-fest per Datenname, 350 ms Per-Spalten-Debounce.
         **Backend byte-genau unverändert** (DT 1.13 sendet im Legacy-Kompat-Modus
         weiter `sSearch_{N}`/`mDataProp_{N}`, `fnServerData` sendet `advSearch`).
         Legacy behält das Plugin.  *(Operator-Wunsch 2026-06-04.)*
         **Plus Regressions-Fix (gleicher Commit):** `fnStateSaveParams` strippte
         die Suche per DT-1.9-Namen (`oSearch`/`aoSearchCols`), damit sie nicht
         über Seitenwechsel persistiert — DT 1.13 hat die State-Felder umbenannt
         (`search` + `columns[].search`), der Strip lief ins Leere → Suche leakte
         in den gespeicherten State (Tabelle kam gefiltert zurück, Panel leer +
         zu).  Jetzt auch die 1.13-Form gestrippt, beim Speichern **und** Laden;
         Library **+** rechtes Showbuilder-Panel (`builder.js`, gleicher Bug).
      3. **Buttons/ColReorder-CSS** — für die Library erledigt (`body.rt-jq3`-Block
         in styles.css); für die übrigen Tabellen noch angleichen.
      4. **Kosmetik-Politur** (zurückgestellte jQuery-UI-1.13-Punkte): Scheduled-
         Tracks-Dialog sitzt zu weit oben; View-Dialog-Schließen-Icon unsichtbar;
         Add/Edit-Show-Hintergrund zu hell; restliche blaue Reste (Borders/
         Datepicker-Tage/Icons).
      5. **Flag→Default flippen + Migrate-Netz entfernen** (gestaffelt):
         - ✅ **5a Default-Flip DONE (2026-06-05, `87c1d35` + CHANGELOG `9514981`).**
           `rtUseJquery3()` Default `false → true` → ohne Flag/Cookie laden jetzt
           jQuery 3.7.1 + migrate + UI 1.13.3 + DataTables 1.13 (App-Layout +
           Radio-Page; `rtDataTablesCore()` hängt am selben Flag → 1.13 im
           Gleichschritt).  Rollback: `?jq3=0` (Cookie, per Session) + Commit-Revert
           (global).  jquery-migrate bleibt als Netz.  Live-verifiziert per curl
           (Default→jquery-3.7.1 HTTP 200, `?jq3=0`→jquery-1.8.3).
         - 🟡 **5b DEFER — Migrate-Netz + Legacy-Assets entfernen.** Zu entfernen:
           jquery-migrate 3.5.2 + die Legacy-Assets (jQuery 1.8.3, jQuery UI 1.8.x +
           redmond-1.8, DataTables 1.9, `$.browser`-Shim) + die `?jq3`-Flag-Logik
           (`rtUseJquery3`/`rtJqueryUiThemeCss`/`rtDataTablesCore` + alle
           Conditional-Loads in PageLayoutInitPlugin/IndexController) + die
           zugehörigen `assets.json`-Einträge.
           **Vorbedingungen (beide nötig):**
           1. Der jq3-Default hat sich über eine Bewährungsphase im Livebetrieb
              stabil gezeigt (Operator gibt Signal — testet ab 2026-06-05 einige
              Tage).
           2. Die `JQMIGRATE`-Konsolen-Warnungen sind seitenübergreifend sauber —
              sonst entfernt man Shims, auf die noch Code baut (vgl. Hauptrisiko 2:
              `method` vs `type` kann AJAX still auf GET kippen).  Prüfung:
              `jQuery.migrateWarnings` pro Seite.
           Bis dahin Legacy + Migrate als Sofort-Rollback behalten.  Abschluss:
           CHANGELOG-Eintrag (ARCHITECTURE.md existiert nicht → CHANGELOG ist die
           Quelle, wie bei FC6).
  - ⬜ **DataTables 1.13 → 2.0** (eigener späterer Schritt nach jQuery 3):
    server-side-Format (sEcho/aaData → draw/data) + Init auf neue API umstellen.
    Modernitäts-Wette, nicht jQuery-3-blockierend.
- **(Optional) Build-Pipeline:** nur bei Trigger (s. Strategie), eigener ADR.

**Hauptrisiken (Stufe 2 absichern):**
1. ✅ **FullCalendar-Zeitzonen-Patch — GELÖST (2026-06-01)** — war: Schedule-Grid
   lief auf Server- statt Browser-Zeit via hand-gepatchter 2012-Lib
   (`fullcalendar/AIRTIME_DEV_README`), fragilste Kopplung.  Die FC6-Migration
   ersetzt den Handpatch durch naive Stationszeit-Strings + FC6
   `timeZone:'local'` + natives `now` auf Stationszeit (wie das Embed-Widget).
   Der Fork bleibt nur noch als Rollback bis zur Entfernung.
2. **jQuery-1.8-Semantik-Falle** — `soundcardsetting.js:228` dokumentiert
   `method` vs `type` (1.9+); ein jQuery-Bump kann AJAX **still** auf GET
   umstellen („200 OK, speichert aber nicht").
3. **Lokal geforkte** Plugins (DataTables columnFilter/ColVis, serverbrowser,
   tipsy, contextmenu) — Patches bei Lib-Update von Hand neu anwenden.

**Aufwand:** Stufe 0 ~1 Woche · Stufe 1 ~3-4 Wochen · Stufe 2 ~4-6 Wochen.
Voll ~8-12 Wochen, über Monate verteilt.
**Vorbedingung:** ruhige Phase (kein paralleler Feature-Rollout) — HW-Wartezeit
passt für Stufe 0/1.
**Risiko Live-Betrieb:** Stufe 0/1 niedrig (isoliert/additiv); Stufe 2 mittel
(Legacy parallel als Fallback halten, Live-Verifikation pro Seite).

---

## 🤔 Strategische Entscheidungen (vor Implementation klären)

### 🔴 Payware / Feature-Gating (Tier-System)

**Status:** Hold — juristisch + strategisch vorklären.
**Evaluiert:** 2026-05-22.
**Geschäftlicher Wert:** Hoch (Monetarisierung).
**Technischer Aufwand:** ~3250 LoC, 6-10 Wochen.

**Kandidaten-Features für Gating** (Operator-Wunschliste):
Line-Inputs, Analytics, Auto-DJ, ausgewählte Widgets, Show Templates,
Local Machine, Restart Services, Podcast Auto-Expiry, etc.
Sowohl Menü-Ebene als auch Einzelfeld-Ebene gewünscht.

**Vorbedingungen (kein Code vor diesen Klärungen):**
1. **License-Modell juristisch klären** — RASTATIME ist Fork von LibreTime (AGPL). Paid-Tier auf AGPL-Fork ist tricky: Source bleibt offen, jemand könnte Gates entfernen und re-distribuieren. Dual-Licensing oder eigene Re-Lizenzierung wäre nötig.
2. **Pricing-Tiers definieren** — welche Features in welchem Tier (Marketing-Entscheidung)
3. **Kommunikations-Strategie** für bestehende Operator (Grace-Period? Grandfathering?)
4. **Konkurrenzanalyse** — Airtime Pro, RadioDJ, BroadcastBuddy

**Alternative**: Donation-Modell (wie OBS Studio) — gleiche Open-Source-Reputation, deutlich weniger juristischer Aufwand, keine Gates im Code.

**Empfehlung:** Erst die vier Vorbedingungen klären, dann technisch entscheiden ob Payware oder Donation.

---

## 💡 Future Feature Ideas (nicht evaluiert, nur notiert)

### 🟢 Mid-Show Song Requests (echtes Just-in-time) — GO 2026-06-16

**Status:** 🟢 Go (Operator 2026-06-16).  Variante **(a) inkrementell entlang
der Dramaturgie** gewählt.
**Evaluiert:** 2026-06-16.
**Operator-Wert:** Hoch — der Hörer hört seinen Wunsch in DERSELBEN Show
statt erst in der nächsten.

Aktuell füllt sich eine Request-Show **einmal** ~8 Min vor Start (Option
C-onepass, Dead-Air-sicher).  Ein Request *nach* der Befüllung landet erst
in der nächsten Show.

**Gewähltes Design (Variante a):** den Ein-Pass-Fill (`AutoPlaylistManager::
_fillRequestShowByPositions`) auf **inkrementelles Cursor-Fill** umstellen —
pro Poll nur die nächste(n) Dramaturgie-Position(en) bis `now + kleiner
Vorlauf` auflösen, mit den dann **frischen** Requests.  Braucht einen
**persistenten Positions-Cursor pro Instanz** (kleine additive Spalte
`cc_show_instances.autoplaylist_cursor`, Migration 0057 — sonst füllt der
nächste Poll die Dramaturgie doppelt).  Reuse `addAutoloadItemToShow` +
`_consumeScheduledRequests`.  **Kein Playout-Eingriff** — pypo nimmt
Mid-Show-`cc_schedule`-Änderungen auf (deque-replace bei `PushSchedule`,
Push zur Startzeit); `fillRequestShows` erfasst bereits laufende Instanzen.

**Aufwand:** ~150–300 Z. PHP + Migration 0057 + Doku-Umschrift (SONG_REQUESTS
§5/FAQ "late requests" dreht sich um, 4 Sprachen).  ~1–2 Tage.
**Risiko Live-Betrieb:** Niedrig (Frontend, kein Playout-Eingriff).

### 🟢 Traffic Alerts (kurzfristige MP3, max. 10 min bis Ausstrahlung) — T1+T2 GELIEFERT 2026-06-16

**Status:** 🟢 Kern geliefert 2026-06-16 — T1 Settings-Picker (`96b5f30`) +
T2 inkrementeller Fill (`e0c7873`).  **Design-Pivot** gegenüber der
ursprünglichen Go-Entscheidung (siehe unten).  🟡 **Deadline-Skip deferred**
(Operator wählte 2026-06-16 Dramaturgie-Dichte statt aktivem Skip).
🟢 **T4 Doku** noch offen (Verifikation + Manual-Kapitel 4 Sprachen + i18n +
CHANGELOG + ARCHITECTURE).
**Operator-Wert:** Hoch — hartes Betriebs-Requirement mit klarer 10-min-SLA.

Kurzfristig eintreffende Traffic-MP3s müssen binnen max. 10 min laufen.

**GELIEFERTES Design (Pivot — inkrementeller Fill statt Insert+Shift):** Ein in
Settings definierter **Traffic-Alert-Smart-Block** (Single-Select-Dropdown,
cc_pref `traffic_alert_block_id`).  Eine Show, die diesen Block in ihrer
Autoload-Dramaturgie trägt, wird **inkrementell gefüllt — exakt wie eine
Request-Show** (Reuse der Mid-Show-R1-Engine): jede Traffic-Position wird erst
kurz vor ihrem Slot aufgelöst und zieht dann den neuesten, noch nicht
eingeplanten Alert (FIFO nach `utime`, kein Random-Fallback, keine
Doppel-Ausstrahlung).  Weil künftige Items noch gar nicht aufgelöst sind,
**entfällt das Insert-after-current + Folge-Item-Schieben komplett** —
Operator-Vereinfachung 2026-06-16.  pypo spielt über die normale
`scheduled`-Queue, kein Liquidsoap-Template-Eingriff, erscheint in
History/Kalender.

**SLA-Methode (Operator-Entscheidung B, 2026-06-16):** Die 10-min-Frist wird
über **Dramaturgie-Dichte** gehalten — der Operator platziert Traffic-Slots eng
genug (≤ SLA) und hält Tracks direkt vor einem Slot kurz.  Kein aktiver
Deadline-Skip.

**🟡 Deferred — Deadline-Skip (Vorbedingung zum Wiederaufgreifen):** Falls der
Live-Betrieb zeigt, dass Dramaturgie-Dichte allein die SLA nicht hält (z. B. ein
überlanger laufender Track schiebt einen Alert-Slot über `Import+10min`), dann
schmaler Skip (Option A): wenn das **nächste** eingeplante Item ein Traffic-Alert
ist und seine Frist zu reißen droht, `source.skip` auf den laufenden Track über
die bestehende Liquidsoap-Telnet-Verbindung.  Erkennung des Alert-Items via
`file_id ∈ Traffic-Block-Pool` (kein Schema) oder Marker-Spalte auf
`cc_schedule` (Migration 0058).  ~80–150 Z.  Erst bauen, wenn die Vorbedingung
im Betrieb eintritt.

**Verworfen:** Weg B (Liquidsoap interrupting queue, AzuraCast-Stil) — Playout-
Eingriff + Drift mit pypos zeitbasiertem Modell + nicht in History.  Nur falls
"immer sofort, mitten im Track abbrechen" zwingend würde.

**Wie andere das machen:** AzuraCast = interrupting `request.queue` +
Fallback-Priorität (`track_sensitive`); klassische Automation (Zetta/Rivendell/
mAirList/RadioDJ) = Cart-Wall/Insert-Next oder feste Uhrzeit-Slots + Netz-Trigger.

**Gemeinsame Basis (Operator-Wunsch 4) — eingelöst:** Mid-Show Requests und
Traffic Alerts teilen sich EINE inkrementelle Fill-Engine
(`_fillRequestShowByPositions`); der Unterschied ist nur die Slot-Auflösung
(Request-Draw + Random-Fallback vs. `_appendTrafficAlert` FIFO ohne Fallback).

### 7-Tage-Catchup Frontend

Web-Player der auf Record-per-Hour-Chunks zugreift. HTTP-Range-
Streaming, einfacher Index, Sprung zu Show-Starts via
Cue-Marker-Sidecars. Folge-Projekt nach Record-per-Hour.

### Outbound Podcast Generator

RSS-Feed-Generator der aus Record-per-Show-Files automatisch einen
Podcast-Feed erzeugt. Erwähnt in `docs/operator/UPGRADE.md` Backlog
und im Manual als "noch nicht implementiert". Komplementär zum
Catchup.

### Per-Weekday Autoplaylist

"Rock am Samstagabend, Jazz am Sonntagmorgen". Erwähnt in
ARCHITECTURE §23.20 (Auto DJ) als Out-of-Scope. Aktuell ist
`auto_dj_playlist_id` global.

### Daypart-aware Auto DJ

Verschiedene Auto-DJ-Playlists für verschiedene Tageszeiten.
Workaround heute: einzelner Smart Block mit
Time-of-Day-Tags + wöchentlicher Filter-Anpassung.

### Operator-Confirmation vor Auto-DJ-Show-Erstellung

"5 Lücken erkannt, 1 Show würde erstellt werden — bestätigen?"
statt direkter Materialisierung. Erwähnt in ARCHITECTURE §23.20.

### Auto-DJ-Show eigene Farbgebung

Visuell dimmer als Operator-Shows im Kalender, statt
Default-Farbe.

### Auto-DJ Recording Opt-in

Heute `record = false` hardcodiert für Auto-DJ-Shows. Preference
zum opt-in für Operator die Auto-DJ-Recordings wollen.

### Show-Templates: Cross-Station Export

Aktuell nur via direktem DB-`pg_dump`. UI-basierter Export /
Import (mit ID-Resolution für Playlists + Bilder).

### Recurring "third Friday of month" Pattern

Aktuell nicht unterstützt. Workaround: vier monatliche
einmalige Shows. Echte Implementation erfordert RRULE-style
recurrence (iCal-RFC).

### HLS / DASH Output-Stream

Aktuell nur Icecast/Shoutcast. Workaround: externer
`ffmpeg -hls_time 6` Repackager.

### Listener Auth (Subscriber-Only-Stream)

`icecast-auth.php` existiert bereits. Aktivierung pro Mount
in `config/icecast.xml`. Default-Install hat es aus.

### SSO / OAuth für API

Aktuell nur API-Keys + PHP-Session. Authn-Proxy vor Apache
nötig. Erwähnt in `docs/operator/UPGRADE.md` Backlog.

### RTL-Sprach-Support (Arabisch, Hebräisch)

UI ist LTR-designed. Bräuchte CSS-Rework zusätzlich zur
Translation. Erwähnt in `docs/manual/*/I18N.md`.

### Show-Builder mid-air editing

Live-Show während sie läuft umsortieren, ohne Cut. Heute:
Sortierung der bereits-gespielten + nächsten Tracks freezable.

---

## 🐞 Known Issues / Bug Backlog

### ✅ „Recent Uploads"-Liste aktualisiert sich nicht automatisch nach Upload (DONE 2026-08-30, `8110b47`)

**Status:** Behoben.
**Ursache (nicht fehlender Callback — Callback kam nie zum Zug):**
Dropzone 4 Auto-Discover scannt das DOM auf seinem eigenen
DOMContentLoaded-Hook, die `Dropzone.options.*`-Objekte (mit dem
`success`-Handler, der die Liste nachzieht) werden aber erst in
jQuery 3s asynchronem `$(document).ready` zugewiesen — einen Microtask
später.  Je nach Load-Order initialisierte die Zone **ohne** Optionen
→ Upload lief, `success`-Refresh nie.
**Fix:** `Dropzone.autoDiscover = false` + explizites `new Dropzone(...)`
direkt nach der Options-Zuweisung (`plupload.js` + Dashboard-Zone in
`main_builder.js`); `dropzone.min.js` wird jetzt vor den Options-Files
appended (`PluploadController.php`).
**Rest-Check (offen, klein):** ein realer Upload-Roundtrip im Browser
(Liste zieht nach) — Operator-Sichtprüfung genügt.

### 🟡 Statische Asset-Cache-Buster: Clients kleben an alten CSS/JS

**Status:** Defer — Fund 2026-08-31 beim Rahmen-Fix (`5ff7713`).
**Befund:** Die `?<hash>`-Query an CSS/JS-Links ist **versionsbasiert,
nicht inhaltsbasiert** — sie ändert sich bei Datei-Edits nicht.  Dazu
sendet Apache für statische Assets **weder `Cache-Control` noch
`Expires`** → Browser nutzen Heuristik-Caching (10 % der Zeit seit
Last-Modified; bei monatealten Dateien Tage bis Wochen) und
revalidieren nicht.  Folge: UI-Fixes erreichen bereits benutzte
Browser erst stark verzögert.  So blieb auch der (heute behobene)
Juni-Parse-Bug in `schedule-fc6.css` unsichtbar konsistent.
**Workaround heute:** Operator-Browser wurde per `fetch(cache:
'reload')` aktualisiert; andere Rechner: einmal **Strg+F5** pro Seite.
**Fix-Optionen (bei Umsetzung entscheiden):** (a) mtime-basierter
Buster im Layout-Helper (kleiner PHP-Eingriff, präzise), (b)
`mod_expires`/`Cache-Control: no-cache` für `/css`+`/js` in der
Apache-Conf (2 Zeilen, revalidiert per 304, minimal mehr Requests).
**Aufwand:** ~0.5–2 h je nach Option.

### 🟡 CSRF-Token rotiert bei jedem Fehlversuch (poisont die offene Seite bis Reload)

**Status:** Defer — kein Bug, aber raue UX (notiert 2026-06-05 beim Upload-Fix).
**Hintergrund:** `Acl_plugin.php:184` regeneriert den Session-`authtoken` bei
**jedem** fehlgeschlagenen CSRF-Check.  Folge: ein einzelner Fehlschlag macht den
im DOM gerenderten Token der bereits offenen Seite ungültig → alle weiteren
nicht-GET-REST-Aktionen dieser Seite scheitern, bis hart neu geladen wird.
Aggressiver als nötig.
**Option:** nur bei echten Angriffs-Signalen rotieren statt bei jedem Mismatch —
Sicherheits-Verhalten, separat zu entscheiden.
**Verwandt (optional, jetzt unnötig):** Der Dashboard-Dropzone-`sending`-Hook, der
`csrf_token` anhängen würde, feuert auf jQuery 3 nicht rechtzeitig (sein
`$(document).ready`-Setup läuft einen Microtask nach Dropzones Auto-Discover).  Der
Server-Fix (akzeptiert das statische `csrf`-Formularfeld) macht den Client-Pfad
überflüssig; optionales Aufräumen wäre, die `Dropzone.options.content`-Zuweisung aus
`onReady` auf Modul-Init zu ziehen (`main_builder.js`).

### ✅ Playout History: Tabelle + Export-Buttons werden nicht angezeigt (CLOSED 2026-08-30)

**Status:** Geschlossen — reproduziert nicht mehr; live in eingeloggter
Browser-Session verifiziert (2026-08-30, 18:15).
**Entdeckt:** 2026-06-01 beim DataTables-1.13-Test.
**Browser-Befund (alle drei Tabs funktionieren):**
- **Log Sheet:** 5 Spalten + echte Zeilen (heutige 08:07/12:07-
  Sendungen), Export-/Toolbar-Buttons gerendert;
  `localStorage['datatables-historyitem-aoColumns']` korrekt gefüllt.
- **File Summary:** baut beim Tab-Wechsel (6 Spalten, aggregierte
  Track-Zählung).  **Show Summary:** Per-Show-Blöcke inkl.
  CSV/PDF-Export.  Konsole über alles hinweg fehlerfrei.
**Einordnung:** Der Eintrag stammte vom 2026-06-01 — **vor** den
historytable-Fixes vom 2026-06-05 (`faf249d`: `activate`-Tab-Event,
sDom, Accordion-Guard), die die Render-Kette reparierten; der Eintrag
war seither stale.  Diagnose 2026-08-30 hatte das Backend bereits
entlastet (Feed-SQL liefert Zeilen).
**Nebenbei gehärtet (`4522e43`):** SQL-Injection im File-Summary-Sort
(ORDER-BY-Whitelist) + beide `fnSetFilteringDelay(350)`-Aufrufe
entfernt (kein „f" im sDom → Plugin band `$('input', undefined)` =
alle Inputs der Seite neu und riss den Range-Pickern die
Keyup-Listener ab).

### 💡 Latent: `HistoryService::getSqlTypes()` mappt DATETIME auf ungültigen PG-Cast

**Status:** Idea/Latent — heute harmlos, Fund der 2026-08-30er
Playout-History-Diagnose.
**Befund:** `getSqlTypes()` übersetzt `TEMPLATE_DATETIME` in den
Cast-String `'datetime'` — den Typ gibt es in PostgreSQL nicht
(korrekt wäre `timestamp`).  Harmlos, solange kein History-Template
ein eigenes DATETIME-Feld definiert (die Stock-Templates tun es
nicht); sobald eines angelegt wird, wirft der Feed-Query einen
SQL-Fehler.  Einzeiler-Fix, bei nächster Arbeit an
`HistoryService.php` mitnehmen.

### ✅ Smart Block speichern funktioniert nicht (DONE 2026-08-30, `5029a7c`)

**Status:** Behoben — Root Cause empirisch bewiesen (Standalone-Harness).
**Ursache (PHP-8-Klasse, nicht jQuery):** Eine Criteria-Zeile, die noch
auf ihrem „Select criteria"-Platzhalter steht, postet den Key `'0'` —
der nicht in der Criteria-Map liegt.  Auf PHP 7 humpelte der
Missing-Key-Zugriff als null + Notice durch und das Formular zeigte
danach den gewollten Fehler „You must select Criteria and Modifier";
auf PHP 8 knallt derselbe Zugriff in den non-nullable Return-Type von
`BlockCriteria::get()` → TypeError → HTTP 500.  Das Save-`$.post`
hatte keinen `.fail()`-Handler → Editor hing stumm am Spinner =
„Block wird nicht gespeichert".  Traf **jeden** Save mit unberührter
Criteria-Zeile.
**Fix:**
- `Criteria.php`: `BlockCriteria::get()` liefert für unbekannte Keys
  einen neutralen Platzhalter → die freundliche Validierung greift
  wieder statt des 500ers.
- `Block.php`: etc-Feld-Reads in `saveSmartBlockCriteria()`
  null-coalesced — die Methode DELETEt erst alle gespeicherten
  Kriterien und insertet dann neu; ein TypeError mittendrin
  vernichtete die Kriterien des Blocks endgültig (Datenverlust-Guard).
- `spl.js`: Save-`$.post` hat jetzt einen `.fail()`-Handler (meldet
  HTTP-Status statt stumm zu hängen).
**Rest-Check (offen, klein):** ein Save-Roundtrip im eingeloggten
Browser (unberührte Zeile → Validierungsfehler; echte Kriterien →
gespeichert) — Operator-Sichtprüfung genügt.

### ✅ Analytics: Listener Stats + Show Listener Stats sammeln keine Daten (DONE 2026-08-30, `00ce768`)

**Status:** Behoben — gebaut wie unten evaluiert, mit einer Abweichung:
die Poll-Liste kommt aus den live `cc_pref stream_output_N`-Settings
(inkl. Admin-Creds) statt aus icecast.xml — damit folgt der Collector
Stream-Änderungen ohne Neustart.  E2E bewiesen (2 Test-Listener →
exakt 1/1/0 in `cc_listener_count`); Details im ✅-Eintrag
„Listener-Statistik zeigt keine Daten" oben.  Ursprüngliche
Evaluierung darunter als Referenz belassen:
**Evaluiert:** 2026-05-29 (Operator-Wunsch).
**Operator-Priorität:** Low.  Listener Stats wichtiger als Show
Listener Stats.

**Symptom:** Unter ANALYTICS → "Listener Stats" + "Show Listener
Stats" ist nur die Date-Range-Auswahl bedienbar, sonst bleibt alles
leer (kein Chart, keine Tabelle).

**Diagnose (Anzeige-Kette intakt, Daten-Sammlung gebrochen):**
Controller (`ListenerstatController`), Model (`ListenerStat`), Views,
flot-Chart-JS und der API-Endpoint (`ApiController::pushStreamStatsAction`
→ `insertDataPoints`) funktionieren.  `cc_listener_count` hat aber
**0 Zeilen** → leeres JSON → leerer Graph.  Drei Brüche:

1. **StatsCollectorThread läuft nicht.**  Wird nur in der verwaisten
   `backend/playout/libretime_playout/main.py` gestartet; der aktive
   Entry-Point `__main__.py` (`python -m libretime_playout`) kennt ihn
   nicht (0 Referenzen).
2. **Output-Quelle leer.**  `StatsCollector.collect()` liest
   `config.stream.outputs.merged` aus libretime.conf, dort
   `outputs: icecast: []`.  Beim Liquidsoap-Cutover (Phase D) wanderte
   die Output-Config nach cc_pref + rastatime.liq.
3. **Admin-Passwort fehlt.**  Der Collector pollt Icecast
   `/admin/stats.xml` und braucht das Icecast-**Admin**-Passwort
   (nicht das Source-Passwort, das Liquidsoap zum Pushen nutzt) —
   aktuell nirgends für den Collector verdrahtet.

**Was gebaut werden müsste:**
- `StatsCollectorThread` in `__main__.py` starten (~3-5 Zeilen).
- Output-Quelle umstellen: Icecast `/admin/stats.xml` direkt pollen
  mit Admin-Creds aus icecast.xml/config — unabhängig von der leeren
  libretime.conf-Output-Liste.
- Admin-Passwort-Config-Read.
- Show Listener Stats: baut auf denselben cc_listener_count-Daten
  (JOIN cc_show_instances) — funktioniert fast automatisch sobald
  Listener Stats Daten liefert; nur Tabellen-View prüfen.

**Aufwand:** Listener Stats ~150-250 LoC + Tests (~1 Tag);
Show Listener Stats ~50 LoC zusätzlich (~0.5 Tag).
**Vorbedingungen:** (1) Live-Betrieb aktiv, (2) erste echte Listener
(sonst nicht testbar — ohne Hörer keine Daten), (3) Hardware-Migration
durch (auf stabiler Plattform reparieren).
**Risiko Live-Betrieb:** Sehr niedrig — Collector ist ein Read-Only-
Beobachter neben dem Stream; kein Eingriff in Playout/Recording/Output.

### ✅ Liquidsoap clock.assign_new wrapped alle Outputs in portaudio_clock (DONE 2026-05-28 — C5-Side-Fix)

**Status:** DONE — bus-split via `buffer(buffer=0.5, bus)` als asynchrone
Clock-Bruecke implementiert (Task #108).  Phase-D-Defer hat sich erledigt
weil der C5-Reality-Test 2026-05-28 01:25 zeigte dass die clock.assign_new-
allein-Variante NICHT reicht: PortAudio underflow crashte trotzdem das
ganze Liquidsoap (Output underflowed → Shutdown started, ~5s NSSM-Restart
mitten in einer aktiven Recording).  Der echte Bus-Split via buffer() ist
die canonical Liquidsoap-Loesung, jetzt im Renderer + Test gesichert.
Trade-off: lokales Monitor-Speaker laeuft 500 ms hinter Stream/Recording.

**Festgestellt:** 2026-05-27 (Phase-C4 Reality-Test).
**Behoben:** 2026-05-28 (Phase-C5 Reality-Test, Renderer-Edit in
`liquidsoap_config.py::_render_local_output_block`).

---

### 🟡 Liquidsoap Latency-Catchup unter System-Last verliert Recording-Audio (Phase-D)

**Status:** Defer — funktional kein Showstopper, aber Recording-Loss-Risk
unter Spitzenlast.
**Festgestellt:** 2026-05-28 (C5 Burn-In #2).

**Symptom:**
Im 6-Stunden-Burn-In (02:48 - 10:05) waren 5 von 6 Shows mit
99-100 % Recording-Duration korrekt. Eine 60-min-Show (06:00-07:00)
landete bei 88.2 % (3173 von 3600 s = 7 min Audio verloren).

Korrelation: Liquidsoap-Log zeigt `Latency is too high: catchup N.NN s`
Warnungen mit folgender Häufigkeit pro Stunde:
- 04: 28  /  05: 21  /  06: **96**  /  07: 72  /  08: 21

Peak in der Stunde wo die Show 7 Minuten verlor. Zusätzlich
1 Telnet-Timeout (Pypo → Liquidsoap) um 06:11:45 — Liquidsoap war
zu beschäftigt mit Catchup um den `scheduled.push` Befehl
rechtzeitig zu beantworten. Pypo hat sich nach dem Timeout
sauber erholt (kein Folge-Error).

**Realer Datenpunkt (2026-06-06, erster 24/7-Recorder-Live-Test):** Im
11-h-Test (23:00–10:00) waren fast alle Stunden-Dateien exakt 60 min;
einzig die 00:00-Datei verlor ~5 min (55:01), die 23:00-Datei war die
erwartete Teil-Erststunde (57:31).  Operator korreliert den 00:00-Verlust
mit HW-Überlast durch komplexe Schaltungen um Mitternacht (HW-Tausch steht
unmittelbar bevor).  Bestätigt: das Symptom betrifft auch den **24/7-
Recorder** (zweiter `output.file` auf demselben Bus), nicht nur Per-Show —
selbe vermutete Ursache (Catchup unter Last).  Nach HW-Tausch erneut prüfen.

**Hypothesen:**
- System-Last-Quelle: Hintergrund-Disk-I/O (Backup? Indizierung?
  Windows-Update?), oder anderer Process (Bitdefender-Scan?)
- Liquidsoap-Pipeline-Tuning: Frame-Size, Buffer-Größen,
  Threading-Settings könnten Catchup-Latenz reduzieren
- output.file selbst könnte Mit-Verursacher sein (synchroner Disk-
  Write blockt Bus)

**Diagnose-Skript für Phase-D:**
- 24h Burn-In MIT zusätzlicher Last-Probe (perfmon-Logging
  parallel zu burnin2_snapshots: CPU%, Disk-I/O, Memory-Pressure)
- Cross-Reference: korrelieren Catchup-Events mit System-Metriken?
- Falls Disk-I/O der Schuldige: output.file separat per
  clock.assign_new vom Bus isolieren (analog zur PortAudio-Lösung)

**Workaround bis dahin:**
- Nichts. 60-min-Show-Recordings unter Spitzenlast sind potentiell
  unvollständig. 10-min-Show-Recordings sind in der Praxis stabil
  bei 99-100 %.

**Aufwand:** ~4-8 h für Diagnose, danach 1-3 d Fix je nach Root-Cause.

---

### 🟡 Per-Track Crossfade-Entscheidung basierend auf Track-Länge

**Status:** Defer — Phase-D-Polish.
**Evaluiert:** 2026-05-28 (Phase-D Stück-B Operator-Wunsch).
**Operator-Vision (klare Spezifikation):**

> "Für alle Tracks < 30 s gilt IMMER kein (0.0 s) Crossfade,
> Fade-In oder Fade-Out.  Für alle Tracks ≥ 30 s kann man die
> Einstellung unter SETTINGS → GENERAL vornehmen."

**Aktueller Stand (2026-05-28 nach Phase-D Stück-B):**
- Globaler Default `crossfade(fade_in=0.0, fade_out=0.0)` (commit X)
  = hart-cut für ALLE Tracks. Sicher dass jeder Track zu 100 %
  spielt, aber Music-zu-Music-Übergänge sind abrupt.
- Crossfade-Duration weiterhin via env-var
  `RASTATIME_LIQUIDSOAP_CROSSFADE_SECONDS` (default 1.0).

**Was gebaut werden müsste:**

1. **Per-Track fade-Decision** — über Pypo's `_build_annotate_uri`
   eine Liquidsoap-Metadata-Annotation, die der crossfade-Operator
   pro Track liest:
     - Tracks `(cue_out - cue_in) < 30 s`: `liq_cross_start_duration="0.0"`
       + `liq_cross_end_duration="0.0"`  (separat, NICHT die
       zusammenfassende `liq_cross_duration` — das hat Phase-D
       Stück-B-Iteration 2026-05-28 silenced statt no-fade'd).
     - Tracks `≥ 30 s`: keine Annotation, Liquidsoap nutzt das
       globale fade_in/fade_out (= cc_pref settings, siehe unten).

   Vorbedingung: lokales Liquidsoap-Test-Setup mit echten Files
   (5-s-Jingle + 60-s-Music + per-track Annotations) bauen, um
   zu verifizieren dass `liq_cross_start/end_duration="0.0"` wirklich
   "no fade" macht und nicht "skip track".

2. **Frontend-Settings funktional machen** (siehe separates BACKLOG-Item
   "Frontend-Settings Default Fade In / Out / Crossfade Duration"):
   die GLOBAL fade_in/fade_out Werte für Tracks ≥ 30 s sollen aus
   cc_pref (Settings → General → Default Crossfade Duration / Default
   Fade In / Fade Out) gelesen werden, nicht aus env-var.  Bei
   Settings-Save: re-render rastatime.liq + Pypo signal-restart.

**Aufwand:** ~6-10 h gesamt:
- ~2 h Liquidsoap lokaler Test-Setup + Verify start/end_duration-Semantik
- ~2 h Pypo `_build_annotate_uri` + Tests
- ~3-4 h Frontend-Setting-Wiring (cc_pref-Reader + render-Hook)
- ~1 h Doku-Updates

**Vorbedingungen:**
- Phase E + F idealerweise durch (damit auch Webstreams/Line-Inputs
  per cue_in/cue_out durch den gleichen Mechanismus laufen)
- Phase D Live-Betrieb stabil ohne kritische Bugs

**Workaround heute (2026-05-28):**
Operator akzeptiert globale hard-cuts.  Kurze Jingles spielen zu
100 %; Music-zu-Music ist hart aber click-frei (kein audible
gap, nur kein smooth fade).

---

### 🟡 Frontend-Settings "Default Fade In / Out / Crossfade Duration" wieder funktional machen

**Status:** Defer — Operator-Wunsch 2026-05-28, kein akuter Blocker.
**Evaluiert:** 2026-05-28 (Phase-D Stück-B-Iteration).
**Operator-Wert:** Mittel — bessere UX (Settings statt env-var-Bearbeitung).

**Aktueller Stand:**
- **Default Fade In (s)** und **Default Fade Out (s)** in
  Settings → General Preferences werden vermutlich beim
  Schedule-Build/Play noch nicht verwendet (Upstream-Erbe;
  Liquidsoap-Engine ignoriert sie).
- **Default Crossfade Duration (s)** wird aktuell durch die
  env-var `RASTATIME_LIQUIDSOAP_CROSSFADE_SECONDS` am
  RASTATIME-PLAYOUT NSSM-Service kontrolliert (default 2.0,
  jetzt operator-gesetzt auf 1.0).  Das Frontend-Setting wird
  ignoriert.

**Was gebaut werden müsste:**
1. Pypo: in `__main__.py` oder `liquidsoap_config.py` die env-var
   als Fallback behalten, aber primary-source soll das cc_pref
   sein (analog zu wie stream-outputs aus cc_pref gelesen werden).
2. Bei Settings-Save: Pypo `reload_outputs` oder ähnlicher Mechanismus
   triggert .liq re-render + Liquidsoap-restart (optional;
   einfacher: Operator restartet manuell).
3. Fade-In/Out: in Pypo's Track-push-annotate-string als
   `fade_in="N"` / `fade_out="N"` mit-geben (Liquidsoap kann
   diese annotations).

**Aufwand:** ~3-4 h für Crossfade-Setting + Re-Render-Hook;
~1-2 h für Fade-In/Out.

**Vorbedingung:** Frontend-Setting muss Operator-Permission haben
(Admin only — UI ist da, nur Backend-Wiring fehlt).

---

### 🟡 Pypo-NSSM-Service-Resilience untersuchen (Phase-D-Beobachtung)

**Status:** Defer — bei nächstem Auftreten Logs sammeln, dann analysieren.
**Festgestellt:** 2026-05-28 (Phase-D Stück-B-Start).

**Symptom:**
Operator hat festgestellt dass `RASTATIME-PLAYOUT` (Pypo) als
NSSM-Service nicht lief, obwohl er nicht manuell gestoppt wurde.
Konsequenz: source_switcher pollt nicht → DJ-Source-Connect via
Liquidsoap-Harbor wird zwar von Liquidsoap detected, aber Pypo
meldet keinen Source-Switch an Backend → kein rotes On-Air-Light
im Dashboard, kein Recording-Hook, kein notify-media-item-start-play.

**NSSM-Config-Status (geprüft 2026-05-28):**
- `AppExit Default = Restart` ✓
- `AppRestartDelay = 5000` ms ✓
- Service-Auto-Start: ✓

**Mögliche Ursachen bei nächstem Auftreten zu prüfen:**
- Pypo-Crash mit env-var-Fehler beim Liquidsoap-Engine-Init
  (z. B. Liquidsoap-Telnet nicht erreichbar bei kalt-Boot →
  ConnectionError → Crash)
- Mehrfacher Crash → NSSM-Throttle (Default: nach 5 Restart-
  Versuchen in 60 s pausiert NSSM den Auto-Restart)
- Race beim Boot: Liquidsoap-Service startet später als Pypo,
  Pypo crashed beim ersten Telnet-Versuch, NSSM-Throttle greift

**Untersuchung beim nächsten Auftreten:**
```powershell
# NSSM-Reset, falls Throttle aktiv:
nssm reset RASTATIME-PLAYOUT

# Pypo-stderr für die Crash-Zeit
Get-Content C:\rastatime\logs\playout-stderr.log -Tail 50

# NSSM-Stop-Reason
Get-WinEvent -LogName System -MaxEvents 100 |
    Where-Object { $_.ProviderName -match "Service Control Manager" -and
                   $_.Message -match "RASTATIME-PLAYOUT" } |
    Format-Table TimeCreated, Id, LevelDisplayName, Message -Wrap
```

**Mögliche Fixes:**
- NSSM-Service-Dependency auf RASTATIME-LIQUIDSOAP setzen
  (Pypo startet erst NACH Liquidsoap)
- Pypo-Constructor: ConnectionError beim initial recording.stop
  bereits abgefangen, aber engine-init könnte separat crashen —
  hier defensive try/except prüfen
- Telnet-Retry beim Pypo-Init mit exponential-backoff (5 Versuche
  über 30 s) bevor Crash

**Workaround bis untersucht:** Operator prüft regelmäßig
`Get-Service RASTATIME-PLAYOUT`, startet manuell falls down.

---

### ✅ PowerShell `NativeCommandError`-Noise beim Pypo-Start (DONE 2026-08-30, `88e1071`)

**Status:** Behoben — Root Cause war präziser als unten vermutet:
**kein** `print(file=sys.stderr)` in `soundcard/apps.py`, sondern das
Django-`LOGGING`-Dict in `settings/_internal.py`: der Console-
`StreamHandler` defaultete auf **stderr**, und `propagate: True` ließ
jede Zeile zusätzlich über playouts Root-`basicConfig` laufen →
Doppel-Emission, wovon die stderr-Kopie in PowerShell als roter
`NativeCommandError` erschien.  Fix: Handler auf `ext://sys.stdout`,
`propagate: False`, Formatter mit Timestamp/Level angeglichen.
Live verifiziert: die Soundcard-Zeile erscheint genau einmal,
getimestampt, auf stdout.  Ursprüngliche Analyse darunter als
Referenz belassen:
**Festgestellt:** 2026-05-26 (Phase-C8 Reality-Test).

**Symptom:**
Wenn Pypo manuell aus PowerShell mit `2>&1 | Tee-Object …` gestartet
wird, kommt für die `INFO Soundcard manager registered ...` Zeile ein
roter PowerShell-Stack-Trace:
```
C:\rastatime\.venv\Scripts\python.exe : INFO Soundcard manager registered ...
    + CategoryInfo          : NotSpecified: (...) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError
```

**Root cause:**
`libretime_api.soundcard.apps.SoundcardAppConfig.ready()` schreibt direkt
auf **stderr** (per `print(..., file=sys.stderr)` oder ähnlichem
Django-internen Mechanismus), **bevor** das Python-Logging-Framework
voll aufgesetzt ist. PowerShell klassifiziert externes Stderr-Output
mit `2>&1`-Merge automatisch als `NativeCommandError`, auch wenn der
Inhalt nur ein INFO ist. Die gleiche Information wird kurz danach
auch sauber vom Python-Logger ausgegeben (mit Timestamp + Logger-Name) —
**keine doppelte Funktionalität, nur doppelter Log-Eintrag.**

**Workaround:**
Operator kann statt `2>&1 | Tee-Object` einfach `*> file` benutzen,
dann landet alles sauber in der Datei + im Terminal:
```powershell
C:\rastatime\.venv\Scripts\python.exe -m libretime_playout *> C:\rastatime\logs\pypo.log
```

**Echter Fix (für später):**
In `backend/api/libretime_api/soundcard/apps.py` (oder wo das `print`
herkommt) den stderr-print auf `logger.info(...)` umstellen. Müsste
die Audit-Aktion sein dass alle App-Init-Logs durch Python-Logging
laufen. ~30 min.

**RASTATIME-Bezug:** kein funktionaler Impact, betrifft nur das
Terminal-Erlebnis beim manuellen Pypo-Start für Diagnose-Zwecke.

---

### 🔴 Host-Hardware-Instabilität (STUDIO-Maschine, nicht RASTATIME-Code)

**Status:** Hold — blockiert Live-Betrieb, externe Hardware-Aktion nötig.
**Festgestellt:** 2026-05-25 (Analyse von 5 BSODs der letzten 11 Tage).

**Befund:**
5 unerwartete Host-Reboots (14.05. / 18.05. / 23.05. / 24.05. / 25.05.) mit
**verschiedenen** Bug-Check-Codes (`0x0A`, `0x1E`, `0x13A`, `0x154`, `0x20001`)
in **verschiedenen** Schuld-Domänen (Storage `storahci.sys`, Kernel-Heap,
Intel-PPM/Hyper-V, Bitdefender-AV, Lock-Wait). Muster ist **Hardware-Instabilität**,
nicht ein einzelner Treiber-Bug.

**Top-Verdacht:**
1. **SSD-Defekt** (`WD Blue SA510 2TB`, Consumer-Modell) — 24.05.-Crash war
   `IO_DEVICE_ERROR` im Storage-Stack
2. **RAM-Defekt** — Kernel-Heap-Korruption (23.05.) + Stack-Korruption (25.05.)
3. **Thermal/CPU** — Pre-Boot-Event 25.05.: CPU 7 wurde 71 Sek. firmware-throttled

**RASTATIME-Bezug:** Kein direkter. RASTATIME läuft komplett im User-Mode
(Python, ffmpeg, mpv, Icecast, Apache) und kann diese Kernel-Crashes nicht
auslösen. Korrelation entsteht durch 24/7-Workload, der latente Hardware-Defekte
schneller manifestiert.

**Bereits durchgeführte Mitigationen (Stand 2026-05-26):**
- ✅ SSD-SMART via `Get-StorageReliabilityCounter` + WMI ATAPISmartData
  ausgewertet: keine harten Defekt-Indikatoren (Reallocated=0, Uncorrectable=0,
  CRC=0), aber SSD-Temp 63 °C bei Idle + 977 ms Read-Latency-Peak verdächtig
- ✅ WD Dashboard installiert; Firmware `530500WD` ist laut WD für 2TB-Modell aktuell
  (kein Critical Update verfügbar; das `52046100`-Update betrifft nur 250G/500G/1T-Varianten)
- ✅ Bitdefender aktualisiert + Exclusions gesetzt:
  - Paths: `C:\RASTATIME`, `C:\Tools`, `C:\Program Files\PostgreSQL\17\data`
  - Processes: Python (venv), PHP-CGI, Apache httpd, Icecast, mpv, Liquidsoap,
    NSSM, PostgreSQL
- ✅ Killer Performance Suite UWD (Rivet Networks) deinstalliert; Treiber bleibt
  (ist eh Intel-Unified-Driver für die I225/I226-Hardware mit Killer-Branding)
- ✅ Windows DISM `/RestoreHealth` erfolgreich (Component Store integer);
  Media Feature Pack auf Pro-N installiert (Reboot ausstehend, separates Thema)
- ✅ Übernacht-Monitoring 12.5 h (1150 Samples) mit eigenem PS-Skript:
  - SSD-Temp **runter auf min 42 / avg 45 / max 54 °C** (vorher 63 °C)
  - Disk Busy avg 0.1 %, CPU avg 5 %
  - Bitdefender nur in 1 % der Samples Top-RAM (vorher 42 %)
  - **0 BSODs** in 12.5 h (Crash-Frequenz vorher: alle ~2 Tage → statistisch
    aber zu kurz für harte Aussage; mindestens 1 Woche stabil = signifikant)
  - ⚠️ Caveat: Read/Write-Latenz-Counter `AvgDiskSec*` ist uint32-in-Sekunden,
    rundet alles <1 s auf 0; sub-second Spikes nicht erfasst. Für nächsten Test
    muss `Win32_PerfRawData_*` mit manueller Frequency-Berechnung verwendet werden.

**Noch offen:**
- ❌ Memtest86+ über Nacht — bleibt die wichtigste unabhängige Hardware-Verifikation
- ❌ BIOS-Update prüfen
- ❌ Sub-second Latenz-Messung mit korrektem Counter (sensor-monitor v3)
- ❌ Mittelfristig: Consumer-SSD durch Enterprise-Modell ersetzen (WD Red, Samsung PM, Kioxia CD)

**Trigger für Re-Eskalation:**
- BSOD in den nächsten 7 Tagen → Mitigationen waren nicht ausreichend, Hardware-Test priorisieren
- 7+ Tage BSOD-frei → Bitdefender-AV-Interaktion war wahrscheinlich Haupt-Trigger;
  Mitigationen ausreichend, Memtest weiterhin als routine-Check empfohlen

**Minidumps + cdb-Setup für künftige Analyse:** vorhanden in `C:\Temp\dumps\`,
Symbole gecached in `C:\Temp\symbols\`, WinDbg installiert. Pro Crash:
```
cdbX64.exe -z <dump> -y "srv*C:\Temp\symbols*https://msdl.microsoft.com/download/symbols" -c "!analyze -v;q"
```

**Monitoring-Artefakte aus 2026-05-25/26 Session** (für späteres Re-Analysieren):
- `C:\Temp\dump_analyze.py` — Minidump-Bugcheck + Driver-Liste-Parser
- `C:\Temp\analyze-overnight.py` — CSV-Stats für sensor-log-v2
- `C:\Temp\sensor-monitor-v2.ps1` — Übernacht-Sensor-Logger (mit oben genanntem Bug)
- `C:\Temp\sensor-log-v2.csv` — 12.5 h Übernacht-Daten 25.→26.05.
- `C:\Temp\ssd-smart.ps1` / `.txt` — SMART-Snapshot vom 25.05.

---

## 📊 Wartungs-Metrik

| | Stand 2026-05-22 |
|---|---|
| Aktive Backlog-Items | 3 (Show-Shift, Record-per-Hour, Widgets — Welle 1 erste Hälfte fertig) |
| Deferred Items | 1 (JS-Modernisierung) |
| Hold Items | 1 (Payware) |
| Future Ideas | 13 |
| Known Bugs | 0 (RASTATIME-Code) + 1 Host-Hardware-Issue (Stand 2026-05-26, Mitigationen in Verifikation) |

---

## 🔄 Pflege-Hinweis

Dieses Backlog wird über Sessions hinweg gepflegt.  Wenn ein
Feature implementiert wird:
1. Eintrag aus aktiven / deferred items entfernen
2. Im CHANGELOG.md vermerken (Standard-Workflow)
3. Bei Architektur-Relevanz: ARCHITECTURE.md neuer Section + Versions-Bump
4. Manual in allen 4 Sprachen aktualisieren

Wenn ein neues Feature evaluiert wird:
1. Sechs-Punkte-Evaluation (Machbarkeit, Architektur-Eingriff,
   Aufwand, Dauer, Sinn, Empfehlung) durchführen
2. Eintrag hier hinzufügen mit Status-Marker
3. Wenn Hold mit Vorbedingungen: diese explizit auflisten
