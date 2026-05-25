# Liquidsoap Phase A — POC + 4 h Burn-In

> **Zweck:** dein Liquidsoap-Build mit dem **echten Production-
> Encoder** (MP3 via FFmpeg) gegen einen separaten Test-Mountpoint
> 18 Stunden lang dauerlaufen lassen.  Erfolgsmesser: läuft noch,
> Memory stabil (kein Leak), Browser/VLC kann den Mount jederzeit
> abspielen.

---

## Was Phase A testet (jenseits von Phase 0)

| | Phase 0 (✅ erledigt) | Phase A (dieser Schritt) |
|---|---|---|
| Encoder | WAV (kein echter Codec) | **MP3 via FFmpeg** (Production-Format) |
| Dauer | 45 Sek Smoke-Test | **4 h Dauerlauf** |
| Browser-Playback | ❌ (WAV-Stream nicht abspielbar) | ✅ erwartet — direkt im Browser abspielbar |
| Memory-Profil | nicht messbar | über 4 h beobachten |
| Cache aktiv | ❌ (`./cache: Permission denied`) | ✅ (explizit konfiguriert) |

---

## Schritt 1 — POC-Script anlegen

PowerShell:

```powershell
$content = "phase_a_src = sine(440.)`r`noutput.icecast(%ffmpeg(format=`"mp3`", %audio(codec=`"libmp3lame`", b=`"128k`")), host=`"localhost`", port=8000, password=`"admin`", mount=`"/phase-a-test.mp3`", name=`"Liquidsoap Phase-A POC`", description=`"4h burn-in test`", phase_a_src)"
[System.IO.File]::WriteAllText('C:\Tools\liquidsoap\phase-a-poc.liq', $content, [System.Text.UTF8Encoding]::new($false))
```

Sanity-Check:

```powershell
C:\Tools\liquidsoap\liquidsoap.exe --check C:\Tools\liquidsoap\phase-a-poc.liq
```

Erwartet: keine Errors, keine Warnings.

**Falls `libmp3lame` nicht eingebunden ist** (würde sich als Runtime-Error
zeigen, ähnlich wie Vorbis in Phase 0): Fallback ohne expliziten
Codec (FFmpeg deduziert dann den Default-MP3-Codec):

```powershell
$content = "phase_a_src = sine(440.)`r`noutput.icecast(%ffmpeg(format=`"mp3`"), host=`"localhost`", port=8000, password=`"admin`", mount=`"/phase-a-test.mp3`", name=`"Liquidsoap Phase-A POC`", description=`"4h burn-in test`", phase_a_src)"
[System.IO.File]::WriteAllText('C:\Tools\liquidsoap\phase-a-poc.liq', $content, [System.Text.UTF8Encoding]::new($false))
```

## Schritt 2 — Start mit korrektem current-dir + Log-File

Aus `C:\Tools\liquidsoap\` starten (damit der Cache schreibbar ist),
Output in eine Log-Datei umleiten (damit du nach 4 h zurückschauen
kannst):

```powershell
cd C:\Tools\liquidsoap
.\liquidsoap.exe .\phase-a-poc.liq *>&1 | Tee-Object -FilePath .\phase-a-burnin.log
```

`Tee-Object` schreibt parallel auf Bildschirm UND in die Log-Datei
— du siehst live was passiert und hast trotzdem die volle Historie.

**Erwartete Startup-Logs:**

```
[main:3] Liquidsoap 2.4.4
[main:3] User script loaded in X seconds.
[output.icecast(...):3] Content type is {audio=pcm(stereo)}.
[output.icecast(...):3] Connecting mount /phase-a-test.mp3 for source@localhost...
[output.icecast(...):3] Connection setup was successful.
```

**Browser-Test sofort:** `http://localhost:8000/phase-a-test.mp3`
→ durchgehender 440-Hz-Sinus sollte hörbar sein.

## Schritt 3 — Burn-In-Monitoring (4 h)

Alle ~3–4 Stunden mal kurz in einer **zweiten** PowerShell prüfen
(Liquidsoap im Original-Terminal weiterlaufen lassen):

**A. Läuft der Prozess noch?**
```powershell
Get-Process liquidsoap -ErrorAction SilentlyContinue | Select-Object Id, ProcessName, WorkingSet, StartTime
```

`WorkingSet` ist der RAM-Verbrauch in Bytes.  Notier dir den Wert.

**B. Ist der Mount noch verbunden?**
```powershell
Invoke-WebRequest http://localhost:8000/admin/stats.xml -Headers @{Authorization=("Basic " + [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("admin:admin")))} | Select-Object -ExpandProperty Content | Select-String "phase-a-test"
```

(Tausche `admin:admin` falls dein Admin-Login anders heißt.)

**C. Browser-Spot-Check:** alle paar Stunden den `phase-a-test.mp3`-
Mount im Browser oder VLC kurz öffnen — Audio muss durchlaufen.

## Schritt 4 — Burn-In stoppen (nach 4 h)

Im Original-Terminal `Ctrl+C`.

**Saubere Shutdown-Logs sollten sein:**
```
[main:3] Shutdown signal received.
[output.icecast(...):3] Closing connection...
[threads:3] Main threads terminated.
[threads:3] Shutting down scheduler...
```

## Schritt 5 — Bericht

Schreib mir bitte:

1. **WorkingSet-Werte über die Zeit:** Start vs. nach 4 h / 8 h /
   12 h / 4 h.  Wachstum von < 10 MB über 4 h = sehr gut.
   Wachstum von > 100 MB über 4 h = Memory-Leak, würde Phase B
   blockieren.
2. **Browser-Playback durchgehend OK?**  Wenn irgendwann
   Aussetzer oder kein Audio mehr — exakter Zeitpunkt + ob
   Mount-Stats sagen Connection ist gestorben.
3. **Sauberer Shutdown?**  Oder hat Liquidsoap auf Ctrl+C
   gehangen?
4. **Volle Log-Datei** (`C:\Tools\liquidsoap\phase-a-burnin.log`)
   überfliegen — auffällige Warnings/Errors die nicht beim
   normalen Start kommen?  Wenn ja: copy-paste die Zeilen, ich
   schaue rein.

Sobald positiv → Phase B (LiquidsoapEngine Python-Adapter).
Wenn Memory-Leak / Crash / Hänger → wir entscheiden ob anderer
Build oder andere Strategie.

---

## Aufräumen nach Phase A

```powershell
# Liquidsoap stoppen (Ctrl+C im Original-Terminal)
# Log-File behalten (phase-a-burnin.log) als Referenz
# Mount /phase-a-test.mp3 verschwindet automatisch
```

Der `phase-a-poc.liq`-Script bleibt liegen — wir bauen Phase B
darauf auf (mit Telnet-Server + Source-Queue statt Sine).
