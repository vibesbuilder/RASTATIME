# Bibliothek

> **Wo Sie sich im Handbuch befinden.** Dies ist eines der
> **Inhalt und Bibliothek**-Kapitel. Für detaillierte
> Informationen pro Eingabetyp siehe auch
> [Webstreams](./WEBSTREAMS.md) und [Line-In](./LINE_IN.md),
> die als eigene Bibliotheks-Items verfolgt werden.

Die **Bibliothek** ist das Inventar jedes Audiomaterials,
das RASTATIME auf Sendung bringen kann. Sie hat fünf
Item-Typen:

| Typ | Was es ist | Wo die Zeilen leben |
|---|---|---|
| **Track** | Eine einzelne Audiodatei (MP3, FLAC, OGG, WAV, AAC). | `cc_files` |
| **Smart Block** | Eine *Abfrage* — "wähle N Tracks, wo Genre = Pop und BPM > 100", ausgewertet zur Build-Zeit. | `cc_block` + `cc_blockcontents` (Kriterien) |
| **Playlist** | Eine geordnete Liste von Items: Tracks, Smart Blocks, Webstreams oder Line-Ins. | `cc_playlist` + `cc_playlistcontents` |
| **Webstream** | Eine URL, die auf eine andere Icecast- / Shoutcast- / einfache HTTP-Audioquelle zeigt. | `cc_webstream` |
| **Line-In** | Ein benannter Live-Audio-Eingang auf der Operator-Maschine. | `rastatime_linein` |

Aus der Bibliothek ziehen Sie beim Füllen einer Sendung.

---

## 1. Die Bibliotheksseite

Bibliothek → öffnet die Tabellenansicht mit einer Zeile pro
Item.

```
  ┌─────────────────────────────────────────────────────────────────┐
  │  Bibliothek                                         ▼  Hochladen │
  ├─────────────────────────────────────────────────────────────────┤
  │  Filter:  [Typ ▾]  [Ersteller ▾]  [Genre ▾]  [Länge ▾]          │
  │  Suche:   [_______________________________]                     │
  ├──┬──────────┬────────────────┬──────────┬──────────┬─────────┬──┤
  │  │ Typ      │ Titel          │ Ersteller│ Länge    │ Besitzer│  │
  ├──┼──────────┼────────────────┼──────────┼──────────┼─────────┼──┤
  │ ◯│ Track    │ Song A         │ Artist 1 │ 03:42    │ admin   │  │
  │ ◯│ Track    │ Song B         │ Artist 2 │ 04:15    │ admin   │  │
  │ ◯│ Smart B. │ Hot pop        │ —        │ ~30:00   │ admin   │  │
  │ ◯│ Playlist │ Morgensendung  │ —        │ 60:00    │ host1   │  │
  │ ◯│ Webstream│ BBC Radio 1    │ —        │ 60:00    │ admin   │  │
  │ ◯│ Line-In  │ Studio-Mixer   │ —        │ ∞        │ admin   │  │
  └──┴──────────┴────────────────┴──────────┴──────────┴─────────┴──┘
```

### Filter-Chips

Die Chips über der Tabelle schränken die sichtbaren Zeilen
ein. Sie kombinieren sich mit **UND**: Setzt man *Typ =
Track* und *Genre = Pop*, werden nur Pop-Tracks gezeigt.
Löschen Sie jeden Chip mit seinem **×**.

| Chip | Wofür gefiltert wird |
|---|---|
| **Typ** | Track / Smart Block / Playlist / Webstream / Line-In. Das fünf-farbige Chip-Set in der Spaltenüberschrift spiegelt dies wider. |
| **Ersteller** | Der Metadaten-Ersteller (Künstler) des Tracks, nicht der Upload-Besitzer. |
| **Genre** | Metadaten-Genre-Tag. |
| **Länge** | Grobe Buckets (< 30 s, 30 s – 2 min, 2 – 10 min, > 10 min, ∞). |
| **Besitzer** | Der RASTATIME-Benutzer, der das Item importiert hat. DJs sind auf ihre eigenen Items beschränkt; Admins sehen alles. |

> **Operator-Tipp.** Die Chips färben auch die Zeilen-Badges
> ein. Nach ein paar Wochen mit demselben Set lesen Sie die
> *Typ*-Spalte nicht mehr und lesen nur die Farben: blau =
> Track, grün = Line-In, gelb = Block, orange = Stream,
> lila = Playlist.

### Freitext-Suche

Die **Suche**-Box läuft über **Titel, Ersteller, Album,
Genre, Dateiname** bei Tracks; **Name** bei Blocks /
Playlists / Webstreams / Line-Ins. Sie verwendet einen
Substring-Match — eingeben von `bowie` matched "David
Bowie", "BOWIE" und "bowie-heroes.mp3".

> **Wie es unter der Haube funktioniert.** Die Suche läuft
> serverseitig über `LibraryController::contentsFeedAction`.
> Das DataTable-Widget sendet den Suchbegriff + den
> aktuellen Chip-Zustand als URL-Parameter; der Controller
> baut eine PostgreSQL-`ILIKE`-Abfrage gegen die relevanten
> Spalten zusammen. Auch die Paginierung ist serverseitig,
> sodass eine Bibliothek mit 100.000 Tracks nicht 100.000
> Zeilen in den Browser lädt.

### Spalten sortieren

Klicken Sie auf eine Spaltenüberschrift zum aufsteigenden
Sortieren; klicken Sie erneut für absteigend. Die
Standard-Sortierung ist **Titel, aufsteigend**.

---

## 2. Tracks

### Tracks importieren

Drei Wege:

#### 2.1 Browser-Upload (einmalig)

Bibliothek → **Hochladen** → Dateien auf den Upload-Bereich
ziehen oder anklicken zum Auswählen.

| Feld | Hinweise |
|---|---|
| **Datei** | Eine von: MP3, FLAC, OGG, WAV, AAC, M4A. |
| **Besitzer** | Standardmäßig Sie. Admins können überschreiben. |

Der Upload startet den Analyzer (Metadaten +
Abspielbarkeits-Prüfung) und fügt die Zeile zur Bibliothek
hinzu. Große Dateien können einige Sekunden dauern, bis sie
erscheinen, weil die Abspielbarkeits-Dekodierung die gesamte
Datei von Anfang bis Ende prüft.

#### 2.2 Lokaler Import-Ordner (Batch)

Konfigurieren Sie einmalig Einstellungen → **Lokale Maschine**
→ **Lokaler Import-Ordner**. Dann legen Sie Dateien in
dieses Verzeichnis auf dem Server; sie erscheinen beim
nächsten Analyzer-Poll (standardmäßig alle 60 s) in der
Bibliothek. Unterordner werden rekursiv durchsucht. Siehe
[Lokale Maschine](./LOCAL_MACHINE.md).

> **Operator-Tipp.** Verwenden Sie den lokalen Import-Ordner
> für jeden Batch über einem Dutzend Dateien. Der
> Browser-Uploader hält die Anfrage offen, bis der Analyzer
> fertig ist; ein 200-Datei-Batch kann die Anfrage viele
> Minuten offen halten, und der Operator gibt auf.

#### 2.3 Podcast-Abonnement (wiederkehrend)

Einstellungen → **Podcasts** → **Abonnieren**. Fügen Sie
eine RSS-Feed-URL ein, optional einen Standard-Track-Typ,
eine Auto-Ablauf-Richtlinie (Episoden älter als N Tage
löschen). Neue Episoden werden vom Worker-Job-Runner
heruntergeladen und genau wie manuelle Uploads als Tracks
importiert.

> **Wie es unter der Haube funktioniert.** Podcast-Fetching
> basierte früher auf Celery; auf RASTATIME (Windows) läuft
> es im `PodcastFetchJob` des Dienstes `RASTATIME-WORKER`,
> der im konfigurierten Intervall (standardmäßig 30 Min)
> abgefragt wird. Siehe ARCHITECTURE §16 für den neuen
> Threading-basierten Runner.

### Track-Metadaten bearbeiten

Klicken Sie auf eine Track-Zeile → **Metadaten bearbeiten**
im Aktionsmenü der Zeile.

| Feld | Wo es endet |
|---|---|
| **Titel** | `cc_files.track_title` |
| **Ersteller (Künstler)** | `cc_files.artist_name` |
| **Album** | `cc_files.album_title` |
| **Genre** | `cc_files.genre` |
| **Jahr** | `cc_files.year` |
| **BPM** | `cc_files.bpm` |
| **Track-Typ** | `cc_files.track_type` — von Smart-Block-Filtern verwendet |
| **Cue In / Out** | `cc_files.cuein` / `cueout` — Anfang / Ende ohne Neu-Kodierung trimmen |
| **Fade In / Out** | `cc_files.fadein` / `fadeout` |
| **Replay Gain** | `cc_files.replay_gain` — von der Playout-Engine zur Pegel-Normalisierung verwendet |

> **Operator-Tipp.** Setzen Sie **Cue In** auf
> Radio-Promos / Stings, die ein paar Sekunden Stille am
> Anfang haben. Der Cue-Punkt ist ein zerstörungsfreier
> Trim — die Datei auf der Festplatte bleibt unverändert,
> aber die Wiedergabe beginnt am Cue.

### Einen Track löschen

Zeile → **Löschen**. Der Track wird aus der Bibliothek
entfernt *und* aus jeder Playlist, in der er Teil war. Wenn
der Track gerade in einer kommenden Sendung eingeplant ist,
erhalten Sie eine Warnung und können abbrechen oder
fortfahren (die Schedule-Zeilen werden ebenfalls entfernt).

> **Wie es unter der Haube funktioniert.** Löschen entfernt
> die `cc_files`-Zeile und alle `cc_playlistcontents` /
> `cc_schedule`-Zeilen, die darauf verweisen (CASCADE). Die
> Datei auf der Festplatte wird nach
> `C:\rastatime\media\.trash\` verschoben statt entfernt,
> sodass ein Operator, der versehentlich löscht, für 7 Tage
> wiederherstellen kann. Siehe
> [`docs/operator/BACKUP.md`](../../operator/BACKUP.md) für
> den Trash-Cleanup-Cron.

---

## 3. Smart Blocks

Ein **Smart Block** ist eine Abfrage. Wenn der Block in
einer Sendung eingeplant ist, wird die Abfrage zur Build-Zeit
ausgewertet und in eine konkrete Menge von Tracks expandiert.
Smart Blocks sind, wie Sie Sendungen bauen, die sagen "spiele
30 Minuten Upbeat-Pop-Tracks von nach 2010", ohne jeden Track
manuell auszuwählen.

### Einen Smart Block erstellen

Bibliothek → **+ Neu** → **Smart Block**.

| Feld | Bedeutung |
|---|---|
| **Name** | Sichtbar in der Bibliothek und im Kalender. |
| **Typ** | **Statisch** — wählt einmalig zum Erstellungszeitpunkt; die Menge ändert sich nie. **Dynamisch** — wählt jedes Mal neu, wenn der Block eingeplant wird. |
| **Kriterien** | Zeilen hinzufügen: *Künstler enthält "Bowie"*, *BPM zwischen 100 und 130*, *Genre ist Pop* usw. Jede Zeile wird UND-kombiniert mit den anderen; eine ODER-Gruppe kann durch eine verschachtelte Gruppe erstellt werden. |
| **Begrenzen auf** | Eines von: **Anzahl Tracks** (z.B. 10), **Dauer in Zeit** (z.B. 30:00), **Verbleibende Zeit in der Sendung** (lässt den Smart Block exakt bis zum Ende der Sendung füllen). |
| **Sortieren** | Zufällig / neueste zuerst / nach Künstler / nach Spielzahl / etc. |

> **Operator-Tipp.** Das **"Verbleibende Zeit in der
> Sendung"**-Limit ist das nützlichste für autoloading
> Playlists. Kombiniert mit einer Intro- + Outro-Playlist
> können Sie eine einstündige Sendung bauen, indem Sie ein
> 30-s-Intro + einen `*`-Smart-Block + ein 60-s-Outro
> stempeln, und der Auto-Build wird die richtige Anzahl von
> Tracks dazwischen sandwichen.

### Warum ein Smart Block weniger Tracks zurückgeben kann als gefragt

Smart Blocks respektieren den **Bibliotheks-Scope** des
Operators:

- Der besitzende DJ sieht nur seine eigenen Tracks.
- Ein Program Manager sieht die gesamte Bibliothek.

Wenn Sie "Begrenzen auf 10 Tracks" setzen, aber nur 4 Tracks
in der Bibliothek die Kriterien erfüllen, erhalten Sie 4.
Der Block scheitert nicht.

> **Wie es unter der Haube funktioniert.** Kriterien sind
> in `cc_blockcriteria` gespeichert. Zur Build-Zeit baut
> `BlockExpander.expand()` ein PostgreSQL-`SELECT … WHERE …
> LIMIT …` über `cc_files` zusammen. Time-remaining-Limits
> werden über die `getSecondsRemaining()`-Methode der
> Sendungsinstanz in eine Dauer-Obergrenze umgerechnet.
> Siehe ARCHITECTURE §23.19 für die Outro-Reserve-Interaktion
> mit Time-remaining-Smart-Blocks.

### Einen Smart Block bearbeiten

Klicken Sie den Block → **Bearbeiten**. Das Ändern von
Kriterien ändert *nicht* rückwirkend Sendungen, die bereits
gebaut wurden — nur zukünftige Auswertungen.

---

## 4. Playlists

Eine **Playlist** ist eine geordnete Liste von Items, wobei
jedes Item ein Track, ein Smart Block, ein Webstream oder
ein Line-In ist. Playlists sind die Bausteine des
Sendungsinhalts.

### Eine Playlist erstellen

Bibliothek → **+ Neu** → **Playlist**.

Der Playlist-Editor öffnet sich mit der Playlist links und
der Bibliothek rechts. Ziehen Sie Bibliotheks-Items auf die
Playlist; ordnen Sie per Drag-and-Drop um. Setzen Sie
Crossfades und Cue-Punkte pro Item, falls nötig.

| Item-Typ-Verhalten |  |
|---|---|
| **Track** | Wird abgespielt wie konfiguriert (Cue In / Out, Fade In / Out). |
| **Smart Block** | Expandiert zur Build-Zeit, nicht zur Playlist-Bearbeitungszeit. |
| **Webstream** | Wird für die konfigurierte Dauer der Playlist-Zeile abgespielt (standardmäßig 60 min, kann überschrieben werden). Siehe [Webstreams](./WEBSTREAMS.md). |
| **Line-In** | Wird für die konfigurierte Dauer der Playlist-Zeile abgespielt. Siehe [Line-In](./LINE_IN.md). |

### Standardlänge

Jede Playlist hat eine **Standardlänge**, die als nominale
Dauer der Playlist in der Bibliothek angezeigt wird. Für
eine reine Track-Playlist ist dies die Summe der
Track-Dauern. Für eine Playlist, die Smart Blocks /
Webstreams / Line-Ins enthält, ist die Standardlänge das,
was *abspielen würde*, wenn jedes variable Item für seine
konfigurierte Dauer laufen würde.

### Eine Playlist in einer Sendung verwenden

Zwei Pfade:

1. **Einmalig**: Ziehen Sie die Playlist auf eine leere
   Sendung im Show-Builder. Die Items der Playlist werden am
   Drag-Punkt in den Sendeplan *abgeflacht*. Die
   ursprüngliche Playlist ist nicht mit der Sendung
   verknüpft — das Bearbeiten der Playlist später beeinflusst
   den Sendeplan nicht.

2. **Autoloading**: Hängen Sie die Playlist an die
   Sendungsdefinition im Abschnitt **Autoloading Playlist**
   des Sendungs-Bearbeitungsformulars an. Jede zukünftige
   Instanz der Sendung wird die Items der Playlist
   automatisch in ihren Sendeplan gebaut bekommen. Das
   Bearbeiten der Playlist *beeinflusst* zukünftige Builds.
   Siehe [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md).

> **Operator-Tipp.** Eine einzelne Playlist kann
> Doppelfunktion erfüllen: Ziehen Sie sie auf eine
> Ad-hoc-Sendung und hängen Sie sie auch als autoloading
> Playlist für eine wiederkehrende Sendung an. Die beiden
> Verwendungen sind unabhängig.

---

## 5. Webstreams und Line-Ins als Bibliotheks-Items

Sowohl [Webstreams](./WEBSTREAMS.md) als auch
[Line-Ins](./LINE_IN.md) erscheinen in der Bibliothek und
verhalten sich wie Tracks, wenn sie eingeplant werden: auf
eine Sendung oder in eine Playlist auf genau die gleiche
Weise ziehen.

Ihre Feature-spezifischen Kapitel behandeln die Spezifika
(URL-Format, Authentifizierung, Geräte-Probing usw.). Der
Bibliotheks-Einstiegspunkt ist derselbe wie für jedes andere
Item.

---

## 6. Massenaktionen

Markieren Sie das Kontrollkästchen am Anfang jeder Zeile und
verwenden Sie dann die Symbolleiste, die am unteren Rand der
Tabelle erscheint:

| Aktion | Effekt |
|---|---|
| **Zu Playlist hinzufügen** | Die ausgewählten Zeilen an eine bestehende Playlist Ihrer Wahl anhängen. |
| **Löschen** | Die ausgewählten Zeilen löschen. Gleiche Confirm-on-Scheduled-Use-Semantik wie beim Einzelzeilen-Löschen. |
| **Metadaten bearbeiten** | Einen Batch-Bearbeitungs-Dialog öffnen. Gilt nur für Tracks. |
| **Besitz übertragen** | Besitz neu zuweisen (nur Admin / Super Admin). Verwendet, wenn ein DJ ausscheidet und seine Dateien an das Stations-Konto übergehen sollen. |

---

## 7. Häufig gestellte Fragen

### "Ich habe einen Track hochgeladen, und er ist nie aufgetaucht."

Prüfen Sie den Upload-Status-Badge:

- **Gelb (Warnung)**: Die Datei wurde importiert, aber die
  Abspielbarkeits-Prüfung erzeugte Warnungen (typischerweise
  ein schlecht codiertes MP3 mit Trailing-Frame-Problemen).
  Die Datei *wird* abspielen; Sie können die Warnung
  ignorieren.
- **Rot (Fehlgeschlagen)**: Die Datei ist nicht abspielbar
  oder der Metadaten-Parser ist abgestürzt. Die Zeile wird
  aus der Bibliotheksliste unterdrückt (Filter-Chip
  **Fehlgeschlagene Importe** auf der Upload-Status-Seite
  zeigt sie).
- **Kein Badge aber auch keine Zeile**: Der Analyzer-Dienst
  läuft nicht. Prüfen Sie `Get-Service RASTATIME-ANALYZER`.

### "Warum gibt mein Smart Block jedes Mal dieselben Tracks zurück?"

Sie haben wahrscheinlich **Statisch** statt **Dynamisch**
gewählt. Bearbeiten Sie den Block und ändern Sie den Typ;
der nächste Build wird neu abfragen.

### "Kann ich eine Ordnerstruktur importieren und Unterordnernamen erhalten?"

Der lokale Import-Ordner behält Unterordnernamen als
**Album**-Feld der importierten Tracks bei, wenn kein
ID3-Album-Tag gesetzt ist. Das ist das häufigste
Operator-Muster für ein Long-Tail-Musikarchiv.

### "Was ist die maximale Dateigröße?"

Der Browser-Uploader ist durch Apaches `LimitRequestBody`
begrenzt — standardmäßig 100 MB. Der lokale Import-Ordner
hat kein praktisches Limit (Dateien werden von der Platte
gelesen, nicht POSTet).

---

## Wohin als Nächstes

* [Kalender](./CALENDAR.md) — wie Sie Bibliotheks-Items auf
  Sendung bringen.
* [Sendungs-Vorlagen](./SHOW_TEMPLATES.md) — Sendungs-
  Einstellungen wiederverwenden.
* [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) —
  Sendungen aus einer Playlist sich selbst füllen lassen.
* [Webstreams](./WEBSTREAMS.md) und [Line-In](./LINE_IN.md)
  für die typenspezifischen Details der beiden neueren
  Item-Typen.
