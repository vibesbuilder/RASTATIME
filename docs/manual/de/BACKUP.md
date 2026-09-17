# Backup

> **Wo Sie sich im Handbuch befinden.** Dieses Kapitel behandelt die
> Seite Settings → **Backup**: Sicherungen von Datenbank und
> Konfiguration per Klick in einen Ordner Ihrer Wahl, und deren
> Download über den Browser.  Das Wiederherstellen einer Sicherung ist
> ein bewusster Offline-Vorgang und für Administratoren in
> `docs/operator/BACKUP.md` dokumentiert — es ist kein Knopf.

Alles, was RASTATIME weiß — Shows, Sendeplan, Bibliotheks-Metadaten,
Benutzer, Einstellungen — liegt in der PostgreSQL-Datenbank; die
Dienst-Passwörter und Ports liegen in einigen Konfigurationsdateien.
Die Seite **Backup** schreibt beides in ein einzelnes, in sich
vollständiges ZIP pro Lauf.

Die Medienbibliothek (die Audiodateien selbst) wird nie gezippt — sie
umfasst viele Gigabyte.  Aktivieren Sie stattdessen **Include media
library**, dann wird sie serverseitig neben den ZIPs gespiegelt;
siehe Abschnitt 3.

## 1. Der Backup-Ordner

Geben Sie einen absoluten Pfad auf einem lokalen Laufwerk ein, zum
Beispiel `D:\rastatime-backups`, und klicken Sie **Check** und **Save
settings**.

- Der Ordner wird angelegt, falls er nicht existiert.
- Er darf nicht innerhalb der Medienbibliothek liegen.
- Idealerweise liegt er auf einem **anderen Laufwerk** als die
  Datenbank, damit eine ausfallende Platte nicht beides mitnimmt.
- Netzwerkpfade werden nicht unterstützt.

## 2. Jetzt sichern

**Back up now** startet die Sicherung auf dem Server und meldet sich
unter den Knöpfen; wenige Sekunden später erscheint die neue Datei
unter **Existing backups**.  Jede Sicherung ist ein ZIP, benannt nach
ihrer Erstellzeit:

```
rastatime-backup-2026-09-16T1830.zip
    db.dump          die vollständige Datenbank (pg_dump, Custom-Format)
    config/…         jede Konfigurationsdatei (libretime.conf, …)
    manifest.json    was enthalten ist, erstellt wann, mit welchem pg_dump
```

Eine fehlgeschlagene Sicherung (etwa weil PostgreSQL nicht erreichbar
ist) hinterlässt **kein** halb geschriebenes ZIP; die Meldung unter den
Knöpfen nennt den Grund.  Eine durch einen Dienst-Neustart
unterbrochene Sicherung wird als unterbrochen angezeigt — starten Sie
sie einfach erneut.

## 3. Die Medienbibliothek einbeziehen

Setzen Sie das Häkchen **Include media library** und klicken Sie
**Save settings**.  Von da an synchronisiert jeder Lauf zusätzlich die
Bibliothek in den Unterordner `media` neben den ZIPs:

- **Inkrementell.**  Nur neue und geänderte Dateien werden kopiert;
  Dateien, die Sie aus der Bibliothek gelöscht haben, verschwinden
  auch aus dem Spiegel.  Der Spiegel ist immer *die aktuelle*
  Bibliothek, keine Historie.
- **Verifiziert.**  Nach jedem Lauf wird jede Bibliotheksdatei gegen
  den Spiegel geprüft (Existenz und Größe); eine Abweichung lässt die
  Sicherung fehlschlagen.
- **Erster Lauf.**  Kopiert alles und kann dauern — der
  Fortschrittsbalken zeigt den Stand.  **Cancel** stoppt den Spiegel
  (das Datenbank-ZIP ist zu dem Zeitpunkt bereits vollständig); der
  nächste Lauf setzt einfach dort fort.

Der Spiegel wandert nie durch den Browser.  Zum Wiederherstellen der
Medien kopieren Sie den Inhalt von `media` zurück in die
Bibliotheks-Wurzel, die unter [Lokale Maschine](./LOCAL_MACHINE.md)
angezeigt wird.

## 4. Vorhandene Sicherungen

Die Tabelle listet jede Sicherung im Ordner, neueste zuerst, mit Größe
und Erstellzeit.  **Download** speichert das ZIP über den Browser —
nützlich für eine Kopie außerhalb der Maschine.  Die Dateien auf der
Platte bleiben unangetastet; löschen Sie alte von Hand, wenn Sie sie
nicht mehr brauchen.

## 5. Automatische Sicherungen

Setzen Sie **Enable automatic backups**, wählen Sie die Häufigkeit
(**Run every** N Tage) und die Aufbewahrung (**Keep backups for** N
Tage, 0 = alles behalten), dann **Save automatic backups**.

Das Uhrwerk ist eine Windows-Aufgabe, die ein Administrator **einmal**
registriert (erhöhte PowerShell):

```powershell
$action  = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File C:\RASTATIME\scripts\backup-auto.ps1"
$trigger = New-ScheduledTaskTrigger -Daily -At 03:30
Register-ScheduledTask -TaskName "RASTATIME-Backup" -Action $action `
    -Trigger $trigger -User "SYSTEM" -RunLevel Highest
```

Die Aufgabe feuert täglich, aber der Lauf entscheidet anhand der
Einstellungen dieser Seite selbst, ob eine Sicherung fällig ist — „alle
7 Tage" funktioniert also mit einer täglichen Aufgabe.  Jeder Lauf
nutzt denselben Ordner und dieselbe Medien-Einstellung wie die manuelle
Sicherung, protokolliert sein Ergebnis in `logs\backup-auto.log` und
löscht danach ZIPs, die älter als die Aufbewahrung sind.  Die neueste
Sicherung überlebt immer, egal wie alt; der Medien-Spiegel ist ein
einzelner Spiegel und wird nie aufgeräumt.

## 6. Wiederherstellen

Das Wiederherstellen ersetzt die laufende Datenbank und ist deshalb
ein bewusster, dokumentierter Offline-Vorgang — Dienste stoppen,
Datenbank mit `pg_restore` wiederherstellen, Dienste starten.  Folgen
Sie `docs/operator/BACKUP.md`, Abschnitt 7.  Die `db.dump` im ZIP ist
genau das, was `pg_restore` erwartet.

## 7. Bewährte Praxis

- Sichern Sie vor allem, was Sie ungern noch einmal machen würden:
  Massenlöschungen, große Sendeplan-Änderungen, Versions-Updates.
- Laden Sie ab und zu eine Kopie auf eine andere Maschine herunter —
  eine Sicherung auf demselben Rechner überlebt diesen Rechner nicht.
- Die Konfigurationsdateien im ZIP enthalten Dienst-Passwörter.
  Behandeln Sie heruntergeladene Sicherungen wie die Passwörter, die
  sie enthalten.
