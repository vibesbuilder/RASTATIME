# Dashboard

> **Wo Sie sich im Handbuch befinden.** Das Dashboard ist
> die erste Seite, die Operatoren nach der Anmeldung
> erreichen. Es zeigt den Stationszustand auf einen Blick
> und bietet die manuellen Übersteuerungen (Live-Source-
> Schalter, aktuelle-Sendung-Abbrechen), die keinen Ausflug
> in den Kalender benötigen.

Das **Dashboard** beantwortet drei Fragen in einem
Bildschirm:

1. Was ist *gerade* auf Sendung?
2. Was kommt *als Nächstes*?
3. Sind die öffentlichen Streams gesund?

Ein viertes Panel — die **Live-Quelle**-Controls — ist die
Notluke des Operators, um die Station live zu nehmen, ohne
einen separaten Broadcasting-Client zu öffnen.

---

## 1. Das Seitenlayout

Dashboard → standardmäßig die Live-Ansicht.

```
   ┌─────────────────────────────────────────────────────────────────┐
   │  Dashboard                  [Auto-Aktualisierung: 5 s ▾]        │
   ├──────────────────────────────────────────────────────────────────┤
   │                                                                 │
   │  Now Playing                                                    │
   │  ┌────────────────────────────────────────────────────────────┐ │
   │  │   ♪  Tracktitel — Künstler                                 │ │
   │  │      Sendung: Morgensendung  (90 % gefüllt)                │ │
   │  │      Quelle: Scheduler                                     │ │
   │  │      [████████████████░░░░] 03:14 / 03:42                  │ │
   │  └────────────────────────────────────────────────────────────┘ │
   │                                                                 │
   │  Kommt als Nächstes                                             │
   │   • 14:30  Nachrichten        (60 % gefüllt)                    │
   │   • 14:35  Music Hour         (100 % gefüllt)                   │
   │   • 15:35  Auto DJ            (—)                               │
   │                                                                 │
   │  Streams                                                        │
   │   1. /rastatime          ● Verbunden   23 Hörer                  │
   │   2. /rastatime-mobile   ● Verbunden    8 Hörer                  │
   │                                                                 │
   │  Live-Quelle                          [ ☐ Master DJ auf Sendung]│
   │   Show DJ:    Nicht verbunden                                   │
   │   Master DJ:  Nicht verbunden                                   │
   │   [Monitor anhören] [Aktuelle Sendung abbrechen]                │
   └─────────────────────────────────────────────────────────────────┘
```

Die Seite aktualisiert sich alle 5 Sekunden
(konfigurierbar im Dropdown oben rechts — 1 / 5 / 10 / 30
Sekunden oder Manuell).

---

## 2. Now Playing

Das größte Panel. Zeigt das aktuelle Schedule-Item plus
den Kontext für das, was den öffentlichen Stream füttert.

### Felder

| Feld | Bedeutung |
|---|---|
| **♪ Titel — Künstler** | Die Metadaten des aktuell spielenden Items. Für Tracks: Titel + Künstler aus `cc_files`. Für Webstreams: der Anzeigename des Webstreams. Für Line-Ins: der Anzeigename des Line-Ins. Für Auto-DJ: der zugrunde liegende Track + "Auto DJ"-Label. |
| **Sendung** | Die Sendung, zu der dieses Item gehört, + der Gesamt-Füllprozentsatz der Sendung. |
| **Quelle** | Welchen Eingang der Source-Switcher gerade routet — siehe §3. |
| **Fortschrittsbalken** | Verstrichene Zeit / Item-Dauer. Der Balken füllt sich von links nach rechts, während das Item spielt. |

> **Warum der Füllprozentsatz wichtig ist.** Eine Sendung
> mit 60 % Füllung hat 40 % ihres Slots leer. Wenn der
> aktuelle Track endet, erreicht das Playout den leeren
> Schwanz und fällt durch auf Stille (oder Auto DJ, falls
> aktiviert). Der Fortschrittsprozentsatz auf dem
> Now-Playing-Panel ist das Warnsignal, dass dies
> unmittelbar bevorsteht.

### Live-DJ-Übersteuerungs-Erscheinung

Wenn eine Live-DJ-Quelle aktiv ist, ändert sich das Panel:

```
   ┌────────────────────────────────────────────────────────────┐
   │   🎙 LIVE — Show DJ                                         │
   │      Sendung: Late Night                                    │
   │      Quelle: Show DJ (BUTT @ studio-1)                      │
   │      [LIVE — kein Fortschrittsbalken]                       │
   └────────────────────────────────────────────────────────────┘
```

Kein Tracktitel (die Live-Quelle ist offenes Audio), kein
Fortschrittsbalken und ein klarer "🎙 LIVE"-Indikator,
damit der Operator auf einen Blick sehen kann, dass der
Sendeplan nicht das ist, was sendet.

> **Wie es unter der Haube funktioniert.** Das
> Now-Playing-Panel konsumiert `/api/v2/now-playing`, das
> den aktuellen Source-Switcher-Zustand plus das aktive
> Schedule-Item zurückgibt. Der Endpunkt liest aus
> `rastatime_playback_state`, das von der Playout-Engine
> bei jedem Track- / Quellen-Übergang geschrieben wird.
> Siehe ARCHITECTURE §9.

---

## 3. Quellenzustand

Das **Quelle**-Feld auf dem Now-Playing-Panel durchläuft
fünf mögliche Zustände. Zu wissen, welcher davon gerade
auf Sendung ist, ist der Unterschied zwischen "Stream
funktioniert" und "Stream funktioniert, sendet aber das
Falsche".

| Quelle | Was es bedeutet | Wann besorgt sein |
|---|---|---|
| **Scheduler** | Playout spielt, was der Kalender sagt. Der normale Zustand. | Nie. Das ist das Ziel. |
| **Show DJ** | Eine Live-Remote-Quelle hat die Sendung übernommen. Der Sendeplan ist für diese Sendung pausiert. | Wenn Sie keinen Show DJ live erwarten — untersuchen Sie (könnte eine veraltete Verbindung sein, könnte ein falsch konfigurierter Host sein). |
| **Master DJ** | Stationsweite Live-Quelle hat alles übersteuert. | Master DJ sollte nur auf Sendung sein, wenn der Stations-Ingenieur absichtlich übernommen hat. Wenn Sie das sehen und Sie nicht der Ingenieur sind — kontaktieren Sie ihn. |
| **Auto DJ** | Auto-DJ-Füllung ist auf Sendung (entweder eine Auto-DJ-erstellte Sendung oder der Fill-Pass für eine unvollständige Sendung). | Wenn Sie operator-geplanten Inhalt erwartet haben — öffnen Sie den Kalender, um zu sehen, warum der Slot leer ist. |
| **Fallback / Stille** | Nichts ist geplant, Auto DJ ist aus, und die Fallback-Schleife spielt (oder die Station ist still). | Fast immer ein Problem. Öffnen Sie den Kalender, um etwas zu planen. |

### Quellen manuell umschalten

Der Quell-Switch wird **nicht** vom Dashboard-Operator
gesteuert — er wird von der Playout-Engine als Reaktion auf
das Folgende angetrieben:

- Den Kalender (Scheduler-Quelle).
- Einen Remote-DJ, der sich verbindet (Show DJ / Master DJ).
- Auto-DJ-Einspringen (Auto-DJ-Quelle).

Um einen Wechsel zu **erzwingen**:

- **Aktuelle Sendung abbrechen** beendet die laufende
  Sendung sofort, sodass der Source-Switcher zu dem
  vorrückt, was als Nächstes kommt.
- **Master DJ von Sendung nehmen** trennt die
  Master-Quelle (falls verbunden) und kehrt zum Scheduler
  zurück.

Diese Aktionen leben im **Live-Quelle**-Panel — siehe §5.

---

## 4. Kommt als Nächstes

Die nächsten 3-5 kommenden Items (konfigurierbar unter
Allgemeine Einstellungen → Dashboard-Vorausschau).

Jede Zeile zeigt:

| Spalte | Bedeutung |
|---|---|
| **Zeit** | Startzeit der Sendung (HH:MM in Operator-Zeitzone). |
| **Sendungsname** | Der Name der nächsten Sendung. |
| **Füll-%** | Wie gefüllt die Sendung ist. Mauszeiger darüber für einen Tooltip mit den gesamten geplanten Sekunden der Sendung. |

> **Operator-Tipp.** Eine "0 %"- oder "—"-Füllung auf
> einer Sendung, die bald beginnt, ist ein Problem.
> Klicken Sie die Sendung im Kalender und füllen Sie sie
> manuell, oder verlassen Sie sich auf Auto DJ, um sie
> aufzufüllen (falls aktiviert).

---

## 5. Streams

Kompaktansicht derselben Informationen, die Sie aus
Einstellungen → [Streams](./STREAMS.md) erhalten:

| Spalte | Bedeutung |
|---|---|
| **N. /mount** | Stream-Nummer + Mountpoint. |
| **Status-Badge** | Dieselben fünf Badges wie auf der Streams-Einstellungsseite (Verbunden / Verbindet / Getrennt / Deaktiviert / Veraltet). |
| **Hörerzahl** | Live-Zahl, alle 5 s aktualisiert. |

Klicken Sie auf einen Stream → öffnet die Streams-
Einstellungsseite mit Fokus auf diesen Stream.

> **Operator-Tipp.** Diese Kompaktansicht ist, was die
> meisten Operatoren während einer Sendung beobachten —
> aufsteigende Hörerzahlen bedeuten, dass die Sendung
> Menschen erreicht. Stark abfallend (z.B. von 50 auf 5)
> bedeutet, dass Hörer abspringen; prüfen Sie den
> Stream-Status und das On-Air-Audio.

---

## 6. Live-Quelle-Panel

Zwei Controls + zwei Status-Zeilen.

```
   ┌────────────────────────────────────────────────────────────┐
   │  Live-Quelle                       [ ☐ Master DJ auf Sendung]│
   │   Show DJ:    Nicht verbunden                               │
   │   Master DJ:  Nicht verbunden                               │
   │   [Monitor anhören] [Aktuelle Sendung abbrechen]            │
   └────────────────────────────────────────────────────────────┘
```

### Master-DJ-auf-Sendung-Checkbox

Das Kontrollkästchen oben rechts schaltet die
Master-DJ-Übersteuerung um:

| Checkbox | Effekt |
|---|---|
| **Aus** (Standard) | Master DJ ist am Source-Switcher stummgeschaltet, selbst wenn verbunden. Der Scheduler / Show DJ ist auf Sendung. |
| **An** | Master DJ ist auf Sendung, wenn verbunden. Jeder Source-Switcher-Eingang wird übersteuert. |

Nützlich für "der Ingenieur ist verbunden, aber wartet;
der Sendeplan sollte weiterlaufen, bis ich den Schalter
umlege".

> **Warum eine Checkbox und nicht nur "verbunden = auf
> Sendung"?** Das ursprüngliche LibreTime-Modell war
> "Master DJ auf Sendung, wann immer verbunden"; RASTATIME
> 2026-05-15 fügte den expliziten Toggle hinzu, nachdem
> Operator-Feedback besagte, dass ein Ingenieur, der eine
> Verbindung testet, nicht versehentlich eine Live-Sendung
> übernehmen sollte.

### Show-DJ- / Master-DJ-Statuszeilen

Jede Zeile zeigt eines von:

- **Nicht verbunden** — der Quell-Mount empfängt derzeit
  kein Audio.
- **Verbunden (im Leerlauf)** — empfängt Audio, aber nicht
  auf Sendung (entweder ist die Master-DJ-Checkbox aus
  oder eine höher priorisierte Quelle ist aktiv).
- **Verbunden (auf Sendung)** — füttert derzeit den
  öffentlichen Output.

### Monitor anhören

Spielt den Monitor-Ausgang der
[Lokalen Maschine](./LOCAL_MACHINE.md) über Ihren Browser
ab. Nützlich, um zu prüfen, wie der Vorschau-Ausgang der
Operator-Maschine klingt, *ohne* physisch vor den
Lautsprechern sein zu müssen.

> **Browser-Unterstützung.** Die Schaltfläche verwendet
> die Web-Audio-API, die in allen modernen Browsern
> funktioniert. Safari kann nach Mikrofon-Berechtigung
> fragen (es verwendet tatsächlich kein Mikrofon, aber
> Safari verwechselt Audio-Erfassung mit
> Audio-Wiedergabe in einigen Kontexten).

### Aktuelle Sendung abbrechen

Beendet die aktuell spielende Sendung **sofort**.

Effekte:

- Die `cc_show_instances.ends_at` der Sendung wird auf
  "jetzt" gesetzt.
- Der Source-Switcher rückt zu dem vor, was als Nächstes
  im Sendeplan war (oder zu Auto DJ, falls keine nächste
  Sendung, oder zu Fallback / Stille).
- Wenn die Sendung aufgezeichnet wurde
  (Aufnahme pro Sendung), stoppt die Aufnahme grazil
  (FFmpeg SIGTERM, Datei finalisiert).
- Ein mit dieser Sendung verbundener Show DJ wird gekickt.

> **Operator-Tipp.** Verwenden Sie **Aktuelle Sendung
> abbrechen** sparsam — der Abbruch ist irreversibel. Um
> eine Sendung kürzer zu machen, ohne sie sofort zu
> beenden, bearbeiten Sie die Sendung im Kalender und
> ändern Sie die Endzeit; das wirkt sich auf die *nächste*
> Episode aus und ist reversibel.

---

## 7. Häufig gestellte Fragen

### "Das Now-Playing-Panel sagt 'Stille'. Was bedeutet das?"

Die Playout-Engine läuft, keine Sendung ist aktuell, kein
Auto DJ ist aktiviert, und keine Fallback-Schleife ist
konfiguriert. Der öffentliche Stream ist Stille.

Lösung: Öffnen Sie den Kalender und planen Sie eine
Sendung, oder aktivieren Sie [Auto DJ](./AUTO_DJ.md).

### "Die Quelle ist 'Scheduler', aber ich höre nichts auf dem öffentlichen Stream."

Drei Möglichkeiten:

1. Das aktuell geplante Item ist selbst still (z.B. ein
   30-Sekunden-Silence-Stinger). Prüfen Sie den Track.
2. Die Icecast-Verbindung ist offen, aber die Kodierung
   ist still (operator-maschinen-seitiges Audio-Geräte-
   Problem). Prüfen Sie Einstellungen →
   [Streams](./STREAMS.md) für den Verbindungszustand.
3. Der Browser-Tab ist stummgeschaltet (prüfen Sie den
   kleinen Stumm-Indikator auf dem Tab selbst).

### "Warum hängt die Seite manchmal ein paar Sekunden hinter der Realität?"

Der Now-Playing-Endpunkt aktualisiert alle 5 Sekunden; die
Anzeige zeigt, was die letzte Aktualisierung zurückgegeben
hat. Für Sub-Sekunden-Genauigkeit bräuchten Sie einen
Streaming-Endpunkt (WebSocket / SSE); derzeit nicht
implementiert.

### "Kann ich das Dashboard ohne Anmeldung sehen?"

Nein — das Dashboard erfordert Authentifizierung. Für eine
unauthentifizierte öffentliche "Was läuft"-Seite verwenden
Sie das Embed-Widget unter `/embed/now-playing`, das nur
den Now-Playing-Titel exponiert (keine Quelle, keine
Hörerzahlen, keine Controls).

### "Warum fällt die Hörerzahl für einen Aktualisierungszyklus auf null?"

Icecast setzt den Hörerzähler kurz zurück, wenn die Quelle
sich neu verbindet (jedes Mal, wenn die Bitrate sich
ändert, der Stream neu startet oder die Quelle kurz
trennt). Die nächste 5-s-Aktualisierung zeigt die Zahl
wieder. Wenn der Abfall persistiert, ist der Stream
tatsächlich nicht erreichbar — untersuchen Sie.

---

## Wohin als Nächstes

* [Kalender](./CALENDAR.md) — was "Kommt als Nächstes"
  bevölkert.
* [Streams](./STREAMS.md) — vollständiges Detail über
  jeden Output-Stream.
* [Auto DJ](./AUTO_DJ.md) — was die Lücken füllt, wenn
  keine Sendung aktuell ist.
* [Lokale Maschine](./LOCAL_MACHINE.md) — der
  Monitor-Ausgang, den die Schaltfläche **Monitor
  anhören** verwendet.
