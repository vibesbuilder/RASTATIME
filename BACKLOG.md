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

### 🟡 Line-In Metadaten in Track History (Defer)

**Status:** Operator-Wunsch 2026-05-22, deferred bis nach
Welle-3-Polish.

**Problem:** Line-Inputs (z.B. externes Studio-Mic, externes
Mischpult) liefern aktuell **keine** Metadaten in
`cc_playout_history`.  Liquidsoap behandelt einen Line-In
als rohes Audio ohne Metadata-Stream — anders als bei
einem Webstream, wo der Source-Server ICY/Now-Playing-
Metadaten mitsendet.

**Lösungspfad:**
1. Liquidsoap-Skript erweitern, sodass beim Wechsel auf
   Line-In ein `notify_webstream_data`-äquivalenter Call
   gefeuert wird, mit `track_title` = Show-Name (oder
   freiem Operator-Text) und `artist_name` = "Line-In".
2. ApiController um `notifyLineInDataAction` erweitern
   (oder bestehenden `notifyWebstreamDataAction` für
   Line-In wiederverwenden).
3. HistoryService::insertLineInMetadata() neu, analog zu
   `insertWebstreamMetadata`.
4. Optional: Operator-konfigurierbares Label für Line-In
   im UI (Settings → Streams → Line-In Label).

**Aufwand:** ~1 Tag (Liquidsoap-Konfig-Test + Backend +
Pypo-Bridge-Check).  Voraussetzung: stabile
Liquidsoap-Skript-Modifikation, kein Live-Betrieb-Risiko.

**Wert:** Mittel — Stationen mit häufigem Line-In-Use
(z.B. Live-Sendungen aus dem Studio) hätten dann auch
diese im Public-Log-Widget.  Stationen die fast nie
Line-In nutzen sehen keinen Unterschied.

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

(Aktuell leer — alle bekannten Bugs sind committed gefixt.)

---

## 📊 Wartungs-Metrik

| | Stand 2026-05-22 |
|---|---|
| Aktive Backlog-Items | 3 (Show-Shift, Record-per-Hour, Widgets — Welle 1 erste Hälfte fertig) |
| Deferred Items | 1 (JS-Modernisierung) |
| Hold Items | 1 (Payware) |
| Future Ideas | 13 |
| Known Bugs | 0 |

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
