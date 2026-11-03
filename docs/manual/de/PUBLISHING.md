# Veröffentlichung: Redaktionsteam, Episoden, Teilnehmende

> **Wo Sie sich im Handbuch befinden.** Einstellungen →
> **Redaktionsteam**; Kalender → Sendungsformular, Abschnitt
> **Veröffentlichung**; Kalender → Rechtsklick auf eine Instanz →
> **Episode...**; Statistiken → **Teilnehmende** (in der englischen
> Oberfläche Settings → Editorial Team, Publishing, Episode...,
> Analytics → Participants).  Lesen Sie zuerst [Kalender](./CALENDAR.md)
> und [Aufnahme pro Sendung](./RECORD_PER_SHOW.md) - der Ton einer
> Episode ist die Aufzeichnung der Sendung.
>
> **Was diese Funktion vorbereitet.** Jede Episode ohne Hochladen von
> Hand auf [cba.media](https://cba.media) veröffentlichen (dem Archiv
> der österreichischen Freien Radios), und die jährliche Zählung der
> Menschen, die das Programm machen.

Seit 2026-11-03 hält RASTATIME die Daten, die eine veröffentlichte
Episode braucht: wer eine Sendung macht, die Vorgaben ihres Podcasts auf
cba.media und je Episode Titel, Teaser, Beschreibung und ein optionales
Bild.  Dieselben Daten speisen die Übersicht **Teilnehmende** für die
Jahresstatistik.

**Es wird noch nichts hochgeladen.**  Das Senden der Episoden an
cba.media - von Hand aus dem Kalender und automatisch nach der
Aufzeichnung - folgt in den nächsten Stufen; dieses Kapitel wächst mit.

Eine *Episode* ist eine Instanz einer Sendung im Kalender: die
„Morgensendung" am nächsten Montag ist eine Episode, die am Montag
darauf die nächste.

---

## 1. Profile des Redaktionsteams

**Einstellungen → Redaktionsteam** listet die Menschen hinter den
Sendungen.

| Feld | Bedeutung |
|---|---|
| **Name** | So, wie er auf cba.media und in der Statistik erscheinen soll. |
| **E-Mail (optional)** | Für Ihre eigene Übersicht. |
| **Benutzer (optional)** | Verknüpft das Profil mit einem RASTATIME-Login. Ein Profil braucht kein Login - die meisten Redakteur:innen melden sich nie an. |
| **Aktiv** | Nur aktive Profile werden im Sendungsformular angeboten.  Ein abgeschaltetes Profil bleibt in den Sendungen, zu denen es schon gehört. |

**Ändern** lädt das Profil in das Formular über der Tabelle;
**Löschen** entfernt das Profil nach einer Rückfrage aus dem Team jeder
Sendung.  Die Spalte **Sendungen** zählt, zu wie vielen Sendungen ein
Profil gehört.

Programm-Manager und Admins öffnen diese Seite.

---

## 2. Vorgaben der Sendung: Abschnitt „Veröffentlichung"

Bearbeiten Sie eine Sendung (Kalender → Rechtsklick → **Sendung
bearbeiten**, oder eine neue Sendung) und öffnen Sie den Abschnitt
**Veröffentlichung** zwischen **Who** und **Style**.  Die Werte gelten
für jede Episode der Sendung, solange eine Episode keine eigenen setzt.

| Feld | Bedeutung |
|---|---|
| **Redaktionsteam** | Die Profile der Menschen hinter der Sendung ankreuzen. Sie gehen als Redakteur:innen an cba.media und erscheinen in der Übersicht Teilnehmende. |
| **Teilnehmende** | Wie viele Menschen üblicherweise an einer Episode mitwirken (0-999). Zählt in Statistiken → Teilnehmende. |
| **CBA-Podcast-ID** | Die Nummer des Podcasts (Serie) auf cba.media, zu dem die Episoden gehören. |
| **Lizenz** | Standardlizenz der Episoden: Alle Rechte vorbehalten, CC BY-NC-ND, CC BY-ND, CC BY-NC, CC BY-SA, CC BY, CC0, Gemeinfrei. |
| **CBA-Themen-ID** | Die Nummer des Themas (Kategorie) auf cba.media. |
| **Sprachen** | Bis zu drei Sprachcodes, z. B. `de, en`. |
| **Schlagworte** | Schlagworte für cba.media, durch Komma getrennt. |
| **Standard-Teaser** | Gilt für jede Episode ohne eigenen Teaser. |
| **Enthält urheberrechtlich geschützte Musik (AKM)** | Die Episoden enthalten üblicherweise geschützte Musik. |

In **Instanz bearbeiten** fehlt der Abschnitt: er gehört zur ganzen
Sendung.  Die Daten einer einzelnen Episode bearbeiten Sie im Dialog
**Episode...** (§3).

> **Woher kommen die CBA-Nummern?**  Öffnen Sie den Podcast oder das
> Thema auf cba.media; die Nummer steht in der Adresse oder auf der
> Seite.  Die nächste Stufe bietet eine Auswahlliste an.

---

## 3. Episodendaten: „Episode..."

Rechtsklick auf eine Instanz im Kalender → **Episode...**.  Der Eintrag
steht vor und nach der Sendung zur Verfügung - das Bild können Sie auch
nach der Ausstrahlung setzen - für Admins, Programm-Manager und die
Hosts der Sendung.

| Feld | Bedeutung |
|---|---|
| **Titel** | Leer: Name der Sendung und Datum, grau als Vorschlag angezeigt. |
| **Teaser** | Eine kurze Zusammenfassung. Leer: der Standard-Teaser der Sendung. |
| **Beschreibung** | Der Text der Episode - dasselbe Feld wie **Episode Beschreibung** im Sendungsformular. |
| **Teilnehmende** | Nur wenn diese Episode von der Sendung abweicht, z. B. mit Gästen. Der Wert der Sendung steht grau im Feld. |
| **Episodenbild** | Optional, JPG oder PNG bis 10 MB. Die Auswahl einer Datei lädt sie sofort hoch; **Bild entfernen** löscht sie. Ohne Bild zeigt cba.media das Bild des Podcasts. |
| **Bildlizenz** / **Bildunterschrift** | Lizenz und Bildnachweis (z. B. wer fotografiert hat). |

Die rechte Spalte zeigt außerdem, was die Episode von der Sendung
übernimmt (Redaktionsteam, CBA-Podcast-ID, Lizenz), und die Zeile oben
sagt, ob die Episode gesendet wurde und ob ihre Aufzeichnung in der
Library liegt.

**Speichern** sichert die Textfelder; das Bild wird gespeichert, sobald
Sie es wählen.  Episodenbilder liegen im Library-Ordner unter
`imported/episode-images/<Instanz>/` und gehören zum Medien-Spiegel des
[Backups](./BACKUP.md).

> **Nah an der Sendung planen.**  Ändert sich das Wiederholungsmuster
> einer Sendung, legt der Kalender ihre künftigen Instanzen neu an, und
> deren Episodendaten gehen mit.  Tragen Sie Titel und Bilder für die
> nächsten Wochen ein, nicht Monate im Voraus.

---

## 4. Übersicht Teilnehmende

**Statistiken → Teilnehmende** zählt die Teilnehmenden je Sendung und
Jahr (Stationszeit) - die Zahlen für die Jahresstatistik.

* **Jahr** - das laufende Jahr zeigt den Stand bis heute.
* **Nur Sendungen ohne Wert** - die Sendungen, die gelaufen sind, aber
  noch keine *Teilnehmende* haben.  Arbeiten Sie diese Liste einmal
  durch; setzen Sie `0` für automatisierte oder übernommene Programme.
* **CSV herunterladen** - Tabelle und Summen als Tabellen-Datei.

Gezählt werden die Episoden, die im Jahr **gesendet** wurden (beendet,
nicht gelöscht).  Rebroadcasts der alten LibreTime-Art bleiben außen
vor; Sendungen, die als [Wiederholung einer anderen Sendung](./CALENDAR.md)
angelegt sind, stehen mit dem Merkmal **Wiederholung** in der Liste -
setzen Sie ihren Wert auf `0`, wenn ihre Menschen schon im Original
zählen.

| Spalte / Summe | Bedeutung |
|---|---|
| **Gesendete Episoden** | Episoden der Sendung im Jahr. |
| **Teilnehmende** | Der Wert der Sendung; die Summe addiert die Werte aller Sendungen. |
| **Episoden mit eigenem Wert** | Episoden, deren Dialog eine andere Zahl setzt. |
| **Teilnahmen** | Die Teilnehmenden jeder Episode zusammengezählt (eine Episode mit eigenem Wert zählt mit diesem Wert). |
| **Redaktions-Profile** (Summe) | Verschiedene Profile in den Teams der gesendeten Sendungen - jede Person einmal. |
| **Sendungen ohne Wert** (Summe) | Orange, solange es welche gibt. |

Wer in mehreren Sendungen mitwirkt, zählt bei **Teilnehmende** einmal
je Sendung; die Profil-Summe zählt jede Person einmal.

Programm-Manager und Admins öffnen diese Seite.

---

## 5. Häufige Fragen

### „Ich habe Profile angekreuzt, aber sie erscheinen nicht in der Übersicht."

Die Übersicht listet nur Sendungen, die im gewählten Jahr **gesendet**
wurden.  Eine neue Sendung erscheint, sobald ihre erste Episode zu Ende
ist.

### „Der Abschnitt Veröffentlichung fehlt oder ist grau."

In **Instanz bearbeiten** fehlt er - der Abschnitt gehört zur ganzen
Sendung; für eine Episode nehmen Sie **Episode...**.  Grau ist er, wenn
Sie nicht Programm-Manager oder Admin sind.

### „Episode... fehlt im Menü."

Der Eintrag erscheint für Admins, Programm-Manager und die Hosts der
Sendung, und nicht bei Rebroadcast-Instanzen der alten LibreTime-Art.

---

## Wie es weitergeht

* [Kalender](./CALENDAR.md) - das Sendungsformular und das Kontextmenü.
* [Aufnahme pro Sendung](./RECORD_PER_SHOW.md) - die Aufzeichnung, die
  zum Ton der Episode wird.
* [Analytics](./ANALYTICS.md) - die anderen Statistik-Seiten.
* [Einstellungen](./SETTINGS.md) - jede Seite des Einstellungen-Menüs.
