# Archivierung: Produzenten, Episoden, Online-Archiv, Teilnehmende

> **Wo Sie sich im Handbuch befinden.** Einstellungen →
> **Archivierung** (Produzenten, CBA-Konten); Kalender →
> Sendungsformular, Abschnitt **Archivierung**; Kalender → Rechtsklick
> auf eine Episode → **Extras** → **Online archivieren**; Statistiken →
> **Teilnehmende** und **Archiv-Status** (in der englischen Oberfläche
> Settings → Archiving, Archiving, Archive Online, Analytics →
> People Involved und Archive Status).  Lesen Sie zuerst
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

Eine *Episode* ist ein einzelnes Vorkommen einer Sendung im Kalender: die
„Morgensendung" am nächsten Montag ist eine Episode, die am Montag
darauf die nächste.

**Stand der Stufen.**

| Stufe | Was | Stand |
|---|---|---|
| 1 | Produzent, Vorgaben der Sendung, Episodendaten, Teilnehmende | seit 2026-11-03 |
| 2 | Eine Episode von Hand aus dem Kalender online archivieren | seit 2026-11-03 |
| 3 | Jede Episode nach der Aufzeichnung automatisch archivieren | seit 2026-11-03 |

---

## 1. Produzenten

**Einstellungen → Archivierung** listet im oberen Teil,
**Produzenten**, wer die Sendungen macht - je eine Person oder ein
Team.  Jede Sendung wählt einen Produzenten (§3).  (Bis 2026-11-04
*Redaktionsteams*; cba.media nennt sie *Redaktion*.)

| Feld | Bedeutung |
|---|---|
| **Name** | So, wie er auf cba.media (als Redaktion) und in der Statistik erscheinen soll. |
| **E-Mail (optional)** | Für Ihre eigene Übersicht. |
| **Benutzer (optional)** | Verknüpft den Produzenten mit einem RASTATIME-Login, z. B. dem der verantwortlichen Person. Ein Produzent braucht kein Login. |
| **Aktiv** | Nur aktive Produzenten werden im Sendungsformular angeboten.  Ein abgeschalteter bleibt in den Sendungen, die ihn schon haben. |

**Ändern** lädt den Produzenten in das Formular über der Tabelle;
**Löschen** entfernt ihn nach einer Rückfrage aus jeder Sendung.  Die
Spalte **Sendungen** zählt die Sendungen eines Produzenten.

Programm-Manager und Admins öffnen diese Seite; Programm-Manager sehen
nur diesen Teil.

---

## 2. CBA-Konten

Jede Sendung wird unter einem cba.media-Benutzer archiviert - die
Episoden erscheinen unter dessen Namen.  Der untere Teil von
**Einstellungen → Archivierung**, **CBA-Konten**, hält diese Benutzer;
nur Admins sehen ihn.

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
**Archivierung** zwischen **Who** und **Style** - wie die anderen
Abschnitte ist er zunächst zugeklappt; klicken Sie auf seine
Überschrift.  Die Werte gelten für jede Episode der Sendung, solange
eine Episode keine eigenen setzt.

| Feld | Bedeutung |
|---|---|
| **Produzent** | Wer die Sendung macht - eine Person oder ein Team, aus der Liste gewählt (einer je Sendung, §1). Der Name geht als Redaktion an cba.media und erscheint in Statistiken → Teilnehmende. |
| **CBA-Konto** | Der CBA-Benutzer, unter dem die Episoden archiviert werden (§2). |
| **Sichtbarkeit auf cba.media** | *Öffentlich* (gelistet), *Ungelistet* (nur über die Adresse erreichbar) oder *Privat* (nur für den CBA-Benutzer sichtbar). |
| **CBA-Podcast-ID** | Die Nummer des Podcasts (Serie) auf cba.media, zu dem die Episoden gehören. Ohne sie hält cba.media den Beitrag privat. |
| **Lizenz** | Lizenz der Episoden. Das Hilfe-Symbol zeigt, welche Lizenz die Fragen des CBA-Webformulars beantwortet (siehe unten). |
| **CBA-Thema** | Das Thema (Kategorie) auf cba.media, aus der Liste, die RASTATIME einmal am Tag holt. Vor dem ersten Abruf nimmt das Feld die Nummer. |
| **Sprachen** | Bis zu drei Sprachcodes, die die CBA kennt, z. B. `de, en`. |
| **Schlagworte** | Schlagworte für cba.media, durch Komma getrennt. |
| **Standard-Teaser** | Gilt für jede Episode ohne eigenen Teaser. |
| **Enthält urheberrechtlich geschützte Musik** | Die Episoden enthalten üblicherweise geschützte Musik (AKM); cba.media schränkt dann den Download ein. |
| **Automatisch archivieren** | Jede neue Episode von selbst auf cba.media archivieren (§5, *Automatisch*). Braucht CBA-Konto, Thema, Sprache und Lizenz; neben dem Kästchen steht, seit wann es eingeschaltet ist. Hat die Sendung keine Beschreibung, weist ein Hinweis unter dem Kästchen darauf hin, dass eine Episode ohne eigene dann den Namen der Sendung als Text bekommt. |

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

Die Zahl der Teilnehmenden steht nicht mehr in diesem Abschnitt (seit
2026-11-04): Sie steht im Abschnitt **What**, unter **Eigenproduktion**,
als **Moderierende** (Hosts involved, 0-999; bis 2026-11-07 *Anzahl
Teilnehmende*) und erscheint, sobald **Eigenproduktion** angehakt ist -
sie zählt in Statistiken → Teilnehmende (§6).

In **Episode bearbeiten** wird der Abschnitt **schreibgeschützt** mit
den Werten der Sendung angezeigt (seit 2026-11-04; vorher fehlte er):
er gehört zur ganzen Sendung.  Die Daten einer einzelnen Episode
bearbeiten Sie unter **Online archivieren** (§4).

> **Woher kommt die Podcast-Nummer?**  Öffnen Sie den Podcast auf
> cba.media; die Nummer steht in der Adresse oder auf der Seite (die
> CBA listet die Podcasts einer Station nur angemeldeten Benutzern).

---

## 4. Episodendaten: „Online archivieren"

Rechtsklick auf eine Episode im Kalender → **Extras** → **Online archivieren** (bis
2026-11-03 *Episode...*).  Der Eintrag steht vor und nach der Sendung
zur Verfügung - das Bild können Sie auch nach der Ausstrahlung setzen -
für Admins, Programm-Manager und die Hosts der Sendung.

| Feld | Bedeutung |
|---|---|
| **Titel** | Leer: Name der Sendung und Datum, grau als Vorschlag angezeigt. |
| **Teaser** | Eine kurze Zusammenfassung. Leer: der Standard-Teaser der Sendung. |
| **Beschreibung** | Der Text der Episode, auf cba.media der Text des Beitrags. Leer: die Beschreibung der Sendung oder, wenn die Sendung keine hat, der Name der Sendung (grau angezeigt). Hier ist die einzige Stelle dafür (Episode bearbeiten zeigt das Feld nicht mehr). |
| **Gäste** (Guests involved) | Die Gäste dieser einen Episode (0-999), gezählt zusätzlich zu den Moderierenden der Sendung (seit 2026-11-07; vorher hieß das Feld *Teilnehmende* und ersetzte den Wert der Sendung). Leer bedeutet keine Gäste; die Zeile unter dem Feld zeigt die Moderierenden der Sendung. |
| **Produktionsdatum** | Von cba.media verlangt. Leer: der Sendetag. Setzen Sie es, wenn die Episode früher produziert wurde. |
| **Diese Episode nicht automatisch archivieren** | Für Tests, ausgefallene Episoden oder Rechteprobleme. Wirkt mit der automatischen Archivierung (§5); von Hand archivieren bleibt möglich. |
| **Episodenbild** | Optional, JPG oder PNG bis 10 MB. Die Auswahl einer Datei lädt sie sofort hoch; **Bild entfernen** löscht sie. Ohne Bild zeigt cba.media das Bild des Podcasts. |
| **Bildlizenz** / **Bildunterschrift** | Lizenz und Bildnachweis (z. B. wer fotografiert hat), Bildunterschrift bis 500 Zeichen. |

Die rechte Spalte zeigt, was die Episode von der Sendung übernimmt
(Produzent, CBA-Konto, Podcast, Lizenz, Sichtbarkeit); die Zeile
oben sagt, ob die Episode gesendet wurde und ob ihre Aufzeichnung in
der Library liegt.

**Speichern** sichert die Textfelder; das Bild wird gespeichert, sobald
Sie es wählen.  Episodenbilder liegen im Library-Ordner unter
`imported/episode-images/<Instanz>/` und gehören zum Medien-Spiegel des
[Backups](./BACKUP.md).

> **Nah an der Sendung planen.**  Ändert sich das Wiederholungsmuster
> einer Sendung, legt der Kalender ihre künftigen Episoden neu an, und
> deren Episodendaten gehen mit.  (**Episode bearbeiten** einer
> einzelnen Episode behält sie.)  Tragen Sie Titel und Bilder für die
> nächsten Wochen ein, nicht Monate im Voraus.

---

## 5. Online archivieren

Der untere Block von **Online archivieren** - **Online-Archiv
(cba.media)** - zeigt den Stand der Episode auf cba.media.  Admins und
Programm-Manager archivieren von hier aus; Hosts sehen den Stand.

1. Ergänzen Sie, was der Block unter *Bevor diese Episode archiviert
   werden kann* auflistet - meist CBA-Konto, Thema, Sprache und Lizenz
   der Sendung.  Eine Beschreibung ist nicht nötig: Fehlt sie bei der
   Episode und der Sendung, wird der Name der Sendung zum Text des
   Beitrags.
2. Klicken Sie **Jetzt online archivieren** und wählen Sie den Ton:
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
| *Der Upload ist gescheitert: Grund* | Fehlende Daten, oder cba.media hat abgelehnt (z. B. falsches Anwendungspasswort, unbekanntes Thema). Ursache beheben und erneut **Jetzt online archivieren**. |
| *Unklar, ob der Beitrag angelegt wurde* | Die Verbindung brach während des Uploads ab. Der Beitrag existiert vielleicht - auf cba.media nachsehen, dann **Bestehenden Beitrag verknüpfen** oder erneut archivieren. RASTATIME wiederholt diesen Fall nie von selbst, damit keine Episode doppelt erscheint. |

**Bestehenden Beitrag verknüpfen** ist für einen Beitrag, der schon auf
cba.media liegt - dort von Hand hochgeladen oder nach einem *unklaren*
Upload.  Tragen Sie seine Nummer (oder seine Adresse mit `?p=<Nummer>`)
ein und klicken Sie den Knopf: RASTATIME markiert die Episode als
archiviert und lädt nichts hoch.  Ein leeres Feld entfernt die
Verknüpfung.  Das Hilfe-Symbol neben dem Knopf sagt dasselbe.

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
2. Nach der Wartezeit (Einstellungen → Archivierung, Standard 30 Minuten)
   prüft der Hintergrunddienst die Episode und stellt den Upload in die
   Warteschlange, mit der Sichtbarkeit der Sendung.
3. Fehlt noch etwas (die Aufzeichnung, ein Thema ...), wartet die
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

**Online archivieren** zeigt im Block *Online-Archiv*, was der
automatische Lauf mit der Episode vorhat, z. B. *Wird ab 2026-11-10
14:30 automatisch archiviert, sobald unten nichts mehr fehlt*.

Scheitert ein automatischer Upload, bleibt er unklar oder wird
aufgegeben, nennt der Warnhinweis oben auf der Seite die Episode sieben
Tage lang, bis sie von Hand archiviert oder ihr Beitrag verknüpft ist;
Programm-Manager und Admins finden dort einen Link zu **Statistiken →
Archiv-Status** (§7).

> **Nicht erkannt:** Ein Ersatzprogramm, das statt einer Live-Sendung
> lief (die Moderation kam nicht), wird wie die Sendung archiviert.
> Schalten Sie die Automatik für Sendungen ein, die verlässlich laufen;
> passiert es doch, löschen Sie den Beitrag auf cba.media.

---

## 6. Teilnehmende

**Statistiken → Teilnehmende** zählt die Teilnehmenden je
Eigenproduktion und Jahr (Stationszeit) - die Zahlen für die
Jahresstatistik.  Nur Sendungen mit **Eigenproduktion** (Sendung ändern
→ What) zählen.  Eine Sendung, deren Häkchen entfernt wird, behält ihre
Zahlen, bleibt aber außen vor.

Seit 2026-11-07 folgt die Zählung den Menschen, nicht den Episoden:

* **Moderierende** (Hosts involved; Sendung ändern → What, direkt unter
  **Eigenproduktion**) sind die Menschen, die in jeder Episode dieselben
  sind.  Sie zählen **einmal je Sendung und Jahr**, egal wie viele
  Episoden gesendet wurden.
* **Gäste** (Guests involved; Online archivieren im Kalender) sind die
  Gäste einer Episode.  Sie zählen **in jeder Episode** und werden
  zusammengezählt.
* **Teilnehmende** = Moderierende + Gäste.

Beispiel: eine Wochensendung mit 2 Moderierenden lief 40-mal; drei
Episoden hatten Gäste (1, 2 und 1).  Teilnehmende: 2 + 4 = 6.

* **Jahr** - das laufende Jahr zeigt den Stand bis heute.
* **Nur Sendungen ohne Wert** - die Eigenproduktionen, die gelaufen
  sind, aber noch keine *Moderierenden* haben.  Arbeiten Sie diese Liste
  einmal durch; setzen Sie `0` für automatisierte oder übernommene
  Programme.
* **CSV herunterladen** - Tabelle und Summen als Tabellen-Datei.

Gezählt werden die Episoden, die im Jahr **gesendet** wurden (beendet,
nicht gelöscht).  Rebroadcasts der alten LibreTime-Art bleiben außen
vor.  Sendungen, die als [Wiederholung einer anderen Sendung](./CALENDAR.md)
angelegt sind, stehen mit dem Merkmal **Wiederholung** in der Liste und
zählen nichts: ihre Menschen sind schon beim Original gezählt.  Sie
erscheinen nie unter *Sendungen ohne Wert*.

| Spalte / Summe | Bedeutung |
|---|---|
| **Gesendete Eigenproduktionen** (Summe) | Eigenproduktionen mit mindestens einer gesendeten Episode im Jahr, Wiederholungen eingeschlossen. |
| **Gesendete Episoden** | Episoden der Sendung im Jahr. |
| **Moderierende** | Die Moderierenden der Sendung, einmal pro Jahr; die Summe addiert die Moderierenden aller Sendungen. |
| **Gäste** | Die Gäste aller gesendeten Episoden der Sendung zusammengezählt. |
| **Teilnehmende** | Moderierende + Gäste; die Summe ist die Zahl für die Statistik. |
| **Sendungen ohne Wert** (Summe) | Eigenproduktionen (ohne Wiederholungen) ohne *Moderierende*; orange, solange es welche gibt. |

Wer in mehreren Sendungen mitwirkt, zählt einmal je Sendung; ein Gast,
der wiederkommt, zählt in jeder Episode.  Die Zahlen sind Anzahlen,
keine Namen - RASTATIME kann nicht erkennen, dass zwei Sendungen
dieselbe Moderation haben.  Die Produzenten werden nicht gezählt.

Programm-Manager und Admins öffnen diese Seite.

---

## 7. Archiv-Status

**Statistiken → Archiv-Status** (seit 2026-11-04, englisch Analytics →
Archive Status) zeigt auf einer Seite, ob die Episoden auf cba.media
ankommen.  Programm-Manager und Admins öffnen sie; der Warnhinweis
verlinkt dorthin.

* **Läuft und wartet** - der laufende Upload (der gesendete Anteil, alle
  paar Sekunden aktualisiert) und die wartenden: auf den
  Hintergrunddienst oder nach einem Verbindungsproblem auf den nächsten
  Versuch (Zeit und Grund).  **Abbrechen** stoppt einen wartenden
  Upload.  Ein laufender Upload lässt sich nicht abbrechen - er gehört
  bis zu seinem Ende dem Hintergrunddienst.
* **Steht an (automatisches Archivieren)** - die Episoden der Sendungen
  mit *Automatisch archivieren* aus den nächsten 7 Tagen und die
  gesendeten, die noch nicht eingereiht sind, mit ihrer Fälligkeit:

  | Status | Bedeutung |
  |---|---|
  | *Noch nicht gesendet - fällig ...* | Die Episode kommt erst. |
  | *Gesendet - fällig ...* | Die Wartezeit (Einstellungen → Archivierung) läuft. |
  | *Fällig - wird bei der nächsten Prüfung eingereiht* | Es fehlt nichts; der Hintergrunddienst reiht sie innerhalb von fünf Minuten ein. |
  | *Wartet, längstens bis ...* | Etwas fehlt (Spalte **Fehlt**); danach gibt der automatische Lauf auf. |
  | *Nicht automatisch archiviert: ...* | *Diese Episode nicht automatisch archivieren* ist angehakt. |

  Schon vor der Sendung nennt **Fehlt**, was der Sendung fehlt
  (CBA-Konto, Thema, Sprache, Lizenz) - Zeit, die Sendung zu ergänzen.
* **Probleme (letzte 30 Tage)** - Uploads von Hand oder automatisch, die
  gescheitert, unklar geblieben oder aufgegeben sind, solange die
  Episode keinen Beitrag hat.  **Erneut archivieren** reiht dasselbe
  Audio noch einmal ein (die Aufzeichnung, falls die Datei weg ist).
  Nach einem *unklaren* Upload fragt die Seite zuerst nach, denn der
  Beitrag existiert vielleicht: Sehen Sie auf cba.media nach und nehmen
  Sie **Beitrag verknüpfen…** (Nummer oder Adresse), falls er dort ist.
  Die Zeile verschwindet, sobald die Episode archiviert oder verknüpft
  ist.
* **Verlauf** - jeder Upload mit Zeit, Sendung, Episode, wer ihn
  gestartet hat (*Automatisch* oder das Login), Status, Link zum
  Beitrag, Audio, Größe, Dauer und Hinweis.  Filter nach Jahr, Monat,
  Status, Gestartet von und Sendungsname; **CSV herunterladen** nimmt die
  ganze gefilterte Liste (die Seite zeigt die neuesten 500).

Die Seite lädt sich selbst neu, wenn ein Upload beginnt oder endet.

---

## 8. Häufige Fragen

### „Jetzt online archivieren fehlt."

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

### „Ich habe einen Produzenten gewählt, aber die Sendung erscheint nicht in der Übersicht."

Die Übersicht listet nur Sendungen, die im gewählten Jahr **gesendet**
wurden.  Eine neue Sendung erscheint, sobald ihre erste Episode zu Ende
ist.

### „Der Abschnitt Archivierung ist grau."

In **Episode bearbeiten** ist er schreibgeschützt - der Abschnitt gehört
zur ganzen Sendung; für eine Episode nehmen Sie **Online archivieren**.
Grau ist er auch, wenn Sie nicht Programm-Manager oder Admin sind.

### „Eine Episode wurde nicht automatisch archiviert."

Öffnen Sie **Online archivieren**: Der Block *Online-Archiv* nennt den
Grund - der Schalter ist aus, *Nicht automatisch archivieren* ist
angehakt, die Episode endete vor dem Einschalten, sie wartet noch auf
etwas, oder der Lauf hat aufgegeben und warum.  Archivieren Sie sie dort
von Hand.  **Statistiken → Archiv-Status** (§7) zeigt alle solchen
Episoden auf einmal.

### „Wo sind Redaktionsteam und CBA-Konten?"

Seit 2026-11-03 liegen beide auf einer Seite, **Einstellungen →
Archivierung**: oben die Produzenten (bis 2026-11-04 *Redaktionsteams*), darunter die CBA-Konten mit
der Upload-Grenze und der Wartezeit (nur Admins).

---

## Wie es weitergeht

* [Kalender](./CALENDAR.md) - das Sendungsformular und das Kontextmenü.
* [Aufnahme pro Sendung](./RECORD_PER_SHOW.md) - die Aufzeichnung, die
  zum Ton der Episode wird.
* [Analytics](./ANALYTICS.md) - die anderen Statistik-Seiten.
* [Einstellungen](./SETTINGS.md) - jede Seite des Einstellungen-Menüs.
