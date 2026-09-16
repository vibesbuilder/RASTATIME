# 24/7-Aufnahme (Record-per-Hour)

> **Wo Sie sich im Handbuch befinden.** Dies ist die
> stationsweite **24/7-Aufnahme**, konfiguriert unter
> [Einstellungen → Lokale Maschine](./LOCAL_MACHINE.md). Sie
> ist die Dauerlauf-Ergänzung zur sendungsbezogenen
> [Aufnahme pro Sendung](./RECORD_PER_SHOW.md).

Die **24/7-Aufnahme** zeichnet rund um die Uhr alles auf, was
auf Sendung geht — unabhängig von Sendungen — und teilt es in
**eine Datei pro Uhr-Stunde**. Sie erfasst die Lücken, die die
Aufnahme pro Sendung verpasst (Auto-DJ-Füller, Stille zwischen
Sendungen, ungeplante Inhalte, Notfälle) und ist damit das
richtige Werkzeug für **Compliance-Archive, Nachhören/Catchup
und Notfall-Backup**.

Wie der Sendungs-Recorder ist sie ein paralleler
**Output-Abgriff** am internen Liquidsoap-Bus: Sie ändert
nichts an Planung oder Wiedergabe — sie hört das On-Air-Signal
mit und schreibt es auf die Platte.

---

## 1. 24/7-Aufnahme vs. Aufnahme pro Sendung

Die beiden Recorder sind unabhängig und können gleichzeitig
laufen — in **getrennte Ordner**.

| | Aufnahme pro Sendung | 24/7-Aufnahme |
|---|---|---|
| **Umfang** | Eine Datei je als „Aufnahme" markierter Sendung | Eine Datei pro Uhr-Stunde, immer an |
| **Erfasst** | Nur während eine aufgenommene Sendung läuft | Alles, 24/7 (inkl. Lücken, Füller, Notfälle) |
| **Konfiguriert** | Pro Sendung (Kalender) | Einmalig (Einstellungen → Lokale Maschine) |
| **Dateiname** | `<YYYY-MM-DD HH-MM> - <Sendung>.mp3` | `<YYYY-MM-DD HH>-00.<ext>` |
| **Qualität** | Fix 320 kbps MP3 | Format + Bitrate wählbar (Default 192 kbps MP3) |
| **Cue-Sidecars** | Nein | Ja (`.cues.json` pro Stunde) |

> **Warum zwei Recorder?** Die Sendungs-Aufnahme liefert eine
> saubere, mit Sendungstitel benannte Datei für die Sendungen,
> die Ihnen wichtig sind. Die 24/7-Aufnahme liefert ein
> lückenloses Archiv der gesamten Ausstrahlung für Compliance
> und Catchup. Viele Stationen betreiben beides.

---

## 2. Wie es funktioniert

Ein zweiter Liquidsoap-`output.file`-Block greift denselben
internen Audio-Bus ab, der auch die öffentlichen Icecast-
Outputs speist, und rotiert zur vollen Stunde in eine neue
Datei:

```liquidsoap
output.file(
  id="recording_hourly",
  reopen_when=rec247_reopen,   # wahr, wenn die Wanduhr-Stunde wechselt
  fallible=true,
  %ffmpeg(format="mp3", %audio(codec="libmp3lame", b="192k")),
  {rec247_path()},             # <Ordner>/<YYYY-MM-DD>/<YYYY-MM-DD HH>-00.mp3
  bus,
)
```

Der Block wird **nur in das laufende Liquidsoap-Skript
gerendert, wenn Sie die Funktion aktivieren**; andernfalls ist
er ein No-Op-Kommentar und der Live-Stream bleibt unberührt.

> **Von Liquidsoap geschrieben.** Wie die Sendungs-Aufnahme
> wird die 24/7-Aufnahme von Liquidsoaps `output.file` am
> internen Bus erbracht (Liquidsoap ist seit dem 2026-09-10 die
> einzige Playout-Engine).

---

## 3. 24/7-Aufnahme aktivieren

**Einstellungen → Lokale Maschine → „24/7 Recording Folder"**
(der Abschnitt direkt über „Show Recording Folder"):

| Feld | Bedeutung |
|---|---|
| **Enable** | Hauptschalter. Bei „an" ist ein Ordner erforderlich. |
| **Folder path** | Absoluter Pfad auf dieser Maschine — wird beim Speichern angelegt, falls nicht vorhanden. Innerhalb oder außerhalb des Projektordners (z.B. `C:\rastatime\recordings-247` oder `D:\rec247`). Halten Sie ihn **getrennt** vom Show Recording Folder. |
| **Format** | MP3 / AAC / OGG (Vorbis) / Opus. Default **MP3**. |
| **Bitrate** | 96–320 kbps. Default **192** (archiv-tauglich, ~halber Platzbedarf von 320). |
| **Delete after (days)** | Automatisches Aufräum-Fenster. `0` = ewig behalten. |

**Save** klicken, dann den **Playout-Dienst neu starten**, um
die Änderung anzuwenden (siehe [§5](#5-änderungen-anwenden)).
Die Statuszeile erinnert daran.

> **Unter der Haube.** Save speichert die cc_pref-Schlüssel
> `local_247_recording_{enabled,folder,format,bitrate,retention_days}`.
> Beim Playout-Start werden sie gelesen und in `rastatime.liq`
> gerendert; der Aufräum-Daemon und der Cue-Writer lesen sie
> ebenfalls.

---

## 4. Wo die Aufnahmen liegen

```
   <Ordner>\<YYYY-MM-DD>\<YYYY-MM-DD HH>-00.<ext>
   <Ordner>\<YYYY-MM-DD>\<YYYY-MM-DD HH>-00.cues.json
```

Beispiel (Ordner `C:\rastatime\recordings-247`, MP3):

```
   C:\rastatime\recordings-247\2026-06-05\2026-06-05 14-00.mp3
   C:\rastatime\recordings-247\2026-06-05\2026-06-05 14-00.cues.json
```

Die Zeiten sind die **lokale Wanduhrzeit des Studio-Rechners**,
damit der Dateiname dem entspricht, was auf Sendung war.
Dateien rotieren zur vollen Stunde; der Übergang ist nahtlos
(keine hörbare Lücke zwischen den Stunden).

### 4.1 Cue-Sidecars

Neben jeder Stunden-Audiodatei liegt ein JSON-**Cue-Sidecar**,
das markiert, was in dieser Stunde passiert ist — damit ein
künftiger Catchup-Player direkt zu einer Sendung oder einem
Track springen kann:

```json
{
  "version": 1,
  "recording": "2026-06-05 14-00.mp3",
  "hour_start": "2026-06-05T14:00:00",
  "audio_start": "2026-06-05T14:00:00",
  "audio_start_offset": 0.0,
  "marks": [
    {"t": 0.0,   "kind": "show",  "event": "start", "name": "Nachmittagsfahrt"},
    {"t": 0.0,   "kind": "track", "event": "start", "show": "Nachmittagsfahrt",
                 "title": "Song A", "artist": "Artist A"},
    {"t": 183.4, "kind": "track", "event": "end"},
    {"t": 600.0, "kind": "webstream", "event": "start", "show": "Nachrichten"}
  ]
}
```

`t` ist der Offset **in Sekunden ab Stundenbeginn**. `kind` ist
`track` / `show` / `webstream` / `linein`; `event` ist `start`
/ `end`. Sendungsgrenzen werden aus einem Wechsel der Sendung
abgeleitet und decken daher jede Sendung mit Inhalt ab. Ein
Track, der über die volle Stunde hinausreicht, hat seinen
`start` im Sidecar der vorherigen Stunde und sein `end` in der
neuen.

Seit dem 16.09.2026 hält das Sidecar auch fest, wann die
Audiodatei der Stunde angelegt wurde: `audio_start` (Ortszeit) und
`audio_start_offset` (Sekunden nach `hour_start`). Eine volle
Stunde hat den Offset 0; die angebrochene erste Stunde nach einem
Neustart - täglich nach dem Neustart um 04:00 - beginnt später, und
ein Player springt dann in dieser Datei zu `t - audio_start_offset`.

---

## 5. Änderungen anwenden

Die 24/7-Einstellungen werden beim Playout-Start gelesen und in
das Liquidsoap-Skript eingebacken. Nachdem Sie eine Änderung
gespeichert haben (Enable, Ordner, Format, Bitrate), **starten
Sie den Playout-Dienst neu**, damit er das Skript neu rendert:

- Den Windows-Dienst **RASTATIME-PLAYOUT** neu starten (er
  rendert `rastatime.liq` neu und startet
  **RASTATIME-LIQUIDSOAP** neu).
- Einen Moment mit wenigen Hörern wählen — der Neustart
  verursacht eine kurze (~5 s) Stream-Unterbrechung.

Ausnahme ist der Wert **Delete after (days)**: der Aufräum-
Daemon liest ihn in jedem Zyklus neu, eine reine Retention-
Änderung wirkt also innerhalb einer Stunde ohne Neustart.

> **Rollback.** Enable abwählen, speichern, neu starten — der
> Recorder-Block wird nicht mehr gerendert und der Stream
> verhält sich exakt wie zuvor. Bereits aufgenommene Dateien
> bleiben auf der Platte.

---

## 6. Automatisches Aufräumen (Retention)

Ist **Delete after (days)** größer als 0, löscht ein Daemon im
Playout-Dienst ganze Tages-Ordner, sobald sie so viele Tage alt
sind. Er läuft etwa einmal pro Stunde.

Er fasst ausschließlich `YYYY-MM-DD`-benannte Tages-Ordner
**innerhalb des 24/7-Ordners** an — Ihr Show Recording Folder
und alle anderen Dateien bleiben unberührt. `0` deaktiviert das
Aufräumen (ewig behalten).

---

## 7. Antivirus-Ausnahme ist PFLICHT

> ⚠️ Gleiche Einschränkung wie bei [Aufnahme pro Sendung §3.5](./RECORD_PER_SHOW.md#35-antivirus-ausnahme-ist-pflicht)
> — und sie wiegt hier noch schwerer, weil der 24/7-Recorder
> **durchgehend** schreibt.

Echtzeit-Antivirus (Bitdefender, Windows Defender, …) scannt
jeden Schreibvorgang in die wachsende Datei und kann den
Encoder lange genug blockieren, dass Audio verloren geht.
**Fügen Sie den 24/7-Ordner zur Ausnahmeliste Ihres Antivirus
hinzu**, bevor Sie den Recorder aktivieren.

Kommt eine Stunden-Datei kürzer heraus, während sonst alles in
Ordnung ist, sind die üblichen Ursachen der Antivirus-Scan oder
eine Überlastung der Maschine (Liquidsoaps „Latency-Catchup"
unter hoher CPU-/Disk-Last kann Aufnahme-Audio verlieren). Die
erste Datei nach dem Aktivieren ist immer eine Teil-Stunde —
das ist erwartet.

---

## 8. Plattenplatz planen

Die 24/7-Aufnahme hört nie auf, dimensionieren Sie die Platte
also für den ganzen Tag × das Retention-Fenster:

| Bitrate | 1 Stunde | 1 Tag | 1 Woche |
|---|---|---|---|
| 128 kbps | ~58 MB | ~1,4 GB | ~9,5 GB |
| 192 kbps *(Default)* | ~86 MB | ~2,1 GB | ~14 GB |
| 320 kbps | ~145 MB | ~3,4 GB | ~24 GB |

Mit gesetztem **Delete after (days)** ist der Platzbedarf
begrenzt: etwa `1-Tag-Größe × Retention-Tage`. Die Cue-Sidecars
sind winzig (wenige KB pro Stunde).

---

## 9. Häufige Fragen

### „Warum ist die erste Datei kürzer als eine Stunde?"

Der Recorder startet, wenn Sie aktivieren + neu starten, meist
mitten in der Stunde — die erste Datei deckt also nur den Rest
dieser Stunde ab. Jede weitere Datei ist eine volle Uhr-Stunde.

### „Eine Stunde kam ein paar Minuten zu kurz — ein Fehler?"

Fast immer externe Last, nicht der Recorder: ein Antivirus-Scan
(siehe [§7](#7-antivirus-ausnahme-ist-pflicht)) oder eine
überlastete Maschine, sodass Liquidsoap beim Latency-Catchup
Audio verliert. Eine Abweichung von 1–3 Sekunden ist normale
MP3-Frame-Ausrichtung.

### „Kann ich 24/7 und pro Sendung gleichzeitig aufnehmen?"

Ja. Es sind unabhängige `output.file`-Abgriffe am selben Bus,
die in getrennte Ordner schreiben. Beide laufen ohne
zusätzliche Koordination zusammen.

### „Erfasst sie Live-DJ / Webstream / Line-In?"

Ja — sie greift den On-Air-Bus ab, also wird aufgenommen, was
die Hörer hören, unabhängig von der Quelle. (Cue-Marken für
eine Live-DJ-Harbor-Übernahme sind eine bekannte v1-Lücke — das
Audio wird trotzdem aufgenommen, der Live-Abschnitt bekommt nur
evtl. keine eigene Cue-Marke.)

### „Kann ich Format / Bitrate später ändern?"

Ja — in den Einstellungen ändern und den Playout-Dienst neu
starten. Vorhandene Dateien behalten ihr ursprüngliches Format;
neue Stunden nutzen die neue Einstellung.

---

## Weiterführend

* [Aufnahme pro Sendung](./RECORD_PER_SHOW.md) — der
  sendungsbezogene Begleit-Recorder.
* [Einstellungen → Lokale Maschine](./LOCAL_MACHINE.md) — wo Sie
  beide Recorder konfigurieren.
* [Streams](./STREAMS.md) — der On-Air-Output, den beide
  Recorder abgreifen.
* [`docs/operator/BACKUP.md`](../../operator/BACKUP.md) —
  Retention- / Off-Machine-Kopie-Politik.
