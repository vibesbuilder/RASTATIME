# Line-In

> **Wo Sie sich im Handbuch befinden.** Dieses Kapitel deckt
> den Bibliotheks-Item-Typ **Line-In** ab — benannte Live-
> Audio-Eingänge, die Sie auf Playlists und Sendungen ziehen
> können. Für die operator-maschinen-seitige Soundkarten-
> Konfiguration, die einen Line-In physisch verfügbar macht,
> siehe [Lokale Maschine](./LOCAL_MACHINE.md). Für die
> Notfall-Prozedur, wenn ein Line-In still oder verrauscht
> wird, siehe
> [`docs/operator/LINE_IN_BROKEN.md`](../../operator/LINE_IN_BROKEN.md).

Ein **Line-In** ist ein benannter Live-Audio-Eingang von
einem Soundkarten-Gerät auf der Operator-Maschine — ein
Mikrofon, ein Mixer-Ausgang, ein CD-Player, ein externes
Audio-Interface — den RASTATIME als Bibliotheks-Item
exponiert. Einmal konfiguriert, können Sie ihn auf genau die
gleiche Weise in Playlists und auf Sendungen ziehen, wie Sie
einen Track ziehen.

Line-Ins sind neu in RASTATIME (2026-05-12). Sie ersetzen
den einzelnen hartkodierten "Line In"-Slot, den das
ursprüngliche LibreTime hatte, und fügen benanntes,
persistentes, drag-and-drop-fähiges, bibliothek-gelistetes
Verhalten hinzu.

---

## 1. Konzeptüberblick

Ein Line-In hat zwei Ebenen:

| Ebene | Was es ist | Wo es lebt |
|---|---|---|
| **Physisches Gerät** | Der tatsächliche Soundkarten-Eingang — ein USB-Mikrofon, eine eingebaute Line-Buchse, ein XLR-Interface usw. Identifiziert durch seine OS-seitige Geräte-ID. | Das Soundkarten-Setup der Operator-Maschine; siehe [Lokale Maschine](./LOCAL_MACHINE.md). |
| **Benannter Line-In** | Eine Bibliothekszeile, die *referenziert* ein physisches Gerät per ID, plus einen Anzeigenamen und eine Konfiguration. | Tabelle `rastatime_linein`; sichtbar in der Bibliothek + auf der Line-In-Bibliothek-Seite. |

Ein einzelnes physisches Gerät kann zu jedem Zeitpunkt
**höchstens einen** Line-In rückendecken. Das erneute Binden
desselben Geräts an einen zweiten Line-In überschreibt den
ersten.

---

## 2. Die Line-In-Bibliothek-Seite

Einstellungen → **Line-In-Bibliothek** (oder klicken Sie auf
den grünen Line-In-Chip in der Haupt-Bibliotheks-Seite).

```
   ┌──────────────────────────────────────────────────────────────┐
   │  Line-Ins                                          + Neu     │
   ├──────────────────────────────────────────────────────────────┤
   │  Name             │ Gerät                  │ Standardlänge   │
   ├───────────────────┼────────────────────────┼─────────────────┤
   │  Studio-Mikro     │ USB-Mikro (Standard)   │  ∞              │
   │  Mixer-Out        │ Behringer X-AIR Ausgang│  01h 00m 00s    │
   │  CD-Player        │ Front-Mikro-Eingang    │  03m 00s        │
   │  Telefonleitung   │ Realtek HD Audio In #2 │  10m 00s        │
   └───────────────────┴────────────────────────┴─────────────────┘
```

Jede Zeile ist ein benannter Line-In. Die Tabellenspalten:

| Spalte | Bedeutung |
|---|---|
| **Name** | Der Anzeigename. Wird überall verwendet, wo der Line-In erscheint (Bibliotheksliste, Drag-Chip, Schedule-Item, Now-Playing-Widget). |
| **Gerät** | Das Soundkarten-Gerät, das der Line-In referenziert. Das Label ist der OS-seitige Name des Geräts. |
| **Standardlänge** | Die Standarddauer, die eine Line-In-Zeile belegt, wenn sie in eine Playlist oder Sendung gezogen wird. `∞` bedeutet "spielt bis gestoppt"; eine endliche Dauer bedeutet, dass die Zeile genau für diese Zeit eingeplant wird. |

Die Symbolleiste:

| Schaltfläche | Was sie tut |
|---|---|
| **+ Neu** | Den Neuer-Line-In-Dialog öffnen. |
| **Bearbeiten** (Zeilen-Kontextmenü) | Den Bearbeitungs-Dialog für diesen Line-In öffnen. |
| **Löschen** | Den Line-In entfernen. Schedule-Zeilen, die ihn referenzieren, werden ebenfalls entfernt. |

> **Wie es unter der Haube funktioniert.** Alle mutierenden
> Aktionen sind dünne Pass-Throughs von
> `application/controllers/LineinController.php` zur
> Django-REST-API unter `/api/v2/audio/linein[/<id>]`. Der
> Controller erzwingt nur ACL (Admin + Super Admin); die
> Python-Seite unter `backend/api/libretime_api/linein/`
> besitzt Validierung und Persistenz in
> `rastatime_linein`. Siehe ARCHITECTURE §14.

---

## 3. Einen Line-In erstellen

Line-In-Bibliothek → **+ Neu**.

```
   ┌──────────────────────────────────────────────────────────────┐
   │  Neuer Line-In                                               │
   ├──────────────────────────────────────────────────────────────┤
   │   Name:           [                       ]                  │
   │   Gerät:          [Gerät auswählen... ▾]                     │
   │   Channels:       [Stereo 1/2 ▾]                             │
   │   Standardlänge:  [10m 00s   ]   (00s für unendlich)         │
   │   Eingangsverstärkung (dB): [0.0 ]  -20,0 bis +20,0 dB       │
   ├──────────────────────────────────────────────────────────────┤
   │                                       [Abbrechen][Speichern] │
   └──────────────────────────────────────────────────────────────┘
```

| Feld | Hinweise |
|---|---|
| **Name** | Erforderlich. Eindeutig. Das sichtbare Label überall. |
| **Gerät** | Erforderlich. Dropdown listet jedes Eingabegerät, das das OS gerade sieht. Wenn Ihr Gerät im Dropdown fehlt, siehe [Lokale Maschine](./LOCAL_MACHINE.md) → Geräte-Probing. |
| **Standardlänge** | Erforderlich. Format `HHh MMm SSs` (derselbe Parser wie Webstreams). Für "spielt bis gestoppt" verwenden Sie `0h 0m 0s` (zeigt als `∞`). |
| **Eingangsverstärkung (dB)** | Optional, Standard `0` (unverändert). Hebt oder senkt den Pegel dieses Line-Ins auf Sendung, `-20,0` bis `+20,0` dB — siehe *Eingangsverstärkung* unten. |

> **Ein Editor seit dem 17.09.2026.** Dieser Dialog ist der
> vollständige Line-In-Editor: Er wählt auch die **Channels** (eine
> Option je Stereo-Paar des Geräts, danach jeder Mono-Kanal).
> Die frühere Sektion unter Settings → Local Machine gibt es
> nicht mehr.  Einen Aktiv-Schalter gibt es nicht (entfernt am
> 17.09.2026): Ein vorhandener Line-In darf verwendet werden;
> aus dem Verkehr zieht man ihn per Löschen.

### Mehrkanal-Interfaces: ein Line-In pro Studio

Hat das Audio-Interface der Station mehr als zwei Eingänge (z.B.
ein Tascam US-16x08 mit 16 Eingängen und mehreren angeschlossenen
Studios), legen Sie **einen Line-In pro Studio** an — gleiches
**Gerät**, unterschiedliche **Eingangskanäle** (Auswahl unter
dem Feld **Channels** direkt im Dialog):

- `Studio A` → Gerät `US-16x08`, Eingangskanäle `Stereo 1/2`
- `Studio B` → Gerät `US-16x08`, Eingangskanäle `Stereo 5/6`
- `Studio C Gastmikro` → Gerät `US-16x08`, Eingangskanäle `Mono 7`

Jeder Line-In verhält sich dann in Bibliothek und Sendungen wie
eine eigene Quelle; aufeinanderfolgende Sendungen aus verschiedenen
Studios am selben Interface wechseln sauber an der Sendungsgrenze.

> **Wie es unter der Haube funktioniert.** Jeder Line-In — seit
> 2026-09-03 auch schlichtes `Stereo 1/2` — läuft über einen
> kleinen Capture-Feeder. Der Feeder liest das Gerät über die
> MME-API (die eine Windows-API, die nachweislich alle Kanäle
> liefert, ohne Systemeinstellungen anzufassen), extrahiert die
> gewählten Kanäle und speist sie über den lokalen
> `/linein-capture`-Mount in die Stream-Engine. Bis 2026-09-03
> nahm schlichtes `Stereo 1/2` stattdessen einen direkten
> DirectShow-Pfad; dieser Pfad adressiert das Gerät über seine
> Windows-Audio-Endpoint-GUID, die DirectShow nicht kennt — an
> einem Mehrkanal-Interface öffnete er das Gerät daher nicht und
> der Slot blieb still. Jede andere Kanalauswahl konnte ihn
> ohnehin nie nutzen: der DirectShow-Pin eines Mehrkanal-
> Interfaces bietet grundsätzlich nur zwei Kanäle. Der Feeder
> braucht den Anzeigenamen des Geräts auf der Zeile, deshalb
> **müssen Line-Ins, die vor diesem Feature gespeichert wurden,
> einmal neu gespeichert werden** — ohne den Namen fallen sie auf
> den alten DirectShow-Pfad zurück und senden womöglich Stille.

Klicken Sie **Speichern**. Der Line-In erscheint sofort im
Line-In-Chip-Filter der Bibliotheks-Seite.

### Die Standardlänge ist wichtig

Die Standardlänge ist die Dauer, die eine Line-In-Zeile in
einer Sendung reserviert:

- Für ein **Mikrofon** in einem normalen Sprech-Studio
  setzen Sie die Standardlänge auf die typische
  Sprech-Segmentlänge (5 Min ist üblich).
- Für einen **Mixer-Ausgang**, der die gesamte Sendung
  treibt, setzen Sie die Standardlänge auf die volle
  Sendungslänge (z.B. 60 Min) oder unendlich.
- Für einen **CD-Player** oder eine andere zeitgesteuerte
  Quelle setzen Sie die Standardlänge auf die typische
  Tracklänge (3 Min).

Der Operator kann die Dauer pro Verwendung im Show-Builder
immer überschreiben; die Standardlänge ist nur der
Anfangswert.

### Eingangsverstärkung: den Studiopegel angleichen

Studios kommen selten mit demselben Pegel an: ein Mischpult
fährt heiß, ein Gastmikrofon auf einem Mono-Kanal ist leise.
Die **Eingangsverstärkung (dB)** gleicht einen Line-In an die
Lautheit des Senders an, ohne das Mischpult anzufassen — dasselbe
Feld, das Webstreams haben (siehe [Webstreams](./WEBSTREAMS.md)
→ Stream-Gain).

| Einstellung | Wirkung |
|---|---|
| `0.0` (Standard) | Keine Pegeländerung. |
| `+3.0` | Um 3 dB anheben. |
| `-6.0` | Um 6 dB absenken. |

Die Verstärkung wirkt, solange dieser Line-In auf Sendung ist —
jeder Stream, die 24/7-Aufnahme und der Main Output hören den
angepassten Pegel.  Jeder Line-In hat seinen eigenen Wert: Zwei
Line-Ins am selben Gerät (z.B. zwei Sendungen aus einem Studio)
können unterschiedliche Werte haben, umgeschaltet wird an der
Sendungsgrenze.  Eine Änderung gilt für jeden Slot, der nach dem
nächsten Einlesen des Sendeplans durch den Playout beginnt (alle
zwei Minuten); ein Line-In, der gerade auf Sendung ist, behält
seinen Pegel bis zum Ende seines Slots.

> **Operator-Tipp.** Gleichen Sie mit einem Lautheitsmesser am
> Ausgangsstream an: Planen Sie den Line-In als 10-Minuten-Test
> ein, sprechen und spielen Sie in normalem Sendepegel, passen
> Sie die Verstärkung an, wiederholen Sie.  Heben Sie mit
> Bedacht an: Mit der EBU-R128-Lautheitsnormalisierung fängt der
> Ausgangs-Limiter (und Stereo Tool, wenn aktiviert) die Spitzen
> ab, ohne sie kann eine große Anhebung am Ausgang clippen.  Eine
> Quelle, die schon am Mischpult clippt, bleibt geclippt — das
> beheben Sie am Mischpult.

> **Wie es unter der Haube funktioniert.** Die Migration
> `linein 0005` ergänzt `rastatime_linein.input_gain_db`.  Die
> Stream-Engine legt ein `amplify` um die Line-In-Quelle; der
> Playout setzt dessen Faktor (`var.set linein.gain`, aus dB
> umgerechnet) jedes Mal, wenn ein Line-In auf Sendung geht,
> nachdem ein DJ zurückgibt und nach einem Neustart der Engine.
> Beim ersten Mal nach dem Update braucht das einen Neustart von
> Playout und Stream-Engine (neuer Skript-Block).

---

## 4. Einen Line-In in einer Sendung verwenden

> **In der Audio-Vorschau der Sendung (seit 17.09.2026)** erscheint
> ein geplanter Line-In als gedimmte Zeile mit der Markierung *live
> input* — ein Hardware-Eingang hat keine Quelle, die der Browser
> abspielen könnte; die Zeile steht der Vollständigkeit halber da,
> und die Vorschau fährt einfach mit dem nächsten abspielbaren
> Titel fort.

Zwei Pfade:

### 4.1 Direkter Drag auf eine Sendung

Show-Builder → ziehen Sie die Line-In-Zeile aus dem
Bibliotheks-Panel auf die Sendung. Ein Schedule-Item
erscheint mit dem Namen des Line-Ins und der Standardlänge
des Line-Ins.

Klicken Sie auf das Item → **Bearbeiten** → setzen Sie die
Überschreibungs-Dauer für diese spezifische Verwendung oder
ändern Sie die Cue-In-Verzögerung.

### 4.2 Innerhalb einer Playlist

Playlist-Editor → ziehen Sie den Line-In aus der
Bibliothek. Die Playlist-Zeile trägt die Referenz des
Line-Ins + dessen Standardlänge und verhält sich wie jedes
andere Playlist-Item.

Wenn die Playlist später in einer Sendung eingeplant wird
(via Drag-and-Drop oder via Autoloading Playlist), wird
der Line-In zu einem Schedule-Item genau wie in Pfad 4.1.

> **Wie es unter der Haube funktioniert.** Migration 0054
> (2026-05-19) fügte `cc_playlistcontents.linein_id` als
> nullable Foreign Key in `rastatime_linein` hinzu, plus
> eine CHECK-Beschränkung, dass genau eines von `file_id`
> / `stream_id` / `block_id` / `linein_id` pro Zeile
> non-NULL ist. Typ 3 in `cc_playlistcontents.type`
> kennzeichnet eine Line-In-Zeile. ARCHITECTURE §23.18
> behandelt die Schema-Entscheidung.

### Was spielt, wenn der Slot des Line-Ins beginnt?

**Liquidsoap-Engine-Pfad (Produktions-Default seit 2026-05-29):**

1. Pypo startet den FfmpegLineinCapture-Subprozess für das
   konfigurierte Soundkarten-Gerät (MME-Capture-Feeder → MP3 → lokaler
   Icecast-Mount unter `http://localhost:8000/linein-capture`).
2. Pypo sendet einen einzelnen Telnet-Befehl an Liquidsoap:
   `linein.start` — der dediziertes `input.http`-Source beginnt
   den lokalen Capture-Mount zu konsumieren.
3. Liquidsoap buffert nur wenig Audio (1,0 s seit 2026-09-04).
   Sobald `source.is_ready` auf true schaltet, routet der
   Bus-Switch das Audio zur Linein-Source — Hörer hören das
   Mikrofon. Die `input.http`-Begleitquelle wird *parallel* zum
   Capture-Start scharfgeschaltet, ihr Buffer füllt sich also
   während der Capture warmläuft statt erst danach.
4. Bei der konfigurierten Dauer sendet Pypo `linein.stop` und
   stoppt zusätzlich FfmpegLineinCapture; der Switch fällt
   zurück auf scheduled.  Seit 2026-09-04 ist die Übergabe ein
   **Mix, kein Schnitt**: Der Line-In wird über ein *Gate* im
   Liquidsoap-Bus von der Sendung genommen, der Bus blendet ihn über
   die Standard Show-Crossfade-Dauer (Settings → General; der
   Nachfolger startet sofort in voller Lautstärke und der Line-In
   blendet darunter über so viele Sekunden aus, 0 = harter Wechsel —
   seit 2026-09-27 die einzige Form) unter dem Nachfolger aus, und
   erst danach werden Capture und Quelle gestoppt — die letzten
   Worte des Moderators, die noch in der Kette stecken, sind so
   hörbar statt verloren.  Was danach kommt — Jingle, Webstream —
   gibt den Line-In beim eigenen Start auf dieselbe Weise frei; das
   Mikrofon kann also nie über seinen Slot hinaus auf Sendung
   bleiben.  Einzige Ausnahme ist ein **echtes Back-to-Back** auf
   demselben Gerät (nächster Line-In startet innerhalb von ~2 s):
   der übernimmt den laufenden Capture ohne Unterbrechung.

**Aufnahme-Verhalten (neu seit Phase F, 2026-05-29):**
Scheduled Line-Inputs fließen jetzt durch den Liquidsoap-internen
Bus, an den `output.file` angeschlossen ist, und landen im
Per-Show-`.mp3`-Aufnahme-Archiv — gleiche Abdeckung wie Tracks
und Webstreams. Vor Phase F hatten reine Line-Input-Shows stille
Aufnahmen.

**Warum FfmpegLineinCapture statt Liquidsoaps `input.portaudio`:**
input.portaudio hat keine `set_device`-Methode zur Laufzeit, keinen
Auto-Reconnect bei USB-Cable-Unplug und nutzt PortAudio-Integer-
Indizes statt der Windows-Audio-Endpoint-GUIDs, die die Frontend-
Bibliothek führt. FfmpegLineinCaptures Watchdog behandelt
Unplug-Replug transparent; Liquidsoap konsumiert den lokalen
Icecast-Mount ohne sich um Device-Identität zu kümmern.

**Latenz — Slot-Anfang und Slot-Ende:** Der Line-In-Pfad hat eine
Durchlauf-Latenz: Was zur Studiozeit *t* gesprochen wird, erreicht
den Stream bei *t + L*. Zwei Folgen: Der Slot-Anfang ist etwa L
lang still, während sich die Kette füllt, und am Slot-Ende stecken
die letzten L Sekunden noch in der Kette, wenn die Quelle
geschlossen wird — **sie erreichen den Stream nie**. Auf Sendung
gemessen am 2026-09-04 (Sekunden ins Mikrofon gezählt): L war
~6 s. Fünf davon waren FFmpegs *Format-Autodetection* am
Capture-Mount — ein Hörer steigt mitten in den Icecast-Datenstrom
ein, ohne Header in Sicht, und der Decoder scannt ~5 s, bevor er
einrastet. Seit 2026-09-04 ist das Format fest vorgegeben
(`format="mp3"`, die Capture muxt immer MP3), der `input.http`-
Buffer beträgt 1,0 s (einstellbar über
`RASTATIME_LIQUIDSOAP_LINEIN_HTTP_MAX_BUFFER_SECONDS`), und der
Start-Health-Check der Capture 0,75 s. Danach gemessen: Startlücke
2 s, Verlust am Slot-Ende 2 s.

Beide verbleibenden Sekunden werden seit 2026-09-04 (abends)
angegangen: **Vorwärmen** — 10 s vor einem Line-In-Slot startet das
Playout bereits den Capture und verbindet die Liquidsoap-Quelle bei
geschlossenem Bus-Gate, sodass beim Slot-Start nur noch das Gate
öffnet und der Line-In innerhalb eines Frames auf Sendung ist; und
der **Gate-Off-Mix** am Slot-Ende (siehe Schritt 4 oben), der den
gepufferten Rest unter dem Nachfolger abspielt, statt ihn zu
verwerfen. Vorgewärmt wird nicht, wenn ein anderer Line-In auf
Sendung ist (ein Capture zur Zeit) oder die Zeile keinen
gespeicherten Gerätenamen hat; solche Slots starten auf dem
normalen Weg (~2 s).

Wenn die Slot-Dauer abgelaufen ist, sendet die Engine ein
`LINEIN_END`-Event, und der Source-Switcher kehrt zum
Sendeplan zurück.

> **Operator-Tipp.** Wenn ein Line-In für "unendliche"
> Dauer in einem Slot konfiguriert ist, spielt die
> Playout-Engine ihn bis zum *Ende der Sendung* — nicht
> buchstäblich für immer. Der Slot endet mit der Sendung.

---

## 5. Einen Line-In bearbeiten oder entfernen

### Bearbeiten

Line-In-Bibliothek → Zeile klicken → **Bearbeiten**. Ändern
Sie Name, Gerät, Kanäle, Standardlänge oder
Eingangsverstärkung.
Klicken Sie **Speichern**.

Effekte:

- **Namensänderung** propagiert zur Bibliotheksliste und zum
  Now-Playing-Widget bei der nächsten Aktualisierung.
  Bestehende Schedule-Items behalten den alten Namen bis
  zum nächsten Build-Zyklus.
- **Geräteänderung** propagiert auf *jede* zukünftige
  Verwendung, einschließlich Schedule-Items, die bereits in
  kommenden Sendungen sind.
- **Standardlängen-Änderung** beeinflusst nur *neue*
  Verwendungen; bestehende Schedule-Items behalten ihre
  konfigurierte Dauer.
- **Änderung der Eingangsverstärkung** gilt für jeden Slot, der
  nach dem nächsten Einlesen des Sendeplans durch den Playout
  beginnt (höchstens zwei Minuten), einschließlich
  Schedule-Items, die bereits in kommenden Sendungen sind; ein
  Line-In auf Sendung behält seinen Pegel bis zum Slot-Ende.

### Löschen

Zeilen-Kontextmenü → **Löschen**. Bestätigen. Der Line-In
wird entfernt *und* jede `cc_playlistcontents`- und
`cc_schedule`-Zeile, die ihn referenziert, wird entfernt
(CASCADE).

> **Operator-Tipp.** Löschen kaskadiert in Sendungen, die Sie
> möglicherweise nicht bemerkt haben — prüfen Sie den Kalender,
> bevor Sie einen genutzten Line-In löschen.

---

## 6. Die Abhängigkeit vom physischen Gerät

Ein Line-In referenziert ein Soundkarten-Gerät per
**OS-seitiger ID**. Diese ID ist über Reboots hinweg
stabil, solange:

- Das Gerät eingesteckt bleibt.
- Keine andere Audio-Software installiert wurde, die
  Geräte-IDs neu zuweist (selten unter Windows, gelegentlich
  unter Linux).

Wenn das Gerät fehlt (ausgesteckt, Treiber-Absturz,
Operator-Maschine mit ausgeschaltetem Gerät neu gestartet):

- Der Line-In ist noch in der Bibliothek.
- Die Zeile des Line-Ins in der Seite Einstellungen →
  Line-In-Bibliothek zeigt einen **roten Ausrufezeichen**-
  Badge neben der Geräte-Spalte.
- Jeder Sendeplan, der versucht, den Line-In zu spielen,
  überspringt ihn mit einer "Device not found"-Warnung im
  Playout-Log.
- Der Fallback (Stille oder Fallback-Schleife) spielt für
  die Dauer des Slots.

Siehe
[`docs/operator/DEVICE_MISSING.md`](../../operator/DEVICE_MISSING.md)
für das Wiederherstellungs-Runbook.

> **Wie es unter der Haube funktioniert.** Die Playout-
> Engine prüft die Geräte-Verfügbarkeit via
> `audio.soundcard.windows_manager` vor dem Öffnen des
> Eingangs. Die Geräteliste kommt von einer Live-
> WASAPI / portaudio-Enumeration unter Windows. Der
> "rote Ausrufezeichen"-UI-Hinweis wird vom Endpunkt
> `/api/v2/audio/devices` gesteuert, der die persistierte
> ID gegen die aktuelle Enumeration vergleicht.

---

## 7. Berechtigungen

Nur **Program Manager (P)**, **Admins (A)** und der **Super
Admin (S)** können Line-Ins erstellen, bearbeiten oder
löschen (seit 25.10.2026; vorher nur Admins). Gründe:

- Ein Line-In referenziert ein physisches Gerät auf der
  Operator-Maschine. Änderungen können den Sendeplan jedes
  DJs brechen.
- Soundkarten-Konfiguration ist stationsweit.

DJs (H) und Gäste (G) sehen Line-Ins gar nicht: DJs arbeiten
nur mit Tracks, deshalb sind der Reiter Line Inputs und der
Eintrag **Neu → Line Input** ausgeblendet, und das Einfügen
eines Line-Ins in eine Playlist oder Sendung wird für sie
abgelehnt.  Ein Program Manager setzt den Line-In in die
Sendung.

> **Wie es unter der Haube funktioniert.** ACL erzwungen in
> `application/configs/ACL.php`, Ressource
> `linein-controller`.

---

## 8. Häufig gestellte Fragen

### "Wo ist die ursprüngliche 'Show Source' / 'Master Source' / 'Line In'-Einstellung?"

Das ursprüngliche LibreTime hatte drei hartkodierte
Eingänge ("Show Source", "Master Source", "Line In"),
konfiguriert unter **Einstellungen → Live-Quellen**.
RASTATIME behält Show Source und Master Source (das sind
Remote-DJ-Eingänge über Icecast — siehe
[Streams](./STREAMS.md) → §3 Quellen), ersetzt aber den
einzelnen hartkodierten "Line In" mit dem
benannten-Line-In-Feature, das hier dokumentiert ist.

Wenn Sie Legacy-Daten aus einer LibreTime / Airtime-
Installation haben, wird der alte "Line In"-Toggle während
der Migration verworfen. Die ursprüngliche "Record from
Line In?"-Checkbox wird umgewidmet (siehe
[Aufnahme pro Sendung](./RECORD_PER_SHOW.md)).

### "Können zwei Line-Ins dasselbe physische Gerät referenzieren?"

Ja, aber nur einer wird zu jedem Moment erfolgreich sein.
Die meisten Soundkarten-Treiber gewähren dem ersten
Öffner exklusiven Zugriff; ein zweiter Line-In, der
versucht, dasselbe Gerät zur selben Zeit zu öffnen,
scheitert mit "device busy". Nur nützlich für "dasselbe
physische Gerät unter zwei verschiedenen Namen"-Fälle —
typischerweise selten.

### "Warum erscheint mein Mikrofon als 'Microphone (USB Audio CODEC)'?"

Das ist der OS-seitige Gerätename. Windows weist den
Namen basierend auf der vom Treiber gemeldeten
Produkt-ID zu. Der Anzeigename in RASTATIME ist der
**Name des Line-Ins** (Sie setzen dies im Neuer-Line-In-
Dialog), nicht der OS-seitige Gerätename — nennen Sie ihn
also "Studio-Mikro" oder "Annas Mikro" und ignorieren
Sie das OS-Label.

### "Kann ein Line-In der einzige Inhalt der Autoloading Playlist sein?"

Ja. Erstellen Sie eine Playlist, die genau eine
Line-In-Zeile mit Standardlänge = der Sendungslänge (oder
unendlich) enthält. Hängen Sie diese Playlist als
Autoloading Playlist der Sendung an. Jede Instanz der
Sendung wird ausschließlich vom Line-In spielen.

### "Wird das Audio des Line-Ins aufgezeichnet, wenn Record-per-Show aktiviert ist?"

Ja (seit Phase F, 2026-05-29). Im Liquidsoap-Engine-Modus
fließt das Line-In-Audio durch denselben internen Audio-Bus,
an den `output.file` für das Per-Show-MP3-Archiv angeschlossen
ist, und wird nativ erfasst — zusammen mit eventuellen
regulären Tracks oder geplanten Webstreams derselben Sendung.
Siehe [Aufnahme pro Sendung](./RECORD_PER_SHOW.md).

### "Kann ich eine Netzwerk-Audio-Quelle (z.B. AES67 / Dante) als Line-In hinzufügen?"

Nur wenn die Quelle als Windows-Soundkarten-Eingabegerät
präsentiert wird — viele AES67- / Dante-Treiber liefern
eine virtuelle Soundkarte mit. Wenn sie im
Eingabegeräte-Dropdown der Einstellungen → Lokale Maschine
erscheint, funktioniert sie als Line-In.

---

## Wohin als Nächstes

* [Lokale Maschine](./LOCAL_MACHINE.md) — physische
  Soundkarten-Konfiguration auf der Operator-Maschine.
* [Bibliothek](./LIBRARY.md) — Line-Ins erscheinen auch in
  der Haupt-Bibliothek; der Chip-Filter zeigt sie.
* [Dashboard](./DASHBOARD.md) → Quellenstatus — sehen Sie,
  welcher Line-In gerade auf Sendung ist.
* [`docs/operator/LINE_IN_BROKEN.md`](../../operator/LINE_IN_BROKEN.md)
  — Notfall-Prozedur, wenn ein Line-In still oder
  verrauscht wird.
* [`docs/operator/DEVICE_MISSING.md`](../../operator/DEVICE_MISSING.md)
  — wenn das zugrunde liegende Soundkarten-Gerät
  verschwindet.
