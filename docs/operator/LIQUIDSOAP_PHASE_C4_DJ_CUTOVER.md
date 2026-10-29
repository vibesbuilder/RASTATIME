# Liquidsoap Phase C4 — DJ-Source-Cutover (BUTT/Mixxx)

> **Zweck:** DJ-Workstations (BUTT / Mixxx / b.u.t.t. / anderes
> Streaming-Tool) von den Legacy-Icecast-Source-Mounts auf die neuen
> Liquidsoap `input.harbor`-Mounts umstellen.
>
> **Voraussetzung:** Phase C4 Teil 1 ist deployed (Commit `ebf424b`
> oder neuer). Das Liquidsoap-Script `rastatime.liq` enthält jetzt
> `input.harbor("main", port=8001, ...)` und `input.harbor("show",
> port=8002, ...)` Blöcke.
>
> **Wenn dieser Schritt klappt:** Phase C4 Teil 1 ist live-validiert.
> Pypo source_switcher (Teil 2) folgt danach für saubere
> Dashboard-Integration.
>
> **Wenn was schief geht:** Roll-Back ist trivial — DJ-Workstation
> auf alten Port (8000, Icecast-Mounts) zurückstellen, Live-Betrieb
> läuft unverändert über die Legacy-Schiene weiter.

---

## Was sich konkret ändert

| | Vorher (Icecast Source-Mount) | Nachher (Liquidsoap input.harbor) |
|---|---|---|
| **Server** | localhost | localhost |
| **Port (Master DJ)** | 8000 | **8001** |
| **Port (Show DJ)** | 8000 | **8001** *(gleicher Port wie Master)* |
| **Mount (Master)** | `/main` | `/main` (gleich) |
| **Mount (Show)** | `/show` | `/show` (gleich) |

> **Wichtig zur Port-Wahl:** Operator-Decision 2026-05-25 war Master=8001
> und Show=8002 auf getrennten Ports. **Aber:** Phase-C4-Reality-Test
> 2026-05-27 hat einen Liquidsoap-2.4.4-Bug aufgedeckt — zwei
> `input.harbor` Calls mit verschiedenen Ports kommen nur einer
> wirklich hoch (das andere mount registriert silent ohne
> Verbindungen anzunehmen). Workaround: **beide Mounts auf demselben
> Port 8001**. Liquidsoap unterstützt das nativ (wie Icecast mit
> mehreren Mount-Paths auf Port 8000). Show wird also auch auf
> **Port 8001** mit Mount `/show` connectet.
| **Username** | `source` (default) | `source` (default — egal, input.harbor ignoriert username) |
| **Passwort** | aus `icecast.xml` `<source-password>` der jeweiligen Mount | aus `rastatime.conf` `stream.harbor.{main,show}_password` |
| **Format** | mp3 / aac / ogg / opus | gleich (Liquidsoap-Encoder akzeptiert was BUTT/Mixxx sendet) |
| **Bitrate** | unverändert | unverändert |

Nur die **Port-Nummer** und das **Passwort** ändern sich. Mount-Pfad
und Format bleiben gleich, damit DJs nicht ihre gesamte Streaming-
Software-Konfiguration neu denken müssen.

---

## Schritt 1 — Server-seitige Vorbereitung (einmalig)

### A. Passwörter in `rastatime.conf` setzen

Im Editor (PowerShell-elevated):

```powershell
notepad C:\rastatime\config\rastatime.conf
```

Die `stream:`-Sektion erweitern um:

```yaml
stream:
  # ... existing internal_listener etc. ...
  internal_listener:
    user: rastatime-playout
    password: change-me-internal-listener-secret

  # NEU — Phase C4 (Liquidsoap input.harbor)
  # WICHTIG: die spitzen Klammern unten sind PLATZHALTER, NICHT Teil des
  # Passworts.  Beispiel-Eintrag korrekt:
  #     main_password: ABC123XYZ-something-secret
  # NICHT:
  #     main_password: <ABC123XYZ-something-secret>
  harbor:
    main_password: <DEIN-MAIN-SOURCE-PASSWORT-HIER>
    show_password: <DEIN-SHOW-SOURCE-PASSWORT-HIER>

  inputs:
    main:
      # ... bestehende main-Sektion ...
```

**Passwort-Empfehlung:** lange Zufalls-Strings (z.B.
`[Convert]::ToBase64String((New-Object Random).NextBytes((New-Object byte[] 24)))`
oder ein Passwort-Manager). Die werden nur Machine-to-Machine
verwendet — kein Mensch tippt sie ein.

Speichern.

### B. Pypo neu starten — rendert `rastatime.liq` mit den input.harbor-Blöcken

```powershell
# Wenn Pypo unter dem RASTATIME-PLAYOUT NSSM-Service läuft
nssm restart RASTATIME-PLAYOUT
# Oder, wenn Pypo manuell im Liquidsoap-Modus läuft:
# Ctrl+C im Pypo-Fenster, dann:
$env:RASTATIME_PLAYOUT_ENGINE = "liquidsoap"
$env:RASTATIME_LIQUIDSOAP_LOCAL_OUTPUT = "true"
C:\rastatime\.venv\Scripts\python.exe -m rastatime_playout *> C:\rastatime\logs\pypo.log
```

Im Pypo-Log sollte zeigen:
```
INFO  Liquidsoap input.harbor enabled: main=yes show=yes
WARN  Rendered C:\Tools\liquidsoap\rastatime.liq (content changed). RESTART the RASTATIME-LIQUIDSOAP NSSM service...
```

### C. Liquidsoap-Sanity-Check + NSSM-Restart

```powershell
& "C:\Tools\liquidsoap\liquidsoap.exe" --check C:\Tools\liquidsoap\rastatime.liq
# erwartet: keine Fehler

nssm restart RASTATIME-LIQUIDSOAP
nssm status RASTATIME-LIQUIDSOAP   # erwartet: SERVICE_RUNNING

Get-Content C:\rastatime\logs\liquidsoap.log -Tail 30
```

Erwartete neue Log-Zeilen:
```
[harbor:3] Opening port 8001 for input mounts
[harbor:3] Opening port 8002 for input mounts
[master_dj:3] Content type is {audio=pcm(stereo)}.
[show_dj:3] Content type is {audio=pcm(stereo)}.
[switch:3] Switch to scheduled with transition.   # weil noch kein DJ connected
```

Wenn das alles steht: **Server ist bereit für DJ-Connects.**

---

## Schritt 2 — BUTT (Broadcast Using This Tool) umstellen

Auf jeder Master-DJ-Workstation:

1. **BUTT öffnen**.
2. **Settings → Add → Streaming**.
3. **Neuen Stream-Eintrag anlegen** (alten erst mal stehen lassen für Roll-Back):
   - **Name:** `RASTATIME-Master-Liquidsoap`
   - **Server type:** **Icecast** (Liquidsoap input.harbor spricht das Icecast-Source-Protokoll)
   - **Server address:** IP-Adresse deines RASTATIME-Servers (z.B. `192.168.1.192`) bzw. `localhost` wenn BUTT auf der gleichen Box läuft
   - **Server port:** `8001` ← **wichtig, NICHT 8000!**
   - **Mount point:** `main` (ohne führenden `/`)
   - **Username:** `source` (Default — input.harbor ignoriert das eigentlich)
   - **Password:** `<dein-main_password aus rastatime.conf>`
   - **Bitrate:** wie bisher (z.B. 192 kbps)
   - **Format:** MP3 (oder was bisher)
4. **Save**.
5. **Diesen neuen Stream als aktiv markieren**, alten "RASTATIME-Master" temporär deaktivieren.

Für **Show-DJ analog**, nur:
- Name: `RASTATIME-Show-Liquidsoap`
- Port: `8002`
- Mount point: `show`
- Password: `<dein-show_password>`

---

## Schritt 3 — Mixxx umstellen

Auf jeder DJ-Workstation mit Mixxx:

1. **Mixxx öffnen**.
2. **Preferences → Live Broadcasting**.
3. **New Connection** (alten stehen lassen für Roll-Back).
4. Felder ausfüllen:
   - **Connection name:** `RASTATIME-Master-Liquidsoap` (oder Show analog)
   - **Type:** **Icecast 2**
   - **Host:** IP des RASTATIME-Servers
   - **Mount:** `/main` (mit führendem `/`, Mixxx-Konvention)
   - **Port:** `8001` (Master) bzw. `8002` (Show)
   - **Login:** `source`
   - **Password:** `<main_password>` bzw. `<show_password>`
   - **Stream name / website / description:** wie bisher
   - **Stream public:** wie bisher
   - **Format:** MP3
   - **Bitrate:** wie bisher
5. **OK / Apply**.

---

## Schritt 4 — Live-Test

1. **DJ-Workstation: Streaming starten** in BUTT/Mixxx.
2. **Liquidsoap-Log mitlesen** (auf dem RASTATIME-Server):
   ```powershell
   Get-Content C:\rastatime\logs\liquidsoap.log -Wait -Tail 30
   ```
3. **Erwartete Zeilen direkt nach DJ-Connect:**
   ```
   [harbor:3] Connected user source as source on mount main
   [master_dj:3] New session, format = audio/mpeg
   [switch:3] Switch to master_dj with transition.
   [cross:3] Analysis: ... (... / ...)
   ```
4. **Browser-Test:** `http://localhost:8000/rastatime` öffnen — die
   DJ-Audio sollte sofort statt der scheduled tracks hörbar sein.
   Falls aktuell ein scheduled track lief, blendet Liquidsoap mit
   2 s Crossfade.
5. **Lokal-Soundkarten-Test:** an deiner Studio-Soundkarte ist die
   DJ-Audio auch über `output.portaudio` zu hören.
6. **Disconnect-Test:** in BUTT/Mixxx auf "Stop" — Liquidsoap-Log
   zeigt:
   ```
   [harbor:3] Closing connection of mount main
   [switch:3] Switch to scheduled with transition.
   ```
   und der scheduled track läuft sofort wieder weiter.

---

## Schritt 5 — Was C4 Teil 1 (Server-Backend) noch NICHT abdeckt

Diese Punkte folgen mit **C4 Teil 2** (Pypo source_switcher) — bis dahin
sind sie kosmetisch / nicht-blockierend:

- **Dashboard "Master Source / Show Source" Indikator** im RASTATIME-UI
  wird beim Liquidsoap-Modus **nicht aktualisiert** wenn DJ connectet.
  Der eigentliche Audio-Switch passiert trotzdem korrekt auf
  Liquidsoap-Seite (du hörst die DJ-Audio im Stream + lokal).
- **Pypo's `_on_file_start` hold-back** funktioniert noch nicht
  liquidsoap-aware: Pypo pusht weiter scheduled tracks in die queue
  während DJ live ist. Diese tracks landen aber harmlos im
  scheduled-source der vom switch nicht aktiviert wird. Wenn DJ
  disconnectet, ist die queue mit aufgestauten Tracks gefüllt und
  spielt sie sequenziell → das wäre ein Problem für lange
  DJ-Sessions (mehrere Tracks "verloren"). C4 Teil 2 fixt das.
- **HistoryService Live-Show-Logging** vom DashboardController-Hook
  triggert noch über den alten Icecast-Source-Polling — funktioniert
  also nicht für Liquidsoap-Harbor-Connects. C4 Teil 2 fixt das.

**Heißt:** für reine **Hör-Tests** und **kurze DJ-Sessions** ist C4
Teil 1 produktiv-tauglich. Für **vollständige Production-Use** (länger
laufende DJ-Sessions mit allen Dashboard-Reaktionen) brauchst du
C4 Teil 2.

---

## Roll-Back

**Wenn die Umstellung schief geht** (Audio kommt nicht durch,
Liquidsoap stürzt ab, Mixxx weigert sich):

1. **In BUTT/Mixxx:** Stream auf alten Eintrag zurückwechseln
   (Port 8000, Icecast-Mounts).
2. **Auf dem Server:**
   ```powershell
   # rastatime.conf: stream.harbor.*_password Werte LEER setzen oder Sektion löschen
   notepad C:\rastatime\config\rastatime.conf
   # Pypo restart -> rendert .liq ohne input.harbor blocks
   nssm restart RASTATIME-PLAYOUT
   # NSSM Liquidsoap restart
   nssm restart RASTATIME-LIQUIDSOAP
   ```
3. Du bist wieder auf C3-Stand (scheduled only, kein DJ-Source).
4. **Bericht** an mich was schief ging — Log-Snippets aus
   `C:\rastatime\logs\liquidsoap.log` und `pypo.log` für die
   Zeit des Fail-Versuchs.

---

## Bericht-Template nach erfolgreichem Cutover

Schick mir kurz:

1. **Liquidsoap-Log-Snippet** um den ersten DJ-Connect herum
   (insbesondere `[harbor:3] Connected user ...` + `Switch to
   master_dj`).
2. **DJ-Software die ihr nutzt** (BUTT version / Mixxx version / etc.).
3. **Hörbar im Webstream?** ja / nein
4. **Hörbar lokal über Soundkarte?** ja / nein
5. **Switch zurück auf scheduled nach Disconnect klappt?** ja / nein
6. **Crossfade beim Source-Switch hörbar?** ja / nein (sollte sein —
   `track_sensitive=true` im switch wartet auf Track-Ende, aber
   der `crossfade(duration=2.0, bus)` downstream macht den 2-s-Fade)

Mit dem Bericht plane ich C4 Teil 2 zielgerichtet.
