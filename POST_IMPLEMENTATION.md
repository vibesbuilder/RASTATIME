# POST_IMPLEMENTATION.md — Nächste Schritte nach M25

**Erstellt:** 2026-05-03  
**Stand:** Milestone M25 abgeschlossen — 925/996 Tests grün, 0 fehlgeschlagen  
**Zweck:** Vollständiger Fahrplan zum Betrieb und zur GitHub-Veröffentlichung

---

> ## ⚠️ HISTORISCHES DOKUMENT — teilweise überholt (Hinweis 2026-05-31)
>
> Dieser Fahrplan stammt vom **2026-05-03** und beschreibt die damalige
> **VLC-zentrierte** Engine-Planung. Die Architektur hat sich seitdem
> grundlegend geändert:
>
> - **Liquidsoap ist seit 2026-05-28 (Phase-C5) die Produktions-Engine**,
>   NICHT VLC. mpv war der Legacy-Fallback und wurde am 2026-09-10 gelöscht;
>   VLC ist ein aufgegebener Plan (aus dem Code entfernt). Maßgeblich:
>   `docs/manual/SETTINGS.md` §6 + `docs/operator/LIQUIDSOAP_CUTOVER.md`.
> - **VLC ist KEINE Voraussetzung** mehr (der VLC-Installationsschritt in
>   T-OP-1 unten ist obsolet).
> - **⛔ T-GH-1 ist UNGÜLTIG und darf NICHT ausgeführt werden** — es würde
>   die heute produktive Liquidsoap-Engine löschen.
>
> Die operativen Schritte (DB, Services, GitHub) bleiben als historische
> Referenz erhalten; vor Ausführung gegen die aktuelle Doku abgleichen.

---

## Teil 1 — RASTATIME auf diesem Windows 11 in Betrieb nehmen

> **Priorität: Hoch.** Die Tests beweisen, dass der Code korrekt ist — sie
> beweisen nicht, dass RASTATIME *läuft*. Die folgenden Schritte sind rein
> operativ und sequenziell abhängig voneinander.

---

### T-OP-1 — Voraussetzungen prüfen und fehlende installieren

**Was zu tun ist:**  
Prüfe mit PowerShell, welche der vier Voraussetzungen schon vorhanden sind.
Installiere alle fehlenden manuell (Download-Links unten) und bestätige
danach jede einzelne per Versionsprüfung.

**Prüfbefehle:**
```powershell
python --version                        # Braucht: 3.11+  (ist: 3.13 ✓)
pg_isready -h localhost -p 5432         # Braucht: PostgreSQL 17 laufend
& "C:\Program Files\VideoLAN\VLC\vlc.exe" --version 2>&1 | Select -First 1
                                        # Braucht: VLC 3.x 64-bit
nssm version                            # Braucht: NSSM 2.24+
```

**Download-Quellen (falls fehlend):**
- PostgreSQL 17: https://www.postgresql.org/download/windows/
- VLC 64-bit: https://www.videolan.org/vlc/download-windows.html
- NSSM: https://nssm.cc/download

**Abnahmekriterium:** Alle vier Befehle geben eine Versionsnummer zurück
ohne Fehler. `pg_isready` antwortet mit `accepting connections`.

---

### T-OP-2 — Linux-Abhängigkeiten aus requirements.txt entfernen

**Was zu tun ist:**  
Zwei `requirements.txt`-Dateien enthalten noch Linux-spezifische Pakete,
die auf Windows nicht installierbar sind. Diese müssen vor dem `pip install`
entfernt werden.

**Betroffene Zeilen:**
```
backend/api/requirements.txt       Zeile 8:   gunicorn>=22.0.0,<23.1
backend/worker/requirements.txt    Zeile 3:   celery==4.4.7
```

**Was zu tun ist (the coding assistant):**
1. `gunicorn`-Zeile aus `backend/api/requirements.txt` entfernen
2. `celery`-Zeile aus `backend/worker/requirements.txt` entfernen
3. Sicherstellen, dass kein anderes `requirements.txt` diese Pakete listet
4. 10 Tests schreiben, die bestätigen: keines der beiden Pakete erscheint
   mehr in einem `requirements.txt` im Repo

**Abhängigkeit:** Muss vor T-OP-3 erledigt sein.

**Abnahmekriterium:** `grep -r "gunicorn\|celery" backend/*/requirements.txt`
liefert keine Treffer. Suite weiterhin grün.

---

### T-OP-3 — Python-Venv anlegen und alle Pakete installieren

**Was zu tun ist:**  
Erzeuge das produktive Venv unter `C:\rastatime\.venv` und installiere alle
Backend-Pakete. Danach prüfe, ob die wichtigsten Imports funktionieren.

**Befehle:**
```powershell
cd C:\rastatime
python -m venv .venv
.venv\Scripts\Activate.ps1

pip install -r backend\shared\requirements.txt
pip install -r backend\api\requirements.txt
pip install -r backend\playout\requirements.txt
pip install -r backend\worker\requirements.txt
pip install -r backend\analyzer\requirements.txt

# Smoke-Import-Test:
python -c "import django; import waitress; import vlc; print('OK')"
```

**Abnahmekriterium:** `python -c "import django; import waitress; import vlc"`
läuft ohne ImportError durch.

---

### T-OP-4 — Konfigurationsdatei erstellen

**Was zu tun ist:**  
Lege `C:\rastatime\config\libretime.conf` an. Das ist die zentrale
YAML-Konfigurationsdatei, die alle Dienste beim Start lesen.

**Was zu tun ist (the coding assistant):**
1. Prüfe, ob schon ein Template (`libretime.example.conf` o. Ä.) im Repo
   vorhanden ist
2. Wenn ja: kopieren und die Pflichtfelder eintragen
3. Wenn nein: eine minimale `libretime.conf` mit allen Pflichtfeldern
   (`general.public_url`, `general.api_key`, `general.secret_key`,
   `database.*`) als Template ins Repo schreiben und nach
   `C:\rastatime\config\` kopieren

**Pflichtfelder:**
```yaml
general:
  public_url: http://localhost:8000
  api_key: <zufälliger-string-32-zeichen>
  secret_key: <zufälliger-django-secret-key>
  timezone: Europe/Berlin

database:
  host: localhost
  port: 5432
  name: libretime
  user: libretime
  password: libretime

storage:
  path: C:/rastatime/media
```

**Abnahmekriterium:** `python -c "from libretime_shared.config._base import
DEFAULT_CONFIG_FILEPATH; print(DEFAULT_CONFIG_FILEPATH)"` zeigt
`C:\rastatime\config\libretime.conf`. Die Datei existiert und ist gültiges YAML.

---

### T-OP-5 — PostgreSQL-Datenbank und Nutzer anlegen

**Was zu tun ist:**  
Erzeuge Datenbank und Nutzer mit den Werten aus `libretime.conf`.

**Befehle (als postgres-Admin):**
```powershell
psql -U postgres -c "CREATE DATABASE libretime;"
psql -U postgres -c "CREATE USER libretime WITH PASSWORD 'libretime';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE libretime TO libretime;"
psql -U postgres -c "ALTER DATABASE libretime OWNER TO libretime;"
```

**Abnahmekriterium:** `psql -U libretime -d libretime -c "\dt"` verbindet
sich ohne Fehler (leere Tabellenliste ist korrekt — Migrationen folgen in
T-OP-6).

---

### T-OP-6 — Django-Migrationen ausführen

**Was zu tun ist:**  
Führe alle Datenbankmigrationen durch und lege einen Admin-Nutzer an.

**Befehle:**
```powershell
cd C:\rastatime
.venv\Scripts\Activate.ps1
$env:DJANGO_SETTINGS_MODULE = "libretime_api.settings.prod"
$env:LIBRETIME_CONFIG_FILEPATH = "C:\rastatime\config\libretime.conf"

python backend\api\libretime_api\manage.py migrate
python backend\api\libretime_api\manage.py createsuperuser
```

**Abnahmekriterium:** `manage.py migrate` endet mit
`No migrations to apply.` (alle Migrationen erfolgreich). `manage.py
showmigrations` zeigt alle Migrationen als `[X]`.

---

### T-OP-7 — NSSM-Dienste installieren und starten

**Was zu tun ist:**  
Installiere die vier Windows-Dienste per NSSM und starte sie in der
korrekten Reihenfolge (API → Worker → Playout, Icecast optional).

**Befehle (als Administrator):**
```powershell
powershell -ExecutionPolicy Bypass -File C:\rastatime\infra\nssm\install-api.ps1     -StartService
powershell -ExecutionPolicy Bypass -File C:\rastatime\infra\nssm\install-worker.ps1  -StartService
powershell -ExecutionPolicy Bypass -File C:\rastatime\infra\nssm\install-playout.ps1 -StartService
# Optional:
powershell -ExecutionPolicy Bypass -File C:\rastatime\infra\nssm\install-icecast.ps1 -StartService

# Status prüfen:
powershell -ExecutionPolicy Bypass -File C:\rastatime\infra\nssm\status.ps1
```

**Abnahmekriterium:** `status.ps1` zeigt alle drei Pflichtdienste als
`Running`. Kein Dienst erscheint als `StartPending` nach 60 Sekunden.

---

### T-OP-8 — Smoke-Test und Django-gated Tests nachführen

**Was zu tun ist:**  
Führe manuelle API-Prüfungen durch und wiederhole die Testsuite —
dieses Mal mit laufender Datenbank, sodass die bisher übersprungenen
Django-Tests grün werden.

**Manuelle Checks:**
```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/api/v2/now-playing
Invoke-RestMethod http://127.0.0.1:8000/api/v2/audio/devices
```

**Testsuite mit DB:**
```powershell
$env:DJANGO_SETTINGS_MODULE = "libretime_api.settings.prod"
$env:LIBRETIME_CONFIG_FILEPATH = "C:\rastatime\config\libretime.conf"
python -m pytest tests/unit/ -q
```

**Abnahmekriterium:** Alle drei REST-Aufrufe liefern HTTP 200 mit gültigem
JSON. Die Testsuite zeigt deutlich weniger als 81 Skips — idealerweise nur
noch die VLC-Hardware-Skips (~15–20). Keine neuen Fehler.

---

## Teil 2 — RASTATIME als GitHub-Projekt veröffentlichen

> **Priorität: Mittel.** Kann parallel zu Teil 1 begonnen werden, sobald
> T-OP-2 (requirements.txt) abgeschlossen ist. Die Schritte 2.1–2.4 sind
> Codebereinigung; 2.5–2.10 sind reine Projektinfrastruktur.

---

### T-GH-1 — Liquidsoap-Unterverzeichnis entfernen

> **⛔ UNGÜLTIG / NICHT AUSFÜHREN (Hinweis 2026-05-31).** Die Prämisse
> unten ist falsch: Liquidsoap wurde NICHT durch VLC ersetzt — im
> Gegenteil, **Liquidsoap ist seit 2026-05-28 die Produktions-Engine**
> und VLC ist tot. Das Löschen von
> `backend/playout/libretime_playout/liquidsoap/` würde die laufende
> Engine zerstören. Diesen Schritt übersprungen lassen.

**Was zu tun ist:**  
Der gesamte Ordner `backend/playout/libretime_playout/liquidsoap/` ist
toter Code — die Liquidsoap-Engine wurde in Phase 3–4 durch VLC ersetzt.
Er muss gelöscht und alle noch vorhandenen Imports bereinigt werden.

**Was zu tun ist (the coding assistant):**
1. `grep -r "liquidsoap" backend/playout/libretime_playout/` ausführen —
   alle Importpfade auflisten
2. Alle gefundenen Imports in den *neuen* Playout-Modulen entfernen oder
   durch die VLC-Implementierung ersetzen
3. Den gesamten Ordner `liquidsoap/` löschen
4. 10 Tests schreiben: Ordner existiert nicht; keine Python-Datei im
   Playout-Paket importiert noch `liquidsoap`

**Abnahmekriterium:** `grep -r "from.*liquidsoap\|import.*liquidsoap"
backend/` liefert keine Treffer. Suite weiterhin grün.

---

### T-GH-2 — Alten Celery-Worker-Code entfernen

**Was zu tun ist:**  
`backend/worker/libretime_worker/` enthält noch den alten Celery-basierten
Worker (tasks.py, main.py, config.py). Der neue RASTATIME-Worker ersetzt ihn
vollständig.

**Was zu tun ist (the coding assistant):**
1. Prüfen, ob `libretime_worker/` noch von irgendwo importiert wird
2. Alle verbleibenden Celery-Imports in anderen Dateien entfernen
3. Den Inhalt von `backend/worker/libretime_worker/` löschen (oder Ordner
   auf den neuen Worker-Code reduzieren, falls noch Hilfscode darin ist)
4. 10 Tests schreiben: keine Datei enthält `celery`-Import; kein
   `libretime_worker`-Modul importiert Celery

**Abnahmekriterium:** `grep -r "from celery\|import celery" backend/`
liefert keine Treffer. Suite weiterhin grün.

---

### T-GH-3 — systemctl-Aufrufe in der PHP-UI ersetzen

**Was zu tun ist:**  
`frontend/legacy/application/check.php` und `config-check.php` prüfen noch
Dienste per `systemctl is-active`. Das schlägt auf Windows fehl und zeigt
Benutzern falsche Statusinformationen.

**Was zu tun ist (the coding assistant):**
1. Die `systemctl is-active libretime-*`-Aufrufe in beiden Dateien lesen
2. Durch einen `sc.exe query <ServiceName>` oder `Get-Service`-basierten
   Check ersetzen, der die RASTATIME-NSSM-Dienstnamen verwendet
3. Die `with_systemd()`-Funktion in `check.php` entfernen oder durch eine
   `with_nssm()`-Funktion ersetzen
4. 10 Tests schreiben: keine der beiden Dateien enthält `systemctl`;
   beide enthalten `RASTATIME-API` (den korrekten Dienstnamen)

**Abnahmekriterium:** `grep -r "systemctl" frontend/legacy/application/` 
liefert keine Treffer. Suite weiterhin grün.

---

### T-GH-4 — ALSA/PortAudio aus dem Shared-Config-Modell entfernen

**Was zu tun ist:**  
`backend/shared/libretime_shared/config/_models.py` enthält noch
`SystemOutput.ALSA`, `SystemOutput.PORTAUDIO`, `ALSASystemOutput` und
`PortAudioSystemOutput`. Diese Linux-Audio-Backends existieren auf Windows
nicht. Sie sollen durch den Windows-Audio-Eintrag (`WASAPI`) ersetzt werden.

**Was zu tun ist (the coding assistant):**
1. Die vier betroffenen Klassen/Enum-Werte lesen (Zeilen ~220–260)
2. `ALSA`- und `PORTAUDIO`-Enum-Werte löschen; `WASAPI` hinzufügen
3. `ALSASystemOutput` und `PortAudioSystemOutput` löschen;
   `WindowsAudioOutput` (WASAPI) ergänzen
4. Die Union-Type-Annotation in Zeile ~255 anpassen
5. Den dazugehörigen Test `backend/shared/tests/config/models_test.py`
   aktualisieren
6. 10 Tests schreiben: keine der Klassen enthält `alsa` oder `portaudio`;
   `wasapi` oder `WindowsAudioOutput` ist vorhanden

**Abnahmekriterium:** `grep -i "alsa\|portaudio" backend/shared/` liefert
keine Treffer. Suite weiterhin grün.

---

### T-GH-5 — README.md für GitHub erstellen

**Was zu tun ist:**  
Das bestehende `readme.txt` ist ein Changelog. GitHub braucht ein
`README.md` das als Projekt-Landing-Page dient.

**Was zu tun ist (the coding assistant):**
Schreibe `README.md` im Repo-Root mit folgenden Abschnitten:
1. Projektname + einzeiliger Zweck
2. Was ist RASTATIME? (Windows-Port von LibreTime; AGPL-3.0)
3. Architektur-Überblick (Dienste: API, Worker, Playout, Icecast)
4. Systemvoraussetzungen (Windows 11, Python 3.11+, PostgreSQL 17,
   VLC 64-bit, NSSM)
5. Schnellstart (5 Befehle: clone → config → migrate → install → status)
6. Dokumentation (Links zu `docs/operator/INSTALL.md` und weiteren)
7. Upstream-Attribution (Based on LibreTime 4.5.0, AGPL-3.0)
8. Lizenz

**Abnahmekriterium:** `README.md` existiert, ist valides Markdown,
enthält alle 8 Abschnitte. Kein Test nötig (dokumentarisch).

---

### T-GH-6 — .gitignore, LICENSE und CONTRIBUTING.md anlegen

**Was zu tun ist:**  
Drei kurze Dateien, die für jedes öffentliche GitHub-Projekt Pflicht sind.
Können in einem einzigen assistant-Code-Schritt erledigt werden.

**Was zu tun ist (the coding assistant):**

1. `.gitignore` erweitern (bestehende Datei hat Grundgerüst):
   - `config/libretime.conf` (Produktionskonfiguration nie einchecken)
   - `media/` (Medienbibliothek)
   - `logs/`
   - `frontend/legacy/cache/`
   - `*.mo` (kompilierte Gettext-Binaries, optional)

2. `LICENSE` anlegen: vollständiger AGPL-3.0-Text mit Copyright-Zeile
   `Copyright (C) 2026 RASTATIME Contributors / Based on LibreTime 4.5.0`

3. `CONTRIBUTING.md` anlegen mit:
   - Entwicklungsumgebung einrichten (Venv, Pakete, dev-settings)
   - Teststrategie (`python -m pytest tests/unit/`)
   - Branch-Modell und PR-Konvention
   - Commit-Message-Konvention

**Abnahmekriterium:** Alle drei Dateien existieren. `LICENSE` enthält
den AGPL-3.0-Text. `.gitignore` enthält `config/libretime.conf`.

---

### T-GH-7 — GitHub Actions CI-Workflow anlegen

**Was zu tun ist:**  
Lege `.github/workflows/test.yml` an, der bei jedem Push und Pull Request
die Testsuite auf einem Windows-Runner ausführt.

**Was zu tun ist (the coding assistant):**
Schreibe `.github/workflows/test.yml` mit:
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.13" }
      - run: pip install -r backend/shared/requirements.txt
                         # ... alle requirements
      - run: python -m pytest tests/unit/ -q
```

Außerdem: Prüfe, ob für Django-gated Tests ein Service-Container für
PostgreSQL sinnvoll ist, und füge ihn ggf. hinzu.

**Abnahmekriterium:** `.github/workflows/test.yml` existiert und ist
valides YAML. `python -m pytest tests/unit/ -q` läuft lokal weiterhin
durch (Proxy-Test).

---

### T-GH-8 — Erstes GitHub-Release vorbereiten

**Was zu tun ist:**  
Erzeuge ein `CHANGELOG.md` im Keep-a-Changelog-Format aus dem bestehenden
`readme.txt`-Changelog und tagge den aktuellen Stand als `v0.25.1`.

**Was zu tun ist (the coding assistant):**
1. `CHANGELOG.md` schreiben: die wichtigsten Meilenstein-Einträge aus
   `readme.txt` in das Keep-a-Changelog-Format überführen
   (Abschnitte: Added, Changed, Removed — gruppiert nach Version)
2. Sicherstellen, dass `README.md` auf `CHANGELOG.md` verlinkt

**Danach manuell (nicht the coding assistant):**
```bash
git add -A
git commit -m "chore: prepare v0.25.1 release"
git tag v0.25.1
git remote add origin https://github.com/<user>/rastatime.git
git push origin main --tags
```
Auf GitHub: Release aus Tag `v0.25.1` erstellen, Release Notes aus
`CHANGELOG.md` einfügen.

**Abnahmekriterium:** `CHANGELOG.md` existiert, enthält mindestens
Versionen 0.25.1 bis 0.7.0. `README.md` verlinkt darauf.

---

## Übersicht — Reihenfolge und Abhängigkeiten

```
Teil 1 (Betrieb) — sequenziell:
  T-OP-1  Voraussetzungen installieren
    ↓
  T-OP-2  requirements.txt bereinigen         ← auch Voraussetzung für T-GH-2
    ↓
  T-OP-3  Venv + pip install
    ↓
  T-OP-4  libretime.conf erstellen
    ↓
  T-OP-5  PostgreSQL-DB anlegen
    ↓
  T-OP-6  Django migrate
    ↓
  T-OP-7  NSSM-Dienste starten
    ↓
  T-OP-8  Smoke-Test + Django-Tests nachführen

Teil 2 (GitHub) — nach T-OP-2, weitgehend parallel möglich:
  T-GH-1  Liquidsoap entfernen
  T-GH-2  Celery-Worker entfernen
  T-GH-3  systemctl → Windows-SC ersetzen
  T-GH-4  ALSA/PortAudio → WASAPI ersetzen
    ↓ (alle vier abgeschlossen)
  T-GH-5  README.md
  T-GH-6  .gitignore / LICENSE / CONTRIBUTING.md
  T-GH-7  GitHub Actions CI
  T-GH-8  CHANGELOG.md + Release
```

---

## Schnellreferenz

| Task | Typ | Abhängigkeit | Aufwand |
|---|---|---|---|
| T-OP-1 | Manuell | — | 30 min |
| T-OP-2 | Code | T-OP-1 | 15 min |
| T-OP-3 | Manuell | T-OP-2 | 15 min |
| T-OP-4 | Code + Manuell | T-OP-3 | 20 min |
| T-OP-5 | Manuell | T-OP-4 | 10 min |
| T-OP-6 | Manuell | T-OP-5 | 10 min |
| T-OP-7 | Manuell | T-OP-6 | 15 min |
| T-OP-8 | Code + Manuell | T-OP-7 | 20 min |
| T-GH-1 | Code | T-OP-2 | 30 min |
| T-GH-2 | Code | T-OP-2 | 20 min |
| T-GH-3 | Code | — | 30 min |
| T-GH-4 | Code | — | 25 min |
| T-GH-5 | Dokument | T-GH-1–4 | 20 min |
| T-GH-6 | Dokument | — | 15 min |
| T-GH-7 | Code | T-GH-5 | 20 min |
| T-GH-8 | Dokument + Manuell | T-GH-7 | 20 min |
