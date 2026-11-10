# Analytics

> **Wo Sie sich im Handbuch befinden.** Dies ist ein Kapitel aus
> **Ausgabe und Infrastruktur**, ein Begleiter zu
> [Streams](./STREAMS.md). Streams behandelt das *Konfigurieren*
> Ihrer Ausgänge und deren Live-Überwachung; dieses Kapitel
> behandelt den **Rückspiegel** — was tatsächlich gesendet wurde
> und wie viele Menschen dabei zugehört haben.

Das Menü **Analytics** in der oberen Navigation bündelt acht
Seiten:

| Seite | Frage, die sie beantwortet |
|---|---|
| **Playout History** | Was hat die Station tatsächlich gesendet, Minute für Minute? |
| **History Templates** | Welche Spalten soll das Sendeprotokoll aufzeichnen und exportieren? |
| **Listener Stats** | Wie viele Hörer waren je Stream verbunden, im Zeitverlauf? |
| **Show Listener Stats** | Wie hat jede *Sendung* bei den Hörerzahlen abgeschnitten? |
| **People Involved** (Teilnehmende) | Wie viele Menschen haben die Eigenproduktionen des Senders in einem Jahr gemacht? Siehe § 6 und [Archivierung](./ARCHIVING.md) § 6 (seit 2026-11-03, eigener Menüeintrag seit 2026-11-04). |
| **Programme Minutes** (Sendeminuten) | Wie viele Minuten Eigenproduktion liefen in einem Jahr auf Sendung? Je ein Jahr, CSV. Siehe § 5 (seit 2026-11-03; bis 2026-11-04 Teil des „Jahresberichts"). |
| **Music by Country** (Musik nach Land) | Woher kommt die gesendete Musik (Musikquote)? Je ein Jahr, CSV. Siehe § 7 (seit 2026-11-08). |
| **Archive Status** (Archiv-Status) | Ist jede Episode auf cba.media angekommen? Laufende und wartende Uploads, was das automatische Archivieren vor sich hat, Probleme, Verlauf, CSV. Siehe [Archivierung](./ARCHIVING.md) § 7 (seit 2026-11-04). |

Die ersten beiden existieren für die **Rechenschaftspflicht** —
Tantiemen-Meldungen, Sendeprotokolle für Behörden, Anrufe der Art
„Welcher Track lief um 14:32?". Die letzten beiden existieren für
**Programmentscheidungen** — welche Sendeplätze und Sendungen
tatsächlich Publikum ziehen.

---

## 1. Playout History

**Analytics → Playout History** zeigt alles, was die
Playout-Engine tatsächlich auf Sendung gebracht hat — unabhängig
davon, wie es in den Plan kam (Kalender-Sendung, Auto DJ,
manueller Override, Live-DJ).

Oben grenzt eine **Datum/Uhrzeit-Bereichsauswahl** mit **Filter
History** jede Ansicht auf ein Zeitfenster ein — Standard ist der
aktuelle Tag.

Darunter drei Tabs (DJs sehen nur den dritten, mit den Sendungen,
deren Host sie sind; dort legen sie Einträge an, bearbeiten und
löschen sie - Program Manager und Admins bearbeiten jeden Eintrag):

* **Log Sheet** — das rohe Sendeprotokoll, eine Zeile pro
  gespieltem Element, mit Start-/Endzeit und den
  Metadaten-Spalten, die Ihr aktives Template definiert (siehe
  §2). Diese Ansicht exportieren Sie für
  Verwertungsgesellschaften.
* **File Summary** — dasselbe Zeitfenster aggregiert **pro
  Track**: wie oft jede Datei im Zeitraum lief. Nach jeder Spalte
  sortierbar.
* **Show Summary** — dasselbe Zeitfenster gruppiert **pro
  Episode**. Eine Sendung aufklappen zeigt, was darin
  lief.

> **Operator-Tipp.** Das Log Sheet protokolliert, was die *Engine*
> gespielt hat. Ein Live-DJ, der über den Stream sendet,
> hinterlässt hier keine Zeilen — nur Datei- und
> Webstream-Wiedergabe wird protokolliert.

> **Wie es unter der Haube funktioniert.** Der Playout-Dienst
> schreibt beim Start jedes gesendeten Elements eine Zeile in
> `cc_playout_history` (plus `cc_playout_history_metadata`). Die
> drei Tabs sind DataTables-Ansichten über
> `/playouthistory/{playout-history-feed,file-history-feed,show-history-feed}`,
> alle serverseitig nach dem gewählten Bereich gefiltert.

> **Ein gelöschter Titel behält sein Protokoll (seit 2026-10-08).** Jede
> Datei-Zeile trägt Titel, Interpret, Länge, Komponist und Copyright zum
> Zeitpunkt des Sendens. Wird der Titel aus der Bibliothek gelöscht,
> wird nur der Dateiverweis geleert, die Zeile bleibt und wird aus
> diesen Werten angezeigt - so wie Webstream- und Line-In-Zeilen. Der
> Reiter *File Summary* zählt Titel, die es noch gibt. Vorher löschte
> LibreTime die Protokollzeilen mit dem Titel.

---

## 2. History Templates

**Analytics → History Templates** steuert, **welche
Metadaten-Spalten** Log Sheet und File Summary aufzeichnen und
anzeigen. Es gibt zwei Template-Arten — **Log Sheet Template** und
**File Summary Template** — und von jeder ist genau eine das
aktive Standard-Template.

Felder nach Name und Typ (String / Integer / Datum …) hinzufügen,
ordnen, dann **Set Default Template**. Neue History-Zeilen
zeichnen die Felder des Templates auf, das *zum Sendezeitpunkt*
aktiv ist; ein Template-Wechsel schreibt alte Zeilen nicht um.

> **Operator-Tipp.** Richten Sie Ihr Template **einmal ein, bevor**
> Sie Ihren ersten Tantiemen-Report brauchen, und lassen Sie es
> dann in Ruhe. Die mitgelieferten Felder (Künstler, Titel,
> Sendedatum/-zeit) erfüllen die meisten Meldepflichten.

---

## 3. Listener Stats

**Analytics → Listener Stats** zeichnet die Zahl der **gleichzeitig
verbundenen Hörer pro Stream-Mount** über den gewählten Zeitraum,
eine farbige Linie pro Mount (z.B. `rastatime`,
`rastatime-aac`). Verwenden Sie dieselbe Datum/Uhrzeit-Auswahl wie
in der Playout History; die Checkboxen der Legende blenden
einzelne Mounts ein und aus.

Die Zahlen stammen von Ihrem Streaming-Server und zählen daher
*direkte* Stream-Hörer. Hörer hinter einem Relay, CDN oder
Aggregator erscheinen als **eine** Verbindung.

> **Wie es unter der Haube funktioniert.** Der Playout-Dienst
> fragt alle **120 Sekunden** die `/admin/stats.xml` jedes
> konfigurierten Icecast-Servers mit den Admin-Zugangsdaten aus
> der jeweiligen Stream-Konfiguration ab und speichert einen
> Datenpunkt pro Mount in `cc_listener_count`. Abgefragt werden
> nur Streams, deren **Admin Password** in **Settings → Streams**
> gesetzt ist; Streams ohne Passwort werden mit einer Warnung in
> `logs/playout.log` übersprungen.
> *(Unter Windows wiederhergestellt in RASTATIME 2026-08-30 — auf
> früheren Builds blieb dieses Diagramm leer, weil kein Collector
> lief.)*

**Stream Data Collection Status** (der Kasten rechts, seit
26.10.2026): eine Zeile je aktivem Stream mit seinem Mount.  **OK**
heißt, die letzte Abfrage hat geklappt.  Sonst nennt die Zeile Ursache
und Zeitpunkt: Icecast lehnt Admin-Benutzer/Passwort ab (prüfen Sie sie
unter **Settings → Streams**), ist nicht erreichbar, antwortet nicht
rechtzeitig, liefert eine unlesbare Statistikseite oder antwortet mit
einem anderen Fehler.  Mit der ersten erfolgreichen Abfrage nach dem
Problem springt die Zeile von selbst auf OK zurück - vor dem 26.10.2026
blieb ein Fehler dauerhaft stehen und lautete immer „admin
user/password prüfen“.  Ein Stream ohne Admin Password meldet, dass für
ihn keine Statistik erfasst wird.

**Leeres Diagramm?** In absteigender Wahrscheinlichkeit:

1. Der Dienst **RASTATIME-PLAYOUT** läuft nicht (er beherbergt
   den Collector).
2. Das **Admin Password** des Streams in **Settings → Streams**
   ist leer oder falsch — prüfen Sie `logs/playout.log` auf eine
   Skip-Warnung oder HTTP 401.
3. Sie betrachten einen Zeitraum vor Beginn der Statistik-Erfassung
   — Daten sammeln sich erst ab dem ersten Lauf des Collectors an.

---

## 4. Show Listener Stats

**Analytics → Show Listener Stats** faltet dieselben Hörerdaten
**pro Episode**: Für jede Sendung im gewählten Zeitraum
erhalten Sie die **durchschnittliche** und die **maximale** Zahl
gleichzeitiger Hörer während ihrer Sendezeit.

Das ist die Seite für Programmentscheidungen — vergleichen Sie die
Zahlen einer Sendung über Wochen hinweg oder zwei Sendungen im
selben Sendeplatz.

> **Sendungszahlen brauchen Sendungsdaten.** Eine Sendung, die vor
> Beginn der Hörer-Erfassung lief (oder während Playout gestoppt
> war), zeigt Nullen — die Aggregation kann nur Datenpunkte
> falten, die für das Zeitfenster der Sendung in
> `cc_listener_count` existieren.

## 5. Sendeminuten (seit 2026-11-03)

Die Zahlen für die jährliche Meldung an die Behörden stehen auf zwei
Seiten, jede mit einer Jahresauswahl (Senderzeit; das laufende Jahr bis
heute): **Analytics → Programme Minutes** (Sendeminuten, dieser
Abschnitt) und **Analytics → People Involved** (Teilnehmende, § 6).  Bis
2026-11-04 waren beide eine Seite, der „Jahresbericht" (Yearly Report).

Kreuzen Sie **Own production** (Eigenproduktion) in einer Sendung an
(Edit Show → What; das Hilfe-Symbol daneben erklärt es kurz; einmalig
oder wiederholend, Vorlagen und Import/Export tragen es als
`own_production`).  Die Seite zählt die
Episoden markierter Sendungen, die im Jahr gesendet wurden - beendet,
nicht gelöscht, keine alte Rebroadcast-Episode - mit ihrer **geplanten**
Dauer, je Sendung und Monat auf Minuten gerundet.  Sendungen, die als
[Wiederholung einer anderen Sendung](./CALENDAR.md) angelegt sind,
stehen in einer eigenen Spalte (Erstausstrahlungen gegenüber
Wiederholungen), weil die meisten Behörden sie getrennt abfragen.
Sendungen ohne Häkchen erscheinen ausgegraut mit ihren Minuten unter
„andere Sendungen (nicht gezählt)", damit sichtbar bleibt, was fehlt.
Eine Monatstabelle und **Download CSV (minutes)** (je Sendung, Summen,
je Monat) runden den Abschnitt ab.

Program Managers und Admins öffnen diese Seite.

## 6. Teilnehmende (seit 2026-11-03)

**Analytics → People Involved** (Teilnehmende) zählt die Menschen, die
die **Eigenproduktionen** des Senders in einem Jahr gemacht haben.  Seit
2026-11-07 gilt: **People involved** (Teilnehmende) = die **Hosts
involved** (Moderierende; Edit Show → What, unter **Own production**;
das Feld erscheint, sobald das Kästchen angekreuzt ist), gezählt
**einmal pro Jahr**, + die **Guests involved** (Gäste) jeder gesendeten
Episode (Archive Online bzw. Online archivieren im Kalender), gezählt
**je Episode**.  Nur Sendungen mit **Own production** zählen - eine
Sendung ohne Häkchen behält ihre Zahl, bleibt aber außen vor, bis sie
wieder angekreuzt ist; Wiederholungssendungen (*Repeat of*) stehen in
der Liste, zählen aber nichts.  **Only shows without a
value** (Nur Sendungen ohne Wert) und **Download CSV** (CSV
herunterladen) helfen bei der Jahresmeldung.  Die Einzelheiten stehen in
[Archivierung](./ARCHIVING.md) § 6.

Program Managers und Admins öffnen diese Seite.

## 7. Musik nach Land (seit 2026-11-08)

**Analytics → Music by Country** (Musik nach Land) zeigt, woher die
Musik kommt, die in einem Jahr auf Sendung ging - die Musikquote des
Senders.  Je ein Jahr (Senderzeit; das laufende Jahr bis heute).

Gezählt werden die Ausstrahlungen in der Playout History (§ 1) von
Tracks, deren Track-Typ den Code `music` hat (Settings → Track Types);
Tracks eines anderen Typs oder ohne Typ zählen nicht.  Jede
Ausstrahlung zählt mit dem Land ihres Tracks, wie es heute eingetragen
ist (Edit Track → **Land**, beim Import aus dem Tag `Country` gelesen -
siehe [Bibliothek](./LIBRARY.md)); ein korrigiertes Land korrigiert also
auch die vergangenen Ausstrahlungen.  Ein Track ohne Land zählt als
**Kein Land**; eine Kombination wie `Germany/Switzerland` ist eine
eigene Zeile.

Die Seite zeigt die Minuten Musik, die Ausstrahlungen, die Zahl der
Länder und den Anteil der Minuten mit Land; eine Tabelle je Land
(Ausstrahlungen und Minuten mit ihren Anteilen, nach Minuten sortiert,
*Kein Land* zuletzt); eine Tabelle je Monat (Ausstrahlungen, Minuten,
Minuten mit Land und deren Anteil); und die **25 meistgespielten
Musiktitel ohne Land** - tragen Sie deren Land ein, wird der Bericht
vollständiger.  **CSV herunterladen** enthält zusätzlich die Minuten je
Land und Monat.

Nicht gezählt, weil sie nicht in der Playout History stehen: Musik, die
DJs live spielen, Line-Ins und Webstreams sowie Ausstrahlungen von
inzwischen gelöschten Tracks.  Die Historie beginnt mit der ersten
protokollierten Ausstrahlung der Installation; beginnt sie später im
Jahr, sagt die Seite das.

Program Managers und Admins öffnen diese Seite.
