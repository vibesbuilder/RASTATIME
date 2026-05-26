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

### 🟢 Record-per-Hour (Vorstufe für 7-Tage-Catchup)

**Status:** Go.
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

### 🟡 JavaScript-Stack-Modernisierung (Option B aus Eval 2026-05-22)

**Status:** Defer — nach Abschluss laufender Feature-Arbeit.
**Evaluiert:** 2026-05-22.
**Operator-Wert:** Mittel (Security, Wartbarkeit, Reputation).
**Aufwand:** ~2130 LoC + ~500 LoC Doku, ~8 Wochen kalendarisch.

**Bestandsaufnahme:**
| Library | Version | Status |
|---|---|---|
| jQuery | **1.8.3 + 1.10.2 (parallel)** | Veraltet; bekannte XSS-Issues (CVE-2020-11023) |
| AngularJS | 1.x | **EOL seit Januar 2022** |
| FullCalendar | ~1.6 | EOL — v6 ist aktuell |
| qtip2 | 2.x | EOL seit 2016 |
| jPlayer | 2.x | Maintained-archiviert seit 2018 |
| DataTables | ~1.10 | v2 aktuell |
| Build-Pipeline | keine | kein Bundler, kein TS, kein Linter |

**Phasen:**
1. **🔥 Quick Win: jQuery-Doppel-Load beheben** (Operator hat Interesse signalisiert)
   - Aktuell: jquery-1.8.3.min.js UND jquery-1.10.2.min.js werden parallel ausgeliefert
   - Aufwand: 1-2 Tage (analysieren welches Plugin welche Version braucht; auf 1.10 konsolidieren als Brücke vor 3.x)
   - Sofortiger Win: weniger Auslieferungs-Größe, weniger Verwirrung im Stack
   - Könnte als isolierte Bug-fix-Aktion vor dem Rest gestartet werden
2. **AngularJS 1 Footprint ist klein**: nur 7 .phtml Views nutzen ng-Direktiven (Podcast-Editor + 6 kleine Form-Bits)
   - Inseln-Portierung auf Vue 3 — ~3-4 Wochen total
3. **jQuery 1.10 → 3.7 Migration mit `jquery-migrate`-Plugin als Warner**: ~1 Woche
4. **Vite + TypeScript für neue Komponenten**: ~3 Tage Setup
5. **Alte jQuery-Plugins schrittweise**: FullCalendar v6, DataTables v2, qtip → Floating UI

**Vorbedingung:** Operator-ruhige Phase (keine parallele Feature-Roll-outs).
**Risiko Live-Betrieb:** Niedrig wenn Legacy-Code parallel bleibt als Fallback.

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

### 🟡 PowerShell `NativeCommandError`-Noise beim Pypo-Start (kosmetisch)

**Status:** Defer — kosmetisch, nicht funktional.
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
