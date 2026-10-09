# Lokale Maschine

> **Wo Sie sich im Handbuch befinden.** Dieses Kapitel
> behandelt die Seite Einstellungen → **Lokale Maschine**,
> die jeden Aspekt besitzt, der an die *Operator-Maschine
> selbst* gebunden ist — Soundkarten-Ausgang,
> Line-In-Eingabegeräte und den lokalen Import-Ordner. Für
> die netzwerkseitigen ausgehenden Streams siehe
> [Streams](./STREAMS.md). Für den Bibliotheks-Item-Typ, der
> einen Soundkarten-Eingang *referenziert*, siehe
> [Line-In](./LINE_IN.md).

Die Seite **Lokale Maschine** ist, wo Sie RASTATIME über
die physischen Ressourcen der Operator-Maschine informieren:
welcher Lautsprecher-Ausgang abgespielt werden soll, welche
Geräte als Line-In-Kandidaten zählen und welchen Ordner der
Analyzer auf importierte Tracks überwachen soll.

Die Seite ersetzt die "Soundcard"-Seite des ursprünglichen
LibreTime und fügt das Import-Ordner-Feature hinzu. Die
Legacy-URL funktioniert weiterhin; nur der Seitentitel und
der Slug ändern sich.

---

## 1. Die Seite

Einstellungen → **Lokale Maschine**.

```
   ┌─────────────────────────────────────────────────────────────────┐
   │  Lokale-Maschine-Einstellungen                       [Speichern]│
   ├─────────────────────────────────────────────────────────────────┤
   │  Soundkarte                                                     │
   ├─────────────────────────────────────────────────────────────────┤
   │  Ausgabegeräte               │  Eingabegeräte                   │
   │  ─────────────────            ──────────────                    │
   │  ◉  Lautsprecher (Realtek)    ☑  Mikrofon (USB)                 │
   │  ◯  Kopfhörer (Realtek)       ☐  Line-Eingang (Realtek)         │
   │  ◯  USB-Headset                ☑  Mixer-Out (Behringer)          │
   │                                                                 │
   │  Standard-Ausgang für Cue/Monitor: [Lautsprecher (Realtek) ▾]   │
   ├─────────────────────────────────────────────────────────────────┤
   │  Lokaler Import-Ordner                                          │
   ├─────────────────────────────────────────────────────────────────┤
   │  Ordnerpfad:     [C:\rastatime\import\                  ]        │
   │  Zuletzt gescannt: 2026-05-21 14:32 — 0 neue Dateien gefunden   │
   │                                                                 │
   │  [ Jetzt scannen ]                                              │
   └─────────────────────────────────────────────────────────────────┘
```

Drei unabhängige Abschnitte.

---

## 2. Soundkarte — Ausgabegeräte

Die Liste zeigt jedes Audio-Ausgabegerät, das die
Operator-Maschine exponiert (eingebaute Lautsprecher,
USB-Headset, HDMI-Audio usw.).

### Standard-Ausgang (der "Monitor")

Das ausgewählte Gerät ist der **Monitor- / Cue**-Ausgang:

- Die Schaltfläche **Anhören** des Dashboards spielt darüber.
- Die Schaltfläche **Vorschau** der Bibliothek (Track
  anklicken, um eine 10-s-Probe zu hören) spielt darüber.
- Die Vorschau des Show-Builders spielt auch darüber.

> **Was es NICHT ist.** Der Standard-Ausgang ist *nicht*
> der öffentliche Stream. Hörer hören nicht, was hier
> abgespielt wird. Der öffentliche Stream ist der
> Icecast-Ausgang, der in [Streams](./STREAMS.md)
> konfiguriert ist und vom Playout-Engine völlig getrennt
> von diesem Gerät gefüttert wird.

### Warum ein bestimmtes Gerät wählen

- **Stationen mit einzelnem Operator** mit nur einem
  Lautsprecherpaar — Standard belassen; das OS-Standardgerät
  funktioniert.
- **Stationen mit zwei Monitoren** mit einem
  "Air-Check"-Lautsprecher (zum Überwachen des
  öffentlichen Streams) und einem "Internen"-Lautsprecher
  (zum Vorhören von Tracks bevor sie live gehen) — wählen
  Sie hier den internen Lautsprecher, damit Vorschauen den
  Air-Check nicht unterbrechen.
- **Nur-Kopfhörer-Stationen** — wählen Sie das
  Kopfhörer-Gerät, damit Vorschauen nie in das Studio-
  Mikrofon lecken.

### "(System-Standard)" Pseudo-Gerät

Der erste Eintrag im Dropdown ist immer
**(System-Standard)**. Dies folgt dem, was das Windows- /
Linux-System als Standard-Audio-Ausgang markiert hat.
Nützlich, wenn:

- Der Operator das USB-Headset ab- / einsteckt und möchte,
  dass RASTATIME der OS-Wahl folgt.
- Die Operator-Maschine zwischen mehreren Benutzern mit
  unterschiedlichen Kopfhörer-Präferenzen geteilt wird.

> **Wie es unter der Haube funktioniert.** Geräte werden
> über `audio.soundcard.windows_manager` enumeriert (WASAPI
> unter Windows, portaudio unter Linux). Das ausgewählte
> Gerät wird in `cc_pref` als `default_output_device_id`
> persistiert (`(System-Standard)` ist der leere String).
> Die tatsächliche Wiedergabe verwendet das libVLC-
> Audio-Output-Modul mit der Geräte-ID pro Output gesetzt.
> Siehe ARCHITECTURE §9.

### Änderung anwenden — "Jetzt anwenden"

> **Seit dem 16.09.2026 geschieht das von selbst.** Nach dem Speichern
> bemerkt das Playout das geänderte Gerät bei der nächsten
> Aktualisierung des Sendeplans (innerhalb von zwei Minuten) und startet
> die Audio-Kette im nächsten ruhigen Moment neu - bei einem
> 24/7-Programm zwischen zwei Datei-Titeln. Hörer bleiben über die
> Standby-Mounts verbunden. Dasselbe gilt für die 24/7-Aufnahme, die
> Track- und Show-Crossfade-Dauer und die Stream-Ausgänge. **Jetzt anwenden** bleibt
> der Weg, es sofort zu erzwingen.

Speichern legt das Gerät ab; der lokale Monitor wechselt
dadurch **noch nicht**. Die Playout-Engine kompiliert das
gewählte Gerät beim Dienststart in ihr Liquidsoap-Skript, und
Liquidsoap liest dieses Skript nur beim *eigenen* Start. Eine
Änderung braucht daher einen Neustart beider Dienste, in
genau dieser Reihenfolge.

Statt beim Speichern stillschweigend neu zu starten — was den
öffentlichen Stream ohne Vorwarnung unterbrechen würde —
bietet die Seite unter der Auswahl einen bewussten Knopf:

**Jetzt anwenden (startet Audiokette neu)** — startet
RASTATIME-PLAYOUT neu (rendert das Skript mit dem neuen Gerät)
und danach RASTATIME-LIQUIDSOAP (lädt es).

Über dem Knopf zeigt die Seite an, **welcher Ausgang gerade
wirklich den Monitor speist** — ausgelesen aus dem gerenderten
Liquidsoap-Skript, nicht aus der gespeicherten Einstellung. Weichen
beide voneinander ab (Änderung noch nicht angewendet, oder das Gerät
ließ sich nicht öffnen), sagt die Zeile das in Bernstein. Ein
gespeicherter Wert ist kein Beleg dafür, dass er auch benutzt wird.


> **Auswirkung auf den Sendebetrieb.** Der zweite Neustart
> trennt die Icecast-Quellverbindungen für einige Sekunden;
> Hörer nehmen eine kurze Lücke wahr. Am besten zwischen zwei
> Sendungen ausführen. Der Knopf fragt vorher nach.

> **Wie das Gerät zugeordnet wird.** PortAudio listet denselben
> Endpunkt einmal pro Windows-Host-API auf (MME, DirectSound,
> WASAPI, WDM-KS), und welche Kopie tatsächlich funktioniert,
> ist gerätespezifisch. RASTATIME probiert die Kandidaten daher
> beim Start durch — über PortAudios **blockierende** API, also
> genau den Weg, den Liquidsoap selbst nimmt — und nimmt den
> ersten, der wirklich aufgeht. Auf der Studio-Maschine bei
> 44,1 kHz gemessen: MME und DirectSound funktionieren für ein
> USB-Headset; WASAPI funktioniert, wenn das Windows-Format des
> Endpunkts passt (siehe nächster Hinweis), und WDM-KS beherrscht
> die blockierende API überhaupt nicht. Öffnet kein Kandidat,
> bleibt der OS-Standard-Endpunkt aktiv, und jeder Fehlergrund
> wird im Playout-Log vermerkt.

> **Das Gerät steht mit Namen im Skript, nicht mit Nummer.**
> PortAudio nummeriert seine Geräte in Aufzählungsreihenfolge, und
> auf einer Maschine, auf der Endpunkte nach einem Neustart spät
> erscheinen oder kommen und gehen (USB-Headsets, HDMI-Audio),
> verschieben sich diese Nummern. Seit dem 2026-09-05 benennt das
> Skript den Endpunkt daher (`device_name="…"`); Liquidsoap schlägt
> den Namen nach, wenn *es* startet, sodass eine Nummer, die sich
> zwischen den beiden Dienststarts geändert hat, den Monitor nicht
> mehr auf die falsche Buchse schicken kann. Der Name wird nur
> verwendet, wenn der Eintrag, den er auswählt, bekanntermaßen
> spielt (MME oder WASAPI, im selben Test wie oben geöffnet);
> andernfalls fällt RASTATIME auf die Nummer zurück und begründet
> das im Playout-Log. Die „Aktiv"-Zeile oben zeigt, was in Gebrauch ist.

> **Das Windows-Format des Geräts muss 44,1 kHz sein.** Liquidsoap
> läuft mit 44,1 kHz, und WASAPI im Shared-Modus verlangt exakt die
> eingestellte Mix-Rate des Endpunkts. Ein Gerät, dessen Windows-
> Standardformat auf 48 kHz steht, wird von jeder Host-API abgelehnt
> und wirkt tot — gemessen am Tascam US-16x08, der unbrauchbar war
> und in dem Moment funktionierte, als sein Format auf 44,1 kHz
> gestellt wurde (Windows-Sound → der Ausgang → Erweitert →
> Standardformat). Das Playout-Log verweist bei einer abgelehnten
> Abtastrate genau auf diese Korrektur. Eine Treiber-Neuinstallation
> kann das Format zurücksetzen; die Aktiv-Zeile oben zeigt dann die
> Abweichung. Ausgabe und Line-In-Aufnahme am selben Interface
> laufen gleichzeitig.

### Automatische Neustarts und Gesundheitswarnungen

Zwei Situationen starten die Audio-Engine ohne den Knopf neu, und
drei Dashboard-Warnungen wachen über sie (seit dem 2026-09-05; die
Sicherung und die dritte Warnung seit dem 2026-09-07):

- **Nach einem Neustart der Maschine.** Beide Dienste starten
  parallel, und die Engine kann das vorherige Skript laden, bevor
  das Playout das neue gerendert hat. Stellt das Playout fest, dass
  sein Render das Skript innerhalb der ersten zehn Minuten nach dem
  Hochfahren geändert hat, startet es RASTATIME-LIQUIDSOAP selbst
  neu. So früh ist nichts auf Sendung. Spätere Änderungen brauchen
  weiterhin den Knopf oder die manuelle Reihenfolge: zuerst
  Playout, dann Liquidsoap.
- **Geplanter Neustart.** Der Windows-Build von Liquidsoap verliert
  im Betrieb langsam Speicher, deshalb startet das Playout ihn
  gezielt neu. Wann: in einem Fenster ab 04:00 Uhr
  (Maschinen-Einstellung `RASTATIME_LIQUIDSOAP_NIGHTLY_RESTART`,
  `HH:MM` oder `off`), sobald die Engine älter als N Tage ist
  (`RASTATIME_LIQUIDSOAP_RESTART_EVERY_DAYS`, Standard 1, `0` = aus)
  oder mehr als `RASTATIME_LIQUIDSOAP_RESTART_AT_MB` belegt (Standard
  1536); und zu jeder Tageszeit oberhalb von
  `RASTATIME_LIQUIDSOAP_RESTART_HARD_MB` (Standard 3072). Wie (seit
  2026-09-09): in einem ruhigen Moment, wenn nichts auf Sendung ist,
  oder bei 24/7-Programm zwischen zwei Titeln der laufenden Playlist,
  sodass die Lücke von etwa zwei Sekunden einen Crossfade ersetzt,
  statt in einen Titel zu schneiden. Ein Webstream oder Line-In auf
  einer Seite der Titelgrenze lässt den Neustart auf die nächste
  warten. Seit dem 2026-10-02 steigt der Titel nach dem Neustart um die
  paar Sekunden, die der Neustart gedauert hat, in sein Audio ein, damit
  die Sendung ihre Zeiten behält, statt bis zum Ende so viel zu spät zu
  laufen. Seit dem 2026-09-09 melden die DJ-Quellen ihr Verbinden
  und Trennen selbst, das Playout fragt die Engine also nicht mehr
  alle fünf Sekunden ab; diese Abfrage war die Hauptursache des
  Wachstums. Bleibt der Speicher eine Woche lang flach, kann
  `RASTATIME_LIQUIDSOAP_RESTART_EVERY_DAYS` erhöht werden (7 bis 30).
- **Standby-Fallback für Hörer.** Ein zweites, kleines Liquidsoap
  (Dienst RASTATIME-STANDBY, Skript `standby.liq`, vom Playout mit
  denselben Encodern gerendert) streamt Stille auf eine `-standby`-
  Kopie jedes öffentlichen Mounts, und `icecast.xml` verweist jeden
  öffentlichen Mount als Fallback darauf. Während der zwei Sekunden
  eines Neustarts schiebt Icecast die Hörer auf den Standby-Mount und
  wieder zurück; niemand wird getrennt. Einmalig als Administrator mit
  `backend/playout/config/nssm-install-standby.ps1` installieren,
  nachdem das Playout `standby.liq` gerendert hat, danach Icecast
  einmal neu starten, damit es die Fallback-Mounts liest. Setzen Sie
  `RASTATIME_STANDBY_AUDIO` auf eine Audiodatei, wenn Sie ein
  Stations-Bett statt Stille bevorzugen. Wenn Sie einen Stream-Output
  umbenennen oder neu anlegen, folgt die Standby-Seite von selbst
  (RASTATIME-STANDBY neu starten, sobald das Playout-Log dazu
  auffordert); die Fallback-Blöcke von Icecast folgen nicht: tragen Sie
  in `icecast.xml` einen passenden Block für den neuen Mount ein und
  starten Sie Icecast neu. Das Playout warnt bei jedem Start im Log
  vor öffentlichen Mounts ohne Fallback.
- **Per Name oder gar nicht.** Unmittelbar vor jedem automatischen
  Neustart liest das Playout die Soundkarten-Liste neu ein und
  adressiert den Main Output über den Geräte-*Namen*. Ist das in
  diesem Moment nicht möglich (das Studio-Display schläft und sein
  HD-Audio-Endpunkt ist verschwunden, das Gerät wurde umbenannt,
  oder nur ein DirectSound/WDM-KS-Eintrag passt), entfällt der
  automatische Neustart und die laufende Engine spielt weiter; das
  Playout-Log nennt den Grund. Starten Sie manuell neu, sobald das
  Gerät wieder da ist. Hintergrund: am 2026-09-06 und 2026-09-07
  verwendete der 04:01-Neustart einen Geräteindex, der bei
  schlafendem Display ermittelt worden war; die frische Engine
  öffnete den falschen Endpunkt, starb nach zwei Sekunden und wurde
  bis zum Morgen in einer Schleife neu gestartet.
- **Speicher-Warnung.** Das Dashboard-Banner zeigt *Liquidsoap
  belegt N MB*, wenn der Speicher der Engine 2048 MB überschreitet
  (Maschinen-Einstellung `RASTATIME_LIQUIDSOAP_MEMORY_WARN_MB`).
  Starten Sie in einem ruhigen Moment das Playout und danach
  Liquidsoap neu. Seit dem 14.09.2026 hält das Playout-Log außerdem alle 15 Minuten
  den Speicher der Engine samt Zuwachs seit ihrem Start fest; suchen
  Sie in `playout-stdout.log` nach `Liquidsoap memory`, um den
  Verlauf zu sehen.
- **Main-Output-Warnung.** Das Banner zeigt *Main Output: Liquidsoap
  spielt auf … statt …*, wenn die Engine keine Audio-Sitzung auf
  dem gewählten Ausgabegerät hält, obwohl sie schon eine Weile
  läuft. Der Monitor liegt dann auf der falschen Buchse; starten
  Sie das Playout und danach Liquidsoap neu.
- **Main Output bleibt offen.** Seit dem 14.09.2026 öffnet die Engine
  den Main Output einmal beim Start und schließt ihn nicht mehr,
  solange sie läuft. Der kleine Puffer vor dem Gerät lief früher etwa
  zweimal am Tag leer; die Engine öffnete das Gerät dann mit einer
  veralteten Geräteliste neu und brach entweder ab oder spielte auf
  ein anderes Gerät. Jetzt überbrückt eine kurze Stille einen solchen
  Moment, und der Puffer passt das Abspieltempo unhörbar an, damit er
  gefüllt bleibt. Falls Sie diese Anpassung je in Verdacht haben,
  setzen Sie die Maschinen-Einstellung
  `RASTATIME_LIQUIDSOAP_LOCAL_OUTPUT_ADAPTIVE` auf `false` und starten
  Sie das Playout und danach Liquidsoap neu; der Ausgang bleibt dann
  mit einem festen Puffer offen.
- **Engine-läuft-nicht-Warnung.** Das Banner zeigt *Liquidsoap läuft
  nicht* oder *Liquidsoap startet ständig neu (Absturzschleife)*,
  wenn kein Engine-Prozess existiert oder bei jedem Scan ein neuer
  auftaucht. Lesen Sie die neueste
  `logs/liquidsoap-stdout-*.log`-Scheibe (meist das Main-Output-
  Gerät), beheben Sie die Ursache und starten Sie dann das Playout
  und danach Liquidsoap neu.

---

## 3. Soundkarte — Eingabegeräte

Die Liste zeigt jedes Audio-Eingabegerät, das die
Operator-Maschine exponiert (eingebaute Mikrofone,
USB-Mics, Mixer-Ausgänge, Line-In-Buchsen usw.). Das
Kontrollkästchen steuert, welche davon **Kandidaten** für
die Verwendung als benannte Line-Ins sind.

### Welche aktivieren

| Gerät | Ankreuzen? | Warum |
|---|---|---|
| **Studio-Mikrofon** | Ja | Der Grund, warum die meisten Stationen einen Line-In haben. |
| **Mixer-Ausgang** (XLR / TRS via Interface) | Ja | Der vollständige Studio-Mix als einzelne Quelle. |
| **Eingebautes Mikrofon** | Nur wenn verwendet | Abwählen unterdrückt es vom Line-In-Erstellungs-Dropdown, um versehentliche Auswahl zu vermeiden. |
| **Webcam-Mikrofon** | Nein (normalerweise) | Niedrige Qualität, wird oft versehentlich ausgewählt. |
| **Line-In-Buchse auf der Rückseite** (wenn nicht in Verwendung) | Nein | Dieselbe Unfall-Prävention. |

Ankreuzen / Abwählen **deaktiviert** das Gerät auf
OS-Ebene nicht — Windows sieht es weiterhin. RASTATIME
entfernt es nur aus dem Line-In-Erstellungs-Dropdown.

### Vom Eingabegerät zum benannten Line-In

Um ein Gerät als Scheduling-Quelle zu verwenden, erstellen
Sie einen benannten Line-In in der Bibliothek unter **Line
Inputs → + Neu** — seit dem 17.09.2026 ist dieser Dialog der
eine vollständige Editor (Name, Gerät, Kanäle); die
frühere Line-In-Sources-Sektion auf dieser Seite gibt es
nicht mehr.  Siehe [Line-In](./LINE_IN.md).

> **Operator-Tipp.** Ein Gerät muss hier *vor* dem
> Erscheinen im Geräte-Dropdown des Neuer-Line-In-Dialogs
> angekreuzt sein. Wenn Sie Ihr USB-Mikrofon im
> Line-In-Dialog nicht finden, ist der häufigste Grund,
> dass es auf dieser Seite nicht angekreuzt ist.

---

## 4. Standard-Ausgang für Cue / Monitor

Das Dropdown unter der Ausgabegeräte-Liste wiederholt den
Standard in Einzelzeilen-Form. Die Auswahl ist dieselben
Daten wie der Radio-Button oben; beide bleiben
synchronisiert.

(Operativ redundant; beibehalten für Ein-Klick-Auffindbarkeit
durch Operatoren, die an der Geräteliste vorbeiscrollen
und nach einer "Standard setzen"-Steuerung suchen.)

---

## 5. Lokaler Import-Ordner

Der lokale Import-Ordner ist ein Verzeichnis auf der
Operator-Maschine, das der Analyzer auf neue Dateien
überwacht. Alles, was in den Ordner abgelegt wird, wird
beim nächsten Analyzer-Poll-Zyklus (standardmäßig alle
60 s) automatisch in die Bibliothek importiert.

### Den Ordner konfigurieren

| Feld | Hinweise |
|---|---|
| **Ordnerpfad** | Ein absoluter Pfad auf der Operator-Maschine. Muss existieren und vom RASTATIME-ANALYZER-Dienst lesbar sein. Standard: `C:\rastatime\import\`. Leer lassen, um die Funktion zu deaktivieren. |
| **Zuletzt gescannt** | Wann der Analyzer zuletzt einen Scan + Zusammenfassung des Ergebnisses ausgeführt hat. Aktualisieren Sie die Seite, um das Neueste zu sehen. |

Die Schaltfläche **Jetzt scannen** löst einen sofortigen
Scan aus, ohne auf den 60-s-Poll zu warten. Verwenden Sie
sie nach dem Ablegen eines Batches in den Ordner, um ohne
Verzögerung zu importieren.

### Wie Dateien verarbeitet werden

Der Scanner läuft alle 5 Minuten (und sofort bei **Scan Now**).  Für
jede Datei, die direkt im Ordner liegt:

1. **Nicht-Audio-Dateien werden übersprungen** und bleiben liegen —
   der Scanner nimmt nur Audiodateien (`mp3`, `wav`, `m4a`, `flac`,
   `ogg`, `oga`, `aac`, `opus`).  Die Statuszeile zählt sie als
   „skipped".
2. **Noch nicht zur Ruhe gekommene Dateien bleiben für später (seit
   17.09.2026).**  Eine in den letzten 60 Sekunden veränderte Datei
   wird womöglich noch geschrieben (langsame Kopie, FTP-Upload); die
   Statuszeile zählt sie als „settling", ein späterer Durchlauf nimmt
   sie mit.
3. Jede ruhende Audiodatei geht an die **Standard-Upload-Pipeline**:
   ein Bibliothekseintrag wird angelegt, die Datei wird in den
   `organize`-Bereich der Bibliothek **verschoben** (nicht kopiert),
   und der Analyzer übernimmt — Metadaten lesen, Abspielbarkeits-
   Prüfung, endgültiger Platz in der Bibliothek.  Ab da verhält sie
   sich genau wie eine über die Web-Oberfläche hochgeladene Datei.
4. **Schlägt die Übergabe fehl, wird die Quelldatei gelöscht** —
   beim ersten Versuch und mit Absicht: Eine dauerhaft kaputte Datei
   darf sich nicht im Ordner stauen und bei jedem Scan erneut
   versucht werden.

Der Ordner leert sich also nach jedem Durchlauf von Audiodateien —
bei Erfolg in die Bibliothek verschoben, bei Fehlschlag gelöscht.
Nicht-Audio-Dateien bleiben.

### Unterordner und große Mengen (seit 2026-10-08)

Unterordner werden **durchlaufen**: Jede Audiodatei im Import-Ordner
und in jedem Unterordner wird importiert, Ordner für Ordner in
Pfadreihenfolge; ein Unterordner, den die Verschiebungen leer
zurücklassen, wird entfernt.  Die Ordnerstruktur wandert nicht in die
Bibliothek (sie ordnet Dateien nach ihren Metadaten), taggen Sie die
Dateien also vor dem Kopieren.

Ein Scan übergibt außerdem nichts, solange noch **300 oder mehr
Dateien** beim Analyzer anstehen (er verarbeitet etwa eine Datei pro
Sekunde); die Statuszeile zeigt diese Warteschlange.  So bleiben der
Bibliothek Zeilen erspart, die so lange warten, dass die stündliche
Aufräumaufgabe sie als fehlgeschlagen markiert.

Ein Scan übergibt höchstens **300 Dateien** und hält nach **20
Sekunden** an; der Rest wartet auf den nächsten Lauf (alle 5 Minuten
oder **Scan Now**), die Statuszeile nennt die Zahl der wartenden
Dateien.  So bleibt ein Scan innerhalb des PHP-Zeitlimits - ein
mitten im Verschieben abgebrochener Scan hinterließ früher eine halbe
Datei.  Der Analyzer arbeitet die Warteschlange danach Datei für Datei
ab; auf dieser Maschine braucht eine vierminütige MP3 etwa
1.1 s (Probe mit 50 Dateien, 2026-10-08), rechnen Sie also mit
rund 3.000 Titeln pro Stunde von Anfang bis Ende und für 20.000 Titel
mit etwa sieben Stunden.  Legen Sie den Import-Ordner auf dasselbe Laufwerk wie
die Mediathek (das Verschieben ist dann sofort und atomar), setzen Sie
vorher *Track Type Upload Default* (der Besitzer braucht keine
Einstellung: Hintergrund-Importe gehören dem ersten Administrator,
Scan-Now-Importe Ihnen) und kopieren Sie in Tranchen von einigen
tausend Dateien.

### Besitz

Bei **Scan Now** gehören die importierten Dateien dem Operator, der
den Knopf gedrückt hat.  Dateien aus dem Hintergrund-Scan gehören dem
ersten Administrator-Konto.

> **Wie es unter der Haube funktioniert.**  Der Scanner ist der
> `LocalImportScanTask` im Task-Manager des Legacy-PHP-Frontends: Er
> reitet auf normalen Web-Anfragen mit, läuft höchstens alle 300 s
> und aktualisiert die `cc_pref`-Schlüssel `local_import_last_run`
> und `local_import_last_status` (die Statuszeile auf dieser Seite).
> Siehe ARCHITECTURE §23.12.

### Import vom FTP-Server

Unter dem Import-Ordner sitzt eine zweite Import-Quelle (seit
17.09.2026): RASTATIME holt alle 5 Minuten (oder sofort mit **Fetch
now**) Audiodateien von einem FTP-, FTPS- oder SFTP-Server und führt
sie durch den Import-Ordner oben — der dafür konfiguriert sein muss.
Aktivieren Sie die Checkbox, tragen Sie Server, Port (leer =
Protokoll-Standard), Konto und den **absoluten** entfernten Ordner
ein, dann **Save FTP import**.

- **Briefkasten-Semantik.**  Nach einem verifizierten Download wird
  die entfernte Datei gelöscht — das Konto braucht Löschrecht.
  Scheitert das Löschen, wird die Datei trotzdem importiert und der
  Status warnt, weil der nächste Zyklus sonst ein Duplikat holt.
- **Laufende Uploads sind sicher.**  Eine Datei wird erst geholt,
  wenn ihre Größe über zwei Prüfungen hinweg mindestens eine Minute
  unverändert war, und nach dem Download wird die Größe erneut
  verglichen.  Bis dahin zählt der Status sie als „settling".
- **Nicht-Audio-Dateien bleiben auf dem Server.**  Geholt werden nur
  die Audio-Endungen des Import-Ordners.
- **Bevorzugen Sie FTPS oder SFTP** — Klartext-FTP überträgt das
  Passwort unverschlüsselt.  Das Passwort liegt wie die anderen
  Dienst-Passwörter in der Einstellungs-Datenbank, damit die
  Abholung unbeaufsichtigt anmelden kann; die Seite zeigt es nie
  wieder an.
- Jeder Zyklus startet höchstens eine Minute lang neue Downloads;
  was darüber hinausgeht, nimmt der nächste Zyklus mit („left for
  the next run" im Status).

---

## 6. Speicherort der Medienbibliothek

Seit dem 16.09.2026 ist der Ordner, in dem die Medienbibliothek liegt
(importierte Titel, Cover, Show-Bilder), eine Einstellung auf dieser
Seite und keine Zeile in `libretime.conf` mehr. Die Konfigurationsdatei
liefert nur den Anfangswert; sobald Sie die Bibliothek einmal verschoben
haben, gilt die Einstellung.

Der Abschnitt zeigt den **aktuellen Speicherort**, woher der Wert
stammt (Einstellung oder Konfigurationsdatei), die Zahl der Dateien und
die Größe der Bibliothek. So verschieben Sie sie:

1. Geben Sie den **neuen Speicherort** ein - einen absoluten Pfad auf
   einem lokalen Laufwerk dieses Rechners, zum Beispiel `D:\stor`. Der
   Ordner wird bei Bedarf angelegt. Netzlaufwerke werden nicht
   unterstützt.
2. Klicken Sie auf **Prüfen**. RASTATIME bestätigt, dass es dort
   schreiben kann und dass genug freier Platz vorhanden ist (die
   Bibliothek plus zehn Prozent).
3. Klicken Sie auf **Bibliothek verschieben** und bestätigen Sie. Ein
   Fortschrittsbalken begleitet die Kopie.

Was während des Verschiebens passiert:

- Stream, Sendeplan, Aufnahmen und der lokale Monitor laufen weiter;
  nichts sendet direkt aus dem Bibliotheksordner, das Playout spielt
  aus seinem Cache.
- Importe pausieren: Uploads, die Prüfung des lokalen Import-Ordners,
  Podcast-Downloads und Bild-Uploads lehnen mit einer kurzen Meldung
  ab, bis der Umzug fertig ist.
- RASTATIME kopiert die Bibliothek mit robocopy, prüft dann, dass jede
  Datei in der richtigen Größe angekommen ist und dass jeder Titel der
  Datenbank am neuen Ort gefunden wird. Erst dann schaltet es die
  Einstellung um. Web-Anwendung und API folgen sofort, das Playout beim
  nächsten Aktualisieren des Sendeplans (innerhalb von zwei Minuten).
- Die **bisherige Kopie bleibt auf der Platte**. Löschen Sie sie
  selbst, sobald Sie zufrieden sind - und nur ihren Inhalt, nicht den
  in `libretime.conf` genannten Ordner, weil die Web-Anwendung beim
  Start prüft, dass dieser Ordner existiert.

Startet der Dienst RASTATIME-API während einer laufenden Kopie neu,
zeigt der Abschnitt den Umzug als *unterbrochen*. Geben Sie dasselbe
Ziel erneut ein und verschieben Sie noch einmal: Die Kopie setzt dort
fort, wo sie stehen blieb, bereits kopierte Dateien werden übersprungen.
**Umzug abbrechen** stoppt eine laufende Kopie; das bisher Kopierte
bleibt am Ziel, ein späterer Umzug setzt darauf auf.

Sollte der eingestellte Speicherort einmal fehlen oder schreibgeschützt
sein - eine nicht eingebundene Platte, ein umbenannter Ordner - zeigt
das Dashboard-Banner *Media library location … is missing*, bis er
wieder da ist.

---

## 7. Aufnahme-Ordner (verwandt)

Einstellungen → Lokale Maschine hat **zwei** Aufnahme-Ausgabe-
Ordner:

### Show Recording Folder

Wohin [Aufnahme pro Sendung](./RECORD_PER_SHOW.md) eine Datei je
als „Aufnahme" markierter Sendung schreibt. *(Umbenannt von
„Recording Folder", als die 24/7-Aufnahme dazukam — 2026-06-06.)*

Standard: `C:\rastatime\recordings\`.

### 24/7 Recording Folder

Wohin die durchgehende [24/7-Aufnahme](./RECORD_PER_HOUR.md) eine
Datei pro Uhr-Stunde schreibt (plus ein `.cues.json`-Cue-Sidecar),
unabhängig von Sendungen. Aktivieren, Format / Bitrate wählen und
ein Auto-Lösch-Fenster setzen Sie direkt in diesem Abschnitt.
Halten Sie ihn **getrennt** vom Show Recording Folder, damit das
Retention-Aufräumen nie Per-Sendung-Dateien anfasst. Der Ordner
wird beim Speichern angelegt, falls noch nicht vorhanden.

Keiner der Ordner ist ein Kandidat für die Bibliothek — Aufnahmen
sind eigenständige Dateien zum Download / Archiv, nicht
automatisch importiert. Um eine Aufnahme als Track zurück in die
Bibliothek zu legen, ziehen Sie sie manuell in den lokalen
Import-Ordner.

> **Änderungen durch Neustart des Playout-Dienstes anwenden.** Die
> Recorder-Einstellungen werden beim Start in das Liquidsoap-
> Skript eingebacken; starten Sie nach einer Änderung also
> **RASTATIME-PLAYOUT** neu (der Save-Dialog erinnert daran). Nur
> der 24/7-Wert **Delete after (days)** wirkt ohne Neustart.

---

## 8. Häufig gestellte Fragen

### "Mein USB-Mikrofon erscheint in Windows, aber nicht in RASTATIME."

Drei Dinge zu prüfen:

1. Das Mikrofon ist auf der Eingabegeräte-Liste auf dieser
   Seite **angekreuzt**.
2. Der `RASTATIME-API`-Dienst läuft und der
   `/api/v2/audio/devices`-Endpunkt gibt das Mikrofon
   zurück — testen Sie mit
   `curl http://localhost:8765/api/v2/audio/devices`.
3. Der Windows-Audio-Treiber erlaubt weiterhin
   Eingangszugriff (einige Windows-Updates setzen dies
   zurück; prüfen Sie Einstellungen → Datenschutz →
   Mikrofon).

### "Lokaler Import-Ordner importiert nichts."

Diagnose-Reihenfolge:

1. Der Ordnerpfad ist korrekt und existiert.
2. Das Web-Frontend läuft (`RASTATIME-APACHE`) — der Scanner
   reitet auf Web-Anfragen mit, **Zuletzt gescannt** rückt also
   nur vor, solange die Oberfläche Verkehr sieht.  **Scan Now**
   erzwingt einen Durchlauf.
3. Eine in den letzten 60 Sekunden veränderte Datei zählt als
   „settling" — eine Minute warten und erneut scannen.
4. „failed N" in der Statuszeile heißt: die Übergabe schlug fehl
   und die Quelle wurde gelöscht (Absicht).  Prüfen Sie die Datei
   in einem anderen Player und suchen Sie den Grund in
   `logs\legacy.log`; für den fertigen Import muss der Dienst
   `RASTATIME-ANALYZER` laufen.

### "Warum verschieben und nicht kopieren im lokalen Import-Ordner?"

Ein kopierbasierter Workflow hinterlässt dem Operator zwei
Kopien jeder importierten Datei und keine klare
Eigentümerschaft. Ein verschiebungsbasierter Workflow
garantiert, dass die Datei nach dem Import an genau einem
Ort ist. Operatoren, die das Original behalten möchten,
sollten eine Kopie in den Import-Ordner ablegen, nicht das
Original.

### "Kann der lokale Import-Ordner auf einer Netzwerkfreigabe sein?"

Ja, mit zwei Vorbehalten:

- Die Freigabe muss an dem Pfad gemountet sein, den
  RASTATIME sieht (z.B. `Z:\import\`). UNC-Pfade
  `\\server\share\import` sind *nicht* zuverlässig mit
  NSSM-gestarteten Diensten unter Windows.
- Das RASTATIME-ANALYZER-Dienstkonto muss Lese- +
  Schreib- + Lösch-Berechtigung auf der Freigabe haben.

### "Kann ich mehrere lokale Import-Ordner haben?"

Nein. Der Poller scannt ein konfiguriertes Verzeichnis.
Wenn Sie mehrere Drop-Punkte benötigen, mounten Sie sie
alle unter einer einzelnen Wurzel (z.B. `Z:\imports\` mit
Unterverzeichnissen für jede Quelle).

### "Was ist der Unterschied zwischen dem lokalen Import-Ordner und der Upload-Schaltfläche?"

| | Upload-Schaltfläche | Lokaler Import-Ordner |
|---|---|---|
| Herkunft | Browser-seitig | Server-seitiges Dateisystem |
| Am besten für | Eine oder zwei Dateien | Batches vieler Dateien |
| Timeout | Browser kann bei großen Batches Timeout | Kein Timeout (server-seitiger Poller) |
| Besitz | Eingeloggter Benutzer | Konfigurierter Standard-Besitzer |

### "Beeinflusst die Ausgabegerät-Auswahl, was Hörer hören?"

Nein. Das Ausgabegerät auf dieser Seite ist der **Monitor- /
Cue**-Ausgang. Hörer hören den
[Streams](./STREAMS.md)-Ausgang, der an Icecast gesendet
wird und unabhängig von diesem Gerät ist.

---

## Wohin als Nächstes

* [Line-In](./LINE_IN.md) — ein angekreuztes Eingabegerät
  in ein benanntes, einplanbares Bibliotheks-Item
  verwandeln.
* [Bibliothek](./LIBRARY.md) → §2 — Alternativen zum
  lokalen Import-Ordner (Browser-Upload, Podcast-
  Abonnement).
* [Streams](./STREAMS.md) — der hörer-seitige Audio-
  Ausgang.
* [`docs/operator/DEVICE_MISSING.md`](../../operator/DEVICE_MISSING.md)
  — wenn ein zuvor konfiguriertes Gerät verschwindet.
