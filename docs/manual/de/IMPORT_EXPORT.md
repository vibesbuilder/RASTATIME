# Import/Export

> **Wo Sie sich im Handbuch befinden.** Einstellungen → **Import/Export**
> bringt Kalender-Objekte als Dateien in RASTATIME hinein und wieder
> heraus: Sendungen, Playlisten, Smart Blocks, Webstreams und
> Podcast-Abos. Lesen Sie zuerst [Kalender](./CALENDAR.md) und
> [Sendungs-Vorlagen](./SHOW_TEMPLATES.md), falls der Dialog „Neue
> Sendung" neu für Sie ist — der Import legt Sendungen genau so an, wie
> es dieser Dialog tut.
>
> **Was diese Funktion ersetzt.** Das Anlegen eines ganzen
> Sendeplans über den Dialog „Neue Sendung", eine Sendung nach der
> anderen, und das Abtippen beim Umzug auf ein neues RASTATIME.

Die Seite hat zwei Hälften. **Export** schreibt die vorhandenen Objekte
als CSV (Smart Blocks als JSON). **Import** nimmt solche Dateien
zurück — ein ZIP-Bündel mit allem oder eine einzelne Datei eines
Typs — und zeigt immer zuerst eine **Vorschau**: Jede Zeile wird
geprüft, Sie haken die gewünschten Zeilen an, nur diese werden
geschrieben. Eine Zeile, deren Zeit sich mit einer bestehenden Sendung
überschneidet, wird nie importiert.

Die Seite sehen nur Administratoren.

---

## 1. Export

1. Haken Sie die gewünschten Typen an. Die Zahl in Klammern ist die
   Anzahl der Zeilen im Export; der Dateiname ist der, den der Import
   wieder erwartet.
2. Klicken Sie **Gewählte Typen exportieren**.
   * Ein Typ ergibt eine einzelne Datei (`shows.csv`, `playlists.csv`,
     `webstreams.csv`, `podcasts.csv` oder `blocks.json`).
   * Mehrere Typen ergeben ein ZIP mit allen Dateien, einem Ordner
     `logos/` mit den Sendungslogos und einer `README.txt`, die jede
     Spalte erklärt.
3. **Vorlagen-Bündel herunterladen** liefert dasselbe ZIP mit den
   Spaltenköpfen, einer Beispielzeile je Typ und der README — der
   schnellste Weg, eine Tabelle von null zu beginnen.

Der Sendungs-Export enthält die Sendungen mit bevorstehenden
Ausstrahlungen. Jede Zeile beginnt bei der **nächsten** Ausstrahlung
der Sendung, sodass eine exportierte Datei ohne Eingriff in die
Vergangenheit wieder importierbar ist.

CSV-Dateien sind UTF-8 mit `;` als Trennzeichen und öffnen sich sauber
in Excel oder LibreOffice; beim Import werden auch `,` und Tabulator
akzeptiert. Schalter-Spalten nehmen `yes`/`no`.

## 2. Import

1. Wählen Sie die Datei: das ZIP-Bündel oder eine einzelne CSV/JSON.
   Lassen Sie **Typ** auf *aus der Datei erkennen*, außer die Datei
   trägt einen ungewöhnlichen Namen.
2. **Vorhandene Namen**: *überspringen* (Standard) lässt ein Objekt,
   dessen Name bereits existiert, unberührt; *ersetzen* überschreibt
   Playlisten, Smart Blocks, Webstreams und die Optionen eines
   Podcast-Abos. Sendungen werden nie ersetzt — eine Sendung, die sich
   überschneiden würde, scheitert einfach.
3. Klicken Sie **Vorschau**. Die Tabelle zeigt jede Zeile mit Status:
   * **bereit** — gültig, wird beim Import angelegt;
   * **übersprungen** — existiert bereits (bei *überspringen*) oder
     nicht ausgewählt;
   * **Fehler** — der Hinweis sagt warum (unbekannte Playlist,
     Überschneidung, falsches Datum …). Korrigieren Sie die Datei und
     laden Sie sie erneut hoch, oder importieren Sie die übrigen Zeilen.
4. Entfernen Sie den Haken bei allem, was Sie nicht wollen, und klicken
   Sie **Gewählte Zeilen importieren**. Die Zeilen werden in
   Abhängigkeitsreihenfolge angelegt — Webstreams, Smart Blocks,
   Playlisten, Podcasts, Sendungen —, sodass eine Playlist einen Block
   aus demselben Bündel referenzieren kann und eine Sendung eine
   Playlist aus demselben Bündel.
5. Die Ergebnistabelle zeigt, was angelegt, übersprungen oder
   fehlgeschlagen ist. Kalender und Playout übernehmen die neuen
   Sendungen beim nächsten Refresh (etwa zwei Minuten).

Jede Zeile wird unmittelbar vor dem Schreiben ein zweites Mal geprüft;
eine Sendung, die sich während Ihrer Vorschau überschneidend geworden
ist, wird weiterhin abgewiesen.

## 3. Die Dateien

### shows.csv

| Spalte | Bedeutung |
|---|---|
| `name`, `url`, `genre`, `description` | wie im Dialog; nur `name` ist Pflicht |
| `start_date`, `start_time`, `end_date`, `end_time` | erste Ausstrahlung; `end_date` darf leer bleiben (gleicher Tag, oder Folgetag, wenn das Ende vor dem Start liegt) |
| `timezone` | IANA-Name wie `Europe/Berlin`; leer = Zeitzone der Station |
| `allow_delayed_start` | yes/no, siehe [Verzögerter Sendungsstart](./DELAYED_START.md) |
| `repeats`, `repeat_type` | `none`, `weekly`, `biweekly`, `every_3_weeks`, `every_4_weeks`, `monthly_date`, `monthly_weekday` |
| `days` | für die wöchentlichen Typen: `Mon,Tue,Wed,Thu,Fri,Sat,Sun` (deutsche Kurzformen gehen auch); leer = Wochentag von `start_date` |
| `months` | für die monatlichen Typen (seit 2026-10-15): `Jan,Feb,...,Dec` oder `1..12` (deutsche Kurzformen gehen auch); leer = jeden Monat |
| `repeat_end_date`, `no_end` | Datum der letzten Ausstrahlung oder `no_end = yes` |
| `linked`, `record` | yes/no |
| `content`, `content_repeat` | Name einer Playlist als **Autoloading-Playlist** der Sendung, und ob sie bis zur vollen Sendung wiederholt wird — siehe [Autoloading-Playlisten](./AUTOLOADING_PLAYLISTS.md). Eine Playlist kann Titel, Smart Blocks, Webstreams und Line-In-Eingänge enthalten, damit wird jede Instanz der Sendung automatisch befüllt. |
| `intro_playlist`, `outro_playlist` | Playlist-Namen; leer = Stationsvorgaben |
| `rastatime_auth`, `custom_auth`, `custom_username` | Live-DJ-Authentifizierung wie im Dialog |
| `djs` | DJ-Logins, kommagetrennt; nur Benutzer vom Typ DJ lassen sich zuweisen |
| `background_color`, `text_color` | sechs Hex-Ziffern ohne `#` |
| `logo` | Dateiname im Ordner `logos/` des Bündels (jpg, png, gif) |

**Das eigene Live-Passwort ist nie Teil der Datei.** Der Export lässt
es weg, und der Import gibt einer Sendung mit eigener
Authentifizierung ein Zufallspasswort, das niemand kennt. Setzen Sie
das echte Passwort danach im Kalender; Vorschau und Ergebnis weisen
bei jeder solchen Zeile darauf hin.

### playlists.csv

`name`, `description` und `items`. `items` listet den Inhalt in
Reihenfolge, getrennt durch `|`:

```
file:imported/Example Radio/StationID/Intro.mp3|webstream:BBC World Service|block:Morning Music|linein:Studio A
```

Dateien werden über ihren Pfad unterhalb der Bibliothekswurzel
referenziert (so, wie der Export ihn schreibt), alles andere über den
Namen. Cue-Punkte und Fades kommen aus der Datei und den Vorgaben, wie
beim Ablegen eines Elements in einer Playlist. Mit *ersetzen* wird eine
Playlist ganz oder gar nicht ersetzt.

### blocks.json

Eine JSON-Liste, ein Objekt je Smart Block: `name`, `description`,
`type` (`dynamic` oder `static`), `limit` (`value` und `modifier`:
items, minutes, hours, remaining), `sort`, die Schalter
(`repeat_tracks`, `overflow_tracks`, `only_unplayed`,
`only_with_expiry`, `use_requests`, `exclude_played_lately` mit
Stunden, `exclude_artists_played_lately` mit Stunden) und `criteria`,
eine Liste von Regeln mit `group`, `field`, `modifier`, `value` und
`extra` (der zweite Wert von `between` und *ist im Bereich*).

**Wie Regeln verknüpft werden.** Eine `group` ist eine Zeile im
Smart-Block-Editor. Regeln mit derselben Gruppe **und** demselben Feld
sind Alternativen (ODER) — die Zeilen, die der **+**-Knopf neben einem
Kriterium anlegt. Alles andere ist mit UND verknüpft: verschiedene
Gruppen, und verschiedene Felder auch innerhalb einer Gruppe. Beispiel
— *Genre ist Pop oder Electronic, und über 110 BPM*:

```json
"criteria": [
  {"group": 0, "field": "genre", "modifier": "is", "value": "Pop"},
  {"group": 0, "field": "genre", "modifier": "is", "value": "Electronic"},
  {"group": 1, "field": "bpm", "modifier": "is greater than", "value": "110"}
]
```

„Entweder A und B, oder C“ über verschiedene Felder lässt sich in einem
Block nicht ausdrücken; legen Sie dafür zwei Smart Blocks in eine
Playlist. Ein Feld darf in
mehreren Gruppen vorkommen, jede mit eigenen Alternativen: (A oder B)
und (C oder D).

**Datumsangaben.** Für *Hochgeladen* (`utime`), *geändert am*
(`mtime`) und *Zuletzt gespielt* (`lptime`):

* `before`, `after` und `between` zählen ab jetzt zurück: eine ganze
  Zahl in `value` plus `unit` — `minute`, `hour`, `day`, `week`,
  `month` oder `year`; `between` nimmt zusätzlich `extra` mit
  `extra_unit`. `{"field": "utime", "modifier": "after", "value": "30", "unit": "day"}` = in den letzten 30 Tagen hochgeladen. Exporte
  vor dem 2026-10-14 schrieben `"7 day ago"` in `value`; diese Form
  wird weiter angenommen.
* Die übrigen Modifikatoren nehmen ein festes Datum `JJJJ-MM-TT` oder
  `JJJJ-MM-TT HH:MM:SS` in Ihrer Benutzer-Zeitzone, so wie der Editor
  es zeigt.

Die Vorschau prüft jede Regel wie der Editor — Modifikator passt zum
Kriterium, Zahlen, Dauern (`HH:MM:SS`), Datumsangaben, Länge — und
listet, was nicht stimmt. Ein Block wird ganz oder gar nicht
geschrieben.

### webstreams.csv

`name`, `description`, `url`, `length` (`HH:MM:SS`) und `input_gain_db`.
Die URL wird beim Import geprüft, wie im Webstream-Dialog.

### podcasts.csv

`url` (der Feed), `title`, `auto_ingest`, `auto_expiry_enabled`,
`auto_expiry_days`, `album_override`, `default_track_type` (der Code aus
Einstellungen → Track-Typen). Der Feed wird beim Import abgerufen;
Episoden werden nicht exportiert — der Feed liefert sie erneut.

## 4. Tipps

* Exportieren Sie zuerst, auch auf einer leeren Station: Die Datei
  trägt die exakten Spaltenköpfe und die README.
* Führen Sie eine Tabelle je Station und importieren Sie sie nach
  Änderungen erneut; mit *überspringen* werden nur neue Zeilen angelegt.
* Zwei Zeilen derselben Datei, die sich gegenseitig überschneiden: Die
  erste wird angelegt, die zweite scheitert beim Import mit der
  Überschneidungs-Meldung.
* Große Logos: Die Upload-Grenze des Servers steht unter dem Dateifeld.

## 5. Siehe auch

* [Kalender](./CALENDAR.md) — der Dialog „Neue Sendung", dessen Regeln
  der Import anwendet.
* [Sendungs-Vorlagen](./SHOW_TEMPLATES.md) — Einstellungen innerhalb des
  Dialogs wiederverwenden.
* [Autoloading-Playlisten](./AUTOLOADING_PLAYLISTS.md) — was die Spalte
  `content` einschaltet.
* [Backup](./BACKUP.md) — die vollständige Datenbanksicherung;
  Import/Export ist das lesbare, bearbeitbare Gegenstück.
