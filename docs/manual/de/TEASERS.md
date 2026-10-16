# Teaser-Automatik

> **Wo Sie sich im Handbuch befinden.** Bibliothek → Track-Editor,
> Felder **Teaser für Sendung** und **Teaser-Typ**; Bibliothek → Smart
> Blocks, Kriterien **Teaser: Sendung**, **Teaser: Typ**, **Teaser:
> passt zum Sendeplan**.  Lesen Sie zuerst [Bibliothek](./LIBRARY.md)
> § 3 (Smart Blocks) und
> [Autoloading-Playlisten](./AUTOLOADING_PLAYLISTS.md) - die Automatik
> ist ein Smart-Block-Kriterium, das das Autoloading ausspielt.
>
> **Was diese Funktion ersetzt.** Das tägliche Platzieren der
> „heute"- und „morgen"-Jingles jeder Sendung von Hand, vor und nach
> den Nachrichten und in den Musiksendungen.

Eine Station kennt drei Arten von Teasern: einen **Showteaser**, der
eine Sendung allgemein ankündigt („Around the World - jeden
Donnerstag um 11"), einen **Tagesteaser „heute"** („Around the World - heute um 11") und einen **Tagesteaser „morgen"**.  Welcher
passt, hängt vom Tag ab, an dem der Jingle läuft, und vom Kalender.
Seit 2026-10-16 weiß die Bibliothek, welche Sendung ein Jingle
ankündigt und wie, und ein Smart-Block-Kriterium wählt die Jingles,
die zum Tag der befüllten Sendung passen.

---

## 1. Einen Jingle mit seiner Sendung verknüpfen

Öffnen Sie den Jingle im Track-Editor (Bibliothek → Stift oder
Doppelklick) und setzen Sie

| Feld | Bedeutung |
|---|---|
| **Teaser-Typ** | **Showteaser (jederzeit)**, **Tagesteaser: „heute"** oder **Tagesteaser: „morgen"**.  Wählen Sie ihn zuerst: Die Sendungsliste darunter bleibt ausgegraut, bis ein Typ gesetzt ist, und ein Speichern mit Sendungen ohne Typ wird abgewiesen. |
| **Teaser für Sendungen** | die Sendungen, die dieser Jingle ankündigt - eine oder mehrere anhaken, ein Kontrollkästchen je Sendung wie beim Song-Request-Pool.  Die Liste enthält jede Sendung mit bevorstehender Ausstrahlung, jeweils mit der nächsten Sendezeit (`bbc (Sat 12:00)`), damit gleichnamige Sendungen unterscheidbar sind; die stündlichen Nachrichten-Slots sind eigene Sendungen, und ein „BBC heute"-Jingle kann sie alle ankündigen.  Keine Auswahl = kein Teaser; wird der Typ wieder auf *None* gesetzt, leert sich die Liste. |

Für viele Jingles auf einmal markieren Sie sie in der Bibliothek und
nutzen **Edit** (Mehrfach-Bearbeitung): dieselben zwei Felder; keine
Auswahl lässt ein Feld unberührt, *None* löst die Verknüpfungen,
gewählte Sendungen ersetzen die Liste - und brauchen im selben Speichern
einen Typ, weil die markierten Tracks noch keinen haben müssen.  Die
Bibliotheksspalte **Teaser** (Spaltenwähler, standardmäßig
ausgeblendet) zeigt `Sendungsname (today)` und ist durchsuchbar, sodass
„Teaser enthält Worldwide" alle Jingles dieser Sendung listet.

Ein Jingle hat einen Typ und kündigt eine oder mehrere Sendungen an;
er passt, sobald eine seiner Sendungen passt.  Zwei Jingles können
natürlich dieselbe Sendung mit verschiedenen Typen ankündigen.

## 2. Die Smart-Block-Kriterien

| Kriterium | Modifikatoren | Wert | Trifft |
|---|---|---|---|
| **Teaser: Sendung** | ist / ist nicht | eine Sendung | Jingles, die diese Sendung (unter anderen) ankündigen |
| **Teaser: Typ** | ist / ist nicht | Showteaser, heute, morgen | Jingles dieses Typs |
| **Teaser: passt zum Sendeplan** | ist | dem Tag der befüllten Sendung | siehe unten |

**Teaser: passt zum Sendeplan** ist die Automatik.  „Der Tag" ist der
Kalendertag (Zeitzone der Station) des *Slots*, für den der Block
expandiert wird: der Sendungsbeginn für eine Autoloading-Intro-Playlist,
das Sendungsende für das Outro, die aktuelle Position für die
Inhalts-Playlist, und - wenn Sie einen Block von Hand in eine Sendung
ziehen - das Ende der Zeile, hinter die Sie ihn legen.  Mit diesem Tag
*D* und dem Zeitpunkt *T* des Slots gilt:

* ein **„heute"**-Teaser passt, wenn seine Sendung an *D* eine
  Ausstrahlung hat, die nach *T* beginnt;
* ein **„morgen"**-Teaser passt, wenn seine Sendung an *D + 1* eine
  Ausstrahlung hat;
* ein **Showteaser** passt an jedem Tag - außer seine Sendung ist *für
  heute vorbei*: Sie hatte an *D* eine Ausstrahlung, die vor *T*
  endete, und hat an *D* keine spätere mehr;
* ein Jingle passt nie zur Sendung, deren Instanz gerade befüllt wird -
  eine Sendung teasert sich nicht selbst.

Eine abgesagte oder verschobene Ausstrahlung nimmt ihre Tagesteaser
also mit: Das Kriterium schaut zur Füllzeit in den Kalender, nicht in
eine feste Liste.

## 3. Rotation: kein Jingle zweimal in einer Sendung

Kombinieren Sie das Kriterium mit **Exclude tracks played lately** (zum
Beispiel 3 Stunden).  Seit 2026-10-16 zählt dieser Filter auch
**geplante** Zeilen: Ein Titel, der im Zeitfenster geplant ist - vor
oder nach dem Slot, einschließlich der Zeilen, die ein früherer Block
desselben Fülldurchgangs eben in dieselbe Sendung gelegt hat - wird
ausgeschlossen, obwohl er noch nicht gelaufen ist.  Zwei Teaser-Blöcke
in einer Sendung ziehen daher nie denselben Jingle, und ein in der
Sendung davor geplanter Jingle kommt in der nächsten nicht wieder.  Das
gilt für jeden Smart Block mit diesem Filter, Musik eingeschlossen.

## 4. Rezepte

**Nachrichtenblock (z. B. die stündliche BBC-Sendung).**  Geben Sie der
Sendung eine Autoloading-Intro- und eine Outro-Playlist mit je einem
dynamischen Smart Block: *1 Titel*, Kriterium *Teaser: passt zum
Sendeplan ist dem Tag der befüllten Sendung*, *Exclude tracks played
lately 3 h*.  Der Slot braucht Platz für die Jingles: Eine
7-Minuten-Sendung mit einem 7-Minuten-Stream hat keinen.

**Musiksendungen.**  Ersetzen Sie die handgebauten Tagesteaser-Blöcke in
deren Autoloading-Playlisten durch denselben Block.  Behalten Sie einen
zweiten Block *Teaser: Typ ist Showteaser* für Sendungen, die noch
keine Tagesteaser haben.

**Nur eine Sendung.**  *Teaser: Sendung ist Worldwide* zusammen mit
*Teaser: passt zum Sendeplan* liefert die Jingles dieser Sendung nur,
wenn sie passen.

## 5. Import/Export

[Import/Export](./IMPORT_EXPORT.md) trägt die Kriterien in
`blocks.json`: `teaser_show` mit dem Sendungsnamen (beim Import die
erste Sendung dieses Namens), `teaser_type` als `show`, `today` oder
`tomorrow`, `teaser_fits` mit dem Wert `yes`.  Die Verknüpfungen der
Jingles selbst sind Metadaten der Dateien und nicht Teil des Bündels.

## 6. Häufig gestellte Fragen

### „Generate im Smart-Block-Editor zeigt andere Jingles, als die Sendung bekommt."

Der Editor hat keinen Slot: Er nimmt *jetzt* als Zeitpunkt und schließt
keine Sendung aus.  Die echte Auswahl geschieht beim Befüllen der
Sendung.

### „Eine Sendung ist aus der Liste verschwunden."

Die Liste enthält Sendungen mit bevorstehender Ausstrahlung.  Ein
Jingle behält seine Verknüpfung zu einer Sendung, die keine mehr hat;
der Editor zeigt sie weiterhin, das Kriterium findet nur keinen
passenden Tag.

### „Es wird gar nichts gewählt."

Prüfen Sie, dass die Jingles Sendung und Typ tragen, dass die Sendung an
diesem Tag wirklich eine Ausstrahlung hat und dass die übrigen
Kriterien des Blocks (Track-Typ, Genre) sie nicht ausschließen.  Bis die
Datenbank-Migrationen 0069 und 0070 gelaufen sind, liefert das Kriterium einen
leeren Pool, und das Log sagt es.

## Siehe auch

* [Bibliothek](./LIBRARY.md) § 3 - Smart-Block-Kriterien, Limits und
  die Exclude-Filter.
* [Autoloading-Playlisten](./AUTOLOADING_PLAYLISTS.md) - Intro-, Outro-
  und Inhalts-Playlisten, die die Teaser-Blöcke tragen.
* [Kalender](./CALENDAR.md) - die Ausstrahlungen, die das Kriterium
  liest.
