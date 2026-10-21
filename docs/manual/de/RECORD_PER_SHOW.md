# Aufnahme pro Sendung

> **Wo Sie sich im Handbuch befinden.** Dies ist ein
> per-show-Toggle auf dem Sendungs-Bearbeitungsformular
> (siehe [Kalender](./CALENDAR.md) §2.3). Die Funktion
> ersetzt die ursprüngliche "Record from Line In?"-
> Checkbox durch eine breitere "Aufzeichnen, was während
> der Sendung auf Sendung geht"-Erfassung. Abschnitt 23.13
> in ARCHITECTURE behandelt die technischen Entscheidungen.

**Aufnahme pro Sendung** schreibt eine Datei mit allem, was
während einer Sendung auf Sendung war — die Musik, das Live-
Mikrofon, das Webstream-Relay, alles davon — für Archiv,
Wiedergabe, Podcast oder Compliance-Zwecke.

Die Aufnahme ist ein paralleler **Output-Tap**: sie ändert
nichts daran, wie die Sendung geplant oder abgespielt wird.
Der Recorder hört einfach den öffentlichen Icecast-Output
ab und schreibt ihn für die Dauer der Sendung in eine Datei.

---

## 1. Warum es so funktioniert

### Was das ursprüngliche LibreTime tat

Die ursprüngliche LibreTime-"Record from Line In?"-Funktion
zeichnete *nur* die Line-In-Quelle (einen bestimmten
physischen Eingang) auf, unter Verwendung von Liquidsoap.
Die Aufnahme begann, wenn die Sendung startete, und
stoppte, wenn sie endete; der aufgezeichnete Inhalt war
immer genau das Line-In-Audio.

Das war nützlich für "ein Host mit einem Mikrofon im
Studio", aber kaputt für alles andere:

- Eine Sendung, die zwischen Tracks und einem Mikrofon
  wechselte, erfasste nur den Mikrofon-Teil.
- Eine Sendung, die voraufgezeichnete Segmente spielte,
  zeichnete sie nicht auf.
- Eine Sendung ohne Line-In-Quelle konnte überhaupt nicht
  aufgezeichnet werden.

### Was RASTATIME tut

Das neue Modell zeichnet den **vollständigen On-Air-Output**
auf — was auch immer die Hörer während der Sendung hören,
unabhängig von der Quelle.

> **Architektur-Update — Phase-C5 (2026-05-28).** Die
> Aufnahme-Pipeline wurde von einem separaten FFmpeg-
> Icecast-Tap-Subprozess auf einen Liquidsoap-`output.file`-
> Block migriert, der den internen Audio-Bus direkt abgreift.
> Beide Architekturen liefern dasselbe operator-sichtbare
> Verhalten (Pro-Sendung-Aufnahme in einen Ordner); der
> Bus-Tap ist nur einfacher, zuverlässiger und nutzt
> hochwertigeres festes 320-kbps-MP3. Siehe ARCHITECTURE
> §23.13.bis für die technischen Details.

Die Implementierung ist ein Liquidsoap-
`output.file(id="recording")`-Block im
langlaufenden Liquidsoap-Subprozess. Er zapft denselben
internen Audio-Bus an, der die öffentlichen Icecast-Ausgaben
speist, und kodiert ihn im Format und mit der Bitrate aus
Einstellungen → Lokaler Rechner → **Show Recording** (Standard MP3
320 kbps; seit 2026-10-18 auch AAC, OGG Vorbis und Opus mit 96–320
kbps).  Mit dem Standard lautet der gerenderte Block:

```liquidsoap
output.file(
  id="recording",
  %ffmpeg(format="mp3", %audio(codec="libmp3lame", b="320k", samplerate=44100)),
  {recording_path()},
  fallible=true,
  bus,
)
```

Pypos Pro-Sendung-Start/Stop-Hooks steuern den Lebenszyklus
über die Liquidsoap-Telnet-Schnittstelle:

```
recording.stop
var.set recording_path = C:/.../<YYYY-MM-DD HH-MM-SS> - <show>.mp3
recording.start
```

Das ergibt:

| Eigenschaft | Wert |
|---|---|
| **CPU-Kosten** | ~3 % eines Kerns auf Intel i3-1315U (ein libmp3lame-Encoder) |
| **Qualität** | Standard MP3 320 kbps (Einstellungen → Lokaler Rechner → Show Recording: MP3 / AAC / OGG Vorbis / Opus, 96–320 kbps) — gleiche Quelle wie der Haupt-Icecast-Stream |
| **Quellen-Wechsel** | Automatisch erfasst (Aufnahme greift denselben internen Bus ab wie der Live-Stream) |
| **Fehler-Isolation** | `fallible=true` an `output.file` verhindert, dass ein einzelner Output-Fehler (Disk voll, AV-Scan-Lock) sich im Source-Graph fortpflanzt |

> **Format und Bitrate** werden unter Einstellungen → Lokaler
> Rechner → Show Recording gewählt (seit 2026-10-18; Standard MP3
> 320 kbps, der feste Wert vom 2026-05-27).  Das Playout übernimmt
> eine Änderung im nächsten ruhigen Moment (oder an der nächsten
> Titelgrenze); bereits geschriebene Dateien behalten ihr Format,
> die Dateiendung folgt dem Format (`.mp3` / `.aac` / `.ogg` /
> `.opus`).  Das alte `PlayoutConfig.record_bitrate` wird ignoriert.

> **Die Aufnahme schreibt Liquidsoap** (`output.file` am
> internen Bus). Phase-C5 Teil 2d hat den Legacy-
> FfmpegRecorder-Code-Pfad gelöscht; seit dem 2026-09-10 ist
> Liquidsoap die einzige Playout-Engine, jede Sendung mit
> aktivierter Aufnahme wird also aufgezeichnet.

---

## 2. Aufnahme pro Sendung aktivieren

Pro Sendung, auf dem Sendungs-Bearbeitungsformular. Zwei
Wege dorthin:

### 2.1 Auf einer neuen Sendung

Kalender → Neue Sendung → **Aufnahme**-Abschnitt erweitern
→ **Diese Sendung aufzeichnen:** ankreuzen → Speichern.

### 2.2 Auf einer bestehenden Sendung

Kalender → Sendung klicken → **Sendung bearbeiten** →
**Aufnahme**-Abschnitt erweitern → **Diese Sendung
aufzeichnen:** ankreuzen → Speichern.

Der Toggle wird ab der *nächsten* zu startenden Instanz
wirksam. Eine bereits gestartete Sendung zeichnet nicht
rückwirkend auf (der FFmpeg-Subprozess startet nur, wenn
die Sendung beginnt).

> **Operator-Tipp.** Viele Stationen zeichnen jede Sendung
> standardmäßig auf. Der schnellste Weg, dies stationsweit
> einzurichten: ankreuzen Sie **Diese Sendung aufzeichnen:**
> auf einer Vorlage, speichern Sie als Sendungs-Vorlage
> namens "Aufgezeichnete Sendung" oder ähnlich, dann wenden
> Sie diese Vorlage auf jede Sendung an. Siehe
> [Sendungs-Vorlagen](./SHOW_TEMPLATES.md).

> **Wie es unter der Haube funktioniert.** Der Toggle setzt
> `cc_show.record = TRUE`. Beim Sendungsstart sendet der
> Schedule-Builder der Playout-Engine ein
> `SHOW_RECORD_START`-Event mit der id, dem Namen und der
> Startzeit der Sendung. Der Handler in
> `backend/playout/libretime_playout/playout_scheduler.py`
> sendet einen `recording.start`-Befehl an das Liquidsoap-
> Telnet, das die Pro-Sendung-.mp3-Datei öffnet. Beim
> Sendungsende sendet die Engine `SHOW_RECORD_END`, und der
> Handler sendet `recording.stop`, um die Datei sauber zu
> schließen. Siehe ARCHITECTURE §23.13 (originales FFmpeg-
> Design) und §23.13.bis (Phase-C5 Liquidsoap-Migration).

---

## 3. Wo die Aufnahme lebt

Standardmäßig werden Aufnahmen geschrieben nach:

```
   C:\rastatime\recordings\<show-id>-<starts-at>.mp3
```

Beispiel:

```
   C:\rastatime\recordings\1234-2026-05-21_14-00-00.mp3
```

Das Verzeichnis und das Dateinamen-Muster sind in
`config\libretime.conf` unter dem `[recording]`-Abschnitt
konfiguriert:

```ini
[recording]
output_dir = C:\rastatime\recordings
filename_template = {show_id}-{starts_at:%Y-%m-%d_%H-%M-%S}.mp3
```

Verfügbare Platzhalter: `{show_id}`, `{show_name}`,
`{starts_at}` (datetime), `{ends_at}` (datetime).

> **Operator-Tipp.** Halten Sie die show_id am Anfang des
> Dateinamens. Das OS sortiert nach Dateinamen, also
> bedeutet show_id-zuerst, dass die Aufnahmen in
> chronologischer Reihenfolge bleiben, auch wenn sie
> alphabetisch sortiert werden.

## 3.5 Antivirus-Ausnahme ist PFLICHT

> ⚠️ **Wichtig — gilt für jeden Studio-Rechner mit RASTATIME.**

Echtzeit-Antivirus-Software (Bitdefender, Windows Defender,
Kaspersky, McAfee, ESET, …) scannt jeden Datei-Schreibvorgang
— einschließlich der wachsenden .mp3-Datei, die gerade
aufgezeichnet wird. Bei langen Sendungen (>30 min) sammelt
sich der Scan-Lock-pro-Schreibvorgang so weit an, dass
Liquidsoaps Audio-Pipeline Frames droppt um Schritt zu halten.

Reality-Test 2026-05-28: eine 60-min-Sendung ohne Antivirus-
Ausnahme nahm nur 52 min 53 s Audio auf (~88 % der geplanten
Dauer); dieselbe Aufnahme-Pipeline mit aus dem Antivirus
ausgenommenem Ordner erreichte reproduzierbar 100 %.

**Mitigation: Aufnahme-Ordner zur Ausnahmeliste des Antivirus
hinzufügen.**

- **Bitdefender** (am häufigsten auf RASTATIME-Deployments):
  Bitdefender-GUI → **Schutz** → **Antivirus** →
  **Einstellungen** → **Ausnahmen verwalten** → den
  Aufnahme-Ordnerpfad hinzufügen (z.B.
  `C:\Users\studio\Music\Show Recordings\` oder was Sie unter
  Settings → Local Machine → Show Recording Folder konfiguriert
  haben).
- **Windows Defender**: Einstellungen → **Update & Sicherheit**
  → **Windows-Sicherheit** → **Viren- & Bedrohungsschutz** →
  **Einstellungen verwalten** → **Ausschlüsse hinzufügen
  oder entfernen** → den Aufnahme-Ordner hinzufügen.
- **Andere AVs**: deren Doku konsultieren; die Option heißt
  meist "Ausnahme", "Ausschluss" oder "Whitelist".

Nach dem Hinzufügen der Ausnahme ist kein Neustart nötig;
die nächste Sendungs-Aufnahme läuft mit voller Qualität.

> **Operator-Tipp.** Fügen Sie die Ausnahme bei der
> RASTATIME-Erst-Einrichtung hinzu BEVOR die erste Sendung
> aufnimmt. Sonst haben Sie ggf. ein paar Stunden mit
> verkürzten Aufnahmen, bevor Sie das Problem bemerken.

---

## 3.6 Aufnahmen in die Bibliothek kopieren *(seit 2026-10-19)*

Unter Einstellungen → Lokale Maschine → **Show Recording** gibt es das
Kontrollkästchen **Sendungsaufnahmen in die Bibliothek kopieren**.
Ist es gesetzt, wird jede aufgezeichnete Sendung in die
Medienbibliothek importiert, sobald ihre Aufnahmedatei geschlossen
ist:

- Importiert wird eine **Kopie**; die Datei im Aufnahmeordner bleibt
  unverändert liegen (Ihr Archiv wird nicht angetastet).
- Die Kopie erhält den Track-Typ **Recordings** (wird beim ersten
  Einsatz angelegt), den Titel `<Sendungsname> <JJJJ-MM-TT HH:MM>`,
  den Sendungsnamen als Interpret und das Album `Show Recordings`,
  damit sie in der Bibliothek leicht zu finden ist.
- Der Bibliothekstitel wird **mit der Sendungsinstanz verknüpft**
  (die „aufgezeichnete Datei" des Kalenders), sodass eine spätere
  Wiederholung einer Live-Sendung darauf zugreifen kann.
- Eine bereits importierte Aufnahme wird an ihrer Prüfsumme erkannt
  und nicht ein zweites Mal importiert.
- Der Track-Typ **Recordings** trägt die Überblendung des
  Sendungswechsels (standardmäßig 1 s) statt der 3 s Titel-Überblendung,
  damit eine aus Aufnahme-Scheiben gebaute Wiederholung die Länge des
  Originals behält.  Einstellbar unter Einstellungen → Track Types.

So funktioniert es: Das Playout meldet die geschlossene Datei an die
Web-Anwendung; diese prüft, dass der Pfad im eingestellten
Show-Recording-Ordner liegt, versieht die Kopie per ffmpeg mit Tags
und übergibt sie wie einen Upload an den Analyzer.  Das
Kontrollkästchen wirkt für Sendungen, die nach einem einmaligen
Neustart des Dienstes RASTATIME-PLAYOUT nach dem Update enden;
danach lässt es sich jederzeit ohne Neustart ein- und ausschalten.

## 4. Eine Aufnahme finden und herunterladen

### Aus dem Kalender

Klicken Sie die Sendung → **Aufnahmedatei ansehen** im
Kontextmenü. Erscheint nur, nachdem die Aufnahme fertig
geschrieben wurde (typischerweise ein paar Sekunden nach
Sendungsende).

Der Dialog zeigt:

| Feld | Wert |
|---|---|
| **Dateiname** | `1234-2026-05-21_14-00-00.mp3` |
| **Größe** | `144.5 MB` |
| **Dauer** | `01:00:00` |
| **Bitrate** | `320 kbps` |
| **Download** | Direkter Download-Link |

### Aus dem Dateisystem

Browsen Sie `C:\rastatime\recordings\` direkt. Das
Verzeichnis ist aus Sicherheitsgründen nicht über die
Web-Oberfläche exponiert; nur der per-show
"Aufnahmedatei ansehen"-Dialog gibt Zugriff über die
Oberfläche.

> **Wie es unter der Haube funktioniert.** Der Dialog ruft
> `/api/v2/recordings/<show-instance-id>` auf, das die
> Datei-Metadaten zurückgibt (per ffprobe gemessen). Der
> Download wird über den Storage-Endpunkt mit einer
> Streaming-Antwort bereitgestellt.

---

## 5. Archiv-Größenplanung

Aufnahmen sammeln sich an. Planen Sie die
Festplattenkapazität entsprechend.

Ungefähre Größe für eine 1-stündige Aufnahme bei
typischen Bitraten:

| Stream-Bitrate | 1-Stunden-Größe |
|---|---|
| 96 kbps MP3 | ~43 MB |
| 128 kbps MP3 | ~58 MB |
| 192 kbps MP3 | ~86 MB |
| 256 kbps MP3 | ~115 MB |
| 320 kbps MP3 | ~145 MB |

Eine Station, die 24/7 mit 192 kbps läuft und alle
Sendungen aufzeichnet, füllt etwa **2 GB pro Tag** oder
**730 GB pro Jahr**.

Aufnahmen werden nicht automatisch gelöscht. Um sie zu
rotieren, richten Sie eine geplante Aufgabe auf der
Operator-Maschine ein:

```powershell
# Aufnahmen älter als 90 Tage löschen (PowerShell)
Get-ChildItem "C:\rastatime\recordings\" -File |
   Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-90) } |
   Remove-Item
```

Siehe [`docs/operator/BACKUP.md`](../../operator/BACKUP.md)
für die Aufnahme-Aufbewahrungs-Richtlinien-Vorlage.

---

## 6. Was Aufnahmen enthalten

Der Recorder erfasst **was auch immer der Icecast-
Mountpoint während der Sendung sendet**:

| Quelle | Enthalten? |
|---|---|
| Geplante Tracks | Ja |
| Webstreams | Ja |
| Line-Ins | Ja |
| Show DJ (Live-Remote-Quelle) | Ja |
| Master DJ (stationsweite Live-Quelle) | Ja |
| Auto-DJ-Fallback | Ja (falls eingesprungen) |
| Stille (der Fallback, wenn nichts geplant ist) | Ja (als tatsächliche Stille in der Datei) |

Die Aufnahme enthält auch jeden operator-seitigen Fehler —
"stille Lücke, weil ich Track 3 zu planen vergessen habe"
erscheint als stille Lücke in der Aufnahme. Der Recorder
trifft kein Urteil; er zeichnet auf, was auf Sendung war.

### Was Aufnahmen NICHT enthalten

- **Pre-Fader-Audio** aus dem Studio. Nur das
  Post-Icecast-Audio wird erfasst.
- **Mehrere Stream-Varianten.** Wenn Sie einen 192-kbps-
  Hauptstream und einen 96-kbps-Mobil-Stream haben, wird
  nur der **erste konfigurierte** Stream aufgezeichnet
  (typischerweise der Haupt).
- **Output-Stream-Metadaten** (ICY-Titel-Updates). Die
  MP3-Datei hat ihre eigenen ID3-Tags, die von FFmpeg
  geschrieben werden, nicht die Live-ICY-Metadaten.

---

## 7. Aufnahmen als Podcasts / Catchup verwenden

Ein üblicher Folge-Workflow:

1. Aufnahmen werden in `C:\rastatime\recordings\`
   geschrieben.
2. Eine geplante Aufgabe kopiert sie in ein
   web-zugängliches Verzeichnis (z.B. nginx-Public-Root).
3. Ein RSS-Feed-Generator (separates Tool) produziert
   einen Podcast-Feed, der auf die kopierten Dateien
   zeigt.
4. Hörer abonnieren den Feed.

RASTATIME liefert keinen eingebauten RSS-Generator für
Aufnahmen mit (Podcasts in der Bibliothek sind
**Eingangs**-Abonnements, keine ausgehenden). Das
[`docs/operator/UPGRADE.md`](../../operator/UPGRADE.md)-
Backlog erwähnt ein geplantes
`outbound-podcast`-Feature; noch nicht implementiert.

---

## 8. Compliance-Aufzeichnung

Einige Gerichtsbarkeiten verlangen von Rundfunkstationen,
ein Sende-Log für N Tage aufzubewahren. Aufnahme pro
Sendung mit jeder aufgezeichneten Sendung + einer
Pro-Tag-Archivkopie ist für die meisten Vorschriften
ausreichend, aber:

- Verifizieren Sie, dass die **Bitrate** für Ihren
  Regulator akzeptabel ist (einige verlangen verlustfrei
  oder nahezu verlustfrei).
- Richten Sie **externen Speicher** für Resilienz gegen
  Festplattenausfall ein.
- Dokumentieren Sie die **Chain of Custody** — wer Zugriff
  auf das Archiv hat, wer Dateien löschen kann usw.

> **Operator-Tipp.** Wenn Ihr Regulator verlustfreie
> Archivierung verlangt, ist der Record-per-Show-Output
> (der `-c copy` des verlustbehafteten Icecast-Streams ist)
> nicht ausreichend. Die Alternative ist die
> Internal-Bus-Encoder-Route, die derzeit nicht in
> RASTATIME ist. Sprechen Sie mit Ihrem Regulator über die
> Annahme des verlustbehafteten Archivs als Arbeits-
> Kompromiss; viele tun es, angesichts der De-facto-
> Industriepraxis.

---

## 9. Aufnahme pro Sendung deaktivieren

Sendung bearbeiten → **Aufnahme**-Abschnitt erweitern →
**Diese Sendung aufzeichnen:** abwählen → Speichern.

Effekte:

- Bereits aufgezeichnete Instanzen sind nicht betroffen
  (die Dateien bleiben auf der Festplatte).
- Zukünftige Instanzen starten den FFmpeg-Subprozess nicht.
- Das **Aufnahmedatei ansehen**-Menü-Item verschwindet für
  zukünftige Sendungen.

---

## 10. Häufig gestellte Fragen

### "Warum beginnt die Aufnahme ein paar Sekunden vor der Sendung?"

Der FFmpeg-Subprozess braucht ~1-2 Sekunden zum Hochfahren
und zum Anhängen an den Icecast-Stream. Um zu vermeiden,
dass die allererste Sekunde der Sendung abgeschnitten wird,
startet der Recorder ~3 Sekunden *vor* `starts_at`. Die
aufgezeichnete Datei enthält diese Pre-Show-Sekunden
(typischerweise den Schwanz der vorherigen Sendung oder
des Fallbacks).

Um das Pre-Show-Padding nachträglich zu entfernen, trimmen
Sie die Datei mit ffmpeg:

```
ffmpeg -ss 00:00:03 -i input.mp3 -c copy output.mp3
```

### "Warum ist die Aufnahme still?"

Wenn die gesamte Aufnahme still ist, hat sich der Recorder
an den Stream angehängt, aber der Stream selbst war
während der Sendung still. Verifizieren Sie das Audio des
Streams, indem Sie unter `http://<host>:8000/rastatime`
während einer Live-Sendung zuhören.

Wenn nur Teile still sind, sind das Lücken im Sendeplan
(kein Item spielt), die so wie sie waren aufgezeichnet
wurden.

### "Kann ich nur einen Teil einer Sendung aufzeichnen?"

Nein. Der Toggle ist per Sendung; der Recorder läuft für
die volle Sendungsdauer oder gar nicht. Um teilweise
Aufnahme zu erhalten, bearbeiten Sie die Sendungs-
Definition, um sie in zwei kürzere Sendungen aufzuteilen,
und schalten Sie die Aufnahme nur auf einer ein.

### "Können zwei gleichzeitig sendende Sendungen auf verschiedenen Outputs beide aufzeichnen?"

RASTATIMEs Schedule-Modell ist Single-Show: zu jedem
Zeitpunkt ist höchstens eine Sendung auf Sendung, parallel
auf allen konfigurierten Output-Streams. Die Aufnahme zapft
den internen Liquidsoap-Bus an (derselbe Audio, der alle
Icecast-Outputs speist), also ist "verschiedene Sendungen auf
verschiedenen Outputs" architektonisch kein unterstützter Fall.

### "Erfasst Aufnahme pro Sendung die Live-DJ-Quelle?"

Ja. Solange die Live-DJ-Quelle auf Sendung ist (auf dem
öffentlichen Stream hörbar), wird sie erfasst. Die
Aufnahme unterscheidet keine Quelle — sie ist, was auf dem
internen Liquidsoap-Bus liegt (= was die Hörer hören).

### "Warum ist die Dateigröße der Aufnahme größer als Sendungsdauer × Bitrate?"

Die MP3-Frame-Struktur hat ein paar Bytes Overhead pro
Frame. Für eine 320-kbps-1-Stunden-Datei ist die
tatsächliche Größe typischerweise 144-145 MB statt der reinen
Mathe-Größe von 144 MB.

### "Warum ist eine lange Aufnahme kürzer als die geplante Sendungsdauer?"

Mit ziemlicher Sicherheit scannt Ihr Antivirus die wachsende
.mp3-Datei und blockiert den Liquidsoap-Encoder lange genug,
dass Frames gedroppt werden. Siehe
[Abschnitt 3.5](#35-antivirus-ausnahme-ist-pflicht) — den
Aufnahme-Ordner zur Ausnahmeliste des Antivirus hinzufügen
behebt das.

Eine kleine Rest-Diskrepanz (1–3 Sekunden in einer 1-Stunden-
Sendung) ist normal und kommt von der MP3-Frame-Grenzen-
Ausrichtung.

### "Kann ich mit einer anderen Bitrate als dem Stream aufzeichnen?"

Ja — seit 2026-10-18 unter Einstellungen → Lokaler Rechner →
**Show Recording**: Format MP3 / AAC / OGG Vorbis / Opus und
Bitrate 96–320 kbps (Standard MP3 320 kbps).  Die Aufnahme ist ein
separater Liquidsoap-`output.file`-Block mit eigenem Encoder, also
unabhängig von den öffentlichen Stream-Einstellungen.  Das Playout
übernimmt eine Änderung im nächsten ruhigen Moment; kein manueller
Neustart.

---

## Wohin als Nächstes

* [Streams](./STREAMS.md) — der Output-Stream, den
  Record-per-Show anzapft.
* [Kalender](./CALENDAR.md) — wo Sie pro Sendung
  aktivieren / deaktivieren.
* [Sendungs-Vorlagen](./SHOW_TEMPLATES.md) — Aufnahme auf
  jeder neuen Sendung über eine Vorlage stempeln.
* [`docs/operator/BACKUP.md`](../../operator/BACKUP.md) —
  Aufnahme-Aufbewahrungs-Richtlinien-Vorlage.
