# Autoloading Playlists

> **Wo Sie sich im Handbuch befinden.** Lesen Sie zuerst
> [Bibliothek](./LIBRARY.md) und [Kalender](./CALENDAR.md) —
> autoloading Playlists verbinden ein Bibliotheks-Item (die
> Playlist) mit einem Kalender-Item (die Sendung). Die
> separate [Auto DJ](./AUTO_DJ.md)-Funktion ist *nicht*
> dasselbe; siehe §8 für den Unterschied.

Eine **autoloading Playlist** ist eine Bibliotheks-Playlist,
die *an eine Sendungsdefinition angehängt* ist, sodass jede
Episode der Sendung automatisch aus dieser Playlist gefüllt
wird. Sie verwalten die Playlist einmal; jede Montags-Sendung
um 09:00 nimmt auf, was die Playlist gerade enthält.

Dies ist der mächtigste Arbeitserleichterer in RASTATIME für
Stationen mit regelmäßiger Programmierung. Eine
"Morgensendung" mit einer autoloading Playlist aus Smart
Blocks braucht null wöchentliche Aufmerksamkeit: bearbeiten
Sie die Smart-Block-Kriterien einmal pro Saison, und die
Sendung füllt sich jeden Werktag selbst.

---

## 1. Die Grundlagen

Eine Sendung mit einer autoloading Playlist wird **einmal
pro Episode** vom Hintergrund-Autoplaylist-Builder gebaut.
Der Build erfolgt typischerweise 60 Sekunden vor Beginn der
Episode — gerade rechtzeitig, damit die Sendung den
allerneuesten Zustand der Playlist widerspiegelt.

Die Build-Reihenfolge für jede Episode ist:

1. (Optional) **Intro-Playlist** am Anfang hinzugefügt.
2. **Body-Playlist**-Items in Reihenfolge hinzugefügt; Smart
   Blocks expandieren hier.
3. (Optional) **Outro-Playlist** am Ende hinzugefügt.
4. Wenn der Slot noch mehr als 5 s ungeplanten Schwanz hat
   und **Wiederholen bis voll** aktiviert ist, wiederholt
   sich der Body, bis er füllt (Smart Blocks werden bei
   jedem Zyklus neu ausgewertet).
5. Die nachfolgenden Sekunden nach dem Outro-Slot werden
   getrimmt, sodass kein Item überläuft.

Wenn der Operator manuell etwas in die Sendung eingeplant
hat, bevor der Autoplaylist-Build lief, sieht der
Autoplaylist-Build den Slot als bereits gefüllt und tut
nichts.

---

## 2. Eine autoloading Playlist an eine Sendung anhängen

Öffnen Sie die Sendung im Kalender → **Sendung bearbeiten**
→ erweitern Sie **Autoloading Playlist**.

```
   ┌─────────────────────────────────────────────────────────┐
   │  Autoloading Playlist                                   │
   ├─────────────────────────────────────────────────────────┤
   │  ☑  Autoloading Playlist hinzufügen?                    │
   │                                                         │
   │   Intro-Playlist:    [Auswählen... ▾]                   │
   │   Haupt-Playlist:    [Auswählen... ▾]  ◀── Pflicht      │
   │   Outro-Playlist:    [Auswählen... ▾]                   │
   │                                                         │
   │  ☐  Wiederholen bis voll                                │
   └─────────────────────────────────────────────────────────┘
```

| Feld | Was es tut |
|---|---|
| **Autoloading Playlist hinzufügen?** | Hauptschalter. Nicht angekreuzt = kein Auto-Build. |
| **Intro-Playlist** | Am ganz Anfang der Sendung hinzugefügt. Optional. Spielt genau einmal. |
| **Haupt-Playlist** | Der Body-Inhalt. Erforderlich, wenn der Hauptschalter an ist. Smart Blocks in dieser Playlist expandieren zur Build-Zeit unter Verwendung der verbleibenden Sekunden des Slots als Limit, falls konfiguriert. |
| **Outro-Playlist** | Am ganz Ende der Sendung hinzugefügt. Optional. Spielt genau einmal. |
| **Wiederholen bis voll** | Wenn an, wiederholen sich die Items der Haupt-Playlist (Smart Blocks werden bei jedem Zyklus neu ausgewertet), solange das noch Zeilen bringt (streng in Reihenfolge, Stopp beim ersten Titel, der nicht passt). Wenn aus, spielt die Haupt-Playlist einmal; einen Rest füllen ihre „verbleibende Zeit"-Smart-Blocks, sonst bleibt er Stille. |

Speichern Sie die Sendung. Der Autoplaylist-Builder nimmt
die Anbringung beim nächsten Poll (standardmäßig alle 60 s)
auf und baut zukünftige Episoden entsprechend.

---

> **Wiederholung von Sendung (seit 2026-10-18).**  Der Abschnitt
> direkt darüber, **Wiederholung** (eigener Abschnitt seit
> 2026-10-21), trägt **Wiederholung von Sendung**: Original
> wählen, und dessen zuletzt gesendeter Inhalt wird kurz vor dem Start
> in diese Sendung übernommen; die Autoloading-Playlist füllt dann nur
> die Restzeit.  Details in [Kalender](./CALENDAR.md) § 4
> „Wiederholung einer anderen Sendung".

> **Autoloading je Episode (seit 2026-11-03).**  „Episode bearbeiten"
> kann einer Episode eine eigene Playlist, ein eigenes Intro, Outro oder
> die Wiederholung geben, oder gar kein Autoloading; dazu **Use the
> show's autoloading settings** im Abschnitt Autoloading Playlist
> abwählen.  Nur vor der Befüllung (etwa eine Stunde vor dem Start) -
> siehe [Kalender](./CALENDAR.md) § 3.

## 3. Die 60-Sekunden-Build-Kadenz

Der Autoplaylist-Builder läuft alle 60 Sekunden. Für jede
kommende Episode einer Autoloading-Playlist-Sendung:

- Wenn die Episode in **weniger als ~60 s** startet und
  noch nicht gebaut wurde, baue jetzt.
- Andernfalls lasse sie für den nächsten Zyklus.

Das bedeutet, dass der Build *immer* ein Build des
**aktuellen** Zustands der Playlist ist, nicht eines
veralteten Snapshots. Wenn Sie die Playlist um 08:58 für
eine 09:00-Sendung bearbeiten, erhält die 09:00-Sendung die
bearbeitete Version.

> **Operator-Tipp.** Wenn Sie eine Same-Minute-Bearbeitung
> pushen müssen (z.B. einen Track um 08:59:30 für eine
> 09:00-Sendung tauschen), erzwingen Sie einen manuellen
> Build: Öffnen Sie die Sendung → **Sendeplan leeren** →
> Schließen. Der nächste Poll-Zyklus (innerhalb von 60 s)
> wird aus der aktualisierten Playlist neu bauen.

> **Wie es unter der Haube funktioniert.** Der Builder ist
> die statische Methode
> `AutoPlaylistManager.buildAutoPlaylist()`, aufgerufen vom
> `SchedulePollJob` des Worker-Job-Runners alle 60 s. Jeder
> Zyklus läuft jede kommende Sendung mit
> `cc_show_autoplaylist.has_autoplaylist = TRUE` durch,
> prüft, ob der Sendeplan der Episode bereits gefüllt ist,
> und baut andernfalls. Siehe ARCHITECTURE §17 für die
> vollständige Pipeline.

---

## 4. Wie der Slot befüllt wird (seit 2026-10-01)

Der Builder befüllt eine Sendung in drei Schritten, immer gegen
die Zeit, die im Slot **wirklich** noch frei ist:

1. Die **Intro-Playlist** kommt an den Anfang, genau einmal.
2. Die **Outro-Playlist** kommt ans Ende, genau einmal — sie wird
   real gesetzt, ihre Länge ist damit exakt bekannt (die
   Probe-Einfügung mit Messung der früheren Builds entfällt, und
   mit ihr die 5-Sekunden-Marge).
3. Die **Autoloading-Playlist** füllt den Raum dazwischen.

Jede Liste wird **streng in ihrer Reihenfolge** genommen und
endet beim ersten Titel, der nicht mehr vor das Sendungsende
passt (Operator-Entscheid, „Variante a"): Nichts wird je über
das Ende hinaus gesetzt, also muss hinterher nichts gekürzt
werden. Ein Intro oder Outro, das länger ist als der Slot, wird
genauso beschnitten (die nicht passenden Titel bleiben weg; das
Log nennt die Zahl).

„Wirklich frei" meint die ausgelegte Zeit: Seit 2026-09-29
überlappen die Zeilen um ihren Crossfade (Hauswert 3 s oder der
des Track-Typs), und die Summe der Titellängen sagt nicht mehr,
wo die letzte Zeile endet. Der Builder legt die Zeilen mit
derselben Paar-Regel aus wie der Scheduler; eine 60-Minuten-
Sendung mit fünfzehn Musiktiteln endet darum **nicht** mehr
42 Sekunden zu früh.

Ein Smart Block mit *Begrenzen auf: verbleibende Sendezeit*
bekommt diese ausgelegte Zeit als Budget — erhöht um die
Überlappung, die seine eigene Auswahl erzeugt; der Builder
versucht das mehrfach und behält die beste Passung. Nach dem
Füllen zieht ein Nachfüll-Lauf die „verbleibende Zeit"-Blöcke
der Playlist gegen die Restlücke, bis die letzte Zeile innerhalb
von **4 Sekunden** vor dem Sendungsende endet oder nichts mehr
passt. In den Proben vom 2026-10-01 lag die Lücke meist bei
0–3 s, schlimmstenfalls bei etwa 6 s (der Löser des Blocks
arbeitet mit Zufall; der Pool bestimmt, was möglich ist), nie
eine Überbuchung.

> **So funktioniert es unter der Haube.** `AutoPlaylistManager::fillInstance()`
> expandiert die Playlists selbst (`expandPlaylist`), plant mit
> `chainEnd()` — der Paar-Regel von `Scheduler::calculateCrossfades`
> — und fügt nur die passenden Zeilen über
> `Scheduler::scheduleFilesAfter()` ein. Die Log-Zeile
> „show_instance_id=N filled - intro a, outro b, auto c (+d top-up)
> rows, x s free at the end" fasst jeden Build zusammen;
> `ap_fill_test.php` (C:\Temp\optd) probt eine Befüllung an einer
> temporären Episode.

**Eine Folge, die länger ist als der Sendeplatz (seit 26.10.2026).**
Das erste Element, das nicht passte, wurde bisher weggelassen, und
Auto DJ füllte die leere Sendung - auch bei einer Folge von
60:00,2 in einem 60-Minuten-Platz.  Jetzt wird ein solches Element
trotzdem eingeplant, als letzte Zeile über das Sendungsende hinaus,
wenn

- es ein **einzelnes Element** ist (direkt aus der Playlist oder aus
  einem Smart Block mit Limit nach Anzahl, etwa „Album is ...,
  newest, 1 item“) und die **nächste Sendung „Allow delayed start“**
  hat: Die Folge läuft komplett, die nächste Sendung beginnt später
  (siehe [Verzögerter Sendungsbeginn](./DELAYED_START.md)); oder es
  ist höchstens **5 Sekunden** zu lang (Kodier-Überhang) - am Ende
  gekappt;
- oder sein Smart Block **„Allow last track to exceed time limit“**
  hat und die nächste Sendung später beginnen darf oder mindestens
  die **Hälfte** des Elements vor dem Ende läuft - am Ende gekappt
  (keine Schnipsel).

Vor einer Sendung ohne „Allow delayed start“ wird der Überhang am
Ende gekappt, wie bei jeder überbuchten Sendung; der Kalender zeigt
die rote Spitze.  Vor einem festen Outro erlaubt es nur eine
nächste Sendung, die später beginnen darf - so wird nie das Outro
gekappt.  Musikblöcke mit Zeitlimit ohne das Häkchen bleiben exakt.
Sonst wird das Element wie bisher weggelassen.  Das Log meldet
„item N runs x s past the show end (Grund)“.

**Ein Füll-Outro folgt dem Inhalt (seit 26.10.2026).**  Eine
Outro-Playlist mit einem Smart-Block *Limit to: Time remaining in
show* - die Playlists „Tagesplaylist ... Outro“, allein oder hinter
einem Sender-Outro-Jingle - ist ein Füller, kein festes Ende.  Sie
kommt **nach** dem Inhalt, in ihrer eigenen Reihenfolge, und füllt
nur, was übrig ist: Inhalt → Outro-Jingle → Musik bis zum Ende, wie
in LibreTime.  Vorher wurde sie wie jedes Outro zuerst gesetzt,
belegte den ganzen Slot und ließ keinen Platz für den Inhalt (eine
Folge von 59:53 in einer 60-Minuten-Sendung fiel weg).  Ein Outro
ohne einen solchen Block (StationID, Dayteaser) bleibt das feste
Ende aus Schritt 2.

---

## 5. Die richtige Playlist für Autoloading auswählen

### Was gut funktioniert

- **Nur-Smart-Block-Playlists** mit *Begrenzen auf:
  Verbleibende Zeit in der Sendung*. Das mit Abstand
  häufigste Muster: ein Smart Block, ein Filter ("Genre =
  Pop und BPM > 100"), ein Limit. Gegen die wirklich
  verbleibende Zeit ausgelegt füllt dies jede Slot-Länge bis
  auf wenige Sekunden.

- **Intro + Smart Block + Outro** für Sendungen mit einem
  Station-ID-Intro und einem Station-ID-Outro. Das Intro
  spielt genau einmal, der Smart Block füllt den Body, das
  Outro spielt genau einmal.

- **Statische Playlists für kurze Sendungen** unter 5
  Minuten, wo Smart Blocks Overkill wären. Eine
  60-s-"Nachrichten-Update"-Sendung mit drei expliziten
  Clip-Referenzen ist ohne Smart Blocks in Ordnung.

### Was nicht gut funktioniert

- **Mischung aus statischen Tracks und
  "Wiederholen-bis-voll"-Smart-Blocks** — die Smart Blocks
  fügen weiter Tracks hinzu, auch nachdem die statischen
  Tracks den Slot gefüllt hätten. Für den Builder
  vorhersehbar, für den Operator überraschend.

- **Webstreams oder Line-Ins im Body**, wenn **Wiederholen
  bis voll** an ist. Webstream- und Line-In-Items haben
  eine konfigurierte Dauer (standardmäßig 60 min), aber das
  Playout behandelt sie als "spiele für immer, bis
  gestoppt wird"; der Auto-Builder sieht die konfigurierte
  Dauer, aber die tatsächlich verbrauchte Zeit ist, was die
  Sendung erlaubt. Generell verwenden Sie Webstreams /
  Line-Ins als *gesamten* Body, nicht gemischt.

- **Sehr lange Playlists** (1000+ Items) — der Auto-Build
  ist schnell, aber Sie wollen normalerweise einen Smart
  Block über einer langen statischen Playlist für die
  Neu-Auswertung bei jedem Zyklus.

---

## 6. Wiederholen-bis-voll-Verhalten

Wenn **Wiederholen bis voll** angekreuzt ist:

- Die Items der Haupt-Playlist werden eingefügt, Smart
  Blocks expandiert, und die Playlist läuft erneut, solange das
  noch Zeilen bringt — streng in Reihenfolge, Stopp beim ersten
  Titel, der nicht passt.
- Der Zyklus wertet Smart Blocks bei jeder Iteration neu
  aus, sodass ein *dynamischer* Smart Block bei jeder
  Wiederholung eine andere Auswahl trifft — variierter
  Inhalt innerhalb eines Slots.
- Track-only-Playlists wiederholen sich auch, sodass
  dieselben Tracks erneut spielen. Wenn Sie variierten
  Inhalt möchten, verwenden Sie Smart Blocks.

Wenn nicht angekreuzt:

- Die Haupt-Playlist spielt einmal durch.
- Einen Rest, den der Body lässt, füllen die „verbleibende
  Zeit"-Smart-Blocks der Playlist (der Nachfüll-Lauf läuft in
  jedem Fall); ohne solchen Block bleibt er Stille.

> **Operator-Tipp.** Aktivieren Sie immer **Wiederholen
> bis voll** für einen Smart-Block-Body. Ohne dies spielt
> eine 60-min-Sendung mit einem Smart Block "Begrenzen auf
> 10 Tracks" ~40 min Musik und 20 min Stille vor dem Outro.

---

## 7. Eine autoloading Playlist entfernen

Sendung bearbeiten → **Autoloading Playlist** erweitern →
**Autoloading Playlist hinzufügen?** abwählen → Speichern.

Zukünftige Episoden werden nicht mehr automatisch gebaut.
Bereits gebaute Episoden behalten ihren gebauten Inhalt
(keine rückwirkende Änderung). Um eine bereits gebaute
Episode zu leeren, öffnen Sie die Sendung im Kalender →
**Sendeplan leeren**.


> **Gelöschte Playlist (seit 28.10.2026).**  Beim Löschen der Playlist
> aus der Bibliothek fragt RASTATIME zuerst und zählt die Sendungen auf,
> die sie verwenden; nach Bestätigung wird auch das Häkchen *Add
> Autoloading Playlist* dieser Sendungen abgeschaltet.  Trägt eine
> Sendung trotzdem das Häkchen ohne Playlist (Import, alte Datenbank),
> warnt das Dashboard-Banner „Autoloading ist an, aber die Sendung hat
> keine Playlist" für jede Episode der nächsten 48 Stunden - Sendung
> bearbeiten und eine Playlist wählen.

---

## 8. Autoloading Playlists vs Auto DJ

Diese beiden Funktionen werden leicht verwechselt. Schnelle
Referenz:

| | Autoloading Playlist | Auto DJ |
|---|---|---|
| **Wo angehängt** | An ein Sendungs-Bearbeitungsformular einer bestimmten Sendung | Einstellungen → Auto DJ (stationsweit) |
| **Wann es füllt** | Pro Episode, 60 s vor Beginn | (a) Erstellt neue Sendungen in Kalenderlücken. (b) Füllt unvollständige kommende Sendungen auf. |
| **Womit es füllt** | Die konfigurierte Playlist (jede Struktur) | Eine konfigurierte Auto-DJ-Playlist |
| **Welche Sendungen betroffen** | Nur die Sendung, an die es angehängt ist | Alle Sendungen + erstellt neue |
| **Braucht einen Host?** | Nein | Nein |
| **Standardmäßig deaktiviert** | Ja | Ja |

Verwenden Sie autoloading Playlists für **regelmäßige
Programmierung** (die Morgensendung verwendet immer die
Morgen-Playlist). Verwenden Sie Auto DJ für **ungeplante
Sendezeit** (was Sie vergessen haben einzuplanen, fängt der
Auto DJ ab).

Siehe [Auto DJ](./AUTO_DJ.md) für die vollständige Funktion.

---

## 9. Häufig gestellte Fragen

### "Ich habe eine Playlist angehängt, aber die Sendung blieb leer."

Drei Möglichkeiten:

1. Die Episode hat bereits begonnen — der Auto-Build
   berührt nur *zukünftige* Episoden.
2. Die Episode wurde bereits manuell gefüllt. Der
   Auto-Build überspringt jede Sendung, die bereits
   geplante Items hat.
3. Der Worker-Job-Runner läuft nicht. Prüfen Sie
   `Get-Service RASTATIME-WORKER`.

### "Wie sehe ich, ob der Auto-Build für eine bestimmte Episode lief?"

Öffnen Sie die Sendung im Kalender; der Kalender-Füll-Balken
sollte > 0 % sein. Wenn er Sekunden vor Startzeit 0 % ist,
ist der Auto-Build noch nicht gelaufen. Warten Sie 60 s und
laden Sie neu, oder verwenden Sie **Sendeplan leeren** +
erneut öffnen, um den nächsten Poll-Zyklus zu zwingen, die
Episode als frisch zu behandeln.

### "Kann die Intro-Playlist einen Smart Block enthalten?"

Ja, aber das Intro wird zuerst gesetzt, gegen den ganzen
freien Slot, und das Outro direkt dahinter. Wenn der
Smart Block des Intros das "verbleibende Zeit"-Limit hat,
wird er die ganze Sendung verschlingen. Verwenden Sie
Smart Blocks mit fester Dauer ("Begrenzen auf 30 s") oder
statische Tracks für Intro / Outro.

### "Warum wählt der Auto-Build manchmal denselben Track zweimal?"

Wenn die Body-Playlist **Wiederholen bis voll** mit einer
statischen Playlist verwendet, wiederholen sich dieselben
Tracks. Um dies zu vermeiden, entweder:

- Verwenden Sie einen Smart Block mit Typ **Dynamisch**,
  sodass jede Wiederholung neu abfragt.
- Setzen Sie "Sortieren: Zufällig" innerhalb des Smart
  Blocks, sodass jede Wiederholung eine andere zufällige
  Reihenfolge wählt.

### "Kann ich zwei autoloading Playlists in einer Sendung haben?"

Nein. Das Modell ist **Intro + Body + Outro**, und nur der
Body ist die "Haupt"-autoloading Playlist. Um zwei
unterschiedliche Auswahlen in einer Sendung zu erhalten,
legen Sie zwei Smart Blocks — einen je Auswahl — in die
Body-Playlist. Ein einzelner Smart Block kann nur
Alternativen desselben Feldes anbieten (z.B. Genre Jazz oder
Blues); siehe [Import / Export → blocks.json](./IMPORT_EXPORT.md#blocksjson).

---

## Wohin als Nächstes

* [Teaser-Automatik](./TEASERS.md) — das Smart-Block-Kriterium,
  das die richtigen „heute"-/„morgen"-Jingles in Intro-, Outro-
  und Inhalts-Playlisten legt.
* [Auto DJ](./AUTO_DJ.md) — die stationsweite
  Automatisierung, die per-show Autoloading ergänzt.
* [Sendungs-Vorlagen](./SHOW_TEMPLATES.md) — die
  Autoloading-Playlist-Anbringung als Teil einer Vorlage
  erfassen, sodass jede neue Sendung dasselbe Setup
  erhält.
* [Bibliothek](./LIBRARY.md) → §3 Smart Blocks — das
  mächtigste Body-Playlist-Primitiv.
