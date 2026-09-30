# Changelog

All notable changes to RASTATIME are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **„No Fade during Crossover" als Track-Typ-Vorgabe (2026-09-30,
  Operator-Go)** — Die Operator-Frage nach einer Checkbox „Exclude from
  Crossover" am Track-Typ war ein No-Go: dieses Preset gibt es bereits als
  Crossfade Duration = 0 (Scheduler und Playout liefern für beides den
  Seitenwert 0).  Die zweite Ausnahme fehlte auf Typ-Ebene: Settings →
  Track Types → Checkbox „No Fade during Crossover" (Tooltip;
  `cc_track_types.no_fade_crossfade`, Migration 0063 angewendet,
  Schema 63).  Titel mit Crossover „As the track type" erben die Vorgabe:
  sie behalten ihren vollen Pegel, während der Nachbar blendet, die
  Überlappung bleibt wie die Crossfade-Dauer des Typs.  Das Titel-Feld
  gewinnt („No Fade" erzwingt, „Exclude" hat keine Überlappung); aufgelöst
  wird einmal im Playout (`schedule._effective_no_fade`) aus Datei plus dem
  neuen Read-only-Feld `track_type_no_fade` des File-Serializers.  Kein
  Neu-Layout — die Überlappung ändert sich nicht — nur ein Schedule-Push
  (`Tracktype::save()` meldet, welche der beiden Vorgaben sich änderte).
  Track-Editor-Tooltip nennt die Vererbung; Texte DE/FR/ES; Playout-Test
  (Vererbung, Vorrang, Exclude, alte API ohne Feld), 32/32 grün, Django
  check + Serializer geprüft; Formular live verifiziert (Checkbox,
  Hidden-Fallback, Tooltip, Daten-Endpoint).  Handbuch SETTINGS + LIBRARY
  ×4, Architektur §23.44 Addendum (0.53).  Inbetriebnahme: API- und
  PLAYOUT-Neustart (Serializer-Feld, Auflösung), Apache-Neustart für die
  Übersetzungen; danach die Vorgabe am gewünschten Typ setzen — `1fe5a44`.

- **Webstream default length follows into the upcoming shows (2026-09-30,
  follow-up to the cue-point package)** - the operator set the BBC relay from
  302 to 305 s so the hourly show is filled; the rows copy the length at
  insertion, so 238 upcoming instances kept 302/303 s.
  `Application_Model_CuePoints::applyWebstreamLengthToFutureRows()` copies the
  length into the not-started rows (`clip_length`, `cue_out`) and the
  instances are laid out again; `Application_Model_Webstream::save()` calls it
  for an existing webstream.  One-off tool `C:/Temp/optd/ws_length_apply.php
  <stream id> [--apply]` (dry run in a rolled-back transaction, reports rows
  past the show end and the gap to the show end) - applied for the already
  saved value: 238 instances, gap to the show end 3.9 s -> 0.9 s, no row past
  the show end.  Manual WEBSTREAMS x4 - `e833192`.

- **Cue points: re-detect from the library, follow into the upcoming shows,
  capped at the file length (2026-09-30, operator Go after the evaluation)** -
  with jingles laid out without an overlap every silent tail is a pause; all
  24 TOH jingles end 1.05-1.25 s before their cue out, and the track editor
  accepted a cue out past the file length (6.90 s on a 5.97 s file - the 1.9 s
  of silence before the BBC relay in the 2026-09-30 test show).  New
  `Application_Model_CuePoints`: `detect()` runs ffmpeg silencedetect with the
  analyzer's parameters (-60 dB, 0.3 s; FFMPEG_PATH, else C:/ffmpeg/bin),
  `clamp()` keeps cue in / out inside the file, `applyToFutureRows()` copies a
  file's cue points into the rows of the upcoming shows (not started, instance
  not modified) and `relayoutInstances()` lays those instances out again
  (calculateCrossfades reads clip_length) and pushes the schedule.  The track
  editor clamps and propagates on every cue change
  (`StoredFile::setDbColMetadata`), the library toolbar gets **Cue Points**
  (selected tracks, files over 15 min skipped; `library/redetect-cue-points`,
  JSON summary).  Translations DE/FR/ES, manual LIBRARY x4, dry run
  `C:/Temp/optd/cue_dryrun.php` (unit checks, detection on sample files, apply
  + relayout in a rolled-back transaction) - `7d34b09`.

- **Crossfade je Track-Typ und „Exclude from Crossover" (2026-09-29,
  Operator-Go)** — Auslöser: die stündliche Jingle-Folge lief dem Kalender
  5 s voraus und ließ vor dem BBC-Relais Stille (Zeilen Stoß an Stoß, Track-
  Crossfade 3 s).  Die Überlappung wird jetzt je ÜBERGANG bestimmt:
  `cc_track_types.crossfade_duration` (Settings → Track Types → „Crossfade
  Duration (s)", leer = Hauswert; der Typ Jingles beginnt mit 0) und
  `cc_files.exclude_crossfade` (Migration 0062).  Paar-Regel: zwischen zwei
  Titeln der KLEINERE Wert, 0 bei „Exclude"; an einem Wechsel Titel ↔
  Webstream/Line-In der kleinere aus Titel-Wert und Show-Crossfade (das
  Layout nutzte dort bisher den Track-Wert, der Playout blendete mit dem
  Show-Wert); nie mehr als der Crossfade-Puffer.  Titel-Editor: ein
  Dreiwege-Feld „Crossover" (As the track type / No Fade during Crossover /
  Exclude from Crossover) ersetzt die Checkbox — die beiden Ausnahmen
  schließen einander aus.  Kalender: `calculateCrossfades()` legt je
  Zeilenpaar aus, speichert mit Mikrosekunden (die Propel-Setter kürzten auf
  ganze Sekunden), läuft nach jedem Insert/Move/Remove und lässt Zeilen in
  Ruhe, die schon gestartet sind (`removeGaps()` ebenso);
  `relayoutFutureInstances()` legt kommende Sendungen neu aus — automatisch
  bei Änderung eines Track-Typs, eines Titel-Modus (Exclude) oder der
  Hauswerte.  Playout: `_pair_crossfade()` nach derselben Regel, der Modus
  trägt die Überlappung als drittes Feld (`track/-/0.00`), die Engine setzt
  `rt_dur`; Liquidsoap liest die Überlappung je Übergang (0 = Titel spielt
  aus, Nachfolger folgt; −1 = Hauswert).  Bench: bei 0 startet der
  Nachfolger exakt am Ende des Vorgängers ohne Lücke und ohne Pegeleinbruch,
  bei 1 s / 3 s entsprechend früher.  Daten: die 100 „No Fade"-Jingles auf
  „wie Track-Typ" zurückgesetzt (Liste gesichert), 639 kommende Instanzen
  neu ausgelegt (390 von 951 Zeilen, Sekundenbruchteile).  Tests (Paar-Regel,
  Modus, Engine, Render), Trockenlauf-Werkzeuge `xf_layout_dryrun.php` /
  `xf_relayout.php`, Handbuch LIBRARY + SETTINGS ×4, Architektur §23.44.
  Inbetriebnahme: API- und PLAYOUT-Neustart, Apache-Neustart für die
  Übersetzungen — `b28bc98` (Kern), `f36de90` (Kalender, UI).

- **Primärfarbe der Oberfläche als Einstellung (2026-09-29, Operator-Wunsch,
  Operator-Go Option A)** — Settings → General → „Primary Color": Hex-Feld
  mit Farbwähler und „Reset to default", stationsweit (`cc_pref`
  `ui_accent_color`, leer = Standard `#ff5d1a`).  Das bisher fest codierte
  Orange (~90 Stellen: `#ff5d1a`, `#ff6f01`, `#ff611f` und ein Dutzend
  Abstufungen) ist jetzt eine CSS-Variablen-Palette:
  `Application_Model_AccentColor` leitet Akzent, rgb-Tripel, zwei helle und
  zwei dunkle Abstufungen sowie zwei Textfarben für Flächen in der
  Akzentfarbe ab (weiß bzw. schwarz bevorzugt, kippt nur bei zu hellen bzw.
  zu dunklen Farben — das Standard-Orange sieht aus wie bisher) und gibt sie
  in allen sechs Layouts sowie im Player- und Wochenprogramm-Widget als
  `<style id="rt-accent">` aus; `styles.css` hält die Standardpalette als
  Rückfall.  Umgestellt: Links/Hover, Menü-Markierung, Seitennummern,
  Scrollbalken, Speicher- und Fortschrittsbalken, ausgewählte Zeilen,
  Kontextmenü, Checkboxen, Fokus-Rahmen, Upload-Überschrift, Datepicker,
  Radio-Seite, Vorschau-/Stream-Player, Player-Widget, Waveform-Zeitleiste;
  einfarbige Bilder (Abschnittspfeile, orange Icon-Hover) als CSS-Masken.
  Bleiben: Signal-/Kategoriefarben, mehrfarbige Icons (Operator-Entscheid),
  Installer, die eigenen Akzente der Widgets Now Playing/Wochenprogramm und
  Song Request.  Texte DE/FR/ES (`.mo` neu, wirksam nach Apache-Neustart),
  Handbuch SETTINGS ×4, Architektur §23.43.  Live verifiziert mit
  Standard- und simulierter Palette — `4ef9cfd`.

- **Loudness-Normalisierung nach EBU R128, Stufe 1 (2026-09-28,
  Operator-Go)** — Settings → Streams: „Loudness Normalization" als
  Dreiwege-Modus Off / ReplayGain / EBU R128 (ersetzt die Checkbox „Enable
  Replay Gain"; ein Altbestand leitet den Modus aus dem bisherigen Schalter
  ab), dazu „Target Loudness" (frei, Vorgabe −23 LUFS) und „True Peak
  Ceiling" (Vorgabe −1 dBTP), Beschreibungen als Tooltips, Felder je Modus
  ein-/ausgeblendet.  Analyzer: neuer Schritt `analyze_loudness` misst mit
  ffmpegs `ebur128`-Filter integrierte Lautheit, True Peak und Loudness
  Range (`cc_files.loudness_lufs` / `true_peak_dbtp` / `loudness_range_lu`,
  Migration 0061, Raw-SQL im Legacy-REST, Django-Feld für die API); die
  bisherige ReplayGain-1.0-Messung bleibt für den ReplayGain-Modus.
  Bestand: „Measure missing files now" / „Re-measure all" stellen die
  Bibliothek per RabbitMQ (`options.loudness_only`) dem Analyzer ein, der
  die Datei an Ort und Stelle misst und nur die drei Spalten zurückschreibt
  (keine Bewegung, kein Import-Status); Stand „Measured: N of M files".
  Playout: `file_gain_db()` — R128 = Ziel − Lautheit, gekappt, damit der
  True Peak die Grenze nicht überschreitet; ungemessene Titel bis zur
  Messung mit ReplayGain-Wert um (Ziel + 18) verschoben; API
  `/stream/preferences` liefert `loudness_mode` / `loudness_target_lufs` /
  `loudness_true_peak_dbtp`.  Liquidsoap: im R128-Modus `limit()` (Ratio
  20, 5 ms Attack) hinter dem Titel-Gain als Peak-Sicherung, Grenze als
  `interactive.float("loudness_ceiling")`; Modus und Grenze im
  Settings-Fingerprint (geplanter Neustart).  Bench auf dem Windows-Build
  (`xbench/bench_r128.liq`).  Tests (Analyzer-Parser + echte Messung, API,
  Playout-Gain-Matrix, Render), Handbuch STREAMS ×4, Architektur §23.41.
  Inbetriebnahme: ANALYZER-, API- und PLAYOUT-Neustart, dann Modus wählen
  und „Measure missing files now" — `b258e44`.

- **Live Text Info: die „Now playing"-Zeile als Textdatei (2026-09-28,
  Operator-Go)** — Neuer Bereich Settings → General → „Live Text Info"
  (oberhalb TuneIn): Hauptschalter, eigenes Live-Text-Format (dieselben drei
  Varianten wie das Stream Label, unabhängig davon), Web-Veröffentlichung
  unter `/live/now-playing.txt` (statische Datei im Public-Ordner, ohne Login,
  unabhängig vom Public-API-Schalter), optionale lokale Datei, FTP-Push bei
  jeder Änderung (FTP / FTPS per `ftplib`, SFTP per curl mit libssh2; eigene
  Zugangsdaten, Passwort bleibt in cc_pref).  Damit DJ-Titel und
  Webstream-Titel enthalten sind, bildet Liquidsoap die Zeile selbst: das
  ICY-Label ist zu `label_for(fmt, m)` verallgemeinert, `livetext_report`
  hängt per `bus.on_metadata` vor dem ICY-Rewrite und POSTet die Zeile an den
  Playout-Listener `/live-text`; `LiveTextWriter` dedupliziert, schreibt
  atomar (tmp + replace) und lädt auf einem Worker-Thread hoch.  Schalter
  und Format werden bei Änderung per Telnet in die laufende Instanz gesetzt
  (`livetext_enabled` / `livetext_format`), ein Save wirkt ohne Neustart.
  Handbuch SETTINGS ×4, Tests (Konfiguration, Schreiben, Dedup, FTP-Push und
  Fehler, SFTP-Voraussetzung, Render, Listener, Scheduler-Sync).
  Live-Prüfung (Web-Abruf, FTP-Upload) nach dem PLAYOUT-Neustart — `d70f2db`.
  Nachbesserung: der Schreiber muss `start_listener()` übergeben werden — die
  vorab gesetzte Handler-Eigenschaft wurde vom Listener-Start mit dem
  Standardwert überschrieben, `/live-text` antwortete 503 und keine Datei
  entstand (erster Live-Versuch 14:35); Regressionstest — `716f28f`.

- **TuneIn „Now playing" aus dem Playout (2026-09-28, Operator-Go Option 2)** —
  Die Einstellungen unter Settings → TuneIn waren nur halb verdrahtet: der
  Legacy-Notify meldete Datei-Starts, das Keep-alive aus dem alten
  Pypo-Fetcher lief nicht mehr (TuneIn löscht die Anzeige nach fünf Minuten),
  Webstreams und Line-Ins wurden nie gemeldet, und ein nicht erreichbares
  TuneIn warf mitten im Notify eine Exception.  Neues Modul
  `libretime_playout/tunein.py` (`TuneInPusher`): Titel + Interpret bei jedem
  Titelstart, Sendungsname bei Webstream- und Line-In-Start, Keep-alive im
  Schedule-Refresh (alle ~2 min, sendet erneut nach 240 s), Einstellungen vor
  jedem Push frisch aus cc_pref (Save wirkt ohne Neustart), HTTP auf einem
  Daemon-Thread mit 10-s-Timeout, XML-Antwort geprüft, Partner-Key nie im
  Log.  Legacy-Push und `update-metadata-on-tunein` stillgelegt,
  `common/TuneIn.php` entfernt; Hinweistext auf der Settings-Seite
  (EN/DE/FR/ES), Handbuch SETTINGS ×4.  Tests: Push, deaktiviert/unvollständig,
  Ablehnung/Netzfehler ohne Key im Log, Keep-alive-Intervall, Scheduler-Hooks.
  Live-Verifikation gegen TuneIn steht aus, bis die Zugangsdaten vorliegen — `4417320`.

- **Settings → Streams „Switch Transition Fade" wirkt jetzt: DJ-Übergabe mit
  Fade (2026-09-28, Operator-Go Option 2, Startwert 1 s)** — Das
  LibreTime-Feld (`cc_pref default_transition_fade`) hatte in RASTATIME
  keine Wirkung: der Playout legte damit nur ein `switch_off`-Ereignis an,
  das der Scheduler nie behandelt, der RabbitMQ-Pfad `update_transition_fade`
  läuft nicht mehr, und beide DJ-Arme im Bus-Switch waren fest 50 ms.  Jetzt
  eigene Form `bus_dj` für Master- und Show-Arm: der DJ ist sofort auf
  Sendung, das Programm blendet über den Wert darunter aus; die Programm-Arme
  (Webstream, Line-In, Scheduled) nutzen dieselbe Form, wenn die abgehende
  Quelle ein DJ ist (`source.id(old)`), d. h. beim Auflegen blendet der DJ
  über den Wert aus und das Programm kommt sofort voll.  Wert kommt aus
  cc_pref (Fallback `RASTATIME_LIQUIDSOAP_DJ_FADE_SECONDS`), ist Teil des
  Einstellungs-Fingerprints; `transition_length` deckt den längeren der
  beiden Fades.  Getter-Default und DB-Wert auf 1 s gesetzt, Beschreibung am
  Feld (EN/DE/FR/ES), Handbuch STREAMS §3 ×4 — `7a93633`.

- **Show-Grenzen-Crossfade + „Exclude from Crossover" (2026-09-27,
  Operator-Go, Arbeitsreihenfolge Punkt 2, `07e6e1f`)** — Zwei Crossfade-Werte unter
  Settings → General: **Default Track Crossfade Duration** (bisher „Default
  Crossfade Duration", `default_crossfade_duration`) ist jetzt ein echter
  Crossfade zwischen zwei Titeln derselben Sendung (alter Titel blendet aus,
  während der neue einblendet); **Default Show Crossfade Duration** (neu,
  `default_show_crossfade_duration`, Startwert 1 s) gilt an Sendungsgrenzen
  — die alte Sendung blendet über diesen Wert aus, der erste Titel der neuen
  Sendung startet sofort voll — und prägt jeden Eingangswechsel (Titel ↔
  Webstream ↔ Line-In, gleiche Form).  Gleicher Webstream / Line-In in
  beiden Sendungen bleibt nahtlos (unverändert).  Neues Titel-Attribut
  **Exclude from Crossover** (Edit Metadata, `cc_files.exclude_crossfade`,
  Migration 0059): ein markierter Titel wird nie ein- oder ausgeblendet,
  spielt bis zum Ende, der Nachbar folgt ohne Überlappung; der PHP-Scheduler
  legt Nachbarzeilen ohne Crossfade-Versatz an (`calculateCrossfades`,
  `removeGaps2`, verknüpfte Sendungen).  Technik: `cross()` um die
  Request-Queue (Stille-Arm bleibt außen) mit Übergangsfunktion, die die
  Form aus der interaktiven Variable `rt_cross` liest (track / show / cut,
  `_skip`-Varianten bei Overbook, instant); PLAYOUT legt den nächsten
  Datei-Titel `BUFFER + 1,5 s` vor Zeilenstart in die Queue („Queue-Ahead",
  `enqueue` / `adopt_queued`) und skippt nur bei Overbook.  Bench mit vier
  Testtönen (L/R getrennt, Hüllkurve je 100 ms) für alle Formen; gerenderte
  Skripte per `liquidsoap --check`.  Handbuch SETTINGS / LIBRARY / LINE_IN
  / WEBSTREAMS in EN/DE/FR/ES.  Wirksam nach PLAYOUT-Neustart (Render +
  Einstellungs-Fingerprint enthält beide Werte).
  **Live abgenommen 2026-09-27 in der vierten Probe (22:45–23:04, Track
  3 s / Show 1 s, zwei Test-Sendungen mit Overbook und Jingle-Ausnahme):**
  Titelwechsel in der Sendung als 3-s-Crossfade am wahren Titelende
  (`track`, Queue-Ahead 8–11 s vorher, Übergabe ohne Skip), Sendungsgrenze
  mit Ausblenden des alten Titels über die letzte Sekunde und pünktlichem
  Start der neuen Sendung (`show`, Playout erkannte „already on the queued
  track" und skippte nicht), Jingle ohne Überlappung vollständig gespielt
  (`cut` auf beiden Seiten), Ende in Stille ohne Fade.  Proben 1–3 hatten
  jeweils einen Fehler aufgedeckt (siehe Fixed).  Werkzeug
  `C:/Temp/optd/crossfade_rehearsal.py setup|status|cleanup`.

- **Show-Shift: Filler statt Kürzung (2026-09-27, Operator-Go mit
  Design-Entscheiden D1–D4, `b7d2890`)** — Neue Einstellung Settings → General →
  „Show-Shift Filler Playlist" (Picker wie Traffic-Alert, Preference
  `show_shift_filler_playlist_id`, 0 = aus).  Im SHIFT-Fall des
  `ShowShiftService` ersetzt `fillShiftedTail()` das bisherige Abschneiden
  von Bs letztem Titel: (D1) Endet B mit seiner Outro-Playlist
  (sendungseigenes „Select Outro Playlist" oder Stations-Standard), bleibt
  das Outro ans Slot-Ende gepinnt — geprüft als Suffix-Abgleich der
  Playlist-Titel, nie angenommen — und ersetzt wird davor; (D3) alle
  Schluss-Titel, die nicht mehr passen, fliegen raus; (D2) die Lücke wird
  per 0/1-Knapsack mit minimalem Überschuss aus der Filler-Playlist
  gefüllt, der letzte Filler wird gekürzt — nie Stille, nie ein
  Sendungs-Titel gekürzt, auch bei Lücken kürzer als der kürzeste Filler;
  (D4) nur B, As eigene Kürzung am Anker bleibt.  Läuft in der
  Shift-Transaktion (alles oder nichts), pflegt position/time_filled/
  is_scheduled, loggt Zusammenfassung.  Reine Funktionen `pickFillers` +
  `matchOutroSuffix` per PHP-CLI gegengerechnet (exakte Treffer, minimaler
  Überschuss, Kürzeste-Filler-Fall, Shortfall mit Wiederholung, Suffix-
  Fälle).  Settings-Seite live verifiziert (Picker nach Traffic-Alert, 24
  Optionen, keine PHP-Fehler).  Handbuch DELAYED_START §2 + §3
  EN/DE/FR/ES, Labels de/fr/es übersetzt.  **Live-Probe mit Testshows
  (deckt auch den nie ausgelösten Basis-Shift ab) steht aus — Operator-
  Termin.**  Nebenbefund: Kein `msgfmt` auf dem neuen Studio-Rechner
  (C:\Tools\gettext-iconv fehlt) → `frontend/legacy/scripts/po2mo.py` als
  eigenständiger .po→.mo-Compiler (gegen die drei getrackten Kataloge
  gegengerechnet: 989/946/946 Einträge, byte-für-Wert identisch).
  Übersetzungen greifen nach Apache-Neustart (gettext-Cache je Prozess).

- **Cover-Artwork in den Widgets (2026-09-18, Operator-Go W4.1, `fb17949`)** — Drei
  Widgets zeigen jetzt das Cover des Titels: Stream Player (beide
  Layouts), Track-History-Zeilen und Now Playing — Track.  Neuer
  Parameter `?art=on|off`; Default AN bei Player und Track History, AUS
  bei Now Playing — dieses Widget ist mit `height="50"` dokumentiert, ein
  Cover hätte jede bestehende Einbettung verändert (mit `?art=on` wächst
  es auf ~48 px).  Beide Payloads führen jetzt `fileId` + `hasArtwork`;
  ein `<img>` entsteht NUR bei vorhandenem Cover — der Artwork-Endpoint
  beantwortet einen Titel ohne Bild mit 0-Byte-200, was ein `<img>` ewig
  hängen ließe (weder load noch error).  Track-History-Zeilen ohne Cover
  behalten einen leeren Platzhalter (Spalten bleiben bündig), Webstream-
  und Line-In-Zeilen haben systembedingt nie eines.  Bilder kommen vom
  gleichen Endpunkt wie beim Song-Request-Widget (64 px für Zeilen/Bar,
  128 px für die Player-Karte, `loading=lazy`) und hängen damit am
  Public-API-Schalter: ist er aus, bleiben die Widgets funktionsfähig,
  nur ohne Bilder.  Handbuch WIDGETS EN/DE/FR/ES.  **Datenlage-Hinweis
  für den Betrieb:** von 216 Dateien mit Cover sind 202 Jingles und nur
  13 von 64 Musiktiteln haben eines — sichtbar werden Cover also erst,
  wenn die Musikdateien Artwork bekommen.

- **Podcast-Episoden landen in einem Ordner pro Podcast (2026-09-17,
  Operator-Go, `b4d3b0a`)** — Downloads schrieben flach nach `imported/`; jetzt
  `imported/<Podcast-Name>/<Datei>` (Name Windows-sicher gesäubert:
  verbotene Zeichen → Leerzeichen, Länge gedeckelt, Rückfall „Podcast").
  Gilt für neue Downloads; Bestandsdateien bleiben flach (Nachzug auf
  Wunsch).  Umbenannter Podcast = neuer Ordner für künftige Episoden.
  Tests +1 (Sanitizer), bestehende Download-Tests angepasst.  Handbuch
  LIBRARY §2.3 EN/DE/FR/ES (dabei die veraltete Worker-PodcastFetchJob-
  Notiz korrigiert — der Download läuft synchron in der API).  Aktiv nach
  RASTATIME-API-Neustart.

- **Settings → Backup: automatische Sicherungen + Restore-Hinweis
  (2026-09-17, Arbeitsreihenfolge Punkt 10 Stufe 3, Operator-Go — Punkt 10
  damit komplett, `a522ede`)** — Neue Sektion „Automatic backups": Häufigkeit alle
  N Tage, Aufbewahrung N Tage (0 = alles behalten), Einstellungen in
  cc_pref `local_backup_auto`.  Uhrwerk = Windows-Aufgabenplaner: der
  Operator registriert einmalig `scripts/backup-auto.ps1` (täglich, Log
  nach `logs/backup-auto.log`); das neue Management-Kommando
  `backup_auto` prüft die Fälligkeit selbst (jüngstes ZIP + Intervall,
  1 h Kulanz), nutzt denselben BackupJob wie „Back up now" (inkl.
  Medien-Spiegel je nach Schalter) und räumt danach ZIPs älter als die
  Aufbewahrung ab — das neueste überlebt immer, der Spiegel wird nie
  aufgeräumt.  Bewusst kein Scheduler im Code (Worker bleibt Stub).
  Restore-Sektion schlank: Hinweiskasten auf den dokumentierten
  Offline-Weg.  Route `/api/v2/storage/backup/auto`, Proxy
  `preference/backup-auto`.  Tests +6 (Fälligkeit, Aufräumen, Kommando
  fällig/nicht fällig/Fehlschlag, Endpoint); Backup-Tests 20, API-Suite
  grün.  Handbuch BACKUP §5 EN/DE/FR/ES (Neu-Nummerierung), operator
  BACKUP.md §3.3-Hinweis, ARCHITECTURE 0.39 (§23.35-Nachtrag).  Aktiv
  nach RASTATIME-API-Neustart; die Aufgaben-Registrierung macht der
  Operator.

- **Import vom FTP-Server — zweite Import-Quelle neben dem Import-Ordner
  (2026-09-17, Operator-Go, `75d52f8`)** — Neue Sektion Settings → Local Machine →
  „Import from FTP Server": `FtpImportScanTask` holt alle 5 Minuten (oder
  per „Fetch now") Audiodateien per PHP-curl von einem FTP-, FTPS-
  (explizites TLS) oder SFTP-Server in den lokalen Import-Ordner — ab dort
  übernimmt die bestehende Kette (Ruhe-Prüfung, organize, Analyzer),
  bewusst kein zweiter Import-Pfad.  Briefkasten-Semantik: nach
  verifiziertem Download wird das Original gelöscht (Konto braucht
  Löschrecht; scheitert das Löschen, warnt der Status vor Duplikaten).
  Entfernte Ruhe-Regel: geholt wird nur, was über zwei Sichtungen ≥ 60 s
  größenstabil ist (Zustand in `local_ftp_import_pending`), plus
  Größenvergleich nach dem Download — das Replikat mit wachsender Datei
  zeigte, dass die Nach-Download-Probe allein stoßweise Uploads verpasst.
  Nicht-Audio bleibt auf dem Server; Lauf-Budget 60 s je Zyklus;
  Zugangsdaten in cc_pref `local_ftp_import_config` (Passwort write-only
  in der UI, nie geloggt).  Live getestet gegen einen Wegwerf-FTP-Server
  (pyftpdlib: Abholen + Löschen + wachsende Datei bleibt liegen) und per
  SFTP gegen test.rebex.net (Auth + Listing).  Handbuch LOCAL_MACHINE
  §5 EN/DE/FR/ES, ARCHITECTURE 0.38 (§23.36).  PHP live (kein OpCache).

- **Settings → Backup: Medienbibliothek als inkrementeller Spiegel
  (2026-09-17, Arbeitsreihenfolge Punkt 10 Stufe 2, Operator-Go, `72e13c7`)** — Neue
  Option „Include media library" (cc_pref `local_backup_include_media`):
  jeder Lauf spiegelt die Bibliothek zusätzlich per robocopy /MIR nach
  `<Backup-Ordner>/media` — inkrementell (nur Geändertes kopiert,
  Gelöschtes verschwindet auch aus dem Spiegel), danach Datei-für-Datei
  verifiziert (Existenz + Größe, Wiederverwendung von
  `move.verify_copy`); nie gezippt, nie durch den Browser.  Job-Zustand
  mit Phasen (database → media → verifying), Fortschritt per walk_size
  alle 3 s, Platz-Prüfung vor dem Lauf (Bibliothek × 1,1 minus schon
  Gespiegeltes).  „Cancel" stoppt nur den Spiegel (das ZIP ist dann schon
  vollständig), der nächste Lauf setzt fort; ein Fehlschlag lässt den
  Teil-Spiegel liegen (inkrementell), löscht aber weiterhin halbe ZIPs.
  UI: Checkbox, Fortschrittsbalken, Phasen-Text, Cancel-Knopf; neue Route
  `/api/v2/storage/backup/cancel`, Proxy `preference/backup-cancel`.
  Tests `test_storage_backup.py` +4 (echtes robocopy, Purge-Nachweis).
  Live abgenommen 2026-09-17 15:31 (nach dem Proxy-Fix `3a31f5b`):
  2512 Dateien / 6,7 GB in 24 s nach `D:\backups\media` gespiegelt,
  Datei-für-Datei-Vergleich ohne Abweichung.
  Handbuch BACKUP §3 EN/DE/FR/ES, ARCHITECTURE 0.37 (§23.35-Nachtrag).
  Aktiv nach RASTATIME-API-Neustart.

- **Settings → Backup: Datenbank + Konfiguration per Klick sichern
  (2026-09-16, Arbeitsreihenfolge Punkt 10 Stufe 1, Operator-Go, `df53122`)** — Neue
  Settings-Seite nach dem Muster der Media Library Location: Backup-Ordner
  als Einstellung (cc_pref `local_backup_folder`, Validierung wie beim
  Umzugsziel), Backup-Job im API-Prozess (Zustand in `local_backup_state`
  mit PID/Heartbeat).  Ein Lauf schreibt ein in sich vollständiges ZIP
  `rastatime-backup-<Zeit>.zip` mit `db.dump` (pg_dump Custom-Format,
  direkt in das ZIP gestreamt, Zugangsdaten aus den Django-Settings =
  libretime.conf, Passwort nur via PGPASSWORD), allen Konfigurationsdateien
  und einem Manifest; ein Fehlschlag hinterlässt kein halbes ZIP.  UI:
  Ordner prüfen/speichern, „Back up now", Liste vorhandener Backups mit
  Download (ZIP über PHP gestreamt, API-Key bleibt serverseitig,
  Namensmuster gegen Pfad-Tricks).  Restore bleibt bewusst der
  dokumentierte Offline-Weg (docs/operator/BACKUP.md §7).  5 API-Routen
  `/api/v2/storage/backup*`, PHP-Proxies `preference/backup-*`,
  Nav-Eintrag Settings → Backup.  Tests `test_storage_backup.py` (10),
  API-Suite 107.  Handbuch-Kapitel BACKUP EN/DE/FR/ES + TOC,
  ARCHITECTURE 0.36 (§23.35).  Aktiv nach RASTATIME-API-Neustart.
  Live abgenommen 2026-09-17 10:20: erstes Operator-Backup über die UI —
  ZIP 453 KB, Integrität OK, `db.dump` 764 KB mit `pg_restore --list`
  gelesen (394 Einträge, 47 Tabellen mit Daten, cc_files/cc_show/cc_pref/
  podcast vorhanden), 3 Konfigurationsdateien + Manifest (pg_dump 17.7).

- **Gerenderte Einstellungen übernimmt das Playout selbst — kein manueller
  Neustart mehr nach 24/7-Aufnahme, Main Output, Crossfade oder
  Stream-Ausgängen (2026-09-16, Operator-Go, `6be216a`)** — Diese Werte werden beim
  Rendern in `rastatime.liq` gebacken; bisher hieß es nach dem Speichern
  „Restart the playout service to apply" bzw. „Apply now".  Jetzt bildet
  `__main__._render_settings_fingerprint()` einen Hash aus 24/7-Konfiguration,
  Main-Output-Gerät, Crossfade-Dauer und Stream-Ausgängen (nur DB-Lesezugriffe,
  keine Gerätesonde); `PlayoutScheduler._maybe_settings_restart()` vergleicht
  ihn bei jedem Refresh mit dem Stand des letzten Renders (Basis = erster
  Refresh nach dem Start) und nutzt bei Abweichung den Pfad des geplanten
  Neustarts: sofort im ruhigen Moment, sonst an der nächsten Datei→Datei-
  Grenze (Hörer über die Standby-Mounts verbunden); PLAYOUT rendert dabei
  im Prozess neu, nur LIQUIDSOAP startet.  Fehlgeschlagene Versuche werden
  nach 30 min wiederholt; nach einem erfolgreichen Neustart gilt der neue
  Hash als Basis.  „Apply now" bleibt für den Sofort-Fall.  UI-Texte auf der
  Local-Machine-Seite angepasst.  Tests `test_settings_restart.py` (8),
  Backend 626.  Handbuch LOCAL_MACHINE §2 und RECORD_PER_HOUR §5
  EN/DE/FR/ES, ARCHITECTURE 0.35 (§23.34).  Aktiv nach PLAYOUT-Neustart.
  **Live 2026-09-16 10:32:** Bitrate 128 → 192 gespeichert 10:31, Refresh
  10:32:35 → Render → LIQUIDSOAP-Neustart → wieder oben 10:32:38, Skript
  mit 192k.  **Nachtrag:** auch ein beim PLAYOUT-Start geändertes Skript
  (Vorlagen- oder Code-Update) wird jetzt so übernommen
  (`render_restart_pending`, Grund „rastatime.liq changed at the playout
  start"); die Startmeldung verlangt keinen manuellen Neustart mehr.

- **Cue-Sidecars kennen den Aufnahmebeginn der Audiodatei (2026-09-16,
  Operator-Go nach dem Cue-Marker-Test 7a, `642dd0c`)** — Befund: bei einer
  angebrochenen ersten Stunde (Aufnahme startet mitten in der Stunde, täglich
  nach dem 04:00-Neustart) beginnt die Audiodatei nicht am Stundenanfang, die
  Marker zählen aber ab `hour_start`.  `CueWriter` schreibt jetzt beim ersten
  Marker, der die Audiodatei vorfindet, `audio_start` (Erstellzeit, `st_birthtime`
  bzw. `st_ctime`) und `audio_start_offset` (Sekunden nach `hour_start`; volle
  Stunde = 0); ein Player springt zu `t - audio_start_offset`.  Tests
  `test_cue_writer.py` (+4).  Handbuch RECORD_PER_HOUR §4.1 EN/DE/FR/ES.
  Aktiv nach PLAYOUT-Neustart.

- **Speicherort der Medienbibliothek als Einstellung mit Umzugs-Job (2026-09-16,
  Stufe 2 von Arbeitsreihenfolge Punkt 7, Operator-Go, `c0b3c70`)** — Settings → Local
  Machine → „Media Library Location": aktueller Ort mit Herkunft, Dateizahl
  und Größe; neues Ziel eingeben, „Check" (absolut, lokales Laufwerk — keine
  Netzpfade in v1 —, anlegbar/beschreibbar, nicht in der alten Wurzel und
  umgekehrt, freier Platz ≥ Bibliothek + 10 %), „Move library" mit Rückfrage,
  Fortschrittsbalken, „Cancel move".  Wahrheit ist der cc_pref-Schlüssel
  `local_storage_folder` (leer = `storage.path` aus `libretime.conf`, das nur
  noch Startwert ist).  Auflöser: PHP `Application_Common_Storage::root()`
  (alle 19 bisherigen `Config::getStoragePath()`-Aufrufe), API
  `libretime_api.storage.root.get_storage_root()` (Datei-Download/-Löschen,
  Podcast-Download, `storage_flatten`), PLAYOUT holt die Wurzel bei jedem
  Refresh von `GET /api/v2/storage/location`.  Umzugs-Job im API-Prozess
  (`libretime_api.storage.move`, Zustand als JSON in `local_storage_move`):
  robocopy `/E /COPY:DAT /R:2 /W:2` (wiederaufnehmbar), Prüfung jeder
  Quelldatei am Ziel (Größe) und jedes `cc_files`-Pfads, dann Umschalten;
  Fehler/Abbruch lassen das Ziel teilkopiert, ein neuer Start setzt fort; ein
  API-Neustart während der Kopie → „interrupted" (Heartbeat/PID).  Während
  `copying`/`verifying` pausieren Importe: Upload (`MediaService`),
  Import-Ordner-Scan (`LocalImportScanTask`), Show-Bild- und Logo-Upload
  (PHP, `assertNotMoving()`), Podcast-Download (API, 409).  Die alte Kopie
  bleibt liegen — Löschen durch den Operator (Entscheidung 2026-09-16).
  Zugriff: PHP-Actions `preference/storage-location-{status,validate,move,
  cancel}` hinter Login + CSRF, Proxy zur API mit dem API-Key; die neuen
  API-Endpunkte `storage/location`, `storage/move/{validate,start,cancel,
  status}` verlangen den API-Key.  Preflight-Warnung `storage_root_unavailable`
  (Wurzel fehlt/schreibgeschützt) im Dashboard-Banner.  Tests:
  `test_storage_location.py` (21, Umzug mit echtem robocopy),
  `test_storage_root_follow.py` (10); API 97, Backend 614.  Handbuch
  LOCAL_MACHINE §6 EN/DE/FR/ES, INSTALL.md, MIGRATION.md, ARCHITECTURE 0.34
  (§23.33).  Aktiv nach Neustart von RASTATIME-API und RASTATIME-PLAYOUT (PHP
  sofort).

- **Speicherverlauf der Liquidsoap-Hauptinstanz im Playout-Log (2026-09-15,
  Operator-Go „günstige Mitte", `ac20f02`)** — Die Speicherwoche 2026-09-08..15 hatte
  keinen Verlauf: die Instanz lebte selten länger als einen Tag, und die
  Messwerte des Preflight-Scans wurden nur gegen die Warnschwelle geprüft,
  nie festgehalten.  Jetzt schreibt jeder Scan (alle 15 min) eine INFO-Zeile
  `preflight: Liquidsoap memory: PID … MB, … h old, +… MB since the first
  sample … h ago, … MB/h` (erste Messung einer Instanz: `first sample of
  this instance`; Rate erst ab 30 min Spanne).  Neue PID oder jüngeres Alter
  = neue Instanz, neue Basis; die Standby-Instanz wird wie bisher
  ausgefiltert.  Auswertung: `grep "Liquidsoap memory" logs/playout-stdout.log`.
  Tests `test_preflight_memory_log.py` (7).  Handbuch LOCAL_MACHINE
  EN/DE/FR/ES.  Wirksam nach PLAYOUT-Neustart.

- **Stream-Metadaten: Stream Label, Off Air Metadata und Show-Namen erreichen
  die Hörer (2026-09-13, Arbeitsreihenfolge Punkt 8, Operator-Go, `b997a7a`)** — Befund:
  die Werte aus Settings → Streams kamen nie im Liquidsoap-Skript an (PHP
  schickte sie auf RabbitMQ, das in RASTATIME niemand liest); bei Stille
  blieb der letzte Titel stundenlang auf Icecast stehen, „Stream Label" war
  wirkungslos, AAC/OGG meldeten „Unspecified name".  Jetzt: (1)
  `icy_metadata.py` liest `stream_label_format`, `off_air_meta`,
  `station_name` (ORM); der Renderer schreibt sie als Standardwerte in einen
  ICY-Block (`interactive` `icy_format`, `offair_text`, `station_name`,
  `bus_show`); der Scheduler liest sie bei jedem Refresh neu und schiebt
  Änderungen per Telnet (`var.set`, nur bei Änderung); `bus_show` = Show auf
  Sendung, gesetzt bei Refresh und Slot-Start.  (2) `icy_label` baut das
  Label je Metadaten-Paket (0 Artist - Title, 1 Show - Artist - Title, 2
  Station name - Show name; `off_air`-Pakete = Off-Air-Text; Pakete ohne
  unsere Felder bleiben unangetastet), `icy_rewrite` schreibt es per
  `metadata.map` auf dem Bus in `title` (Artist geleert) — so gilt es für
  ICY auf MP3/AAC, in-band bei OGG und für die Aufnahme-Tags;
  `output.icecast` bekommt `icy_song=icy_song_title`.  (3) Die Stille-Quelle
  trägt Off-Air-Metadaten: beim Fallen aus der Queue (Transition der
  `fallback`, `replay_metadata=false`), einmal beim Start und wenn der Bus
  mit leerer Queue auf den Scheduled-Arm fällt; die Live-Arme (Master, Show,
  Webstream, Line-In) fügen beim Umschalten ein `show_name`-Paket ein —
  jeweils auf der Transition-Quelle selbst, der einzigen Stelle, die den Bus
  erreicht (Replikat-Sonde: Inserts auf dem Arm oder der Quelle darunter
  kommen nie an; `icy_song` sieht nur Standardfelder wie title/artist/genre).
  (4) Mounts: leerer Name/Beschreibung → Sendername, Genre und URL werden
  gerendert.  Replikat-E2E `C:/Temp/optd/run_e2e_icy.py` (eigener Test-Mount
  am Produktions-Icecast, Sonden `probe_song.py`/`probe_insert.py`), acht
  Schritte grün: Startstille → Off-Air-Text; Datei → „Attwenger - Muamen";
  Format 1 → „Morgenshow - Attwenger - Zwoa"; Format 2 → „RASTATIME -
  Morgenshow"; Queue leer → Off-Air; Webstream-Arm → „RASTATIME - Webshow";
  Gate zu → Off-Air; geänderter Off-Air-Text nach dem nächsten Titel.  Tests
  `test_icy_metadata.py` (28, inkl. `--check` mit allen Bus-Armen), Backend
  591 / Unit 105.  Handbuch STREAMS EN/DE/FR/ES.  Aktiv nach PLAYOUT- **und**
  LIQUIDSOAP-Neustart (neuer Skript-Block).

### Changed

- **Kalender: Füllstandsbalken der Sendungen bleibt fest Orange (2026-09-29,
  Operator-Entscheid)** — Der Balken in den Show-Slots des Kalenders folgt
  nicht der Primärfarbe, sondern bleibt `#ff5d1a` wie bisher
  (`#schedule_calendar .ui-progressbar .ui-progressbar-value`).  Live
  verifiziert mit der gespeicherten Primärfarbe `#ffd900`: alle 31
  Balken orange.  Handbuch SETTINGS ×4, Architektur §23.43 — `b368a24`.

- **Widgets folgen der Primärfarbe (2026-09-29, Operator-Entscheid)** — Die
  eigenen Akzente der Widgets — Petrol `#459B8F` in Now Playing,
  Wochenprogramm (inkl. „heute"-Kästchen auf der Startseite), Multi-View,
  Track History, On Air Today, Shows-Listen; Blau `#2b7de9` im Song Request
  — sowie der Petrol-Login-Knopf und die Wochen-Tabs der Radio-Seite lesen
  jetzt `--rt-accent` (Rückfall: Standard-Orange); weißer Text auf vollen
  Akzentflächen nutzt die automatische Textfarbe.  Alle Widget-Views geben
  den Farbblock aus.  Sichtbare Änderung beim Standard: Petrol/Blau werden
  Orange.  Live verifiziert (alle Widget-Routen 200 mit Farbblock,
  Standard- und simulierte Palette); Handbuch SETTINGS ×4, Architektur
  §23.43 — `3697948`.

- **Dashboard: Hand-Cursor über den Spaltenüberschriften (2026-09-29,
  Operator-Wunsch)** — Über den Kopfzellen der Library-, Podcasts- und
  Scheduled-Shows-Tabelle zeigte der Browser den Text-Cursor; sie sortieren
  per Klick und lassen sich ziehen (ColReorder), daher jetzt
  `cursor: pointer` (dashboard.css, gilt auch im Schedule-Tracks-Dialog).
  Live verifiziert — `39be557`.

- **Library: Spalte „Type" zeigt den vollen Namen (2026-09-29,
  Operator-Wunsch)** — Dashboard → Tracks und der Schedule-Tracks-Dialog
  zeigen den Namen des Track-Types („Music", „Jingles", „Shows") statt des
  Codes (`music`, `jngl`, `show`); Spalte von 60 auf 80 px verbreitert, damit
  der Name im Dashboard-Button nicht abgeschnitten wird.  Live verifiziert — `e8ebc6c`.

- **Stream Label: Live-Quelle ohne Metadaten zeigt „Station - Sendung"
  (2026-09-28, Operator-Entscheid)** — Ein DJ, der keine Metadaten sendet,
  ein Webstream ohne eigene Titel und ein Line-In zeigten in den Formaten
  „Artist - Title" und „Show - Artist - Title" bisher nur den Sendungsnamen;
  jetzt in allen drei Formaten „Stationsname - Sendungsname" (bei fehlendem
  Sendungsnamen der Stationsname).  Gilt für Stream und Live Text Info
  gleichermaßen.  Handbuch STREAMS ×4.

- **Dashboard → Tracks: Spaltentitel und Dunkel-Kontrast (2026-09-28,
  Operator-Wunsch)** — Die drei Icon-Spalten der Bibliothek tragen jetzt
  Titel („Preview", „Cover", „Actions"; DE „Vorschau", „Cover",
  „Aktionen"; „Cover" neu in der JS-Übersetzungstabelle und in DE/FR/ES) und
  sind breiter (60/50/60 px) und zentriert.  Das dunkle Vorhör-Icon
  (Lautsprecher, Playlist, Block) war auf den #282828-Zeilen kaum zu sehen
  und wird per CSS-Filter hell dargestellt; die Zeilen-Checkboxen werden mit
  `color-scheme: dark` und dem RASTATIME-Akzent gezeichnet, damit sie in
  jedem Browser auf dem dunklen Grund sichtbar sind.  Im Browser geprüft — `2f6d3d8`.

- **Settings → General und → Streams: Erklärungstexte als Tooltips, DJ-Übergabe
  als eigener Block (2026-09-28, Operator-Wunsch)** — Gemeinsamer Helfer
  `$.rtDescriptionTooltips(root, {where, only})` in `common/tooltip.js`
  wandelt Zend-Beschreibungsabsätze in das Standard-Hilfe-Icon mit rtTooltip
  um (Text bleibt serverseitig übersetzt, HTML-escaped; der Track-Editor nutzt
  ihn jetzt auch).  General: die sieben langen Erklärungen (Track-/Show-
  Crossfade, Traffic-Alert Smart Block, Show-Shift Filler Playlist, Podcast
  Metatags, Podcast Smartblock, Public API) sitzen als Icon rechts neben dem
  Feldtitel; die kurzen Hinweise unter Logo/Favicon bleiben Text.  Streams:
  „Switch Transition Fade" steht in einem eigenen Block „DJ Hand-over" mit
  Einleitungssatz, gestaltet wie Master Source / Show Source, das Icon rechts
  neben dem Eingabefeld.  Neue Strings in EN/DE/FR/ES.  Im DOM nachgemessen:
  alle Icons 14×14 auf der Zeile ihres Labels bzw. Feldes, Tooltip-API
  gebunden, keine Absätze mehr außer Logo/Favicon — `a884207`.

- **Track-Editor: Erklärungstexte als Tooltips (2026-09-28, Operator-Wunsch)** —
  Die Beschreibungen unter „Expiry Date" und „No Fade during Crossover"
  (Zend `description`-Absatz) werden beim Öffnen des Editors in das
  Standard-Hilfe-Icon mit rtTooltip umgewandelt (`_initFileMdEvents` in
  `spl.js`, generisch für jedes Feld mit Beschreibung; Text bleibt
  serverseitig übersetzt, wird HTML-escaped).  Gleiche Optik wie unter
  Settings → Streams.  Im Browser geprüft: zwei Icons 14×14 mit Tooltip-API,
  keine Absätze mehr — `720e479`.  Nachschärfung: das Icon sitzt rechts auf
  der Zeile des Feldes (Eingabefeld lässt 26 px Platz statt 100 % Breite,
  Checkbox und Icon vertikal zentriert), wie bei Settings → Streams →
  Stream Type; nachgemessen im DOM — `07c58ac`.

- **„Exclude from Crossover" → „No Fade during Crossover" (2026-09-27, Operator
  nach der Abnahme)** — Der markierte Titel bleibt im Crossover (Überlappung
  wie eingestellt), wird aber selbst nicht ein- oder ausgeblendet: er behält
  seine volle Lautstärke, während der andere Titel blendet (beide markiert =
  reine Überlappung; an einer überzogenen Sendungsgrenze wird ein markierter
  abgehender Titel geschnitten statt ausgeblendet).  Spalte umbenannt
  (`cc_files.no_fade_crossfade`, Migration 0060), Checkbox, API-Feld,
  FileEvent, Handbuch ×4.  Liquidsoap: zweite Variable `rt_nofade`
  (old/new/both/-), der Playout sendet `<form>/<seite>`; „kein Fade" ist ein
  1-ms-`fade.out` mit unerreichbarer Verzögerung — `fade.out` blendet, sobald
  die Verzögerung erreicht ist ODER der Rest auf die Dauer sinkt, und bleibt
  danach stumm (Bench).  Die Sonderregel „keine Überlappung neben einem
  markierten Titel" im PHP-Scheduler entfällt wieder (Zeilen überlappen
  normal).  Bench mit vier Formen bestanden — `336e86e`.  **Live abgenommen
  2026-09-28 00:22–00:38 (fünfte Probe):** Sweetlove → Jingle `track/new`
  (Jingle sofort voll, Sweetlove blendet aus), Jingle → Bam `track/old`
  (Jingle voll bis zum Ende, Bam blendet ein), Bam → Komm Baby `track/new`;
  Sendungsgrenze und normaler Titelwechsel unverändert korrekt, Icecast
  ohne Fehler.

- **Settings → General: Fade-In/Fade-Out-Felder ausgeblendet, Crossfade-Feld
  umbenannt (2026-09-27, `07e6e1f`)** — „Default Fade In (s)" / „Default Fade Out (s)"
  (LibreTime-Erbe, seit der Liquidsoap-Migration ohne Wirkung — die Werte
  landen nur noch in `cc_schedule.fade_in/fade_out`) werden nicht mehr
  angezeigt; die Preference-Schlüssel bleiben.  „Default Crossfade Duration
  (s)" heißt „Default Track Crossfade Duration (s)".  Die 8-Sekunden-Regel
  („Titel unter 8 s ohne Crossfade") war seit Mai 2026 nicht aktiv (Revert,
  weil `liq_cross_duration=0` kurze Titel stumm schaltete); der Rest
  (Konstante, Kommentar) ist entfernt, Ersatz ist das Titel-Attribut.  Die
  Umgebungsvariable `RASTATIME_LIQUIDSOAP_CROSSFADE_FADE_SECONDS` ist
  außer Dienst (Warnung, wenn gesetzt).  Bus-Übergänge haben nur noch eine
  Form (neu sofort voll, alt blendet darunter aus, Dauer = Show-Wert; 0 =
  50-ms-Schnitt).

- **Player-Cover per Checkbox, Track History ohne Cover (2026-09-18,
  Operator-Nachschärfung zu W4.1, `eea2038`)** — Settings → Widgets → Player hat
  jetzt die gespeicherte Checkbox „Show cover artwork" (Preference
  `widget_player_show_art`, ab Werk an).  Sie bestimmt den Standard
  jeder Player-Einbettung ohne `art`-Parameter, also auch die Leiste
  der Stations-Homepage; ein ausdrückliches `?art=on|off` gewinnt.  Die
  Track History zeigt keine Cover mehr (Operator: nicht benötigt) —
  Zelle, Datenfelder, SQL-Spalten und CSS wieder entfernt; der
  Parameter-Fix für `exclude_short`/`min_seconds` bleibt.  Nebenbei
  einen falschen Code-Kommentar im Player korrigiert: Ausgeblendete
  Cover (display:none) lassen den Text nachrücken, das Layout springt
  also bei Titeln ohne Bild — es gibt bewusst keinen Platzhalter.
  Handbuch WIDGETS EN/DE/FR/ES.

- **Stream-Player-Widget v2 — das letzte Upstream-Widget im Wellen-Stil
  neu gebaut (2026-09-18, Punkt 12, Operator-Go Option A, `4178007`)** — Der 2015er
  jQuery-1.10.2/JSONP-Player ist ersetzt: selbstenthaltenes Vanilla-
  iframe wie alle Wellen-Widgets.  Metadaten über den Widget-Endpoint
  /embed/now-playing-data (kein JSONP, kein Public-API-Gate mehr — auch
  die Settings-Seite gated nicht mehr), Stream-Wahl clientseitig per
  Audio.canPlayType (Mobile-Streams zuerst auf kleinen Schirmen) mit
  Fehler-Fallback auf den nächsten Stream, localhost-Icecast-Host wird
  für entfernte Hörer auf den Seiten-Host umgeschrieben, Play/Stop
  trennt beim Stopp die Verbindung (kein stiller Hörer-Slot), neuer
  Lautstärkeregler (localStorage), Layouts card (Standard) + bar
  (Seitenfuß; Legacy-`style=premium` mappt darauf, die Radio-Page-
  Einbettung läuft unverändert), `?theme=auto|dark|light`, kein
  LibreTime-Branding.  Settings → Widgets → Player im Wellen-Stil
  (Vorschau + Embed-Codes, kein Formular).  Raus: playerhtml5.js,
  player.js, jquery-1.10.2 (letztes jQuery im öffentlichen Bereich),
  player.css, premium_player.css, player-form.css, Form_Player.
  Dabei entdeckt + entfernt: die Radio-Page griff per
  `$("#player_iframe").load(...)` in den Player-iframe (in jQuery 3
  entferntes .load(fn) — seit dem Migrate-Aus vom 17.09. fatal für den
  Block) und injizierte Tab-Knöpfe in die alte bottom_bar; Block
  gestrichen (jPlayer-Teil tot, RSS-Tab auf dieser Station aus).
  Falls der Stations-Podcast je öffentlich wird: Podcast-Tab braucht
  dann einen SEITEN-Link statt In-Player-Knopf.  Handbuch WIDGETS
  (Tabellenzeile + eigener Abschnitt) EN/DE/FR/ES.  Live verifiziert:
  card + bar rendern themenkorrekt ohne Konsolen-Fehler, Radio-Page
  sauber; Hör-Abnahme durch den Operator offen (Chrome lädt in nie
  sichtbaren Automations-Hintergrund-Tabs keinerlei Medien — auch die
  native Player-Seite nicht; kein Player-Defekt).

- **Line-In-Dialog: Enabled-Schalter entfernt (2026-09-17, Operator-
  Nachschärfung zur Konsolidierung, `d21cc94`)** — „Wenn es einen Line-Input gibt,
  darf man ihn auch verwenden."  Checkbox samt Beschreibung raus
  (Dialog, spl.js, Modell-Getter); Neuanlagen pinnen enabled=true,
  Updates lassen das Feld unangetastet (DB-Spalte bleibt — API/Playout-
  Vertrag; alle 6 Bestandszeilen stehen auf true).  Im Handbuch starben
  dabei auch die „Disable"-Abschnitte, die eine nie existierende
  Kontextmenü-Aktion beschrieben (Doku-Drift), EN/DE/FR/ES.

- **Line-In komplett im Library-Dialog — die Local-Machine-Sektion ist weg
  (2026-09-17, Operator-Go, `e836c26`)** — Es gab EINE Datenhaltung, aber zwei
  Editoren: schlanker Dialog unter Line Inputs (Name, Gerät) und voller
  Editor unter Settings → Local Machine (zusätzlich Kanalwahl, Aktiv).
  Jetzt ist der Library-Dialog der eine vollständige Editor: Kanal-Picker
  (eine Option je Stereo-Paar des Geräts, dann jeder Mono-Kanal; alte
  freie Mappings bleiben als Custom-Eintrag wählbar) und Aktiv-Schalter
  wandern hinein, jede Speicherung überträgt beide Felder.  Die Sektion
  „Line-In Sources" samt `_sources.phtml` und `linein.js` ist entfernt;
  `/linein` leitet auf das Dashboard.  Historie: eigenständige Seite
  (05/2026) → Sektion in Local Machine (08/2026, weil unauffindbar) →
  konsolidiert (09/2026).  Bewusste Rechte-Folge: Wer Line Inputs
  verwalten darf, wählt jetzt auch Kanäle/Aktiv (vorher Admin-Seite) —
  auf dieser Ein-Personen-Instanz gewollt, siehe Backlog-Item
  „Benutzergruppen-Audit".  Handbuch LINE_IN + LOCAL_MACHINE EN/DE/FR/ES.
  Live verifiziert: Sektion weg, Dialog trägt Kanäle/Aktiv, Redirect
  greift, keine Konsolen-Fehler.  PHP/JS live (kein OpCache).

- **Medienbibliothek ohne owner-id-Ebene, alle Pfade relativ zur
  Speicherwurzel (2026-09-16, Stufe 1 von Arbeitsreihenfolge Punkt 7,
  Operator-Go, `6059dc4`)** — Vorbereitung für den wählbaren Speicherort (Settings →
  Local Machine, Stufe 2): `imported/<owner-id>/…` wird `imported/…`.  Die
  owner-id-Ebene entstand an fünf Stellen, nicht nur im Upload:
  `MediaService.php` (Import-Ziel), `CcFiles.php` (Cover unter
  `artwork/`), `ShowImageController.php` (Show-Bilder, zweimal),
  `PreferenceController.php` (Auto-DJ-Logo) und `podcasts/download.py`
  (Podcast-Episoden; jetzt `imported/…` ohne führenden Schrägstrich wie der
  Analyzer).  Show-Bilder und das Auto-DJ-Logo wurden bisher **absolut**
  gespeichert (`C:/rastatime/media/imported/2/…`) und hätten jeden
  Wurzelwechsel gebrochen; neu speichert PHP sie relativ
  (`Application_Common_Storage::toRelative`) und löst sie beim Lesen auf
  (`toAbsolute`: Show-Logo-Endpunkt, Vorschau im Show-Formular, Vorschau im
  Auto-DJ-Dialog; alte absolute Werte bleiben lesbar).  Einmalige Migration:
  Django-Befehl `storage_flatten` (Trockenlauf; `--apply` verschiebt die
  Einträge von `imported/<id>/` eine Ebene hoch und schreibt
  `cc_files.filepath`/`artwork`, `cc_show.image_path` und
  `cc_pref.auto_dj_logo_path` in einer Transaktion um; Fehler → Zeilen
  zurückgerollt, Einträge zurückgeschoben; nur bekannte owner-ids werden
  entfernt, ein rein numerischer Interpreten-Ordner bleibt).  Trockenlauf in
  Produktion: 80 Einträge, 343 + 216 + 29 + 1 Zeilen, alle 343 Datei-Pfade
  vorher und nachher auflösbar.  Tests `test_storage_flatten.py` (17),
  Podcast-Tests angepasst.  MIGRATION.md §4.4/§4.5 auf den Befehl
  umgestellt, ARCHITECTURE 0.33 (§23.32).  Ausgeführt in Produktion am
  2026-09-16 09:10 (Operator, nach DB-Dump): 80 Einträge, 343 + 216 + 29 + 1
  Zeilen, 343/343 Pfade auflösbar; Show-Logo, Cover und Downloads danach
  live geprüft.

### Fixed

- **Track Types: Daten-Endpoint ohne XHR-Header antwortete 500 (2026-09-30,
  Upstream-Erbe)** — `Tracktype/get-tracktype-data` schaltete nur bei
  `X-Requested-With`-Aufrufen auf JSON; jeder andere Aufruf rendete das
  View-Script `get-tracktype-data.phtml`, das das Array ausgab und mit
  „Array to string conversion" starb.  Die Action sendet das JSON jetzt
  selbst (wie die Tabellen-Action daneben), das View-Script ist weg.  Live
  verifiziert: `fetch` und `$.ajax` liefern 200 mit `entries`, das Formular
  füllt sich weiter.  Dasselbe Muster liegt noch in fünf anderen
  View-Scripts (schedule, user, remove-tracktype) — dort nicht angefasst.

- **A relay or line-in after a jingle came in about one second early
  (2026-09-29, found while checking the logs after the crossfade per track
  type went live)** - the rows carry microseconds now (a jingle sequence ends
  at 08:01:06.78), but the playout's timers fire on the whole second
  (`event_isoparse` drops the microseconds) and the file chain runs a moment
  behind the rows (push + request resolution, about 0.2 s): the gate of the
  pre-warmed BBC relay would have opened at 08:01:06.0 and the switch would
  have faded the intro's last second away.  Events carry the exact row times
  (`start_exact`, `end_exact`), the scheduler measures the lag of the file
  chain at the push that starts it, and a pre-warmed webstream or line-in that
  follows a file track opens its gate when the track's audio is over, minus
  the overlap of the pair (at most `FILE_TAIL_HOLD_MAX_SECONDS` = 4 s; more is
  an overbook and the live item starts at once).  The stop of a file track
  waits the same way, so neither the deferred skip nor the bookkeeping reset
  comes before the last moments are out.  The engine cannot be asked: inside
  its last BUFFER seconds a track sits in the cross operator's tail.  21 tests
  (`test_live_after_file_hold.py`).  Active after a restart of
  RASTATIME-PLAYOUT - `8c8d1c5`.

- **Upload-Seite: weißer Streifen, unlesbare Texte (2026-09-29,
  Operator-Meldung)** — Unter beiden Panels (Upload, Recent Uploads) lag ein
  weißer Streifen: `.content-pane` überschreibt die Farbe des
  jQuery-UI-Themes (`.ui-widget-content`, #fcfdfd), aber nicht dessen
  100-px-Verlaufsbild an der Panel-Unterkante.  Die Regel
  `.rt-jq3 .content-pane.ui-widget-content { background-image: none }`
  (styles.css) gilt jetzt für alle Content-Panels statt Seite für Seite.
  „Drop files here or click to browse your computer.", die Filter „All /
  Failed / Pending" und die Links „Delete from Library" erbten die
  Grundfarbe #222 (dunkel auf dunkel) und sind jetzt hellgrau (#ccc, Hover
  weiß; addmedia.css).  Live verifiziert, Dashboard unberührt — `38f41f2`.

- **Library: Type-Ziffer nach Umsortieren, Kopf-/Fußleiste scrollten mit
  (2026-09-29, Operator-Meldung, Nachbesserung zu `c3960c3`)** — (1) Mit
  gespeicherter Spaltenreihenfolge zeigte Dashboard → Tracks in „Type" die
  Ziffer (und leere Preview-/Cover-Zellen): ColReorder schreibt nach jedem
  Umsortieren — Ziehen oder gespeichertes Layout nach dem ersten Zeichnen —
  alle Zellen aus den Rohdaten neu (`rows().invalidate("data")`).  Checkbox,
  Preview-Icon, Cover, Type-Code, Scheduled-Icon und Actions sind jetzt
  Spalten-Renderer (`mRender`), `fnCreatedRow` bindet nur noch die
  Klick-Handler; ein ausgeblendeter Track-Type wirft nicht mehr, er bleibt
  leer.  (2) Das Layout wurde asynchron geladen, DataTables baute die
  Tabelle dadurch erst nach dem Code, der sie in den Scroll-Container
  packt: Überschrift, Suchzeile und Pager lagen im Scroll-Bereich (Tracks,
  Playlists, Smart Blocks, Webstreams, Line Inputs; Podcasts nicht
  betroffen), die Spalten-Auswahl-Buttons fehlten.  Das Laden ist wieder
  synchron (wie Upstream).  Neu: die Spaltenüberschriften der
  Scroll-Tabellen bleiben beim Scrollen stehen (`position: sticky`,
  dashboard.css; vorher scrollten sie mit).  Live verifiziert (Dashboard
  mit gespeichertem, umsortiertem Layout, Spalte ziehen, Tracks/Playlists
  scrollen, Dialog); Handbuch LIBRARY ×4, Architektur §23.42 — `4889619`.

- **Tabellen-Layout pro Benutzer; Type/Cover/Preview nach Spalten-Einblenden
  (2026-09-29, Operator-Meldung)** — Dashboard → Tracks und Kalender →
  Schedule Tracks vergaßen Spaltenreihenfolge, sichtbare Spalten und Zeilen
  pro Seite: DataTables 1.13 kennt die 1.9-Optionen `fnStateSave` /
  `fnStateLoad` nicht, seit der jq3-Umstellung lag der Stand nur im
  localStorage des Browsers und verfiel nach 2 Stunden.  Neu:
  `rtDatatableServerState()` (common.js) lädt das Layout vor dem ersten
  Zeichnen vom Server und speichert es als DataTables-State-JSON pro
  Benutzer (`cc_pref`: `library_datatable`, `library_builder_datatable` für
  den Dialog ohne Actions-Spalte, `timeline_datatable` für Scheduled Shows),
  ohne Ablauf; gepostet wird nur ein geändertes Layout (die Timeline zeichnet
  periodisch neu).  Suchen und aktuelle Seite werden nicht gemerkt.  Die
  erweiterte Suche paart `sSearch_i` jetzt direkt mit `mDataProp_i` — der
  Umweg über die gespeicherte ColReorder-Map (für das 1.9-columnFilter-Plugin)
  hätte mit gespeicherter Reihenfolge Suchbegriff und Spalte vertauscht.
  Außerdem: Spalten, die beim Zeichnen versteckt waren und danach
  eingeblendet wurden, zeigten die Rohdaten — Type als Ziffer, Cover als
  Pfad (`imported/artwork/…`), Preview leer, aber klickbar; `fnCreatedRow`
  dekoriert jetzt alle Zellen der Zeile (`cells`-Argument) statt nur der
  sichtbaren.  Das Preview-Icon der Scheduled-Shows-Tabelle ist wie das der
  Library auf hellgrau invertiert.  Live verifiziert (Laden/Neuladen,
  Dialog-Layout getrennt, Spalte einblenden, erweiterte Suche bei
  umsortierten Spalten); Handbuch LIBRARY ×4, Architektur §23.42 — `c3960c3`.

- **Analyzer: ffmpeg-Ausgabe tolerant lesen (2026-09-29)** — Eine von 373
  Dateien blieb bei der R128-Bestandsmessung ungemessen (und hatte seit dem
  Import auch keinen ReplayGain-Wert): ffmpeg gibt die Tags der Datei aus,
  ein Byte außerhalb der Konsolen-Codepage ließ den Lese-Thread des
  Subprozesses mit einer Ausnahme sterben, das Ergebnis ging verloren.
  `compute_loudness` und `compute_replaygain` übergeben jetzt
  `errors="backslashreplace"` (wie `probe_replaygain` schon immer); Test.
  Wirksam nach ANALYZER-Neustart, danach „Measure missing files now" — `a361002`.

- **Titel-Verstärkung galt seit dem Crossfade-Umbau nur für den ersten Titel
  einer Strecke (2026-09-29)** — Beim Abgleich der 24/7-Aufnahme mit den
  Messwerten fiel ein Titel mit unveränderter Spitze auf.  Bench (drei Töne
  mit −10 / −20 / −4 dB): `amplify(override="replaygain_track_gain")`
  übernimmt den Wert am TRACK-ANFANG; auf dem Bus liefern die
  Crossfade-Übergänge seit 27.09. Metadaten, aber keine Track-Marke — jeder
  Titel einer durchgehenden Strecke spielte mit der Verstärkung des ERSTEN
  (Ton C mit −4 dB lief mit den −10 dB von A).  Betroffen: ReplayGain seit
  2026-09-27 und R128 gleichermaßen.  Die Verstärkung sitzt jetzt auf der
  Queue vor dem Crossfade (`scheduled_g = amplify(id="track_gain", …,
  scheduled_q)`, `cross(…, scheduled_g)`): jede Anforderung beginnt dort
  einen Track, und die beiden Seiten eines Crossfades tragen je ihre eigene
  Verstärkung.  Das Bus-`amplify` entfällt (Webstreams haben ihr eigenes
  Gain am Arm).  Bench danach: A −19,7 / B −29,6 / C −13,7 LUFS in den
  Formen track, show und track_skip.  Render-Regressionstest; wirksam nach
  PLAYOUT-Neustart (Skript ändert sich → geplanter Liquidsoap-Neustart) — `60b3f56`.

- **R128: True-Peak-Kappung nur noch für Anhebungen (2026-09-29)** — Die
  erste Bibliotheksmessung (352 von 373 Dateien: Ø −14,7 LUFS, −35,8 …
  −4,9; True Peak Ø −0,3 dBFS, 172 Dateien über 0 dBFS, ein Ausreißer mit
  +15,2) zeigte: `file_gain_db()` zog auch ABSENKUNGEN weiter herunter, wenn
  True Peak + Gain über der Grenze lag — bei −23 LUFS Ziel 9 Dateien, bei
  einem −16-Ziel wären es 133 gewesen (MP3s messen routinemäßig +1 … +2
  dBTP), die dann unter dem Ziel gespielt hätten.  Jetzt wird nur eine
  Anhebung gekappt (nie unter 0 dB); laute Dateien gehen auf das Ziel, die
  Spitzen nimmt der Bus-Limiter.  Tests erweitert; wirksam nach
  PLAYOUT-Neustart — `83b5749`.

- **PLAYOUT startete nach dem R128-Commit nicht (2026-09-29 07:53)** —
  `write_rastatime_liq()` (der Datei-Wrapper um das Rendern) kannte den
  neuen Parameter `loudness_limiter_ceiling` nicht: „unexpected keyword
  argument", Render-Abbruch, nssm pausierte den Dienst nach drei Versuchen;
  Liquidsoap lief mit dem alten Skript weiter (Sender auf Sendung, aber ohne
  Scheduler).  Parameter im Wrapper ergänzt, Regressionstest für den
  Wrapper — `c41e27c`.

- **Sendepause nach einem geplanten Liquidsoap-Neustart an der Titelgrenze
  (2026-09-28, 20:27:11 bis zum nächsten Titel)** — Der geplante Neustart
  an der Titelgrenze (gerendertes Skript geändert, §23.34) leert die
  Liquidsoap-Queue, der Scheduler hielt den Nachfolger aber weiter als
  „vorgelegt" (`_queued_ahead`, seit 27.09.): sein PLAY „adoptierte" eine
  leere Queue, nichts spielte, die Mounts zeigten den Off-Air-Text bis zur
  nächsten Zeile.  Neu: `_after_liquidsoap_restart()` (geplante Neustarts)
  und die Neustart-Erkennung per Prozesstabelle/Uptime
  (`_forget_queued_ahead()`) verwerfen die Queue-Ahead-Buchführung samt
  Push-Zeitpunkt; `_on_file_start()` tut es direkt nach einem
  durchgeführten Grenz-Neustart und pusht den Titel frisch.  Drei Tests;
  wirksam nach PLAYOUT-Neustart — `29236a9` (Grenz-Neustart), `d098f1a`
  (Neustart-Erkennung).

- **19 s Sendepause an einer Titelgrenze während eines Schedule-Refreshs
  (2026-09-28, 20:05:35–20:05:57)** — Zwei vorbestehende Fehler, die
  zusammen den Nachfolger abschnitten und danach Stille ließen: (1) Der
  Schedule-Abruf dauert ~4 s; fällt eine Titelgrenze in dieses Fenster,
  feuert der PLAY des Nachfolgers während des Abrufs, und das anschließende
  Neu-Armen sah den Vorgänger als „in progress" (seine Zeile überlappt um
  den Crossfade) → Catch-up des Vorgängers, der den Nachfolger per Skip
  abschnitt.  Neu: `_precedes_playing()` — eine Zeile, die in der
  Reihenfolge vor dem laufenden Item liegt, wird nie nachgeholt (Datei,
  Webstream, Line-In); ohne laufendes Item bleibt jede laufende Zeile ein
  Catch-up.  (2) `scheduled.remaining` meldete 214,9 s Rest für einen Titel
  mit 3 s Audio: sobald `cross` den Nachfolger gezogen hat, gehört das
  „remaining" der Queue dem Nachfolger, und die gemeldete RID hinkt kurz
  hinterher → Skip traf den Nachfolger.  Neu: der Scheduler merkt sich
  Push-Zeitpunkt und Audiolänge des laufenden Titels
  (`_current_started_at` / `_current_clip_seconds`); meldet die Engine mehr
  Rest, als der Titel noch haben kann (Länge − verstrichene Zeit + BUFFER +
  2 s), gilt die Übergabe als geschehen (kein Skip).  Ein verspätet
  gestarteter Vorgänger (Probe 2 vom 27.09.) bleibt plausibel, weil der
  Push-Zeitpunkt die tatsächliche Startzeit ist.  Dazu: `drop_metadata` →
  `source.drop.metadata` (in 2.4 als veraltet gemeldet, eine Warnung je
  Übergang).  Vier Tests; wirksam nach PLAYOUT-Neustart — `5b34d71`.

- **Catch-up steigt am Offset ein, Zeilenverschiebung der laufenden Zeile
  ohne Neustart (2026-09-28, Operator-Go)** — Zwei hörbare Neuansätze des
  laufenden Titels aus dem Log vom 28.09.: (a) Nach einem PLAYOUT-Neustart
  spielte der Catch-up den laufenden Titel von vorn („Fade" 141 s
  gelaufen; der Folgetitel maß 140 s Restaudio, wo die Zeilen 2 s sagten,
  und schnitt per `track_skip`).  Der Catch-up übergibt jetzt den Versatz
  (`now - start`) an `_on_file_start(key, event, seek)`, der ihn auf den
  Cue-In addiert — derselbe `liq_cue_in`-Seek, den der Resume-Pfad nach
  DJ-Auflegen schon immer nutzte; Versatz hinter dem Audio-Ende → nichts
  spielen; eine vorgelegte Kopie desselben Titels wird ab 1 s Versatz
  verworfen (sie startete am Anfang).  (b) Eine Show-Builder-Änderung an der
  laufenden Sendung (`schedule-remove`, 18:30:16) terminiert die Folgezeilen
  neu, auch die laufende (Row 6252: Start +9 s, Cue-In 2,18 s, gleiche
  Row-ID); `_same_scheduled_item` verglich Row-ID UND Start → „removed from
  schedule", Stop, Catch-up desselben Titels von vorn, eine Sekunde später
  Skip auf den Nachfolger.  Identität ist jetzt Row-ID + Medium (Datei-,
  Stream- bzw. Line-In-ID; Line-In zusätzlich Gerät + Kanal-Mapping), der
  Start nicht mehr (Row-IDs sind serial, nie wiederverwendet); der Refresh
  rebindet eine neu terminierte laufende Zeile ohne Teardown (das Event auf
  Sendung behält seine Zeiten — die Audio-Wahrheit für die Crossfade-
  Rechnung), eine in die Zukunft verschobene laufende Zeile gilt als weg
  (Stop, Neustart zum neuen Start); ein Stop aus dem Refresh räumt auch
  die Queue-Ahead-Buchführung (engine.stop() flusht die Queue); der
  Queue-Ahead legt einen umgecueten Nachfolger neu vor.  Tests
  `test_catchup_offset.py` (10) + Identitätstest angepasst; Architektur
  §23.40; wirksam nach PLAYOUT-Neustart, Live-Probe (Neustart im Titel,
  Zeile aus laufender Sendung entfernen) offen — `0f62b14`.

- **Stream-Titel und Live Text hingen einen Titel hinterher (2026-09-28)** —
  Seit den Crossfade-Formen vom 27.09. zeigten ICY-Titel und die
  Live-Text-Datei während eines Titels noch den vorherigen; der richtige
  erschien erst beim nächsten Übergang.  Bench (drei Töne, `on_metadata` am
  Bus): `add()` reicht nur die Metadaten der ERSTEN Quelle in der Liste
  durch, und `cross` spielt die Metadaten des endenden Titels auf dessen
  gepuffertem Schwanz noch einmal aus — mit dem Schwanz vorn ging das Paket
  des neuen Titels verloren, das wiederholte alte kam durch.  Jetzt steht in
  jeder `add`-Form (track, track_skip, show_skip, instant) der neue Titel an
  erster Stelle und der Schwanz läuft durch `drop_metadata`; die
  `sequence`-Form (show) war nicht betroffen.  Bench danach: das Paket kommt
  in allen fünf Formen genau zum hörbaren Start des neuen Titels.  Dazu:
  `/live/now-playing.txt` wird per `.htaccess` als `text/plain;
  charset=utf-8` und ohne Cache ausgeliefert (Browser zeigten „KÃ¼nstler"),
  die Laufzeitdatei ist git-ignoriert.  Render-Regressionstest; wirksam nach
  PLAYOUT-Neustart (gerendertes `rastatime.liq`) — `e767c0f`.

- **Podcast-Episodentitel doppelt HTML-kodiert (2026-09-28, Operator-Go)** —
  WordPress-Feeds liefern typografische Anführungszeichen als HTML-Entities
  in CDATA (`&#8222;…&#8220;`), SimplePie escapt beim Sanitizen das `&` noch
  einmal, und RASTATIME übernahm die Ausgabe ungeprüft: `&amp;#8222;` stand
  in `podcast_episodes.episode_title`, im Bibliothekstitel und im ID3-Tag
  (20 Titel, 24 Episoden — „Reading Hour", „Newsmag", „The Talk Show").
  Fix: `PodcastEpisodeService::feedPlainText()` dekodiert Feed-Text bis zur
  Ruhe (max. drei Runden) zu Klartext, die Bibliothek escapt ohnehin bei der
  Ausgabe.  Einmalige Bereinigung der bestehenden Zeilen (Titel, Interpret,
  Album, Episodentitel) mit derselben Dekodierung: 44 Aktualisierungen, keine
  kodierten Reste.  Die ID3-Titel der bereits geladenen Dateien bleiben wie
  sie sind (nur der Bibliothekseintrag zählt für Sendeplan und Stream) — `56fa348`.

- **Track-Editor: „Expiry Date" war seit Mai 2026 unübersetzt (2026-09-28)** —
  Label, Beschreibung und Validierungsmeldung des Ablaufdatums fehlten in den
  DE/FR/ES-Katalogen (aufgefallen bei der Tooltip-Prüfung auf Deutsch);
  nachgetragen — `0f377f1`.

- **Cue-Punkte wurden seit der Liquidsoap-Migration nie angewendet
  (2026-09-27, gefunden in der zweiten Crossfade-Probe)** — Der Playout
  annotierte Requests mit den LibreTime-Schlüsseln `cue_in`/`cue_out`;
  Liquidsoap 2.4 wertet bei der Request-Auflösung nur `liq_cue_in` /
  `liq_cue_out` aus (`cue_cut` ist deprecated, das Template hatte keinen).
  Jeder Titel lief von 0 bis zum Dateiende — Bibliotheks-Cue-Punkte,
  Filler-Kürzungen und das von der API auf das Sendungsende gekappte
  `cue_out` eines überziehenden Titels blieben wirkungslos (der Titel lief
  45 s in die nächste Sendung).  Bench: `liq_cue_in=1,liq_cue_out=4` →
  exakt 3 s hörbar, die alten Namen ignoriert.  Jetzt native Schlüssel.
  Zweite Probe außerdem: Skip-Toleranz 0,3 → 1,5 s, weil Event-Starts auf
  ganze Sekunden gerundet sind (Zeilenstart 17:43:00,56 → PLAY 17:43:00,0,
  „3,56 s Rest" bei 3 s Überlapp wurde als Overbook geskippt) — `45634cc`.

- **Der bisherige Titel-Crossfade war ein Butt-Splice (2026-09-27, `07e6e1f`)** —
  PLAYOUT skippte den laufenden Titel und pushte erst danach; Liquidsoaps
  `cross` fiel für einen Frame auf den Stille-Arm (Produktions-Log:
  `Analysis … / -infdB` gefolgt von `-infdB / …` eine Sekunde später), der
  alte Titel spielte seinen Rest aus, der neue folgte hart.  Jetzt Push vor
  Skip (die synchrone Queue löst den Request sofort auf) bzw. Queue-Ahead,
  ein Skip nur, wenn der Vorgänger noch Audio hat — sonst hätte er den neuen
  Titel getroffen.  Erste Live-Probe 2026-09-27 16:46–17:05 (zwei
  Test-Sendungen, Track 3 s / Show 1 s): Titelwechsel in der Sendung
  sauber (Queue-Ahead, `track`), die Sendungsgrenze aber nicht — die API
  kappt `ends_at` eines überziehenden Titels auf das Sendungsende, der
  STOP-Timer des Vorgängers feuerte im selben Augenblick wie der PLAY des
  Nachfolgers, sein `engine.stop()` spülte den vorgelegten Titel aus der
  Queue, „Rest 0,0 s" statt 45 s → kein Skip, B startete 43 s zu spät.
  Fix (`STOP`-Fall): Rest-Audio aus `start + (cue_out − cue_in)` statt aus
  dem Zeilenende, STOP lässt die Queue in Ruhe, wenn ein Nachfolger
  vorgelegt ist, der Vorgänger wird beim Vorlegen gemerkt; Vorlauf
  BUFFER + 5 s (Datei-Kopie in den Cache dauert ~2 s) — `b09cdba`.  Dazu
  misst der Playout das Rest-Audio des Vorgängers jetzt in Liquidsoap
  (Telnet `scheduled.remaining`, cue-basiert) statt es aus der Zeile zu
  rechnen — ein verspätet gestarteter Titel hat mehr Rest als die Zeile
  sagt; der gerechnete Wert bleibt Rückfall — `7618c4e`.  Dritte Probe
  22:12–22:31: die Sendungsgrenze selbst stimmte (Liquidsoap blendete A's
  Titel am gekappten Cue-Ende über 1 s aus, B startete pünktlich), doch die
  Messung meldete den Rest des bereits gezogenen NEUEN Titels (162,8 s) →
  Skip traf B's ersten Titel, Stille und Folgeskips.  `scheduled.remaining`
  liefert jetzt `<rid> <sekunden>`; gehört die RID dem vorgelegten Titel,
  ist die Übergabe schon passiert und es wird nicht geskippt — `aae5b4c`.

- **Show-Shift: zweite Live-Probe 2026-09-27 12:26–12:56 — Sichtbarkeit
  bestätigt, Punkt 5 der Arbeitsreihenfolge abgeschlossen** — Gleiches
  Szenario wie um 11:20.  Task griff 12:19:33: B trägt
  `delayed_start_from = 12:36:00`, `modified_instance = false`; Filler
  erneut sekundengenau (179+26+5 s), Outro gepinnt.  Sichtbarkeit, die in
  der ersten Probe fehlte: On-Air-Today-Widget listet B 12:41:58–12:56:00,
  Kalender-Feed 200 mit A (12:26–12:41:59) und B, und um 12:43:31 melden
  `now-playing-data` und `/api/live-info` „RT-Probe B" mit „Sweetlove" als
  laufende Sendung/Titel; Playout-Start 12:41:58,055.  Testshows nach
  Sendungsende entfernt.  Werkzeug `C:/Temp/optd/shift_rehearsal.py`
  (setup|status|cleanup) bleibt für künftige Proben.

- **Show-Shift: Kalender-Feed 500 durch Mikrosekunden im verlängerten
  A-Ende (2026-09-27, zweiter Fund der Live-Probe, `a842747`)** — Der Shift schrieb
  `cc_show_instances.ends` von Show A als `MAX(cc_schedule.ends)` samt
  Mikrosekunden (…:58.186074).  `Show::getFullCalendarEvents` parst
  Instanzzeiten mit `createFromFormat('Y-m-d H:i:s')` → `false` →
  „Call to a member function setTimezone() on false" → HTTP 500 für den
  gesamten sichtbaren Kalenderbereich, solange eine solche Instanz darin
  liegt.  Genau das zeigte der Kalender während der ersten Probe (0 Events).
  Fix: Inhaltsende auf ganze Sekunden AUFgerundet (As letzter Titel bleibt
  innerhalb der Instanz; B startet auf derselben ganzen Sekunde).
  Kalender-Feed nach dem Fix live geprüft: 200, A 12:26–12:41:59 und die
  verschobene B 12:41:58–12:56:00 beide sichtbar.

- **Show-Shift: verschobene Sendungen sind wieder sichtbar — Marker
  delayed_start_from statt modified_instance (2026-09-27, Operator-Go,
  Migration 0058, `dc51f15`)** — Der Juni-Shift markierte verschobene Instanzen mit
  `modified_instance = true`, Upstreams „Folge gelöscht"-Flag, das jede
  Was-läuft-Abfrage (Dashboard, Live-Info, Widgets, Kalender, Showbuilder,
  Überlappungsprüfung) herausfiltert.  Neue Spalte
  `cc_show_instances.delayed_start_from` (TIMESTAMP NULL) = der Slot-Start,
  von dem die Folge weggerückt wurde.  SHIFT setzt nur diesen Marker;
  CLEARING behält zusätzlich `modified_instance = true` (ein geleerter,
  nie sendender Slot IST eine gelöschte Folge — und zwei gleichzeitige
  „aktuelle" Sendungen werden vermieden).  Trigger filtern
  `delayed_start_from IS NULL` (Idempotenz) und `modified_instance =
  false`; die Nachfolger-Suche überspringt gelöschte Folgen (vorher
  konnte eine gelöschte Folge als „nächste Show" gelten).
  `ShowService::getInstance()` findet eine verschobene Folge zusätzlich
  über `delayed_start_from`, damit das Bearbeiten der Serie kein Duplikat
  zur Serienzeit anlegt.  Handbuch DELAYED_START EN/DE/FR/ES (dabei die
  falsche Aussage korrigiert, Kalender-Ziehen setze `modified_instance`
  — `CalendarService::moveShow` tut das nicht).  Zweite Live-Probe: siehe
  Folgeeintrag.

- **Show-Shift Live-Probe 2026-09-27 11:20–11:50 — Basis-Shift + Filler auf
  Sendung bestätigt, ein Design-Fehler aufgedeckt** — Zwei Testshows im
  freien Fenster (A 10 min mit 15:58 Inhalt, B 20 min angehakt mit
  Outro-Playlist).  Der Task griff um 11:13:33, sieben Minuten vor A: B auf
  As Inhaltsende 11:35:58 gerückt, zwei Schluss-Titel entfernt, 210-s-Lücke
  mit drei Fillern (179+26+5 s) SEKUNDENGENAU gefüllt, Outro ans Slot-Ende
  gepinnt.  Playout: A lief bis 11:35:58 ungekürzt (nichts um 11:30), B
  startete 11:35:58,064, Filler 11:45:35/11:48:33/11:48:59, Outro 11:49:05
  + 11:49:55, Ende 11:50:00,060 — jeder Zeitstempel auf <200 ms am Plan.
  Filler-Zeilen tragen jetzt `playout_status = 1` (im Slot; vorher 0 =
  „überbucht"-Marker).  **AUFGEDECKT:** der Juni-Shift setzt
  `cc_show_instances.modified_instance = true` als „verschoben"-Marker —
  im Upstream bedeutet dieses Flag „Instanz gelöscht" (ShowInstance::delete).
  Folge, live beobachtet: Die verschobene Show ist für Dashboard-Header,
  Live-Info, Now-Playing-Widgets, Kalender (`Show::getShows`), Showbuilder
  und die Überlappungsprüfung UNSICHTBAR, während das Playout sie spielt.
  Fix = eigener Marker (Migration 0058, `delayed_start_applied`) statt des
  Lösch-Flags; wartet auf Operator-Go.  Testshows wieder entfernt.

- **Track History: `?exclude_short=` / `?min_seconds=` wirken wieder
  (2026-09-18, Nebenfund bei W4.1)** — Das Widget-JS baute seine
  Nachlade-URL aus Datum, Zeit, Seitengröße und Zeitzone und ließ die
  beiden Filter-Parameter weg.  Da die Liste IMMER per JS geholt wird,
  hatten die dokumentierten Overrides faktisch keine Wirkung — es galt
  stumm die Operator-Voreinstellung.  Die Parameter der Seiten-URL
  werden jetzt an jeden Abruf durchgereicht.

- **Kontextmenüs wieder da — Kalender-Slots und Library-Rechtsklick
  (2026-09-18, Operator-Fund, `b9a7e7a`)** — Das vendored contextMenu-Plugin (2012)
  ruft zweimal `.andSelf()`, das jQuery 3 entfernt hat; bis zum
  Migrate-Aus (5b, 17.09.) polierte das Netz den Alias drüber.  Seitdem
  starb JEDES Kontextmenü still im `update()` des Plugins — Kalender
  (Linksklick auf Show-Slots) wie Library (Rechtsklick: Preview/Delete/
  Edit/…).  Fix: `.andSelf()` → `.addBack()` (Alias seit jQuery 1.8).
  Der Fall war der 5b-Verifikation entgangen: Seiten luden fehlerfrei,
  Menüs wurden nicht geklickt — und die Automations-Klicks des
  Browser-Werkzeugs erreichen Hintergrund-Tabs unzuverlässig, weshalb
  das Symptom gestern wie eine Test-Eigenheit aussah.  Begleitender
  Sweep aller vendored Plugins nach weiteren entfernten jQuery-APIs:
  `$.browser`-Nutzer (blockUI, FixedColumns/Header, timepicker) deckt
  der seitenweite jquery-browser-shim ab, das `.live()` in
  preferences.js liegt in einem Kommentarblock, das in
  plupload.queue.min.js in einem nie betretenen rename-Zweig.  Live
  verifiziert: Kalender-Menü öffnet und bleibt offen („View"),
  Library-Menü zeigt Preview/Delete/Edit/Publish/Download.

- **Widgets: parameterloser /embed/player spielt wieder (2026-09-18,
  Punkt-12-Verifikation, `cd5ad1d`)** — Ohne `?stream=` blieb der
  Player-Modus leer und das Template renderte `this.settings.url = ;`
  (SyntaxError, tote Player-Hülle).  `stream` defaultet jetzt auf
  `auto` (derselbe Modus wie der generierte Embed-Code der Settings-
  Seite).  Begleitender Widget-Sweep: alle 15 Embed-Endpoints 200 ohne
  PHP-Fehler, alle Assets auflösbar, die vier JS-schweren Widgets ohne
  Konsolen-Fehler.

- **Logging: 530-MB/Tag-Warnungsflut gestoppt, eine Log-Senke, nächtlicher
  Log-Hausmeister (2026-09-18, Operator-Auftrag LOGGING, `8677c47`)** — Befund der
  Inventur: 2 GB im Log-Ordner, ~99 % Liquidsoap, doppelt geschrieben
  (eigene Datei + NSSM-stdout).  Seit 16.09. flutete der 24/7-Recorder
  beide Senken: `rec247_reopen()` läuft pro Frame und rief zweimal das
  in Liquidsoap 2.4 deprecatete `gettimeofday()` auf — je Aufruf eine
  WARNING-Zeile, 53 × 10-MB-Scheiben allein am 17.09.  Fixes: (1)
  `gettimeofday()` → `time()` im Generator (Test angepasst, 81 grün);
  (2) eine Senke — `settings.log.file.set(false)` im Template, stdout +
  NSSM-Rotation (10 MB) bleibt; der Pfad bleibt gerendert, damit eine
  Debug-Session den Schalter nur zurückdrehen muss; Operator-Hinweise
  (Preflight, Scheduler, Handbuch LOCAL_MACHINE + WEBSTREAMS ×4) zeigen
  auf die neueste stdout-Scheibe; (3) `scripts/log-janitor.ps1` +
  Task RASTATIME-LogJanitor (täglich 03:50, SYSTEM): rotierte Scheiben
  älter 7 Tage und unrotierte Singles über 50 MB wandern in
  `logs/archive/logs-YYYY-MM.zip` (gesperrte Dateien werden still
  übersprungen), Archive älter ~6 Monate gelöscht.  Sofort-Aufräumung:
  103 Dateien / ~1 GB → 6,2-MB-Archiv (Faktor ~160 — die Flut ist
  repetitiv).  Verbleibt: das gesperrte 1-GB-`liquidsoap.log`, das der
  Hausmeister nach dem nächsten PLAYOUT/LIQUIDSOAP-Neustart einsammelt.
  Restliche Schreiber sind Rundungsfehler (Apache access 0,3 MB/Tag,
  legacy 1 MB gesamt, Postgres 3 MB gesamt, Icecast 0).  **Wirksam nach
  PLAYOUT- und LIQUIDSOAP-Neustart** (regeneriert rastatime.liq); bis
  dahin flutet die Warnung weiter.

- **Audio-Vorschau: geplante Line-In-Slots erscheinen als Live-Eingang
  statt als kaputter Eintrag (2026-09-17, vermerkte Feature-Lücke,
  Operator-Go, `c65d0ca`)** — Der Popup-Player baute aus einem Line-In-Slot eine
  Zeile mit leerer Quelle: Klick lud `null` ins Audio-Element, und die
  Auto-Weiter-Kette blieb an der Zeile hängen.  Jetzt trägt die Zeile
  die Markierung „[live input]" (gedimmt, kursiv), die Infozeile erklärt
  „live input, no browser preview", ins Audio-Element wird nichts
  geladen, und Weiter/Zurück sowie das automatische Weiterschalten
  überspringen die Zeile.  Server unverändert (Typ 2 + leere Quelle
  waren schon da).  Live verifiziert an Instanz 1976 („Tascam 1-2").
  Handbuch LINE_IN §4 EN/DE/FR/ES.  Echtes Reinhören in den Eingang
  bräuchte einen eigenen Vorschau-Feeder — als 💡 im BACKLOG.

- **jQuery-UI-1.13-Politur: sichtbarer Dialog-Schließen-Knopf, dunkler
  Datepicker, blaue Ränder weg (2026-09-17, `707538d`)** — Der 1.13-Dialog lässt den
  Schließen-Knopf auf diesem Stack als nacktes `<button>` ohne
  Icon-Markup zurück (heller leerer Kasten) → direkt gestylt: dunkler
  runder Knopf mit weißem ✕, für jeden Dialog.  Der Datepicker war der
  letzte redmond-blaue Rest (die Juni-Umfärbung ließ die Tageszellen
  bewusst aus): dunkles Panel, dunkle Zellen, Auswahl in Brand-Orange,
  Heute in Bernstein.  `.ui-widget-content`-Rand entblaut.  Live
  verifiziert (Probe-Dialog + Add-Show-Datepicker).  Nicht reproduzierbar
  und geparkt: „Scheduled-Tracks-Dialog zu hoch" und „Add/Edit-Show zu
  hell" — beide Notizen stammen von vor dem dunklen Dialog-Theme vom
  31.08.

- **Backup Stufe 2: „Include media library“ kam nie bei der API an
  (2026-09-17, Operator-Befund beim Stufe-2-Test, `3a31f5b`)** — Die Seite schickte
  das Häkchen mit, aber die PHP-Proxy-Action `backup-folder` reichte nur
  den Ordner weiter; `local_backup_include_media` wurde nie gespeichert,
  der Lauf schrieb nur das ZIP (und die Checkbox sprang nach dem
  Speichern zurück).  Proxy reicht `include_media` jetzt durch; neue
  Endpoint-Tests decken den Schalter ab (14 Backup-Tests grün).  PHP
  live (kein OpCache).

- **Handbuch: das Import-Ordner-Kapitel beschrieb einen nie gebauten Ablauf
  (2026-09-17, `46c0ce3`)** — LOCAL_MACHINE §5 (EN/DE/FR/ES) erzählte von Staging-
  und `.failed`-Ordnern mit `.err`-Sidecars, rekursiven Unterordnern mit
  Album-Zuordnung und einem `LocalImportJob` im Worker-Dienst — nichts
  davon existiert.  Abschnitte und Fehlersuche neu geschrieben nach dem
  tatsächlichen Verhalten: `LocalImportScanTask` im PHP-Task-Manager
  (reitet auf Web-Anfragen, alle 300 s), nur Dateien direkt im Ordner,
  Ruhe-Prüfung 60 s, Verschieben nach organize, Löschen bei Fehlschlag,
  Besitz Scan-Now-Operator bzw. erster Admin.

- **Import-Ordner: halb geschriebene Dateien werden nicht mehr importiert
  (2026-09-17, Operator-Go nach der Netz-/FTP-Quellen-Evaluierung,
  `67db437`)** —
  Der 5-Minuten-Scan importierte, was gerade da war; eine Datei mitten
  in einer langsamen Kopie oder einem FTP-Upload wäre abgeschnitten
  verschoben und bei einem Fehlschlag samt Quelle GELÖSCHT worden.
  Ruhe-Prüfung in `LocalImportScanTask::scanOnce`: importiert wird nur,
  wessen mtime älter als 60 s ist (`QUIET_SECONDS`); jüngere Dateien
  zählt die Statuszeile als „settling" und der nächste Durchlauf nimmt
  sie mit.  Gilt auch für „Scan Now".  Handbuch LOCAL_MACHINE §5
  EN/DE/FR/ES, ARCHITECTURE §23.12-Hinweis.  PHP live (kein OpCache).

- **Einstellungs-Neustart: ein erfolgreicher Neustart hielt die nächste
  Änderung 30 Minuten zurück (2026-09-16, `4edc6ec`)** — Live: Ordner der 24/7-Aufnahme
  um 16:53 geändert → sofort übernommen; Bitrate 192 → 128 um 16:59:45
  gespeichert → erst um 17:24:00 übernommen.  Die 30-Minuten-Sperre in
  `_maybe_settings_restart()` (gedacht für fehlgeschlagene Versuche) zählte
  ab jedem Versuch, auch dem erfolgreichen.  Nach einem erfolgreichen
  Neustart wird der Zeitstempel jetzt gelöscht; Test
  `test_a_successful_restart_does_not_hold_the_next_change`.  Bitrate der
  Stundendateien per ffprobe bestätigt: `17-00.mp3` 192 kbit/s bis 17:24:01,
  `17-00.2.mp3` 128 kbit/s danach.  Aktiv nach PLAYOUT-Neustart.

- **Podcast-Episoden seit der Migration leer — PHP ohne CA-Bundle
  (2026-09-16, Doku + Maschinen-Konfiguration, `98dbded`)** — Befund beim Podcast-Test
  des Operators auf der neuen Bibliothekswurzel: Doppelklick auf einen
  Podcast → Lade-Symbol dreht endlos, DataTables meldet „Requested unknown
  parameter 'guid' for row 0".  Ursache: `/rest/podcast/<id>/episodes`
  liefert `[]`, weil SimplePie den RSS-Feed nicht lesen kann — PHP unter
  Windows bringt kein CA-Bundle mit (`cURL error 60: unable to get local
  issuer certificate`); letzter erfolgreicher Episoden-Import war der
  17.06.2026, also vor der Migration.  Mit `curl.cainfo` und
  `openssl.cafile` auf ein Bundle (`C:\\Tools\\PHP\\cacert.pem`, certifi
  oder curl.se) liefert der Feed 20 Episoden (Probe mit dem Apache-PHP).
  Kein Code-Fix; Doku INSTALL_APACHE §3.1, INSTALL §5.7 + Checkliste,
  MIGRATION §5.2.  Aktiv nach php.ini-Änderung + APACHE-Neustart.

- **24/7-Aufnahme: ein Neustart innerhalb der Stunde überschrieb die
  laufende Stundendatei (2026-09-16, `bfa216e`)** — Beim ersten automatischen
  Einstellungs-Neustart um 10:32 öffnete `recording_hourly` die Datei
  `10-00.mp3` neu und kürzte sie auf null; 10:00–10:32 waren weg (Teststunde).
  Erster Versuch `append=true` (`bfa216e`) wirkte nicht: der ffmpeg-Muxer
  kürzt die Datei trotzdem (Replikat `C:/Temp/optd/append_probe.py`, zweiter
  Lauf 10:46 → 10:32–10:46 erneut weg), ein nativer `%mp3`-Encoder fehlt dem
  Build.  Lösung: `rec247_path()` öffnet nie eine vorhandene Stundendatei,
  sondern schreibt in `<Stunde>-00.2.<ext>`, `.3.` … weiter (Replikat: drei
  Läufe → drei Teile, nichts gekürzt); das Cue-Sidecar bekommt `parts`
  (Datei, Erstellzeit, Offset je Teil), `audio_start` ist der erste Teil.
  Tests `test_liquidsoap_config.py`, `test_cue_writer.py` (`3cb5e33`).  Aktiv nach
  PLAYOUT-Neustart (der das geänderte Skript selbst übernimmt, siehe „Added").
  Live bestätigt 2026-09-16 12:37: PLAYOUT-Start 12:37:30 → Skript geändert →
  ruhiger Moment → LIQUIDSOAP wieder oben 12:37:34; `12-00.mp3` (12:00:00,
  54 MB ≈ 37,5 min) blieb unangetastet, `12-00.2.mp3` ab 12:37:32, Rotation
  13:00:00 normal.

### Security

- **CSRF-Prüfung gehärtet, wirkungslose Token-Rotation entfernt (2026-09-10,
  Arbeitsreihenfolge Punkt 3, Operator-Go „kleine Form", `7f51156`)** — Befund beim
  Lesen: das ACL-Plugin würfelte bei jedem fehlgeschlagenen REST-CSRF-Check
  einen neuen Session-Token, aber `PageLayoutInitPlugin::_initCsrfNamespace()`
  schließt die Session in `routeShutdown` schreibend, bevor der `preDispatch`-
  Hook läuft — die Rotation landete nur im Speicher des abgebrochenen Requests
  und persistierte nie.  Der im BACKLOG beschriebene Effekt („ein Fehlschlag
  vergiftet alle offenen Tabs bis zum Reload") existierte also nicht; live
  bewiesen (Brave, eingeloggte Sitzung, `PUT /rest/media/999999999`): zwei
  falsche Tokens → 401, danach der echte Token → der Request erreicht den
  Controller.  Änderungen: (1) Rotation entfernt; die 401-Warnung nennt jetzt
  Methode, Pfad, `Origin`, `Sec-Fetch-Site` und ob der Token fehlte oder
  falsch war (Sec-Fetch-Header senden Browser nur an HTTPS/localhost, im
  Studio-LAN über HTTP bleibt das Feld leer, der Origin genügt).  (2)
  `SecurityHelper::verifyCSRFToken` vergleicht mit `hash_equals` und lehnt
  fehlende, leere oder nicht-string Tokens auf beiden Seiten ab — das alte
  `==` hätte `null == null` durchgewinkt (Session ohne Token + Request ohne
  Token).  (3) `PluploadController::uploadAction` nutzt dieselbe Prüfung statt
  eines eigenen `==`.  Live nach dem Patch: falsch, fehlend, numerisch → 401,
  echter Token → durch.  Nebenbefund, separat im BACKLOG: `PUT /rest/media/<id>`
  mit nicht existierender ID antwortet 500 statt 404 (PHP-`Error` aus
  `CcFiles::updateFromArray`, vom `catch (Exception)` nicht gefangen).  Kein
  Neustart nötig (PHP ohne OpCache, sofort live).

### Removed

- **jQuery-Migrate-Netz + Legacy-JS-Assets entfernt — der ?jq3-Schalter ist
  Geschichte (2026-09-17, Bewährungs-Signal des Operators nach drei ruhigen
  Monaten auf dem jQuery-3-Standard, `3d02d50`)** — Raus: jquery-migrate 3.5.2,
  jQuery 1.8.3, jQuery UI 1.8.24 (+ totes 1.8.18-Custom), redmond-1.8-Theme
  (images/ bleibt — zwei Stylesheets nutzen die Icon-Sprites), DataTables-
  1.9-Kern, 2012er ColVis/ColReorder samt css/datatables-Baum, 16
  assets.json-Einträge und die gesamte Flag-Logik.  Vorher behoben: das
  Artwork-Drag-and-drop der Library nutzte das in jQuery 3 entfernte
  `$.event.props` (ohne Migrate wäre library.js komplett gebrochen) —
  jetzt `event.originalEvent.dataTransfer`.  Drei Seiten, die den
  1.9-Kern noch direkt luden (Upload, Tracktypes, Users), laden 1.13.
  Der `rt-jq3`-Body-Marker bleibt fest (CSS/Tabellen-Code hängen daran).
  Live verifiziert: Showbuilder, Kalender, Users, Upload, Tracktypes ohne
  Migrate und ohne Konsolen-Fehler.

- **FullCalendar-1.5-Fork entfernt — FC6 ist die einzige Kalender-Engine
  (2026-09-17, Bewährungs-Signal; FC6 Standard seit 2026-06-01, `ce36765`)** — Raus:
  der handgepatchte 2012er Fork (`js/fullcalendar/` samt Zeitzonen-Patches),
  `css/fullcalendar.css`, der `?fc6`-Rückfall, der FC1.5-Zweig in
  `createFullCalendar()` (jetzt lauter Wächter) und die fünf FC1.5-
  Callbacks in full-calendar-functions.js; dayClick/windowResize/
  addQtipsToIcons bleiben (FC6 ruft sie direkt).  Kalender live
  verifiziert (31 Events, FC6-Toolbar, keine Fehler).  Die zurückgestellte
  Screenshot-Aktualisierung des Handbuchs entfällt: das Kalender-Kapitel
  enthält keine Screenshots.

- **Scheduler-Poll-Rückfall des Webstream-Wächters entfernt (2026-09-15,
  Operator-Go nach der ruhigen Woche seit 2026-09-09, `de822e4`)** — Der Wächter läuft seit
  2026-09-07 als Frame-Zähler in Liquidsoap; der Telnet-Poll von 2026-09-06
  blieb als Rückfall (`RASTATIME_WEBSTREAM_WATCHDOG=scheduler`) und als
  Notnagel für eine ältere geladene .liq.  Kriterien geprüft: kein `upstream
  stalled`; ein regulärer Reap (14.09. 08:15 direkt nach dem Slot-Ende, der
  Eingang hatte sich selbst neu verbunden); 15 Webstream-Starts, 14 in ≤ 3 s
  dekodiert, einer in 8 s (11.09. 17:06: erster Verbindungsversuch zur Cloud
  fehlgeschlagen, zweiter 3 s vor Slot-Beginn, pünktlich auf Sendung);
  Nacht-Neustarts am 12./13.09. sauber, sonst wegen Instanzalter korrekt
  ausgelassen.  Entfernt: die Maschinen-Einstellung und
  `_webstream_watchdog_mode` in `__main__`; im Scheduler der Modus-Schalter,
  der Timer-Poll (`_start/_stop/_arm_webstream_watchdog`,
  `_webstream_watchdog_tick`, `_reconnect_stalled_webstream`) und die Probe
  „hat die geladene .liq den internen Wächter"
  (`_liquidsoap_has_internal_watchdog`,
  `LiquidsoapPlayoutEngine.webstream_watchdog_present`); im Renderer der
  Parameter `webstream_watchdog_in_liquidsoap` samt Reaper-only-Stub — der
  Standard-Render bleibt byte-gleich (Vorher/Nachher-Vergleich).  Die
  Telnet-Kommandos `webstream.ready` und `webstream.watchdog` bleiben als
  Diagnose.  Tests: `test_scheduler_webstream_watchdog.py` gelöscht,
  `test_webstream_watchdog_in_liquidsoap.py` auf Regressionsschutz umgebaut.
  Handbuch WEBSTREAMS EN/DE/FR/ES, ARCHITECTURE 0.32 (§23.31).  Wirksam nach
  PLAYOUT-Neustart, LIQUIDSOAP unberührt.

- **Legacy-mpv-Engine gelöscht — Liquidsoap ist die einzige Playout-Engine
  (2026-09-10, Arbeitsreihenfolge Punkt 15, Operator-Go, `2590cf2`)** — Seit dem
  Phase-D-Cutover (2026-05-28) lief PLAYOUT ausschließlich mit
  `streaming_handled_externally=True`; der mpv-Pfad (libmpv-Monitor plus
  drei FfmpegStreamer-Subprozesse für die Icecast-Ausgänge, Icecast-Admin-
  `killsource`, Hot-Reload der Stream-Ausgänge, Listener-Zugangsdaten für
  das /main-/show-Relais) war seit Monaten toter Code mit einem `if` an
  jedem Scheduler-Einstieg (~1.600 Zeilen).  Gelöscht: `engine/mpv_engine.py`,
  `engine/ffmpeg_streamer.py`, `tests/engine/test_ffmpeg_streamer_gain.py`;
  in `playout_scheduler.py` alle `streaming_handled_externally`-Zweige,
  `_start_streamers`/`_stop_streamers`, `_reload_stream_outputs_if_changed`,
  `_kick_icecast_source`, `_build_icecast_input_url`,
  `set_listener_credentials` (Konstruktor ohne `stream_outputs`,
  `read_stream_outputs`, `streaming_handled_externally`); in
  `source_switcher.py` der Icecast-`listmounts`-Poller und der
  `engine_kind`-Parameter von `start_listener`; in `__main__.py` die
  Engine-Auswahl samt Deprecation-Warnung und
  `_read_internal_listener_credentials` (der Schlüssel
  `stream.internal_listener` in libretime.conf bleibt für die PHP-Seite).
  `ffmpeg_linein_capture.py` bleibt — es ist seit Option B (2026-09-03)
  der aktive MME-Feeder-Pfad jedes geplanten Line-Ins.  Verhalten:
  `RASTATIME_PLAYOUT_ENGINE` wird weiter gelesen, akzeptiert aber nur
  `liquidsoap` (fehlend = liquidsoap; alles andere bricht den Start mit
  CRITICAL ab, `_require_liquidsoap_engine`); `RASTATIME_MPV_PATH` und
  `RASTATIME_MPV_LOG_LEVEL` sind wirkungslos.  Der DJ-Kick („Cancel Show",
  `/disconnect-source`, gelöschte Show bei aktiver Show-Quelle) geht jetzt
  per Telnet an den Harbor in Liquidsoap (`master_dj.stop`/`show_dj.stop`;
  `LiquidsoapPlayoutEngine.dj_kick`, `LiquidsoapTelnetClient.harbor_stop`)
  — der bisherige Icecast-`killsource` konnte einen Harbor-DJ gar nicht
  erreichen.  Zwei mpv-förmige Restpfade wurden dabei korrigiert: der
  Neustart-Callback der Line-In-Capture (Watchdog) hätte die Listen-URL
  per `engine.play` in die Request-Queue geschoben und bewaffnet jetzt den
  `input.http`-Begleiter (`linein_start_http` + Gate); der Webstream-Resume
  nach DJ-Off tat dasselbe und ruft jetzt `webstream_start` + Gate +
  Wächter (in der .liq antwortet `webstream.start` bei gleicher URL
  „already started", eine laufende Quelle bleibt unangetastet).  Tests: elf
  Legacy-Tests entfernt, Fixtures ohne Engine-Flag; neu
  `test_main_engine_env.py`, `test_scheduler_dj_kick.py`, `dj_kick`/
  `harbor_stop` in den Engine-Tests, Capture-Restart- und Webstream-
  Resume-Tests (Backend inkl. Engine-Tests 563 bestanden / 2 übersprungen,
  Unit 105).  Doku: Handbuch SETTINGS §6 (nur noch Liquidsoap), LINE_IN,
  WEBSTREAMS, RECORD_PER_HOUR, RECORD_PER_SHOW in EN/DE/FR/ES; README,
  CLEANUP_INVENTORY, Operator-Doku, Systemstatus-Text, .liq-Template-
  Kommentare.  Aktiv nach PLAYOUT-Neustart; rastatime.liq wird dabei nur
  wegen geänderter Kommentare neu gerendert (ein LIQUIDSOAP-Neustart ist
  dafür nicht nötig, der nächste geplante Neustart übernimmt sie).

### Added

- **DJ-Logins: die Oberfläche wird zur Wahrheit (2026-09-10, Operator-Go
  Option 2, `fec9df9`)** — Bisher akzeptierten die Liquidsoap-Harbors nur Benutzer
  `source` mit den statischen Passwörtern aus `stream.harbor` in
  libretime.conf; die Master-Source-Zugangsdaten aus Settings → Streams
  und die per-Show-Logins wurden nicht benutzt, und die Settings-Seite
  zeigte Port 8000 statt des Harbor-Ports 8001 (BUTT-Login schlug fehl).
  Jetzt: (1) Beide Harbors bekommen `auth=rastatime_dj_auth(...)`
  (`_render_dj_auth_function`): jeder Login-Versuch wird per POST an
  PLAYOUTs Listener `/dj-auth` gemeldet; `ok` akzeptiert, `denied` lehnt
  ab, alles andere (PLAYOUT nicht erreichbar — `http.post` wirft dann
  nicht, sondern liefert einen leeren Body — oder `error`) fällt auf die
  statische Prüfung `source` + Harbor-Passwort zurück.  (2) PLAYOUT
  (`dj_auth.DjAuthenticator`) fragt die bestehende Legacy-Prüfung
  `check-live-stream-auth` (POST, `general.public_url` bzw.
  `RASTATIME_DJ_AUTH_WEB_URL`): Master = Settings → Streams → Master
  Source; Show = die gerade laufende Show, registrierter Host oder
  Custom-Login aus „Live Stream Input"; keine laufende Show → abgelehnt.
  200 + `icecast-auth-user: 1` = ok, 401 = denied, sonst error.
  Passwörter erscheinen in keinem Log.  (3) Harbor-Ports und -Mounts
  kommen aus `stream.inputs.main/show` in libretime.conf — genau die
  readonly-Felder von Settings → Streams (`_read_harbor_inputs`; ein
  Icecast-Port wird mit Warnung durch 8001 ersetzt); libretime.conf auf
  8001/main und 8001/show gesetzt, `libretime.conf.example` dokumentiert.
  Replikat: akzeptiert/abgelehnt/Fallback in vier Runden; Legacy-Endpunkt
  live mit falschen Daten geprüft (401 → denied).  Tests
  `test_harbor_dj_auth.py` (inkl. `--check`), `test_dj_auth.py`,
  `test_main_harbor_inputs.py`.  Handbuch STREAMS EN/DE/FR/ES.  Aktiv
  nach PLAYOUT- und LIQUIDSOAP-Neustart.
- **Geplanter LIQUIDSOAP-Neustart für 24/7-Programm: an der Titelgrenze,
  Auslöser Intervall/Speicher, Icecast-Standby-Fallback ohne
  Hörer-Trennung (2026-09-09, Operator-Go a+b, `1362634`)** — Mit durchgehendem
  Programm fand der Nacht-Neustart nie einen ruhigen Moment und entfiel
  (Speicher wächst 150–180 MB/h, nach Tagen unkontrollierter Absturz).
  (1) Auslöser (`NightlyRestartPolicy.reason_due`): Fenster ab 04:00
  (`RASTATIME_LIQUIDSOAP_NIGHTLY_RESTART`), alle N Tage nach Prozessalter
  (`RASTATIME_LIQUIDSOAP_RESTART_EVERY_DAYS`, Standard 1, 0 = aus), weiche
  Speicher-Schwelle im Fenster (`RASTATIME_LIQUIDSOAP_RESTART_AT_MB`,
  Standard 1536), harte Schwelle jederzeit
  (`RASTATIME_LIQUIDSOAP_RESTART_HARD_MB`, Standard 3072); Prozessalter und
  Speicher je Scheduler-Zyklus per `liquidsoap_process_info`; Fehlversuche
  30 min gedrosselt.  (2) Ausführung: ruhiger Moment → sofort wie bisher;
  sonst führt `_on_file_start` den Neustart zwischen zwei Datei-Titeln aus
  (Webstream/Line-In auf einer Seite → nächste Grenze), Bleibt-oben-
  Prüfung dann asynchron.  (3) Standby-Fallback: PLAYOUT rendert
  `standby.liq` (`render_standby_liq`: gleiche Encoder, Mounts `-standby`,
  Stille oder `RASTATIME_STANDBY_AUDIO`-Loop, kein Telnet), Dienst
  RASTATIME-STANDBY (`config/nssm-install-standby.ps1`), `icecast.xml`
  mit `fallback-mount`/`fallback-override` für /rastatime, -aac, -ogg:
  Icecast schiebt die Hörer während des Neustarts auf den Standby-Mount
  und zurück, niemand wird getrennt.  Tests
  `test_planned_restart_triggers.py` (13), `test_standby_render.py` (4);
  Handbuch „Lokale Maschine" EN/DE/FR/ES; Architektur 0.26.  Aktiv:
  Standby-Dienst installieren, Icecast einmal neu starten (einmalige
  Trennung), PLAYOUT neu starten.  Nachtrag: PLAYOUT prüft bei jedem
  Render `icecast.xml` gegen die Stream-Outputs
  (`icecast_mounts_without_fallback`, `RASTATIME_ICECAST_CONFIG_PATH`) und
  warnt im Log vor öffentlichen Mounts ohne Standby-Fallback — die
  Standby-Seite folgt Umbenennungen von selbst, Icecasts Fallback-Blöcke
  nicht.

- **Liquidsoap-Prozesshygiene auf Windows: automatische Neustarts und
  Watchdogs (2026-09-05, Operator-Go, `1dbeb71`)** — Drei Ergänzungen
  aus der Untersuchung des Speicherlecks und des Geräteindex:
  1. **Boot-Fenster-Neustart:** Ändert PLAYOUTs Render die `rastatime.liq`
     innerhalb von 10 min nach dem Hochfahren, startet PLAYOUT
     RASTATIME-LIQUIDSOAP selbst neu (`nssm restart`, LocalSystem) —
     die Instanz vom Boot lief bisher mit der Datei vom Vortag
     (Boot-Race; am 2026-09-05 11:15 starb Instanz #1 an einem
     veralteten Geräteindex).  `RASTATIME_LIQUIDSOAP_BOOT_RESTART=0`
     schaltet ab.
  2. **Nächtlicher Neustart im ruhigen Fenster:** ab 04:00
     (`RASTATIME_LIQUIDSOAP_NIGHTLY_RESTART`, `HH:MM` oder `off`) startet
     der Scheduler LIQUIDSOAP einmal täglich neu — nur wenn nichts auf
     Sendung, nichts vorgewärmt und kein Titel in den nächsten 5 min;
     vorher Re-Render, danach Telnet-Warten und Gate-Reset.
     Schutznetz gegen das verbleibende `Unix.select`-Leck.
  3. **Preflight-Warnungen** im Dashboard-Banner:
     `liquidsoap_memory_high` (private Bytes über
     `RASTATIME_LIQUIDSOAP_MEMORY_WARN_MB`, Default 2048, Fehler ab dem
     Doppelten) und `main_output_session_missing` (kein Liquidsoap-
     Prozess älter als 90 s hält eine Core-Audio-Session auf dem
     gewählten Main-Output-Endpunkt; pycaw/comtypes im Playout-venv).
     Handbuch „Lokale Maschine" in vier Sprachen, Architektur 0.22 §23.27.

- **Nahtlose Eingangswechsel: Bus-Gates, Übergangsfunktionen,
  Vorwärmen — „Paket 2" (2026-09-04, Operator-Go, Leitlinie
  „Seamless-Mix")** — Nach Paket „Line-In-Latenz" blieben 2 s Stille am
  Slot-Anfang und 2 s verlorener Rest am Slot-Ende.  Beides adressiert:
  1. **Gates im Bus-Switch** (`webstream_live`, `linein_live`,
     `interactive.bool`, Default true): Pypo kann eine Quelle mit
     geschlossenem Gate verbinden und puffern (kein vorzeitiges
     Auf-Sendung-Gehen) und sie per `var.set` am Slot-Start öffnen
     bzw. am Slot-Ende schließen.
  2. **Übergangsfunktionen** (`switch(transitions=…)`): Wechsel
     zwischen Webstream-, Line-In- und Scheduled-Arm laufen über
     `bus_transition` — Crossfade D > 0: `fade.out(old, D)` +
     `fade.in(new, D)`; D = 0: **Ducking**, neue Quelle sofort voll
     (50-ms-Rampe, klickfrei und typgleich), alte blendet über 1 s
     darunter aus.  DJ-Arme bleiben sofort.  Isoliert verifiziert
     (zwei Sinus-Quellen, Gate per Telnet, Spektralanalyse der
     Aufnahme): beide Formen wirken am Umschaltpunkt, nicht erst nach
     `transition_length`.
  3. **Haus-Crossfade aus Settings → General**: `default_crossfade_duration`
     (cc_pref, per ORM beim Render gelesen) ist jetzt primäre Quelle für
     Queue-Crossfade, Bus-Übergänge und Drain; die Env-Var
     `RASTATIME_LIQUIDSOAP_CROSSFADE_SECONDS` ist nur noch Fallback.
     **Achtung:** Das Feld stand auf 0 — vor dem Neustart auf den
     gewünschten Wert setzen (Operator: 1 s).
  4. **Vorwärmen** (`PREPARE_LEAD_SECONDS` = 10): Prepare-Timer starten
     Capture + `linein_http` bzw. `webstream_start` bei geschlossenem
     Gate; am Slot-Start öffnet nur das Gate → Startlücke ~0.  Kein
     Vorwärmen, wenn ein Line-In auf Sendung ist (ein Capture), ein
     Webstream spielt (eine Quelle) oder die Zeile keinen Gerätenamen
     hat.  Verschwindet ein vorgewärmtes Item beim Refresh, wird es
     zurückgebaut.
  5. **Freigabe mit Drain**: Slot-Ende und Nachfolger schließen nur das
     Gate (der Bus blendet aus), Capture + Quelle werden erst nach
     Übergangslänge + 0,5 s gestoppt — Generation-Zähler verhindern,
     dass ein alter Drain eine neuere Quelle killt.  Startup öffnet
     beide Gates.
  Commits `eabf798`, `b92c08a`, `1a150a0`, `6820158`.  Manuals (LINE_IN,
  WEBSTREAMS, SETTINGS) in vier Sprachen; Architektur 0.21 / §23.26.
  **Live-Abnahme 2026-09-04 19:50–20:22** (sechs Shows: Line-In →
  Line-In gleiches Gerät → Jingles + BBC + Showteaser → Cloud-Stream →
  gleicher Cloud-Stream → Line-In; Crossfade 1 s), Ohr + Monitor, alle
  Übergänge vom Operator abgenommen: Line-In vorgewärmt **0,15 s**
  Startlücke (vorher 2 s), gleiches Gerät nahtlos, Line-In → Jingle mit
  hörbarem Nachlauf unter dem Jingle, BBC und Cloud-Stream sofort auf
  Sendung (vorher 5–9 s), Showteaser pünktlich mit BBC-Ausklang
  darunter, Slot-Ende mit Nachlauf.  Zwei Nachbesserungen daraus
  (`59c8e8f`, siehe Fixed): Vorwärmen bei Refresh im 10-s-Fenster, und
  gleicher Stream → gleicher Stream ohne Dip.  Die drei offenen
  Test-Themen wurden am 2026-09-05 untersucht (Ergebnisse im BACKLOG):
  der Cloud-Stream stallt in jedem Modus (Upstream, nicht das
  Vorwärmen); „Latency is too high" ist das Zeichen eines
  funktionierenden WASAPI-Ausgangs gegen `sync="cpu"`; „possible source
  leak" ist die Warnschwelle 50 bei 50–63 Quellen während Übergängen.
  Dabei gefunden: ein echtes Speicherleck von ~5 KB pro `Unix.select`
  (OCaml-4.14-Windows-Build, Duppy-Scheduler, savonet #1122) und die
  Instabilität des PortAudio-Geräteindex (Main Output lag nach dem
  Reboot auf der Realtek-Buchse) — beides mit Optionen im BACKLOG.

### Fixed

- **Main Output: Liquidsoap öffnet den Tascam-Ausgang nur noch einmal pro
  Prozess — keine Abstürze und keine stillen Fehlleitungen mehr nach einem
  Pufferleerlauf (2026-09-14, Operator-Go Variante B, `9b0aa3e`)** — Befund: der 2-s-Puffer
  vor `output.portaudio` lief durch Taktdrift (Tascam ≈ 50 ppm schneller als die
  Haupt-Uhr) alle 10–12 h leer; mit `fallible=true` stoppte der Ausgang dabei
  und öffnete das Gerät nach dem Nachfüllen neu.  PortAudio zählt die Geräte
  nur beim Prozessstart, der Audio-Endpunkt des DELL-Monitors kommt und geht
  mit dem Bildschirm.  War die Liste beim Wiederöffnen kürzer, beendete sich
  Liquidsoap („device ID out of range" → `Invalid_argument("option is None")`,
  Exit 2, NSSM-Neustart; 2026-09-07 21:44, 09-08 20:22, 09-09 16:36, 09-14
  03:51); war sie anders, öffnete der Ausgang ohne Fehler ein falsches Gerät
  (2026-09-10 21:38, Start nach dem Reboot mit kurzer Liste — Main-Output-
  Warnung rund 30 h bis zum Nacht-Neustart).  Jetzt: (1)
  `output.portaudio(fallible=false, …, mksafe(id="portaudio_safe",
  bus_for_portaudio))` — bei Leerlauf spielt Stille, der Ausgang stoppt nie und
  öffnet das Gerät nie neu; fehlt `mksafe`, verweigert Liquidsoap den Start
  („That source is fallible"; `--check` erkennt das nicht, deshalb der
  Render-Test `test_local_output_bridge.py`).  (2) Die Brücke ist
  `buffer.adaptative(id="portaudio_buffer", buffer=2.0, limit=1.001)`: eine
  Tempoanpassung von höchstens 0,1 % gleicht die Drift aus, die 2-s-Lücken am
  Tascam entfallen.  Die Funktion ist in 2.4.4 als experimentell markiert,
  deshalb schaltet die Maschinen-Einstellung
  `RASTATIME_LIQUIDSOAP_LOCAL_OUTPUT_ADAPTIVE=false` auf den festen `buffer()`
  zurück (weiter mit `mksafe`); PLAYOUT loggt die Wahl bei jedem Rendern.
  Laufzeitprobe `C:/Temp/optd/bridge_probe.py` (Realtek-Gerät, Stille,
  erzwungener Leerlauf): beide Brücken starten, laufen leer, der Ausgang stoppt
  nicht; ohne `mksafe` kein Start.  Handbuch LOCAL_MACHINE EN/DE/FR/ES,
  ARCHITECTURE 0.31 (§23.30).  Aktiv nach PLAYOUT- **und** LIQUIDSOAP-Neustart.

- **Playout History: `HistoryService::getSqlTypes()` bildet DATETIME jetzt auf
  `timestamp` ab (2026-09-10, Arbeitsreihenfolge Punkt 4, `cdc8f0b`)** — der bisherige
  Cast-String `datetime` existiert in PostgreSQL nicht (gegen die Datenbank
  geprüft: `SELECT NULL::datetime` scheitert, `::timestamp` nicht).  Latent,
  weil die einzigen DATETIME-Felder der Vorlagen (`starts`/`ends`) Pflicht-
  felder sind, die die Cast-Schleifen überspringen, und der Vorlagen-Editor
  keine neuen DATETIME-Felder anbietet — ein künftiges Feld hätte den
  History-Feed mit einem SQL-Fehler abgeschossen.  Einzeiler, sofort live.

- **REST `PUT /rest/media/<id>` mit unbekannter ID: 404 statt 500 (2026-09-10,
  Nebenbefund des CSRF-Live-Beweises, `7993bfe`)** — `CcFiles::updateFromArray()` warf für
  eine unbekannte ID zwar `LibreTimeFileNotFoundException`, markierte im
  `catch` aber `$file->setDbImportStatus()` auf `null` — ein PHP-`Error`, den
  das `catch (Exception)` in `MediaController::putAction` nicht fängt, also
  eine HTML-500-Seite.  Jetzt wird nur eine existierende Zeile als
  fehlgeschlagener Import markiert, die Ausnahme trägt die ID im Text, und
  der REST-Aufruf antwortet `404 ERROR: Media not found.` (live geprüft:
  PUT und DELETE auf ID 999999999).  Sofort live, kein Neustart.

- **Cue-Sheet: kein überzähliger „end"-Marker mehr bei überholtem STOP,
  Marker tragen die Item-Identität (2026-09-10, Operator-Go, `2b208a0`)** —
  `_on_stop` schrieb `cue_item_end` vor dem Ownership-Re-Check; gewann
  der Nachfolger das Rennen (bei jedem Datei→Datei-Übergang), landete
  der Marker ~30 ms hinter dessen `start` als „end" seines Typs.  Der
  Marker wird jetzt erst nach dem Re-Check geschrieben (ein überholter
  STOP schreibt nichts; der `start` des Nachfolgers impliziert das
  Ende), und `start`/`end` beider Seiten tragen `item` = Schedule-Row-ID
  (`CueWriter.item_end(kind, **meta)`), damit ein späterer Leser Paare
  bilden kann.  Tests `test_cue_marker_ownership.py`,
  `test_cue_writer.py`.  Aktiv nach PLAYOUT-Neustart.  **Nachbesserung
  (Testfolge 11:00, Übergang BBC → Teaser 11:16:08):** der Marker stand
  zunächst zwischen Re-Check und Reset; `CueWriter.item_end` liest dabei
  die 24/7-Konfiguration (DB-Roundtrip), und in dieses Fenster fiel der
  Bookkeeping-Wechsel des Nachfolgers, den der Reset dann löschte — beim
  nächsten Refresh „Catch-up" des laufenden Teasers (unhörbar dank der
  Same-URI-Idempotenz des Engines, aber 28 s falscher Zustand).  Jetzt:
  Re-Check, Reset, danach der Marker.
- **Webstream-Eingang: frische Quelle pro Slot statt Wiederverwendung
  (2026-09-08, Operator-Go „Plan A", `1eb8713`)** — Phase D am 2026-09-08 (drei
  Cloud-Slots, ein BBC-Slot): zwei Starts dekodierten erst nach 48 s und
  97 s, der BBC-Slot kam nie auf Sendung; danach hing jeder Start an der
  Produktionsinstanz über 90 s in „starting" oder „polling", ein Stop
  in „stopping", und eine BBC-Zombie-Verbindung blieb ohne gestarteten
  Zustand zurück (`ffmpeg_io.ml:121 Assertion failed`: der Verbindungs-
  Task lief erst beim zweiten Weckbyte doppelt).  Ursache: `input.http`
  verbindet über einen Duppy-Async-Task, dessen Weckbyte-Pipe auf dem
  Windows-Build unter normaler Last unzuverlässig ist — Replikate: ohne
  Last 12/12 Starts in 3,7 s; mit Icecast-Ausgängen oder dem 5-s-Telnet-
  Poll von PLAYOUT hingen in vier von fünf Läufen Starts 20–110 s, auch
  mit Warten auf „stopped" vor jedem Start.  Der ERSTE Start einer
  frischen Quelle war in 9/9 Zyklen schnell.  Fix: das Template rendert
  `webstream_raw = source.dynamic(id="webstream", …)`; `webstream.start`
  erzeugt einen neuen `input.http` (`webstream_in_N`, `start=true`) mit
  eigener 5-s-Bridge (`webstream_bridge_N`) und hängt ihn ein,
  `webstream.stop` stoppt und verwirft ihn (`source.fail()` dazwischen,
  der Switch fällt wie bisher durch); der interne Wächter erholt sich
  ebenfalls mit frischer Quelle.  Telnet-Vertrag für PLAYOUT unverändert
  (`webstream.url [<url>]`, `.start` idempotent bei gleicher URL, `.stop`,
  `.status`, `.ready`, `.watchdog`, `var.set webstream.gain`).  Nebeneffekt:
  keine veraltete Bridge mehr, der Rest des vorigen Streams bzw. der
  „Hacker" am Slot-Anfang (BACKLOG „falscher Stream ~5 s") entfällt.
  Kosten: ~1 Thread pro Slot bis zum Nacht-Neustart.  Ende-zu-Ende im
  produktionsnahen Replikat: Slot-Folge Cloud/BBC/Cloud 3,7 / 1,0 / 3,7 s,
  Stall-Server mit zwei Wächter-Erholungen über frische Quellen.  Tests
  angepasst (295 Backend, 105 Unit); Handbuch „Webstreams" EN/DE/FR/ES;
  Architektur 0.25.  Aktiv nach Neustart PLAYOUT → LIQUIDSOAP.
  **Nachtrag 22:40 — Reaper für verworfene Eingänge (`6a0fa8d`):** Live-Stall-Test
  22:20 (DEVA zweimal stromlos, ~30 s / ~55 s): Erholung über frische
  Quellen 6–7 s nach Rückkehr des DEVA (Stille 29 s / 58 s), aber die
  verworfenen `webstream_in_1/_2` pollten weiter, verbanden sich beim
  DEVA selbst wieder und hielten je eine Verbindung — `input.http`
  verliert ein Stop, solange es einen toten Server pollt (der Connect-
  Task überschreibt `Stopping` nach jedem Fehlversuch mit `Starting`).
  Ein zweites `start`+`stop` auf einer „connected" gemeldeten Quelle
  trennt sie sauber (live an beiden Zombies bestätigt).  Das Template
  merkt sich jetzt jede Quelle, deren Stop nicht griff
  (`webstream_zombies`), und der Frame-Zähler räumt sie beim ersten
  „connected" ab (`webstream_reap`, auch im Scheduler-Modus);
  `webstream.watchdog` zeigt `zombies=`/`reaped=`.  Replikat: drei
  Stalls, jede verworfene Quelle binnen 3 s abgeräumt.  Test
  `test_dropped_inputs_are_remembered_and_reaped`.

- **Nächtlicher LIQUIDSOAP-Neustart: Absturzschleife 04:02–08:21
  behoben (2026-09-07, `e66e675`)** — In beiden Nächten seit dem Feature
  (2026-09-06 und 2026-09-07) endete der 04:01-Neustart in einer
  NSSM-Absturzschleife bis zum manuellen Neustart am Morgen: Sendeweg
  und alle Icecast-Mounts über vier Stunden tot, Preflight meldete
  „keine Warnungen".  Ursache: PortAudio zählt seine Geräte nur beim
  Prozessstart; um 04:01 schlief das Studio-Display, sein HD-Audio-
  Endpunkt (`DELL U2419HC`) fehlte in allen vier Host-APIs, alle
  späteren Indizes waren verschoben.  PLAYOUTs veraltete Liste
  lieferte für den MME-Eintrag des Tascam „device ID out of range"
  (MME error 2), der Renderer fiel auf `device_id=18` zurück, und die
  frische Instanz öffnete unter 18 ein anderes Gerät („Invalid number
  of channels") und starb nach 2 s; `nssm restart` meldete Exit 1
  (Dienst „paused" = NSSM-Drossel), PLAYOUT versuchte es dreimal und
  schoss jede frische Instanz erneut ab.  Vier Maßnahmen:
  (1) `refresh_device_list()` — PortAudio wird vor jeder Auflösung
  neu initialisiert (`sounddevice._terminate/_initialize`), Namens-
  Treffer und Probe sehen die aktuelle Liste; (2) „per Name oder gar
  nicht": Boot-Fenster- und Nacht-Neustart werden übersprungen, wenn
  der Render den Main Output nur per Index adressieren kann
  (`RenderOutcome.main_output_mode`), die laufende Instanz spielt
  weiter; (3) `restart_liquidsoap_service(verify=)` — ein Exit ≠ 0
  wird per Telnet-`uptime` verifiziert (frische Instanz < 120 s) statt
  blind wiederholt, danach 10 s Bleibt-oben-Prüfung mit lautem Fehler;
  (4) neue Preflight-Warnung `liquidsoap_unavailable` (kein
  liquidsoap.exe oder auf jedem Scan eine neue junge PID =
  Absturzschleife) im Dashboard-Banner.  Tests
  `test_nightly_restart_hardening.py` (23) und
  `test_portaudio_refresh.py` (4); Handbuch „Lokale Maschine" in vier
  Sprachen; Architektur 0.23 (Addendum 2026-09-07 zu §23.27).  Aktiv
  nach dem nächsten PLAYOUT-Neustart.

- **Sentinel-Aufnahme nach separatem LIQUIDSOAP-Neustart gestoppt
  (2026-09-07, `0d3f097`)** — Die Betriebs-Reihenfolge „PLAYOUT dann
  LIQUIDSOAP" (und ein Crash + NSSM-Neustart) ließ die frische
  Liquidsoap-Instanz die Sentinel-Datei `_uninitialized.mp3` weiter
  aufnehmen, weil PLAYOUT seine einmalige Initialisierung schon gegen
  die vorherige Instanz erledigt hatte (live 2026-09-07 08:21, 7 MB in
  ~3 min).  `refresh()` liest jetzt bei jedem Poll die Liquidsoap-
  Uptime; ein Rückgang (neue Instanz) setzt das Init-Flag zurück und
  sendet `recording.stop` + Gate-Reset erneut.  Ergänzt den
  Startreihenfolge-Fix `578e950`.

- **Webstream-Wächter: Erholung nach stillem Upstream-Stall; Rücknahme
  der „Option 1"-Aufblähung (2026-09-06, Operator-Go, `405b200`)** — Der
  Live-Testlauf am 2026-09-06 legte die echte Ursache der Cloud-
  Aussetzer offen.  Der DEVA-Server ist gesund (eine Einzelverbindung
  liefert makellos, Listener-Limit 10, die elfte bekommt `503`), aber
  `input.http` erkennt einen Stall MITTEN im Stream nicht: nach „Buffer
  emptied" wird bis zum Slot-Ende kein Reconnect versucht, und die
  stehengelassene Zombie-Verbindung belegt einen der zehn DEVA-Plätze,
  bis nach ein paar toten Slots `503` kommt.  **Wächter:** Während ein
  Webstream sendet, pollt der Scheduler alle 2 s
  `source.is_ready(webstream)` (Telnet `webstream.ready`) und erzwingt
  nach zwei toten Abfragen, die auf eine lebende folgen, ein sauberes
  `webstream.stop` + `webstream.start`; frische Verbindung < 200 ms,
  der saubere Stop gibt den DEVA-Platz frei.  End-to-End gegen einen
  dauerhaft verstummenden Server bewiesen (zwei Stalls, zwei Erholungen
  in ~6 s statt tot).  **Zurückgenommen:** die Option-1-Aufblähung
  (Clock-Bridge 10 s/20 s → 5 s/10 s, Webstream-Vorlauf 20 s → 10 s) —
  eine fette Bridge überbrückt diese Stalls nicht und verdoppelte das
  Fenster, in dem am Slot-Anfang der Rest eines anderen Streams spielt;
  `timeout` 3 s / `poll` 0,5 s bleiben.  Die ffmpeg-`reconnect`-Optionen
  werden NICHT verwendet (hängen in einer Reconnect-Schleife).  Manual
  WEBSTREAMS in vier Sprachen, Architektur §23.27 Addendum.  Offen: Live-
  Abnahme 2026-09-07; „falscher Stream am Anfang" nur auf ~5 s
  zurückgestutzt (eigener BACKLOG-Punkt „Bridge leeren").

- **Startreihenfolge-Lücke: `recording.stop` und Gate-Reset warten jetzt
  auf Liquidsoaps Telnet (2026-09-06, `578e950`)** — Kommt PLAYOUT vor
  LIQUIDSOAP hoch (manuelle Reihenfolge mit Abstand, Boot-Fenster-
  Neustart, nächtlicher Neustart), lief der einmalige Startversuch ins
  Leere: die frische Instanz nahm die Sentinel-Datei
  `_uninitialized.mp3` auf (32 MB in 14 min am 2026-09-06 17:30) und
  behielt ihren Boot-Gate-Zustand.  Der Konstruktor versucht es weiter
  einmal; `ensure_liquidsoap_initial_state()` (aus `__main__`) wiederholt
  in einem Daemon-Thread alle 2 s bis 90 s, `recording.stop` dient als
  Bereitschafts-Sonde; der nächtliche Neustart nutzt dieselbe Sonde vor
  dem Gate-Reset.

- **Speicherleck der Windows-Liquidsoap: synchrone Scheduled-Queue
  (2026-09-05, Operator-Go, `462d684`)** — Der savonet-Windows-Build
  (OCaml 4.14) leakt ~5 KB pro `Unix.select` des Duppy-Schedulers
  (win32unix `select.c`, savonet #1122).  Ein `scheduled.push` startete
  den asynchronen Fetch-Task von `request.dynamic`, der sich nach dem
  Leerlaufen der Queue oder einem gescheiterten Request alle
  `retry_delay` (0,1 s) neu einplant — für immer: 0,15–0,8 MB/s, 3,4 GB
  nach zwei Stunden am 2026-09-05.  Das Template rendert jetzt
  `request.queue_sync`, eine wörtliche Kopie der Stdlib-`request.queue`
  mit `request.dynamic(synchronous=true)` und `timeout=5.0`: der Push
  löst inline im Telnet-Handler auf, kein Poller existiert.  Replika
  des Produktions-Renders gegen Icecast + Tascam: Speicher flach
  (94 MB konstant), jeder Push sofort vorbereitet, auch nach einem
  Fehl-Push; `skip`/`flush`/`annotate:` unverändert.  Upstream-Entwurf
  in `docs/upstream/`.
- **Main Output landete nach dem Reboot auf der falschen Buchse:
  Gerät per Namen statt Index (2026-09-05, Operator-Go, `1dbeb71`)** —
  PortAudio-Indizes sind auf der Studio-Maschine nicht stabil (Tascam
  WASAPI: 14 um 11:15, 18 um 12:10, 15 um 12:33); zwischen PLAYOUT-Probe
  und Liquidsoap-Open verschob sich die Liste, die Live-Instanz spielte
  stundenlang auf die Realtek-Onboard-Buchse, und ein Neustart mit dem
  veralteten Index hätte den Prozess am Geräte-Open beendet (NSSM-
  Neustart-Schleife).  Der Resolver prüft nach dem blockierenden Probe
  den Eintrag, den der exakte Name auswählt (Liquidsoap nimmt den
  ersten gleichen Namen; MME zuerst, MME-Namen 31 Zeichen): Ausgang
  auf MME/WASAPI, der öffnet → `device_name=`; sonst wie bisher
  `device_id=` mit Begründung im Log.  DirectSounds blockierender Write
  ist ein stummer Stub, WDM-KS hat keine blockierende API.
  Replika: Audio-Session liegt auf dem Tascam.

- **Regression: fremder Webstream direkt nach einem Webstream verband
  nicht neu — der alte Stream lief weiter (2026-09-05, `2e6367c`)** —
  Beim A/B-Test um 11:44:30 und 11:59:00 (BBC → Cloud-Stream) blieb
  **BBC** für den ganzen Cloud-Slot auf Sendung.  Ursache: Die
  Drain-Freigabe aus Paket 2 hält die einzige `webstream`-Quelle am
  Leben; `set_url` + `start` auf einer laufenden `input.http` verbindet
  nicht neu, und der verzögerte Stop wurde per Generation-Wächter als
  „neuere Quelle hat übernommen" übersprungen.  Vor Paket 2 war es
  Stop + Start.  Jetzt wieder: bei fremder URL harter Stop, dann
  Start (alter Rest fällt weg, neuer Stream puffert ~5 s) — mit einer
  Stream-Quelle die einzig korrekte Übergabe.  Gleiche URL bleibt
  Übergabe ohne Bounce, vorgewärmte Streams bleiben Gate-Start.  Test
  angepasst.  Lehre: Der A/B-Kontrollarm (frische Verbindung) ist
  dadurch nie gelaufen — Vergleich isoliert nachgeholt.

- **Vorwärmen ging am Refresh verloren; gleicher Stream → gleicher
  Stream hatte einen Dip (2026-09-05, `59c8e8f`)** — Aus der Live-Abnahme
  von Paket 2: (1) Ein Schedule-Refresh löscht und armt alle Timer neu.
  Fiel er in die letzten 10 s vor einem Slot (20:16:49 für 20:17:00),
  verwarf die Regel „Vorlauf ≤ 0,5 s → kein Prepare" das Vorwärmen, und
  der Slot startete mit den normalen 2 s Lücke.  Jetzt feuert das
  Prepare in dem Fall sofort (einzige Untergrenze
  `MIN_PREPARE_SECONDS` = 2,5 s), und beide Prepare-Handler sind für ein
  bereits vorgewärmtes Item idempotent — ein Re-Arm bounct nie eine
  laufende Vorwärmung.  (2) Webstream → derselbe Webstream in der
  Folgeshow (20:12) gab die laufende Quelle frei und startete sie neu:
  ~1 s Aus-/Einblend-Dip.  Jetzt eine Buchführungs-Übergabe wie beim
  Line-In auf gleichem Gerät (Quelle bleibt, Generation hochgezählt,
  Gate offen), mit passender Same-Stream-Follow-up-Regel in `_on_stop`,
  damit die Übergabe bei beiden Timer-Reihenfolgen hält.  Abweichender
  Gain startet weiterhin neu.

- **Sendeausfall 19:26–19:35 durch Typfehler im Bus-Switch (2026-09-04,
  `acdde5c`)** — Nach dem Neustart auf Paket 2 startete Liquidsoap
  nicht: Die Übergangsliste `[bus_instant, bus_instant, bus_transition,
  …]` ist für den Typprüfer nicht homogen — `bus_instant` gab `new` roh
  zurück, `bus_transition` ein `add()` aus Fades.  Alle Prüf-Renders und
  der isolierte Prüfstand hatten keine DJ-Arme (Harbor-Passwörter leer),
  also stand `bus_instant` nie in einer geprüften Liste.  Der Dienst
  blieb „Paused", der Stream war ~8,5 min tot.  Behoben durch Hot-Fix
  der Live-`rastatime.liq` (Neustart durch den Operator 19:35:19) und im
  Repo: `bus_instant` ist jetzt dieselbe Form (add zweier 50-ms-Fades),
  die Prüf-Renders enthalten die DJ-Arme für Crossfade und Ducking, ein
  Test pinnt die Form.  Lehre: **Prüf-Render immer in Produktionsform
  (mit DJ-Armen)** — steht jetzt im Render-Check-Skript.

- **Line-In: letzte ~6 s der Show fehlten, ~6 s Stille am Anfang —
  Paket „Line-In-Latenz" (2026-09-04)** — Der Operator zählte die
  Sekunden live ins Mikrofon: die letzten ~6 s einer Line-In-Show
  erreichten den Stream nie.  Das ist keine Startlücke, sondern die
  Durchlauf-Latenz L der Kette (Studiozeit t → Stream t+L; am Slot-Ende
  steckt [E−L, E] noch in der Kette und wird mit der Quelle verworfen).
  Messung, wo L steckt — zuerst falsch, dann richtig:
  - *Falsch:* Icecast-`burst-size` (2,7 s) — der `/linein-capture`-Mount
    hat seit 2026-05-13 bereits `burst-size 0`.  Kein ICECAST-Neustart.
  - *Richtig* (Icecast-`access.log`: Quelle UND Hörer ab +0,0 s
    verbunden, Audio ab +0,7 s, Decoder erst bei +6 s; dann vier
    isolierte Hörer gegen den echten Mount): **FFmpegs
    Format-Autodetection** braucht auf dem Icecast-Stream ~5 s (Hörer
    steigt mitten im Datenstrom ohne Header ein).  Autodetect 6 s,
    `format="mp3"` **1 s**, `format`+Probe-Argumente 2 s, nur
    Probe-Argumente 6 s.
  Fixe: `linein_http` bekommt `format="mp3"` (Container ist Eigenschaft
  unserer eigenen Capture, `-f mp3`); `max_buffer` 2,0 → 1,0 s (der
  Puffer ist permanente Latenz, nicht nur Startlücke); Capture-Start-
  Health-Check 1,5 → 0,75 s (`_STARTUP_HEALTH_CHECK_S`).  Erwartung:
  Abschneiden ~6 → ~2 s, Startlücke ~6 → ~2–3 s.  Manual (4 Sprachen):
  Latenz-Absatz neu, inkl. Moderations-Praxis „~2 s vor Slot-Ende
  aufhören".  Webstreams behalten die Autodetection (beliebige
  Container).

- **Show-Übergänge nach einem Line-In: Line-In blieb auf Sendung,
  Jingles stauten sich, laufender Slot wurde abgeschossen
  (2026-09-04)** — Beobachtet bei der Show-Folge Line-In 10:55 →
  Jingles + BBC-Webstream 11:00 → Line-In 11:07: die Jingles um 11:00
  waren unhörbar, nach dem Webstream kam sofort wieder das Tascam-Signal
  statt des Showteasers, die vier Jingles kamen um 11:07 gebündelt
  sieben Minuten zu spät, und um 11:08:17 wurde der laufende Line-In
  für 9 s abgeschossen.  Vier Ursachen, vier Fixe (Operator-Go, Option A):
  1. **Follow-up-Regel nur noch für echtes Back-to-Back.**  `_on_stop`
     übersprang den Line-In-Teardown, sobald *irgendein* Line-In auf
     demselben Gerät scharf war — auch einer sieben Minuten später.  Der
     Line-In blieb dadurch die ganze Zwischen-Show über im Bus-Switch
     (Line-In > Scheduled; Webstream > Line-In, fällt aber nach seinem
     Ende darauf zurück).  Jetzt greift die Übergabe nur, wenn der
     Nachfolger innerhalb von `LINEIN_FOLLOW_UP_WINDOW_SECONDS` (2 s)
     startet.
  2. **`scheduled.flush`** — neues Telnet-Kommando im `.liq`
     (`scheduled_q.set_queue([])`), das `engine.stop()` vor dem
     verzögerten `skip` absetzt.  `skip` erreicht nur das laufende
     Element; Requests, die gepusht wurden, während Line-In oder
     Webstream den Bus hielten, wurden nie „gespielt", also nie
     übersprungen, und kamen später gebündelt heraus.  Isolierter
     Liquidsoap-Lauf (Telnet 1235, ohne Ausgänge): RID 0 spielt, `queue`
     = „1 2", `flush` → Done, `queue` leer, RID 0 läuft ungestört weiter.
  3. **Option A der Key-Instabilität:** `insert_event` vergibt `_N`-
     Suffixe nach Einfügereihenfolge; fällt ein Event mit gleichem
     Startzeitpunkt (z. B. das Record-End der Vorshow) aus dem
     Abruffenster, rutscht der laufende Slot auf einen anderen Key.
     `refresh()` hielt das für „aus dem Schedule entfernt", killte den
     Capture und startete per Catch-up neu.  Jetzt vergleichen der
     Removed-Check und alle Catch-up-Zweige die **Identität** des
     Schedule-Items (`_same_scheduled_item`: Klasse, Typ, Row-ID,
     Start; bei Line-In zusätzlich Gerät + Kanäle) und binden nur den
     Key um.  Option B (stabile Keys) im Backlog.
  4. **Race-Härtung:** `_on_stop` prüft unmittelbar vor dem Zurücksetzen
     der Buchführung erneut, ob es noch der spielende Event ist (11:00:09:
     der STOP des Jingles überschrieb die Buchführung des schon
     laufenden Nachfolgers).  Und jeder Nachfolger schließt einen
     Line-In- bzw. Webstream-Vorgänger **selbst**
     (`_close_predecessor_source`, alle Aufrufe idempotent), statt sich
     auf die Timer-Reihenfolge mit dessen `_on_stop` zu verlassen.
  Dazu: drei Verträge in `backend/playout/tests/test_scheduler_linein.py`
  beschrieben noch den dshow-Pfad für 1/2 und „http nicht vorab scharf"
  — beides seit 2026-09-03 bewusst anders; auf den aktuellen Vertrag
  nachgezogen (die Paket-Suite war gestern nicht mitgelaufen).  Und die
  harmlose `→`-cp1252-Logging-Warnung aus dem Main-Output-Resolver ist
  weg (`->`).  Commit `ff567ce`.
  **Live-Abnahme 2026-09-04 14:55–15:20** (Line-In → Jingles + BBC +
  Showteaser → Line-In → Webstream), 21 Log-Prüfpunkte, alle grün:
  um 15:00:00 „armed but starts in 420s - not back-to-back" (Fix 1),
  „superseded … during teardown" + „takes over from line-in … closing
  its capture" (Fix 4 — der Nachfolger hat das Rennen tatsächlich
  gewonnen, ohne den Nachfolger-Teardown wäre der 11:00-Ausfall über
  diesen zweiten Weg wiedergekommen), TOH-Jingle sofort „Prepared",
  nach dem Webstream der Showteaser statt Tascam, um 15:07 keine
  gestauten Jingles, beim Refresh um 15:08:50 „rebinding, no teardown"
  statt „removed from schedule" (Option A), um 15:12 schließt der
  Webstream den Line-In selbst, um 15:20 kein Line-In-Comeback.

- **Catch-up-Log-Politur (2026-09-04)** — Die neue Identitäts-Prüfung
  für File- und Webstream-Catch-ups griff auch, wenn der Key bereits der
  spielende war, und loggte bei jedem Refresh ein sinnloses „Catch-up
  skipped (X → X); rebinding" (live 15:12:52 ff.).  Funktional harmlos
  (Rebinding auf denselben Key), jetzt an `key != playing_key` gekoppelt
  wie beim Line-In-Zweig; Test dazu.

### Changed

- **Event-Keys mit Identität statt Einfügereihenfolge — „Option B"
  (2026-09-10, Operator-Go, `23012bc`)** — `player/schedule.py` bildete Event-Keys
  aus dem Zeitstempel und hängte bei Kollisionen `_0`, `_1`, … nach
  Einfügereihenfolge an; fiel ein Ereignis aus dem Abruffenster,
  wanderten die Suffixe der übrigen (derselbe Slot kam als `…_0` und
  einen Refresh später als `…` zurück; 2026-09-04 ein 9-s-Loch, seit
  Option A per Rebinding abgefangen).  Keys lauten jetzt
  `<Zeitstempel>#<Tag>` mit einem Tag aus Typ und Identität
  (`make_event_key` in `player/events.py`): `file-<row>`,
  `ws-buffer-<row>`/`ws-play-<row>`/`ws-buffer-end-<row>`/`ws-stop-<row>`,
  `linein-<row>`, `record-start-<instance>`/`record-end-<instance>`,
  `switch_off-<instance>`/`kick_out-<instance>`.  Sortierung bleibt
  zeitlich (gleicher Präfix bis zum `#`), `insert_event` dedupliziert
  weiter strukturell und behält `_N` nur als theoretischen Rückfall;
  `event_key_to_datetime` ignoriert einen Tag.  Logs zeigen jetzt
  `PLAY 2026-09-10-10-00-00#file-4711`.  Sechs Upstream-Fixtures in
  `tests/player/schedule_test.py` nachgezogen.  Aktiv nach
  PLAYOUT-Neustart (keine Mischform alter/neuer Keys: die Schlüssel
  leben nur im Prozess).
- **DJ-Auflegen wird nach 5 s statt 30 s erkannt: `input.harbor`
  `timeout=5.` (2026-09-09, Operator-Go, `10e682f`)** — Der Windows-Build bemerkt
  einen DJ-Client, der nur den Socket schließt, erst mit dem Netzwerk-
  Timeout des Harbors (Standard 30 s).  Solange PLAYOUT einen DJ für live
  hält, schiebt es keine Titel nach; der Bus fiel nach dem 5-s-Puffer auf
  eine leere Warteschlange zurück — bis zu 25 s Stille nach dem Auflegen.
  Der Renderer setzt jetzt `timeout=` an beiden Harbors
  (`DEFAULT_HARBOR_TIMEOUT_SECONDS` 5, Maschinen-Einstellung
  `RASTATIME_HARBOR_TIMEOUT_SECONDS`, Minimum 1), passend zum 5-s-Puffer:
  Zustand und Audio kippen praktisch gleichzeitig.  Preis: ein Client,
  dessen Verbindung länger als 5 s stockt, wird getrennt und muss neu
  verbinden (BUTT tut das selbst).  Replikat: Trennen nach 5,06 s
  gemeldet (zwei Durchläufe).  Aktiv nach PLAYOUT-Neustart (rendert) und
  LIQUIDSOAP-Neustart.
- **Neustart-Erkennung ohne Telnet, DJ-Verifikation alle 10 min, Prozess-
  Probe kennt die Standby-Instanz (2026-09-09, Operator-Go, `9f8089a`)** — Nach dem
  ereignisgesteuerten Umschalter blieben drei Telnet-Kommandos je 2 min
  (Scheduler `uptime` zur Neustart-Erkennung, Umschalter zweimal Status),
  gemessen 14 MB/h.  (1) Der Scheduler erkennt einen LIQUIDSOAP-Neustart
  jetzt an der Prozesstabelle: neue PID oder jüngeres Prozessalter der
  Hauptinstanz (`_liquidsoap_process_identity`, `_maybe_reinit_by_process`);
  die Tabelle wird einmal je Zyklus gelesen (`_liquidsoap_process_infos`)
  und mit den Neustart-Auslösern geteilt; der Telnet-`uptime`-Vergleich
  bleibt Rückfall, wenn die Tabelle nicht lesbar ist.  (2)
  `RASTATIME_DJ_RECONCILE_SECONDS` Standard 120 → 600 s; Verbinden, Kick
  und Neustart werden weiterhin sofort verarbeitet, nur ein verlorenes
  Ereignis wird spätestens nach 10 statt 2 Minuten korrigiert.  (3) Dabei
  gefundener Fehler behoben: `liquidsoap_process_info` meldet jetzt das
  Skript jeder Instanz (WMI-Kommandozeile) und `main_instances` wählt die
  Hauptinstanz (Basisname von `RASTATIME_LIQUIDSOAP_CONFIG_PATH`,
  Standard `rastatime.liq`) — bisher nahmen Neustart-Auslöser und Preflight
  „den ältesten liquidsoap.exe", seit dem Standby-Dienst (09:18) also die
  Standby-Instanz: Speicher-Auslöser und `liquidsoap_unavailable` wären
  blind gewesen.  Erwartung ~2 MB/h Leerlauf (0,4 statt 3 Kommandos je
  2 min).  Tests `test_scheduler_process_restart_detection.py`,
  `test_liquidsoap_health_main_instance.py`,
  `test_preflight_main_instance.py`.  Aktiv nach PLAYOUT-Neustart,
  LIQUIDSOAP unberührt.
- **Telnet-Server trennt stille PLAYOUT-Clients nicht mehr (2026-09-09,
  Operator-Go, `8d9b067`)** — Erste Messung nach dem ereignisgesteuerten Umschalter
  (10:20–10:50, nichts auf Sendung): 14 MB/h statt ~150 MB/h.  Der Rest
  waren Telnet-Neuverbindungen: `settings.server.timeout` (Standard 30 s)
  trennte die stillen Verbindungen beider PLAYOUT-Clients, die sich
  danach alle 2 min neu aufbauten (30 in 30 min, je ~262 KB ≈ 16 MB/h).
  Das Template setzt jetzt `settings.server.timeout.set(-1.)`; es gibt
  nur Loopback-Clients, und Windows schließt deren Sockets beim
  Prozessende.  Erwartung ~5–8 MB/h; wirkt ab dem nächsten LIQUIDSOAP-
  Neustart (der geplante um 04:00 rendert vorher neu, kein PLAYOUT-
  Neustart nötig).  Test `test_telnet_server_timeout.py`.
- **Quellen-Umschalter ereignisgesteuert: der Harbor meldet DJ-Verbindungen
  selbst, der 5-s-Telnet-Poll entfällt (Option d = Ziel c, 2026-09-09,
  Operator-Go, `758fd6f`)** — PLAYOUTs SourceSwitcher fragte `master_dj.status` und
  `show_dj.status` alle 5 s per Telnet ab; auf dem Windows-Build leckt
  jedes Telnet-Kommando ~87 KB, und dieser Poll war das Leerlauf-Wachstum
  von ~150 MB/h, also der Grund für den täglichen Neustart.  Jetzt rendert
  das Template pro Harbor `on_connect`/`on_disconnect`-Callbacks
  (`_render_harbor_source_events`, `synchronous=true`, damit ein schnelles
  Verbinden/Trennen seine Reihenfolge behält), die aus einer abgesetzten
  `thread.run`-Aufgabe `http.post` auf PLAYOUTs Listener
  `http://127.0.0.1:8770/source-event?source=master|show&status=on|off`
  absetzen (Timeout 2 s, Fehler nur geloggt).  PLAYOUT übernimmt das
  Ereignis sofort und verifiziert 1 s später einmal per Telnet
  (`SourceSwitcher.request_reconcile`, `_reconcile_liquidsoap_once`);
  die periodische Verifikation läuft nur noch alle
  `RASTATIME_DJ_RECONCILE_SECONDS` (Standard 120, Minimum 5) als
  Sicherheitsnetz, und nach einem LIQUIDSOAP-Neustart fordert der
  Scheduler eine Verifikation an (`_request_source_reconcile`), weil der
  alte Prozess seine Verbindungen nicht mehr abmelden kann.  Läuft noch
  eine alte rastatime.liq ohne Callbacks (Probe `rastatime.source_events`),
  pollt PLAYOUT wie bisher alle 5 s, bis LIQUIDSOAP mit dem neuen Render
  startet — die Reihenfolge der Neustarts ist damit egal.  Replikat
  2026-09-09: Verbinden → Ereignis binnen Millisekunden, Kick
  (`show_dj.stop`) → sofort; ein DJ, der einfach auflegt, wird wie bisher
  erst nach dem 30-s-Netzwerk-Timeout des Harbors erkannt (der Windows-
  Build sieht das Verbindungsende im `select` nicht; BACKLOG-Idee).
  Restkosten: zwei Telnet-Kommandos je DJ-Ereignis und je 120 s (~125 MB
  pro Tag statt 1440 Kommandos pro Stunde).  Tests:
  `test_harbor_source_events.py` (inkl. `liquidsoap --check` des
  Voll-Renders), `test_source_switcher_events.py`,
  `test_scheduler_source_reconcile.py`; die bestehenden Reconciler-Tests
  rufen jetzt die echte Rundenfunktion.  Aktiv nach PLAYOUT-Neustart; die
  Callbacks ab dem nächsten LIQUIDSOAP-Neustart (spätestens 04:00).
  Danach `RASTATIME_LIQUIDSOAP_RESTART_EVERY_DAYS` auf 7–30 setzen, sobald
  eine Woche Speicherverlauf flach ist.
- **Webstream-Wächter läuft jetzt in Liquidsoap selbst, als Frame-Zähler
  ohne Poll (2026-09-07, Operator-Go, `8785bec`)** — Der Wächter vom 2026-09-06
  fragte alle 2 s per Telnet `webstream.ready` ab; auf dem Windows-Build
  leckt jedes Telnet-Kommando ~87 KB (`Unix.select`), also ~157 MB pro
  Webstream-Stunde.  Replikat-Messung 2026-09-07 über 15 min: Telnet-
  Poll +57 MB, `thread.run.recurrent`-Timer +25 MB, Frame-Zähler auf
  `bus.on_frame` +0,1 MB (flach wie die Basis).  Das Template rendert
  daher einen Block hinter der `bus`-Definition: der Zähler im
  Streaming-Thread prüft alle 100 Frames (2 s) `source.is_ready
  (webstream)`, solange der Eingang gestartet ist, und lässt nach zwei
  toten Prüfungen hinter einer guten per einmaligem `thread.run`
  `stop`+`start` des Eingangs laufen (Logik des Scheduler-Wächters,
  unverändertes Zeitverhalten).  Telnet `webstream.watchdog` liefert
  Zähler und Zustand.  Ende-zu-Ende im Replikat gegen einen stallenden
  Server: zwei Stalls, zwei Reconnects nach 3–4 s, Bus nach ~11 s
  wieder auf dem Stream.  PLAYOUT: `RASTATIME_WEBSTREAM_WATCHDOG`
  (`liquidsoap` Standard, `scheduler` = alter Telnet-Poll als
  Rückfall); im Standardmodus prüft der Scheduler einmal je Liquidsoap-
  Instanz, ob die geladene .liq den Block hat, und pollt sonst selbst
  (Übergang PLAYOUT-Neustart vor LIQUIDSOAP-Neustart).  Tests
  `test_webstream_watchdog_in_liquidsoap.py` (17); Handbuch
  „Webstreams" in vier Sprachen; Architektur 0.24.  Aktiv nach dem
  nächsten Neustart PLAYOUT → LIQUIDSOAP (der nächtliche Neustart
  erledigt den zweiten Schritt selbst).

- **Webstream-Erholung nach Server-Aussetzern: Timeout 3 s, Poll 0,5 s,
  10-s-Bridge, Vorwärmen 20 s vor dem Slot („Option 1", 2026-09-05,
  Operator-Go, `860ebee`)** — Der Cloud-Stream (`DEVAStreamServer 1.4`,
  Live-Signal „Event Calendar") stallt gelegentlich wenige
  Sekunden nach einer frischen Verbindung; mit `timeout` 10 s,
  `poll_delay` 2 s und 5-s-Bridge kostete jeder Stall 20–50 s Stille
  (11:36: 52 s).  Jetzt `timeout` 3 s, `poll_delay` 0,5 s, Bridge 10 s
  (`max` 20 s): Erholung ≈ 5–9 s, also unter der Bridge — ein Stall bis
  etwa 10 s erreicht die Sendung nicht mehr.  Webstreams werden dafür
  20 s vor dem Slot vorgewärmt (`WEBSTREAM_PREPARE_LEAD_SECONDS`,
  Line-Ins weiter 10 s); ein nicht vorwärmbarer Webstream braucht ~10
  statt ~5 s.  Messungen: zwei nackte Sonden vom Studio (6 min
  Dauerlesen, 15 min mit frischer Verbindung alle 90 s) waren sauber;
  ein absichtlich langsamer Leser wurde von der DEVA nach 48 s
  ausgehungert und nach 328 s zurückgesetzt; Liquidsoap liest bei
  geschlossenem Gate durchgehend weiter (Server sah 100 s lang keinen
  blockierten Send), das Vorwärmen löst dieses Verhalten also nicht
  aus.  A/B gegen einen lokalen Server, der alle 60 s für 6 s
  schweigt: siehe BACKLOG-Eintrag A/B-Test.  Manual WEBSTREAMS in vier
  Sprachen, Architektur §23.27 Addendum.

- **Monitor-Uhr `sync="auto"`, Quellen-Warnschwelle 200 (2026-09-05,
  `462d684`)** — `output.portaudio` ist selbst-synchron (blockierende
  Writes takten die Uhr am Gerät); `sync="cpu"` kämpfte dagegen und
  meldete „Latency is too high" jede Sekunde (3.560/h), sobald der
  Ausgang wirklich spielte — nach dem Reboot fehlten die Meldungen nur,
  weil die Instanz auf DirectSound (Stub) lag.  `sync="auto"` lässt das
  Gerät takten, die `buffer()`-Brücke fängt die Drift.  Replika mit dem
  Tascam: „Switching to self-sync mode", 0 Warnungen.
  `settings.clock.leak_warning := 200`: die Kette hat ~45 statische
  Quellen plus 10–13 kurzlebige je Übergang; 50–63 war Fehlalarm.

- **`input.http`-Puffer des Line-In-Companions 1,5 → 2,0 s
  (2026-09-03)** — Auf Operator-Wunsch nach dem ~1 s Aussetzer der
  15:15-Show.  Die Ursache war zwar der Catch-up-Bounce (siehe Fixed)
  und kein Under-run, aber die Messung zeigte auch, dass `max_buffer`
  ohnehin nicht der dominierende Anteil der Startlücke ist: die
  zusätzliche Reserve kostet ~0,5 s Startlücke und kauft dafür
  Reserve gegen echte Under-runs — auf einem Sendeweg ein guter
  Tausch.  Weiterhin per
  `RASTATIME_LIQUIDSOAP_LINEIN_HTTP_MAX_BUFFER_SECONDS` einstellbar
  (Boden 0,2 s).  Laufzeitgeprüft mit echtem Liquidsoap-Lauf: 2,0 s /
  `poll_delay` 0,5 s werden akzeptiert (11 Polls in 6 s).

### Fixed

- **Geplante Line-Ins auf Kanal 1/2 sendeten Stille (2026-09-03)** —
  „Option B".  Schlichtes Stereo 1/2 nahm bisher den direkten
  DirectShow-Pfad: ffmpeg öffnete das Gerät als
  `audio=@device_cm_{...}\wave_{<GUID>}`, gebaut aus der auf der
  Line-In-Zeile gespeicherten Windows-Audio-*Endpoint*-GUID.
  DirectShow führt aber eine eigene Geräte-GUID-Liste und kennt diese
  nicht — an der 15:20-Testshow („Tascam 1-2") antwortete ffmpeg
  `Could not find audio only device` und der Slot ging stumm auf
  Sendung.  Dasselbe Gerät öffnet über MME einwandfrei, deshalb läuft
  **jeder** geplante Line-In jetzt über den sounddevice/MME-Feeder, der
  per Anzeigename auflöst.  Der dshow-Pfad bleibt nur noch als
  Fallback für Alt-Zeilen ohne gespeicherten Gerätenamen (die der
  Feeder nicht auflösen kann) — solche Zeilen bitte einmal neu
  speichern.  Die Entscheidung fällt an drei Stellen und wird jetzt
  im Gleichschritt gehalten: `PlayoutScheduler._on_linein_start`,
  `PlayoutScheduler._resume_scheduled_locked` (sonst hätte ein
  Liquidsoap-Neustart mitten in der Show den Slot still zurück auf
  dshow geworfen) und `FfmpegLineinCapture._start_locked` — letztere
  ist die, die tatsächlich über den Audiofluss entscheidet.

- **~1 s Aussetzer mitten in einer laufenden Line-In-Show
  (2026-09-03)** — Ein Schedule-Refresh kann denselben laufenden
  Line-In-Slot unter einem *anderen* Key zurückliefern (live gesehen:
  `…-13-15-00_2` beim Start, blankes `…-13-15-00` 70 s später).  Der
  Catch-up-Wächter verglich nur Keys, spielte den Slot deshalb erneut
  an, und `linein_start_http` riss die http-Quelle mitten in der Show
  ab und wieder auf — hörbar als ~1 s Stille um 15:16:20.  Der Capture
  selbst war idempotent („already capturing"), der Quellen-Bounce war
  also der ganze Schaden.  Catch-up überspringt jetzt einen Line-In,
  der mit gleichem Gerät + gleicher Kanalwahl bereits auf Sendung ist,
  und übernimmt nur den neuen Key, damit der zugehörige `_on_stop`
  weiterhin greift.

- **Line-In-Start-Lücke von ~7 s auf ~6 s verkürzt (2026-09-03)** —
  Bei einer geplanten Line-In-Show auf dem Mehrkanal-Pfad
  (Feeder → `/linein-capture` → `input.http`) lagen zwischen Ende der
  Vorshow und erstem hörbaren Signal ~7 s Stille (14:20-Show gemessen:
  Mount ab +1,8 s, Umschaltung erst +7,0 s).  Hauptursache war
  `input.http`'s `max_buffer` — die Quelle wird erst „ready", wenn so
  viele echte Sekunden gepuffert sind.  **Hebel 1:** `max_buffer`
  4,0 → 1,5 s (per `RASTATIME_LIQUIDSOAP_LINEIN_HTTP_MAX_BUFFER_SECONDS`
  auf 1,0 A/B-testbar, Boden 0,2 s) und `poll_delay` des http-Companions
  2,0 → 0,5 s.  **Hebel 2:** der Scheduler armt `input.http` jetzt
  *parallel* zum blockierenden Feeder-Start (der ~1,5 s
  Health-Check-Schlaf), statt strikt danach — die Pufferfüllung
  überlappt das Feeder-Hochlaufen; scheitert der Feeder, wird die
  vorab-gestartete Quelle wieder gestoppt (der b4cd37b-404-Poll-Schutz
  bleibt).  Verifiziert mit echtem Liquidsoap-Lauf + Tests.
  **Nachgemessen an der 15:15-Live-Show: nur ~7 s → ~6 s.**  Die
  ursprüngliche Schätzung „~2-3 s" war zu optimistisch — `max_buffer`
  war *nicht* der dominierende Anteil.  Den Löwenanteil hält die
  Capture-Kette selbst (Gerät öffnen, ffmpeg-Encoding, genug MP3 im
  Mount, damit ein Decoder einrastet: ~4 s vom ffmpeg-Start bis zu
  dekodierbarem Audio).  Als eigener Backlog-Punkt notiert.

- **Sendeausfall durch Callback-Probe behoben (2026-09-03)** — Die
  Geräte-Probe des Main-Output-Features testete im PortAudio-
  *Callback*-Modus, Liquidsoap benutzt aber die *blockierende* API.
  WDM-KS beherrscht nur ersteres, wurde deshalb als tauglich gemeldet,
  und Liquidsoap stürzte beim Öffnen ab (`Blocking API not supported
  yet` → `Invalid_argument("option is None")`) — inklusive aller
  Icecast-Ausgänge.  `liquidsoap --check` fand das nicht, weil es nur
  typprüft und nie ein Gerät öffnet.  Die Probe läuft jetzt blockierend
  **und schreibt** einen Puffer (DirectSound am Tascam öffnet und
  scheitert erst beim Schreiben); die Verifikation umfasst jetzt einen
  echten Liquidsoap-Lauf, nicht nur `--check`.

- **„Main Output" wirkt jetzt tatsächlich (2026-09-03)** — Die
  Geräteauswahl unter Settings → Local Machine war für die
  Liquidsoap-Engine wirkungslos: Der Wert wurde gespeichert und an
  Playout gepusht, dort aber von einem No-Op
  (`LiquidsoapPlayoutEngine.set_audio_device`) verworfen, und
  `output.portaudio` wurde ohne Geräteargument gerendert — der lokale
  Monitor hing also immer am Windows-Standardgerät.  Das UI versprach
  eine Funktion, die es nicht hatte.  Neu: `engine/portaudio_output.py`
  löst den Endpunkt zu einem PortAudio-Index auf und rendert ihn als
  `device_id=` in die `.liq`.  Die Auflösung **probiert die Host-APIs
  durch** statt eine zu unterstellen, und zwar über PortAudios
  **blockierende** API — genau den Weg, den Liquidsoap selbst nimmt.
  Bei 44,1 kHz gemessen: MME und DirectSound funktionieren fürs
  USB-Headset; WDM-KS kann keine blockierende Ausgabe.  **Tascam:**
  Solange das Windows-Mix-Format des Endpunkts auf 48 kHz stand, lehnte
  ihn jede Host-API ab (WASAPI shared verlangt exakt die Mix-Rate) —
  das sah nach totem Gerät aus.  Nach Umstellung des Endpunkt-Formats
  auf **44,1 kHz** (Windows-Sound → Erweitert) öffnet WASAPI blockierend,
  Liquidsoap treibt den Tascam als Sendeausgang, Line-In-Aufnahme am
  selben Interface und Fremd-Apps laufen parallel (verifiziert
  2026-09-03).  Der Resolver loggt bei „Invalid sample rate" jetzt
  genau diesen Hinweis.  Kein Kandidat öffenbar → OS-Standard-Rückfall
  mit Log-Eintrag je Fehlgrund statt stiller Stille.  Zusätzlich findet die Zuordnung
  die WDM-KS-Variante über einen Hardware-Token (`US-16x08`), weil der
  Treiber sie anders benennt als den Windows-Anzeigenamen.

### Added

- **Anzeige „welcher Ausgang läuft wirklich" (2026-09-03)** — Settings
  → Local Machine zeigt über dem Anwenden-Knopf den **tatsächlich
  aktiven** Ausgang, gelesen aus einem Marker in der gerenderten
  `.liq` (`# rastatime-main-output: <endpoint-id>`), nicht aus dem
  gespeicherten Wert.  Weichen beide ab — Änderung noch nicht
  angewendet, oder Gerät nicht öffenbar —, sagt die Zeile das
  ausdrücklich.  Anlass: Ein gespeichertes „Tascam" bei real laufendem
  Jabra war für den Operator nicht erkennbar.  Verglichen wird die
  Windows-Endpunkt-ID, nicht der Gerätename: PortAudio benennt
  denselben Endpunkt je Host-API anders, ein Namensvergleich erzeugte
  Fehlalarme.

- **„Jetzt anwenden"-Knopf für Main Output (2026-09-03)** — Das
  gewählte Gerät wird beim PLAYOUT-Start in die `.liq` kompiliert und
  von Liquidsoap erst beim eigenen Start gelesen; ein Wechsel braucht
  also beide Dienste neu.  Automatischer Neustart beim Speichern wäre
  falsch (er unterbräche den Stream ohne Vorwarnung), daher ein
  bewusster Knopf mit Bestätigung unter der Geräteauswahl
  (`preference/restart-audio-chain`, PLAYOUT zuerst, dann LIQUIDSOAP).
  Der Endpunkt liegt bewusst in der Legacy-PHP-Schicht hinter Login +
  CSRF und **nicht** an der Django-API: Die bindet `0.0.0.0:8765` ohne
  Authentifizierung, ein Neustart-Endpunkt dort wäre für jeden im Netz
  erreichbar.

- **Line-In-Kanalwahl auf Mehrkanal-Interfaces (2026-08-31,
  `e91ae9b`)** — Ein Line-In wählt jetzt, **welche Kanäle** seines
  Geräts er aufnimmt (Stereo-Paar oder Mono-Kanal): am 16-Input-Tascam
  US-16x08 bedient damit ein Interface mehrere Studios (ein Line-In
  pro Paar).  `channel_mapping` existierte durch alle Schichten, wurde
  aber von keiner Capture angewendet.  PoC-getriebener Modus-Entscheid:
  WASAPI shared ist aufs Stereo-Mix-Format gedeckelt, exclusive lehnt
  der Treiber ab, DirectSound liefert Stille, WDM-KS kann kein
  Blocking-Read — **MME** liefert nachweislich alle 16 echten Kanäle
  (Per-Lane-Bitvergleich).  Neuer `linein_feeder`-Subprozess
  (sounddevice/MME → s16le-Stereo an ffmpeg-stdin, `/linein-capture`
  wie gehabt); in Liquidsoap-Mode konsumiert eine zweite Source
  `input.http(id="linein_http")` den Mount (Phase-F-Muster neben der
  F-2-dshow-Source, per `fallback` in denselben Switch-Arm gefaltet).
  Schlichtes `Stereo 1/2` bleibt byte-identisch auf dem bewährten
  dshow-Pfad.  Same-Device-Transition vergleicht jetzt auch das
  Mapping (zwei Studios an einer Karte müssen bouncen); der
  Linein-Resume re-armt in Liquidsoap-Mode die Sourcen statt eine
  Capture-URL durch die Request-Queue zu schieben (vor-F-2-Altlast).
  UI: Freitext `0,1` → Picker aus der Gerät-Kanalzahl („Stereo 1/2"
  … „Mono 16"; live verifiziert: Tascam 24 Optionen, Jabra exakt
  „Mono 1").  Domain lehnt Mappings > 2 ab.  Neue Dependency
  `sounddevice` (pip-only, bündelt PortAudio).  Tests: playout 295
  passed, audio-unit 196 passed; Feeder live gegen das Tascam
  verifiziert (16 ch @ 48 kHz, Kanäle 5/6 → Stereo).  Doku: Manual
  LINE_IN in EN/DE/FR/ES + ARCHITECTURE 0.19 (`e003f08`).
  **Deploy-Hinweis:** PLAYOUT-Neustart rendert das rastatime.liq mit
  der neuen linein_http-Source — bis dahin ist der Multichannel-Pfad
  inaktiv (Stereo-Betrieb unverändert).
  **Live-Härtung nach den ersten Testläufen (2026-09-01):** Der
  Erstlauf scheiterte an der **Tascam-WDM-Exklusivität** (Render
  belegt → jeder Capture-Open scheitert; gemessen in beide
  Richtungen — auch der Monitor-Ausfall vom 31.08. war die
  Gegenrichtung).  Interim: Windows-Default-Ausgabe auf den Jabra
  (BACKLOG-Eintrag „Monitoring zurück auf Tascam" mit
  WASAPI-Koexistenz-Plan).  Gehärtet: Feeder-Open-Kandidaten-Kette
  (MME all-ch / MME cover-ch / WASAPI) + Rate-Ladder in der Capture
  (`d73e6bc`), `is_running`-Guard vor `linein_start_http` — kein
  404-Polling auf toten Mount mehr (`b4cd37b`), verlorenes
  stdout-Handle aus dem Refactor restauriert (`b2dee35`).  Danach
  end-to-end ON AIR bewiesen: Kaltstart 12:17 (Paar 3/4, 1,5 s bis
  streaming) und Same-Device-Studio-Wechsel 12:30 (3/4 → 9/10,
  sauberer Capture-Bounce, ~14 s Umschalt-Übergang).

- **Listener-Statistik-Collector läuft jetzt wirklich (2026-08-30,
  `00ce768`)** — Root Cause des 🔴-BACKLOG-Items „Listener-Statistik
  zeigt keine Daten": der `StatsCollectorThread` wurde nur im
  verwaisten `main.py` gestartet, der aktive Entry-Point
  `__main__.py` kannte ihn nicht → `cc_listener_count` blieb leer.
  Jetzt startet der Playout-Dienst den Collector (120-s-Poll gegen
  Icecast `/admin/stats.xml`); die Poll-Liste kommt via
  `outputs_from_stream_settings()` aus den live
  `cc_pref stream_output_N`-Settings (inkl. Admin-Creds; Einträge
  ohne Admin-Passwort werden mit Warnung übersprungen) statt aus der
  seit dem Phase-D-Cutover leeren `libretime.conf`-Output-Liste.
  4 neue Tests; E2E live bewiesen (2 Test-Listener → exakt 1/1/0 in
  `cc_listener_count`).  Flankierend: neues Manual-Kapitel
  **Analytics** in EN/DE/FR/ES + TOC-Zeilen (`96cc252`).

- **Traffic Alerts (2026-06-16, T1–T2)** — Kurzfristig eintreffende
  Verkehrsmeldungs-MP3s laufen binnen ~10 Minuten on air, ohne Eingriff in den
  Python-Playout-Pfad:
  - **Settings**: ein **Traffic-Alert-Smart-Block** wird unter
    **Settings → General** als Quelle gewählt (Single-Select, cc_pref
    `traffic_alert_block_id`; „(none — disabled)" schaltet das Feature ab)
    (`96b5f30`).
  - **Inkrementeller Fill statt Insert+Shift** (Operator-Vereinfachung
    2026-06-16): eine Show, die diesen Block in ihrer Autoload-Dramaturgie
    trägt, wird **inkrementell gefüllt wie eine Request-Show** — Reuse der
    Mid-Show-R1-Engine (`_fillRequestShowByPositions`).  Jeder Traffic-Slot
    wird erst kurz vor seiner Spielzeit aufgelöst und zieht dann den ältesten
    noch nicht eingeplanten Alert (`_appendTrafficAlert`: FIFO nach
    `cc_files.utime`, kein Random-Fallback, keine Doppel-Ausstrahlung).  So
    läuft eine **mitten in der Sendung importierte Meldung am nächsten Slot**,
    und kein Folge-Item muss geschoben werden (`e0c7873`).
  - **SLA über Dramaturgie-Dichte** (Operator-Entscheidung B): die 10-Min-Frist
    wird gehalten, indem der Operator Traffic-Slots eng genug platziert und
    Tracks direkt davor kurz hält; ein aktiver **Deadline-Skip** ist mit
    Vorbedingung in den Backlog gestellt (🟡 Defer).
  - Feature lässt sich jederzeit abschalten (Settings → „(none)"): eine
    Traffic-Show fällt dann sauber auf den normalen One-Pass-Fill zurück.
  - i18n der drei Settings-Strings (de/fr/es), korrigierte Feld-Beschreibung
    (`f61e470`).

- **Show-Shift / „Allow delayed start" (2026-06-15, Phasen 1–3b)** — Eine
  opt-in-Checkbox **„Allow delayed start?"** pro Show (When-Section, direkt
  unter „Repeats?") lässt eine Show **später beginnen**, wenn die vorige Show
  ihren Slot überzieht — statt die vorige Show am Slot-Ende abzuschneiden:
  - **Datenmodell**: additive Spalte `cc_show.allow_delayed_start`
    (Legacy-Migration 0056, `BOOLEAN DEFAULT false`); ohne Propel-Accessor,
    Form liest/schreibt per raw SQL — selber Präzedenzfall wie die
    Song-Request-Spalten (`fe630ec`).
  - **Form/UI**: Checkbox in `AddShowWhen` + `add-show-when.phtml`, Speichern
    in `ShowService::setCcShow`, Vorbelegung in `ShowFormService`
    (Edit + Instanz-Edit) (`277f4e5`).
  - **Engine** (`Application_Service_ShowShiftService`): die überbuchende Show
    spielt voll aus (ihr Ende wird auf das Content-Ende erweitert → kein
    Eingriff in den Python-Playout-Pfad); die folgende opted-in-Show behält ihr
    **Ende fix** und verschiebt ihren **Start** auf das Content-Ende (Items
    mit, letzter Track am Slot-Ende geclamped = akzeptierter Cut-off).  Der
    Effekt **kaskadiert** über aufeinanderfolgende opted-in-Shows bis zur
    ersten Show **ohne** Flag (harter Anker); eine komplett überrollte Show
    wird **geleert** (leerer „skipped"-Slot bleibt als Marker).  Vorwärts-only
    (kein automatisches Rückgängigmachen, daher keine Original-Slot-Spalte),
    idempotent über ganzzahlige Sekunden-Deltas + `modified_instance`-Filter
    (`5d24276` Single-Shift + Task, `bdd0f54` Kaskade + Clearing).
  - **Trigger**: `ShowShiftTask` (TaskManager, alle 2 min, 15 min Vorlauf,
    env-overridebar via `RASTATIME_SHOW_SHIFT_INTERVAL_SECONDS` /
    `RASTATIME_SHOW_SHIFT_LEAD_SECONDS`); greift auch bei manuell gefüllten
    Shows; eine wiederkehrende Show ändert nur die betroffene Episode
    (`modified_instance`).  Die Playout-History bleibt automatisch korrekt
    (reale Spielzeiten, kein Eingriff nötig).
  - Verifiziert: PHP-Lint, Rollback-TX-Logiktests (Shift/Kaskade/Clearing/
    Anker/Idempotenz), Produktions-Smoke + isolierter End-to-End-Live-Test
    (dedizierte Test-Shows, echter Commit, mit Teardown).
  - Doku: neues Kapitel **Delayed Show Start** im User-Manual (EN/DE/FR/ES),
    ARCHITECTURE §23.24.

- **Song Requests (2026-06-08, SR-Phasen 1–7)** — Hörer können über ein
  öffentliches Embed-Widget (`/Embed/song-request`) Tracks wünschen, die
  automatisch in einer **Request-Show** laufen.  Vollständig aus vorhandenen
  Bausteinen zusammengesetzt — kein neuer Objekttyp, keine Moderations-Queue:
  - **Datenmodell**: neue Django-Tabelle `rastatime_song_request`
    (Lifecycle pending → queued → played → expired) + Aggregat-Cache auf
    `cc_files` (`requested` / `requested_at` / `request_count` /
    `requestable`).
  - **Smart-Block-Konsum**: neues Kriterium **„Use requests"** zieht nur
    Tracks mit offenem Request, Sortierung „ältester Request zuerst" oder
    „meistgewünscht".
  - **Öffentliches Intake** (Django `/api/v2/song-requests`, Such- +
    Submit-Endpoint, ohne Login): Rate-Limit (5/h), Dedup (30 min),
    Katalog-Beschränkung über den Pool; Roh-IP wird nie gespeichert (nur
    gesalzener Hash).
  - **Hörer-Widget**: scrollbare Tabelle (Cover · Artist/Title ·
    Request-Button), kein Suchfeld, keine Pagination; Cover via 3rd-Party-API.
  - **In-Show-Befüllung (Option C-onepass)**: eine Request-Show ist *implizit*
    markiert (Autoload-Playlist enthält einen „Use requests"-Block — kein
    Per-Show-Flag).  `RequestShowFillTask` (alle 2 min, 8 min Vorlauf) befüllt
    **Position für Position**, sodass mehrere „Use requests"-Slots
    **verschiedene** Requests ziehen; ein abschließender „time remaining"-Block
    füllt den Rest.  Leere Request-Slots fallen auf einen **Zufalls-Track** aus
    dem Block-Katalog zurück (kein Dead Air).
  - **Lifecycle-Tasks**: `RequestPlayedTask` (Schedule-basiert, kein
    Playout-Eingriff) + `RequestExpiryTask` (8 h TTL, env-overridebar;
    setzt zudem eingeplante Requests einer *gelöschten* Show zurück in
    den Pool — Re-Pending statt Verwaisung, 2026-06-09).
  - **Pool-Auswahl** (Settings → General): „Song-Request Pool" als Dropdown im
    Stil des Library-„Columns"-Pickers.
  - Doku: neues Kapitel **Song Requests** im User-Manual (EN/DE/FR/ES),
    ARCHITECTURE §23.23.

### Removed

- **qtip2-Tooltip-Bibliothek vollständig entfernt (JS-Modernisierung Stufe 1,
  2026-06-01, `d63394f`)** — qtip2 (EOL, nightly 2012) war über ~31 Tooltip-
  Aufrufe in 14 Dateien im Einsatz.  Alle auf **rtTooltip** (eigener Wrapper auf
  Floating UI) migriert (s. *Changed* / *Added*), dann die Lib (`js/qtip/` +
  `css/qtip/`, ~3.800 Zeilen) + globaler Load + 4 `assets.json`-Einträge
  entfernt.  Verifiziert: kein funktionaler `.qtip()`-Aufruf mehr.  Damit ist
  **JS-Modernisierung Stufe 1 komplett** — die zwei anvisierten EOL-Libraries
  (AngularJS + qtip2) sind beide weg.

- **AngularJS-Bibliothek vollständig entfernt (JS-Modernisierung Stufe 1,
  2026-06-01, `62fbe18`)** — AngularJS 1.4.5 (EOL 2022) wurde nur noch von zwei
  Stellen genutzt: dem Publish-Dialog und den Podcast-/StationPodcast-Editoren.
  Beide auf vanilla/jQuery migriert (s. *Changed*), danach die Lib (~150 KB) +
  ihre per-page-Loads (`PodcastController`, `ShowbuilderController`) + der
  `assets.json`-Eintrag entfernt.  Verifiziert: kein funktionaler
  `angular.module`/`.bootstrap`/`ng-*`-Code mehr (nur Kommentare).
  Nebeneffekt: Angular probt beim Laden `eval` (eigene CSP-Feature-Detection),
  was die Site-CSP auslöste und einen Konsolen-Verstoß auf diesen Seiten loggte
  — dieses Rauschen ist jetzt weg.

- **jPlayer-Bibliothek vollständig entfernt (JS-Modernisierung Stufe 0,
  2026-06-01, `9fa39e8`)** — nachdem alle drei Nutzer auf natives `<audio>`
  migriert waren (Audio-Preview 1/3, Dashboard-Stream-Player 2/3, Radio-Page
  Podcast-Player + GUI 3/3), wurde die archivierte jPlayer-Lib (2.7.0, 2014)
  samt globalem Load entfernt: der ganze `public/js/jplayer/`-Baum (Core,
  Playlist-/Inspector-Plugins, Popcorn-Bridge, `Jplayer.swf`-Flash-Fallback,
  blue.monday-Skin — 13 Dateien, ~2.600 Zeilen), der globale Script-Load in
  `PageLayoutInitPlugin`, das tote `#jquery_jplayer_1`-Mount-Div im
  Header-Partial und 7 `assets.json`-Einträge.  Die Radio-Page-GUI behält ihre
  eigenen `jplayer.png`/`pbar-ani.gif`-Kopien unter `css/radio-page/` (von
  `station-podcast.css` referenziert) → Optik unverändert.  Verifiziert: kein
  funktionaler `.jPlayer()`/`jPlayerPlaylist`-Aufruf mehr (nur Kommentare),
  Radio-Page + Login laden 200, kein jPlayer-Asset wird mehr ausgeliefert.

- **Toter VLC-Engine-Code entfernt (Cleanup Stufe 1, 2026-05-31)** — die
  nie produktiv gewordene libVLC-Engine-Architektur (RASTATIME lief über
  mpv → Liquidsoap, nie über VLC) wurde vollständig entfernt: ~12.900
  Zeilen über drei thematische Commits, jeweils mit fokussierter
  Regression.
  - **top-level playout-Stack**: `playout/{engine_vlc,scheduler,
    queue_manager,fallback}/` + `rastatime_common/` (0 Live-Importe,
    per Import-Graph verifiziert).
  - **Streaming-Layer**: ganz `streams/ingress/` +
    `streams/egress/{_vlc_manager,_sout,_archive,_connection,_health,
    _metadata}.py`; `streams.egress` behält nur die lebende
    Status-API-Oberfläche (`interface`/`_registry`/`_api_helpers`, vom
    Django-View `/api/v2/streams/outputs` genutzt).
  - **backend**: `engine/vlc_engine.py` + der
    `RASTATIME_PLAYOUT_ENGINE=vlc`-Branch in `__main__.py` (mpv- +
    liquidsoap-Pfade unberührt); VLC-Präsenz-Check + VLC-PATH-env-vars
    aus `infra/nssm/install-playout.ps1`.
  - **veraltete VLC-Ära-Guard-Tests**: `test_tgh1_no_liquidsoap.py`
    gelöscht (Prämisse „Liquidsoap ist toter Code" invers zur Realität);
    `test_tgh5_readme.py` prüft jetzt Liquidsoap statt VLC.
  Lebende RASTATIME-Feature-Pakete (`audio/`, `playout/now_playing`,
  `playout/engine_interface`, egress-Status-API) blieben erhalten.
  Kein User-sichtbares Verhalten geändert.  Details + Methodik:
  `CLEANUP_INVENTORY.md`.

- **Toter Celery-Worker `libretime_worker` entfernt (Cleanup §4-Bonus,
  2026-05-31)** — `backend/worker/` war seit T-GH-2 (Celery-Removal) nur
  noch ein Heartbeat-Stub; die echten Background-Tasks laufen direkt im
  API via HTTP.  Funktional ersetzt durch `backend/rastatime_worker`
  (Windows-native Runner, Phase-8-Vorbereitung).  Dabei behoben:
  `infra/nssm/install-worker.ps1` startete fälschlich `-m libretime_worker`
  (Z232) statt `-m rastatime_worker` — Header/Doku nannten bereits
  rastatime_worker; jetzt konsistent (+ `backend/` im PYTHONPATH).
  Obsoleter Celery-Guard `test_tgh2_no_celery.py` gelöscht.
  **⚠️ Operator-Aktion nötig:** der laufende RASTATIME-WORKER-Service
  nutzt aktuell `-m libretime_worker` (per `nssm get` verifiziert) → nach
  diesem Update `nssm set RASTATIME-WORKER AppParameters "-m
  rastatime_worker"` (oder Service neu installieren), sonst schlägt der
  nächste Worker-Neustart mit ModuleNotFoundError fehl.

### Changed

- **Line-In-Verwaltung jetzt unter Settings → Local Machine
  (2026-08-31, `1f60295`)** — Die eigenständige `/linein`-Seite hatte
  nie einen Settings-Menüeintrag und war praktisch unauffindbar
  (Operator fand nur den Library-Editor, der die Kanalwahl nicht
  kennt).  Der Inhalt lebt jetzt als Sektion **„Line-In Sources"**
  (mit Tooltip) oberhalb von Import Folder auf Local Machine — exakt
  der Ort, von dem das Panel beim Phase-A.4-Cleanup (2026-05-12)
  entfernt worden war; `/linein` leitet dorthin um, die
  Ajax-CRUD-Routen sind unverändert.  Außerdem trugen **Show
  Templates** und **Auto DJ** noch den Redmond-hellen
  `.ui-widget-content`-Wrapper → beide auf das dunkle
  `.prefpanel`-Muster der übrigen Settings-Unterseiten umgestellt.
  Live verifiziert (Redirect, Sektionsreihenfolge, Dialog inkl.
  Kanal-Picker, beide Seiten durchgehend dunkel).  Nachtrag
  (`d12c6ca`, Operator-Entscheid Option B): der schlanke
  Library-Schnell-Editor bleibt ohne Kanal-Feld, verlinkt aber unter
  dem Geräte-Feld auf den vollen Editor (neue Einträge starten mit
  Kanälen 1/2); Option A — Picker auch dort — liegt im BACKLOG.
  Manual in vier Sprachen nachgezogen (LINE_IN §3 ordnete die
  Kanalwahl fälschlich dem Schnell-Dialog zu; LOCAL_MACHINE-Wegweiser
  zeigt jetzt auf die On-Page-Sektion).

### Fixed

- **Line-In: Bearbeiten/Löschen bestehender Einträge schlug fehl
  (2026-09-01, `9f40ad2`)** — Operator-Fund auf der neuen
  Settings-Sektion: Update/Delete meldeten Fehler, Create ging.
  Ursache (so alt wie die nie benutzte Standalone-Seite): linein.js
  rief `/linein/update/<uuid>` bzw. `/delete/<uuid>` auf — Zends
  Default-Route paart überzählige Pfad-Segmente aber als
  Key/Value, die UUID wurde zum Parameter-**Namen**, `getParam('id')`
  blieb leer und der Controller sprach die Django-API mit leerer ID
  an.  Die ID reist jetzt als Query-Parameter (`?id=<uuid>`) an
  allen drei Aufrufstellen (Save, Delete, Enable-Toggle).  Live
  verifiziert: Edit-Roundtrip meldet Erfolg, beide alten
  „Untitled"-Duplikate ließen sich löschen.

- **Asset-Cache-Buster jetzt mtime-basiert (2026-08-31, `0767393`)** —
  `Assets::url()` las den `?<hash>` aus der build-zeitlichen
  `assets.json`: Datei-Edits änderten die URL nie, und da Apache
  keine Cache-Header für statische Assets sendet, klebten Browser
  tagelang an alten CSS/JS (heuristisches Caching; biss allein am
  2026-08-31 dreimal bei den UI-Fixes).  Der Hash kommt jetzt aus
  mtime+Größe der Live-Datei — jede Änderung ergibt sofort eine neue
  URL, Unverändertes bleibt stabil gecacht.  Strg+F5 nach UI-Fixes
  entfällt damit dauerhaft.

- **Weiße Rahmen um Kalender + Playout History → #242424 (2026-08-31,
  `5ff7713`)** — Kalender-Root-Cause war ein Ein-Zeichen-CSS-Bug vom
  2026-06-01: der Header-Kommentar von `schedule-fc6.css` schrieb eine
  Klassenliste als „.fc-agenda-*/.fc-header" — das Stern-Slash-Paar
  beendete den Kommentar vorzeitig, der Resttext wurde ein ungültiger
  Selektor, und die Browser-Fehler-Erholung verschluckte den kompletten
  `#schedule_calendar`-Block mitsamt aller FC6-Variablen (dunkler
  Rahmen, Grid `#3a3a3a`, dunkle Toolbar-Buttons, orange Now-Linie,
  Today-Tint-Kill) — das gedachte Dark-Theme wirkte nie.  Kommentar
  entschärft, Rahmen auf Operator-Spec `#242424`; das Sheet parst
  jetzt 16 statt 15 Regeln und der Kalender rendert erstmals das
  volle Design.  Playout History hatte schlicht keinen Override:
  `#his-tabs` (jQuery-UI-Tabs, `.ui-widget-content`) zeigte Redmonds
  Fast-Weiß als Rahmen — neue `#id`-Regel in `styles.css`
  (Background + Border `#242424`).  Beides live im DOM verifiziert.
  Feintuning nach Operator-Sichtung (`14752a4`, `b23056b`): beide
  Rahmen von `#242424` auf **`#3a3a3a`** aufgehellt und Redmonds
  hellblauer 1px-`.ui-widget-content`-Border am Kalender passend
  eingefärbt (1px bleibt — kein Layout-Shift).  Gleiche Ursache am
  **„+ New Show"-Panel** (`cd987dd`): `#schedule-add-show` bekam
  `#2f2f2f` und kippt die vererbte `#222`-Textfarbe auf Weiß (129
  Labels/DTs/DDs live verifiziert, explizit gefärbte Elemente
  unberührt).

- **Schedule-Tracks-Dialog: Tab-Wechsel tot, Header-Überdeckung,
  weißer Rahmen (2026-08-31, `3b1e23e`)** — Drei Ursachen: (1) Der
  hashchange-Handler des Dialogs rief `oTable.fnDraw()` — `oTable`
  ist aber eine library.js-**modul**-lokale Variable, nie global →
  ReferenceError bei jedem Tab-Klick, die Library blieb still auf
  Tracks stehen.  Jetzt über die öffentliche API
  (`AIRTIME.library.setCurrentTable(LIBRARY)`, das
  main_builder.js-Muster).  (2) Der fixe Dashboard-Header (`#Panel`,
  z-index 1000) überdeckte Titelzeile + obere Tab-Hälfte — und sogar
  das Modal-Overlay; redmond-1.13 gibt `.ui-front` nur z-index 100 →
  auf 1001 angehoben (jQuery-UI 1.13 stackt Dialoge per DOM-Reihenfolge
  auf der gemeinsamen Basis, kein Stacking-Bruch).  (3) Weißer
  Dialog-Rahmen + Buttonpane (Redmond `.ui-widget-content`) → neue
  `classes`-Hook `schedule-tracks-dialog` an beiden
  Kalender-Content-Dialogen (Schedule Tracks + Contents of Show) mit
  `#2f2f2f`-Regel.  Live verifiziert: Playlists-Klick lädt
  Playlist-Zeilen bei sauberer Konsole, Dialog liegt über dem Header.
  Nachtrag (`2715872`): die zwei Dauer-Anzeigen unter der
  Content-Tabelle des View-Dialogs (`#show_time_filled`,
  `#show_length`) erbten die `#222`-Basisfarbe → jetzt Weiß.
  Andere Browser brauchen wegen des versionsbasierten Cache-Busters
  einmal Strg+F5 (Folge-Item im BACKLOG).

- **Smart-Block-Save crashte auf PHP 8 bei unberührter Criteria-Zeile
  (2026-08-30, `5029a7c`)** — Root Cause des BACKLOG-Items „Smart
  Block speichern funktioniert nicht": der „Select criteria"-
  Platzhalter postet Key `'0'`, der Missing-Key-Zugriff lief auf
  PHP 8 in den non-nullable Return-Type von `BlockCriteria::get()`
  → TypeError → HTTP 500, vom Save-`$.post` ohne `.fail()`-Handler
  stumm geschluckt (Spinner hing).  Empirisch per Standalone-Harness
  bewiesen.  Fix: neutraler Platzhalter für unbekannte Keys (die
  gewollte Validierungsmeldung greift wieder), etc-Feld-Reads in
  `Block.php` null-coalesced (Datenverlust-Guard: die Methode DELETEt
  Kriterien vor dem Re-Insert), `.fail()`-Handler am Save-Post.

- **Dropzone-Init-Race: Recent-Uploads-Liste zog nach Upload nicht
  nach (2026-08-30, `8110b47`)** — Dropzone 4 Auto-Discover scannt
  das DOM vor jQuery 3s asynchronem `$(document).ready`, in dem die
  `Dropzone.options.*` (mit dem `success`-Refresh) erst zugewiesen
  werden → Zone initialisierte ohne Optionen.  Fix:
  `Dropzone.autoDiscover = false` + explizites `new Dropzone(...)`
  nach der Options-Zuweisung (Upload-Seite + Dashboard-Zone);
  `dropzone.min.js` wird vor den Options-Files geladen.

- **Playout-History-Feed gehärtet (2026-08-30, `4522e43`)** —
  Diagnose-Nebenfunde: SQL-Injection im File-Summary-Sort
  (client-gesendete Spaltennamen/Richtung liefen roh ins ORDER BY —
  jetzt Identifier-Whitelist + erzwungenes ASC/DESC) und beide
  `fnSetFilteringDelay(350)`-Aufrufe entfernt (kein „f" im sDom →
  das Plugin band `$('input', undefined)` = alle Inputs der Seite
  neu und riss den Datum/Zeit-Range-Pickern die Keyup-Listener ab).
  Der Haupt-Bug „Tabelle bleibt leer" reproduziert nicht mehr —
  in eingeloggter Browser-Session verifiziert (alle 3 Tabs rendern
  mit echten Daten, Export-Buttons da, Konsole sauber); der
  BACKLOG-Eintrag stammte von vor den historytable-Fixes vom
  2026-06-05 (`faf249d`) und war stale → geschlossen.

- **Django-Console-Logging: stdout, einmal, mit Timestamp
  (2026-08-30, `88e1071`)** — Der Console-`StreamHandler` des
  API-`LOGGING`-Dicts defaultete auf stderr und `propagate: True`
  doppelte jede Zeile über playouts Root-Logger — die stderr-Kopie
  erschien in PowerShell als roter `NativeCommandError`-Stack
  (BACKLOG „NativeCommandError-Noise beim Pypo-Start").  Handler auf
  `ext://sys.stdout`, `propagate: False`, Formatter angeglichen.

- **Phase-E-Webstream-Haker behoben — `localhost`→IPv6 fror die
  Playout-Clock ein (2026-08-30, `428805e` + cc_pref-Update)** — Root
  Cause des BACKLOG-Items „Phase-E Polish: Webstream-Buffer + Switch-
  Verhalten": Windows löst `localhost` AAAA-first auf, Icecast 2.4.4
  lauscht IPv4-only → jeder ICY-Metadata-Call der Icecast-Outputs
  (pro Trackstart, mp3+aac) blockierte ~5 s im IPv6-Connect und fror
  die Liquidsoap-Hauptclock ein (~10 s gestapelt). Webstream-Shows:
  Freeze-Catchup leerte den 5-s-Brückenpuffer → Switch-Ping-Pong alle
  ~11 s; Datei-Shows: hörbare Mikro-Stalls an jedem Trackwechsel.
  Empirisch bewiesen im isolierten Testbett (T9 localhost: 25 Tracks =
  25 Catchups 1:1; T10 127.0.0.1: 26 Tracks = 0). Fix: Stream-Settings-
  Hosts auf `127.0.0.1` + Renderer normalisiert `localhost` künftig
  automatisch (`_normalize_loopback_host`, +6 Tests, 81/81).
  **Validierung abgeschlossen (2026-08-31):** vier
  Webstream-Show-Fenster über den Tag — 08:07 → 0 Catchups, 12:07 →
  3 einmalige Start-Einschwinger (0,5–1 s, erste 15 s), 17:07 → 0,
  19:00 (Extra-Test, frisch neu gestarteter Liquidsoap) → 0 inkl.
  sauberem Start- und End-Übergang.  Vorher-Referenz: 12 Catchups +
  Switch-Ping-Pong in einem einzigen Fenster.

- **Podcast-Downloads erben jetzt die Library-ACL (2026-08-27, `a34f914`)** —
  Root-Cause des BACKLOG-Items „ACL sperrt den studio-User aus":
  `download_episode()` lud in den %TEMP% des Dienstkontos und
  `shutil.move` = Same-Volume-**Rename behält die NTFS-ACL** — die
  restriktive SYSTEM-Temp-ACL wanderte in `media\imported\`, jedes
  nicht-elevated Backup übersprang die Episoden still (robocopy
  exit ≥ 8; real passiert beim Migrations-Transfer 2026-06-17 und
  erneut am 2026-08-26).  Fix: Temp-Datei wird direkt im Ziel-Ordner
  geboren (`NamedTemporaryFile(dir=import_dir)`) + `os.replace` im
  selben Ordner → erbt die Library-ACL ab Erstellung.  Regressionstests
  (`podcasts/tests/test_download.py`, Temp-Dir-Spy + Failure-Cleanup);
  E2E auf der Live-Library verifiziert (`studio:(I)(F)` vererbt).
  Flankierend: BACKUP.md warnt jetzt vor nicht-elevated Medien-Copies
  und prüft das robocopy-Log (`3c5d413`).

- **`status.ps1` meldet kein falsches „alles läuft" mehr (2026-08-27,
  `e1bfc11`)** — das Status-Werkzeug (erster Schritt jedes Notfall-
  Runbooks) kannte nur die 4 Ur-Dienste und druckte „All mandatory
  services are Running", selbst wenn ANALYZER/APACHE/LIQUIDSOAP down
  waren (= Uploads hängen / kein Web-UI / Stille auf Sendung).  Jetzt:
  alle 7 Dienste inkl. HTTP-Proben (API `:8765/health`, Apache `:80`,
  Icecast `:8000`), korrigierte Port-Tabelle (Icecast 8000 statt 8001,
  nicht mehr „optional"), Install-Hints pro Dienst.  Die
  „prüfe die anderen drei separat"-Workarounds aus `3c5d413` sind
  wieder aus INSTALL/RESTART_ORDER/CRASH_RECOVERY/README entfernt.
  Live getestet: 7× Running, 3× HTTP 200.  Außerdem `run-api.ps1`
  (Dev-Helfer) Default-Port 8000 → **8766** (Operator-Entscheid:
  kollidiert weder mit Icecast 8000 noch mit dem Produktions-API-Dienst
  8765; parallel zum vollen Stack getestet), WINDOWS_DEV_STATUS.md
  nachgezogen.

- **Datei-Upload (REST-CSRF) repariert — `csrf`-Formularfeld akzeptiert
  (2026-06-05, `1f66224`)** — Uploads auf `/rest/media` (Dashboard-Dropzone)
  scheiterten: der Zend-CSRF-**Form**-Element-Feldname ist `csrf`, der ACL-Plugin
  las aber `csrf_token` → `getParam('csrf_token')` leer → Fallback auf
  `json_decode(body)` (bei multipart leer) → `verifyCSRFToken(null)` → **401** bei
  jedem Upload.  Auf PHP 8 warf der alte `null['csrf_token']`-Body-Fallback
  zusätzlich „Trying to access array offset on null" → **500**.  Fix: der
  ACL-Plugin akzeptiert nun `csrf` **oder** `csrf_token` (`csrf_token` bevorzugt →
  plupload / PUT-JSON / Query-String unverändert) + Null-Guard für
  nicht-JSON-Bodies.  Hintergrund: der Dropzone-`sending`-Hook, der `csrf_token`
  anhängen würde, feuert auf jQuery 3 nicht rechtzeitig (sein
  `$(document).ready`-Setup läuft einen Microtask nach Dropzones Auto-Discover) —
  gelesen wird daher das zuverlässig gesendete statische `csrf`-Formularfeld,
  timing-unabhängig.  Vorbestehender Backend-/PHP-8-Bug, kein jq3-Flip-Blocker
  (läuft auf Legacy identisch).  Operator-verifiziert: Upload läuft auf `?jq3=1`
  **und** `?jq3=0`, Track erscheint in der Library.

- **Live-Stream im Embed-Player für Remote-Hörer erreichbar gemacht
  (2026-06-01, `bd5d9ca`)** — der Embed-Player (Muses `Html5Player`, u.a. der
  Live-Stream-Player auf der Radio-Page) spielte die konfigurierte Stream-
  `public_url` wörtlich ab.  Bei `host = localhost` (hiesige Default-Konfig)
  bekam ein Remote-Hörer `ERR_CONNECTION_REFUSED`, weil `localhost` auf seinen
  eigenen Rechner zeigt.  `reachableStreamUrl()` schreibt jetzt
  `localhost`/`127.0.0.1` auf den Host um, über den die Embed-Seite
  ausgeliefert wird (`window.location`); ein expliziter Host (Domain /
  dedizierter Icecast, z.B. für externe Einbettung) bleibt unangetastet.
  Vorbestehendes Stream-Config-Thema, kein Regression — dasselbe Muster wie
  zuvor im Dashboard-Stream-Player.  Operator-verifiziert remote.

- **Irreführende/gefährliche VLC-Engine-Doku korrigiert (2026-05-31)** —
  `README.md` + `FORK_NOTES.md` beschrieben libVLC noch als „mandatory
  main playout engine" bzw. „in development", obwohl RASTATIME seit
  2026-05-28 (Phase-C5) produktiv auf **Liquidsoap** läuft (mpv =
  Legacy-Fallback, VLC = aufgegebener Plan). Auf die Liquidsoap-Realität
  korrigiert. `POST_IMPLEMENTATION.md` (datierter Fahrplan 2026-05-03)
  mit Banner + Inline-Warnung versehen: insbesondere **T-GH-1**
  („Liquidsoap-Ordner als toten Code löschen") ist invers zur Realität
  und würde die Produktions-Engine zerstören — explizit als UNGÜLTIG
  markiert. Grundlage: neue datei-genaue `CLEANUP_INVENTORY.md` (kartiert
  toten VLC-Code, `libretime`→`rastatime`-Aufwand, `airtime`-Heritage).

- **Error-Page (`error-500.phtml`) Grafik + Links (2026-05-29)** —
  `images/maintenance.png` durch eine RASTATIME-eigene Broadcast-Tower-
  Grafik ersetzt (Orange-Akzent #e76400 + Warn-Badge, 360×340,
  transparent).  "Troubleshooting"-Button zeigt jetzt auf die lokale
  User/Operator-Help (`dashboard/help`) statt die externe
  libretime.org-Troubleshooting-URL; separater "More help"-Button
  entfernt.  Text "Oops! / Something went wrong!" unverändert.

- **`docs/operator/MIGRATION.md` Storage-Pfad-Bug (2026-05-29)** —
  die Doku referenzierte `C:\rastatime\stor` (existiert nicht); der
  echte Storage-Pfad ist `C:\rastatime\media` (libretime.conf
  storage.path).  Hätte beim Media-Backup die gesamte Library
  verfehlt.  Korrigiert + media\ aus dem Repo-Backup ausgeschlossen
  (wird separat gesichert).

### Changed

- **Operator-/Architektur-Doku auf den realen Liquidsoap-Stack
  nachgezogen (2026-08-27, `3c5d413`)** — 15 Docs + 2 Skript-Header:
  API-Port 8765 überall (8000 = Icecast), 7-Dienste-Topologie inkl.
  ANALYZER/APACHE/LIQUIDSOAP, RabbitMQ+Erlang als Pflicht-Prereq,
  INSTALL.md-Neuaufbau (Windows-Prep/SAC, venv-Sequenz inkl.
  psycopg2, Step 9a–9h mit Engine-Env, DB-Rolle `rastatime`),
  MIGRATION.md ohne den nie funktionierenden `nssm dump`-Pfad
  (NSSM 2.24 kennt kein `dump`; Fresh-Install ist der dokumentierte
  Weg) + dediziertem `pg_dump -Fc`-Bundle-Schritt + §4.9
  (`rastatime.liq` rendert der Playout-Startup — der CLI-Render
  strippt die DJ-Harbors, live am 2026-08-27 passiert), DJ-Harbor-
  Wahrheit `/main`+`/show` teilen Port 8001 (2.4.4-Workaround),
  LINE_IN_BROKEN-Debug-Rezept ohne Env-Block-Wipe, INSTALL_APACHE
  (VC-Redist, Module, HTTP_AUTHORIZATION-Rewrite, /api/v2-Proxy),
  `bootstrap.ps1` Required/Optional-Tausch.  Agenten-gestützter
  Audit (94 Findings) + adversarialer Verify-Pass (43 Findings).

- **Song Requests: echte Mid-Show-Befüllung (2026-06-16, Mid-Show R1,
  `a820bdf`)** — Eine Request-Show löst ihre Dramaturgie nicht mehr in einem
  Pass ~8 min vor Start auf, sondern **inkrementell während der Sendung**: pro
  2-Min-Poll nur die nächste(n) Position(en) bis
  `now + RASTATIME_REQUEST_FILL_AHEAD_SECONDS` (Default 300 s) vor dem Play-Head.
  Ein „use requests"-Block weiter hinten in der Dramaturgie wird damit erst
  aufgelöst, wenn er gleich dran ist, und zieht die Wünsche, die **während** der
  laufenden Show eingingen (statt sie in die nächste Show zu verschieben).  Ein
  persistenter Positions-Cursor (`cc_show_instances.autoplaylist_cursor`,
  Legacy-Migration 0057, raw-SQL) merkt sich den Fortschritt über die Polls;
  sobald die Dramaturgie durch ist, füllt der time-remaining-Block den Rest
  **komplett** bis zum Show-Ende (Dead-Air-Fenster auf die kurze Dramaturgie
  begrenzt).  **Kein Playout-Eingriff** — pypos `PypoLiqQueue` ersetzt bei
  jedem `PushSchedule` die Zukunfts-Deque und pusht Items zur Startzeit, nimmt
  einen Mid-Show-Insert also auf.  Regler
  `RASTATIME_REQUEST_FILL_AHEAD_SECONDS` (kleiner = frischere Requests, größer =
  mehr Dead-Air-Sicherheit; > 2-Min-Poll halten).  Live-verifiziert (ein um
  15:01 — nach der Vorab-Befüllung — gewünschter Track lief in derselben Show).
  Doku: SONG_REQUESTS §5/FAQ (EN/DE/FR/ES), ARCHITECTURE §23.23.

- **jQuery 3.7 + DataTables 1.13 als Default aktiviert (JS-Modernisierung
  Stufe 5a, 2026-06-05, `87c1d35`)** — nach bestandener app-weiter Verifikation
  (Stufe 4) wurde der `?jq3`-Default von **jQuery 1.8 + UI 1.8 + DataTables 1.9**
  auf **jQuery 3.7.1 + jquery-migrate 3.5.2 + jQuery UI 1.13.3 + DataTables 1.13**
  umgestellt (`rtUseJquery3()` Default `false → true` — eine Stelle, geteilt von
  App-Layout + Radio-Page; `rtDataTablesCore()` hängt am selben Flag, 1.13 folgt
  also im Gleichschritt, da 1.9 nicht jQuery-3-kompatibel ist).  Ohne Flag/Cookie
  lädt jetzt der moderne Stack.  Rückwege: **`?jq3=0`** = sofortiger
  per-Session-Rollback (Cookie-persistent), Commit-Revert = global.
  **jquery-migrate bleibt als Sicherheitsnetz**, bis die JQMIGRATE-Warnungen
  seitenübergreifend sauber sind (**Stufe 5b** entfernt das Netz + die
  Legacy-1.8/1.9-Assets — separater, späterer Schritt).  Keine
  `assets.json`-Änderung (jq3-Assets längst registriert) → reiner Loader-Default.
  Live-verifiziert: Login lädt ohne Flag jquery-3.7.1 + migrate + UI 1.13.3
  (HTTP 200), `?jq3=0` weiterhin jquery-1.8.3 + UI 1.8.  Voraus ging die Migration
  in Stufe 2–4: 29 `.live()`→`.on()`, jQuery-UI-1.13-Event-Umbau (tabs `activate`,
  accordion-Guard), DataTables-1.13-sDom-Umbau aller Widget-Tabellen +
  columnFilter-Neubau, Flot 0.7→0.8.3, REST-CSRF-Upload-Fix.

- **Schedule-Kalender von FullCalendar 1.5 auf FullCalendar 6 umgestellt
  (JS-Modernisierung Stufe 2, 2026-06-01, `8ce8ec1` + `5abaab5` + `169106d` +
  `688e466` + `81d8c8d` + `be429da`)** — der geforkte, EOL-FullCalendar 1.5.4 (jQuery-Plugin,
  2011) auf der Schedule-Seite wurde durch das bereits für das Embed-Multi-View-
  Widget vendorte **FullCalendar 6.1.10** (vanilla, kein jQuery) ersetzt. Neue
  Datei `schedule-fc6.js` (`buildScheduleFc6()`), schrittweise hinter `?fc6=1`
  gebaut und verifiziert, jetzt **Default** (FC1.5 als Rollback via `?fc6=0` +
  Safety-Net, falls die FC6-Datei nicht lädt; Fork-Entfernung deferred, s.
  BACKLOG). Migriert wurde **funktionsgleich**:
  - *Zeitzone*: Server liefert naive Stationszeit-Strings; FC6 (`timeZone:'local'`
    + natives `now` auf Stationszeit) rendert die Wand-Uhr-Zeit verbatim →
    Stationszeit in jedem Browser, ersetzt den FC1.5-`serverTimezoneOffset`-
    Handpatch des Forks.
  - *Anzeige*: drei Views (timeGridDay/Week + dayGridMonth) auf die
    Legacy-Präferenz gemappt; Status-Icons (empty/partial/overbooked/linked/
    autoplaylist/rebroadcast/now-playing) + jQuery-UI-Fill-Bar + Hover-Tooltips
    aus `eventRender()` portiert; Show-Farben, 60-s-Auto-Refresh, Grid-Dropdown
    (1/5/10/15/30/60m), Höhe via `contentHeight`. Back-to-back-Shows voll-breit
    (`slotEventOverlap:false` + `inset-inline:0`-Override, da FC6 Touch-Boundaries
    als geteilte Spalten wertet). Deutscher Week-Titel via `Intl.formatRange`
    (Ordinal-Punkt, vdom-sicher über `titleFormat`).
  - *Interaktion*: `dateClick`→Add-Show-Formular (alle Recurrence-Rhythmen
    unverändert: weekly+Wochentage, every 2/3/4 weeks, monthly day-of-month,
    monthly day-of-week, 5. Donnerstag), Links-Klick-ContextMenu (Selektor
    `div.fc-event`→`.fc-event`, da FC6-Events `<a>` sind), Drag→`move-show`,
    Resize→`resize-show`, per-Event-Editierbarkeit aus dem Feed. Geteilte Helfer
    (`scheduleCalRefetch`, `windowResize`, `makeAddShowButton`, …) Engine-
    agnostisch gemacht (per `SCHEDULE_USE_FC6` geguarded → FC1.5-Pfad
    verhaltensgleich). Geschäftslogik (Endpoints, Add-Show-Formular) unangetastet.
  - *Design* (`be429da`): dediziertes `css/schedule-fc6.css` stellt den dunklen
    LibreTime-Look wieder her (FC6 ist hell; der alte kam aus jQuery-UI
    `theme:true`) — graue Tagesleiste, dunkle Zellen + Grid-Linien, graue
    Toolbar-Buttons, Brand-Orange Now-Linie, kein gelber Today-Tint, dezente
    Event-Kanten, Fill-Bar-Fix für Kurz-Events, No-Leading-Zero-Uhrzeiten
    („8:00"). Scoped auf `#schedule_calendar` → Rollback/Embed unberührt.
  - Operator-verifiziert auf beiden Pfaden (FC6 + FC1.5-Rollback). Entfernt eine
    jQuery-Abhängigkeit (Stufe-2-Ziel: Vorarbeit für jQuery 1.8→3.7).

- **Alle Tooltips von qtip2 auf rtTooltip (Floating UI) umgestellt
  (JS-Modernisierung Stufe 1, 2026-06-01, `f07c53c` + `4cba934`)** — ein neuer
  schlanker `$.fn.rtTooltip`-Wrapper auf Floating UI (computePosition +
  offset/flip/shift/arrow) ersetzt qtip2.  Der Wrapper akzeptiert sowohl eine
  saubere API als auch die alte qtip2-Optionsform (Kompat-Schicht: placement aus
  `position.at`, interactive aus `hide.fixed`, extraClass aus `style.classes`,
  Titel/Close-Button aus `content.title`, dismissable aus `hide.event:"unfocus"`,
  light-Theme aus `style.name`, show-on-init aus `show.ready`, `overwrite`),
  sodass die meisten Aufrufstellen per `.qtip(`→`.rtTooltip(`-Rename migrierten.
  ~31 Tooltips über 14 Dateien; dunkel-abgerundeter Look (`css/tooltip.css`) wie
  zuvor.  Operator-verifiziert (Streams, Add-Show, Calendar-Icons,
  Users-Dropdown, Smart-Block/Podcast u.a.).

- **Publish-Dialog + Podcast-/StationPodcast-Editoren von AngularJS auf
  vanilla/jQuery (JS-Modernisierung Stufe 1, 2026-06-01, `6b79128` + `ede7c12`)**
  — die drei AngularJS-Controller (Publish, Podcast, StationPodcast) wurden ohne
  Framework neu verdrahtet: `$http`→`$.ajax` (mit `dataType:"json"`, da die
  REST-API JSON ohne `application/json`-Content-Type liefert — sonst lieferte
  jQuery rohe Strings), 2-Wege-`ng-model` → Laden/Lesen der Formulare per
  `[data-field]`, `ng-click`/`ng-show`/`ng-repeat` → Vanilla-Handler/Toggle/
  Rendering, `angular.bootstrap` → schlichte Init-Funktionen.  ~750 Z.
  DataTables-Code (Podcast-Episoden) blieben unberührt (Low-Diff-Strategie:
  „Zuverlässigkeit vor Modernität").  Operator-verifiziert (Publish/Unpublish,
  Podcast anlegen/bearbeiten/speichern, Smartblock, Station-Metadaten + Privacy,
  Episoden-Tabelle).

- **Audio-Player im LibreTime-Look wiederhergestellt (Custom-GUI auf nativem
  `<audio>`, 2026-06-01, `6312961` + `69ab09a`)** — die nach der jPlayer-Ablösung
  rohen Browser-`<audio controls>` von **Audio-Preview** und
  **Dashboard-Stream-Player** haben wieder einen custom jPlayer/LibreTime-Skin:
  dunkle Gradient-Leiste, orange (`#FF6F01`) Seek-/Volume-Balken, per CSS
  gezeichnete Transport-Buttons (kein jQuery-UI-/Bootstrap-/Sprite-Abhängigkeit),
  Zeitanzeige + Mute, an das native Element gebunden.  Preview: Playlist +
  Prev/Next (nur bei Mehr-Track), Popup ~20 % schmaler (384px) ohne Scrollbalken.
  Dashboard: Live-Stream mit play/pause/stop (Stop trennt, Play verbindet neu) +
  „● LIVE"-Marker, kein Seek.  Operator-verifiziert.  Die Radio-Page behielt ihr
  Skin bereits (Teil 3/3).

- **Radio-Page Podcast-Player von jPlayer auf natives `<audio>` umgestellt
  (JS-Modernisierung Stufe 0, jPlayer Teil 3/3, 2026-06-01, `86a4ef0`)** — der
  Station-Podcast-Episoden-Player auf der öffentlichen Radio-Page nutzt jetzt
  ein vanilla natives `<audio>` + einen kleinen `_podcastPlayer`-Manager statt
  `jPlayerPlaylist`.  Das custom jPlayer-Skin (`station-podcast.css`,
  `#jp_container_1`) bleibt auf Operator-Wunsch erhalten und wird nativ
  angesteuert: Play/Pause-Sichtbarkeit per `display`-Toggle (so funktioniert der
  bestehende Block-2-`.jp-play:hidden`-Check weiter), Seekbar klick-zum-Springen,
  Volume-/Mute-/Max-Bar, Laufzeit-Anzeige, `ended`→nächster Track; Pagination +
  Description-Toggle unverändert.  `IndexController` lädt kein per-page jPlayer
  mehr.  Operator-Browser-verifiziert (alle Controls + Pagination).  Der
  Live-Stream-Player (Embed-iframe) ist separat und unberührt.  Damit war
  jPlayer auf dieser Seite abgelöst → Lib global entfernbar (s. *Removed*).

- **Dashboard-Stream-Player von jPlayer auf natives `<audio>` umgestellt
  (JS-Modernisierung Stufe 0, jPlayer Teil 2/3, 2026-05-31, `b2b11b4`)** — der
  Live-Stream-Player im Dashboard-Popup nutzt jetzt ein vanilla natives
  `<audio>`-Element statt jPlayer; die jPlayer-Skin-CSS
  (`jplayer.blue.monday.css`) entfällt.  Operator-verifiziert remote mit allen
  drei aktiven Streams (mp3 / aac / opus).  **Erreichbarkeits-Fix dabei:** der
  Stream-`host` ist als `localhost` konfiguriert (nur auf dem Server selbst
  auflösbar) → ein Remote-Browser bekam `ERR_CONNECTION_REFUSED`.
  `reachableStreamUrl()` schreibt `localhost`/`127.0.0.1` jetzt auf den Host um,
  über den die App aufgerufen wird (`window.location`), für Wiedergabe **und**
  Share-Link; ein expliziter Host (Domain / dedizierter Icecast) bleibt
  unangetastet.  War ein vorbestehendes Stream-Config-Thema, kein Regression
  (jPlayer lud dieselbe URL).  **jPlayer-Lib lädt weiter global** — die
  Radio-Page (`index.phtml`) ist der letzte Nutzer (Teil 3/3), danach kann die
  Lib + der globale Load entfernt werden.

- **Zweite Tooltip-Lib (Tipsy) entfernt, auf qtip2 konsolidiert
  (JS-Modernisierung Stufe 0b, 2026-05-31, `38c4525`)** — Tipsy (2012,
  lokal geforkt, EOL) wurde global auf jeder Seite **neben** qtip2 geladen,
  aber nur an **einer** Stelle genutzt (`user.js`, der User-Rechte-Tooltip am
  `#type`-Dropdown).  Diese eine Stelle wurde auf qtip2 (die überall sonst
  genutzte Tooltip-Lib, 30+ Stellen) migriert; Tipsy danach komplett entfernt
  (globaler CSS+JS-Load aus `PageLayoutInitPlugin`, 4 Dateien gelöscht,
  3 `assets.json`-Einträge raus).  qtip2 bringt einen eingebauten
  `.ui-tooltip-tipsy`-Stil mit → die dunkle Optik bleibt 1:1.
  Operator-Browser-verifiziert (Tooltip erscheint nur bei Hover/Fokus,
  aktualisiert sich bei Typ-Wechsel).  Nebenbei zwei veraltete 0c-Asset-Hashes
  korrigiert (`audioplaytest.js`, `spl.js`).

- **Audio-Preview von jPlayer auf natives `<audio>` umgestellt
  (JS-Modernisierung Stufe 0c, Teil 1/3, 2026-05-31, `9792349`)** — der
  Vorschau-Player (Library-Einzeltrack, Playlist, Block, Show, geplanter
  Webstream) nutzt jetzt ein vanilla natives `<audio>`-Element statt des
  archivierten jPlayer (2014) + dessen Playlist-Plugin + Skin-CSS.  Neuer
  `preview_audio.js` (IIFE, behält die globalen Einstiegspunkte
  `playAllPlaylist`/`playBlock`/`playAllShow`/`stopPreview`, baut die Queue
  per `fetch` aus den bestehenden JSON-Endpoints, eigener Playlist-Manager
  mit next/prev + ended→next).  `AudiopreviewController` lädt in allen vier
  Preview-Actions `preview_audio.js`; JSON-Endpoints unverändert.  Toter
  Flash-Fallback in `audioplaytest.js` entfernt (native `canPlayType` ist
  maßgeblich).  Operator-Browser-verifiziert (Einzeltrack, Playlist, Block/
  Show, geplanter Webstream).  **jPlayer-Lib bleibt vorerst** — Dashboard-
  Stream-Player + Radio-Page nutzen sie noch (Teil 2/3 + 3/3, s. `BACKLOG.md`).
  Player-Styling ist aktuell roh (Browser-Default); LibreTime-Optik wird
  separat wiederhergestellt (Backlog).

- **Scheduled Line-Inputs via Liquidsoap `input.ffmpeg(dshow)`
  (Phase-F-2, 2026-05-30)** — die Audio-Erfassung geplanter
  Line-In-Items läuft jetzt direkt in Liquidsoap über
  `input.ffmpeg(format="dshow")` (in-process libavdevice), statt über
  den separaten `FfmpegLineinCapture`-Subprozess + `input.http`-Hop aus
  Phase F.  Ein Tool weniger im Signalweg: Liquidsoap öffnet das
  Windows-dshow-Device selbst, Pypo baut nur noch den
  dshow-Alternative-Name-Spec aus der Device-GUID und reicht ihn per
  Telnet an `linein.set_url` / `linein.start`.  `FfmpegLineinCapture`
  wird im Liquidsoap-Mode nicht mehr für die Audio-Erfassung verwendet;
  daraus importiert wird nur noch der reine Helper
  `_stable_id_to_dshow_audio` (dshow-Spec aus Device-GUID).

  Zwei im Live-Test (2026-05-29) gefundene Bugs sind hier enthalten:
  - **Device-Wechsel zwischen Shows** — `set_url` auf einer bereits
    laufenden `input.ffmpeg`-Quelle ist ein No-Op; das Device wechselt
    nur, wenn die Quelle vorher gestoppt wird.  Fix: `linein_start`
    nutzt **Mechanismus B** (stop → set_url → start), dasselbe Muster
    wie `recording_start`.
  - **Timer-Race beim Show-Übergang** — feuerten die
    `threading.Timer`-Callbacks zweier aufeinanderfolgender Shows in
    der Reihenfolge "Stop-der-alten nach Start-der-neuen", killte das
    `linein_stop` der alten Show die frisch geöffnete Quelle der neuen
    (Stille, live beobachtet 21:15:00).  Fix: ein generationsbasierter
    Guard (`_linein_generation`) in `_on_stop` — lock-frei und auf den
    Line-In-Teardown beschränkt, sodass Webstream/File-Übergänge (wo
    Webstream im Bus-Switch über Line-In rankt) unberührt bleiben.

- **NSSM-Service `RASTATIME-LIQUIDSOAP` DisplayName (2026-05-29)** —
  war "RASTATIME Liquidsoap" (mit Leerzeichen), passte nicht zum
  Service-Namen den `nssm`-Befehle + Doku nutzen.  Jetzt überall
  konsistent "RASTATIME-LIQUIDSOAP".  (Operator führt `nssm set
  RASTATIME-LIQUIDSOAP DisplayName "RASTATIME-LIQUIDSOAP"` auf der
  Live-Maschine aus; das Install-Script deckt Fresh-Installs ab.)

- **`docs/operator/MIGRATION.md` Storage-Bereinigung (2026-05-29)** —
  §4.4 + §4.5 erweitert um die Storage-Struktur-Bereinigung als Teil
  der Hardware-Migration: neuer Root `D:\stor` (SSD-B, außerhalb des
  Projektordners) + Wegfall der `imported/<owner-id>/`-Ebene.
  Enthält Code-Patch (MediaService.php), DB-Transaktion (cc_music_dirs
  + cc_pref + regexp_replace auf cc_files.filepath) und robocopy-
  Flattening.  Operator-Entscheidung: Daten-Migration im geplanten
  Wartungs-Stopp statt riskant auf der Live-Maschine.  Details in
  BACKLOG "Storage-Struktur-Bereinigung".

### Added

- **24/7-Aufnahme (Record-per-Hour) — durchgehendes Stunden-Archiv
  (2026-06-06, `80c3dbf` + `0127ff0` + `7b9a8bc` + `84c5c34` + `9b3d857`)** —
  ein kontinuierlicher Archiv-Recorder als zweiter Liquidsoap-`output.file`
  auf dem Bus, der rund um die Uhr aufnimmt und **stündlich rotiert** —
  unabhängig von Shows, erfasst also auch die Lücken, die Record-per-Show
  verpasst (AutoDJ-Filler, Stille, Unscheduled, Notfälle).  Für Compliance,
  Catchup und Notfall-Backup.  Konfiguration unter **Settings → Local
  Machine → „24/7 Recording Folder"** (oberhalb des in „Show Recording
  Folder" umbenannten Per-Show-Felds): Enable, Ordner (wird beim Speichern
  angelegt), Format (MP3/AAC/OGG/Opus, Default 192 kbps MP3), Bitrate,
  „Delete after (days)".  Dateien
  `<Ordner>/<YYYY-MM-DD>/<YYYY-MM-DD HH>-00.<ext>` in lokaler Zeit, nahtlose
  Stundenübergänge.  Bausteine:
  - **Recorder** (`80c3dbf`): `_render_hourly_recording_block` im
    `liquidsoap_config`-Renderer (`reopen_when`-Rotation; `seg` auf die
    aktuelle Stunde geseedet → kein Boot-Reopen; Tages-Unterordner via
    `file.mkdir`).  Per **Default aus** → Kommentar-Stub, Live-Stream
    unberührt bis zum Einschalten.
  - **Retention** (`0127ff0`): Pypo-Daemon löscht Tages-Ordner älter als N
    Tage (nur `YYYY-MM-DD`-Ordner im 24/7-Pfad; `0` = ewig behalten).
  - **Settings-UI** (`7b9a8bc` + Auto-Create-Fix `84c5c34`): neue Sektion +
    Umbenennung „Recording Folder" → „Show Recording Folder",
    jQuery-3-saubere Save-Handler auf dem jq3-Default.
  - **Cue-Sidecars** (`9b3d857`): pro Stunde ein `…-00.cues.json` mit
    Track-/Show-/Webstream-/Line-In-Marken (Offset in Sekunden ab
    Stundenbeginn) für den späteren Catchup-Player.
  Neu auf die **Phase-C5-Liquidsoap-Aufnahme-Architektur** aufgesetzt (der
  ursprüngliche 2026-05-22-FFmpeg-Tap-Plan war seit dem FfmpegRecorder-Delete
  obsolet).  Live-verifiziert: 11-h-Lauf, fast alle Dateien exakt 60 min,
  nahtlose Übergänge; 266 Playout-Tests grün (Render/Retention/Cue).  Manual:
  neues Kapitel `RECORD_PER_HOUR.md` + `LOCAL_MACHINE.md`-Update.

- **Floating UI (vendored) + rtTooltip-Helper (2026-06-01, `f07c53c`)** — die
  moderne Positionierungs-Lib Floating UI (UMD core+dom, ~22 KB) unter
  `js/libs/floating-ui/`, plus `js/airtime/common/tooltip.js` (rtTooltip) +
  `css/tooltip.css` — die Grundlage der qtip2-Ablösung (s. *Removed* /
  *Changed*).  Vanilla-First, kein Build-Schritt.

- **„My Podcast" (Station-Podcast) im Hauptmenü (2026-06-01, `b30326e`)** — die
  Station-Podcast-Seite (`/podcast/station`) war funktionsfähig, aber nur per URL
  erreichbar; der Menüeintrag war upstream deaktiviert (libretime#1320, Feature
  dort unfertig).  Nach der Vanilla-JS-Migration funktioniert sie in RASTATIME,
  daher bekommt sie einen Top-Level-Menüeintrag direkt über „Calendar"
  (Bullhorn-Icon, admin-sichtbar via `resource 'preference'`).

- **Scheduled Line-Inputs via Liquidsoap `input.http` (Phase-F,
  2026-05-29)** — geplante Line-In-Items im Schedule fließen jetzt
  durch die Liquidsoap-Engine.  Pattern analog zu Phase E
  (Webstreams), nur einfacher weil die HTTP-URL fix ist
  (`http://localhost:8000/linein-capture`, FfmpegLineinCapture's
  lokaler Icecast-Mount) und LineinEvent kein gain-Feld hat.

  **Konsequenzen für den Operator:**
  - **Line-In-Shows landen jetzt im Liquidsoap-Recording** — vorher
    waren reine Line-In-Shows still im .mp3-Archiv, jetzt komplett
    aufgenommen.
  - **Multi-Device-Support bleibt erhalten** — Pypo's
    FfmpegLineinCapture nutzt weiterhin die Windows-Audio-Endpoint-
    GUID aus dem Schedule-Item; Liquidsoap konsumiert nur den
    lokalen Icecast-Mount und kennt das Device nicht direkt.
  - **Hot-Plug-Recovery (USB-Cable raus/rein)** funktioniert
    weiterhin — FfmpegLineinCapture's Watchdog kümmert sich darum.
  - **Initiale Show-Latency ~5 s** (analog zu Webstream-Buffer).

  **Architektur-Entscheidung 2026-05-29:** Option B (input.http +
  bestehendes FfmpegLineinCapture) statt Option A (input.portaudio
  direkt).  Gründe:
  - `input.portaudio` hat **keine `set_device`-Method zur Laufzeit**
    → Device-Wechsel zwischen Shows würde Liquidsoap-Restart
    erfordern (Stream-Glitch).
  - `input.portaudio` nutzt PortAudio-Integer-Indizes (nicht stable
    across reboots), inkompatibel mit unserem Windows-Audio-Endpoint-
    GUID-System im Frontend.
  - `input.portaudio` hat keinen Auto-Reconnect bei USB-Plug-Out;
    FfmpegLineinCapture's Watchdog macht das transparent.
  - `input.external.rawaudio` mit ffmpeg-Pipe wäre möglich, aber PR
    [savonet/liquidsoap#5139](https://github.com/savonet/liquidsoap/pull/5139)
    (2026-05-06) zeigte einen Crash-Bug bei Subprozess-EOF.  Umgehen
    wir komplett indem wir ffmpeg als Pypo-Subprozess + Liquidsoap-
    HTTP-Konsum nutzen.

  Implementation:
  - Template `rastatime.liq.template`: neuer `${LINEIN_INPUT_BLOCK}`
    Placeholder mit `input.http(id="linein", start=false,
    self_sync=false, ..., "<FfmpegLineinCapture-URL>")` +
    `buffer(buffer=5.0, linein_raw)` Clock-Bridge-Wrapper.  Switch-
    Block um neuen Arm zwischen webstream und scheduled erweitert.
  - `liquidsoap_telnet.py`: 4 neue Convenience-Methoden
    (`linein_set_url`, `linein_start`, `linein_stop`,
    `linein_status`).
  - `liquidsoap_engine.py`: `linein_start(url=None)` / `linein_stop()`
    / `linein_status()` mit fail-soft try/except.  URL ist optional
    weil das Template eine fixe URL hard-codet.
  - `playout_scheduler.py`: `_on_linein_start` branches in der
    SCHEDULED-path auf `streaming_handled_externally` — Liquidsoap-
    Path ruft zusätzlich `engine.linein_start()` (FfmpegLineinCapture
    wird wie zuvor gestartet); `_on_stop` ergänzt um `was_linein` +
    Liquidsoap-Branch.
  - Tests: 22 neue (5 Renderer + 5 Telnet + 6 Engine + 6 Scheduler);
    voller Suite 231 pass + 2 skipped.

  **Bekannte Polish-Items (BACKLOG):** Live-Verifikation steht aus —
  wird mit der neuen Hardware nächste Woche zusammen mit Phase-E-
  Polish-Iteration getestet.  Bei sauberem Verhalten ist Phase F
  die letzte Vorbedingung für den Legacy-mpv-Code-Delete (~2000 LoC
  `mpv_engine.py` + `ffmpeg_streamer.py` + Scheduler-Branches).

- **Scheduled Webstreams via Liquidsoap `input.http` (Phase-E,
  2026-05-29)** — geplante Webstream-Items im Schedule laufen jetzt
  durch die Liquidsoap-Engine statt durch den Legacy-mpv-Adapter.
  Konkret: Pypo's `_on_webstream_start` schickt im Liquidsoap-Modus
  drei Telnet-Commands (`webstream.url <url>` → `var.set
  webstream.gain = <linear>` → `webstream.start`) an Liquidsoap, das
  daraufhin den `input.http`-Source aktiviert.  Beim Show-Ende
  `webstream.stop`.  Switch flippt automatisch sobald
  `source.is_ready(webstream)` true wird.

  **Konsequenzen für den Operator:**
  - **Webstream-Shows landen jetzt im Liquidsoap-Recording** (output.file
    vom internen Bus) — vorher waren reine Webstream-Shows still im
    .mp3 Archiv, jetzt komplett aufgenommen.
  - **Crossfade vom vorherigen Track zum Stream funktioniert nativ**
    über den scheduled→switch Übergang.
  - **Per-Stream Input-Gain** (cc_webstream.input_gain_db) wird in
    Pypo dB→linear umgerechnet und als `amplify`-Faktor an Liquidsoap
    weitergegeben — kein Unterschied im UI-Workflow.
  - **Initiale Show-Latency ~5 s** (Buffer-Build-up von input.http
    + 5 s Clock-Bridge Buffer) — Listener mit Player-Buffer merken
    das nicht (Player buffert eh ~10 s).

  Implementation:
  - Template `rastatime.liq.template`: neuer `${WEBSTREAM_INPUT_BLOCK}`
    Placeholder mit `input.http(id="webstream", start=false,
    self_sync=false, max_buffer=10.0, ...)` + `interactive.float
    ("webstream.gain", 1.0)` + `amplify({gain()}, buffer(buffer=5.0,
    webstream_raw))` wrapper.  Switch-Block um neuen Arm zwischen
    DJ-Sources und scheduled erweitert.
  - **Crossfade-Architektur-Fix als Side-Effect**: crossfade wraps
    jetzt NUR den `scheduled`-Source statt den ganzen `bus`.  Grund:
    Liquidsoap's crossfade-Operator akzeptiert keine self-syncing
    Sources (input.http + input.harbor beide), wirft Error 7 "This
    source may control its own latency".  Semantisch korrekt — DJ
    und Webstream sind kontinuierliche Live-Quellen ohne Track-
    Übergänge.
  - `liquidsoap_telnet.py`: 6 neue Convenience-Methoden
    (`webstream_set_url`, `webstream_set_gain`, `webstream_start`,
    `webstream_stop`, `webstream_status`, `webstream_url`).
  - `liquidsoap_engine.py`: `webstream_start(url, gain_db=None)` /
    `webstream_stop()` mit fail-soft try/except + dB→linear
    Conversion (`10 ** (gain_db/20)`).
  - `playout_scheduler.py`: `_on_webstream_start` + `_on_stop`
    branchen auf `streaming_handled_externally` — Liquidsoap-Path
    nutzt `engine.webstream_start/stop`, Legacy-mpv/VLC-Path
    unverändert.
  - Tests: 33 neue (9 Engine + 9 Scheduler + 6 Renderer + 9 Telnet);
    voller Suite 209 pass + 2 skipped.

  **Bug-Kette während Implementation (5 echte Bugs, alle gefixt):**
  - **#1 Liquidsoap-Cache-Stale**: Cache-File-Hash erfasste Template-
    Änderungen nicht zuverlässig — Liquidsoap lud Pre-Phase-E-Bytecode
    aus dem Cache.  Workaround: vor Restart explizit
    `del C:/Tools/liquidsoap/cache/*.liq-cache`.
  - **#2 request.queue für Streams falsch**: Liquidsoap's
    request.queue versucht HTTP-URLs als endliche Files zu fetchen
    (procol.external Mime-Type-Sniff, 29 s Timeout).  Funktioniert
    nicht für persistente Webstreams.  Dedizierter `input.http` ist
    das richtige Pattern.
  - **#3 crossfade(bus) rejects self-syncing sources**: Mit input.http
    UND input.harbor zusammen im switch crash mit Error 7.  Fix:
    crossfade nur um scheduled (Architektur-Änderung).
  - **#4 `self_sync=false` reicht nicht allein**: crossfade-Check ist
    compile-time auf input.http-Funktionssignatur basiert, nicht
    runtime-parameter.  Fix: zusätzlich `buffer()` Wrapper als
    Clock-Bridge.
  - **#5 Telnet Wire-Forms falsch geraten**: `webstream.set_url` und
    `webstream.gain.set` existieren nicht — die echten Commands sind
    `webstream.url <url>` und `var.set webstream.gain = <value>`.
    Live-`help`-Output war Wahrheits-Quelle.

  **Vorbedingung erfüllt**: Phase-E ist eine der zwei Vorbedingungen
  für den Legacy-mpv-Code-Delete.  Nach Phase-F (Line-Inputs) werden
  ~2000 LoC mpv_engine.py + ffmpeg_streamer.py + Scheduler-Branches
  gelöscht.

  **Bekannte Polish-Items (BACKLOG):**
  - Regelmäßige kleine Haker während Webstream (möglicherweise
    Hardware-bedingt — wartet auf neue Maschine).
  - Mountpoint /rastatime verschwand kurz während kurzer Tracks
    (möglicherweise PortAudio-Cascade).
  - Falscher Track-Schnipsel mittendrin im Webstream
    (Switch-Flip-Verhalten bei kurzem Buffer-Underrun).
  - ICY-Metadata-Forwarding vom Stream zu Hörern (heute nicht
    durchgereicht, nice-to-have für später).

- **Operator-Doc `docs/operator/LIQUIDSOAP_CUTOVER.md` (2026-05-28)**
  — step-by-step recipe for the permanent switch from the legacy
  mpv playback engine to the Liquidsoap production engine.
  Covers the antivirus exclusion (mandatory), NSSM-service setup,
  env-var configuration, restart sequence, smoke-test, end-to-end
  show-record verification, and rollback path.  English only
  (operator docs are administrative, not 4-language).

- **User-Manual `SETTINGS.md` §6 "Playout Engine" (EN/DE/FR/ES,
  2026-05-28)** — short section explaining what the three
  available engines (Liquidsoap, mpv, VLC) do well and where each
  is appropriate, with a pointer to the LIQUIDSOAP_CUTOVER doc
  for the actual switch.  Documents the deprecation of mpv / VLC
  and the conditions for the eventual delete (Phase-E + Phase-F).

### Deprecated

- **mpv and VLC playout engines (`RASTATIME_PLAYOUT_ENGINE=mpv`
  und `=vlc`, 2026-05-28)** — Liquidsoap is the production
  playout engine since Phase-C5.  Setting
  `RASTATIME_PLAYOUT_ENGINE=mpv` (the historical default) or
  `=vlc` now emits a `DeprecationWarning` on Pypo startup and
  the `Local-playback engine: …` log line is tagged
  `[DEPRECATED]`.  Operators should switch to
  `RASTATIME_PLAYOUT_ENGINE=liquidsoap`.

  The mpv (and VLC) engine code paths stay in the repo as
  fallback for two not-yet-ported schedule-item types:
  scheduled webstreams and scheduled line-inputs.  Those will
  move to Liquidsoap `input.http` / `input.wasapi` in the
  separate Phase-E (webstreams) and Phase-F (line-inputs)
  blocks.  After Phase-E + Phase-F land, ~2000 LoC of legacy
  engine code (`mpv_engine.py`, `ffmpeg_streamer.py`, related
  scheduler-branches) get deleted.

  **Recording was ALREADY Liquidsoap-only since C5 Teil 2d
  (2026-05-28)** — see the C5 entry below.  In the legacy
  mpv/VLC engine modes, show-record-start events log a
  warning and silently skip; the show plays normally, only
  the recording is missing.

### Changed

- **Recording-Pipeline auf Liquidsoap output.file migriert
  (Phase-C5 Komplett, 2026-05-27/28)** — die per-Show MP3-
  Aufnahmen kommen jetzt direkt aus dem internen Liquidsoap-
  Bus statt über einen separaten FFmpeg-Tap der Icecast-Mountpoint
  abzapfte.  Vorteile: keine HTTP-Source-Buffering-Lücke (~500 ms
  Tail-Cut entfällt), kein 404-Race im Bring-up, kein Watchdog-
  Respawn nötig (Bus-Tap kann nicht netzwerk-flappen), einheitliche
  Audio-Quelle = bit-identisch mit was Listener hören.

  Implementation (Operator-Decisions 2026-05-27):
    - **MP3@320kbps fest** (Archive-Qualität, statt historisch
      192/256 kbps); im `output.file(%ffmpeg(format="mp3",
      %audio(codec="libmp3lame", b="320k")), …)` Block.
    - **Recording vom internen Bus direkt** — Quelle ist der
      `bus` post-switch / post-crossfade / post-amplify.
    - **Mechanismus B** für Path-Switching: `recording.stop` →
      `var.set recording_path = NEW` → `recording.start` triple-
      command zwingt Liquidsoap die Filename-Function neu zu
      evaluieren.  Reality-test 2026-05-27 verifiziert: 100.3 %
      Recording-Duration (vs. expected) bei back-to-back-Switches
      mit < 1 s telnet-roundtrip.

  Operator-spürbare Änderung: kein Workflow-Unterschied
  (Show-Edit "Record this show"-Checkbox unverändert), aber:
  - **Recording-Mode gilt nur bei `RASTATIME_PLAYOUT_ENGINE=
    liquidsoap`** — im Legacy mpv/VLC-Modus ist Recording seit
    diesem Release nicht mehr verfügbar (FfmpegRecorder gelöscht).
  - **Antivirus-Exclusion Pflicht** — der Recording-Folder
    (`C:\Users\studio\Music\Recording\` oder operator-konfiguriert)
    MUSS in Bitdefender / Defender als Exception eingetragen
    werden.  Live-Test 2026-05-28 04:00–08:00 hat reproduzierbar
    gezeigt: ohne Exclusion verlieren lange Shows (>30 min) durch
    Real-Time-AV-Scan auf der wachsenden .mp3-Datei messbar
    Audio (88 % statt 100 % Duration bei einer 60-min Show).
    Mit Exclusion: 100.3 % Duration verifiziert über 30 min.

- **Liquidsoap PortAudio Bus-Split via `buffer(2.0)` + eigene Clock
  (Phase-C5 Side-Fix, 2026-05-28)** — der C5-Reality-Test deckte
  auf dass die Phase-C4 `clock.assign_new`-Allein-Variante nur die
  Main-Clock umbannte, nicht echt isolierte (alle Outputs liefen
  weiter im selben Worker-Clock).  Folge: jeder PortAudio-Underflow
  (CPU-/Disk-Last-Spike) crashte den ganzen Liquidsoap-Prozess
  mit-Recording und allen 3 Icecast-PUTs.  NSSM-Restart dauerte
  ~5 s.

  Real fix: `bus_for_portaudio = buffer(buffer=2.0, bus)` als
  asynchrone Clock-Bridge, der Buffer selbst per `clock.assign_new
  (id="portaudio_clock", sync="cpu", [bus_for_portaudio])` in einer
  eigenen wall-time-getriebenen Clock.  output.portaudio konsumiert
  bus_for_portaudio.  Burn-In #2 (2026-05-28 02:48–10:05, 7h 17m)
  verifiziert: 0 PortAudio-Crashes, Liquidsoap-uptime ungebrochen.
  Trade-off: lokales Monitor-Speaker läuft 2 s hinter Stream/Recording
  — akzeptabel für Operator-Monitoring.

### Removed

- **FfmpegRecorder + Lifecycle-Code (~693 LoC netto, 2026-05-28)** —
  `backend/playout/libretime_playout/engine/ffmpeg_recorder.py`
  komplett gelöscht (493 LoC) sowie die zugehörige Lifecycle-
  Maschinerie in `playout_scheduler.py`: `_show_record_lifecycle`,
  `_show_record_mid_show_respawn`, `_show_record_initial_start`,
  `_RECORDER_RETRY_*`-Konstanten, `_show_record_stop_events`-Dict,
  `_first_stream_listen_url` (~250 LoC).  Die zwei noch genutzten
  Helper (`build_output_path`, `sanitize_show_name`) wurden in das
  neue Modul `libretime_playout/recording_path.py` (~80 LoC)
  gerettet.  Operator-Decision irreversibel 2026-05-27 ("FfmpegRecorder
  Code komplett loeschen"), verifiziert durch Burn-In #2 vor dem
  Delete.

### Fixed

- **Liquidsoap Phase-C8 Reality-Test — 10 Bugfixes durch live
  Operator-Validierung gegen Liquidsoap 2.4.4 Windows-Build**
  (operator session 2026-05-26 Vormittag, Commits `9c8f891` …
  `f346e37`).  Der erste echte Stack-Run hat eine Reihe von
  Inkompatibilitäten zwischen meinem theoretischen Modell und
  dem konkreten savonet-Windows-Build aufgedeckt.  Alle gefixt;
  scheduled-tracks-Pfad ist jetzt **vollständig produktiv-testbar**
  (Audio im Browser + an der lokalen Soundkarte, Crossfades,
  ReplayGain, ICY-Metadata, Catch-Up-stabil).

  Konkrete Fixes:
    - `9c8f891` — Operator-Doku: Pypo muss aus `C:\rastatime\.venv\Scripts\python.exe`
      gestartet werden, nicht System-Python (sonst `No module named
      libretime_playout`).
    - `56cabf4` — `opus` als 4. Stream-Type im Renderer (das LibreTime
      cc_pref.stream_output_N akzeptiert seit jeher mp3/aac/ogg/opus,
      ich hatte opus übersehen).
    - `22690d9` → `e541558` — Liquidsoap 2.4 hat `output.icecast`'s
      `restart_delay=5.` kwarg entfernt, neue Form heißt `on_error:
      (string) -> float` Callback.  Erst auf `on_error=fun(_) -> 5.`
      umgestellt, dann gemerkt dass die 2.4-Signatur eigentlich ein
      Record-Typ `(restart_in : _, ...) -> _` ist und der einfache
      `fun(_)` nicht passt — komplett weggelassen, Liquidsoap-Default-
      Reconnect übernimmt.
    - `52b3b38` — Encoder-Block braucht `samplerate=…` weil Liquidsoap-
      internal frame samplerate 44100 Hz ist aber libopus nur 8/12/16/
      24/48 kHz akzeptiert.  Renderer liest jetzt `samplerate` aus
      cc_pref.stream_output_N (gleicher Pfad wie FfmpegStreamer) und
      clampt für opus invalide Werte auf 48000.
    - `c2d7155` — Liquidsoap 2.4 exposed `request.queue(id="X")` als
      Server-Commands `X.push` / `X.skip` / `X.queue` / `X.flush_and_skip`,
      NICHT als die legacy `request.queue.push` aus älteren Builds.
      LiquidsoapTelnetClient bekommt einen `queue_id`-Parameter
      (default `"scheduled"` matched die rastatime.liq).  Plus:
      `play()` prüft jetzt ob Liquidsoap-Reply mit `ERROR:` startet
      und flippt state auf ERROR statt silently auf PLAYING zu
      bleiben (das war der bisher schlimmste silent-failure-Modus).
    - `e82a0b4` — Doppelfix für zwei Show-Stopper:
      * Windows-Pfade brauchen `file://C:/…` (2 slashes), nicht
        `file:///C:/…` (3 slashes wie RFC 8089) — Liquidsoap 2.4
        strippt `file://` und behält `/C:/…` über das es als
        "Unknown protocol URI" abweist.
      * `fallback(track_sensitive=true, [scheduled, blank()])` hängt
        sich auf weil `blank()` nie ein Track-End-Event emittiert —
        die fallback wartet ewig auf einen Track-Boundary der nie
        kommt.  Umgestellt auf `track_sensitive=false` damit der
        scheduled-source sofort übernimmt sobald Requests da sind.
    - `1d131a6` — Pypo's PlayoutScheduler bekommt einen
      `streaming_handled_externally: bool` flag.  Bei
      `engine_kind=liquidsoap` werden die FfmpegStreamer-Subprocesses
      gar nicht erst gespawnt — Liquidsoap hält ja schon die Icecast-
      Mounts, parallele FFmpeg-Spawns würden mit 403 "mount taken"
      scheitern.
    - `5c82b47` — Deferred-Stop in LiquidsoapEngine: `stop()` sendet
      nicht mehr sofort `scheduled.skip`, sondern markiert nur die
      Intention + armt einen 500ms-Timer.  `play()` innerhalb des
      Fensters mit gleichem URI cancelt beide Calls (Pypo's catch-up-
      pattern feuert stop+play+stop+play für den gleichen Track 2-3×
      hintereinander wenn die Schedule-API ein Event re-identifiziert).
      Plus: lokales Audio via `output.wasapi` ins `.liq` (zunächst).
    - `f346e37` — `output.wasapi` ist nicht im savonet Liquidsoap-
      2.4.4-Windows-Build (`--list-functions` zeigt nur `output.ao` /
      `output.portaudio` / `output.audio_video` / `output.external`).
      Auf `output.portaudio` umgestellt — PortAudio nutzt auf Windows
      unter der Haube WASAPI/DirectSound.  Liquidsoap-Clock wechselt
      automatisch in `self-sync mode` (PortAudio wird Clock-Master)
      was Drift zwischen Icecast und Soundkarte verhindert.

  **Operator-bestätigt 2026-05-26 13:30 Uhr:** scheduled Tracks der
  Test-Show um 13:30 sind lokal via Soundkarte UND im Webstream
  hörbar.  Crossfades sauber, ReplayGain-Ausgleich wirkt, ICY-Title
  propagiert zu allen 3 Icecast-Mounts.

  Test-Suite: **113 Tests grün in ~3.3 s** (5 neue durch die C8-Fixes:
  3 deferred-stop + 2 local-output).  Production-Path unverändert —
  `RASTATIME_PLAYOUT_ENGINE` defaultet weiter auf `mpv`.

### Added

- **Liquidsoap Phase-C7 + C8 — Pypo Auto-Render bei Start +
  Operator-Integration-Test-Guide** (Operator-Entscheidung
  2026-05-26 "C7+C8 vor C4+C5 vorziehen", Seamless-Bus-Mix
  Phase 2).

  Phase-C7 verdrahtet das Pypo-Bootstrap mit dem C3-Renderer
  hinter dem `RASTATIME_PLAYOUT_ENGINE=liquidsoap` Feature-Flag:

    - `__main__.py` hat jetzt einen `_render_rastatime_liq_at_startup()`
      Helper, der beim Pypo-Start die `cc_pref.stream_output_N`
      Rows liest, die operator-konfigurierten Pfade aus env-vars
      auflöst und die finale `rastatime.liq` atomar nach dem
      Liquidsoap-Tools-Verzeichnis schreibt.
    - Idempotent: wenn sich gegenüber dem letzten Render nichts
      geändert hat, wird die Datei nicht neu geschrieben und Pypo
      loggt nur ein `INFO  up-to-date — no restart needed`.  Wenn
      sich etwas geändert hat, kommt ein `WARN  Rendered … RESTART
      the RASTATIME-LIQUIDSOAP NSSM service` — Operator muss den
      Service manuell restarten (wir bouncen NSSM bewusst nicht
      automatisch, um Credential-Tippfehler nicht stillschweigend
      live zu schalten).
    - Skelett-Warning für die Liquidsoap-Engine entfernt — die
      Engine ist seit C2 voll funktional und braucht keinen
      "raises NotImplementedError" Hinweis mehr.
    - Neue Env-Vars dokumentiert im Modul-Docstring:
      `RASTATIME_LIQUIDSOAP_HOST` / `_PORT` /
      `_CONFIG_PATH` / `_LOG_PATH` / `_CROSSFADE_SECONDS`.

  Phase-C8 ist ein **Operator-Integration-Test-Guide**, weil ein
  echter Liquidsoap-Spin-up nicht im pytest-Setup machbar ist:

    - `docs/operator/LIQUIDSOAP_PHASE_C8.md` — Schritt-für-Schritt-
      Guide: NSSM-Service installieren, Pypo im Liquidsoap-Modus
      starten (rendert .liq), liquidsoap.exe --check Sanity, NSSM
      starten, Test-Track in cc_schedule eintragen, Browser-
      Playback prüfen (Audio, Crossfade, ReplayGain, ICY-Title),
      strukturierter Bericht-Template am Ende.
    - Doku weist explizit darauf hin was C8 NICHT abdeckt
      (DJ-Sources → C4, Recording → C5) und wie der Operator
      während C8 mit gleichzeitig laufendem mpv-DJ-Listener
      umgeht.

  Damit ist der **scheduled-tracks-Pfad** über Liquidsoap
  vollständig in Operator-Hand testbar.  Production-Path
  unverändert (Default bleibt `mpv`).

  Combined engine + config suite weiter bei **101 Tests grün
  in 2.5 s** — keine neuen Unit-Tests in diesem Schritt
  (Bootstrap-Code ist zu eng an Module-Init gekoppelt um
  sinnvoll in pytest zu kapseln; die einzelnen Bausteine —
  Renderer, Engine, Telnet — sind bereits unabhängig getestet).

- **Liquidsoap Phase-C6 (Teil 2) — ICY-Metadata via
  PlayoutEngine-Vertrag + 8 neue Tests** (Seamless-Bus-Mix
  Phase 2).  Erweitert den `PlayoutEngine`-ABC um einen
  optionalen `metadata: Optional[Dict[str, str]]` Parameter
  auf `play()` und reicht Track-Title / Artist / Show-Name
  vom Pypo-Scheduler bis in die `annotate:`-Envelope der
  LiquidsoapEngine durch.  Liquidsoap propagiert die
  metadata automatisch in alle `output.icecast`-Blöcke
  (kein zusätzlicher telnet-`metadata.update` Call nötig).

  Änderungen:
    - `interface.py` — `play()` Signatur erweitert um
      `metadata: Optional[Dict[str, str]] = None`,
      ausführlich dokumentiert.
    - `mpv_engine.py` + `vlc_engine.py` — Parameter
      angenommen + ignoriert (mpv/VLC sind local-only,
      Icecast-Metadata kommt im mpv/VLC-Pfad weiter aus
      FfmpegStreamer `-metadata`).
    - `liquidsoap_engine.py`:
       * `play()` reicht `metadata` an `_build_annotate_uri` weiter
       * `_build_annotate_uri()` erweitert um `metadata` kwarg —
         hängt nach cue/gain Keys weitere `key="value"` Paare an
         (None / "" Werte werden silently übersprungen)
       * Neuer `_escape_annotate_value()` Helper (Backslash + Quote
         Escape, gleiche Semantik wie `LiquidsoapTelnetClient._escape_value`)
       * Log-Line um `meta=` Spalte erweitert
    - `playout_scheduler.py`:
       * `_on_file_start()` baut `track_metadata = {title, artist,
         show_name}` aus dem FileEvent + reicht es an `engine.play()`
       * Resume-Path (`_resume_current_event` nach Pypo-Restart)
         macht das gleiche, mit `isinstance(FileEvent)` Guard so
         dass Webstream/Linein-Resumes nicht den Parameter setzen
         (deren Metadata kommt ja vom Stream selbst).

  8 neue Tests in `tests/engine/test_liquidsoap_engine.py`:
    - `_build_annotate_uri` mit metadata-only (kein cue, kein gain)
    - metadata mit `None` / "" Werten — Skip-Verhalten
    - leerer metadata-Dict → kein annotate-Wrapper
    - Quote-Escape in metadata-Wert
    - Backslash-Escape in metadata-Wert
    - Alle vier (cue_in + cue_out + gain + metadata) gleichzeitig
      — Order-Check: cue, gain, dann metadata
    - End-to-End `play(metadata=...)` → richtiger Payload bei
      `request_queue_push`
    - `play()` ohne metadata bleibt rückwärts-kompatibel

  Test-Suite nun **101 Tests** (43 Engine + 17 Telnet + 36 Config
  + 5 FFmpeg-Streamer-Gain), alle grün in ~2.5 s.

  Damit ist Phase C6 vollständig: scheduled tracks werden mit
  ReplayGain compensiert, kreuzgefadet, und tragen ICY-Metadata
  zu allen drei Icecast-Mounts.  Mpv/VLC-Pfad unverändert —
  der neue `metadata`-Parameter wird dort ignoriert.

- **Liquidsoap Phase-C6 (Teil 1) — Crossfade + ReplayGain
  im `.liq`-Bus + 12 neue Tests** (Operator-Entscheidung
  2026-05-26 "C6 vor C4 vorziehen", Seamless-Bus-Mix Phase 2).
  Erweitert den `rastatime.liq`-Bus um die zwei Liquidsoap-
  Operatoren die die echten "live-radio"-Eigenschaften
  einbringen — sauber zwischen Tracks rüberfaden und
  Lautheits-Sprünge ausgleichen.

  Template-Changes (`config/rastatime.liq.template`):
    - Neuer Platzhalter `${CROSSFADE_DURATION}` (default 2.0 s)
    - `bus = crossfade(duration=..., bus)` zwischen
      consecutive `request.queue` items.  `duration=0.` setzt
      Crossfades effektiv ab.
    - `bus = amplify(override="replaygain_track_gain", 1., bus)`
      multipliziert den Bus mit dem ReplayGain wenn die
      `annotate:replaygain_track_gain="X dB"` Metadata vorhanden
      ist (die C2-Engine setzt das aus `cc_files.replay_gain` +
      `cc_pref.replay_gain_modifier`).

  Renderer-Changes (`liquidsoap_config.py`):
    - Neuer kwarg `crossfade_duration: float = 2.0` für
      `render_rastatime_liq()` + `write_rastatime_liq()`
    - CLI: neues `--crossfade-duration` Flag
    - Neuer Helper `_format_crossfade_duration()` — rendert
      Liquidsoap-konforme Float-Syntax (`2.0`, `1.25`, `0.0`,
      Rundung auf 2 Nachkommastellen)
    - Defaults-Konstante `DEFAULT_CROSSFADE_DURATION = 2.0`
      matched die historische `cc_pref.default_crossfade_seconds`
      Vorgabe.

  12 neue Tests:
    - `_format_crossfade_duration` mit 8 parametrisierten
      Input-Cases (Int, Float, fractional, Rundung)
    - Custom-Duration im gerenderten Template
    - Default-Wert `2.0` im gerenderten Template
    - Crossfade explizit auf 0 → `duration=0.0` (no-op)
    - Crossfade fraktional (1.25 s)
    - Defaults-Render-Test prüft zusätzlich `crossfade(`
      und `amplify(...)` Vorkommen

  Test-Suite nun **93 Tests**, alle grün in ~2.5 s.

  Production-Path unverändert.  ICY-Metadata-Push (Teil 2 von
  C6) — der PlayoutEngine-Vertrag muss um optionalen
  `metadata`-Parameter erweitert werden (alle drei Engines
  + Scheduler-Aufrufstellen) — folgt als separater Commit.

- **Liquidsoap Phase-C3 — Produktions-`.liq` Template +
  Python-Renderer + 25 Unit-Tests** (operator go 2026-05-26,
  Seamless-Bus-Mix Phase 2 Variante A).  Operator decisions:
  Credentials aus `libretime.conf` + cc_pref (Single Source of
  Truth), indefinite-retry-mit-5s-backoff für Icecast-Bring-up,
  `blank()`-Fallback für leere `request.queue`.

  New / changed files:
    - `backend/playout/config/rastatime.liq.template` — komplett
      neu geschriebene produktionsbereite Version (ersetzt das
      kommentierte Phase-B Skelett).  Aktivierter telnet-Server
      auf `127.0.0.1:1234`, Log-File via `settings.log.file.path`,
      `request.queue(id="scheduled")` wrapped in
      `fallback([scheduled_q, blank()])` für persistente Icecast-
      PUTs, `${ICECAST_OUTPUTS}` Platzhalter für gerenderte
      `output.icecast(...)` Blöcke.
    - `backend/playout/libretime_playout/liquidsoap_config.py` —
      neuer `render_rastatime_liq()` + `write_rastatime_liq()`
      + CLI-Entry-Point `python -m libretime_playout.liquidsoap_config
      render --out C:/Tools/liquidsoap/rastatime.liq`.  Liest
      `cc_pref.stream_output_N` JSON-Blobs (gleiche Quelle wie
      die bisherigen FFmpeg-Streamer), rendert pro enabled
      Stream einen `output.icecast(...)` Block mit dem
      richtigen Codec (mp3 → libmp3lame / aac → adts/aac /
      ogg → libvorbis), Bitrate, Host/Port/Mount/User/Pass +
      `restart_delay=5., fallible=true` (für indefinite retry).
      Atomic-Write via `.tmp` + `os.replace`, BOM-frei (Phase-0
      hatte BOM-Trip), Idempotenz-Check zurück
      `True/False = changed/unchanged`.
    - `backend/playout/tests/test_liquidsoap_config.py` —
      25 Tests: String-Escape (Quotes, Backslashes), Codec-
      Mapping (mp3/aac/ogg), Bitrate-Substitution,
      Mount-Leading-Slash-Normalisierung, unbekannter Stream-
      Typ → `ValueError`, leere Stream-Liste → Kommentar-Stub,
      mehrere Streams hintereinander, vollständiger Template-
      Render mit Defaults + Custom-Telnet/Log, BOM-Vermeidung,
      Atomic-Write ohne `.tmp`-Leftover, Idempotenz-Check
      (unchanged → `False`), Regression-Guard "kein
      `${...}` darf nach Render im Output sein".  Alle 25 grün
      in ~0.1 s.

  Kombinierte Test-Suite jetzt **82 Tests** (24 Config-Renderer
  + 35 Engine + 17 Telnet + 5 FFmpeg-Streamer-Gain + 1 Telnet-
  Edge-Case).  Alles grün in ~2.4 s.

  Production-Path unverändert.  C4 wird input.harbor + switch()
  ins Template injektieren, C5 output.file für Recording, C6
  crossfade + amplify wrappen, C7 verdrahtet Pypo so dass der
  Render-Schritt beim Start mit `RASTATIME_PLAYOUT_ENGINE=liquidsoap`
  automatisch läuft (heute manuell via CLI).

- **Liquidsoap Phase-C2 — LiquidsoapEngine play/stop/close
  wire-up gegen Telnet-Client + 35 Unit-Tests** (operator go
  2026-05-26, Seamless-Bus-Mix Phase 2 Variante A).  Replaces
  the Phase-B `NotImplementedError` stubs in
  `backend/playout/libretime_playout/engine/liquidsoap_engine.py`
  with a working implementation that talks to a long-running
  Liquidsoap subprocess over the C1 telnet client.

  * `play(uri, cue_in, cue_out, gain_db)` normalises Windows
    paths (`C:\…` → `file:///C:/…`), wraps the URI in a
    Liquidsoap `annotate:` envelope when cue points or gain
    are present, then sends `request.queue.push <annotate-uri>`
    via telnet.  Numeric reply (the request id) is captured for
    diagnostics.  Telnet errors flip `state = ERROR` and log
    but never propagate out — the Pypo scheduler treats
    play-exceptions as fatal so we deliberately swallow.
  * `stop()` sends `request.queue.skip` and flips state to
    `STOPPED`.  Same swallow-on-error policy.
  * `close()` forwards to `telnet.close()`.  Does NOT terminate
    the Liquidsoap subprocess — that's NSSM's job.
  * `wait_until_stopped()` is a true `return True` — Liquidsoap
    has native gapless transitions, so the 500 ms tail-flush
    hack in the mpv path goes away once the Liquidsoap engine
    is the active backend.
  * `set_audio_device()` stays a warn-only no-op — runtime
    device switching needs `.liq`-script reconfiguration and
    is deferred to Phase D.
  * Telnet client is injectable via constructor for tests
    (`telnet_client=` kwarg), defaults to building a real
    client from `RASTATIME_LIQUIDSOAP_HOST` / `_PORT` env vars.

  New helpers documented + tested:
    - `_normalise_uri` — Windows drive-letter path → `file:///`
      forward-slash form (regex-detected, three-slash variant
      per RFC 8089 which Liquidsoap requires).
    - `_build_annotate_uri` — composes the
      `annotate:cue_in="N",cue_out="N",replaygain_track_gain=
      "X dB":<uri>` envelope; omits the wrapper entirely when
      no annotations are needed.
    - `_extract_request_id` — pulls Liquidsoap's numeric
      request-id reply out of (possibly multi-line) responses.
    - `_redact` — strips password from `http://user:pass@…`
      URIs in log lines (mirrors `MpvPlayoutEngine._redact`).

  New test file
  `backend/playout/tests/engine/test_liquidsoap_engine.py` —
  35 tests with `MagicMock(spec=LiquidsoapTelnetClient)`
  injected (no real socket I/O): URI normalisation for
  Windows back/forward slashes + already-prefixed URIs + HTTP
  passthrough; annotate building for every combination of
  cue_in/cue_out/gain_db including the no-annotation early-out
  and zero-gain epsilon; play→PLAYING state transition;
  numeric/multi-line/non-digit request-id parsing; stop→STOPPED
  + skip telnet call; telnet `ConnectionError` swallowed in
  play/stop/close without propagating; close idempotency;
  `wait_until_stopped` truly immediate (not polling);
  `set_audio_device` warn-only; both micro-helpers
  (`_extract_request_id`, `_redact`) exercised independently.
  All 35 pass in ~0.07 s.

  Combined engine suite now at **57 tests** (35 new + 17 from
  C1 + 5 pre-existing FFmpeg-streamer-gain) — all green in
  ~2.2 s.

  No production-path change.  `RASTATIME_PLAYOUT_ENGINE` still
  defaults to `mpv`; switching to `liquidsoap` will now reach a
  *working* play/stop loop but will fail at telnet-connect
  because there's no `rastatime.liq` running yet (that's Phase
  C3 — produktions-.liq Script).

- **Liquidsoap Phase-C1 — Telnet-Client volle Implementation
  + 17 Unit-Tests** (operator go 2026-05-26, Seamless-Bus-Mix
  Phase 2 Variante A).  Replaces the Phase-B
  `NotImplementedError` skeleton in
  `backend/playout/libretime_playout/engine/liquidsoap_telnet.py`
  with a working thread-safe TCP-telnet client for Liquidsoap's
  server-line protocol.

  * Lazy-connect on first `send_command`; explicit `connect()`
    and `close()` for tests / shutdown.
  * `threading.Lock`-serialised socket I/O so notify-thread,
    recorder-thread and source-switcher-thread can't interleave
    bytes on the wire.
  * `END` sentinel parser accepts both `\nEND\n` (Linux build)
    and `\nEND\r\n` (Windows build of Liquidsoap), plus the
    empty-response special case `END\n` / `END\r\n`.
  * Receive buffer carried across calls so any bytes pipelined
    past the sentinel survive to the next `recv()`.
  * One-shot reconnect-and-retry on `OSError` / `ConnectionError`;
    after second failure the exception propagates so the
    scheduler can decide.
  * Convenience wrappers: `request_queue_push(uri)`,
    `request_queue_skip()`, `metadata_update(dict)` with
    backslash + double-quote escaping, `var_set(name, value)`,
    `help()`.

  New test file
  `backend/playout/tests/engine/test_liquidsoap_telnet.py` —
  17 tests against an in-process fake TCP server
  (`_FakeLiquidsoapServer`) covering basic roundtrip, empty +
  multiline responses, auto-newline append, reconnect on stale
  socket (both retry-then-fail and retry-then-success via
  `FlipFlopServer`), connection-refused → `ConnectionError`,
  all 5 convenience wrappers including metadata-update quote +
  backslash escaping, idempotent `connect` / `close`, CRLF END
  sentinel handling (Windows builds), CRLF empty response.
  All 17 pass in ~2.2 s on Windows Python 3.12.

  No production-path change yet — Engine adapter `play` /
  `stop` / `close` still raise `NotImplementedError`; that
  wires up in Phase C2.

- **Liquidsoap Phase-B skeleton — engine adapter + telnet client
  + .liq template** (operator go 2026-05-25, Seamless-Bus-Mix
  Phase 2 Variante A).  Inert until operator switches
  `RASTATIME_PLAYOUT_ENGINE=liquidsoap`; default stays `mpv`.

  New files:
    - `backend/playout/libretime_playout/engine/liquidsoap_telnet.py`
      — thread-safe TCP-telnet client skeleton for Liquidsoap's
      server-line protocol on `127.0.0.1:1234`.  Class structure,
      connection-lifecycle stubs, command wrappers
      (`request_queue_push`, `metadata_update`, `var_set`,
      `request_queue_skip`, `help`) — all raise
      `NotImplementedError` pending Phase-C wire-up.
    - `backend/playout/libretime_playout/engine/liquidsoap_engine.py`
      — `LiquidsoapPlayoutEngine` implementing the same
      `PlayoutEngine` ABC as the mpv / VLC adapters.  `play`,
      `stop`, `close`, `set_audio_device`, `get_state`,
      `wait_until_stopped` all present.  `wait_until_stopped` is
      a true no-op-returning-True because Liquidsoap has native
      gapless transitions — that's the whole reason for the
      migration.
    - `backend/playout/config/rastatime.liq.template` — heavily-
      commented Liquidsoap-script outline showing the target
      Phase-C architecture: telnet-server enable, request.queue
      for scheduled tracks, input.harbor for Master/Show DJ,
      `switch(...)` for source switching, `crossfade(...)`,
      `amplify(override="replaygain_track_gain", ...)`, 3 ×
      `output.icecast` (mp3/aac/ogg) with persistent PUT.  All
      blocks commented out — this is the design contract for
      Phase C, not a runnable script yet.

  `__main__.py` engine-factory extended: third option `liquidsoap`
  alongside `mpv` and `vlc`.  Engine instantiates cleanly but
  scheduler will hit `NotImplementedError` on first track play,
  with a clear `Logging::critical` pointing at the BACKLOG entry.

  No production-path change.  Operator-facing risk in this
  commit: zero — feature-flag is env-var-gated and default is
  unchanged.

### Fixed

- **Playout: tail-flush wait raised from 200 ms to 500 ms —
  Seamless-Bus-Mix Phase 1 follow-up 2** (operator follow-up
  2026-05-25).  After commit 2b2a787 the operator confirmed
  the wait now greift (visible in playout-stdout.log as a
  202 ms gap between the scheduler `STOP` event and `mpv
  stop`), but tails of longer tracks were still being clipped
  by a few seconds.  Operator decision: bump the wait to
  500 ms on all four stop sites (`_on_file_start`,
  `_on_webstream_start`, `_on_linein_start`, `_on_stop`).
  Math on a 9.9 s-cue_out track: `9.9 − 0.5 (mpv-start
  latency after parallel-stops) + 0.5 (tail wait) ≈ 9.9 s`
  effective playback.

  Operator preference recorded for future iterations: every
  track should play to its configured cue_out regardless of
  duration; a short pause on track transitions is acceptable.

- **Playout: short-track tail cut — Seamless-Bus-Mix Phase 1
  follow-up** (operator follow-up 2026-05-25).  After the
  initial Phase-1 commit landed, the operator still heard
  the tail-cut on the 10.1-s `TOH-Jingle 12 Uhr` (cue_out
  9.9 s) — clipped at ~8.4 s.  Two root causes that the
  first commit didn't cover:

  1. The `_on_stop` handler (the second track-end stop
     path, fired by the track-end Timer in parallel with
     `_on_*_start` for the next event) hard-stopped mpv
     and the FFmpeg streamers without the new
     `wait_until_stopped` guard.  Because Python's
     `threading.Timer` makes no ordering guarantee for two
     timers firing on the same wallclock instant, `_on_stop`
     fired first about half the time and set the engine to
     STOPPED before `_on_file_start`'s wait ever saw a
     non-stopped state.  Added the same bounded 200 ms
     `wait_until_stopped` in `_on_stop` so this path also
     gives the previous file a brief grace period.
  2. `_stop_streamers()` ran the three FfmpegStreamer
     `stop()` calls sequentially — each costing ~500 ms for
     its graceful 'q'-exit handshake — for a total of
     ~1.5 s of latency injected into the next track's
     mpv-start.  That latency was the dominant component
     of the ~8.4 s observed clip on the 9.9 s-cue_out
     jingle (9.9 − 1.5 ≈ 8.4).  Switched to threaded
     parallel stops with a 4-s join timeout per thread;
     the total cost is now bounded by the slowest single
     streamer (~500 ms) instead of the sum.

  Expected effect: short tracks should now play
  consistently up to (or very close to) their configured
  cue_out, since the next-track mpv-start latency drops
  from ~1.5 s to ~0.5 s and both stop paths respect the
  200 ms decode-tail flush.

- **Playout: short-track tail cut at next-track time —
  Seamless-Bus-Mix Phase 1** (operator request 2026-05-25).
  Symptom: short tracks (4–10 s) regularly lost their last
  1–2 s of audio in the Icecast output, most noticeable on
  the transition from a scheduled track to a scheduled
  webstream item.

  Root cause: `playout_scheduler.py::_on_*_start` (file,
  webstream, line-in) hard-stopped mpv and all three
  FfmpegStreamer instances the instant the scheduler-clock
  reached the next track's start time, regardless of whether
  mpv had actually finished decoding (and ffmpeg's `-re`-
  paced read had actually finished encoding) the previous
  file's tail.  On short files the gap between scheduler-
  clock and mpv's `end-file` event was large enough to clip
  audibly.

  Fix: new `PlayoutEngine.wait_until_stopped(timeout)`
  method, overridden in `MpvPlayoutEngine` with a real
  blocking wait on a `threading.Event` that is set by the
  libmpv `end-file` event callback and cleared on
  `loadfile`.  All three `_on_*_start` paths now call
  `wait_until_stopped(timeout=0.2)` immediately before their
  hard-stop, giving the previous file up to 200 ms to flush
  its tail.  Common case (previous track already ended
  naturally) returns immediately, no perceptible delay.

  Phase 2 of the Seamless-Bus-Mix work (persistent
  Icecast-PUT connection so listeners don't get kicked on
  every track change) is parked on `BACKLOG.md` for a
  separate dedicated session — A vs. B architecture
  decision happens at that kickoff.

### Added

- **Smart Block: within-block spread for the exclude-played-
  lately filters** (operator request 2026-05-25).  The two
  exclude filters (`exclude_played_lately` for tracks +
  `exclude_artists_lately` for artists) so far only kept the
  candidate pool clean of items that played in the last N h
  via `cc_playout_history`.  That SQL filter does not look at
  what the smart block itself is about to play, so the block
  could still hold e.g. two Beatles tracks back-to-back inside
  the same generation.

  New second pass `Block::applyWithinBlockSpread()` runs after
  the track-list build in `getListOfFilesUnderLimit`.  For each
  slot of the originally-selected track list:
    1. Try the original track first.
    2. If it conflicts with the elapsed-time spread window of
       the tracks already placed, pull a non-conflicting
       replacement from the broader SQL-filtered pool
       (up to 500 tracks).
    3. If no non-conflicting replacement is left, place the
       original anyway and emit a `Logging::warn` so the
       operator sees in `legacy.log` when the pool was too
       narrow for the configured spread (operator decision
       2026-05-25 — "Track stehen lassen + Warnung loggen").

  Block length stays the same (same slot count, original
  block-limit honoured); only the track choice shifts.
  Replacement order is deterministic (first non-conflicting
  track in the pool order), so re-generating the same block
  on the same inputs yields the same result.

  Artist lookups for the broader pool are done in a single
  `SELECT id, artist_name FROM cc_files WHERE id IN (...)`
  query at the start of the pass, so the spread loop itself
  is in-memory only.  No schema change.

### Changed

- **Weekly Schedule widget scaled up to 670 px width**
  (operator request 2026-05-25).  Container `max-width` raised
  from 400 px to 670 px, all other dimensions scaled
  proportionally (≈ 1.67× factor):
    - Body `font-size` 1em → 1.2em (em-based padding / gap
      values inherit the new scale automatically).
    - Header `padding-bottom` + `margin-bottom` 6px → 10px;
      nav buttons `padding` 2/8 → 4/14, `font-size` 1.1em →
      1.3em.
    - Tab strip `margin-bottom` 6 → 10, tab `padding` 4 → 8,
      active-tab border-bottom 2 → 3 px, day-of-month
      `font-size` 1em → 1.15em.
    - Content area `min-height` 120 → 200 px; day-panel
      `max-height` 470 → 790 px (matches the new iframe
      height); scrollbar 6 → 8 px wide.
    - Row `padding` 6/8 → 10/12, `gap` 0.8em → 1em, current-
      show left-border 3 → 4 px.

  Settings page (Settings → Widgets → Weekly Schedule)
  iframe + embed-snippet defaults raised from `width="400"
  height="560"` to `width="670" height="940"` so the preview
  + the copy-paste embed code match the new dimensions out of
  the box.  Operator-doc width line updated in WIDGETS.md
  EN/DE/FR/ES.

### Changed

- **Dashboard header: `source-info-block` → `status-info-block`,
  new Auto-DJ shortcut button** (operator request 2026-05-24).
  Four edits to the master panel header partial:
    1. `<h3>Source Streams</h3>` → `<h3>Status</h3>`.
    2. CSS class `.source-info-block` renamed to
       `.status-info-block` throughout the template, both
       stylesheets (`styles.css`, `masterpanel.css`, 27 hits
       combined) and the layout partial that injects the
       header.
    3. Tighter `padding-top` on the source-status `<ul>`
       (10 px → 2 px) — operator wanted the Master / Show /
       Auto-DJ rows closer together to make room for the new
       button without stretching the header.
    4. New `<li class="auto-dj-item">` row under Show Source
       with a small dark pill-button "⚙ AUTO DJ" linking to
       `/preference/auto-dj` (same tab, same window).  A 2-px
       red underline below the button is shown via the
       `.auto-dj-active` class on the `<li>` only when
       `Application_Model_Preference::GetAutoDjEnabled()`
       returned true at render time — operator-visible
       Auto-DJ status from any dashboard page at a glance.

  The Auto-DJ status is read at page-render time, not
  AJAX-polled — toggling Auto-DJ from the Preferences page
  surfaces in the header on the next page navigation.  No
  extra HTTP round-trips per page load.

### Fixed

- **Smart Block: Save button silently fails for blocks with the
  exclude-artists filter** (operator report 2026-05-24).
  `cc_blockcriteria.criteria` is `VARCHAR(32)`.  The criteria
  names introduced on 2026-05-23 were 29 and 35 characters long:
  the `..._hours` row hit PDO 22001 ("Wert zu lang für Typ
  character varying(32)"), Propel aborted the whole
  `saveSmartBlockCriteria()` transaction, the JSON response
  never arrived, and the frontend stayed stuck on the loading
  icon — operator could not see the updated track-match count
  and had to re-open the block to edit again.

  Fix in `Application_Model_Block::storeCriteriaIntoDb()`:
  rename the persisted criteria from
  `exclude_artists_played_lately` / `..._hours` to
  `exclude_artists_lately` / `..._hours` (22 / 28 chars, both
  fit in VARCHAR(32)).  Load path accepts both names so any
  rows the operator already managed to insert with the v1 name
  are still honoured.  Save path runs a `DELETE FROM
  cc_blockcriteria WHERE criteria IN (v1-names)` cleanup first
  so the next save returns to a clean two-row state.  Internal
  `$storedCrit` keys (`exclude_artists_played_lately[_hours]`)
  stay unchanged so the rest of the code (form fields, WHERE
  clause) needed no edits.

  No schema migration — chose the rename over a column widen
  because (a) zero downtime, (b) consistent with the existing
  `exclude_played_lately` / `..._hours` names (27 / 21 chars,
  both well within 32), (c) the operator's existing
  `exclude_played_lately` filter was never affected because
  the longest name there is 27 chars.

### Added

- **Smart Block: "Exclude artists played lately" filter**
  (operator request 2026-05-23).  Companion to the existing
  "Exclude tracks played lately" toggle, identical UI shape:
  a master checkbox that reveals an "Exclude tracks played in
  the last hours" input (1..8760 h, default 24).  Filters the
  pool by `cc_files.artist_name` instead of `cc_files.lptime`
  — drops any track whose artist was heard via _any_ other
  track in the last N hours.

  Use case: a smart block with hundreds of Beatles tracks
  should not still play two Beatles tracks back-to-back just
  because the second one has never aired specifically.  The
  two filters compose AND-wise: activating both gives "no
  recent track AND no recent artist".

  NULL / empty `artist_name` is intentionally never matched
  (passes the filter as-is) — a single track with a blank
  artist would otherwise exclude every other blank-artist
  track globally.

  Implementation: two new `cc_block_criteria` rows
  (`exclude_artists_played_lately` master + `..._hours`
  window), same persistence + load pattern as the per-track
  filter so missing rows = disabled (backwards-compatible).
  WHERE clause uses a `NOT EXISTS` subquery against
  `cc_playout_history JOIN cc_files` so cost is bounded even
  with a large history table.

  Files: `application/forms/SmartBlockCriteria.php`,
  `application/models/Block.php` (save/load + WHERE),
  `application/views/scripts/form/smart-block-criteria.phtml`,
  `public/js/airtime/playlist/smart_blockbuilder.js`, docs
  in EN/DE/FR/ES `LIBRARY.md`.

### Changed

- **Track-history Title/Artist mapping for webstream + line-in
  swapped** (operator follow-up 2026-05-23 v18.4).  v18.3 put
  `description` into the Artist column and `name` into the
  Title column; operator preferred the opposite — short `name`
  in the Artist column (like a band name), longer `description`
  in the Title column (like a song title).

    Webstream:  title = cc_webstream.description (fallback: name)
                artist = cc_webstream.name
    Line-In:    title = rastatime_linein.description (fallback: name)
                artist = rastatime_linein.name

  Same fallback rule as before: when `description` is empty
  (NULL or trimmed-empty), `name` is used so Title is never
  blank.  Artist is always the short `name` and therefore
  never blank.

  De-dupe SQL switched from matching on `description` (v18.3)
  to matching on `name` (v18.4) — `name` is the stable
  identifier across this swap and stays the same regardless
  of how the operator edits the description later.

- **Track-history Artist column now carries the `description`
  field for webstream + line-in entries** (operator request
  2026-05-23 v18.3).  Previously the synthetic block entries
  written by `HistoryService::insertPlayedItem()` for scheduled
  webstream and scheduled line-in items duplicated the short
  name into both `track_title` and `artist_name`.  Operator
  feedback: the Artist column should carry the longer-form
  `description` (Webstream: `cc_webstream.description`,
  Line-In: `rastatime_linein.description`) — leaving Title as
  the short label gives a two-line "Title — Artist" view with
  meaningful information on both lines, instead of repeating
  the same string.

  Fallback: when `description` is empty (NULL or trimmed-empty
  string), we keep writing `name` into the Artist column so
  the field is never blank.

  Surfaces in the Track-History widget AND the Analytics
  Playout-History dashboard (both read from
  `cc_playout_history` without further interpretation of
  what's in `track_title` vs `artist_name`).

  De-dupe SQL in both branches updated to look up the new
  Artist value, so a Liquidsoap restart firing the same
  notify still produces only one row per slot.

### Fixed

- **`Object of class DateTime could not be converted to string`
  in `insertPlayedItem` de-dupe SQL** (operator second follow-up
  2026-05-23 v18.2).  Both the v18 webstream branch and the
  v18.1 line-in branch bound `$recordStart` (a `DateTime` object
  from `CcSchedule::getDbStarts(null)`) directly to a PDO
  `:starts` placeholder.  Under PHP 8 `PDO::bindValue()` no
  longer auto-stringifies the object — it throws a fatal Error,
  which the `insertPlayedItem` `try`/`catch` rolls back (`con->
  rollback`) before re-throwing.  The outer `notifyMediaItem-
  StartPlayAction` `catch` logs and continues, but the
  history row is gone.  Net effect: every webstream-as-show-
  content and every line-in-as-show-content notify silently
  produced zero history rows.

  First production trigger was today's 09:55:00 `PLAY (line-in)
  name='Jabra-Mikro' show=test-line-in` event, which threw three
  identical exceptions visible in `logs/legacy.log` at 07:55:00
  / 08:01:06 / 08:07:00 UTC.

  Fix: pre-format `$recordStart` once into `$recordStartStr`
  (`'Y-m-d H:i:s'`) and bind the string to both `:starts`
  placeholders.  The Propel `setDbStarts($recordStart)` calls
  on the new `CcPlayoutHistory` row stay unchanged — Propel
  accepts `DateTime` directly.

  Same hotfix: the v18.1 `Logging::debug` line in
  `insertPlayedItem` printing `(file_id, stream_id, linein_id)`
  is promoted to `Logging::info` so it shows up in production
  logs without flipping the log level.  Future regressions in
  this code path will be diagnosable from a single `grep
  insertPlayedItem` over `legacy.log` without touching the
  PHP-frontend log config.

- **Scheduled Line-In items now appear in cc_playout_history**
  (operator follow-up 2026-05-23 v18.1).  The v18 commit
  earlier the same day covered scheduled file plays
  (`cc_schedule.file_id`) and scheduled webstream items
  (`cc_schedule.stream_id`), but silently missed the third
  shape RastaTime supports: scheduled Line-In items
  (`cc_schedule.linein_id`, RastaTime-only column added by
  legacy migration 0047 in the Line-In Library Phase A).
  Operator example that exposed the gap: a show with a
  "Jabra-Mikro" line-in slot inside — `notifyMediaItem-
  StartPlayAction` fired (Liquidsoap's `_on_linein_start`
  calls `_notify_media_started(row_id)` just like the file
  and webstream paths), but `insertPlayedItem` had no
  `linein_id` branch and dropped the call without writing
  any history row.

  Fix: `HistoryService::insertPlayedItem()` now reads
  `cc_schedule.linein_id` via raw SQL (the Propel-generated
  `CcSchedule` class doesn't know about the column because
  it was added after the ORM sources were generated, and
  we deliberately don't regenerate Propel sources just for
  one column) and, when set, writes a synthetic "block"
  history row analogous to the webstream branch: `file_id
  = NULL`, `instance_id` from the schedule, `track_title
  = artist_name = rastatime_linein.name`, plus `showname`.
  De-duped on `(instance_id, starts, artist_name)` so
  Liquidsoap restarts that re-fire the notify don't
  double-insert.  Surfaces in both the Track History
  widget and the Analytics Playout History dashboard.

  Also added in the same hotfix:
    - Debug-level `Logging::debug` line printing the
      `(file_id, stream_id, linein_id)` triple at the
      start of every `insertPlayedItem` call, so future
      bug reports against this code path can be diagnosed
      from the legacy log without re-instrumenting.
    - Explicit `Logging::warn` when the webstream branch
      hits `getCcWebstream() === null` (previously the
      branch silently exited with no trace), and when a
      schedule row arrives with none of the three FK
      columns set.
    - Track History widget manual (EN/DE/FR/ES) updated
      from "Five kinds of rows" to **Six kinds of rows**
      with the new scheduled-line-in path described.

### Added

- **Live-Show + Webstream content in cc_playout_history**
  (operator request 2026-05-23 v18).  Closes two gaps in
  the v17 Line-Input logging:

  1. **Webstream AS show content** — when an operator
     drops a `cc_webstream` row into a show's schedule
     (operator example: "Event Calendar" running
     for the duration of a show slot), the schedule item
     starting previously generated no history row at all
     (`HistoryService::insertPlayedItem` had a "don't add
     webstreams" early-return).  Now writes a synthetic
     "block" row with `file_id = NULL` + `instance_id` +
     starts/ends from `cc_schedule`, plus three metadata
     rows: `track_title = artist_name = cc_webstream.name`
     + `showname`.  De-duped on
     `(instance_id, starts, artist_name)` so a Liquidsoap
     restart that re-fires the notify call doesn't double-
     insert.  Surfaces in both the Track History widget
     and the internal Analytics Playout History dashboard.
  2. **Live show with no scheduled items** — when an
     operator creates a show slot but schedules nothing
     in it (so `cc_show_instances.time_filled =
     '00:00:00'`), Liquidsoap auto-switches to master_dj
     for the slot duration.  This path bypasses the
     Dashboard-source-switch hook from v17 entirely.  Now
     covered by a new `HistoryService::
     ensureLiveShowLogged()` opportunistic side-effect
     called from `ApiController::liveInfoAction` and
     `liveInfoV2Action` (both hot-path endpoints polled
     by every now-playing widget).  Writes one row per
     live-show instance with `file_id = NULL`,
     `track_title = operator label`, `artist_name =
     "Live Show"` (distinguishes from the manual-switch
     "Master Source" / "Show Source" labels), guarded by
     an idempotent `(instance_id + file_id IS NULL)` lookup
     so polling traffic can't cause duplicates.  Failure
     wrapped in try/catch + `Logging::warn` so a history-
     write error never breaks the live-info response.

  After v18 the Track History widget + Analytics Playout
  History dashboard now show **five row kinds**:
  scheduled file plays, scheduled webstream items (NEW),
  per-track webstream ICY metadata, live-show sessions
  (NEW), and manual Dashboard source switches.

- **AutoDjService: max auto-show duration raised from
  12 h to 24 h** (operator request 2026-05-23 v18).
  Original 12 h cap (operator Q2 from 2026-05-21) was
  too low for long-form live events and overnight blocks
  that legitimately need to fill a full day before the
  next manually-scheduled show kicks in.  Code change
  is one constant + 3 comment-updates in
  `AutoDjService.php`; the rest of the fill / cleanup
  logic is unchanged.

- **Line-Input session logging in cc_playout_history**
  (operator request 2026-05-22 v17).  Master Source +
  Show Source switches (= Line-In + remote-DJ) now write
  history rows whenever the Dashboard source-switch toggles
  ON, with `ends` set when the switch goes OFF.  Surfaces
  in both the Track History widget AND the internal
  Analytics Playout History dashboard (both read from
  `cc_playout_history`).

  Operator-explicit scope: do NOT pull real stream
  metadata from Liquidsoap (Line-In is raw audio with no
  ICY data anyway); just log the source label as the
  display title.  Operator-configurable via the new
  `widget_line_input_label` Preference (default "Line
  Input"), editable under Settings → Widgets → Track
  History → "Line-Input label".

  Implementation:
    - `application/models/Preference.php`: new
      `GetWidgetLineInputLabel` / `SetWidgetLineInputLabel`.
    - `application/services/HistoryService.php`: new
      `insertLineInLog($sourcename, $startDT)` and
      `endLineInLog($sourcename, $endDT)`.  insertLineIn-
      Log binds to the currently-airing show instance
      (best-effort via `Application_Model_Show::
      GetCurrentShow`), writes `file_id = NULL` (same
      shape as a webstream entry), and stores three
      metadata rows: `track_title` (= operator label),
      `artist_name` (= "Master Source" / "Show Source"
      so a future UI can differentiate the two), and
      `showname` (when bound to a show).  Wrapped in
      try/catch + Logging::warn so a history-write
      failure can never break the on-air state.  endLineIn-
      Log closes the most-recent matching open row
      (file_id NULL + ends NULL + artist_name match) —
      idempotent, safe to call multiple times.
    - `application/controllers/DashboardController.php`:
      Source-switch handler picks up new HistoryService
      calls for master_dj / live_dj (scheduled_play
      stays out of this path — it goes through
      `HistoryService::insertPlayedItem` per item start).
    - `application/forms/WidgetTrackHistory.php`: new
      `line_input_label` text input.
    - `application/controllers/EmbeddablewidgetsController.php`:
      populate + persist for the new Preference.
    - `application/views/scripts/embeddablewidgets/
      track-history.phtml`: caption explains what the
      label is for + which source switches it covers.
    - `docs/manual/WIDGETS.md` + `de/` + `fr/` + `es/` —
      source-table description now lists the three row
      kinds (scheduled / webstream / line-in).
    - `BACKLOG.md`: the "Line-In Metadaten" deferred
      item flipped to DONE with the implementation
      scope + a note on the one known limitation
      (direct Liquidsoap-Source-Connect bypasses the
      Dashboard hook).

  Known limitation: the hook fires only on Dashboard-UI
  source-switches.  A DJ connecting directly to the
  Icecast source endpoint won't trigger the history
  write — that would need a Liquidsoap/Pypo bridge
  extension.  Standard operator workflow is via the
  Dashboard though, so in practice this rarely matters.

- **Public Embed Widget: Track History** (operator request
  2026-05-22, BACKLOG widget-wave 3).  Recent-track playout
  log for the last 7 days — visitor picks a day from a
  date-picker (HTML5 native), chooses a page size
  (10/20/50/100), and the widget lists the played tracks in
  reverse-chronological order.  Click any row → modal with
  the track's metadata + show context + click-through link
  to the show URL when configured.

      <iframe src=".../embed/track-history"
              width="100%" height="500" frameborder="0"></iframe>

  URL parameters: `date` (clamped to -6..0 days from
  today), `pagesize` (10/20/50/100, default 10), `theme`,
  `cache`, `bg`, `bgcolor`, `timezone`.

  Pagination: "Load more" button at the footer appends the
  next page in-place.  Hard-capped at 10 pages × 100
  pagesize = 1000 rows total — operators who need a deeper
  history-browser use the internal Playout History
  dashboard.

  Files:
    - `application/controllers/EmbedController.php` —
      `trackHistoryAction` + `trackHistoryDataAction` +
      `_resolveTrackHistoryDay` + `_fetchTrackHistoryRows`.
      SQL: cc_playout_history JOIN cc_files LEFT JOIN
      cc_show_instances → cc_show.  Tracks without a
      file_id (some auto-DJ filler entries) are filtered
      out — they have no usable display data.  hasMore
      detection via a +1 lookup (lighter than SELECT
      COUNT(*)).
    - `application/views/scripts/embed/track-history.phtml`
      — header band (date-picker + Today + pagesize),
      `<ul>` list, footer (Load-more + status), modal
      scaffolding.
    - `application/controllers/EmbeddablewidgetsController.php`
      — new `trackHistoryAction` settings page.
    - `application/forms/WidgetTrackHistory.php` — single
      empty-state label input.
    - `application/views/scripts/embeddablewidgets/track-history.phtml`
      — settings page: label form + preview iframe (dark
      backdrop) + two embed-code snippets (pagesize 10 + 50).
    - `application/configs/navigation.php` — new "Track
      History" submenu entry under Widgets, next to On Air
      Today.
    - `application/models/Preference.php` — new
      `GetWidgetNoTrackHistory` / `SetWidgetNoTrackHistory`
      pair with English fallback.
    - `public/css/embed/now-playing-widget.css` — new
      `.np-track-history` block: header band, list, load-
      more footer, modal styling.  Kantig + accent-colour
      conventions match the Wave-2 widgets.
    - `public/js/airtime/embed/track-history-widget.js` —
      vanilla JS runtime (~260 LoC): date / pagesize
      handlers, Load-more appender, row-click modal,
      hour-without-leading-zero formatter.
    - `docs/manual/WIDGETS.md` + `de/` + `fr/` + `es/` —
      new §8 chapter, family table row added, downstream
      sections renumbered 9-14.

- **Public Embed Widget: Multi-View Schedule** (operator
  request 2026-05-22, BACKLOG widget-wave 2 second half).
  Calendar-style iframe widget powered by FullCalendar 6.1.10
  (locally vendored, no CDN dependency).  Sister widget to
  the simpler Weekly-Schedule tab widget; sits under it in
  the **Settings → Widgets** submenu.

      <iframe src=".../embed/multi-view-schedule"
              width="100%" height="600" frameborder="0"></iframe>

  Three operator-switchable views: **Day**, **2-Day**,
  **Week**.  In-widget header band with ◀ / ▶ navigation,
  centred date-range label, **Today** button (snaps view +
  re-runs auto-scroll), and DAY / 2-DAY / WEEK toggle.

  Show slots are coloured from each show's configured
  `cc_show.background_color`; empty colours fall back to a
  soft accent fill.  Clicking a show opens a modal with the
  show's name, time range, description, and a click-through
  link to the show URL (if configured).  The currently-
  airing show is outlined with an accent ring, and on
  first paint (or after a Today click) the calendar auto-
  scrolls the now-indicator line into the centre of the
  viewport.

  URL parameters: `view=day|2day|week`, `theme`, `cache`
  (default 300 s = 5 min — bigger than the other widgets
  because the calendar payload is larger and refreshes
  less often), `bg`, `bgcolor`, `timezone`.

  Inspired by the operator's existing radio-calendar
  prototype (https://example.org/radio-calendar/), reworked
  to source from RASTATIME's cc_show_instances + cc_show
  instead of the original Outlook calendar bridge.

  Files:
    - `application/controllers/EmbedController.php` —
      two new actions (`multiViewScheduleAction`,
      `multiViewScheduleDataAction`) + one helper
      (`_fetchMultiViewEvents`).  `_resolveCacheTtl` picks
      up an optional `$defaultSeconds` parameter so this
      widget can default to 300 s instead of 60 s.
    - `application/views/scripts/embed/multi-view-schedule.phtml`
      — vanilla shell with FullCalendar mount point + header
      band markup + modal scaffolding.
    - `application/controllers/EmbeddablewidgetsController.php`
      — new `multiViewScheduleAction` settings page.
    - `application/forms/WidgetMultiViewSchedule.php` —
      single empty-state label input.
    - `application/views/scripts/embeddablewidgets/multi-view-schedule.phtml`
      — settings page: label form + dark-backdrop preview
      iframe + ready-made embed-code snippets for all three
      default views.
    - `application/configs/navigation.php` — new submenu
      entry "Multi-View Schedule" right under "Weekly
      Schedule" (operator-requested placement).
    - `application/models/Preference.php` — new
      `GetWidgetNoMultiViewSchedule` /
      `SetWidgetNoMultiViewSchedule` pair with English
      fallback.
    - `public/js/libs/fullcalendar/index.global.min.js`
      (~282 KB) — vendored FullCalendar 6.1.10 bundle (core
      + day-grid + time-grid + list views; CSS injected at
      runtime, no separate stylesheet).
    - `public/js/libs/fullcalendar/locales-all.global.min.js`
      (~26 KB) — all 80+ locales bundled.
    - `public/js/libs/fullcalendar/VERSION.txt` — pinned
      version + upgrade instructions.
    - `public/js/airtime/embed/multi-view-schedule-widget.js`
      — vanilla JS runtime (~350 LoC): FullCalendar init +
      lazy event-fetch + custom header wiring + modal +
      auto-scroll-to-now + current-event marking.
    - `public/css/embed/now-playing-widget.css` — new
      `.np-multi-view-schedule` block (~200 LoC): header
      band, view switcher, FullCalendar theme integration,
      kantig (zero border-radius) overrides, accent-coloured
      now-indicator, modal styling, light/dark theme
      variants.
    - `docs/manual/WIDGETS.md` + `de/` + `fr/` + `es/` —
      new §7 chapter; family table updated; downstream
      sections renumbered 8-13.

- **Public Embed Widget: Weekly Schedule v2**
  (operator request 2026-05-22, BACKLOG widget-wave 2 first
  half).  Modernised replacement for the upstream jQuery 1.8.3
  + Handlebars schedule embed.  Same `/embed/weekly-program`
  endpoint, fully Wave-1-styled internals:
    * Vanilla JS (no jQuery, no Handlebars).
    * Transparent background blends into the embedding page.
    * Wave-1 URL parameters: `theme` (auto/dark/light),
      `cache` (10..3600 s), `overflow` (ellipsis/marquee),
      `link` (plain/underline, default plain), `timezone`.
    * New `?week_offset=-52..52` parameter for ±N week
      navigation.  ◀ / ▶ buttons in the widget header
      update the URL parameter in-place via
      `history.pushState` and reload.
    * New `?bg=URL` parameter — optional cover-positioned
      background image (operator hosts the image themselves,
      typically on the station's own site).
    * Show names linked to a `cc_show.url` render as
      click-through links opening in a new tab.
    * "Powered by LibreTime" footer removed.
    * Operator-configurable empty-state label "No shows
      scheduled on this day" (per-day-tab placeholder when
      a particular day has no scheduled shows).

  Settings page at **Settings → Widgets → Weekly Schedule**
  hosts the empty-state label, a live preview on a dark
  backdrop, and a ready-made embed-code snippet.

  Width is 400 px (wider than the 340 px now-playing /
  on-air-today widgets — the row layout needs more horizontal
  space for the HH:MM-HH:MM cell + the show-name cell without
  truncation).

  Files:
    - `application/controllers/EmbedController.php` —
      modernised `weeklyProgramAction` reuses the existing
      `_resolveCacheTtl` / `_resolveTimezone` / `_emitCacheHeaders`
      helpers, threads new view-vars for the Wave-1 conventions.
    - `application/common/WidgetHelper.php` — new optional
      `$weekOffset` parameter on `getWeekInfoV2`; behaviour
      identical to pre-2026-05-22 when offset is 0.
    - `application/views/scripts/embed/weekly-program.phtml` —
      complete rewrite: vanilla JS shell, JSON `<script>`
      data block, transparent BG, optional `--np-bg-image`
      inline CSS variable.
    - `application/controllers/EmbeddablewidgetsController.php` —
      modernised `scheduleAction` (now a form + preview +
      embed-code page like the other widget settings).
    - `application/forms/WidgetWeeklySchedule.php` — single
      label input + Save submit.
    - `application/views/scripts/embeddablewidgets/schedule.phtml` —
      mirror layout of the other widget settings pages.
    - `application/models/Preference.php` — new
      `GetWidgetNoWeeklyShows` / `SetWidgetNoWeeklyShows`
      with English fallback.
    - `public/css/embed/now-playing-widget.css` — new
      `.np-weekly-schedule` block: header band with
      navigation buttons, day-tab strip, per-day row list.
      Inherits the .np-widget theme variables.
    - `public/js/airtime/embed/weekly-schedule-widget.js` —
      new vanilla JS runtime (~280 LoC): parses the JSON
      payload, builds the tabs + panels, wires ◀ / ▶ to
      history.pushState + reload, pre-selects today's tab
      when week_offset is 0.
    - `docs/manual/WIDGETS.md` + `de/` + `fr/` + `es/` —
      new §6 chapter for the modernised widget; family
      table row updated; renumbered downstream sections
      7-12.

- **Public Embed Widget: On Air Today** (operator request
  2026-05-22, BACKLOG widget-wave 1 third half — added on top
  of the Now-Playing / Next-Latest pairs).  A compact day-grid
  widget that lists today's schedule from the currently-airing
  show through the next several upcoming shows.  Capped at the
  station's midnight so the widget never spills into tomorrow's
  programme:

      <iframe src=".../embed/on-air-today"
              width="300" height="250" frameborder="0"></iframe>

  Each row reads "HH:MM - HH:MM  Show name", with the
  currently-airing row in bold and show names linked to their
  `cc_show.url` opening in a new tab (`target="_blank"
  rel="noopener noreferrer"`).

  Code-side default = 6 total rows (1 current + 5 upcoming),
  changeable via the `ON_AIR_TODAY_DEFAULT_LIMIT` class
  constant on `EmbedController`.  Operators can override per-
  embed with `?limit=N` (clamped 1..20).

  URL parameters: `limit`, `day` (YYYY-MM-DD, optional —
  pin any specific day for historical or upcoming overviews),
  `theme`, `cache`, `overflow`, `timezone`.

  Day boundary follows the station's calendar day (00:00 to
  24:00 in the resolved timezone).  A show that started
  yesterday 23:30 and is still on air at 14:00 today counts
  as the current row; a show starting tomorrow 00:30 is
  never listed even if `limit` would leave room.  Same
  `modified_instance` filtering as the Next/Latest Shows
  widgets so cancelled / moved instances do not leave
  phantom rows.

  Refresh model: identical to the other widgets — JS poll
  cadence matches the HTTP cache TTL, with an early refresh
  fired within ~1 s when the currently-airing row's end
  passes so the bold highlight migrates to the next row
  without waiting out the cache TTL.

  Settings page at **Settings → Widgets → On Air Today**
  hosts: a single empty-state label (default "No shows on
  air today"), a live preview iframe on a dark backdrop,
  and a ready-made `<iframe>` embed code block.  No show
  picker — the widget auto-pulls the live schedule.

  Files:
    - `application/controllers/EmbedController.php`
        Two new actions: `onAirTodayAction`,
        `onAirTodayDataAction`.  Plus private helpers
        `_prepareOnAirTodayView`, `_resolveOnAirTodayLimit`,
        `_resolveOnAirTodayWindow`, `_fetchOnAirTodayShows`.
        New class constant `ON_AIR_TODAY_DEFAULT_LIMIT = 6`.
    - `application/views/scripts/embed/on-air-today.phtml`
        Header band + `<ul>` of `<li>` rows with time-of-day
        cell + name cell (anchor-wrapped when URL non-empty).
    - `application/controllers/EmbeddablewidgetsController.php`
        New `onAirTodayAction` settings page.
    - `application/forms/WidgetOnAirToday.php`
        One text input (empty-state label) + Save submit.
    - `application/views/scripts/embeddablewidgets/on-air-today.phtml`
        Mirror layout of the other widget settings pages.
    - `application/configs/navigation.php`
        New submenu entry "On Air Today" under Widgets.
    - `application/models/Preference.php`
        New `GetWidgetNoOnAirToday` / `SetWidgetNoOnAirToday`
        with English-fallback.  Backed by `cc_pref` key
        `widget_no_on_air_today`.
    - `public/css/embed/now-playing-widget.css`
        Extended with `.np-on-air-today` block: header band,
        list rows with time-left/name-right flex layout,
        bold current-row treatment, inherit-coloured
        underlined links.
    - `public/js/airtime/embed/on-air-today-widget.js`
        New runtime: per-second `paintTimes()` + periodic
        `pollOnce()` + early-poll on current-row end
        crossover for today's view.
    - `docs/manual/WIDGETS.md` + `de/` + `fr/` + `es/`
        New §5 "On-Air-Today widget" plus new
        troubleshooting entry; renumbered downstream
        sections 6–11.

- **Public Embed Widgets: Next Shows + Latest Shows**
  (operator request 2026-05-22, BACKLOG widget-wave 1 second
  half).  Two new drop-in iframe widgets that list multiple
  instances of a single recurring show — sibling widgets to
  the Now-Playing pair but for the "next four episodes" /
  "last three episodes" use case typical on a per-show
  sidebar of a station's public website.

      <iframe src=".../embed/next-shows?show_id=42"
              width="300" height="140" frameborder="0"></iframe>
      <iframe src=".../embed/latest-shows?show_id=42"
              width="300" height="120" frameborder="0"></iframe>

  Both widgets share a single template (`shows-list.phtml`),
  a single JSON endpoint (`/embed/shows-data`), and a single
  300 px-wide CSS layout.  The only structural difference is
  ASC vs DESC ordering of the instances list and the default
  `limit` (4 for next, 3 for latest).

  Show identification:
    - `?show_id=N` — preferred, stable across renames; all
      instances of a recurring show share the same
      `cc_show.id`.
    - `?show=Name` — case-sensitive fallback used when
      `show_id` is absent.  `show_id` wins when both are set.

  URL parameters: `show_id` / `show`, `limit` (1..20),
  `theme` (auto / dark / light), `cache` (10..3600 s,
  default 60), `overflow` (ellipsis / marquee), `timezone`.

  Modified / cancelled instances
  (`cc_show_instances.modified_instance = TRUE`) are filtered
  out, matching the convention `Application_Model_Show::
  getNextShows` already uses on the internal Dashboard, so a
  single postponed episode does not leave a phantom row in
  the public widget.

  Refresh model: identical to the Now-Playing widgets — JS
  poll cadence matches the HTTP cache TTL, and a slipped
  topmost row (Next Shows) triggers an immediate refresh
  within ~1 s so the widget flips on time even under long
  cache TTLs.

  Files:
    - `application/controllers/EmbedController.php`
        Three new actions: `nextShowsAction`,
        `latestShowsAction`, `showsDataAction`.  Plus private
        helpers `_prepareShowsListView`, `_resolveShowsLimit`,
        `_resolveShowId`, `_fetchShowMeta`,
        `_fetchShowInstances`.  Reuses `_resolveCacheTtl`,
        `_resolveTimezone`, `_emitCacheHeaders`,
        `_formatTimestamp` from the Now-Playing block below.
    - `application/views/scripts/embed/shows-list.phtml`
        Shared template for both `next-shows` and
        `latest-shows` actions; renders the title row plus
        the `<ul>` of instances.
    - `application/controllers/EmbeddablewidgetsController.php`
        New `nextLatestShowsAction` settings page with a
        show-picker dropdown (cc_show ordered by name), the
        two empty-state labels, live preview iframes on a
        dark backdrop, and the ready-made embed-code blocks
        with `show_id` baked in.
    - `application/forms/WidgetNextLatestShows.php`
        New form: `preview_show_id` select +
        `widget_no_next_shows` + `widget_no_latest_shows`
        text inputs + Save submit.
    - `application/views/scripts/embeddablewidgets/next-latest-shows.phtml`
        Mirror-layout of the Current Show/Track page —
        800 px max-width, preview iframes only render once
        a show is picked.
    - `application/configs/navigation.php`
        New submenu entry "Next/Latest Shows" under Widgets.
    - `application/models/Preference.php`
        Two new getters/setters with English-fallback pattern:
        `GetWidgetNoNextShows`, `SetWidgetNoNextShows`,
        `GetWidgetNoLatestShows`, `SetWidgetNoLatestShows`.
        Backed by `cc_pref` keys `widget_no_next_shows` and
        `widget_no_latest_shows`.
    - `public/css/embed/now-playing-widget.css`
        Extended with `.np-shows-list .np-list-row` /
        `.np-list-date` / `.np-list-time` / `.np-list-empty`
        rules.  Inherits theme variables + transparency from
        the base `.np-widget` ruleset above.
    - `public/js/airtime/embed/shows-list-widget.js`
        New runtime: per-second `paintRows()` to re-render the
        date / time cells from the absolute timestamps in
        `data-starts` / `data-ends`, periodic `pollOnce()` to
        rebuild the `<ul>`, plus the early-poll mechanism
        keyed on the topmost upcoming instance for the
        Next-Shows widget.
    - `docs/manual/WIDGETS.md` + `de/` + `fr/` + `es/`
        New §4 "Next-Shows / Latest-Shows widgets" plus new
        troubleshooting entry; renumbered downstream sections
        5–10.

- **Public Embed Widgets: Now Playing — Show + Now Playing —
  Track** (operator request 2026-05-22, BACKLOG widget-wave 1
  first half).  Two new drop-in iframe widgets for external
  station homepages.  Two-line text layout, transparent
  background, no auth required:

      <iframe src=".../embed/now-playing-show?theme=dark"
              width="100%" height="50" frameborder="0"></iframe>

  Each widget shows the current item on line 1 (name left,
  end-countdown right) and the next item on line 2 (name left,
  start–end window right).  Track widget renders as
  "Artist - Title"; show widget as the show name.

  URL parameters: `theme` (auto / dark / light), `cache`
  (server-side HTTP TTL in seconds, 10–3600, default 60),
  `timezone` (any standard IANA zone, defaults to station).

  Both widgets share a single JSON feed at
  `/embed/now-playing-data` (cached identically to the iframe
  HTML).  The in-iframe JS recomputes the countdown every
  second client-side from absolute ISO timestamps and
  proactively re-polls when the current item's end-time
  passes — so a `cache=300` embed still flips to the next
  track within ~1 s of it starting, the staleness only ever
  affects the first display after a long idle pause.

  Files:
    - `application/controllers/EmbedController.php`
        Three new actions: `nowPlayingShowAction`,
        `nowPlayingTrackAction`, `nowPlayingDataAction`.
        Plus private helpers `_renderNowPlayingWidget`,
        `_resolveCacheTtl`, `_resolveTimezone`,
        `_emitCacheHeaders`, `_buildNowPlayingPayload`,
        `_slimShow`, `_slimTrack`, `_formatTimestamp`.
        Data source: `Application_Model_Schedule::GetPlayOrderRange()`
        (same as `/api/live-info` but trimmed payload).
    - `application/views/scripts/embed/now-playing-show.phtml`
    - `application/views/scripts/embed/now-playing-track.phtml`
    - `public/css/embed/now-playing-widget.css`
        Two-line flexbox layout, three theme variants,
        prefers-color-scheme media query for the auto theme,
        muted state for stale/empty data.
    - `public/js/airtime/embed/now-playing-widget.js`
        Vanilla JS (no jQuery), ~250 LoC.  Per-second
        countdown tick + cache-TTL polling + early re-poll
        on item end-time crossing + jittered poll cadence
        so massively-embedded widgets don't synchronise.

  Documentation: new `docs/manual/{en,de,fr,es}/WIDGETS.md`
  chapter; master USER_MANUAL TOC updated in all four
  languages.  ARCHITECTURE.md gets a new Section 23.22.

- **Smart Block: new "Exclude tracks played lately" pool-restriction
  toggle** (operator request 2026-05-21).  Sits between the existing
  `Allow only tracks not played yet` and `Allow only tracks with
  expiry date` toggles in the Advanced-options section of the
  New/Edit Smart Block dialog.  When enabled, the smart block's
  candidate pool is narrowed to tracks whose `cc_files.lptime` is
  either `NULL` (never played — included by operator decision
  2026-05-21) or older than the configured hours-back window.
  Companion field "Exclude tracks played in the last hours" accepts
  an integer 1..8760 (1 hour up to 1 year, operator decision
  2026-05-21); validator rejects empty / out-of-range values when
  the master checkbox is on.  Defaults to 24 h on first
  toggle-on.  Compositional with all existing criteria — common
  pairing is `Sort: Random` + `Exclude played lately: 24 h` for
  fresh-rotation auto-build content.

  Persisted in two new `cc_block_criteria` rows
  (`exclude_played_lately`, `exclude_played_lately_hours`) — no
  schema change.  Backwards-compatible: existing smart blocks
  without these rows behave exactly as before.

  Files:
    - `application/forms/SmartBlockCriteria.php` — checkbox +
      number-input form elements with Between(1, 8760) validator.
    - `application/models/Block.php` — save (2 rows), load (2
      elseif clauses), and `getListOfFilesUnderLimit()` WHERE
      clause `cc_files.lptime IS NULL OR cc_files.lptime <
      NOW() - INTERVAL 'X hours'`.  Server-side clamp of the
      hours value to [1, 8760] as defence-in-depth against a
      hand-crafted POST.
    - `application/views/scripts/form/smart-block-criteria.phtml`
      — two separate `<dl>` rows mirroring the podcast
      Auto-Expiry pattern (operator request 2026-05-22): the
      first row holds the master checkbox; the second row
      (own label + own input) is hidden by default and shown
      only when the master is on.  Initial visibility is
      computed server-side from the persisted checkbox value
      so the row does not flash visible before
      smart_blockbuilder.js takes over.
    - `public/js/airtime/playlist/smart_blockbuilder.js` —
      show/hide of the entire second dl-row (selector
      `#sp_exclude_played_lately_hours_wrap`) based on master
      checkbox; auto-fills 24 on first toggle-on so the
      active state is never empty.

  Documentation updated in all four languages under
  `docs/manual/{en,de,fr,es}/LIBRARY.md` (Smart Blocks section)
  and ARCHITECTURE.md Section 23.

### Changed

- **Track History: webstream entries + "Played in the show:"
  modal caption** (operator request 2026-05-22 v16, two
  items in one shot):

  1. **Webstream plays included in the history**.  Previous
     versions used an `INNER JOIN cc_files` which silently
     dropped all rows with `file_id IS NULL` — the shape
     that `HistoryService::insertWebstreamMetadata()`
     writes when Liquidsoap reports a webstream metadata
     update via `/api/notify-webstream-data`.

     Fix: `LEFT JOIN cc_files` plus a fallback lookup
     against `cc_playout_history_metadata` (correlated
     subquery with the `track_title` / `artist_name`
     constants from `MDATA_KEY_TITLE` / `MDATA_KEY_CREATOR`).
     For webstream entries the `artist` field carries the
     webstream's display name (`cc_webstream.name`,
     typically the operator-set label like "BBC News Live")
     and the `title` carries whatever ICY-/Now-Playing-
     metadata the upstream stream server sent at the time.
     New `isWebstream` flag exposed in the JSON payload so
     future UI passes can decorate streaming entries
     differently.

     Line-In plays still don't write any metadata to
     `cc_playout_history` — Liquidsoap treats Line-In as
     raw audio without a metadata stream, so the playout
     engine would need a configuration extension to emit
     anything.  Tracked in BACKLOG.md as a defer item with
     a documented solution path.

  2. **Modal: "Played in the show:" caption** added between
     the time-range line and the show-name line.  Operator
     request — labels the show-context for clarity.  When
     a webstream entry has no instance binding (e.g. the
     stream wasn't part of a scheduled show), the caption
     + show-name pair is hidden via a `np-th-no-show` body
     class so the modal doesn't show an orphan label.

  Files:
    - `application/controllers/EmbedController.php` —
      SQL rewrite in `_fetchTrackHistoryRows`: INNER JOIN
      → LEFT JOIN; COALESCE on cc_files + correlated
      subquery to cc_playout_history_metadata; new
      `is_webstream` flag in the row output.
    - `application/views/scripts/embed/track-history.phtml`
      — new `<p class="np-th-modal-show-intro">Played in
      the show:</p>` between time and show in the modal.
    - `public/css/embed/now-playing-widget.css` —
      `.np-th-modal-show-intro` muted-caps caption style;
      `.np-th-no-show` toggle rule that hides both the
      intro and show lines when no show context exists.
    - `public/js/airtime/embed/track-history-widget.js` —
      replaced inline `style.display` toggle with
      `body.classList.toggle('np-th-no-show')` so a single
      CSS rule covers both elements.
    - `docs/manual/WIDGETS.md` + `de/` + `fr/` + `es/` —
      §8 source-table description updated for the LEFT
      JOIN + webstream fallback; modal section mentions
      the new caption + show-context-hide rule.
    - `BACKLOG.md` — new "Line-In Metadaten in Track
      History" deferred entry with a documented solution
      path (Liquidsoap-skript erweitern + insertLineIn-
      Metadata helper).

- **Track History: 'Today' button renamed to 'Now'**
  (operator request 2026-05-22 v15).  Semantically more
  accurate — the button snaps BOTH date and time to the
  current wall-clock value (v14), so "Now" reads truer
  than "Today" (which suggested only the date would
  change).  Rename applied across the rendered button
  label, the CSS class name (`np-th-today` → `np-th-now`),
  the `data-np` attribute (`today` → `now`), the JS state
  variable (`todayBtn` → `nowBtn`), the inline comments,
  and the manual in all four languages.  No behavioural
  change — pure label rename.  Asset hashes auto-bump.

- **Track History v14 polish — 5 operator-requested items**
  (2026-05-22 v14):

  1. **Exclude-short-tracks filter**: drops jingles / station
     IDs / silence-tail entries from the public log.  Toggle
     on by default with a 60 s threshold.  Two new
     Preferences (`widget_track_history_exclude_short`,
     `widget_track_history_min_seconds`).  Per-embed
     `?exclude_short=0|1` + `?min_sec=N` URL parameters
     override the global setting.  SQL adds
     `EXTRACT(EPOCH FROM (ph.ends - ph.starts)) >= :min_sec`
     when the filter is on.

  2. **Time-of-day picker**: new `<input type="time">`
     between the date input and the Today button.
     Semantics: upper-bound — the widget lists tracks that
     ended BEFORE the picked moment, most recent first.
     Default seeds the picker to "now" on first paint so
     the widget opens on the most-recently-played slice.
     `?time=HH:MM` URL parameter for pre-pinned embeds.

  3. **Today button snaps date + time**: clicking Today
     now sets both the date AND the time to the current
     wall-clock value (operator request: "Datum + Uhrzeit
     auf jetzt").

  4. **End-time in row display**: rows now read
     `HH:MM - HH:MM Artist - Title` (was `HH:MM Artist -
     Title`).  Row-time column widened from `min-width:
     3.5em` to `7.5em` to comfortably hold the range.

  5. **Bold artist - title**: `font-weight: 700` on the
     `.np-th-row-title` so the artist / title reads as the
     primary content of each row.

  Settings page (Settings → Widgets → Track History) gets
  the new Exclude-short-tracks checkbox + threshold input,
  with the threshold field showing / hiding client-side
  based on the checkbox state — Auto-Expiry-style toggle
  pattern lifted from the podcast settings.

  Files:
    - `application/models/Preference.php` — 2 new
      Preference accessor pairs.
    - `application/controllers/EmbedController.php` —
      `_resolveTrackHistoryUpperBound`,
      `_resolveTrackHistoryTime`,
      `_resolveExcludeShortFlag`,
      `_resolveMinSecondsThreshold`; SQL `durationClause`
      added in `_fetchTrackHistoryRows`.
    - `application/views/scripts/embed/track-history.phtml`
      — `<input type="time">` + `data-time-local` attribute.
    - `application/controllers/EmbeddablewidgetsController.php`
      — form populate / persist for the two new Preferences.
    - `application/forms/WidgetTrackHistory.php` — checkbox
      + number input elements.
    - `application/views/scripts/embeddablewidgets/track-history.phtml`
      — inline JS toggle for the show/hide behaviour;
      embed-code parameter list updated with `time`,
      `exclude_short`, `min_sec`.
    - `public/css/embed/now-playing-widget.css` —
      `.np-th-time` style; `.np-th-row-time` `min-width`
      bumped to 7.5em; `.np-th-row-title` `font-weight: 700`.
    - `public/js/airtime/embed/track-history-widget.js` —
      `currentTime` state + time-input change handler +
      Today button now snaps date+time to now + row render
      uses `fmtTimeRange` for the start-end display.
    - `docs/manual/WIDGETS.md` + `de/` + `fr/` + `es/` —
      §8 parameter table extended with `time`,
      `exclude_short`, `min_sec`; layout description
      updated for the bold title + start-end-time format.

- **Multi-View Schedule v11 follow-up** (operator-reported that
  the v10 attempt didn't fully land for items 2 + 3 of the
  polish trio below):

  - **Full-width events**: `slotEventOverlap: false` alone
    wasn't enough — FullCalendar 6 treats touch-boundary
    events (event A ends 12:07, event B starts 12:07) as
    "shared columns" and packs them into half-width slots
    even though they don't actually overlap.  Fix: CSS
    override on `.fc-timegrid-event-harness` pinning
    `inset-inline-start: 0`, `inset-inline-end: 0`,
    `width: 100%` with `!important`.  Inspected the live
    payload — zero real overlaps, all boundaries are TOUCH
    or gap, so the override never hides a genuinely
    overlapping show.

  - **Hour format without leading zero**: `clockFormat()`
    was using the FullCalendar object form
    `{ hour: 'numeric', ... }` which gets silently coerced
    back to 2-digit padding in some locale + meridiem
    combinations.  Switched to the explicit string form
    (`'H:mm'` for 24h, `'h:mm a'` for 12h) which is
    deterministic.  The modal's `fmtTimeRange` ported to
    manual fmt24/fmt12 functions for the same reason.

- **All widgets: time format polish trio** (operator request
  2026-05-22 v10).  Three independent UX items:

  1. **Multi-View Schedule: event padding** — `.fc-event`
     vertical padding dropped from `2px 4px` to `0 4px` so
     sub-15-min shows have room for the time + name on one
     line (the standard layout for short events) without
     the text feeling crushed.

  2. **Multi-View Schedule: `slotEventOverlap: false`** —
     FullCalendar's default packs back-to-back events into
     half-width columns when their boundaries kiss
     (e.g. show A ends 12:07, show B starts 12:07).
     Setting `slotEventOverlap: false` renders each event
     in the full column width unless they genuinely
     overlap in time (which is rare in a radio schedule).
     The operator reported the indented layout was
     confusing — full-width events read cleaner.

  3. **All five widgets: hour format without leading zero**
     — `9:00` instead of `09:00`.  Minute stays 2-digit
     (`9:05`, not `9:5`).  Applied to:
     * `now-playing-widget.js` (`fmtTimeOfDay`)
     * `shows-list-widget.js` (`fmtTimeRange.fmt`)
     * `on-air-today-widget.js` (`fmtTimeRange.fmt`)
     * `weekly-schedule-widget.js` (`fmtTimeOfDay`)
     * `multi-view-schedule-widget.js` (`clockFormat`
       helper drives slotLabelFormat + eventTimeFormat,
       plus `fmtTimeRange` for the modal) — uses
       `hour: 'numeric'` instead of `'2-digit'` in the
       FullCalendar / Intl format objects.

  Files: `public/css/embed/now-playing-widget.css` (event
  padding); `public/js/airtime/embed/multi-view-schedule-
  widget.js` (slotEventOverlap, clockFormat,
  fmtTimeRange); `public/js/airtime/embed/now-playing-
  widget.js`, `shows-list-widget.js`,
  `on-air-today-widget.js`, `weekly-schedule-widget.js`
  (per-widget time-format helpers).  Asset hashes auto-
  bump via Assets::url() mtime versioning so visitors
  pick up the new layout on the next iframe reload.

- **Multi-View Schedule: infinite-loop fix + ?clock parameter**
  (operator bug report + UX request 2026-05-22 v9).

  Bug fix: the browser's "page unresponsive" warning was
  popping up every minute or so on the Multi-View Schedule
  settings preview, and the calendar showed no events / no
  navigation.  Root cause was an event-render infinite
  loop:

      eventsSet → markCurrentEvent → ev.setExtendedProp →
        re-render → eventsSet → ...

  FullCalendar's `setExtendedProp` triggers a re-render of
  the mutated event, which fires the `eventsSet` callback,
  which called `markCurrentEvent` again, which mutated every
  event again — a tight loop that froze the browser thread
  until it crossed the unresponsive-script threshold.

  Fix: drop `markCurrentEvent` entirely.  `eventClassNames`
  (already called by FullCalendar on every event render)
  now evaluates `Date.now()` directly against the event's
  start/end and returns `['np-mv-event-current']` or `[]`.
  No mutation, no loop.

  Trade-off: the "currently airing" highlight no longer
  walks with the wall clock once the page is loaded — if
  the operator leaves the iframe open for a full hour the
  highlight stays on the show that was airing at first
  paint.  Re-evaluated on every view change / navigation /
  Today click, which catches 99 % of real-world use.  A
  proper live-update would need a setInterval that
  periodically dirties the calendar, heavier than the
  value.

  New feature: `?clock=24|12|auto` URL parameter to
  control the time-of-day format on the hour axis, in
  show slots, and in the modal.  Default `24` (operator
  preference — the previous locale-default behaviour gave
  `5 PM` for english locales, confusing for European
  stations).  `12` forces AM/PM.  `auto` keeps the
  legacy locale-default behaviour.  Threaded through
  `slotLabelFormat` + `eventTimeFormat` on the
  FullCalendar config, plus the modal's `fmtTimeRange`
  helper.

  Files: `application/controllers/EmbedController.php`
  (new `?clock` param with strict validation); `application/
  views/scripts/embed/multi-view-schedule.phtml`
  (data-clock attribute); `public/js/airtime/embed/multi-
  view-schedule-widget.js` (loop removal + `clockFormat`
  helper + `isCurrentEvent` predicate + modal time-range
  format); `application/views/scripts/embeddablewidgets/
  multi-view-schedule.phtml` (URL params list extended
  with `clock`); `docs/manual/WIDGETS.md` + `de/` + `fr/` +
  `es/` (new `clock` row in the §7 parameter table).

- **Weekly Schedule v2: iframe height bump 340 → 560 px**
  (operator request 2026-05-22 v8).  Pure sizing change —
  no behaviour difference.  The panel `max-height`
  follows up from 250 to 470 px so the show list takes
  advantage of the extra room instead of leaving
  whitespace below.  Updated the iframe height in all six
  places that reference it: the settings page preview
  iframe, the settings page embed-code snippet, and the
  drop-in iframe examples in `docs/manual/WIDGETS.md` +
  `de/` + `fr/` + `es/`.  Operators with existing embeds
  who want to keep the old height can still override via
  the iframe's `height` attribute — the widget body
  doesn't enforce a minimum.

- **Weekly Schedule v2: auto-scroll to the currently-airing
  show** (operator request 2026-05-22 v7).  When the today-tab
  is active, the widget centres the show that is on air
  right now in the panel viewport, so the visitor lands
  directly on "what's playing now" instead of having to
  scroll past the early-morning programme.

  Implementation:
    * `.np-ws-day` becomes its own scroll container
      (`max-height: 250px; overflow-y: auto;`) so the show
      list can grow without spilling outside the 340 px
      iframe (which has `scrolling="no"`).
    * Subtle scrollbar styling (matches `--np-fg-muted`,
      thin on Firefox, 6 px on WebKit).
    * Client-side: each row gets the `.np-ws-row-current`
      class when `Date.now()` falls in `[starts, ends)` —
      same boundary semantics as the On-Air-Today widget.
    * `.np-ws-row-current` is marked with an accent left-
      border (`--np-accent`) so the visitor spots it after
      the scroll; rows reserve a 3 px transparent border-
      left on every line so the layout stays stable.
    * On `activate()` of any day-panel, `scrollToCurrent`
      runs — finds the current row (if any) and computes
      `panel.scrollTop` to centre it.  Skipped when the
      activated day has no airing show, or when the
      visitor switches to a non-today tab (no
      `.np-ws-row-current` is present there).
    * Uses `requestAnimationFrame` so the panel is laid
      out (display:block via `.np-ws-day-active`) before
      reading `offsetTop` / `clientHeight` — avoids the
      first-paint zero-height race.
    * Manual `panel.scrollTop` instead of
      `scrollIntoView({block:'center'})` — the latter walks
      all scroll ancestors and would scroll the embedding
      iframe too in some browsers.

  Files: `public/css/embed/now-playing-widget.css`
  (`.np-ws-day` scroll container + scrollbar styling +
  `.np-ws-row-current` accent border); `public/js/airtime/
  embed/weekly-schedule-widget.js` (current-row marker in
  render + `scrollToCurrent` helper called from
  `activate`); `docs/manual/WIDGETS.md` + `de/` + `fr/` +
  `es/` (new note block about the auto-scroll behaviour).

- **Weekly Schedule v2: kantig look + accent colour + tight
  navigation cap + bgcolor parameter** (operator request
  2026-05-22 v6, five polish items on the just-shipped v2
  widget):

  1. **"Kantig" styling**: the today indicator switches from
     a rounded pill ring (`border-radius: 999px`) to a solid
     accent-coloured rectangle, matching the legacy schedule
     widget's blocky LibreTime-teal look.  Nav buttons and
     day tabs lose their rounded edges everywhere.

  2. **Accent colour as a CSS variable**: `--np-accent`
     (default `#459B8F`, the LibreTime teal) plus
     `--np-accent-hover` (the same colour at 40 % alpha)
     are exposed on the `.np-weekly-schedule` block so a
     future per-station brand override is a one-line change.

  3. **Navigation tightened from ±52 to -2 / +4 weeks**:
     server clamp + JS clamp + view-vars supplied to the
     template; ◀ / ▶ buttons get the `disabled` attribute
     at the boundaries (CSS dims them to 30 % opacity and
     switches the cursor to `not-allowed`).

  4. **Hover states with the accent colour**: day tabs and
     navigation buttons light up at `--np-accent-hover`
     when hovered; show-name links in the row list switch
     to the full `--np-accent` on hover.  Today's tab keeps
     its solid accent on hover (so the highlight doesn't
     fade away on mouse-over).

  5. **`?bgcolor=#hex` URL parameter** for an optional
     background colour, controlled via the `--np-bg-color`
     CSS variable analogous to the existing `--np-bg-image`
     for `?bg=URL`.  Both can stack (colour shows through
     transparent regions of the image, or acts as a fallback
     while the image loads).  Validated against a strict
     `/^#[0-9a-fA-F]{3,8}$/` regex so the value can't
     smuggle CSS via the inline style attribute.

  Files: `application/controllers/EmbedController.php`
  (clamp + bgcolor validation); `application/views/scripts/
  embed/weekly-program.phtml` (data-week-offset-min/max
  attrs + --np-bg-color CSS variable); `public/js/airtime/
  embed/weekly-schedule-widget.js` (clamp + disabled-state
  on the navigation buttons); `public/css/embed/now-playing-
  widget.css` (kantig look + --np-accent + hover states +
  --np-bg-color rule); `application/views/scripts/
  embeddablewidgets/schedule.phtml` (URL params list updated
  to mention bgcolor + new -2..4 range); `docs/manual/
  WIDGETS.md` + `de/` + `fr/` + `es/` (week_offset range,
  bgcolor row, new note about today-tab + active-tab
  styling).

- **Widget width: Now-Playing + On-Air-Today bumped to 340 px**
  (operator request 2026-05-22 v5).  The Current Show, Current
  Track, and On-Air-Today widgets now have a 340 px-wide body
  instead of the previous uniform 300 px — more breathing room
  for the bold show names and the time-of-day cells.

  Next-Shows / Latest-Shows widgets stay at 300 px (they
  serve a narrower sidebar use-case where the tighter body
  reads cleaner).

  Implementation:
  * New marker class `np-now-playing` added to both
    Now-Playing templates so the CSS can target them
    explicitly (`np-on-air-today` already existed).
  * Width cap moved from the unconditional `.np-widget`
    rule into per-family overrides: base default stays
    300 px (covers shows-list), the two wider families
    bump to 340 via `.np-widget.np-now-playing,
    .np-widget.np-on-air-today { max-width: 340px; }`.
  * Marquee animation end-offset parameterised through a
    `--np-marquee-end` CSS variable: 280 px for the narrow
    300 px widgets (default), 320 px for the wider 340 px
    widgets.  Single `@keyframes np-marquee-scroll` works
    for both via `var(--np-marquee-end, 280px)`.
  * Settings-page preview iframes and embed-code snippets
    updated to `width="340"` on both Current Show/Track
    and On-Air-Today pages.

  Files: `application/controllers/EmbedController.php`
  (unchanged); `application/views/scripts/embed/now-
  playing-{show,track}.phtml` (added `np-now-playing` to
  body class); `application/views/scripts/embeddablewidgets/
  current-show-track.phtml` + `on-air-today.phtml`
  (iframe width 300 → 340); `public/css/embed/now-playing-
  widget.css` (per-family max-width override + marquee
  variable); `docs/manual/WIDGETS.md` + `de/` + `fr/` +
  `es/` (Now-Playing & On-Air-Today iframe snippets + Note
  about widget cap updated; Next/Latest still 300 px noted).

- **On-Air-Today: typography & link-default polish**
  (operator request 2026-05-22 v4).  Three small visual
  changes to make the widget more legible at sidebar embed
  sizes:
    * `?link` parameter default flipped from `underline` to
      `plain`.  The underline competed with the (now bold)
      show names; operators who want the classic hyperlink
      affordance back can opt in with `?link=underline`.
    * Row height roughly doubled — `padding: 12px 0` (was
      `3px 0`) and `line-height: 1.6` (was `1.4`), so each
      row reads as a distinct band instead of a tight stack.
    * Uniform bold: header + every row now uses
      `font-weight: 700` and a `1.1em` (rows) / `1.2em`
      (header) font-size.  Operator explicitly asked for
      "all bold, all bigger".  Current-row weight flourish
      removed (would collide with the new uniform weight);
      the `.np-row-current` selector kept live but empty as
      a clean attachment point if the operator later wants
      the current row distinguished by colour or background.
  Files: `application/controllers/EmbedController.php` (link
  default), `public/css/embed/now-playing-widget.css` (the
  size / weight / padding block), `docs/manual/WIDGETS.md`
  + `de/` + `fr/` + `es/` (updated `?link` default in the §5
  parameter table).

- **Public Embed Widget polish trio** (operator request 2026-05-22 v3,
  three small UX changes on top of the wave-1 widgets).

  1. **On-Air-Today: `?link=plain` URL parameter.**  Optional
     URL param to drop the underline from the show-name links
     when the operator prefers a clean text-only look.  Default
     `underline` keeps the previous behaviour and the standard
     hyperlink affordance.  CSS class `.np-link-plain` on the
     widget body.

  2. **Next/Latest Shows: manual show-name input + dropdown
     grouping by name.**  The Settings → Widgets → Next/Latest
     Shows page now offers two ways to identify the show:
       * The existing dropdown — but **grouped by name** so a
         station with seven shows all called "BBC News" sees
         one dropdown entry "BBC News (7 shows)" instead of
         seven near-identical lines.  Single-instance names
         still resolve to `?show_id=N`; multi-instance groups
         use `?show=Name` (semantic change below).
       * A new **manual show-name text input** for operators
         who want to generate embed snippets for shows not (yet)
         in the database, or who prefer to filter by string.
         Tooltips explain that the dropdown takes precedence
         over the manual field (mirrors the `?show_id` >
         `?show` rule the public widget URL uses).

  3. **Next/Latest Shows: light-theme time-cell colour
     alignment.**  The time-of-day cell in the list rows now
     uses the full `--np-fg` colour instead of the muted
     variant, matching the corresponding cell in the
     On-Air-Today widget.  Previously the cell read as
     mid-grey on the light theme that was harder to scan than
     the date cell next to it.

  **Semantic change** (worth noting for existing embeds):
  `?show=Name` on the next-shows / latest-shows widgets now
  matches **every** cc_show row that shares the name, rather
  than silently taking only the first id.  Operators with
  multiple same-named shows (e.g. one per weekday) get a
  merged timeline; operators whose show names are unique see
  identical behaviour.  Backend pivots from
  `_resolveShowId` (single int) to `_resolveShowIds` (int
  array) and switches the WHERE clause from `show_id = :sid`
  to `show_id = ANY(:sids)`.

  Files:
    - `application/controllers/EmbedController.php` —
      `_resolveShowIds`, multi-id WHERE in `_fetchShowMeta`
      and `_fetchShowInstances`, new `?link` parameter for
      On-Air-Today widget.
    - `application/controllers/EmbeddablewidgetsController.php`
      — group-by-name dropdown via ARRAY_AGG SQL, parse the
      "name:..." marker on submit, expose previewShowName +
      manualShowName to the view.
    - `application/forms/WidgetNextLatestShows.php` — new
      `manual_show_name` Zend_Form_Element_Text with tooltip.
    - `application/views/scripts/embeddablewidgets/next-latest-shows.phtml`
      — show-id OR show-name preview/embed URL generator,
      precedence explanation in the form description.
    - `application/views/scripts/embed/on-air-today.phtml` —
      thread the `linkClass` view-var into the body.
    - `public/css/embed/now-playing-widget.css` —
      `.np-link-plain` rule for On-Air-Today links;
      `.np-shows-list .np-list-time` colour from muted to
      full `--np-fg`.
    - `docs/manual/WIDGETS.md` + `de/` + `fr/` + `es/` —
      `?link` parameter row in §5, `?show=Name` description
      updated to reflect multi-match semantics.

- **Public Embed Widgets: Next/Latest Shows theme contrast fix**
  (operator request 2026-05-22).  Bug report: all three themes
  (auto / dark / light) on the new shows-list widgets looked
  visually identical — the theme switch had no obvious effect.
  Root cause: every list row used `color: var(--np-fg-muted)`,
  which renders as a mid-grey in both dark (`#bbb`) and light
  (`#555`) themes — close enough on most embedding backdrops
  that the operator perceived them as the same shade.

  Fix: realign the shows-list colour palette with the Now-Playing
  widget's "current row" convention from wave 1.
    * `.np-row-title` and `.np-list-row .np-list-date` now use
      the full `var(--np-fg)` colour (near-white in dark, near-
      black in light) instead of the muted variant — so the
      theme switch flips text contrast clearly.
    * `.np-list-time` and `.np-list-empty` keep `var(--np-fg-
      muted)` to preserve the "primary date, secondary time-of-
      day" reading hierarchy that mirrors the start–end cell in
      the Now-Playing widget.
  File: `public/css/embed/now-playing-widget.css`.

- **Settings → Widgets → Current Show/Track: page polish**
  (operator request 2026-05-22).  Pure UX cleanup — no
  behaviour change.
  * Page container capped at `max-width: 800px` to match the
    Weekly Schedule settings page so the Widgets section reads
    consistently.
  * Preview iframes forced to `?theme=dark` so the previews
    sit on a dark backdrop that matches the rest of the admin
    UI (the actual embed code at the bottom of the page does
    NOT force a theme, so the public widget keeps following
    the visitor's `prefers-color-scheme`).
  * Section heading renamed `Empty-state labels` → `Labels`
    (shorter, less jargon).
  * Four input labels shortened from `Label when no show is
    on air:` etc. to the actual configured strings
    (`No show on air:`, `No upcoming show:`, `No track
    playing:`, `No upcoming track:`).  The form now reads as
    a list of the outputs rather than meta-descriptions of
    them.
  * Input widths reduced from full-row to `18em` (about 30 %
    of previous width).  Manual tables in
    `docs/manual/{en,de,fr,es}/WIDGETS.md` updated to match
    the new UI labels.

- **Now-Playing widgets: 300 px width cap + truncate / marquee
  overflow handling + operator-configurable empty-state labels
  + dedicated Widgets → Current Show/Track settings page**
  (operator request 2026-05-22).  Three coupled polish items
  that ship together because they all touch the same widget
  pair.

  Width: the widget body is now `max-width: 300 px` to fit
  common station-website sidebar layouts.  An embedding page
  that sets the iframe to 300 px wide gets a flush widget; a
  wider iframe shows white space around the widget.

  Overflow: long show / track names that exceed the 300 px
  body now have a per-embed strategy picked via
  `?overflow=ellipsis|marquee` URL parameter.  `ellipsis`
  (default) truncates with `…`; `marquee` scrolls the text
  left over 24 s so the operator can still read the whole
  title.  Pure CSS animation — no extra JS.

  Empty-state labels: the four placeholder texts that the
  widgets show when a current / next show / track is missing
  are now operator-configurable via four new cc_pref keys
  (`widget_no_current_show`, `widget_no_upcoming_show`,
  `widget_no_current_track`, `widget_no_upcoming_track`).
  Each Preference getter falls back to the English source
  string when blank so an unconfigured station behaves
  exactly as before.  Labels are shipped both in the
  server-rendered HTML (`data-label-no-current` /
  `data-label-no-upcoming` body attrs) and in the JSON
  refresh payload (`labels` key), so an operator's label edit
  surfaces within one cache TTL without a manual iframe
  reload.

  Settings UI: new submenu entry **Widgets → Current
  Show/Track** alongside Player and Weekly Schedule.  The
  page combines a live side-by-side iframe preview, the
  four label inputs, and the ready-made `<iframe>` embed
  code for both widgets with the absolute station URL
  pre-filled.

  Files:
    - `application/controllers/EmbedController.php`
        New `?overflow=` parameter parsing; `emptyLabels`
        view variable populated from `Preference::GetWidget*`
        getters; `labels` block added to the JSON payload.
    - `application/controllers/EmbeddablewidgetsController.php`
        New `currentShowTrackAction` that handles GET (form
        seeding from cc_pref) and POST (label persistence
        via `Preference::SetWidget*`).
    - `application/forms/WidgetCurrentShowTrack.php`
        New Zend_Form with four text inputs (one per
        label).  Allow-empty + placeholder-as-default
        pattern so a cleared field falls back to the
        English source string at render time.
    - `application/models/Preference.php`
        Eight new static methods (`GetWidgetNo*` +
        `SetWidgetNo*`) using the same blank-fallback
        pattern as `GetAutoDjShowName`.
    - `application/views/scripts/embed/now-playing-show.phtml`
    - `application/views/scripts/embed/now-playing-track.phtml`
        Body class now carries both `themeClass` and
        `overflowClass`; new `data-label-no-current` /
        `data-label-no-upcoming` body attrs hold the
        server-rendered labels for the JS-side fallback.
    - `application/views/scripts/embeddablewidgets/current-show-track.phtml`
        New settings page with three fieldsets: live
        preview, four-input label form, embed-code blocks.
    - `application/configs/navigation.php`
        New "Current Show/Track" entry under the existing
        Widgets parent.
    - `public/css/embed/now-playing-widget.css`
        `max-width: 300px` on `.np-widget`; new
        `.np-overflow-marquee` class with a 24 s CSS
        animation; documented kick-off conditions in the
        block comment.
    - `public/js/airtime/embed/now-playing-widget.js`
        Reads labels from data-attrs on boot, then
        refreshes them from each poll's `labels` payload
        so the JS-side no longer carries hard-coded
        English defaults.

  Documentation: `docs/manual/{en,de,fr,es}/WIDGETS.md`
  extended with two new sections (max-width note in §2 +
  empty-state labels in §4), URL-parameter table extended
  with the `overflow` row.  Subsequent section numbers
  shifted by one in all four languages.

### Fixed

- **Now-Playing widgets: 500 Internal Server Error on the two
  iframe widget URLs** (bug reported + fixed 2026-05-22, same
  day as the feature shipped).  Both `/embed/now-playing-show`
  and `/embed/now-playing-track` returned the Zend error page
  while `/embed/now-playing-data` (the shared JSON endpoint)
  worked fine.  Root cause: the shared `_renderNowPlayingWidget`
  helper called `$this->_helper->viewRenderer->setScript(...)`
  to pick the template — but `setScript()` does not exist on
  Zend-1's `Zend_Controller_Action_Helper_ViewRenderer` (the
  correct API is `setScriptAction()`, or simpler: rely on the
  default convention `actionName → action-name.phtml`).  Fix:
  rename the helper to `_prepareNowPlayingView`, drop the
  setScript call, let Zend's default view resolution turn
  `nowPlayingShowAction` into `now-playing-show.phtml` on its
  own.  Plus a secondary polish in `_slimShow` /
  `_slimTrack`: the upstream Schedule model returns a stub
  `{ name: "", starts: null, ends: null }` for "no next show",
  which the template's `?? 'No upcoming show'` fallback failed
  to catch (empty string is not null).  Normalised both
  helpers to return a single null in the empty case so the
  template stays simple.

- **Smart Block: "Exclude tracks played lately" pool count
  was inflated by broken OR-grouping in the WHERE clause**
  (bug reported + fixed 2026-05-22).  When the operator's
  Search Criteria already contained an OR-chain (typical
  case: "Genre is X or Y or Z"), enabling the new
  `Exclude tracks played lately` filter caused the
  `N tracks match your search criteria` counter to *grow*
  instead of shrink — sometimes returning more tracks than
  the unfiltered query.  Root cause: the WHERE string
  `cc_files.lptime IS NULL OR cc_files.lptime < NOW() -
  INTERVAL '24 hours'` was appended to the assembled query
  with `AND` but without an outer set of parens around the
  OR-pair.  SQL operator precedence (AND binds tighter than
  OR) then re-parsed the whole WHERE as `... OR (last_genre
  AND lptime IS NULL) OR (lptime < INTERVAL...)`, which let
  every track with `lptime` older than the window slip back
  in regardless of genre.  Fix: wrap the OR-expression in
  explicit parens so it remains a single conjunctive group.
  Other filters (`only_unplayed`, `only_with_expiry`) are
  single-atom predicates so they were not affected by the
  same precedence trap.

### Fixed

- **Calendar: per-show fill bar auto-refreshes every 60 s.**
  The fill indicator drawn in `eventRender()` reflects
  `cc_show_instances.time_filled` via the `event.percent`
  property delivered by the `Schedule/event-feed` endpoint.
  Pre-2026-05-20 the calendar only refetched events on direct
  user actions (drag/drop, edit, delete) — so an autoplaylist
  that ran 1 h before show start (AutoPlaylistManager's 60 s
  polling job) filled `time_filled` in the DB but the visual
  fill bar stayed at 0 % until the operator manually reloaded
  the page.  Added a single `setInterval(refetchEvents, 60_000)`
  in `full-calendar-functions.js` so the calendar pulls
  fresh events on the same cadence as the auto-build polling.
  The poll is gated on `$cal.is(":visible")` to avoid wasted
  AJAX when the operator is on a different tab.

- **Settings → Streams: "Streaming Server status" no longer
  stuck on "Getting information from the server…".**  The
  `Preference/get-liquidsoap-status` endpoint queries Icecast's
  `status-json.xsl` to determine each output's connected/
  inactive/waiting state.  Two Windows-specific failures were
  combined into a complete silence on the front-end side:
  (1) the configured stream host defaults to `localhost`, and
      Windows' resolver returns the IPv6 `::1` for that name
      before the IPv4 `127.0.0.1`; Icecast on this fork binds
      to IPv4 only, so every status check sat through the full
      2 s socket timeout before falling back.
  (2) the timeout produced an `E_WARNING` from
      `file_get_contents`, which the global error handler
      promotes into an `ErrorException` — and `@` does NOT
      suppress error-handler-mediated exceptions.  The whole
      action then HTTP 500'd and the JS poll silently
      discarded the response, leaving the page on its
      initial "Getting information…" placeholder forever.
  Fix in `PreferenceController::getLiquidsoapStatusAction()`:
  rewrite `localhost` → `127.0.0.1` when building the
  Icecast status URL (forces IPv4 directly, no resolver
  round-trip), and wrap the `file_get_contents` call in
  `try { … } catch (Throwable)` so any future transient
  hiccup degrades to status `waiting` instead of nuking the
  whole JSON response.  No schema change.

- **Embed Player widget: mobile-flag categorisation no longer
  broken.**  The `/embed/player?stream=auto` endpoint built the
  available-stream list straight from `cc_pref`.  The `mobile`
  flag is stored as the literal string `"false"` (not boolean
  false) because the cc_pref persistence layer serialises
  everything as strings, and `"false"` is truthy in PHP — so
  the `if ($s['mobile']) { mobile-queue } else { desktop-queue }`
  branch silently routed every stream into the mobile queue and
  left the desktop player with nothing to play.  Fix in
  `EmbedController::playerAction()`: normalise the flag to a real
  boolean with explicit string comparison
  (`$m === true || $m === 'true' || $m === '1' || $m === 1`).
  Note: stream URL itself is **not** rewritten — operators are
  expected to configure a publicly-reachable host in
  Settings → Streams (Icecast `host` field) for LAN / external
  embedding.  A first version of this fix auto-rewrote
  `localhost` / `127.0.0.1` in the URL to the request host name,
  but that was reverted on operator request — settings should be
  the single source of truth.

- **Settings → Show Templates: left sidebar sub-navigation no
  longer collapses.**  Every other Settings page assigns
  `parent_page = 'Settings'` to the Zend layout (the layout
  uses that key to keep the General / My Profile / Users /
  Track Types / Show Templates / Streams / Local Machine /
  Status sub-nav visible).  The
  `PreferenceController::showTemplatesAction` shipped without
  that assignment when the Show-Templates page landed in
  Section 23.16, so opening it collapsed the sub-nav and the
  operator had to click the parent Settings entry again to
  navigate away.  One-line fix.

- **Autoloading Playlist: margin capped at 5 s, post-outro
  cleanup pass added** (Section 23.19 v8, 2026-05-20).
  Operator policy clarification:
    * margin ≤ 5 s (any "silence" tail visible to listeners
      must stay small),
    * over-fill must be avoided,
    * if measured-vs-real outro divergence pushes the show
      beyond the slot anyway, trim autoplaylist tail tracks
      (not the outro!) until the overbook is gone.
  Implementation:
    * The safety margin reverts from 10 s (v7) to 5 s.
    * Before the real outro insert,
      `MAX(cc_schedule.id)` for the instance is snapshotted.
    * After the insert, the new helper
      `ShowInstance::trimTailExcept($excludeAboveId, $reserve)`
      runs and trims schedule rows with `id <= snapshot`
      (= autoplaylist tail) until `getSecondsRemaining() >= 0`.
      The outro rows are protected by the id filter.
    * Skipped in the "outro > slot" edge case (operator
      explicitly wants overbook in that branch).
  Result: in the worst case where the smart-block-pick divergence
  exceeds the 5 s margin, the autoplaylist becomes a bit shorter
  than ideal but the show never overbooks.

- **Autoloading Playlist: 5 s safety margin bumped to 10 s
  on the outro reserve** (Section 23.19 v7, 2026-05-20).
  *Reverted in v8 — operator policy capped margin at 5 s and
  introduced a post-outro cleanup pass instead.*
  v6 used 5 s but the Auto+Outro variant (no intro)
  still showed a 4 s overbook in operator testing — the
  trial-measured outro length and the real outro length
  diverged enough (smart-block random pick) that 5 s was not
  always enough.

- **Autoloading Playlist: 5 s safety margin on the outro
  reserve** (Section 23.19 v6, 2026-05-20).  Operator testing
  on the "Time remaining in show" autoplaylist smart-block
  variant flagged a consistent 4 s overbook: the SSP-best-fit
  picker in `Block::getListOfFilesUnderLimit()` maximises the
  subset sum against the strict ≤ target, but the Scheduler's
  later crossfade pass adjusts the actual schedule timestamps
  by a few hundred milliseconds per transition, and those
  shifts do not line up exactly with what the SSP saw.  Result:
  an autoplaylist sized to fit (slot − measured_outro) lands a
  few seconds over the slot boundary, pushing the outro into
  overbook territory.  v6 adds a defensive 5 s cushion on top
  of the measured outro length when computing the reserve.
  Sacrifices at most ~5 s of slot fill but eliminates the
  overbook the operator flagged as unacceptable (under-fill ≤ 5 s
  is OK; over-fill is not).  This does not touch the
  fixed-time-limit Smart Block path — those blocks ignore the
  reserve and run against their own time limit, so a slot with
  a 9 min Fixed-Time-Limit autoplaylist and a 10 min slot will
  always have ~60 s of unscheduled tail.  Operators who want
  the whole slot filled should configure their autoplaylist
  smart block as "Limit to: Time remaining in show".

- **Autoloading Playlist: trial-insert no longer poisons
  `cc_files.is_scheduled`, outro is no longer skipped on the
  edge case** (Section 23.19 v5, 2026-05-20).  Two follow-up
  problems shipped together with the v4 trial-insert
  measurement:
  (1) `Scheduler::insertAfter()` flips
      `cc_files.is_scheduled = TRUE` for every file it adds to
      `cc_schedule`, and the DELETE on roll-back does NOT walk
      that flag back.  After the trial pass the outro's track
      pool was marked "already scheduled".  Subsequent smart-
      block expansions reading the flag would see a poisoned
      pool — empirically the autoplaylist kept picking the same
      tiny subset across all tests because everything else was
      flagged.  v5 snapshots
      `SELECT id FROM cc_files WHERE is_scheduled = TRUE` *after*
      the intro insert (so intro tracks are in the snapshot and
      are not reset), runs the trial, then resets the flag for
      any cc_files row that is TRUE *and* not in the snapshot,
      *before* deleting the trial schedule rows (order matters:
      drop the flag before removing the row that justifies it).
  (2) The v2/v3/v4 edge-case branch *skipped* the outro
      entirely when its length was greater than the show slot —
      so a too-long outro turned into a fully-filled autoplaylist
      and an empty 30 s tail.  Operator policy revised
      2026-05-20: "Es ist besser, die Show ist überfüllt, als
      zu wenig befüllt".  The outro is now always inserted; the
      edge-case branch only zeroes the reserve so the autoplaylist
      fills the entire slot, and the outro overbooks on top.
  Plus a one-off DB heal recomputed `cc_files.is_scheduled` from
  the actual `cc_schedule` rows to clean up the poisoning that
  v4 had already inflicted on the test installation (67 rows
  fixed; should be a no-op on a fresh database).

- **Autoloading Playlist: outro length is now measured by a
  trial-insert + roll-back** (Section 23.19 v4, 2026-05-20).
  Reading `cc_playlist.length` directly (v1–v3) works only for
  static playlists.  Any playlist that contains a smart block
  reports `length = 00:00:00` because Propel does not aggregate
  the smart-block contribution into the parent playlist's length
  column — empirically verified on the operator's 8
  "Tagesplaylist <Genre> Outro" playlists, all of which carry
  one smart block and all of which had `length = 0:00:00`.  With
  length=0 the previous reserve was 0 and the trim was a no-op,
  so the outro continued to overbook the slot.  The new approach
  inserts the outro temporarily *after* the intro, reads the
  before/after delta of `cc_show_instances.time_filled` to get the
  *actual* smart-block-expanded outro duration, then deletes the
  trial rows by `id > max_id_before` and re-aggregates time_filled
  via a new public helper `ShowInstance::refreshScheduleStatus()`.
  The measured length then feeds both the in-Scheduler reserve
  (layer 3) for time-remaining smart blocks in the autoplaylist
  and the post-loop tail trim (layer 4) for static playlists /
  fixed-time-limit smart blocks.  Approximation note: a dynamic
  smart block in the outro may pick a different track set on the
  second (real) insert than on the trial pass; the variance is
  bounded by the smart block's own length limit and any residual
  overflow is caught by `trimOverbooked` later.

- **Autoloading Playlist: outro silently overbooked the show when
  Intro + Auto + Outro were all configured** (Section 23.19).
  The upstream `AutoPlaylistManager::buildAutoPlaylist()` filled the
  entire remaining slot with the autoplaylist (including any
  time-remaining smart blocks expanded against
  `getSecondsRemaining()`) and only then appended the outro — which
  therefore spilled past the show's end time.  The upstream
  comment in the code even acknowledged it: *"it will always
  overbook shows that have repeat until full enabled"*.  With only
  Intro + Auto the bug was invisible because the loop terminated
  at the ">100 %" check before the entire slot was full.  Fix:
  pre-compute the outro length from `cc_playlist.length` *before*
  the auto-loop (via a direct `CcPlaylistQuery::findPK` Propel
  call — `Application_Model_Playlist` has no public `getDbLength()`
  wrapper, calling it raised a fatal `Error: Call to undefined
  method` and left every Intro+Auto+Outro show empty for an hour of
  polling — fixed before ship), then (a) terminate the auto-loop
  as soon as the unscheduled tail is ≤ the outro length, and (b)
  pass the outro length as a new `reservedSecs` reserve to
  `ShowInstance::addPlaylistToShow($pl_id, $checkPerm, $reservedSecs)`
  so that any time-remaining smart block inside the autoplaylist
  is sized against `(slot − outro)` instead of the full slot.  New
  scheduler-side setter `Application_Model_Scheduler::setReservedSeconds($n)`
  subtracts the reserve in `retrieveMediaFiles()` when computing
  the per-call smart-block limit.  Edge case (operator-revised
  2026-05-20): outro length ≥ show slot → **outro is skipped**, the
  autoplaylist still fills the slot (auto > outro priority).  The
  skip is logged at `WARN` level so the operator can find the
  misconfiguration in `legacy.log`.  Throwable-level catch around
  the outro-length read so any future `Error` here cannot empty
  every upcoming show again.

  Smart-block-reserve alone is not enough for two upstream
  expansion paths that ignore the scheduler's `$showLimit`:
  static playlists (every track inserted at full length, no trim)
  and fixed-duration smart blocks (honour their own
  `cc_block.length`, not `$showLimit`).  Both produce a slot that
  is filled (or overbooked) before the outro is inserted.  New
  helper `ShowInstance::trimTailToReserve($reservedSecs)` deletes
  tail items (filter `starts > NOW() AT TIME ZONE 'UTC'` so an
  already-playing track is never touched) until the required
  reserve is free; the auto-loop calls it once before the outro
  insertion.  An earlier draft of the helper used
  `playout_status = 0` as the safety filter — that is the
  "overbooked" marker set by `CcShowInstances::updateScheduleStatus()`
  *after* the schedule pass, and in-slot future tracks have
  `playout_status = 1`, so the original filter matched zero rows
  and silently trimmed nothing in every realistic Intro+Auto+Outro
  test.  The `starts > NOW()` formulation is intent-based
  (don't touch the past) instead of relying on an enum that means
  something different than the helper's safety goal.  This makes the outro fit
  even for static playlists and fixed-time-limit smart blocks at
  the cost of trimming whole tail tracks of the autoplaylist —
  acceptable trade-off because tracks cannot be cut mid-stream
  and the autoplaylist length is operator-chosen, so a slightly
  shorter autoplaylist is a better outcome than an out-of-slot
  outro.

  No schema change.  Affects only the auto-build-1h-before-show
  path; the manual Show-Builder add-from-Library workflow already
  worked because it inserts items one-at-a-time and never tries
  to "fill" a slot.

- **Show-Logo upload silently failed on Windows.**  Selecting a
  logo in Calendar → New/Edit Show → Style and saving completed
  *without* error in the browser but the file was never written to
  `<storage>/imported/<owner-id>/show-images/<show-id>/` and
  `cc_show.image_path` stayed NULL — no DB row in the entire
  installation ever had a logo since RASTATIME setup.  Root cause:
  `ShowImageController::copyFileToStor()` built the destination
  filename via
  `substr($tempFilePath, strrpos($tempFilePath, '/'))` which
  assumes a POSIX upload tempfile like `/tmp/phpXYZ.tmp`.  On
  Windows the upload tempfile path uses backslashes (e.g.
  `C:\Temp\Python\phpD254.tmp`), so `strrpos('/')` returns `false`,
  `substr(s, false)` is coerced to `substr(s, 0)` and returns the
  *entire* path — the resulting "newFileName" embedded a drive
  letter and `@rename()` failed silently.  Replaced with
  `basename($tempFilePath)`, which handles both separators on every
  platform.  No schema change.

- **Dashboard: drag-and-drop from Library into the Playlist /
  Smart-Block editor tabs was silently broken** (only the
  double-click "Add" path worked).  Root cause was in
  `library_showbuilder.js::fnDrawCallback`: it chose
  `connectToSortable` as *either* `#show_builder_table` (Scheduled
  Shows timeline) *or* `.active-tab .spl_sortable` (Playlist /
  Block editor) with an if-else, but in the Dashboard
  (`showbuilder/index.phtml`) `#show_builder_table` is always
  present in the DOM as the initial "Scheduled Shows" tab — so the
  if-branch always won and the Playlist editor was never
  registered as a drop target.  Double-click still worked because
  it bypasses the sortable receive-handler and calls
  `AIRTIME.playlist.fnAddItems()` directly.  Fix: pass both
  selectors as a single comma-separated string to
  `connectToSortable`; jQuery UI resolves each independently and
  delegates the drop to whichever container is the actual visible
  target.  Affects all Library item types (Track, Smart Block,
  Webstream, Line-Input).

### Changed

- **Podcasts → Edit Podcast: Auto-Expiry helper text moved into
  a hover tooltip** (operator request 2026-05-21).  The grey
  inline span next to the days input field
  (`"Episodes expire this many days after download."`) was
  visually noisy and pushed the row width to the right.  Replaced
  with a `?` help-icon at the same position; the same wording
  surfaces as a qtip on hover.  Same hover convention as
  `.album_names.help_icon` already used inside the podcast edit
  dialog, so the visual style stays uniform.  Pure UX change —
  the underlying `auto_expiry_days` semantics are unchanged.
  Files: `application/views/scripts/podcast/podcast.phtml`,
  `public/js/airtime/library/podcast.js`.

- **Calendar New/Edit Show: minor label polishing**
  (operator request 2026-05-19).
  * Templates section: "Save as Template" button moved onto its
    own row below the Load-Template dropdown row for breathing
    room (`margin-bottom: 0.8em` between the two rows).
  * Record section: `Record this show` → `Record this show:`
    (trailing colon for consistency with the other "Name:" /
    "Description:" / "Default Length:" labels).
  * Autoloading Playlist section: `Add Autoloading Playlist ?` →
    `Add Autoloading Playlist?` (removed stray space before `?`).
  * Live Stream Input section: `Use LibreTime Authentication:` →
    `Use RASTATIME Authentication:`.  Hard-coded brand string in
    `AddShowLiveStream` only; the global `PRODUCT_NAME` constant
    stays "LibreTime" per the upstream-sync-tracking comment in
    `constants.php` (2026-05-16) so all other PRODUCT_NAME
    consumers (Powered-by footer, Help/About pages, file-not-
    found API errors, …) are unaffected.  Element id
    `cb_airtime_auth` is unchanged so JS selectors, template_data
    JSON keys and Icecast source-config remain compatible.

- **Calendar New/Edit Show: Templates promoted to a proper
  collapsible section.**  The Template "Load Template" dropdown,
  "Load" button (was "Apply") and "Save as Template" button used to
  live in a raw `<div>` above the "What" section; they're now
  enclosed in a standard `Templates` collapsible section that
  matches the visual pattern of every other section in the dialog
  (What, When, Record, Autoloading Playlist, Live Stream Input,
  Who, Style).  Default state is **collapsed**, in line with the
  other "advanced" sections, so the operator's eye is drawn to the
  required fields (What / When) on open and Templates is reachable
  with one click when needed.  No functional change beyond the
  Apply → Load button rename.
- **Calendar New/Edit Show: Record section is now default-
  collapsed.**  The Record section used to come up expanded
  because of a stale selector in `openAddShowForm()`: the
  legacy hide-list referenced `#schedule-record-rebroadcast`,
  which no longer exists at the top level since the
  record-per-show refactor (Section 23.13) renamed the section
  to `#schedule-show-record`.  Added the correct id to the
  initial-hide list while leaving the legacy selector in place
  as a harmless no-op.  Operator request 2026-05-19.

- **Webstream "Default Length" now accepts seconds** (Section 23.17).
  The Webstream edit dialog's Default-Length field previously
  validated only `HH+MM` (e.g. `01h 05m`) and silently dropped any
  sub-minute precision.  It now also accepts an optional seconds
  component (e.g. `01h 05m 05s`), matching the granularity of the
  Line-Input dialog so an operator preparing a short, time-critical
  stream entry no longer has to round to whole minutes.  Backwards-
  compatible (`01h 05m` without the seconds suffix is still valid by
  operator decision 2026-05-19).  The Edit-dialog readback always
  shows all three components, including zero seconds, for visual
  consistency (operator decision 2026-05-19).  The Library list shows
  the same `HHh MMm SSs` formatting because `LengthFormatter`
  pass-through preserves the Webstream-specific string unchanged.
  Scope: `Application_Model_Webstream` only — Line-Input and Smart
  Block were already seconds-aware; consolidating the three
  independent parsers into a shared helper was deferred (operator
  decision 2026-05-19, "nur Webstream anfassen").
  DB: `cc_webstream.length` is a Postgres `interval` so it already
  carries seconds at the storage layer — no migration needed; pre-
  2026-05-19 rows come back as `HH:MM:00` from the driver and
  validate as `00s` in the Edit dialog.

### Fixed

- **Auto DJ: shortening an auto-created show failed with
  "Cannot schedule overlapping shows", End-Time displayed one
  minute too early** (Section 23.20 v6, 2026-05-21).  Both
  symptoms shared one root cause: the gap returned by
  `findNextGap()` carries sub-minute timestamps (the preceding
  Operator show often ends at `:34` or similar due to
  crossfade-rounding), so the auto-created show inherited
  sub-minute `starts` / `ends` / `start_time` / `duration`
  values.  The Edit-Show form works at minute granularity and
  could not round-trip those values cleanly — End-Time
  rendered one minute short of the real end (16:59 for a
  17:00:00 ends), and `AddShowWhen`'s overlap-check refused
  to save a shortened version of the show because the form's
  recomputed end timestamp shifted relative to the original
  `cc_show_instances` row.  Fix in
  `AutoDjService::createGapFillingShow()`: round the gap
  start UP to the next whole minute (never earlier than the
  gap start, protects the preceding show) and round the gap
  end DOWN to the previous whole minute (never later than the
  gap end, protects the following show).  Shows now have
  whole-minute starts / ends / durations and survive the
  Edit-Show round-trip.  Forfeits at most ~59 s at each end
  of a gap.  If the rounded gap drops below the 60 s minimum
  the show is skipped.

- **Auto DJ: Edit-Show dialog showed wrong start/end time for
  auto-created shows** (Section 23.20 v5, 2026-05-21).  v3/v4
  wrote `cc_show_days.start_time` and `.timezone` as UTC,
  which made the calendar render correctly (because
  `cc_show_instances.starts` is the authoritative UTC
  timestamp and the calendar converts that to local) but the
  Edit-Show dialog reads the operator-local representation
  from `cc_show_days` directly — on a UTC+2 system an
  Auto-DJ show created for 15:08 local was displayed as 13:08
  in Edit-Show (and 14:59 as End Time for the 17:00 end).
  Fix: convert the UTC gap-start to the operator's
  `Application_Model_Preference::GetDefaultTimezone()` and
  store both `start_time` and `timezone` in that zone, the
  same convention `ShowService::setCcShowDays()` uses.  The
  `cc_show_instances.starts/ends` columns keep storing UTC.
  No schema change; only auto-created shows are affected.

- **Auto DJ chopped long gaps into a chain of 1–4 min sub-shows**
  (Section 23.20 v4, 2026-05-21).  `findNextGap()` bounded its
  Postgres query by `starts < lookahead_end` (= `NOW() + 1h`),
  which silently broke any gap whose follow-on show started
  beyond the lookahead window.  Example from operator's log:
  poll at 13:31:51 saw the 14:07–15:00 gap (53 min) but did
  NOT see the 15:00 show that bounds it (outside lookahead),
  so the cursor walked to `lookahead_end` (14:31:51) and the
  tail-gap branch returned a 25-min gap.  60 s later the next
  poll saw the rest (14:31:51–14:32:51) and created a 1-min
  show, and so on for 17 polls.  Fixed by widening the query
  to ALL upcoming instances (with a 200-row safety LIMIT) so
  the cursor sees the real next-show boundary, while still
  enforcing the operator-Q1 "only auto-create a show whose
  gap STARTS inside the lookahead window" rule.  The 12 h
  show-length cap in `createGapFillingShow()` still applies
  for the (mostly theoretical) "empty for a whole day" case.

- **Auto DJ Settings: Logo preview rendered as an `<img>`
  instead of a raw filesystem path.**  Previous version
  displayed the absolute server path in a `<code>` block; the
  browser cannot fetch absolute server paths so the operator
  had no visual confirmation that the upload actually
  produced a usable image.  Now the controller reads the
  configured logo file via `file_get_contents()` + base64,
  packages it as a `data:` URI and the view renders it as an
  `<img>` (max 200×200 px) — same pattern as
  `ShowFormService::imagePathToDataUri()` already uses for
  per-show logos.

- **Auto DJ pre-pass still failed after v2 — rewritten to direct
  Propel insertion** (Section 23.20 v3, 2026-05-21).  v2 swapped
  the auth storage to `Zend_Auth_Storage_NonPersistent` to dodge
  the session-write strict-mode guard, but
  `ShowService::addUpdateShow()` touches *additional* session-
  backed state internally (RabbitMQ helpers, intro/outro
  lookups, UserService construction) that ALSO trips the guard
  from a polling-job context — every poll continued to log
  `"You must explicitly start the session with Zend_Session::start()"`
  and no gap-filling show was ever created.  v3 abandons the
  ShowService path entirely and writes the three required rows
  (`cc_show` + `cc_show_days` + `cc_show_instances`) via Propel
  setters in a single transaction.  These are the only rows
  AutoPlaylistManager's `_upcomingAutoPlaylistShows()` query and
  the calendar event-feed need to find the show; no hosts, no
  rebroadcasts, no linked-show machinery — Auto-DJ shows stay
  intentionally bare.  Removed the `withAdminContext()` helper
  along with the unused ShowService dependency.  No schema
  change.

- **Auto DJ pre-pass crashed on every poll with "must explicitly
  start the session with Zend_Session::start()"** (Section 23.20
  v2, 2026-05-21).  v1 of `AutoDjService::withAdminContext()`
  swapped the Zend_Auth identity by writing into the *current*
  session storage adapter (`$auth->getStorage()->write($info)`).
  The polling-job context (PageLayoutInitPlugin) had read the
  session but not opened it for writing, so the write attempt
  hit Zend's strict-mode session guard and threw on every
  60 s poll — gap-filling shows were never actually created.
  v2 swaps the *storage adapter itself* for a
  `Zend_Auth_Storage_NonPersistent` (in-memory only) and
  restores the original adapter on exit (incl. via `finally`).
  No session is touched and the admin identity exists only for
  the duration of the show-create call — invisible to every
  other concurrent request.

### Added

- **Auto DJ Settings: "Show Logo" help-icon tooltip.**
  Added a `.help_icon` tooltip next to the "Show Logo" label
  carrying "Upload a JPG / PNG / GIF (max 2 MB)." — same
  pattern as the "Default Playlist" tooltip introduced in v3.

- **Auto DJ Settings UI polish** (Section 23.20 v4,
  2026-05-21).  Cumulative cosmetic pass after operator
  testing:
  * Tooltip-icon class unified to `.help_icon` (the same PNG
    "ⓘ" glyph used by `stream_username_help_icon` in
    Settings → Streams), no more inline unicode character.
  * Tooltip on "Default Playlist" carries both the short
    "what's this for" sentence and the longer "use a Smart
    Block with Limit to: Time remaining in show" tip — the
    tip used to be a paragraph under the dropdown but the
    hover surface is cleaner.
  * Colour-input labels trimmed to "Background Color" /
    "Text Color" (was "… (6-digit hex, without #)").
  * "No default logo set …" sentence moved below the Upload
    button so the upload-flow is the first thing the
    operator sees when the field is empty.
  * Button labels shortened to "Upload" / "Save".

- **Auto DJ Settings UI tweaks** (Section 23.20 v3,
  2026-05-21).  "Default Playlist" now appears as the first
  field inside "Auto DJ Show Defaults" (previously buried
  between the colour pickers and the fill-checkbox).  Long
  in-line label "Default Playlist (used as autoplaylist for
  created shows)" trimmed to just "Default Playlist" with a
  small ⓘ icon next to it — hovering opens a qtip tooltip
  with the longer explanation, same pattern as the
  `show_record_help_icon` in the Calendar's New-Show dialog.

- **Auto DJ: extended show-detail defaults** (Section 23.20 v2,
  2026-05-21).  Five additional cc_pref keys plus matching
  Settings → Auto DJ form fields so the operator can pre-stamp
  every auto-created show with URL, Genre, Description,
  Background Color and Text Color.  The values are passed
  straight through to `ShowService::setCcShow` and end up on
  the new cc_show row.  Empty defaults are safe — Propel just
  stores them as NULL/empty.  Form section renamed from
  "Defaults" to "Auto DJ Show Defaults", "State" to "Status",
  "Default Auto DJ Show Name" to "Show Name", and the
  Show-Logo upload moved from its own section into the
  Auto-DJ-Show-Defaults section as the final field.

- **Auto DJ** (Section 23.20).  New Settings → Auto DJ page plus
  a service that auto-creates and auto-fills shows in calendar
  gaps.  Operator workflow:
  1. Configure under Settings → Auto DJ:
     * **Enabled** (master switch)
     * **Default Auto DJ Show Name** (e.g. "Auto DJ")
     * **Default Playlist** (any cc_playlist; recommended: a
       playlist that wraps a smart block with
       "Limit to: Time remaining in show" so the slot fills
       exactly — same trick that powers Section 23.19)
     * **Automatically fill any show** (also tops up shows that
       end up incomplete after the per-show autoplaylist build)
     * **Default Auto DJ Show Logo** (uploads to
       `<storage>/imported/<owner>/auto-dj-logos/`)
  2. Every 60 s — same cadence as `AutoPlaylistManager` — the
     pre-pass scans the next hour of the calendar for the first
     unscheduled gap ≥ 60 s and auto-creates a single
     non-repeating show inside it, capped at 12 h length.  The
     new show has `has_autoplaylist = true` so the existing
     autoplaylist build loop in the same poll cycle picks it up
     and fills the slot.
  3. After the build loop, the fill-pass walks the next hour of
     upcoming instances; any whose unscheduled tail is more than
     5 s gets a final `addPlaylistToShow($auto_dj_playlist)`
     pass.

  Architecture notes:
  * No schema change.  Five new keys in `cc_pref`
    (auto_dj_enabled, auto_dj_show_name, auto_dj_playlist_id,
    auto_dj_fill_any_show, auto_dj_logo_path).
  * New `Application_Service_AutoDjService` is the central
    place.  Two public entry points (`runPrePass`, `runFillPass`)
    are called from
    `AutoPlaylistManager::buildAutoPlaylist()` — bookending
    the existing per-show build loop.
  * Programmatic show creation goes through
    `Application_Service_ShowService::addUpdateShow()` under
    `Zend_Auth` admin-context swap (via
    `Application_Model_User::getFirstAdmin()`) because that
    service hard-rejects non-Admin/PM callers.
  * Show defaults: no recording, no rebroadcast, no host, no
    intro/outro override, no linking — strictly minimal filler
    shows.
  * Logo upload re-uses the show-image MIME validation pattern
    (JPG/PNG/GIF, 2 MB client-side limit) but persists a single
    global path rather than per-show.

- **Line-In entries in Playlists** (Section 23.18, migration 0054).
  Operators can now drop a Line-In item from the Library into a
  Playlist editor (Doppelklick or drag-and-drop), the same way
  Tracks, Smart Blocks and Webstreams already worked.  When the
  Playlist is later scheduled into a Show, the Line-In slot becomes
  a live-source switch on the playout side — same end-result as if
  the operator had scheduled the Line-In directly into a Show
  (which was the only path before).
  * Migration 0054 adds `cc_playlistcontents.linein_id INTEGER`
    (no hard FK to `rastatime_linein` — Django/Propel ownership
    boundary, same call as `cc_schedule.linein_id` in migration
    0047).
  * New `cc_playlistcontents.type = 3` discriminator (was 0=file,
    1=stream, 2=block before).  Watch out: the SCHEDULE-side type
    enum is different (file=0, stream=1, linein=2); the Scheduler
    maps playlist-type 3 → schedule-type 2.
  * `Playlist::buildEntry()` gains a `linein` branch that fetches
    `rastatime_linein` via raw SQL (Propel skip-regen pattern, same
    as Webstream `input_gain_db`).  Default slot length 30 min when
    the Library record left `length` NULL.
  * `Playlist::insertPlaylistElement()` saves the row via Propel for
    the common fields, then writes `linein_id` via a follow-up raw
    SQL UPDATE (the Propel `CcPlaylistcontents` model was not
    regenerated for the new column).
  * `Playlist::getContents()` gains a fourth `UNION ALL` arm
    joining `rastatime_linein` so the Playlist editor sees Line-In
    rows alongside files / streams / blocks.
  * `Scheduler::scheduleItemsInPlaylistBranch` (the `type === 'playlist'`
    branch) gains a `type == 3` mapping that produces a schedule
    row with `type = 2` (linein) and zero-length fades — fades on a
    live mic source make no sense.
  * `update.phtml` renders the Line-In row with a disabled signal
    icon (no browser preview is possible for a server-local
    hardware input).
  * Doppelklick + DnD already worked because the Library already
    classified `ftype === "linein"` as `lib-stream` (same CSS class
    as Webstream) and the Library toolbar / DnD glue does not
    filter by item type.  The only thing that was blocking the
    flow was the server side throwing "Unknown file type" in
    `Playlist::buildEntry()` — that's now handled.

- **Show Templates.**  New feature for reusing show configurations
  across the Calendar's New-Show dialog and a Settings page.
  Operator workflow:
  1. Fill in a show's fields in the **New Show** dialog (name, URL,
     genre, description, duration, repeats, days, end date, record
     flag, autoloading playlist trio, auth flags, host list, BG /
     text colour, logo path).
  2. Click "Save as Template" — the show name becomes the template
     name (with overwrite-confirmation if the name already exists).
  3. Next time a New Show is opened, pick the template from the
     "Load Template" dropdown and click "Apply" — every captured
     field is populated.  Start date / start time are deliberately
     left alone so a click into the calendar still wins.
  4. The Settings → "Show Templates" page lists every template
     and allows rename / delete.

  Architecture & decisions (Section 23.16):
  * New table `cc_show_template` (migration 0053) with
    `template_data JSONB` snapshot.
  * Templates are **station-wide** (no per-user filter).
  * One-way stamp model: editing a template does NOT propagate to
    existing shows; templates are just blueprints.
  * `cb_custom_auth` live-stream password is **explicitly excluded**
    from the template payload (security).
  * Hosts are stored as `cc_subjs.login` strings, not as surrogate
    IDs, so a template survives the deletion-and-recreation of a
    user; missing logins at apply-time are silently skipped with
    an `INFO`-level log.
  * Show logo is stored as a path reference to the existing file
    in `cc_files`; if the source image is later deleted the
    template loses its image (operator's explicit choice 2026-05-19
    to keep storage flat).
  * Schema drift on `cc_show`: missing fields in older templates
    fall back to the show-form defaults at apply time; superfluous
    fields are silently ignored.  Operator-confirmed strategy
    "use defaults, manually refresh templates if needed".
  * Five new JSON actions on `ScheduleController`: list / get /
    save / rename / delete; the New-Show dialog and the Settings
    page share the same backend.
  * UI is rendered in **New-Show and Edit-Show** dialogs (operator
    follow-up 2026-05-19); deliberately omitted from the
    **Edit-Instance** dialog because a single repeating-show
    instance is a per-occurrence override and re-stamping it with a
    template would either silently propagate to the linked siblings
    or have no visible effect on them — both confusing.  In
    Edit-Show, Apply re-stamps the in-flight form values from the
    chosen template but does NOT auto-submit — the operator still
    has to click "Update show".  `start_date` / `start_time` are
    still skipped (one-way stamp model — Apply must never silently
    reschedule an existing show).

### Fixed

- **Show Templates: Apply inverted the "Repeats?" checkbox.**
  jQuery 1.8.3's default-action simulation for click events on form
  controls toggles the native checked state of a checkbox *after* the
  user handlers run.  The earlier `setCheck()` did
  `$el.prop("checked", on).trigger("click")` which (1) set the desired
  value, then (2) ran the existing click handler (which toggled the
  visibility fieldset correctly), then (3) the default-action
  simulation flipped the checkbox state back — leaving the box
  un-checked but the repeat-options fieldset visible.  Replaced the
  trigger-based approach with a single `prop("checked", on)` per
  field plus a new `syncDependentVisibility(form)` pass at the end of
  `applyShowTemplate()` that recomputes all toggle-driven UI sections
  (Repeats, Record/Rebroadcast, Autoplaylist, Custom auth, End-date,
  Repeat-type → day-picker / monthly-picker).
- **Show Templates: Linked-show state was sometimes lost after Apply.**
  Symptom of the same `.trigger("click")` problem above (linked was
  also a setCheck), plus an ordering issue: `add_show_record` was set
  *after* `add_show_linked`, and Record's click handler force-clears
  + disables Linked as a domain rule (a recorded show cannot be
  linked).  Both fixed in the single sync pass at the end of
  `applyShowTemplate()`, which evaluates the post-write Record state
  exactly once.
- **Show Templates: Add-this-Show stopped working after Save-as-
  Template.**  The two template-control buttons live inside
  `<form id="add-show-form">`; their click handlers did not stop
  propagation, so the click bubbled into the form and (depending on
  browser timing) left the form in a state where the subsequent
  Add-this-Show / Update-show click was discarded.  Added explicit
  `event.preventDefault() + event.stopPropagation() + return false`
  to both `#show-template-apply` and `#show-template-save` click
  handlers, and pinned the Save-as-Template payload to
  `$("#add-show-form").serializeArray()` instead of the broader
  `$("form")` selector that could pick up sibling forms on the page.

- **Smart Blocks: "Allow only tracks with expiry date" checkbox.**
  New entry in the Smart Block edit dialog's Advanced Options,
  directly under "Allow only tracks not played yet".  Adds a
  `WHERE cc_files.expires_at IS NOT NULL` filter to the candidate
  pool, restricting the block to perishable content (dated news
  segments, time-limited trailers, podcast episodes with auto-
  expiry).  Pairs naturally with the new "Earliest expiry first"
  sort: enable both for a block that always airs the most-urgent
  short-lived content first.  Persisted as a single
  `cc_block_criteria` row with `criteria='only_with_expiry'`
  (`value='0'/'1'`) — same pattern as `only_unplayed`.  Default off;
  backwards-compatible (missing row treated as off).
- **Smart Blocks: shortened "Allow only tracks not played yet"
  label** (was "Allow only selecting tracks not played yet") to
  match the new sibling checkbox's pattern and reduce visual noise
  in the Advanced Options panel.

- **Smart Blocks: "Earliest expiry first" sort option.**  New entry
  in the Smart Block edit dialog's Advanced Options → Sort Tracks
  dropdown, alongside "Randomly", "Newest", "Oldest", "Most
  recently played" and "Least recently played".  Sorts the
  candidate-pool query by `cc_files.expires_at ASC NULLS LAST`:
  tracks with the closest expiry date are picked first so the
  Smart Block airs them before the hourly pruner auto-disables
  them; tracks without an expiry go to the end of the queue so
  they do not dilute the air-before-expiry intent.  `filepath` is
  used as a stable secondary sort key for tracks sharing the same
  expiry second (e.g. a batch of episodes auto-expired by the same
  podcast setting).  Pairs naturally with the existing Track-Expiry
  / Podcast Auto-Expiry feature (ARCHITECTURE 23.11).

- **Smart Blocks: "Allow only selecting tracks not played yet"
  checkbox.**  New entry in the Smart Block edit dialog's "Advanced
  options" section (between "Allow last track to exceed time limit"
  and "Sort Tracks").  When enabled, the SQL projection in
  `Block::getListofFilesMeetCriteria()` adds a
  `WHERE cc_files.lptime IS NULL` filter, restricting the candidate
  pool to tracks the playout has never logged.  Useful for
  discovery / new-content-rotation blocks.  Persisted as a single
  `cc_block_criteria` row with `criteria='only_unplayed'`,
  `value='0'/'1'` — same pattern as the existing `repeat_tracks` and
  `overflow_tracks` toggles.  Default off; backwards-compatible with
  existing blocks (missing row treated as off).

- **Per-podcast default Track-Type.**  New dropdown "Track Type:" in
  the New / Edit Podcast dialog.  When set, every episode imported
  from that podcast (manual download or auto-ingest) gets
  `cc_files.track_type_id` pre-filled with the chosen value at
  download time, independent of the analyzer's ID3-based inference.
  Empty = no override (existing behaviour).  Existing already-imported
  episodes are not retroactively changed.
  Implementation pattern mirrors the Auto-Expiry feature
  (migration 0049 / 2026-05-16):
  * New column `imported_podcast.default_track_type_id` (FK to
    `cc_track_types.id`) via migration 0050.
  * Python model + `download_episode()` get the optional kwarg.
  * PHP `PodcastService` reads/writes the column via raw SQL
    (Propel regen not yet pulled).
  * Frontend `podcast.phtml` renders the dropdown options from the
    `podcast.track_type_options` field that
    `PodcastService::getPodcastById` now embeds directly into the
    podcast JSON payload — `Application_Model_Tracktype::getTracktypes()`
    is queried server-side once per editor open, no extra REST
    round-trip and no fragile `<script>` tag inside server-rendered
    HTML that is later injected via jQuery's `.html()`.

### Fixed

- **Library context-menu "Publish..." item re-enabled.**  Was
  hard-disabled upstream as part of the
  [LibreTime issue #1320](https://github.com/libretime/libretime/issues/1320)
  podcast-feature lockdown (which targeted the
  SoundCloud-integration and the Celery/RabbitMQ paths — neither of
  which exist in RASTATIME).  Now restored as a normal entry next
  to "Delete" and "Edit..." in the file context menu.  The Library
  toolbar's "Publish" button already worked the same way; both
  paths bottom out in `AIRTIME.publish.openPublishDialog`.

- **Publish-to-Station-Podcast: every save threw HTTP 400 with no
  episode created.**  `Application_Service_PodcastEpisodeService::
  publish()` called `_buildEpisode($id, $url, $guid, date('r'))`
  without passing `$title` or `$description`, so both got the
  default `null` and PostgreSQL rejected the INSERT with
  SQLSTATE[23502] (`NULL-Wert in Spalte »episode_title« ... verletzt
  Not-Null-Constraint`).  Now reads `cc_files.track_title` (fallback
  to `cc_files.name`, last-resort `"Track <id>"`) for the title and
  `cc_files.description` (fallback to `""`) for the description and
  passes both into `_buildEpisode`.  Existing call sites for
  RSS-feed-imported episodes were already passing real values and
  are unaffected.

- **Edit Track form: silent save-everything-fails when no Track-Type
  is chosen.**  `FileDataHelper::sanitizeData()` ran
  `intval($data['track_type_id'])` on the POSTed value, which
  collapses the empty-string placeholder (`''` = "Select a Type" in
  the Edit-Track dropdown) to `0`.  But `0` is not in the dropdown's
  Multi-Options list (valid IDs start at 1), so Zend's `InArray`
  validator silently rejected the WHOLE form.  Result: the dialog
  closed as if "Save" had worked, but NO field (Expiry, Description,
  Genre, etc.) was actually persisted, for every track without a
  chosen Track-Type.  Discovered while debugging a report that the
  Expiry field disappeared after save — turned out to be a much
  bigger bug that just nobody noticed because most tracks carry a
  Track-Type.  `sanitizeData` now keeps empty/null as an empty string
  (matches the placeholder option), and the existing
  `StoredFile::setDbColMetadata` mapping converts that back to `NULL`
  at DB-write time, so the storage shape is unchanged.  Also added a
  `WARN`-level log of `Zend_Form::getMessages()` on validation
  failure in `editFileMdAction` so the next silent-validation bug
  leaves a breadcrumb in `legacy.log`.
- **Edit Track form: `expires_at` UPDATE was a no-op on PostgreSQL.**
  The raw-SQL UPDATE that writes the operator-entered Expiry date
  reused the same `:exp` named placeholder twice (once for the value,
  once for the `disabled` flag's comparison).  PostgreSQL's PDO with
  native prepared statements (`ATTR_EMULATE_PREPARES=false`, the
  default) rejects same-name double-bound placeholders, the
  prepare/execute silently failed, no DB row was updated, no
  exception bubbled up.  Split into two distinct placeholders
  (`:exp_set` / `:exp_cmp`) that get bound to the same value;
  semantically identical SQL, but PDO now accepts it.  Latent bug
  that would have surfaced once the Track-Type validation fix above
  let the save actually reach this code path.

- **Smart Block: adding a dynamic block to a show timed out with
  HTTP 500 and the show stayed empty.**
  `Block::getListOfFilesUnderLimit()`'s "repeat tracks until limit
  reached" loop had no safety against the case where no remaining
  track fits the time-left budget (overflow off, shortest track in
  pool > time-to-limit).  `addTrack()` silently no-ops, `totalTime`
  stops growing, the `while` predicate never flips, PHP spins
  forever, mod_fcgid eventually kills it on its pipe-read timeout
  (~40 s), and the caller gets HTTP 500 with zero diagnostics in
  `legacy.log` because no `Throwable` is ever raised.  The
  operator's report 2026-05-18 triggered it with a Smart Block on
  two ~30-min episodes, 4 h limit, repeat=on, overflow=off — two
  tracks at a time cannot fill the residual cleanly.  Bounded the
  loop two ways: (a) precompute the minimum track length in the
  pool and bail out as soon as `(blockTime - totalTime) < minLen`
  since no track can ever fit again; (b) a hard 1000-iteration
  spin-guard as paranoia fallback that emits a `WARN` if it ever
  trips.  Pre-existing upstream LibreTime bug; not a RASTATIME
  regression.
- **showbuilder/schedule-add: PHP `Error` (not just `Exception`)
  now surfaces in operator log.**
  `ShowbuilderController::scheduleAddAction` only caught `Exception`,
  so PHP 7+ `Error` instances (`TypeError`, undefined-method, etc.)
  bubbled up as opaque HTTP 500 with no log entry.  Now catches
  `Throwable` (covers both) and logs class name + file + line +
  full stack trace.  Also bumped the request-parameter
  `Logging::debug` to `Logging::info` and added a `Logging::info('
  success')` marker on the happy path so every schedule-add is
  greppable in `legacy.log` for future diagnostics.

- **Calendar — New/Edit Show: DJs / Hosts selected under "Who" were
  silently dropped on save.**  The "Schedule" form submit used
  `$(...).attr("checked")` to extract checkbox state for the hosts
  list, days-of-week list, and several rebroadcast / record / live-
  link toggles.  Since jQuery 1.6 `.attr("checked")` returns the
  static HTML attribute (i.e. only the initial state, typically
  undefined), not the runtime DOM property — so every user-toggled
  checkbox was treated as unchecked at submit time.  Switched all
  19 affected sites in `add-show.js` to `.prop("checked")` / `.prop
  ("checked", true|false)`.  Fixes the DJ-save bug and likely also
  several latent rebroadcast / record / linked-show toggle bugs that
  no one had reported yet.
- **Calendar — Schedule Tracks dialog now always opens on the
  "Tracks" tab.**  Upstream picked whichever Library tab the
  operator was on most recently (via `location.hash`), so a previous
  click on Playlists / Smart Blocks / Webstreams / Podcasts persisted
  into the dialog.  `highlightMediaTypeSelector` in `schedule.js`
  now explicitly sets `#tracks` on every dialog open.
- **Calendar — Edit Show (non-repeating): renaming silently dropped
  due to locale-dependent `strftime` time format.**  The Propel-
  generated `BaseCcShowDays::getDbStartTime()` defaults to format
  `'%X'` ("preferred time representation"), which is locale-
  dependent.  On a 12-hour-clock locale (en_US default) `'%X'`
  applied to a start_time of `00:00:00` returns the string
  `"12:00:00 AM"` instead of `"00:00:00"`.  Callers that did
  `explode(':', $row->getDbStartTime())` then read the hour as
  `"12"` instead of `"0"`, and
  `Application_Service_ShowService::getInstance()` looked up the
  cc_show_instances row at 12:00 local time (10:00 UTC) instead of
  00:00 local time (22:00 UTC of the previous day).  The lookup
  failed, `createNonRepeatingInstance` threw "Could not find show
  instance with start time: ...", and the entire transaction rolled
  back — including the just-written name update.  The operator saw
  the dialog close successfully, but on reopen the old name was
  back.  Fixed by overriding `getDbStartTime()` in the
  hand-written `CcShowDays` subclass to default to the unambiguous
  24-hour `'H:i:s'` format.  One-line fix that corrects all 29+
  call sites in the codebase without touching Propel-generated
  code (which a future schema regen would overwrite).

- **Calendar — "Edit Instance" dialog: show name stays read-only.**
  The show name lives on cc_show (one row per series), not on the
  per-instance cc_show_instances row, so a name change made from
  the "Edit Instance" dialog would silently rename every other
  instance of the series too — confusing because the operator only
  opened the dialog for one specific instance.  `AddShowWhat::
  makeReadonly()` now greys out `add_show_name` along with every
  other "What" field.  Operators who want to rename the whole
  series use the separate "Edit Show" menu entry (which routes
  through editShowAction / addUpdateShow / setCcShow and now
  works correctly thanks to the getDbStartTime fix above).
- **Podcasts: imported episodes showed "0 sec" in the Library.**
  The Library DataTable computes a track's displayed length as
  `cueout - cuein` (StoredFile.php SQL projection), not by reading
  `cc_files.length` directly.  The standard analyzer pipeline sets
  `cue_in=0` and `cue_out=length` at import time so the subtraction
  yields the real length.  `download_episode()` bypassed the
  analyzer and forgot to set them, so every podcast episode showed
  `0:00` in the Library (Calendar ShowContent, which reads `length`
  directly, was correct).  Now sets `cue_in=0` and
  `cue_out=length` at episode import.  Migration
  `0052_backfill_podcast_cuein_cueout` back-fills the same two
  columns on every existing podcast-referenced cc_files row with
  NULL cuein/cueout — limited to rows referenced by
  `podcast_episodes.file_id` so non-podcast files with deliberately
  empty cue points (e.g. webstreams) are not disturbed.

- **Podcasts: episodes whose download failed were stuck on the
  spinning "downloading" icon forever.**  When the PHP frontend's
  synchronous `/api/v2/podcast-episodes/{id}/download` call returned
  an error, `_download()` just `return`ed without touching the
  placeholder `podcast_episodes` row that `addPlaceholder()` had
  just inserted — so the row stayed with `file_id IS NULL`, and the
  UI's `_getImportedPodcastEpisodeArray()` reported `ingested=-1`
  (pending) indefinitely.  Removing the stuck placeholder on failure
  flips the UI back to "not imported" so the operator can simply
  click Download again.  Already-imported episodes (`file_id` set)
  are never touched.  Migration `0051_cleanup_stuck_podcast_episodes`
  also one-shot deletes any rows that accumulated BEFORE this fix
  went in, so the operator's library does not stay polluted with
  permanently-spinning ghosts (`DELETE FROM podcast_episodes
  WHERE file_id IS NULL`).

### Changed

- **Edit Show form — Record section help-icon text shortened** from
  the long "When enabled, the show's on-air output..." paragraph to
  "When enabled, the Show is recorded to the folder configured in
  Settings → Local Machine".

- **Record-per-Show: recorder now writes its FFmpeg stderr to a
  per-recording log.**  Previously the recorder's subprocess sent
  stderr to `DEVNULL`, so a mid-show crash (rc=3419392776 in a
  recent test) left no diagnosable trace — only the playout's own
  log saying "already exited".  Now each `start()` opens
  `C:\rastatime\logs\ffmpeg-recorder-show<id>-<YYYYMMDD-HHMMSS>.log`
  and writes the full FFmpeg command line as a header, then captures
  every stderr line for the lifetime of that recording.  On
  non-zero exit the playout log now also includes the last ~2 KB of
  stderr inline so the failure is visible without hunting for the
  log file.  Pattern lifted 1:1 from `FfmpegStreamer` and
  `FfmpegLineinCapture` so all three FFmpeg subprocess types share
  the same log-dir convention (`RASTATIME_LOG_DIR` env override).

### Fixed

- **Record-per-Show: long source-switch gaps (~16 s) still produced
  short recordings.**  The mid-show watchdog poll-interval was 5 s
  and respawned the recorder exactly once per detected death.  When
  the recorder respawn _also_ died within the early-death window
  (e.g. `/rastatime` returning 404 because the Line-In Capture
  Tascam-race was still failing during a master->scheduled switch),
  the outer 5 s poll meant another 5-7 s of lost audio before the
  next attempt.  Two tightenings:
  * Poll interval 5 s -> 2 s so the watchdog notices a death within
    a few seconds.
  * Inner retry loop on each respawn: up to 8 attempts with the same
    3 s early-death window and 1 s backoff as the initial-start
    retry, so up to ~32 s of source unavailability are bridged
    without falling back to the outer poll.  Sufficient for the
    longest observed source-switch gap (~16 s for scheduled<->master
    with Line-In Capture flake).

- **Record-per-Show: recording was truncated when the upstream source
  briefly dropped mid-show.**  When `/rastatime` had a transient
  source-loss (Webstream AAC decode error + mpv reconnect,
  scheduled→master switch, Icecast hiccup, FFmpeg-streamer restart),
  the recorder's `-reconnect_*` flags gave up after roughly 3 reconnect
  rounds (~10 s of tries) and FFmpeg exited cleanly with rc=0.  The
  resulting .mp3 ended at the moment the drop started — operators saw
  11-second files from 5-minute shows (193) or 2:34 from 5:00 (194).
  Replaced the one-shot retry thread with a full per-show lifecycle
  thread in `playout_scheduler._show_record_lifecycle`: phase 1 is the
  existing initial-start retry (Line-In warmup 404 window); phase 2 is
  a new mid-show watchdog that polls FFmpeg every 5 s and, on death,
  respawns it in MP3-**append-mode** so the new segment concatenates
  byte-by-byte onto the same .mp3 (MP3 is frame-based and has no
  container header when written with `-write_id3v2 0 -write_xing 0`,
  so no post-processing is needed — every player decodes the joined
  file end-to-end).  The watchdog retries unlimited until SHOW_RECORD_END
  per operator decision; a dauerhaft source-loss log-spams once per
  5 s but the recording resumes the moment Icecast is back.
- **FfmpegLineinCapture: sporadic immediate-death on first dshow open
  killed Line-In shows.**  Tascam USB-audio + Windows dshow occasionally
  fails the very first open with rc=0xCCCC1008 — a known
  kernel-driver-handle-release race.  Added an initial-spawn retry
  (max 3 attempts, 1 s backoff) inside `FfmpegLineinCapture.start()`
  so a single transient failure is recovered before the Line-In show
  starts.  Distinct from the existing post-start watchdog (which only
  kicks in once the capture has been healthy at least once).

- **Record-per-Show: Line-In recordings reliably produced no file
  because FFmpeg gave up after 3 initial-open 404s.**  FFmpeg's HTTP
  demuxer has a hard 3-attempt limit on `avformat_open_input` when
  the server returns an HTTP error; the `-reconnect_*` flags only
  apply AFTER a successful connection.  The Line-In source warmup
  (FfmpegLineinCapture spawn + dshow handshake + mpv attach + 3
  streamer spawns) takes ~1.5-2 s, during which `/rastatime` returns
  404 — the entire 3-retry window expires inside the warmup.  Added
  a Python-side retry thread in `playout_scheduler._on_show_record_start`
  that respawns the recorder if it dies within a 3-second
  early-death window, up to 8 attempts (~32 s total).  The thread
  aborts cleanly if a back-to-back follow-up show has taken over
  the recorder slot.  Required two small `FfmpegRecorder` API
  additions: `current_show_id` property (so the retry thread can
  tell "died" apart from "another show took over") and idempotent
  cleanup of stale state in `start()` when called after a previous
  attempt died asynchronously.  No effect on file / webstream shows
  — those connect on the first attempt and the retry loop returns
  immediately.

- **Record-per-Show: Line-In show recordings silently crashed mid-show.**
  When a Line-In show followed another show, the playout engine's
  source-switch tore down and respawned the three FFmpeg streamers
  from scratch, leaving the `/rastatime` Icecast mountpoint without a
  source for ~2 seconds.  The recorder's FFmpeg saw an EOF on the
  body stream and the default behaviour is to terminate (exit code
  3419392776 in the log).  The recording file ended up zero bytes /
  missing.  Added `-reconnect_at_eof 1` and
  `-reconnect_on_network_error 1` to the recorder command so it
  rides out short Icecast gaps the same way the source-side mpv
  engine already does (those flags were already on mpv's
  `stream_lavf_o` line but missing from the recorder).
- **Record-per-Show: recording typically ~500 ms short of show length.**
  At SHOW_RECORD_END the recorder was stopped synchronously, so the
  tail of the Icecast output that had already been pushed by the
  streamer but not yet consumed by the recorder was lost.  Added a
  1-second post-roll: the deferred stop checks `stop_if_recording
  (show_id)` so a back-to-back follow-up recording is never
  interrupted by the previous show's post-roll timer.

- **Record-per-Show: filename used UTC instead of local time.**  The
  scheduler hands `show_starts_at` to the recorder as a naive UTC
  datetime, and `build_output_path()` formatted it directly — a show
  scheduled at 13:00 local time (Europe/Berlin, CEST = UTC+2) ended
  up as `... 11-00 - <show>.mp3` on disk, off by the operator's UTC
  offset.  Re-attached UTC tzinfo and called `.astimezone()` to
  render in the system's local timezone.  DST-safe: a 13:00 show
  produces `13-00` in both summer (CEST = UTC+2) and winter
  (CET = UTC+1).
- **Dashboard On-Air light + source switches lagged ~3-4 s behind
  reality.**  The dashboard polled `Schedule/get-current-playlist`
  every 5 seconds, so a sub-second backend state change (Icecast
  mount_add when a show starts, mount_remove when it stops) only
  surfaced on the next poll.  Lowered the interval to 2 s; the
  request load on the local Apache is negligible (small JSON
  endpoint), worst-case lag drops from ~5 s to ~2 s.  A push-based
  SSE/WebSocket fix would be cleaner but is a much larger change.

- **Record-per-Show: recorder never started — recording folder
  endpoint shadowed by REST detail route.**  The new
  `LocalRecordingFolderView` was registered at
  `/api/v2/preferences/local-recording-folder`, but
  `router.register("preferences", PreferenceViewSet)` already claims
  the entire `/preferences/<pk>` subtree for its REST detail route.
  DRF treated the path as `pk="local-recording-folder"`, found no
  integer-pk match, and 404'd before the explicit `path()` was ever
  consulted.  The playout's `_fetch_recording_folder()` saw the 404,
  returned `None`, and the show-record handler logged
  "no recording folder configured" and skipped silently — even
  though `cc_pref.local_recording_folder` was populated.  Moved the
  endpoint out of the `preferences/` subtree to `/api/v2/recording-folder`
  (router.py) and updated the client URL in
  `playout_scheduler._fetch_recording_folder` to match.
- **Record-per-Show: file showed 0 bytes during a live recording.**
  FFmpeg buffered output in RAM and only flushed on graceful exit, so
  the operator had no way to monitor the recording mid-show and a
  crash would have lost everything.  Added `-flush_packets 1` to the
  output side of the recorder command so each packet is written to
  disk as it arrives.
- **Record-per-Show: first ~7 seconds of every show were missing.**
  The recorder reached the Icecast mountpoint a few hundred
  milliseconds before the streamer pushed its first packet; the
  resulting 404 triggered FFmpeg's reconnect loop, which then waited
  up to 5 s before retrying.  Lowered `-reconnect_delay_max` from 5 s
  to 1 s so the worst-case loss is roughly one reconnect attempt.

- **Record-per-Show: schedule builder read wrong JSON key.**  The
  Django `ShowInstance` model exposes the `record` DB column under
  the Python attribute name `record_enabled`, and
  `ModelSerializer(fields="__all__")` puts the Python attribute name
  in the JSON.  The schedule builder checked
  `show_instance.get("record")` which was always `None`, so
  `generate_show_record_events()` was never invoked even after the
  endpoint issue above is resolved.  Fixed by reading
  `show_instance.get("record_enabled")` in
  `libretime_playout.player.schedule.get_schedule`.
- **Calendar: recording-enabled shows lost their fill-bar + content
  icons.**  `full-calendar-functions.js` gated the per-show progress
  bar and the empty / partial-filled / overbooked icons on
  `event.record === 0` — a Linein-era assumption that a "recorded
  show" had no schedule.  Under RASTATIME's parallel record-tap
  semantic, the show still has a normal schedule, so both gates are
  dropped; recording shows now render identically to non-recording
  shows.

### Changed

- **Edit Show form: Record section laid out like Autoloading
  Playlist.**  The previous inline paragraph above the checkbox was
  replaced with an info-icon (`.show_record_help_icon`) that opens
  the same explanatory text on hover via qtip2 — same component
  pattern as the existing Add-Autoloading-Playlist help-icon.  The
  checkbox + label + icon now sit on a single `<dt>/<dd>` row inside
  a `<fieldset>/<dl>`, so spacing, alignment and visual weight match
  the other collapsible sections of the Edit Show form.

- **`cc_show_instances.record` flag semantic broadened.**
  Upstream LibreTime used the record flag to mean "this show IS a
  Liquidsoap line-in recording": the dashboard rendered "Recording
  From Line In", the calendar context menu hid Schedule Tracks /
  View / Clear / Cancel, the showbuilder refused all editing on
  recorded-show rows, and the "Record" checkbox locked itself once
  saved.  RASTATIME's Phase B Record-per-Show feature redefines
  the flag as "tap the on-air output to a parallel MP3 recorder"
  — the show is otherwise a normal scheduled show.  All the
  Linein-specific code paths that gated normal operation on
  isRecorded() were dropped: Dashboard.php no longer returns the
  show's own name as a recording placeholder when no schedule
  items exist; CalendarService.php's full menu (Schedule Tracks /
  View / Clear / Cancel) is always available; ShowBuilder.php no
  longer early-returns isAllowed() for si_record == 1 and no
  longer sets row['record'] = true; ScheduleController.php and
  ShowFormService.php no longer disable the checkbox post-save.
  The isRecorded() method itself is preserved (used by form
  pre-fill and the calendar rebroadcast-conflict check).  See
  architecture **Section 23.13**.

### Added

- **Record-per-Show (per-show on-air recording).**  Shows flagged as
  "Record this show" in the Edit Show form now produce a single MP3
  of the on-air output, written to
  `<recording-folder>/<YYYY-MM-DD>/<YYYY-MM-DD HH-MM> - <show-name>.mp3`.
  Implementation taps the first configured Icecast output mountpoint
  (e.g. `http://localhost:8000/rastatime`) with FFmpeg `-c copy` —
  1-2 % CPU cost, no re-encode, recording quality matches what
  listeners hear, source switches (file track / web stream /
  line-in / master) captured automatically.  New event types
  `SHOW_RECORD_START` / `SHOW_RECORD_END` decouple the recorder
  lifecycle from the per-source event chain.  Recording folder is
  configured under Settings -> Local Machine (new "Recording
  Folder" section below the Import Folder), exposed to the playout
  via new endpoint `GET /api/v2/preferences/local-recording-folder`.
  The old Line-In-only label "Record from Line In?" on the show
  form is renamed to plain "Record this show".  See architecture
  **Section 23.13** for the full plumbing, considered alternatives,
  and operator-visible failure modes.

- **Local Import Folder (drop-folder semantics) under
  Settings -> Local Machine.**  Operator configures a single
  absolute folder path on the RASTATIME host; every 5 minutes a
  TaskManager job (`LocalImportScanTask`) walks the folder, hands
  every audio file to the standard `CcFiles::createAndImport`
  pipeline (organize -> analyzer -> cc_files), and deletes the
  source after each attempt — successful OR failed.  A "Scan Now"
  button bypasses the 5-minute throttle for immediate verification
  after configuring a new folder.  Reuses existing infrastructure
  end-to-end: no new analyzer, no new storage code, no schema
  change.  Audio formats recognised: mp3, wav, m4a, flac, ogg, oga,
  aac, opus; non-audio files are left untouched (operator may have
  placed them intentionally).  The Settings -> Soundcard page is
  renamed in the navigation to Settings -> Local Machine to cover
  both the existing audio-device sections and the new Import Folder
  section; the controller action is unchanged so existing
  bookmarks/links survive.  See architecture **Section 23.12**.

- **Track Expiry + Podcast Auto-Expiry feature with a shared
  hourly pruner.**  Operators can now attach an expiry date to any
  file in the library through one of three input pipelines:
  (1) a custom ID3v2 TXXX frame named `Expiry` with an
  ISO-8601 date value (`Expiry: 2026-12-21`), read by the analyzer
  on manual uploads; (2) per-podcast auto-expiry: the Edit-Podcast
  form gains an "Auto-Expiry" checkbox and a "Days" field, and
  the Django `download_episode` view computes
  `expires_at = now() + days` on every episode imported from that
  podcast (per design decision B, this overrides any ID3 tag the
  publisher set — subscribers own retention); (3) manual edit on
  the Library's Edit Audio MD form, with a YYYY-MM-DD text field.
  An hourly `TrackExpiryTask` (TaskManager) flips
  `cc_files.disabled = true` on every row where
  `expires_at < NOW()`.  Disabled tracks stay visible in the
  Library and in already-built Smartblocks (so scheduled shows
  keep playing them) but are excluded from NEW Smartblock
  evaluations via a `disabled = false` clause on the criteria
  query.  Two new optional columns in the library DataTable
  ("Expiry Date" and "Disabled") let the operator sort and bulk-
  delete the expired set at their leisure.  Migration
  `0049_add_track_expiry_and_podcast_auto_expiry`.  See
  architecture **Section 23.11** for the full design and the
  rationale for precedence decision B and disable-vs-delete
  decision A.

- **Per-webstream static input-gain.**  New column
  `cc_webstream.input_gain_db` (default 0, range -20..+20 dB) lets
  operators compensate for chronically quiet or loud third-party
  webstream feeds without leaning on the upstream feed operator to
  re-normalise.  Applied by the FFmpeg streamer and the mpv local
  monitor as a single `-af volume=<dB>dB` audio filter for the
  lifetime of the webstream event, using the same mechanism as the
  existing file-track ReplayGain pipeline (Section 23.8).  The
  webstream edit dialog gains an "Input Gain (dB)" numeric field
  between Default-Length and Save; legacy webstreams without a value
  fall back to 0 = no change to behaviour.  Migration
  `0048_add_cc_webstream_input_gain_db`.  See architecture
  **Section 23.10** for the full plumbing and the engine-parameter
  generalisation (`replay_gain_db` -> `gain_db`).

- **Distinct `RASTATIME_VERSION` constant for the fork.**  Introduced in
  `application/configs/constants.php` (currently `0.5`, in lockstep with
  the ARCHITECTURE.md version-history).  Settings -> Status now displays
  "RASTATIME Version 0.5" in the top row instead of the upstream
  LibreTime release.  The upstream version (from `frontend/legacy/VERSION`)
  is still available as `Config::getConfig()['airtime_version']` for
  callers that need upstream-sync tracking, API-response compatibility,
  etc.

- **Service-restart UI on Settings -> Status (admin-only).**  Adds a per-
  service Restart button for each of the six RASTATIME NSSM services
  (ANALYZER, API, APACHE, ICECAST, PLAYOUT, WORKER) plus a "Restart All
  Services" button.  Each row carries a short "what this service does
  and when to restart it" hint so the operator does not need to leave
  the page to make the right call.  All requests are CSRF-protected,
  POST-only, and the service name is matched against a constant
  whitelist before reaching the shell; the page itself is ACL-gated to
  the Admin role via the existing `systemstatus` resource entry.
  The upper status table's six RASTATIME-service rows now display a
  pure-icon running-state cell (green check via the existing `.check`
  class on RUNNING, red cross via the new `.fail` class otherwise),
  matching the look of the Postgres / Database / RabbitMQ dependency
  rows.  The previous `sc query` / `sc start` recovery hints were
  removed from those cells; the Restart button in the lower table is
  now the canonical recovery path.

  Apache restarts (single or as part of restart-all) are scheduled
  through a self-deleting temp .bat file spawned via
  `wmic process call create`, NOT via `start /B`.  `start /B` leaves the
  child in the same console as the Apache worker that issued it; when
  Windows tears down Apache's job object during the restart, the child
  goes with it and Apache hangs in SERVICE_STOP_PENDING
  ("Wird beendet") with nothing left to fire `nssm start` afterwards.
  This was the cause of the first restart-all hang on 2026-05-16 (only
  recoverable via `taskkill /F /IM httpd.exe`).  WMI spawns the child
  outside Apache's job object, and the batch file includes a short
  ping-based pre-delay so the JSON response to the operator reaches
  the browser before nssm reaches into Apache.  Restart-all also
  reorders services so Apache is restarted LAST, after a 6s delay
  (other services get 2s).  The JS auto-reload waits 15s before
  refreshing the status page.

- **ReplayGain is now actually applied** to scheduled file tracks.  The
  precomputed dB offset (``cc_files.replay_gain`` + ``cc_pref.replay_gain_modifier``)
  has been summed onto ``FileEvent.replay_gain`` since the early
  schedule-builder was written, but neither the FFmpeg streamers nor
  the mpv local-monitor consumed the value — it ran into the void.
  Both engines now accept a ``replay_gain_db`` parameter and apply
  it as a single ``volume=<dB>dB`` audio filter (FFmpeg: ``-af
  volume=...`` between input and encoder; mpv: ``af`` property
  ``lavfi=[volume=...]`` reset on every ``play()`` so live sources
  don't inherit a previous track's gain).  ``PlayoutScheduler``
  threads the value through from ``_on_file_start`` and caches it
  on ``_current_replay_gain_db`` so the resume path (DJ-disconnect
  fallback, hot-reload restart, schedule refresh mid-track) keeps
  the right correction in place.  Live sources (linein, webstream,
  master/show) pass ``None`` and are not gain-modified.  5 new unit
  tests in ``backend/playout/tests/engine/test_ffmpeg_streamer_replay_gain.py``
  cover the filter-emission paths.
- **FFmpeg-based playability check at file import time.** The upstream
  `analyze_playability` step required Liquidsoap on PATH; since RASTATIME
  intentionally ships without Liquidsoap (ADR-002), the check was a silent
  no-op on this platform and broken or partially-corrupted audio files were
  only surfaced at actual playout time (mid-show "Header missing" log
  spam, briefly muted last frames).  The new check runs
  `ffmpeg -v error -i <file> -f null -` against every imported file:
  - exit 0 + empty stderr → clean (no log)
  - exit 0 + decoder warnings → soft-warn (logged at WARNING; import
    allowed; typical "trailing-frame Header missing" pattern from
    poorly-encoded MP3s)
  - exit non-zero → hard reject via `UnplayableFileError` (existing
    upstream behaviour, importer skips the file)
- **Re-scan tool for the existing library**:
  `infra/scripts/maintenance/rescan-playability.py`.  Walks every
  ``cc_files`` row, applies the same FFmpeg-based check, and reports
  hard failures / soft warnings / missing-on-disk entries.  Run via the
  project venv's Python; reads storage root and DB creds from
  ``libretime.conf``.  Smoke-test on a 10-row slice surfaced 4 pre-
  existing soft-warn files plus one DB-row-without-file (id=1) in the
  current library.

- **Per-DJ source authentication against the LibreTime database** (Phase B.4
  #2).  Replaces the previous "single shared password per mount" model with
  Icecast 2.4's `stream_auth` URL-auth callback (Apache → light PHP at
  `public/icecast-source-auth.php`, no Zend bootstrap).  The PHP validates
  the source against `cc_pref` (master DJ) or the active show's
  `cc_subjs ∪ cc_show_hosts` set with md5 password comparison (show DJs,
  Legacy LibreTime hash format).  Operator-override fallback credentials
  (`source` / `master-secret` / `show-secret`) remain valid as a DB-down
  escape hatch.  Strict mode (Variant A): no active show → /show is
  rejected, no DJ may pre-connect.
- **`GET /source-state` endpoint** on the playout listener (`:8770`).
  Returns JSON `{master_connected, show_connected, current_state}` with a
  process-internal-state read; consumed by the legacy dashboard's "On Air"
  indicator instead of stale `cc_pref.{master_dj,live_dj}_switch` columns.
- **Reconciliation watchdog** in `libretime_playout.source_switcher`.  A
  daemon thread polls Icecast's `/admin/listmounts` every 10 s and syncs
  the `SourceSwitcher` state with whatever Icecast actually reports — auto-
  heals stuck `master_connected=True` / `show_connected=True` states caused
  by missed `mount_remove` notifications.  Worst-case stuck-state
  duration: ~10 s.
- **Direct-to-`:8770` source-event wiring** in `icecast.xml`.  Mount-level
  `mount_add` and `mount_remove` URL options now point straight at the
  playout's source-event listener, bypassing PHP.  PHP's async
  `popen('start /B …')` + curl path turned out to be unreliable on
  Windows fcgid — the curl child was reported as spawned (`popen=ok`) but
  did not consistently reach `:8770`.  Icecast 2.4 itself does proper
  outbound HTTP for these URLs, which we trust as the fast path; the
  reconciliation watchdog above is the slow safety net.
- **Friendly-name fallback for unstable USB audio endpoint GUIDs**
  (Phase B.4 #4).  Empirically, Windows can reassign the WASAPI endpoint
  GUID of a USB audio device after reboot / driver update / port re-
  enumeration — observed with Jabra USB headsets.  Both `rastatime_linein`
  and `rastatime_soundcard_settings` now carry a `device_name`-style
  column alongside the `device_id` stable-ID.  The shared resolver
  `WindowsAudioDeviceManager.find_device_by_id_or_name()` tries the saved
  GUID first and falls back to a case-insensitive friendly-name match,
  logging a WARNING that prompts the operator to re-save the picker
  once.  Migrations: `linein/0004_linein_device_name`,
  `soundcard/0002_add_output_device_names`.

### Changed

- **Playout engine gain parameter generalised from `replay_gain_db`
  to `gain_db`.**  The mechanism (single FFmpeg `volume` filter
  before the encoder, or mpv `af` property `lavfi=[volume=...]` for
  the local monitor) is unchanged, but the parameter now carries
  whatever per-event dB value applies for the current event type:
  precomputed ReplayGain sum for file events,
  `cc_webstream.input_gain_db` for webstream events, `None` for
  live sources (Master/Show/Linein).  The scheduler picks the
  right source value per event and passes the result.  Affected
  symbols: `PlayoutEngine.play()`, `FfmpegStreamer.start()`,
  `MpvPlayoutEngine.play()`, `VlcPlayoutEngine.play()`,
  `PlayoutScheduler._start_streamers()`, and the cached
  `PlayoutScheduler._current_replay_gain_db` field (renamed to
  `_current_gain_db`).  Test file
  `test_ffmpeg_streamer_replay_gain.py` renamed to
  `test_ffmpeg_streamer_gain.py` with the same five assertions
  updated to the new keyword; the tests do not depend on which
  feature the gain originated from.

- **`Preference::GetSourceStatus()` / `GetSourceSwitchStatus()` (legacy
  frontend)** now fetch live state from the playout's `/source-state`
  endpoint with a per-request static cache and a 500 ms timeout, falling
  back to `off` on playout unreachability.  Previously these read from
  `cc_pref.{master_dj,live_dj}` and `cc_pref.{master_dj,live_dj}_switch`
  columns that nobody writes anymore since the icecast-hook refactor,
  resulting in a permanently-dark "On Air" indicator.

### Fixed

- **Windows-service health probe was locale-dependent.**
  `check_windows_service()` ran `sc query <name>` and matched the literal
  string "RUNNING" in the output to decide whether a service was up.
  On any non-English Windows install (e.g. German "WIRD AUSGEFÜHRT")
  the match silently failed and the Settings -> Status table rendered
  a red-cross indicator for healthy services.  Two text-parsing
  iterations were tried (anchor on the literal label "STATE :",
  then parse by value-line position) and both regressed in subtle
  locale-specific ways because sc.exe localises labels, separators,
  and header lines independently.  Final fix switches the probe to
  PowerShell `Get-Service`, whose `.Status` property is the .NET
  ServiceControllerStatus enum --- its member names ("Running",
  "Stopped", "Paused", ...) are language-invariant regardless of OS
  display language.  Two further snags surfaced during deployment:
  (a) PowerShell on Windows defaults to UTF-16 LE output with a BOM,
  which PHP's exec() reads as NUL-interleaved bytes that never compare
  equal to the ASCII string `'Running'`; fixed by forcing
  `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8` in the
  PowerShell command line.  (b) The Apache/NSSM service worker can run
  with a stripped-down PATH that does not contain
  `C:\Windows\System32\WindowsPowerShell\v1.0\` (NSSM service-account
  environment is not the same as the interactive user shell --- nssm.exe
  itself happened to be on PATH which masked this issue); fixed by
  resolving an absolute path via `getenv('SystemRoot')` with explicit
  fallbacks.  Results are static-cached for the lifetime of the request
  and pre-warmed with a single batched PowerShell call so the
  Settings -> Status page pays one process-start cost (~500ms) instead
  of six.  Affects all six RASTATIME NSSM service rows.

- **Settings -> Status icons (.check / .fail) were invisible because
  the empty status TD collapsed below the background image's height.**
  Added explicit `min-height: 24px; min-width: 24px` to
  `.solution.check, .solution.fail` in `config-check.css` so the cell
  is always tall enough to render the 16-pixel accept/delete glyph.
  Latent upstream issue that became visible the moment we added the
  six RASTATIME-service icon rows.

- **Playlist row preview silently no-op'd from the Library context menu.**
  Two compounding bugs:
  1. `Application_Model_StoredFile::searchFiles()` had a copy-paste typo —
     the per-row recompute block used `$r` (undefined) instead of `$row`
     (the loop's reference variable), so `Application_Model_Playlist::getLength()`
     and the Smart-Block `bl_type` flag never made it into the
     DataTables response.
  2. The icon-click and context-menu "Play" callbacks in `library.js`
     guarded the playlist branch with `data.length !== "0.0"`.  Combined
     with the typo above, every legacy playlist whose `cc_playlist.length`
     DB column was `00:00:00` (most of them) formatted to the literal
     string `"0.0"` and silently failed the guard.
  Both addressed: `$r → $row` rename, plus the strict-equality length
  check dropped from both JS callbacks (an empty player popup is better
  UX than a click that does nothing).
- **Dashboard header showed bare "," for active Line-In schedule rows.**
  `Schedule::getPreviousCurrentNextMedia()` only inspected `cc_schedule.file_id`
  and `cc_schedule.stream_id`, so Line-In rows (which carry their reference
  in `cc_schedule.linein_id`) fell into the "unknown type" branch with an
  empty `name`.  Dashboard JS then printed `name + ","` giving the
  observed comma-only display.  Added a raw-SQL bridge
  `_fetchLineinForScheduleId()` (Propel's CcSchedule base class isn't
  aware of `linein_id`; the legacy schema.xml was extended but the
  generated classes were never regenerated) and use it in the previous /
  current / next branches to populate `name` with the operator-given
  Line-In label (e.g. `"Jabra-Mikro"`) and `type='linein'`.
- **Library "Delete" button silently no-op on Line-In rows.**  The dashboard's
  "Delete" button and the row-level context menu's "Delete" entry both
  forwarded `{type: 'linein', id: ...}` to `library/delete`, but
  `LibraryController::deleteAction()` only handled `audioclip` / `playlist` /
  `block` / `stream` types.  Line-In items fell through the type-dispatch
  with no DELETE call and no error, leaving the row in the table.  Added a
  dedicated branch that calls `DELETE /api/v2/audio/linein/<pk>` on the
  Django API and surfaces non-2xx responses as a "Could not delete some
  Line-In sources" message.
- **"Stuck `master_connected=True`" state** that left the playout pointing
  FFmpeg streamers at an empty `/main` mount after a brief BUTT connection
  to `/main` was followed by a disconnect that Icecast 2.4 occasionally
  failed to surface via `mount_remove`.  Output mounts then carried
  silence even though the scheduler thought everything was healthy.
  Addressed by the reconciliation watchdog described above.
- **Per-DJ accountability on `/show` source connections**.  Pre-refactor,
  any client knowing the shared static `<password>show-secret>` could
  push to `/show` as any username with no DB check.  Now the URL-auth
  layer rejects sources whose user is not a configured host of the
  currently-running show (or the show's custom auth user, when the show
  has `live_stream_using_custom_auth`).

- **Settings -> General -> "Default Language" silently flipped the
  operator's UI language back to whatever the global default happens
  to be, on every save that did not touch the language dropdown.**
  The form pre-filled the language dropdown with `GetDefaultLocale()`
  (the global cc_pref.locale row, used as the seed value for new
  users).  Combined with the three-source-sync save handler
  introduced earlier on this date, any save where the operator
  changed an unrelated field (e.g. uploading a favicon) round-tripped
  the global default through `SetUserLocale()` and the
  `airtime_locale` cookie, overwriting the operator's own per-user
  language preference.  Fix: pre-fill the dropdown with
  `GetLocale()` (the operator's effective locale) so an untouched
  dropdown is a no-op on save.  Non-logged-in users still see the
  global default because `GetLocale()` falls back to it when no
  session user is set.

- **Settings -> General -> "Default Language" never visibly took effect**
  for the operator who flipped it.  Three issues compounded, all
  uncovered the moment the new `.po -> .mo` pipeline produced
  real translations to bind against:

  1. `PreferenceController::indexAction()` only wrote `cc_pref.locale`
     (the global default for new users).  RASTATIME has three Locale
     source surfaces and `GetLocale()` for a logged-in user prefers
     the per-user `cc_pref.user_locale` row, which the form save
     never updated.  The `airtime_locale` cookie additionally out-
     prioritises both in the pre-login and Edit-User paths and was
     also not refreshed.  Fix: the save now writes `SetDefaultLocale`,
     `SetUserLocale`, the cookie, and re-runs
     `configureLocalization()` inline so the "Preferences updated"
     confirmation and the re-rendered form labels are already in the
     newly selected language.

  2. `Application_Model_Locale::configureLocalization($locale = null)`
     contained a use-after-null bug: when called without an argument
     (the `PageLayoutInitPlugin` hot path on every request), it built
     `$lang` from `Preference::GetLocale()` correctly but then ran
     `putenv("LANGUAGE={$locale}")` with `$locale` still null,
     silently emptying the LANGUAGE env var that drives gettext's
     `.mo` lookup.  gettext then fell back to whatever LC_MESSAGES
     the Apache/fcgid worker carried from a previous request, which
     on a recycled worker pinned the UI to the first locale ever
     bound in that process ("sticky-stale German even after
     switching to English").  Fix: resolve `$locale` before the
     `putenv` call.  Also added a multi-format `setlocale` retry
     (`en_US.UTF-8` -> `en_US` -> `en-US`) for Windows hosts that
     reject POSIX locale names, and switched `bindtextdomain` to an
     absolute path so CWD churn under Apache/fcgid cannot
     misdirect the lookup.

  3. `application/configs/navigation.php` is loaded at Bootstrap
     time, before `configureLocalization()` runs.  It was calling
     `_('Calendar')`, `_('Settings')`, etc. directly while building
     the Zend_Navigation container, which translated against the
     half-set worker locale state and stored the translated text in
     the container.  `views/scripts/menu.phtml` then ran
     `_($page->getLabel())` at render time, but the label was
     already in the target language (e.g. "Kalender") and gettext
     msgid keys are always English, so the second pass was a no-op
     fallback.  Symptom: top-nav labels like "Calendar" / "Kalender"
     never changed when the operator switched language, while
     correctly-bound strings inside view scripts (e.g. "Smart Block"
     in `layout.phtml`) did switch.  Fix: navigation.php now stores
     plain English source strings; the .po extraction tools still
     pick up these msgids from the many other .phtml files that
     reference them.  Header comment in `navigation.php` updated to
     match the actual design.

### Added

- **Service restart controls on Settings -> Status (admin-only).**
  A new "Service Management" block underneath the existing status table
  exposes one "Restart" button per RASTATIME Windows service
  (ANALYZER, API, APACHE, ICECAST, PLAYOUT, WORKER) plus a
  "Restart All Services" button.  Each row carries a short description
  of what the service does and a one-line "when to restart" hint so
  the operator does not have to memorise which service owns which
  function.  Backend: `SystemstatusController::restartServiceAction`
  and `restartAllAction` shell out to `nssm restart <name>` after a
  POST + CSRF + whitelist check (only the six service names above
  are accepted; anything else is rejected before reaching exec).
  Apache restarts run detached (`start /B "" nssm restart ...`)
  because the Apache worker hosting the request would otherwise be
  killed mid-response; the UI shows a warning and auto-reloads after
  a 12-second delay.  ACL inherits from the existing `systemstatus`
  resource which is already restricted to role `A` (Admin) and
  above.  Also: the status table was extended to display health for
  the analyzer, icecast, and apache services that were previously
  not covered by `checkExternalServices()`.

- **Custom station favicon upload in Settings -> General.**  Operators can
  now upload a `.png`, `.jpg`, `.gif`, or `.ico` (<= 200 KB) and it
  replaces the bundled `public/favicon.ico` for every page in the
  legacy frontend (dashboard, library, login, radio page, etc.).
  Storage follows the same pattern as the existing station-logo upload:
  base64 blob in `cc_pref.station_favicon` plus a separate
  `cc_pref.station_favicon_mime` row.  Render path emits a `data:` URI
  in the `<link rel="icon">` tag, so no writes to `public/` happen at
  request time.  `PageLayoutInitPlugin` and `LoginController` both
  query `Preference::GetStationFaviconHref()` and fall back to the
  static `favicon.ico` when no custom upload exists.  Live preview
  on the form mirrors the station-logo upload, and a Remove button
  clears both cc_pref rows.

- **Operator-facing localisation guide** at
  `frontend/legacy/locale/README.md`.  Step-by-step instructions for
  editing a single translation, ratifying fuzzy entries, adding a new
  language (Locale.php + locale.gen + datatables-i18n + plupload-i18n
  + build script), and a short troubleshooting list for "string
  stubbornly in the wrong language".  Architecture **Section 23.9**
  links to it as the lower-abstraction operator reference.

- **Windows-native `.po → .mo` build pipeline for the legacy frontend
  locales.**  `infra/scripts/maintenance/build-locales.ps1` compiles
  every active language's `libretime.po` into a binary `libretime.mo`
  using mlocati's standalone `gettext-iconv-windows` distribution (no
  MSYS2 / Cygwin / WSL).  Until now, RASTATIME shipped the upstream
  `.po` source files but never the compiled `.mo` artefacts the PHP
  gettext extension actually reads — every language selection on
  Settings → General silently fell back to the English source string.
  See architecture **Section 23.9** for the toolchain choice and the
  rationale against MSYS2 / Chocolatey / pre-compile-at-CI.

### Changed

- **Filled all 234 previously-empty `msgstr` entries in `de_DE/libretime.po`**
  (Phase G).  225 strings went through a user-reviewed translation pass via
  `C:\Temp\rastatime-de-DE-translations-review.md` (HIGH/MEDIUM/LOW
  confidence buckets); 9 additional multi-line `msgid` blocks that the
  single-line extractor had missed (UsabilityHints linked-show banner,
  three embeddable-widget pre-flight checklists, the
  "cannot schedule outside a show" hint, the third-party-API description,
  and three password-reset email templates) were translated with
  best-effort and flagged for follow-up review.  `de_DE.mo` now contains
  985 translated entries; `msgfmt --check-format --check-domain` builds
  it without warnings.

- **Ratified three fuzzy translations in `fr_FR/libretime.po`.**
  Upstream had marked them `#, fuzzy` (translator-suggested but
  unconfirmed) so `msgfmt` excluded them from the compiled `.mo` and
  the strings rendered in English.  All three (`"Retreiving data from
  the server..."`, `"Select Track Type"`, `"Select track type"`) had
  accurate French translations already; we removed the fuzzy flag so
  they are now active.

- **Reduced the legacy frontend's language dropdown from 22 to 4
  maintained locales** (`en_US`, `de_DE`, `fr_FR`, `es_ES`).  The other
  18 entries were inherited Transifex / Weblate translations of varying
  staleness with no RASTATIME support pathway.  `Locale.php $locales`
  array trimmed, `locale.gen` updated, and the 18 unused
  `locale/<LANG>/` directories plus the matching
  `public/js/datatables/i18n/<LANG>.txt` and
  `public/js/plupload/i18n/<LANG>.js` files removed via the one-shot
  delete script `C:\Temp\delete-scripts\rastatime-delete-unused-locales.ps1`.
  Re-adding a language requires synchronised edits documented in
  `Locale.php`.

### Removed

- **Phantom "Feature Previews" setting on Settings → General.**  The radio-
  button pair stored a value to `cc_pref.feature_preview_mode` but the
  getter `Application_Model_Preference::GetFeaturePreviewMode()` was called
  in exactly one place — the form rebuilding its own current value on
  re-render — and the setter only by the form's save handler.  No feature
  anywhere in RASTATIME (or upstream) ever gated on the value, so toggling
  the radio had no observable effect.  Removed: form element +
  `preferences_general.phtml` render line + `PreferenceController` save
  line + `Preference::{Get,Set}FeaturePreviewMode` accessors.  The
  `cc_pref` row with `keystr = 'feature_preview_mode'` is left in place
  for legacy data preservation; nothing reads it now.

- **"Preview (coming in Phase B)" placeholder on Line-In Library rows.**
  Earlier the context menu installed a permanently-disabled "Preview"
  entry to signal a planned feature.  Product decision: don't offer
  Preview for Line-In at all.  A meaningful preview would require a
  per-row Preview-on-Demand FFmpeg capture-to-Icecast pipeline (start
  on right-click, stop on popup-close); the cost / benefit ratio
  doesn't justify it.  The menu entry is now ``unset`` for `linein`
  rows so operators see Edit + Delete only.

- **Phantom "Auto Switch On" / "Auto Switch Off" UI on Settings → Streams →
  Live Broadcasting.**  Both checkboxes saved a value to `cc_pref` but the
  only code path that consumed those values was
  `ApiController::updateSourceStatusAction()`, which dispatched RabbitMQ
  messages to the Liquidsoap-based Pypo playout — both removed in ADR-002.
  The replacement `libretime_playout.source_switcher.SourceSwitcher`
  performs Master > Show > Scheduled priority transitions
  unconditionally, so the operator-controllable gate the upstream
  checkboxes used to provide no longer has a dispatch target.
  Removed: form fields, view template fragments, qtip help popovers,
  `Application_Model_Preference::{Set,Get}{AutoTransition,AutoSwitch}` helpers,
  the `PreferenceController::liveStreamAction` save lines for them.
  Reduced `ApiController::updateSourceStatusAction()` to a no-op stub
  (kept for v1 API client backwards compatibility).  `cc_pref` rows
  with `keystr = 'auto_transition' / 'auto_switch'` are left in place
  for legacy data preservation; nothing reads them now.

- **FFmpeg-Streamer listener-auth via PHP** (`listener_add` URL option) on
  `/main` and `/show` — Icecast 2.4 was rejecting ~50 % of the playout's
  parallel listener-add bursts under load with HTTP 400 even when the
  Apache-side PHP responded 200.  Since `/main` and `/show` are
  `<hidden>1</hidden>` + `<public>0</public>` and Windows-firewall-bound
  to 127.0.0.1, the only realistic listeners are the playout's own mpv +
  FFmpeg streamers; static-password source-auth and `stream_auth` cover
  the authentication need without `listener_add`.

- **FFmpeg-based Icecast streaming.** Replaces VLC's broken sout/shout chain
  on Windows with a per-mount FFmpeg subprocess that reads the same audio
  file VLC plays locally and pushes it to Icecast via the built-in
  `icecast://` protocol. Stable across MP3, Ogg Vorbis, Opus, and AAC.
- **Multi-stream output.** Up to three simultaneous Icecast streams with
  independent codec, bitrate, sample rate, and mountpoint per stream
  (Settings → Streams).
- **Opus codec support** in stream outputs. Frontend dropdown, Backend
  encoder pipeline, and a sample-rate guard that forces 48 kHz when Opus is
  selected (libopus does not accept 44.1 kHz).
- **Sample-rate selector** (44.1 / 48 kHz) per stream output. The Frontend
  greys out 44.1 kHz when the codec is Opus; the Backend additionally
  clamps invalid values with a warning so misconfigured sources never
  reach Icecast.
- **Stream-config hot reload.** Stream-output settings are re-read from
  `cc_pref` on every schedule poll (≤120 s). When a track is playing, the
  new streamers re-attach mid-track at the correct seek position — no
  service restart required.
- **NSSM install / remove scripts** for `RASTATIME-API`, `RASTATIME-WORKER`,
  `RASTATIME-PLAYOUT`, and `RASTATIME-ICECAST` under `infra/nssm/`. All
  services run unattended at boot, with auto-restart, log rotation, and
  log files under `C:\rastatime\logs\`.
- **VLC playout engine (libVLC / `python-vlc`)** as the local-playback
  layer. Catch-up logic re-attaches to in-progress tracks across service
  restarts so a crash mid-show does not silence the air signal.
- **Per-mountpoint FFmpeg stderr logs** (`C:\rastatime\logs\ffmpeg-<mount>.log`)
  capture connection failures and encoder warnings that would otherwise
  vanish into a closed pipe.
- **Legacy v1 API notify** for the dashboard "On Air" indicator. The
  scheduler hits `/api/notify-media-item-start-play` on each track start
  so the red light flips on without depending on Liquidsoap.
- **GitHub Actions CI** (`python.yml`, `php.yml`). Ruff lint and format
  checks are hard-fails for `backend/`; per-package pytest jobs run for
  `analyzer`, `api-client`, `playout`, and `shared`. PHP CI runs
  `composer install` and `php -l` over `frontend/legacy/application/`.
- **Line-In sources** as a first-class equivalent to webstreams: multiple
  local hardware inputs that can be scheduled like any other source.
- **Soundcard settings** page (Settings → Soundcard) for explicit local
  input/output device mapping.
- **German UI translation** alongside the English default.

### Changed

- **Playout engine: Liquidsoap → libVLC → mpv (libmpv).** Liquidsoap is no
  longer required on Windows. All scheduling, queue management, and
  source switching go through the engine-agnostic `PlayoutScheduler`
  (renamed from `VlcScheduler` after the libVLC → mpv migration of
  May 2026) which talks to the `PlayoutEngine` interface — currently
  satisfied by the mpv-backed implementation in
  `libretime_playout.engine.mpv_engine`.
- **Worker: Celery → plain Python task runner.** Removes the RabbitMQ /
  AMQP broker hard-dependency from the worker process.
- **WSGI server: Gunicorn → Waitress** on port 8765, native to Windows.
- **Service manager: systemd → NSSM.** All four services use NSSM with
  identical install / remove / status scripts.
- **Audio output: ALSA / PortAudio / PulseAudio → WASAPI** via libVLC.
- **Filesystem layout.** Linux paths (`/etc`, `/srv`, `/var/log`) replaced
  with Windows paths (`C:\rastatime\config`, `C:\rastatime\media`,
  `C:\rastatime\logs`) repo-wide.
- **Default UI port (operator-facing):** Apache on port 80 (frontend),
  RASTATIME-API on port 8765 (no longer 8000), Icecast on port 8000.

### Removed

- **Liquidsoap dependency.** No `*.liq` template is generated or evaluated
  at runtime; the bundled fixtures remain only as upstream-snapshot
  references for diff'ing with LibreTime.
- **Linux-only installers / packaging** — no `.deb`, no systemd unit
  files, no `apt`-based bootstrapper.

### Notes for upgraders from LibreTime

- RASTATIME is a **functional fork**, not a drop-in replacement. The
  Postgres schema is compatible (LibreTime media libraries can be
  imported), but the playout / streaming subsystems are rewritten from
  scratch. Do not point a running LibreTime install at RASTATIME services.
- Legacy `cc_pref` keys (`stream_output_1..3`) are reused as the source of
  truth for stream-output settings. The Liquidsoap-era keys
  (`use_stream_output_*`, `output_sound_device`) are still read for
  backwards compatibility but are no longer the operative source for
  Icecast egress.

---

<!--
Future releases will go below this line, with the most recent at the top.
Each entry should follow the Keep-a-Changelog grouping:

  ### Added       — new features
  ### Changed     — changes to existing functionality
  ### Deprecated  — soon-to-be removed features
  ### Removed     — features removed in this release
  ### Fixed       — bug fixes
  ### Security    — vulnerability fixes (highlight in release notes!)
-->

[Unreleased]: https://github.com/RASTATIME/rastatime/compare/v0.0.0...HEAD
