# Öffentliche Embed-Widgets

> **Wo Sie sich im Handbuch befinden.** Dieses Kapitel
> behandelt die Drop-in-Widgets, die eine externe Website
> (Ihre Stations-Homepage, eine Partner-Seite, ein
> Info-Bildschirm) per einfachem `<iframe>` einbetten
> kann. Die Widgets ziehen RASTATIMEs Live-Daten und
> benötigen keine Anmeldung — sie sind für die
> Öffentlichkeit sichtbar.

RASTATIME liefert eine kleine Familie von HTML-Widgets,
die externe Seiten einbetten können, um anzuzeigen, was
gerade auf Sendung ist, was als Nächstes kommt, das
Wochenprogramm usw. Jedes Widget ist eine eigenständige
iframe-URL, die Sie in das HTML Ihrer Homepage einfügen.

Dieses Kapitel ist die Operator-Referenz: welche Widgets
existieren, welche URL-Parameter sie akzeptieren und wie
Sie sie auf einer externen Seite einbetten.

---

## 1. Die Widget-Familie

| Widget | URL | Zweck |
|---|---|---|
| **Now Playing — Show** | `/embed/now-playing-show` | Zwei-Zeilen-Text-Widget. Aktueller Sendungsname + verbleibende Dauer; nächster Sendungsname + Start-End-Zeiten. |
| **Now Playing — Track** | `/embed/now-playing-track` | Zwei-Zeilen-Text-Widget. Aktueller Track "Künstler - Titel" + verbleibende Dauer; nächster Track + Start-End-Zeiten. |
| **Next Shows** | `/embed/next-shows` | Listen-Widget. Sendungstitel + chronologische Liste der kommenden Instanzen einer wiederkehrenden Sendung. |
| **Latest Shows** | `/embed/latest-shows` | Listen-Widget. Sendungstitel + umgekehrt-chronologische Liste der letzten Instanzen einer wiederkehrenden Sendung. |
| **On Air Today** | `/embed/on-air-today` | Tages-Grid-Widget. Header-Band + heutige laufende + kommende Sendungen, jede Zeile "HH:MM – HH:MM   Sendungsname (Link)". |
| **Weekly Schedule** | `/embed/weekly-program` | Sieben-Tage-Tab-Widget. Header mit ◀ / ▶ Wochen-Navigation + Datums-Range-Label; Tagestabs; Zeilenliste pro Tab mit HH:MM – HH:MM + Sendungsname (Link). Optionales Hintergrundbild via `?bg=URL`. |
| **Multi-View Schedule** | `/embed/multi-view-schedule` | Kalender-Widget basierend auf FullCalendar 6 (lokal gehostet). Operator-umschaltbare Day / 2-Day / Week Views via In-Widget-Buttons oder `?view=`. Show-Slots eingefärbt aus `cc_show.background_color`. Klick → Modal mit Sendungs-Beschreibung + URL-Button. Auto-Scroll zur Now-Linie. |
| **Track History** | `/embed/track-history` | Tracker-History-Log (letzte 7 Tage). HTML5 Date-Picker + Time-Picker + Now-Button + Pagesize-Dropdown (10/20/50/100). Zeilen "HH:MM - HH:MM Künstler - Titel"; Klick → Modal mit Show-Kontext + URL-Link. Load-More-Button, hart-gecappt bei 1000 Zeilen. |
| **Audio Player** | `/embed/player` | (Bestehend) Eingebetteter HTML5-Audio-Player für den öffentlichen Stream. |

Weitere Widgets sind geplant (siehe [BACKLOG.md](../../../BACKLOG.md)).

---

## 2. Now Playing — Show Widget

Drop-in-iframe:

```html
<iframe src="https://ihre-station.example/embed/now-playing-show"
        width="100%" height="50" frameborder="0"
        scrolling="no" style="border: 0; background: transparent;">
</iframe>
```

### Was es anzeigt

Zwei Zeilen, jede mit einem Namen links und einer Zeit
rechts:

```
Morgensendung                                             -25:14
Music Hour                                          10:00 - 11:30
```

- **Zeile 1**: aktueller Sendungsname + Countdown zum Ende (`-MM:SS` oder `-H:MM:SS`)
- **Zeile 2**: nächster Sendungsname + dessen `HH:MM - HH:MM` Fenster

Der Countdown aktualisiert sich jede Sekunde clientseitig,
sodass die Anzeige flüssig wirkt. Die zugrunde liegenden
Daten werden alle 60 Sekunden aktualisiert (konfigurierbar
— siehe §7).

### URL-Parameter

| Parameter | Werte | Standard | Effekt |
|---|---|---|---|
| `theme` | `auto`, `dark`, `light` | `auto` | Textfarbe. `auto` folgt dem `prefers-color-scheme` des einbettenden Browsers. Hintergrund ist immer transparent. |
| `cache` | Ganzzahl Sekunden, 10–3600 | `60` | Server-seitige HTTP-Cache-TTL. Niedriger = frischere Daten + mehr Backend-Anfragen. |
| `overflow` | `ellipsis`, `marquee` | `ellipsis` | Was passiert mit Sendungs- / Tracknamen, die breiter als das 340-px-Widget sind. `ellipsis` kürzt mit `…`; `marquee` scrollt den Text 24 s lang nach links, damit der vollständige Titel lesbar wird. |
| `timezone` | beliebige Standard-Zeitzone (`Europe/Berlin`) | Stations-Standard | Alle Zeiten in dieser Zone gerendert. |

> **Hinweis.** Der Widget-Body ist auf **340 px Breite** begrenzt,
> damit er in typische Sidebar-Layouts auf Stations-Websites
> passt.  Setzen Sie die iframe-Breite im einbettenden HTML auf
> 340, dann passt es bündig; ein breiteres iframe zeigt Leerraum
> um das Widget.  (Next-Shows / Latest-Shows Widgets sind auf
> 300 px gekappt — sie bedienen einen schmaleren Sidebar-
> Use-Case.)

---

## 3. Now Playing — Track Widget

Drop-in-iframe:

```html
<iframe src="https://ihre-station.example/embed/now-playing-track"
        width="100%" height="50" frameborder="0"
        scrolling="no" style="border: 0; background: transparent;">
</iframe>
```

### Was es anzeigt

Gleiches Zwei-Zeilen-Layout wie das Show-Widget, aber für
Tracks:

```
The Beatles - Hey Jude                                    -02:14
Pink Floyd - Comfortably Numb                       16:00 - 17:30
```

- **Zeile 1**: aktueller Track `Künstler - Titel` + Countdown zum Ende
- **Zeile 2**: nächster Track `Künstler - Titel` + dessen `HH:MM - HH:MM` Fenster

Wenn ein Track keine Künstler-Metadaten hat, wird nur der
Titel angezeigt (und umgekehrt). Wenn weder Künstler noch
Titel verfügbar sind, zeigt die Zeile "No track playing" /
"No upcoming track" in gedämpftem Stil an.

### URL-Parameter

Gleich wie das Show-Widget — siehe §2.

---

## 4. Next-Shows / Latest-Shows Widgets

Schwester-Widgets, die mehrere Instanzen **einer einzelnen
wiederkehrenden Sendung** auflisten anstatt des "Was läuft gerade"-
Rahmens der beiden Now-Playing-Widgets.  Nützlich für eine
Sendungs-Detailseite auf Ihrer Stations-Website: Widget in die
Sidebar, und Hörer sehen die nächsten vier Episoden (oder die
letzten drei, je nachdem welches Widget Sie einbetten).

Drop-in-iframe (Next Shows):

```html
<iframe src="https://ihre-station.example/embed/next-shows?show_id=42"
        width="300" height="140" frameborder="0"
        scrolling="no" style="border: 0; background: transparent;">
</iframe>
```

Drop-in-iframe (Latest Shows):

```html
<iframe src="https://ihre-station.example/embed/latest-shows?show_id=42"
        width="300" height="120" frameborder="0"
        scrolling="no" style="border: 0; background: transparent;">
</iframe>
```

### Was es anzeigt

```
Morgensendung
Di. 21. Mai                                 06:00 - 08:00
Mi. 22. Mai                                 06:00 - 08:00
Do. 23. Mai                                 06:00 - 08:00
Fr. 24. Mai                                 06:00 - 08:00
```

- **Titelzeile**: Sendungsname aus `cc_show.name`
- **Listenzeilen**: eine Zeile pro Instanz, `Wochentag DD Mon`
  links, `HH:MM - HH:MM` rechts

Die Liste aktualisiert sich alle `cache` Sekunden (siehe §7).
Wenn die oberste Zeile eines Next-Shows-Widgets in die
Vergangenheit rutscht (die Sendung hat tatsächlich begonnen),
feuert innerhalb von ~1 s ein Early-Refresh, damit die Zeile
ohne Abwarten der Cache-TTL verschwindet.

### URL-Parameter

| Parameter | Werte | Standard | Effekt |
|---|---|---|---|
| `show_id` | Ganzzahl (cc_show.id) | — | Identifiziert die Sendung. Stabil über Umbenennungen und über Recurring-Instanz-Änderungen — jede Instanz einer wiederkehrenden Sendung teilt sich diese ID. **Empfohlen gegenüber `show`.** |
| `show` | String (cc_show.name) | — | Fallback, wenn `show_id` fehlt.  Case-sensitive exakter Treffer — **matched alle Shows, die den Namen teilen**, sodass eine Station mit einer "BBC News"-Show pro Wochentag alle auf einmal mit einem einzigen `?show=BBC%20News`-Embed listen kann.  `show_id` gewinnt, wenn beide gesetzt sind. |
| `limit` | Ganzzahl 1..20 | 4 (next), 3 (latest) | Wie viele Instanzen aufgelistet werden. |
| `theme` | `auto`, `dark`, `light` | `auto` | Wie die Zwei-Zeilen-Widgets — siehe §2. |
| `cache` | Ganzzahl Sekunden 10..3600 | `60` | Wie die Zwei-Zeilen-Widgets — siehe §7. |
| `overflow` | `ellipsis`, `marquee` | `ellipsis` | Verhalten des Sendungstitels, wenn breiter als 300 px. |
| `timezone` | beliebige Standard-Zeitzone | Stations-Standard | Alle Zeiten in dieser Zone gerendert. |

> **Tipp.** Wählen Sie die Sendung aus dem Dropdown auf der
> Einstellungs-Seite (nächster Abschnitt) statt die ID
> handschriftlich einzutippen — die Seite zeigt eine
> Live-Vorschau und kopiert einen vorgefertigten iframe-Snippet
> mit der ID schon eingebaut.

### Geänderte / abgesagte Instanzen

Einzelne Instanzen, die der Operator verschoben oder
abgesagt hat (`cc_show_instances.modified_instance = TRUE`),
werden aus der Liste herausgefiltert — passend zur
Konvention, die `Application_Model_Show::getNextShows` im
internen Dashboard verwendet.  Eine einzelne verschobene
Episode hinterlässt also keinen Phantom-Eintrag im
öffentlichen Widget.

---

## 5. On-Air-Today Widget

Kompaktes Tages-Grid-Widget, das das heutige Programm
auflistet — von der aktuell laufenden Sendung bis zu den
nächsten paar Sendungen, gedeckelt an Stations-Mitternacht,
damit das Widget nie ins morgige Programm überläuft.

Drop-in-iframe:

```html
<iframe src="https://ihre-station.example/embed/on-air-today"
        width="340" height="250" frameborder="0"
        scrolling="no" style="border: 0; background: transparent;">
</iframe>
```

### Was es anzeigt

```
On Air Today                       ← Header-Band
────────────────────────────────
16:00 - 16:30    Newslink           ← aktuelle Zeile (fett)
16:30 - 17:00    Pages of History (EN)
17:00 - 17:30    L'Info Chez-Vous
17:30 - 04:00    Pages d'histoire
18:30 - 19:00    Choices (EN)
19:00 - 19:30    L'Info chez vous (FR)
```

- **Header**: "On Air Today" (oder "On Air *<Datum>*", wenn
  ein bestimmter Tag via `?day` gepinnt ist)
- **Zeilen**: `HH:MM - HH:MM` links, Sendungsname rechts.
  Die aktuell laufende Zeile wird **fett** gerendert, damit
  Operator (und Hörer) auf einen Blick sieht, welche Zeile
  gerade live ist.
- **Links**: eine Sendung mit konfigurierter **Sendung →
  Bearbeiten → URL** rendert ihren Namen als anklickbaren
  Link, der in einem neuen Tab öffnet (`target="_blank"
  rel="noopener noreferrer"`).  Sendungen ohne URL rendern
  als Plain-Text.

Die Liste aktualisiert sich alle `cache` Sekunden (siehe §7).
Wenn die Endzeit der aktuell laufenden Zeile passiert, feuert
innerhalb von ~1 s ein Early-Refresh, damit das Bold-Highlight
zur nächsten Zeile wandert, ohne die Cache-TTL abzuwarten.

### URL-Parameter

| Parameter | Werte | Standard | Effekt |
|---|---|---|---|
| `limit` | Ganzzahl 1..20 | `6` | Gesamt-Zeilen (current + kommend).  Default = 1 current + 5 kommend. |
| `day` | `YYYY-MM-DD` | heute | Pinnt einen bestimmten Tag (in der aufgelösten Zeitzone), um historische oder zukünftige Tagesübersichten zu rendern.  Wenn weggelassen oder gleich heute, filtert das Widget bereits ausgestrahlte Sendungen aus; für jeden anderen Tag listet es alle Sendungen, deren Start ins 24-Stunden-Fenster fällt. |
| `theme` | `auto`, `dark`, `light` | `auto` | Wie die anderen Widgets — siehe §2. |
| `cache` | Ganzzahl Sekunden 10..3600 | `60` | Wie die anderen Widgets — siehe §7. |
| `overflow` | `ellipsis`, `marquee` | `ellipsis` | Verhalten bei Sendungsnamen breiter als 340 px. |
| `link` | `underline`, `plain` | `plain` | Link-Darstellung für Sendungsnamen: `plain` (Default) entfernt die Unterstreichung, sodass die Namen in den fetten Zeilentext eingehen; `underline` aktiviert wieder die klassische Hyperlink-Affordance.  Bei `plain` überlebt die Link-Affordance nur noch über den Cursor-Pointer beim Hover. |
| `timezone` | beliebige IANA-Zone | Stations-Standard | Definiert "heute" und rendert alle Zeiten in dieser Zone. |

> **Tagesgrenze.** "Heute" ist der Stations-Kalendertag —
> 00:00 bis 24:00 in der Stations-Zeitzone (oder in
> `?timezone`, falls überschrieben).  Eine Sendung, die
> gestern 23:30 startete und um 14:00 heute noch läuft, gilt
> als aktuelle Zeile.  Eine Sendung, die morgen 00:30
> startet, wird **nicht** gelistet, auch wenn das `limit`
> sonst Platz lassen würde — die Deckelung ist hart.

### Geänderte / abgesagte Instanzen

Gleiche Konvention wie bei den Next-Shows / Latest-Shows
Widgets — Zeilen mit `cc_show_instances.modified_instance =
TRUE` werden herausgefiltert, damit eine einzelne
verschobene / abgesagte Instanz keinen Phantom-Eintrag im
öffentlichen Widget hinterlässt.

### Einstellungs-Seite

**Einstellungen → Widgets → On Air Today** enthält:

- Ein einziges konfigurierbares Empty-State-Label (Default
  `No shows on air today`, fällt auf englischen Default
  zurück bei leerem Feld).
- Eine Live-Vorschau-iframe auf dunklem Backdrop.
- Den vorgefertigten `<iframe>`-Embed-Code mit absoluter
  Stations-URL.

Kein Show-Picker — das Widget zieht automatisch aus dem
Live-Schedule für den ganzen Stations-Tag.

---

## 6. Weekly Schedule Widget

Ein 7-Tage-Tab-Widget — der modernisierte Ersatz für das
Legacy-jQuery+Handlebars-Schedule-Embed.  Kompakter Header mit
◀ / ▶ Navigation, Wochentag-Tabs und Zeilenliste der Sendungen
pro Tag.

Drop-in-iframe:

```html
<iframe src="https://ihre-station.example/embed/weekly-program"
        width="400" height="560" frameborder="0"
        scrolling="no" style="border: 0; background: transparent;">
</iframe>
```

### Was es anzeigt

```
◀  21 May – 27 May 2026                ▶            ← Header-Band
MON  TUE  WED  THU  FRI  SAT  SUN                   ← Tagestabs
 21   22   23   24   25   26   27                      (heute eingekreist)
─────────────────────────────────────────────────
06:00 - 08:00    Morgensendung                      ← Zeilenliste
08:00 - 10:00    Newslink                              (pro aktivem Tab)
...
```

- **Header-Band**: ◀ Button → vorige Woche, Wochen-Range-Label
  zentriert (z.B. "21 May – 27 May 2026"; Wochen über
  Jahresgrenzen zeigen das Jahr zweimal), ▶ Button →
  nächste Woche.  Klick auf einen Button aktualisiert den
  `week_offset`-Parameter der iframe-URL in-place via
  `history.pushState` und lädt neu.
- **Tagestabs**: 7 Tabs (Mo … So in der Visitor-Locale).
  Heutiger Tab ist mit einem subtilen Pill-Ring um die
  Tagesnummer dekoriert.  Klick auf einen Tab tauscht das
  sichtbare Panel — kein Netzwerk-Round-Trip.
- **Zeilenliste**: pro Tab eine Zeile pro Sendung.  Zeit
  links, Sendungsname rechts.  Namen mit konfigurierter
  `cc_show.url` rendern als Click-Through-Links, die in
  einem neuen Tab öffnen.

### URL-Parameter

| Parameter | Werte | Standard | Effekt |
|---|---|---|---|
| `week_offset` | Ganzzahl -2..4 | `0` | Pinnt das gerenderte Fenster auf ±N Wochen vom heutigen rollenden 7-Tage-Block.  Default 0 = heute + 6 kommende Tage.  Enger Cap (-2 / +4) weil Public-Homepage-Use-Cases selten eine weitere Range brauchen; die ◀ / ▶ Buttons deaktivieren sich am Limit. |
| `theme` | `auto`, `dark`, `light` | `auto` | Wie die anderen Widgets — siehe §2. |
| `cache` | Ganzzahl Sekunden 10..3600 | `60` | Wie die anderen Widgets — siehe §8. |
| `overflow` | `ellipsis`, `marquee` | `ellipsis` | Verhalten bei Sendungsnamen breiter als 400 px. |
| `link` | `underline`, `plain` | `plain` | Show-Name-Link-Darstellung (siehe On-Air-Today Widget §5 für Details). |
| `bg` | URL eines Bildes | keine | Optionales Hintergrundbild (cover-positioniert) statt transparenter Fülle.  Operator hostet das Bild selbst. |
| `bgcolor` | Hex-Farbe, z.B. `#222222` | keine | Optionale Hintergrundfarbe als Hex-String (3, 6 oder 8 Zeichen inkl. Alpha — z.B. `#fff`, `#112233`, `#11223388`).  Rendert hinter `?bg` wenn beide gesetzt sind.  Nicht-Hex-Werte werden aus Sicherheitsgründen abgewiesen. |
| `timezone` | beliebige IANA-Zone | Stations-Standard | Alle Zeiten in dieser Zone gerendert. |

> **Today-Tab + aktive Zustand.**  Der Wochentag-Tab, der
> dem heutigen Kalendertag entspricht, wird in der
> Akzentfarbe (Default LibreTime-Teal `#459B8F`) gefüllt,
> sodass der Operator auf einen Blick weiß, wo er in der
> Woche ist.  Der aktuell-aktive Panel-Tab bekommt eine
> akzentfarbene Unterstreichung.  Hover über einen Tab
> oder die ◀ / ▶ Buttons leuchtet die gleiche Akzentfarbe
> mit niedriger Alpha auf — subtiler Interaktivitäts-Cue.

> **Auto-Scroll zur laufenden Sendung.**  Wenn der aktive
> Tab heute ist, scrollt das Widget die gerade ausgestrahlte
> Sendung in die Mitte des Panel-Viewports — so landet der
> Besucher direkt auf "was läuft jetzt", statt erst durch das
> Morgenprogramm scrollen zu müssen.  Die laufende Sendung
> bekommt zusätzlich einen akzentfarbenen Left-Border, damit
> der Besucher sie nach dem Scroll sofort erkennt.  Kein
> Effekt, wenn heute gerade eine Programmlücke ist (keine
> laufende Sendung) oder wenn ein anderer Tag aktiv ist.

> **Breite.** Das Weekly-Schedule-Widget ist **670 px breit**
> (hochgesetzt von 400 px am 2026-05-25 auf Operator-Wunsch — alle
> Schriften, Padding und die Day-Panel-Maxhöhe wurden proportional
> mitskaliert; das iframe im empfohlenen Embed-Snippet ist
> `width="670" height="940"`).  Setzen Sie die iframe-Werte im
> einbettenden HTML auf diese Werte für bündige Darstellung.

### Geänderte / abgesagte Instanzen

Gleiche Konvention wie bei den anderen Widgets —
`modified_instance = TRUE` werden herausgefiltert.

### Einstellungs-Seite

**Einstellungen → Widgets → Weekly Schedule** enthält die
Empty-State-Label-Anpassung ("No shows scheduled on this day"
default), eine Live-Vorschau-iframe auf dunklem Backdrop und
den vorgefertigten `<iframe>`-Embed-Code.

---

## 7. Multi-View Schedule Widget

Ein Kalender-Widget basierend auf **FullCalendar 6.1.10**
(lokal eingebettet, keine CDN-Abhängigkeit).  Drei operator-
umschaltbare Views: **Day**, **2-Day**, **Week**.  Steht
neben dem Weekly-Schedule-Widget als reicherer Alternative:
Time-Grid-Layout mit eingefärbten Show-Slots, Now-Indikator-
Linie, Auto-Scroll zur aktuell laufenden Sendung und Klick-
zum-Öffnen-Modal mit Sendungs-Beschreibung + URL-Link.

Drop-in-iframe (~600 px hoch, damit das 24-Stunden-Grid
bequem reinpasst):

```html
<iframe src="https://ihre-station.example/embed/multi-view-schedule"
        width="100%" height="600" frameborder="0"
        scrolling="no" style="border: 0; background: transparent;">
</iframe>
```

### Was es anzeigt

- **Header-Band**: ◀ / ▶ Navigation, zentriertes Datums-
  Range-Label, **Today**-Button (springt zurück zu jetzt
  und triggert erneut den Auto-Scroll), View-Switcher
  (DAY / 2-DAY / WEEK).
- **Time-Grid**: 24h, 15min Slots, 60min Stundenlabels.
  Now-Indicator-Linie in der Akzentfarbe.
- **Show-Slots**: aus `cc_show_instances` JOIN `cc_show`.
  Hintergrundfarbe aus dem konfigurierten `background_color`
  der Sendung (Kalender → Sendung → Bearbeiten → Stil);
  leere Farben fallen zurück auf einen weichen Akzent-Fill.
  Die aktuell laufende Sendung bekommt einen Akzent-Ring.
- **Klick**: öffnet Modal mit Sendungsname, Zeit-Range,
  Beschreibung und Click-Through-Link zur Show-URL
  (falls konfiguriert).

### URL-Parameter

| Parameter | Werte | Standard | Effekt |
|---|---|---|---|
| `view` | `day`, `2day`, `week` | `day` | Initial-View.  Visitor kann via In-Widget-Buttons weiter wechseln; dies steuert nur den Start-Zustand. |
| `theme` | `auto`, `dark`, `light` | `auto` | Wie die anderen Widgets — siehe §2. |
| `clock` | `24`, `12`, `auto` | `24` | Uhrzeit-Format auf der Stunden-Achse, in Show-Slots und im Modal.  `24` erzwingt `17:00`-Stil unabhängig vom Locale; `12` erzwingt `5 PM`-Stil; `auto` lässt FullCalendar nach Locale entscheiden (`en` → AM/PM, `de` → 24h). |
| `cache` | Ganzzahl Sekunden 10..3600 | `300` (5 min) | Server-seitige HTTP-Cache-TTL für JSON-Event-Feed.  Höherer Default als bei den anderen Widgets — Schedule verschiebt sich selten mittags, Payload ist größer. |
| `bg` | URL eines Bildes | keine | Wie das Weekly-Schedule-Widget — siehe §6. |
| `bgcolor` | Hex-Farbe | keine | Wie das Weekly-Schedule-Widget — siehe §6. |
| `timezone` | beliebige IANA-Zone | Stations-Standard | Alle Zeiten in dieser Zone gerendert; definiert auch was "heute" für den Auto-Scroll bedeutet. |

### Datenfeed

Interner JSON-Endpoint unter `/Embed/multi-view-schedule-data`,
aufgerufen vom FullCalendar-Lazy-Loading-Callback für den
aktuell sichtbaren Datums-Bereich.  Output entspricht dem
FullCalendar-Event-Format mit `id`, `title`, `start`, `end`,
`url`, `backgroundColor`, `borderColor`, `textColor`,
`extendedProps.{description, showId}`.  Modified / abgesagte
Instanzen werden herausgefiltert.

### Einstellungs-Seite

**Einstellungen → Widgets → Multi-View Schedule** enthält:
- Operator-konfigurierbares Empty-State-Label,
- Live-Vorschau-iframe auf dunklem Backdrop,
- Vorgefertigte `<iframe>`-Embed-Code-Snippets für alle
  drei Default-Views (Day / 2-Day / Week).

### Performance

- **FullCalendar lokal gehostet** unter
  `/js/libs/fullcalendar/` (~282 KB JS + ~26 KB Locales).
  Kein CDN-Round-Trip, keine externe Netzwerk-Abhängigkeit,
  funktioniert hinter Firmen-Firewalls und in air-gapped
  Umgebungen.  Version-pinning siehe
  `frontend/legacy/public/js/libs/fullcalendar/VERSION.txt`.
- **CSS ist im JS gebündelt** (FullCalendar 6 injected es
  zur Laufzeit ins `<head>`) — kein separater Stylesheet-
  Load.
- **Browser-Cache** absorbiert den initialen 308 KB Hit
  nach dem ersten Page-View jedes Visitors.
- **Lazy Event-Fetch**: FullCalendar holt nur die Events
  für die aktuell sichtbare Range, nicht den ganzen Monat.

---

## 8. Track History Widget

Recent-Track-Playout-Log — Besucher wählt einen Tag aus den
letzten 7, wählt eine Seitengröße (10 / 20 / 50 / 100), und
das Widget rendert die gespielten Tracks chronologisch
absteigend.  Klick auf eine Zeile → Modal mit Track-Metadaten
+ Show-Kontext + Click-Through-Link zur Show-URL falls
konfiguriert.

Drop-in-iframe (~500 px hoch, damit 10 Zeilen + Header +
Load-More-Footer reinpassen):

```html
<iframe src="https://ihre-station.example/embed/track-history"
        width="100%" height="500" frameborder="0"
        scrolling="no" style="border: 0; background: transparent;">
</iframe>
```

### URL-Parameter

| Parameter | Werte | Standard | Effekt |
|---|---|---|---|
| `date` | `YYYY-MM-DD` | heute | Zu ladender Tag.  Gecappt auf `[heute - 6 Tage, heute]` — out-of-range snappt auf den nächsten gültigen Wert statt 500. |
| `time` | `HH:MM` (24h) | jetzt (heute) / 23:59 (vergangener Tag) | Obere Schranke der Uhrzeit.  Das Widget zeigt Tracks die VOR diesem Zeitpunkt endeten, neueste zuerst.  Default seed auf "jetzt" → Widget öffnet auf dem zuletzt gespielten Slice. |
| `pagesize` | `10`, `20`, `50`, `100` | `10` | Anzahl Tracks pro Seite.  Besucher kann es in-widget ändern. |
| `exclude_short` | `0`, `1` | Preference (default `1`) | Tracks kürzer als `min_sec` Sekunden ausblenden — fängt Jingles / Station-IDs / Silence-Tails ab.  URL-Param überschreibt die Stations-Preference. |
| `min_sec` | Ganzzahl 1..3600 | Preference (default `60`) | Schwelle in Sekunden für den Exclude-Short-Filter. |
| `theme` | `auto`, `dark`, `light` | `auto` | Wie die anderen Widgets — siehe §2. |
| `cache` | Ganzzahl Sekunden 10..3600 | `60` | Server-seitige HTTP-Cache-TTL. |
| `bg`, `bgcolor` | URL bzw. Hex-Farbe | keine | Wie die anderen Widgets — siehe §6. |
| `timezone` | beliebige IANA-Zone | Stations-Standard | Alle Zeiten in dieser Zone. |

**Zeilen-Format**: `HH:MM - HH:MM Artist - Title` — Start + End-Zeit links in Tabular-Numerics, dann Artist / Title in **fett**.

**Einstellungs-Seite** unter *Widgets → Track History* enthält zusätzlich den **Exclude short tracks**-Checkbox + zugehöriges **Sekunden-Feld** (Auto-Expiry-Stil — Sekunden-Feld erscheint nur wenn Checkbox aktiv).

> **7-Tage-Cap-Begründung.**  Das Widget ist für "was hat
> gerade gespielt"-Neugier gedacht, nicht als
> Langzeit-Archiv.  Tieferer History-Browser-Bedarf wird
> durch das interne Playout-History-Dashboard abgedeckt.

### Datenfeed

Interner JSON-Endpoint unter `/Embed/track-history-data`.
Quelle: `cc_playout_history` LEFT JOIN `cc_files` LEFT JOIN
`cc_show_instances → cc_show` mit Fallback auf
`cc_playout_history_metadata`.  Sechs Row-Arten:

1. **Scheduled File Plays** (`file_id IS NOT NULL`) —
   Title / Artist aus `cc_files`.
2. **Scheduled Webstream-Items** (`file_id IS NULL`) —
   geschrieben von `insertPlayedItem()` bei Schedule-Items
   mit `stream_id`.  Synthetischer "Block"-Eintrag mit
   `title = cc_webstream.description` (Fallback auf
   `name` wenn description leer) und `artist =
   cc_webstream.name` — auch wenn der Stream-Server
   keine ICY-Metadata sendet.
3. **Scheduled Line-In-Items** (`file_id IS NULL`,
   **RASTATIME-only**, benötigt Migration 0047
   `cc_schedule.linein_id`) — geschrieben von
   `insertPlayedItem()` bei Schedule-Items mit
   `linein_id` (Operator hat Line-In aus der Library in
   eine Show gezogen, z.B. "Jabra-Mikro").  Synthetischer
   "Block"-Eintrag mit `title =
   rastatime_linein.description` (Free-Text-Kontext,
   Fallback auf den kurzen Namen wenn description leer)
   und `artist = rastatime_linein.name` (kurzes Label).
   `linein_id` wird per Raw-SQL gelesen, weil die
   Propel-ORM-Klassen vor der RastaTime-Migration
   generiert wurden.
4. **Webstream-Tracks** (`file_id IS NULL`) — geschrieben
   von `insertWebstreamMetadata()` bei eingehender
   ICY-Metadata.  Per-Track-Granularität.
5. **Live-Show-Sessions** (`file_id IS NULL`) — neu
   2026-05-23.  Geschrieben von `ensureLiveShowLogged()`
   als Side-Effect bei `/api/live-info(-v2)`.  Catched
   Show-Instances mit `time_filled = '00:00:00'`
   (Operator hat Slot ohne Items angelegt, Liquidsoap
   schaltet automatisch auf master_dj).  Artist = "Live
   Show".
6. **Manual Dashboard Source Switches** (`file_id IS NULL`)
   — geschrieben von `insertLineInLog()` bei Operator-
   Toggle im Dashboard.  Artist = "Master Source" /
   "Show Source".

Label für Arten 5+6 konfigurierbar unter Settings →
Widgets → Track History → "Line-Input label".  Art 3
nutzt stattdessen den per-Line-In `name` aus
`rastatime_linein`, den der Operator in der Line-In-
Library setzt.

Im Modal: über der Show-Zeile steht jetzt die Beschriftung
**"Played in the show:"**.  Bei Webstream-Einträgen ohne
Instance-Bindung wird der Show-Kontext-Block ausgeblendet.

### Einstellungs-Seite

**Einstellungen → Widgets → Track History** enthält:
- Operator-konfigurierbares Empty-State-Label,
- Live-Vorschau-iframe auf dunklem Backdrop,
- Zwei vorgefertigte Embed-Code-Snippets (Pagesize 10 + 50).

---

## 9. Empty-State-Labels anpassen

Wenn keine aktuelle oder kommende Show / Track vorhanden ist,
zeigt das Widget einen kurzen Platzhalter-Text. Operator können
alle vier Platzhalter ohne Code-Eingriff anpassen unter:

**Einstellungen → Widgets → Current Show/Track**

| Einstellungs-Label | Standard-Wert |
|---|---|
| No show on air: | `No show on air` |
| No upcoming show: | `No upcoming show` |
| No track playing: | `No track playing` |
| No upcoming track: | `No upcoming track` |

Bearbeitungen werden in `cc_pref` persistiert und vom Widget
innerhalb einer Cache-TTL (Standard 60 s) übernommen. Lassen Sie
ein Feld leer, um auf den englischen Default im Placeholder
zurückzufallen.

Dieselbe Einstellungs-Seite enthält auch:

- eine **Live-Vorschau** beider Widgets nebeneinander, sodass
  Sie eine Label-Änderung sofort nach dem Speichern sehen;
- den **vorgefertigten `<iframe>`-Embed-Code** für jedes
  Widget mit absoluter Stations-URL, bereit zum Einfügen in
  den HTML-Code der Homepage.

Die Next-Shows / Latest-Shows Widgets haben eine eigene
Labels-Seite unter:

**Einstellungen → Widgets → Next/Latest Shows**

| Einstellungs-Label | Standard-Wert |
|---|---|
| No upcoming shows: | `No upcoming shows` |
| No past shows: | `No past shows` |

Diese Seite enthält außerdem ein **Show-Picker-Dropdown**, das
die Preview-iframes und die Embed-Code-Snippets steuert —
Sendung auswählen, Speichern drücken und den generierten
`<iframe ...>`-Block kopieren, mit der `show_id` schon in der
URL eingebaut.

---

## 10. Der `cache`-Parameter — welche TTL ist richtig?

Der Server cached die zugrunde liegenden Daten für `cache`
Sekunden, bevor er sie regeneriert. Die JS-Abfrage im
iframe entspricht dieser Kadenz, sodass unter hoher Last
jeder Besucher auf den **Browser-Cache** trifft anstatt
auf Ihr Backend.

Empfohlene Werte:

| `cache=` | Wann |
|---|---|
| `30` | Hochpräzise Anzeige, z.B. Lobby-Bildschirm in der Station. Verbraucht ~2 Backend-Anfragen/Min pro Browser. |
| `60` (Standard) | Öffentliche Homepage mit moderatem Traffic. Gute Balance zwischen Frische und Last. |
| `120`–`300` | Sehr hochfrequentierte Einbettung. Tausche bis zu 5 Min Veraltung gegen eine Größenordnung weniger Backend-Anfragen. |
| `> 600` | Nicht empfohlen — die angezeigte Sendung / der Track ist oft bereits beendet, wenn der Browser erneut abfragt. |

> **Operator-Tipp.** Das Widget gleicht veraltete Daten
> aus: Wenn die End-Zeit des aktuellen Items vergeht
> (clientseitig aus den absoluten Zeitstempeln im Payload
> berechnet), feuert das JS sofort eine Anfrage, ohne auf
> das nächste Intervall zu warten. So wechselt eine
> `cache=300` Einbettung trotzdem innerhalb von ~1 s zum
> nächsten Track — die Veraltung betrifft nur die erste
> Anzeige nach einer langen Pause.

> **Wie es unter der Haube funktioniert.** Beide
> Widget-Endpunkte setzen
> `Cache-Control: public, max-age=<cache>`. Apache
> liefert das iframe-HTML; das JS im iframe fragt
> `/embed/now-playing-data` (gleiche Cache-TTL) für
> Refresh-Payloads ab. Der JSON-Endpoint zieht aus
> `Application_Model_Schedule::GetPlayOrderRange()` —
> derselben Quelle, die `/api/live-info` verwendet —
> aber getrimmt auf ~1-2 kB Payload, sodass der
> Round-Trip günstig bleibt.

---

## 11. Themes

Drei Modi, gesteuert über den `theme`-URL-Parameter:

| `theme=` | Effekt |
|---|---|
| `auto` (Standard) | Helle Schrift auf dunklen einbettenden Seiten, dunkle Schrift auf hellen. Erkannt über die `prefers-color-scheme` Media-Query des Browsers. |
| `dark` | Erzwingt helle Schrift (verwenden Sie dies, wenn Ihre einbettende Seite dunkel ist, aber das OS des Besuchers auf hell eingestellt ist). |
| `light` | Erzwingt dunkle Schrift. |

Der Hintergrund des Widgets ist **immer transparent**,
sodass es in das integriert, wie die einbettende Seite
aussieht. Der Font-Stack verwendet standardmäßig die
System-Schrift der einbettenden Seite.

Wenn Sie eigenes CSS benötigen, ist der einfachste Weg,
das iframe in einen eigenen gestylten Container zu wickeln
und sich auf den transparenten Hintergrund zu verlassen:

```html
<div class="my-station-now-playing-card">
    <iframe src=".../embed/now-playing-show?theme=dark" ...></iframe>
</div>
```

---

## 12. Authentifizierung

Keine. Die Now-Playing-Widgets sind absichtlich
öffentlich: Der ganze Zweck ist, dass jeder Besucher auf
Ihrer öffentlichen Stationswebsite sehen kann, was auf
Sendung ist. Es gibt keinen API-Schlüssel, kein
Session-Cookie, keine Pro-Besucher-Auth.

Das ist sicher, weil die Widgets nur die Daten exponieren,
die ein Hörer ohnehin im Player sehen würde (Sendungs- /
Track-Name + Zeiten). Sie exponieren **nicht**:

- Hörerzahlen
- Stream-Quellen-Zustand (Show DJ / Master DJ / Auto DJ)
- Operator-Namen
- Aufnahme-Zustand
- Interne IDs

Wenn Sie ein reicheres authentifiziertes Widget benötigen
(z.B. zeigt, welcher DJ gerade auf Sendung ist), öffnen
Sie stattdessen das passwortgeschützte
[Dashboard](./DASHBOARD.md).

---

## 13. Cross-Origin-Einbettung

Iframes funktionieren cross-origin von Haus aus — keine
zusätzliche Konfiguration nötig. Die Homepage Ihrer
Station kann das Widget einbetten, unabhängig davon,
welcher Host die Homepage bereitstellt.

Wenn Sie zuvor versucht haben, über JavaScript-Snippet
einzubetten und auf CORS-Fehler gestoßen sind, umgeht der
Wechsel zum iframe-Ansatz (dieses Kapitel) das Problem
vollständig.

---

## 14. Fehlerbehebung

### "Widget zeigt 'No show on air', aber eine Sendung läuft"

- Verifizieren Sie, dass die Sendung tatsächlich läuft —
  prüfen Sie das interne [Dashboard](./DASHBOARD.md) oder
  den Hauptstream der Station.
- Der serverseitige Cache könnte noch veraltete Daten
  haben. Warten Sie bis zu `cache` Sekunden (Standard 60)
  oder laden Sie die übergeordnete Seite des iframes hart
  neu.

### "Widget zeigt überhaupt nichts (leeres iframe)"

- Verifizieren Sie, dass die iframe-URL aus dem
  Browser-Kontext der einbettenden Seite erreichbar ist.
  Öffnen Sie die URL direkt in einem neuen Tab — sie
  sollte das Widget eigenständig rendern.
- Prüfen Sie die Browser-Konsole (Rechtsklick iframe →
  Element untersuchen → Konsole) auf JS-Fehler.
- Stellen Sie sicher, dass RASTATIMEs Apache die
  iframe-URL auf dem öffentlichen Hostnamen ausliefert,
  der unter Einstellungen → Allgemeine Einstellungen
  konfiguriert ist.

### "Widget-Hintergrund ist weiß, aber ich möchte dunkel"

Fügen Sie `?theme=dark` zur iframe-URL hinzu. Wenn es der
OS-Präferenz des Besuchers folgen soll, verwenden Sie
`?theme=auto` (Standard).

### "Countdown zeigt -00:00 und bleibt dort"

Die End-Zeit des aktuellen Items ist vergangen, aber das
Widget hat die neuen Daten noch nicht aufgenommen. Das
erholt sich innerhalb von ~1 s dank des Early-Poll-
Mechanismus. Wenn es länger anhält, ist möglicherweise
die Playout-Engine gestoppt — prüfen Sie
`Get-Service RASTATIME-PLAYOUT`.

### "On-Air-Today Widget ist leer, obwohl Sendungen geplant sind"

- Prüfen Sie, ob *heute* in der Stations-Zeitzone noch
  kommende Sendungen hat: spät nachts wird das Widget
  legitim leer, bis die nächste Stations-Mitternacht
  vorüberzieht.  Um vorauszuschauen, pinnen Sie einen
  bestimmten Tag via `?day=YYYY-MM-DD`.
- Verifizieren Sie, dass die Sendungen tatsächlich im
  Kalender geplant sind — abgesagte Instanzen
  (`modified_instance = TRUE`) werden by-design
  herausgefiltert.
- Wenn die iframe-URL `?timezone=...` enthält, überschreibt
  das die Stations-Zeitzone für die "heute"-Berechnung.
  Ein `?timezone=Asia/Tokyo`-Embed zeigt Tokios Heute,
  was an der Station bereits morgen sein kann.

### "Next / Latest Shows Widget zeigt den Empty-Placeholder"

- Verifizieren Sie, dass die iframe-URL `?show_id=N`
  (bevorzugt) oder `?show=Name` enthält.  Die
  Einstellungs-Seite (§5) generiert den Snippet mit der
  ID schon eingebaut — kopieren Sie ihn von dort, statt
  die URL handschriftlich zu basteln.
- Bestätigen Sie, dass die Sendung tatsächlich künftige
  Instanzen im Kalender hat (für Next Shows) oder
  mindestens einmal gesendet wurde (für Latest Shows).
  Eine brandneue Sendung ohne ausgestrahlte Episoden zeigt
  im Latest-Widget den Empty-Placeholder bis die erste
  Episode beendet ist.
- `modified_instance = TRUE`-Zeilen werden by-design
  herausgefiltert (passend zum internen Dashboard).  Eine
  Sendung, deren einzige kommende Instanz verschoben
  oder abgesagt wurde, zeigt Empty, bis eine neue
  Instanz generiert wird.

---

## Wohin als Nächstes

* [Dashboard](./DASHBOARD.md) — die interne Version
  derselben Daten, mit vollen Operator-Kontrollen.
* [Streams](./STREAMS.md) — die zugrunde liegenden
  Audio-Streams, die die Widgets beschreiben.
* [BACKLOG.md](../../../BACKLOG.md) — kommende
  Widget-Wellen (Next Shows / Latest Shows, Weekly
  Program Erweiterungen, Track History).
