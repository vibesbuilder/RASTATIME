# Benutzer und Rollen

> **Wo Sie sich im Handbuch befinden.** Dieses Kapitel ist
> die Berechtigungsreferenz für jede Funktion im Rest des
> Handbuchs. Jede "Sie können X nicht tun, weil Sie kein
> Admin sind"-Fußnote in einem anderen Kapitel löst sich
> gegen die Matrix unten auf.

RASTATIME hat fünf Benutzerrollen und ein einziges
Berechtigungssystem. Jede Aktion — eine Seite öffnen, einen
Track ziehen, eine Sendung speichern, einen Dienst neu
starten — wird serverseitig gegen die Rolle des Benutzers
geprüft.

Dieses Kapitel behandelt:

1. Die fünf Rollen + was jede tun kann.
2. Benutzer verwalten (erstellen, bearbeiten, Passwort
   zurücksetzen, deaktivieren).
3. Die vollständige Berechtigungsmatrix.
4. API-Schlüssel-Verwaltung.
5. Best-Practice-Rollenzuweisung für typische Stationen.

---

## 1. Die fünf Rollen

| Rolle | Symbol | Typischer Benutzer | Einzeilen-Zusammenfassung |
|---|---|---|---|
| **Gast** | G | Rezeptions-Display / Lobby | Nur Lese-Dashboard. |
| **DJ** | H | Jeder einzelne Host | Nur eigene Sendungen + eigene Dateien. |
| **Program Manager** | P | Programm-Koordinator | Alle Kalender + Bibliothek, keine Stationseinstellungen. |
| **Admin** | A | Stations-Technischer Admin | Alles außer dem Erstellen anderer Admins. |
| **Super Admin** | S | Stationsinhaber | Alles inklusive dem Erstellen von Admins. |

Ein Benutzer hat genau **eine** Rolle. Die Rolle wird auf
der Seite "Benutzer verwalten" gesetzt und ist das Einzige,
was steuert, was die Oberfläche den Benutzer tun lässt.

### Warum rollenbasiert und nicht capability-basiert?

Rollenbasiert ist das einfachste Modell, das 99 % der
Stationsbedürfnisse abdeckt. Capability-basiert (granulare
per-feature Toggles) ist flexibel, aber erzeugt exponentiell
mehr zu testende Konfigurationen. RASTATIME wählte Rollen,
weil:

- Operatoren verstehen "dieser Benutzer ist ein DJ".
- Die Rollengrenze bildet klar organisatorische Rollen ab.
- Berechtigungs-Audits ("wer kann X tun?") sind ein
  einziger Spaltenscan.

> **Wie es unter der Haube funktioniert.** Rollen leben in
> `cc_subjs.type` als einzelnes Zeichen (G / H / P / A / S).
> Berechtigungsprüfungen erfolgen in
> `application/configs/ACL.php` über Zend_Acl. Jede
> Controller-Aktion deklariert ihre erforderliche
> Ressource; ACL.php whitelisted pro-Rollen-Zugriff. Die
> Web-Oberfläche verbirgt Menü-Items, die der Benutzer
> nicht erreichen kann, aber das Backend prüft jede Aktion
> erneut, sodass ein Angreifer nicht durch URL-Crafting
> umgehen kann. Siehe ARCHITECTURE §11.

---

## 2. Pro-Rolle-Fähigkeiten

### Gast (G)

Die kleinste Rolle. Verwendet für:

- Read-only-Displays in öffentlichen Bereichen (Rezeption,
  Café-Bereich), die zeigen, was gerade auf Sendung ist.
- Hörer, die in der Lage sein sollten, den kommenden
  Sendeplan zu sehen, aber nicht zu interagieren.

Kann:

- Sich anmelden.
- Now-Playing + Kommt-als-Nächstes des Dashboards sehen.
- Den öffentlichen Kalender sehen (read-only).

Kann nicht:

- Auf die Bibliothek, Einstellungen oder ein
  administratives Menü zugreifen.
- Hörerzahlen sehen.
- Pro-Sendungs-Füllprozentsätze sehen.
- Live-Quelle-Controls verwenden.

### DJ (H)

Per-Host-Konto. Die Rolle, die die meisten Benutzer haben.

Kann:

- Alles, was Gast kann.
- Tracks hochladen (in eigenem Besitz).
- Smart Blocks und Playlists erstellen (in eigenem Besitz).
- Eigene Tracks / Blocks / Playlists in eigene Sendungen
  einplanen.
- Sendungen bearbeiten, in denen er Host ist.
- Eigene Aufnahmen sehen und herunterladen.

Kann nicht:

- Sendungen erstellen (Program Manager müssen die Sendung
  erstellen; der DJ füllt sie).
- Sendungen bearbeiten, in denen jemand anderes Host ist.
- Tracks / Blocks / Playlists anderer DJs sehen oder
  verwenden.
- Stationsweite Einstellungen ändern (Streams, Lokale
  Maschine, Auto DJ, Sendungs-Vorlagen, Benutzer).
- Dienste neu starten.

> **Die DJ-vs-Program-Manager-Trennung.** Viele Stationen
> vermischen die beiden Rollen. RASTATIME trennt sie
> bewusst: DJs sind Inhaltsersteller; Program Manager sind
> Sendeplan-Besitzer. Eine Station mit fünf DJs hat einen
> Program Manager (oder eine rotierende Rolle).

### Program Manager (P)

Der Sendeplan-Besitzer.

Kann:

- Alles, was DJ kann.
- *Jede* Sendung erstellen / bearbeiten / löschen,
  unabhängig vom Host.
- Tracks / Blocks / Playlists *jedes* DJs sehen und
  verwenden.
- Sendungs-Vorlagen verwenden (erstellen / anwenden /
  umbenennen / löschen).
- Auto DJ verwenden (konfigurieren + aktivieren /
  deaktivieren).
- Webstream-Bibliotheks-Einträge verwalten.
- Master DJ über den Dashboard-Toggle auf / von Sendung
  nehmen.

Kann nicht:

- Line-Ins verwalten (soundkarten-abhängig — nur Admin).
- Streams verwalten (Output-Bitrate / Icecast-
  Anmeldedaten — nur Admin).
- Benutzer verwalten.
- Einstellungen → Lokale Maschine, → Streams, → Benutzer
  zugreifen.
- Dienste neu starten.
- API-Schlüssel anderer Admins lesen.

### Admin (A)

Voller Stations-Ebenen-Zugriff außer Erstellen anderer
Admins.

Kann:

- Alles, was Program Manager kann.
- Line-Ins verwalten.
- Streams verwalten.
- Benutzer verwalten (DJs und Program Manager erstellen /
  bearbeiten / deaktivieren; kann keine anderen Admins
  erstellen / degradieren).
- Einstellungen → Allgemeine Einstellungen konfigurieren.
- Einstellungen → Lokale Maschine konfigurieren.
- Auto-DJ-Standards konfigurieren (Logo, Name, Farben,
  Playlist).
- Passwörter anderer Benutzer zurücksetzen.
- Die Systemstatus-Seite lesen.
- Dienste über das Systemstatus-Neustart-Widget neu
  starten.

Kann nicht:

- Einen Benutzer zum Admin befördern (nur Super Admin).
- Einen anderen Admin degradieren.
- Den API-Schlüssel des Super Admins sehen oder ändern.

### Super Admin (S)

Maximale Rolle. Reserviert für den Stationsinhaber /
technischen Admin.

Kann:

- Alles, was Admin kann.
- Neue Admins erstellen.
- Admins zurück zu niedrigeren Rollen degradieren.
- API-Schlüssel jedes Benutzers sehen.
- Die Datenbank / den API-Schlüsselspeicher direkt über
  Einstellungen → Tools → DB-Konsole modifizieren (falls
  zur Installationszeit aktiviert).

Per Design gibt es **genau einen** Super Admin pro
Station. Mehrere Super Admins werden technisch
unterstützt, aber operativ entmutigt — zu viele Menschen,
die anderen Admin-Zugriff geben können.

> **Operator-Tipp.** Setzen Sie den Super Admin auf den
> Stationsinhaber (die juristische Person, die die
> Sendelizenz besitzt). Der Super Admin ist die einzige
> Person, die einen abtrünnigen Admin aussperren kann.

---

## 3. Benutzer verwalten

Einstellungen → **Benutzer verwalten** (nur Admin / Super
Admin).

```
   ┌──────────────────────────────────────────────────────────────┐
   │  Benutzer verwalten                                  [+ Neu] │
   ├──────────────────────────────────────────────────────────────┤
   │  Benutzer    │ Rolle         │ Letzte Anmeldung   │ Status   │
   ├──────────────┼───────────────┼────────────────────┼──────────┤
   │  admin       │ Super Admin   │ 2026-05-21 14:32   │ Aktiv    │
   │  anna        │ Admin         │ 2026-05-20 08:15   │ Aktiv    │
   │  ben         │ Program Mgr   │ 2026-05-19 19:00   │ Aktiv    │
   │  carla       │ DJ            │ 2026-05-21 12:00   │ Aktiv    │
   │  david       │ DJ            │ (nie)              │ Inaktiv  │
   │  rezeption   │ Gast          │ 2026-05-21 13:00   │ Aktiv    │
   └──────────────┴───────────────┴────────────────────┴──────────┘
```

### Einen neuen Benutzer erstellen

Benutzer verwalten → **+ Neu**.

| Feld | Hinweise |
|---|---|
| **Benutzername** | Kleinbuchstaben, keine Leerzeichen, 3-32 Zeichen. Verwendet in URLs und als Host-Zuweisung. Kann nach dem Setzen nicht geändert werden. |
| **Vor- / Nachname** | Anzeigename. Wird im Benutzer-Dropdown und auf Sendungen gezeigt, in denen sie Host sind. |
| **E-Mail** | Verwendet für Passwort-Zurücksetzung (falls SMTP konfiguriert ist). |
| **Passwort** | Min. 8 Zeichen. Der Benutzer kann es bei der ersten Anmeldung ändern. |
| **Rolle** | Eine der fünf Rollen. Standardmäßig DJ. |
| **Mobiltelefon** | Optional. Einige Stationen verwenden es für Notfall-Textalarme. |
| **Skype** | Optional. Legacy-Feld; viele Stationen lassen es leer. |
| **Aktiv** | Standardmäßig an. Abwählen, um einen Benutzer zu erstellen, ohne ihm noch Zugriff zu gewähren. |

Klicken Sie **Erstellen**.

### Einen Benutzer bearbeiten

Zeile → **Bearbeiten**. Alle Felder außer Benutzername
sind bearbeitbar.

Um die Rolle eines Benutzers zu ändern:

- Eine Rolle senken (Admin → PM, PM → DJ) ist für Admin
  und höher erlaubt.
- Beförderung zum Admin ist **nur Super Admin**.
- Einen Super Admin degradieren: nur der Super Admin
  selbst kann das tun (d.h. Sie können zurücktreten, aber
  niemand sonst kann Sie degradieren). Wenn das
  Super-Admin-Konto verloren geht, ist die einzige
  Wiederherstellung direkter Datenbankzugriff — siehe
  [`docs/operator/CRASH_RECOVERY.md`](../../operator/CRASH_RECOVERY.md).

### Ein Passwort zurücksetzen

Zeile → **Passwort zurücksetzen**.

| Option | Effekt |
|---|---|
| **E-Mail senden** | Falls SMTP konfiguriert ist (Einstellungen → Allgemeine Einstellungen → E-Mail), einen einmaligen Link senden, der 24 Stunden gültig ist. |
| **Passwort setzen** | Ein temporäres Passwort setzen. Der Benutzer wird gezwungen, es bei seiner nächsten Anmeldung zu ändern. |

### Einen Benutzer deaktivieren

Zeile → **Deaktivieren**. Der Benutzer kann sich nicht mehr
anmelden, aber seine historische Aktivität (hochgeladene
Tracks, bearbeitete Sendungen) bleibt erhalten.

Zum Reaktivieren bearbeiten und **Aktiv** ankreuzen.

Um einen Benutzer dauerhaft zu löschen, **Löschen**. Sein
Inhalt (Tracks, Blocks, Playlists) wird dem konfigurierten
**Standard-Fallback-Besitzer** (typischerweise `admin`)
neu zugewiesen.

> **Operator-Tipp.** Bevorzugen Sie **Deaktivieren** über
> **Löschen**. Löschen kaskadiert in die
> Inhalts-Neuzuweisung, was verwirrend sein kann, wenn die
> Tracks des Benutzers stark referenziert wurden.
> Deaktivieren ist reversibel und bewahrt den Audit-Trail.

### Letzter-Login-Tracking

Jede Benutzerzeile zeigt den Zeitstempel der letzten
erfolgreichen Anmeldung. Nützlich für die Audit-Frage "wird
dieses Konto noch verwendet?" vor dem Deaktivieren.

---

## 4. API-Schlüssel

Jeder Benutzer kann einen API-Schlüssel für
skript-basierten Zugriff auf die REST-API generieren.

### Eigenen API-Schlüssel generieren

Benutzer-Dropdown (oben rechts) → **Mein Profil** →
Abschnitt **API-Schlüssel**.

| Aktion | Effekt |
|---|---|
| **Neuen Schlüssel generieren** | Erstellt einen Schlüssel. Vorheriger Schlüssel (falls vorhanden) wird widerrufen. |
| **Anzeigen** | Zeigt den Schlüssel einmal (zum Copy-Paste). |
| **Widerrufen** | Deaktiviert den Schlüssel, ohne einen neuen zu generieren. |

API-Schlüssel tragen dieselben Berechtigungen wie der
Benutzer. Der API-Schlüssel eines DJs kann nichts tun, was
der DJ-Benutzer nicht kann.

### API-Schlüssel eines anderen Benutzers generieren

Benutzer verwalten → Benutzer-Zeile → **API-Schlüssel** →
Generieren. Nur Admin / Super Admin.

Dies ist nützlich für Service-Konten: Erstellen Sie einen
`script`-Benutzer mit der DJ-Rolle + einem bekannten
API-Schlüssel, übergeben Sie den Schlüssel an das Skript,
und das Skript kann Tracks über die API ohne interaktive
Anmeldung hochladen.

> **Wie es unter der Haube funktioniert.** API-Schlüssel
> sind 32-Byte-Zufallsstrings, die in `cc_subjs.api_key`
> (gehasht) gespeichert sind. Authentifizierung erfolgt
> über den Header `Authorization: Api-Key <key>` gegen
> `/api/v2/`. Jede Anfrage authentifiziert unabhängig; es
> gibt keine Session. Siehe ARCHITECTURE §11.

> **Operator-Tipp.** Behandeln Sie API-Schlüssel wie
> Passwörter. Jeder mit dem Schlüssel kann als der
> Benutzer agieren. Rotieren Sie bei Verdacht auf
> Offenlegung. Vermeiden Sie das Hardcoden von Schlüsseln
> in Quelldateien, die in die Versionskontrolle committed
> werden — verwenden Sie Umgebungsvariablen oder einen
> Secret-Manager.

---

## 5. Die Berechtigungsmatrix

Die Single-Source-of-Truth-Tabelle für "kann Rolle X
Aktion Y tun".

| Aktion | G | H | P | A | S |
|---|:---:|:---:|:---:|:---:|:---:|
| **Dashboard** | | | | | |
| Now Playing sehen | ✓ | ✓ | ✓ | ✓ | ✓ |
| Hörerzahlen sehen | | ✓ | ✓ | ✓ | ✓ |
| Master DJ auf / von Sendung nehmen | | | ✓ | ✓ | ✓ |
| Aktuelle Sendung abbrechen | | ✓¹ | ✓ | ✓ | ✓ |
| Monitor anhören | | ✓ | ✓ | ✓ | ✓ |
| **Kalender** | | | | | |
| Kalender sehen | ✓ | ✓ | ✓ | ✓ | ✓ |
| Sendung erstellen | | | ✓ | ✓ | ✓ |
| Eigene Sendung bearbeiten | | ✓ | ✓ | ✓ | ✓ |
| Jede Sendung bearbeiten | | | ✓ | ✓ | ✓ |
| Eigene Sendung löschen | | ✓ | ✓ | ✓ | ✓ |
| Jede Sendung löschen | | | ✓ | ✓ | ✓ |
| Sendungs-Vorlage anwenden / speichern | | | ✓ | ✓ | ✓ |
| **Bibliothek** | | | | | |
| Eigene Dateien sehen | | ✓ | ✓ | ✓ | ✓ |
| Alle Dateien sehen | | | ✓ | ✓ | ✓ |
| Track hochladen | | ✓ | ✓ | ✓ | ✓ |
| Eigene Playlists, Blocks erstellen / bearbeiten | | ✓ | ✓ | ✓ | ✓ |
| Jede Playlist, jeden Block erstellen / bearbeiten | | | ✓ | ✓ | ✓ |
| Webstream erstellen / bearbeiten | | ✓² | ✓ | ✓ | ✓ |
| Line-In erstellen / bearbeiten | | | | ✓ | ✓ |
| Eigene Dateien löschen | | ✓ | ✓ | ✓ | ✓ |
| Jede Datei löschen | | | ✓ | ✓ | ✓ |
| **Streams** | | | | | |
| Stream-Status sehen | | ✓ | ✓ | ✓ | ✓ |
| Stream-Konfig bearbeiten | | | | ✓ | ✓ |
| **Lokale Maschine** | | | | | |
| Soundkarten-Konfig sehen | | | | ✓ | ✓ |
| Soundkarten-Konfig bearbeiten | | | | ✓ | ✓ |
| Lokalen Import-Ordner setzen | | | | ✓ | ✓ |
| **Auto DJ** | | | | | |
| Aktivieren / deaktivieren | | | ✓ | ✓ | ✓ |
| Standards bearbeiten (Name, Farben, Playlist) | | | | ✓ | ✓ |
| **Einstellungen** | | | | | |
| Allgemeine Einstellungen | | | | ✓ | ✓ |
| Lokalisierung | | | | ✓ | ✓ |
| Sendungs-Vorlagen-Seite | | | ✓ | ✓ | ✓ |
| Benutzer-Verwaltung | | | | ✓ | ✓ |
| Admin erstellen | | | | | ✓ |
| **System** | | | | | |
| Systemstatus sehen | | | | ✓ | ✓ |
| Dienst neu starten | | | | ✓ | ✓ |
| DB-Konsole zugreifen (falls aktiviert) | | | | | ✓ |
| **API** | | | | | |
| Eigenen API-Schlüssel generieren | | ✓ | ✓ | ✓ | ✓ |
| API-Schlüssel jedes Benutzers sehen / generieren | | | | ✓ | ✓³ |

Hinweise:

- ¹ — Nur seine derzeit auf Sendung befindliche Sendung.
- ² — Per DJ; kann Webstreams anderer DJs nicht bearbeiten.
- ³ — Einschließlich denen anderer Admins. Der Schlüssel
  eines degradierten Admins bleibt bestehen, es sei denn,
  er wird explizit widerrufen.

---

## 6. Empfohlene Rollenzuweisung für typische Stationen

### Solo-Operator-Station (1 Person)

- `admin` — Super Admin (der Operator).
- (Optional) `rezeption` — Gast (Lobby-Display, falls
  vorhanden).

### Kleine Community-Station (3-10 Beitragende)

- `admin` — Super Admin (der Stationsinhaber / technische
  Leiter).
- `pm1` — Program Manager (der Sendeplan-Koordinator).
- `anna`, `ben`, `carla`, … — DJ (einer pro Host).
- (Optional) `ingenieur` — Admin (falls ein separater
  technischer Admin existiert).
- (Optional) `rezeption` — Gast.

### Mittlere / kommerzielle Station (10-50 Beitragende)

- `owner` — Super Admin.
- `engineer1` — Admin (technische Operationen).
- `pm1`, `pm2` — Program Manager (einer pro
  Programmabteilung).
- DJ-Konten pro Host.
- `script` — DJ (Service-Konto für Automatisierungs-
  Skripte).
- `rezeption` — Gast.

Für alle Größen: **ein Super Admin pro Station** ist der
Sweet Spot. Zwei oder mehr führt zu
"Wer-hat-wen-ausgesperrt"-Verwirrung.

---

## 7. Häufig gestellte Fragen

### "Ich bin als Super Admin ausgesperrt. Wie stelle ich wieder her?"

Direkter Datenbankzugriff ist die einzige Wiederherstellung.
Siehe
[`docs/operator/CRASH_RECOVERY.md`](../../operator/CRASH_RECOVERY.md)
§5. Sie benötigen PostgreSQL-Anmeldedaten und ein Backup
der Datenbank.

### "Kann ein Benutzer zwei Rollen haben?"

Nein. Eine Rolle pro Benutzer. Wenn eine Person sowohl DJ-
als auch Program-Manager-Fähigkeiten braucht, geben Sie
ihr die Program-Manager-Rolle (sie umfasst alles, was DJ
kann).

### "Können zwei Benutzer ein Konto teilen?"

Technisch ja, aber stark entmutigt:

- Letzter-Login-Tracking wird bedeutungslos.
- Audit-Trails (wer hat was eingeplant?) werden anonym.
- API-Schlüssel können nicht pro Person widerrufen werden.

Bevorzugen Sie ein Konto pro reale Person.

### "Wie lange dauert eine Session?"

Standard 8 Stunden. Konfigurierbar über die
PHP-Session-Cookie-Lebensdauer in `php.ini`. Nach Ablauf
wird der Benutzer zur Anmeldeseite zurückgeworfen.

### "Kann ich mich von zwei Browsern gleichzeitig anmelden?"

Ja. Sessions sind per Cookie. Dasselbe Benutzerkonto kann
gleichzeitig von einem Desktop- und einem Mobil-Browser
angemeldet sein.

### "Unterstützt die API OAuth / SSO?"

Derzeit nicht. Authentifizierung erfolgt per API-Schlüssel
(per Benutzer) oder per Session-Cookie (interaktive
Oberfläche). SSO-Integration würde einen separaten
Authn-Proxy vor Apache erfordern; siehe
[`docs/operator/UPGRADE.md`](../../operator/UPGRADE.md)-
Backlog.

### "Kann ein DJ die Aufnahmen eines anderen DJs sehen?"

Nein. Aufnahmen erben den Besitz der Sendung; nur der
Host der Sendung (und Program Manager / Admins / Super
Admins) können sie herunterladen.

---

## Wohin als Nächstes

* [Einstellungen](./SETTINGS.md) — Tour durch jede
  Einstellungs-Unterseite.
* [Dashboard](./DASHBOARD.md) — die am meisten genutzte
  Seite des Operators, durch Rolle gegated.
* [`docs/operator/CRASH_RECOVERY.md`](../../operator/CRASH_RECOVERY.md)
  — Super-Admin-Aussperrungs-Wiederherstellung.
