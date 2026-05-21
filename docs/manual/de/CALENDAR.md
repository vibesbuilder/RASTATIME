# Kalender

> **Wo Sie sich im Handbuch befinden.** Dies ist eines der
> Kapitel zum **täglichen Sendebetrieb**. Viele andere
> Kapitel im Handbuch enden mit "Ziehen Sie aus der
> Bibliothek auf eine Sendung im Kalender" — dieses Kapitel
> erklärt die Empfängerseite. Lesen Sie
> [Bibliothek](./LIBRARY.md) zuerst, falls noch nicht
> geschehen.

Der **Kalender** ist der Ort, an dem Sie planen, was auf
Sendung geht. Jeder Slot der Sendezeit ist entweder:

- Eine **Sendung**, die Sie auf den Kalender gestellt haben,
  oder
- Sendezeit, die der [Auto DJ](./AUTO_DJ.md) füllt (wenn
  aktiviert), oder
- Der konfigurierte Fallback / Stille (wenn keines der
  beiden zutrifft).

Dieses Kapitel deckt alles ab, was Sie *mit* dem Kalender
tun können. Was *innerhalb* einer Sendung abgespielt wird —
Tracks, Smart Blocks, Playlists — wird in
[Bibliothek](./LIBRARY.md) und in den Feature-Kapiteln
behandelt.

---

## 1. Die Kalenderseite

Kalender → öffnet standardmäßig die Wochenansicht.

```
  ┌──────────────────────────────────────────────────────────────────────┐
  │  ◀ Heute ▶            18.–24. Mai 2026             [Tag][Woche][Monat]│
  ├──────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┤
  │      │   Mo 18  │   Di 19  │   Mi 20  │   Do 21  │   Fr 22  │   Sa 23  │
  ├──────┼──────────┼──────────┼──────────┼──────────┼──────────┼──────────┤
  │ 08   │■ Morgen- ■        │■ Morgen-  │■ Morgen-  │■ Morgen-  │          │
  │      │■ sendung ■        │■ sendung  │■ sendung  │■ sendung  │          │
  │ 09   │           │           │           │           │           │          │
  │ 10   │■ Music    │           │           │■ Nach-    │■ Music    │          │
  │      │■ Hour     │           │           │■ richten  │■ Hour     │          │
  │ 11   │           │           │           │           │           │          │
  │      │           │           │           │           │           │          │
  └──────┴──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘
```

### Ansichten wechseln

| Schaltfläche | Was Sie sehen |
|---|---|
| **Tag** | Ein Tag, Stundenzeilen, große Lücken für leere Slots. Am besten für "Was läuft heute"-Planung. |
| **Woche** | Sieben Tage, Standard. Am besten für wöchentliche Programmplanung. |
| **Monat** | Ein Monats-Raster, Sendungen als farbige Balken über Tage. Am besten für "Ist die Woche von X voll?"-Übersicht. |

Die Pfeil-Schaltflächen springen um den sichtbaren Bereich
(ein Tag / eine Woche / ein Monat). Die **Heute**-Schaltfläche
springt zurück zur aktuellen Periode.

### Was die Farben bedeuten

Jede Sendung hat ihre eigene Hintergrundfarbe und Textfarbe
(auf dem Bearbeitungsformular der Sendung gesetzt). Verwenden
Sie dies, um:

- Wiederkehrende von einmaligen Sendungen zu unterscheiden
  (z.B. alle wiederkehrenden Sendungen auf dunklem
  Hintergrund).
- Programme nach Genre hervorzuheben (Nachrichten = rot,
  Musik = blau, Community = grün).
- Spezielle Programmierung zu markieren (Live-Remote = gelb).

Die Farbe hat keine funktionale Bedeutung — sie ist rein
visuell.

### Der Füll-Balken pro Sendung

Innerhalb jedes Sendungs-Blocks ist ein dünner horizontaler
Balken am unteren Rand. Er zeigt den **Füllstand** — wie
viel Prozent der Sendungsdauer tatsächlich eingeplant ist.

| Füll-Balken | Bedeutung |
|---|---|
| (leer) | 0 % eingeplant — die Sendung fällt durch auf Fallback / Stille |
| Halb gefüllt | Etwa die Hälfte der Dauer ist eingeplant |
| Voll | 100 % — jede Sekunde der Sendung hat Inhalt |
| Solide rote Spitze | Über 100 % — Items wären über das Slot-Ende hinausgelaufen und wurden getrimmt |

> **Operator-Tipp.** Der Füll-Balken aktualisiert sich
> automatisch alle 60 Sekunden, sodass Sie beobachten
> können, wie sich der Balken von leer zu voll bewegt, wenn
> eine [Autoloading Playlist](./AUTOLOADING_PLAYLISTS.md)
> im Hintergrund eine Sendung baut, ohne die Seite neu zu
> laden. Vor 2026-05-20 mussten Sie manuell neu laden; das
> wurde in Commit 9484db6 behoben.

> **Wie es unter der Haube funktioniert.** Der Prozentsatz
> des Balkens ist `cc_show_instances.time_filled / (ends_at
> − starts_at)` × 100, abgerufen über den JSON-Endpunkt
> `/Schedule/event-feed`. Die 60-s-Aktualisierung ist
> `setInterval(refetchEvents, 60_000)` in
> `full-calendar-functions.js`, gegated auf
> `$cal.is(":visible")`, sodass die AJAX-Abfrage pausiert,
> wenn der Operator auf einem anderen Tab ist.

---

## 2. Eine Sendung erstellen

Zwei Wege:

### 2.1 Aus dem Kalender-Raster

Klicken Sie auf eine beliebige leere Zelle im Kalender.

- Einzelklick auf eine Zelle in der **Wochen**- oder
  **Tages**-Ansicht öffnet **Neue Sendung** zu dieser
  Stunde.
- Einzelklick auf einen Tag in der **Monats**-Ansicht öffnet
  **Neue Sendung** zu 09:00 dieses Tages.
- Rechtsklick auf eine beliebige leere Zelle zeigt ein
  Kontextmenü mit **Neue Sendung** + **Vorlage anwenden**.

### 2.2 Aus der Symbolleiste

Kalender → **+ Neue Sendung** oben rechts auf der Seite.
Standardmäßig "jetzt + 1 Stunde" mit 60 Minuten Dauer.

### Das Formular "Neue Sendung"

Das Formular ist in einklappbare Abschnitte unterteilt.
**Was** und **Wann** sind Pflicht; der Rest kann bei
Standardwerten bleiben.

| Abschnitt | Zweck |
|---|---|
| **Vorlagen** | Das Formular aus einer gespeicherten [Sendungs-Vorlage](./SHOW_TEMPLATES.md) vorausfüllen oder das aktuelle Formular nach Abschluss als Vorlage speichern. Versteckt beim Bearbeiten einer einzelnen Instanz einer wiederkehrenden Sendung. |
| **Was** | Name, URL, Genre, Beschreibung, Hosts, Hintergrund- / Textfarben, Sendungs-Bild. Das sichtbare Label im Kalender. |
| **Wann** | Startdatum / Uhrzeit, Dauer, Enddatum, Wiederholungen. |
| **Live-Stream-Eingabe** | Remote-Hosts erlauben, die Sendung via Show DJ zu übernehmen (Pro-Sendung-Benutzername + Passwort). |
| **Aufnahme** | Ankreuzen, um den On-Air-Output der Sendung in eine Datei aufzuzeichnen. Siehe [Aufnahme pro Sendung](./RECORD_PER_SHOW.md). |
| **Autoloading Playlist** | Eine Playlist anhängen, um jede Instanz automatisch zu füllen. Siehe [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md). |
| **Wer** | Zusätzliche Hosts über den primären unter Was gesetzten hinaus. |
| **Style** | Hintergrundfarbe, Textfarbe, Sendungs-Bild (sichtbar nur hier für einmalige Sendungen; für wiederkehrende Sendungen bleiben diese über Instanzen hinweg konstant). |

> **Operator-Tipp.** Wenn Sie im Begriff sind, denselben
> Namen, dieselben Hosts, Farben und Autoloading Playlist
> wie letzte Woche einzugeben, halten Sie inne und prüfen
> Sie zuerst das **Vorlagen**-Dropdown. Wenn die Vorlage
> existiert, füllt das Wählen sechs von sieben Abschnitten
> mit einem Klick aus. Wenn nicht, erstellen Sie sie jetzt
> über die **Als Vorlage speichern**-Schaltfläche am Ende
> des Abschnitts.

### Warum das Formular Ihr Speichern ablehnt

Häufige Gründe:

| Fehler | Ursache |
|---|---|
| "Cannot schedule overlapping shows." | Eine andere Sendung belegt bereits eine oder mehrere Sekunden des Slots. RASTATIME erlaubt keine überlappenden Sendungen. |
| "Start time must be in the future." | Einmalige Sendungen müssen mindestens 1 Minute ab jetzt starten. |
| "End time must be after start time." | Selbsterklärend; prüfen Sie Dauer und Enddatum. |
| "You are not allowed to schedule show *X*." | Sie haben einen anderen DJ als Host ausgewählt, aber Sie sind kein Admin. DJs können nur sich selbst als Host setzen. |

Wenn das Formular mit einem generischen "Save failed"-Toast
und ohne sichtbare Pro-Feld-Nachricht ablehnt, prüfen Sie
das Operator-Log (`C:\rastatime\logs\error.log`). RASTATIME
2026-05-17 fügte diagnostisches Logging für den
Pass/Fail-Zustand der Sub-Formulare hinzu, sodass
"validateShowForms FALSE: what=1 when=0 …" erscheinen sollte
und auf das beleidigende Sub-Formular hinweist.

---

## 3. Eine bestehende Sendung bearbeiten

Klicken Sie auf die Sendung → Kontextmenü → wählen Sie eine
Aktion.

### Aktionsmenü

| Aktion | Effekt | Verfügbar wenn |
|---|---|---|
| **Tracks einplanen** | Den Show-Builder öffnen, um Items hinzuzufügen / zu entfernen / umzuordnen. | Immer |
| **Vorlage anwenden** | Eine [Sendungs-Vorlage](./SHOW_TEMPLATES.md) auf diese Sendung stempeln; ersetzt die Formularfelder. | Nur zukünftige Sendungen |
| **Als Vorlage speichern** | Die aktuellen Sendungseinstellungen als neue Vorlage speichern. | Immer |
| **Ansehen** | Lese-Ansicht der Metadaten der Sendung + Sendeplan. | Immer |
| **Sendung bearbeiten** | Die Sendungsdefinition bearbeiten (Name, Zeit, Wiederholungen usw.). | Zukünftige oder aktuelle Sendungen |
| **Instanz bearbeiten** | Nur dieses eine Vorkommen einer wiederkehrenden Sendung bearbeiten. | Nur wiederkehrende Sendungen |
| **Sendung abbrechen** | Die Sendung *jetzt* beenden — nur für die aktuell laufende Sendung sinnvoll. | Nur aktuelle Sendung |
| **Sendung löschen** | Die gesamte Sendung + alle Instanzen entfernen. | Nur zukünftige Sendungen |
| **Diese Instanz löschen** | Nur dieses eine Vorkommen einer wiederkehrenden Sendung entfernen. | Wiederkehrende Sendungen, nur zukünftige |
| **Sendeplan leeren** | Den geplanten Inhalt der Sendung löschen, aber den leeren Slot behalten. | Nur zukünftige Sendungen |

> **Warum "Sendung bearbeiten" vs "Instanz bearbeiten".**
> Eine wöchentliche Sendung ist eine *Definition* mit vielen
> *Instanzen*. Das Bearbeiten der Definition ändert jede
> zukünftige Instanz (z.B. Verschieben der Sendung von
> Montagen auf Dienstage). Das Bearbeiten einer einzelnen
> Instanz erzeugt eine Pro-Vorkommen-Übersteuerung (z.B.
> diese eine Woche ist der Host anders). Die Instanz-
> Übersteuerung überlebt die nächste Definitionsbearbeitung,
> propagiert sich aber nicht auf Geschwister.

### Was "Instanz bearbeiten" nicht kann

- Kann keine Sendungs-Vorlage anwenden. Vorlagen gelten nur
  für ganze Sendungen, weil das Stempeln einer Vorlage auf
  eine Instanz entweder still auf Geschwister propagieren
  würde (verletzt das Einweg-Stempel-Modell) oder keinen
  Effekt auf sie haben würde (was den Operator in die Irre
  führen würde). RASTATIME 2026-05-19 unterdrückt den
  Vorlagen-Abschnitt im Instanz-Bearbeiten-Formular aus
  diesem Grund.
- Kann den Start/Ende der Instanz nicht auf eine Zeit
  außerhalb des Wiederholungsmusters der übergeordneten
  Sendung ändern.

---

## 4. Wiederkehrende Sendungen

Eine wiederkehrende Sendung ist eine Definition mit vielen
Instanzen, die eifrig bis zu einem konfigurierbaren Horizont
(standardmäßig ~3 Monate) materialisiert werden.

### Eine wiederkehrende Sendung erstellen

Im Abschnitt **Wann** kreuzen Sie **Wiederholt sich** an.
Drei Unterfelder erscheinen:

| Feld | Bedeutung |
|---|---|
| **Wiederholungstyp** | Wöchentlich / Zweiwöchentlich / Dreiwöchentlich / Monatlich. |
| **Tage** | Welche Wochentage (für Wöchentlich / Zweiwöchentlich / Dreiwöchentlich). |
| **Enddatum** | Optional — wann die Wiederholung stoppt. Leer lassen, um unbegrenzt zu wiederholen. |

> **Operator-Tipp.** Eine monatliche Sendung, die "am
> dritten Freitag" wiederkehrt, wird *nicht* direkt
> unterstützt. Am nächsten kommt "wöchentlich, Freitag, aber
> an einen 4-Wochen-Zyklus gebunden" — einfacher, die vier
> monatlichen Vorkommen als einmalige Sendungen zu planen.

### Eine wiederkehrende Sendung bearbeiten

- **Sendung bearbeiten** ändert die Definition: jede
  zukünftige Instanz übernimmt die Änderung.
  Vergangene Instanzen bleiben wie sie waren.
- **Instanz bearbeiten** erzeugt eine
  Pro-Vorkommen-Übersteuerung (siehe oben).
- **Diese Instanz löschen** entfernt nur dieses eine
  Vorkommen.
- **Sendung löschen** entfernt die gesamte Serie inklusive
  aller zukünftigen Instanzen.

> **Wie es unter der Haube funktioniert.** Wiederkehrende
> Sendungen schreiben eine `cc_show`-Zeile + eine
> `cc_show_days`-Zeile pro Wiederholungstag + `cc_show_instances`-
> Zeilen für jede materialisierte Instanz. Der
> Materialisierungshorizont wird unter Einstellungen →
> Allgemeine Einstellungen konfiguriert. Das Erweitern des
> Horizonts ist O(N) auf bestehenden wiederkehrenden
> Sendungen; das Upgrade-Runbook behandelt, wie man damit
> umgeht.

---

## 5. Drag-and-Drop

Zwei Arten von Drag werden auf dem Kalender unterstützt:

### 5.1 Eine Sendung verschieben

Klicken und ziehen Sie eine beliebige zukünftige
Sendungs-Block auf eine andere Zeit / einen anderen Tag.

- Snap ist standardmäßig 15 Minuten (konfigurierbar unter
  Allgemeine Einstellungen).
- Das Ziehen respektiert die Nicht-Überlappungs-Regel: das
  Ablegen auf einem belegten Slot wird mit einem roten
  Flash abgelehnt.
- Für eine wiederkehrende Sendung wird nur *diese Instanz*
  verschoben — der Rest der Serie bleibt.

### 5.2 Eine Sendung skalieren

Bewegen Sie den Mauszeiger über die untere Kante einer
Sendung; der Cursor wird zu einem Doppelpfeil. Ziehen Sie
nach unten zum Verlängern, nach oben zum Verkürzen.

- Snap ist standardmäßig 15 Minuten.
- Eine Skalierung kann die Sendung nicht über eine
  Nachbarsendung hinausschieben (würde überlappen) oder
  unter 5 Minuten (die minimale Sendungsdauer).

### Was nicht gezogen werden kann

- Vergangene Sendungen (Geschichte kann nicht rückwirkend
  geändert werden).
- Die aktuell auf Sendung befindliche Sendung (verwenden
  Sie stattdessen **Sendung abbrechen**).
- Sendungen, die Sie nicht besitzen (außer Sie sind
  Program Manager oder Admin).

---

## 6. Das Kalender-Kontextmenü — Vollständige Referenz

Rechtsklick auf eine beliebige Sendung:

| Gruppe | Items |
|---|---|
| Inhalt | Tracks einplanen, Sendeplan leeren |
| Bearbeitung | Sendung bearbeiten, Instanz bearbeiten, Vorlage anwenden, Als Vorlage speichern |
| Lebenszyklus | Sendung abbrechen (nur aktuelle), Sendung löschen, Diese Instanz löschen |
| Info | Sendung ansehen, Aufnahmedatei ansehen (wenn eine Aufnahme existiert) |

Das Menü passt sich dem Zustand der Sendung an — z.B.
**Aufnahmedatei ansehen** erscheint nur, nachdem die
Aufnahme fertig geschrieben wurde.

---

## 7. Die Jetzt-Linie

Eine dünne rote Linie kreuzt den Kalender zur aktuellen
Zeit. Die Linie aktualisiert jede Minute. Sendungen
vollständig links der Linie sind vergangen; Sendungen, die
die Linie gerade kreuzt, sind auf Sendung.

> **Operator-Tipp.** Wenn Sie debuggen "warum spielt jetzt
> die falsche Sendung" — peilen Sie die Jetzt-Linie gegen
> den Kalender an. Die On-Air-Sendung ist der Block, den
> die Jetzt-Linie schneidet. Wenn es keinen Block gibt,
> übernimmt der [Auto DJ](./AUTO_DJ.md) (falls aktiviert)
> oder Fallback / Stille spielt.

---

## 8. Massenoperationen

Kalender → Dropdown **Massenaktionen** oben rechts:

| Aktion | Effekt |
|---|---|
| **Vorlage auf ausgewählte Sendungen anwenden** | Markieren Sie mehrere zukünftige Sendungen im Raster; die Massenaktion restempelt jede aus derselben Vorlage. |
| **Ausgewählte Sendungen löschen** | Jede ausgewählte Sendung löschen. Bestätigungsübersicht listet jede einzelne auf. |

Für größere Umplanungen (z.B. "alles nächste Woche eine
Stunde später wegen Sommerzeit verschieben") unterstützt
der Kalender derzeit keine Massen-Shift-Aktion. Die
Umgehung ist, die verschobene Woche als separate
Sendungs-Vorlage zu definieren und anzuwenden.

---

## 9. Häufig gestellte Fragen

### "Ich habe eine Sendung geplant, aber zur Startzeit spielt nichts."

Drei Möglichkeiten:

1. Die Sendung ist leer (Füll-Balken zeigt 0 %). Öffnen Sie
   Tracks einplanen und fügen Sie mindestens ein Item
   hinzu.
2. Die Sendung hat eine
   [Autoloading Playlist](./AUTOLOADING_PLAYLISTS.md), aber
   die Playlist ist leer.
3. Der **RASTATIME-PLAYOUT**-Dienst läuft nicht. Prüfen Sie
   mit `Get-Service RASTATIME-PLAYOUT`. Siehe
   [`CRASH_RECOVERY`](../../operator/CRASH_RECOVERY.md)
   falls so.

### "Kann eine Sendung eine andere Sendung enthalten?"

Nein. Sendungen sind flach. Eine Sendung enthält
Schedule-Items (Tracks, Smart Blocks, Webstreams, Line-Ins).
Um verwandten Inhalt zu gruppieren, verwenden Sie eine
Playlist (die per Referenz in eine andere Playlist
verschachtelt werden kann).

### "Können zwei Sendungen überlappen, wenn sie verschiedene DJs sind?"

Nein. Die "Nicht-Überlappungs"-Regel ist stationsweit, weil
es nur einen Output gibt. Um "zwei gleichzeitige
Produktionen" zu handhaben, verwenden Sie zwei
Output-Streams: jede Sendung zielt auf einen bestimmten
Stream.

### "Was ist die maximale Sendungsdauer?"

Technisch 24 Stunden. Operativ sollten Sie alles über ein
paar Stunden in mehrere Sendungen aufteilen — der
Show-Builder ist für Sendungen typischer Dauer (15 min –
4 h) ausgelegt.

### "Kann ich den Kalender als ICS importieren / exportieren?"

Ja — Read-only-ICS-Export unter `/Calendar/ics/format/ics`.
Nützlich für das Syndizieren des öffentlichen
Programmplans an eine Website oder ein anderes
Kalendersystem. Import wird nicht unterstützt.

---

## Wohin als Nächstes

* [Sendungs-Vorlagen](./SHOW_TEMPLATES.md) — hören Sie auf,
  jede Woche dieselben Sendungseinstellungen einzugeben.
* [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) —
  Sendungen aus einer Playlist sich selbst füllen lassen.
* [Auto DJ](./AUTO_DJ.md) — das System Kalenderlücken für
  Sie füllen lassen.
* [Aufnahme pro Sendung](./RECORD_PER_SHOW.md) — erfassen,
  was auf Sendung war, in einer Datei.
