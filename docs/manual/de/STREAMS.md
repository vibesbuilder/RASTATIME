# Streams

> **Wo Sie sich im Handbuch befinden.** Dieses Kapitel
> behandelt **ausgehende Streams** — was RASTATIME für
> Hörer publiziert. Für **eingehende** (Streams anderer
> Leute, die RASTATIME in eine Sendung relayt), siehe
> [Webstreams](./WEBSTREAMS.md). Für den
> operator-maschinen-seitigen Soundkarten-Ausgang, siehe
> [Lokale Maschine](./LOCAL_MACHINE.md).

Ein **Stream** ist ein Icecast- (oder Shoutcast-)
Mountpoint, an den RASTATIME an Hörer sendet. Eine Station
kann bis zu **vier Output-Streams** konfigurieren,
typischerweise verwendet für:

- **Hauptqualität** (192-320 kbps) für Desktop- /
  feste Hörer.
- **Mobile-Qualität** (96-128 kbps) für Mobilfunk-Hörer mit
  begrenzten Daten.
- **Verlustfrei / Archiv** (FLAC) für High-End-Hören oder
  Beitrag zu einem Syndizierer.
- **Reserve / Standby** für Failover oder Tests.

Jeder Stream hat seine eigene Bitrate, Codec, Mountpoint
und kann sogar auf einen anderen Icecast-Server zeigen
(z.B. ein lokales Icecast für den Hauptstream und ein
Cloud-Relay für den Mobile-Stream).

---

## 1. Die Streams-Einstellungsseite

Einstellungen → **Streams**.

```
   ┌─────────────────────────────────────────────────────────────────┐
   │  Stream-Einstellungen                       [Änderungen speichern]│
   ├─────────────────────────────────────────────────────────────────┤
   │  Stream 1   ☑  Aktiviert            Status: ● Verbunden          │
   │    Typ:         [Icecast ▾]                                     │
   │    Server:      [localhost            ]   Port:  [8000  ]        │
   │    Mount:       [/rastatime            ]                         │
   │    Source-User: [source                ]                         │
   │    Passwort:    [********              ]                         │
   │    Format:      [MP3 ▾]   Bitrate: [192 kbps ▾]                 │
   │    Kanäle:      [Stereo ▾]                                      │
   │    Samplerate:  [44,1 kHz ▾]                                    │
   │    Stream-Name: [Mein Radiosender                    ]           │
   │    Stream-URL:  [https://meine-station.example.com   ]           │
   │    Genre:       [Verschiedenes                       ]           │
   │    Beschreibung:[Mein Community-Radiosender          ]           │
   │                                                                 │
   │  Stream 2   ☐  Aktiviert                                        │
   │  Stream 3   ☐  Aktiviert                                        │
   │  Stream 4   ☐  Aktiviert                                        │
   └─────────────────────────────────────────────────────────────────┘
```

Jede der vier Stream-Karten hat dasselbe Feldset; nur
**Stream 1** ist standardmäßig aktiviert (der Install-
Standard).

### Pro-Stream-Felder

| Feld | Hinweise |
|---|---|
| **Aktiviert** | Hauptschalter für diesen Stream. Wenn aus, verbindet sich das Playout nicht. |
| **Typ** | **Icecast** (empfohlen; modern, kostenlos, weit unterstützt), **Shoutcast** (Legacy; pre-2010-Hörer), **Custom** (rohes HTTP-MP3-Push an ein Nicht-Standard-Ziel). |
| **Server / Port** | Wo der Icecast-Server ist. `localhost:8000` für die Standardinstallation. Verwenden Sie eine Remote-IP / einen Hostnamen, wenn Sie an ein Cloud-Icecast streamen. |
| **Mount** | Der Mountpoint-URL-Pfad, mit führendem `/`. z.B. `/rastatime` wird zu `http://<server>:<port>/rastatime`. Muss pro Icecast-Server eindeutig sein. |
| **Source-User / Passwort** | Anmeldedaten, die Icecast von einem Quell-Client erwartet. Gesetzt in der Icecast-Konfigurationsdatei (`config/icecast.xml`); die Standardinstallation verwendet `source` / `hackme`. Ändern Sie beides für die Produktion. |
| **Format** | **MP3** (universelle Kompatibilität), **AAC** (bessere Qualität bei niedrigen Bitraten), **OGG Vorbis** (kostenlos, weniger allgegenwärtig), **OPUS** (modern, sehr effizient), **FLAC** (verlustfrei, sehr groß). |
| **Bitrate** | Kbps. Die Wahl des richtigen Werts ist die folgenreichste Pro-Stream-Entscheidung; siehe §2. |
| **Kanäle** | **Stereo** (Standard), **Mono** (spart ~30 % Bandbreite für reines Sprechen). |
| **Samplerate** | 22,05 / 32 / 44,1 / 48 kHz. 44,1 kHz ist der universelle Standard. |
| **Stream-Name / URL / Genre / Beschreibung** | ICY-Metadaten, die an Hörer annonciert werden. Erscheinen in ihrem Player als Stationsname + Click-Through. Seit 2026-09-13 werden alle vier gerendert; leerer Name oder leere Beschreibung fallen auf den Sendernamen zurück (Icecast zeigte vorher „Unspecified name"). |

### Stream Label und Off Air Metadata

Was Hörer als „Now playing"-Titel in ihrem Player sehen.  Beide Felder
stehen auf der Streams-Seite über den Pro-Stream-Blöcken; der Sendername
kommt aus Einstellungen → General.

| Quelle auf Sendung | Artist - Title | Show - Artist - Title | Station name - Show name |
|---|---|---|---|
| Geplanter Titel | Interpret - Titel | Show - Interpret - Titel | RASTATIME - Show |
| Webstream mit eigenen Titeln | Titel des Quellstreams | Show - Titel des Quellstreams | RASTATIME - Show |
| Webstream ohne Titel, Line-In | RASTATIME - Show | RASTATIME - Show | RASTATIME - Show |
| DJ (BUTT / Mixxx) | Titel der DJ-Software, sonst RASTATIME - Show | Show - Titel der DJ-Software, sonst RASTATIME - Show | RASTATIME - Show |
| Nichts geplant | Off-Air-Text | Off-Air-Text | Off-Air-Text |

- **Off Air Metadata** ersetzt den letzten Titel, sobald nichts auf
  Sendung ist (vor dem 2026-09-13 blieb der alte Titel stundenlang stehen).
- Änderungen an beiden Feldern wirken innerhalb eines Sendeplan-Refreshs
  (etwa zwei Minuten), ohne Neustart.
- Das Label wird in die Titel-Metadaten des Streams geschrieben und gilt
  damit für MP3/AAC (ICY), für OGG (in-band) und für die Aufnahmen.

### Lautheitsnormalisierung (ReplayGain / EBU R128)

Gleicht den Pegel geplanter Titel an, damit eine leise Folk-Aufnahme
und ein lauter Club-Mix die Hörer mit derselben Lautheit erreichen.
Drei Modi, wählbar auf der Streams-Seite; jede Beschreibung steht als
Hilfesymbol neben ihrem Feld bereit.

| Modus | Was er tut |
|---|---|
| **Aus** | Jeder Titel spielt mit seinem eigenen Pegel. |
| **ReplayGain** | Der beim Import gemessene ReplayGain-Wert plus der Schieberegler *Replay Gain Modifier* (das Verhalten früherer Versionen). |
| **EBU R128** | Jeder Titel wird nach dem Rundfunk-Lautheitsstandard (ITU BS.1770 / EBU R128) gemessen und mit der **Ziel-Lautheit** gespielt; ein Peak-Limiter auf dem Ausgangsbus hält die **True-Peak-Grenze** ein. |

Einstellungen für EBU R128:

- **Ziel-Lautheit (LUFS)** — die integrierte Lautheit, mit der jeder
  Titel gespielt wird.  EBU R128 sieht −23 LUFS für Rundfunk vor;
  Webstreams verwenden häufig lautere Ziele zwischen −18 und −16 LUFS.
  Der Wert ist frei wählbar; −23 ist die Vorgabe.
- **True-Peak-Grenze (dBTP)** — der Pegel, den kein Spitzenwert
  überschreiten darf (Vorgabe −1 dBTP).  Ein leiser Titel wird nur so
  weit angehoben, wie sein gemessener True Peak es zulässt; den Rest
  fängt der Limiter auf dem Bus ab.
- **Lautheitsmessung** — ab jetzt importierte Dateien werden
  automatisch gemessen.  *Fehlende Dateien jetzt messen* reiht jede
  Datei ohne Messung beim Analyzer ein; *Alle neu messen* die gesamte
  Bibliothek.  Die Messung läuft im Hintergrund, wenige Sekunden je
  Datei; die Zeile „Gemessen: N von M Dateien" zeigt den Stand nach dem
  Neuladen der Seite.  Bis ein Titel gemessen ist, spielt er mit seinem
  auf das Ziel verschobenen ReplayGain-Wert.

Hinweise:

- Eine Änderung von Modus, Ziel oder Grenze wirkt beim nächsten
  Schedule-Refresh (etwa zwei Minuten) auf die Titel-Verstärkung; den
  Bus-Limiter übernimmt der geplante Neustart des Playouts an der
  nächsten Titelgrenze.
- Live-Quellen (DJ, Webstream, Line-In) sind von dieser Stufe nicht
  betroffen; ihr Pegel ist der, den die Quelle liefert.
- Die Messwerte werden je Datei gespeichert (integrierte Lautheit, True
  Peak, Loudness Range) und bleiben bei Änderungen der Einstellungen
  erhalten.

### Ausgangs-Processing (Stereo Tool)

Optional, standardmäßig aus.  Wenn aktiviert, führt der Playout den
gesamten Ausgang - jeden Icecast-Stream, die 24/7-Aufnahme und den Main
Output - über Liquidsoaps `stereotool()`-Operator durch
[Stereo Tool](https://www.thimeo.com/stereo-tool/): einen
Sendeprozessor mit BS.1770-Lautheitsregler, Multiband-Processing und
Final-Limiter.  Diese Stufe macht den Stream, den ein Distributionspartner
misst, unabhängig von seiner Quelle R128-konform; die
Lautheitsnormalisierung oben gleicht nur die Dateien aus.

| Feld | Bedeutung |
|---|---|
| **Ausgangs-Processing (Stereo Tool)** | Der Schalter.  Standardmäßig aus; eine Station ohne Stereo Tool lässt ihn einfach aus. |
| **Stereo-Tool-Bibliothek (DLL)** | Vollständiger Pfad der 64-Bit-Stereo-Tool-Bibliothek für Liquidsoap auf dem Studio-Rechner (von der Stereo-Tool-Downloadseite).  Die Seite zeigt, ob die Datei existiert; die Einstellung wird nur dann verwendet. |
| **Stereo-Tool-Preset (.sts)** | Optional.  Ein aus der Stereo-Tool-Anwendung exportiertes Preset; ohne Preset startet die Bibliothek mit ihren Vorgaben. |
| **Stereo-Tool-Lizenzschlüssel** | Der Schlüssel aus Ihrem Stereo-Tool-Konto.  Wird auf dem Server gespeichert und nie wieder angezeigt; leer lassen, um den gespeicherten Schlüssel zu behalten, `CLEAR` eingeben, um ihn zu entfernen.  Ohne Lizenz läuft die Bibliothek mit den Einschränkungen der freien Version. |

Hinweise:

- Eine Änderung wird beim geplanten Liquidsoap-Neustart des Playouts
  übernommen (ruhiger Moment oder nächste Titelgrenze), wie jede andere
  Einstellung, die in das Liquidsoap-Skript eingebaut ist.
- Sicherheitsnetz: Eine fehlende Bibliotheksdatei lässt den Ausgang
  unverändert, und bleibt die frische Liquidsoap-Instanz nach einem Start
  mit Stereo Tool nicht oben (inkompatible Bibliothek, abgelehnte Lizenz),
  startet der Playout sie **ohne** Stereo Tool neu, lässt es bis zum
  nächsten PLAYOUT-Neustart aus und meldet die Preflight-Warnung
  `stereotool_unavailable`.  Der Sendebetrieb hängt nie vom Plugin ab.
- Stereo Tool fügt allem Nachfolgenden Verarbeitungslatenz hinzu; der
  Kalender ist davon nicht betroffen, jeder Ausgang verschiebt sich um
  denselben Betrag.

### Stream-Status-Badge

Der Badge rechts neben dem Namen jedes aktivierten Streams:

| Badge | Bedeutung |
|---|---|
| ● **Verbunden** (grün) | Playout verbunden; sendet. Hörer können einschalten. |
| ◐ **Verbindet** (gelb) | Mitten im Verbindungsversuch. Sollte innerhalb weniger Sekunden übergehen. |
| ● **Getrennt** (rot) | Playout kann sich nicht verbinden. Häufige Ursachen: Icecast läuft nicht, falsche Anmeldedaten, Port blockiert. |
| ◯ **Deaktiviert** (grau) | Stream ist konfiguriert, aber der Hauptschalter ist aus. |

Der Badge aktualisiert sich alle 5 Sekunden über den
Endpunkt `/api/v2/streams`.

> **Operator-Tipp.** Ein roter Badge auf Stream 1
> bedeutet, dass Hörer nichts hören. Prüfen Sie Icecast
> (`Get-Service icecast2`), verifizieren Sie
> Anmeldedaten, bestätigen Sie, dass Port 8000 erreichbar
> ist. Siehe
> [`docs/operator/CRASH_RECOVERY.md`](../../operator/CRASH_RECOVERY.md).

---

## 2. Eine Bitrate wählen

Die am häufigsten konsultierte Einstellung. Leitfaden:

| Anwendungsfall | Format | Bitrate | Kanäle | Samplerate |
|---|---|---|---|---|
| Musik, Hauptqualität | MP3 | 192 kbps | Stereo | 44,1 kHz |
| Musik, Premium / FLAC-Fans | MP3 | 320 kbps | Stereo | 44,1 kHz |
| Musik, FLAC-Archiv | FLAC | (variabel, ~700-1000 kbps) | Stereo | 44,1 kHz |
| Talkshow / Sprechen | MP3 | 96 kbps | Mono | 44,1 kHz |
| Mobil / Mobilfunk | AAC | 64 kbps | Stereo | 44,1 kHz |
| Reserve / Debug | MP3 | 128 kbps | Stereo | 44,1 kHz |

### Warum diese und nicht andere

- **AAC ist besser als MP3 bei niedrigen Bitraten**
  (< 128 kbps). Bei 64 kbps Stereo produziert AAC deutlich
  bessere Qualität als MP3.
- **MP3 über 192 kbps Stereo** ist der Sweet Spot für
  Allgegenwärtigkeit + Qualität. Alles mehr ist auf den
  meisten Wiedergabesetups schwer zu unterscheiden.
- **OPUS ist der technisch beste moderne Codec**, aber
  einige Legacy-Hardware-Player unterstützen ihn nicht.
  Verwenden Sie OPUS nur, wenn Sie Ihre Hörerbasis
  kontrollieren.
- **OGG Vorbis** ist in Ordnung, bietet aber wenig
  Vorteile gegenüber MP3 für die meisten Hörer und
  schlechtere Kompatibilität.
- **FLAC** ist riesig und nur den Betrieb für Archive
  oder Beiträge an andere Sender wert.

### Bandbreitenmathematik

Jeder aktivierte Stream verbraucht Bandbreite gleich
`Bitrate × max_gleichzeitige_Hörer`. Ein 192-kbps-Stream
mit 50 gleichzeitigen Hörern verbraucht ~9,6 Mbps
ausgehend.

Wenn Ihr Operator-Maschinen-Internet-Uplink 10 Mbps hat,
kann dieser 192-kbps-Stream nicht über ~50 Hörer
skalieren. Lösungen:

- Betreiben Sie einen **Mobil**-Stream bei 96 kbps für
  Kapazität (200 Hörer auf einem 10-Mbps-Link).
- Verwenden Sie ein **Cloud-Icecast-Relay**, das viel mehr
  Hörer verarbeitet, als Ihr Heim-Uplink kann.

---

## 3. Live-Quellen

Zusätzlich zum geplanten Inhalt akzeptiert RASTATIME zwei
**Live-Quellen**-Verbindungen pro Sendung:

| Quelle | Zweck |
|---|---|
| **Show DJ** | Per-Sendung-Login. Der primäre Host der Sendung verbindet sich von überall und übernimmt die Sendung live. Benutzername + Passwort auf dem Sendungs-Bearbeitungsformular (Abschnitt **Live-Stream-Eingabe**) gesetzt. |
| **Master DJ** | Stationsweiter Login. Ein Produzent / Ingenieur kann jederzeit übernehmen und überschreibt, was auf Sendung ist. Benutzername + Passwort unter Einstellungen → Stream-Einstellungen → **Master-Quelle** gesetzt. |

Wenn eine der beiden Live-Quellen sich verbindet, routet
der Source-Switcher ihr Audio an den Output-Mixer anstelle
des Inhalts des Schedulers. Wenn die Live-Quelle die
Verbindung trennt, kehrt der Source-Switcher zum Sendeplan
zurück.

Seit dem 2026-09-09 meldet die Engine jedes Verbinden und Trennen
selbst sofort an das Playout, die Umschaltung erfolgt also
unmittelbar; das Playout prüft nur noch über seine Kommando-
verbindung nach (Maschinen-Einstellung
`RASTATIME_DJ_RECONCILE_SECONDS`, Standard 600 Sekunden). Ein DJ,
der die Verbindung einfach schließt, wird innerhalb des Netzwerk-
Timeouts der Engine von 5 Sekunden erkannt (Maschinen-Einstellung
`RASTATIME_HARBOR_TIMEOUT_SECONDS`); ein DJ, dessen Verbindung länger
stockt, wird getrennt und muss neu verbinden, was BUTT von selbst tut.
Das Trennen eines DJs über das Dashboard wirkt sofort.

> **Operator-Tipp.** Master DJ hat Vorrang vor Show DJ.
> Ein Stations-Ingenieur kann mitten in einer Sendung über
> die Master-Quelle einspringen, und der Show DJ wird
> stummgeschaltet (immer noch verbunden, nur nicht auf
> Sendung), bis der Master die Verbindung trennt.

**Switch Transition Fade (s)** (Settings → Streams, seit 2026-09-28,
Startwert 1 s) prägt die Übergabe: Verbindet sich ein DJ, ist er sofort
auf Sendung und das Programm blendet über so viele Sekunden darunter
aus; trennt der DJ die Verbindung, blendet der DJ über dieselbe Zeit aus
und das Programm kommt sofort in voller Lautstärke zurück. 0 = harter
Wechsel. Die Audiokette übernimmt den Wert wenige Sekunden nach dem
Speichern (geplanter Neustart in einem ruhigen Moment oder an einer
Titelgrenze). Vor dem 2026-09-28 hatte das Feld keine Wirkung; beide
Richtungen waren ein 50-ms-Wechsel.

### Verbindung als Live-Quelle

Hosts verwenden jede Audio-Broadcasting-Software (BUTT,
Mixxx, RadioDJ, SAM Broadcaster), konfiguriert mit:

| Feld | Wert |
|---|---|
| Server | Der öffentliche Hostname oder IP der Station |
| Port | Der **Master Source Port** / **Show Source Port** aus Einstellungen → Streams (Standard 8001; 8000 ist der Hörer-Port) |
| Mount | Der **Master Source Mount** / **Show Source Mount** aus Einstellungen → Streams (Standard `main` und `show`) |
| Benutzername | Master DJ: der Benutzername unter Einstellungen → Streams → **Master-Quelle**. Show DJ: das RASTATIME-Login eines eingetragenen Moderators oder der Custom-Benutzername im Abschnitt **Live Stream Input** der Show |
| Passwort | Das zugehörige Passwort |
| Format | MP3 (Anpassung an das Format des Hauptstreams der Station ist bevorzugt) |

Sobald verbunden, erscheint das Audio innerhalb von
~1 Sekunde auf dem Output-Stream.

> **Wie es unter der Haube funktioniert.** Der Quell-Eingang-Port
> ist ein Liquidsoap-Harbor in der Playout-Engine. Jedes Login wird
> im Moment des Verbindens geprüft (seit 2026-09-10): Die Engine
> fragt das Playout, das Playout fragt die Web-Anwendung, und die
> wendet die obigen Einstellungen an. Für den Show DJ zählt die
> gerade laufende Show; ein Show DJ kann sich also nicht vor dem
> Showbeginn einwählen. Nur solange das Playout selbst nicht
> erreichbar ist, greift die Engine auf das statische Harbor-
> Passwort aus `libretime.conf` zurück. Siehe ARCHITECTURE §23.27
> (Addendum 2026-09-10).

---

## 4. Stream-Gesundheit überwachen

### Aus der Oberfläche

Einstellungen → Streams zeigt den Badge pro Stream. Die
Seite **Systemstatus** (Hilfe → Systemstatus) fasst
zusammen:

- Pro-Stream-Verbindungszustand.
- Aktuelle Hörerzahl pro Stream.
- Höchste Hörerzahl heute.
- Bytes heute gesendet.

### Aus der Icecast-Admin-Oberfläche

`http://<server>:8001/admin/` (Standardbenutzer `admin`,
Passwort in `config/icecast.xml` gesetzt).

Die Icecast-Admin zeigt eine Fülle von per-listener-Daten:

- IP, User-Agent, Verbindungsdauer jedes Hörers.
- Pro-Mount-Byte-Rate.
- Listener-Kick- / Source-Disconnect-Controls.

### Aus der API

`GET /api/v2/streams` gibt den vollen Zustand jedes
konfigurierten Streams als JSON zurück. Nützlich für
externes Monitoring (Prometheus, Nagios, Uptime Robot).

```json
{
  "streams": [
    {
      "id": 1,
      "enabled": true,
      "state": "connected",
      "server": "localhost",
      "port": 8000,
      "mount": "/rastatime",
      "listener_count": 23,
      "peak_today": 47
    },
    ...
  ]
}
```

> **Operator-Tipp.** Verkabeln Sie den
> `/api/v2/streams`-Endpunkt in Ihr bestehendes
> Monitoring. Ein roter Stream 1 bedeutet, dass Hörer
> nichts hören — das ist der #1-Alarm, den Sie wollen.

---

## 5. Stream-Auth (Hörer-seitig)

Standardmäßig sind alle Streams **öffentlich** — jeder
HTTP-Client kann einschalten.

Um das Zuhören auf authentifizierte Benutzer zu beschränken:

1. Konfigurieren Sie Listener-Auth in
   `config/icecast.xml`:
   ```xml
   <mount>
     <mount-name>/rastatime</mount-name>
     <authentication type="url">
       <option name="listener_add" value="http://<station>/icecast-auth.php"/>
     </authentication>
   </mount>
   ```
2. Starten Sie Icecast neu.
3. Das `icecast-auth.php`-Skript (mit RASTATIME geliefert)
   authentifiziert gegen `cc_subjs`.

Hörer werden dann nach ihrem RASTATIME-Benutzernamen +
Passwort gefragt, wenn sie einschalten.

> **Warum dies selten verwendet wird.** Die meisten
> Community- / kommerziellen Stationen wollen einen
> öffentlichen Stream. Listener-Auth macht Sinn für
> bezahlte Abonnenten-Stationen oder interne / nur für
> Mitarbeiter zugängliche Feeds. Die Standardinstallation
> liefert Listener-Auth aus; aktivieren Sie sie pro Mount
> nach Bedarf.

---

## 6. Mehrere Icecast-Server

Jeder der vier Streams kann auf einen **anderen
Icecast-Server** zielen. Dies ist das Standard-Setup für:

- **Lokal + Cloud**: Stream 1 zu lokalem Icecast (niedrige
  Latenz für das eigene Monitoring des Operators), Stream
  2 zu einem Cloud-Icecast (hohe Hörerkapazität).
- **Geografische Verteilung**: Stream 1 zu EU-Icecast,
  Stream 2 zu US-Icecast (jeder bedient die Hörer seiner
  Region).

Das Playout kodiert einmal (pro Stream) und pusht
unabhängig. Das Versagen eines Servers beeinträchtigt die
anderen nicht.

> **Wie es unter der Haube funktioniert.** Jeder Stream
> wird einer `libvlc_VLM`-Quelle mit ihrer eigenen
> `#transcode{}:standard{access=shout,...}`-Output-Kette
> zugeordnet. Die Streams laufen als unabhängige Threads
> innerhalb des RASTATIME-PLAYOUT-Dienstes. Siehe
> ARCHITECTURE §10.

---

## 7. Häufig gestellte Fragen

### "Wie viele gleichzeitige Hörer kann RASTATIME bewältigen?"

RASTATIME selbst kodiert nur einmal pro Stream. Die
Hörerkapazität hängt ab von:

- **Icecast** — bewältigt Tausende von gleichzeitigen
  Hörern pro Server auf bescheidener Hardware.
- **Netzwerk-Uplink** — Bitrate × Hörerzahl muss innerhalb
  der ausgehenden Kapazität der Operator-Maschine passen.

Für mehr als ~50-100 Hörer betreiben Sie Icecast auf einem
Cloud-Server mit einem dicken Uplink, nicht auf der
Heim-Internet-Verbindung des Operators.

### "Kann ich einen HLS- / DASH-Stream-Output haben?"

Nicht direkt — RASTATIME gibt Icecast- /
Shoutcast-HTTP-Streams aus. Um HLS zu bekommen, betreiben
Sie einen externen Repackager
(`ffmpeg -i icecast-url -hls_time 6 ...`), der vom
Icecast-Mountpoint liest.

### "Warum ist die Hörerzahl meines Streams immer 0?"

Drei Möglichkeiten:

1. Niemand hört zu (am häufigsten — verifizieren Sie über
   die Icecast-Admin).
2. Der Badge ist falsch (versuchen Sie, die Seite neu zu
   laden; der Badge aktualisiert sich alle 5 s, kann aber
   verzögert sein).
3. Hörer verbinden sich mit einem anderen Mountpoint als
   dem konfigurierten (verifizieren Sie, dass der
   Mountpfad übereinstimmt).

### "Ich habe die Bitrate geändert, aber Hörer sagen, es klingt gleich."

Die meiste Player-Software cached die Verbindung für die
Dauer der Hör-Session. Hörer müssen sich neu verbinden,
um die neue Bitrate aufzunehmen. Sagen Sie ihnen, sie
sollen die Stations-URL neu laden / aktualisieren.

### "Kann ich die Bitrate des Streams ändern, während er spielt?"

Ja. Speichern Sie die neue Bitrate; die Playout-Engine
verbindet den Stream mit den neuen Parametern neu. Hörer
sehen ~5 s Stille während der Neuverbindung.

### "Wie füge ich ICY-Metadaten (Now-Playing-Track-Titel) hinzu?"

Sie sind bereits da: das Playout beschriftet jedes Metadaten-Paket
nach **Stream Label** (siehe §1), zeigt den **Off Air Metadata**-Text,
solange nichts auf Sendung ist, und reicht die Titel eines Webstreams
oder der DJ-Broadcasting-Software durch dasselbe Label.  Eine Live-
Quelle ohne eigene Titel wird mit der laufenden Sendung beschriftet.

### "Warum spielt dieselbe Stream-URL anders auf verschiedenen Playern?"

Verschiedene Player-Software behandelt Buffer-Underrun,
Reconnect und Metadaten unterschiedlich. Testen Sie mit
VLC (einem Referenz-Player) für die Grundwahrheit.
iTunes, Winamp, browser-basierte Player haben jeweils ihre
eigenen Eigenheiten.

---

## Wohin als Nächstes

* [Lokale Maschine](./LOCAL_MACHINE.md) — der
  operator-maschinen-seitige Soundkarten-Ausgang (separat
  von Streams).
* [Dashboard](./DASHBOARD.md) — schnelle Stream-Gesundheit
  auf jeder Seite sichtbar.
* [Webstreams](./WEBSTREAMS.md) — das *eingehende*
  Gegenstück (Relaying von Streams anderer Leute in Ihre
  Sendungen).
* [`docs/operator/CRASH_RECOVERY.md`](../../operator/CRASH_RECOVERY.md)
  — wenn ein Stream rot wird.
