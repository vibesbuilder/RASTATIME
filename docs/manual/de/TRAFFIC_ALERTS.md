# Verkehrsmeldungen

> **Wo Sie im Handbuch sind.** Lesen Sie zuerst [Bibliothek](./LIBRARY.md)
> → §3 Smart Blocks und
> [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md), idealerweise auch
> [Song Requests](./SONG_REQUESTS.md) — Verkehrsmeldungen nutzen denselben
> inkrementellen On-Air-Fill-Mechanismus. Es wird kein neuer Objekttyp
> eingeführt.

**Verkehrsmeldungen** lassen eine kurzfristige MP3 — eine Meldung, die
Ihnen Minuten vor der Ausstrahlung übergeben wird — automatisch in der
**laufenden Sendung** laufen, binnen etwa zehn Minuten, ohne dass ein Host
etwas anklicken muss und ohne Eingriff in die Playout-Engine.

Das gesamte Feature setzt sich aus Bausteinen zusammen, die Sie bereits
kennen:

- ein **Smart Block**, der Ihre Verkehrsmeldungen erfasst, wird einmalig
  in den Einstellungen als **Verkehrsmeldungs-Quelle** benannt;
- eine **Autoloading Playlist**, die diesen Block enthält, an einigen
  Stellen einer Sendung platziert, macht aus einer gewöhnlichen Sendung
  eine **verkehrsmeldungsfähige Sendung**;
- der Import einer neuen Meldung in die Bibliothek genügt, um sie am
  nächsten Traffic-Slot auf Sendung zu bringen.

Es gibt keine separate „Meldungs-Warteschlange" und keine Änderung auf
der Playout-Seite. Eine Sendung *wird* verkehrsmeldungsfähig, wenn ihre
Autoloading Playlist den konfigurierten Traffic-Block enthält — mehr
nicht.

---

## 1. Das große Bild

```
   REDAKTION                RASTATIME                       ON AIR
   ┌──────────┐  Import     ┌────────────────────────┐
   │ Verkehr  │────────────▶│ Bibliothek: die Datei   │
   │  .mp3    │             │  passt jetzt zum Block   │
   └──────────┘             └───────────┬─────────────┘
                                        │  die laufende Sendung füllt
                                        │  sich inkrementell, on air
                            ┌───────────▼─────────────┐   ┌──────────┐
                            │ Traffic-Block am NÄCHSTEN│──▶│ Sende-   │
                            │  Dramaturgie-Slot;        │   │  plan    │
                            │  Älteste zuerst, einmalig │   └──────────┘
                            └──────────────────────────┘
```

Der Mechanismus ist derselbe, den schon die Song Requests verwenden
(siehe [Song Requests](./SONG_REQUESTS.md) §5): eine
verkehrsmeldungsfähige Sendung wird **inkrementell gefüllt, während sie
läuft**, nur ein Stück weit vor dem Play-Head. Jeder Traffic-Slot der
Sendung wird kurz vor seiner Ausstrahlung aufgelöst — und nimmt dabei
mit, was inzwischen importiert wurde. Eine *während* der Sendung
importierte Meldung läuft daher am **nächsten** Traffic-Slot; nichts
bereits Eingeplantes wird nach hinten geschoben.

Sie konfigurieren die Quelle einmal (§2–§3) und platzieren den Block in
Ihren Sendungen (§4); danach läuft das Feature unbeaufsichtigt (§5).

---

## 2. Der Verkehrsmeldungs-Smart-Block

Eine Verkehrsmeldung ist einfach eine Audiodatei. Der „Traffic-Block" ist
ein gewöhnlicher [Smart Block](./LIBRARY.md), dessen Kriterien genau diese
Dateien erfassen und sonst nichts. Typische Einrichtung:

- **Kriterien**, die nur Meldungen auswählen — etwa *Genre ist Verkehr*
  oder *Ordner/Pfad enthält `/verkehr/`*, was auch immer sie in Ihrer
  Bibliothek sauber isoliert.
- **Sortierung: Neueste zuerst** ist naheliegend, aber die
  Ausstrahlungsreihenfolge hängt nicht davon ab — das System spielt stets
  die **älteste noch nicht ausgestrahlte** Meldung zuerst (die mit der
  knappsten Frist; siehe §5).
- **Kürzlich gespielte Tracks ausschließen** (optional, empfohlen): hat
  eine Meldung einmal gelaufen, fällt sie aus dem Block, sodass eine
  veraltete Meldung an einem späteren Tag nicht erneut aufgegriffen wird.
- **Kein enges Item-Limit.** Lassen Sie Platz für mehrere Meldungen,
  damit bei zwei kurz aufeinanderfolgenden beide Kandidaten sind.

> **Tipp.** Halten Sie diesen Block ausschließlich für Verkehr. Verwenden
> Sie keinen Musik-Block — jede Datei, die der Block erfasst, gilt als
> ausstrahlbare Meldung.

---

## 3. In den Einstellungen auswählen

Öffnen Sie **Einstellungen → Allgemeine Einstellungen** und suchen Sie
**Verkehrsmeldungs-Smart-Block**. Wählen Sie Ihren Traffic-Block aus der
Liste und speichern Sie.

- Die Liste enthält jeden Smart Block Ihrer Bibliothek.
- **`(keiner — deaktiviert)`** ist die Voreinstellung und schaltet das
  Feature vollständig ab — eine Sendung, die den Block dennoch enthält,
  spielt ihn dann einmalig als gewöhnlichen Block.

Es kann immer nur **ein** Block die Verkehrsmeldungs-Quelle sein. Dies ist
der einzige Schalter, der das Feature scharf stellt.

---

## 4. Eine verkehrsmeldungsfähige Sendung bauen

Fügen Sie den Traffic-Block der **Autoloading Playlist** einer Sendung
hinzu, genauso wie Sie jeden Block hinzufügen — aber platzieren Sie ihn an
**mehreren Stellen** entlang der Dramaturgie der Sendung, nicht nur
einmal. Zum Beispiel:

```
   Jingle · Musik · VERKEHR · Musik · Musik · VERKEHR · Musik · …
```

Jeder `VERKEHR`-Eintrag ist ein Slot, an dem eine Meldung *einspringen
darf*. Wartet beim Erreichen des Slots keine Meldung, spielt der Slot
nichts und das nächste Element läuft einfach — leere Slots kosten Sie also
nichts.

**Wie dicht Sie sie platzieren, ist die Art, wie Sie die
Zehn-Minuten-Frist halten** (siehe §6). Als Faustregel hält ein
Traffic-Slot alle fünf bis sieben Programm-Minuten, ohne einen sehr langen
Track unmittelbar davor, jede Meldung bequem innerhalb ihrer Frist.

Die Sendung benötigt eine aktivierte **Autoloading Playlist** (sie ist es,
die die Sendung sich selbst füllen lässt). Sonst sind an der Sendung keine
besonderen Einstellungen nötig.

---

## 5. Wie und wann eine Meldung läuft

Während eine verkehrsmeldungsfähige Sendung läuft, löst der Fill-Task
(alle zwei Minuten) ihre Dramaturgie ein Stück vor dem Play-Head auf.
Erreicht er einen Traffic-Slot, wählt er **eine** Meldung nach diesen
Regeln:

1. **Älteste zuerst (FIFO).** Unter den wartenden Meldungen läuft die
   **zuerst importierte** — die mit der knappsten Zehn-Minuten-Frist.
2. **Einmalig.** Eine Meldung, die in dieser Sendung bereits eingeplant
   ist, wird nie erneut gewählt, sodass derselbe Alert nicht zweimal
   läuft, obwohl der Block an mehreren Slots sitzt.
3. **Kein Füller.** Wartet keine frische Meldung, spielt der Slot
   **nichts** — es gibt bewusst keinen Zufallstitel-Fallback (anders als
   bei einem Request-Slot). Stattdessen läuft das nächste Programm-Element.

Der normale Arbeitsablauf ist also schlicht: **importieren Sie die Meldung
in die Bibliothek** (in den Ordner/das Genre, das Ihr Block erfasst).
Innerhalb eines Poll-Zyklus wird sie zum Kandidaten und läuft am nächsten
Traffic-Slot der laufenden Sendung.

> **Unter der Haube.** Verkehrsmeldungen und Song Requests teilen sich
> eine inkrementelle Fill-Engine. Der einzige Unterschied ist, wie ein
> Slot auflöst: ein Request-Slot zieht Hörer-Wünsche und fällt auf einen
> Zufallstitel zurück; ein Traffic-Slot zieht die älteste noch nicht
> ausgestrahlte Meldung und fällt auf *nichts* zurück. Beide schreiben in
> den normalen Sendeplan, den die Playout-Engine bei ihrem nächsten
> Refresh aufnimmt — der Live-Audio-Pfad wird nicht verändert, und die
> Meldung erscheint wie jeder Track in der History und im Kalender.

---

## 6. Die Zehn-Minuten-Frist halten Sie

Da eine Meldung an ihrem **Dramaturgie-Slot** läuft, hängt die
Geschwindigkeit von der Art ab, wie Sie die Sendung gebaut haben — nicht
davon, dass das System in einen Track hineinschneidet. RASTATIME
überspringt den gerade laufenden Track **nicht**, um eine Meldung
hinauszudrängen (dieser automatische *Deadline-Skip* ist eine geplante
spätere Option, zurückgestellt, bis der Live-Betrieb zeigt, dass er
tatsächlich gebraucht wird).

Sie halten die SLA mit zwei Gewohnheiten:

- **Platzieren Sie Traffic-Slots dicht** — nicht weiter als Ihre Frist
  auseinander, sodass der nächste Slot immer nah ist.
- **Halten Sie den Track vor einem Slot kurz.** Ein fünfzehnminütiger Mix
  direkt vor einem Traffic-Slot kann den Slot allein schon über zehn
  Minuten hinausschieben.

Kann Ihr Programm einen Slot innerhalb der Frist wirklich nicht garantieren
(etwa bei sehr langformatigen Sendungen), sagen Sie Ihrem
RASTATIME-Betreuer Bescheid — der aktive Deadline-Skip kann dann gebaut
und aktiviert werden.

---

## 7. Betreiber-Checkliste

1. **Einmalig:** einen Smart Block bauen, der nur Ihre
   Verkehrsmeldungen erfasst (§2).
2. **Einmalig:** Einstellungen → Allgemein → **Verkehrsmeldungs-Smart-
   Block** → auswählen (§3).
3. **Pro Sendung:** diesen Block an mehreren Stellen der Autoloading
   Playlist der Sendung einfügen, ≤ Ihrer Frist auseinander (§4).
4. **Pro Meldung:** die MP3 so in die Bibliothek importieren, dass sie zum
   Block passt — sie läuft am nächsten Slot (§5).
5. **Feature pausieren:** Einstellungen → den Block zurück auf
   `(keiner — deaktiviert)` setzen.

---

## 8. Häufige Fragen

### „Ich habe eine Meldung importiert, aber sie lief nicht."
Prüfen Sie drei Dinge: ob die Datei tatsächlich **zum Traffic-Block
passt** (öffnen Sie den Block und bestätigen Sie, dass sie erscheint); ob
der **Block in den Einstellungen ausgewählt** ist; und ob die **laufende
Sendung den Block** in ihrer Autoloading Playlist enthält. Treffen alle
drei zu, läuft sie am nächsten Traffic-Slot — der je nach Dramaturgie ein
paar Minuten entfernt sein kann (§6).

### „Dieselbe Meldung lief zweimal."
Das sollte nicht passieren — eine in der Sendung bereits eingeplante
Meldung wird von späteren Slots ausgeschlossen. Lief sie wirklich erneut,
sind die beiden Ausstrahlungen in *verschiedenen Sendungen* (die Slots
einer neuen Sendung sehen sie als frisch, bis sie tatsächlich gespielt
wurde; aktivieren Sie *Kürzlich gespielte Tracks ausschließen* am Block,
um das zu verhindern).

### „Ein Traffic-Slot spielte nichts."
Das ist erwartet, wenn keine frische Meldung wartete — ein Traffic-Slot
hat keinen Füller, also läuft schlicht das nächste Programm-Element. Leere
Slots sind gratis; platzieren Sie so viele Sie möchten.

### „Zwei Meldungen kamen gleichzeitig — welche läuft zuerst?"
Der **älteste Import** zuerst, dann der nächste am folgenden Traffic-Slot.
Jeder Slot spielt eine Meldung, geben Sie ihnen also genug Slots zum
Abfließen.

### „Wie schnell läuft eine Meldung?"
Am nächsten Traffic-Slot der laufenden Sendung. Bei Slots innerhalb Ihrer
Zehn-Minuten-Frist und ohne überlangen Track davor ist das innerhalb der
SLA. RASTATIME unterbricht dafür nicht den laufenden Track (§6).

### „Kann ich es abschalten?"
Ja — Einstellungen → **Verkehrsmeldungs-Smart-Block** →
`(keiner — deaktiviert)`. Eine Sendung, die den Block noch trägt, spielt
ihn dann einfach einmalig als gewöhnlichen Block.

---

## Wohin als Nächstes

- [Song Requests](./SONG_REQUESTS.md) — derselbe inkrementelle
  On-Air-Fill, für Hörer-Wünsche.
- [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) — wie eine Sendung
  sich selbst aus Playlists und Blöcken füllt.
- [Bibliothek](./LIBRARY.md) → §3 Smart Blocks — den Block bauen, der Ihre
  Meldungen erfasst.
