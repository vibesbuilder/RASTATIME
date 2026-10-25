# Benutzer und Rollen

> **Wo Sie sich im Handbuch befinden.** Dieses Kapitel ist die
> Berechtigungsreferenz für das übrige Handbuch: Wenn ein anderes
> Kapitel „nur Program Manager und Admins“ sagt, zeigt die Matrix in §2
> das vollständige Bild.  Es beschreibt den Stand nach dem Rollen-Audit
> vom 25.10.2026.

RASTATIME kennt fünf Rollen.  Jedes Konto hat genau eine davon, und der
Server prüft sie bei jeder Anfrage - ein ausgeblendeter Knopf ist nur
Komfort, die Aktion lehnt der Server ohnehin ab.  Dieses Kapitel
behandelt:

1. Die fünf Rollen.
2. Die Berechtigungsmatrix.
3. Benutzer verwalten (Einstellungen → Benutzer).
4. Ihr eigenes Profil (Mein Profil).
5. Logins für Live-Einwahlen.
6. API-Zugriff.
7. Sitzungen und Schutz vor Missbrauch.
8. Login-Schutz.
9. Typische Rollenverteilung und häufige Fragen.

---

## 1. Die fünf Rollen

| Rolle | Typischer Benutzer | In einem Satz |
|---|---|---|
| **Gast** | Empfangsbildschirm, Besucher | Sieht Dashboard und Kalender, ändert nichts. |
| **DJ** | Moderator | Arbeitet mit Tracks: Upload, eigene Playlisten und Smart Blocks, befüllt die eigenen Sendungen. |
| **Program Manager** | Programmkoordination | Führt das Programm: alle Sendungen, alle Inhalte, Webstreams, Line-Ins, Podcasts, Auto DJ, Show-Vorlagen, Widgets. |
| **Admin** | Stationstechnik | Alles, dazu die Stationseinstellungen und die Benutzerkonten. |
| **Super Admin** | Aus Airtime übernommen; meist nicht vorhanden | Dieselben Rechte wie ein Admin; kann nicht gelöscht werden. |

Jede Rolle umfasst alles, was die Rolle darüber in der Tabelle darf.

**Der Super Admin** ist eine aus Airtime übernommene Rolle.  Eine
RASTATIME-Installation legt ihr Hauptkonto `admin` als **Admin** an, und
kein Konto lässt sich in der Oberfläche zum Super Admin machen (der
Benutzer-Dialog bietet Gast, DJ, Program Manager und Admin) - einen Super
Admin gibt es nur, wenn eine alte Airtime-Datenbank oder eine externe
Anmeldung (LDAP / FreeIPA) ihn mitbringt.  Wo es ihn gibt, hat er genau
die Rechte eines Admins, kann nicht gelöscht werden, und seine Angaben
sind unter Einstellungen → Benutzer nicht bearbeitbar (er ändert sie
selbst unter Mein Profil).  Admins können weitere Admins anlegen.

> **Unter der Haube.** Die Rolle ist der eine Buchstabe in
> `cc_subjs.type` (G, H, P, A, S).  Die groben Regeln stehen in
> `application/configs/ACL.php`; die feineren (Besitzer einer Datei,
> Host einer Sendung, Program Manager oder höher) prüfen die Controller.
> Das Audit und seine Befunde: `docs/operator/ROLE_AUDIT_2026-10.md`.

---

## 2. Die Berechtigungsmatrix

✓ = erlaubt, – = nicht erlaubt.  „Eigene“ heißt: Der Benutzer ist
Besitzer des Objekts (hat es hochgeladen oder angelegt); „als Host“
heißt: Der Benutzer ist Host der Sendung.  Die Spalte Super Admin
gleicht der Spalte Admin und ist weggelassen.

| Bereich | Gast | DJ | Program Manager | Admin |
|---|:---:|:---:|:---:|:---:|
| **Konto** | | | | |
| Eigenes Profil bearbeiten (Name, E-Mail, Passwort, Sprache, Zeitzone) | ✓ | ✓ | ✓ | ✓ |
| Andere Benutzer verwalten (Einstellungen → Benutzer) | – | – | – | ✓ |
| **Dashboard und Live-Quellen** | | | | |
| Now Playing und die geplanten Sendungen sehen | ✓ | ✓ | ✓ | ✓ |
| Auto-DJ-Status im Kopfbereich sehen | ✓ | ✓ | ✓ | ✓ |
| Live-Quelle (Master / Show) schalten oder trennen | – | während einer Sendung als Host | ✓ | ✓ |
| Laufende Sendung abbrechen | – | – | ✓ | ✓ |
| **Kalender** | | | | |
| Kalender ansehen | ✓ | ✓ | ✓ | ✓ |
| Sendungen anlegen, bearbeiten, verschieben, verlängern, löschen, absagen | – | – | ✓ | ✓ |
| Sendungsinhalt leeren, Teaser, Show-Vorlagen im Sendungsdialog | – | – | ✓ | ✓ |
| Inhalte in eine Sendung einplanen | – | als Host | ✓ | ✓ |
| **Bibliothek** | | | | |
| Bibliothek ansehen (Tracks, Playlisten, Smart Blocks, Podcast-Liste) | – | ✓ | ✓ | ✓ |
| Tracks hochladen | – | ✓ | ✓ | ✓ |
| Metadaten, Cue-Punkte bearbeiten, Tracks löschen | – | eigene | ✓ | ✓ |
| Besitzer eines Tracks ändern | – | – | – | ✓ |
| Playlisten und Smart Blocks anlegen | – | ✓ | ✓ | ✓ |
| Playlisten und Smart Blocks bearbeiten, mischen, löschen | – | eigene | ✓ | ✓ |
| Webstreams und Line-Ins sehen, verwenden, bearbeiten | – | – | ✓ | ✓ |
| Podcasts abonnieren, bearbeiten, löschen; Episoden | – | – | ✓ | ✓ |
| Im Stations-Podcast veröffentlichen (Mein Podcast) | – | – | ✓ | ✓ |
| **Statistiken** | | | | |
| Hörerstatistiken | – | ✓ | ✓ | ✓ |
| Sendeprotokoll ansehen | – | als Host | ✓ | ✓ |
| Sendeprotokoll: Einträge anlegen, bearbeiten, löschen | – | als Host | ✓ | ✓ |
| Verlaufsvorlagen | – | – | – | ✓ |
| **Widgets** | | | | |
| Widgets-Seiten (Embed-Codes, Widget-Einstellungen) | – | – | ✓ | ✓ |
| **Einstellungen** | | | | |
| Auto DJ | – | – | ✓ | ✓ |
| Seite Show Templates | – | – | ✓ | ✓ |
| Standardsprache der Station (Dialog beim ersten Start) | – | – | ✓ | ✓ |
| Allgemein, Benutzer, Track-Typen, Streams, Lokale Maschine, Import / Export, Backup, Status | – | – | – | ✓ |

Was die Rollen unterschiedlich sehen:

- **Gäste** bekommen Dashboard und Kalender.  Die Bibliothek zeigt
  „Sie haben keine Berechtigung, die Bibliothek anzusehen.“; das Menü
  **Neu**, **Upload** und das Menü **Widgets** werden nicht angeboten.
- **DJs** sehen alle Tracks, Playlisten und Smart Blocks der Station,
  ändern aber nur ihre eigenen.  Sie planen in die Sendungen ein, deren
  Host sie sind - jeden Track, jede Playlist und jeden Smart Block, auch
  fremde.  Webstreams und Line-Ins sind für sie ausgeblendet
  (Bibliotheks-Reiter, Menü **Neu**); ein DJ kann sie nicht in Playlisten
  oder Sendungen einfügen.  Im Sendeprotokoll bekommt ein DJ die *Show
  Summary* seiner eigenen Sendungen und kann dort Einträge anlegen,
  bearbeiten und löschen.  Die Podcast-Liste ist für DJs nur lesbar,
  das Menü **Widgets** wird ihnen nicht angeboten.
- **Program Manager** führen das Programm, nutzen die
  **Widgets**-Seiten und öffnen drei Einstellungsseiten: **Auto DJ**,
  **Show Templates** und Mein Profil.  Show-Vorlagen werden im
  Sendungsdialog gespeichert und angewendet und unter Einstellungen →
  Show Templates umbenannt oder gelöscht.
- **Admins** verwalten zusätzlich die Station: Einstellungen, Streams,
  Soundkarte, Benutzer, Track-Typen, Backup, Import / Export,
  Systemstatus.

Der Dialog für Sprache und Zeitzone beim ersten Start setzt für jeden
die **eigene** Sprache und Zeitzone; die stationsweite Standardsprache
ändert sich nur, wenn ein Program Manager oder Admin ihn bestätigt.

---

## 3. Benutzer verwalten

Einstellungen → **Benutzer** (Admins).

### Benutzer anlegen und bearbeiten

**Neu** öffnet den Benutzer-Dialog; ein Klick auf eine Zeile öffnet
denselben Dialog für diesen Benutzer.

| Feld | Hinweise |
|---|---|
| **Benutzername** | Der Login-Name. |
| **Passwort** / **Passwort bestätigen** | Für einen neuen Benutzer Pflicht.  Beim Bearbeiten den Platzhalter stehen lassen, um das Passwort zu behalten. |
| **Vorname**, **Nachname** | Erscheinen in den Benutzerlisten und als Sendungs-Host. |
| **E-Mail** | Kontaktadresse. |
| **Mobiltelefon**, **Skype**, **Jabber** | Freiwillige Kontaktfelder. |
| **Benutzertyp** | Gast, DJ, Program Manager oder Admin. |

Zum Super Admin lässt sich hier niemand machen.  Hat die Station einen
Super Admin, öffnet sich seine Zeile ohne bearbeitbare Angaben und zeigt
„Der Super Admin ändert seine Angaben selbst unter Mein Profil.“.

### Benutzer löschen

Das Löschen-Symbol in der Benutzerliste entfernt das Konto.  Tracks, die
dem Benutzer gehörten, werden dem ersten Administrator **übergeben**
(dem Super Admin bzw. dem ersten Admin, falls es keinen gibt) - sie
bleiben in der Bibliothek.  Das eigene Konto lässt sich nicht löschen,
der Super Admin ebenfalls nicht.

Einen Zustand „deaktiviert“ gibt es nicht: Um jemandem den Zugang zu
nehmen, löschen Sie das Konto oder setzen ein neues Passwort; soll nur
Lesezugriff bleiben, ändern Sie den Typ auf Gast.

### Benutzer in Import / Export

Einstellungen → Import / Export führt die Benutzer als `users.csv` -
ohne Passwörter; beim Import wird ein Passwort nur für neue Konten
gesetzt.  Siehe [Import / Export](./IMPORT_EXPORT.md).

---

## 4. Ihr eigenes Profil

Einstellungen → **Mein Profil** - für jede Rolle, auch für Gäste.

Sie ändern Vor- und Nachname, E-Mail, Passwort, die Kontaktfelder, Ihre
**Oberflächensprache** und Ihre **Zeitzone**.  Der Benutzername steht
fest.  Die Seite speichert immer das Konto, mit dem Sie angemeldet
sind; andere Konten bearbeitet ein Admin unter Einstellungen → Benutzer.

---

## 5. Logins für Live-Einwahlen

Ein DJ, der live sendet (BUTT, Mixxx, …), verbindet sich mit dem
Live-Eingang der Station und meldet sich mit einem der folgenden Logins
an:

| Login | Gilt, wenn |
|---|---|
| Eigener RASTATIME-Benutzername und eigenes Passwort des DJ | Der DJ ist Host der laufenden Sendung, und die Sendung nutzt die *RASTATIME Authentication* (Sendungsdialog → *Live Stream Input*). |
| Eigenes Login der Sendung (*Benutzerdefiniertes Login* im selben Abschnitt) | Diese Sendung läuft gerade. |
| Login der Master-Quelle (Einstellungen → Streams) | Immer; übersteuert die laufende Sendung. |

Das benutzerdefinierte Live-Passwort einer Sendung zeigt der
Sendungsdialog nur Program Managern und Admins.  Ports und Mount-Namen
stehen im Kapitel [Streams](./STREAMS.md).

---

## 6. API-Zugriff

Es gibt **keine persönlichen API-Schlüssel**.

- **Dienste** (Playout, Analyzer, Skripte auf dem Stationsrechner)
  verwenden den API-Schlüssel der Station aus `config/libretime.conf`
  (`Authorization: Api-Key …`).  Behandeln Sie ihn wie ein Passwort.
- **Personen** können die REST-API v2 (`/api/v2/`) mit ihrem eigenen
  Benutzernamen und Passwort nutzen; sie erhalten die Rechte ihrer
  Rolle.
- Einige interne Endpunkte (Line-In-Geräte, Soundkarte,
  Preflight-Warnungen, Stream-Status, die DJ-Login-Prüfung) antworten
  nur dem Stationsrechner selbst oder einem Aufrufer mit API-Schlüssel.

---

## 7. Sitzungen und Schutz vor Missbrauch

- **Sitzung.** Eine Anmeldung gilt, bis der Browser geschlossen wird
  oder die Sitzung eine Weile keine Anfrage gesehen hat (PHP
  `session.gc_maxlifetime`, auf dem Studiorechner 24 Minuten).  Ein
  offener RASTATIME-Tab hält seine Sitzung mit seinen
  Hintergrund-Aktualisierungen am Leben.  Gleichzeitige Anmeldungen aus
  mehreren Browsern sind möglich.
- **Cookie.** Das Sitzungs-Cookie ist `Secure`, `HttpOnly` und
  `SameSite=Lax`: Andere Webseiten können Ihre Anmeldung nicht für
  Anfragen im Hintergrund nutzen, und Skripte auf der Seite können es
  nicht lesen.
- **Anfrage-Token.** Jede Änderung über die Oberfläche trägt ein an Ihre
  Sitzung gebundenes Token.  Der Server vergleicht es; eine Anfrage ohne
  Token wird protokolliert (`CSRF monitor` in `logs/legacy.log`) und,
  sobald die Prüfung scharf geschaltet ist, abgelehnt.  Ein Tab, der
  länger als eine Woche offen war, braucht vor dem Speichern eventuell
  ein Neuladen (F5).

---

## 8. Login-Schutz (seit 06.10.2026)

Die Login-Seite bremst wiederholte Fehlversuche - notwendig, weil die
Weboberfläche aus dem Internet erreichbar ist.

| Bereich | Regel | Wirkung |
|---|---|---|
| Je Absenderadresse | 10 fehlgeschlagene Logins in 15 Minuten | die Adresse wartet 15 Minuten; jeder Versuch in dieser Zeit wird mit „Too many failed login attempts. Please try again in N minute(s).“ (HTTP 429) beantwortet, kein Passwort wird geprüft |
| Je Benutzername | 20 fehlgeschlagene Logins in 60 Minuten | der Name wartet 5 Minuten - bewusst kurz, damit niemand, der den Namen eines Administrators von vielen Adressen aus bestürmt, den Administrator dauerhaft aussperren kann |
| DJ-Einwahl (Harbor) | 5 abgelehnte Logins von einer Adresse in 10 Minuten | die Adresse wird 15 Minuten lang abgewiesen, ohne die Webanwendung zu fragen |

Ein erfolgreicher Login setzt die Zähler seiner Adresse und seines
Namens zurück.  Die Schwellen stehen in `constants.php`
(`RASTATIME_LOGIN_*`) und im Playout (`RejectThrottle`); gesperrte
Versuche werden mit der Adresse protokolliert (`logs/legacy.log`,
`logs/playout-stdout.log`).

**Sperren sehen und aufheben.**  Einstellungen → Status → *Blocked
addresses* listet jede Ebene (Web-Login je Adresse und je Benutzer,
DJ-Einwahl, Firewall-Wächter) mit der Zahl der Fehlversuche und den
verbleibenden Minuten; der Knopf **Unblock** löscht den Eintrag auf allen
Ebenen - für den DJ, der anruft, weil im Sendeprogramm das falsche
Passwort gespeichert war.  Dieselbe Liste gibt es in PowerShell:
`infra\scripts\rt-blocks.ps1` (`-Unblock <Adresse>` oder
`-Unblock user:<Login>`).  Ein DJ, der sich **vor** Sendungsbeginn
einwählt, wird abgewiesen, aber nie gezählt: Nur ein falsches Passwort
zählt.  Hartnäckige Internet-Scanner sperrt ein Wächter-Task für
24 Stunden in der Windows-Firewall (alle 5 Minuten; 50 abgewiesene
Anfragen in 60 Minuten, 3 typische Scanner-Pfade oder 5 falsche
DJ-Passwörter); sie erscheinen in derselben Liste.  Eine Antwort „nicht
angemeldet“ (401) zählt nie: Sie bekommt ein Browser-Tab mit
abgelaufener Sitzung für seine Hintergrundabfragen, und seit 07.10.2026
hört ein solcher Tab beim ersten Mal auf abzufragen.

**Erlaubte Adressen (seit 08.10.2026).**  Neben **Unblock** hat jede
gesperrte Adresse **Allow**: Sie wird auf jeder Ebene entsperrt und in
die Liste *Allowed addresses* darunter aufgenommen, in der Sie auch von
Hand eine Adresse oder ein Netz in CIDR-Schreibweise (`203.0.113.0/24`)
eintragen und Einträge entfernen können.  Eine erlaubte Adresse wird nie
vom Web-Login gebremst, nie von der DJ-Einwahl gedrosselt und nie vom
Firewall-Wächter gesperrt; Adressen des Studionetzes sind ohnehin
ausgenommen.  Halten Sie die Liste kurz - sie schaltet für diese Adresse
jede Bremse ab - und nehmen Sie für einen Heimanschluss, dessen Adresse
mit dem Anbieter wechselt, besser ein Netz.  Die Liste liegt in der
Datenbank und wird für Playout und Wächter nach `config\allowlist.txt`
gespiegelt.

> **Wenn Sie selbst ausgesperrt sind:** Warten Sie die angezeigten
> Minuten, oder bitten Sie eine Kollegin oder einen Kollegen an einer
> anderen Adresse.  Im Notfall stehen die Zähler in den Tabellen
> `cc_login_attempts` (je Adresse) und `cc_subjs.login_attempts` (je
> Benutzer).

---

## 9. Typische Rollenverteilung und häufige Fragen

### Typische Verteilung

| Station | Konten |
|---|---|
| Eine Person | das Konto `admin` (Admin); bei Bedarf ein Gast für einen Bildschirm im Foyer |
| Freies Radio | `admin` und ein persönliches Admin-Konto für die technische Leitung, ein Program Manager je Programmbereich, ein DJ-Konto je Moderator, bei Bedarf ein Gast |
| Größere Station | zusätzlich ein oder zwei Admins für den technischen Betrieb |

Ein Konto je echter Person: Geteilte Konten machen unkenntlich, wer was
geändert hat.

### „Ein DJ findet keinen Webstream und keinen Line-In.“

So gewollt: DJs arbeiten nur mit Tracks.  Ein Program Manager fügt den
Webstream oder Line-In in die Sendung oder in eine Playlist ein.

### „Ein DJ kann Zeit oder Beschreibung seiner Sendung nicht ändern.“

Sendungen legen Program Manager und Admins an und bearbeiten sie.  DJs
befüllen die Sendungen, deren Host sie sind, und können ihre Live-Quelle
ein- und ausschalten, solange ihre Sendung läuft.

### „Jemand braucht die Rechte von DJ und Program Manager.“

Geben Sie ihm die Rolle Program Manager - sie umfasst alles, was ein DJ
darf.

### „Kann ein Benutzer zwei Rollen haben?“

Nein, genau eine je Konto.

### „Das Passwort eines Admins ist verloren.“

Ein anderer Admin setzt unter Einstellungen → Benutzer ein neues - ein
Grund, zwei Admin-Konten zu führen.  Kann sich kein Admin mehr anmelden,
muss das Passwort in der Datenbank zurückgesetzt werden (Tabelle
`cc_subjs`, Spalte `pass`, MD5 des neuen Passworts) - siehe
[`docs/operator/CRASH_RECOVERY.md`](../../operator/CRASH_RECOVERY.md).
Ein Super Admin, wo es ihn gibt, ändert sein Passwort nur selbst (Mein
Profil).

---

## Wie es weitergeht

* [Einstellungen](./SETTINGS.md) - jede Einstellungsseite.
* [Dashboard](./DASHBOARD.md) - Live-Quellen und die laufende Sendung.
* [Import / Export](./IMPORT_EXPORT.md) - Benutzer als `users.csv`.
* [Streams](./STREAMS.md) - Ports für Live-Einwahlen und das Master-Login.
