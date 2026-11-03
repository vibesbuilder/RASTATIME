# Archivierung: Redaktionsteam, Episoden, Online-Archiv, Teilnehmende

> **Wo Sie sich im Handbuch befinden.** Einstellungen →
> **Redaktionsteam** und **CBA-Konten**; Kalender → Sendungsformular,
> Abschnitt **Archivierung**; Kalender → Rechtsklick auf eine Instanz →
> **Episode...**; Statistiken → **Teilnehmende** (in der englischen
> Oberfläche Settings → Editorial Team / CBA Accounts, Archiving,
> Episode..., Analytics → Participants).  Lesen Sie zuerst
> [Kalender](./CALENDAR.md) und [Aufnahme pro Sendung](./RECORD_PER_SHOW.md)
> - der Ton einer archivierten Episode ist die Aufzeichnung der Sendung.
>
> **Was diese Funktion macht.** Sie archiviert die Episoden Ihrer
> Sendungen auf [cba.media](https://cba.media) (dem Archiv der
> österreichischen Freien Radios), ohne dass Sie sie von Hand
> hochladen, und zählt die Menschen, die das Programm machen, für die
> Jahresstatistik.
>
> **Warum „Archivierung".** „Veröffentlichen" bedeutet in RASTATIME den
> Stations-Podcast (My Podcast).  Eine Episode auf cba.media zu bringen
> heißt deshalb *online archivieren*, damit beides auseinanderbleibt.

Eine *Episode* ist eine Instanz einer Sendung im Kalender: die
„Morgensendung" am nächsten Montag ist eine Episode, die am Montag
darauf die nächste.

**Stand der Stufen.**

| Stufe | Was | Stand |
|---|---|---|
| 1 | Redaktionsteam, Vorgaben der Sendung, Episodendaten, Teilnehmende | seit 2026-11-03 |
| 2 | Eine Episode von Hand aus dem Kalender online archivieren | seit 2026-11-03 |
| 3 | Jede Episode nach der Aufzeichnung automatisch archivieren | seit 2026-11-03 |

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

## 2. CBA-Konten

Jede Sendung wird unter einem cba.media-Benutzer archiviert - die
Episoden erscheinen unter dessen Namen.  **Einstellungen → CBA-Konten**
hält diese Benutzer; nur Admins öffnen die Seite.

| Feld | Bedeutung |
|---|---|
| **Kontoname** | Ihr Name für das Konto, z. B. die Person oder der Sender. |
| **CBA-Benutzername** | Der Benutzername auf cba.media. |
| **Anwendungspasswort** | Wird auf cba.media im Profil des Benutzers angelegt (WordPress-*Anwendungspasswort*, nicht das Login-Passwort). RASTATIME speichert es und zeigt es nie wieder an; ein leeres Feld behält das gespeicherte. |

* **Verbindung testen** fragt bei cba.media mit den gespeicherten Daten
  nach, wer der Benutzer ist und ob er hochladen darf (Rollen admin,
  author, podcaster, stationmanager, channelmanager).  Hochgeladen wird
  dabei nichts.
* **Löschen** entfernt das Konto; Sendungen, die es nutzen, haben dann
  kein Konto mehr, bis Sie ein anderes wählen.
* **Upload-Grenze** - der Upload teilt sich die Internetleitung mit den
  Hörer-Streams, deshalb sendet RASTATIME höchstens mit dieser Rate
  (Standard 4 Mbit/s: eine Stunde Audio mit 320 kbit/s braucht etwa
  fünf Minuten).
* **Automatisches Archivieren** - wie viele Minuten nach dem Ende einer
  Episode die Sendungen mit *Automatisch archivieren* (§3) sie hochladen
  (Standard 30): Zeit, die Episode zu vervollständigen oder *Diese
  Episode nicht automatisch archivieren* anzuhaken.

---

## 3. Vorgaben der Sendung: Abschnitt „Archivierung"

Bearbeiten Sie eine Sendung (Kalender → Rechtsklick → **Sendung
bearbeiten**, oder eine neue Sendung) und öffnen Sie den Abschnitt
**Archivierung** zwischen **Who** und **Style**.  Die Werte gelten für
jede Episode der Sendung, solange eine Episode keine eigenen setzt.

| Feld | Bedeutung |
|---|---|
| **Redaktionsteam** | Die Profile der Menschen hinter der Sendung ankreuzen. Sie gehen als Redakteur:innen an cba.media und erscheinen in der Übersicht Teilnehmende. |
| **Teilnehmende** | Wie viele Menschen üblicherweise an einer Episode mitwirken (0-999). Zählt in Statistiken → Teilnehmende. |
| **CBA-Konto** | Der CBA-Benutzer, unter dem die Episoden archiviert werden (§2). |
| **Sichtbarkeit auf cba.media** | *Öffentlich* (gelistet), *Ungelistet* (nur über die Adresse erreichbar) oder *Privat* (nur für den CBA-Benutzer sichtbar). |
| **CBA-Podcast-ID** | Die Nummer des Podcasts (Serie) auf cba.media, zu dem die Episoden gehören. Ohne sie hält cba.media den Beitrag privat. |
| **Lizenz** | Lizenz der Episoden. Das Hilfe-Symbol zeigt, welche Lizenz die Fragen des CBA-Webformulars beantwortet (siehe unten). |
| **CBA-Thema** | Das Thema (Kategorie) auf cba.media, aus der Liste, die RASTATIME einmal am Tag holt. Vor dem ersten Abruf nimmt das Feld die Nummer. |
| **Sprachen** | Bis zu drei Sprachcodes, die die CBA kennt, z. B. `de, en`. |
| **Schlagworte** | Schlagworte für cba.media, durch Komma getrennt. |
| **Standard-Teaser** | Gilt für jede Episode ohne eigenen Teaser. |
| **Enthält urheberrechtlich geschützte Musik (AKM)** | Die Episoden enthalten üblicherweise geschützte Musik; cba.media schränkt dann den Download ein. |
| **Automatisch archivieren** | Jede neue Episode von selbst auf cba.media archivieren (§5, *Automatisch*). Braucht CBA-Konto, Thema, Sprache und Lizenz; neben dem Kästchen steht, seit wann es eingeschaltet ist. Hat die Sendung keine Beschreibung, weist ein Hinweis unter dem Kästchen darauf hin, dass dann jede Episode eine eigene braucht. |

**Welche Lizenz?**  Das CBA-Webformular stellt drei Fragen; die Lizenz
beantwortet sie:

| Lizenz | Autor nennen? | Kommerzielle Nutzung? | Bearbeitung? |
|---|---|---|---|
| CC BY | ja | ja | ja |
| CC BY-NC | ja | nein | ja |
| CC BY-ND | ja | ja | nein |
| CC BY-NC-ND | ja | nein | nein |
| CC0 | nein | ja | ja |

*Alle Rechte vorbehalten* erlaubt nichts davon ohne Rückfrage;
*CC Sampling+* lässt Ausschnitte weiterverwenden, das ganze Werk nur
nicht-kommerziell; *Gemeinfrei* behält keinerlei Rechte.

In **Instanz bearbeiten** fehlt der Abschnitt: er gehört zur ganzen
Sendung.  Die Daten einer einzelnen Episode bearbeiten Sie unter
**Episode...** (§4).

> **Woher kommt die Podcast-Nummer?**  Öffnen Sie den Podcast auf
> cba.media; die Nummer steht in der Adresse oder auf der Seite (die
> CBA listet die Podcasts einer Station nur angemeldeten Benutzern).

---

## 4. Episodendaten: „Episode..."

Rechtsklick auf eine Instanz im Kalender → **Episode...**.  Der Eintrag
steht vor und nach der Sendung zur Verfügung - das Bild können Sie auch
nach der Ausstrahlung setzen - für Admins, Programm-Manager und die
Hosts der Sendung.

| Feld | Bedeutung |
|---|---|
| **Titel** | Leer: Name der Sendung und Datum, grau als Vorschlag angezeigt. |
| **Teaser** | Eine kurze Zusammenfassung. Leer: der Standard-Teaser der Sendung. |
| **Beschreibung** | Der Text der Episode, auf cba.media der Text des Beitrags. Leer: die Beschreibung der Sendung. Hier ist die einzige Stelle dafür (Instanz bearbeiten zeigt das Feld nicht mehr). |
| **Teilnehmende** | Nur wenn diese Episode von der Sendung abweicht, z. B. mit Gästen. Der Wert der Sendung steht grau im Feld. |
| **Produktionsdatum** | Von cba.media verlangt. Leer: der Sendetag. Setzen Sie es, wenn die Episode früher produziert wurde. |
| **Diese Episode nicht automatisch archivieren** | Für Tests, ausgefallene Episoden oder Rechteprobleme. Wirkt mit der automatischen Archivierung (§5); von Hand archivieren bleibt möglich. |
| **Episodenbild** | Optional, JPG oder PNG bis 10 MB. Die Auswahl einer Datei lädt sie sofort hoch; **Bild entfernen** löscht sie. Ohne Bild zeigt cba.media das Bild des Podcasts. |
| **Bildlizenz** / **Bildunterschrift** | Lizenz und Bildnachweis (z. B. wer fotografiert hat), Bildunterschrift bis 500 Zeichen. |

Die rechte Spalte zeigt, was die Episode von der Sendung übernimmt
(Redaktionsteam, CBA-Konto, Podcast, Lizenz, Sichtbarkeit); die Zeile
oben sagt, ob die Episode gesendet wurde und ob ihre Aufzeichnung in
der Library liegt.

**Speichern** sichert die Textfelder; das Bild wird gespeichert, sobald
Sie es wählen.  Episodenbilder liegen im Library-Ordner unter
`imported/episode-images/<Instanz>/` und gehören zum Medien-Spiegel des
[Backups](./BACKUP.md).

> **Nah an der Sendung planen.**  Ändert sich das Wiederholungsmuster
> einer Sendung, legt der Kalender ihre künftigen Instanzen neu an, und
> deren Episodendaten gehen mit.  (**Instanz bearbeiten** einer
> einzelnen Episode behält sie.)  Tragen Sie Titel und Bilder für die
> nächsten Wochen ein, nicht Monate im Voraus.

---

## 5. Online archivieren

Der untere Block von **Episode...** - **Online-Archiv (cba.media)** -
zeigt den Stand der Episode auf cba.media.  Admins und Programm-Manager
archivieren von hier aus; Hosts sehen den Stand.

1. Ergänzen Sie, was der Block unter *Bevor diese Episode archiviert
   werden kann* auflistet - meist CBA-Konto, Thema, Sprache und Lizenz
   der Sendung und eine Beschreibung.
2. Klicken Sie **Online archivieren...** und wählen Sie den Ton:
   * **Die Aufzeichnung dieser Episode** - die Kopie, die
     [Aufnahme pro Sendung](./RECORD_PER_SHOW.md) in die Library gelegt
     hat;
   * **Eine Library-Datei** - Suche nach Titel oder Urheber, z. B. die
     vorproduzierte Datei ohne Jingles (nur MP3, OGG und Opus; M4A nimmt
     die CBA nicht).
3. **Upload starten**.  Der Hintergrunddienst (RASTATIME-WORKER) holt
   den Auftrag innerhalb von etwa 15 Sekunden ab; der Block zeigt den
   Fortschritt und danach den Link zum Beitrag.

Titel, Teaser, Beschreibung, Bild und die Vorgaben der Sendung werden
beim Start des Uploads gelesen.  **Änderungen nach dem Upload erfolgen
auf cba.media** - die CBA-Schnittstelle kann einen Beitrag weder ändern
noch ersetzen.

| Stand | Bedeutung, was tun |
|---|---|
| *Wartet auf den Upload* | Eingereiht; der Worker startet gleich. |
| *Wird auf cba.media hochgeladen: n %* | Läuft, gebremst auf die Upload-Grenze (§2). |
| *Auf cba.media archiviert als Beitrag n* | Fertig; die Nummer verlinkt den Beitrag. |
| *Wartet auf einen weiteren Versuch* | cba.media war nicht erreichbar oder ausgelastet; RASTATIME versucht es nach 2, 5, 15, 30 Minuten ... bis zu 24 Stunden lang erneut. |
| *Der Upload ist gescheitert: Grund* | Fehlende Daten, oder cba.media hat abgelehnt (z. B. falsches Anwendungspasswort, unbekanntes Thema). Ursache beheben und erneut **Online archivieren...**. |
| *Unklar, ob der Beitrag angelegt wurde* | Die Verbindung brach während des Uploads ab. Der Beitrag existiert vielleicht - auf cba.media nachsehen, dann **Bestehenden Beitrag verknüpfen** oder erneut archivieren. RASTATIME wiederholt diesen Fall nie von selbst, damit keine Episode doppelt erscheint. |

**Bestehenden Beitrag verknüpfen** nimmt die Nummer eines Beitrags auf
cba.media (oder seine Adresse mit `?p=<Nummer>`), z. B. für eine Episode,
die Sie früher von Hand hochgeladen haben; ein leeres Feld entfernt die
Verknüpfung.  Eine verknüpfte Episode gilt als archiviert.

> **Den Worker stoppen** hält nur die Uploads an; die Sendung merkt
> davon nichts.  Ein Auftrag, der gerade lief, wird nach dem Neustart
> geprüft: ging noch kein Byte hinaus, startet er erneut, sonst endet er
> als *unklar*.

### Automatisch

Ist im Abschnitt *Archivierung* der Sendung (§3) **Automatisch
archivieren** angehakt, archiviert RASTATIME jede neue Episode von
selbst, immer mit der Aufzeichnung:

1. Die Episode endet; [Aufnahme pro Sendung](./RECORD_PER_SHOW.md) legt
   die Aufzeichnung binnen Sekunden in die Library (die Sendung muss
   aufzeichnen, und *Copy Show Recordings into Library* muss unter
   Einstellungen → Local Machine eingeschaltet sein).
2. Nach der Wartezeit (Einstellungen → CBA-Konten, Standard 30 Minuten)
   prüft der Hintergrunddienst die Episode und stellt den Upload in die
   Warteschlange, mit der Sichtbarkeit der Sendung.
3. Fehlt noch etwas (eine Beschreibung, die Aufzeichnung ...), wartet die
   Episode und wird alle fünf Minuten erneut geprüft, bis zu 24 Stunden.
   Danach gibt der Lauf auf; der Dialog zeigt *Das automatische
   Archivieren hat aufgegeben* mit dem Grund.

Nie automatisch archiviert werden:

* Episoden, die **vor** dem Anhaken endeten - nichts wird nachgeholt;
  ältere Episoden archivieren Sie von Hand;
* Wiederholungen und Sendungen, die als *Wiederholung einer anderen
  Sendung* angelegt sind;
* Episoden mit **Diese Episode nicht automatisch archivieren** (§4);
* Episoden, die schon archiviert oder verknüpft sind oder die jemand von
  Hand gestartet hat - die lässt der automatische Lauf in Ruhe;
* Episoden, deren Aufzeichnung weniger als die halbe Sendung umfasst
  (z. B. eine abgebrochene Aufzeichnung).

**Episode...** zeigt im Block *Online-Archiv*, was der automatische Lauf
mit der Episode vorhat, z. B. *Wird ab 2026-11-10 14:30 automatisch
archiviert, sobald unten nichts mehr fehlt*.

Scheitert ein automatischer Upload, bleibt er unklar oder wird
aufgegeben, nennt der Warnhinweis oben auf der Seite die Episode sieben
Tage lang, bis sie von Hand archiviert oder ihr Beitrag verknüpft ist.

> **Nicht erkannt:** Ein Ersatzprogramm, das statt einer Live-Sendung
> lief (die Moderation kam nicht), wird wie die Sendung archiviert.
> Schalten Sie die Automatik für Sendungen ein, die verlässlich laufen;
> passiert es doch, löschen Sie den Beitrag auf cba.media.

---

## 6. Übersicht Teilnehmende

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

## 7. Häufige Fragen

### „Online archivieren... fehlt."

Der Knopf erscheint für Admins und Programm-Manager, und nur solange
die Episode weder archiviert ist noch auf einen Upload wartet.

### „Verbindung testen meldet, Benutzername oder Passwort wurden abgelehnt."

Verwenden Sie das *Anwendungspasswort* aus dem Profil auf cba.media,
nicht das Passwort, mit dem Sie sich anmelden; Leerzeichen darin spielen
keine Rolle.  Prüfen Sie den Benutzernamen auf Tippfehler.

### „Das Thema ist ein Zahlenfeld, keine Liste."

Der Hintergrunddienst holt die Themenliste einmal am Tag.  Nach einer
Neuinstallation oder bevor RASTATIME-WORKER lief, nimmt das Feld die
Nummer.

### „Kommentare auf cba.media?"

Die CBA-Upload-Schnittstelle hat dafür keine Einstellung; es gilt die
Voreinstellung des CBA-Benutzers.

### „Ich habe Profile angekreuzt, aber sie erscheinen nicht in der Übersicht."

Die Übersicht listet nur Sendungen, die im gewählten Jahr **gesendet**
wurden.  Eine neue Sendung erscheint, sobald ihre erste Episode zu Ende
ist.

### „Der Abschnitt Archivierung fehlt oder ist grau."

In **Instanz bearbeiten** fehlt er - der Abschnitt gehört zur ganzen
Sendung; für eine Episode nehmen Sie **Episode...**.  Grau ist er, wenn
Sie nicht Programm-Manager oder Admin sind.

### „Eine Episode wurde nicht automatisch archiviert."

Öffnen Sie **Episode...**: Der Block *Online-Archiv* nennt den Grund -
der Schalter ist aus, *Nicht automatisch archivieren* ist angehakt, die
Episode endete vor dem Einschalten, sie wartet noch auf etwas, oder der
Lauf hat aufgegeben und warum.  Archivieren Sie sie dort von Hand.

---

## Wie es weitergeht

* [Kalender](./CALENDAR.md) - das Sendungsformular und das Kontextmenü.
* [Aufnahme pro Sendung](./RECORD_PER_SHOW.md) - die Aufzeichnung, die
  zum Ton der Episode wird.
* [Analytics](./ANALYTICS.md) - die anderen Statistik-Seiten.
* [Einstellungen](./SETTINGS.md) - jede Seite des Einstellungen-Menüs.
