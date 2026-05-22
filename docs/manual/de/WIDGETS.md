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
| **Weekly Program** | `/embed/weekly-program` | (Bestehend) Sieben-Tage-Kalenderraster der Stations-Programmübersicht. |
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

## 6. Empty-State-Labels anpassen

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

## 7. Der `cache`-Parameter — welche TTL ist richtig?

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

## 8. Themes

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

## 9. Authentifizierung

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

## 10. Cross-Origin-Einbettung

Iframes funktionieren cross-origin von Haus aus — keine
zusätzliche Konfiguration nötig. Die Homepage Ihrer
Station kann das Widget einbetten, unabhängig davon,
welcher Host die Homepage bereitstellt.

Wenn Sie zuvor versucht haben, über JavaScript-Snippet
einzubetten und auf CORS-Fehler gestoßen sind, umgeht der
Wechsel zum iframe-Ansatz (dieses Kapitel) das Problem
vollständig.

---

## 11. Fehlerbehebung

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
