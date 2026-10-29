# Liquidsoap Phase C8 — Integration-Test gegen echte Instanz

> **Zweck:** den C1–C7 Stack (Telnet-Client + LiquidsoapEngine + .liq
> Renderer + Crossfade/ReplayGain/ICY + Pypo Auto-Render) gegen eine
> echte laufende Liquidsoap-Instanz validieren — scheduled tracks
> spielen via Liquidsoap, kreuzfaden, tragen ICY-Metadata, kommen
> durch alle 3 Icecast-Mounts.
>
> **Wenn alles klappt:** Phase C ist durch, wir gehen in C4 (DJ-
> Sources) + C5 (Recording) oder direkt in Phase D (Cutover).
>
> **Wenn ein Test schiefgeht:** der entsprechende C-Schritt bekommt
> einen Hotfix, dann C8 wiederholen.

---

## Voraussetzungen

- Phase 0 + Phase A erledigt (Liquidsoap 2.4.4 Build läuft, FFmpeg
  Codecs validiert, Memory stabil über 12h Burn-In).
- C1–C7 committed (heute, 2026-05-26).
- Mindestens **eine** Icecast stream-output-Zeile in cc_pref
  konfiguriert + enabled (Settings → Streams).
- Icecast läuft auf localhost:8000 wie üblich.

---

## Schritt 1 — NSSM-Service installieren (einmalig)

PowerShell **als Administrator**:

```powershell
cd C:\RASTATIME\backend\playout\config
.\nssm-install-liquidsoap.ps1
```

Das installiert den `RASTATIME-LIQUIDSOAP` Windows-Service.  Er
startet automatisch beim Boot, restartet sich bei Crashes, schreibt
Logs nach `C:\Tools\liquidsoap\nssm.log` (rotiert bei 10 MB).

**Verifikation:**

```powershell
nssm status RASTATIME-LIQUIDSOAP
# Sollte SERVICE_STOPPED zeigen (wir starten den erst nach dem
# Render-Schritt unten).
```

---

## Schritt 2 — Pypo im Liquidsoap-Modus starten → rendert .liq

Im **normalen User-Terminal** (kein Admin).  **Wichtig: die
Pypo-venv-Python-Executable verwenden, nicht das System-Python**
— sonst kommt `No module named rastatime_playout`:

```powershell
$env:RASTATIME_PLAYOUT_ENGINE = "liquidsoap"
C:\rastatime\.venv\Scripts\python.exe -m rastatime_playout
```

**Erwarteter Log-Output:**

```
INFO  RASTATIME-PLAYOUT: starting (libVLC engine).
INFO  Config loaded from C:\rastatime\config\rastatime.conf
INFO  Found N enabled Icecast stream output(s) — …
WARN  Rendered C:/Tools/liquidsoap/rastatime.liq (content changed).  RESTART the RASTATIME-LIQUIDSOAP NSSM service so it picks up the new .liq:   nssm restart RASTATIME-LIQUIDSOAP
INFO  Local-playback engine: Liquidsoap (Phase-C2+C3+C6 fully wired). Telnet target 127.0.0.1:1234.
INFO  API client base URL: http://127.0.0.1:8765
…
```

**Wichtig:** Pypo läuft jetzt im Liquidsoap-Modus — aber Liquidsoap
selbst noch nicht.  Das ist OK: die LiquidsoapEngine connectet lazy
beim ersten play(), und der einzige Track-Push wird scheitern bis
NSSM hochfährt (das tun wir im nächsten Schritt).

**Falls statt "Rendered …" eine "Liquidsoap config target directory
does not exist" oder "Failed to render" Fehlermeldung kommt:**
Pypo loggt die exakte Ursache + exit(1).  Häufigste Ursachen:

- `C:\Tools\liquidsoap\` existiert nicht → Phase 0 Setup
  unvollständig.
- `RASTATIME_LIQUIDSOAP_CONFIG_PATH` zeigt auf einen Pfad ohne
  Schreibrechte für das Pypo-User-Konto.

---

## Schritt 3 — Liquidsoap-Sanity-Check (optional aber empfohlen)

Bevor wir den NSSM-Service starten, prüfen wir ob die gerenderte
`rastatime.liq` syntaktisch korrekt ist:

```powershell
C:\Tools\liquidsoap\liquidsoap.exe --check C:\Tools\liquidsoap\rastatime.liq
```

**Erwartet:** keine Errors, evtl. ein paar Warnings die OK sind
(z.B. "Liquidsoap will be running with reduced privileges" — egal).

**Falls Errors:** copy-paste hierher, ich gucke rein.  Mögliche Ursachen:
- Eine `cc_pref.stream_output_N` Zeile hat unerwartete Felder
- Crossfade-Duration ist negativ oder NaN (sollte float sein)
- Liquidsoap-Build kennt einen Operator nicht (z.B. wenn der
  Burn-In-Build älter als 2.4.x ist)

---

## Schritt 4 — NSSM-Service starten

```powershell
nssm start RASTATIME-LIQUIDSOAP
```

Etwa 3–5 Sekunden warten, dann verifizieren:

```powershell
nssm status RASTATIME-LIQUIDSOAP
# Sollte SERVICE_RUNNING zeigen.
```

**Live-Log mitlesen (in eigenem Terminal):**

```powershell
Get-Content C:\rastatime\logs\liquidsoap.log -Wait -Tail 30
```

**Erwarteter Log-Output (innerhalb 5–10s):**

```
[main:3] Liquidsoap 2.4.4
[main:3] User script loaded in X seconds.
[server:3] Listening on 127.0.0.1:1234
[output.icecast(/rastatime):3] Connection setup was successful.
…
```

Wenn 3 stream-outputs in cc_pref konfiguriert sind, sollten 3 mal
"Connection setup was successful" für 3 verschiedene Mountpoints
kommen.

**Falls "Connection refused" für einen Mount:**
- Icecast läuft nicht oder Mount-Passwort stimmt nicht
- Liquidsoap retried alle 5s (restart_delay=5.) — sollte sich
  automatisch verbinden sobald Icecast greifbar
- Im Browser kannst du jederzeit den Mount-Zustand prüfen:
  `http://localhost:8000/admin/stats.xml`

---

## Schritt 5 — Test-Track schedulen + hören

Im Dashboard:
1. Eine **leere Show** anlegen (Now or +5 min, Dauer ~5 min)
2. Eine **Smart Block** oder **Playlist** mit 2–3 kurzen Tracks
   reinziehen
3. Show speichern, warten bis sie startet

**Pypo-Log beobachten** (parallel im ersten Terminal):
```
INFO  Liquidsoap play: uri=file:///C:/rastatime/media/.../580.mp3 cue_in=0.00s cue_out=natural gain=-5.95dB meta=title='Song Title',artist='Band Name',show_name='Test Show'
DEBUG Liquidsoap accepted request_id=42 for file:///C:/rastatime/media/.../580.mp3
```

**Browser-Test:**
```
http://localhost:8000/rastatime
```
(oder welche Mounts du in cc_pref konfiguriert hast.)

**Hörbare Verifikation:**
- [ ] Audio kommt durch (kein Schweigen, kein Crackle).
- [ ] Bei Track-Wechsel: **Crossfade** ist deutlich hörbar (2.0 s
      default — wenn anders gewünscht: env-var
      `RASTATIME_LIQUIDSOAP_CROSSFADE_SECONDS=…`).
- [ ] Lautheit zwischen Tracks **gleichmäßig** (ReplayGain).  Wenn
      Tracks unterschiedlich laut sind: prüfe `cc_files.replay_gain`
      Werte für die getesteten Files.
- [ ] **ICY-Title** im Browser/VLC sichtbar: zeigt `<Artist> — <Title>`
      (oder ähnliches Format je nach Client).

---

## Schritt 6 — Was C8 NICHT testet

C8 deckt nur den **scheduled-tracks-Pfad** ab — das was C1+C2+C3+C6
liefern.  Folgendes braucht noch C4 / C5:

- **DJ-Sources (Master/Show)**: Phase C4 — input.harbor im .liq
  + Pypo source_switcher Umstellung auf telnet `var.set`.
  In C8 noch via mpv im Legacy-Pfad (gleichzeitig laufende
  Engine).  **Vorsicht** wenn ein DJ während des C8-Tests
  connectet — der mpv-DJ-Listener kollidiert ggf. mit der
  Liquidsoap-Audio-Ausgabe.  Saubere Workaround:
  C8-Test in einer Slot wo kein DJ angekündigt ist.
- **Recording**: Phase C5 — output.file im .liq mit reopen-on-
  show-boundary.  In C8 noch via Legacy FfmpegRecorder.
- **Webstream-Events**: Funktionieren über die LiquidsoapEngine
  (URI wird über `request.queue.push http://…` gepusht), aber
  C8 fokussiert auf File-Events weil ICY-Metadata vom Stream
  selbst kommt (nicht aus cc_*).

---

## Schritt 7 — Aufräumen + Bericht

**Wenn alles klappt:**
```powershell
# Pypo Ctrl+C
# nssm stop RASTATIME-LIQUIDSOAP  (optional — service kann ruhig
#                                  laufen, leakt im idle <1 MB/h)
```

Schreib mir bitte:
1. **Hat der Render-Schritt geklappt?**  ja / nein + Log
2. **Hat liquidsoap.exe --check sauber durchgelaufen?**  ja / nein
3. **Sind alle Icecast-Mounts verbunden?**  Anzahl
4. **Audio im Browser hörbar?**  ja / nein für jeden Mount
5. **Crossfade hörbar?**  ja / nein + Dauer-Schätzung
6. **ReplayGain wirkt?**  ja / nein (subjektiv ausreichend)
7. **ICY-Title im Browser?**  ja / nein
8. **Auffällige Errors im Pypo-Log oder liquidsoap.log?**

Daraus mache ich entweder das Phase-C-Sign-off oder fixe was nicht
geht.

**Wenn nichts klappt** (z.B. Liquidsoap stürzt sofort ab): wir
gehen schrittweise zurück — erst Pypo-Engine ohne render-Schritt
isoliert testen (mit der Phase-A-POC .liq), dann inkrementell die
neuen Features dazuschalten.

---

## Aufräumen nach Phase C8

```powershell
$env:RASTATIME_PLAYOUT_ENGINE = "mpv"  # zurück auf legacy default
nssm stop RASTATIME-LIQUIDSOAP         # optional, idle ist OK
```

Die gerenderte `C:\Tools\liquidsoap\rastatime.liq` darf liegen
bleiben — Pypo regeneriert sie bei jedem nächsten Liquidsoap-Start.
