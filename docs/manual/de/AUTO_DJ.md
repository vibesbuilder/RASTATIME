# Auto DJ

> **Wo Sie sich im Handbuch befinden.** Lesen Sie zuerst
> [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md), falls
> noch nicht geschehen — Auto DJ ist das stationsweite
> Gegenstück zur per-show autoloading Playlist. §8 dieses
> Kapitels enthält den Seite-an-Seite-Vergleich.

**Auto DJ** ist der Hintergrund-Filler, der die Station auf
Sendung hält, während der Operator nicht geplant hat. Er
arbeitet in zwei komplementären Durchgängen, beide
vollautomatisch, sobald aktiviert:

1. **Pre-Pass** — wenn die nächste Stunde des Kalenders eine
   Lücke länger als 60 Sekunden enthält, erstellt er eine
   neue Sendung in der ersten solchen Lücke, benannt nach
   Ihren Standards, mit der Auto-DJ-Playlist autoloaded.
2. **Fill-Pass** (optional) — wenn eine kommende Sendung
   nach ihrem Build mehr als 5 s kurz vor ihrem Slot endet,
   ergänzt er den Schwanz mit der Auto-DJ-Playlist.

Das Ergebnis: Solange Auto DJ aktiviert ist und auf eine
gesunde Playlist zeigt, fällt Ihre Station nie in Stille.

---

## 1. Warum Auto DJ existiert

Vor 2026-05-21 war der Fallback für "gerade keine geplante
Sendung" eine konfigurierte Loop-Datei (standardmäßig
Stille). Das deckte "nie eine Sendung" ab, aber ein
Kalender mit 80 % Abdeckung und 20 % Lücken spielte trotzdem
Stille in den Lücken.

Die zwei Muster, denen der Operator wiederholt begegnete:

- Die Montagmorgen-Sendung endet um 10:00, aber die nächste
  Sendung beginnt um 14:00. Die vierstündige Lücke spielte
  Fallback-Stille auf dem öffentlichen Stream — schlechte
  Hörererfahrung.
- Die Autoplaylist einer 60-Minuten-Sendung füllte nur 55
  Minuten (Smart Blocks gingen die passenden Tracks aus);
  die letzten 5 Minuten waren Stille.

Auto DJ deckt beides mit derselben konfigurierten Playlist
ab.

---

## 2. Auto DJ aktivieren

Einstellungen → **Auto DJ**.

```
   ┌──────────────────────────────────────────────────────────────┐
   │  Auto DJ Einstellungen                                       │
   ├──────────────────────────────────────────────────────────────┤
   │  Wenn aktiviert, scannt Auto DJ den Kalender auf Lücken in   │
   │  der nächsten Stunde und erstellt automatisch eine Sendung   │
   │  in der ersten gefundenen, gefüllt mit der unten gewählten   │
   │  Playlist. Wenn "Jede Sendung automatisch auffüllen"         │
   │  aktiviert ist, wird auch jede unvollständige kommende       │
   │  Sendung mit derselben Playlist aufgefüllt.                  │
   ├──────────────────────────────────────────────────────────────┤
   │  Status                                                      │
   │  ☑  Aktiviert — Auto DJ erstellt und füllt Sendungen autom.  │
   ├──────────────────────────────────────────────────────────────┤
   │  Auto DJ Sendungs-Standards                                  │
   │                                                              │
   │   Standard-Playlist: [Playlist auswählen ▾]  ◀── Pflicht     │
   │   Sendungsname:      [Auto DJ              ]                 │
   │   URL:               [                     ]                 │
   │   Genre:             [                     ]                 │
   │   Beschreibung:      [                     ]                 │
   │   Hintergrundfarbe:  [222222   ]                             │
   │   Textfarbe:         [ffffff   ]                             │
   │                                                              │
   │  ☐  Jede unvollständige Sendung nach dem Autoplaylist-Build  │
   │     automatisch auffüllen                                    │
   │                                                              │
   │   Sendungs-Logo:    [Datei wählen ▾]  Hochladen              │
   ├──────────────────────────────────────────────────────────────┤
   │                                       [  Speichern  ]        │
   └──────────────────────────────────────────────────────────────┘
```

### Pflichtfelder

| Feld | Hinweise |
|---|---|
| **Aktiviert** | Hauptschalter. Wenn aus, läuft keiner der beiden Durchgänge. |
| **Standard-Playlist** | Die Playlist, die Auto DJ verwendet, um seine Sendungen zu füllen und (wenn Fill-Pass an ist) unvollständige Sendungen aufzufüllen. Erforderlich, wenn **Aktiviert** an ist. |

### Empfohlene Playlist-Form

Verwenden Sie eine Playlist, die genau **einen Smart Block**
enthält mit:

- Typ: **Dynamisch** (wertet bei jedem Zyklus neu aus).
- Kriterien: ein großzügiger Filter, der mehrere hundert
  Tracks matched. "Track-Typ = Musik" ist eine gute
  Baseline.
- **Begrenzen auf: Verbleibende Zeit in der Sendung**. Das
  ist kritisch — Auto-DJ-erstellte Sendungen haben variable
  Länge je nach der Lücke, die sie füllen (5 Minuten bis
  mehrere Stunden), und der Smart Block muss genau den Slot
  füllen, den er bekommt.
- Sortieren: **Zufällig**.

> **Operator-Tipp.** Die Einstellungsseite zeigt einen
> Tooltip auf dem Label **Standard-Playlist** mit genau
> dieser Empfehlung. Halten Sie den Mauszeiger über das
> "?"-Symbol, falls Sie die Empfehlung vergessen.

### Optionale Felder

| Feld | Was Auto DJ damit tut |
|---|---|
| **Sendungsname** | Verwendet als Name der auto-erstellten Sendung im Kalender. Standard `Auto DJ`. |
| **URL / Genre / Beschreibung** | Kopiert in die Metadaten jeder auto-erstellten Sendung. Sichtbar im öffentlichen Programmplan-Export. |
| **Hintergrund- / Textfarbe** | Verwendet, um die auto-erstellten Sendungen im Kalender zu färben — hilfreich, um sie auf einen Blick von operator-geplanten Sendungen zu unterscheiden. |
| **Sendungs-Logo** | Standard-Logo für die auto-erstellten Sendungen. Als base64-Blob in `cc_pref` gespeichert. Upload-Limit 2 MB; JPG / PNG / GIF / WebP. |
| **Jede Sendung automatisch auffüllen** | Wenn an, aktiviert den zweiten Durchgang (Fill-Pass). |

> **Wie es unter der Haube funktioniert.** Einstellungen
> leben in der Tabelle `cc_pref` als einfache
> Schlüssel/Wert-Zeilen (keine Schemaänderung):
> `auto_dj_enabled`, `auto_dj_show_name`,
> `auto_dj_playlist_id`, `auto_dj_fill_any_show`,
> `auto_dj_logo_path`, plus URL/Genre/Beschreibung/Bg/Text-
> Farbe. Der Logo-Upload verwendet ein separates
> Multipart-POST an `autoDjUploadLogoAction`. Der
> PHP-Service `Application_Service_AutoDjService` wird von
> `AutoPlaylistManager.buildAutoPlaylist()` mit 60-s-Kadenz
> aufgerufen. Siehe ARCHITECTURE §23.20.

---

## 3. Der Pre-Pass — Lückenfüllung

Alle 60 Sekunden scannt Auto DJ die nächste Stunde nach
Kalenderlücken. Eine **Lücke** ist jeder zusammenhängende
Bereich, in dem keine Sendung geplant ist.

Für die **erste** Lücke länger als 60 Sekunden, deren
Beginn innerhalb der nächsten Stunde liegt:

1. Erstellen Sie eine neue `cc_show`-Zeile mit den
   konfigurierten Standards (Name, Farben, URL usw.).
2. Fügen Sie eine `cc_show_days`-Zeile mit der
   operator-lokalen Zeitzone und gerundeten Zeiten ein
   (Start AUF die nächste Minute, Ende AB auf die vorherige
   Minute).
3. Fügen Sie eine `cc_show_instances`-Zeile für denselben
   Bereich ein.
4. Hängen Sie die konfigurierte Auto-DJ-Playlist als
   Autoloading an.

Die neue Sendung wird dann von **demselben** Poll-Zyklus
des Body-Loops aufgenommen und gebaut. Also einen
5-Minuten-Tick, nachdem der Operator eine Sendung löscht,
die eine einstündige Lücke hinterlässt, hat Auto DJ sie
bereits durch eine Auto-DJ-Sendung ersetzt und gefüllt.

### Warum nur eine Sendung pro Zyklus?

Der Pre-Pass erstellt **eine** Sendung pro 60-s-Zyklus,
selbst wenn mehrere Lücken existieren. Dies ist
beabsichtigt:

- Nachdem eine Sendung erstellt ist, bewegt sich die
  nächste Lücke. Der Zyklus wertet neu aus.
- Ein Operator, der den Kalender aktiv umordnet, sollte
  nicht zehn Auto-DJ-Sendungen schneller materialisieren
  sehen, als er reagieren kann.
- Eines-nach-dem-anderen passt zur natürlichen Kadenz
  menschlicher Planung.

Nach zehn Zyklen (10 Minuten) wurden bis zu zehn
Auto-DJ-Sendungen erstellt, wenn der Operator nichts getan
hat. Für einen typischen Kalender mit einer
mehrstündigen Lücke ist das das richtige Tempo.

### Sendungszeiten werden auf die Minute gerundet

Auto-DJ-erstellte Sendungen starten immer an einer
Minuten-Grenze (von der Lücken-Startzeit *auf* gerundet)
und enden an einer Minuten-Grenze (von der Lücken-Endzeit
*ab* gerundet). Dies hat zwei Gründe:

- Das Sendungs-Bearbeitungsformular des Operators zeigt
  Subminuten-Zeitstempel nicht sauber an, was zu einem
  "Cannot schedule overlapping shows"-Fehler führte, wenn
  der Operator eine Auto-DJ-Sendung mit einem 14:00:30-Start
  öffnete. RASTATIME 2026-05-21 rundet bei der Erstellung,
  um die Verwirrung zu vermeiden.
- Eine konsistente Minuten-Ausrichtung entspricht den
  Operator-Erwartungen für geplante Sendungen.

Der Trade-off: Wenn die Lücke 14:00:30 → 15:00:30 ist,
belegt die Auto-DJ-Sendung 14:01 → 15:00 — 59 Minuten statt
59:30. Eine halbe Minute verloren. Akzeptabel.

> **Operator-Tipp.** Wenn Sie präzise Lückenfüllung
> benötigen (z.B. ein straff geplantes Syndizierungs-Relay),
> verwenden Sie eine einmalige Sendung mit den exakten
> Zeiten, statt sich auf Auto DJ zu verlassen.

---

## 4. Der Fill-Pass — Auffüllen unvollständiger Sendungen

Optional, opt-in via **Jede unvollständige Sendung nach
dem Autoplaylist-Build automatisch auffüllen**.

Alle 60-s-Zyklen, nach dem Pre-Pass + den normalen
Autoplaylist-Body-Builds, läuft der Fill-Pass jede
kommende Sendung durch, deren Schwanz mehr als 5 Sekunden
kurz vor ihrem Slot endete. Für jede hängt er die
Auto-DJ-Playlist ans Ende, um den Slot aufzufüllen.

Häufige Gründe, warum eine Sendung kurz endet:

- Die Smart Blocks ihrer Autoplaylist sind die passenden
  Tracks ausgegangen.
- Die Autoplaylist hatte keinen "verbleibende Zeit"-Smart-
  Block, nur eine feste Anzahl von Items.
- Der Operator vergaß überhaupt, eine Autoplaylist
  anzuhängen.

**Nie vor der eigenen Befüllung der Sendung (seit 26.10.2026).**
Eine Sendung mit Autoloading-Playlist wird ausgelassen, bis ihre
Befüllung gelaufen ist, und eine Wiederholung („Repeat of show“),
bis sie ihre Kopie hat - solange die Kopie noch kommen kann (bis 5
Minuten vor Beginn).  Song-Request- und Traffic-Alert-Sendungen, die
schrittweise kurz vor dem Abspielen befüllt werden, werden nie
aufgefüllt.  Vorher konnte der Fill-Pass eine Sendung einen Moment
vor ihrem Autoloading erreichen und mit der Auto-DJ-Playlist füllen
(26.10.2026, „Vinyl Hour“: um 15:00:00 gefüllt, das Autoloading
fand sie um 15:01:30 voll vor).

### Warum 5 Sekunden und nicht ein strengerer Schwellenwert?

Die Outro-Reserve (siehe
[Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) §4)
lässt absichtlich bis zu 5 s Spielraum, damit der
Auto-Build nicht überbucht. Das Verschärfen des
Fill-Pass-Schwellenwerts auf z.B. 1 s würde ständig
Sendungen auffüllen, die bereits optimal gefüllt waren —
verschwenderisch und nervig.

### Der Fill-Pass lässt eine Sendung in Bearbeitung in Ruhe (seit 2026-11-07)

Während Sie im Kalender oder im Show Builder Titel in eine Sendung
ziehen, gehört diese Sendung Ihnen: Jede Planungsaktion sperrt jetzt
zuerst die Sendungsinstanz, und der Fill-Pass wartet nicht auf diese
Sperre.  Er überspringt die Sendung in diesem Zyklus, schreibt eine
Informationszeile ins Log („is being edited right now - left alone
until the next pass") und schaut eine Minute später wieder nach.
Sobald Ihre Bearbeitung gespeichert ist und der Sendung weiterhin mehr
als 5 Sekunden fehlen, füllt der Fill-Pass sie wie gewohnt auf.  Vor
dieser Änderung liefen beide gleichzeitig und konnten in der Datenbank
kollidieren (Deadlock) - wer verlor, war Zufall, sodass auch ein Drop
des Operators mit einer Fehlermeldung scheitern konnte.

### Der Fill-Pass modifiziert nie die Sendungsdefinition

Der Fill-Pass fügt nur **Schedule-Items** in die bestehende
Instanz ein. Er ändert weder den Namen, die Hosts, die
Autoplaylist-Anbringung noch ein anderes Definitionsfeld
der Sendung. Die Absicht des Operators für die Sendung
bleibt intakt; nur der leere Schwanz wird gefüllt.

---

## 5. Auto-DJ-erstellte Sendungen im Kalender

Auto-DJ-erstellte Sendungen sehen aus wie jede andere
Sendung, mit dem visuellen Hinweis der konfigurierten
Hintergrundfarbe (typischerweise dunkler als
operator-geplante Sendungen).

| Aktion | Auf Auto-DJ-Sendungen erlaubt? |
|---|---|
| **Ansehen** | Ja |
| **Sendung bearbeiten** | Ja — aber beachten Sie, dass die Bearbeitung auf der auto-erstellten Sendung erfolgt, nicht auf den Auto-DJ-Standards. Um die Standards zu ändern, verwenden Sie Einstellungen → Auto DJ. |
| **Tracks einplanen** | Ja — Items anhängen / ersetzen wie auf jeder Sendung. |
| **Sendung abbrechen** | Ja (nur aktuelle Sendung). |
| **Sendung löschen** | Ja. Nach Löschung erscheint die Lücke wieder, und Auto DJ kann sie im nächsten Zyklus erneut füllen. |

> **Operator-Tipp.** Wenn Sie **verhindern** möchten, dass
> Auto DJ eine Lücke erneut füllt (z.B. Sie möchten 30
> Minuten Stille für einen Gedenkmoment), erstellen Sie
> eine explizite leere einmalige Sendung ohne Autoloading
> Playlist über dieser Lücke. Auto DJ berührt nie
> bestehende Sendungen für den Pre-Pass, nur Lücken.

---

## 6. Auto DJ deaktivieren

Einstellungen → Auto DJ → **Aktiviert** abwählen →
**Speichern**.

Effekte:

- Pre-Pass hört auf, neue Sendungen zu erstellen. Bereits
  erstellte Auto-DJ-Sendungen bleiben im Kalender.
- Fill-Pass hört auf, unvollständige Sendungen aufzufüllen.

Um bereits erstellte Auto-DJ-Sendungen massenhaft zu
entfernen, verwenden Sie die Massenaktionen →
**Ausgewählte Sendungen löschen** auf dem Kalender.

---

## 7. Häufig gestellte Fragen

### "Auto DJ erstellt keine Sendungen."

Prüfen Sie in dieser Reihenfolge:

1. **Aktiviert** ist angekreuzt und **Speichern**
   geklickt.
2. **Standard-Playlist** ist auf eine nicht-leere Playlist
   gesetzt.
3. Das Nächste-Stunde-Fenster enthält tatsächlich eine
   Lücke > 60 s. Wenn die nächste Stunde vollständig
   gebucht ist, ist der Pre-Pass korrekt ein No-Op.
4. Der Dienst **RASTATIME-WORKER** läuft
   (`Get-Service RASTATIME-WORKER`).
5. Die Smart Blocks der konfigurierten Playlist geben
   mindestens einen passenden Track zurück. Eine leere
   Auswahl erzeugt einen leeren Build.

### "Auto DJ erstellte 17 winzige Sendungen über eine lange Lücke."

Dies war eine Regression in v4 (Abschnitt 23.20). Ab
RASTATIME 2026-05-21 behoben: der Pre-Pass fragt bis zu 200
kommende Instanzen ab und verlangt nur, dass der
Lücken*beginn* (nicht das Lücken*ende*) innerhalb des
Lookahead-Fensters liegt. Eine einzelne Lücke erstellt also
eine einzelne Sendung, selbst wenn die Lücke mehrere Stunden
lang ist. Wenn Sie das immer noch sehen, aktualisieren Sie.

### "Auto-DJ-Sendungen zeigen falsche Zeitzone im Bearbeitungs-Dialog."

Dies war eine Regression in v5 (Abschnitt 23.20). RASTATIME
speichert die lokale Zeit der Sendung + die lokale Zeitzone
des Operators in `cc_show_days.timezone`. Vor dem Fix war
die Zeitzone 'UTC', sodass der Bearbeitungs-Dialog UTC
anzeigte und der Operator 13:08 für eine Sendung sah, die
tatsächlich um 15:08 Ortszeit startete. Behoben am
2026-05-21.

### "Kann Auto DJ verschiedene Playlists für verschiedene Tageszeiten verwenden?"

Nicht direkt. Die Auto-DJ-Playlist ist eine einzelne
stationsweite Wahl. Die Umgehung:

1. Verwenden Sie die Auto-DJ-Playlist als *Daypart-Router*:
   sie enthält einen einzelnen Smart Block mit einem
   Kriterium wie *Track-Typ = Musik UND Tag enthält
   "morgen"*.
2. Taggen Sie Tracks nach Tageszeit
   (Operator-Konvention).
3. Verwenden Sie zu einer anderen Tageszeit ein anderes
   Kriterium, indem Sie den Smart-Block-Filter ändern
   (manuell, wöchentlich).

Zukünftige Arbeit könnte einen daypart-bewussten Auto DJ
hinzufügen; noch nicht implementiert.

### "Berücksichtigt Auto DJ den per-show Fill-Pass anders?"

Nein — der Fill-Pass ist stationsweit. Entweder erhält
jede unvollständige Sendung das Auffüllen, oder keine.
Per-show Opt-out wird nicht unterstützt (verwenden Sie eine
Autoloading Playlist mit derselben Playlist für denselben
Effekt; das umgeht den Fill-Pass für diese Sendung, weil
die Sendung nicht mehr unvollständig ist).

---

## 8. Empfohlenes Auto-DJ-Profil für neue Stationen

Wenn Sie Auto DJ zum ersten Mal einrichten, beginnen Sie
mit diesem konservativen Profil:

| Einstellung | Wert |
|---|---|
| **Aktiviert** | Aus (alles andere zuerst einrichten, dann aktivieren) |
| **Standard-Playlist** | Eine Playlist namens "Auto DJ", die einen Smart Block enthält: Typ Dynamisch, Kriterien "Track-Typ = Musik", Limit "Verbleibende Zeit in der Sendung", Sortieren Zufällig |
| **Sendungsname** | `Auto DJ` |
| **Hintergrundfarbe** | `222222` (dunkelgrau — visuell von Operator-Sendungen unterscheidbar) |
| **Textfarbe** | `ffffff` |
| **Jede Sendung automatisch auffüllen** | Aus (später aktivieren, sobald Sie der Playlist vertrauen) |

Dann aktivieren, den Kalender für einen ganzen Tag
beobachten und anpassen.

---

## Wohin als Nächstes

* [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) —
  das per-show-Gegenstück; beide laufen im selben
  60-s-Build-Zyklus.
* [Bibliothek](./LIBRARY.md) → Smart Blocks — nützlichstes
  Primitiv für die Auto-DJ-Playlist.
* [Kalender](./CALENDAR.md) — wo Auto-DJ-erstellte
  Sendungen erscheinen; Massenaktionen zum Entfernen.
