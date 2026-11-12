# API

> **Wo Sie im Handbuch sind.** Dieses Kapitel richtet sich an alle,
> die Daten von RASTATIME von außen lesen wollen — Stationswebsite,
> Partnerseite, Überwachungsskript — oder wissen wollen, was das
> System öffentlich preisgibt.  Es listet die öffentlichen Endpunkte,
> erklärt den Schalter, der sie freigibt, und sagt, wofür der API-Key
> da ist und warum er die Station nie verlassen darf.  Für die
> fertigen iframe-Widgets siehe [Öffentliche Embed-Widgets](./WIDGETS.md).

RASTATIME hat zwei HTTP-Schnittstellen, die zu verschiedenen Zeiten
entstanden sind:

| Schnittstelle | Basispfad | Format | Genutzt von |
|---|---|---|---|
| **REST-API v2** | `/api/v2/` | JSON, OpenAPI-Schema, Swagger-UI | Playout, Analyzer, Einstellungsseiten, Skripte |
| **Legacy-API** | `/api/<aktion>` | JSON (teils JSONP), Bilder, M3U | Embed-Widgets, Dashboard, ältere Anbindungen |

Beide antworten unter der Webadresse der Station
(`https://<station-host>/…`).  Alles Folgende gilt für die
Live-Station; eine Entwicklungsinstallation verhält sich gleich.

---

## 1. Wer darf was lesen

| Zugang | Was dazugehört |
|---|---|
| **Öffentlich, ohne Login** | Die reinen Lese-Endpunkte der Legacy-API aus Abschnitt 3, solange **Einstellungen → General → Public RASTATIME API** eingeschaltet ist; dazu `version`, `info`, `now-playing` und Suche/Abgabe der Song-Requests der API v2. |
| **Login (Session oder Basic Auth)** | Das Blättern in `/api/v2/` im Browser, das OpenAPI-Schema und die Swagger-UI.  Ein angemeldetes Konto sieht, was seine Rolle erlaubt (siehe [Benutzer und Rollen](./USERS_AND_ROLES.md)). |
| **API-Key** | Alle übrigen Endpunkte: Schreiben, interner Zustand, Dateilisten, Stream-Einstellungen.  Ein Schlüssel für die ganze Station, Vollzugriff. |

Alles, was nicht öffentlich ist, antwortet ohne Berechtigung mit `401`
oder `403`.  Auf den öffentlichen Lese-Endpunkten gibt es keine
Drossel; nur die Song-Request-Endpunkte sind je Hörer begrenzt.

---

## 2. Der Schalter: Public RASTATIME API

**Einstellungen → General → Public RASTATIME API** (an / aus).

- **An:** die Lese-Endpunkte der Legacy-API antworten ohne Schlüssel.
- **Aus:** dieselben Endpunkte verlangen den API-Key.  Nur sinnvoll,
  wenn keine externe Seite das Programm über sie liest.  Seit
  2026-11-12 gilt das auch für `shows`, `show-schedules`,
  `show-tracks`, `item-history-feed` und `show-history-feed`, die
  vorher auch bei ausgeschaltetem Schalter antworteten.

Die Embed-Widgets lesen ihre Daten über eigene `/embed/…`-Adressen,
die in jedem Fall öffentlich sind; aus dieser API holen sie nur die
Cover und Sendungsbilder (`track`, `show-logo`).  Bei ausgeschaltetem
Schalter laufen die Widgets weiter, nur ohne Cover (bis 2026-11-12
stand hier, sie würden lahmgelegt).

Der Schalter berührt die API v2 nicht und öffnet nichts, was schreibt.

---

## 3. Öffentliche Lese-Endpunkte (Legacy-API)

Alle liefern JSON, wenn nicht anders vermerkt.  Zeiten in der
Zeitzone der Station, außer Sie übergeben `timezone=` (ein Name aus
der tz-Datenbank wie `Europe/Berlin`, oder `UTC`).

| Endpunkt | Parameter | Liefert |
|---|---|---|
| `/api/live-info-v2` | `days` (Standard 2), `shows` (Standard 5), `timezone` | Was auf Sendung ist: `shows` (vorige / laufende / nächste), `tracks` (voriger / laufender / nächster), `sources` (Live-DJ, Master-DJ, Automation), `station`. |
| `/api/live-info` | `type` (`endofday` oder Intervall), `limit` (Standard 5), `timezone` | Die ältere Form derselben Daten: `currentShow`, `nextShow`, `current`, `next`, `previous`, `schedulerTime`. |
| `/api/week-info` | `timezone` | Das Programm dieser und der nächsten Woche, eine Liste je Wochentag (`monday` … `nextsunday`), je Sendung Name, Zeiten, Beschreibung, Bild, URL. |
| `/api/station-metadata` | — | Stationsname, Beschreibung, Logo, Sprache, Zeitzone und die Liste der Streams. |
| `/api/shows` | `show_id` (optional) | Alle Sendungen oder eine: id, Name, Beschreibung, Genre, URL, Farben, Verknüpfungs-Flag. |
| `/api/show-schedules` | `show_id` (Pflicht), `start`, `end` (`YYYY-MM-DD HH:MM:SS`) | Die Episoden einer Sendung im Zeitraum. |
| `/api/show-tracks` | `instance_id` (Pflicht) | Die Zeilen einer Episode: Position, Titel, Interpret, Länge, Start.  Eine Webstream-Zeile trägt nur den Namen des Streams, `file_id` gibt es nur für Dateien (bis 2026-11-12 standen dort die Quell-URL des Streams und der Login dessen, der ihn angelegt hat). |
| `/api/item-history-feed` | `start`, `end`, `instance_id` (optional) | Die Playout-History: was wann lief, mit Titel, Interpret und Episode. |
| `/api/show-history-feed` | `start`, `end`, `user_id` (optional) | Die Sendungen, die im Zeitraum liefen; `user_id` beschränkt sie auf die Sendungen dieses Hosts.  Ohne `user_id` antwortete der Endpunkt bis 2026-11-12 leer. |
| `/api/track?id=<Datei-ID>&return=<Art>` | `return` = `artwork`, `artwork-32`, `artwork-64`, `artwork-data` | Das Cover eines Titels (JPG). |
| `/api/show-logo?id=<Sendungs-ID>` | — | Das Bild einer Sendung. |
| `/api/track-types` | — | Die in der Bibliothek eingerichteten Track-Typen. |
| `/api/stream-m3u` | — | Eine M3U-Playlist-Datei mit den Streams der Station. |

**Was ein Titel preisgibt.**  Die Titel-Metadaten in `live-info` und
`live-info-v2` sind bewusst auf die Credit-Angaben beschränkt, die ein
Hörer sehen darf: Titel, Interpret, Album, Jahr, Genre, Sprache,
Länge, Track- und Disc-Nummer, Komponist, Dirigent, Texter,
Original-Interpret, Label, Copyright, ISRC, BPM, Stimmung, die Info-,
Kauf- und Interpreten-URLs, der Cover-Verweis und der Track-Typ.
Dateipfade, Besitzer, Prüfsummen, Kommentare, Liedtexte und
Import-Details werden nie gesendet.  `/api/shows` lässt ebenso die IDs
der Autoloading-, Intro- und Outro-Playlists weg.

---

## 4. Öffentliche Endpunkte der API v2

| Endpunkt | Liefert |
|---|---|
| `GET /api/v2/version` | `{"api_version": "…"}` |
| `GET /api/v2/info` | `{"station_name": "…"}` |
| `GET /api/v2/now-playing` | Was auf Sendung ist, aus dem Sendeplan gelesen (siehe unten). |
| `GET /api/v2/song-requests/search?q=<Text>` | Titel, die ein Hörer wünschen darf: id, title, artist, album, has_artwork. |
| `POST /api/v2/song-requests` | Gibt einen Wunsch ab (`file_id`, optional `listener_label`).  Je Hörer gedrosselt; siehe [Song Requests](./SONG_REQUESTS.md). |

**now-playing** antwortet immer mit `200`:

```json
{
  "is_playing": true,
  "now": "2026-11-05T13:07:21+00:00",
  "source": "scheduled",
  "started_at": "2026-11-05T13:07:00+00:00",
  "item": {
    "type": "file", "id": 1304,
    "title": "Example Song", "artist": "Example Artist", "album": "Example Album",
    "genre": "Pop", "year": "2024",
    "length_seconds": 251.438, "has_artwork": true,
    "starts_at": "2026-11-05T13:07:00+00:00",
    "ends_at": "2026-11-05T13:11:11+00:00"
  },
  "show": {"id": 912, "name": "…", "description": "…", "url": "…",
           "genre": "…", "starts_at": "…", "ends_at": "…"},
  "next": {"type": "file", "id": 1305, "title": "…", "…": "…"}
}
```

`type` ist `file`, `webstream` oder `linein`; `source` ist `scheduled`,
`live_dj` oder `master_dj`.  Läuft nichts aus dem Sendeplan, ist
`is_playing` `false`, `item` und `started_at` sind `null`, und `show`
nennt weiterhin die laufende Sendung.  Zeiten in UTC (ISO 8601).

---

## 5. Die API mit Berechtigung nutzen

**Im Browser.**  Bei RASTATIME anmelden, dann
`https://<station-host>/api/v2/` für die blätterbare API und
`https://<station-host>/api/v2/schema/swagger-ui` für die Swagger-UI
öffnen (das rohe OpenAPI-Schema liegt unter `/api/v2/schema`).  Beide
brauchen den Login; ohne antworten sie mit `403`.

**Aus einem Skript.**  Den API-Key der Station im `Authorization`-Header
mitsenden:

```
Authorization: Api-Key <key>
```

Der Schlüssel ist der Wert `api_key` unter `[general]` in
`C:\rastatime\config\rastatime.conf`.  Die Legacy-API nimmt ihn auch
als `?api_key=<key>`.

> **Den Schlüssel nie an Dritte geben.**  Es gibt genau einen
> Schlüssel, und er gewährt Vollzugriff: Schedule-Pushes, Dateilisten,
> Stream-Passwörter, Einstellungen.  Eine Partnerseite, die nur das
> Programm braucht, nutzt die öffentlichen Endpunkte aus Abschnitt 3 —
> die brauchen keinen Schlüssel.  Braucht ein Partner mehr als Lesen,
> ist das eine Anfrage nach einem Lese-Token je Client (siehe
> BACKLOG), nicht nach dem Stationsschlüssel.

---

## 6. Beispiele

Was auf Sendung ist (öffentlich):

```bash
curl -s "https://<station-host>/api/v2/now-playing"
```

Das Programm dieser Woche in UTC (öffentlich):

```bash
curl -s "https://<station-host>/api/week-info?timezone=UTC"
```

Die Zeilen einer Episode (öffentlich):

```bash
curl -s "https://<station-host>/api/show-tracks?instance_id=12345"
```

Die Playout-History eines Tages (öffentlich):

```bash
curl -s "https://<station-host>/api/item-history-feed?start=2026-11-05%2000:00:00&end=2026-11-05%2023:59:59"
```

Ein geschützter Endpunkt mit Schlüssel (vom Stationsrechner):

```bash
curl -s -H "Authorization: Api-Key <key>" "https://<station-host>/api/v2/files?limit=5"
```

---

## 7. Häufige Fragen

**Darf die API-Adresse auf der Stationswebsite stehen?**  Ja, für die
öffentlichen Endpunkte.  Sie enthalten nur das Programm und die
Credit-Daten der Titel.

**Warum antwortet `/api/version` mit 401?**  Dieser Legacy-Endpunkt
gehört nicht zum öffentlichen Satz; nehmen Sie `/api/v2/version`.

**Sagt die API, ob ein DJ live ist?**  `live-info-v2` → `sources` und
`now-playing` → `source`.

**Gibt es eine Drossel?**  Nicht auf den öffentlichen
Lese-Endpunkten.  Eine Seite, die `live-info-v2` für jeden Besucher
alle paar Sekunden abfragt, ist für eine Stationswebsite in Ordnung;
ein Crawler, der `week-info` (etwa 270 KB) in Dauerschleife holt,
nicht — davor gehört ein Cache.

> **Wie es unter der Haube funktioniert.**  Die Legacy-Aktionen ohne
> Schlüssel stehen in `ApiController::$ignoreAuth`; sie prüfen trotzdem
> den Schalter (`Application_Model_Preference::GetAllow3rdPartyApi`).
> Die Titel-Whitelist ist `WidgetHelper::PUBLIC_TRACK_FIELDS`
> (`restrictLiveInfo`), die Sendungs-Whitelist `PUBLIC_SHOW_FIELDS`.
> Die Berechtigungen der API v2 liegen in
> `rastatime_api/permissions.py` (`IsSystemTokenOrUser`: Api-Key oder
> angemeldeter Benutzer mit den Django-Rechten seiner Rolle;
> `internal_only` für die einfachen Views, die das Playout aufruft).
> Die Schema-Views tragen `IsAuthenticated`.  `now-playing` liest aus
> `cc_schedule` die Zeile, die *jetzt* abdeckt, und fragt das Playout
> unter `/source-state` nach den DJ-Flags.  Siehe ARCHITECTURE §23.90
> und §23.91.
