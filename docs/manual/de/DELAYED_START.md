# Verzögerter Sendungsstart

> **Wo Sie sich im Handbuch befinden.** Dies ist ein Kapitel aus
> **Täglicher Sendebetrieb**, ein Begleiter zum
> [Kalender](./CALENDAR.md). Lesen Sie zuerst das Kalender-Kapitel —
> der einzige Schalter, den diese Funktion hinzufügt, liegt im
> Abschnitt **Wann** des Formulars „Neue Sendung" / „Sendung
> bearbeiten", direkt unter **Wiederholt sich?**.

Normalerweise beginnt jede Sendung exakt zu ihrem Kalender-Slot, und
eine Sendung mit **mehr geplantem Inhalt, als in ihren Slot passt**,
wird am Slot-Ende einfach abgeschnitten — der letzte Track wird
getrimmt (die solide rote Spitze am
[Kalender-Füllbalken](./CALENDAR.md#1-die-kalender-seite)). Die
folgende Sendung beginnt trotzdem pünktlich.

**Verzögerter Start** ändert das für Sendungen, die Sie dafür
freischalten. Wenn die Sendung *vor* der Ihren ihren Slot überzieht,
**verschiebt sich** eine freigeschaltete Sendung nach hinten, damit
die vorige Sendung zu Ende laufen kann — statt die vorige Sendung
abzuschneiden. Sie kreuzen ein Kästchen pro Sendung an; ein
Hintergrund-Task erledigt den Rest, wenige Minuten vor der Ausstrahlung.

> **Das ist eine Opt-in-Funktion und arbeitet nur vorwärts.** Eine
> Sendung verschiebt sich nur, wenn **ihr eigenes** Kästchen
> angekreuzt ist. Die Verschiebung wird nie automatisch rückgängig
> gemacht — siehe §6. Wenn Sie es sich anders überlegen, entfernen Sie
> das Häkchen (künftige Überziehungen verschieben die Sendung dann
> nicht mehr) oder ziehen Sie die Episode im Kalender zurück.

---

## 1. Das Gesamtbild

```
   Slot:    │ Sendung A (1h-Slot) │ Sendung B (1h-Slot) │ Sendung C │
            08:00              09:00               10:00      11:00

   A ist überbucht — ihr Inhalt läuft tatsächlich bis 09:10.

   Ohne verzögerten Start (B nicht angekreuzt):
            │ Sendung A …✂ Schnitt │ Sendung B        │ Sendung C │
            08:00            09:00                   10:00
            A's letzter Track wird um 09:00 getrimmt; B startet pünktlich.

   Mit verzögertem Start (B angekreuzt):
            │ Sendung A ……………… │ Sendung B     │ Sendung C │
            08:00            09:10            10:00     11:00
            A läuft voll bis 09:10. B behält ihr ENDE (10:00) und
            verschiebt ihren START auf 09:10, ist also 50 statt 60 min
            lang und ihr eigener letzter Track wird ggf. getrimmt.
            C startet weiterhin um 10:00.
```

Zwei Regeln machen die ganze Funktion aus:

1. **Die überziehende Sendung läuft voll aus.** Das Slot-Ende von
   Sendung A wird bis dorthin gedehnt, wo ihr Inhalt tatsächlich endet
   (09:10), sodass der Playout A's letzten Track nicht mehr trimmt.
2. **Die freigeschaltete Folgesendung behält ihr ENDE fix und
   verschiebt ihren START.** Sendung B läuft jetzt 09:10 → 10:00 statt
   09:00 → 10:00. Ihre geplanten Items wandern mit; was vor 10:00 nicht
   mehr passt, wird am Ende abgeschnitten (derselbe akzeptierte
   Kompromiss wie bei jeder überbuchten Sendung).

Eine Sendung **ohne** das Kästchen ist ein harter Stopp: Sie beginnt
immer pünktlich, und die Sendung davor wird an ihrem Start getrimmt
(Regel 1 gilt nicht über eine nicht-freigeschaltete Grenze hinweg).

---

## 2. Aktivieren

Öffnen Sie **Neue Sendung** oder **Sendung bearbeiten** und klappen Sie
den Abschnitt **Wann** auf. Direkt unter **Wiederholt sich?** steht:

```
   Wann
   ─────────────────────────────
   Start  [2026-06-15] [08:00]
   …
   Wiederholt sich?              [ ]
   Verzögerten Start erlauben?   [x]   ◀── ankreuzen, damit DIESE
                                           Sendung sich verschieben darf
```

Kreuzen Sie **„Verzögerten Start erlauben?"** bei
jeder Sendung an, die später beginnen darf, wenn die vorige Sendung
überzogen hat. Lassen Sie es bei Sendungen frei, die exakt pünktlich
beginnen müssen (Nachrichten zur vollen Stunde, ein Netz-Feed, eine
zeitgebundene Live-Schaltung) — diese werden zu den Ankern, die eine
Verschiebung stoppen (§4).

Bei einer **wiederkehrenden** Sendung ist das Kästchen Teil der
Sendungsdefinition und gilt damit für jede Episode. Wenn eine konkrete
Überziehung eine Episode verschiebt, wird nur **diese** Episode
geändert (sie wird zu einer einzelnen Ausnahme); die übrigen Episoden
behalten ihren normalen Slot.

> **Wie es unter der Haube funktioniert.** Das Häkchen steckt im neuen
> Boolean `cc_show.allow_delayed_start` (Legacy-Migration 0056). Es hat
> keinen Propel-Accessor — das Formular liest und schreibt es per raw
> SQL, dasselbe Muster wie bei den Song-Request-Spalten. Sonst ändert
> sich an der Sendung nichts, wenn Sie es ankreuzen; das Kästchen ist
> nur für den Hintergrund-Task aus §6 relevant.

### Die Filler-Playlist (Settings → General)

Seit dem 27.09.2026 gibt es einen zweiten, optionalen Schalter für
die ganze Station: **Settings → General → Show-Shift Filler
Playlist**.  Wählen Sie eine Ihrer Playlists — idealerweise Musik in
verschiedenen Längen — und der verzögerte Start kürzt keine
Sendungs-Titel mehr: Die Titel, die nicht mehr passen, werden
stattdessen gegen Filler-Titel getauscht.  §3 erklärt genau, was
dabei passiert.  Bei *(keine — letzten Titel kürzen)* bleibt das
bisherige Verhalten.

---

## 3. Was passiert, wenn eine Sendung überzieht

Wenn der Hintergrund-Task feststellt, dass der geplante Inhalt von
Sendung A **nach** ihrem Slot endet, und die nächste Sendung B
**„Verzögerten Start erlauben"** angekreuzt hat:

| | Vorher | Nachher |
|---|---|---|
| **Ende von A** | 09:00 (Slot) | 09:10 (auf Content-Ende gedehnt) |
| **Start von B** | 09:00 | 09:10 (= Content-Ende von A) |
| **Ende von B** | 10:00 | **10:00 (unverändert)** |
| **Items von B** | 09:00 … | um +10 min verschoben |

So strahlt A jeden geplanten Track aus, und B beginnt genau dann, wenn
A tatsächlich endet. Weil das **Ende von B fix bleibt**, ist B
effektiv zehn Minuten kürzer, und falls B bereits voll war, wird ihr
letzter Track um 10:00 getrimmt — genau das, was ohne die Funktion mit
A passiert wäre. Der Schnitt wandert lediglich zu der Sendung, die sich
freigeschaltet hat, ihn aufzufangen.

> **Warum das Ende von B fix bleibt.** Damit eine einzelne Überziehung
> nicht unbegrenzt in den Rest des Tages durchschlagen kann. B gibt
> ihre ersten zehn Minuten ab, übergibt aber pünktlich um 10:00 an das,
> was folgt. Dies war eine bewusste Entscheidung gegen „auch das Ende
> von B nach hinten schieben" (was jede spätere Sendung verschieben
> würde). Siehe ARCHITECTURE §23.24.

### Filler statt Kürzung (seit 27.09.2026)

Mit konfigurierter Filler-Playlist wird die verschobene Sendung B
nicht einfach abgeschnitten.  Sobald B auf das Inhaltsende von A
gerückt ist, schaut der Task, was jetzt über Bs Ende hinausragt, und
tut drei Dinge:

1. **Das Outro bleibt, wo es hingehört.**  Endet B mit seiner
   Outro-Playlist — der sendungseigenen *Select Outro Playlist* oder
   dem Stations-Standard aus Settings → General —, werden diese
   Outro-Titel am Ende von B festgenagelt und nie angerührt.  Ersetzt
   werden die Titel *davor*, also der vorletzte Titel (oder mehrere).
   (Ob die letzten Zeilen wirklich das Outro sind, wird gegen die
   Titel der Playlist geprüft, nie angenommen: Eine von Hand befüllte
   Sendung ohne Outro hat schlicht keinen geschützten Schluss.)
2. **Jeder Titel, der nicht mehr passt, fliegt raus** — einer oder
   mehrere, vom Ende des Hauptteils rückwärts —, bis der Rest vor dem
   Outro (oder vor Bs Ende, wenn es kein Outro gibt) Platz hat.
3. **Die Lücke wird aus der Filler-Playlist gefüllt**, mit der
   Kombination von Titeln, deren Gesamtlänge die Lücke mit dem
   geringsten Überschuss abdeckt.  Der *letzte* Filler wird am Ende
   der Lücke gekürzt.  So entsteht nie Stille, und gekürzt wird
   immer nur ein Filler — nie ein Titel von B.  Das gilt auch, wenn
   die Lücke kürzer ist als der kürzeste Filler: Dann läuft der
   kürzeste und wird gekürzt.

Der Tausch passiert in derselben Datenbank-Transaktion wie die
Verschiebung — entweder landet alles oder nichts.  Playout,
Dashboard, Widgets und Track History sehen das Ergebnis als ganz
normale Schedule-Zeilen.  Nur die verschobene Sendung B wird so
behandelt; der Schluss von Sendung A wird an einem nicht
freigegebenen Anker weiterhin abgeschnitten (§4).

> **Beispiel.**  B läuft 10:00–11:00, endet mit einem 30-Sekunden-
> Outro-Jingle, und A überzieht um vier Minuten.  B beginnt jetzt um
> 10:04.  Ihr letzter Musiktitel würde um 11:03:30 enden — er fliegt
> raus.  Der verbleibende Hauptteil endet um 10:59:10, die Lücke bis
> zum Outro (das um 10:59:30 beginnen muss) beträgt also 20 Sekunden:
> Der kürzeste Filler läuft und wird um 10:59:30 ausgeblendet, das
> Outro läuft vollständig, und was folgt, beginnt pünktlich um 11:00.

---

## 4. Die Kaskade und der Anker

Eine große Überziehung kann über mehr als eine Sendung hinausreichen.
Die Verzögerung **pflanzt sich vorwärts fort** über aufeinanderfolgende
freigeschaltete Sendungen:

```
   Slot:  │ A (überbucht → 09:40) │  B  │      C      │ D │
          08:00                 09:00 09:30         10:30

   A's Inhalt läuft bis 09:40.

   • B (09:00–09:30, angekreuzt)  komplett verschüttet (09:40 > 09:30)
                                  → GELEERT, Slot bleibt „übersprungen"
   • C (09:30–10:30, angekreuzt)  teilweise verschüttet (09:40 < 10:30)
                                  → auf 09:40 VERSCHOBEN, Ende 10:30 bleibt;
                                    die Kaskade STOPPT hier
   • D (10:30, …)                 unberührt → startet pünktlich um 10:30
```

Eine **Sendung ohne das Kästchen** hätte die Kaskade stattdessen an
ihrem eigenen Start gestoppt: Sie ist ein harter **Anker**, der immer
pünktlich beginnt, und der überziehende Inhalt davor wird am
Anker-Start getrimmt.

Mit jeder freigeschalteten Sendung, die die Überziehung erreicht,
können zwei Dinge passieren:

- **Teilweise verschüttet → sie verschiebt sich.** Wenn der Sendung
  nach der Überziehung noch Zeit bleibt (die Überziehung endet vor dem
  eigenen Ende der Sendung), verschiebt sie sich ans Ende der
  Überziehung, behält ihr Ende, und die Kaskade **stoppt dort** —
  diese Sendung fängt den Rest auf.
- **Komplett verschüttet → sie wird geleert.** Wenn die Überziehung den
  gesamten Slot der Sendung abdeckt, kann die Sendung gar nicht laufen.
  Ihr Inhalt wird geleert, und der leere Slot bleibt im Kalender als
  **„übersprungen"-Marker** stehen (§5). Die Kaskade läuft zur nächsten
  Sendung weiter.

Die Kaskade endet immer bei der **ersten Sendung ohne das Kästchen** —
dem **harten Anker**. Der Anker beginnt exakt pünktlich; der
überziehende Inhalt davor wird am Anker-Start getrimmt. Sie steuern
also, wie weit eine Verzögerung wandern kann, einfach indem Sie das
Kästchen bei der nächsten zeitgebundenen Sendung frei lassen.

> **Operator-Tipp.** Setzen Sie an jeden Punkt des Tages, der sich
> nicht verschieben darf, einen nicht angekreuzten Anker — die
> Nachrichten zur vollen Stunde, einen syndizierten Feed, den Beginn
> der Morgensendung. Alles zwischen zwei Ankern darf sich verschieben;
> nichts überschreitet einen Anker.

---

## 5. Eine komplett überrollte Sendung: der übersprungene Slot

Wenn eine Sendung von einer früheren Überziehung vollständig verschüttet
wird, wird sie **geleert, nicht gelöscht**:

- ihre geplanten Items werden entfernt (der Füllbalken des Slots fällt
  auf 0 %),
- der leere Slot **bleibt im Kalender**, damit Sie sehen, dass die
  Sendung übersprungen wurde, statt klanglos zu verschwinden,
- bei einer wiederkehrenden Sendung wird nur **diese eine Episode**
  geleert; die Serie bleibt unangetastet.

Die frühere Sendung läuft einfach durch die Sendezeit des
übersprungenen Slots. Der Marker ist dafür da, dass Sie es im Nachhinein
bemerken — etwa um sich On Air zu entschuldigen oder die überbuchte
Sendung beim nächsten Mal zu straffen.

> **Wie es unter der Haube funktioniert.** Das Leeren einer
> verschütteten Episode spiegelt die Aktion **Sendeplan leeren** für
> eine einzelne Episode: Ihre `cc_schedule`-Zeilen werden gelöscht,
> `time_filled` wird auf null gesetzt, die Episode wird als
> `modified_instance` markiert — Upstreams „gelöschte Episode", passend
> für einen Slot, der nie sendet — plus `delayed_start_from` (seit
> 27.09.2026, siehe unten), und `cc_files.is_scheduled` wird für jeden
> Track zurückgesetzt, der nirgends mehr eingeplant ist.

---

## 6. Wann — und wie oft — die Verschiebung passiert

Die Verschiebung erledigt ein Hintergrund-Task, **nicht** im Moment, in
dem Sie eine Sendung speichern:

- Ein Task (`ShowShiftTask`) läuft alle **2 Minuten**.
- Er handelt nur bei Überziehungen, deren betroffene Sendung innerhalb
  der nächsten **15 Minuten** startet (der *Vorlauf*). Weit in der
  Zukunft liegende Sendungen, die Sie womöglich noch bearbeiten, bleiben
  unberührt, bis sie nahe heranrücken.
- Er arbeitet auf Basis des **geplanten Inhalts** (`cc_schedule`), gilt
  also gleichermaßen für von Hand befüllte Sendungen wie für solche, die
  eine Autoloading Playlist befüllt hat.

Der Task ist **idempotent und arbeitet nur vorwärts**:

- Ihn erneut auszuführen ändert nichts mehr, sobald eine Sendung bereits
  am Ende der Überziehung sitzt — er schiebt eine Sendung bei
  wiederholten Durchläufen nie weiter.
- Eine Verschiebung wird **nie automatisch rückgängig gemacht.** Wenn Sie
  die überbuchte Sendung später straffen, sodass sie nicht mehr
  überzieht, bleibt die bereits verschobene Sendung dort stehen, bis Sie
  sie zurückbewegen (im Kalender ziehen) oder der Slot neu generiert
  wird. Dieses „Nur vorwärts"-Verhalten wurde gewählt, um die Funktion
  einfach und vorhersehbar zu halten; es gibt keinen verborgenen Zustand,
  der sich den ursprünglichen Slot jeder Sendung merkt.

> **Die Playout-History bleibt automatisch korrekt.** Die Verschiebung
> passiert *vor* der Ausstrahlung, und die Playout-History zeichnet auf,
> was **tatsächlich** lief und wann (Wanduhrzeit), nicht die geplanten
> Slot-Zeiten. Eine spät ausgestrahlte Sendung wird also mit ihrer
> realen Sendezeit protokolliert, ganz ohne Zusatzaufwand.

> **Wie es unter der Haube funktioniert.**
> `Application_Service_ShowShiftService::applyDelayedStarts()` wählt
> überbuchende Episoden aus, die weder gelöschte Episoden
> (`modified_instance`) noch bereits verschoben (`delayed_start_from`)
> sind und deren Slot-Ende im Vorlauf-Fenster liegt, und läuft dann von
> jeder vorwärts: leert
> komplett überrollte angekreuzte Sendungen, verschiebt die erste nur
> teilweise überrollte angekreuzte Sendung (Start → Content-Ende, Ende
> fix, Items via `SchedulerService::updateScheduleStartTime` verschoben,
> markiert mit `delayed_start_from` = dem Slot-Start, von dem sie
> weggerückt wurde) und stoppt beim ersten nicht angekreuzten Anker.
>
> **Warum ein eigener Marker (27.09.2026).**  Die erste Live-Probe
> zeigte, dass der Juni-Marker — `modified_instance`, Upstreams
> „diese Episode wurde gelöscht" — die verschobene Sendung in Dashboard,
> Live-Info, allen Widgets, Kalender, Showbuilder und
> Überlappungsprüfung versteckte, während das Playout sie spielte.
> Migration 0058 ergänzte `cc_show_instances.delayed_start_from`; eine
> verschobene Sendung bleibt jetzt überall an ihrer neuen Zeit
> sichtbar.  Dass der ursprüngliche Slot gespeichert wird (nicht nur
> ein Flag), lässt den Wiederholungs-Regenerator die verschobene Episode
> auch beim Bearbeiten der Sendung wiederfinden, statt ein Duplikat
> zur Serienzeit anzulegen. Das Ende der überziehenden Sendung wird bis
> dorthin gedehnt, wo ihr Inhalt zur Ruhe kam. Intervall und Vorlauf sind
> über `RASTATIME_SHOW_SHIFT_INTERVAL_SECONDS` (Standard 120) und
> `RASTATIME_SHOW_SHIFT_LEAD_SECONDS` (Standard 900) überschreibbar.
> Siehe ARCHITECTURE §23.24.

---

## 7. Wissenswertes

**Sendungen ohne den Schalter beenden ihren Vorgänger an der Grenze
(seit 2026-11-06).**  Das Playout nimmt „Allow delayed start" wörtlich:
Vor einer Sendung, die es *nicht* erlaubt, wird das, was noch läuft, zum
Sendungsbeginn beendet.  Die letzten Sekunden des ablaufenden Titels
werden über 0,3 s ausgeblendet, sodass die neue Sendung genau auf ihrer
Zeile beginnt; ein Überlauf bis 0,3 s bleibt unangetastet.  Vor dieser
Änderung konnte ein Vorgänger bis etwa 4,5 s in die Folgesendung
hineinlaufen.  Sendungen *mit* dem Schalter behalten die oben
beschriebene sanfte Übergabe.

**Eine Sendung beginnt auch nie zu früh (seit 2026-11-07).**  Endet der
letzte Titel der Vorgängersendung einige Sekunden vor Ihrem Slot (eine
Autoloading-Playlist lässt am Ende oft ein bis drei Sekunden frei),
zieht das Playout Ihren ersten Titel nicht mehr vor, um die Lücke zu
füllen.  Die alte Sendung blendet wie gewohnt aus, die Lücke ist
**Stille**, und Ihr erster Titel beginnt genau auf seiner Zeile - mit
oder ohne „Allow delayed start".  Lücken unter 0,3 s werden weiterhin
nahtlos überbrückt.


- **Eine von Hand verschobene Sendung ist nicht selbst ein
  Verschiebungs-Ursprung.** Eine vom Task verschobene Sendung
  (`delayed_start_from` gesetzt) gilt nie als *Quelle* einer neuen
  Kaskade, eine gelöschte Episode (`modified_instance`) wird ganz
  übersprungen — eine Sendung, die Sie nur im Kalender gezogen haben,
  ist dagegen eine gewöhnliche Episode und kann weiterhin verschoben
  oder geleert werden oder (wenn sie überzieht) selbst eine Kaskade
  auslösen. So bleibt der Mechanismus idempotent, ohne mit Ihren
  manuellen Änderungen in Konflikt zu geraten, konsistent damit,
  wie von Hand bearbeitete Episoden auch von anderen automatischen
  Durchläufen in Ruhe gelassen werden.
- **An jedem Schritt zählt nur das Kästchen der nächsten Sendung.** Ob
  Sendung A selbst angekreuzt ist, ist dafür unerheblich, ob A's
  Überziehung B verschiebt — entscheidend ist das Kästchen von B. (A's
  Kästchen zählt nur, wenn die Sendung *vor* A in A hineinläuft.)
- **Eine Lücke fängt eine Überziehung kostenlos auf.** Wenn nach der
  überbuchten Sendung leere Zeit liegt, läuft ihr Inhalt einfach in die
  Lücke; keine Folgesendung muss sich bewegen, und nichts wird geändert.
- **Autoloading kann die Überbuchung erzeugen (seit 26.10.2026).**  Eine
  Folge, die länger ist als ihr Sendeplatz, wird komplett eingeplant, wenn
  die nächste Sendung das Häkchen hat - das Häkchen genügt also, damit
  solche Folgen vollständig laufen.  Vor einer Sendung ohne Häkchen wird
  sie am Ende gekappt (bis 5 s immer, mehr nur mit „Allow last track to
  exceed time limit“ in ihrem Smart Block); siehe
  [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) §4.

---

## 8. Operator-Checkliste

Damit sich ein Block des Sendeplans verschiebt, wenn eine Sendung
überzieht:

1. **Kreuzen Sie „Verzögerten Start erlauben?"** bei jeder Sendung an,
   die
   später beginnen darf — im Abschnitt **Wann** ihres Formulars
   „Neue Sendung" / „Sendung bearbeiten".
2. **Lassen Sie es frei** bei jeder zeitgebundenen Sendung, die auf die
   Sekunde starten muss (Nachrichten, Feeds, Live-Schaltungen). Das sind
   Ihre Anker.
3. Das ist alles. Wenige Minuten vor der Ausstrahlung verschiebt eine
   Überziehung vor einer angekreuzten Sendung diese automatisch; der
   Schnitt landet bei der angekreuzten Sendung statt bei der überbuchten,
   und nichts überschreitet einen nicht angekreuzten Anker.

Außer dem Kästchen pro Sendung gibt es nichts zu konfigurieren.

---

## 9. Häufige Fragen

### „Ich habe das Kästchen angekreuzt, aber meine Sendung startete trotzdem pünktlich."

Dann hat die Sendung davor nicht überzogen (ihr Inhalt passte in ihren
Slot), oder eine Lücke hat die Überziehung aufgefangen, oder die
Überziehung war kürzer als eine Sekunde. Das Kästchen bewirkt nur etwas,
wenn die vorige Sendung tatsächlich über ihren Slot **in** den Ihren
läuft.

### „Meine Sendung verschob sich nach hinten und ihr letzter Track wurde abgeschnitten."

Das ist so vorgesehen: Die verschobene Sendung behält ihr **Ende** fix,
ist also kürzer und schneidet ihr Ende ab — der Schnitt wandert von der
überbuchten Sendung zu der, die sich freigeschaltet hat, ihn
aufzufangen. Planen Sie etwas weniger Inhalt ein, oder nehmen Sie den
Schnitt in Kauf.

### „Eine ganze Sendung wurde übersprungen — ihr Slot ist leer."

Sie wurde von einer früheren Überziehung komplett verschüttet und auf
einen „übersprungen"-Marker **geleert** (§5). Die frühere Sendung lief
durch ihre Sendezeit. Straffen Sie die überbuchte Sendung, oder setzen
Sie früher einen nicht angekreuzten Anker, damit die Überziehung
abgeschnitten wird, bevor sie diese Sendung erreicht.

### „Ich habe die überbuchte Sendung gekürzt, aber die nächste ist immer noch spät."

Verschiebungen arbeiten nur vorwärts (§6) — sie werden nicht automatisch
zurückgenommen. Ziehen Sie die verschobene Sendung im Kalender zurück in
ihren Slot, oder warten Sie, bis der Slot neu generiert wird.

### „Wie weit kann eine Überziehung den Sendeplan verschieben?"

Bis zur ersten Sendung **ohne** das Kästchen. Alles zwischen zwei nicht
angekreuzten Ankern darf sich verschieben; nichts überschreitet einen
Anker. Setzen Sie Anker, um die Kaskade zu begrenzen.

### „Bringt eine spät laufende Sendung die Playout-History / das Now-Playing durcheinander?"

Nein. Die Verschiebung passiert vor der Ausstrahlung, und die History
protokolliert reale Sendezeiten — eine spät laufende Sendung wird also zu
der Zeit gemeldet, zu der sie tatsächlich lief.

---

## Wie es weitergeht

* [Kalender](./CALENDAR.md) — das Sendungsformular, der Abschnitt
  **Wann**, der Füllbalken, dessen rote Spitze eine überbuchte Sendung
  markiert.
* [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) — ein häufiger Weg,
  wie eine Sendung überbucht wird (eine Dramaturgie, die leicht
  überfüllt).
* [Sendungs-Vorlagen](./SHOW_TEMPLATES.md) — „Verzögerten Start erlauben" in
  eine Vorlage backen, sodass eine ganze Klasse von Sendungen auf einmal
  freigeschaltet wird.
