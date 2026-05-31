# CLEANUP_INVENTORY — airtime / libretime / VLC

**Stand:** 2026-05-31 · **Status:** Entwurf zur Freigabe · **Autor-Notiz:**
Datei-genaue Inventur als Vorbedingung für jeden Code-Eingriff
(Operator-Wunsch 2026-05-31). **Kein Code wird angefasst, bevor diese
Inventur freigegeben ist.**

**Methodik:** drei parallele read-only-Rechercheure über das gesamte
Repo, danach manuelle Verifikation der risikoreichsten Behauptungen
(Import-Kopplungen, env-Prefix, „0 Live-Imports"-Klassifikation). Counts
schließen `**/build/**`, `**/*.egg-info/**`, `**/__pycache__/**`, `.venv/`
aus (generiert).

**Grundsatz (ASSISTANT.local.md):** Zuverlässigkeit vor Modernität. Der
Live-Betrieb darf durch das Aufräumen nicht gefährdet werden. **mpv wird
NICHT angefasst** (lebender Legacy-Fallback, separat im BACKLOG an die
Stabilitätsphase gekoppelt).

---

## 0. Die Realität: drei Code-Schichten

Das Repo wirkt widersprüchlich, weil die Doku + ein Teil des Codes noch
eine **VLC-Engine-Architektur** beschreiben, die nie produktiv wurde.
Die echte Evolution war:

> **VLC (ursprünglicher Plan)** → **mpv (interim, „legacy default")** →
> **Liquidsoap (Produktion seit 2026-05-28, Phase-C5)**

| Schicht | Was | Status |
|---|---|---|
| **1. Live-Stack** | `backend/*/libretime_*` (playout/api/shared/analyzer/api-client) + `backend/rastatime_worker` + `frontend/legacy` (PHP) + Liquidsoap | **läuft live** |
| **2. Lebende RASTATIME-Feature-Pakete** (top-level) | `audio/`, `playout/now_playing`, `playout/engine_interface`, `streams/egress/{interface,_registry,_api_helpers}`, `streams/_types` | **lebt** (von der API importiert) |
| **3. Toter VLC-Code** (top-level + 1 backend-Datei) | `playout/engine_vlc`, `playout/{scheduler,queue_manager,fallback,engine_mock}`, `streams/*/_vlc_manager`, `streams/egress/_sout`, ganz `streams/ingress`, `rastatime_common`, `backend/.../engine/vlc_engine.py` | **tot** |

---

## 1. Toter VLC-Code — löschbar (Stufe-1-Kandidat)

**Verifikation:** Grep über `backend/**/*.py` nach Importen von
`streams.ingress`, `playout.engine_vlc`, `playout.scheduler`,
`playout.queue_manager`, `rastatime_common` → **nur 1 Treffer, und der ist
ein Docstring** (`backend/rastatime_worker/jobs/_inventory.py:221`). Keine
echten Live-Importe.

### 1a. Sauber löschbar (0 Live-Importe — nur Tests referenzieren sie)

```
playout/engine_vlc/            (__init__, _engine, events, probe)
playout/scheduler/             (__init__, _scheduler)
playout/queue_manager/         (__init__, _manager)
playout/fallback/              (__init__, _queue)
playout/engine_mock/           (__init__, _engine)
rastatime_common/              (__init__, config.py)
streams/egress/_vlc_manager.py
streams/egress/_sout.py
```

### 1b. Chirurgisch — erst `__init__`/Branch editieren, DANN löschen

| Datei | Eingriff | Grund |
|---|---|---|
| `streams/egress/__init__.py` | auf `interface` + `_registry` + `_api_helpers` trimmen (Z6-7 `_sout`/`_vlc_manager` raus, ggf. Z1-4 mit den Orphans) | **verifiziert:** `__init__` importiert eager `_sout`+`_vlc_manager`; jeder Live-Import von `streams.egress._registry` zieht damit die VLC-Module in den API-Prozess |
| `backend/playout/libretime_playout/engine/__init__.py` | Z15 `from .vlc_engine import VlcPlayoutEngine` + Z21 `"VlcPlayoutEngine"` raus (+ stale Docstring Z1-12) | **verifiziert:** eager-Import macht `vlc_engine.py` sonst unlöschbar |
| `backend/playout/libretime_playout/__main__.py` | `RASTATIME_PLAYOUT_ENGINE=vlc`-Branch (~Z489-492) entfernen | macht `vlc_engine.py` erst dann vollständig tot |
| → danach: `backend/playout/libretime_playout/engine/vlc_engine.py` löschen | | |

### 1c. Geklärt (2026-05-31, verifiziert per Import-Graph)

**Beide Punkte sind technisch sicher löschbar** — verifiziert über den
internen `streams/`-Import-Graph + repo-weite Consumer-Suche:

| Kandidat | Verifizierter Befund | Entscheidung |
|---|---|---|
| ganz `streams/ingress/**` (`__init__`, `_connection`, `interface`, `_vlc_manager`) | repo-weit **kein** Live-Import; nur Docstrings (`streams/__init__.py:7`, ingress-intern) + `tests/unit/streams/` referenzieren es | **löschen** (Tests mit anpassen) |
| `streams/egress/{_archive,_connection,_health,_metadata}.py` + `_sout.py` + `_vlc_manager.py` | LIVE-Trio (`interface`/`_registry`/`_api_helpers`) importieren **nur** `interface`+`_types`; die Orphans zieht **ausschließlich** `_vlc_manager` (tot) + `__init__`. Repo-weiter Consumer-Check der Klassen (`ArchiveOutput`, `IcecastHealthChecker`, `IcyMetadataPusher`, `StreamConnection`, `SoutBuilder`, `LibVlc*Manager`): einziger Treffer außerhalb tot/test = 1 Docstring in `playout/engine_vlc/_engine.py` (selbst tot) | **löschen** |

**Was in `streams/egress/` bleibt (LIVE):** `__init__.py` (getrimmt auf
`interface`+`_registry`+`_api_helpers`), `interface.py`, `_registry.py`,
`_api_helpers.py`. Plus `streams/_types.py` + `streams/__init__.py`
(Docstring-Erwähnung von `ingress` anpassen). `streams/ingress/` entfällt
komplett.

### 1d. Zugehörige Tests (mit dem getesteten Code löschen)

```
tests/unit/playout/engine_vlc/         (ganzer Ordner)
tests/unit/playout/test_scheduler*.py, test_queue_manager.py,
   test_fallback.py, test_mock_engine.py, test_now_playing.py*,
   test_linein_integration.py
tests/unit/rastatime_common/test_engine_config.py
tests/unit/streams/test_sout_builder.py, test_egress_manager.py,
   test_ingress_manager.py, test_archive_output.py,
   test_stream_connection.py, test_icy_metadata.py,
   test_health_checker.py, ...
```
*`test_now_playing.py` testet teils LIVE-Module — vor Löschen prüfen,
ggf. nur anpassen. Die `tests/unit/streams/test_output_status_api.py` +
`test_stream_interfaces.py` decken die LIVE-Trio (`interface`/`_registry`/
`_api_helpers`) ab → behalten/anpassen.*

### 1e. NICHT betroffen (häufiges Missverständnis)
- `infra/nssm/install-playout.ps1` startet tatsächlich `-m libretime_playout`
  (Z256, live) — nur der **Kommentar-Header** sagt fälschlich `-m playout`.
- `backend/playout/libretime_playout/engine/mpv_engine.py` → **behalten**.

**Aufwand 1a-1d:** ~3-5 h inkl. Test-Bereinigung + voller Regression-Lauf
(`tests/unit/` + `backend/playout/tests/`). **Risiko:** niedrig-mittel —
toter Code, aber die 1b-Edits müssen sitzen.

---

## 2. Lebende Pakete — NICHT anfassen

Von `backend/api/libretime_api/` (und worker/playout) importiert:

```
audio/soundcard/**     → Soundcard-Settings-API, Device-Manager (13 Importstellen)
audio/linein/**        → Line-In-API
playout/now_playing/** → Now-Playing-State, Playback-Events
playout/engine_interface/** → PlayoutEngine-ABC (transitiv via now_playing)
streams/egress/{interface,_registry,_api_helpers}.py → Stream-Status-API
streams/_types.py      → StreamProtocol/StreamState enums
```
Diese erwähnen VLC nur in **Kommentaren/Docstrings** — kein `import vlc`.

---

## 3. Doku-Korrektur (VLC als „aktuelle Engine" → Liquidsoap)

Kanonischer, bereits korrekter Wortlaut zum Abschreiben:
`docs/manual/SETTINGS.md` §6 (Z302-374) + `docs/operator/LIQUIDSOAP_CUTOVER.md`.

| Datei | Zeilen | Aktion | Begründung |
|---|---|---|---|
| `README.md` | 16, 20, 53 | **korrigieren** → Liquidsoap (Produktion), VLC/mpv als Legacy | öffentliche Landing-Page, kein historischer Rahmen |
| `FORK_NOTES.md` | 33, 35, 49, 77, 82 | **korrigieren** + 1-Zeilen-Historie („ursprünglich libVLC; Liquidsoap in Phase 2 adoptiert") | lebendes Orientierungsdoc |
| `infra/nssm/install-playout.ps1` | 10, 12, 42-44, 63, 196-207, 289-303 | **korrigieren** | aktives Install-Script sagt „VLC mandatory, ohne libvlc.dll startet nichts" — falsch |
| `POST_IMPLEMENTATION.md` | 28-35, 89-92, **236-253 (T-GH-1!)** | **korrigieren / Banner** | ⚠️ T-GH-1 weist an, die Liquidsoap-Engine zu LÖSCHEN („durch VLC ersetzt") — gefährlich |
| `backend/.../engine/__init__.py` | 1-12 (Docstring) | **korrigieren** | beschreibt VLC als aktive Engine |
| `backend/.../__main__.py` | 2, 9 (Docstring) | **korrigieren** | nennt nur mpv/VLC, nicht Liquidsoap |

**AS-IS lassen (nur optionaler datierter Banner):** datierte/eingefrorene
Dokumente — `RASTATIME_ARCHITECTURE_DRAFT_v0.1.md` (self-correct Z1419-1421),
`IMPLEMENTATION_PLAN.md` (pre-coding plan), `BLOCKERS_T0.1.md`, `readme.txt`.

---

## 4. `libretime` → RASTATIME — GROSSER Eingriff, an HW-Wechsel koppeln

**Empfehlung: 🟡 Defer auf die Neuinstallation** (frischer venv + neue
`rastatime.conf` = sauberer Schnitt statt Live-Risiko).

**Impact (verifiziert):**
- **Python-Pakete** `libretime_{playout,api,shared,api_client,analyzer,worker}`:
  146 Import-Statements in 71 Dateien; 6 Verzeichnisse + 6 `*.egg-info`;
  12 `setup.py`/`pyproject.toml` (hardcoden dist-Name + `console_scripts`).
- **venv editable-installs** (`__editable___libretime_*_finder.py`) hardcoden
  Import-Name + Pfad → **jedes Paket muss neu `pip install -e`**, sonst
  `ModuleNotFoundError` beim Service-Start.
- **env-Prefix `LIBRETIME_`**: definiert in `backend/shared/libretime_shared/
  config/_base.py:14` (`DEFAULT_ENV_PREFIX="LIBRETIME"`). 276 Vorkommen in
  62 Dateien. Ändern macht **alle bestehenden env-Overrides** (API-Key,
  DB-Host) still wirkungslos.
- **`libretime.conf`**: 57 Dateien; Default in `_base.py:18`, dupliziert in
  `manage.py:12`, `playout/__main__.py:73`. Pfad ist **halb-migriert**
  (`C:\rastatime\config\libretime.conf`).
- **Django**: 11 `INSTALLED_APPS`-Einträge `"libretime_api.<app>"`, 10
  AppConfig `name=`, 33 dotted Refs; `DJANGO_SETTINGS_MODULE` in allen 3
  NSSM-Scripts + Code.
- **PHP-Frontend** (`constants.php` 11×, `ApiController.php`, `icecast-auth.php`)
  liest Config-Pfad/Keys — separate Sprache, von Python-Refactoring nicht erfasst.
- **Guard-Tests** (`test_t24_2_config_defaults.py`, `test_tgh5/6`, `test_t23_*`,
  `test_t22_1_nssm_install.py`) müssen im Gleichschritt mit.
- Aggregat: **547 Token-Vorkommen in 165 Dateien.**

**Bonus-Fund (eigener Cleanup-Punkt):** `backend/worker/libretime_worker/`
ist **toter Celery-Code** — ersetzt durch das bereits umbenannte, lebende
`backend/rastatime_worker/` (Windows-native). Repo-weit nur 1 echter Import.
Kandidat für Löschung statt Umbenennung.

---

## 5. `airtime` → RASTATIME — Befund: **NICHT umbenennen**

**Wichtige Erkenntnis:** Es gibt **kein** „airtime"-Vorkommen, das ein
Rebranding rechtfertigt. Alle ~430 Treffer fallen in:

| Kategorie | Beispiele | Warum bleiben |
|---|---|---|
| **DB-/ORM-Heritage** | `frontend/legacy/application/models/airtime/**` (184 Dateien!), `cc_*`-Tabellen, `public/js/airtime/**`, `AIRTIME.*` JS-global, `airtime_locale`-Cookie | Propel-ORM-Namespace mappt `cc_*`-Tabellen → Umbenennen **bricht die DB** |
| **DB-Migrations/Schema** | `backend/api/.../legacy/migrations/**` (`schema.sql`, `sqldb.map`, …) | Migrations-Historie nie umschreiben |
| **Upstream-Doku** | `docs/upstream/**` | LibreTime-Referenz, MUSS bleiben |
| **Englisches Wort** | „fills airtime", „during airtime" | normale Prosa, keine Marke |
| **Attribution** | „migrating from LibreTime / Airtime" | legitime Ahnen-Nennung, teils rechtlich |

→ **Empfehlung: 🔴 No-Go für airtime-Rebranding.** Keine sichere,
sinnvolle Ersetzung möglich.

---

## 6. Build-Müll (eigener Cleanup-Punkt)

- `backend/api/build/lib/**` — setuptools-Build-Output, gehört nicht ins Repo
  (prüfen ob in `.gitignore`, sonst entfernen + ignorieren).
- `*.egg-info/` — generiert (werden bei `pip install -e` neu erzeugt).

---

## 7. Empfohlene Reihenfolge

| Stufe | Inhalt | Status | Risiko |
|---|---|---|---|
| **1 — ✅ ERLEDIGT 2026-05-31** | Toter VLC-Code (§1) + Doku-Korrektur (§3) | ✅ committet: `31eb8c4` (Doku) · `981026f` (Gruppe 1) · `9a30edd` (Gruppe 2) · `e6c4f2f` (Gruppe 3). ~12.900 Z. entfernt; Regression grün. Build-Müll (§6) war bereits `.gitignore`'d (Z20 `build/`). | erledigt |
| **1b — offen, optional** | toten Celery-`libretime_worker` löschen (§4-Bonus) | 🟢 prüfen | niedrig |
| **2 — mit HW-Wechsel** | `libretime`→`rastatime` Pakete + `libretime.conf` + env-Prefix (§4) | 🟡 Defer | hoch |
| **nie** | `airtime` (§5), `docs/upstream`, DB-Schema, `LICENSE`/Attribution | 🔴 No-Go | — |
| **separat** | mpv-Cleanup (bereits im BACKLOG, an Stabilitätsphase gekoppelt) | — | — |
