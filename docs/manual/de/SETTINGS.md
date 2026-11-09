# Einstellungen

> **Wo Sie sich im Handbuch befinden.** Dieses Kapitel ist das
> Verzeichnis des Einstellungs-Menüs.  Es beschreibt die Seiten
> *Allgemein* und *Status* direkt und verweist für jede andere Seite auf
> ihr eigenes Kapitel.  Gegen die Oberfläche geprüft am 25.10.2026.

Das Einstellungs-Menü ist die Konfigurationsoberfläche der Station.  Die
meisten Seiten gehören den **Admins**; ein
**Program Manager** sieht *Mein Profil*, *Show Templates*, *Auto DJ* und die
Produzenten unter *Archivierung*;
Gäste und DJs sehen nur *Mein Profil*.  Siehe
[Benutzer und Rollen](./USERS_AND_ROLES.md) §2 für die vollständige
Berechtigungsmatrix.

---

## 1. Das Einstellungs-Menü

Linke Navigation → **Einstellungen** öffnet das Untermenü:

| Seite | Zweck | Wer | Kapitel |
|---|---|---|---|
| **Allgemein** | Stationsname und -beschreibung, Sprache, Wochenbeginn, öffentliche API, Radio-Seite, Logo, Hintergrund der Startseite, Favicon, Primärfarbe, Crossfades, Track-Typ für Uploads, Automations-Playlisten, Live Text Info, TuneIn, Dangerous Options. | Admin | Dieses Kapitel §2 |
| **Mein Profil** | Eigener Name, E-Mail, Passwort, Oberflächensprache und Zeitzone. | alle | [Benutzer und Rollen](./USERS_AND_ROLES.md) §4 |
| **Benutzer** | Benutzer anlegen, bearbeiten und löschen, Benutzertyp festlegen. | Admin | [Benutzer und Rollen](./USERS_AND_ROLES.md) §3 |
| **Track-Typen** | Track-Typen mit ihren Vorgaben für Crossfade, Crossover und Stream-Metadaten sowie ihrer Cue-Punkt-Analyse beim Import. | Admin | [Bibliothek](./LIBRARY.md) |
| **Show Templates** | Übersicht der gespeicherten Show-Vorlagen: umbenennen, löschen. | Program Manager, Admin | [Sendungs-Vorlagen](./SHOW_TEMPLATES.md) |
| **Archivierung** | Produzenten der Sendungen - je eine Person oder ein Team (Name, optional Login; einer je Sendung, unter Archivierung gewählt); für Admins darunter die cba.media-Benutzer, unter denen die Sendungen archiviert werden (Benutzername, Anwendungspasswort), Verbindungstest, Upload-Grenze, Wartezeit des automatischen Archivierens. Bis 2026-11-03 zwei Einträge, *Redaktionsteam* und *CBA-Konten*. | Program Manager (Produzenten), Admin | [Archivierung](./ARCHIVING.md) |
| **Auto DJ** | Lückenfüller und Auffüllen unvollständiger Sendungen. | Program Manager, Admin | [Auto DJ](./AUTO_DJ.md) |
| **Streams** | Ausgabe-Streams (Bitrate, Mount, Codec), Eingänge für Live-Einwahlen, Master-Login. | Admin | [Streams](./STREAMS.md) |
| **Lokale Maschine** | Soundkarte, Import-Ordner und -Format, Aufnahme-Ordner und -Format, Speicherort der Bibliothek. | Admin | [Lokale Maschine](./LOCAL_MACHINE.md) |
| **Alarme** | Meldungen per E-Mail und Telegram bei Stille (Dead Air), ausgefallenen Diensten und Preflight-Warnungen; je Kanal ein Schalter. Seit 2026-11-03; seit 2026-11-04 unter Lokale Maschine. | Admin | Dieses Kapitel §6 |
| **Import / Export** | Benutzer, Sendungen, Playlisten, Smart Blocks, Webstreams und Podcast-Abos als CSV/JSON-Dateien, mit Vorschau beim Import. | Admin | [Import / Export](./IMPORT_EXPORT.md) |
| **Backup** | Sicherungen von Datenbank und Konfiguration, der Medienspiegel, automatische Backups, Wiederherstellung. | Admin | [Backup](./BACKUP.md) |
| **Status** | Zustand der Dienste, Speicherplatz, Dienst-Neustarts, erlaubte und gesperrte Adressen. | Admin | Dieses Kapitel §3 |

Line-In-Quellen werden unter **Dashboard → Line Inputs** verwaltet (siehe
[Line-In](./LINE_IN.md)); die Oberflächensprachen behandelt
[Sprachen](./I18N.md).

---

## 2. Allgemein

Einstellungen → **Allgemein**.

Die Seite ist in **eingeklappte Abschnitte** gegliedert (seit
08.10.2026): Stationsname und -beschreibung stehen oben, darunter
*Station*, *Styling*, *Playout* und *Automation*, dann *Live Text Info*,
*TuneIn Settings* und *Dangerous Options*.  Ein Klick auf eine Überschrift
öffnet den Abschnitt; ein Abschnitt mit einem Prüffehler nach
**Speichern** öffnet sich von selbst.

### Oben auf der Seite

| Feld | Hinweise |
|---|---|
| **Stationsname** | Überall sichtbar - Seitentitel, Stream-Metadaten, Radio-Seite. |
| **Stationsbeschreibung** | Freitext, verwendet in Podcast-Feeds und auf der Radio-Seite. |

### Station

| Feld | Hinweise |
|---|---|
| **Standardsprache** | Oberflächensprache für neue Benutzer und den Anmeldebildschirm sowie Sprache aller Widgets (Datum, Wochentage, Knöpfe; seit 25.10.2026). Jeder Benutzer behält seine eigene Sprache aus Mein Profil. |
| **Stations-Zeitzone** | Nur zur Information angezeigt.  Die Zeitzone der Station steht in `config/rastatime.conf` (`general.timezone`); jeder Benutzer kann in Mein Profil eine Anzeige-Zeitzone wählen. |
| **Woche beginnt am** | Erster Wochentag im Kalender und in den Widgets (Weekly Schedule, Multi-View Schedule). |
| **Public RASTATIME API** | *Enabled* erlaubt Widgets, die in andere Websites eingebettet sind, die Sendeplan-Daten zu lesen. Nötig für die einbettbaren Sendeplan-Widgets. |
| **Login-Knopf auf der Radio-Seite anzeigen?** | Zeigt einen Anmelde-Knopf auf der öffentlichen Radio-Seite. |
| **Öffentliche Radio-Seite abschalten und zur Anmeldung umleiten?** | Besucher der Stationsadresse landen direkt bei der Anmeldung. |

### Styling

| Feld | Hinweise |
|---|---|
| **Stationslogo** | Bild oben links auf jeder Seite. Bis 1 MB, JPG / PNG / GIF / WebP; **Entfernen** löscht es. |
| **Hintergrundbild der Startseite** | Das Foto hinter der öffentlichen Startseite (`/`). JPG, PNG oder WebP bis 5 MB; empfohlen 1920 px breit und höchstens 1 MB. Als Datei unter `landing/` im Speicherort der Mediathek abgelegt (damit der nächtliche Spiegel es mitnimmt); **Entfernen** stellt das eingebaute Bild wieder her. Wirkt beim nächsten Laden der Startseite (der Browser hält das Bild eine Woche, ein neuer Upload bekommt eine neue Adresse). Seit 2026-10-07. |
| **Stations-Favicon** | Bild im Browser-Tab. Bis 200 KB, PNG / JPG / GIF / ICO. Als data: URI gerendert; keine Datei-Schreibvorgänge nach public/. |
| **Primärfarbe** | Die Akzentfarbe der gesamten Oberfläche, der Radio-Seite und der Widgets — Links, Hervorhebungen, ausgewählte Zeilen, der aktive Menüpunkt und der aktive Reiter in Playout History, Fortschritts- und Speicherbalken, Scrollbalken, Abschnittspfeile, Play-Knopf und Lautstärkeregler des Stream-Players, Tabs, Knöpfe und Hervorhebungen der Widgets, die Grafik der Fehlerseite. Geben Sie `#rrggbb` ein oder nutzen Sie den Farbwähler neben dem Feld; **Auf Standard zurücksetzen** stellt das Orange (`#ff5d1a`) wieder her. Wirkt beim nächsten Seitenaufruf. Wählen Sie eine Farbe, die sich vom dunkelgrauen Hintergrund abhebt; Text auf der Farbe wechselt von selbst zwischen Weiß und Schwarz. Signalfarben (Fehler, Warnungen, die Sendungsfarben im Kalender) und der Füllstandsbalken der Sendungen im Kalender (immer Orange) bleiben unverändert. |
| **Sekundärfarbe** | Die zweite Farbe der Oberfläche (seit 26.10.2026): der Fortschrittsbalken der Sendung in der Kopfzeile, die Markierung am rechten Rand des aktiven Eintrags im Dashboard-Menü (Tracks, Playlists, Smart Blocks, …) und in den Untermenüs von Settings, Analytics, Help und Widgets, der aktuelle Titel in den Scheduled Shows des Dashboards sowie die Knöpfe Upload, New Show, New Log Entry, Add, New und ähnliche. Geben Sie `#rrggbb` ein oder nutzen Sie den Farbwähler neben dem Feld; **Auf Standard zurücksetzen** stellt das Hellblau (`#1adeff`) wieder her. Die Knöpfe tragen weiße Schrift: für sie wird die Farbe nur so weit abgedunkelt, wie die Lesbarkeit es braucht (Standard: `#0e7a8c`, vorher `#246b86`); Text auf der Zeile des aktuellen Titels wechselt von selbst zwischen Schwarz und Weiß. Wirkt beim nächsten Seitenaufruf. |

### Playout

| Feld | Hinweise |
|---|---|
| **Default Track Crossfade Duration (s)** | Der Crossfade zwischen zwei aufeinanderfolgenden Titeln **derselben Sendung**: der abgehende Titel blendet aus, während der ankommende über so viele Sekunden einblendet (1 Sekunde ist typisch; 0 = die Titel folgen ohne Überlappung; bis zu 10 Sekunden für weiche Übergänge). Der Kalender legt aufeinanderfolgende Zeilen mit genau dieser Überlappung an. |
| **Default Show Crossfade Duration (s)** | Der Übergang **an einer Sendungsgrenze** (seit 2026-09-27): die alte Sendung blendet über so viele Sekunden aus, während der erste Titel der neuen Sendung sofort in voller Lautstärke startet — eine Sendung, die mit Jingle oder ID beginnt, ist vom ersten Schlag an zu hören. Dieselbe Form und derselbe Wert gelten für jeden Wechsel zwischen **Eingängen** (Titel ↔ Webstream ↔ Line-In): die ankommende Quelle ist sofort voll da, die abgehende blendet darunter aus; 0 = harter Wechsel. Ein Webstream oder Line-In, der in beiden Sendungen eingeplant ist, läuft nahtlos weiter. Startwert 1 s. Beide Crossfade-Werte übernimmt die Audiokette wenige Sekunden nach dem Speichern (geplanter Neustart in einem ruhigen Moment oder an einer Titelgrenze); „Jetzt anwenden" in Einstellungen → Lokale Maschine erzwingt es. |
| *Crossfade je Track-Typ* | Einstellungen → Track-Typen → *Crossfade Duration (s)* (seit 2026-09-29) überschreibt den Hauswert für alle Titel dieses Typs; leer = Hauswert. Zwischen zwei Titeln gilt der **kleinere** der beiden Werte, ein Typ mit 0 stößt also immer hart an - der mitgelieferte Typ *Jingles* beginnt mit 0, weil kurze, sekundengenau gebaute Elemente nicht durch einen musiklangen Crossfade verkürzt werden dürfen. An einem Wechsel zwischen einem Titel und einem Webstream oder Line-In gilt der kleinere Wert aus dem Titel-Wert und der Default Show Crossfade Duration. Eine Änderung der Hauswerte oder eines Track-Typs legt die Zeilen aller kommenden Sendungen automatisch neu aus; bereits gestartete Zeilen werden nie angefasst. |
| *Kein Fade je Track-Typ* | Einstellungen → Track-Typen → *No Fade during Crossover* (seit 2026-09-30) ist die Typ-Vorgabe für das Feld *Crossover* im Titel-Editor: Jeder Titel des Typs, der auf *As the track type* steht, behält seinen vollen Pegel, während der Nachbartitel ein- oder ausblendet - die Überlappung selbst bleibt, wie die Crossfade-Dauer des Typs es vorgibt. Gedacht für Jingles oder IDs, die über das Ende eines Songs schneiden sollen. Ein einzelner Titel kann im Titel-Editor weiterhin anders eingestellt werden; ein vom Crossover ausgenommener Titel hat keine Überlappung, in der er seinen Pegel halten könnte. Eine Änderung erreicht das Playout mit dem nächsten Schedule-Push; Zeilen werden nicht neu ausgelegt, weil sich die Überlappung nicht ändert. |
| *Metadaten weitergeben je Track-Typ* | Einstellungen → Track-Typen → *Forward Metadata to the Stream* (seit 2026-10-14) ist die Voreinstellung des Typs für das Feld *Stream-Metadaten* im Track-Editor: abgewählt läuft jeder Titel des Typs mit *Wie der Track-Typ* ohne Interpret / Titel auf dem Stream, die Player zeigen stattdessen „Sendername - Sendungsname" (Jingles, Station-IDs, Promos). Ein Titel kann das in seinem Editor überstimmen. |
| *Cue-Punkte je Track-Typ* | Einstellungen → Track-Typen → (Typ öffnen) → *Analyze cue points*: ob der Import Cue-In und Cue-Out (Stille am Anfang und am Ende) der Tracks dieses Typs erkennt. Entschieden wird einmal, beim Import, nach dem Typ des Tracks - seit 2026-11-09 nach dem Typ, den ein Media-Type-Tag nennt. Die Liste der Track-Typen zeigt die Einstellung nicht; öffnen Sie den Typ, um sie zu sehen. Ein ohne Cue-Punkte importierter Track erhält sie später mit **Cue Points** in der Werkzeugleiste der Bibliothek. |
| **Track Type Upload Default** | Der Track-Typ für neue Uploads, die keinen eigenen setzen. Beeinflusst Smart-Block-Filter. Seit 2026-11-09 gewinnt ein **Media-Type**-Tag in der Datei, der einen Track-Typ nennt, gegen ihn und gegen den im Upload-Dialog gewählten Typ (Bibliothek → *Track-Typ aus dem Media-Type-Tag*). |
| **Trim overbooked shows after autoloading?** | Kürzt den Inhalt einer per Autoloading befüllten Sendung, der länger ist als die Sendung. |
| *Import-Besitzer* | Es gibt keine Einstellung: Dateien, die der Hintergrund-Scan des lokalen Import-Ordners aufnimmt, gehören dem ersten Administratorkonto (`admin`), mit **Scan Now** importierte Dateien dem Operator, der geklickt hat. |

### Automation

| Feld | Hinweise | Kapitel |
|---|---|---|
| **Intro / Outro Autoloading Playlist** | Läuft zu Beginn / am Ende jeder Sendung mit Autoloading. | [Autoloading-Playlisten](./AUTOLOADING_PLAYLISTS.md) |
| **Song-Request Pool (smart blocks)** | Die Smart Blocks, deren Titel Hörer wünschen dürfen. | [Musikwünsche](./SONG_REQUESTS.md) |
| **Traffic-Alert Smart Block** | Der Block für Verkehrsmeldungen. | [Verkehrsmeldungen](./TRAFFIC_ALERTS.md) |
| **Show-Shift Filler Playlist** | Füllt die Lücke, wenn eine Sendung verschoben wird. | [Verzögerter Sendungsstart](./DELAYED_START.md) |
| **Overwrite Podcast Episode Metatags** | Setzt Interpret, Titel und Album heruntergeladener Episoden aus dem Podcast-Feed. | [Bibliothek](./LIBRARY.md) |
| **Generate a smartblock and a playlist upon creation of a new podcast** | Legt für jedes neue Podcast-Abo einen passenden Smart Block und eine Playlist an. | [Bibliothek](./LIBRARY.md) |

### Live Text Info

Aufklappbarer Bereich unter den Allgemeinen Einstellungen (seit
2026-09-28). Die „Now playing"-Zeile als Textdatei für andere Systeme
(Website, Displays, Aggregatoren): eine UTF-8-Zeile, immer ersetzt, vom
Playout bei jedem Wechsel von Titel, Webstream, Line-In oder DJ geschrieben.

| Feld | Hinweise |
|---|---|
| **Die „Now playing"-Zeile in eine Textdatei schreiben?** | Hauptschalter. |
| **Live-Text-Format** | Dieselben drei Varianten wie das Stream Label (Artist - Title / Show - Artist - Title / Station name - Show name) mit denselben Rückfällen: eine Live-Quelle ohne Interpret und Titel zeigt *Station name - Show name*, Stille den Off-Air-Text. Unabhängig vom Stream Label. |
| **Im Web veröffentlichen** | Die Datei wird unter `http://<host>/live/now-playing.txt` ausgeliefert (statische Datei, ohne Login, unabhängig vom Public-API-Schalter). Aus dem Internet erreichbar, sobald der Webserver es ist, wie die Widgets. |
| **Zusätzlich in Datei schreiben** | Optionaler absoluter Pfad (dieser Rechner oder Netzwerkfreigabe). |
| **Auf einen FTP-Server hochladen** | Bei jeder Änderung wird die Datei per FTP, FTPS (explizites TLS) oder SFTP auf den Zielpfad hochgeladen; eigene Zugangsdaten, getrennt vom FTP-Import. SFTP braucht ein `curl` mit libssh2 (das von Git für Windows; das in Windows eingebaute kann es nicht). Fehler werden geloggt, die nächste Änderung versucht es erneut. |

Die Zeile bildet die Audio-Engine aus den Metadaten, die sie tatsächlich
in den Stream sendet, DJ-Titel und Webstream-Titel eingeschlossen. Eine
geänderte Einstellung greift beim nächsten Wechsel, kein Neustart.

### TuneIn Settings

Aufklappbarer Bereich unter den Allgemeinen Einstellungen. Seit
2026-09-28 sendet der Playout die „Now playing"-Information selbst an
TuneIn; vorher wurden nur Datei-Starts gemeldet, und die Anzeige verschwand
nach fünf Minuten.

| Feld | Hinweise |
|---|---|
| **Push metadata to your station on TuneIn?** (Metadaten an TuneIn senden) | Hauptschalter. Wenn an, sendet der Playout bei jedem Titelstart Titel und Interpret, beim Start eines Webstreams oder Line-Ins den Sendungsnamen, und wiederholt die letzte Meldung alle vier Minuten (TuneIn entfernt eine Anzeige, die fünf Minuten still bleibt). Speichern mit aktivem Schalter prüft die Zugangsdaten gegen TuneIn und lehnt ungültige ab. |
| **Station ID**, **Partner Id**, **Partner Key** | Aus Ihrem TuneIn-Partnerkonto (AIR API). Der Key erscheint in keinem Log. |

Eine geänderte Einstellung greift beim nächsten Push; kein Neustart. Ein
Live-DJ (Master / Show Source) wird nicht gemeldet; der letzte Titel
bleibt bis zum nächsten geplanten Element in der Anzeige.

### Dangerous Options

Standardmäßig eingeklappt; beide Knöpfe fragen nach und sind nur für
Administratoren.

| Knopf | Wirkung |
|---|---|
| **Delete All Tracks in Library** | Entfernt jeden Track aus der Bibliothek und aus künftigen Sendeplänen (Upstream). |
| **Clear Calendar** (seit 2026-10-14) | Entfernt jede Sendung, die **noch nicht begonnen** hat, samt Inhalt und beendet alle Wiederholungen. Die laufende Sendung und alles Vergangene bleiben, das Sendeprotokoll behält seine Sendungsnamen. Eine Sendung ohne verbleibende Instanz wird gelöscht. Die Bestätigung nennt, wie viele Instanzen und Sendungen entfernt wurden. |

> **Unter der Haube.** Die Werte sind Zeilen der Tabelle `cc_pref`
> (Schlüssel / Wert).  Werte je Benutzer (Sprache, Zeitzone,
> Tabellen-Layouts) sind `cc_pref`-Zeilen, die an den Benutzer gebunden
> sind.  Dienst-Konfiguration, die nicht in der Datenbank liegen kann
> (Datenbank-Zugang, Pfade, Zeitzone der Station, API-Schlüssel), steht
> in `config/rastatime.conf`.

---

## 3. Status

Einstellungen → **Status**.  Von oben nach unten:

| Abschnitt | Inhalt |
|---|---|
| **RASTATIME Version** | Die installierte Version. |
| **Komponenten** | PDO- und PostgreSQL-Bibliotheken, Datenbank- und RabbitMQ-Konfiguration und die Windows-Dienste RASTATIME-PLAYOUT, -WORKER, -API, -ANALYZER, -ICECAST und -APACHE mit ihrem Zustand. Ein als gestoppt angezeigter Dienst ist das Signal, nachzusehen (`Get-Service RASTATIME-*` in PowerShell oder das Runbook [`CRASH_RECOVERY`](../../operator/CRASH_RECOVERY.md)). |
| **Speicherplatz** | Freier und belegter Platz des Speichers. |
| **Dienst-Neustarts** | Je Dienst (Analyzer, API, Apache, Icecast, Playout, Worker) ein Knopf **Restart** mit Beschreibung, was der Dienst tut und wann ein Neustart hilft, dazu **Restart All Services** (die Oberfläche ist etwa 10 Sekunden nicht erreichbar). |
| **Erlaubte Adressen** | Adressen und Netze, die keine Login-Bremse je sperrt. |
| **Gesperrte Adressen** | Jede aktuell gesperrte Adresse oder jeder Benutzer je Ebene (Web-Login, DJ-Einwahl, Firewall) mit **Unblock** und **Allow**. |

Die beiden Adresslisten beschreibt
[Benutzer und Rollen](./USERS_AND_ROLES.md) §8.

Was ein Neustart kostet:

| Dienst | Wirkung eines Neustarts |
|---|---|
| **Playout** | Der Sendeplan-Treiber startet neu; nicht während einer Live-Sendung.  Die Audio-Engine (Liquidsoap) ist ein eigener Dienst (RASTATIME-LIQUIDSOAP) und spielt weiter, was sie in der Warteschlange hat. |
| **Icecast** | Alle Hörer und alle Quellen werden getrennt; die Ausgänge verbinden sich in Sekunden neu, Hörer müssen neu verbinden. Nur in einem ruhigen Fenster. |
| **Apache** | Die Weboberfläche ist einige Sekunden nicht erreichbar. |
| **API**, **Worker**, **Analyzer** | Hintergrundarbeit pausiert kurz; keine Wirkung auf den Stream. |

> **Operator-Tipp.** Starten Sie nur den Dienst neu, der sich
> fehlverhält.  Die vollständige Reihenfolge steht in
> [`RESTART_ORDER`](../../operator/RESTART_ORDER.md).

**Preflight-Warnungen** sind kein Abschnitt dieser Seite: Sie erscheinen
als Banner auf jeder Seite.  Ein Beispiel: **Podcast-Download
fehlgeschlagen** (seit 08.10.2026) - schlägt ein automatischer oder
manueller Episoden-Download fehl, nennt eine Warnung den Podcast, die
Episode, die Zahl der Versuche, den letzten Versuch und den Grund
(HTTP-Code oder „API unreachable").  Sie verschwindet von selbst, wenn
der Download später gelingt oder der Podcast entfernt wird.  Prüfen Sie
den Feed und die Download-Adresse der Episode unter Bibliothek →
Podcasts.

---

## 4. Häufige Fragen

### „Ich habe eine Einstellung geändert, aber nichts passiert.“

Die meisten Einstellungen wirken sofort oder beim nächsten
Seitenaufruf.  Ausnahmen:

| Einstellung | Wirkt |
|---|---|
| Crossfades, Streams, Soundkarte | Wenn die Audiokette neu startet - automatisch in einem ruhigen Moment geplant; **Jetzt anwenden** in Einstellungen → Lokale Maschine erzwingt es. |
| Primär- und Sekundärfarbe, Logo, Favicon | Beim nächsten Seitenaufruf (F5). |
| Ihre eigene Sprache | Beim nächsten Seitenaufruf; der Anmeldebildschirm nutzt die Standardsprache. |
| Live Text Info, TuneIn | Beim nächsten Wechsel von Titel oder Quelle. |

### „Gibt es ein Tools-Menü, einen Log-Viewer oder eine DB-Konsole?“

Nein.  Wartungsskripte liegen auf dem Stationsrechner unter
`infra\scripts` (zum Beispiel
`infra\scripts\maintenance\rescan-playability.py`) und sind in der
Operator-Dokumentation beschrieben.  Die Logs liegen in
`C:\RASTATIME\logs`.

### „Wie sichere oder restauriere ich die Einstellungen?“

Einstellungen → **Backup** sichert die Datenbank (mit jeder
`cc_pref`-Zeile) und die Konfiguration; zur Wiederherstellung siehe
[Backup](./BACKUP.md).  `config/rastatime.conf` enthält Passwörter -
legen Sie die Datei nie unverändert in eine Versionsverwaltung.

### „Welche Einstellungen kann ein Program Manager öffnen?“

*Mein Profil*, *Show Templates*, *Auto DJ* und die Produzenten unter
*Archivierung*.  Alles andere unter
Einstellungen gehört den Admins.  Siehe [Benutzer und Rollen](./USERS_AND_ROLES.md) §1-§2.

---

## 5. Playout-Engine (Liquidsoap)

> **Einstellung auf Service-Ebene**, keine UI-Einstellung.  Der
> NSSM-Dienst RASTATIME-PLAYOUT kann `RASTATIME_PLAYOUT_ENGINE=liquidsoap`
> in seiner Umgebung tragen; das ist der einzige zulässige Wert.  Nur
> Operator; nicht in der Web-UI exponiert.

Seit dem 2026-09-10 ist Liquidsoap die **einzige** Playout-Engine.  Die
frühere mpv-Engine (mit ihren FFmpeg-Streamern für die Icecast-Ausgänge)
und der nie fertiggestellte VLC-Plan wurden aus dem Code entfernt,
nachdem Liquidsoap seit dem 2026-05-28 jeden Sendeplan-Typ (Dateien,
Webstreams, Line-Inputs, Aufnahme, DJ-Quellen) im Produktivbetrieb
getragen hatte.

Was Liquidsoap leistet:

- **Aufnahme** wird vom internen Audio-Bus erfasst (post-switch,
  post-crossfade, post-amplify) — bit-identisch mit dem, was die Hörer
  hören.  Format und Bitrate folgen Einstellungen → Lokale Maschine →
  Show Recording (Standard MP3 320 kbps).
- **Hörer-Erfahrung**: die Icecast-Mountpoints bleiben über Track-/
  Sendungswechsel offen — kein Reconnect, kein Zähler-Reset.
- **DJ-Quellen-Routing** nutzt Liquidsoaps `input.harbor` +
  `switch(...)` nativ — Master-/Show-DJ-Clients verbinden sich direkt
  mit dem von Liquidsoap verwalteten Harbor (standardmäßig Port 8001,
  siehe [Streams](./STREAMS.md)).

**Wenn der Dienst den Start verweigert** mit

```
CRITICAL __main__: RASTATIME_PLAYOUT_ENGINE='mpv' is not supported - Liquidsoap is the only playout engine since 2026-09-10 ...
```

nennt die Dienst-Umgebung noch die entfernte Engine: in der
NSSM-Umgebung von `RASTATIME-PLAYOUT` `RASTATIME_PLAYOUT_ENGINE=liquidsoap`
setzen (oder die Variable entfernen) und den Dienst erneut starten.
`RASTATIME_MPV_PATH` / `RASTATIME_MPV_LOG_LEVEL` werden ignoriert und
können entfernt werden.

**Der Engine-Start ist im Playout-Log sichtbar:**

```
INFO __main__: Playout engine: Liquidsoap (telnet target 127.0.0.1:1234).
```

---

## Wie es weitergeht

* Folgen Sie dem Link in der Tabelle von §1 zum eigenen Kapitel einer
  Einstellungsseite.
* [Benutzer und Rollen](./USERS_AND_ROLES.md) — wer welche Seite öffnen
  darf.
* [`docs/operator/INSTALL.md`](../../operator/INSTALL.md) — die bei der
  Installation vorgenommenen Einstellungen.

## 6. Alarme (seit 2026-11-03)

Settings → **Alerts** (Admins).  RASTATIME meldet, wenn die Sendung
stumm wird, ein Dienst nicht mehr antwortet oder eine Preflight-Warnung
erscheint, und gibt Entwarnung, sobald das Problem weg ist.

| Feld | Bedeutung |
|---|---|
| **Dead air after (seconds)** | So lange Stille auf dem Sendebus (unter -50 dB, die Stille-Ersatzquelle eingeschlossen) löst *Dead air* aus; 2 s Ton geben Entwarnung.  5 bis 3600, Standard 30.  Die Schwelle steckt in der Audio-Engine und greift mit ihrem nächsten geplanten Neustart. |
| **Reminder every (minutes)** | Solange ein Problem offen bleibt; 0 = keine Erinnerungen.  Höchstens 20 Nachrichten je Kanal und Stunde. |
| **Services** | Playout (vom API-Dienst überwacht), API, Apache, Icecast, Analyzer und Worker, minütlich geprüft; zwei Fehlversuche hintereinander lösen einen Alarm aus. |
| **Pre-flight warnings** | Jede Warnungsart des Dashboard-Banners löst einmal einen Alarm aus und gibt Entwarnung, wenn sie weg ist. |
| **Send alerts by e-mail** (Alarme per E-Mail senden) | Schaltet den E-Mail-Kanal ein (seit 2026-11-04; vorher ein Hauptschalter für beide Kanäle).  Die Felder des Kanals erscheinen, solange er angekreuzt ist; das Speichern lehnt ihn ohne Server, Absender und Empfänger ab. |
| **E-mail (SMTP)** | Server, Port, Verschlüsselung (STARTTLS, SSL/TLS, keine), Benutzername und Passwort (Anmeldung; das Passwort wird nie wieder angezeigt), Absender, Empfänger durch Komma getrennt.  Die Passwort-Zurücksetzen-Mail der Anmeldeseite ist davon unabhängig. |
| **Send alerts by Telegram** (Alarme per Telegram senden) | Schaltet den Telegram-Kanal ein (seit 2026-11-04), seine Felder erscheinen, solange er angekreuzt ist; das Speichern lehnt ihn ohne Bot-Token und Chat-ID ab. |
| **Telegram** | Bot-Token von @BotFather (nur schreibbar) und Chat-IDs durch Komma getrennt; der Bot muss Mitglied des Chats oder der Gruppe sein und eine Nachricht erhalten haben.  Eine Gruppen-ID beginnt mit Minus. |
| **Send test e-mail / message** | Nach dem Speichern: eine Testnachricht mit den gespeicherten Einstellungen, gesendet vom Playout-Dienst. |

Beide Kanäle aus: Es wird nichts gesendet, der Zustand wird trotzdem
verfolgt.  Vor 2026-11-04 gespeicherte Einstellungen gelten weiter: Ein
Kanal gilt als eingeschaltet, wenn der alte Hauptschalter an war und der
Kanal eingerichtet ist.  Playout- und API-Dienst lesen die Schalter je
Kanal nach ihrem nächsten Neustart; bis dahin folgen sie dem alten
Hauptschalter, der an ist, solange irgendein Kanal an ist.

Nachrichten sehen so aus: `[Sender] ALERT: Dead air` mit Zeit, Detail
und meldendem Dienst, `STILL OPEN` für Erinnerungen und `OK` für die
Entwarnung.  Geplante Neustarts der Audio-Engine (nächtlich,
Einstellungen) unterdrücken neue Alarme drei Minuten lang.

Noch nicht abgedeckt: ein toter Uplink (kein Kanal verlässt das
Studio), eine langsame statt ausgefallene Weboberfläche sowie Signal,
WhatsApp oder SMS (siehe BACKLOG).
