# Webstreams

> **Wo Sie sich im Handbuch befinden.** Webstreams sind ein
> Bibliotheks-Item-Typ neben Tracks, Smart Blocks, Playlists
> und Line-Ins. Siehe [Bibliothek](./LIBRARY.md) für die
> Gesamt-Bibliothek-Tour; dieses Kapitel deckt die
> Webstream-spezifischen Aspekte ab.

Ein **Webstream** ist eine URL, die auf eine andere
HTTP-Audioquelle zeigt — typischerweise einen Icecast- oder
Shoutcast-Stream, der von jemand anderem betrieben wird.
Wenn in einer Sendung eingeplant, verbindet sich die
Playout-Engine mit der URL und überträgt deren Inhalt für
die konfigurierte Dauer.

Webstreams sind der einfachste Weg, externen Inhalt zu
syndizieren: ein stündliches Nachrichten-Bulletin von der
BBC, ein lokaler Wetter-Feed, ein automatisierter
Musikdienst. Die Remote-Quelle übernimmt die ganze schwere
Arbeit; Ihre Station muss nur die URL in den Sendeplan
aufnehmen.

---

## 1. Der Webstream-Bibliothekseintrag

Bibliothek → Filter-Chip **Webstream** (orange).

```
   ┌───────────────────────────────────────────────────────────────┐
   │  Typ       │ Titel          │ URL                     │ Länge │
   ├────────────┼────────────────┼─────────────────────────┼───────┤
   │  Webstream │ BBC Radio 1    │ http://stream.bbc.co.uk/│ 60:00 │
   │  Webstream │ FIP Live       │ http://icecast.radiofra/│ 30:00 │
   │  Webstream │ Wetter stündl. │ http://wx.example.com/m/│ 03:00 │
   └────────────┴────────────────┴─────────────────────────┴───────┘
```

Jeder Webstream hat:

| Spalte | Bedeutung |
|---|---|
| **Titel** | Anzeigename. Wird überall verwendet. |
| **URL** | Die HTTP(S)-Quell-URL. |
| **Länge** | Standarddauer, wenn eingeplant — wie lange der Webstream pro Verwendung spielt. Format `01h 05m 05s` seit 2026-05-19. |

Die Länge ist der *einzige* zeitkritische Parameter — ein
Webstream "spielt für immer" aus Sicht der Remote-Quelle;
die Länge in RASTATIME sagt dem Playout, wann es trennen
und zum nächsten Schedule-Item übergehen soll.

---

## 2. Einen Webstream erstellen

Bibliothek → **+ Neu** → **Webstream**.

```
   ┌───────────────────────────────────────────────────────────────┐
   │  Neuer Webstream                                              │
   ├───────────────────────────────────────────────────────────────┤
   │   Name:             [                                       ] │
   │   Quell-URL:        [                                       ] │
   │   Standardlänge:    [01h 00m 00s   ]                          │
   │   Beschreibung:     [                                       ] │
   │   MIME-Typ:         [Automatisch erkennen ▾]                  │
   ├───────────────────────────────────────────────────────────────┤
   │                                       [Abbrechen][Speichern]  │
   └───────────────────────────────────────────────────────────────┘
```

| Feld | Hinweise |
|---|---|
| **Name** | Erforderlich. Das sichtbare Label in der Bibliothek und im Sendeplan. |
| **Quell-URL** | Erforderlich. Die HTTP(S)-URL des Audio-Streams. Direkte Stream-URL, keine Player-Landing-Page. Beispiele: `http://stream.bbc.co.uk/...`, `http://icecast.example.com:8000/mountpoint`. |
| **Standardlänge** | Erforderlich. `HHh MMm SSs`-Format. Siehe §3 für das Sekunden-Präzisions-Detail. Seit dem 30.09.2026 wird eine geänderte Länge in die Zeilen der kommenden Sendungen übernommen, die den Webstream enthalten (bereits gestartete Zeilen bleiben unberührt), und diese Sendungen werden neu ausgelegt - ein Relais, das eine Sendung füllen soll, braucht kein Neu-Befüllen mehr. |
| **Beschreibung** | Freitext, optional. Wird im Bibliothekszeilen-Tooltip und im öffentlichen Programmplan-Export gezeigt. |
| **MIME-Typ** | Standardmäßig automatisch erkennen; überschreiben Sie nur, wenn die Quelle ihren MIME-Typ falsch meldet. |

Klicken Sie **Speichern**. Der Webstream erscheint sofort in
der Bibliothek und kann zu jeder zukünftigen Zeit eingeplant
werden.

> **Operator-Tipp.** Testen Sie die URL in einem Browser
> oder mit `curl -I`, bevor Sie speichern. RASTATIME führt
> kein Pre-Flight der URL beim Speichern durch — eine
> kaputte URL fällt erst auf, wenn der Webstream tatsächlich
> eingeplant wird und das Playout versucht, sich zu
> verbinden.

> **Wie es unter der Haube funktioniert.** Webstreams leben
> in `cc_webstream` (id, name, description, url, length,
> creator_id, mtime). Beim Einplanen referenziert eine
> `cc_schedule`-Zeile den Webstream via `stream_id`. Zur
> Spielzeit öffnet die Playout-Engine eine HTTP-Quelle via
> libVLC und publiziert sein dekodiertes PCM an den
> Output-Mixer. Siehe ARCHITECTURE §10.

---

## 3. Standardlänge mit Sekunden-Präzision (Abschnitt 23.17)

Vor 2026-05-19 akzeptierte das Standardlänge-Feld nur
Stunden und Minuten ("01h 05m"). Die zugrunde liegende
Datenbank-Spalte ist ein PostgreSQL-`interval`, das
intern immer "HH:MM:SS" speicherte, aber die
Sekunden-Komponente war hart-null, und der Parser des
Formulars akzeptierte sie nicht.

Seit 2026-05-19 akzeptiert das Formular eine **optionale
dritte Sekunden-Komponente**:

```
   01h 05m 05s    ← 1 Stunde 5 Minuten 5 Sekunden
   01h 05m        ← 1 Stunde 5 Minuten (Sekunden optional)
        05m       ← 5 Minuten (Stunden optional)
            45s   ← 45 Sekunden (eine 45-s-Station-ID via Webstream)
```

Die Anzeige zeigt immer alle drei Komponenten
("01h 05m 00s") für visuelle Konsistenz — Operator-
Entscheidung 2026-05-19. Der Validator ist vollständig
abwärtskompatibel: jede pre-2026-05-19-Eingabe ("01h 05m")
parst noch.

> **Warum das wichtig ist.** Kurze Stings, Station-IDs und
> Jingles, die via Webstream-URL bedient werden, mussten
> zuvor auf eine Minute aufgerundet werden. Ein 30-s-Jingle,
> als "1 Minute" eingeplant, spielte den Jingle gefolgt von
> 30 s Stille (oder 30 s der nächsten Playlist-Iteration).
> Mit Sekunden-Präzision ist der Jingle-Slot genau 30 s
> und das nächste Item startet pünktlich.

> **Wie es unter der Haube funktioniert.** Drei Hot Spots
> in `application/models/Webstream.php` tragen die
> Sekunden-Behandlung:
>
> - `getDefaultLength()` formatiert mit `%H:%I:%S`.
> - `analyzeFormData()`-Regex wächst eine optionale
>   `(<n>s)`-Gruppe; der Parser ist
>   `^(?:([0-9]{1,2})h)?\s*(?:([0-9]{1,2})m)?\s*(?:([0-9]{1,2})s)?$`.
> - `save()` schreibt das `DateInterval` als `%H:%I:%S`,
>   sodass der persistierte Wert die neue Präzision
>   widerspiegelt.
>
> Siehe ARCHITECTURE §23.17 + Commit fae0fc5.

> **Out-of-Scope-Vereinheitlichung.** Dasselbe Dauer-Konzept
> taucht an drei anderen Stellen auf: Line-Ins (verwenden
> ihren eigenen Parser via
> `LineinController::_parseHmsToSeconds`), Smart Blocks
> (`SmartBlockCriteria` streng `HH:MM:SS`) und das
> Sendungs-Bearbeitungsformular. Die Vereinheitlichung
> aller vier in einen Helper würde die Inkonsistenz
> beseitigen (Webstream zeigt "01h 05m 05s", während
> Tracks "1:05:05.0" zeigen), erfordert aber das Berühren
> von drei Live-Konsumenten und ist aufgeschoben.

---

## 4. Einen Webstream einplanen

Genauso wie jedes Bibliotheks-Item:

### 4.1 Direkt auf eine Sendung

Show-Builder → ziehen Sie die Webstream-Zeile auf die
Sendung. Ein Schedule-Item erscheint mit dem Namen des
Webstreams und der Standardlänge.

Klicken Sie auf das Item → **Bearbeiten** → überschreiben
Sie die Dauer für diese spezifische Verwendung, wenn Sie
eine andere Länge als die Standard benötigen.

### 4.2 Innerhalb einer Playlist

Playlist-Editor → ziehen Sie den Webstream auf die Playlist.
Die Playlist-Zeile trägt den Webstream + dessen
Standardlänge und verhält sich wie jedes andere
Playlist-Item.

### Was spielt, wenn der Slot beginnt?

**Liquidsoap-Engine-Pfad (Produktions-Default seit 2026-05-29):**

1. Pypo sendet drei Telnet-Befehle an Liquidsoap:
   - `webstream.url <URL>` — setzt die HTTP-URL auf der
     dedizierten `input.http`-Source.
   - `var.set webstream.gain = <Faktor>` — setzt den
     per-Stream-Verstärkungs-Faktor (dB → linear Konversion
     passiert in Pypo).
   - `webstream.start` — fordert die Source auf zu verbinden.
2. Liquidsoaps `input.http`-Source öffnet die HTTP-
   Verbindung und buffert einige Sekunden Audio (5-s-Clock-
   Bridge, bis zu 10 s Stream-Puffer). Seit 2026-09-04 passiert
   das bereits **10 s vor dem Slot** („Vorwärmen") bei
   geschlossenem Bus-*Gate*, sodass der Puffer beim Slot-Start
   voll ist.
3. Beim Slot-Start öffnet Pypo das Gate; der Bus-Switch routet
   das Audio innerhalb eines Frames zur Webstream-Source — Hörer
   hören den Stream. Der **gleiche** Stream in der Folgeshow läuft
   einfach weiter (nur Übergabe der Buchführung, kein Bounce). Ein
   *anderer* Webstream direkt nach einem Webstream kann nicht
   vorgewärmt werden (eine Stream-Quelle): Er verbindet beim
   Slot-Start und ist nach vollem Puffer, ~5 s, auf Sendung.
   Am Slot-Ende schließt Pypo das Gate: Der Bus blendet den
   Webstream über die Standard Show-Crossfade-Dauer (Settings →
   General; das nächste Element ist sofort voll da, 0 = harter
   Wechsel) unter dem nächsten Element aus und sendet dann
   `webstream.stop`. Das nächste Element startet pünktlich, statt
   auf das Leerlaufen des Puffers zu warten.
4. Bei der konfigurierten Dauer sendet Pypo `webstream.stop`;
   der Switch fällt zurück auf scheduled (Stille oder den
   nächsten Track).

**Server-Aussetzer (seit 2026-09-06):** Manche Stream-Server hören
mitten im Stream auf zu senden, ohne die Verbindung zu schließen —
Liquidsoap merkt das nicht von selbst, und der Slot bliebe still bis
zum Ende. Ein Wächter bewacht jetzt jeden sendenden Webstream: liefert
die Quelle ein paar Sekunden kein Audio, verbindet das Playout sie neu
(sauberes Stop + Start). Eine frische Verbindung ist in wenigen
Sekunden wieder auf Sendung, und der saubere Stop gibt den Hörer-Platz
auf dem Server frei, damit dessen Verbindungslimit nicht von toten
Verbindungen belegt wird. Ein Server, der keine neuen Verbindungen
annimmt, erzeugt weiter Stille, bis er wieder eine annimmt. Seit dem
2026-09-07 läuft der Wächter in der Audio-Engine selbst: ein
Frame-Zähler prüft die Quelle alle zwei Sekunden und verbindet nach
zwei stillen Prüfungen neu, ganz ohne Abfrageverkehr zwischen Playout
und Engine (der Windows-Build von Liquidsoap verliert bei jeder
solchen Abfrage Speicher). Die frühere Abfrage aus dem Playout wurde
am 2026-09-15 nach einer ruhigen Woche entfernt. Seit dem 2026-09-08
öffnet jeder Webstream-Slot und jede Neuverbindung eine ganz neue Verbindung mit
eigenem Puffer, statt einen dauerhaften Eingang wiederzuverwenden: auf
dem Windows-Build brauchte ein wiederverwendeter Eingang mitunter eine
Minute und länger bis zur Neuverbindung, und ein Slot konnte mit ein
paar Sekunden des vorigen Streams im Puffer beginnen. Beides ist
Geschichte; ein Slot beginnt auf seinem eigenen Stream, und das
Vorwärmen zehn Sekunden vor dem Slot gibt der neuen Verbindung Zeit,
sich zu füllen. Eine verworfene Verbindung, die nach einem Ausfall von
selbst zurückkommt, wird binnen Sekunden wieder geschlossen, damit der
Stream-Server keinen Hörerplatz mit einer Verbindung belegt hält, der
niemand zuhört.

**Aufnahme-Verhalten (neu seit Phase E, 2026-05-29):**
Scheduled Webstreams landen jetzt im Per-Show-`.mp3`-
Aufnahme-Archiv — das Audio fließt durch den internen
Liquidsoap-Bus, an den `output.file` angeschlossen ist, und
wird zusammen mit eventuellen regulären Tracks der Show
aufgezeichnet. Vor Phase E hatten Webstream-only-Shows
stille Aufnahmen.

**Initiale Show-Latenz:** Mit Vorwärmen (seit 2026-09-04)
startet ein Webstream-Slot ohne Lücke — der Stream wurde 10 s
vorher verbunden und gepuffert. Nur ein Webstream, der nicht
vorgewärmt werden konnte (siehe Schritt 3), braucht noch ~5 s
zum Puffern. Listener-seitige Player haben ihren eigenen
~10-s-Puffer, sodass die effektive End-Hörer-wahrgenommene
Verzögerung von diesem Player-seitigen Puffer dominiert wird.

### Was passiert, wenn die URL nicht erreichbar ist?

`input.http` versucht die Verbindung alle **2 Sekunden** neu
(`poll_delay`) mit einem **10-Sekunden-Timeout** pro Versuch
(`timeout`). Während die Retries laufen, bleibt
`source.is_ready` auf false und der Bus-Switch fällt auf
scheduled (Stille). Die Retries laufen für die volle Dauer
des geplanten Slots.

Der Liquidsoap-Log erfasst jeden fehlgeschlagenen
Verbindungsversuch:

```
[input.http:3] Connection refused: <url>
[input.http:3] Connecting to <url> ...
```

Operator-sichtbares Symptom: die Show spielt Stille für
ihre volle Dauer. Keine Warnung im Dashboard-Popup; prüfen
Sie den Liquidsoap-Log — seit dem 18.09.2026 die neueste
`C:/rastatime/logs/liquidsoap-stdout-*.log`-Scheibe —, wenn
ein geplanter Webstream still blieb.

> **Operator-Tipp.** Ein Webstream, der "manchmal nichts
> spielt", bedeutet normalerweise, dass sich die URL der
> Quelle geändert hat und die Webstream-Bibliotheks-Zeile
> auf die alte zeigt. Verifizieren Sie die URL in einem
> Browser. Viele Nachrichten- / Wetter-Feeds rotieren URLs
> täglich — bookmarken Sie die persistente
> Direkt-Stream-URL, nicht die dynamisch umleitende
> Player-Seite.

---

## 5. Einen Webstream bearbeiten oder löschen

Gleiche Aktionen wie jedes Bibliotheks-Item:

| Aktion | Effekt |
|---|---|
| **Bearbeiten** | Den Dialog öffnen. Speichern propagiert auf *alle* zukünftigen geplanten Verwendungen (die URL-Änderung greift beim nächsten Spielen). Bestehende Playlist-Referenzen behalten ihre Standardlänge, es sei denn, der Operator bearbeitet die Playlist auch. |
| **Löschen** | Den Webstream entfernen. Alle `cc_playlistcontents`- und `cc_schedule`-Zeilen, die ihn referenzieren, werden entfernt (CASCADE). |

---

## 6. Stream-Gain (pro-Stream-Eingangsverstärkung)

Webstreams aus Drittanbieter-Quellen sind oft lauter oder
leiser als der Rest Ihrer Bibliothek. Um die Lautstärke zu
normalisieren:

Webstream bearbeiten → **Eingangsverstärkung (dB)** →
setzen Sie einen positiven Wert zum Boosten oder einen
negativen zum Abschwächen.

| Einstellung | Effekt |
|---|---|
| `0.0` (Standard) | Keine Gain-Änderung. |
| `+3.0` | Um 3 dB boosten. |
| `-6.0` | Um 6 dB abschwächen. |

Der Gain wird in der Playout-Engine angewendet, bevor das
Audio den Output-Mixer trifft; sowohl die Lautsprecher der
Operator-Maschine als auch der Output-Stream empfangen den
angepassten Pegel.

> **Operator-Tipp.** Verwenden Sie einen Lautstärke-
> Meter-Durchgang über ein paar Minuten des Webstream-
> Inhalts, um den richtigen Gain zu setzen. Ein üblicher
> Operator-Workflow: planen Sie den Webstream als Test für
> 10 Minuten, überwachen Sie den Output-Stream mit einem
> Pegel-Meter (z.B. dem Audio-Meter von VLC), passen Sie
> den Gain an, wiederholen.

> **Wie es unter der Haube funktioniert.** Migration 0048
> fügte `cc_webstream.input_gain_db` (FLOAT) hinzu.  Die
> Stream-Engine legt ein `amplify` um die Webstream-Quelle;
> der Playout setzt dessen Faktor (`var.set webstream.gain`,
> aus dB umgerechnet als 10^(dB/20), z.B. `-6` dB → `0.50`)
> jedes Mal, wenn ein Webstream startet — beim Vorwärmen 10 s
> vor dem Slot oder beim Slot-Start — und nachdem ein DJ
> zurückgibt.  Ein Webstream ohne Gain bekommt ausdrücklich den
> Faktor `1.0`, damit kein Stream den Pegel des vorigen erbt.
> Bis zur Übernahme durch die Liquidsoap-Engine (2026-05-29)
> wendete der Playout stattdessen einen FFmpeg-`volume`-Filter
> an.  Siehe ARCHITECTURE §23.10.

---

## 6a. Puffer (Verzögerung und Reserve je Stream)

Ein geplanter Webstream läuft in der Playout-Engine durch einen
kleinen Puffer. Zwei Felder im Webstream-Dialog steuern ihn
(jedes mit einem Hilfe-Symbol, das die Kurzfassung zeigt):

| Feld | Bedeutung | Standard |
|---|---|---|
| **Puffer (s)** | Sekunden Ton, die der Stream sammelt, bevor er zu spielen beginnt. Etwa 1 s unter *Puffer max* halten. | 5 |
| **Puffer max (s)** | Größte Menge Ton, die der Puffer hält. In den 10 s vor dem Slot füllt er sich bis zu diesem Wert; das ist die Verzögerung zusätzlich zum Verbindungs-Burst des Servers und zugleich die Reserve bei Aussetzern. | 10 |

Kleinere Werte bringen den Stream näher an live, größere geben
mehr Reserve. Lassen Sie beide Felder leer für die
Standardwerte. Die Werte gelten ab dem nächsten Start des
Streams; kein Neustart nötig. Sie reisen auch mit
**Einstellungen → Import / Export** (`webstreams.csv`, Spalten
`bridge_seconds`, `bridge_max_seconds`).

**Beispiel: BBC-World-Service-Nachrichten.** Gemessen am
2026-11-05: der BBC-Server schickt beim Verbinden 3,6 s Ton,
der Puffer fügte 10 s hinzu, der Slot lief also 13,8 s hinter
dem Server, und die Moderation war 8,5 s nach dem Einstieg zu
hören. Mit *Puffer* 2 und *Puffer max* 3 sinkt die Verzögerung
auf etwa 6,6 s: das Bulletin beginnt 1,5 s nach dem Einstieg,
und eine Zeile von 5:02 endet in der Pause danach.

> **Wie es unter der Haube funktioniert.** Migration 0079
> fügte `cc_webstream.bridge_seconds` / `bridge_max_seconds`
> hinzu (NULL = Standard).  Das Playout setzt `var.set
> webstream.bridge` / `webstream.bridge_max` vor jedem
> `webstream.start`; der frische `buffer()` des Slots wird damit
> gebaut.  Das `max_buffer` von `input.http` ist kein Hebel für
> die Verzögerung: der Eingang verwirft nie Daten, er bremst nur
> das Lesen.  Siehe ARCHITECTURE §23.88.

---

## 7. Webstreams in autoloading Playlists

Ein Webstream kann der gesamte Body einer autoloading
Playlist sein — nützlich für "jeden Montag 14:00 relayen
wir X", ohne die URL jede Woche manuell einzuplanen.

Einschränkungen:

- Ein Webstream innerhalb eines **Wiederholen bis voll**-
  Bodys erzeugt wiederholte kurze Verbindungsversuche, da
  jede "Iteration" des Bodys feuert. Vermeiden — verwenden
  Sie stattdessen eine einzelne Langzeit-Webstream-Zeile.
- Smart Blocks innerhalb einer Webstream-tragenden Playlist
  erhalten die Outro-Reserve-Behandlung nicht auf dieselbe
  Weise wie in einem Track-only-Body. Planen Sie
  konservativ.

Siehe [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md)
§5 für die allgemeine "was funktioniert / was nicht"-
Anleitung.

---

## 8. Häufig gestellte Fragen

### "Warum schneidet mein Webstream nach ein paar Sekunden ab?"

Wahrscheinlich ist die **Standardlänge** sehr kurz gesetzt.
Prüfen Sie die Längen-Spalte der Bibliothekszeile.

### "Kann ich denselben Webstream auf zwei Sendungen gleichzeitig einplanen?"

Nein. Es gibt eine Playout-Engine und einen Output-Mixer.
Zwei Sendungen können nicht gleichzeitig auf demselben
Output laufen. (Sie *können* zwei verschiedene
Output-Streams haben, die unterschiedliche Inhalte spielen
— siehe [Streams](./STREAMS.md).)

### "Warum klingt der Webstream schlecht / verzerrt?"

Häufige Ursachen:

- Die Webstream-URL ist intermittierend (Quell-seitiges
  Problem).
- Die Quelle ist in einem Codec, den die Playout-Engine
  nicht sauber dekodieren kann. Prüfen Sie den MIME-Typ und
  versuchen Sie, ihn explizit zu setzen.
- Netzwerklatenz zur Quelle übersteigt den Puffer.
  Versuchen Sie eine kürzere URL oder eine nähere Quelle.
- Das Netzwerk der Operator-Maschine hat Paketverlust.
  Verifizieren Sie mit `Test-Connection -Continuous
  <hostname>`.

### "Kann ich den Inhalt eines Webstreams mit Record-per-Show aufzeichnen?"

Ja. Der Recorder zapft den On-Air-Output; was auch immer
spielt (Track, Webstream, Line-In) wird erfasst. Siehe
[Aufnahme pro Sendung](./RECORD_PER_SHOW.md).

### "Wie authentifiziere ich mich an einer passwort-geschützten Quelle?"

Inline-Credentials in der URL:

```
   http://user:password@stream.example.com/private
```

RASTATIME gibt diese direkt an den HTTP-Client von libVLC
weiter. Für Quellen, die ein Bearer-Token oder ein
Session-Cookie erfordern, müssen Sie ein kleines Relay
einrichten (z.B. ein lokales nginx, das die
authentifizierte Quelle proxied) und den Webstream auf das
Relay zeigen lassen.

### "Kann ich eine HLS- (.m3u8) URL verwenden?"

Ja — libVLC behandelt HLS. Verwenden Sie die
.m3u8-Master-Playlist-URL als Quell-URL. Der Standard-MIME-
Typ "Automatisch erkennen" wählt HLS korrekt.

### "Kann ich eine YouTube-Live-URL verwenden?"

Nicht direkt — YouTube exponiert keine stabile direkte
Stream-URL. Operator-Umgehung: verwenden Sie `yt-dlp`, um
die aktuelle Stream-URL aufzulösen, und aktualisieren Sie
die Webstream-Bibliotheks-Zeile per Cron. Nicht offiziell
unterstützt.

---

## Wohin als Nächstes

* [Bibliothek](./LIBRARY.md) — Gesamt-Bibliothek-Tour.
* [Kalender](./CALENDAR.md) — Bibliotheks-Items einplanen.
* [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) —
  Webstreams als autoloaded Inhalt.
* [Streams](./STREAMS.md) — die *Ausgangs*-Seite; Webstreams
  hier sind die *Eingangs*-Seite.
