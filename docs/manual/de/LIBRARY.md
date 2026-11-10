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
| **Track** | Eine einzelne Audiodatei (MP3, M4A, OGG, Opus, ...; WAV und FLAC werden beim Import standardmäßig in MP3 umgewandelt). | `cc_files` |
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

> **Restzeit und Crossfades (seit 2026-10-06).** Musik-Zeilen überlappen
> sich um ihren Crossfade (Hauswert 3 s bzw. der Wert des Track-Typs;
> Jingles 0), darum ist die Restzeit einer Sendung die *ausgelegte* Zeit:
> vom Ende der letzten Zeile bis zum Sendungsende – die Zahl in der
> Fußzeile des Show Builders. Ein Smart Block mit „Verbleibende Zeit in
> der Sendung" wird gegen diese Zeit gewählt, zwischen seinen echten
> Nachbarn, sodass die letzte Zeile bis auf etwa eine Sekunde am
> Sendungsende endet (der Löser des Blocks ist zufällig; der Pool
> entscheidet, was möglich ist). Ein Block mit *Dauer in Zeit* wird
> genauso gewählt (Operator-Entscheidung 2026-10-06): 12 Minuten sind 12
> Minuten **Sendezeit**, nicht Titelsumme – eine StationID nach drei
> solchen Blöcken sitzt bei 12:00, 24:xx und 36:xx der Stunde. Ein Jingle
> zwischen zwei Musiktiteln kostet seine eigene Länge plus die 3 s
> Überlappung, die er unterbricht.

### Freitext-Suche

Die **Suche**-Box läuft über **Titel, Ersteller, Album,
Genre, Dateiname** bei Tracks; **Name** bei Blocks /
Playlists / Webstreams / Line-Ins. Sie verwendet einen
Substring-Match — eingeben von `bowie` matched "David
Bowie", "BOWIE" und "bowie-heroes.mp3".

**Anzeige für aktive Filter (seit 2026-10-09).** Solange Suchtext
oder ein Feld der erweiterten Suche gesetzt ist, erhält die Suchbox
einen Rahmen in der Akzentfarbe und zeigt rechts, wie viele Einträge
der gewählten Art passen („13 von 11.108 Titeln", „0 von 32 Smart
Blöcken"; seit 2026-10-18 nennt die Zahl die Art - Titel, Playlisten,
Smart Blöcke, Webstreams, Podcasts, Line-Eingänge). Das **×** neben
dieser Zahl leert den Suchtext und alle Felder der erweiterten Suche
in einem Zug.

**Podcasts (seit 2026-10-21).** Die Podcast-Liste hat dasselbe
Suchfeld: Es durchsucht **Titel** und **Creator** des Podcasts ohne
Rücksicht auf Groß-/Kleinschreibung und zeigt „X of N podcasts" und das
**×** genauso.  Der Pfeil der erweiterten Suche ist dort ausgeblendet -
er gehört zu den anderen Arten.

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

### Tabellen-Layout

Ziehen Sie eine Spalte an ihrer Überschrift, um sie zu
verschieben; die Schaltfläche **Spalten** (Listen-Symbol) über
der Tabelle blendet Spalten ein und aus, die Auswahl
**… anzeigen** darunter legt die Zeilen pro Seite fest.
RASTATIME merkt sich dieses Layout — Spaltenreihenfolge,
sichtbare Spalten, Zeilen pro Seite und Sortierung — **pro
Benutzer auf dem Server**; es folgt Ihnen also in jeden Browser
und auf jeden Rechner. Seit 2026-10-24 werden die **sichtbaren
Spalten je Medientyp** gemerkt: Tracks, Playlists, Smart Blocks,
Webstreams und Line-Ins haben jeweils ihren eigenen Satz, und die
Schaltfläche **Spalten** bearbeitet immer den Satz des gerade
geöffneten Reiters. Ein noch nie angepasster Reiter beginnt mit
einer sinnvollen Vorgabe (Tracks: Cover, Titel, Interpret, Typ,
Genre, Länge, Hochgeladen; Playlists und Smart Blocks: Titel,
Beschreibung, Länge, Ersteller, Zuletzt geändert; Webstreams:
Titel, Beschreibung, Website, Länge, Ersteller, Zuletzt geändert;
Line-Ins: Titel, Beschreibung, Länge, Zuletzt geändert). Die
Track-Tabelle des Dashboards und die
im Kalender-Dialog **Sendungsinhalte verwalten** haben je ein
eigenes Layout (der Dialog hat keine Spalte *Actions*); die
Tabelle *Scheduled Shows* daneben teilt ein Layout zwischen
beiden Orten. Suchen und die aktuelle Seite werden nicht
gemerkt — die Tabelle öffnet immer auf Seite 1. Beim Scrollen
durch die Zeilen bleiben Suchzeile, Spaltenüberschriften und
Seitenleiste sichtbar.

---

## 2. Tracks

### Tracks importieren

Drei Wege:

#### 2.1 Browser-Upload (einmalig)

Bibliothek → **Hochladen** → Dateien auf den Upload-Bereich
ziehen oder anklicken zum Auswählen.

| Feld | Hinweise |
|---|---|
| **Datei** | Eine von: MP3, M4A, MP4, AAC, OGG, OGA, Opus, FLAC, WAV, MP2, MP1, AU - seit 2026-10-14 dieselbe Liste, die der lokale Import-Ordner und der FTP-Import annehmen. Verlustfreie Dateien werden beim Import standardmäßig in MP3 umgewandelt (siehe *Dateiformate beim Import* unten). |
| **Besitzer** | Standardmäßig Sie. Admins können überschreiben. |

Der Upload startet den Analyzer (Metadaten +
Abspielbarkeits-Prüfung) und fügt die Zeile zur Bibliothek
hinzu. Große Dateien können einige Sekunden dauern, bis sie
erscheinen, weil die Abspielbarkeits-Dekodierung die gesamte
Datei von Anfang bis Ende prüft.

> **Wo die Datei landet (seit 2026-10-24).**  Der Analyzer legt jeden
> Track unter `imported/<Interpret>/<Album>/` in der Bibliothek ab
> (Interpret und Album wie getaggt; ohne Album-Tag nur
> `imported/<Interpret>/`).  Eine Datei **ohne Interpreten-Tag**
> kommt nach `imported/tagless/` - vor dem 2026-10-24 lagen solche
> Dateien direkt in `imported/`.  Der Ordner ist nur der Ablageort;
> die Bibliothek zeigt den Track in jedem Fall nach seinen Tags.
> Taggen Sie die Datei also vorher, wenn sie unter ihrem Interpreten
> abgelegt werden soll.
>
> **Cover.**  Ein eingebettetes Cover wird als fünf JPG-Größen
> (32 bis 512 px) unter `imported/artwork/` gespeichert; mehr wird
> seit dem 2026-10-24 dafür nicht geschrieben.  Die kleinen
> Cover-Vorschauen in Bibliothek und Editor entstehen aus diesen JPGs,
> wenn die Seite sie anfordert.

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
> die Episode synchron in der API (ausgelöst aus der
> Web-Oberfläche oder der Feed-Prüfung), die Datei und ihren
> Bibliothekseintrag direkt schreibt.
>
> **Episoden-Dateien (seit 17.09.2026)** landen in einem Ordner
> pro Podcast innerhalb der Bibliothek: `imported/<Podcast-Name>/`.
> Wird ein Podcast umbenannt, beginnt für künftige Episoden ein
> neuer Ordner; vorhandene Dateien bleiben, wo sie sind.

### Dateiformate beim Import (seit 2026-10-14)

Ganz gleich, auf welchem Weg ein Track ankommt - Upload, lokaler
Import-Ordner, FTP-Import oder Massenimport -, der Analyzer prüft das
Audio in der Datei (nicht ihre Endung), bevor er sie ablegt:

- **MP3, MP2, MP1, AAC in M4A / MP4, OGG Vorbis und Opus** werden
  unverändert importiert und nie neu kodiert.
- **Rohes AAC (`.aac`)** wird immer ohne Neukodierung in eine `.m4a`
  umverpackt: Eine rohe AAC-Datei hat keinen Index, ihre Länge lässt
  sich nur schätzen, und sie kann keine Tags tragen.
- **Verlustfreies Audio** - WAV, FLAC, AU, Apple Lossless in M4A -
  wird in **MP3 mit 320 kbit/s** umgewandelt, solange Einstellungen →
  **Lokale Maschine** → **Importformat** eingeschaltet ist (der
  Standard).  Das verlustfreie Original wird nicht aufbewahrt; Tags,
  Expiry- und Enable-Datum, das Land und ein eingebettetes Cover werden
  übernommen.
  Schlägt eine Umwandlung fehl, wird das Original unverändert
  importiert.  Einzelheiten: [Lokale Maschine](./LOCAL_MACHINE.md),
  Abschnitt 5.
- **Tags werden aus jedem Format gelesen.**  Neben ID3 in MP3-Dateien
  liest der Analyzer die Tags in WAV-Dateien (ID3-Block und RIFF
  INFO), die Kommentare von FLAC-, OGG- und Opus-Dateien und die Felder
  von M4A-Dateien, einschließlich Beschreibung / Kommentar, der Daten und des
  Landes (nächster Abschnitt).  Vor dem 2026-10-14 wurden die Tags
  in WAV-Dateien nicht gelesen, und eine rohe `.aac` mit ID3-Tag
  scheiterte beim Import.

Podcast-Episoden gehören nicht dazu: Sie werden direkt in die
Bibliothek heruntergeladen (Abschnitt 2.3) und behalten ihr Format.
Seit 2026-10-24 wird jede heruntergeladene Episode dennoch direkt
nach dem Download auf **Lautheit gemessen** (EBU R128), damit das
Playout ihre echte Titelverstärkung anwendet statt einer Näherung.
Episoden von vor diesem Datum holen Sie mit **Settings → Streams →
Measure loudness** nach; der Knopf misst nur Dateien ohne Werte.

### Daten und Land aus den Tags (seit 2026-11-08)

Drei Felder des Track-Editors werden beim Import aus den Tags der Datei
gefüllt - ID3-`TXXX`-Frames in MP3-Dateien, und dieselben Namen als
Kommentare von FLAC-, OGG- und Opus-Dateien, als Freiform-Felder in
M4A-Dateien oder im ID3-Block einer WAV-Datei:

| Tag-Name | Feld | Format |
|---|---|---|
| `Expiry` oder `Expiry Date` | **Ablaufdatum** | `2026-11-08` oder `20261108` |
| `Enable Date` oder `Enabled From` | **Aktiv ab** | `2026-11-08` oder `20261108` |
| `Country` | **Land** | freier Text wie im Tag, z. B. `Austria` |

Groß- und Kleinschreibung, Leerzeichen, Unter- und Bindestriche im
Tag-Namen spielen keine Rolle (`EXPIRY_DATE` ist `Expiry Date`).  Ein
Datum in einem anderen Format wird übergangen; das Analyzer-Log nennt
die Datei.  Ein erreichtes Ablaufdatum oder ein noch in der Zukunft
liegendes Aktivierungsdatum deaktiviert den Track sofort.  Das Land
wird nur gefüllt, wenn der Track noch keines hat.

**Tags neu einlesen** übernimmt das Land ebenfalls aus der Datei (eine
Datei ohne den Tag leert es), aber nie die beiden Daten: Ein in
RASTATIME gesetztes Datum bleibt.  Vor dem 2026-11-08 importierte
Tracks erhalten ihr Land einmalig aus ihren Tags mit
`manage.py backfill_country --yes` auf dem Studiorechner; der Befehl
füllt nur leere Länder und zählt ohne `--yes` nur.

### Track-Typ aus dem Media-Type-Tag (seit 2026-11-09)

Eine Datei kann ihren Track-Typ selbst mitbringen: Nennt ihr Tag
**Media Type** einen Track-Typ, den RASTATIME kennt, erhält der Track
beim Import genau diesen Typ.

- **Wo der Tag steht:** im ID3-Standardframe `TMED` (Media Type) in
  MP3-Dateien; `MEDIATYPE` - oder `MEDIA`, wie MusicBrainz Picard ihn
  schreibt - in FLAC-, OGG- und Opus-Kommentaren und
  M4A-Freiform-Feldern; `TMED` im ID3-Block einer WAV-Datei.  Das
  Genre (`TCON`) bleibt das Genre.
- **Was drinstehen muss:** der Code oder der Name eines Track-Typs,
  Groß- und Kleinschreibung egal - `Jingles`, `JINGLES` und `jngl`
  meinen alle *Jingles*.  Es zählen nur die Typen, die der
  Upload-Dialog anbietet (Einstellungen → Track-Typen, *Visibility*
  aktiviert).
- **Wogegen er gewinnt:** gegen den im Upload-Dialog gewählten Typ und
  gegen den Track Type Upload Default (den auch der Import-Ordner
  verwendet).
- **Cue-Punkte folgen ihm:** Ob der Import Cue-Punkte erkennt, ist
  eine Einstellung des Track-Typs (*Analyze cue points*); mit dem Tag
  entscheidet der Typ aus dem Tag.
- **Alles andere wird verworfen:** Ein leerer Tag, ein falsch
  geschriebener Typ (`Jingle`) oder ein Wert wie `CD` oder
  `Digital Media`, den MusicBrainz in denselben Frame schreibt, ändert
  nichts; der Track erhält den Typ, den er ohne den Tag bekäme, und
  das Analyzer-Log nennt die Datei.

**Tags neu einlesen** setzt den Typ ebenfalls, wenn der Tag einen
bekannten Typ nennt; ein unbekannter oder fehlender Tag lässt den Typ,
wie er ist.  Eine verlustfreie Datei, die in MP3 umgewandelt wird,
behält den Tag.  Am 2026-11-09 trug kein Track der Bibliothek diesen
Tag; bestehende Tracks sind also unverändert.

### Track-Metadaten bearbeiten

Klicken Sie auf eine Track-Zeile → **Metadaten bearbeiten**
im Aktionsmenü der Zeile.  Wird das Speichern abgelehnt (etwa ein Datum im falschen Format), bleibt der Editor offen und nennt den Grund über den Feldern (seit 2026-11-08).

| Feld | Wo es endet |
|---|---|
| **Titel** | `cc_files.track_title` |
| **Ersteller (Künstler)** | `cc_files.artist_name` |
| **Album** | `cc_files.album_title` |
| **Genre** | `cc_files.genre` |
| **Jahr** | `cc_files.year` |
| **Land** (seit 2026-11-08) | `cc_files.country` - freier Text, beim Import aus dem Tag `Country`; das Feld schlägt die schon verwendeten Länder vor. Grundlage von Analytics → [Music by Country](./ANALYTICS.md); Smart Blocks können danach filtern (Kriterium *Land*). Library-Spalte *Land* (standardmäßig ausgeblendet, durchsuchbar). |
| **BPM** | `cc_files.bpm` |
| **Track-Typ** | `cc_files.track_type` — von Smart-Block-Filtern verwendet |
| **Cue In / Out** | `cc_files.cuein` / `cueout` — Anfang / Ende ohne Neu-Kodierung trimmen. Seit dem 30.09.2026 bleiben die Werte innerhalb der Datei: ein Cue Out hinter der Dateilänge wird auf die Länge gekappt, ein Cue In unter null wird null. Eine Änderung wird in die Zeilen der kommenden Sendungen kopiert, die den Track enthalten (bereits gestartete Zeilen bleiben unberührt), und diese Sendungen werden neu ausgelegt - kein Neu-Befüllen nötig. |
| **Fade In / Out** | `cc_files.fadein` / `fadeout` |
| **Replay Gain** | `cc_files.replay_gain` — von der Playout-Engine zur Pegel-Normalisierung verwendet |
| **Play Count** | Bibliotheksspalte (standardmäßig ausgeblendet, Spaltenwähler), nur lesend: wie oft der Titel gesendet wurde - ein Zähler pro Zeile des Sendeprotokolls, dieselbe Zahl wie Sendeprotokoll → File Summary. Sortierbar; die erweiterte Suche nimmt einen Bereich. Seit 2026-10-07. |
| **ID** | Bibliotheksspalte (standardmäßig sichtbar, Spaltenwähler), nur lesend: die Datenbank-ID der Datei, dieselbe Nummer, die REST-API und Playout-Logs verwenden. Nur Dateien tragen sie - Playlisten, Smart Blocks und Webstreams haben eigene Nummernkreise und zeigen eine leere Zelle. Sortierbar; die erweiterte Suche nimmt einen Bereich. Seit 2026-10-16. |
| **Teaser** / **Teaser für Sendungen**, **Teaser-Typ** | Die Sendung(en), die ein Jingle ankündigt, und wie (Showteaser, Tagesteaser „heute", Tagesteaser „morgen"); zwei Felder des Track-Editors und der Mehrfach-Bearbeitung, in der Bibliotheksspalte *Teaser* (standardmäßig ausgeblendet, durchsuchbar) als `Sendungsname · today`. Smart Blocks wählen die passenden Jingles mit dem Kriterium *Teaser: passt zum Sendeplan* - siehe [Teaser-Automatik](./TEASERS.md). Seit 2026-10-16. |
| **Crossover** | Wie dieser Titel auf seine Nachbarn trifft (seit 2026-09-29 ein Dreiwege-Feld; die beiden Ausnahmen schließen einander aus). **As the track type** (Wie der Track-Typ, Vorgabe): Der Titel überlappt und überblendet so, wie sein Track-Typ es vorgibt - Settings → Track Types → *Crossfade Duration* - oder, ohne Wert dort, mit der Default Track Crossfade Duration; seit 2026-09-30 erbt er auch die Typ-Vorgabe *No Fade during Crossover*. **No Fade during Crossover** (Kein Fade beim Crossover, `cc_files.no_fade_crossfade`): Die Überlappung bleibt, aber dieser Titel behält seinen vollen Pegel, während der andere blendet; an einer überzogenen Sendungsgrenze wird ein markierter abgehender Titel geschnitten statt ausgeblendet. **Exclude from Crossover** (Vom Crossover ausnehmen, `cc_files.exclude_crossfade`): Dieser Titel überlappt nie mit einem Nachbarn - er startet am Ende des vorherigen Titels, und der nächste startet an seinem Ende. Ein Wechsel zu oder von *Exclude* legt die Zeilen der kommenden Sendungen, die den Titel enthalten, neu aus. |
| **Stream-Metadaten** (seit 2026-10-14) | Ob Interpret und Titel dieses Titels in die Player der Hörer (ICY) und in den Live Text gelangen. **Wie der Track-Typ** (Standard): die Voreinstellung aus Settings → Track Types → *Forward Metadata to the Stream*. **An den Stream weitergeben** / **Nicht weitergeben**: die eigene Wahl des Titels. Solange ein Titel ohne Weitergabe läuft, zeigt der Stream in jedem Stream-Label-Format „Sendername - Sendungsname", wie eine Live-Quelle ohne Metadaten. Gedacht für Jingles, Station-IDs und Promos; das Sendeprotokoll bleibt unberührt. |
| **Aktiv ab** (seit 2026-11-08) | `cc_files.enabled_from`, Format JJJJ-MM-TT, leer = kein Aktivierungsdatum. Der Track bleibt bis 00:00 Uhr dieses Tages deaktiviert; dann aktiviert ihn der stündliche Lauf, außer er wurde von Hand deaktiviert. Muss vor dem Ablaufdatum liegen. Beim Import aus dem Tag `Enable Date`. Library-Spalte *Aktiv ab* (standardmäßig ausgeblendet). |
| **Ablaufdatum** | `cc_files.expires_at`, Format JJJJ-MM-TT, leer = kein Ablauf. Das Datum gilt ab 00:00 Uhr dieses Tages: Ist es erreicht, hakt der stündliche Ablauf-Lauf **Track deaktiviert** an. Ein späteres oder geleertes Datum aktiviert den Track wieder, außer er wurde von Hand deaktiviert. Beim Import aus dem Tag `Expiry` / `Expiry Date`. |
| **Track deaktiviert** (seit 2026-11-08) | `cc_files.disabled`. Haken Sie es von Hand an, oder es wird automatisch angehakt, solange das Aktivierungsdatum in der Zukunft liegt und sobald das Ablaufdatum erreicht ist. Ein deaktivierter Track wird von Smart Blocks nicht mehr ausgewählt; Sendungen, in denen er schon steht, spielen ihn weiter, und Sie können ihn weiterhin von Hand einplanen. Im Editor folgen die Felder einander schon vor dem Speichern: Ein Ablaufdatum bis einschließlich heute oder ein Aktivierungsdatum nach heute hakt das Kästchen an; ändern oder leeren Sie die Daten, verschwindet der Haken wieder, außer Sie haben ihn von Hand gesetzt; nehmen Sie den Haken weg, werden ein erreichtes Ablaufdatum und ein noch in der Zukunft liegendes Aktivierungsdatum geleert. Ohne Haken lehnt das Speichern mit einer Meldung ab, solange ein Datum den Track noch deaktiviert. Ein Haken von Hand wird eigens gespeichert (`cc_files.disabled_by_hand`), daher bleibt ein von Ihnen deaktivierter Track deaktiviert, wenn sich seine Daten ändern. Library-Spalte *Deaktiviert* (standardmäßig ausgeblendet, Spaltenauswahl). |

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

Während der Server löscht, zeigt die Tabelle ihre Lade-Überlagerung
und der Knopf **Löschen** lautet „%s Element(e) werden gelöscht…";
beides verschwindet, sobald die Anfrage beendet ist.  Viele Tracks
auf einmal zu löschen geht schnell (seit 2026-11-06 dauert die
Prüfung, ob eine Wiederholung den Track noch braucht, Millisekunden
statt etwa zwei Sekunden je Datei).  Schlägt die Anfrage fehl oder
läuft sie in eine Zeitüberschreitung, bittet eine Meldung darum, die
Seite neu zu laden, um zu sehen, welche Elemente entfernt wurden.

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
| **Kriterien** | Zeilen hinzufügen: *Künstler enthält "Bowie"*, *BPM ist im Bereich 100 bis 130*, *Genre ist Pop* usw. Zeilen werden UND-verknüpft; das **+** neben einer Zeile fügt eine Alternative für dasselbe Feld hinzu (ODER), z.B. *Genre ist Pop* **+** *Genre ist Rock*. Seit 2026-11-08 auch *Land* (z. B. *Land ist Austria*; *ist* und *ist nicht* vergleichen genau, *ist nicht* und *enthält nicht* schließen Tracks ohne Land ein). Details unter [Import / Export → blocks.json](./IMPORT_EXPORT.md#blocksjson). |
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

Smart Blocks durchsuchen für jede Rolle die **gesamte
Bibliothek** - auch der Smart Block eines DJ greift auf Tracks
anderer Benutzer zu.  Um einen Block auf Ihre eigenen Tracks
zu beschränken, fügen Sie das Kriterium **Owner** hinzu.

Wenn Sie "Begrenzen auf 10 Tracks" setzen, aber nur 4 Tracks
in der Bibliothek die Kriterien erfüllen, erhalten Sie 4.
Der Block scheitert nicht.

**Deaktivierte Tracks** werden nie ausgewählt.  Seit 2026-11-08
beurteilt ein Smart Block das zur Sendezeit der Zeile, nicht zum
Zeitpunkt der Befüllung: Das Autoloading befüllt eine Sendung etwa eine
Stunde vorher, daher wird ein Track, dessen **Aktiv ab** der Tag einer
00:07-Sendung ist, für sie ausgewählt, und ein Track, dessen
**Ablaufdatum** dieser Tag ist, nicht.  Ein von Hand deaktivierter
Track wird nie ausgewählt.

> **Wie es unter der Haube funktioniert.** Kriterien sind
> in `cc_blockcriteria` gespeichert. Zur Build-Zeit baut
> `BlockExpander.expand()` ein PostgreSQL-`SELECT … WHERE …
> LIMIT …` über `cc_files` zusammen. Time-remaining-Limits
> werden über die `getSecondsRemaining()`-Methode der
> Episode in eine Dauer-Obergrenze umgerechnet (seit
> 2026-10-06 die ausgelegte freie Zeit: `time_filled` = Start bis Ende
> der letzten Zeile; die Auswahl trifft `Scheduler::pickRemainingBlock()`).
> Siehe ARCHITECTURE §23.19 für die Outro-Reserve-Interaktion
> mit Time-remaining-Smart-Blocks.

### Pool-Restriktions-Toggles (Erweiterte Optionen)

Die Schublade **Erweiterte Optionen** unten im Smart-Block-
Dialog beherbergt drei Pool-Restriktions-Toggles, die die
Kandidatenmenge *vor* dem Sort + Limit einschränken:

| Toggle | Worauf der Pool eingeschränkt wird |
|---|---|
| **Allow only tracks not played yet** (Nur noch nicht gespielte Tracks) | Tracks, bei denen `cc_files.lptime` `NULL` ist (das Playout hat sie nie protokolliert). Nützlich für Discovery- / Neue-Inhalte-Rotations-Blöcke. |
| **Exclude tracks played lately** (Kürzlich gespielte Tracks ausschließen) | Tracks, bei denen `lptime` `NULL` ist *oder* älter als das konfigurierte Rückblick-Fenster, seit 2026-10-23 in **Minuten** (1..525600 min, Default 1440 = 24 h; ein in Stunden gespeichertes Fenster wird als Minuten angezeigt). Verwenden Sie dies, wenn Sie kürzliche Wiederholungen vermeiden möchten, ohne jede frühere Wiedergabe zu verbieten. Das Begleitfeld "Exclude tracks played in the last minutes" erscheint, wenn der Toggle an ist.  Seit 2026-10-16 wird das Fenster vom Slot aus gemessen, für den der Block expandiert wird, und **geplante Zeilen zählen mit**: Ein Titel, der im Fenster geplant ist - vor oder nach dem Slot, einschließlich der Zeilen, die ein früherer Block desselben Fülldurchgangs in dieselbe Sendung gelegt hat - wird ausgeschlossen, obwohl er noch nicht gelaufen ist.  Seit 2026-10-23 gilt das auch **innerhalb einer Playlist**: Eine Playlist wird Block für Block aufgelöst, bevor etwas eingefügt wird, und ein Titel (beim Artist-Filter: ein Artist), den ein früherer Block oder fester Eintrag derselben Playlist bereits gesammelt hat, bleibt für die späteren Blöcke außen vor - zwei "Dayteaser"-Blöcke in einer Playlist wählen nicht mehr denselben Teaser. |
| **Exclude artists played lately** (Kürzlich gespielte Artists ausschließen) | Tracks, deren `artist_name` NULL / leer ist *oder* deren Artist nicht über irgendeinen anderen Track im konfigurierten Rückblick-Fenster gespielt wurde, seit 2026-10-23 in **Minuten** (1..525600 min, Default 1440). Verwenden Sie dies, wenn Sie vermeiden möchten, dass zwei Tracks desselben Artists clustern — unabhängig davon, welcher konkrete Track gespielt wurde. Das Begleitfeld "Exclude artists played in the last minutes" erscheint, wenn der Toggle an ist. |
| **Allow only tracks with expiry date** (Nur Tracks mit Ablaufdatum) | Tracks, bei denen `cc_files.expires_at IS NOT NULL` ist. Nützlich für Blöcke, die nur aus kurzlebigen / vergänglichen Inhalten ziehen sollen (datierte News-Segmente, Trailer). |

Alle vier kombinieren sich UND-weise und mit jedem Kriterium
in der Haupt-Kriterien-Section.

> **Operator-Tipp.** Der Toggle "Exclude tracks played lately"
> ist die richtige Antwort auf "spiele 30 min Pop, aber nichts
> aus den letzten 4 Stunden." Kombinieren Sie ihn mit
> `Sortieren: Zufällig` für einen Frisch-Rotations-Auto-Build,
> der nie innerhalb des konfigurierten Fensters repetitiv
> klingt. Nie gespielte Tracks sind im Filter *eingeschlossen*
> — ein Track, der nie auf Sendung war, kann offensichtlich
> nicht "kürzlich" auf Sendung gewesen sein.
>
> Der Begleit-Toggle **"Exclude artists played lately"** ist
> die Antwort auf "lass auf einen Beatles-Track nicht für
> mindestens 6 Stunden einen weiteren Beatles-Track folgen,
> auch wenn ich 50 Beatles-Tracks im Pool habe". Die beiden
> Filter komponieren sich: beide aktivieren ergibt "kein
> kürzlicher Track UND kein kürzlicher Artist" gleichzeitig.

> **Wie es unter der Haube funktioniert.** `Exclude played
> lately` fügt eine einzige `WHERE cc_files.lptime IS NULL OR
> cc_files.lptime < NOW() - INTERVAL 'N minutes'`-Klausel zur
> Propel-Abfrage hinzu. Der Stundenwert wird in
> `cc_block_criteria` persistiert (criteria =
> `exclude_played_lately_minutes`) neben dem Master-Flag
> (criteria = `exclude_played_lately`).  `Exclude artists
> played lately` fügt eine `WHERE cc_files.artist_name IS
> NULL OR cc_files.artist_name = '' OR NOT EXISTS (SELECT 1
> FROM cc_playout_history JOIN cc_files ON ... WHERE
> artist_name matches AND starts > NOW() - INTERVAL 'N
> hours')`-Klausel hinzu — `NOT EXISTS` short-circuited beim
> ersten Treffer, daher bleiben die Kosten auch bei großer
> History-Tabelle begrenzt.  Persistiert als zweites
> Kriterien-Paar (`exclude_artists_played_lately` +
> `..._minutes`).  Keine Schemaänderung für beide Filter —
> abwärtskompatibel mit Smart Blocks, die vor dem jeweiligen
> Feature erstellt wurden (fehlende Zeilen = deaktiviert).
> Siehe ARCHITECTURE §23.21.
>
> **Innerhalb-des-Blocks-Spread (2026-05-25).** Der oben
> beschriebene SQL-Filter hält den Kandidaten-Pool frei von
> Artists / Tracks die in den letzten N h *außerhalb* des
> Blocks liefen.  Aber der Block selbst kann trotzdem zwei
> Beatles-Tracks hintereinander enthalten — der SQL schaut
> nur auf History, nicht auf das was der Block gleich
> abspielt.  Ein zweiter Pass läuft nach dem Track-Listen-
> Aufbau in `Block::applyWithinBlockSpread()`: für jeden
> Slot der ursprünglich gewählten Liste wird der originale
> Track zuerst versucht; wenn dessen Artist (oder File-ID
> je nach aktivem Filter) innerhalb des elapsed-time-
> Fensters der bereits platzierten Tracks liegt, holt die
> Engine stattdessen einen nicht-konflikt-Ersatztrack aus
> dem breiteren SQL-gefilterten Pool (bis 500 Tracks).
> Block-Länge bleibt gleich; nur die Track-Wahl ändert
> sich.  Falls kein nicht-konfliktierender Ersatz mehr im
> Pool ist, wird der Original-Track trotzdem platziert
> und ein `Logging::warn`-Eintrag in `legacy.log`
> geschrieben, damit der Operator sieht wenn der Pool zu
> klein war für den konfigurierten Spread.

### „Allow last track to exceed time limit“ (Erweiterte Optionen)

Bei einem Zeitlimit (Minuten, Stunden, Restzeit) nimmt der Block so
lange Titel auf, bis das Limit erreicht ist, und mit diesem Häkchen
darf der letzte darüber hinausgehen.  Für die **Autoloading-
Befüllung** (seit 26.10.2026) heißt das Häkchen außerdem: Der letzte
Titel des Blocks darf über das **Sendungsende** hinausragen -
komplett, wenn die nächste Sendung „Allow delayed start“ hat, sonst
am Ende gekappt, wenn mindestens die Hälfte läuft.  Bei einem
Folgen-Block („limit: 1 item“) braucht es das Häkchen nur vor einer
Sendung, die pünktlich beginnen muss; siehe [Autoloading
Playlists](./AUTOLOADING_PLAYLISTS.md) §4.

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
Statt zu ziehen können Sie Items auch auswählen und in der
Bibliotheks-Werkzeugleiste **Add to current playlist** klicken oder im
Kontextmenü einer Zeile **Add to Playlist** wählen (Titel, Smart
Blocks, Webstreams, Line-Eingänge; seit 2026-10-21).  Beides bezieht
sich auf den aktiven Editor-Tab; ist **Scheduled Shows** aktiv, fügt der
Knopf stattdessen zur Sendung hinzu.

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

### Eine Playlist löschen, die Sendungen noch verwenden (seit 28.10.2026)

Beim Löschen einer Playlist aus der Bibliothek prüft RASTATIME zuerst,
welche Sendungen sie als **Autoloading-**, **Intro-** oder
**Outro-Playlist** verwenden und ob sie der Senderstandard für Intro /
Outro aus Settings → General ist.  Die Löschfrage zählt diese Sendungen
auf.  Bestätigen Sie, verlieren die Sendungen die Playlist **und** ihr
Häkchen *Add Autoloading Playlist* wird abgeschaltet, damit der
Kalender den echten Zustand zeigt statt einer scheinbar befüllten
Sendung, die still läuft.  Wählen Sie danach im Sendungsdialog eine
andere Playlist.  Vor dem 28.10.2026 blieb das Häkchen gesetzt und die
Sendung leer; das Dashboard warnt jetzt außerdem bis 48 Stunden im
Voraus vor solchen Sendungen (siehe
[Autoloading-Playlists](./AUTOLOADING_PLAYLISTS.md), Abschnitt 7).

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
   Episode der Sendung wird die Items der Playlist
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
| **Bearbeiten** | Ein Track ausgewählt: sein Editor-Tab wie bisher. **Zwei oder mehr Tracks ausgewählt (seit 2026-10-08): ein Dialog für alle** - Interpret, Album, Genre, Jahr, Track-Typ, Sprache, Mood, Label, Komponist, Dirigent, Copyright, Land (seit 2026-11-08), Aktiv ab und Ablaufdatum (`none` löscht sie), Track deaktiviert (*Ja* / *Nein*; seit 2026-11-08, *Nein* leert auch erreichte Ablaufdaten und noch in der Zukunft liegende Aktivierungsdaten), Beschreibung. Leere Felder bleiben unverändert, ein ausgefülltes Feld wird in jeden ausgewählten Track geschrieben; Titel, Track-Nummer, BPM, Cue-Punkte und Cover bleiben je Track. Nur Datenbank, wie der Einzel-Editor (Tags in den Dateien werden beim Import gelesen und nie zurückgeschrieben). Tracks ohne Bearbeitungsrecht werden übersprungen und im Ergebnis gezählt. |
| **Besitz übertragen** | Besitz neu zuweisen (nur Admins). Verwendet, wenn ein DJ ausscheidet und seine Dateien an das Stations-Konto übergehen sollen. |
| **Cue Points** | Erkennt die Cue-Punkte der ausgewählten Tracks aus dem Audio (dieselbe Stille-Erkennung, die der Analyzer beim Import ausführt: leiser als −60 dB für mindestens 0,3 s am Anfang oder Ende) und speichert sie. Kommende Sendungen, die die Tracks enthalten, übernehmen die neuen Werte und werden neu ausgelegt. Tracks über 15 Minuten werden übersprungen - die Aktion ist für Jingles und andere kurze Elemente gedacht. Seit dem 30.09.2026. |
| **Tags neu einlesen** *(seit 2026-10-21)* | Liest die Tags der ausgewählten Tracks neu aus den Dateien - für Dateien, die Sie nach dem Import in Windows bearbeitet haben.  RASTATIME liest eine Datei nie von sich aus erneut: Die Datenbank ist die Wahrheit für Bibliothek und Playout.  Der Knopf ersetzt Titel, Interpret, Album, Genre, Jahr, Tracknummer, Komponist, Copyright, Label, ISRC, BPM, Mood, Sprache, Kommentar und (seit 2026-11-08) Land durch den Inhalt der Datei (ein in der Datei fehlender Tag leert die Spalte), setzt den Track-Typ, den ein **Media-Type**-Tag nennt (seit 2026-11-09; ein unbekannter oder fehlender Tag lässt den Typ), und zieht Prüfsumme und Größe nach; alles andere, was nur in RASTATIME gesetzt wird (Teaser, Cue-Punkte, Lautheit, Ablauf- und Aktivierungsdatum, Anfragen), bleibt.  Admins und Programm-Manager für jede Datei, andere für ihre eigenen.  Die Datei wird nur gelesen, ein laufender Titel ist also sicher - bearbeiten Sie eine Datei in Windows aber nur, solange sie nicht geplant ist, das Playout spielt direkt aus der Bibliothek. |

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

> **Gescheiterte Uploads (seit 28.10.2026).**  Der Filter auf der
> Upload-Seite heißt **Failed (N)**, sobald etwas gescheitert ist, und die
> Zeile sagt *warum* (der Grund des Analyzers, z. B. „ffprobe could not
> read the file").  **Download** liefert das Original, wie es hochgeladen
> wurde, zum Prüfen oder Reparieren; **Clear** entfernt die Zeile samt dem
> Original, das der Analyzer bei Fehlschlägen in `organize/` aufbewahrt.
> Das Dashboard warnt, wenn gescheiterte Uploads älter als eine Stunde
> warten oder Dateien älter als ein Tag in `organize/` liegen.  Eine Art
> Beschädigung wird automatisch repariert: eine WAV-Datei mit einem
> ID3-Tag-Block vor ihrem RIFF-Kopf wird freigeschnitten und importiert.

### "Ich habe eine WAV-Datei hochgeladen, und die Bibliothek zeigt eine MP3."

Das ist gewollt: Verlustfreie Dateien werden beim Import in MP3 mit
320 kbit/s umgewandelt (Abschnitt 2, *Dateiformate beim Import*).  Um
eine Datei verlustfrei zu behalten, schalten Sie Einstellungen →
**Lokale Maschine** → **Importformat** vor dem Hochladen aus.

### "Warum gibt mein Smart Block jedes Mal dieselben Tracks zurück?"

Sie haben wahrscheinlich **Statisch** statt **Dynamisch**
gewählt. Bearbeiten Sie den Block und ändern Sie den Typ;
der nächste Build wird neu abfragen.

### "Kann ich eine Ordnerstruktur importieren und Unterordnernamen erhalten?"

Der lokale Import-Ordner behält Unterordnernamen als
**Album**-Feld der importierten Tracks bei, wenn kein
ID3-Album-Tag gesetzt ist. Das ist das häufigste
Operator-Muster für ein Long-Tail-Musikarchiv.  In der
Bibliothek liegt die Datei danach unter
`imported/<Interpret>/<Album>/`; eine Datei ohne Interpreten-Tag
kommt nach `imported/tagless/` (seit 2026-10-24).

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
