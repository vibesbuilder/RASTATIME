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

Eine Sendung über Mitternacht erscheint in der Tages- und
Wochenansicht in zwei Teilen, einer an jedem Tag. Beide Teile
zeigen die ganze Sendezeit (z. B. *23:08 - 0:08*), nicht den Anteil
des jeweiligen Tages.

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

> Seit 2026-10-06 ist `time_filled` die ausgelegte Länge (Sendungsstart
> bis Ende der letzten Zeile, Crossfade-Überlappungen eingerechnet) –
> eine Sendung, die der Balken als voll zeigt, ist es auch.

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
| **Vorlagen** | Das Formular aus einer gespeicherten [Sendungs-Vorlage](./SHOW_TEMPLATES.md) vorausfüllen oder das aktuelle Formular nach Abschluss als Vorlage speichern. Versteckt beim Bearbeiten einer einzelnen Episode einer wiederkehrenden Sendung. |
| **Was** | Name, URL, Genre, Beschreibung, Hosts, Hintergrund- / Textfarben, Sendungs-Bild. Das sichtbare Label im Kalender. |
| **Wann** | Startdatum / Uhrzeit, Dauer, Enddatum, Wiederholungen, **Verzögerten Start erlauben** (diese Sendung später beginnen lassen, wenn die vorige überzogen hat — siehe [Verzögerter Sendungsstart](./DELAYED_START.md)). |
| **Live-Stream-Eingabe** | Remote-Hosts erlauben, die Sendung via Show DJ zu übernehmen (Pro-Sendung-Benutzername + Passwort). |
| **Aufnahme** | Ankreuzen, um den On-Air-Output der Sendung in eine Datei aufzuzeichnen. Siehe [Aufnahme pro Sendung](./RECORD_PER_SHOW.md). |
| **Genre** / **Kategorie** | Freitext; beide bieten die Werte, die andere Sendungen schon verwenden, als Vorschläge an (eine abweichende Schreibweise bildet trotzdem eine eigene Gruppe, wählen Sie also einen Vorschlag, wo einer passt).  Die Kategorie gibt es seit 2026-11-10 (sie erscheint, sobald die Datenbank-Migration 0082 gelaufen ist).  Analytics → [Sendeminuten](./ANALYTICS.md) wertet die Minuten je Genre, je Kategorie und je Genre und Kategorie aus. |
| **Own production** (Eigenproduktion) | Ankreuzen bei Eigenproduktionen des Senders: die gesendeten Minuten der Sendung zählen in Analytics → [Sendeminuten](./ANALYTICS.md), ihre Teilnehmenden in Analytics → Teilnehmende (seit 2026-11-03).  Steht im Abschnitt **What** (Was); das Hilfe-Symbol daneben erklärt es kurz. |
| **Hosts involved** (Moderierende) | Erscheint unter **Own production**, sobald es angekreuzt ist (seit 2026-11-04; bis 2026-11-07 *Number of involved people*): wie viele Moderierende in jeder Episode mitwirken, 0-999. Zählt einmal pro Jahr in Analytics → [Teilnehmende](./ANALYTICS.md), egal wie viele Episoden gesendet wurden; die Gäste einer einzelnen Episode werden unter Extras → Teilnehmende eingetragen (**Guests involved**) und dazugezählt. Wird das Häkchen entfernt, bleibt die Zahl erhalten, sie zählt nur nicht mehr. |
| **Autoloading Playlist** | Eine Playlist anhängen, um jede Episode automatisch zu füllen. Siehe [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md). |
| **Wer** | Zusätzliche Hosts über den primären unter Was gesetzten hinaus. |
| **Archivierung** | Produzent, CBA-Konto, die cba.media-Vorgaben und das automatische Archivieren der Sendung (in Episode bearbeiten seit 2026-11-04 schreibgeschützt). Siehe [Archivierung](./ARCHIVING.md). Seit 2026-11-03. |
| **Style** | Hintergrundfarbe, Textfarbe, Sendungs-Bild (sichtbar nur hier für einmalige Sendungen; für wiederkehrende Sendungen bleiben diese über Episoden hinweg konstant). |

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
| "You are not allowed to schedule show *X*." | Sie wollten Inhalte in eine Sendung einplanen, deren Host Sie nicht sind. DJs planen in die Sendungen ein, deren Host sie sind; Program Manager und Admins in jede Sendung. |

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
| **Ansehen** | Lese-Ansicht der Metadaten der Sendung + Sendeplan. *Start* und *Length* je Zeile sind die ausgelegte Sendeplanzeile (Length = Cue-Out minus Cue-In, wie im Show Builder; seit 2026-10-23); die Summen unten sind die ausgelegte Inhaltslänge (inkl. Cue-Punkten und Crossfade-Überlappungen) gegenüber der Sendungsdauer. | Immer |
| **Extras → Teaser** | Seit 2026-11-10 im Untermenü **Extras** (zusammen mit Online archivieren und Teilnehmende).  Die Jingles, die diese Sendung ankündigen - Typ ändern, lösen, weitere verknüpfen; siehe [Teaser-Automatik](./TEASERS.md). Seit 2026-10-16. | Admin / PM |
| **Extras → Online archivieren** | Titel, Teaser, Beschreibung und Bild dieser einen Episode, vor oder nach der Sendung, und „Jetzt online archivieren“ auf cba.media; siehe [Archivierung](./ARCHIVING.md). Seit 2026-11-03 (zuerst *Episode...* genannt). | Admin / PM / Hosts der Sendung (archivieren: Admin / PM) |
| **Extras → Teilnehmende** | Die Gäste dieser einen Episode (**Gäste**, Guests involved, 0-999), gezählt zusätzlich zu den Moderierenden der Sendung in Analytics → [Teilnehmende](./ANALYTICS.md); die Zeile unter dem Feld zeigt die Moderierenden der Sendung. Seit 2026-11-10 (vorher war das Feld Teil von Online archivieren). | Admin / PM / Hosts der Sendung |
| **Bearbeiten → Episode bearbeiten** | Nur diese eine Episode einer wiederkehrenden Sendung bearbeiten. | Nur wiederkehrende Sendungen |
| **Bearbeiten → Sendung bearbeiten** | Die Sendungsdefinition bearbeiten (Name, Zeit, Wiederholungen usw.). Eine nicht wiederholte Sendung zeigt nur **Sendung bearbeiten**. | Zukünftige oder aktuelle Sendungen |
| **Sendung abbrechen** | Die Sendung *jetzt* beenden — nur für die aktuell laufende Sendung sinnvoll. | Nur aktuelle Sendung |
| **Löschen → Episode löschen** | Nur diese eine Episode einer wiederkehrenden Sendung entfernen. | Wiederkehrende Sendungen, nur zukünftige |
| **Löschen → Episode und alle folgenden löschen** | Diese Episode und alle folgenden Episoden der Sendung entfernen.  Eine nicht wiederholte Sendung zeigt nur **Löschen** und entfernt die Sendung. | Nur zukünftige Sendungen |
| **Sendeplan leeren** | Den geplanten Inhalt der Sendung löschen, aber den leeren Slot behalten. | Nur zukünftige Sendungen |

Eine einzeln bearbeitete Episode einer wiederholten Sendung zeigt nur
**Episode bearbeiten** und **Episode löschen** (bis 2026-11-10 hießen
die Einträge *Instanz bearbeiten* / *Instanz löschen*).

> **Warum "Sendung bearbeiten" vs "Episode bearbeiten".**
> Eine wöchentliche Sendung ist eine *Definition* mit vielen
> *Episoden*. Das Bearbeiten der Definition ändert jede
> zukünftige Episode (z.B. Verschieben der Sendung von
> Montagen auf Dienstage). Das Bearbeiten einer einzelnen
> Episode erzeugt eine Pro-Vorkommen-Übersteuerung (z.B.
> diese eine Woche ist der Host anders). Die Episoden-
> Übersteuerung überlebt die nächste Definitionsbearbeitung,
> propagiert sich aber nicht auf Geschwister.

### Was "Episode bearbeiten" nicht kann

- Kann keine Sendungs-Vorlage anwenden. Vorlagen gelten nur
  für ganze Sendungen, weil das Stempeln einer Vorlage auf
  eine Episode entweder still auf Geschwister propagieren
  würde (verletzt das Einweg-Stempel-Modell) oder keinen
  Effekt auf sie haben würde (was den Operator in die Irre
  führen würde). RASTATIME 2026-05-19 unterdrückt den
  Vorlagen-Abschnitt im Episoden-Formular aus
  diesem Grund.
- Kann den Start/Ende der Episode nicht auf eine Zeit
  außerhalb des Wiederholungsmusters der übergeordneten
  Sendung ändern.
- Kann den Abschnitt **Archivierung** nicht ändern: Er zeigt
  die Werte der Sendung schreibgeschützt (seit 2026-11-04).
  Beschreibung und Bild dieser Episode bearbeiten Sie unter
  **Extras → Online archivieren**, ihre Gäste unter **Extras →
  Teilnehmende**.

---

### Was „Episode bearbeiten" seit 2026-11-03 ändern kann: das Autoloading

Der Abschnitt **Autoloading Playlist** des Episoden-Formulars ist
bearbeitbar.  **Use the show's autoloading settings** (vorangekreuzt)
hält die Episode bei Playlist, Intro, Outro und Wiederholung der
Sendung.  Abgewählt gelten die Felder darunter nur für diese Episode -
eine andere Playlist, gar kein Autoloading, ein anderes Intro oder
Outro.  **Repeat of show** bleibt eine Einstellung der Sendung.

Die Regel **„nur vor der Befüllung"**: Die Autoloading-Befüllung läuft
etwa eine Stunde vor dem Start.  Ist die Episode befüllt, zeigt der
Abschnitt einen Hinweis und lässt sich nicht mehr ändern; leeren Sie die
Episode im Show Builder, dann wird sie mit den aktuellen Einstellungen
neu befüllt.

---

## 4. Wiederkehrende Sendungen

Eine wiederkehrende Sendung ist eine Definition mit vielen
Episoden, die eifrig bis zu einem konfigurierbaren Horizont
(standardmäßig ~3 Monate) materialisiert werden.

### Eine wiederkehrende Sendung erstellen

Im Abschnitt **Wann** kreuzen Sie **Wiederholt sich** an.
Drei Unterfelder erscheinen:

| Feld | Bedeutung |
|---|---|
| **Wiederholungstyp** | Wöchentlich / Zweiwöchentlich / Dreiwöchentlich / Monatlich. |
| **Monate wählen** (seit 2026-10-14) | Nur bei monatlicher Wiederholung: Haken bei den Monaten, in denen die Sendung stattfindet, standardmäßig alle zwölf. Juli und August abwählen für eine Sommerpause, jeden dritten Monat behalten für eine Quartalssendung. Kombinierbar mit *Repeat By* (Tag des Monats / Wochentag). Wird bei einer bestehenden Sendung ein Monat abgewählt, verschwinden ihre künftigen Episoden in diesem Monat. |
| **Tage** | Welche Wochentage (für Wöchentlich / Zweiwöchentlich / Dreiwöchentlich). |
| **Enddatum** | Optional — wann die Wiederholung stoppt. Leer lassen, um unbegrenzt zu wiederholen. |

> **Operator-Tipp.** Eine monatliche Sendung, die "am
> dritten Freitag" wiederkehrt, wird *nicht* direkt
> unterstützt. Am nächsten kommt "wöchentlich, Freitag, aber
> an einen 4-Wochen-Zyklus gebunden" — einfacher, die vier
> monatlichen Vorkommen als einmalige Sendungen zu planen.

### Eine wiederkehrende Sendung bearbeiten

- **Sendung bearbeiten** ändert die Definition: jede
  zukünftige Episode übernimmt die Änderung.
  Vergangene Episoden bleiben wie sie waren.
- **Episode bearbeiten** erzeugt eine
  Pro-Vorkommen-Übersteuerung (siehe oben).
- **Episode löschen** entfernt nur diese eine
  Episode.
- **Episode und alle folgenden löschen** entfernt diese und
  alle zukünftigen Episoden der Serie.
- **Rückgängig nach dem Löschen** (seit 2026-10-28): ein Löschen
  über das Kalendermenü erreicht den Server nicht sofort. Die
  Sendung verschwindet aus dem Kalender, und ein Hinweis am
  unteren Seitenrand zählt zehn Sekunden herunter, mit dem Link
  **Rückgängig**. Ein Klick darauf bringt die Sendung unverändert
  zurück; läuft der Zähler ab, wird wie bisher gelöscht. Wird die
  Seite innerhalb der zehn Sekunden geschlossen, geht das Löschen
  trotzdem ab. *Sendung abbrechen* für die laufende Sendung ist
  nicht verzögert und wirkt sofort wie immer.

> **Wie es unter der Haube funktioniert.** Wiederkehrende
> Sendungen schreiben eine `cc_show`-Zeile + eine
> `cc_show_days`-Zeile pro Wiederholungstag + `cc_show_instances`-
> Zeilen für jede materialisierte Episode. Der
> Materialisierungshorizont wird unter Einstellungen →
> Allgemeine Einstellungen konfiguriert. Das Erweitern des
> Horizonts ist O(N) auf bestehenden wiederkehrenden
> Sendungen; das Upgrade-Runbook behandelt, wie man damit
> umgeht.

---

### Wiederholung einer anderen Sendung (seit 2026-10-18)

Viele Sendungen laufen einmal und werden einmal wiederholt, an einem
anderen Wochentag oder in einer anderen Woche.  Öffnen Sie das
**Edit-Show**-Formular der Wiederholung, Abschnitt **Wiederholung**
(direkt über Autoloading Playlist), und wählen Sie unter **Wiederholung von Sendung** das
Original.  Von da an wird jede Episode der Wiederholung automatisch
befüllt:

- **Welche Sendungen die Liste anbietet** *(seit 2026-10-27)*: jede
  Sendung, die noch kommt oder gerade läuft, und eine bereits
  gelaufene Sendung (innerhalb der letzten 60 Tage) nur, wenn ihre
  letzte Episode vollständig wiederholbar ist - nur Tracks, oder ihre
  Aufnahme ist importiert.  Eine vergangene Live-Sendung ohne Aufnahme
  wird nicht angeboten: Wählen Sie das Original, bevor es läuft.  Eine
  bereits gespeicherte Quelle bleibt wählbar.
- **Wann**: kurz vor dem Start der Wiederholung (etwa eine Stunde,
  derselbe Vorlauf wie beim Autoloading), nicht am Ende des Originals
  - Korrekturen am Original nach der Ausstrahlung werden so
  mitgenommen.
- **Was**: der Inhalt der **zuletzt beendeten** Episode des Originals
  - Dateien und Webstreams in ihrer Reihenfolge mit den gesendeten
  Cue-Punkten und Blenden, Jingles eingeschlossen.  Die
  Autoloading-Playlist füllt danach die Restzeit.
- **Live-Eingänge und Webstreams** *(seit 2026-10-20, Webstreams seit
  2026-10-21)*: Wird das Original aufgezeichnet
  und ist **Sendungsaufnahmen in die Bibliothek kopieren** aktiv
  (Einstellungen → Lokale Maschine → Show Recording), ersetzt jede
  Line-In- oder Webstream-Zeile des Originals die passende Scheibe seiner Aufnahme -
  Cue-In und Cue-Out sind die Zeitabstände der Zeile zum Sendungsstart,
  die Wiederholung spielt also genau das, was zwischen den Titeln live
  gesendet wurde.  Ein Original ohne Zeilen (reine Live-Sendung) wird
  komplett aus der Aufnahme wiederholt.  Die Befüllung wartet auf den
  Import der Aufnahme, aber nicht länger als bis fünf Minuten vor dem
  Start der Wiederholung; ohne Aufnahme wird ein Webstream wie bisher als
  Live-Zeile kopiert und ein Line-In bleibt draußen.  Die Aufnahme ist vor dem Löschen geschützt, solange eine
  anstehende Wiederholung sie braucht.
- **Wenn das Original noch nicht gelaufen ist** (erste Woche,
  abgesagte Episode): die Wiederholung bleibt ihrer
  Autoloading-Playlist überlassen.
- **Länge**: eine kürzere Wiederholung wird am Ende abgeschnitten wie
  jede überbuchte Sendung; eine längere füllt ihre Autoloading-Playlist
  auf.
- **Ketten** sind erlaubt (C wiederholt B, B wiederholt A); ein Kreis
  wird beim Speichern abgelehnt.  „Wiederholung von Sendung" lässt
  sich nicht mit **Link** kombinieren.
- **Löschen eines Titels**, den das Original gesendet hat, wird
  abgelehnt, solange eine Wiederholung darauf wartet („wird noch für
  die Wiederholung ... am ... gebraucht").  Eine außerhalb von
  RASTATIME von der Platte verschwundene Datei wird übersprungen und
  gezählt.

Im Kalender trägt eine Wiederholung ein **Wiederholungs-Symbol**
(zwei Pfeile, seit 2026-10-21) statt der roten Markierung „leer" oder
„teilweise gefüllt" - wie die Uhr einer Autoloading-Sendung, denn sie
wird von selbst befüllt; mit der Maus über dem Symbol erscheint der
Name des Originals.

**View Show** einer befüllten Wiederholung zeigt „Wiederholung von
Sendung A vom <Datum> um <Zeit>" und, falls Zeilen übersprungen
wurden, wie viele.  Eine Episode, die bereits Inhalt hat (von Hand
befüllt), wird nie überschrieben.  Aufgezeichnete Live-Sendungen
lassen sich so noch nicht wiederholen (Stufe 2, siehe BACKLOG).

## 5. Drag-and-Drop

Zwei Arten von Drag werden auf dem Kalender unterstützt:

### 5.1 Eine Sendung verschieben

Klicken und ziehen Sie eine beliebige zukünftige
Sendungs-Block auf eine andere Zeit / einen anderen Tag.

- Die Sendung rastet im Raster-Intervall ein, das Sie im
  Auswahlfeld oben links im Zeitraster wählen (1, 5, 10, 15, 30
  oder 60 Minuten; 10 Minuten, solange Sie nichts anderes gewählt
  haben, pro Benutzer gespeichert).
- Das Ziehen respektiert die Nicht-Überlappungs-Regel: das
  Ablegen auf einem belegten Slot wird mit einem roten
  Flash abgelehnt.
- Für eine wiederkehrende Sendung wird nur *diese Episode*
  verschoben — der Rest der Serie bleibt.

### 5.2 Eine Sendung skalieren

Bewegen Sie den Mauszeiger über die untere Kante einer
Sendung; der Cursor wird zu einem Doppelpfeil. Ziehen Sie
nach unten zum Verlängern, nach oben zum Verkürzen.

- Sie rastet im selben Raster-Intervall ein wie beim Verschieben.
- Eine Skalierung kann die Sendung nicht über eine
  Nachbarsendung hinausschieben (würde überlappen) oder
  unter 5 Minuten (die minimale Sendungsdauer).

### Was nicht gezogen werden kann

- Vergangene Sendungen (Geschichte kann nicht rückwirkend
  geändert werden).
- Die aktuell auf Sendung befindliche Sendung (verwenden
  Sie stattdessen **Sendung abbrechen**).
- Jede Sendung, außer Sie sind Program Manager oder Admin
  (DJs verschieben und verlängern keine Sendungen).

---

## 6. Das Kalender-Kontextmenü — Vollständige Referenz

Rechtsklick auf eine beliebige Sendung:

| Gruppe | Items |
|---|---|
| Inhalt | Tracks einplanen, Sendeplan leeren |
| Bearbeitung | Bearbeiten → Episode bearbeiten / Sendung bearbeiten, Vorlage anwenden, Als Vorlage speichern |
| Lebenszyklus | Sendung abbrechen (nur aktuelle), Löschen → Episode löschen / Episode und alle folgenden löschen (nicht wiederholte Sendung: nur Löschen) |
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

### "Was passiert in der Nacht der Zeitumstellung?"

Sendungen sind in Ortszeit definiert und bleiben bei ihrer Ortszeit:
Eine Sendung um 08:00 läuft vor und nach der Umstellung um 08:00.  Eine
Sendung, die *über* die Umstellung läuft, endet zu ihrer lokalen
Endzeit: „22:00 für 8 Stunden" endet in der Herbstnacht um 06:00 (neun
reale Stunden, das Autoloading füllt die zusätzliche Stunde) und in der
Frühlingsnacht um 06:00 (sieben reale Stunden).  Es entsteht weder eine
Lücke noch eine Überlappung mit der folgenden Sendung.  Innerhalb der
Umstellungsstunde selbst (02:00–03:00): Eine Sendung, deren Endzeit im
Frühling nicht existiert, endet eine Stunde später; eine Sendung, die
ganz in der übersprungenen Stunde liegt, behält ihre Dauer; eine
Endzeit, die im Herbst zweimal vorkommt, gilt beim ersten Vorkommen.
Seit 2026-10-16; davor endete eine Sendung über die Umstellung eine
Stunde zu früh (Herbst) bzw. zu spät (Frühling).

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
