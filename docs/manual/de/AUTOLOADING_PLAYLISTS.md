# Autoloading Playlists

> **Wo Sie sich im Handbuch befinden.** Lesen Sie zuerst
> [Bibliothek](./LIBRARY.md) und [Kalender](./CALENDAR.md) —
> autoloading Playlists verbinden ein Bibliotheks-Item (die
> Playlist) mit einem Kalender-Item (die Sendung). Die
> separate [Auto DJ](./AUTO_DJ.md)-Funktion ist *nicht*
> dasselbe; siehe §8 für den Unterschied.

Eine **autoloading Playlist** ist eine Bibliotheks-Playlist,
die *an eine Sendungsdefinition angehängt* ist, sodass jede
Instanz der Sendung automatisch aus dieser Playlist gefüllt
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
pro Instanz** vom Hintergrund-Autoplaylist-Builder gebaut.
Der Build erfolgt typischerweise 60 Sekunden vor Beginn der
Instanz — gerade rechtzeitig, damit die Sendung den
allerneuesten Zustand der Playlist widerspiegelt.

Die Build-Reihenfolge für jede Instanz ist:

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
auf und baut zukünftige Instanzen entsprechend.

---

## 3. Die 60-Sekunden-Build-Kadenz

Der Autoplaylist-Builder läuft alle 60 Sekunden. Für jede
kommende Instanz einer Autoloading-Playlist-Sendung:

- Wenn die Instanz in **weniger als ~60 s** startet und
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
> prüft, ob der Sendeplan der Instanz bereits gefüllt ist,
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
> temporären Instanz.

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

Zukünftige Instanzen werden nicht mehr automatisch gebaut.
Bereits gebaute Instanzen behalten ihren gebauten Inhalt
(keine rückwirkende Änderung). Um eine bereits gebaute
Instanz zu leeren, öffnen Sie die Sendung im Kalender →
**Sendeplan leeren**.

---

## 8. Autoloading Playlists vs Auto DJ

Diese beiden Funktionen werden leicht verwechselt. Schnelle
Referenz:

| | Autoloading Playlist | Auto DJ |
|---|---|---|
| **Wo angehängt** | An ein Sendungs-Bearbeitungsformular einer bestimmten Sendung | Einstellungen → Auto DJ (stationsweit) |
| **Wann es füllt** | Pro Sendungsinstanz, 60 s vor Beginn | (a) Erstellt neue Sendungen in Kalenderlücken. (b) Füllt unvollständige kommende Sendungen auf. |
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

1. Die Instanz hat bereits begonnen — der Auto-Build
   berührt nur *zukünftige* Instanzen.
2. Die Instanz wurde bereits manuell gefüllt. Der
   Auto-Build überspringt jede Sendung, die bereits
   geplante Items hat.
3. Der Worker-Job-Runner läuft nicht. Prüfen Sie
   `Get-Service RASTATIME-WORKER`.

### "Wie sehe ich, ob der Auto-Build für eine bestimmte Instanz lief?"

Öffnen Sie die Sendung im Kalender; der Kalender-Füll-Balken
sollte > 0 % sein. Wenn er Sekunden vor Startzeit 0 % ist,
ist der Auto-Build noch nicht gelaufen. Warten Sie 60 s und
laden Sie neu, oder verwenden Sie **Sendeplan leeren** +
erneut öffnen, um den nächsten Poll-Zyklus zu zwingen, die
Instanz als frisch zu behandeln.

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
fügen Sie einen Smart Block in den Body ein, der zwei
Kriteriensätze über die Smart-Block-ODER-Gruppe vereint.

---

## Wohin als Nächstes

* [Auto DJ](./AUTO_DJ.md) — die stationsweite
  Automatisierung, die per-show Autoloading ergänzt.
* [Sendungs-Vorlagen](./SHOW_TEMPLATES.md) — die
  Autoloading-Playlist-Anbringung als Teil einer Vorlage
  erfassen, sodass jede neue Sendung dasselbe Setup
  erhält.
* [Bibliothek](./LIBRARY.md) → §3 Smart Blocks — das
  mächtigste Body-Playlist-Primitiv.
