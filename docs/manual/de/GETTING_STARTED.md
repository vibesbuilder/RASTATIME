# Erste Schritte

> **Wo Sie sich im Handbuch befinden.** Dieses Kapitel setzt
> voraus, dass RASTATIME bereits installiert ist und die
> Web-Oberfläche erreichbar ist. Falls noch nicht, arbeiten
> Sie zuerst [`docs/operator/INSTALL.md`](../../operator/INSTALL.md)
> durch.
>
> **Lesezeit.** ~15 Minuten für den Operator-Pfad, ~25 mit
> den technischen Nebenbemerkungen.

Dieses Kapitel führt einen brandneuen Operator durch die
erste Anmeldung, den ersten Bildschirm, den er sieht, die
Rolle jedes Hauptmenüs und die minimale Reihenfolge, um
einen Track auf Sendung zu bringen. Am Ende werden Sie:

1. Sich mit den Standard-Zugangsdaten angemeldet und Ihr
   Passwort geändert haben.
2. Identifiziert haben, welche Benutzerrolle Sie haben und
   was diese Ihnen erlaubt.
3. Die Bibliothek, den Kalender und das Dashboard gefunden
   haben.
4. Ihren ersten geplanten Track erstellt und gesendet haben.
5. Verifiziert haben, dass der Output-Stream die Hörer
   erreicht.

---

## 1. Erste Anmeldung

Öffnen Sie `http://<station-host>/` in einem modernen
Browser (Chrome, Edge, Firefox; Internet Explorer wird
*nicht* unterstützt).

Die Standard-Super-Admin-Zugangsdaten einer frischen
Installation sind:

| Feld | Wert |
|---|---|
| Benutzername | `admin` |
| Passwort | `admin` |

> **Ändern Sie das jetzt.** Sobald Sie sich angemeldet
> haben, gehen Sie zu **Einstellungen → Benutzer verwalten**,
> klicken Sie auf `admin` und setzen Sie ein echtes Passwort.
> RASTATIME erzwingt keine Passwortänderung bei der ersten
> Anmeldung — das geht nicht, weil einige Installationen die
> erste Anmeldung skripten. Das Default-Konto ist ein
> bekannter Angriffsvektor, wenn der Server außerhalb Ihres
> Studio-LANs erreichbar ist.

> **Wie es unter der Haube funktioniert.** Zugangsdaten
> leben in `cc_subjs`. Passwörter sind gehasht (bcrypt). Das
> Session-Cookie heißt `PHPSESSID`; der Zend-Session-Speicher
> liegt standardmäßig in `C:\rastatime\runtime\sessions\`.
> Eine Anmeldung speichert auch `last_login` für den
> Benutzer — sichtbar auf der Seite "Benutzer verwalten".

Wenn Sie sich nicht anmelden können: Das
[`CRASH_RECOVERY`](../../operator/CRASH_RECOVERY.md)-Runbook
deckt den Fall ab, dass Apache, mod_fcgid oder der
API-Dienst nicht läuft. Bis diese laufen, kann keine
Anmeldung erfolgreich sein.

---

## 2. Die obere Leiste und was jeder Punkt tut

Nach der Anmeldung landen Sie standardmäßig im **Kalender**.
Die obere Navigationsleiste enthält jeden anderen Bereich
der Anwendung:

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │  RASTATIME  │  Dashboard  Kalender  Bibliothek  Einstellungen  Hilfe│ Benutzer ▾│
  └─────────────────────────────────────────────────────────────────────┘
```

| Menü | Was dort lebt |
|---|---|
| **Dashboard** | Was gerade auf Sendung ist, was als Nächstes kommt, Quellenstatus (Scheduler / Line-In / Master DJ / Show DJ) und ein manuelles Übersteuerungs-Panel. Siehe [Dashboard](./DASHBOARD.md). |
| **Kalender** | Das Sendeplan-Raster. Sendungen erstellen / bearbeiten / löschen. Sendungen per Drag-and-Drop verschieben. Siehe [Kalender](./CALENDAR.md). |
| **Bibliothek** | All Ihre Tracks, Smart Blocks, Playlists, Webstreams und Line-Ins. Suchen und filtern. Siehe [Bibliothek](./LIBRARY.md). |
| **Einstellungen** | Streams, Lokale Maschine (Soundkarte + Import-Ordner), Auto DJ, Sendungs-Vorlagen, Allgemeine Einstellungen, Benutzer verwalten, Lokalisierung. Jeder Eintrag ist ein eigenes Unterdokument in diesem Handbuch. |
| **Hilfe** | Links zu diesem Handbuch, dem Installations-Runbook und der originalen LibreTime-Dokumentation (zur Referenz beibehalten). |
| **Benutzer-Dropdown** (oben rechts) | Abmelden, Sprache wechseln, eigenes Profil ansehen, eigener API-Schlüssel (für Skripte). |

> **Operator-Tipp.** Der Kalender ist das Schwerpunktzentrum.
> Sie können fast alles vom Kontextmenü des Kalenders aus
> erledigen — eine Sendung erstellen, sie aus der Bibliothek
> füllen, eine Vorlage anhängen, sie zur Bearbeitung öffnen.
> Die anderen Hauptmenüs sind meist für einmalige
> Konfigurationen.

---

## 3. Rollen — wer Sie sind entscheidet, was Sie sehen

Jeder Benutzer hat genau eine **Rolle**. Die Rolle wird auf
der Seite "Benutzer verwalten" gesetzt und ist das Einzige,
was steuert, was die Oberfläche Sie tun lässt.

| Rolle | Kann sehen / tun |
|---|---|
| **Gast (G)** | Nur Lese-Dashboard. Kein Kalender, keine Bibliothek, keine Einstellungen. Verwendet für Monitoring-Dashboards oder Infoschirme an der Rezeption. |
| **DJ (H)** | Nur eigene Sendungen + eigene Dateien. Kann eigene Sendungen füllen, eigene Tracks hochladen. Kann keine Sendungen erstellen. Kann keine Dateien anderer DJs sehen. |
| **Program Manager (P)** | Vollzugriff auf Kalender und Bibliothek. Kann Sendungen für jeden DJ erstellen und bearbeiten. Kann keine stationsweiten Einstellungen ändern. |
| **Admin (A)** | Alles, was ein Program Manager tun kann, plus stationsweite Einstellungen (Streams, Lokale Maschine, Auto DJ, Sendungs-Vorlagen, Lokalisierung). |
| **Super Admin (S)** | Alles. Plus die Fähigkeit, andere Admins zu erstellen und zu degradieren. Reserviert für den Stationsinhaber / technischen Admin. |

> **Warum es so funktioniert.** Rollenbasierte ACL wird
> serverseitig in `configs/ACL.php` durchgesetzt.
> Menüeinträge in der Oberfläche zu verbergen ist nur eine
> Annehmlichkeit — das Backend prüft jede Aktion erneut
> gegen die Benutzerrolle. Ein DJ kann die Sendung eines
> anderen DJs nicht bearbeiten, selbst wenn er die URL von
> Hand zusammenbaut. Siehe ARCHITECTURE §11 für die
> vollständige Rollenmatrix.

[`USERS_AND_ROLES`](./USERS_AND_ROLES.md) behandelt
Rollenzuweisung und die ressourcenweise Berechtigungsmatrix.

---

## 4. Die ersten zehn Minuten: von leerer Station zum On-Air-Track

Eine brandneue RASTATIME-Installation hat eine leere
Bibliothek, einen leeren Kalender und einen laufenden
Icecast-Dienst, dem aber kein Audio zugeführt wird. Dieser
Abschnitt führt den kürzestmöglichen Weg, um alle drei zu
beheben.

### 4.1 Bestätigen, dass der Output-Stream existiert

Einstellungen → **Streams**.

Die Standardinstallation bringt **Stream 1** konfiguriert mit:

| Feld | Standard |
|---|---|
| Typ | Icecast |
| Server | `localhost` |
| Port | `8000` |
| Mount | `/rastatime` |
| Format | MP3, 192 kbps, 44,1 kHz, Stereo |

Die Spalte **Verbunden** sollte bereits einen grünen Badge
zeigen, wenn der Playout-Dienst läuft. Wenn sie rot
("Getrennt") anzeigt, ist das Playout nicht gestartet —
verifizieren Sie mit `Get-Service RASTATIME-PLAYOUT` in
PowerShell.

> **Wie es unter der Haube funktioniert.** Die Web-Oberfläche
> pusht den Stream nicht selbst — der Windows-Dienst
> **RASTATIME-PLAYOUT** tut es. Er liest die Stream-Konfig
> aus `cc_pref` beim Start und bei jedem Speichern, öffnet
> eine Icecast-Source-Verbindung und beginnt sofort, Stille
> (oder den Fallback-Inhalt, falls konfiguriert) zu
> publizieren. Der grüne / rote Badge wird vom
> `/api/v2/streams`-Endpunkt gesteuert, der den
> Live-`libvlc`-Source-Output-Zustand prüft.

Zum Anhören öffnen Sie in einem weiteren Tab:
`http://<station-host>:8000/rastatime`. Sie sollten Stille
oder die Fallback-Schleife hören, wenn eine konfiguriert
ist. Wenn Sie nichts hören und der Badge grün ist, ist als
Nächstes das Ausgabegerät der Operator-Maschine zu prüfen —
siehe [Lokale Maschine](./LOCAL_MACHINE.md).

### 4.2 Einen Track hochladen

Bibliothek → **Hochladen**.

Ziehen Sie eine beliebige MP3-, FLAC- oder WAV-Datei auf
den Upload-Bereich. Der Analyzer läuft die Datei durch
ffprobe (Metadaten) und ffmpeg (Abspielbarkeit — dekodiert
die gesamte Datei zu `null`, um zu bestätigen, dass sie von
Anfang bis Ende abspielbar ist), dann erscheint die Zeile
in der Bibliotheksliste.

> **Operator-Tipp.** Wenn Sie einen Ordner Musik zu
> importieren haben, ziehen Sie sie nicht einzeln per
> Drag-and-Drop. Setzen Sie unter Einstellungen → Lokale
> Maschine den **Lokalen Import-Ordner** auf ein Verzeichnis
> auf dem Server; alles, was in dieses Verzeichnis abgelegt
> wird, wird beim nächsten Analyzer-Poll (standardmäßig alle
> 60 s) automatisch importiert. Siehe
> [Lokale Maschine](./LOCAL_MACHINE.md).

> **Wie es unter der Haube funktioniert.** Upload schreibt
> in ein Staging-Verzeichnis unter `C:\rastatime\import\`,
> dann wird ein Analyzer-Job eingereiht. Der Analyzer parst
> Metadaten (ID3 / Vorbis-Tags) und verifiziert
> Abspielbarkeit via `ffmpeg -v error -i <file> -f null -`;
> siehe ARCHITECTURE §23.14. Bei Erfolg wird die Datei in
> die Medienbibliothek nach
> `C:\rastatime\media\<owner>\<year>\<month>\` verschoben
> und eine `cc_files`-Zeile eingefügt. Bei hartem Fehler
> (Dekodierfehler) wird der Upload mit "File is unplayable"
> abgelehnt. Bei weichem Fehler (Dekoder-Warnungen, aber
> vollständige Dekodierung) wird der Import mit einem gelben
> Warning-Badge erfolgreich.

### 4.3 Eine Sendung erstellen

Kalender → klicken Sie auf eine beliebige leere Zelle in
der nächsten Stunde → **Neue Sendung**.

Füllen Sie aus:

| Feld | Vorgeschlagener Wert |
|---|---|
| **Name** | `Test` |
| **Startdatum / Uhrzeit** | Jetzt + 2 Minuten |
| **Dauer** | 10 Minuten |
| **Genre** | leer lassen |
| **Hosts** | Sie selbst |

Lassen Sie alles andere bei Standardwerten. Klicken Sie auf
**Speichern**.

Die Sendung erscheint im Kalender als farbiger Block.

> **Wie es unter der Haube funktioniert.** Das Speichern
> des Formulars schreibt eine Zeile in `cc_show` (die
> Sendungsdefinition) und mindestens eine Zeile in
> `cc_show_instances` (jedes Vorkommen). Für eine einmalige
> Sendung wie diese erhalten Sie eine von jeder. Eine
> wiederkehrende Sendung erstellt die Instanzen eifrig bis
> zum konfigurierten Horizont (~3 Monate standardmäßig).

### 4.4 Die Sendung mit dem Track füllen

Kalender → klicken Sie auf die Sendung → **Tracks einplanen**.

Der Show-Builder öffnet sich mit der Sendung links und der
Bibliothek rechts. Ziehen Sie Ihren hochgeladenen Track aus
der Bibliothek auf die Sendung. Er erscheint als erstes
geplantes Item.

Klicken Sie auf **Speichern** oben im Show-Builder.

> **Operator-Tipp.** Sie können auch mit der rechten
> Maustaste auf eine leere Sendung im Kalender klicken und
> **Vorlage anwenden** wählen, um sie aus einer
> wiederverwendbaren [Sendungs-Vorlage](./SHOW_TEMPLATES.md)
> zu füllen, oder eine
> [Autoloading Playlist](./AUTOLOADING_PLAYLISTS.md)
> anhängen, sodass sich jede Instanz selbst füllt.

### 4.5 Warten, bis die Sendung beginnt

Zur Startzeit der Sendung:

1. Das **Now Playing**-Widget des Dashboards wechselt von
   "Fallback" (oder "Stille") zum Tracktitel.
2. Der Icecast-Stream unter
   `http://<station-host>:8000/rastatime` beginnt, Ihren
   Track zu spielen.
3. Der Füll-Balken des Kalenders für die Sendung wechselt
   von grau ("0 %") zu farbig ("100 %", wenn der Track den
   ganzen Slot gefüllt hat, weniger sonst).

Wenn etwas davon nicht passiert, deckt das
[`CRASH_RECOVERY`](../../operator/CRASH_RECOVERY.md)-Runbook
den diagnostischen Pfad ab.

---

## 5. Häufige Operationen am ersten Tag

Sie wissen jetzt genug, um die tägliche Arbeit zu erledigen.
Hier finden Sie jede gängige Aufgabe im Rest des Handbuchs:

| Ich möchte… | Gehen Sie zu |
|---|---|
| Eine Charge Tracks hochladen | [Bibliothek](./LIBRARY.md) |
| Morgen den Sendeplan planen | [Kalender](./CALENDAR.md) |
| Eine wöchentlich wiederkehrende Sendung erstellen | [Kalender](./CALENDAR.md) → Wiederkehrende Sendungen |
| Jede Woche dieselbe Sendungskonfiguration verwenden | [Sendungs-Vorlagen](./SHOW_TEMPLATES.md) |
| Eine Sendung sich selbst füllen lassen | [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) |
| Kalenderlücken automatisch füllen | [Auto DJ](./AUTO_DJ.md) |
| Die Station live über ein Mikrofon nehmen | [Dashboard](./DASHBOARD.md) → Live-Quelle |
| Den externen Icecast-Stream eines Gastes als Webstream hinzufügen | [Webstreams](./WEBSTREAMS.md) |
| Den Studiomixer als benannten Line-In hinzufügen | [Line-In](./LINE_IN.md) |
| Aufzeichnen, was heute auf Sendung war | [Aufnahme pro Sendung](./RECORD_PER_SHOW.md) |
| Einen zweiten Output-Stream hinzufügen (z.B. niedrige Bitrate für mobil) | [Streams](./STREAMS.md) |
| Einen neuen DJ hinzufügen | [Benutzer und Rollen](./USERS_AND_ROLES.md) |
| Die Sprache der Oberfläche ändern | [Sprachen](./I18N.md) |
| Tour durch das Einstellungs-Menü | [Einstellungen](./SETTINGS.md) |

---

## 6. Drei Gewohnheiten, um Schmerzen später zu vermeiden

Diese sind nicht optional. Sie werden Ihnen irgendwann
einen langen Abend ersparen.

1. **Verwenden Sie Sendungs-Vorlagen ab Tag zwei.** Wenn
   Sie zweimal denselben Namen / Hosts / Farben tippen,
   speichern Sie es als Vorlage. Hosts, die das lernen,
   schauen nie zurück.
   Siehe [Sendungs-Vorlagen](./SHOW_TEMPLATES.md).

2. **Stellen Sie den lokalen Import-Ordner ein.**
   Drag-and-Drop-Uploads über den Browser sind in Ordnung
   für ein oder zwei Dateien, aber ein Batch-Import von 200
   Tracks bringt den Browser zum Timeout und frustriert Sie.
   Der lokale Import-Ordner pollt das Verzeichnis auf dem
   Server alle 60 s und hat nie ein Timeout.
   Siehe [Lokale Maschine](./LOCAL_MACHINE.md).

3. **Machen Sie ein Backup am Tag, an dem Sie live gehen.**
   RASTATIME liefert ein Ein-Befehl-Backup-Skript mit, das
   die Datenbank, die hochgeladenen Medien und die Konfig
   erfasst. Stellen Sie es so ein, dass es nächtlich auf
   derselben Maschine läuft, und einmal pro Woche auf
   externen Speicher.
   Siehe [`docs/operator/BACKUP.md`](../../operator/BACKUP.md).

---

## Wohin als Nächstes

* Wenn Sie heute nur noch Zeit für ein weiteres Kapitel
  haben, lesen Sie [Kalender](./CALENDAR.md) — im Kalender
  werden Sie die meiste Zeit verbringen.
* Für den technischen Leser, der das System von Ende zu
  Ende verstehen möchte, bevor er weitermacht, gibt das
  [ARCHITECTURE](../../../RASTATIME_ARCHITECTURE_DRAFT_v0.1.md)-
  Dokument das Gesamtbild in einem Lesedurchgang.
* Für einen Operator, der zum ersten Mal live geht,
  arbeiten Sie auch
  [`docs/operator/INSTALL.md`](../../operator/INSTALL.md) §6
  ("Smoke-Test") durch, um zu bestätigen, dass jeder Dienst
  gesund ist, bevor Sie die Station ankündigen.
