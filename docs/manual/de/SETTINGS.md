# Einstellungen

> **Wo Sie sich im Handbuch befinden.** Dieses Kapitel ist
> der Hub-und-Speiche-Index für das Einstellungs-Menü.
> Jeder Abschnitt unten verweist auf ein dediziertes
> Kapitel (wo eines existiert) oder dokumentiert die Seite
> inline (wo die Seite zu klein für ein eigenes Kapitel
> ist).

Das Einstellungs-Menü ist die per-station Konfigurations-
Oberfläche. Vollständig sichtbar nur für **Admin** und
**Super Admin**; **Program Manager** sieht eine Teilmenge.
Siehe [Benutzer und Rollen](./USERS_AND_ROLES.md) §5 für
die vollständige Berechtigungsmatrix.

Dieses Kapitel:

1. Listet jede Einstellungs-Unterseite mit einem
   Einzeilen-Zweck auf.
2. Dokumentiert inline die kleineren Seiten (Allgemeine
   Einstellungen, Systemstatus, Tools).
3. Verweist auf das dedizierte Handbuch-Kapitel für die
   größeren (Streams, Lokale Maschine, Auto DJ,
   Sendungs-Vorlagen, Benutzer verwalten, Lokalisierung).

---

## 1. Das Einstellungs-Menü

Top-Bar Einstellungen → öffnet das Untermenü:

```
   ┌──────────────────────────┐
   │  Einstellungen           │
   ├──────────────────────────┤
   │  Allgemeine Einst.       │
   │  Lokale Maschine         │
   │  Streams                 │
   │  Line-In-Bibliothek      │
   │  Auto DJ                 │
   │  Sendungs-Vorlagen       │
   │  Benutzer verwalten      │
   │  Lokalisierung           │
   │  Systemstatus            │
   │  Tools  ▾                │
   └──────────────────────────┘
```

### Seite-für-Seite

| Seite | Zweck | Handbuch-Kapitel |
|---|---|---|
| **Allgemeine Einstellungen** | Stationsname, Standardsprache, Standardfarben, Dashboard-Vorausschau, Standard-Import-Besitzer, Standard-Crossfade-Dauer, Favicon, Stationslogo. | Dieses Kapitel §2 |
| **Lokale Maschine** | Soundkarten-Ausgabe-/Eingabegeräte, lokaler Import-Ordner, lokaler Aufnahme-Ordner. | [Lokale Maschine](./LOCAL_MACHINE.md) |
| **Streams** | Bis zu vier Output-Streams, pro-Stream-Bitrate / Mountpoint / Codec, Quell-Authentifizierung. | [Streams](./STREAMS.md) |
| **Line-In-Bibliothek** | Benannte Live-Audio-Eingänge von Soundkarten-Geräten. | [Line-In](./LINE_IN.md) |
| **Auto DJ** | Hintergrund-Lückenfüller + Auffüllen unvollständiger Sendungen. | [Auto DJ](./AUTO_DJ.md) |
| **Sendungs-Vorlagen** | Wiederverwendbare Snapshots des Sendungsformulars. | [Sendungs-Vorlagen](./SHOW_TEMPLATES.md) |
| **Benutzer verwalten** | Benutzer erstellen / bearbeiten / deaktivieren, Passwörter zurücksetzen, API-Schlüssel verwalten. | [Benutzer und Rollen](./USERS_AND_ROLES.md) |
| **Lokalisierung** | UI-Sprachauswahl, Locale-Generierung. | [Sprachen](./I18N.md) |
| **Systemstatus** | Live-Dienst-Gesundheit, Preflight-Warnungen, Dienst-Neustart-Widget. | Dieses Kapitel §3 |
| **Tools** | Untermenü: DB-Konsole, Log-Viewer, Cache-Reset. | Dieses Kapitel §4 |

---

## 2. Allgemeine Einstellungen

Einstellungen → **Allgemeine Einstellungen**.

```
   ┌─────────────────────────────────────────────────────────────────┐
   │  Allgemeine Einstellungen                          [ Speichern ]│
   ├─────────────────────────────────────────────────────────────────┤
   │  Station                                                        │
   │    Stationsname:        [ Mein Community-Radio                ] │
   │    Stationsbeschreibung:[ Ein Community-Radio für ...         ]│
   │    Stationslogo:        [ Datei wählen ▾ ] (derzeit gesetzt)    │
   │    Stations-Favicon:    [ Datei wählen ▾ ] (derzeit gesetzt)    │
   │    Primärfarbe:         [ #ff5d1a ] [■] [ Zurücksetzen ]        │
   │    Zeitzone:            [ Europe/Berlin ▾ ]                     │
   │    Woche beginnt am:    [ Montag ▾ ]                            │
   │                                                                 │
   │  Standards                                                      │
   │    Standardsprache:     [ Deutsch (de_DE) ▾ ]                   │
   │    Standard Track-Crossfade: [ 1.0 ] Sekunden                   │
   │    Standard Show-Crossfade:  [ 1.0 ] Sekunden                   │
   │    Standard-Track-Typ:  [ Musik ▾ ]                             │
   │    Standard-Import-Bes.:[ admin ▾ ]                             │
   │    Standard-Aufnahme:   [ ☐ Alle neuen Sendungen aufzeichnen ]  │
   │                                                                 │
   │  Dashboard                                                      │
   │    Vorausschau:         [ 5 ] kommende Items                    │
   │    Aktualisierung:      [ 5 ▾ ] Sekunden                        │
   │                                                                 │
   │  E-Mail (für Passwort-Zurücksetzung)                            │
   │    SMTP-Server:         [                                     ] │
   │    SMTP-Port:           [ 587 ]   TLS verwenden: [ ☑ ]          │
   │    SMTP-User / Pass:    [          ] [          ]               │
   │    Von-Adresse:         [ noreply@my-station.example.com      ] │
   └─────────────────────────────────────────────────────────────────┘
```

### Station

| Feld | Hinweise |
|---|---|
| **Stationsname** | Überall sichtbar — Seitentitel, ICY-Metadaten, E-Mail-From-Name. |
| **Stationsbeschreibung** | Freitext-Beschreibung. Verwendet in Podcast-Feeds und ICY-Metadaten. |
| **Stationslogo** | Bild oben links auf jeder Seite. Max 200 KB, JPG / PNG / GIF. |
| **Stations-Favicon** | Bild im Browser-Tab. Max 200 KB, JPG / PNG / GIF / ICO. Als data: URI gerendert; keine Datei-Schreibvorgänge nach public/. |
| **Primärfarbe** | Die Akzentfarbe der gesamten Oberfläche und der Radio-Seite — Links, Hervorhebungen, ausgewählte Zeilen, der aktive Menüpunkt, Fortschritts- und Speicherbalken, Scrollbalken, Abschnittspfeile, Play-Knopf und Lautstärkeregler des Stream-Players. Geben Sie `#rrggbb` ein oder nutzen Sie den Farbwähler neben dem Feld; **Auf Standard zurücksetzen** stellt das Orange (`#ff5d1a`) wieder her. Wirkt beim nächsten Seitenaufruf. Wählen Sie eine Farbe, die sich vom dunkelgrauen Hintergrund abhebt; Text auf der Farbe wechselt von selbst zwischen Weiß und Schwarz. Signalfarben (Fehler, Warnungen, die Sendungsfarben im Kalender) sowie die eigenen Akzente der Widgets Now Playing / Wochenprogramm (Petrol) und Song Request (Blau) bleiben unverändert. |
| **Zeitzone** | Die Operator-Zeitzone für alle Kalender- / Sendeplan-Anzeigen. Pro Sendung in `cc_show_days.timezone` gespeichert, sodass das Ändern hier bestehende Sendungen nicht rückwirkend beeinflusst. |
| **Woche beginnt am** | Montag / Sonntag. Beeinflusst das Wochenansichts-Layout des Kalenders. |

### Standards

| Feld | Hinweise |
|---|---|
| **Standardsprache** | UI-Sprache für neue Benutzer + den Anmeldebildschirm. Bestehende Benutzer behalten ihre per-user Spracheinstellung (über das Benutzer-Dropdown gesetzt). |
| **Default Track Crossfade Duration** (Standard Track-Crossfade Dauer) | Der Crossfade zwischen zwei aufeinanderfolgenden Titeln **derselben Sendung**: der abgehende Titel blendet aus, während der ankommende über so viele Sekunden einblendet (1 Sekunde ist typisch; 0 = die Titel folgen ohne Überlappung; bis zu 10 Sekunden für weiche Übergänge). Der Kalender legt aufeinanderfolgende Zeilen mit genau dieser Überlappung an. |
| **Default Show Crossfade Duration** (Standard Show-Crossfade Dauer) | Der Übergang **an einer Sendungsgrenze** (seit 2026-09-27): die alte Sendung blendet über so viele Sekunden aus, während der erste Titel der neuen Sendung sofort in voller Lautstärke startet — eine Sendung, die mit Jingle oder ID beginnt, ist vom ersten Schlag an zu hören. Dieselbe Form und derselbe Wert gelten für jeden Wechsel zwischen **Eingängen** (Titel ↔ Webstream ↔ Line-In): die ankommende Quelle ist sofort voll da, die abgehende blendet darunter aus; 0 = harter Wechsel. Ein Webstream oder Line-In, der in beiden Sendungen eingeplant ist, läuft nahtlos weiter. Startwert 1 s. Beide Crossfade-Werte übernimmt die Audiokette wenige Sekunden nach dem Speichern (geplanter Neustart in einem ruhigen Moment oder an einer Titelgrenze); „Jetzt anwenden" in Settings → Local Machine erzwingt es. |
| **Standard-Track-Typ** | Der Track-Typ, der neuen Uploads zugewiesen wird, wenn der Operator nicht explizit einen setzt. Beeinflusst Smart-Block-Filter. |
| **Standard-Import-Besitzer** | Das Benutzerkonto, dem als Besitzer für Dateien, die über den lokalen Import-Ordner importiert werden, gutgeschrieben wird. Standardmäßig `admin`. |
| **Standard-Aufnahme** | Wenn angekreuzt, haben neue Sendungen **Diese Sendung aufzeichnen:** vor-angekreuzt. Siehe [Aufnahme pro Sendung](./RECORD_PER_SHOW.md). |

### Dashboard

| Feld | Hinweise |
|---|---|
| **Vorausschau** | Wie viele kommende Sendungen das "Kommt als Nächstes"-Panel des Dashboards anzeigt. 3-5 ist typisch. |
| **Aktualisierungsintervall** | Wie oft das Dashboard nach aktualisiertem Zustand pollt. 5 s ist der Standard. 1 s ist reaktionsschnell, aber teuer auf langsamen Netzwerken. 30 s ist leicht, aber verzögert. |

### Live-Text-Info

Aufklappbarer Bereich unter den Allgemeinen Einstellungen (seit
2026-09-28). Die „Now playing"-Zeile als Textdatei für andere Systeme
(Website, Displays, Aggregatoren): eine UTF-8-Zeile, immer ersetzt, vom
Playout bei jedem Wechsel von Titel, Webstream, Line-In oder DJ geschrieben.

| Feld | Hinweise |
|---|---|
| **Die „Now playing"-Zeile in eine Textdatei schreiben?** | Hauptschalter. |
| **Live-Text-Format** | Dieselben drei Varianten wie das Stream Label (Artist - Title / Show - Artist - Title / Station name - Show name) mit denselben Rückfällen: eine Live-Quelle ohne Interpret und Titel zeigt *Station name - Show name*, Stille den Off-Air-Text. Unabhängig vom Stream Label. |
| **Im Web veröffentlichen** | Die Datei wird unter `http://<host>/live/now-playing.txt` ausgeliefert (statische Datei, ohne Login, unabhängig vom Public-API-Schalter). Aus dem Internet erreichbar, sobald der Webserver es ist, wie die Widgets. |
| **Zusätzlich in Datei schreiben** | Optionaler absoluter Pfad (dieser Rechner oder Netzwerkfreigabe). |
| **Auf einen FTP-Server hochladen** | Bei jeder Änderung wird die Datei per FTP, FTPS (explizites TLS) oder SFTP auf den Zielpfad hochgeladen; eigene Zugangsdaten, getrennt vom FTP-Import. SFTP braucht ein `curl` mit libssh2 (das von Git für Windows; das in Windows eingebaute kann es nicht). Fehler werden geloggt, die nächste Änderung versucht es erneut. |

Die Zeile bildet die Audio-Engine aus den Metadaten, die sie tatsächlich
in den Stream sendet, DJ-Titel und Webstream-Titel eingeschlossen. Eine
geänderte Einstellung greift beim nächsten Wechsel, kein Neustart.

### TuneIn-Einstellungen

Aufklappbarer Bereich unter den Allgemeinen Einstellungen. Seit
2026-09-28 sendet der Playout die „Now playing"-Information selbst an
TuneIn; vorher wurden nur Datei-Starts gemeldet, und die Anzeige verschwand
nach fünf Minuten.

| Feld | Hinweise |
|---|---|
| **Push metadata to your station on TuneIn?** (Metadaten an TuneIn senden) | Hauptschalter. Wenn an, sendet der Playout bei jedem Titelstart Titel und Interpret, beim Start eines Webstreams oder Line-Ins den Sendungsnamen, und wiederholt die letzte Meldung alle vier Minuten (TuneIn entfernt eine Anzeige, die fünf Minuten still bleibt). Speichern mit aktivem Schalter prüft die Zugangsdaten gegen TuneIn und lehnt ungültige ab. |
| **Station ID**, **Partner Id**, **Partner Key** | Aus Ihrem TuneIn-Partnerkonto (AIR API). Der Key erscheint in keinem Log. |

Eine geänderte Einstellung greift beim nächsten Push; kein Neustart. Ein
Live-DJ (Master / Show Source) wird nicht gemeldet; der letzte Titel
bleibt bis zum nächsten geplanten Element in der Anzeige.

### E-Mail (Passwort-Zurücksetzung)

Falls konfiguriert, sendet der Flow Benutzer verwalten →
Passwort zurücksetzen → E-Mail senden einmalige Link-
E-Mails. Falls leer gelassen, ist der einzige
Zurücksetzungs-Pfad "temporäres Passwort setzen".

| Feld | Hinweise |
|---|---|
| **SMTP-Server / -Port** | Der ausgehende Mailserver Ihrer Station. |
| **TLS** | Empfohlen an; moderne SMTP-Server lehnen unverschlüsselte Verbindungen ab. |
| **Von-Adresse** | Verwendet als From-Header der E-Mail. Oft erforderlich, dass sie zum SMTP-Konto passt. |

> **Wie es unter der Haube funktioniert.** Einstellungen
> werden in die Tabelle `cc_pref` als Schlüssel/Wert-Zeilen
> geschrieben. Die meisten Einstellungen werden sofort neu
> geladen; die SMTP-Einstellungen erfordern einen Neustart
> des Worker-Dienstes, um aufgenommen zu werden. Siehe
> ARCHITECTURE §11.

---

## 3. Systemstatus

Einstellungen → **Systemstatus**.

Gesundheitsübersicht jeder Komponente, von der RASTATIME
abhängt.

```
   ┌─────────────────────────────────────────────────────────────────┐
   │  Systemstatus                           [ Aktualisieren ]       │
   ├─────────────────────────────────────────────────────────────────┤
   │  Dienste                                                        │
   │   ● RASTATIME-API        Läuft (PID 4321, Uptime 4T 12h)        │
   │   ● RASTATIME-WORKER     Läuft (PID 4322, Uptime 4T 12h)        │
   │   ● RASTATIME-PLAYOUT    Läuft (PID 4323, Uptime 4T 12h)        │
   │   ● RASTATIME-ANALYZER   Läuft (PID 4324, Uptime 4T 12h)        │
   │   ● Icecast2             Läuft (PID 4325, Uptime 4T 12h)        │
   │   ● Apache               Läuft (PID 4326, Uptime 4T 12h)        │
   │                                                                 │
   │  Konnektivität                                                  │
   │   ✓ Datenbank (PostgreSQL)     Verbunden, 2 ms Antwort          │
   │   ✓ Icecast-Quell-Verbindung   Verbunden, /rastatime aktiv      │
   │   ⚠ Lokaler Import-Ordner      3 fehlgeschlagene Imports        │
   │                                                                 │
   │  Preflight-Warnungen                                            │
   │   ⚠ FFmpeg nicht in PATH (Analyzer fiel auf bundled zurück)     │
   │   ⚠ Postgres-Host 'db1.example.com' unerreichbar — lokal nutzen │
   │                                                                 │
   │  Dienst-Controls                                                │
   │   [ API neu starten ] [ Worker neu starten ] [ Playout neu st.] │
   └─────────────────────────────────────────────────────────────────┘
```

### Dienste

Live-PID + Uptime für jeden NSSM-verwalteten Windows-
Dienst. Ein roter Badge hier ist das Signal, den Dienst
über `Get-Service RASTATIME-*` in PowerShell oder das
[`CRASH_RECOVERY`](../../operator/CRASH_RECOVERY.md)-
Runbook zu prüfen.

### Konnektivität

Live-Prüfung jeder externen Abhängigkeit:

- **Datenbank (PostgreSQL)** — Antwortzeit (Round-Trip zu
  `SELECT 1`).
- **Icecast-Quell-Verbindung** — playout-engine-seitiger
  Quell-Verbindungszustand (spiegelt die Streams-Seite).
- **Lokaler Import-Ordner** — letztes Scan-Ergebnis; ein
  gelber Badge bedeutet, dass Dateien an
  Abspielbarkeits-Prüfungen scheiterten; prüfen Sie das
  `.failed/`-Verzeichnis.

### Preflight-Warnungen

Persistierte Warnungen vom Start-Preflight-Check. Dinge
wie "FFmpeg nicht in PATH" oder "erwarteter Port bereits
in Verwendung". Jede Warnung hat einen Click-Through mit
Mitigationsempfehlung.

> **Wie es unter der Haube funktioniert.** Angetrieben vom
> Endpunkt `/api/v2/preflight/warnings`, gestützt auf die
> Tabelle `rastatime_preflight_warning`. Das Start-
> `preflight.py` läuft ~30 Prüfungen und fügt eine Zeile pro
> Fehler ein; die Seite listet sie auf, und der Operator
> kann verwerfen / auflösen.

### Dienst-Controls (nur Admin+)

Ein-Schaltflächen-Neustart für jeden Windows-Dienst.
Ersetzt die Notwendigkeit, RDP zu verwenden und
`Restart-Service RASTATIME-PLAYOUT` auszuführen.

Effekte variieren pro Dienst:

| Dienst | Neustart-Effekt |
|---|---|
| **API** | ~2 s Ausfall der REST-API. UI-Aufrufe können mitten in der Aktion scheitern. |
| **Worker** | Hintergrund-Jobs pausieren (~10 s). Kein benutzer-sichtbarer Effekt. |
| **Playout** | **Der Stream wird ~10 s still.** Sparsam während der Sendezeit verwenden. |
| **Analyzer** | Lokaler Import-Ordner pausiert (~5 s). |
| **Icecast** | Alle Hörer trennen sich; verbinden sich ~30 s später wieder. |
| **Apache** | Die Web-Oberfläche ist ~5 s unerreichbar. Operatoren werden auf die Anmeldeseite zurückgeworfen. |

> **Operator-Tipp.** Starten Sie nur den Dienst neu, der
> sich tatsächlich falsch verhält. Alle sechs in Folge
> neu starten funktioniert (es ist die Standard-
> [`RESTART_ORDER`](../../operator/RESTART_ORDER.md)), ist
> aber Overkill für ein Einzelkomponenten-Problem.

---

## 4. Tools

Einstellungen → **Tools** → Untermenü.

| Tool | Zweck |
|---|---|
| **DB-Konsole** | Read-only PostgreSQL-Abfrage-Oberfläche. Nur Super Admin. Standardmäßig versteckt; in `config/libretime.conf` mit `[tools] db_console = true` aktivieren. |
| **Log-Viewer** | Die letzten 200 Zeilen von `C:\rastatime\logs\error.log`, `api-stderr.log`, `playout-stderr.log` tailen. Automatische Aktualisierung alle 5 s. |
| **Cache-Reset** | Serverseitige Caches leeren (der Locale-String-Cache, der Bibliothek-DataTable-Cache). Verwenden Sie nach dem Bearbeiten von Übersetzungsdateien oder nach einem Massen-Import. |
| **Bibliothek-Abspielbarkeit neu scannen** | Die Analyzer-Abspielbarkeits-Prüfung über jeden bestehenden Track ausführen. Langsam (Minuten auf einer großen Bibliothek); verwenden Sie nach dem Upgrade von FFmpeg. Gestützt auf das Skript `infra/scripts/maintenance/rescan-playability.py`. |

Diese sind *keine* täglichen Tools. Die meisten Stationen
öffnen das Tools-Untermenü nie.

> **Warum DB-Konsole standardmäßig versteckt ist.** Eine
> read-only DB-Konsole kann Anmeldedaten in
> WHERE-Klauseln lecken, persönliche Daten via SELECT
> dumpen und zu einem Standbein werden, wenn die
> Anmeldedaten des Super Admins kompromittiert sind.
> Aktivieren Sie nur beim aktiven Debuggen einer
> Datenfrage.

---

## 5. Häufig gestellte Fragen

### "Ich habe eine Einstellung geändert, aber nichts passiert."

Die meisten Einstellungen treten sofort in Kraft.
Ausnahmen:

| Einstellung | Erfordert |
|---|---|
| SMTP | Worker-Dienst-Neustart |
| Stream-Anmeldedaten | Playout-Dienst-Neustart |
| Soundkarten-Gerät | Playout-Dienst-Neustart |
| Zeitzone | Hard-Refresh des Browsers (die Zeitzone wird client-seitig gecached) |
| Standardsprache | Abmelden / Anmelden (die Sprache wird pro Session beim Anmelden gesetzt) |

### "Wo speichert Einstellungen seine Werte?"

Hauptsächlich in `cc_pref` (Schlüssel / Wert-Tabelle).
Per-user Einstellungen (Sprache, API-Schlüssel) leben in
`cc_subjs`. Dienst-Konfiguration, die nicht in der DB
leben kann (PostgreSQL-Anmeldedaten, Dateisystem-Pfade),
lebt in `config/libretime.conf`.

### "Kann ich meine Einstellungen versionieren?"

Indirekt:

- `config/libretime.conf` ist eine Textdatei — committen
  Sie sie (nach Redaktion der Anmeldedaten).
- `cc_pref`-Zeilen werden nicht versioniert. Zum
  Sichern verwenden Sie `pg_dump --table=cc_pref`. Siehe
  [`docs/operator/BACKUP.md`](../../operator/BACKUP.md).

### "Kann ich Einstellungen aus einem Backup wiederherstellen, ohne die Datenbank zu berühren?"

Für in `cc_pref` gespeicherte Einstellungen: nur durch
Wiederherstellung der `cc_pref`-Tabelle aus dem Backup.
Für `config/libretime.conf`-Einstellungen: kopieren Sie
die Datei.

### "Warum sind einige Einstellungen nur für Super Admin sichtbar?"

Die DB-Konsole, die Fähigkeit, andere Admins zu erstellen,
und das Recht, API-Schlüssel anderer Benutzer zu sehen,
sind dem Super Admin vorbehalten, weil sie Zugriffs-
Eskalation gewähren. Siehe
[Benutzer und Rollen](./USERS_AND_ROLES.md) §1.

---

## 6. Playout-Engine (Liquidsoap)

> **Einstellung auf Service-Ebene**, keine UI-Einstellung.  Der
> NSSM-Dienst RASTATIME-PLAYOUT kann `RASTATIME_PLAYOUT_ENGINE=liquidsoap`
> in seiner Umgebung tragen; das ist der einzige zulässige Wert.  Nur
> Operator; nicht in der Web-UI exponiert.

Seit dem 2026-09-10 ist Liquidsoap die **einzige** Playout-Engine.  Die
frühere mpv-Engine (mit ihren FFmpeg-Streamern für die Icecast-Ausgänge)
und der nie fertiggestellte VLC-Plan wurden aus dem Code entfernt,
nachdem Liquidsoap seit dem 2026-05-28 jeden Sendeplan-Typ (Dateien,
Webstreams, Line-Inputs, Aufnahme, DJ-Quellen) im Produktivbetrieb
getragen hatte.

Was Liquidsoap leistet:

- **Aufnahme** wird vom internen Audio-Bus erfasst (post-switch,
  post-crossfade, post-amplify) — bit-identisch mit dem, was die Hörer
  hören.  Aufnahme-Bitrate fest 320 kbps MP3, Archivqualität.
- **Hörer-Erfahrung**: die Icecast-Mountpoints bleiben über Track-/
  Sendungswechsel offen — kein Reconnect, kein Zähler-Reset.
- **DJ-Quellen-Routing** nutzt Liquidsoaps `input.harbor` +
  `switch(...)` nativ — Master-/Show-DJ-Clients verbinden sich direkt
  mit dem von Liquidsoap verwalteten Harbor (standardmäßig Port 8001,
  siehe [Streams](./STREAMS.md)).

**Wenn der Dienst den Start verweigert** mit

```
CRITICAL __main__: RASTATIME_PLAYOUT_ENGINE='mpv' is not supported - Liquidsoap is the only playout engine since 2026-09-10 ...
```

nennt die Dienst-Umgebung noch die entfernte Engine: in der
NSSM-Umgebung von `RASTATIME-PLAYOUT` `RASTATIME_PLAYOUT_ENGINE=liquidsoap`
setzen (oder die Variable entfernen) und den Dienst erneut starten.
`RASTATIME_MPV_PATH` / `RASTATIME_MPV_LOG_LEVEL` werden ignoriert und
können entfernt werden.

**Der Engine-Start ist im Playout-Log sichtbar:**

```
INFO __main__: Playout engine: Liquidsoap (telnet target 127.0.0.1:1234).
```

---

## Wohin als Nächstes

* Folgen Sie dem Pro-Seite-Link in der Tabelle oben zu dem
  dedizierten Kapitel für jede große Einstellungsseite.
* [Benutzer und Rollen](./USERS_AND_ROLES.md) —
  Berechtigungsmatrix, die jede Einstellungsseite gatet.
* [`docs/operator/INSTALL.md`](../../operator/INSTALL.md)
  — die initialen Einstellungen, die zur Installationszeit
  konfiguriert werden.
