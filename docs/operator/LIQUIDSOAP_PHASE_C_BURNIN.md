# Liquidsoap Phase-C Burn-In — 24–48h Live-Test

> **Zweck:** validieren dass der C8-Bring-up Stand stabil über 24–48
> Stunden läuft, bevor C4 (DJ-Sources) und C5 (Recording) dazukommen.
> Ähnlich wie der Phase-A Burn-In (~12h reine Liquidsoap-Sine),
> diesmal aber mit dem **vollständigen Pypo-Push-Verkehr**: scheduled
> Tracks, Crossfades, ReplayGain, ICY-Metadata, Catch-Up-Patterns,
> drei parallele Icecast-Mounts + lokale Soundkarte.
>
> **Wenn der Burn-In durchläuft:** Phase C ist produktions-bereit,
> wir können entweder C4/C5 anhängen oder direkt Phase-D Cutover
> planen.
>
> **Wenn was schief geht:** der Guide sagt unten was du beobachten
> sollst — mit den richtigen Logs kann ich den Fehler diagnostizieren.

---

## Was getestet wird (≠ Phase A)

| Test-Punkt | Phase A (12h done) | Phase-C Burn-In (dieser Schritt) |
|---|---|---|
| Audio-Eingang | static `sine(440.)` | **echte scheduled tracks aus cc_files** (mp3) |
| Encoder-Aktivität | 1 codec | **3 codecs parallel** (mp3 + aac + opus) |
| Crossfade | nein | **ja** (`crossfade(duration=2.0, bus)`) |
| ReplayGain | nein | **ja** (`amplify(override="replaygain_track_gain", …)`) |
| ICY-Metadata-Updates | nein | **ja** (pro Track via `annotate:`) |
| Telnet-Verkehr | nein | **ja** (Pypo `scheduled.push` + deferred-stop) |
| Local Audio-Sink | nein | **ja** (`output.portaudio`) |
| Pypo-Schedule-Polling | nein | **ja** (alle 120s + auf-Demand) |

---

## Voraussetzungen

- Phase 0 + A + C1–C8 alle done (Stand 2026-05-26 13:30).
- NSSM-Service `RASTATIME-LIQUIDSOAP` ist installed + auto-start.
- Pypo läuft im Liquidsoap-Modus.
- Mindestens ein Tag voller realer Show-Schedules in der DB
  (oder du machst dir einen kleinen Test-Loop von 24h mit
  4–6 Smart-Block-getriebenen Shows).
- DJ-Workstations bleiben während des Burn-Ins **offline** —
  Phase C4 (input.harbor) ist noch nicht aktiv; Master/Show DJ
  würde aktuell über den Legacy-mpv-Pfad pushen aber das wäre
  jetzt während des Liquidsoap-Tests stumm.

---

## Schritt 1 — Burn-In starten

PowerShell (Operator-User, nicht Admin):

```powershell
# 1) Stelle sicher dass der Legacy-NSSM-Service RASTATIME-PLAYOUT
#    aus ist (würde sonst eine zweite mpv-Pypo-Instanz spawnen)
nssm stop RASTATIME-PLAYOUT

# 2) Liquidsoap-Service vorhanden + auto-start
nssm status RASTATIME-LIQUIDSOAP  # erwartet SERVICE_RUNNING
                                  # wenn nicht: nssm start RASTATIME-LIQUIDSOAP

# 3) Pypo im Liquidsoap-Modus + alles in eine Log-Datei kippen
$env:RASTATIME_PLAYOUT_ENGINE = "liquidsoap"
$env:RASTATIME_LIQUIDSOAP_LOCAL_OUTPUT = "true"
$startTime = Get-Date -Format "yyyy-MM-dd_HH-mm"
$logFile = "C:\rastatime\logs\burnin_${startTime}.log"
C:\rastatime\.venv\Scripts\python.exe -m libretime_playout *> $logFile
```

Pypo läuft jetzt im Vordergrund + schreibt alles nach `$logFile`.

**Wichtig:** terminal-Window **offen lassen**.  Wenn das Window
geschlossen wird, terminiert Pypo.  Wenn das stört: später ein zweiter
NSSM-Service `RASTATIME-PLAYOUT-LIQUIDSOAP` mit `engine_kind=liquidsoap`
env-var (= Phase D Cutover-Setup), aber dafür ist es noch zu früh.

---

## Schritt 2 — Snapshot-Skript zum Tracking

In einem **zweiten** PowerShell-Window:

```powershell
# Initial-Snapshot
$snapshotFile = "C:\rastatime\logs\burnin_snapshots.csv"
"timestamp;pypo_rss_mb;liquidsoap_rss_mb;liquidsoap_threads;icecast_clients" | Out-File $snapshotFile

# Snapshot-Funktion
function Get-BurnInSnapshot {
    $pypo = Get-Process python | Sort-Object StartTime | Select-Object -Last 1
    $ls = Get-Process liquidsoap -ErrorAction SilentlyContinue
    $stats = Invoke-WebRequest "http://localhost:8000/admin/stats.xml" `
        -Headers @{Authorization=("Basic " + [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("admin:hackme")))} `
        -ErrorAction SilentlyContinue
    $clients = if ($stats) {
        ([xml]$stats.Content).icestats.source | Measure-Object -Property listeners -Sum | ForEach-Object Sum
    } else { "?" }
    $line = "{0};{1:N1};{2:N1};{3};{4}" -f `
        (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), `
        ($pypo.WorkingSet64 / 1MB), `
        ($ls.WorkingSet64 / 1MB), `
        $ls.Threads.Count, `
        $clients
    Add-Content -Path $snapshotFile -Value $line
    Write-Host $line
}

# Eine Probe sofort, dann alle 15 min eine
Get-BurnInSnapshot
while ($true) {
    Start-Sleep -Seconds 900
    Get-BurnInSnapshot
}
```

Lass das auch durchlaufen.  Es schreibt eine CSV mit Memory + Threads
+ Listener-Count alle 15 min.  Nach 24h hast du ca. 96 Datenpunkte
zur Auswertung.

---

## Schritt 3 — Was beobachten

### A. Memory-Stabilität (wichtigstes Signal)

- **Pypo-RSS** sollte nach dem Warm-Up (~10 min) bei ca. 80–150 MB
  einpendeln.  Wachstum >50 MB/h ist ein Leak-Verdacht.
- **Liquidsoap-RSS** sollte bei ~80–200 MB einpendeln.  Phase-A hat
  ~80 MB über 12h stabil bestätigt für reines Liquidsoap; mit
  Pypo-Push-Verkehr + 3 Codecs + lokalem Output erwarte ich
  150–200 MB.  Auch hier: Wachstum >50 MB/h ist Alert.
- **Liquidsoap-Threads** sollte stabil bleiben (typisch 15–25).
  Stetiges Wachstum ⇒ Thread-Leak im scheduler oder bei Reconnects.

### B. Audio-Qualität (subjektiv über Browser)

- Mindestens 3× am Tag in den `/rastatime` Mount im Browser/VLC
  reinhören (z.B. morgens/mittags/abends).
- **Sollte zu hören sein:** kontinuierliches Audio, Crossfades
  zwischen Tracks ohne Klick, gleichmäßige Lautheit.
- **Alert-Signal:** plötzliche Stille >5s, Klicks, Doppelt-Tracks,
  Lautheits-Sprünge.

### C. Liquidsoap-Log (Filter auf Warnings/Errors)

In einem dritten PowerShell-Window:
```powershell
Get-Content C:\rastatime\logs\liquidsoap.log -Wait -Tail 30 | Where-Object { $_ -match "\[.*:[12]\]" }
```

(`[xxx:1]` = Error, `[xxx:2]` = Warning — Level 3+ ist Info+Debug.)

**Erwartet (akzeptabel):**
- `Latency is too high: must catchup N.NN seconds` — nur am Bring-up
  + ggf. nach Pypo-Track-Wechsel; sollte nach <30s wieder weg sein.
- `Error while decoding file tags: Failure("Unsynchronized headers
  not handled.")` — id3-Tag-Probleme einzelner mp3-Files, harmlos,
  FFmpeg dekodiert trotzdem.

**Alert-Signal:**
- Wiederholt `Unknown protocol URI` (= URI-Format-Bug zurück)
- Wiederholt `Connection setup was successful` + `Closing connection`
  Loops für einen Mount (= Reconnect-Storm — Icecast oder Output
  hat Probleme)
- `Avutil.Error(Invalid argument)` (= Encoder-Init-Bug)
- `decoder ended` für jeden Track innerhalb von 1-2s nach `Prepared`
  (= Tracks werden geskippt statt gespielt)

### D. Pypo-Log (Burn-In-Log-File)

Spot-Check alle 6h:
```powershell
Get-Content $logFile -Tail 100 | Where-Object { $_ -match "(ERROR|WARNING|CRITICAL)" }
```

**Akzeptabel:**
- `WARNING set_audio_device(...) called — Liquidsoap engine does not
  yet implement runtime device switching` (1× beim Start, dann nie
  mehr)
- `WARNING preflight (linein_device_unavailable)` (nur wenn kein
  Mikro angeschlossen)

**Alert:**
- `ERROR Liquidsoap rejected push for ...: ERROR: ...` (= push
  failure regression)
- `ERROR Liquidsoap play failed for ...` (= telnet down)
- `CRITICAL` irgendetwas

---

## Schritt 4 — Wenn was schief geht

### Liquidsoap-Service crashed mitten im Burn-In

NSSM restartet automatisch nach 5s (AppRestartDelay).  Pypo merkt
nichts, sendet weitere pushes ins Leere bis der Service wieder da
ist.  Mounts kommen automatisch zurück (alle output.icecast haben
`fallible=true` + Liquidsoap-Default-Reconnect).

```powershell
# Snapshot der Crash-Info VOR dem Restart (NSSM überschreibt sonst)
Copy-Item C:\rastatime\logs\liquidsoap-stderr.log C:\rastatime\logs\liquidsoap-stderr.before-crash.log
nssm status RASTATIME-LIQUIDSOAP
```

Schick mir die `*-before-crash.log` und ich diagnostiziere.

### Pypo crashed

Im Terminal Stack-Trace zu sehen.  Ctrl+C, `$logFile` an mich
schicken, Pypo neu starten.

### Audio bricht ab

Erste Diagnose: ist die Quelle aus (= keine Show scheduled, fallback
ist legitim silence) oder hat Liquidsoap aufgehört zu encoden?

```powershell
# Sind die Icecast-Mounts noch da?
Invoke-WebRequest http://localhost:8000/admin/stats.xml `
    -Headers @{Authorization=("Basic " + [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("admin:hackme")))} `
    | Select-Object -ExpandProperty Content | Select-String "mount=|listeners="

# Was sagt Liquidsoap-Telnet?
C:\rastatime\.venv\Scripts\python.exe -c @"
from libretime_playout.engine.liquidsoap_telnet import LiquidsoapTelnetClient
c = LiquidsoapTelnetClient()
print('queue:', c.send_command('scheduled.queue'))
print('mount1 status:', c.send_command('output.icecast.status'))
c.close()
"@
```

---

## Schritt 5 — Nach 24–48h: Bericht

Schreib mir:

1. **Memory-Verlauf** (CSV als Anhang oder Min/Max/Final):
   - Pypo RSS Start / nach 6h / nach 12h / nach 24h
   - Liquidsoap RSS Start / nach 6h / nach 12h / nach 24h
   - Liquidsoap Thread-Count Start / Ende
2. **Audio-Glitches**: wie viele subjektive Hör-Tests gemacht, wie
   viele Stille-Aussetzer >5s erlebt
3. **Liquidsoap-Service-Crashes**: 0 / 1 / mehr — falls >0 die
   `liquidsoap-stderr.log` Snapshots
4. **Pypo-Crashes**: 0 / 1 / mehr
5. **Auffällige Errors/Warnings** im Pypo- oder Liquidsoap-Log
6. **Listener-Count-Verhalten**: Browser/VLC blieb stabil verbunden,
   oder hat sich der Player nach N min ausgekoppelt?

Mit dem Bericht entscheiden wir gemeinsam:
- ✅ alles im grünen Bereich → Phase C ist signed-off, weiter mit
  **C5 (Recording)** oder **C4 (DJ-Sources)** oder direkt
  **Phase D (Cutover-Planung)**
- 🟡 ein Bug-Pattern aber kein Show-Stopper → Hotfix, dann
  Burn-In wiederholen mit dem Fix drin
- 🔴 Show-Stopper (z.B. Memory-Leak, Crash-Loop, Audio-Lücken
  alle paar Minuten) → Architektur-Re-Evaluation; ggf. Variante B
  (mpv bleibt, Liquidsoap nur als Output-Mixer) doch noch ziehen

---

## Aufräumen nach dem Burn-In

```powershell
# Pypo Ctrl+C
# RASTATIME-LIQUIDSOAP-Service kann weiterlaufen oder gestoppt werden
# Burn-In-Logs (burnin_*.log + burnin_snapshots.csv) ARCHIVIEREN
#   für die Phase-D Cutover-Doku als Stabilitäts-Beleg
# Bevor du wieder den Legacy-Pfad benutzen willst:
$env:RASTATIME_PLAYOUT_ENGINE = "mpv"
nssm start RASTATIME-PLAYOUT   # alter mpv-basierter Service zurück
```
