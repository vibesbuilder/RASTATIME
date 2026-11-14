# My Podcast

> **Wo Sie im Handbuch sind.** Lesen Sie zuerst [Library](./LIBRARY.md):
> Was Sie in My Podcast veröffentlichen, ist ein gewöhnlicher Track der
> Library.  Nicht zu verwechseln mit **Podcasts** im Hauptmenü (Feeds
> *anderer* Podcasts, die Sie abonnieren und herunterladen) oder mit
> der [Archivierung](./ARCHIVING.md) (Episoden auf cba.media).

**My Podcast** ist der eigene Podcast des Senders: ein RSS-Feed aus
Tracks Ihrer Library, den Hörer in jeder Podcast-App abonnieren.
Veröffentlichen nimmt einen Track in den Feed auf, Zurückziehen
(„Unpublish“) entfernt ihn.  Seit 2026-11-14 kann ein Track außerdem
den **letzten Tag tragen, an dem er veröffentlicht bleibt** - danach
zieht RASTATIME ihn selbst zurück.

Veröffentlichen dürfen Program Manager und Admins (siehe
[Benutzer und Rollen](./USERS_AND_ROLES.md)).

---

## 1. Einen Track veröffentlichen

1. Öffnen Sie unter **Tracks** das Kontextmenü des Tracks und wählen
   Sie **Publish...**.  Der Veröffentlichungs-Dialog öffnet sich in
   einem eigenen Tab.
2. Haken Sie unter **Publish to:** **My Podcast** an.
3. Optional: Tragen Sie bei **Published until:** den letzten Tag ein,
   an dem der Track im Podcast bleibt (JJJJ-MM-TT, oder wählen Sie ihn
   im Kalender, der sich öffnet).  Leer lassen heißt: ohne Ende.  Das
   früheste Datum ist heute.
4. Klicken Sie auf **Publish**.

Der Track erscheint nun im selben Dialog unter **Published on:**, mit
seinem Datum (oder *no end date*) daneben.

Titel, Urheber und Beschreibung im Feed kommen aus den Metadaten des
Tracks - **Edit Metadata...** im Dialog öffnet den Track-Editor.

---

## 2. Datum ändern oder zurückziehen

Öffnen Sie **Publish...** erneut für einen veröffentlichten Track:

- **Datum ändern:** Ändern Sie das Datum neben *My Podcast* und
  klicken Sie auf **Save date**.  Ein leeres Feld plus **Save date**
  entfernt das Ende - der Track bleibt dann veröffentlicht, bis Sie
  ihn zurückziehen.  Ein Datum in der Vergangenheit wird abgelehnt.
- **Zurückziehen:** Klicken Sie auf **Unpublish**.  Der Track
  verschwindet sofort aus dem Feed.

---

## 3. Automatisches Zurückziehen („Published until“)

Das Datum gilt **einschließlich**: Ein Track, der bis 31. Dezember
veröffentlicht ist, steht am 31. Dezember noch im Podcast und wird
**kurz nach Mitternacht** (Zeitzone des Senders) zurückgezogen,
spätestens etwa sieben Minuten nach 00:00.

Das Zurückziehen wirkt genau wie ein Klick auf **Unpublish**:

- die Episode verschwindet aus dem **Feed**;
- ihr **Download-Link** funktioniert nicht mehr - Podcast-Apps können
  die Datei nicht mehr abrufen;
- sie verschwindet aus der Episodenliste auf der Seite My Podcast.

Der Track selbst bleibt in der Library.  Um ihn zurückzuholen,
veröffentlichen Sie ihn erneut - er zählt dann als neue
Veröffentlichung und steht in Podcast-Apps oben.  Kopien, die Hörer
bereits heruntergeladen haben, bleiben auf deren Geräten; die kann
niemand zurückholen.

Podcast-Apps holen einen Feed nur alle paar Stunden ab; eine App kann
eine zurückgezogene Episode also bis zum nächsten Abruf noch zeigen -
der Download funktioniert in der Zwischenzeit nicht mehr.

Jedes automatische Zurückziehen steht im Legacy-Log
(`StationPodcastExpiryTask: unpublished episode ...`).

---

## 4. Die Seite My Podcast

**My Podcast** im Hauptmenü zeigt links die Einstellungen des Podcasts
und rechts seine Episoden.

- **General Fields / iTunes Fields** - Name, Beschreibung, Sprache,
  Autor, Kategorie usw., so wie Podcast-Apps sie anzeigen.  Klicken
  Sie nach Änderungen auf **Save**.
- **Privacy Settings** - **Public** (jeder mit der Feed-Adresse) oder
  **Private** (nur mit der Feed-Adresse, die den Freigabe-Schlüssel
  enthält).  **Feed URL** und **View Feed** zeigen die Adresse, die
  Sie weitergeben.
- **Episodenliste** - jeder veröffentlichte Track mit seinem Datum
  **Published until** (leer = ohne Ende).  Markieren Sie Episoden und
  klicken Sie auf **Unpublish**, um sie zu entfernen.

---

## Siehe auch

- [Library](./LIBRARY.md) - die Tracks, die Sie veröffentlichen.
- [Archivierung](./ARCHIVING.md) - Episoden stattdessen auf cba.media.
- [Benutzer und Rollen](./USERS_AND_ROLES.md) - wer veröffentlichen darf.
