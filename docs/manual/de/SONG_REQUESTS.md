# Song Requests

> **Wo Sie im Handbuch sind.** Lesen Sie zuerst [Bibliothek](./LIBRARY.md)
> → §3 Smart Blocks und
> [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) — Song Requests
> werden vollständig aus diesen beiden Bausteinen plus einem
> öffentlichen Hörer-Widget zusammengesetzt. Es gibt keinen neuen
> „Request"-Objekttyp.

**Song Requests** lassen Ihre Hörer Tracks über ein öffentliches
Web-Widget wünschen, und diese Tracks laufen automatisch in einer
normalen Sendung — ohne dass ein Host etwas anklicken muss. Das
gesamte Feature besteht aus Teilen, die Sie bereits kennen:

- ein **Smart Block** mit der Markierung *Use requests* zieht die
  Tracks, die Hörer tatsächlich gewünscht haben;
- eine **Autoloading Playlist**, die diesen Block enthält, macht aus
  einer gewöhnlichen Sendung eine **Request-Show**;
- ein kleines **Embed-Widget** auf Ihrer öffentlichen Website sammelt
  die Requests.

Es gibt keinen Per-Show-Schalter „akzeptiert Requests" und keine
separate Request-Warteschlange zum Moderieren. Eine Sendung *ist*
eine Request-Show, wenn ihre Autoloading Playlist einen *Use
requests*-Block enthält — sonst nichts.

---

## 1. Das Gesamtbild

```
   HÖRER                    RASTATIME                     ON AIR
   ┌─────────┐   Request    ┌──────────────────────┐
   │ Widget  │─────────────▶│ rastatime_song_request│
   │ (iframe)│   /api/v2    │  status = pending     │
   └─────────┘              │ cc_files.requested=t  │
                            └──────────┬────────────┘
                                       │  Request-Show füllt sich
                                       │  inkrementell, on air
                            ┌──────────▼────────────┐   ┌──────────┐
                            │ „Use requests"-Block   │──▶│  Show    │
                            │  zieht pending Requests │   │ Schedule │
                            │  ältester zuerst, je 1  │   └──────────┘
                            └────────────────────────┘
```

Zwei unabhängige Hälften treffen sich in der Mitte:

1. **Hörer** öffnen das Widget, sehen den Katalog der wünschbaren
   Tracks und senden einen Request. Der Request wird festgehalten und
   der Track als „gewünscht" markiert.
2. **Eine Request-Show** — jede Sendung, deren Autoloading Playlist
   einen *Use requests*-Smart-Block enthält — füllt sich aus diesen
   gewünschten Tracks inkrementell, während sie läuft, sodass ein
   während der Show abgesendeter Wunsch noch in ihr laufen kann.

Die beiden Hälften sind nur über den Request-**Pool** (§2) und das
*Use requests*-Kriterium (§3) verbunden. Sie konfigurieren beides
einmal; danach läuft das Feature unbeaufsichtigt.

---

## 2. Der Request-Pool — was Hörer wünschen dürfen

Der **Pool** ist der Katalog der Tracks, die ein Hörer wünschen
darf. Er wird durch einen oder mehrere Smart Blocks definiert.

Öffnen Sie **Settings → General → Song-Request Pool (Smart
Blocks)**. Das Feld ist ein Dropdown im Stil des Library-*Columns*-
Pickers: klicken Sie **Smart Blocks**, kreuzen Sie einen oder mehrere
Blocks an, klicken Sie daneben zum Schließen.

```
   Song-Request Pool (smart blocks)   [ Smart Blocks ▾ ]
                                      ┌────────────────────┐
                                      │ ☑ Indie / Alt-Pool │
                                      │ ☐ Jingles          │
                                      │ ☑ Request-Katalog  │
                                      │ …                  │
                                      └────────────────────┘
```

Der Pool ist die **Vereinigung** der Kataloge aller angekreuzten
Blocks — die Tracks, die die Kriterien jedes Blocks erfüllen (Genre,
Album, …), *unabhängig* davon, ob sie schon gewünscht wurden. Kreuzen
Sie keinen an, um Song Requests ganz zu deaktivieren: das Widget
zeigt dann „derzeit nicht verfügbar".

> **Wie es unter der Haube funktioniert.** Eine Hintergrundaufgabe
> (`RequestablePoolSyncTask`, alle 5 Min) expandiert die Vereinigung
> der ausgewählten Blocks mit *ignoriertem* Request-Filter und setzt
> `cc_files.requestable = true` für jedes Mitglied, gelöscht für alles
> andere. Der öffentliche Katalog-Such-Endpunkt filtert auf dieses
> Flag. Die ausgewählten Block-IDs liegen im cc_pref-Schlüssel
> `requestable_pool_block_ids`.

---

## 3. Der „Use requests"-Smart-Block

Ein Smart Block wird zu einer **Request-Quelle**, wenn Sie im
Smart-Block-Dialog **Use requests** ankreuzen (Library → Smart Block
bearbeiten → erweiterte Kriterien).

Das ändert, was der Block zieht:

| Zustand | Was der Block auswählt |
|---|---|
| **Use requests AUS** (normal) | Alle Tracks, die seine Kriterien erfüllen (Genre, Album, …). |
| **Use requests AN** | Nur Tracks, die seine Kriterien erfüllen **und** einen offenen Hörer-Request haben (`cc_files.requested = true`). |

Zwei Sortierungen stehen zur Verfügung und sind für Request-Blocks
relevant:

- **Ältester Request zuerst** — faire Warteschlange: wer zuerst
  gewünscht hat, läuft zuerst.
- **Meistgewünscht zuerst** — Popularität: der Track mit den meisten
  offenen Requests läuft zuerst.

> **Operator-Tipp.** Derselbe Block spielt meist beide Rollen: Sie
> wählen ihn in Settings als **Pool** (das nutzt seinen Katalog,
> Request-Filter ignoriert) *und* platzieren ihn in der Playlist einer
> Request-Show (wo das *Use requests*-Kriterium ihn die echten
> Requests ziehen lässt). Halten Sie seine Katalog-Kriterien (z. B.
> `genre = Indie or Alternative`) sinnvoll — sie begrenzen **beides**:
> was gewünscht werden darf und was gezogen wird.

---

## 4. Eine Request-Show bauen

Eine Request-Show ist einfach eine
[Autoloading-Playlist](./AUTOLOADING_PLAYLISTS.md)-Sendung, deren
Playlist mindestens einen *Use requests*-Block enthält. Sie
komponieren die Playlist als **Dramaturgie** — eine feste
Reihenfolge, die die Befüllung einmal durchläuft:

```
   Autoloading Playlist „Request-Stunde"
   ──────────────────────────────────────
   1. Smart Block · Use requests · 1 Item   ◀── Request A
   2. Smart Block · StationID    · 1 Item
   3. Smart Block · Use requests · 1 Item   ◀── Request B (anders!)
   4. Smart Block · StationID    · 1 Item
   5. Smart Block · Use requests · 1 Item   ◀── Request C (anders!)
   6. Smart Block · Musik · Limit „verbleibende Zeit"  ◀── füllt den Rest
```

Wenn sich die Show füllt (§5), zieht jeder *Use requests*-Slot einen
**anderen** Request, und der abschließende **„verbleibende Zeit"**-
Block füllt den Rest mit Musik. Hängen Sie die Playlist auf die
normale Weise an eine Sendung an (**Sendung bearbeiten → Autoloading
Playlist hinzufügen?**) — und diese Sendung ist nun eine Request-Show.

> **Sie dürfen einen Block mehrfach verwenden.** Denselben *Use
> requests*-Block an die Positionen 1, 3 und 5 zu setzen funktioniert
> — die Befüllung löst jede Position einzeln auf, also ziehen drei
> Platzierungen drei verschiedene Requests. Sie brauchen keine drei
> getrennten Blocks.

> **Warum ein abschließender „verbleibende Zeit"-Block.** Ohne einen
> Block, der den Rest füllt, würde eine Request-Show mit nur einer
> Handvoll Requests nach dem letzten Request Dead Air hinterlassen.
> Der „verbleibende Zeit"-Musik-Block ist das Sicherheitsnetz. Geben
> Sie ihm **Tracks wiederholen = ja** (oder einen ausreichend großen
> Katalog), damit er den ganzen Rest in einem Durchgang füllt; mit
> „wiederholen aus" füllt er mit so viel Abwechslung, wie sein Pool
> erlaubt, und lässt möglicherweise eine kleine Lücke, die der
> Fallback des Playout abfängt.

---

## 5. Wie und wann sich eine Request-Show füllt

Eine Request-Show füllt sich **inkrementell, während sie läuft** — ihre
Dramaturgie wird Stück für Stück vor dem Play-Head aufgelöst, nicht alles
auf einmal vor dem Start. Genau das lässt einen *während* der Show
abgesendeten Wunsch noch in ihr laufen.

- Eine Hintergrundaufgabe (`RequestShowFillTask`, alle 2 Min) nimmt sich
  eine Request-Show vor, sobald sie in ein **Vorlauf**-Fenster eintritt
  (`RASTATIME_REQUEST_FILL_LEAD_SECONDS`, Standard 8 Min vor Start), und
  bearbeitet sie weiter, solange sie läuft.
- Sie durchläuft die Playlist **Position für Position**, löst aber nur
  Positionen bis kurz **vor den Play-Head** auf
  (`RASTATIME_REQUEST_FILL_AHEAD_SECONDS`, Standard 5 Min). Nach jedem
  Slot nimmt sie den gezogenen Request aus dem Pool, damit der
  **nächste** *Use requests*-Slot einen anderen Track zieht.
- Ein Cursor pro Show merkt sich, wie weit die Dramaturgie aufgelöst ist,
  sodass der nächste Durchlauf fortsetzt statt von vorne zu füllen. Ein
  *Use requests*-Block weiter hinten in der Dramaturgie wird damit erst
  aufgelöst, wenn sein Slot gleich dran ist — und zieht die Wünsche, die
  **seit Sendebeginn** eingingen.
- Sobald die Dramaturgie durch ist, füllt der abschließende
  „verbleibende Zeit"-Block den Rest der Show **komplett** bis zum Ende.

Das bleibt **dead-air-sicher**: die Show ist stets vor dem Play-Head
gefüllt (das Vorlauf-Fenster übersteigt den 2-Min-Poll deutlich), und der
lange Musik-Tail wird komplett gefüllt, sobald die Dramaturgie steht.

> **Wo späte Requests landen.** Ein Request läuft in der laufenden Show,
> **wenn beim Eintreffen noch ein *Use requests*-Slot vor dem Play-Head
> liegt**. Verteilen Sie Ihre Request-Slots über die Dramaturgie, statt
> sie vorne zu bündeln: ein in Minute 20 abgesendeter Wunsch braucht
> einen Request-Slot, der *nach* Minute 20 läuft. Ein Request, der
> eintrifft, nachdem der letzte Request-Slot der Show schon aufgelöst
> wurde, landet in der nächsten Request-Show.

> **Leerer Request-Slot → Zufalls-Track.** Wenn ein *Use
> requests*-Slot zur Befüllzeit keinen offenen Request hat, lässt er
> **keine** Lücke. Er spielt einen **zufälligen** Track aus dem
> eigenen Katalog dieses Blocks (sein Genre/seine Kriterien,
> Request-Filter ignoriert). So spielt eine Request-Show mit null
> Requests trotzdem eine normale, formatgerechte Stunde; sobald
> Requests eintreffen, ersetzen sie die Zufallswahl Slot für Slot.

> **Frische vs. Dead-Air-Sicherheit.** `RASTATIME_REQUEST_FILL_AHEAD_SECONDS`
> ist der Regler: kleiner löst jeden Slot näher an seiner Spielzeit auf
> (frischere Requests), lässt aber einen dünneren Puffer vor dem
> Play-Head; größer löst früher auf (sicherer). Über dem 2-Min-Poll
> halten.

> **Wie es unter der Haube funktioniert.** `AutoPlaylistManager::`
> `fillRequestShows()` bearbeitet sowohl bereits laufende (noch nicht
> beendete) als auch unmittelbar bevorstehende Instanzen.
> `_fillRequestShowByPositions()` löst `cc_playlistcontents` ab dem
> persistierten `cc_show_instances.autoplaylist_cursor` bis
> `now + RASTATIME_REQUEST_FILL_AHEAD_SECONDS` (Standard 300) auf, hängt
> jede Datei/jeden Block mit `addAutoloadItemToShow()` an, führt zwischen
> den Slots den Consume-Schritt aus und speichert den Cursor, damit der
> nächste Durchlauf fortsetzt. Das Backend-Playout (pypo) nimmt den
> Mid-Show-Insert zur Startzeit auf, daher kein Playout-Eingriff. Der
> normale Autoplaylist-Builder überspringt Request-Shows bewusst. Siehe
> ARCHITECTURE §23.23.

---

## 6. Das Hörer-Widget

Das öffentliche Widget liegt unter:

```
   http://<ihre-station>/Embed/song-request
   http://<ihre-station>/Embed/song-request?theme=dark
```

Betten Sie es in ein `<iframe>` auf Ihrer Website ein (Themes:
`light`, `dark`, `auto`). Es zeigt eine scrollbare Tabelle jedes
wünschbaren Tracks — Cover · Artist / Title · einen **Request**-Button
— ohne Suchfeld und ohne Pagination:

```
   ┌──────────────────────────────────────────────┐
   │ [Cover] Robb — Down with It          [Request]│
   │ [Cover] Leyya — Butter               [Request]│
   │         Viech — Steuermann           [Request]│
   │ …                                             │
   └──────────────────────────────────────────────┘
```

Ein Klick sendet den Request und zeigt eine Statuszeile: Danke,
„bereits kürzlich gewünscht" oder „Request-Limit erreicht".

Eingebaute Schutzmechanismen (keine Moderations-Queue nötig):

| Schutz | Standard |
|---|---|
| **Rate-Limit** | 5 Requests pro Stunde pro Hörer |
| **De-Duplizierung** | derselbe Hörer kann denselben Track nicht innerhalb von 30 Min erneut wünschen |
| **Katalog-Beschränkung** | nur Pool-Tracks (§2) sind listbar / wünschbar |

> **Cover brauchen die 3rd-Party-API.** Die Cover-Thumbnails kommen
> vom Track-Artwork-Endpunkt, der durch **Settings → … → Allow 3rd
> party API** abgesichert ist. Mit „aus" rendert die Tabelle text-only
> (Artist / Title), was völlig brauchbar ist. Tracks, die schlicht
> kein Artwork haben, bleiben ebenfalls text-only.

> **Wie es unter der Haube funktioniert.** Das Widget ist eine
> eigenständige Vanilla-JS-iframe-Seite (`/Embed/song-request`), die
> mit zwei öffentlichen Django-Endpunkten spricht: `GET
> /api/v2/song-requests/search` (der Katalog) und `POST
> /api/v2/song-requests` (Submit). Kein Login, kein Cookie. Die rohe
> Hörer-IP wird nie gespeichert — nur ein gesalzener Hash, genutzt für
> Rate-Limiting und De-Duplizierung.

---

## 7. Der Request-Lebenszyklus

Jeder Request durchläuft vier Zustände:

| Zustand | Gesetzt wenn | Bedeutung |
|---|---|---|
| **pending** | Hörer sendet ihn | wartet im Pool, gezogen zu werden |
| **queued** | die Befüllung plant seinen Track ein | in eine Show gezogen; aus dem Pool |
| **played** | der Track lief | erledigt (für die Historie aufbewahrt) |
| **expired** | TTL abgelaufen, nicht gelaufen | nie gezogen; aus dem Pool entfernt |

- Wenn ein Request **eingeplant** wird, verlässt sein Track den Pool
  (`cc_files.requested` gelöscht), damit der nächste Slot etwas
  anderes zieht, und der Request wird **queued**.
- Eine Schedule-basierte Aufgabe markiert **played**, sobald der Slot
  des Tracks vorbei ist (`RequestPlayedTask`, alle 2 Min) — bewusst
  gewählt statt eines Playout-seitigen Hooks, damit der
  Live-Sendepfad nie angefasst wird.
- Wird eine **Request-Show gelöscht**, bevor ihre Tracks laufen, gehen
  ihre eingeplanten Requests nicht verloren: derselbe Lauf setzt sie
  zurück auf **pending** (ihr Track steht in keinem Schedule mehr),
  sodass die nächste Request-Show den Wunsch erneut versucht.
- Der Expiry-Lauf (`RequestExpiryTask`, alle 10 Min) lässt jeden noch
  **pending** Request nach der TTL ablaufen — Standard **8 Stunden**,
  überschreibbar mit `RASTATIME_REQUEST_EXPIRY_HOURS` — und berechnet
  das Pool-Aggregat neu, sodass ein Track, dessen letzter Request
  ablief, sauber aus dem Katalog fällt.

---

## 8. Operator-Checkliste

Um Song Requests von Grund auf einzurichten:

1. **Erstellen Sie einen Request-Smart-Block.** Library → neuer Smart
   Block → setzen Sie seine Katalog-Kriterien (z. B. `genre = Indie or
   Alternative`), kreuzen Sie **Use requests** an, setzen Sie
   **Sortierung: Ältester Request zuerst**, **Limit: 1 Item**.
   Speichern.
2. **Wählen Sie ihn als Pool.** Settings → General → **Song-Request
   Pool** → Block ankreuzen. (Innerhalb von 5 Min werden seine Tracks
   wünschbar.)
3. **Komponieren Sie die Dramaturgie-Playlist** (§4): Ihr Request-Block
   an einigen Positionen, Jingles/IDs dazwischen, ein **„verbleibende
   Zeit"**-Musik-Block zuletzt (mit **Tracks wiederholen = ja**).
4. **Hängen Sie sie an eine Sendung** als Autoloading Playlist (§4).
5. **Betten Sie das Widget ein** (§6) auf Ihrer Website, optional
   **Allow 3rd party API** für Cover-Art aktivieren.

Das ist die gesamte Einrichtung. Von da an wünschen Hörer, und die
Show füllt sich inkrementell, während sie läuft — und nimmt Wünsche
auf, die eintreffen, solange sie auf Sendung ist, sofern noch ein
Request-Slot vor dem Play-Head liegt.

---

## 9. Häufige Fragen

### „Das Widget zeigt keine Tracks."

Der Pool ist leer. Entweder ist in **Settings → Song-Request Pool**
kein Block ausgewählt, oder die Kriterien des ausgewählten Blocks
treffen nichts, oder der 5-Minuten-Pool-Sync ist noch nicht gelaufen.
Prüfen Sie, dass der Block in der Library Tracks zeigt; warten Sie
einen Sync-Zyklus.

### „Meine Request-Show lief, spielte aber keine gewünschten Tracks."

Höchstwahrscheinlich gab es in dem Moment, in dem jeder *Use
requests*-Slot aufgelöst wurde (ein paar Minuten bevor dieser Slot
lief), keine *offenen* Requests, also fiel er auf einen zufälligen
Katalog-Track zurück (§5). Senden Sie einen Request, solange noch ein
Request-Slot vor dem Play-Head liegt, dann wird er gezogen; sonst läuft
er in der nächsten Request-Show. Prüfen Sie außerdem, dass der
Request-Block der Playlist **Use requests** angekreuzt hat und seine
Kriterien zum Genre der gewünschten Tracks passen.

### „Mehrere Request-Slots spielten denselben Song."

Das sollte nicht passieren — die Befüllung verbraucht jeden Request
beim Einplanen, sodass aufeinanderfolgende Slots verschiedene Tracks
ziehen. Sehen Sie Duplikate, hängt die Playlist wahrscheinlich die
*ganze* Playlist wiederholt an (altes Verhalten); stellen Sie sicher,
dass Sie auf einem Build mit Position-für-Position-Befüllung sind
(ARCHITECTURE §23.23).

### „Am Ende einer Request-Show ist Dead Air."

Dem abschließenden „verbleibende Zeit"-Block gingen die geeigneten
Tracks aus. Geben Sie ihm **Tracks wiederholen = ja**, erweitern Sie
seine Genre-Kriterien oder lockern Sie ein „kürzlich gespielte
Künstler ausschließen"-Fenster, damit er den ganzen Rest füllen kann.

### „Requests treffen ein, nachdem die Show schon begann — laufen sie?"

Ja — wenn beim Eintreffen des Requests noch ein *Use requests*-Slot vor
dem Play-Head liegt. Die Show füllt sich **inkrementell** (§5), sodass
ein weiter hinten in der Dramaturgie aufgelöster Slot die Wünsche zieht,
die eingingen, während die Show auf Sendung war. Ein Request, der
eintrifft, nachdem der letzte Request-Slot der Show schon aufgelöst
wurde, läuft in der nächsten Request-Show — verteilen Sie die
Request-Slots also über die Dramaturgie, damit späte Wünsche einen Slot
zum Landen haben.

### „Kann ich Requests vor der Ausstrahlung moderieren?"

Es gibt bewusst keine Moderations-Queue. Die Schutzmechanismen sind
die Pool-Beschränkung (nur Katalog-Tracks), das Rate-Limit und das
De-Duplizierungs-Fenster (§6). Brauchen Sie strengere Kontrolle,
verengen Sie die Kriterien des Pool-Blocks.

---

## Wohin als Nächstes

* [Bibliothek](./LIBRARY.md) → §3 Smart Blocks — das *Use
  requests*-Kriterium und die Sortierungen liegen hier.
* [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) — die
  Dramaturgie-Playlist und ihr abschließender „verbleibende
  Zeit"-Block.
* [Öffentliche Embed-Widgets](./WIDGETS.md) — das Request-Widget
  neben den anderen öffentlichen Widgets einbetten.
* [Einstellungen](./SETTINGS.md) — der Song-Request-Pool-Picker und
  der Allow-3rd-party-API-Schalter.
