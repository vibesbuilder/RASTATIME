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

> **Auswirkung auf den Sendebetrieb.** Der zweite Neustart
> trennt die Icecast-Quellverbindungen für einige Sekunden;
> Hörer nehmen eine kurze Lücke wahr. Am besten zwischen zwei
> Sendungen ausführen. Der Knopf fragt vorher nach.

> **Wie das Gerät zugeordnet wird.** PortAudio listet denselben
> Endpunkt einmal pro Windows-Host-API auf (MME, DirectSound,
> WASAPI, WDM-KS), und welche Kopie sich tatsächlich öffnen
> lässt, ist gerätespezifisch — auf der Studio-Maschine
> gemessen: Der Tascam-US-16x08-Ausgang öffnet **nur** über
> WDM-KS, ein USB-Headset dagegen über MME. RASTATIME probiert
> die Kandidaten daher beim Start durch, den am wenigsten
> invasiven zuerst, und nimmt den ersten, der wirklich
> aufgeht. Das Ergebnis steht als `device_id=` samt Kommentar
> im Skript. Öffnet kein Kandidat, fällt RASTATIME auf den
> OS-Standard-Endpunkt zurück und vermerkt das im Playout-Log.

> **Ein Interface für Ein- und Ausgang.** Ein Mehrkanal-
> Interface kann gleichzeitig Main Output **und** Line-In-
> Quelle sein (am US-16x08 verifiziert: WDM-KS-Ausgang neben
> einer 16-Kanal-MME-Aufnahme). Beachten Sie, dass ein
> geringer Teil des Ausgangssignals in die Aufnahmekanäle
> einkoppelt — gemessen rund 45–65 dB unter dem Ausgangspegel,
> viel zu wenig für eine Rückkopplung, aber bei einem sehr
> leisen Line-In-Signal kann ein leiser Nachhall des Programms
> mitlaufen.

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
Sie einen benannten Line-In in der Sektion **Line-In
Sources** auf genau dieser Seite (seit 2026-08-31 oberhalb
von Import Folder) — dieser volle Editor wählt auch die
**Eingangskanäle** (Stereo-Paar oder Mono) auf
Mehrkanal-Interfaces. Eine schlanke Schnell-Anlage gibt es
zusätzlich in der Bibliothek unter **Line Inputs → + Neu**
(Kanäle dort standardmäßig 1/2). Siehe
[Line-In](./LINE_IN.md).

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

Für jede neue Datei, die der Analyzer findet:

1. Die Datei wird verschoben (nicht kopiert) in einen
   Staging-Bereich (`C:\rastatime\import\.staging\`).
2. Der Analyzer führt ffprobe (Metadaten) +
   ffmpeg-Abspielbarkeits-Prüfung aus.
3. Bei Erfolg wird die Datei verschoben nach
   `C:\rastatime\media\<owner>\<year>\<month>\<filename>`,
   und eine `cc_files`-Zeile wird eingefügt.
4. Bei hartem Fehler wird die Datei verschoben nach
   `C:\rastatime\import\.failed\` mit einer Sidecar-
   `.err`-Textdatei, die den Fehler erklärt.
5. Bei weichem Fehler (Dekoder-Warnungen, aber vollständige
   Dekodierung) wird die Datei mit einem gelben
   Warning-Badge importiert.

Der eigene Import-Ordner des Operators wird nach jedem Poll
leer gelassen — jede Datei ist entweder importiert oder
nach `.failed` verschoben.

### Unterordner

Unterordner werden rekursiv gescannt. Dateien in
Unterordnern werden importiert, und der **Unterordnername**
wird zum `album`-Metadaten-Feld des importierten Tracks,
wenn der eigene ID3-Album-Tag der Datei leer ist. Dies ist
das übliche Operator-Muster:

```
   C:\rastatime\import\
     ├─ 2026-05-21 Morgensendung/
     │   ├─ intro-jingle.mp3       → album = "2026-05-21 Morgensendung"
     │   ├─ track1.mp3              → album = ditto
     │   └─ outro.mp3               → album = ditto
     └─ stings/
         ├─ news-bumper.mp3         → album = "stings"
         └─ weather-bumper.mp3      → album = ditto
```

### Besitz

Importierte Dateien sind im Besitz des konfigurierten
**Standard-Import-Besitzers** (gesetzt unter Allgemeine
Einstellungen → Standard-Import-Besitzer). Standardmäßig
`admin`. Um Importe einem bestimmten DJ zuzuweisen, ändern
Sie den Besitzer vor dem Auslösen des Imports.

> **Wie es unter der Haube funktioniert.** Der lokale
> Import-Ordner-Poller ist einer der Hintergrund-Jobs des
> Dienstes `RASTATIME-WORKER` (der `LocalImportJob`). Er
> läuft alle 60 s über das `BackgroundRunner`-Framework,
> scannt das konfigurierte Verzeichnis, reiht Dateien in
> die Analyzer-Pipeline ein und aktualisiert die
> `cc_pref`-Schlüssel `local_import_last_run` und
> `local_import_last_status`. Siehe ARCHITECTURE §16.

---

## 6. Aufnahme-Ordner (verwandt)

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

## 7. Häufig gestellte Fragen

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
2. Der `RASTATIME-ANALYZER`-Dienst läuft.
3. Der `RASTATIME-WORKER`-Dienst läuft (er besitzt den
   Poller).
4. Prüfen Sie **Zuletzt gescannt** — wenn es "N neue
   Dateien gefunden, N fehlgeschlagen" zeigt, werden die
   Dateien verarbeitet und scheitern an der
   Abspielbarkeits-Prüfung. Schauen Sie in
   `C:\rastatime\import\.failed\` für die `.err`-Dateien.

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
