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
| **Stream-Name / URL / Genre / Beschreibung** | ICY-Metadaten, die an Hörer annonciert werden. Erscheinen in ihrem Player als Stationsname + Click-Through. |

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
`RASTATIME_DJ_RECONCILE_SECONDS`, Standard 120 Sekunden). Ein DJ,
der die Verbindung einfach schließt, wird erkannt, sobald der
Netzwerk-Timeout der Engine von 30 Sekunden abläuft; das Trennen
eines DJs über das Dashboard wirkt sofort.

> **Operator-Tipp.** Master DJ hat Vorrang vor Show DJ.
> Ein Stations-Ingenieur kann mitten in einer Sendung über
> die Master-Quelle einspringen, und der Show DJ wird
> stummgeschaltet (immer noch verbunden, nur nicht auf
> Sendung), bis der Master die Verbindung trennt.

### Verbindung als Live-Quelle

Hosts verwenden jede Audio-Broadcasting-Software (BUTT,
Mixxx, RadioDJ, SAM Broadcaster), konfiguriert mit:

| Feld | Wert |
|---|---|
| Server | Der öffentliche Hostname oder IP der Station |
| Port | 8001 (der Quell-Eingang-Port, *nicht* der Hörer-Port 8000) |
| Mount | `/show` für Show DJ, `/master` für Master DJ |
| Benutzername | Der konfigurierte per-show oder stationsweite Benutzername |
| Passwort | Das konfigurierte Passwort |
| Format | MP3 (Anpassung an das Format des Hauptstreams der Station ist bevorzugt) |

Sobald verbunden, erscheint das Audio innerhalb von
~1 Sekunde auf dem Output-Stream.

> **Wie es unter der Haube funktioniert.** Der Quell-
> Eingang-Port (8001) ist ein separater Icecast-
> `<authentication>`-Mount, der zur Validierung des
> Benutzernamens + Passworts gegen die per-show oder
> stationsweiten Anmeldedaten über `icecast-source-auth.php`
> ins PHP zurückruft. Auth-erfolgreiche Verbindungen
> werden vom Source-Switcher in der Playout-Engine
> aufgenommen. Siehe ARCHITECTURE §10.5.

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

ICY-Metadaten werden vom Playout für geplante Tracks
automatisch gesetzt (Tracktitel erscheint in Playern, die
ICY unterstützen). Live-Quell-Inhalt hat keine
ICY-Metadaten — setzen Sie sie über die ICY-Felder Ihrer
Broadcasting-Software.

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
