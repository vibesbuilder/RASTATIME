# Import / Export

> **Où vous êtes dans le manuel.** Paramètres → **Import / Export** fait
> entrer et sortir les objets du calendrier sous forme de fichiers :
> émissions, playlists, smart blocks, webstreams et abonnements
> podcast. Lisez d'abord [Calendrier](./CALENDAR.md) et
> [Modèles d'émission](./SHOW_TEMPLATES.md) si la boîte de dialogue
> « Nouvelle émission » vous est nouvelle — l'import crée les émissions
> exactement comme cette boîte de dialogue.
>
> **Ce que cette fonction remplace.** Construire toute une grille de
> programmes par la boîte de dialogue « Nouvelle émission », une
> émission à la fois, et la ressaisir quand la station passe sur un
> nouveau RASTATIME.

La page a deux moitiés. **Export** écrit les objets actuels en CSV
(JSON pour les smart blocks). **Import** reprend ces fichiers — une
archive ZIP avec tout, ou un seul fichier d'un type — et affiche
toujours d'abord un **aperçu** : chaque ligne est vérifiée, vous cochez
les lignes voulues, et seules celles-ci sont écrites. Une ligne dont
l'horaire chevauche une émission existante n'est jamais importée.

Seuls les administrateurs voient la page.

---

## 1. Export

1. Cochez les types voulus. Le nombre entre parenthèses est le nombre
   de lignes de l'export ; le nom de fichier est celui que l'import
   attend en retour.
2. Cliquez **Exporter les types sélectionnés**.
   * Un seul type donne un fichier (`shows.csv`, `playlists.csv`,
     `webstreams.csv`, `podcasts.csv` ou `blocks.json`).
   * Plusieurs types donnent un ZIP avec tous les fichiers, un dossier
     `logos/` avec les logos d'émission et un `README.txt` qui explique
     chaque colonne.
3. **Télécharger l'archive modèle** donne le même ZIP avec les en-têtes
   de colonnes, une ligne d'exemple par type et le README — le moyen le
   plus rapide de démarrer un tableur de zéro.

L'export des émissions contient les émissions qui ont encore des
diffusions à venir. Chaque ligne commence à la **prochaine** diffusion
de l'émission, de sorte qu'un fichier exporté peut être réimporté sans
toucher au passé.

Les fichiers CSV sont en UTF-8 avec `;` comme séparateur et s'ouvrent
proprement dans Excel ou LibreOffice ; à l'import, `,` et la tabulation
sont aussi acceptés. Les colonnes interrupteurs prennent `yes`/`no`.

## 2. Import

1. Choisissez le fichier : l'archive ZIP ou un seul fichier CSV/JSON.
   Laissez **Type** sur *détecter d'après le fichier* sauf si votre
   fichier porte un nom inhabituel.
2. **Noms existants** : *ignorer* (par défaut) laisse intact un objet
   dont le nom existe déjà ; *remplacer* écrase playlists, smart
   blocks, webstreams et les options d'un abonnement podcast. Les
   émissions ne sont jamais remplacées — une émission qui chevaucherait
   échoue simplement.
3. Cliquez **Aperçu**. Les lignes apparaissent aussitôt puis sont
   vérifiées par groupes de dix - la ligne d'état compte « Vérification
   40 sur 373 » ; une grande archive (des centaines d'émissions) prend
   quelques minutes, la page reste utilisable et le bouton d'import se
   débloque à la fin de la vérification. Le tableau liste chaque ligne
   avec son statut :
   * **prêt** — valide, sera créée à l'import ;
   * **ignoré** — existe déjà (avec *ignorer*), ou non sélectionnée ;
   * **erreur** — la remarque dit pourquoi (playlist inconnue,
     chevauchement, mauvaise date …). Corrigez le fichier et renvoyez-le,
     ou importez les autres lignes.
4. Décochez ce que vous ne voulez pas et cliquez **Importer les lignes
   sélectionnées**. L'import procède lui aussi par groupes de dix
   (« Import 30 sur 102 »). Les lignes sont créées dans l'ordre des
   dépendances — webstreams, smart blocks, playlists, podcasts,
   émissions — si bien qu'une playlist peut référencer un bloc de la
   même archive, et une émission une playlist de la même archive.
5. Le tableau de résultat montre ce qui a été créé, ignoré ou a
   échoué. Le calendrier et la diffusion reprennent les nouvelles
   émissions à leur prochain rafraîchissement (environ deux minutes).

Chaque ligne est vérifiée une seconde fois juste avant l'écriture : une
émission devenue chevauchante pendant que vous regardiez l'aperçu est
toujours refusée.

## 3. Les fichiers

### shows.csv

| Colonne | Signification |
|---|---|
| `name`, `url`, `genre`, `description` | comme dans la boîte de dialogue ; seul `name` est obligatoire |
| `start_date`, `start_time`, `end_date`, `end_time` | première diffusion ; `end_date` peut rester vide (même jour, ou lendemain quand la fin précède le début) |
| `timezone` | nom IANA tel que `Europe/Berlin` ; vide = fuseau de la station |
| `allow_delayed_start` | yes/no, voir [Démarrage différé](./DELAYED_START.md) |
| `repeats`, `repeat_type` | `none`, `weekly`, `biweekly`, `every_3_weeks`, `every_4_weeks`, `monthly_date`, `monthly_weekday` |
| `days` | pour les types hebdomadaires : `Mon,Tue,Wed,Thu,Fri,Sat,Sun` (les abréviations allemandes fonctionnent aussi) ; vide = jour de semaine de `start_date` |
| `months` | pour les types mensuels (depuis le 2026-10-15) : `Jan,Feb,...,Dec` ou `1..12` (les abréviations allemandes fonctionnent aussi) ; vide = chaque mois |
| `repeat_end_date`, `no_end` | date de la dernière diffusion, ou `no_end = yes` |
| `linked`, `record` | yes/no |
| `content`, `content_repeat` | le nom d'une playlist utilisée comme **playlist de chargement automatique** de l'émission, et si elle se répète jusqu'à remplir l'émission — voir [Playlists de chargement automatique](./AUTOLOADING_PLAYLISTS.md). Une playlist peut contenir des pistes, des smart blocks, des webstreams et des entrées line-in : chaque occurrence de l'émission est ainsi remplie automatiquement. |
| `repeat_of` | nom d'une émission existante dont le dernier contenu diffusé remplit cette émission peu avant son début (**Rediffusion de l'émission**, depuis le 2026-10-18) ; vide = aucune. Un nom inconnu est signalé en note et l'émission est importée sans lui. |
| `intro_playlist`, `outro_playlist` | noms de playlists ; vide = valeurs par défaut de la station |
| `rastatime_auth`, `custom_auth`, `custom_username` | authentification DJ live comme dans la boîte de dialogue |
| `djs` | identifiants des DJ, séparés par des virgules ; seuls les utilisateurs de type DJ peuvent être affectés |
| `background_color`, `text_color` | six chiffres hexadécimaux sans `#` |
| `logo` | nom de fichier dans le dossier `logos/` de l'archive (jpg, png, gif, webp) |

**Le mot de passe live personnalisé ne fait jamais partie du fichier.**
L'export l'omet, et l'import donne à une émission avec authentification
personnalisée un mot de passe aléatoire que personne ne connaît.
Définissez ensuite le vrai mot de passe dans le calendrier ; l'aperçu
et le résultat le rappellent sur chaque ligne concernée.

### playlists.csv

`name`, `description` et `items`. `items` liste le contenu dans l'ordre,
séparé par `|` :

```
file:imported/Example Radio/StationID/Intro.mp3|webstream:BBC World Service|block:Morning Music|linein:Studio A
```

Les fichiers sont référencés par leur chemin sous la racine de la
bibliothèque (tel que l'export l'écrit), tout le reste par son nom.
Les points de repère et les fondus viennent du fichier et des valeurs
par défaut, comme lorsque vous déposez un élément dans une playlist.
Avec *remplacer*, une playlist est remplacée entièrement ou pas du
tout.

### blocks.json

Une liste JSON, un objet par smart block : `name`, `description`,
`type` (`dynamic` ou `static`), `limit` (`value` et `modifier` :
items, minutes, hours, remaining), `sort`, les interrupteurs
(`repeat_tracks`, `overflow_tracks`, `only_unplayed`,
`only_with_expiry`, `use_requests`, `exclude_played_lately` avec ses
minutes, `exclude_artists_played_lately` avec ses minutes ; depuis le
2026-10-23 les clés sont `*_minutes`, un lot avec les anciennes clés
`*_hours` est toujours lu, heures x 60) et `criteria`,
une liste de règles avec `group`, `field`, `modifier`, `value` et
`extra` (la seconde valeur de `between` et *est dans le champ*).

**Comment les règles se combinent.** Un `group` est une ligne de
l'éditeur de smart blocks. Les règles du même groupe **et** du même
champ sont des alternatives (OU) — les lignes qu'ajoute le bouton **+**
à côté d'un critère. Tout le reste est combiné par ET : des groupes
différents, et des champs différents même au sein d'un groupe. Exemple
— *genre Pop ou Electronic, et plus de 110 BPM* :

```json
"criteria": [
  {"group": 0, "field": "genre", "modifier": "is", "value": "Pop"},
  {"group": 0, "field": "genre", "modifier": "is", "value": "Electronic"},
  {"group": 1, "field": "bpm", "modifier": "is greater than", "value": "110"}
]
```

« Soit A et B, soit C » sur des champs différents ne peut pas
s'exprimer dans un seul bloc ; placez plutôt deux smart blocks dans une
playlist. Un champ peut
apparaître dans plusieurs groupes, chacun avec ses propres
alternatives : (A ou B) et (C ou D).

**Dates.** Pour *Téléversé* (`utime`), *Dernier Modifié* (`mtime`) et
*Dernier Joué* (`lptime`) :

* `before`, `after` et `between` comptent à rebours depuis maintenant :
  un nombre entier dans `value` plus `unit` — `minute`, `hour`, `day`,
  `week`, `month` ou `year` ; `between` prend en plus `extra` avec
  `extra_unit`. `{"field": "utime", "modifier": "after", "value": "30", "unit": "day"}` = téléversé dans les 30 derniers jours. Les
  exports antérieurs au 2026-10-14 écrivaient `"7 day ago"` dans
  `value` ; cette forme est toujours acceptée.
* Les autres modificateurs prennent une date fixe `AAAA-MM-JJ` ou
  `AAAA-MM-JJ HH:MM:SS` dans votre fuseau horaire d'utilisateur, telle
  que l'éditeur l'affiche.

L'aperçu vérifie chaque règle comme l'éditeur — modificateur adapté au
critère, nombres, durées (`HH:MM:SS`), dates, longueur — et liste ce
qui ne va pas. Un bloc est écrit entièrement ou pas du tout.

### webstreams.csv

`name`, `description`, `url`, `length` (`HH:MM:SS`) et `input_gain_db`.
L'URL est sondée à l'import, comme le fait la boîte de dialogue
webstream.

### podcasts.csv

`url` (le flux), `title`, `auto_ingest`, `auto_expiry_enabled`,
`auto_expiry_days`, `album_override`, `default_track_type` (le code de
Paramètres → Types de piste). Le flux est récupéré à l'import ; les
épisodes ne sont pas exportés — le flux les livre à nouveau.

## 4. Conseils

* Exportez d'abord, même sur une station vide : le fichier porte les
  en-têtes exacts et le README.
* Tenez un tableur par station et réimportez-le après modification ;
  avec *ignorer*, seules les nouvelles lignes sont créées.
* Deux lignes du même fichier qui se chevauchent : la première est
  créée, la seconde échoue à l'import avec le message de chevauchement.
* Logos volumineux : la limite d'envoi du serveur est indiquée sous le
  champ de fichier.

## 5. Voir aussi

* [Calendrier](./CALENDAR.md) — la boîte de dialogue « Nouvelle
  émission » dont l'import applique les règles.
* [Modèles d'émission](./SHOW_TEMPLATES.md) — réutiliser des réglages
  dans la boîte de dialogue.
* [Playlists de chargement automatique](./AUTOLOADING_PLAYLISTS.md) —
  ce que la colonne `content` active.
* [Sauvegarde](./BACKUP.md) — la sauvegarde complète de la base ;
  Import / Export en est le pendant lisible et modifiable.
