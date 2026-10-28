# Liquidsoap Phase 0 — Sanity-Test auf Windows-Server

> **Zweck:** verifizieren dass Liquidsoap auf deinem Windows-
> Server überhaupt installierbar ist und einen Trivial-Test-Stream
> stabil über mindestens ein paar Stunden hält, bevor wir mit der
> eigentlichen Migration (Phase A–D, 6–8 Wochen) beginnen.
>
> **Wenn dieser Test scheitert:** Stopp.  Wir reevaluieren — z.B.
> Voll-Migration verwerfen und zurück zur Variante B (inkrementell,
> mpv bleibt, Liquidsoap nur als Output-Mixer).
>
> **Wenn dieser Test klappt:** Ergebnis festhalten, dann starten wir
> Phase A (POC mit echtem Input).

---

## Vorab — Windows-Edition prüfen (nur bei N-Editionen relevant)

Auf Windows 11 / 10 **N-Editionen** (EU-Spezial-Versionen ohne
Multimedia-Komponenten) fehlen die System-Codecs für MP3 / AAC
etc.  Liquidsoap selbst nutzt eigene FFmpeg-Libraries — funktioniert
also auch ohne — aber **Browser- und VLC-Tests** verwenden oft
System-Codecs für inline-Playback, und ohne installiertes
Media Feature Pack können diese Tests fälschlich als "Liquidsoap-
Bug" interpretiert werden.

**Vor Phase 0 — falls N-Edition:** [Media Feature Pack für
Windows 11](https://support.microsoft.com/de-de/topic/media-feature-pack-list-for-windows-n-editions-c1c6fffa-d052-8338-7a79-a4bb980a700a) installieren.
Standard-Editionen haben das schon eingebaut.

(Operator-Erfahrung 2026-05-25 — frühe VLC-Connect-Fehler ließen
sich nach MFP-Installation klar erklären.)

## Schritt 1 — Liquidsoap-Build downloaden

Aktuell stabil: **Liquidsoap 2.2.x** (oder neuer wenn verfügbar).

Offizielle Windows-Builds:
- https://github.com/savonet/liquidsoap/releases
- Suche nach dem aktuellsten Release mit Asset-Name
  `liquidsoap-…-x86_64-w64-mingw32.zip` (oder ähnlich)

Entpacken nach:
```
C:\rastatime\liquidsoap\
```

Im Ziel-Ordner sollte `liquidsoap.exe` direkt liegen.

## Schritt 2 — Smoke-Test: Version + Help

PowerShell (oder cmd) in `C:\rastatime\liquidsoap\`:

```powershell
.\liquidsoap.exe --version
.\liquidsoap.exe --help | Select-Object -First 30
```

**Erwartet:**
- Version-Output (z.B. `Liquidsoap 2.2.5`)
- Help-Output mit Optionen-Liste

**Wenn:** `liquidsoap.exe ist keine ausführbare Win32-Anwendung`
oder DLL-Fehler beim Start → das Build passt nicht zu deinem
Windows.  Anderes Asset versuchen oder per opam-windows aus
Source bauen.

## Schritt 3 — Trivial-.liq-Script

Datei `C:\rastatime\liquidsoap\phase0-test.liq`:

```liquidsoap
# Phase-0 Sanity-Test — wirklich nur das Minimum
#
# Spielt eine konstante 440-Hz-Sinuswelle aus und schickt sie
# an Icecast.  Wenn das stabil läuft, ist der OCaml-Runtime-
# Stack auf diesem Windows-Server grundsätzlich funktionsfähig.

# Source: 1 kHz Sinus (kein File, kein Netz — pure Generator)
source = sine(440.)

# Eine Mp3-Verbindung zum lokalen Icecast.
# Mountpoint /phase0-test damit wir den Produktiv-rastatime-Mount
# nicht stören.
output.icecast(
  %mp3(bitrate=128),
  host = "localhost",
  port = 8000,
  password = "hackme",          # ← deine Icecast source-password
  mount = "/phase0-test",
  name = "Liquidsoap Phase-0 Test",
  description = "Sanity test — should produce a continuous tone",
  source
)
```

**Wichtig:** Icecast-Source-Password aus deiner
`C:\rastatime\icecast.xml` (siehe `<authentication>
<source-password>...</source-password></authentication>` im
relevanten Mount oder im globalen Block) eintragen.

## Schritt 4 — Starten

PowerShell:

```powershell
cd C:\rastatime\liquidsoap
.\liquidsoap.exe phase0-test.liq
```

**Erwartet:**
- Stdout zeigt Lade-Logs, dann z.B.:
  ```
  [main:3] Connecting mount /phase0-test for source@localhost...
  [main:3] Connection setup was successful.
  ```
- Im Browser (oder VLC) `http://localhost:8000/phase0-test`
  öffnen → durchgehender 440-Hz-Ton sollte hörbar sein.

**Wenn Liquidsoap crashed** (SIGSEGV, OCaml-Stack-Dump, sofortige
Beendigung): Build ist instabil auf deinem Setup → STOP.

## Schritt 5 — Burn-In (mindestens 2 Stunden, idealerweise 24h)

Liquidsoap laufen lassen, gelegentlich (alle ~30 min) prüfen:
- läuft `liquidsoap.exe` noch im Task-Manager?
- Memory-Verbrauch stabil oder wächst es kontinuierlich?
- Test-Mount `/phase0-test` weiterhin abspielbar?

## Schritt 6 — Ergebnis festhalten

Schreib in einem kurzen Satz:

- **Klappt:** "Liquidsoap-Version X läuft seit Y Stunden stabil,
  Memory bei Z MB."  → wir gehen direkt in Phase A.
- **Klappt teilweise:** "Liquidsoap startet, aber [Problem]."  →
  wir gucken zusammen warum.
- **Klappt nicht:** "Liquidsoap startet nicht / crashed / etc."
  → wir reevaluieren ob wir zur Variante B umschwenken oder
  ganz bei mpv bleiben.

---

## Aufräumen nach Phase 0

Egal wie der Test ausgeht:

```powershell
# Liquidsoap stoppen (Ctrl+C im Terminal)
# Test-Script behalten, wir brauchen es als Basis für Phase A
```

Den Mount `/phase0-test` in Icecast sollte verschwinden sobald
Liquidsoap beendet ist (Auto-Cleanup).
