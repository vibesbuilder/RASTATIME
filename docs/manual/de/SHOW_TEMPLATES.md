# Sendungs-Vorlagen

> **Wo Sie sich im Handbuch befinden.** Lesen Sie zuerst
> [Kalender](./CALENDAR.md), falls noch nicht geschehen —
> Sendungs-Vorlagen sind ein Beschleuniger auf dem
> Neue-Sendung-/Sendung-Bearbeiten-Formular des Kalenders.
>
> **Was diese Funktion ersetzt.** Vor 2026-05-19 war die
> einzige Abkürzung für "dieselben Sendungseinstellungen wie
> letzte Woche" das Kopieren einer wiederkehrenden Sendung.
> Sendungs-Vorlagen funktionieren sowohl für wiederkehrende
> als auch für einmalige Sendungen und überleben, nachdem
> die Quellsendung gelöscht wurde.

Eine **Sendungs-Vorlage** ist eine gespeicherte
Momentaufnahme der Feldwerte des Neue-Sendung-Formulars.
Wenn Sie eine Vorlage auf eine neue Sendung anwenden, wird
jedes erfasste Feld mit einem Klick vorausgefüllt. Wenn Sie
eine Sendung als Vorlage speichern, wird jedes Feld im
Formular erfasst (mit einigen bewussten Ausnahmen).

Vorlagen sind **stationsweit**: jeder Admin oder Program
Manager kann jede Vorlage anwenden oder bearbeiten. Die
Einstellungen einer Wochensendung werden einmal
gespeichert, und ein Kollege kann dieselbe Vorlage auf eine
andere Sendung stempeln.

---

## 1. Warum Vorlagen verwenden

Ohne Vorlagen dauert das Erstellen einer typischen
wiederkehrenden Musiksendung etwa 90 Sekunden
Formularausfüllung: Name, URL, Genre, Beschreibung, zwei
Hosts, Hintergrundfarbe, Textfarbe, Sendungs-Bild,
Autoloading Playlist, "Autoloading Playlist hinzufügen?",
Dauer. Stationen mit einem wöchentlichen Plan von 15-20
Sendungen haben 30 Minuten pro Woche damit verbracht,
dieselben Felder erneut einzugeben.

Mit Vorlagen sinkt das auf etwa 5 Sekunden pro Sendung:

1. Neue Sendung → wählen Sie **Vorlagen → Morgensendung**
   im Dropdown.
2. Setzen Sie die Startzeit.
3. **Speichern**.

---

## 2. Eine Vorlage erstellen

Zwei Wege:

### 2.1 Eine bestehende Sendung als Vorlage speichern

Öffnen Sie die Sendung im Kalender → **Als Vorlage
speichern** im Kontextmenü. Ein Dialog fragt nach:

| Feld | Hinweise |
|---|---|
| **Vorlagenname** | Eindeutig. Standardmäßig der aktuelle Sendungsname. Das Dropdown der nächsten Neue-Sendung zeigt diesen Namen. |

Klicken Sie **Speichern**. Die Vorlage wird aus dem
aktuellen Zustand des Sendungs-Bearbeitungsformulars
erstellt — jedes unten erfasste Feld wird *wie es zur
Speicherzeit ist* übernommen.

### 2.2 Das Neue-Sendung-Formular speichern, bevor die Sendung gespeichert wird

Innerhalb von Neue Sendung → füllen Sie die Felder aus, die
Sie erfassen möchten → erweitern Sie **Vorlagen** → klicken
Sie **Als Vorlage speichern**. Wählen Sie einen Namen. Die
Vorlage wird gespeichert, ohne dass bereits eine Sendung
erstellt wird.

> **Operator-Tipp.** Dies ist nützlich, wenn Sie eine
> Vorlage für "die Art von Sendung, die wir an Wochenenden
> machen" definieren möchten, bevor Sie tatsächlich eine
> erstellen müssen. Sie können auf diese Weise auch
> Teilvorlagen speichern — füllen Sie nur die Farben und
> Hosts aus, die Sie immer verwenden, und speichern Sie
> dann.

---

## 3. Eine Vorlage anwenden

Beim Erstellen einer neuen Sendung:

1. Neue Sendung → erweitern Sie **Vorlagen**.
2. Wählen Sie eine Vorlage im Dropdown **Vorlage
   auswählen**.
3. Klicken Sie **Anwenden**.
4. Die anderen Abschnitte des Formulars werden aus der
   Vorlage vorausgefüllt.
5. Bearbeiten Sie jedes Feld, das Sie überschreiben
   möchten, dann **Speichern** wie gewohnt.

Die Vorlage überschreibt jedes erfasste Feld. Felder, die
Sie bereits ausgefüllt haben, werden *ersetzt* — es gibt
kein "Mergen". Eine **Anwenden rückgängig**-Schaltfläche
erscheint für zehn Sekunden zum Zurücksetzen.

### Beim Anwenden einer Vorlage auf eine bestehende Sendung

Sie können auch eine Vorlage erneut auf eine bereits
bestehende Sendung anwenden, via **Vorlage anwenden** im
Kalender-Kontextmenü. Dies ist nützlich für "wir haben die
Hosts Mitten in der Saison geändert, wenden Sie die neue
Vorlage auf jede zukünftige Sendung an".

> **Warum nicht Vorlagen-Bearbeitungen automatisch
> propagieren?** RASTATIME 2026-05-19 wählte ein
> **Einweg-Stempel**-Modell. Das Bearbeiten einer Vorlage
> ändert nie Sendungen, die daraus erstellt wurden. Gründe:
>
> - Vorhersagbarkeit: Ein Operator, der eine Vorlage
>   bearbeitet, hätte keine Ahnung, wie viele bestehende
>   Sendungen sich still ändern würden.
> - Pro-Sendung-Übersteuerungen: Ein Operator, der die
>   Farbe einer Sendung nach Anwendung der Vorlage
>   geändert hat, würde die Übersteuerung verlieren, wenn
>   die Vorlage erneut propagiert.
> - Fehlerverhalten: Eine Vorlagen-Bearbeitung, die ein
>   Feld kaputt machte, würde jede Sendung mit dieser
>   Vorlage kaputt machen und Pro-Sendung-Bereinigung
>   erfordern.
>
> Wenn Sie bestehende Sendungen massenhaft aktualisieren
> müssen, verwenden Sie **Vorlage anwenden** auf jeder
> (oder das **Massenaktionen**-Menü — siehe
> [Kalender](./CALENDAR.md) §8). Siehe ARCHITECTURE §23.16
> für das vollständige Entscheidungsprotokoll.

### Beim Anwenden einer Vorlage auf ein Episoden-Bearbeitungsformular

Können Sie nicht. RASTATIME 2026-05-19 unterdrückt den
**Vorlagen**-Abschnitt im Dialog **Episode bearbeiten** (eine
Episode einer wiederkehrenden Sendung). Das erneute
Stempeln einer einzelnen Episode würde entweder still auf
Geschwister propagieren (verletzt das Einweg-Stempel-Modell)
oder keinen Effekt auf sie haben (was den Operator in die
Irre führen würde).

Wenn Sie eine Episode übersteuern müssen, bearbeiten Sie
deren Felder direkt, ohne den Vorlagen-Pfad zu verwenden.

---

## 4. Was eine Vorlage erfasst

Diese Felder werden in der JSONB-Momentaufnahme der Vorlage
gespeichert:

| Gruppe | Felder |
|---|---|
| **Identität** | Sendungsname (wird als Standard für die nächste Neue-Sendung verwendet), URL, Genre, Beschreibung |
| **Visuals** | Hintergrundfarbe, Textfarbe, Referenz auf Sendungs-Bild |
| **Dauer** | Standardlänge |
| **Wiederholungen** | Wiederholungstyp, Wiederholungstage, Enddatum / Kein-Ende-Flag |
| **Aufnahme** | Aufnahme aktiviert (ja/nein) |
| **Autoloading Playlist** | Playlist-ID, Intro-Playlist-ID, Outro-Playlist-ID, "Wiederholen bis voll"-Flag |
| **Auth** | Host-Benutzernamen (NICHT das Pro-Sendung-Live-Stream-Passwort — siehe unten) |
| **Show-DJ-Quelle** | Pro-Sendung-Live-Stream erlaubt (ja/nein) |

### Was eine Vorlage NICHT erfasst

Bewusst ausgeschlossen:

| Feld | Grund |
|---|---|
| **Startdatum / Startzeit** | Pro-Verwendung; die Vorlage ist über viele Startzeiten wiederverwendbar. |
| **Live-Stream-Passwort** | Sicherheit — eine gespeicherte Vorlage sollte keine Zugangsdaten enthalten. Der Operator setzt das Passwort pro Sendung. |
| **Episoden-Beschreibungen** | Episodenspezifisch (z.B. "diese Woche ist der Gast X"). |

> **Wie es unter der Haube funktioniert.** Vorlagen leben in
> der Tabelle `cc_show_template` (`id`, `name UNIQUE`,
> `template_data JSONB`, `created_at`, `updated_at`). Der
> PHP-Service `Application_Service_ShowTemplateService`
> besitzt CRUD via 5 JSON-Aktionen, die auf
> `ScheduleController` registriert sind. Zur Anwendungszeit
> wird das JSONB der Vorlage in das Array gefaltet, das
> `populateForm()` konsumiert. Schema-Drift wird toleriert:
> eine Vorlage, der ein Feld zur Anwendungszeit fehlt, fällt
> auf den Formular-Standard zurück; eine Vorlage, die ein
> unbekanntes Feld trägt, wird still ignoriert.

### Sendungs-Bild als Referenz, nicht als Kopie gespeichert

Wenn eine Vorlage ein Sendungs-Bild erfasst, wird nur der
Pfad zur bestehenden Bilddatei gespeichert — keine Kopie der
Bild-Bytes. Dies war ein bewusster Trade-off:

- Pro: Speicherverbrauch bleibt flach, unabhängig davon,
  wie viele Sendungen aus einer Vorlage gestempelt werden.
- Contra: Das Löschen des Quell-Bildes (z.B. aus
  `C:\rastatime\media\<owner>\.../show-logo.png`) lässt die
  Vorlage (und jede daraus gestempelte Sendung) ohne Bild
  zurück.

Wenn Sie ein Sendungs-Bild löschen oder verschieben, laden
Sie es unter demselben Pfad erneut hoch oder speichern Sie
die Vorlage mit einem aktuellen Bild erneut.

---

## 5. Eine Vorlage umbenennen oder löschen

Zwei Wege:

### 5.1 Aus der Seite Einstellungen → Sendungs-Vorlagen

Einstellungen → **Sendungs-Vorlagen** öffnet eine Liste
jeder Vorlage der Station. Jede Zeile hat:

| Spalte | Aktion |
|---|---|
| **Name** | Klicken zum Umbenennen. Der neue Name muss eindeutig sein. |
| **Zuletzt aktualisiert** | Sortierbar. |
| **Verwendet von** | Eine Zählung der Sendungen, die diese Vorlage derzeit verwenden (informativ; Vorlagen "tracken" die Nutzung nicht rückwirkend). |
| **Bearbeiten** | Das JSON der Vorlage in einem Read-only-Viewer öffnen — nützlich für den technischen Leser, um zu überprüfen, was erfasst wurde. |
| **Löschen** | Bestätigt, dann wird die Vorlage entfernt. Aus ihr gestempelte Sendungen sind nicht betroffen. |

> **Operator-Tipp.** Die Einstellungsseite ist der einfachste
> Weg, eine Vorlage nach einem Tippfehler umzubenennen. Das
> Umbenennen via **Als Vorlage speichern** des
> Neue-Sendung-Formulars mit demselben Namen wie eine
> bestehende Vorlage fragt nach **Überschreiben?** — leicht
> versehentlich zu tun.

### 5.2 Aus dem Neue-Sendung-/Sendung-Bearbeiten-Dialog

Erweitern Sie **Vorlagen** → wählen Sie die Vorlage im
Dropdown → ein **Bearbeiten**-Symbol erscheint neben dem
Dropdown → öffnet den Umbenennen/Löschen-Dialog inline.

---

## 6. Überschreibungs-bei-Duplikat-Verhalten

Wenn Sie eine neue Vorlage mit einem Namen speichern, der
bereits existiert, gibt die Speicheranfrage eine
409-Konflikt-artige Antwort zurück und die Oberfläche fragt:

> **Eine Vorlage namens "Morgensendung" existiert bereits.
> Überschreiben?**

| Klicken Sie | Effekt |
|---|---|
| **Abbrechen** | Die neue Vorlage verwerfen; die bestehende bleibt unverändert. |
| **Überschreiben** | Das `template_data` der bestehenden Vorlage durch die aktuellen Formularwerte ersetzen. `updated_at` wird erhöht. Der Name bleibt unverändert. |

> **Wie es unter der Haube funktioniert.** Der API-Endpunkt
> `Schedule/save-show-template` gibt `{ "conflict": true,
> "template_id": <existing> }` statt `{ "ok": true }` bei
> Namenskollision zurück. Das JS in `add-show.js` zeigt die
> Aufforderung und sendet erneut mit `overwrite=true`, wenn
> der Operator bestätigt. Ohne Überschreiben bleibt die
> bestehende Zeile intakt.

---

## 7. Worked Example: eine wöchentliche Morgensendung

Eine Station betreibt **Morgensendung** Mo-Fr 07:00–10:00
mit:

- Hosts: Anna + Ben
- Hintergrundfarbe: dunkelblau
- Textfarbe: weiß
- Sendungs-Bild: morgensendung-logo.png
- Autoloading Playlist: "Morgensendung-Playlist" mit Intro
  + Outro
- Aufnahme aktiviert
- Live-Stream erlaubt für Gast-Host mittwochs

**Erstes Mal:**

1. Montags-Sendung erstellen: Neue Sendung, alle Felder
   ausfüllen, speichern.
2. Montags-Sendung öffnen → **Als Vorlage speichern** →
   `Morgensendung` benennen.

**Für Dienstag, Mittwoch, Donnerstag, Freitag:**

1. Neue Sendung → Vorlagen → **Morgensendung** → Anwenden.
2. Startdatum setzen.
3. Speichern.

**Oder für eine wiederkehrende Sendungsdefinition
(bevorzugt):**

1. Neue Sendung → Vorlagen → **Morgensendung** → Anwenden.
2. Startdatum setzen.
3. **Wiederholt sich** ankreuzen → Wöchentlich → Mo, Di,
   Mi, Do, Fr.
4. Speichern.

Dies erzeugt alle fünf Tage als Episoden einer
wiederkehrenden Sendungsdefinition. Das Bearbeiten der
Sendungsdefinition später ändert alle fünf.

---

## 8. Häufig gestellte Fragen

### "Kann ich eine Vorlage erstellen, die nur die Farben hat, keine anderen Felder?"

Ja. Öffnen Sie ein leeres Neue-Sendung-Formular, füllen Sie
nur Hintergrund- und Textfarbe aus, dann **Als Vorlage
speichern** mit einem Namen wie `Farbe: Dunkelblau`. Bei
Anwendung werden nur diese beiden Felder überschrieben;
alles andere bleibt bei Formular-Standards.

### "Kann ein DJ Vorlagen speichern / anwenden?"

Nein. Vorlagen stecken im Sendungsdialog, und Sendungen
legen nur Program Manager und Admins an und bearbeiten sie;
diese speichern, benennen und löschen auch die Vorlagen,
im Dialog und auf der Übersichtsseite Einstellungen →
Show Templates.

### "Ich habe die Hostliste in der Vorlage geändert — warum sind bestehende Sendungen unverändert?"

Per Design — siehe §3, "Warum nicht
Vorlagen-Bearbeitungen automatisch propagieren?". Verwenden
Sie **Vorlage anwenden** auf jeder bestehenden Sendung, die
die Änderung erben soll.

### "Kann ich eine Vorlage exportieren, um sie auf einer anderen Station zu verwenden?"

Nicht über die Oberfläche. Die technische Umgehung:
`SELECT * FROM cc_show_template WHERE name = 'Morgensendung'`
auf der Quellstation, dann
`INSERT … ON CONFLICT DO NOTHING` auf der Zielstation.
Beachten Sie, dass referenzierte Playlist-IDs und Bildpfade
stationsübergreifend nicht aufgelöst werden.

### "Was ist die maximale Anzahl von Vorlagen?"

Es gibt kein hartes Limit. Das **Vorlagen**-Dropdown im
Neue-Sendung-Formular scrollt, wenn es mehr als 20 Einträge
gibt. Stationen mit 50+ Vorlagen möchten möglicherweise
eine Namens-Präfix-Konvention verwenden (`Musik — Pop`,
`Musik — Jazz`, `Nachrichten — Stündlich`).

---

## Wohin als Nächstes

* [Kalender](./CALENDAR.md) — wo Vorlagen angewendet werden.
* [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) — der
  häufigste Grund, warum Vorlagen nützlich sind.
* [Einstellungen](./SETTINGS.md) — Tour durch jede
  Einstellungs-Unterseite einschließlich Sendungs-Vorlagen.
