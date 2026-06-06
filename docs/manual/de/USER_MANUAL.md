# RASTATIME — Benutzerhandbuch (Deutsch)

> 🌐 **Sprachen:** [English](../../../USER_MANUAL.md) ·
> **Deutsch** · [Français](../fr/USER_MANUAL.md) ·
> [Español](../es/USER_MANUAL.md)

> **Über dieses Handbuch.** RASTATIME ist ein Windows-first
> Fork von LibreTime für den Betrieb einer Community- /
> kleinen kommerziellen Radiostation. Dieses Dokument ist
> der Operator-orientierte Begleiter zu den technischen
> [ARCHITECTURE](../../../RASTATIME_ARCHITECTURE_DRAFT_v0.1.md)-
> und [INSTALL](../../operator/INSTALL.md)-Dokumenten. Es
> behandelt **wie man eine Radiostation mit RASTATIME im
> täglichen Betrieb führt** — nicht wie man den Server
> installiert oder debuggt.

> **Hinweis zur Konsistenz.** Code, UI-Strings im Repository
> und alle Backend-Komponenten sind in Englisch. Diese
> Übersetzung beschreibt die Bedienung; bei Diskrepanzen
> zwischen dieser Übersetzung und dem englischen Original
> gilt das englische Original als verbindlich.

---

## Zielgruppe und Konventionen

Dieses Handbuch ist für zwei Leser parallel geschrieben:

* **Operator** — Stationsleiter, Programmleiter, Moderatoren,
  DJs. Sie melden sich morgens in der Web-Oberfläche an,
  planen den Tag, klicken "Speichern" und arbeiten weiter.
  Alles, was Sie dafür brauchen, steht im Haupttext jedes
  Kapitels.

* **Techniker** — Administratoren, Ingenieure, Integratoren.
  Sie müssen auch wissen, was darunter passiert: welche
  Datenbanktabelle die Oberfläche schreibt, welcher
  API-Endpunkt die Schaltfläche auslöst, welcher Dienst
  laufen muss, damit die Funktion funktioniert. Achten Sie
  auf die hervorgehobenen Kästen **Wie es unter der Haube
  funktioniert**; diese behandeln die Internals, ohne den
  Operator-Workflow zu verlängern.

### Visuelle Konventionen

| Markierung | Bedeutung |
|---|---|
| **Fettdruck** | Schaltflächen-Label, Menüeintrag oder Feldname wie in der Oberfläche. |
| `Code` | Wörtlicher Wert, den der Operator eingibt oder den das System wörtlich anzeigt — ein Dateiname, ein Konfigurationsschlüssel, eine Stream-URL. |
| > Zitatblock | Nebenbemerkung, Vorbehalt oder Operator-Tipp. Beim ersten Lesen überspringbar. |
| **Wie es unter der Haube funktioniert** | Technischer Hinweiskasten — Datenbanktabelle, API-Endpunkt, Scheduler-Entscheidung. Operator dürfen überspringen. |
| **Warum es so funktioniert** | Hinweiskasten zur Design-Entscheidung — verweist auf die entsprechende Abschnittsnummer in ARCHITECTURE, falls relevant. |

### Standard-URLs und Pfade

Sofern Ihre Installation in `config/libretime.conf` keine
abweichenden Werte gesetzt hat:

| Was | Standard |
|---|---|
| Web-Oberfläche (Apache-Frontend) | `http://<station-host>/` |
| Django REST API | `http://localhost:8765/api/v2/` |
| Icecast Streaming-Server | `http://localhost:8000/` |
| Installationswurzel | `C:\rastatime\` |
| Log-Verzeichnis | `C:\rastatime\logs\` |
| Medienbibliothek auf der Festplatte | `C:\rastatime\media\` |
| Operator-lokaler Audio-Cache | `C:\rastatime\scheduler\` |
| Konfigurationsdatei | `C:\rastatime\config\libretime.conf` |

Wenn Ihre Station andere Pfade verwendet, ersetzen Sie diese
durchgängig.

---

## Wie RASTATIME organisiert ist

RASTATIME ist **kalendergesteuert**. Alles, was auf Sendung
geht, ist entweder:

1. Eine **Sendung**, die zu einer bestimmten Zeit im Kalender
   eingeplant ist, oder
2. Der **Fallback**, der Sendezeit füllt, wenn keine Sendung
   aktiv ist.

Eine Sendung ist ein Slot im Kalender; der Slot wird mit
Inhalt *gefüllt* (Tracks, Smart Blocks, Webstreams, Line-Ins)
entweder manuell im Show-Builder, automatisch über eine
autoloading Playlist oder beides. Wenn der Slot beginnt,
spielt die Playout-Engine den gefüllten Inhalt ab. Wenn der
Slot endet, geht die Engine zur nächsten Sendung über.

Das **Dashboard** oben rechts zeigt, was gerade auf Sendung
ist, was als Nächstes kommt und welche Output-Streams
gesund sind.

```
   ┌──────────────────────────┐         ┌────────────────────────────────┐
   │      OPERATOR (Sie)      │         │     KALENDER (Sendeplan)        │
   │                          │ erstellt│                                │
   │  • Planen den Sendeplan  │────────▶│  • Sendungen zu festen Zeiten  │
   │  • Füllen die Sendungen  │         │  • Jede Sendung = 1 Zeile in   │
   │  • Verwalten Bibliothek  │         │    cc_show_instances           │
   └──────────────────────────┘         └─────────────────┬──────────────┘
              ▲                                           │
              │ sehen im Dashboard                        │ Scheduler dispatcht
              │                                           ▼
   ┌──────────┴───────────────┐         ┌────────────────────────────────┐
   │  NOW PLAYING (Ausgabe)   │◀────────│ PLAYOUT ENGINE (VLC-basiert)  │
   │                          │ füttert │                                │
   │  • Icecast :8000         │         │  • Spielt Dateien / Streams   │
   │  • optional Aufnahmedatei│         │  • Wechselt zu Live-Quelle    │
   │  • optional Studio-Out   │         │  • Sendet Start/End-Events    │
   └──────────────────────────┘         └────────────────────────────────┘
```

Alles in diesem Handbuch hängt an einem dieser vier Kästen.

---

## Das Handbuch im Überblick

Jeder Link unten öffnet ein fokussiertes Unterdokument im
[`docs/manual/de/`](.)-Ordner. Lesen Sie sie in beliebiger
Reihenfolge — das Master-Dokument oben ist das Einzige, was
sie alle voraussetzen.

### Täglicher Sendebetrieb

| Kapitel | Inhalt |
|---|---|
| [Erste Schritte](./GETTING_STARTED.md) | Erste Anmeldung, Dashboard-Tour, Grundkonzepte, Rollen-Übersicht. Lesen Sie das zuerst, wenn Sie RASTATIME noch nie verwendet haben. |
| [Dashboard](./DASHBOARD.md) | Now-Playing-Widget, Quellenstatus, manuelle Übersteuerung, Station live über ein Mikrofon nehmen. |
| [Kalender](./CALENDAR.md) | Sendungen erstellen, bearbeiten, Drag-and-Drop, wiederkehrende Sendungen, Wiederholungen, Hosts. |
| [Sendungs-Vorlagen](./SHOW_TEMPLATES.md) | Sendungseinstellungen wiederverwenden, ohne sie jede Woche neu einzugeben. |

### Inhalt und Bibliothek

| Kapitel | Inhalt |
|---|---|
| [Bibliothek](./LIBRARY.md) | Tracks, Smart Blocks, Playlists. Suchen, importieren, organisieren. |
| [Webstreams](./WEBSTREAMS.md) | Inklusive der sekundengenauen Standardlänge (2026-05-19). |
| [Line-In](./LINE_IN.md) | Die kombinierte Bibliothek-und-Playlist-Ansicht für benannte Live-Eingänge. |

### Automatisierung

| Kapitel | Inhalt |
|---|---|
| [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) | Eine Playlist sich selbst für jede Instanz einer Sendung aufbauen lassen, inklusive Outro-Reserve-Logik. |
| [Auto DJ](./AUTO_DJ.md) | Der Hintergrund-Filler, der Sendungen in Kalenderlücken erstellt und unvollständige Sendungen auffüllt. |
| [Aufnahme pro Sendung](./RECORD_PER_SHOW.md) | Den kompletten On-Air-Output einer Sendung in eine Datei aufzeichnen. |
| [24/7-Aufnahme](./RECORD_PER_HOUR.md) | Den gesamten On-Air-Output rund um die Uhr aufzeichnen, eine Datei pro Stunde — für Compliance, Catchup und Notfall-Backup. |

### Ausgabe und Infrastruktur

| Kapitel | Inhalt |
|---|---|
| [Streams](./STREAMS.md) | Bis zu vier Output-Streams konfigurieren, Hörerzahlen überwachen, Fehlerbehebung. |
| [Lokale Maschine](./LOCAL_MACHINE.md) | Soundkarten-Ausgang, Line-In-Eingang, lokaler Import-Ordner. |
| [Öffentliche Embed-Widgets](./WIDGETS.md) | Drop-in-Widgets für die öffentliche Website Ihrer Station (Now Playing — Show / Track, Weekly Program, Player). |

### Administration

| Kapitel | Inhalt |
|---|---|
| [Benutzer und Rollen](./USERS_AND_ROLES.md) | Super Admin, Admin, Program Manager, DJ, Gast — was jede Rolle darf. |
| [Einstellungen](./SETTINGS.md) | Tour durch jede Seite im Einstellungs-Menü. |
| [Sprachen (i18n)](./I18N.md) | Sprache der Oberfläche wechseln; Übersetzung hinzufügen. |

---

## Wenn etwas nicht funktioniert

Dieses Handbuch beschreibt den **normalen Happy Path**. Wenn
sich etwas nicht so verhält, wie das Handbuch es beschreibt,
liegen die Wiederherstellungsprozeduren woanders:

* [`docs/operator/DEVICE_MISSING.md`](../../operator/DEVICE_MISSING.md)
  — Eine konfigurierte Soundkarte oder ein Line-In ist nicht
  mehr eingesteckt.
* [`docs/operator/LINE_IN_BROKEN.md`](../../operator/LINE_IN_BROKEN.md)
  — Line-In vorhanden, aber liefert Stille oder Rauschen.
* [`docs/operator/CRASH_RECOVERY.md`](../../operator/CRASH_RECOVERY.md)
  — Ein Dienst ist abgestürzt; Neustart-Reihenfolge; wie man
  die Wiederherstellung verifiziert.
* [`docs/operator/RESTART_ORDER.md`](../../operator/RESTART_ORDER.md)
  — Den gesamten Stack in der richtigen Reihenfolge kalt
  starten.
* [`docs/operator/BACKUP.md`](../../operator/BACKUP.md)
  — Backup erstellen, verifizieren und wiederherstellen.
* [`docs/operator/UPGRADE.md`](../../operator/UPGRADE.md)
  — Auf eine neue RASTATIME-Version aktualisieren.

Diese Runbooks sind aktuell nur auf Englisch verfügbar.

---

## Wohin als Nächstes

* Wenn Sie RASTATIME **frisch installiert haben** und die
  Station zum ersten Mal auf Sendung bringen möchten,
  beginnen Sie mit [Erste Schritte](./GETTING_STARTED.md),
  dann [Kalender](./CALENDAR.md), dann [Streams](./STREAMS.md).

* Wenn Sie von **LibreTime / Airtime migrieren**, sind die
  zuerst wissenswerten Unterschiede:
  [Aufnahme pro Sendung](./RECORD_PER_SHOW.md) (erfasst jetzt
  den gesamten On-Air-Output, nicht nur den Line-In),
  [Auto DJ](./AUTO_DJ.md) (neu in RASTATIME) und
  [Lokale Maschine](./LOCAL_MACHINE.md) (ersetzt die alte
  "Soundcard"-Seite und fügt das Import-Ordner-Feature hinzu).

* Wenn Sie RASTATIME **von Grund auf installieren** müssen,
  ist dieses Handbuch nicht das richtige Dokument — siehe
  [`docs/operator/INSTALL.md`](../../operator/INSTALL.md).

* Wenn Sie **verstehen müssen, warum** eine Funktion so
  gestaltet ist, wie sie ist, verweist jedes Kapitel hier auf
  das entsprechende Kapitel in
  [ARCHITECTURE](../../../RASTATIME_ARCHITECTURE_DRAFT_v0.1.md).

---

## Glossar

| Begriff | Bedeutung |
|---|---|
| **Show / Sendung** | Ein Slot im Kalender mit Start, Ende, Name und (üblicherweise) eingeplanten Inhalten. Persistiert in `cc_show` + `cc_show_instances`. |
| **Instanz** | Ein konkretes Vorkommen einer Sendung. Eine tägliche Sendung ist eine `cc_show`-Zeile + viele `cc_show_instances`-Zeilen. |
| **Schedule-Item** | Eine Zeile in der Playlist einer Sendungsinstanz — typischerweise eine Datei, aber auch ein Smart Block, Webstream oder Line-In. Persistiert in `cc_schedule`. |
| **Playlist** | Eine wiederverwendbare geordnete Liste von Items. Persistiert in `cc_playlist` + `cc_playlistcontents`. |
| **Smart Block** | Eine Abfrage innerhalb einer Playlist, die zum Build-Zeitpunkt zu einer Menge von Tracks expandiert, optional begrenzt auf "verbleibende Zeit in der Sendung". Persistiert in `cc_block`. |
| **Webstream** | Eine URL, die auf eine andere Icecast- / Shoutcast- / HTTP-MP3/AAC-Quelle zeigt. Persistiert in `cc_webstream`. |
| **Line-In** | Ein benannter Live-Audio-Eingang auf der Operator-Maschine (ein Mikrofon, ein Mixer, ein externer CD-Player). Persistiert in `rastatime_linein`. |
| **Autoloading Playlist** | Eine Playlist, die an eine *Sendungsdefinition* angehängt ist, sodass jede Instanz der Sendung die Inhalte der Playlist automatisch in den Sendeplan aufnimmt. |
| **Auto DJ** | Ein Hintergrundprozess, der Sendungen in Kalenderlücken erstellt und unvollständige Sendungen auffüllt. Unterscheidet sich von Autoloading Playlists. |
| **Output-Stream** | Einer von bis zu vier Icecast-Mountpoints, an die das Playout sendet. Konfiguriert unter Einstellungen → Streams. |
| **Source-Switcher** | Der interne Mechanismus, der entscheidet, welche Audio-Quelle (Scheduler, Line-In, Master DJ, Show DJ) gerade auf Sendung ist. |
| **Fallback-Queue** | Eine konfigurierte Schleife, die abgespielt wird, wenn keine Sendung eingeplant ist und Auto DJ deaktiviert ist. |
| **Lokaler Import-Ordner** | Ein Verzeichnis auf der Operator-Maschine, das der Analyzer auf neue Dateien überwacht; alles, was hier abgelegt wird, wird automatisch in die Bibliothek importiert. |

---

*Dieses Dokument wird im RASTATIME-Repository versioniert.
Im [CHANGELOG](../../../CHANGELOG.md) finden Sie, was sich
am Handbuch selbst geändert hat; in den jeweiligen
Unterdokumenten, was sich an den einzelnen Funktionen
geändert hat.*
