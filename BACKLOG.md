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

## 📋 Arbeitsreihenfolge (Operator-Festlegung 2026-09-02)

Verbindliche Abarbeitungsreihenfolge, vom Operator am 2026-09-02
festgelegt.  Jeder Punkt bekommt vor Implementierung die
6-Punkte-Evaluierung + explizites Go (siehe ASSISTANT.local.md).

| # | Punkt | Sektion |
|---|-------|---------|
| 1 | ✅ Tascam-Ausgänge als lokales Monitoring | **DONE 2026-09-03** (`6464b17`) — Main-Output-Setting wirkt jetzt |
| 2 | ✅ Crossfade-Paket | **DONE 2026-09-27** — als „Show-Grenzen-Crossfade" gebaut (Operator-Go 2026-09-27): Track- und Show-Crossfade getrennt einstellbar, Show-Wert prägt Eingangswechsel, Titel-Attribut „No Fade during Crossover" (Migrationen 0059/0060; erst „Exclude from Crossover", gleicher Abend verfeinert: Überlapp bleibt, markierter Titel blendet nicht) ersetzt die 8-s-Regel, Fade-In/Out-Felder ausgeblendet; dabei den Butt-Splice des bisherigen Crossfades gefunden und behoben (Push vor Skip, Queue-Ahead).  Details CHANGELOG 27.09.; die 🟡-Items „Per-Track Crossfade" + „Frontend-Settings Fade" damit erledigt |
| 3 | ✅ CSRF-Token-Rotation entschärfen | **DONE 2026-09-10** — Rotation war wirkungslos (Session bereits schreibend geschlossen), Prüfung gehärtet (`7f51156`) |
| 4 | ✅ `getSqlTypes()`-Cast (DATETIME → PG) | **DONE 2026-09-10** — `datetime` → `timestamp` (`cdc8f0b`) |
| 5 | ✅ Show-Shift bei Overbook | **DONE 2026-09-27** — Filler-Erweiterung gebaut, zwei Live-Proben bestanden, zwei Juni-Bugs dabei gefunden und behoben (Marker `delayed_start_from` via Migration 0058, ganze Sekunden); Details CHANGELOG 27.09. |
| 6 | ✅ Seamless Bus-Mix | **CLOSED 2026-09-11** — alle drei Symptome durch die Liquidsoap-Migration erledigt (Belege im Item) |
| 7 | ✅ Storage-Umbau (Root → D:\stor) | **DONE 2026-09-16** — Stufe 1 flach/relativ (`6059dc4`), Stufe 2 Speicherort als Local-Machine-Einstellung mit Umzugs-Job (`c0b3c70`), Umzug nach D:\stor per UI abgenommen 09:43 |
| 7a | ✅ Cue-Marker-Test: 24/7-Aufnahme einschalten (Settings → Local Machine), Cue-Datei prüfen | **DONE 2026-09-16** — zwei Test-Shows 09:55–10:05 über die Stundengrenze: Paare mit Item-Kennung, kein überzähliger End-Marker, Offsets stimmen (Belege im Item „Cue-Marker-Test") |
| 8 | ✅ Stream-Metadaten (Stream Label, Off Air, Show-Namen) | **DONE 2026-09-13** — Off-Air-Text bei Stille, Stream Label wirkt, Webstream-Titel durchgereicht (`b997a7a`); live abgenommen 2026-09-13/14 (Datei-Show und Webstream-Show) |
| 9 | ✅ Recording-Loss bei Latency-Catchup | **CLOSED 2026-09-16** — Beobachtungsfrist bis 15.09. sauber: Catchups seit 06.09. einstellig pro Tag, seit 13.09. keine; 24/7-Stundendateien vom 16.09. exakt 3600 s (Belege im Item) |
| 10 | ✅ Backup/Restore via UI | **DONE 2026-09-17** — Stufe 1 (Manual, abgenommen 10:20), Stufe 2 (Media-Spiegel, abgenommen 15:31), Stufe 3 (Auto via Task Scheduler + Restore-Hinweis); Aufgaben-Registrierung durch den Operator offen — Details im Item |
| 11 | ✅ Pypo-NSSM-Resilience | **CLOSED 2026-09-16** — Beobachtungsfrist bis 15.09. sauber: seit 09.09. 20 PLAYOUT-Starts gegen 20 angeforderte Shutdowns, kein ungeplanter Neustart (Belege im Item) |
| 12 | ✅ Widgets | **DONE 2026-09-18** — drei Wellen + Player v2 (letztes Upstream-Widget, Wellen-Stil); alle 15 Embed-Endpoints live verifiziert; Player-Hör-Abnahme durch Operator 2026-09-18 |
| 13 | ✅ JavaScript-Stack-Modernisierung | **Kern DONE 2026-09-17** — Stufen 0-2 komplett, Migrate-Netz + FC1.5-Fork entfernt, UI-Politur; offen nur DataTables 2.0 (Entscheidung später, Operator 2026-09-17) + optionale Build-Pipeline — Details im Item |
| 14 | **Testplan erstellen** | neu 2026-09-02 — siehe unten |
| 15 | ✅ Legacy-mpv-Code löschen | **DONE 2026-09-10** — Liquidsoap ist die einzige Engine, DJ-Kick per Harbor-Telnet (`2590cf2`) |
| 16 | Internet-Erreichbarkeit | Ideen |

---

## 🎯 Aktive Backlog-Items (warten auf Operator-Go)

### ✅ Cue-Punkte prüfen: Cue-Out hinter dem Dateiende, stille Datei-Enden (neu 2026-09-30, Operator-Go 2026-09-30, DONE 2026-09-30)

**Gebaut 2026-09-30 (Reihenfolge 3 → 2 → 1, Weg A, Library-Mehrfachauswahl):**
`Application_Model_CuePoints` (detect / clamp / applyToFutureRows / relayoutInstances),
Titel-Editor kappt und reicht durch, Toolbar-Knopf „Cue Points" (`library/redetect-cue-points`,
> 15 min übersprungen).  Trockenlauf `C:/Temp/optd/cue_dryrun.php`: TOH 10 Uhr → 0–9,035 s,
Intro → 0–4,981 s, Showteaser unverändert; Durchreichen für Datei 593 trifft genau die 26
alten Zeilen der Dienstag-Serie.  Endpunkt live (200, JSON).  Architektur §23.45 / 0.52.
**Offen:** Operator wendet „Cue Points" auf die Jingles an (Library → Filter Jingles →
alle markieren → Cue Points), danach Kontrolle der Stunden-Folge in der Aufnahme.

**Befund (Testsendung 2026-09-30):** `cc_files.cueout` darf heute größer als die
Dateilänge sein (ID 593: 6,90 s bei 5,97 s — vermutlich Datei ersetzt, Cue blieb),
und der Analyzer setzt Cue-Out per `silencedetect` (−60 dB, ≥ 0,3 s) nur beim
Import; Jingles mit stiller Nachlaufzeit (576: 1,08 s) bleiben lang.  Bei
Überlapp 0 wird jede dieser Stellen als Pause hörbar.  **Ideen:** (a) Speichern im
Titel-Editor und Ersetzen der Datei kappen Cue-Out auf die Länge; (b) Job „Cue-Punkte
neu messen" für Bibliothek oder Track-Typ (wie „Measure missing files now"); (c)
Bericht „Titel mit Cue-Out > Länge / stillem Ende > 0,5 s".  Vorbedingung: Evaluierung.

**Nachtrag 2026-09-30:** Neu-Einfügen durch den Operator kopierte die neuen
Cue-Punkte in 213 von 239 Instanzen (verlinkte Serien); die Dienstag-17-Uhr-Serie
(1056 … 1839, 26 Zeilen) blieb alt.  Alle 24 TOH-Jingles enden 1,05–1,25 s vor
Cue-Out 9,90 still → jede volle Stunde ~1 s Pause.

**Evaluierung 2026-09-30 (Operator-Anfrage):**
1. *Machbarkeit:* ja.  Stille-Erkennung existiert im Analyzer (`analyze_cuepoint`,
   ffmpeg `silencedetect` −60 dB ≥ 0,3 s), läuft nur beim Import; `relayoutFutureInstances()`
   liest `clip_length` der Zeilen → Punkt 2 muss nur `cue_in/cue_out/clip_length` der
   künftigen, nicht gestarteten Zeilen nachziehen und dann neu auslegen.
2. *Eingriff:* Punkt 3 (Cue-Out ≤ Länge kappen) und Punkt 2 (Durchreichen) sind reines
   Legacy (`StoredFile::setDbColMetadata`, `Scheduler`).  Punkt 1 hat zwei Wege:
   **A** Legacy misst selbst (ffmpeg synchron je gewählter Titel, gleiche Parameter wie
   der Analyzer, Messung + Durchreichen + Layout in einer Transaktion; Nachteil:
   Erkennung doppelt implementiert, lange Dateien langsam → Schutz „> 15 min
   überspringen").  **B** Analyzer mit `cue_only` (Muster `loudness_only`), PUT an die
   API, dann Rückruf API → Legacy-v1-Endpunkt fürs Durchreichen (neue
   Abhängigkeitsrichtung Django → PHP, asynchron, aber jede Dateigröße).
3. *Aufwand:* Punkt 3 ~30 Zeilen; Punkt 2 ~80 Zeilen + Trockenlauf-Werkzeug; Punkt 1
   A ~150 Zeilen (Library-Mehrfachauswahl „Re-detect Cue Points", Controller,
   ffmpeg-Aufruf), B ~200 Zeilen über drei Komponenten.  Handbuch ×4, Tests.
4. *Dauer:* Punkte 3+2 ~0,5 Tag; Punkt 1 A +0,5 Tag, B +1 Tag.
5. *Sinn:* hoch — mit Überlapp 0 wird jede stille Nachlaufzeit hörbar (241 Jingles);
   ohne Punkt 2 muss nach jeder Cue-Änderung neu befüllt werden.  Nebenwirkung: kürzere
   Jingles verschieben die Stille ans Sendungsende (BBC-Zeile 302 s fest → ~3 s vor
   der nächsten Sendung), Webstream-Zeile entsprechend verlängern.
6. *Empfehlung:* Go in der Reihenfolge 3 → 2 → 1 (Weg A).  Offene Operator-Entscheidung:
   Weg A oder B für Punkt 1; Auslöser als Library-Mehrfachauswahl (empfohlen) oder je
   Track-Typ in den Settings.

### ✅ Crossfade je Track-Typ und „Exclude from Crossover" — 5 s Stille vor dem BBC-Webstream (Operator-Go 2026-09-29, DONE 2026-09-30 — Testsendung abgenommen)

**Abnahme 2026-09-30 08:00 (Testsendung „BBC", Instanz 2001, Log + 24/7-Aufnahme):**
Jingle-Folge Stoß an Stoß (`track/-/0.00`, Nachfolger startet am Ende des
Vorgängers, Kette läuft konstant 0,30 s hinter den Zeilen), das Relais-Gate
öffnete 08:01:07,02 nach der neuen Wartezeile „0.94 s of audio left" — die
BBC setzt in der Aufnahme bei 67,08 s ein, exakt Zeilenende + Lag.  Die 5-s-Stille
ist weg.  **Restliche Stille kommt aus den Dateien, nicht aus dem Playout:**
„Intro BBC News" (ID 593) hat Cue-Out 6,90 s bei nur 5,97 s Dateilänge (0,93 s
Leerlauf) und endet selbst mit 0,95 s Stille → 1,9 s Pause vor der BBC; „TOH-Jingle
8 Uhr" (576) endet 1,08 s vor seinem Cue-Out still, „Showteaser" (518) beginnt 0,4 s
leise.  Abhilfe: Cue-Punkte der Jingles nachziehen (siehe 💡 unten).  Dabei
gefunden und behoben: Live-Item nach Datei kam 1 s zu früh (`8c8d1c5`, Timer auf
ganzer Sekunde, Architektur §23.44 Nachtrag).

**Stand 2026-09-29 abends:** gebaut (Option C, beide Wege; `b28bc98`, `f36de90`).  Operator-Entscheidungen: Paar-Regel = kleinerer Wert;
Jingles 0 s; die 100 „No Fade"-Jingles auf „wie Track-Typ" zurückgesetzt (Sicherung
`C:/Temp/optd/no_fade_flags_backup_20260929.txt`); Quellenwechsel Datei ↔ Webstream/Line-In im Layout auf den
Show-Wert angeglichen.  639 kommende Instanzen neu ausgelegt.  **Offen:** API- und PLAYOUT-Neustart durch den
Operator, Apache-Neustart für die Übersetzungen, dann Abnahme an der nächsten Jingle-Folge (kein Vorlauf, keine
Stille vor dem Relais; nächste BBC-Instanz 2026-10-06) oder an einer Testsendung.

**Befund:** Die stündliche Folge TOH-Jingle → Dayteaser → Intro BBC News →
BBC-Webstream ist im Kalender Stoß an Stoß gelegt (Zeilenlänge ≈ Cliplänge,
Überlapp ≤ 1 s), der Track-Crossfade steht aber auf 3 s.  Liquidsoap
beginnt jeden Übergang 3 s vor dem Ende des alten Titels, der Nachfolger
startet also ~2–3 s vor seiner Zeile; nach zwei Übergängen endet das Intro
um 10:01:00,9, der Webstream beginnt planmäßig 10:01:06 → 5 s Stille
(24/7-Aufnahme: −70 LUFS von 10:01:01 bis 10:01:05, jede Stunde).
**Optionen (nicht evaluiert):** (a) Zeilen beim Ändern des Track-Crossfades
neu auslegen (Legacy-Scheduler, auch für bestehende Sendungen); (b) der
Playout begrenzt die Überblendung je Übergang auf den tatsächlichen
Zeilen-Überlapp; (c) kurze Elemente (Jingles unter N Sekunden) per
„No Fade during Crossover" kennzeichnen.  Vorbedingung: Evaluierung.

**Evaluierung 2026-09-29 (Operator-Frage: Track-Typ, Exclude-Flag oder beides?):**
- *Fakten:* Track-Typen Shows 31 / Music 64 / Jingles 241 (3–50 s, Ø 20 s) /
  News 0 / Ads 0, 42 Dateien ohne Typ; 100 der 241 Jingles tragen „No Fade
  during Crossover"; 312 künftige Jingle-Zeilen in 639 Instanzen.  Die
  bestehenden Zeilen der Stunden-Folge liegen Stoß an Stoß — bei Überlapp 0
  für Jingles passen sie OHNE Neu-Befüllen.  „Exclude" war am 27.09. schon
  gebaut (`07e6e1f`: Layout-Regel + „cut"-Form) und wurde am selben Abend
  zugunsten „No Fade" zurückgenommen (`336e86e`) — der Code liegt im Verlauf.
- *Gemeinsamer Kern beider Wege:* Überlapp D je ÜBERGANG statt global:
  (1) Liquidsoap-Form mit D als Variable (0 … BUFFER; D = 0 = Titel spielt
  aus, Nachfolger folgt), (2) Playout sendet D mit der Form, (3)
  Legacy-Layout legt das Zeilenpaar mit demselben D, (4) Job „künftige
  Zeilen neu auslegen" bei Änderung.
- *Option A — Crossfade je Track-Typ:* Feld „Crossfade Duration" am
  Track-Typ (leer = globaler Wert); Paar-Regel D = min(Typ links, Typ
  rechts).  + einmal einstellen, neue Importe erben; − Ausnahmen brauchen
  doch einen Schalter, 42 Dateien ohne Typ.
- *Option B — „Exclude from Crossover" je Titel:* Flag, schließt „No Fade"
  aus (UI sperrt wechselseitig).  + einfach, präzise, Code bekannt; − je
  Titel zu setzen (241 Jingles), neue Importe vergisst man, nur 0 oder
  global.
- *Option C — beides:* Typ liefert die Vorgabe, am Titel ein Dreiwege-Feld
  „Crossover: wie Track-Typ / No Fade / Exclude".  Aufwand: Kern ~1,5 Tage,
  A +0,5, B +0,5, Handbuch ×4 + Tests → ~2,5–3 Tage.
- *Empfehlung:* C in zwei Schritten — zuerst Kern + A (löst die Stille für
  alle Jingles auf einen Schlag, ohne Kalender-Eingriff), dann B als
  Ausnahme-Schalter.  Offene Operator-Entscheidungen: Paar-Regel (min),
  Wert für Jingles (0 oder 0,5 s), was mit den 100 „No Fade"-Jingles
  geschieht, Quellenwechsel Datei ↔ Webstream/Line-In (Layout nutzt heute
  den TRACK-Wert, der Playout blendet mit dem SHOW-Wert).

**Nachtrag 2026-09-29 (Frage „hilft Neu-Befüllen?"):** Nur teilweise.  Der
Legacy-Scheduler legt beim Befüllen JEDE Folgezeile um den Track-Crossfade
überlappend (`nextStart = end − crossfade`, ohne Typprüfung, auch vor einem
Webstream).  Bei 3 s: keine Stille mehr, aber der Block wird 9 s kürzer
(BBC-Relais beginnt ~10:00:58 statt 10:01:06), der Webstream startet 3 s
vor dem Ende des Intros und blendet es per Show-Crossfade (1 s) weg, und
das 6,9-s-Intro besteht fast nur aus Ein- und Ausblende.  Kern: 3 s
Crossfade passt nicht zu kurzen Jingles → Option (b) oder ein Crossfade je
Track-Typ (Jingle 0–0,5 s) ist der eigentliche Fix.

### 🟢 Loudness nach EBU R128 im Processing (Stufe 1 in Betrieb seit 2026-09-29 — Pegel-Abnahme an der Aufnahme offen; Stufe 2 unentschieden)

**Ist-Stand (geprüft 2026-09-28):**
- Einzige Lautheits-Verarbeitung heute: ReplayGain je Datei.  Der Analyzer
  misst mit ffmpegs `replaygain`-Filter — das ist **ReplayGain 1.0**
  (RMS-basiert, 89-dB-Referenz), NICHT die BS.1770/R128-Messung; 308 von
  377 Dateien haben einen Wert (Ø −4,8 dB, −14,9 … +16,7).  Angewendet als
  `replaygain_track_gain` im annotate → `amplify(override=…)` auf dem Bus;
  Schalter „Enable Replay Gain" + Modifier-Slider unter Settings → Streams
  (`enable_replay_gain` = 1).  Webstreams haben ein manuelles Input-Gain.
- Live-Quellen (DJ-Harbor, Webstream, Line-In) laufen ohne jede Regelung;
  kein Limiter am Bus-Ende.
- Werkzeuge vorhanden (Bench `xbench/bench_r128.liq` auf dem installierten
  Build): Liquidsoap 2.4.4 hat `lufs()` (Momentary/Short-term/Integrated
  nach R128), `normalize(lufs=true, target=…)` (LUFS-AGC, reines
  Liquidsoap), `limit()`, und die ffmpeg-Filter `loudnorm`, `ebur128`,
  `alimiter` (Filtergraph über die Tracks-API, eigener Clock; im Bench
  regelte `loudnorm` einen −9,7-LUFS-Ton sofort auf −23,0).  ffmpeg 9.0
  (C:\ffmpeg) hat `ebur128` + `loudnorm` für die Offline-Messung.

**Stand 2026-09-28 abends:** Stufe 1 gebaut (`b258e44`),
Zielwert frei mit Vorgabe −23 LUFS (Operator-Entscheidung).  Stufe 0 (Meter)
vom Operator vorerst abgelehnt.  Stufe 2 (Live-Regler) offen, Operator will
erst verstehen, was der Regler tut.  **Inbetriebnahme Stufe 1:**
ANALYZER-, API- und PLAYOUT-Neustart durch den Operator, dann Settings →
Streams → Loudness Normalization = EBU R128, Save, „Measure missing files
now" (≈ 377 Dateien, wenige Minuten), Hörprobe.

**Inbetriebnahme 2026-09-29:** Modus r128 / −23 LUFS / −1 dBTP seit 08:51,
Bibliothek 373 von 373 gemessen (Ø −14,7 LUFS, −35,8 … −4,9).  Dabei
behoben: Wrapper-Parameter (`c41e27c`, PLAYOUT startete nicht),
True-Peak-Kappung nur für Anhebungen (`83b5749`), Titel-Verstärkung auf der
Queue statt auf dem Bus (`60b3f56` — seit dem Crossfade-Umbau galt die
Verstärkung des ersten Titels für die ganze Strecke), tolerantes Lesen der
ffmpeg-Ausgabe (`a361002`).  Skript mit Queue-Gain aktiv seit 09:08.
**Pegel-Abnahme bestanden 2026-09-29 10:00** (24/7-Aufnahme, ffmpeg ebur128):
TOH-Jingle −23,6 / Dayteaser −23,3 (nach Crossfade) / Intro −24,1 (3 s) /
Dayteaser −23,5 LUFS, Spitzen −8,4 … −10,5 dBFS; BBC-Webstream −17,1 LUFS
(Input-Gain +3 dB), Cloud-Webstream −17,2 LUFS (Gain 0).
**Offen:** (2) Operator-Entscheidung zum Pegelsprung Datei ↔ Live-Quelle —
der Cloud-Webstream kommt mit −17,2 LUFS an (gemessen), also 6 dB über dem
Ziel: Zielwert anheben, Webstream-Gain senken oder Stufe 2.

**Plan in Stufen (jede einzeln abnehmbar):**
- **Stufe 1 — R128-Messung + Zielwert + Limiter (~1,5–2 Tage):**
  Analyzer misst mit `ebur128` statt `replaygain`: integrierte Lautheit
  (LUFS), True Peak (dBTP), Loudness Range (LU) → neue Spalten in
  `cc_files` (Migration 0061), `replay_gain` bleibt als abgeleiteter Wert.
  Settings → Streams: Modus „Off / ReplayGain (bisher) / EBU R128",
  Ziel-Lautheit (Vorgabe −23 LUFS; Streaming-Praxis liegt bei −16 … −18,
  frei wählbar), True-Peak-Grenze (−1 dBTP).  `schedule.py` rechnet die
  Titel-Verstärkung = Ziel − gemessene Lautheit (statt RG + Modifier), über
  das bestehende annotate-Feld → keine Liquidsoap-Änderung für Dateien.
  Am Bus-Ende `limit()` als Peak-Sicherung (Sample-Peak; echtes True-Peak
  braucht Oversampling — bei −23 LUFS Ziel ist der Headroom groß).
  Neu-Messung des Bestands als Job (Analyzer-Queue; ~377 Dateien ≈ 20 min).
  Tests, Handbuch ×4.
- **Stufe 0 (optional, in Stufe 1 integrierbar, ~0,5 Tag) — Meter:**
  `lufs()` am Bus, Werte per Telnet/HTTP → Anzeige „Lautheit jetzt /
  letzte Stunde" (Settings oder Dashboard) zur Kontrolle der Einhaltung.
- **Stufe 2 — Live-Quellen (~1 Tag):** `normalize(lufs=true,
  target=Ziel, window=3, gain ±12 dB)` auf den Live-Armen (DJ, Webstream,
  Line-In), per `interactive.bool` schaltbar, Ziel per Telnet; Hörprobe
  mit BUTT und einem Webstream.  Reines Liquidsoap, kein ffmpeg-Graph im
  Sendeweg (Speicher-/Thread-Disziplin auf dem Windows-Build, vgl.
  Select-Leck).
- **Nicht empfohlen als Standard:** `loudnorm` in Echtzeit über den ganzen
  Bus.  Der Filter regelt im Einpass-Modus dynamisch (hörbares Pumpen bei
  Musik), legt einen eigenen ffmpeg-Clock in den Sendeweg und macht die
  Titel-Messung überflüssig — als Option für reine Sprachsender denkbar.

**Sinn:** Gleichmäßige Lautheit zwischen Titeln, DJs und Zuspielern ist
für Hörer das spürbarste Qualitätsmerkmal; R128 ist die Norm dafür, die
heutige RG-1.0-Messung ist ein Näherungswert.  **Aufwand gesamt:** ~3–4
Tage inkl. Proben.  **Vorbedingungen:** Operator-Go je Stufe;
Zielwert-Entscheidung (−23 LUFS Norm vs. lauteres Streaming-Ziel);
Neu-Messung läuft im Hintergrund, Sendebetrieb bleibt unberührt, bis der
Modus umgeschaltet wird.

### ✅ Catch-up steigt am Offset ein, Zeilenverschiebung der laufenden Zeile ohne Neustart (Operator-Go 2026-09-28, DONE 2026-09-28 — beide Proben bestanden)

**Status 2026-09-28:** Teile A und B gebaut und getestet (`0f62b14`, 699
Tests grün, CHANGELOG „Fixed", Architektur §23.40).  Wirksam nach
PLAYOUT-Neustart.
**Probe A bestanden 2026-09-28 19:59:** Neustart im Titel → „Catch-up …
entering at +36.2 s", `cue_in=36.63s` (0,40 + 36,2), Titel lief an der
richtigen Stelle weiter.
**Probe B bestanden 2026-09-28 20:27:23:** spätere Zeile der laufenden Sendung
entfernt → „Playing event …file-6272 is keyed …18-27-20#file-6272 (same item,
re-timed) - rebinding, no teardown“, kein Stop, kein PLAY-Neuansatz; zusätzlich
„Catch-up skipped: … precedes the playing item“ für die ebenfalls neu
terminierte Vorgängerzeile.  Die Probe deckte einen dritten Fehler auf: der
geplante Liquidsoap-Grenz-Neustart (Skript geändert) leerte die Queue, der
Scheduler adoptierte den vorgelegten Nachfolger aus der alten Instanz →
Stille bis zur nächsten Zeile; behoben `29236a9` + `d098f1a` (Queue-Ahead-
Buchführung nach jedem erkannten Liquidsoap-Neustart verworfen).  Live um
20:44:54 zusätzlich bestätigt: Plausibilitätsgrenze („50.4 s left cannot
belong to …, no skip“) und Grenz-Refresh-Schutz griffen ohne Aussetzer.
**Historie Probe B:** 20:00:08 und 20:05:53 wurde jeweils der LAUFENDE Titel
entfernt — LibreTime kürzt den auf „jetzt" (Truncate), der Scheduler stoppt
zu Recht und der Nachfolger steigt am Offset ein.  Der Fall von 18:30
(laufende Zeile neu terminiert, gleiche Row-ID) braucht das Entfernen
einer SPÄTEREN Zeile der laufenden Sendung.  Erfolgskriterium: kein
„removed from schedule" für die laufende Zeile, kein PLAY-Neuansatz.
**Nebenbefund 20:05:35 (behoben, eigener Changelog-Eintrag):** Refresh über
eine Titelgrenze holte den Vorgänger nach + implausibles Engine-„remaining"
→ 19 s Stille; Fixes `_precedes_playing()` und Plausibilitätsgrenze.

**Befund (Playout-Log 2026-09-28):**
- **Neustart mitten im Titel (18:21):** Catch-up spielt den laufenden
  Titel von vorn (`PLAY 'Fade'` obwohl 141 s gelaufen; beim nächsten
  Titel „predecessor has 140.3 s of audio left, rows said 2.3 s").  Der
  Hörer hört den Anfang noch einmal, am Zeilenende schneidet der
  STOP-Timer hart ab.  Die Resume-Pfad nach DJ-Auflegen (`Resume
  scheduled: … at +N s`) seekt bereits per `liq_cue_in`; der Catch-up in
  `_arm_file_event` reicht den Versatz nur nicht weiter.
- **Show-Builder-Änderung an der laufenden Sendung (18:30:16, `POST
  /showbuilder/schedule-remove`):** LibreTime terminiert die Folgezeilen
  neu, auch die laufende (Row 6252: Start 16:26:41 → 16:26:50, Cue-In
  0 → 2,18 s, gleiche Row-ID).  `_same_scheduled_item` vergleicht
  Row-ID **und Start** → „removed from schedule", Stop, Catch-up startet
  denselben Titel von vorn, eine Sekunde später übernimmt der Nachfolger
  per `track_skip`.  Hörbar: kurzer Neuansatz von „Lovemachine".
  Derselbe Identitätsvergleich lässt auch einen vorgelegten Nachfolger
  (`_queued_ahead`) nach einer Verschiebung als „stale" verwerfen →
  harter Schnitt statt Crossfade.

**Plan (zwei Teile, je ein Commit):**
- **A — Catch-up am Offset (≈ 20 Zeilen + Test):** Catch-up-Zweig in
  `_arm_file_event` übergibt `seek = now - event.start`;
  `_on_file_start(key, event, seek=0.0)` addiert ihn auf `cue_in`
  (Muster des Resume-Pfads, Zeile ≈ 3123); liegt der Versatz hinter
  `cue_out`, kein Start (Zeile ist vorbei, STOP-Timer läuft ohnehin).
  Log „Catch-up … at +N s".
- **B — Zeilenverschiebung ohne Neustart (≈ 30 Zeilen + Tests):**
  Identität für Datei-/Webstream-Zeilen = Row-ID + Medium (Datei-ID /
  URL), Start nicht mehr Teil der Identität (Line-In behält Gerät +
  Kanal-Mapping).  Im Refresh-Block: gleiche Zeile, neuer Start ≤ jetzt →
  nur Key rebinden, kein Teardown; neuer Start in der Zukunft → wie
  bisher stoppen und zum neuen Start regulär starten.  Vorgelegter
  Nachfolger überlebt die Verschiebung (Zeile 1534 nutzt dieselbe
  Identität).
- **Live-Probe:** PLAYOUT-Neustart mitten im Titel (A); Zeile im
  Show-Builder aus der laufenden Sendung entfernen (B), Log auf
  „rebinding" statt „removed from schedule" prüfen.

**Aufwand:** ~50 Zeilen in `playout_scheduler.py`, ~80 Zeilen Tests in
`test_scheduler_linein.py`; keine Migration, keine UI, keine neue
Abhängigkeit.  **Dauer:** A 1–2 h, B 2–3 h inkl. Live-Proben, zusammen
ein halber Tag.  **Risiko:** gering — A nutzt den bestehenden
Resume-Mechanismus, B entschärft einen Vergleich, der 2026-09-04 gegen
Key-Instabilität eingeführt wurde (Row-IDs sind serial, werden nie
wiederverwendet).  **Vorbedingung:** Operator-Go; PLAYOUT-Neustart nach
dem Commit.

### 🟡 Benutzergruppen-Audit: Wer darf was? (Operator 2026-09-17)

**Anlass:** Die Rechte-Prüfung steht aus — vor allem für die neuen
Features.  Zu klären, je Rolle (Admin / Programm-Manager / DJ / Gast):
- Settings → Backup (Ordner, Auto-Backup, Download der ZIPs mit
  Config-Passwörtern!) — heute Controller-ACL `preference` wie alle
  Settings-Seiten.
- Import vom FTP-Server (Zugangsdaten!) + Import-Ordner-Pfad.
- Media Library Location (Umzugs-Job!).
- Line-In-Editor nach der Konsolidierung 2026-09-17: Kanäle kann
  jetzt jeder mit Line-Inputs-Zugriff ändern (vorher Admin-Sektion;
  der Aktiv-Schalter wurde am selben Tag ganz entfernt) —
  bewusste Entscheidung auf der Ein-Personen-Instanz, beim Audit
  wieder anfassen.
- Podcasts, Widgets-Konfiguration, Restart-Aktionen.
**Vorgehen bei Go:** Ist-Matrix aus ACL/Controller-Ressourcen erheben,
Soll-Matrix mit dem Operator festlegen, Lücken schließen, Manual
USERS_AND_ROLES aktualisieren.  Aufwand grob 1-2 Tage.

> **Leitlinie (Operator, 2026-09-04):** *„Ich möchte so weit wie möglich
> einen Seamless-Mix beim Wechseln zwischen verschiedenen Inputs
> erreichen."*  Gilt für alle Übergänge File ↔ Webstream ↔ Line-In.
> Darauf zahlen ein: „Quellen vorwärmen — Gate im Bus-Switch",
> „Webstream-Puffer-Nachlauf", das Crossfade-Paket (#2) und die
> Line-In-Latenz-Arbeit.  Bei Bewertungen dieser Punkte ist das
> Kriterium „hörbar nahtlos?" das entscheidende.

Diese sind technisch evaluiert, empfohlen, und können starten sobald
der Operator das Signal gibt.

### ✅ Event-Keys stabil machen — „Option B" (neu 2026-09-04, umgesetzt 2026-09-10)

**Umgesetzt 2026-09-10 (Operator-Go, Punkt 3):** Keys
`<Zeitstempel>#<Typ>-<Identität>` (`make_event_key`), Details im
CHANGELOG „Event-Keys mit Identität".  Option A (Rebinding) bleibt als
Absicherung.  Live-Abnahme: Show-Folge Line-In → Jingles + Webstream →
Line-In ohne Rebinding-Logzeilen (`grep -i rebind logs/playout-stdout.log`).

**Problem:** `player/schedule.py::insert_event` bildet Event-Keys aus
dem Startzeitpunkt und hängt bei Kollisionen `_0`, `_1`, … nach
**Einfügereihenfolge** an.  Show-Record-Start/-End, das
Webstream-Buffer/Output-Paar und der erste Inhalt einer Show teilen sich
regelmäßig eine Sekunde.  Fällt ein solches Event aus dem Abruffenster
(z. B. das Record-End der Vorshow, sobald die Vorshow vorbei ist),
rutschen die Suffixe der Überlebenden nach — derselbe laufende Slot kam
live als `…-09-07-00_0` und einen Refresh später als `…-09-07-00`
zurück (2026-09-04 11:08:17, Teardown + Catch-up = 9 s Loch).

**Stand:** Option A ist umgesetzt (2026-09-04, `ff567ce`): Removed-Check
und Catch-up vergleichen Item-Identität statt Keys und binden nur um.
Live-Abnahme 14:55–15:20: die Wanderung trat erneut auf (Line-In
`…-13-07-00_0` → `…-13-07-00` um 15:08:50, Webstream `_1` → `_0` um
15:12:52) und wurde beide Male per Rebinding ohne Teardown abgefangen.
Das neutralisiert das Symptom vollständig, lässt die Ursache aber
stehen — jeder Refresh produziert weiterhin Rebinding-Logzeilen.

**Option B (empfohlen, Operator-Bauchgefühl 2026-09-04 ebenfalls):**
Keys deterministisch aus Zeitstempel **plus Identität** bilden
(Typ + Row-ID bzw. Show-Instanz), nie aus Einfügereihenfolge.  Dann
gibt es keine Suffix-Wanderung mehr, Logs werden lesbarer
(`2026-09-04-09-07-00#linein-4711` statt `_0`), und Option A wird zur
reinen Absicherung.

**Vorbedingungen / Aufwand:**
- Formatwechsel im ganzen Playout-Modul; Keys sind dort zwar opak
  (nur `start_key`/`end_key` werden aus Zeitstempeln gebildet, nichts
  parst Keys), aber jede Stelle, die Keys loggt oder vergleicht, muss
  einmal durchgesehen werden.
- Sechs Upstream-Fixtures in `backend/playout/tests/player/schedule_test.py`
  pinnen das `_0`/`_1`-Format und müssen nachgezogen werden.
- Sortierung `dict(sorted(events.items()))` bleibt zeitlich korrekt,
  solange das Suffix hinter einem Trennzeichen steht, das nach Ziffern
  sortiert (`#` oder `~`).
- Muss in einem Rutsch stimmen (kein Mischbetrieb alter/neuer Keys);
  Live-Abnahme mit der Show-Folge Line-In → Jingles + Webstream → Line-In.
- ~80–120 Zeilen + Tests, ~3 h.

### ✅ Webstream-Puffer verschiebt und verkürzt das Folgeelement (beobachtet 2026-09-04, durch die Bus-Gates erledigt, abgehakt 2026-09-10)

**Abgehakt 2026-09-10:** mit den Gates aus „Paket 2" schließt
`webstream_stop` zuerst das Gate (Playout-Log 2026-09-08: STOP
15:14:00,016 → „webstream_gate: closed" 15:14:00,065), der Switch
fällt sofort auf den Sendeplan zurück und der Rest im 5-s-Puffer wird
verworfen statt abgespielt; die Folgeelemente der Phase-E-Shows
starteten sekundengenau.  Die Beobachtung stammt vom Nachmittag des
04.09., vor dem Paket.

**Beobachtung (Live-Abnahme 14:55–15:20):** Der Webstream-Zweig hängt
hinter `buffer(buffer=5.0, …)` (Phase-E-Clock-Bridge).  Beim
`webstream_stop` läuft dieser Puffer erst leer, bevor `switch.2` auf
den Scheduled-Zweig zurückfällt — der Showteaser (15:06:08–15:06:58,
50 s) startete daher erst 15:06:13 und wurde um 15:06:58 nach 45 s
abgeschnitten.  Analog um 15:20:05.  Beim Start dagegen 5 s (BBC) bzw.
9 s (cloud.example.org) Stille bis `Switch to amplify` — das ist die
dokumentierte Buffer-up-Latenz.

**Nicht Teil der 2026-09-04-Fixe** (Verhalten war vorher identisch, die
Fixe haben es nur sichtbar gemacht, weil die Übergänge jetzt stimmen).

**Ideenrichtung (nicht evaluiert):** (a) `webstream_stop` mit
`buffer`-Flush statt Leerlaufen; (b) den Folge-Push um die
Pufferlänge vorziehen; (c) Puffer 5 → 2–3 s, gegen Reconnect-
Robustheit abwägen (Phase-E-Lektion: zu kleiner Puffer → „Buffer
emptied"-Flattern).  Vorbedingung: Operator-Go + Hörtest, Sendeweg.

### ✅ Cue-Sheet: überzähliger „end"-Marker bei überholtem STOP (beobachtet 2026-09-04, behoben 2026-09-10)

**Behoben 2026-09-10 (Operator-Go, Punkt 4):** (a) und (b) zusammen —
der Marker wird erst nach dem Ownership-Re-Check geschrieben, und
`start`/`end` tragen `item` = Schedule-Row-ID.  Details im CHANGELOG
(Fixed).

**Mechanismus:** `_on_stop` schreibt `cue_item_end(kind)` *vor* dem
Ownership-Re-Check.  Gewinnt der Nachfolger das Rennen (live bei
**jedem** File→File-Übergang der Fall: „superseded … during
teardown"), ist `_current_event` schon der Nachfolger, und der Marker
landet ~30 ms nach dessen `start`-Marker als „end" seines Typs.  Der
Sidecar (`cue_writer.py`, flache Markerliste, kein Item-Bezug) enthält
dann `start(B) → end(B)` im Abstand von 30 ms.  **Vorbestehend** — der
alte Pfad schrieb denselben Marker und überschrieb danach zusätzlich
die Buchführung.

**Vorbedingung:** Es gibt noch keinen Leser für `*.cues.json` im Repo
(nur Writer + Test).  Sobald der 7-Tage-Catchup / die Cue-Auswertung
gebaut wird, entscheiden: (a) Marker erst nach dem Re-Check schreiben
(überholter STOP schreibt nichts; `start` des Nachfolgers impliziert
das Ende) oder (b) Marker mit Item-Identität (row_id) versehen, damit
der Leser Paare bilden kann.  (b) ist robuster.

### ✅ Quellen vorwärmen — Gate im Bus-Switch (Operator-Idee 2026-09-04, umgesetzt 2026-09-04 abends als „Paket 2", abgehakt 2026-09-10)

**Abgehakt 2026-09-10:** seit „Paket 2" (CHANGELOG „Nahtlose
Eingangswechsel: Bus-Gates, Übergangsfunktionen, Vorwärmen") live —
`PREPARE_LEAD_SECONDS` = 10, Gates `webstream_live`/`linein_live`,
Playout-Log z. B. 2026-09-09 17:06:50 „Prepare … pre-buffering",
17:07:00 „was pre-buffered - opening the gate".  Die Überschrift war
veraltet.

**Idee (Operator):** Webstreams und Line-Ins ~10 s vor dem Play-Zeitpunkt
laden, damit sie beim Start sofort spielen.

**Befund:** Möglich, aber nicht „einfach früher starten" — der Bus
wählt heute jede Quelle, sobald sie `source.is_ready` ist
(`rastatime.liq`: `switch([... (is_ready(webstream), webstream),
(is_ready(linein), linein), ({true}, scheduled)])`).  Früh verbinden
hieße früh auf Sendung = das Vorgänger-Element wird abgeschnitten.
Es braucht ein **Gate**: `webstream_live = interactive.bool(...)`,
`linein_live = interactive.bool(...)`; Prädikat `{webstream_live()
and source.is_ready(webstream)}`; Telnet `var.set`.  Pypo bekommt pro
Event einen zweiten Timer „prepare" bei T−10 s (Verbinden/Capture +
http-Quelle starten, Gate zu), bei T nur noch Gate auf → Umschaltung
sofort; Stop = Gate zu + Quelle stoppen.

**Nutzen:** Webstream-Startstille (5 s = `buffer(buffer=5.0)`-
Vorpufferung; BBC 5–6 s, cloud.example.org 5–9 s) → ~0 s, ohne den
Puffer zu verkleinern (Phase-E-Lektion: kleiner Puffer flattert bei
Jitter).  Line-In-Startlücke → ~0 s.  **Kein Effekt auf das
Abschneiden am Line-In-Ende** (Latenz L bleibt) — siehe Eintrag
„Line-In-Startlücke".

**Randfälle:** Vorgänger ist Line-In auf demselben Gerät mit anderer
Kanalwahl → Capture kann nicht früh gebounct werden (Vorgänger würde
stumm) → kein Prepare, Bounce bei T wie heute.  Gleiche Kanalwahl →
Same-Device-Transition ist schon nahtlos, Prepare überflüssig.
Schedule-Refresh: ein bereits „prepared" Item, das verschwindet, muss
zurückgebaut werden (Gate zu, Quelle stoppen).  DJ auf Sendung: Gate
irrelevant (DJ steht höher im Switch).

**Aufwand:** `.liq`-Template ~40 Zeilen (2 Bools, 2 Prädikate, 4
Server-Kommandos), Telnet-Client +4, Engine +4, Scheduler ~150 Zeilen
(Prepare-Timer, Handler, Refresh-Rückbau), ~12 Tests, Manual 4×.
~1 Tag + Live-Abnahme (Clone-Workflow + Monitor vorhanden).
Eingriff: Bus-Switch + Scheduler = Sendeweg, aber mit klarem Fallback
(Gate-Variablen default `true` = heutiges Verhalten).

**Erweiterung 2026-09-04 (nach der Latenz-Runde, Rest = 2 s vorne und
2 s hinten):** Das Gate kann auch das **Slot-Ende** retten.  Heute
schließt der Nachfolger die Quelle bei E sofort; die 2 s im Puffer
gehen verloren.  Mit Gate: bei E nur `linein_live := false` → der
Bus-Switch wechselt zum Nachfolger **mit Übergangsfunktion**
(`switch(transitions=…)`: alte Quelle ~2 s ausblenden, während ihr
Puffer ausläuft, neue Quelle einblenden) → die letzten 2 s des
Moderators sind hörbar, unter dem beginnenden Jingle; `linein_stop`
+ Capture-Stop erst bei E+3 s (Timer).  Heute hat der Bus-Switch keine
Übergangsfunktionen (nur `cross` innerhalb der Queue).  Gleiches
Prinzip beim Webstream-Ende (5-s-Puffer-Nachlauf → kurzer Crossfade
statt Verzögerung des Folgeelements).  Das ist die technische Form der
Leitlinie „Seamless-Mix".  Aufwand +~0,5 Tag (Transition-Funktion,
verzögerter Stop, Tests), Gesamt ~1,5 Tage.  Designfrage an den
Operator: Crossfade-Länge (1–2 s) und Charakter (echtes Überblenden
vs. „Ducking": Jingle sofort voll, Line-In darunter ausblenden).

**Empfehlung:** Go — nach Paket „Line-In-Latenz" (abgenommen) ist das
der nächste Schritt zur Leitlinie.

**UMGESETZT 2026-09-04 (abends, Go des Operators; Crossfade 1 s,
0 = Ducking):** Teil A (`eabf798`, `b92c08a`, `1a150a0`): Gates +
Übergangsfunktionen im Bus-Switch, Haus-Crossfade aus Settings →
General.  Teil B (`6820158`): Prepare-Timer, Gate-Start, Freigabe
mit Drain, Refresh-Rückbau, Gate-Reset beim Start.  Der exakt
gerenderte Bus-Block wurde isoliert mit Sinus-Quellen geprüft
(Crossfade 1 s: 1,0 s aus / 1,0 s ein; Ducking: neu sofort voll, alt
über 1 s darunter aus).  **Live abgenommen 2026-09-04 19:50–20:22**
(sechs Shows, Crossfade 1 s, Ohr + Monitor): Line-In vorgewärmt 0,15 s
Startlücke, gleiches Gerät nahtlos, Freigaben mit hörbarem Nachlauf,
BBC/Cloud sofort auf Sendung, Showteaser pünktlich.  Zwei
Nachbesserungen (`59c8e8f`): Prepare bei Refresh im Fenster sofort;
gleicher Stream → gleicher Stream als Übergabe.  Zuvor: Sendeausfall
19:26–19:35 durch Typfehler bei den DJ-Armen (`acdde5c`), Lehre
„Prüf-Render in Produktionsform".

### 🟢 Cloud-Stream-Aussetzer — Ursache gefunden, Webstream-Wächter gebaut 2026-09-06 (`405b200`), Live-Abnahme 2026-09-07 offen

**Beobachtung 2026-09-04 20:07:** Die einzige vorgewärmte Cloud-
Verbindung des Abends (`cloud.example.org:3001`, Prepare 20:06:50,
Gate auf 20:07:00) wurde 17 s nach dem Verbinden vom Server
zurückgesetzt (`Error 10054`), danach Puffer leer → Stille →
Reconnect 20:07:29 → erneut Abriss 20:07:39 → `-138` → Reconnect
20:07:59.  Icecast-Ausgänge blieben verbunden (kein Stream-Abriss),
die Show war aber bis ~20:08 zerhackt.  Die 20:12-Show auf demselben
Stream (Übernahme, kein Prepare) lief fehlerfrei; BBC (vorgewärmt
20:00:53) ebenfalls.

**Hypothesen:** (a) Upstream-Wackler zu genau dieser Zeit (`-138` =
Host unreachable spricht dafür); (b) der Server kickt einen Client,
der während der Gate-zu-Phase nicht liest — rechnerisch stallt die
Kette aber erst nach Bridge-`max` (10 s) + `max_buffer` (10 s) = 20 s,
der Reset kam bei 17 s.

**Test:** Zwei Cloud-Shows mit ≥ 10 s Vorlauf (vorgewärmt) und zwei
per Übernahme/ohne Vorlauf, jeweils Log auf `10054`/`-138` und
„Buffer emptied" prüfen.  Tritt der Reset nur vorgewärmt auf:
Prepare-Vorlauf für Webstreams auf 5 s senken (unter Bridge-`max`)
oder Bridge-`max` erhöhen.

**Ergebnis 2026-09-05 (erledigt):** Vier Cloud-Slots live (11:42–
12:15) plus isolierte Runden (`C:/Temp/prewarm_ab.py`, `prewarm_ab2.py`:
Gate 10 s bzw. 20 s geschlossen, mit/ohne `output.dummy`-Keep-alive,
direkt ohne Vorlauf).  Der Shoutcast-Upstream stallt in **jedem**
Modus (Muster: ~45–65 s Ton, dann „Buffer emptied" → `-138` nach
weiteren 20–25 s → Reconnect), auch mit Keep-alive-Konsument, auch bei
sofort offenem Gate; BBC läuft in allen Modi stabil.  `-138` ist
Windows/MSVC `ETIMEDOUT` (nicht „host unreachable"), `10054` =
WSAECONNRESET.  Hypothese (b) ist damit widerlegt — das Vorwärmen ist
nicht die Ursache.  Follow-up ist ein Upstream-/Netzthema (Cloud-
Server bzw. Strecke), kein Playout-Fix; Pre-Warm bleibt wie gebaut.

**Hörtest des Operators (11:36, Show „vah", Cloud-Stream):** ~60 s
ohne Signal.  Log: Verbindung 11:35:50 (Prepare), erstes dekodierbares
Audio erst 11:36:06 (16 s — länger als der 10-s-Vorlauf), auf Sendung
11:36:11, Puffer leer 11:36:18 (der Server stallte nach 7 s), `-138`
11:36:23, Reconnect dekodiert 11:37:05, wieder auf Sendung 11:37:10 →
52 s Stille.  Gleiches Muster wie in den A/B-Runden.
**Optionen, falls der Upstream so bleibt (Go nötig, je ~30 min):**
(a) `timeout` des Webstream-`input.http` 10 → 5 s und `poll_delay`
2 → 1 s: Erholung ~25 s statt ~50 s; (b) Prepare-Vorlauf für
Webstreams 10 → 15 s (`PREPARE_LEAD_SECONDS` je Typ), damit ein
langsamer Erst-Connect wie hier vor dem Slot-Start fertig ist.

**Bewertung 2026-09-05 abends (Operator: „Können wir den Upstream
angehen?"):** Server ist `DEVAStreamServer 1.4` (DEVA-Broadcast-
Encoder/Appliance, `icy-name: Event Calendar`, 320 kbit/s),
Host `ip10.isp.example.net` (203.0.113.10, the provider), Pfad ~25 ms
ohne Hop-Verluste, ICMP geblockt.  Zwei nackte, ständig lesende
Hörer (`C:/Temp/cloud_probe.py`, 19:09–19:15): 360 von 360 Sekunden
Daten, keine Lücke, kein Abbruch.  Log-Statistik seit 29.08.: die
täglichen 12:07/17:07-Cloud-Shows liefen am 01.–03.09. ohne
Aussetzer; alle Aussetzer treffen die Verbindung in den ersten
6–60 s nach dem Verbinden (02.09. 17:07:18, 04.09. 20:07 Reset nach
17 s, 05.09. 11:36 nach 7 s auf Sendung, 17:06:56 `-138` sechs
Sekunden nach dem Pre-Warm-Connect), die zweite Verbindung hält dann
(heute 17:07–17:15 lückenlos).  Zweite Sonde (`cloud_probe2.py`,
19:17–19:32): zehn frische Verbindungen im 90-s-Takt, jede mit ersten
Daten nach ~150 ms und ohne Lücke; Kontrolle 15 min sauber; der
absichtlich langsame Leser (4 KB/s statt 40) bekam nach 48 s
(192 KB) **keine Daten mehr** und wurde nach 328 s vom Server
zurückgesetzt (10054).  Die DEVA stoppt also einen Client, der nicht
mitliest, und wirft ihn später raus — vom Studio-Netz aus sind frische
Verbindungen abends dagegen unauffällig.  Die Live-Aussetzer fielen
alle in Phasen mit mehreren Verbindungen von unserer IP (Live-Show
plus Tests) bzw. in die Sendezeiten der DEVA — der Betreiber (der
Operator selbst) prüft Listener-Limit, Puffer und Log der DEVA.
**Optionen:** (1) Erholung beschleunigen: Webstream-`input.http`
`timeout` 10 → 3 s, `poll_delay` 2 → 0,5 s, Bridge 5 → 10 s, optional
`format="mp3"` per Webstream-Zeile (Autodetect kostet ~5 s) — ein
Stall unter ~10 s wird unhörbar überbrückt, ~1 h; (2) **Dauerverbindung
(„pinned")** für diesen Stream: Quelle bleibt 24/7 verbunden, Slot-
Start öffnet nur das Gate — nutzt den Befund „frische Verbindungen sind
fragil, stehende halten"; entweder Flag am `webstream`-Datensatz mit
Scheduler-Sonderfall (Release schließt nur das Gate) oder zweite
`input.http`-Quelle mit eigenem Bus-Arm, ~½ Tag; (3) Server-Seite:
DEVA-Weboberfläche (Listener-Limit, Puffer, Logs) durch den Betreiber
prüfen; (4) falls der Inhalt eine produzierte Schleife ist: als Datei
in die Library, kein Netz im Sendeweg.  Empfehlung: 1 sofort, 3
parallel anfragen, 2 wenn die Sonde die Fragilität frischer
Verbindungen bestätigt.

**Umgesetzt 2026-09-05 (Operator-Go, `860ebee`): Option 1.**
`timeout` 3 s, `poll_delay` 0,5 s, Bridge 10 s (`max` 20 s), Webstream-
Vorlauf 20 s (`WEBSTREAM_PREPARE_LEAD_SECONDS`, Line-In bleibt 10 s).
Nebenbefund E1 (`C:/Temp/prewarm_drain.py`): bei geschlossenem Gate
liest Liquidsoap 100 s lang durchgehend weiter (`webstream.buffer_length`
≈ 0, Server sah keinen blockierten Send) — das Vorwärmen erzeugt
keinen Backpressure, die DEVA-Aushungerung trifft uns dadurch nicht.
**A/B E2 (`C:/Temp/stall_ab.py`, lokaler Server, der jede Verbindung
30 s nach dem Connect für 6 s schweigt, ohne Burst beim Reconnect):**
alte Werte — erster Stall vom Startpuffer geschluckt, zweiter Stall
hörbar (11 s Stille: 6 s Stall + 5 s Neu-Puffern); neue Werte — erster
und zweiter Stall unhörbar (Timeout nach 3 s, Reconnect + Decode in
~2 s), dritter Stall hörbar (14 s Stille), weil jeder Reconnect ~5–6 s
Puffer kostet und der Testserver nichts nachliefert.  Lehre: **ein**
Stall bis ~9 s wird überbrückt, wiederholte Stalls innerhalb einer
Minute leeren die Bridge trotzdem; und wenn es doch zum Aussetzer
kommt, dauert das Neu-Puffern jetzt 10 s statt 5 s.  Die echte DEVA
stallt pro Verbindung höchstens einmal (Show-Start) und hält ~5 s
Client-Puffer, der beim Reconnect als Burst kommt — damit füllt sich
die Bridge nach jedem Reconnect wieder.
Option 4 entfällt (Live-Signal).  Option 2 (Dauerverbindung) bleibt
🟡 in Reserve: die Sonden zeigten frische Verbindungen abends stabil;
Option 3 macht der Operator (betreibt die DEVA selbst): Listener-Limit,
Puffer, Log zu den Stall-Zeiten 02.09. 17:07:18, 04.09. 20:07:17,
05.09. 11:36:13 und 17:06:50.

**Live-Testlauf 2026-09-06 (zwei Phasen, sechs Cloud-Slots): Option 1
war der falsche Weg, echte Ursache gefunden, Wächter gebaut
(`405b200`).**  Von acht Shows liefen drei tot bis Slot-Ende (Signal
weg ab +10 s), zwei zeigten am Anfang den falschen Stream.  Diagnose
am echten DEVA:
- **Der Server ist gesund.** Sonde vom Studio: eine Einzelverbindung
  liefert 20 s makellos in jedem der acht Zyklen; zehn gleichzeitige
  Verbindungen 40 s durchgehend, die elfte bekommt `HTTP 503 Too many
  connections` (Listener-Limit 10, `DEVAStreamServer 1.4`).
- **input.http erkennt einen Stall MITTEN im Stream nicht.** Zwischen
  „Buffer emptied" und dem Slot-Ende steht KEIN Reconnect im Log; das
  `-138`/die ffmpeg-Assertion kommen erst beim Teardown.  Das
  `timeout` (3 s) gilt nur beim Verbinden, nicht für einen stillen
  Read mitten im Stream.  Die stehengelassene Zombie-Verbindung belegt
  einen der zehn DEVA-Plätze → nach ein paar toten Slots `503` → tote
  Slots.  Erklärt die Verschlechterung über den Lauf (Show 1 gut, 2
  erholt, ab 3 tot).
- **Widerlegt:** Rückstau/Nicht-Leser (Liquidsoap liest bei
  geschlossenem Gate durchgehend weiter, `C:/Temp/prewarm_deva.py`);
  ffmpeg-`reconnect`-Optionen (hängen in einer Reconnect-Schleife,
  `rwtimeout_test.py`).
- **Option 1 verschlimmerte beides:** Bridge 5→10 s verdoppelte das
  Falscher-Stream-Fenster, Vorlauf 10→20 s die Leerlaufzeit.  **Zurück-
  genommen** auf Bridge 5 s / Vorlauf 10 s; `timeout` 3 s / `poll`
  0,5 s bleiben.
- **Wächter (der Fix):** Während ein Webstream sendet, pollt der
  Scheduler alle 2 s `source.is_ready(webstream)` (Telnet
  `webstream.ready`); nach zwei toten Abfragen, die auf eine lebende
  folgen, sauberes `webstream.stop` + `webstream.start`.  Frische
  Verbindung < 200 ms, sauberer Stop gibt den DEVA-Platz frei.  End-
  to-End bewiesen (`C:/Temp/watchdog_repro.py`, Server verstummt
  dauerhaft): zwei Stalls, zwei saubere Erholungen in ~6 s statt tot.
  Konstanten `WEBSTREAM_WATCHDOG_INTERVAL_SECONDS` 2,0 /
  `WEBSTREAM_WATCHDOG_STARVE_TICKS` 2.
- **Erledigt 2026-09-08:** Stall-Tests unter Plan A (DEVA 10 s bzw.
  60 s stromlos, 08:22/08:26 und 22:20): Erholung wie gebaut, Operator
  zufrieden („kurzer Hacker, verschmerzbar").  Der folgende Punkt ist
  damit abgehakt.
- **Offen (historisch):** Live-Abnahme am 2026-09-07 (Operator will die Erholung
  hören und die Latenz bis zur Rückkehr messen; Konstanten ggf.
  straffen).  Der „falsche Stream am Anfang" ist nur auf ~5 s
  zurückgestutzt (Bridge-Rest des Vorgänger-Streams), nicht beseitigt
  — eigener Punkt „Bridge leeren", unten.

### ✅ Webstream: falscher Stream (~5 s) am Slot-Anfang nach einem anderen Stream (neu 2026-09-06, erledigt 2026-09-08 durch Plan A)

**Befund:** Beim Umschalten auf einen ANDEREN Webstream spielt der Bus
zuerst den gepufferten Rest des vorherigen Streams — die Clock-Bridge
(`buffer`) ist FIFO und gibt den alten Inhalt zuerst aus.  Live am
2026-09-06 mehrfach gehört (5–20 s, verschlimmert durch die Option-1-
Bridge von 10 s; nach dem Zurücknehmen wieder ~5 s).  Betrifft nur den
Wechsel zwischen VERSCHIEDENEN Streams, nicht denselben Stream und
nicht Datei→Stream.
**Fix-Optionen (Go nötig):** (a) beim Wechsel die Bridge frisch
aufsetzen — `source.dynamic` mit einer neu erzeugten `buffer()`-Quelle
(die Signatur braucht ein Funktions-Argument, `2026-09-06` erste
Fassung scheiterte am fehlenden Argument; korrekt: `source.dynamic(id=…,
fun () -> buffer(...))` plus `.set(...)` beim Wechsel); (b) Bridge auf
2 s verkleinern (Phase-E-„Haker"-Risiko, jetzt vom Wächter abgefedert);
(c) beim Anderer-Stream-Start das Gate erst öffnen, wenn `webstream.
ready` NACH dem Start neu wahr wurde UND die Bridge einmal
durchgelaufen ist.  Empfehlung: (a), im Replikat testen bevor live.
**Beobachtung 2026-09-07 (Phase C, derselbe Stream):** Auch beim
SELBEN Stream hört der Operator in den ersten ~5 s einen kurzen
„Hacker" (Slots 2 und 3; Slot 1 mit leerer Bridge nicht): die Bridge
gibt erst 5–10 s alten Inhalt des vorigen Slots aus, dann folgt der
Zeitsprung zum frischen Material.  Messbar: `webstream.ready` war
schon 11,6 s VOR dem Slot wahr (vor dem Vorwärmen), weil die Bridge
nach dem Slot-Ende voll bleibt.  Fix (a) behebt beides.
**✅ Erledigt 2026-09-08:** mit der frischen Quelle pro Slot (Eintrag
„Webstream-Eingang: frische Quelle pro Slot" unter „Cloud-Stream-
Aussetzer") bekommt jeder Slot eine neue Bridge — kein Rest, kein
Hacker.  Live-Abnahme mit der nächsten Cloud-Sendung.

### ✅ Webstream: 5 s alte Puffer-Reste spielen nach einem PLAYOUT-Neustart (neu 2026-09-05, erledigt durch Plan A, geprüft 2026-09-09)

**Geprüft 2026-09-09 (Operator-Go):** seit Plan A (frische Quelle pro
Slot, `1eb8713`) tauscht jedes `webstream.stop` eine leere Quelle
(`source.fail()`) ein und verwirft die alte Brücke; nach dem 17:07-Slot
meldete Telnet `webstream.status = stopped`, `webstream.ready = false`.
Ein PLAYOUT-Neustart (`reset_gates`) findet also keine Reste mehr vor.

**Befund 17:50:52:** Beim PLAYOUT-Neustart öffnete `reset_gates()`
beide Gates; die Webstream-Bridge (`buffer(buffer=5.0)`) hielt noch
Reste vom 17:15 gestoppten Cloud-Stream, `source.is_ready(webstream)`
war damit wahr → der Bus schaltete für 5 s auf 35 min alten Cloud-Ton
(„Switch to amplify" 17:50:52, „Buffer emptied" 17:50:57).  Betrifft
jeden PLAYOUT-Neustart nach einer Webstream-Show, hörbar auf Sendung.
**Fix-Optionen (Go nötig, ~1 h):** (a) Gates beim Reset geschlossen
lassen und im nicht-vorgewärmten Start-Pfad explizit öffnen; (b) die
Bridge beim Release leeren (kein Telnet-Kommando vorhanden → Quelle
per `webstream.url` auf leer + kurzes `start/stop` ist kein Flush);
(c) `webstream_live` erst öffnen, wenn `webstream.buffer_length` nach
einem `start` wieder wächst.  Empfehlung: (a).

### ✅ „Latency is too high" jede Sekunde auf `clock.portaudio_clock` (verschwunden seit 2026-09-05, abgehakt 2026-09-09)

**Abgehakt 2026-09-09 (Operator-Go):** `liquidsoap.log` zählt am
2026-09-04 81.222 dieser Warnungen, am 2026-09-08 noch 5, am 2026-09-09
keine.  Verschwunden mit den Änderungen vom 05.09. (synchrone Queue
`request.queue_sync`, kein Dauer-Poller mehr); kein Test mehr nötig.

**Befund 2026-09-04:** ~3.560 Warnungen pro Stunde, den ganzen Tag,
seit dem Main-Output-Umbau (Monitor über `buffer(buffer=2.0, bus)` +
`clock.assign_new(id="portaudio_clock", sync="cpu")`).  Betrifft den
lokalen Monitor-Ausgang (Tascam), **nicht** den Sendeweg (Icecast-
Uhr meldet nichts).  Werte 0,3–1,2 s „catchup".  Kandidaten: `sync="cpu"`
gegen die Gerätetaktung des Tascam (44,1 kHz), Blockgröße/Latenz von
`output.portaudio`, `buffer`-Größe.  Nebenwirkung: 60 MB Log/Tag.
Test: Werte bei Jabra vs. Tascam als Main Output vergleichen;
`settings.log.level` für die Uhr senken, falls harmlos.

**Ergebnis 2026-09-05:** Ursache ist das Zusammenspiel
`clock.assign_new(sync="cpu")` + `output.portaudio` (blockierende
Writes, `self_sync=true`): der Ausgang taktet die Uhr über die
Gerätesamplerate, `sync="cpu"` will sie zusätzlich an der Wanduhr
halten → jede Sekunde „catchup".  Beweis ex negativo: nach dem Reboot
um 11:15 verschwanden die Meldungen (4 statt 3.560/h) — weil die
Instanz auf einem **DirectSound**-Gerät landete, dessen blockierender
PortAudio-Write ein Stub ohne Wirkung ist (kein Ton, keine Taktung).
Die Meldung ist also das Zeichen für einen FUNKTIONIERENDEN WASAPI-
Ausgang; harmlos für den Sendeweg, aber 60 MB Log/Tag.
**Fix-Optionen (Go nötig):** (a) `sync="auto"` für die `portaudio_clock`
— die Uhr folgt dem Gerät, `buffer(buffer=2.0)` fängt die Drift zur
Haupt-Uhr ab (so ist die Bridge gedacht); Risiko: bei einem Gerät ohne
echte Taktung (DirectSound-Stub!) liefe die Uhr frei → dann muss der
Geräte-Fix (Eintrag „PortAudio-Index instabil") zuerst kommen; (b)
`settings.log.level` der Uhr senken (Symptom kaschieren).  Empfehlung:
(a) zusammen mit dem Geräte-Fix, ~1 h inkl. Prüf-Render.
**Umgesetzt 2026-09-05 (`462d684`):** (a) `sync="auto"`; Replika mit
dem Tascam (MME): „Switching to self-sync mode", 0 Warnungen.

### ✅ „possible source leak, 61 sources" (letzte Warnung 2026-09-05, abgehakt 2026-09-09)

**Abgehakt 2026-09-09 (Operator-Go):** letzte Warnung am 2026-09-05
17:50 (58 Quellen), seither keine — die Quellen sammelten sich mit dem
alten `request.dynamic`-Poller an, der am 05.09. entfernt wurde.

**Befund:** Warnung seit 2026-09-03 (54 Quellen), am 2026-09-04 abends
59–61; Liquidsoap-Speicher 232 MB nach 53 min.  Jeder Bus-Übergang
erzeugt `add`/`fade_in`/`fade_out`/`track_audio_amplify`-Quellen, die
Queue-Crossfades ebenso.  Test: Quellenzahl und Speicher über einen
Sendetag beobachten (Zählung aus „Current sources" im Log); steigt sie
monoton, Übergangsquellen nach `transition_length` prüfen.

**Ergebnis 2026-09-05:** Falscher Alarm.  Die Warnung feuert ab
`settings.clock.leak_warning` (Default 50); unsere Kette hat ~45
statische Quellen, jeder Bus-Übergang/Queue-Crossfade legt kurzzeitig
10–13 dazu (`clock.dump_all_sources`: `fade_in`/`fade_out`/`audio.add`/
`source.dynamic`/`track_audio_amplify`, dazu je Übergang ein `fail`-
Clock-Stub) und die Zahl pendelt zurück (50 → 63 → 50 → 59 → 50).
Nicht monoton, kein Quellen-Leck.  Fix: `settings.clock.leak_warning := 200`
im Template — umgesetzt 2026-09-05 (`462d684`).  **Das echte
Speicherleck ist ein anderes** — siehe nächster Eintrag.

### 🟢 Liquidsoap-Windows-Speicherleck: ~5 KB pro `Unix.select` — Milderung umgesetzt 2026-09-05 (`462d684`, `1dbeb71`), Upstream offen

**Befund 2026-09-05:** Die Live-Instanz (Start 11:15:27) wuchs auf
3,2 GB um 13:11 (Mittel 0,46 MB/s; 0,15 MB/s im Leerlauf, bis
0,8 MB/s während Shows).  `runtime.memory` (Telnet): OCaml-Heap
konstant 78 MB; `runtime.gc.full_major` + `compact` geben nichts frei
→ C-seitig.  Read-only-Speicheranalyse (`C:/Temp/memscan*.py`,
`structdecode.py`, `symlookup.py` über die COFF-Symboltabelle der
liquidsoap.exe): 16-MB-NT-Heap-Segmente voller nie freigegebener
Blöcke à 2032 + 3104 Byte (Einheit 5136 Byte), Funktionszeiger darin
= `read_pipe_poll`, Felder = Windows-HANDLEs des Duppy-fd-Sets.  Das
ist OCamls Windows-Emulation von `Unix.select` (`otherlibs/win32unix/
select.c`, SELECTDATA + Worker-Thread für Pipes; Liquidsoap 2.4.4 ist
mit OCaml 4.14.1 gebaut).  **Jeder `Unix.select`-Aufruf des Duppy-
Schedulers leakt ~5 KB.**  Bekannt als savonet/liquidsoap #1122
(2020, „Memory leak on windows using telnet commands", offen).
Vor dem Reboot lief die Instanz 15,5 h — die Rate hängt an der
Wakeup-Frequenz, nicht an der Laufzeit.

**Auslöser (Replika-Bisektion, `C:/Temp/leak_*.py`, Kopien der Live-
.liq mit eigenen Ports/Mounts):** frische Instanz ohne Requests bleibt
flach — mit PortAudio auf jedem Gerät, mit drei Icecast/FFmpeg-
Encodern, nach einer Webstream-Show, mit dauerhaft offener oder halb
geschlossener Telnet-Verbindung, und auch nach einem Titel aus der
Initial-Queue.  **Ein expliziter `scheduled.push` im laufenden Betrieb
(so pusht der Playout jeden Titel) startet den asynchronen Fetch-Task
von `request.dynamic`; sobald die Queue leer ist oder ein Request
scheitert, pollt der Task mit `retry_delay` (Default 0,1 s) für immer
weiter** — ein erfolgreicher Titel danach beendet ihn nicht.  Gemessen:
ein Push → +50–80 KB/s, zwei Pushes → +100 KB/s; live ~33 Selects/s
= 0,15 MB/s im Leerlauf, in Shows mehr.  Telnet-Kommandos kosten je
~2 Selects (vernachlässigbar).  Fehlende Datei = „Unknown protocol
URI", unlesbare Datei = „Error while checking file's content" (der
Jingle „StationID Friska Viljor.mp3" schlägt mit
`Channel_layout.Unsupported` fehl — eigener Punkt, siehe unten).

**Milderungen gemessen (Replika, 150–180 s):**
- `retry_delay={2.0}` (eigene `request.queue`-Kopie mit Parameter):
  Leck ~10 KB/s statt 50–100; Pushes starten sofort — **außer** nach
  einem Decoder-Fehler, dann wartet der nächste Push bis zu
  `retry_delay` (bei 5 s gemessen: Start erst beim nächsten Poll).
- **`synchronous=true`** an `request.dynamic` (Kopie der Stdlib-
  `request.queue` mit diesem Parameter): **flach** (124–126 MB), auch
  nach fehlgeschlagenem Push; alle Pushes sofort vorbereitet.  Die
  Auflösung läuft dann im Telnet-Handler-Thread (lokale, bereits
  heruntergeladene Dateien: Millisekunden) — kein Duppy-Task, kein
  Polling.  Schutz: `timeout=5.0` an der Queue, damit eine kaputte
  Datei den Push (und damit den Playout-Telnet-Aufruf) nicht 20 s
  blockiert.

**Optionen (Trade-offs, Go nötig):**
1. **Template-Fix:** `scheduled_q` auf die synchrone Variante umstellen
   (Stdlib-`request.queue` kopiert, `synchronous=true`, `timeout=5.0`);
   Prüf-Render mit DJ-Armen, Unit-Test auf den gerenderten Block,
   Live-Abnahme einer Jingle-Folge.  ~1,5 h.  Restrisiko: Pushes von
   Nicht-Datei-URIs (gibt es im Scheduled-Pfad nicht).
2. **Betriebs-Sicherung:** Speicher-Schwelle im Preflight (Warnung ab
   2 GB im UI) und ein geplanter Neustart PLAYOUT → LIQUIDSOAP in der
   Nacht als Netz und doppelter Boden (Stream-Abriss ~5 s).  ~2 h.
3. **Upstream:** Meldung an savonet mit dieser Beweiskette (5136 Byte
   pro Select, `read_pipe_poll`, Trigger `request.dynamic`-Retry);
   Fix wäre ein OCaml-5-Build oder ein Socketpair statt Pipe für den
   Duppy-Wakeup.  Zeit bis Fix unbekannt.
**Empfehlung:** 1 sofort (behebt den einzigen dauerhaften Poller),
2 als Schutznetz, 3 parallel.  Bis dahin: Speicher der Instanz
beobachten (`Get-Process liquidsoap`), Neustart ab ~4 GB.

**Umgesetzt 2026-09-05 (Operator-Go):** Option 1 als
`request.queue_sync` im Template (`462d684`), Option 2 als
Preflight-Warnung `liquidsoap_memory_high` (2048 MB, Fehler ab 4096)
plus nächtlicher Neustart im ruhigen Fenster ab 04:00 durch den
Scheduler (`1dbeb71`, `RASTATIME_LIQUIDSOAP_NIGHTLY_RESTART`).
Replika des Produktions-Renders gegen Icecast + Tascam: Speicher flach
(94 MB konstant), alle Pushes sofort, auch nach Fehl-Push.  **Offen:**
Option 3 — Entwurf liegt in
`docs/upstream/2026-09-05-liquidsoap-windows-unix-select-leak.md`,
Operator postet ihn bei savonet.

**Vorfall 2026-09-06/07 — Nacht-Neustart in Absturzschleife (behoben
2026-09-07):** beide 04:01-Neustarts endeten in einer NSSM-Schleife bis
08:21 (Display schlief → HD-Audio-Endpunkt `DELL U2419HC` weg →
PortAudio-Indizes verschoben; PLAYOUTs Geräteliste stammte vom
Prozessstart; Namens-Probe scheiterte mit MME error 2; Fallback
`device_id=18` öffnete ein anderes Gerät; `nssm restart` Exit 1 →
dreifacher Retry; Preflight blind, weil nur Prozesse > 90 s beurteilt).
Fix: Re-Enumeration vor jeder Auflösung, „per Name oder gar nicht",
Verifikation per `uptime`, Bleibt-oben-Prüfung, Preflight
`liquidsoap_unavailable`.  Details CHANGELOG / Architektur-Addendum
2026-09-07.  Aktiv nach PLAYOUT-Neustart; erste scharfe Nacht danach
im Log prüfen (`grep "Nightly" logs/playout-stdout.log`).

### 🟡 Liquidsoap-Upgrade als echte Heilung des `Unix.select`-Lecks (Operator 2026-09-09, evaluiert 2026-09-09: Defer)

**Evaluierung 2026-09-09 (Go, Reihenfolge-Punkt 4):** Stand savonet:
2.4.5 (15.06.2026, win64-Zip 47 MB) ist die neueste Version mit
Windows-Build; die Rolling-Version 2.5.x (18.08.2026) verlangt OCaml 5.5
und hat keinen Windows-Build.  Die `liquidsoap-2.4.5-win64.config` weist
**OCaml 4.14.1** aus — derselbe Compiler wie 2.4.4, also dieselbe
`win32unix/select.c`.  Messung (`C:/Temp/liq245/leak_compare.py`, 400
`uptime`-Kommandos über eine offene Telnet-Verbindung): Minimal-Skript
2.4.4 = 3 KB, 2.4.5 = 2 KB je Kommando; **produktionsnahes Replikat**
(`make_replica_prod.py`: echter Render, Telnet 8823, Harbor 8831,
Icecast-Mounts `-leaktest`, Dummy statt PortAudio) **2.4.4 = 46 KB,
2.4.5 = 48 KB je Kommando** — kein Unterschied; das Leck skaliert mit
dem fd-Set, nicht mit der Liquidsoap-Version.  2.4.5 prüft unseren
Render (`--check`) sauber und hat alle benötigten Operatoren; seine
Fixes (Crash bei EOF externer Eingänge, Crossfade außerhalb des Clock-
Threads, `Strings.Mutable`-Leck) treffen bei uns kein bekanntes Problem.
**Empfehlung: Defer.**  Bleiben bei 2.4.4; erneut prüfen, sobald savonet
einen Windows-Build auf OCaml 5 veröffentlicht (2.5.x) — dann dieselbe
Replikat-Messung wiederholen.  Der 2.4.5-Download liegt in
`C:\Temp\liq245` (Zip + entpackt) für spätere Tests.

**Status:** Idea — Operator 2026-09-09: „Wir merken uns dieses Leck mit
diesem Windows-Build.  Unter Umständen updaten wir irgendwann einmal
zu einer aktuelleren Version von Liquidsoap."  Bis dahin gilt der
Betrieb mit den Milderungen (Option d, kein Telnet-Poll, geplanter
Neustart alle ~7 Tage, Standby-Fallback).
**Stand der Milderungen (2026-09-09):** Leerlauf ~5 MB/h (ursprünglich
~150), Webstream-Slot-Start +7–12 MB einmalig.
**Vorbedingungen für ein Upgrade:**
- Ein Windows-Build einer neueren Liquidsoap-Version, dessen `Unix.select`
  nicht mehr pro Aufruf leckt (OCaml 5 / socketpair-basiertes Select oder
  korrigiertes `win32unix/select.c`) — vorab mit `telnet_leak_probe`/
  `wd_cost_probe` im Replikat messen (Kommando-Kosten, Verbindungs-Kosten,
  `thread.run.recurrent`-Tick).
- Gleiche Fähigkeiten wie 2.4.4: `%ffmpeg`-Encoder (mp3/aac/ogg),
  PortAudio-Ausgang per Gerätename, `input.harbor`, `input.http` mit
  `source.dynamic`, `http.post`, `bus.on_frame`, Telnet-Server.
- Replikat-Test des vollen Renders (`liquidsoap --check` + Laufzeit gegen
  Icecast + Tascam) und der Standby-Render; Prüfung, ob der wieder-
  verwendete `input.http` (Duppy-Weckbyte) und das DJ-Auflegen (30-s-
  Harbor-Timeout) in der neuen Version anders reagieren.
- Wartungsfenster mit Rückweg (alte `liquidsoap.exe` behalten; NSSM-
  Pfad umschalten).

### 🟢 Liquidsoap-Leck: Kosten pro Telnet-Kommando — Poll-Design (neu 2026-09-07, abgeschlossen 2026-09-09)

**Messung 2026-09-07 an der Produktionsinstanz (nichts auf Sendung):**
jede Telnet-**Verbindung** +262 KB, jedes **Kommando** über eine offene
Verbindung +87 KB (≈17 `Unix.select` à ~5 KB); offene, stille
Verbindung kostet nichts.  PLAYOUTs Client ist persistent, also:
SourceSwitcher-Statuspoll alle 5 s ≈ 66 MB/h Leerlauf (≈1,6 GB/Tag),
Webstream-Wächter alle 2 s ≈ 157 MB pro Webstream-Stunde; der 1-s-
Messpoller der Phase C allein +340 MB in 20 min.  Der nächtliche
Neustart (seit 2026-09-07 gehärtet) ist die tägliche Nullstellung;
die 2048-MB-Warnung wird bei mehreren Webstream-Stunden am Tag
trotzdem erreicht.
**Optionen (Go nötig):** (a) Switcher-Poll 5 s → 10–15 s (DJ-Umschalt-
Latenz steigt entsprechend; ~1 GB/Tag gespart, 1 Zeile); (b) Wächter-
Intervall 2 s → 4 s (Erkennung 8 s statt 4 s, halbe Kosten, 1 Zeile);
(c) Wächter in Liquidsoap selbst (`thread.run.recurrent` alle 2 s +
`source.is_ready(webstream)` + Gate-Prüfung, stop/start im Prozess,
~9 MB/h; Scheduler pollt gar nicht; Template-Änderung + Test im
Replikat, ~2 h); (d) Switcher ereignisgesteuert über Harbor-
`on_connect`/`on_disconnect` (größerer Umbau).  Empfehlung: (c) + (a);
(d) später.  Echte Heilung nur upstream (OCaml 5 / socketpair).

**Stand 2026-09-07 abends:** (c) umgesetzt, aber als **Frame-Zähler**
statt Timer — Replikat-Messung über 15 min: Telnet-Poll +57 MB (66 KB/
Kommando), `thread.run.recurrent`-Timer +25 MB (~31 KB/Tick; die „~9
MB/h" von oben waren falsch, das Leck pro Select skaliert mit dem
fd-Set), `bus.on_frame`-Zähler +0,1 MB = flach.  Live nach Neustart
PLAYOUT → LIQUIDSOAP (Details CHANGELOG „Webstream-Wächter läuft jetzt
in Liquidsoap selbst").  **(a) vom Operator abgelehnt** (DJ-Latenz),
**(b) hinfällig**, **(d) offen**: Leerlauf-Wachstum der
Produktionsinstanz weiterhin ~150 MB/h (19:34 1582 → 19:49 1620 MB),
2048-MB-Banner erscheint daher täglich am Abend, Nacht-Neustart setzt
zurück.  Scheduler-Poll bleibt als Rückfall (`RASTATIME_WEBSTREAM_
WATCHDOG=scheduler`) und als Übergangs-Notnagel, wenn eine ältere .liq
geladen ist; nach einer Woche ohne Auffälligkeit entfernen.

**Stand 2026-09-09 — (d) umgesetzt (Ziel c des Operators):** Harbor-
Callbacks `on_connect`/`on_disconnect` posten `source=master|show&
status=on|off` an PLAYOUTs Listener (`/source-event`); PLAYOUT
übernimmt sofort, verifiziert 1 s nach jedem Ereignis und sonst alle
`RASTATIME_DJ_RECONCILE_SECONDS` (120 s) per Telnet; eine alte .liq
ohne Callbacks wird erkannt (Probe `rastatime.source_events`) und wie
bisher alle 5 s gepollt.  Replikat: Verbinden → Ereignis in
Millisekunden, Kick sofort, Auflegen erst nach dem 30-s-Harbor-Timeout
(wie der Status-Poll zuvor; eigener 💡-Eintrag unten).  Erwartetes
Leerlauf-Wachstum danach wenige MB/h statt ~150 MB/h.  **Offen:**
Speicher der LIQUIDSOAP-Instanz eine Woche beobachten (2048-MB-Banner,
Task-Manager, `memscan`), dann `RASTATIME_LIQUIDSOAP_RESTART_EVERY_DAYS`
auf 7–30 setzen.  **Live seit 10:19 (PLAYOUT 10:19:03, LIQUIDSOAP
10:19:24, Probe im Log „posts harbor events").  Messung 10:20–10:50,
nichts auf Sendung: Private Bytes 97 → 104 MB = 14 MB/h** (vorher
~150 MB/h).  Der Rest ist erklärt: der Telnet-Server trennt stille
Verbindungen nach 30 s (`settings.server.timeout`), beide PLAYOUT-
Clients verbinden sich daher alle 2 min neu (30 Neuverbindungen in
30 min à ~262 KB ≈ 16 MB/h).  Umgesetzt (Go 2026-09-09):
`settings.server.timeout.set(-1.)` im Template → erwartet ~5–8 MB/h;
live seit 11:25 (Operator-Neustarts).  **Nachmessung 11:27–11:57,
nichts auf Sendung: 96 → 103 MB = wieder 14 MB/h.**  Die
Neuverbindungen sind weg (keine „New client"-Zeilen mehr nach dem
Wiederanbinden 11:27:37), waren aber nicht der Rest: übrig bleiben
3 Telnet-Kommandos je 120 s (Scheduler `uptime` zur Neustart-Erkennung
+ Umschalter `master_dj.status`/`show_dj.status`) ≈ 155 KB je
Kommando bei der jetzigen fd-Menge.  Dritter Schritt (Go 2026-09-09,
umgesetzt): Neustart-Erkennung über die Prozesstabelle (PID/Alter der
Hauptinstanz, ohne Telnet; `uptime` nur Rückfall) und Verifikations-
Intervall 120 → 600 s → ~0,4 Kommandos je 120 s, erwartet ~2 MB/h,
weiche Grenze erst nach ~4 Wochen; dabei behoben: die Prozess-Probe
nahm seit dem Standby-Dienst die älteste = Standby-Instanz (jetzt
`main_instances` per Skriptname).  **Nachmessung 16:40–17:10 (PLAYOUT
seit 16:39): ruhiger Teil 16:40–17:05 93 → 95 MB = ~5 MB/h** (vorher
14, ursprünglich ~150); der Webstream-Slot 17:07 kostete beim Start
einmalig +7 MB (frischer input.http + Brücke, bekannt) und lief dann
flach.  Damit: weiche Grenze 1536 MB im Leerlauf nach ~12 Tagen, mit
einigen Webstream-Slots pro Tag nach ~6–7 Tagen → `RESTART_EVERY_DAYS`
7 ist der realistische Wert, 30 nicht.  Rechnung für das Intervall: bei 14 MB/h erreicht die
Instanz die weiche Grenze 1536 MB nach ~4 Tagen, bei ~8 MB/h nach
~8 Tagen → 7 Tage realistisch, 30 nicht (harte Grenze 3072 MB nach
~15 Tagen).

### 🟢 24/7-Programm: geplanter Neustart an der Titelgrenze + Standby-Fallback (2026-09-09, Go a+b)

**Befund:** Mit durchgehendem Programm (normal bei Example Radio, um 04:00
läuft eine Playlist) fand der Nacht-Neustart nie einen ruhigen Moment
und entfiel → Speicher wächst 150–180 MB/h unbegrenzt.
**Umgesetzt:** a) Auslöser Fenster/alle N Tage/Speicher weich 1536 MB
im Fenster/Speicher hart 3072 MB jederzeit (`RASTATIME_LIQUIDSOAP_
RESTART_EVERY_DAYS|_AT_MB|_HARD_MB`), Ausführung im ruhigen Moment oder
zwischen zwei Datei-Titeln (`_on_file_start`); b) Standby-Quelle
`standby.liq` (Dienst RASTATIME-STANDBY, `nssm-install-standby.ps1`)
und Icecast-Fallback-Mounts → keine Hörer-Trennung, ~2 s Stille an
einer Titelgrenze.  **Inbetriebnahme durch den Operator:** PLAYOUT neu
starten (rendert standby.liq), `nssm-install-standby.ps1` als Admin,
RASTATIME-ICECAST einmal neu starten (einmalige Trennung), Standby-
Mounts in `status-json.xsl` prüfen.  **Ziel c) = Option d** (Switcher
ereignisgesteuert, Leck weg): umgesetzt 2026-09-09 (Leck-Eintrag oben);
`RESTART_EVERY_DAYS` auf 7–30 setzen, sobald eine Woche Speicherverlauf
flach ist.  Offen: Live-Abnahme des Titelgrenzen-Neustarts in der ersten
Nacht mit Programm.

### ✅ DJ-Auflegen erst nach 30 s erkannt (Harbor-Timeout, Windows-Build) — umgesetzt 2026-09-09 (`timeout=5.`)

**Umgesetzt (Operator-Go 2026-09-09, Reihenfolge-Punkt 2):** der Renderer
setzt `timeout=5.` an beiden Harbors (`RASTATIME_HARBOR_TIMEOUT_SECONDS`,
Minimum 1).  Kern des Problems: PLAYOUT schiebt keine Titel nach, solange
es einen DJ für live hält → nach dem Auflegen bis zu 25 s leere
Warteschlange.  Replikat: Trennen nach 5,06 s gemeldet.  Aktiv nach
PLAYOUT- und LIQUIDSOAP-Neustart.

Replikat 2026-09-09 (Befund): schließt ein DJ-Client nur den Socket, meldet
`input.harbor` auf dem Windows-Build das Ende nicht sofort (`select`
sieht das FIN nicht), sondern erst mit „Timed out after waiting for
30.00 sec" — Audio fällt wegen des 5-s-Puffers trotzdem sofort auf den
Sendeplan zurück, nur Dashboard-Status und Scheduler-Reaktion hängen
30 s nach (vorher mit dem Status-Poll genauso).  Option: `timeout=`
am `input.harbor` auf z. B. 10 s senken (Trade-off: ein DJ mit 10 s
Netzstörung fliegt raus).  Operator-Entscheidung; kein Handlungsdruck.

### 💡 Statisches Harbor-Rückfall-Passwort in libretime.conf ersetzen (Operator 2026-09-10)

**Nachtrag 2026-09-13:** beim Rendern des Replikats fiel auf, dass auch das
Icecast-Quellpasswort (Settings → Streams, Source Password) noch der
Auslieferungsstandard ist; bei derselben Gelegenheit mit ändern (Icecast-
Konfiguration + Settings → Streams + LIQUIDSOAP-Neustart).

**Status:** Idea/Defer — vom Operator am 2026-09-10 für später notiert.
`stream.harbor.main_password`/`show_password` sind noch Installations-
Platzhalter.  Seit den UI-Logins greifen sie nur, wenn PLAYOUT nicht
erreichbar ist (Benutzer `source`), also gerade im Notfall.  To do:
beide Werte in libretime.conf durch echte Passwörter ersetzen, dann
PLAYOUT (rendert) und LIQUIDSOAP neu starten; Werte nie ins Log/Chat.

### ✅ DJ-Logins: die Oberfläche wird zur Wahrheit (Operator-Go Option 2, umgesetzt 2026-09-10)

**Befund 2026-09-10:** BUTT-Login schlug fehl.  Die Harbors prüften nur
`source` + statisches Passwort aus libretime.conf; Settings → Streams
zeigte Port 8000 (Icecast-Ära), der Harbor hörte auf 8001; Master-Source-
und per-Show-Logins aus der UI wurden nie benutzt.
**Umgesetzt:** Harbor-`auth` → PLAYOUT `/dj-auth` → Legacy
`check-live-stream-auth` (Master aus Settings, Show = laufende Show mit
Host- oder Custom-Login); statisches Passwort nur als Rückfall bei
unerreichbarem PLAYOUT; Ports/Mounts aus `stream.inputs` (jetzt 8001,
main/show).  Details CHANGELOG „DJ-Logins".  **Live-Abnahme 2026-09-10
13:20–13:23 (Operator, BUTT als Master Source in einer eigenen
Test-Show, drei Runden):** Login → `dj-auth … accepted` → Switcher
`scheduled -> master` binnen 25 ms, Audio-Umschaltung nach dem 5-s-
Harbor-Puffer; sauberes Trennen → Harbor-Timeout 5,00 s → `master off`
+ „Resume scheduled … at +86.6s" in derselben Sekunde; harter
Prozessabbruch → `ECONNRESET` sofort → `off` + Resume nach 0,8 s, Audio
zurück, sobald der gepufferte DJ-Ton abgespielt war (~9 s).  Operator:
alle Übergänge klangen gut.  **Show-Login 13:35/13:36 ebenfalls
abgenommen:** Login über den Custom-Login der laufenden Show akzeptiert,
Switcher `scheduled -> show` nach 22 ms, Audio nach dem 5-s-Puffer,
Trennen → Timeout 5,0 s → `show off` + Resume an der richtigen Stelle.

### ✅ Gerenderte Einstellungen ohne manuellen Neustart (DONE 2026-09-16)

**Operator-Frage 2026-09-16:** „Muss ich nach dem Aktivieren/Deaktivieren des
24/7-Recordings immer den Dienst neu starten?  Kann man das automatisch
durchführen?" — Evaluierung: Go, auch für den Main Output.  Umgesetzt
(`6be216a`): Fingerprint der gerenderten
Einstellungen, Abgleich bei jedem Refresh, geplanter Neustart im ruhigen
Moment oder an der Titelgrenze.  Nicht umgesetzt (💡 bei Bedarf): Ein/Aus
der Aufnahme ganz ohne Neustart per Telnet (`recording_hourly.start/stop`,
Ordner als interaktive Variable) — ~1 Tag, Format/Bitrate bräuchten den
Neustart trotzdem.
**Live 2026-09-16 10:32 (Bitrate 128 → 192):** Refresh 10:32:35 erkannte die
Änderung, Render, LIQUIDSOAP-Neustart, wieder oben 10:32:38 — dabei gefunden
und behoben: `output.file` kürzte die laufende Stundendatei — `append=true`
(`bfa216e`) half nicht (ffmpeg-Muxer), daher Fortsetzung in `<Stunde>-00.2.mp3`
+ `parts` im Sidecar (`3cb5e33`); außerdem übernimmt der Pfad jetzt auch ein beim
PLAYOUT-Start geändertes Skript (`render_restart_pending`).
**Live 2026-09-16 12:37 (Fortsetzungsteile):** PLAYOUT-Start 12:37:30 mit
geändertem Skript → Neustart im ruhigen Moment, LIQUIDSOAP wieder oben
12:37:34; `12-00.mp3` (ab 12:00:00, 54 MB) unversehrt, `12-00.2.mp3` ab
12:37:32, Rotation 13:00 normal.  `parts` im Sidecar erscheint erst mit der
nächsten Marke der Stunde (in Stunde 12 kam nach 12:37 keine mehr).
**Live 2026-09-16 16:53 / 17:24 (Ordner + Bitrate):** Ordnerwechsel nach
`D:\\recordings\\24-7` um 16:53 sofort übernommen; Bitrate 192 → 128 um
16:59 erst um 17:24 — die 30-Minuten-Sperre galt auch nach Erfolg (behoben,
`4edc6ec`).  ffprobe: 192 kbit/s bis 17:24:01, dann
128 kbit/s in `17-00.2.mp3`.

### ✅ Cue-Marker-Test der 24/7-Aufnahme (Arbeitsreihenfolge 7a, DONE 2026-09-16)

**Ablauf:** Operator schaltet 24/7-Aufnahme ein (MP3 128 kbit/s,
`C:\\Users\\studio\\Music\\Permanent Recordings`, Aufbewahrung 10 Tage — der
Aufräum-Thread löschte beim PLAYOUT-Start 15 Tagesordner von Juni/August, wie
vorgegeben), Neustart PLAYOUT (rendert `recording_hourly`) und LIQUIDSOAP
09:53; zwei Test-Shows „testshow" 09:55–10:00 und „testshow2" 10:00–10:05, je
ein Titel + Station-ID (Crossfade), Show-Wechsel genau auf der Stundengrenze.

**Ergebnis (`C:/Temp/optd/cue_check.py 2026-09-16 09|10`):**

| Stunde | Marker | Befund |
|---|---|---|
| 09 | show start 3300,18; track start 6162 (3300,18); track start 6163 (3587,11); track end 6163 (3598,08) | Paare konsistent, Item-Kennungen vorhanden; 6162 hat keinen eigenen End-Marker — der Start von 6163 impliziert ihn (Fix 2026-09-10 `2b208a0` wirkt: kein 30-ms-Nachzügler mehr) |
| 10 | show end/start 0,09; track start 6164 (0,09); track start 6165 (287,12); track end 6165 (299,08) | Paare konsistent; Show-Grenze auf der Stundengrenze in die neue Datei geschrieben |

Offsets gegen das Playout-Log: 09:55:00,162 → t=3300,18; 09:59:47,060 →
3587,11; 10:00:00,064 → 0,09; Abweichung ≤ 0,1 s.  Audio: `09-00.mp3` 6,3 MB
= 6,6 min (Start 09:53:24 bis Rotation exakt 10:00:00), `10-00.mp3` läuft.
Die Wiedervereinigung nach dem LIQUIDSOAP-Neustart (PLAYOUT 09:55:05
„restarted under PLAYOUT", `recording.stop` an die Show-Aufnahme) hat die
Stunden-Aufnahme nicht berührt.

**Befund umgesetzt (Operator-Go 2026-09-16, `642dd0c`):**
`audio_start` + `audio_start_offset` im Sidecar, aktiv nach PLAYOUT-Neustart.
**Ursprünglicher Befund:** Bei einer angebrochenen
ersten Stunde (Aufnahme startet mitten in der Stunde — täglich nach dem
04:00-Neustart, sowie nach jedem manuellen Neustart) beginnt die Audiodatei
nicht am Stundenanfang, die Marker zählen aber ab Stundenanfang.  Die
Cue-Datei kennt nur `hour_start`, nicht den tatsächlichen Aufnahmebeginn; ein
Catch-up-Player müsste ihn aus der Dateierstellzeit ableiten.  Vorschlag:
Feld `audio_start` (Erstellzeit der Audiodatei) beim ersten Marker der Stunde
in die Cue-Datei schreiben (~15 Zeilen in `cue_writer.py` + Test), Handbuch
RECORD_PER_HOUR §4.1 ergänzen.  Vorbedingung: Operator-Go.

### ✅ Scheduler-Poll-Rückfall entfernen (fällig ab 2026-09-15, Operator 2026-09-09) — DONE 2026-09-15

**Erledigt 2026-09-15 (Operator-Go, `de822e4`):** Kriterien
erfüllt (kein Stall, ein regulärer Reap, 14 von 15 Starts ≤ 3 s, einer 8 s
mit erfolgreichem zweiten Versuch vor Slot-Beginn, Nacht-Neustarts sauber),
Umfang wie geplant umgesetzt, Standard-Render byte-gleich; Details CHANGELOG
„Removed" und ARCHITECTURE §23.31.  Wirksam nach PLAYOUT-Neustart.
**Ursprünglicher Plan:** Nach einer ruhigen Woche mit Plan A + Reaper (live seit 2026-09-08
22:45) den Telnet-Poll-Rückfall aus PLAYOUT ausbauen: Modus-Schalter
`RASTATIME_WEBSTREAM_WATCHDOG`, Poll/Reconnect-Pfad im Scheduler, Probe
„hat die geladene .liq den internen Wächter", Scheduler-Modus-Stub des
Renderers, zugehörige Tests, Handbuch-Satz EN/DE/FR/ES, CHANGELOG
„Removed".  Wirksam nach PLAYOUT-Neustart, LIQUIDSOAP unberührt
(Standard-Render bleibt gleich), risikofrei für den Sendebetrieb.
Kriterien „ruhig": keine Wächter-Reconnects außer echten Stalls,
`reaped=0` außerhalb von Stall-Tests, alle Starts 1–4 s, Nacht-Neustart
täglich sauber.  Operator wird ab dem 15.09. erinnert.

### 🟢 Webstream-Eingang: frische Quelle pro Slot (Plan A, 2026-09-08)

**Befund 2026-09-08:** Live-Stall-Test (DEVA zweimal stromlos) erholte
sich wie gebaut (11 s bzw. Ausfalldauer + 5 s), aber Phase D danach:
zwei Vorwärm-Starts dekodierten erst nach 48 s / 97 s, der BBC-Slot kam
nie auf Sendung, anschließend hing jeder Start an der Produktions-
instanz > 90 s in „starting"/„polling", Stop in „stopping", plus BBC-
Zombie-Verbindung (`ffmpeg_io.ml:121 Assertion failed`).  Ursache im
Quelltext: `input.http` verbindet über EINEN Duppy-Async-Task mit
Pipe-Weckbyte; auf dem Windows-Build wird das Weckbyte unter Last spät
oder doppelt zugestellt.  Replikat-Aufteilung (je 6 Start/Stop-Zyklen):

| Replikat | Ergebnis |
|---|---|
| Grundgerüst | 12/12 in 3,7 s |
| nur Icecast-Ausgänge | 1 Hänger („polling", > 100 s) |
| nur PLAYOUT-Telnet-Poll (5 s) | 1 Hänger („polling", 110 s) |
| Icecast + Poll + PortAudio | 1 Hänger („starting"), 1× 19,6 s |
| Icecast + Poll, Warten auf „stopped" vor Start | 2 Hänger |
| **frische Quelle pro Zyklus (source.dynamic), Icecast + Poll** | **9/9 in 3,7 s (Cloud) / 0,7 s (BBC)** |

**Umgesetzt (Operator-Go „Plan A"):** `source.dynamic(id="webstream")`
als Bus-Arm, `webstream.start` = neuer `input.http` + neue Bridge,
`webstream.stop` = stoppen und verwerfen, Wächter erholt sich mit
frischer Quelle; Telnet-Vertrag unverändert.  Kosten ~1 Thread/Slot bis
zum Nacht-Neustart.  **Plan B (falls A enttäuscht):** Relais in PLAYOUT
holt den Stream per HTTP (Socket-Timeout = Stall-Erkennung in Python)
und schiebt die Bytes als Source-Client in `input.harbor` (wie der
Line-In-Feeder); Liquidsoap öffnet dann keine HTTP-Quellen mehr.
Aufwand ~1 Tag.  **Live-Abnahme 2026-09-08 bestanden:** Cloud-Sendung
12:07 (Vorwärmen −10 s, Dekodieren +3 s, Gate 12:07:00, keine Stille)
und Phase E 15:00 (drei Cloud-Slots + BBC: jeder Slot mit frischer
Quelle `webstream_in_5…8`, Dekodieren 3 s bzw. 0 s, Hörer-Ton exakt zum
Slot-Start, keine Wächter-Ereignisse, Operator: alle vier „gut
gelungen").  **Bekannte Kosten:** ~12 MB und ~1 Thread pro Slot-Start
bleiben bis zum Nacht-Neustart (verworfene Quelle/Bridge werden nicht
freigegeben); bei wenigen Slots/Tag vernachlässigbar gegenüber dem
Leerlauf-Leck.  **Stall-Test unter Plan A live 22:20 (DEVA zweimal
stromlos):** Erholung über frische Quellen 6–7 s nach Rückkehr des DEVA
(Stille 29 s / 58 s = Ausfall + Bridge), kurzer „Hacker" beim Übergang
von Stille auf den frischen Puffer (Operator: verschmerzbar).  Befund:
verworfene Eingänge pollten weiter und hielten nach der Rückkehr je
einen DEVA-Platz (Stop geht in `input.http` verloren, solange es einen
toten Server pollt) → **Reaper** im Frame-Zähler (`webstream_reap`,
`start`+`stop` beim ersten „connected"), Replikat: jede verworfene
Quelle binnen 3 s weg.  Aktiv nach Neustart PLAYOUT → LIQUIDSOAP.

### ✅ Jingle „StationID Friska Viljor.mp3" ist für Liquidsoap unlesbar (neu 2026-09-05) — Fehlalarm, geklärt 2026-09-10

**Geklärt 2026-09-10 (Operator-Go, Punkt 1):** die Datei, die der
Replika-Push am 05.09. ablehnte, war nicht der Jingle, sondern der
**Artwork-Cache** der Library: `imported/<owner>/artwork/<Dateiname>`
ist die Cover-Grafik als Text-Datei (`data:image/...;base64,...`), dazu
die Größen `-32`/`-64`/`-128`/`-256`/`-512` (Data-URI) und `.jpg`
(binär).  Weil der Track-Dateiname selbst auf „.mp3" endet, heißt die
Cache-Datei ebenfalls „StationID Friska Viljor.mp3" — Inhalt beginnt
mit `data:ima`, mutagen: „can't sync to MPEG frame".  Der echte
Jingle liegt unter `imported/2/Example Radio/StationID/StationID Friska
Viljor.mp3.mp3` (Analyzer hängt die Endung an): MPEG-1 Layer 3,
320 kbit/s, 48 kHz, Stereo, 9,96 s, ID3v2.3 mit Cover; Liquidsoap
`request.resolve` = true, Dauer 9.96 s.  Kein Handlungsbedarf; ein
Library-Scan nach unlesbaren Dateien bleibt ein Preflight-Kandidat
(💡, nicht dringend).

**Befund:** Replika-Push der Datei aus `media/imported/2/artwork/`
scheitert mit `[decoder:2] Error while checking file's content:
Audio_converter.Channel_layout.Unsupported` — ein Kanal-Layout, das
der Decoder nicht wandelt (vermutlich Mono/Mehrkanal-Tag).  Im Live-
Betrieb würde der Titel still ausfallen UND den Retry-Poller starten.
**Test:** `ffprobe` auf die Datei (Kanäle/Layout), Datei als Stereo
neu kodieren oder in Liquidsoap `audio_to_stereo`/Decoder-Settings
prüfen; danach Library auf weitere Dateien mit demselben Layout
scannen (Preflight-Kandidat: „Datei nicht dekodierbar").

### 🟢 PortAudio-Geräteindex instabil → `device_name` statt `device_id` — umgesetzt 2026-09-05 (`1dbeb71`)

**Befund:** Der Index desselben Tascam-WASAPI-Endpunkts war 11:15 = 14,
12:10 = 18, 12:33 = 15 (sounddevice und Liquidsoaps PortAudio stimmen
überein; Endpoints kommen und gehen — Jabra-USB, HDMI).  Nach dem
Reboot löste PLAYOUT 11:15:18 Index 14 auf, Liquidsoap öffnete
11:15:28 Index 14 = inzwischen Realtek: **der Main Output lag den
ganzen Tag auf der Realtek-Onboard-Buchse** (Session-Sonde
`C:/Temp/audio_sessions.py <pid>`, pycaw in `C:/Temp/pylibs`), auf
dem Tascam kam nichts an.  Zweite Gefahr: ein ungültiger Index beim
Öffnen (`Invalid number of channels` / `Invalid sample rate` / WDM-KS
„Blocking API not supported") ist eine unbehandelte Exception im
Clock-Thread → Prozess-Exit 2 → NSSM startet mit derselben .liq neu →
**Neustart-Schleife = Sendeausfall** (heute 11:15:15 einmal passiert,
gerettet nur, weil PLAYOUT dazwischen neu gerendert hatte).
**Semantik `device_name` (gemessen):** exakter Namensvergleich, erster
Treffer in PortAudio-Reihenfolge (MME → DirectSound → WASAPI → WDM-KS);
MME-Namen sind auf 31 Zeichen gekürzt.  „Tascam-Lautsprecher
(US-16x08)" (30 Zeichen) → **MME-Eintrag** (8 Kanäle, blockierend OK,
Windows resampelt; Session landet auf dem Tascam); „Realtek-
Lautsprecher (Realtek(R) Audio)" → DirectSound (Stub, kein Ton!).
Nicht-Treffer → Fehlermeldung listet alle Gerätenamen (Prozess-Exit).
**Optionen (Trade-offs, Go nötig):**
1. Renderer schreibt `device_name="<PortAudio-Name>"` statt
   `device_id` — indexunabhängig, aber Host-API nicht wählbar (Tascam →
   MME statt WASAPI: höhere Latenz, kein Mix-Format-Zwang mehr).
   ~2 h inkl. Resolver-Anpassung, Prüf-Render, Tests.
2. `device_id` behalten, aber der Boot-Race-Fix (Option 2 dort:
   PLAYOUT startet LIQUIDSOAP nach dem Render) plus **Geräte-Watchdog**:
   Session-Sonde alle 15 min im Preflight — liegt die Liquidsoap-
   Session nicht auf dem gewählten Endpunkt → Warnung im UI.  Löst
   den Index-Drift zwischen Render und Öffnen nicht.  ~3 h.
3. Beides: `device_name` für Robustheit + Watchdog für Sichtbarkeit.
**Empfehlung:** 3, beginnend mit 1.  **Betriebsregel bis dahin:**
nie LIQUIDSOAP allein neu starten — immer PLAYOUT (rendert den Index
neu) → LIQUIDSOAP, danach Session-Sonde: Session muss auf
„Tascam-Lautsprecher (US-16x08)" liegen.

**Umgesetzt 2026-09-05 (Operator-Go, `1dbeb71`):** Option 3.
Renderer schreibt `device_name=` wenn der erste exakte Namens-Treffer
ein Ausgang auf MME/WASAPI ist und im blockierenden Probe öffnet
(Tascam → MME-Eintrag), sonst weiter `device_id=` mit Begründung im
Log; Boot-Race-Fix (PLAYOUT startet LIQUIDSOAP im 10-min-Boot-Fenster
selbst neu); Preflight-Watchdog `main_output_session_missing`
(Session-Sonde alle 15 min, pycaw/comtypes im venv).  Replika:
Session liegt auf dem Tascam.  Die Betriebsregel bleibt für manuelle
Neustarts außerhalb des Boot-Fensters sinnvoll (Index-Drift zwischen
Render und Öffnen ist mit `device_name` aber entschärft).

### ✅ Line-In-Startlücke: Capture-Kette verkürzen (neu 2026-09-03, Paket umgesetzt und abgenommen 2026-09-04, abgehakt 2026-09-09)

**Abgehakt 2026-09-09:** das Paket „Line-In-Latenz" (unten) ist seit
2026-09-04 live und abgenommen — Startlücke 6 → 2,0 s, Abschneiden am
Ende 6 → ~2 s.  Die restlichen ~2 s sind die Kette selbst; weiter nur
über „Quellen vorwärmen — Gate im Bus-Switch" (💡 oben).  Der folgende
Absatz ist der Stand vor dem Paket.

**Stand (vor dem Paket):** Die Lücke zwischen Show-Ende und erstem hörbaren Line-In-
Signal liegt bei **~6 s** (vorher ~7 s).  Der 2026-09-03er Tuning-
Schritt (`input.http` `max_buffer` 4,0 → 2,0 s, `poll_delay` 2,0 →
0,5 s, http-Quelle parallel zum Feeder-Start scharfgeschaltet) hat nur
~1 s gebracht — `max_buffer` ist **nicht** der dominierende Anteil.

**Messung (15:15-Show):** PLAY bei +0,005 s, `linein_start_http` bei
+0,054 s (Parallel-Arming greift), ffmpeg meldet „streaming" bei
+1,6 s — bis Liquidsoap die Quelle übernimmt vergehen aber weitere
~4 s.  Der Löwenanteil steckt also in der Capture-Kette selbst:
Gerät öffnen → sounddevice-Feeder-Health-Check (~1,5 s) → ffmpeg-
Encoding → genug MP3 im Icecast-Mount, damit ein Decoder einrastet.

**Evaluierung 2026-09-04 (nach Hörtest 15:55–16:20, Go ausstehend):**
Der Operator hat die Sekunden live ins Mikrofon gesprochen — die
**letzten ~6 s der Line-In-Show fehlen** auf dem Stream.  Das ist
dieselbe Größe wie die Startlücke: die **Durchlauf-Latenz L** der
Kette.  Was zur Studiozeit t gesprochen wird, erreicht den Stream bei
t+L; beim Slot-Ende E steckt alles aus [E−L, E] noch in der Kette und
wird mit dem Schließen der Quelle verworfen.  Vorwärmen behebt nur die
Startlücke, NICHT das Abschneiden — nur ein kleineres L hilft beidem.

Aufschlüsselung von L (~6 s) — **korrigiert nach Messung am echten
Mount (16:56, vier isolierte Hörer):**
- ~~Icecast `burst-size` 65535 B (2,7 s)~~ — der `/linein-capture`-
  Mount hat seit 2026-05-13 bereits `burst-size 0` (`config/icecast.xml`
  ist die Live-Konfiguration, `-c C:\rastatime\config\icecast.xml`).
  Meine erste Zuordnung war falsch.
- **FFmpeg-Format-Autodetection ≈ 5 s** (dominant): Icecast-
  `access.log` zeigte Quelle und Hörer ab +0,0 s verbunden, Audio ab
  +0,7 s, Decoder erst bei +6 s.  Hörer mit Default-Argumenten: 6 s;
  mit `format="mp3"`: **1 s**; `format` + Probe-Argumente: 2 s; nur
  Probe-Argumente: 6 s.  Ein ffmpeg-HTTP-Server im Reinraum zeigte das
  nicht (1 s) — er sendet einen Header, Icecast-Hörer steigen mitten
  im Datenstrom ein.
- `input.http max_buffer` = 2,0 s → permanente Latenz.
- Decoder + Switch-Transition ≈ 0,5–1 s.
- Feeder → ffmpeg: 0,1 s; ffmpeg bereits `nobuffer/low_delay/flush_packets`.
- Nur Startlücke: Health-Check `time.sleep(1.5)`.

**Paket „Line-In-Latenz" — UMGESETZT 2026-09-04 (Go des Operators):**
1. `linein_http`: `format="mp3"` (Konstante `LINEIN_HTTP_FORMAT`).
2. `max_buffer` 2,0 → 1,0 s.
3. Health-Check 1,5 → 0,75 s (`_STARTUP_HEALTH_CHECK_S`).
Kein ICECAST-Neustart nötig; PLAYOUT + LIQUIDSOAP.  **Live-Abnahme
2026-09-04 17:45–17:50 (Operator zählt Sekunden ins Mikrofon + Monitor):
Startlücke 6 → 2,0 s** (Feeder streamt +0,93 s, Decoder bereit +2,0 s,
keine Decoder-Fehler), **Abschneiden am Ende 6 → ~2 s**.  Damit ist
das Paket abgenommen.  Die verbleibenden 2 s an beiden Enden sind die
Kette selbst (Feeder-Start + Poll + Decoder bzw. Puffer + Decoder) —
weiter nur über „Quellen vorwärmen — Gate im Bus-Switch" (Start) und
den dort beschriebenen Gate-Off-Crossfade (Ende).

Die verbleibenden ~2 s sind normale Sendeketten-Latenz; Moderatoren
enden entsprechend früher (Studio-Praxis, im Manual dokumentieren).
Nicht empfohlen: „Drain" am Slot-Ende (Quelle L Sekunden länger halten)
— verschiebt jedes Folgeelement um L, Jingles/Stundenwechsel unpünktlich.

### 💡 Testplan erstellen (neu 2026-09-02, Reihenfolge-Punkt 14)

**Status:** Idea — Operator-Wunsch 2026-09-02, Umfang noch zu klären.
**Kontext:** Bisher wird punktuell getestet (pytest-Suiten für
playout/audio/api, plus manuelle Live-Verifikation nach UI-Commits
laut ASSISTANT.local.md).  Was fehlt, ist ein **zusammenhängender,
dokumentierter Testplan** — insbesondere für die Dinge, die nur
live prüfbar sind (Sendekette, Line-In, Recording, Show-Übergänge).
**Vor der Evaluierung mit dem Operator zu klären:**
- Zielgruppe: nur Operator-Selbsttest, oder übergabefähig für Dritte?
- Umfang: reine Abnahme-Checkliste (manuell) vs. automatisierte
  Regressionsschicht vs. beides?
- Auslöser: vor jedem Release / nach Maschinenwechsel / periodisch?
- Soll die Live-Verifikations-Konvention aus ASSISTANT.local.md darin
  aufgehen?
**Erfahrungswert aus der Line-In-Abnahme (2026-09-01/02):** die
teuersten Fehler waren NICHT im Code (Voice-Clarity-APO, Erdschleife,
verklemmter Capture-Handle).  Ein guter Testplan braucht daher auch
**Umfeld-Checks** (Windows-Audio-Effekte aus, Pegel/Rauschabstand
messbar, Geräte-IDs aktuell), nicht nur Software-Tests.

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
Der Feeder-Modus wurde daher MME (siehe ✅-Status oben); das
ASIO-No-Go bleibt unverändert gültig.

**Nachtrag 2026-09-03 („Option B"):** Auch die Automatik-Entscheidung
„≤2ch → dshow" ist gefallen.  Der dshow-Pfad adressiert das Gerät als
`audio=@device_cm_{...}\wave_{<GUID>}` aus der gespeicherten Windows-
Audio-**Endpoint**-GUID — DirectShow führt aber eine eigene
Geräte-GUID-Liste und kennt diese nicht.  An der 15:20-Testshow
(„Tascam 1-2") antwortete ffmpeg `Could not find audio only device`
und der Slot ging **stumm auf Sendung**.  Seither läuft jeder geplante
Line-In über den MME-Feeder (löst per Anzeigename auf); dshow ist nur
noch Fallback für Alt-Zeilen ohne `device_name`.  Kein
Operator-Schalter — die Automatik bleibt, nur ihre Bedingung ist jetzt
„device_name vorhanden?" statt „Kanalzahl?".

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

### ✅ Import-Ordner: Ruhe-Prüfung vor dem Import (evaluiert + umgesetzt 2026-09-17)

**Umgesetzt 2026-09-17 (Operator-Go; `67db437`; Details im CHANGELOG „Fixed"):**
`QUIET_SECONDS = 60` in `LocalImportScanTask` — importiert wird nur, was
60 s unverändert ist; Statuszeile zählt „settling".  FTP-Server und
FTP-Polling: Operator 2026-09-17 „eventuell später" (💡 unten bleibt).
**Nebenbefund:** Manual LOCAL_MACHINE „How files are processed" beschreibt
einen nie gebauten Ablauf (Staging-/.failed-Ordner, rekursive Unterordner
mit Album-Zuordnung) — der Code verschiebt nach organize, löscht
Fehlschläge und ignoriert Unterordner; Doku-Drift, Korrektur in 4 Sprachen
steht aus (🟡).  **Korrigiert 2026-09-17** in allen vier Sprachen
(Abschnitte + Fehlersuche; `46c0ce3`).

**Anlass (Operator-Fragen 2026-09-17):** Was passiert nach dem Import
(Antwort: Audio wird in die Bibliothek VERSCHOBEN, fehlgeschlagene
Importe werden absichtlich gelöscht - Design 2026-05-16 gegen
Dauerwiederholung; Nicht-Audio und Unterordner bleiben liegen)?  Gehen
Netzlaufwerke oder FTP als Quelle?

**Befund:** `LocalImportScanTask::scanOnce` hat KEINEN Schutz gegen halb
geschriebene Dateien - der 5-Minuten-Scan kann eine Datei mitten im
langsamen Upload wegziehen (kaputter Import + Quelle gelöscht =
Verlust).  Lokal nie aufgefallen, bei Netz-/FTP-Zulieferung real.

**Empfehlung (Go ausstehend):** Ruhe-Prüfung - nur Dateien importieren,
deren mtime älter als ~60 s ist; ~1-2 h inkl. Test + Manual-Hinweis
LOCAL_MACHINE (4 Sprachen).  Vorbedingung für jede Netz-/FTP-Quelle.

**Quellen-Varianten:**
- FTP-Server AUF der Studiomaschine mit Wurzel = Import-Ordner: kein
  RASTATIME-Code, Operator installiert/verwaltet (z. B. FileZilla
  Server); empfohlen für Zulieferung von Vorproduktionen.
- NAS per UNC-Pfad: Validierung akzeptiert UNC heute schon (nur
  is_dir/is_writable), Scan läuft aber als LocalSystem im Apache-PHP →
  Freigabe müsste für das Computerkonto/Gast erreichbar sein oder das
  Dienstkonto von RASTATIME-APACHE umgestellt werden (Betriebsarbeit);
  gemappte Buchstaben (Z:) gehen prinzipiell nicht (Session-gebunden).
- 💡 Aktives FTP-Polling durch RASTATIME: zum vollen Item aufgewertet,
  siehe „Import from FTP Server" direkt darunter (2026-09-17).

### ✅ „Import from FTP Server“ als zweite Import-Quelle (evaluiert + umgesetzt 2026-09-17)

**Umgesetzt 2026-09-17 (Operator-Go mit Antworten: löschen nach
Abholung ja, FTP+SFTP — geliefert FTP/FTPS/SFTP via PHP-curl —,
Zugangsdaten in cc_pref, 5-min-Takt, Import-Ordner-Abhängigkeit in UI +
Handbuch; `75d52f8`; Details im CHANGELOG „Added“).**  Entfernte Ruhe-Regel
nach Replikat-Befund (wachsende Datei schlüpfte durch die reine
Nach-Download-Probe): zwei größenstabile Sichtungen ≥ 60 s.  Live-Test:
pyftpdlib (Abholen+Löschen+wachsende Datei bleibt) + SFTP-Listing gegen
test.rebex.net.  ARCHITECTURE 0.38 (§23.36).

**Operator-Wunsch 2026-09-17:** zusätzlich zum Import-Ordner einen
entfernten FTP-Server als Quelle, manuell aktivierbar/deaktivierbar.
Klarstellung: genau das IST das FTP-Polling — FTP kennt kein Push,
RASTATIME muss regelmäßig nachsehen und abholen.

**Design (Evaluierung):** Abhol-Task im PHP-Task-Manager (5-min-Takt
wie der Ordner-Scan + „Fetch now"), lädt per PHP-curl (FTP/FTPS) in den
lokalen Import-Ordner herunter — ab dort übernimmt die bestehende Kette
inkl. Ruhe-Prüfung, kein zweiter Import-Pfad.  Einstellungen in cc_pref
(enabled, host, port, user, password, remote path, FTPS); UI-Sektion
unter dem Import-Ordner.  Aufwand ~1 Tag inkl. Live-Test mit
Wegwerf-FTP-Server (pyftpdlib aus der venv) und Handbuch ×4.

**Klärfragen vor dem Go:** (a) nach Abholung entfernt löschen?
(empfohlen: ja = Briefkasten-Semantik, braucht Löschrecht; sonst
Merkliste nötig); (b) FTP oder FTPS — was kann der Ziel-Server?
(Klartext-FTP überträgt das Passwort offen); (c) Zugangsdaten in
cc_pref wie andere Dienst-Passwörter ok?; (d) 5-Minuten-Takt
ausreichend?  Voraussetzung: Import-Ordner bleibt konfiguriert.

**Alternative ohne Code** (Operator 2026-09-17 „eventuell später"):
FTP-Server AUF der Studiomaschine mit Wurzel = Import-Ordner; braucht
Erreichbarkeit von außen (Portfreigabe, Härtung).

### ✅ Backup/Restore via UI (Settings-Submenü) — DONE 2026-09-17

**Stufe 3 gebaut 2026-09-17 (Operator-Go; `a522ede`):** Auto-Sektion (alle N Tage, Aufbewahrung, cc_pref
`local_backup_auto`), Kommando `backup_auto` (Fälligkeit selbst geprüft,
derselbe BackupJob, Aufräumen mit Überlebensgarantie fürs neueste ZIP),
Runner `scripts/backup-auto.ps1` für die einmalige Aufgabenplaner-
Registrierung (Befehl im Skriptkopf + Handbuch), schlanke
Restore-Sektion.  **In Betrieb seit 2026-09-17 15:48:** API neu
gestartet (Operator), Aufgabe „RASTATIME-Backup" registriert (täglich
03:30, SYSTEM; nach PowerShell-Quoting-Stolperer des Operators in der
erhöhten Sitzung übernommen), zwei Probeläufe mit Exit 0 und korrektem
„nothing to do: disabled"; Log `logs/backup-auto.log` sauber
(PYTHONPATH-Nachtrag im Runner).  **Offen nur noch:** Auto-Sektion in
der UI aktivieren + ersten Nachtlauf im Log prüfen.


**Neu-Evaluierung + Operator-Go 2026-09-16 (Arbeitsreihenfolge Punkt 10):**
Die Lücke von damals (Async-Job/Progress-Infra) existiert seit dem
Storage-Umzugs-Job nicht mehr — Stufe 1 (Manual Backup: DB im
pg_dump-Custom-Format + alle Config-Dateien + Manifest als ein ZIP,
Backup-Ordner als Einstellung, Liste + Download, Job im API-Prozess nach
dem MoveJob-Muster) **gebaut 2026-09-16** (`df53122`; Details im CHANGELOG
„Added"; Settings → Backup, 5 API-Routen, PHP-Proxies, Handbuch-Kapitel
BACKUP in 4 Sprachen, ARCHITECTURE §23.35).  DB-Zugangsdaten aus
libretime.conf (Operator-Entscheidung).  Grundsatzfragen beantwortet:
Scheduler = Windows-Aufgabenplaner + Management-Command (Worker bleibt
Stub); Speicherort = serverseitiger Zielordner + Liste; Restore =
schlank (Browser + Anleitung, kein 1-Klick-Restore).  **Live abgenommen
2026-09-17 10:20:** erstes Operator-Backup über die UI, ZIP-Integrität OK,
`db.dump` per `pg_restore --list` gelesen (47 Tabellen mit Daten), Config
+ Manifest vollständig.  **Offen: Stufe 2**
(Media serverseitig per robocopy-Spiegel + Verify) **und Stufe 3**
(Auto-Backup-Sektion + `backup_run`-Command + Aufbewahrung, Restore-
Sektion als Backup-Browser).  **Stufe 2 gebaut 2026-09-17** (`72e13c7`): Option „Include media library",
robocopy-/MIR-Spiegel nach `<Ordner>/media` mit Verify, Phasen +
Fortschritt + Cancel; Tests mit echtem robocopy inkl. Purge-Nachweis.
**Live abgenommen 2026-09-17 15:31** (nach dem Checkbox-Proxy-Fix
`3a31f5b`): 2512 Dateien / 6,7 GB in 24 s, Spiegel deckungsgleich.

**Status (ursprünglich 2026-05-31):** Defer — A + B empfohlen & gut machbar (architektur-angepasst),
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

**Statusberichtigung 2026-09-23 (Punkt-5-Aufnahme):** Die Funktion ist seit
2026-06-15 KOMPLETT GEBAUT und LIVE — Stufe B: `ShowShiftService` (Kaskade
Anchor/Clearing/Shift, forward-only), `ShowShiftTask` alle 2 min (letzter
Lauf heute 23:06), Checkbox „Allow delayed start?" im Show-Formular,
Handbuch `DELAYED_START.md` EN/DE/FR/ES, CHANGELOG (Commits fe630ec →
53788ba).  Die Neubewertung vom 2026-09-10 unten war ein Buchungsfehler
(ging von ungebaut aus).  **Was wirklich offen ist:** 0 von 489 Shows haben
die Checkbox gesetzt, 0 verschobene Instanzen in 90 Tagen, 0 Log-Zeilen —
die Funktion hat im Betrieb noch nie gearbeitet und wurde nie mit einem
echten Overrun live verifiziert; der PHP-Service hat KEINE automatischen
Tests (die „zehn Scheduler-Testdateien" sind Playout-Tests, nicht dieser
Service).  Design-Entscheide (Stufe, Ende der verschobenen Show, Kaskade,
Obergrenze über 15-min-Lead) sind im Service-Docblock festgehalten.
Nächster Schritt = Operator-Entscheid: kontrollierte Live-Abnahme mit
Testshow-Overrun oder dunkel lassen bis zum ersten Opt-in.

**Status (alt, überholt):** Go vom 2026-05-22; Operator 2026-09-10: „für später gemerkt".

**🟢 Erweiterung „Filler statt Kürzung" — GEBAUT 2026-09-27 (Operator-Go,
Entscheide D1: Outro bleibt, davor ersetzen · D2: bis ≥ Lücke füllen, letzter
Filler gekürzt · D3: mehrere Titel · D4: nur B; Details CHANGELOG „Added").
Live-Probe 2026-09-27 BESTANDEN (Details CHANGELOG „Fixed" 27.09.).
**Marker-Bug BEHOBEN 2026-09-27** (Migration 0058, `delayed_start_from`; Details
CHANGELOG „Fixed" 27.09.).  Ursprüngliche Evaluierung:** Im SHIFT-Fall wird der überstehende
Schluss von Show B nicht gekürzt, sondern die nicht mehr passenden
Schluss-Titel werden entfernt und die Lücke bis B.ends aus einer unter
Settings → General wählbaren **Filler-Playlist** (Picker wie
„Traffic-Alert Smart Block", aber `getPlaylistNames`) mit passend langen
Titeln gefüllt.  Datenlage komplett: `cc_playlistcontents.cliplength`
liefert Dauern, der Shift läuft in einer Transaktion mit anschließendem
PushSchedule, Insert-Form für cc_schedule ist bekannt (Scheduler.php).
Kein Schema-, kein Playout-Eingriff.  Aufwand ~400-500 LoC PHP + Manual
×4, 1,5-2,5 Tage inkl. Live-Probe mit Testshows (die auch den bisher nie
ausgelösten Basis-Shift abnimmt).  Offene Entscheide: (D1) letzten Titel
oder letzten Titel VOR dem Outro-Jingle ersetzen; (D2) Rest-Politik —
Empfehlung: bis ≥ Lücke füllen, der letzte Filler wird gekürzt (nie
Stille, nie ein Show-Titel gekürzt); (D3) mehrere Schluss-Titel entfernen,
wenn der Überhang länger als einer ist; (D4) Geltung auch für As eigene
Kürzung im ANCHOR-Fall; (D5) Wiederholungs-Vermeidung der Filler (v2).
Hinweis: Legacy-PHP hat keine Test-Infrastruktur — Auswahl-Logik als
reine Funktion bauen, Abnahme per Probe-Protokoll.
Die Vorbedingung ist inzwischen erfüllt (zehn Scheduler-Testdateien,
~2.900 Zeilen).  **Neubewertung 2026-09-10:** Stufe A nur im Playout
(Checkbox pro Show, die Timer der Folgeshow werden um den Überhang des
letzten Titels verschoben, Datenbank und Anzeige bleiben unverändert, die
Folgeshow wird am Ende gestaucht; ~600 Zeilen, 2–3 Tage) oder Stufe B wie
unten (Zeilen der Folgeshow in der Datenbank verschieben, Dashboard,
Aufnahme und History folgen; mehrere Wochen).  Vor dem Start ein
Design-Entscheid in eigener Sitzung: Stufe, Verhalten am Ende der
verschobenen Show, Obergrenze des Überhangs, Zusammenspiel mit der
Einstellung „Overbooked trimmen" (`schedule_trim_overbooked`), die das
Gegenteil tut.
**Status (alt):** Go, mit Vorbedingung (Scheduler-Tests erst).
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

### ✅ Seamless Bus-Mix — Output-Stack-Politur (CLOSED 2026-09-11)

**Status:** ✅ Geschlossen 2026-09-11 (Arbeitsreihenfolge Punkt 6,
Statusprüfung auf Operator-Wunsch).  Alle drei Symptome sind durch die
Liquidsoap-Migration (Phase 0–D, Cutover 2026-05-28) und die Folgearbeiten
erledigt:
- **#1 Listener-Reconnect / Counter-Reset:** Liquidsoap hält je Mount eine
  persistente Icecast-Quelle.  Beleg 2026-09-11 08:20 (`status-json.xsl`):
  `rastatime`, `rastatime-aac`, `rastatime-ogg` verbunden seit 2026-09-10
  13:28:15 = seit dem letzten LIQUIDSOAP-Start, über alle Titel- und
  Showwechsel hinweg.
- **#2 Tail-Cut bei kurzen Titeln:** Liquidsoap spielt die Queue gapless;
  `cue_out` läuft als Annotation mit, der Titel läuft in der Überlappung zu
  Ende statt abgeschnitten zu werden.  Live-Abnahmen: Paket 2 (`ff567ce`,
  2026-09-04) und die Sechs-Show-Sequenz 2026-09-10 11:00 („alle Shows
  klangen gut", Übergang Show 1→2 nahtlos).
- **#3 1–2 s Stille beim Webstream-Wechsel:** Vorwärmen mit Gate (Paket 2)
  und frische `input.http`-Quelle je Slot (Plan A, `1eb8713`, 2026-09-08),
  live bestätigt 2026-09-08 (12:07, 17:07, Stall-Test 22:20).
- **Obsolet-Liste:** `mpv_engine.py`, `ffmpeg_streamer.py`, `_stop_streamers`
  und der Tail-Flush-Wait sind am 2026-09-10 gelöscht (`2590cf2`).
  `Scheduler::calculateCrossfades` (PHP) bleibt bewusst: sie legt die
  Überlappung in der Zeitachse (`cc_schedule.starts/ends`) aus
  `default_crossfade_duration` an, derselben Quelle wie der Liquidsoap-
  Crossfade.  Der Rollback-Plan (Feature-Flag zu mpv) ist mit der Löschung
  hinfällig.

**Ursprünglicher Eintrag (2026-05-25):**

**Status (alt):** Go in zwei Phasen.  Phase 1 sofort (Tail-Cut-Bug),
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

**Status:** 🟢 **ENTBLOCKT 2026-09-02** — die zusätzliche Festplatte ist
geliefert (Operator-Meldung 2026-09-02); als Reihenfolge-Punkt 7
eingeplant.  Vor Umsetzung: 6-Punkte-Evaluierung + Wartungsfenster
vereinbaren (Sendepause nötig), Backup vorher verifizieren.

**Evaluierung 2026-09-15 (Arbeitsreihenfolge Punkt 7):** Empfehlung **Go**
in drei Stufen, wartet auf Operator-Go und Wartungsfenster.

*Ist-Stand:* `D:` = Intel-RAID-1-SSD, 1,86 TB, NTFS, leer, gesund,
Authentifizierte Benutzer haben Ändern-Recht (Dienste laufen als
LocalSystem).  Bibliothek `C:\rastatime\media`: 4,3 GB, 2.489 Dateien
(344 Audio, 2.120 Cover unter `imported/2/artwork`, 1 Show-Bild, 1 Auto-DJ-
Logo, 4 hängende Importe vom 2026-05-20 in `organize/`, deren cc_files-Zeilen
599/616/627/631 leeren `filepath` und `import_status=2` haben).  Die
Storage-Wurzel steht nur in `libretime.conf` (`storage.path`); PHP
(`Config::getStoragePath`), API (`settings.CONFIG.storage.path`), PLAYOUT
(`config.storage.path`, Direktzugriff auf die Bibliothek für den Cache) und
Analyzer (Zielordner kommt je Import-Nachricht aus PHP) lesen sie von dort.
Kein Apache-Alias, keine Tabelle `cc_music_dirs`.

*Abweichungen von MIGRATION.md §4.4/§4.5 (dort nicht erfasst):*
- Die owner-id-Ebene wird an **vier** Stellen erzeugt, nicht nur in
  `MediaService.php:35`: `backend/api/libretime_api/podcasts/download.py:169`
  (Podcast-Downloads, `imported/<owner>` bzw. `imported/podcast`),
  `PreferenceController.php:1055` (Auto-DJ-Logos) und
  `ShowImageController.php:168/292` (Show-Bilder).
- `cc_files.filepath`: 343 Zeilen unter `imported/2/`, davon **36 mit
  führendem Schrägstrich** (`/imported/2/podcast_…`, Podcast-Importe) — das
  Muster in §4.4(c) (`^imported/[0-9]+/`) träfe sie nicht; nötig ist
  `^/?imported/[0-9]+/`.  Kein Interpret-Ordner ist rein numerisch (die
  Idempotenz-Warnung greift nicht).
- `cc_files.artwork`: 216 Zeilen `imported/2/artwork/…` — ebenfalls umschreiben.
- `cc_show.image_path` (29 Zeilen) und `cc_pref.auto_dj_logo_path` halten
  **absolute** Pfade `C:/rastatime/media/imported/2/…` — brechen schon durch
  den Wurzelwechsel, müssen auf `D:/stor/imported/…` umgeschrieben werden.
- PLAYOUT entfernt einen führenden Schrägstrich selbst (`lstrip("/")`),
  PHP joint per `OsPath::join`, API per `Path(...) / rel` — die Schreibweise
  der DB-Pfade darf bleiben.

*Eingriff:* (1) `libretime.conf` `storage.path: D:/stor`; (2) vier
Code-Stellen ohne owner-id-Segment (PHP live ohne OpCache, API/Worker
Neustart); (3) eine DB-Transaktion: `cc_files.filepath`, `cc_files.artwork`
(`^/?imported/[0-9]+/` → `imported/`), `cc_show.image_path` und
`cc_pref.auto_dj_logo_path` (Präfix `C:/rastatime/media/imported/2/` →
`D:/stor/imported/`); (4) Dateien: `imported/2/*` → `D:\stor\imported\`
(flach), `organize/` → `D:\stor\organize\`; (5) Neustart API, WORKER,
ANALYZER, PLAYOUT — LIQUIDSOAP, STANDBY, Icecast und Apache bleiben laufen
(Liquidsoap spielt aus dem PLAYOUT-Cache `C:\rastatime\scheduler`); (6)
Umfeld: Windows-Search-Indexierung auf `D:` ist an (für `D:\stor` abschalten),
Defender-Ausnahme für `D:\stor` (siehe Nebenbefund).

*Ablauf in drei Stufen:* **A** Vorbereitung ohne Betriebseingriff:
Migrations- und Prüfskript mit Trockenlauf (zählt, schreibt nichts),
Vorkopie `robocopy /MIR` der 4,3 GB nach `D:\stor` im laufenden Betrieb, DB-
Dump.  **B** Wartungsfenster ~15 min ohne geplante Datei-Sendung
(Webstream-Slots sind unbetroffen, Hörer bleiben verbunden, der Stream zeigt
den Off-Air-Text): Dienste API/WORKER/ANALYZER/PLAYOUT stoppen, Schluss-Sync
(Sekunden), Conf + Code + DB-Transaktion, Dienste starten, Prüfung (3 Titel
abspielen, ein Cover, das Show-Bild, ein Test-Upload, ein Podcast-Download).
**C** `C:\rastatime\media` bleibt 7 Tage als Rückfall liegen, dann löschen.
Rückfall in B: Conf zurück, DB-Dump einspielen, Dienste starten — die Dateien
liegen noch an beiden Orten.

*Aufwand:* Code ~10 Zeilen an vier Stellen + API-Test für den Podcast-Pfad;
Migrationsskript mit Trockenlauf ~150 Zeilen (PowerShell/Python); DB-
Transaktion ~20 Zeilen; MIGRATION.md §4.4/§4.5 korrigieren, CHANGELOG,
ARCHITECTURE (Minor: Storage-Layout), BACKLOG, INSTALL.md/Handbuch-Stellen mit
dem Pfad.  *Dauer:* Stufe A ~3 h, Stufe B ~15–30 min, Stufe C 7 Tage warten.
*Sinn:* mittel — Bibliothek auf der gespiegelten Datenplatte, raus aus dem
Repo-Baum, sauberere Backups und Pfade; kein Platzdruck (C: 848 GB frei).
*Regel:* die DB-Umschreibung ist der eine direkte SQL-Schreibzugriff, den die
Betriebsregel „nur per API" sonst verbietet — nur im Fenster, nur mit
explizitem Go, in einer Transaktion.

*Offene Entscheidungen für den Operator:* (a) Fenster-Termin; (b) die 4
hängenden Importe in `organize/`: Zeilen löschen und Dateien neu importieren,
oder mitnehmen; (c) Aufnahme- und Import-Ordner (`C:\Users\studio\Music\…`,
Settings → Local Machine) ebenfalls nach `D:` (eigene Einstellung, kein Teil
dieses Umbaus); (d) Cover-Ordner `artwork` liegt danach unter
`D:\stor\imported\artwork` neben den Interpreten-Ordnern (wie heute unter
`imported/2/`).

**Stufe 1 umgesetzt 2026-09-16 (Operator-Go, `6059dc4`):** fünf Code-Stellen ohne owner-id-Ebene, Show-Bilder und
Auto-DJ-Logo relativ, Django-Befehl `storage_flatten` (Trockenlauf/`--apply`,
eine Transaktion, Rückgängig bei Fehler).  Trockenlauf in Produktion: 80
Einträge, 343 + 216 + 29 + 1 Zeilen, 343/343 Pfade auflösbar.
**Ausgeführt in Produktion 2026-09-16 09:10 (Operator, nach DB-Dump
`C:\\Temp\\optd\\db_before_flatten_20260916_091032.dump`):** 80 Einträge
verschoben, 343 + 216 + 29 + 1 Zeilen umgeschrieben, 343/343 Pfade
auflösbar, `imported/2` entfernt.  Live geprüft: Show-Logo und Auto-DJ-Logo
(HTTP 200), Cover-Endpunkt, drei Downloads über die API, Track-Metadaten.
RASTATIME-API-Neustart für den Podcast-Pfad durch den Operator.

**Neue Richtung (Operator 2026-09-15): Speicherort als Einstellung**
Nicht nur einmal nach `D:\stor` umziehen: unter Settings → Local Machine
soll der Speicherort der Bibliothek wählbar sein, wie der Import Folder.
Evaluierung 2026-09-15, Empfehlung Go in drei Stufen (wartet auf Go):

- *Machbarkeit:* ja.  Jeder Leser der Wurzel kann die Einstellung statt
  `libretime.conf` fragen: PHP (`Config::getStoragePath`, pro Request), API
  und Worker (`settings.CONFIG.storage.path` → Preference pro Aufruf), PLAYOUT
  (bei jedem Refresh wie die ICY-Werte), Analyzer (Zielordner kommt je Import
  aus PHP).  Vorbedingung: alle DB-Pfade relativ zur Wurzel (Stufe 1), sonst
  bricht jeder Wechsel Show-Bilder und Auto-DJ-Logo.
- *Eingriff:* neuer cc_pref-Schlüssel `local_storage_folder` (leer =
  `libretime.conf`); Feld + Knopf „Verschieben" auf der Local-Machine-Seite
  mit Fortschritt; API-Endpunkt Prüfen/Starten/Status; Umzugs-Job (kopieren →
  zählen/prüfen → Wurzel umschalten → alte Kopie stehen lassen, Hinweis zum
  Löschen), Importe während des Jobs gesperrt; Prüfungen: Pfad
  erreichbar/beschreibbar, nicht innerhalb der alten Wurzel, genug Platz.
- *Aufwand:* ~600–900 Zeilen (PHP/JS/Python) + Tests, Handbuch
  LOCAL_MACHINE EN/DE/FR/ES, ARCHITECTURE (Minor).  *Dauer:* Stufe 1
  (einmalige Bereinigung: owner-id-Ebene an vier Stellen, führende
  Schrägstriche, `cc_files.artwork`, Show-Bilder und Logo relativ) ~½ Tag
  inkl. ruhigem Moment für die DB-Transaktion; Stufe 2 (Einstellung + Job)
  2–3 Tage; Stufe 3 = erster Umzug nach `D:\stor` über die UI als Abnahme.
- *Sinn:* hoch für den Operator-Wunsch, keine Hand-Edits an
  `libretime.conf` mehr, der Umzug wird wiederholbar (weitere Platte, Backup-
  Rückspielung).  *Empfehlung:* Go; Stufe 1 ist auch für den reinen Umzug nötig
  und kann sofort beginnen.

**Stufe 2 umgesetzt 2026-09-16 (Operator-Go; Entscheidungen: alte Kopie löscht
der Operator selbst, keine Netzlaufwerke in v1, Aufnahme-/Import-Ordner bleiben
eigene Einstellungen; `c0b3c70`):** Einstellung,
Auflöser in PHP/API/PLAYOUT, Umzugs-Job, Import-Sperre, Preflight-Warnung,
Handbuch.  **Abnahme 2026-09-16 09:43 (Operator, über die Oberfläche):**
„Check" OK (1,9 TB frei), „Move library" → 2.489 Dateien / 4,5 GB in 9 s
kopiert, geprüft, umgeschaltet; Wurzel `D:/stor` (Quelle: Einstellung);
PLAYOUT folgte beim nächsten Refresh, Preflight ohne Warnung; danach
Show-Logo, Cover und drei API-Downloads von der neuen Wurzel geprüft.  Alte
Kopie unter `C:\\rastatime\\media` liegt noch (Operator löscht sie selbst,
Erinnerung ab ~2026-09-23).  Damit ist Arbeitsreihenfolge Punkt 7 erledigt.

**Stufe 2 im Detail (Evaluierung 2026-09-16):**

*Wahrheit und Leser:* neuer cc_pref-Schlüssel `local_storage_folder`
(leer = `storage.path` aus `libretime.conf`, das damit nur noch Startwert
ist).  Ein Auflöser je Seite: PHP `Config::getStoragePath()` fragt zuerst die
Einstellung (pro Request, wie `local_import_folder`); API/Worker
`libretime_api.storage.root.get_storage_root()` (Einstellung → Config, 15 s
Cache) an den drei Stellen `storage/views/file.py` (2×),
`podcasts/views/podcast.py` und als Standard von `storage_flatten`; PLAYOUT
holt die Wurzel bei jedem Refresh von `GET /api/v2/storage/location` (fällt
ohnehin auf den API-Download zurück, wenn der Direktzugriff fehlschlägt);
Analyzer bekommt das Ziel je Import aus PHP.  `conf.php` prüft beim Start
weiter, dass der Konfig-Pfad existiert — das alte Wurzelverzeichnis bleibt
daher als leerer Ordner stehen (die Löschfunktion leert nur den Inhalt).

*Umzugs-Job (im API-Prozess, Thread; Zustand als JSON in cc_pref
`local_storage_move`, überlebt einen API-Neustart als „unterbrochen →
fortsetzen"):* 1 Prüfen (absolut, lokales Laufwerk — kein UNC in v1,
anlegbar/beschreibbar per Testdatei, nicht in der alten Wurzel und
umgekehrt, freier Platz ≥ Bibliotheksgröße + 10 %) → 2 Importe sperren (eine
Prüfung `Application_Common_Storage::assertWritable()` in MediaService,
LocalImportScanTask, Show-Bild- und Logo-Upload; Podcast-Download in der
API) → 3 Kopieren mit `robocopy <alt> <neu> /E /COPY:DAT /R:2 /W:2 /NP`
(wiederaufnehmbar, Fortschritt = Bytes im Ziel gegen Ausgangsgröße alle 2 s)
→ 4 Prüfen (Dateizahl und Bytes gleich, jede `cc_files.filepath` im Ziel
vorhanden) → 5 Umschalten (Einstellung setzen; PHP/API sofort, PLAYOUT beim
nächsten Refresh) → 6 alte Kopie bleibt; Knopf „Alte Kopie löschen" mit
Rückfrage, nur wenn Schritt 4 grün war.  Abbruch während 3 erlaubt (Ziel
bleibt teilkopiert, ein neuer Start setzt fort); nach 5 kein Rückweg per
Knopf, Rückfall = Einstellung leeren (alte Kopie liegt noch).

*Zugriffsschutz:* Start/Abbruch/Löschen nur über PHP-Actions hinter Login +
CSRF (wie `restart-audio-chain`); PHP ruft die API auf localhost mit dem
API-Key auf.  Die API-Endpunkte `storage/location`, `storage/move` (POST
start/cancel/delete-old, GET status) verlangen den API-Key — anders als die
Soundkarten-Endpunkte, die ohne Auth auf 0.0.0.0:8765 antworten.

*Oberfläche (Local Machine, Abschnitt „Media Library Location"):* aktueller
Pfad, Herkunft (Einstellung/Konfiguration), Bibliotheksgröße, freier Platz am
Ziel; Feld + „Prüfen" + „Verschieben" (Rückfrage), Fortschrittsbalken
(Poll alle 2 s), danach Hinweis auf die alte Kopie mit Löschknopf; bei
„unterbrochen" ein „Fortsetzen".  Tooltips per rtTooltip.  Preflight-Warnung
`storage_root_unavailable` (Wurzel fehlt/nicht beschreibbar, z. B. Platte
weg) im Dashboard-Banner.

*Eingriff:* API ~350 Zeilen + Tests ~250; PHP ~350 (Config/Storage,
Controller-Actions, Sperren, Seite + JS); PLAYOUT ~40 + Tests; Handbuch
LOCAL_MACHINE EN/DE/FR/ES, INSTALL.md/MIGRATION.md (Konfig-Pfad = Startwert),
CHANGELOG, ARCHITECTURE Minor (0.34).  *Dauer:* ~2 Tage Bau, Abnahme = Umzug
nach `D:\stor` über die Oberfläche (4,3 GB ≈ 1 min Kopie).  *Risiken:*
API-Neustart während der Kopie (wiederaufnehmbar), Defender-Echtzeitscan
auf dem Ziel (Ausnahme setzen), ACL: Zielordner erbt vom Laufwerk
(Authentifizierte Benutzer: Ändern — Backups ohne Erhöhung möglich, anders
als die Podcast-Dateien von 2026-06), lange Pfade (robocopy kann sie,
Prüfschritt nutzt `\\?\`-Präfix).
*Sinn:* hoch (Operator-Wunsch, wiederholbar, kein Hand-Edit).
*Empfehlung:* Go.  Offene Entscheidungen: (a) Löschen der alten Kopie per
Knopf oder nur manuell; (b) Netzlaufwerke (UNC) in v1 ausschließen; (c)
Aufnahme-/Import-Ordner bleiben eigene Einstellungen.

*Nebenbefund (eigenes Thema):* Auf der Maschine läuft **Microsoft Defender**,
nicht Bitdefender, und **keine einzige Pfad- oder Prozess-Ausnahme** ist
gesetzt — die Liste aus MIGRATION.md §3.2 gilt damit für Defender und ist
nicht umgesetzt.  Echtzeitscan auf `C:\rastatime\scheduler`, den Aufnahmen und
Liquidsoap kann I/O-Spitzen verursachen; Operator-Entscheidung.

**(Vorgeschichte:)** ERNEUT DEFER (Operator-Entscheid 2026-08-26 bei der Migration):
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

### ✅ Legacy-mpv-Code-Delete (erledigt 2026-09-10)

**Status:** ✅ **DONE 2026-09-10** (Arbeitsreihenfolge Punkt 15, Operator-Go).
Gelöscht: `mpv_engine.py`, `ffmpeg_streamer.py`, der Streamer-Test, alle
`streaming_handled_externally`-Zweige im Scheduler, Icecast-`killsource`,
Listener-Relais-Zugangsdaten, Stream-Output-Hot-Reload, der Icecast-
`listmounts`-Poller und `engine_kind` im Switcher, Engine-Auswahl in
`__main__` (`RASTATIME_PLAYOUT_ENGINE` nur noch `liquidsoap`, sonst
CRITICAL + Abbruch).  DJ-Kick jetzt per Harbor-Telnet
(`master_dj.stop`/`show_dj.stop`); Capture-Restart-Callback und
Webstream-Resume bewaffnen die Liquidsoap-Quellen statt URLs in die
Request-Queue zu schieben.  Details CHANGELOG „Legacy-mpv-Engine
gelöscht", ARCHITECTURE §23.28.  **Abweichung vom Plan:**
`ffmpeg_linein_capture.py` bleibt — es ist seit Option B (2026-09-03)
der aktive MME-Feeder-Pfad jedes geplanten Line-Ins, kein Legacy-Rest;
`_stable_id_to_dshow_audio` musste daher nicht umziehen.  ffmpeg.exe
bleibt damit als Feeder-Encoder in Betrieb.

**Ursprünglicher Plan (historisch):**

**Status (alt):** Go nach 1 Woche stabilem Live-Betrieb.
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

### ✅ Phase-E ICY-Metadata-Forwarding → Stream-Metadaten komplett (DONE 2026-09-13)

**Status:** Erledigt 2026-09-13 (Arbeitsreihenfolge Punkt 8, Operator-Go,
`b997a7a`).  Umfang gewachsen: nicht nur Webstream-Titel,
sondern Stream Label (drei Varianten), Off Air Metadata bei Stille,
Show-Name für DJ/Webstream/Line-In, Mount-Genre/URL.  Details CHANGELOG
„Stream-Metadaten" und ARCHITECTURE §23.29; Replikat-E2E acht Schritte grün.
**Live-Abnahme 2026-09-13/14 (nach dem Operator-Neustart aller Dienste):**
Datei-Show 13.09. 16:17–16:20: „C-60 - Mutters kleine Helfer" auf MP3/AAC
binnen 5 s nach dem Start, 2 s nach dem Ende wieder der Off-Air-Text.
Webstream-Show „Event Calendar" 14.09. 08:07–08:15: Show-Name ab
08:07:00 (der Cloud-Stream sendet keine eigenen ICY-Titel), Off-Air-Text ab
08:15:00.  OGG jeweils im Stream geprüft (Opus-Tags); die Icecast-Statusseite
zeigt für OGG-Mounts keinen Titel.  Rückwirkend nicht belegbar: das
Icecast-`access.log` protokolliert `/admin/metadata` ohne Titeltext.  Nach
dem außerplanmäßigen LIQUIDSOAP-Neustart 14.09. 03:51 hat PLAYOUT die Werte
neu gesetzt (siehe Item „Liquidsoap stirbt beim Wiederöffnen des
Tascam-Ausgangs nach Pufferleerlauf").
**Ursprünglicher Eintrag:**
**Status (alt):** Idea — nice-to-have, nicht eilig.
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

**Nachwelle (2026-09-18, Operator-Go Option A):**
- ✅ **DONE** Stream-Player-Widget v2 — das letzte Upstream-Widget
  (2015er jQuery-Player) im Wellen-Stil neu gebaut; Details im
  CHANGELOG „Changed" 2026-09-18.  Damit ist der öffentliche Bereich
  jQuery-frei und Punkt 12 der Arbeitsreihenfolge komplett.
- 💡 Falls der Stations-Podcast öffentlich geschaltet wird
  (displayRssTab): Radio-Page braucht einen seiteneigenen Podcast-
  Tab-Link — der alte In-Player-Knopf (iframe-Injektion) wurde mit
  dem v2-Player entfernt.

**Aufwand gesamt:** ~1700 LoC + ~400 LoC Doku (Wellen 1-3) + ~700 LoC
Player v2.

**Welle 4 — Ideen-Sammlung (2026-09-18, Operator-Frage „was haben
andere Stationen, das uns fehlt?").  Noch KEIN Go — Bestandsaufnahme
der Datenlage + Priorisierung.  ENTSCHIEDEN am 2026-09-18: nur W4.1
gebaut, alles Übrige vom Operator abgelehnt.**

- ✅ **W4.1 Cover-Artwork in den Widgets — DONE + abgenommen 2026-09-18** (Operator-Go;
  Nachschärfung: Player per gespeicherter Checkbox, Track History ohne Cover;
  Details im CHANGELOG „Added").  Player + Track History default AN, Now
  Playing opt-in per `?art=on` (height="50"-Einbettungen).  **Offen als
  Betriebs-Aufgabe, kein Code:** nur 13 von 64 Musiktiteln haben Artwork
  (202 der 216 Cover hängen an Jingles) — Cover werden erst breit
  sichtbar, wenn die Musikdateien Bilder bekommen.  Ursprüngliche
  Notiz: — der
  verbreitetste Baustein auf Sender-Seiten, bei uns überall Text-only.
  Datenlage GUT: 216 von 372 Dateien haben `cc_files.artwork`, der
  Endpoint `/api/track?id=N&return=artwork` existiert und wird vom
  Song-Request-Widget schon genutzt.  Betrifft Now-Playing-Track,
  Player v2 und Track-History-Zeilen; überall mit Platzhalter für die
  42 % ohne Bild.  Aufwand ~0,5-1 Tag.
- ❌ ABGELEHNT (Operator 2026-09-18): **W4.2 Podcast-/On-Demand-Widget** (`/embed/podcasts`) — Liste der
  letzten Episoden mit Abspiel-Knopf; bei Sendern mit Nachhör-Angebot
  Standard, bei uns gar nicht vorhanden.  Datenlage GUT: 5 Podcasts,
  95 Episoden, 1 Stations-Podcast.  Aufwand ~1-1,5 Tage.  Vorfrage an
  den Operator: nur Stations-Podcast oder auch importierte Feeds?
- ❌ ABGELEHNT (Operator 2026-09-18): **W4.3 „Zum Kalender hinzufügen" (.ics)** — pro Show-Slot eine
  Termindatei; kleine, praktische Ergänzung für On-Air-Today /
  Weekly / Multi-View.  Datenlage vorhanden (Schedule).  Aufwand
  ~0,5 Tag.
- ❌ ABGELEHNT (Operator 2026-09-18): **W4.4 Hörerzähler** (`/embed/listeners`) — „N Hörer gerade".
  Datenlage GUT: Icecast-status-json live + 39.072 Zeilen
  `cc_listener_count`.  ZWEISCHNEIDIG: bei kleinen Zahlen öffentlich
  eher kontraproduktiv; falls gebaut, per Default AUS und optional als
  Tages-/Wochen-Höchstwert statt Momentanwert.
- ❌ ABGELEHNT (Operator 2026-09-18): **W4.5 Meistgespielt-Charts** (`/embed/top-tracks`) — Klassiker
  („Top 10 der Woche").  Technisch machbar: `cc_playout_history`
  (2.617 Zeilen) gefiltert auf `cc_track_types.code='music'`.
  ABER dünn: nur 64 Musik-Dateien im Bestand, Spitzenreiter 22 Plays
  in 90 Tagen — die Liste zeigt faktisch die kleine Rotation.  Ohne
  Track-Type-Filter dominieren Jingles/Teaser (241 Jingle-Dateien).
  Erst sinnvoll, wenn die Musik-Bibliothek deutlich wächst.
- ❌ **W4.6 Show-/DJ-Profil-Widget — ABGELEHNT (Operator 2026-09-18);
  war ohnehin BLOCKIERT durch leere Metadaten.**
  Auf Sender-Seiten üblich (Sendungsbild, Beschreibung, Moderation,
  nächste Termine), bei uns NICHT baubar: von 489 Shows haben nur 29
  ein `image_path`, 2 eine `description` und 9 eine `url`.  Das Widget
  wäre zu ~99 % leer.  **Vorbedingung:** Sendungs-Metadaten pflegen
  (Operator-Aufgabe, kein Code) — lohnt sich unabhängig davon, weil
  Multi-View-Modal und On-Air-Today dieselben Felder anzeigen.
- ❌ ABGELEHNT (Operator 2026-09-18): **W4.7 Grüße/Widmung im Song-Request** — freier Nachrichtentext
  zusätzlich zum Titelwunsch.  Erweiterung des bestehenden Widgets,
  kein neues.  Braucht Moderations-/Missbrauchs-Überlegung, bevor
  öffentlich freitext-Eingaben ins Haus kommen.
- ❌ **Bewusst NICHT vorgeschlagen:** Live-Chat (Moderationslast),
  Sleep-Timer/Wecker (Nischenfunktion, Browser-untauglich),
  „Listen on TuneIn/Alexa"-Kacheln (bloße Links, kein Widget).

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

**Status: Kern ABGESCHLOSSEN 2026-09-17** (Bewährungs-Signal des Operators
für jq3 + FC6 nach drei ruhigen Monaten; Abschluss-Block: dataTransfer-Fix
+ 5b + FC1.5-Fork-Entfernung + UI-Politur, Commit-Hashes im CHANGELOG
„Removed"/„Fixed" 2026-09-17).  Verbleibend: DataTables 2.0 (eigene
Entscheidung später) + optionale Build-Pipeline.  Ursprünglicher Status:
In Arbeit — Strategie geklärt (Operator 2026-05-31: **Hybrid,
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
  - ✅ **Preview für „Scheduled Line-Input" — ehrliche Behandlung DONE
    2026-09-17 (Operator-Go; `c65d0ca`)** — der
    Player kennt Typ 2 jetzt: Zeile „[live input]" (gedimmt), nichts wird
    geladen, Auto-Weiter überspringt sie (vorher kaputter null-Eintrag,
    der die Kette stoppte).  💡 **Echtes Reinhören** in den Eingang wäre
    ein eigenes Feature: ein zweiter, on-demand Vorschau-Feeder auf dem
    MME-Gerät (Shared Mode), der WAV über HTTP an den Browser streamt —
    ~1-2 Tage, Fragen: Gerätekonkurrenz zum Sende-Feeder während einer
    laufenden Line-In-Show, Aufräumen nach dem Schließen des Popups.
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
    - ✅ **FC1.5-Fork entfernt (DONE 2026-09-17)** — Bewährungs-Signal des
      Operators; Fork, css/fullcalendar.css, ?fc6-Flag, FC1.5-Zweig und die
      fünf toten Callbacks raus (dayClick/windowResize/addQtipsToIcons
      bleiben — FC6 ruft sie).  Ursprünglicher Plan: (`js/fullcalendar/` inkl. Fork-
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
    - ✅ **ENTFÄLLT (2026-09-17): User-Manual-Screenshots** — das Kalender-
      Kapitel ist reiner Text, es gibt keine Screenshots zu aktualisieren.
      Ursprüngliche Notiz: (Schedule-Kapitel, alle 4 Sprachen)
      auf den FC6-Look aktualisieren — Bedienung unverändert, daher niedrige
      Prio; sinnvoll gebündelt mit der FC1.5-Fork-Entfernung.
  - ✅ **jQuery 1.8 → 3.7 KOMPLETT (5b DONE 2026-09-17)** — Migrate-Netz +
    Legacy-Assets + Flag-Logik entfernt (Details im CHANGELOG „Removed");
    vorher der dataTransfer-Fix in library.js ($.event.props ist in jQuery 3
    weg).  Historie: `?jq3=0` bleibt der Rollback (wie FC6). Resume-Details:
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
      3. ✅ **Buttons/ColReorder-CSS — OBSOLET (2026-09-17):** Buttons lädt
         nur auf Library, Showbuilder und Podcasts, und alle drei wurden im
         Juni gestylt; die übrigen Tabellen-Seiten laden die Extension gar
         nicht — es gibt nichts mehr anzugleichen.
      4. ✅ **Kosmetik-Politur DONE 2026-09-17** (Commit im CHANGELOG „Fixed"):
         Schließen-✕ für alle Dialoge (1.13 ließ den Knopf als nacktes
         <button> ohne Icon zurück), Datepicker dunkel (letzter Blau-Rest),
         `.ui-widget-content`-Rand entblaut.  Nicht reproduzierbar, geparkt
         bis zu einem Operator-Zeigefinger: „Scheduled-Tracks-Dialog zu
         hoch" + „Add/Edit-Show zu hell" (Notizen von vor dem dunklen
         Dialog-Theme vom 31.08.).  Ursprüngliche Liste: Scheduled-
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
  - 🟡 **DataTables 1.13 → 2.0** (eigener späterer Schritt nach jQuery 3):
    server-side-Format (sEcho/aaData → draw/data) + Init auf neue API umstellen.
    Modernitäts-Wette, nicht jQuery-3-blockierend.  **Evaluiert 2026-09-17:
    Defer** — DT 2 kappt die 1.9-Kompatibilität, auf der der gesamte Bestand
    fährt (Hungarian-Init inkl. der Juni-sDom-Kniffe von Library/Builder,
    Legacy-Server-Protokoll in Datatables.php + 4 weiteren PHP-Stellen);
    ~11 JS-Init-Stellen + 5 PHP-Dateien, Buttons 3/ColReorder 2, kein
    DT2-Pendant für die 2012er FixedColumns/FixedHeader-Forks, State-Format
    wandert erneut.  ~1,5-3 Wochen für null sichtbaren Betriebsnutzen;
    konkurriert strategisch mit der Grundsatzfrage Legacy-Frontend.
    **Wiedervorlage-Trigger:** (a) Sicherheitslücke/EOL der 1.x-Linie, die
    uns trifft; (b) konkretes DT2-only-Bedürfnis (Barrierefreiheit,
    Extension); (c) Entscheidung „Legacy-Frontend bleibt auf Jahre".
    Bis dahin 1.13 vendored + gepinnt.
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

### ✅ Show-Grenzen mit eigener Crossfade-Dauer (Operator-Wunsch 2026-09-10) — GEBAUT 2026-09-27

**Status:** ✅ Umgesetzt 2026-09-27 (Operator-Go; Antworten auf die vier
offenen Fragen: (1) alte Sendung blendet aus, neuer Titel sofort voll; (2)
innerhalb der Sendung ein echter Crossfade, 8-s-Regel entfällt — Ersatz ist
das Titel-Attribut „No Fade during Crossover" (Überlapp bleibt, der markierte Titel blendet nicht); (3) ja, der Show-Wert steuert
auch Line-In/Webstream-Wechsel, gleicher Stream in beiden Sendungen bleibt
nahtlos; (4) Startwert 1 s).  Abweichung von der Skizze: nicht
`liq_cross_duration`/`liq_fade_out` je Titel — in Liquidsoap 2.4 setzt der
Override am NEUEN Titel dessen Kopf-Puffer, nicht den Schwanz des alten
(Bench 2026-09-27) —, sondern eine eigene Übergangsfunktion mit
`rt_cross`-Variable und fester Pufferlänge; Titel werden vorab in die Queue
gelegt (Queue-Ahead).  Details CHANGELOG 27.09.  Ursprüngliche Skizze
darunter zur Historie.

**Ursprünglicher Status (2026-09-10):** 💡 Idee, evaluiert 2026-09-10,
Operator: „kein Go, merken wir uns für später".  Ersetzt als Richtung die
Per-Track-Idee (kurze Titel ohne Fade) aus dem Mai.
**Wunsch:** Der heutige Crossfade (Überlapp aus Settings → General „Default
Crossfade Duration", derzeit 1,0 s, keine Ein-/Ausblendung) funktioniert gut,
gilt aber für alle Übergänge.  An Show-Grenzen (Show-Start/-Ende) sollen
andere Werte gelten als innerhalb einer Show; einstellbar ebenfalls unter
Settings → General.
**Skizze (Evaluierung 2026-09-10):**
- Neues Feld „Show Crossfade Duration" neben dem bestehenden; `cc_pref`-
  Schlüssel, kein Schema-Umbau.
- Scheduler kennt die Show-Instanz je Titel (`FileEvent.instance_id` aus
  `schedule.instance`); beim Push bekommt der letzte Titel einer Show die
  Metadaten `liq_cross_duration` + `liq_fade_out` mit dem Show-Wert, alle
  übrigen den Standardwert (Liquidsoaps `cross` liest beide Schlüssel pro
  Titel; `liq_fade_in` optional für den ersten Titel der Folgeshow).
- Werte je Refresh-Zyklus aus `cc_pref` lesen → Änderungen wirken ab dem
  nächsten Titel ohne Neustart; nur der Gate-Fade für Line-In/Webstream
  bleibt im gerenderten Skript (Neustart der Audio-Kette wie heute).
- Show-Ende in Stille / Show-Start aus Stille bleiben harte Schnitte
  (kein Partner-Titel), separat lösbar (`fade.skip`).
**Aufwand:** ~5–6 h inkl. Replikat-Nachweis, Tests, Handbuch ×4.
**Vor einem Go zu klären:** (1) Form des Show-Übergangs: alte Show blendet
über N s aus und der neue Titel startet sofort voll (Vorschlag, weil Shows
oft mit Jingle/ID beginnen) oder echtes Crossfade mit Einblenden; (2) bleibt
es innerhalb der Show beim heutigen Überlapp ohne Fades, und entfällt die
30-s-Regel für kurze Titel; (3) steuert der Show-Wert auch den Gate-Fade
bei Line-In/Webstream-Showwechseln; (4) Startwert des neuen Feldes (1,0 s
= heutiger Standard).

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

### ✅ REST `PUT /rest/media/<id>` mit unbekannter ID: 500 statt 404 (Nebenbefund 2026-09-10, DONE gleichen Tags)

**Status:** Behoben 2026-09-10 (`7993bfe`): Null-Guard im `catch`
von `CcFiles::updateFromArray`, Ausnahme mit ID im Text; live geprüft, PUT und
DELETE auf eine unbekannte ID antworten jetzt 404.  **Befund (Original):** beim CSRF-Live-Beweis (`PUT
/rest/media/999999999`) antwortet das REST-Modul mit einer HTML-500-Seite:
`CcFiles::updateFromArray()` ruft `setDbImportStatus()` auf `null` auf
(`findPk` findet nichts); das ist ein PHP-`Error`, den das `catch (Exception)`
in `MediaController::putAction` nicht fängt (legacy.log 2026-09-10 18:55:42).
**Fix (~5 Zeilen):** in `updateFromArray` bei `!$file` eine
`LibreTimeFileNotFoundException` werfen (bestehender 404-Pfad) und/oder in
`putAction` `Throwable` fangen.

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

### ✅ Statische Asset-Cache-Buster: Clients kleben an alten CSS/JS (DONE 2026-08-31, `0767393`)

**Status:** Behoben (Operator-Go am selben Tag — das Problem biss
allein heute dreimal).  `Assets::url()` leitet den `?<hash>` jetzt
aus **mtime+Größe der echten Datei** ab (12-Hex-md5, per Request
memoisiert) statt aus der build-zeitlichen `assets.json`: jede
Änderung ergibt sofort eine neue URL, Unverändertes bleibt stabil
gecacht.  Fehlende Dateien behalten das Upstream-Verhalten
(Error-Log + time()).  `tools/assets-checksum-update.py` +
`application/assets.json` sind damit obsolet (liegen gelassen,
nichts referenziert sie).  Live bewiesen: Hash stabil über Requests,
ändert sich bei touch, /schedule lädt ohne Asset-Fehler.  Kein
Strg+F5 mehr nötig — ein normaler Reload genügt ab jetzt.
**Ursprünglicher Eintrag:**
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

### ✅ CSRF-Token rotiert bei jedem Fehlversuch (DONE 2026-09-10 — die Rotation war wirkungslos)

**Status:** Erledigt 2026-09-10 (Arbeitsreihenfolge Punkt 3, Operator-Go „kleine
Form").  **Korrigierte Diagnose:** die Rotation in `Acl_plugin.php` hat nie
gewirkt — `PageLayoutInitPlugin::_initCsrfNamespace()` schließt die Session in
`routeShutdown` schreibend (`session_write_close()`), der `preDispatch`-Hook
schrieb den neuen Token nur in den Speicher des abgebrochenen Requests.  Live
bewiesen (eingeloggte Brave-Sitzung, `PUT /rest/media/999999999`): zwei falsche
Tokens → 401, echter Token danach → Request erreicht den Controller.  Ein
Fehlschlag kostete also immer nur den einen Request; die „Vergiftung" war ein
Trugschluss aus dem Code-Lesen.  **Gemacht:** tote Rotation entfernt, 401-
Warnung mit Methode/Pfad/Origin/Sec-Fetch-Site/Token-Status;
`SecurityHelper::verifyCSRFToken` mit `hash_equals` und ohne `null == null`-
Durchwinken; `PluploadController::uploadAction` auf dieselbe Prüfung.  Details
CHANGELOG „CSRF-Prüfung gehärtet".  Nicht gemacht (Option B, Operator-
Entscheid): das 5-Minuten-Timeout der Zend-Hash-Formulare (Login, Add User,
Add Track Type) bleibt.

**Ursprüngliche Annahme (2026-06-05, überholt):**
**Status (alt):** Defer — kein Bug, aber raue UX (notiert 2026-06-05 beim Upload-Fix).
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

### ✅ Lokales Monitoring / Main-Output-Setting (DONE 2026-09-03, `6464b17`)

**Status:** ERLEDIGT — Reihenfolge-Punkt 1.  Das Main-Output-Setting
wirkt jetzt tatsächlich: `engine/portaudio_output.py` löst den
Windows-Endpunkt zu einem PortAudio-Index auf (probiert die Host-APIs
durch, WASAPI → MME → DirectSound → WDM-KS, Hardware-Token-Matching für
die anders benannte WDM-KS-Variante) und rendert ihn als `device_id=`
in die `.liq`.  Kein Kandidat öffnbar → OS-Default + lauter Log-Eintrag.
Anwenden per bewusstem, bestätigtem Knopf „Jetzt anwenden"
(`preference/restart-audio-chain`: PLAYOUT zuerst, dann LIQUIDSOAP) —
bewusst NICHT automatisch beim Speichern (Stream-Abriss ohne Vorwarnung)
und bewusst NICHT an der Django-API (bindet `0.0.0.0` ohne Auth).
**Live verifiziert:** Jabra → PortAudio-Index 4 (MME), `device_id=4` in
der gerenderten `.liq`, `liquidsoap --check` grün, 14 neue Tests,
keine Regression (37 Fehler auch auf Baseline).
**Tascam-Wunsch erfüllt — mit einer Vorbedingung (2026-09-03 13:30):**
Der US-16x08-Ausgang lehnte jede Host-API ab, solange sein Windows-
Mix-Format auf 48 kHz stand (WASAPI shared verlangt exakt die Mix-Rate,
Liquidsoap läuft auf 44,1).  Nach Umstellung auf **44,1 kHz** öffnet
WASAPI blockierend und Liquidsoap treibt den Tascam als Sendeausgang;
Line-In-Aufnahme am selben Interface läuft parallel.  Details im
Eintrag „Tascam als Sende-/Monitor-Ausgang" weiter unten.
**Teures Learning (Sendeausfall 2026-09-03):** Die erste Probe testete
im Callback-Modus, meldete WDM-KS als tauglich → Liquidsoap starb beim
Geräte-Öffnen und riss die Icecast-Ausgänge mit.  `liquidsoap --check`
fängt das NICHT (nur Typprüfung, öffnet nie ein Gerät).  Regel daraus:
**Geräte-Features immer mit einem echten Liquidsoap-Lauf verifizieren**,
und eine Probe muss dieselbe API-Betriebsart nutzen wie der Konsument.
Offen bleibt damit: ein Monitor-Ausgang am Tascam wäre nur über einen
anderen Weg erreichbar (z. B. Hardware-Routing im Tascam-Panel:
„Computer 1/2 → Line-Out", also ohne Windows-Beteiligung).

**(Ursprünglicher Eintrag zur Historie:)**
**Status (alt):** Defer — Operator-Wunsch 2026-09-01 („am liebsten
Tascam-Ausgänge als Output"); Interim: Windows-Default-Ausgabe =
Jabra (entspricht dem konfigurierten Main-Output-Setting).
**Hintergrund (Messung 2026-09-01):** Der Tascam-WDM-Treiber ist
faktisch **Single-Direction**: Hält ein Client den Render-Pfad
(Liquidsoaps `output.portaudio` auf dem Windows-Default), scheitert
JEDER WDM/MME-Capture-Open (INVALPARAM/BADFORMAT) — und ein
Capture-Versuch gegen laufenden Render riss umgekehrt den Output um
(der Monitor-Ausfall vom 2026-08-31, „host error 6").  Vollduplex
kann das Gerät nur über ASIO (für uns No-Go).
**KOEXISTENZ-PROBE GEFAHREN (2026-09-03) — „Vollduplex nur über ASIO"
ist WIDERLEGT.**  Messmatrix (Tascam-Output + gleichzeitig
MME-16ch-Capture, Skripte `coexist_probe.py` / `crosstalk_scaling.py`):

| Output-Host-API | Ergebnis |
|---|---|
| WASAPI | ❌ Open scheitert (`Invalid device`, −9996) |
| MME | ❌ Open scheitert (`Unanticipated host error`, −9999) |
| DirectSound | ❌ Start scheitert (−9999) |
| **WDM-KS** | ✅ **Output + Capture gleichzeitig, echte ADC-Daten** |

Zusatzbefund **Übersprechen Ausgang→Eingang**: real und
pegel-skalierend nachgewiesen (Ton −20 → −8 dBFS, Anstieg auf den
unbeschalteten Kanälen +9…+13 dB = 1:1-Skalierung).  Stärkster Kanal
**Ch9: Isolation ~45 dB** unter Ausgangspegel; andere Kanäle 55–65 dB.
**Schleifenverstärkung 45 dB unter Eins → KEINE Rückkopplungsgefahr**,
aber ein leiser Programm-„Geist" kann in einem Line-In mitlaufen.
Getriebene Eingänge (echte Quelle dran) sind besser als der
gemessene Worst Case an offenen Buchsen.
**Messfalle dokumentiert:** Eine erste Bleed-Messung an Ch3/4 zeigte
scheinbar +23 dB Übersprechen — das war das laufende Programmsignal,
nicht der Ton.  Übersprechen NUR auf unbeschalteten Kanälen messen
und immer über Pegel-Skalierung verifizieren, nie aus einem
Einzelvergleich schließen.
**Konsequenz für die Implementierung:** Der Device-Resolver darf sich
NICHT auf eine Host-API festlegen — er muss Kandidaten durchprobieren,
bis ein Open gelingt (für den Tascam-Ausgang ist das WDM-KS, für
Jabra/Realtek vermutlich WASAPI/MME).  Hinweis: WDM-KS ist ein
kernel-naher, exklusiver Pfad — währenddessen können andere
Windows-Apps den Tascam-Ausgang nicht mitbenutzen (auf einer
dedizierten Sendemaschine unkritisch).

**Zwei Bausteine für die Rückkehr:**
1. ~~**WASAPI-Koexistenz-Probe**~~ — erledigt 2026-09-03, siehe oben;
   WASAPI-Output geht gar nicht, WDM-KS ist der Weg.
2. **`output.portaudio` ans Main-Output-Setting binden:** Liquidsoap
   nimmt heute stur das Windows-Default-Gerät und ignoriert
   `main_output_id` aus Settings → Local Machine (Lücke).  Renderer
   um eine Device-Auswahl erweitern (PortAudio-Device-Match per
   Name), damit Monitoring-Ziel explizit konfiguriert ist statt
   Default-abhängig.
**Betriebswissen (2026-09-01):** Nach Fehlopen-Serien kann der
Tascam-WDM-Stack verklemmen (alle Opens INVALPARAM) und ein
PnP-Restart bei belegtem Gerät hinterlässt Geister-Endpoints —
Heilung: Gerät freigeben (ggf. LIQUIDSOAP kurz stoppen) + **USB
kurz ab-/anstecken**.  Studio-Wechsel am selben Interface
(Back-to-Back-Shows, anderes Paar) kostet ~14 s Übergang
(Mount-Neuaufbau + input.http-Puffer).
**Zweiter Klemm-Modus (Nachmittag 2026-09-01):** Nach dem
Feeder-Crash-Zyklus von 12:15 (3× Open+Sofort-Tod durch den
NameError) fiel der Capture-Pfad in einen **Dither-Zombie-Modus**:
Opens gelingen, aber es kommen keine ADC-Daten mehr — Fingerabdruck:
alle 16 Kanäle uniform −96,7 dBFS Floor, Mount konstant
−91,0/−84,3 dB, während das Tascam-Panel real anliegendes Signal
zeigt (Kanal 3 bestätigt).  Heilung auch hier nur USB-Re-Plug (um
11:02 nachweislich wirksam — Scan 11:04 sah Signal).  Falls die
Verklemmer chronisch werden: **Tascam-Treiber-Update prüfen**
(nachhaltige Kur; eigenes Wartungsfenster, da Treiberwechsel).
**ROOT CAUSE GEFUNDEN (2026-09-02): Windows „Voice Clarity"-APO —
das Tascam war nie defekt.**  Beweisführung:
1. Fremdrechner-Test (Operator): US-16x08 liefert an einem zweiten
   Windows-Rechner via Audacity/MME einwandfrei Signal → Gerät ok.
2. Jabra-Mikrofon auf der Studio-Maschine zeigt via MME denselben
   Fingerabdruck: ~1 s reales Signal, dann Abfall auf exakt
   −90,3/−96,7 dBFS Dauer-Floor (KI-Filter „konvergiert").
3. Kontrollexperiment gleiche Sekunde, gleiches Gerät: WDM-KS
   (treiber-direkt, ohne APO-Kette) liefert dauerhaft Raumsignal;
   MME (Engine + Effekte) unterdrückt nach 1 Block alles → einziger
   Unterschied ist die Effektkette der Windows-Audio-Engine.
Täter: APO-Paket „Voice Clarity" (PnP „VocaEffectPack",
`SWD\DRIVERENUM\{96BEDF2C-18CB-4A15-B821-5E95ED0FEA61}#VOCAEFFECTPACK
&1&1E3C765A&0`, Klasse AudioProcessingObject, Provider Microsoft,
1.0.4.7057, installiert 2026-08-25), per FxProperties an ALLE
Capture-Endpoints geheftet (TEAC-, Class- und Jabra-Endpoint).
KI-Sprachfreistellung klassifiziert Line-Signal (Musik/Ton = „keine
Stimme") als Störgeräusch → Rest = Dither-Teppich.  Das erklärt
rückwirkend ALLE „Zombie"-Phänomene: die „Heilungen" nach Re-Plug
waren nur frische Konvergenz-Fenster (Kurz-Scans erwischten die
erste Sekunde), die Treiber-Odyssee jagte einen Geist.
**Fix:** Voice-Clarity-APO-Gerät im Geräte-Manager deaktivieren
(global, admin, reversibel via Enable-PnpDevice) und/oder pro
Endpoint Einstellungen → System → Sound → Eingabe →
Audioverbesserungen = Aus.  Auf einer Sende-Maschine hat KEIN
Capture-Endpoint KI-Filter zu tragen.  **Betriebs-Lore:** Nach
großen Windows-Updates prüfen, ob der Effekt reaktiviert/neu
angeheftet wurde (Kurztest: MME-Scan eines Line-Signals > 5 s —
bleibt der Pegel, ist alles gut).

**ABNAHME BESTANDEN + Rauschteppich-Ursache = Erdschleife
(2026-09-02).**  Nach dem Deaktivieren von Voice Clarity lief die
Kanalwahl mehrfach sauber on air (Kaltstart-Show 12:36, Feeder ab
+1,5 s, Mount ≡ öffentlicher Stream).  Operator hörte im Webstream
aber einen Rauschteppich.  Systematische Lokalisierung (alle
Messungen mit `analyze_clean.py`/`raw_floor.py`/`spectrum.py` im
Scratchpad, floor(p5) + HF-Proxy + Goertzel-Sweep):
- Feeder-Code ist transparent (`extract_frames` sortiert nur
  int16-Lanes, kein Float/Dither/Gain); ffmpeg-Cmd ohne Gain/Filter.
- **Stille-Messung ADC-direkt vs. Feeder-Ausgang: auf 0,3 dB
  identisch** (rms −58, HF −69,8) → die Software fügt NULL hinzu.
- Spektrum bei Stille: Brummen bei **100/200/300 Hz je −30 dBFS**
  (gerade Vielfache von 50 Hz dominant = Vollweg-Gleichrichter-
  Fingerabdruck), Höhen 3–10 kHz nur −57…−62 dB → kein Hiss.
- **Beweistest Kabel getrennt:** Eingang unbeschaltet fällt der Floor
  auf −84 dBFS, die 100-Hz-Linie auf −100 dB (70 dB weg).  Das
  Brummen kommt also über die Signalleitung → **Erdschleife**
  (Schirm → Tascam → USB → PC → Netz).
**RASTATIME ist vollständig freigesprochen** — Rauschteppich ist
externe Studio-Verkabelung.  **Fix (Operator-Seite, Priorität):**
(1) Mantelstromfilter/Trennübertrager in die Ch-3/4-Leitung, (2)
symmetrisch (XLR/TRS) verbinden, (3) DI-Box mit Ground-Lift, (4)
gemeinsame Steckdosenleiste.  USB-Isolator NICHT nötig (Schleife
läuft übers Audiokabel).  **Betriebs-Lore:** Kanal 3/4 sind
Mic/Line-Combo-Eingänge; unsymmetrische Quellen brauchen galvanische
Trennung.  Software-Abnahme der Kanalwahl = bestanden.
Rest-Housekeeping: die Line-In-Rows tragen noch die alte, vor der
Treiber-Odyssee gespeicherte `device_id`; der Name-Fallback greift
bei jedem Start (Warnung im Log).  Beim nächsten Settings-Besuch die
Sources einmal neu speichern, dann matcht die aktuelle Endpoint-ID.

**FINAL ABGESCHLOSSEN (2026-09-02 abends).**  Housekeeping erledigt:
die 4 Tascam-Rows per API-PATCH von `eb8ab9e3-…` auf die aktuelle
`15982059-3662-4bfb-ab8c-ecb06ad66f71` gesetzt (Mappings erhalten);
seither startet der Feeder ohne Name-Fallback-Warnung (Log der
19:06-Show bestätigt).  **Erdschleife-Gegenprobe live bestanden:**
Operator schloss eine Signalquelle OHNE eigenes Netzteil an (kein
zweiter Erdungspfad) — Stille-Messung auf dem Stream: 100 Hz von
−30 auf **−90 dBFS** (59 dB weg), 200/300 Hz −72/−75, Floor Ch3
−72 dBFS.  Operator bestätigt per Ohr: „Das Brummen ist weg."  Damit
Kanalwahl-Feature **vollständig abgenommen** (Software + Live-Hörtest).
**Klarstellung „zwei Feeder-Prozesse":** kein Bug — der venv-Python
`…\.venv\Scripts\python.exe` ist ein Launcher-Stub, der den
Basis-Python (`C:\Program Files\Python313\python.exe`) als Kind
startet; nur EINER öffnet das MME-Gerät.  Beim Show-Ende werden beide
sauber beendet (Feeder-Count 0 verifiziert).  Restpegel-Hinweis:
Ch4 rauscht ~12 dB mehr als Ch3 (kanalspezifisch, auch bei
getrenntem Eingang so — unkritisch, Nutzsignal lag auf Ch3).

### ✅ Tascam als Sende-/Monitor-Ausgang ohne PortAudio-Blocking (evaluiert 2026-09-03, erledigt 2026-09-03 über Option B)

**Status:** ✅ **ERLEDIGT über Option B (2026-09-03, 13:30)** — Ursache
war das Windows-Mix-Format des Render-Endpunkts (48 kHz/24 bit).
Operator stellte es auf **44,1 kHz** um → WASAPI öffnet blockierend,
Resolver löst `Tascam-Lautsprecher [WASAPI] idx 18` auf, Produktions-
Rendering läuft stabil, hörbarer Testton läuft, **Koexistenz bewiesen**
(Liquidsoap→Tascam + Line-In-Feeder MME-16ch-Capture vom selben Gerät +
ffplay parallel).  Kein Reboot nötig; Option A (unten) bleibt als
dokumentierter Notfallplan, wird NICHT gebaut.  **Ohr-Abnahme nach dem
Reboot (2026-09-03 ~14:10, Operator):** Tascam als aktives Geraet
angezeigt, Test-Show ueber den Tascam-Ausgang kristallklar.  **Betriebs-Lore:** Das
Endpunkt-Format muss 44,1 kHz bleiben (Liquidsoap-Framerate); springt es
(Treiber-Neuinstallation!) auf 48 kHz zurück, fällt der Ausgang auf
OS-Default, der Resolver loggt den Hinweis, der „Aktiv"-Anzeiger zeigt
die Abweichung.  Check-Skript: `C:/Temp/rastatime-postreboot-check.py`.
**(Evaluierung vor der Lösung, zur Historie:)**
**Ausgangslage (gemessen 2026-09-03):** Der Tascam-US-16x08-Ausgang
lässt sich über KEINEN Weg durch die Windows-Audio-Engine öffnen —
PortAudio (MME/DirectSound/WASAPI, blocking + callback, int16/float32,
44,1 + 48 kHz, 2 + 8 Kanäle), libao/wmm (`waveOutOpen FAILED`), und
sogar SDL/ffplay als „normale App" (`WASAPI can't initialize audio
client`).  Registry: aktiver Render-Endpunkt `{97af73f9…}` state=1,
Mix-Format 48000/24bit/stereo, FxProperties LEER.  Vermutlich
Windows-seitig defekter Render-Endpunkt (Operator hörte schon am
2026-09-01 nichts, als der Tascam Windows-Default war) → nach dem
geplanten Reboot 5-Minuten-Recheck.  **Nur WDM-KS (kernel streaming,
exklusiv, NUR Callback-Modus) funktioniert.**  Liquidsoaps
`output.portaudio` nutzt die blockierende API → am Tascam unbrauchbar;
auch bei `settings.frame.audio.samplerate := 48000` („Invalid device").
**Prototyp bewiesen — `output.external` + eigener Output-Feeder
(sounddevice, WDM-KS, Callback; Spiegelbild des linein_feeder):**
- Audio fließt in Echtzeit (455 323 Frames / 10,3 s @ 44,1 kHz).
- Mit 300 ms Vorpuffer + blocksize 2048: 8 Startup-Underruns, danach
  **konstant 0** über 15 s.
- **Feeder abgeschossen:** Liquidsoap überlebt, `output.file`
  (Icecast-Stellvertreter) läuft weiter, Feeder wird per
  `reopen_on_error` automatisch neu gestartet (Supervision liegt in
  Liquidsoap, kein Python-Watchdog nötig).
- **Feeder hängt (liest stdin nicht mehr):** UNGESCHÜTZT steht der
  Icecast-Stellvertreter (0 B in 8 s) — die Pipe blockiert die Clock.
  MIT `buffer(buffer=2.0)` + `clock.assign_new(sync="cpu")` (dasselbe
  Muster wie der PortAudio-Block) läuft er ungestört weiter.  →
  **Isolation ist Pflicht.**
**Optionen:** (A) output.external-Feeder wie oben, ~150 LoC Feeder +
~60 Renderer + ~40 Resolver (Callback-Probe für den Feeder-Pfad,
Blocking-Probe für portaudio — Probe-Modus MUSS zum Konsumenten
passen, Lehre aus dem Ausfall) + Tests + Doku ×4; ~6–8 h, ~1–1,5 Tage
mit Live-Fenster.  Exklusives KS ist für einen Sendeweg ein Vorteil
(bit-transparent, kein Windows-Mixer, keine Fremd-App kann
einspeisen).  Latenz ≈ Vorpuffer + buffer() (heute 2 s am Monitor-
Block; für Sendeweg auf ~0,5 s tunen).  (B) Engine-Pfad heilt nach
Reboot → evtl. plain output.portaudio via MME/DS wie beim Jabra;
unsicher, 5-min-Check nach Reboot.  (C) PortAudio/Liquidsoap neu bauen
→ No-Go (Zuverlässigkeit vor Modernität).
**Mess-Skripte:** Scratchpad `out_feeder*.py`, `ext*.liq`, `hang*.liq`.

### ✅ Boot-Race: LIQUIDSOAP startet parallel zu PLAYOUT und liest die alte .liq (erledigt 2026-09-07, abgehakt 2026-09-09)

**Erledigt (Operator-Bestätigung 2026-09-09):** der Boot-Fenster-Neustart
vom 2026-09-07 (`__main__`: ändert das Rendern die .liq in den ersten
zehn Minuten nach dem Boot, startet PLAYOUT RASTATIME-LIQUIDSOAP selbst
neu; bei Index-Adressierung des Main Output übersprungen) ist der hier
empfohlene „Boot-Fenster-Schutz".

**Status:** Defer — Design-Entscheidung nötig (gefunden 2026-09-03 beim
Tascam-Sendeausgang).  Kein akuter Blocker: der „Jetzt anwenden"-Knopf
löst es jederzeit auf, und der „Aktiv"-Anzeiger macht es sichtbar.
**Befund:** RASTATIME-PLAYOUT und RASTATIME-LIQUIDSOAP sind beide
StartMode=Auto, DelayedAutoStart=False, ohne Dienst-Abhängigkeit.
PLAYOUT rendert rastatime.liq erst Sekunden nach seinem Start (Django,
DB, API); Liquidsoap liest die Datei sofort beim Start → nach einem
Reboot läuft Liquidsoap mit dem VORHERIGEN Skript.  Jede Änderung, die
ein Re-Rendern braucht (Main Output, Stream-Outputs, Harbor, Hourly
Recording), wird durch einen Reboot also NICHT angewendet; PLAYOUT
loggt nur „RESTART the RASTATIME-LIQUIDSOAP NSSM service".
**Optionen (Trade-offs, vor Umsetzung mit Operator klären):**
1. NSSM: LIQUIDSOAP mit DelayedAutoStart oder Abhängigkeit von PLAYOUT
   — billig, aber nur ein Zeitpolster; die Render-Dauer ist nicht
   garantiert (DB-Start).  Kein echtes Handshake.
2. PLAYOUT startet LIQUIDSOAP selbst neu, wenn der Render-Inhalt sich
   beim Start geändert hat (`changed=True`) — deterministisch; Nachteil:
   ein automatischer Liquidsoap-Neustart ist genau die Aktion, die wir
   beim Speichern bewusst NICHT automatisch auslösen (Stream-Abriss).
   Beim Boot ist noch nichts on air → vertretbar, aber es braucht eine
   Schutzlogik (nur innerhalb der ersten Minute nach Boot, nie im
   laufenden Betrieb).
3. Liquidsoap wartet beim Start auf ein „Render fertig"-Signal (Datei-
   Marker/Health-Gate wie bei WORKER/PLAYOUT gegen die API) — sauberste
   Lösung, mehr Aufwand (NSSM-Wrapper-Skript).
**Empfehlung:** Option 2 mit Boot-Fenster-Schutz, ~2–3 h; vorher Go.
**Bis dahin (Betriebsregel):** Nach jedem Reboot Settings → Local Machine
→ „Aktiv"-Zeile prüfen; bei Abweichung einmal „Jetzt anwenden".

**Nachtrag 2026-09-05 (Beweis nach dem Reboot 11:15):** Instanz #1
startete 11:15:15 mit der .liq vom Vorabend (`device_id=18`), PLAYOUT
renderte 11:15:18 neu (`device_id=14`), Instanz #1 starb 11:15:22 an
„Blocking API not supported" (18 war inzwischen ein WDM-KS-Gerät),
NSSM startete Instanz #2 um 11:15:27 — die nun Index 14 = Realtek
öffnete (Endpoints erschienen zwischen Probe und Öffnen; siehe
„PortAudio-Geräteindex instabil").  Ohne den zufälligen Re-Render
wäre es eine Neustart-Schleife gewesen.  Die Empfehlung (Option 2 mit
Boot-Fenster-Schutz) steht; sie muss zusammen mit dem `device_name`-
Eintrag umgesetzt werden, sonst bleibt der Index-Drift.
**Umgesetzt 2026-09-05 (`1dbeb71`):** Option 2 — PLAYOUT ruft
`nssm restart RASTATIME-LIQUIDSOAP` selbst, wenn sein Render die .liq
innerhalb von 10 min nach dem Hochfahren geändert hat
(`liquidsoap_service.py`, `RASTATIME_LIQUIDSOAP_BOOT_RESTART=0`
schaltet ab).  Status damit 🟢.
**Nachtrag 2026-09-06 (`578e950`):** Das Gegenstück — PLAYOUT vor
LIQUIDSOAP — ließ den einmaligen `recording.stop`/Gate-Reset ins
Leere laufen (Sentinel-Datei wuchs).  Jetzt wiederholt der Scheduler
beides bis zu 90 s, bis Telnet antwortet; gilt auch nach dem Boot-
Fenster- und dem nächtlichen Neustart.

### 💡 Line-In: Kanalwahl auch im Library-Schnell-Editor (Option A)

**Status:** Idea — Operator-Entscheid 2026-09-01: „vorerst Option B,
eventuell später Option A".
**Kontext:** Es gibt zwei Line-In-Editoren: (1) den vollen Editor
unter Settings → Local Machine → Line-In Sources (seit `1f60295`;
inkl. Kanal-Picker, Priorität, Verwaltungstabelle) und (2) den
schlanken Library-Seiten-Editor (`linein/linein.phtml`, Name/Gerät/
Standardlänge/Beschreibung).  Option B (umgesetzt): der
Library-Editor zeigt einen Hinweis-Link auf den vollen Editor; neue
Einträge dort starten mit Kanälen 1/2 (`saveAction` lässt
`channel_mapping` bei PATCH unangetastet, defaultet bei POST).
**Option A (bei Umsetzung):** Kanal-Picker (wie in linein.js
`populateChannelSelect`) auch in `linein/linein.phtml` + `saveAction`
um `channel_mapping` erweitern.  ~1–2 h.
**Mitzunehmen:** LINE_IN.md trägt Alt-Drift aus der Frühzeit — §2/§5/
§6 referenzieren eine Seite „Settings → Line-In Library", die es
nicht (mehr) gibt (real: Library-Hauptmenü „Line Inputs" + Settings →
Local Machine); LOCAL_MACHINE.md §3 beschreibt eine
Input-Device-Checkbox-Liste, die die Seite nicht hat.  Bei
Option-A-Umsetzung das Kapitel in einem Zug sanieren (4 Sprachen).

### ✅ Latent: `HistoryService::getSqlTypes()` mappt DATETIME auf ungültigen PG-Cast (DONE 2026-09-10)

**Status:** Behoben 2026-09-10 (Arbeitsreihenfolge Punkt 4, `cdc8f0b`): Cast-String `timestamp`; Typnamen der ganzen Tabelle gegen die
Datenbank geprüft (`date`, `time`, `timestamp`, `text`, `boolean`, `integer`,
`float` gültig, `datetime` nicht).
**Ursprünglicher Befund:** Idea/Latent — heute harmlos, Fund der 2026-08-30er
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

### ✅ Liquidsoap Latency-Catchup unter System-Last verliert Recording-Audio (Phase-D) — CLOSED 2026-09-16

**Geschlossen 2026-09-16 (Arbeitsreihenfolge Punkt 9, Bedingung vom
09.09. erfüllt):** Catchups pro Tag aus allen Liquidsoap-Logs seit dem
01.09.: 02.–05.09. 100.000–162.000 (die `sync="cpu"`-Uhr, behoben 05.09.),
06.09. 6, 08.09. 10, 10.09. 4, 11./12.09. je 2, seit 13.09. keine.  Die
24/7-Aufnahme vom 16.09. (erster voller Tag nach dem Storage-Umbau) hat
Stundendateien von 3599,9–3600,1 s (11, 13, 14, 15 Uhr); die durch
Einstellungs-Neustarts geteilten Stunden 12 und 16 summieren sich auf
3599,2 bzw. 3599,0 s (≈ 1 s Neustart-Lücke, kein Catchup-Verlust).  Die
Ursache von Mai/Juni (7 min Verlust bei 96 Catchups/h) war die alte
Hardware plus die Uhr-Konfiguration; beides ist weg.  Wieder öffnen,
wenn eine Stundendatei ohne Neustart unter 3595 s fällt.

**Beobachtung bis 2026-09-15 (Operator-Go 2026-09-09):** die Catchups
(„We must catchup") liefen am 2026-09-04 81.222-mal, am 2026-09-08
fünfmal, am 2026-09-09 gar nicht — der Auslöser ist mit den Änderungen
vom 05.09. weg.  Bleibt es bis 15.09. dabei, wird der Punkt geschlossen.
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

### ✅ Per-Track Crossfade-Entscheidung basierend auf Track-Länge — ERSETZT 2026-09-27

**Status:** ✅ Erledigt 2026-09-27 durch das Titel-Attribut „Exclude from
Crossover" (Edit Metadata; Operator-Entscheid: kein Längen-Schwellwert,
sondern eine Markierung je Titel).  Der markierte Titel spielt vollständig,
Nachbarzeilen ohne Crossfade-Versatz.  Historie darunter.

**Ursprünglicher Status:** Defer — Phase-D-Polish.
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

### ✅ Frontend-Settings "Default Fade In / Out / Crossfade Duration" wieder funktional machen — ERLEDIGT 2026-09-27

**Status:** ✅ Erledigt 2026-09-27: „Default Track Crossfade Duration" und
„Default Show Crossfade Duration" wirken (cc_pref primär, env-Fallback,
Einstellungs-Neustart per Fingerprint); die wirkungslosen Fade-In/Out-Felder
sind ausgeblendet statt reanimiert (Operator-Entscheid).  Historie darunter.

**Ursprünglicher Status:** Defer — Operator-Wunsch 2026-05-28, kein akuter Blocker.
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

**Teil-Erledigung 2026-09-04:** Punkt 1 (Crossfade-Setting als
primäre Quelle, Env-Var als Fallback) ist mit Paket 2 umgesetzt
(`eabf798`).  Offen bleiben Punkt 2 (Re-Render-Hook beim Speichern —
heute: „Jetzt anwenden" in Local Machine) und Punkt 3 (Fade-In/Out).

**Aufwand:** ~3-4 h für Crossfade-Setting + Re-Render-Hook;
~1-2 h für Fade-In/Out.

**Vorbedingung:** Frontend-Setting muss Operator-Permission haben
(Admin only — UI ist da, nur Backend-Wiring fehlt).

---

### 💡 Speicherzuwachs der Liquidsoap-Hauptinstanz eingrenzen (≈ 8 MB/h im Leerlauf, festgestellt 2026-09-15)

**Status:** Idee / Untersuchung, kein Handlungsdruck — der geplante Neustart
greift bei 1536 MB im 04:00-Fenster, beim heutigen Zuwachs etwa alle 6 Tage.
**Vorbedingung:** Operator-Go; sinnvoll erst, wenn das Neustart-Intervall über
etwa 6 Tage steigen soll.

**Befund (Speicherwoche, Instanz seit 2026-09-14 10:43):** 103 MB nach dem
Start, 155 MB nach 5,1 h, 301 MB nach 21,3 h, 333 MB nach 24,4 h.  Über Nacht
(2026-09-14 15:50 bis 2026-09-15 08:00: ein Webstream-Slot, keine Titel, keine
DJs, keine Telnet-Verbindungen) +146 MB in 16,2 h, also ≈ 8,5 MB/h im
Leerlauf; dazu ≈ 7–12 MB je Webstream-Slot.  Gemessene Basis am 2026-09-10:
≈ 5 MB/h.  Das Wachstum kommt vermutlich in Stufen (OCaml-Heap), kurze
Messfenster streuen stark.

**Ausgeschlossen:** die Main-Output-Brücke (Replikat 2,8 h auf dem
Realtek-Ausgang: `buffer`, `buffer.adaptative` und `buffer.adaptative(
resample=false)` jeweils flach, die adaptiven Varianten einmalig +38 MB) und
das Telnet-Leck (keine Verbindungen über Nacht).

**Kandidaten:** der Harbor-Accept-Loop (Unix.select-Leck des Windows-Builds),
der `bus.on_frame`-Rückruf des Webstream-Wächters (50 Aufrufe/s), der
ICY-Block (`metadata.map` auf dem Bus), Heap-Wachstum ohne Leck.

**Vorgehen, falls gewünscht:** Replikat mit dem Produktionsskript (Test-Mounts,
eigener Telnet-Port), Blöcke einzeln abschalten, Speicher alle 10 min messen;
`C:/Temp/optd/bridge_mem_compare.py` als Vorlage.
**Umgesetzt 2026-09-15 (Operator-Go „günstige Mitte", `ac20f02`):** der Preflight-Scan loggt alle 15 min den Speicher der
Hauptinstanz mit Zuwachs und Rate seit der ersten Messung (`grep "Liquidsoap
memory" logs/playout-stdout.log`).  Die Ursachensuche selbst bleibt Idee.

### ✅ Liquidsoap stirbt beim Wiederöffnen des Tascam-Ausgangs nach Pufferleerlauf (festgestellt 2026-09-14, DONE 2026-09-14)

**Status:** Erledigt 2026-09-14 (Operator-Go Variante B, `9b0aa3e`):
`output.portaudio(fallible=false, …, mksafe(…))`, Brücke `buffer.adaptative`
mit höchstens 0,1 % Tempoanpassung, abschaltbar per
`RASTATIME_LIQUIDSOAP_LOCAL_OUTPUT_ADAPTIVE=false`.  Aktiv seit 2026-09-14 10:43 (Operator-Neustart PLAYOUT und LIQUIDSOAP,
Tascam-Session bestätigt).  Beobachten: nach dem Start kein
`[portaudio_safe:3] Switch to safe_blank.` und kein `Buffer emptied` mehr,
keine Main-Output-Warnung.  3-h-Dauertest beider Brücken auf dem
Realtek-Ausgang (Stille, `C:/Temp/optd/bridge_probe.py soak`): kein Leerlauf,
kein Stopp; dort ist die Drift klein und läuft in die Gegenrichtung (der
Puffer wächst um ≈ 0,2 s in 3 h), `estimated()` blieb konstant bei 2,002 s —
die Driftkorrektur selbst ist damit nicht belegt.  **Nachweis in Produktion
2026-09-15 08:00:** 21 h nach der Aktivierung kein Leerlauf (nur die
Umschaltung beim Start), kein Neustart, keine Gerätefehler, keine
Main-Output-Warnung.  Bisher lief der Puffer spätestens 12 h nach dem Start
leer (gemessen 5–12 h) — die Driftkorrektur wirkt
(`C:/Temp/optd/bridge_night_check.py`).  Nicht durch die
Stream-Metadaten verursacht: das Muster besteht seit 2026-09-07.

**Befund:** Läuft der 2-s-Puffer vor `output.portaudio` leer
(`[buffer.producer] Buffer emptied`, `portaudio_clock` wechselt in den
„non self-sync mode"), stoppt der Ausgang (`fallible=true`) und öffnet das
Gerät beim Wiederanlaufen neu.  PortAudio kennt nur die Geräteliste vom
Prozessstart.  Hat Windows seitdem einen Endpunkt entfernt (vermutlich wie
bei der Nacht-Neustart-Schleife 2026-09-06/07 der Display-Audio-Endpunkt
beim Display-Schlaf), zeigt der per Name aufgelöste Index ins Leere:
`Unanticipated host error 2 in open_device: A device ID has been used that
is out of range for your system` → `Invalid_argument("option is None")` im
Clock-Thread → Prozessende mit Exit-Code 2 → NSSM startet nach 5 s neu.

| Leerlauf | Wiederöffnen | Folge |
|---|---|---|
| 2026-09-07 21:44:12 | Geräte-ID ungültig | Neustart 21:44:20 |
| 2026-09-08 20:22:44 | Geräte-ID ungültig | Neustart 20:22:52 |
| 2026-09-09 16:36:39 | Geräte-ID ungültig | Neustart 16:36:47 |
| 2026-09-10 03:06:42 | ok | — |
| 2026-09-10 21:38:11 | ohne Fehler, falsches Gerät | Main-Output-Warnung bis 12.09. 04:14 |
| 2026-09-12 15:43:06 | ok | — |
| 2026-09-14 03:51:21 | Geräte-ID ungültig | Neustart 03:51:29 |

**Auswirkung 2026-09-14 03:51 (nichts geplant):** die drei Icecast-Mounts
~6 s ohne Quelle (die Standby-Mounts waren verbunden), Tascam ~10 s stumm.
PLAYOUT hat den Neustart erkannt und `recording.stop`, die Gates und die
Stream-Metadaten neu gesetzt; Preflight danach ohne Warnung.  Während einer
Sendung wäre das ein hörbarer Aussetzer, und laut Code setzt PLAYOUT den
laufenden Datei-Titel danach nicht fort (Wiederaufnahme mit Sprung gibt es
nur nach einem DJ-Ende); der Rest fehlt bis zum nächsten Titel-Timer.

**Stiller Fall, belegt:** Nach dem Reboot am 10.09. startete Liquidsoap um
13:28:15 mit einer kurzen Geräteliste (Tascam = PortAudio 3 [MME]).  Beim
Wiederöffnen um 21:38:11 zeigte der veraltete Index auf ein anderes Gerät:
kein Fehler, aber die Preflight-Prüfung meldete ab 21:43 im Dashboard
(Schwere error) „Liquidsoap plays its Main Output to …, not to
'Tascam-Lautsprecher (US-16x08)'" bis zum Nacht-Neustart am 12.09. 04:01 —
rund 30 h ohne Liquidsoap-Ton am Tascam.

**Evaluierung 2026-09-14:**
- *Ursache der Leerläufe:* Drift zwischen Tascam-Takt und Haupt-Uhr.  Der
  2-s-Puffer ist nach 10–12 h leer (≈ 50 ppm); das ergibt etwa zweimal am
  Tag eine Lücke von ~2 s am Tascam, auch ohne Absturz.
- *Listenwechsel:* Tagsüber rendert PLAYOUT den Tascam als PortAudio 7 [MME]
  (Display-Audio des DELL-Monitors vorhanden), nachts als 6, direkt nach dem
  Reboot am 10.09. als 3.  Alle vier Abstürze: Start mit langer Liste,
  Leerlauf bei ausgeschaltetem Bildschirm (Kernel-Power 566, Abschaltung
  nach 15 min).
- *Laufzeitversuche* (`C:/Temp/optd/probe_p1..p4.liq`, Realtek-Gerät, Stille,
  Erzeuger 4 s abgeschaltet): die heutige Form stoppt den Ausgang und startet
  ihn neu (= Wiederöffnen).  Mit `mksafe` und `fallible=false` läuft der
  Ausgang durch, ohne Neustart, und bleibt self-sync.
  `buffer.adaptative(limit=1.001)` läuft auf dem Windows-Build zusammen mit
  `clock.assign_new`, Füllstand stabil bei ~2,0 s.  Ohne `mksafe` lehnt
  Liquidsoap `fallible=false` beim Start ab („That source is fallible");
  `--check` erkennt das nicht.
- *Optionen:* (A) `mksafe` + `fallible=false`: kein Wiederöffnen mehr, die
  Lücke von ~2 s alle ~12 h bleibt.  (B) A + `buffer.adaptative` mit enger
  Geschwindigkeitsgrenze (0,1 %), per Umgebungsvariable abschaltbar: auch
  keine Lücken mehr; die Funktion ist in 2.4.4 als experimentell markiert.
  (C) Display-Audio des DELL-Monitors in Windows deaktivieren (Operator):
  weniger Listenwechsel, deckt Reboot und USB-Geräte nicht ab.  (D) Eine
  Einstellung für nicht tödliche Streaming-Fehler gibt es in 2.4.4 nicht.
  (E) Externer Feeder statt PortAudio: zu groß für das Problem.
- *Empfehlung:* Go für B (enthält A); C optional.  Aufwand ~3–4 h plus
  Beobachtung über mindestens einen Tag; Aktivierung per PLAYOUT- und
  LIQUIDSOAP-Neustart.  Vor `RASTATIME_LIQUIDSOAP_RESTART_EVERY_DAYS=7`
  umsetzen, weil längere Laufzeiten mehr Leerläufe bedeuten.

**Belege:** `logs/liquidsoap.log` (grep `Buffer emptied|out of range|LOG START`),
`logs/liquidsoap-stderr.log` (`Fatal error: exception Invalid_argument`),
Windows-Anwendungsprotokoll, Quelle `nssm`, Ereignisse 1013/1014 (Exit-Code 2,
Aktion Restart).  PLAYOUT selbst lief durch; Item 11 (NSSM-Resilience)
betrifft PLAYOUT und ist davon nicht berührt.

### ✅ Pypo-NSSM-Service-Resilience untersuchen (Phase-D-Beobachtung) — CLOSED 2026-09-16

**Geschlossen 2026-09-16 (Arbeitsreihenfolge Punkt 11, Bedingung vom
09.09. erfüllt):** `playout-stdout.log` seit dem 09.09.: 20 Zeilen
„RASTATIME-PLAYOUT: running" gegen 20 „shutdown requested", jede
„running"-Zeile folgt auf einen angeforderten Shutdown (alle Neustarts
waren Operator-Neustarts nach Commits); über das ganze Log 55 gegen 54
(die Differenz ist der erste Start des Logs).  `playout-stderr.log` enthält
nur die fünf `NameError`-Tracebacks der Entwicklung vom 10.09. (behoben
in `fec9df9`), nichts Neues.  Die Untersuchungsschritte unten bleiben als
Rezept, falls PLAYOUT je wieder ungeplant fehlt.

**Beobachtung bis 2026-09-15 (Operator-Go 2026-09-09):** im gesamten
`playout-stdout.log` stehen 39 Starts gegen 38 angeforderte Shutdowns,
also höchstens ein ungeplanter Neustart seit Mai und keiner in den
letzten Wochen (die letzten fünf Starts waren Operator-Neustarts am
08./09.09.).  Passiert bis 15.09. nichts, wird der Punkt geschlossen.
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

### ✅ Host-Hardware-Instabilität (STUDIO-Maschine, nicht RASTATIME-Code) — obsolet seit dem Maschinenwechsel 2026-08

**Abgehakt 2026-09-09 (Operator-Bestätigung):** betraf die alte
Maschine; seit der Migration auf den neuen Studio-Rechner (2026-08,
192.168.1.164) nicht mehr aufgetreten.

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
