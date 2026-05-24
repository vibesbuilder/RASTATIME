# Bibliothèque

> **Où vous êtes dans le manuel.** C'est l'un des chapitres
> **Contenu et bibliothèque**. Pour des détails par type
> d'entrée, voir aussi [Webstreams](./WEBSTREAMS.md) et
> [Line-In](./LINE_IN.md), qui sont suivis comme leurs
> propres items de bibliothèque.

La **Bibliothèque** est l'inventaire de chaque morceau
d'audio que RASTATIME peut mettre à l'antenne. Elle a cinq
types d'items :

| Type | Ce que c'est | Où les lignes vivent |
|---|---|---|
| **Piste (Track)** | Un fichier audio unique (MP3, FLAC, OGG, WAV, AAC). | `cc_files` |
| **Smart Block** | Une *requête* — "choisir N pistes où genre = pop et BPM > 100", évaluée au moment du build. | `cc_block` + `cc_blockcontents` (critères) |
| **Playlist** | Une liste ordonnée d'items : pistes, smart blocks, webstreams ou line-ins. | `cc_playlist` + `cc_playlistcontents` |
| **Webstream** | Une URL pointant vers une autre source Icecast / Shoutcast / HTTP audio. | `cc_webstream` |
| **Line-In** | Une entrée audio live nommée sur la machine de l'opérateur. | `rastatime_linein` |

La Bibliothèque est ce depuis quoi vous glissez quand vous
remplissez une émission.

---

## 1. La page Bibliothèque

Bibliothèque → ouvre la vue tableau avec une ligne par item.

```
  ┌─────────────────────────────────────────────────────────────────┐
  │  Bibliothèque                                  ▼  Téléverser    │
  ├─────────────────────────────────────────────────────────────────┤
  │  Filtre :  [type ▾]  [créateur ▾]  [genre ▾]  [longueur ▾]      │
  │  Recherche: [_______________________________]                   │
  ├──┬──────────┬────────────────┬──────────┬──────────┬─────────┬──┤
  │  │ Type     │ Titre          │ Créateur │ Longueur │ Propr.  │  │
  ├──┼──────────┼────────────────┼──────────┼──────────┼─────────┼──┤
  │ ◯│ Piste    │ Chanson A      │ Artist 1 │ 03:42    │ admin   │  │
  │ ◯│ Piste    │ Chanson B      │ Artist 2 │ 04:15    │ admin   │  │
  │ ◯│ Smart B. │ Hot pop        │ —        │ ~30:00   │ admin   │  │
  │ ◯│ Playlist │ Matinale       │ —        │ 60:00    │ host1   │  │
  │ ◯│ Webstream│ BBC Radio 1    │ —        │ 60:00    │ admin   │  │
  │ ◯│ Line-In  │ Mixeur Studio  │ —        │ ∞        │ admin   │  │
  └──┴──────────┴────────────────┴──────────┴──────────┴─────────┴──┘
```

### Puces de filtre

Les puces au-dessus du tableau restreignent les lignes
visibles. Elles se combinent avec **ET** : définir
*type = Piste* et *genre = pop* affiche seulement les
pistes pop. Effacez toute puce avec son **×**.

| Puce | Sur quoi elle filtre |
|---|---|
| **Type** | Piste / Smart Block / Playlist / Webstream / Line-In. Le jeu de puces à cinq couleurs dans l'en-tête de colonne reflète ceci. |
| **Créateur** | Le créateur (artiste) des métadonnées de la piste, pas le propriétaire de téléversement. |
| **Genre** | Tag de genre des métadonnées. |
| **Longueur** | Buckets grossiers (< 30 s, 30 s – 2 min, 2 – 10 min, > 10 min, ∞). |
| **Propriétaire** | L'utilisateur RASTATIME qui a importé l'item. Les DJ sont limités à leurs propres items ; les Admins voient tout. |

> **Conseil opérateur.** Les puces colorent aussi les badges
> de ligne. Après quelques semaines avec le même set, vous
> arrêtez de lire la colonne *Type* et lisez juste les
> couleurs : bleu = piste, vert = line-in, jaune = block,
> orange = stream, violet = playlist.

### Recherche en texte libre

La boîte **Recherche** fonctionne sur **titre, créateur,
album, genre, nom de fichier** pour les pistes ; **nom**
pour les blocks / playlists / webstreams / line-ins. Elle
utilise une correspondance de sous-chaîne — taper `bowie`
correspond à "David Bowie", "BOWIE" et "bowie-heroes.mp3".

> **Comment ça marche sous le capot.** La recherche est
> côté serveur via `LibraryController::contentsFeedAction`.
> Le widget DataTable envoie le terme de recherche + l'état
> actuel des puces comme paramètres d'URL ; le contrôleur
> assemble une requête PostgreSQL `ILIKE` contre les
> colonnes pertinentes. La pagination est aussi côté
> serveur, donc une bibliothèque de 100 000 pistes ne
> charge pas 100 000 lignes dans le navigateur.

### Trier les colonnes

Cliquez sur n'importe quel en-tête de colonne pour trier
en ordre ascendant ; cliquez à nouveau pour descendant.
Le tri par défaut est **titre, ascendant**.

---

## 2. Pistes

### Importer des pistes

Trois façons :

#### 2.1 Téléversement navigateur (ponctuel)

Bibliothèque → **Téléverser** → glissez les fichiers sur
la zone de téléversement ou cliquez pour choisir.

| Champ | Notes |
|---|---|
| **Fichier** | L'un de : MP3, FLAC, OGG, WAV, AAC, M4A. |
| **Propriétaire** | Par défaut vous. Les Admins peuvent surcharger. |

Le téléversement exécute l'analyzer (métadonnées +
vérification de jouabilité) et ajoute la ligne à la
bibliothèque. Les gros fichiers peuvent prendre quelques
secondes à apparaître parce que le décodage de jouabilité
exécute tout le fichier de bout en bout.

#### 2.2 Dossier d'import local (lot)

Configurez une fois Paramètres → **Machine locale** →
**Dossier d'import local**. Puis déposez les fichiers dans
ce répertoire sur le serveur ; ils apparaissent dans la
bibliothèque au prochain poll de l'analyzer (par défaut
toutes les 60 s). Les sous-dossiers sont scannés
récursivement. Voir [Machine locale](./LOCAL_MACHINE.md).

> **Conseil opérateur.** Utilisez le Dossier d'import
> local pour tout lot de plus d'une douzaine de fichiers.
> Le téléverseur navigateur garde la requête ouverte
> jusqu'à ce que l'analyzer finisse ; un lot de 200
> fichiers peut garder la requête ouverte pendant
> plusieurs minutes et l'opérateur abandonne.

#### 2.3 Abonnement podcast (récurrent)

Paramètres → **Podcasts** → **S'abonner**. Collez une URL
de flux RSS, optionnellement un type de piste par défaut,
une politique d'expiration automatique (supprimer les
épisodes plus vieux que N jours). Les nouveaux épisodes
sont téléchargés par le worker job runner et importés
comme pistes exactement comme un téléversement manuel.

> **Comment ça marche sous le capot.** La récupération de
> podcast reposait avant sur Celery ; sur RASTATIME
> (Windows) elle tourne dans le `PodcastFetchJob` du
> service `RASTATIME-WORKER`, interrogé à l'intervalle
> configuré (par défaut 30 min). Voir ARCHITECTURE §16
> pour le nouveau runner basé sur threading.

### Modifier les métadonnées de piste

Cliquez sur une ligne de piste → **Modifier les
métadonnées** dans le menu d'action de la ligne.

| Champ | Où il finit |
|---|---|
| **Titre** | `cc_files.track_title` |
| **Créateur (Artiste)** | `cc_files.artist_name` |
| **Album** | `cc_files.album_title` |
| **Genre** | `cc_files.genre` |
| **Année** | `cc_files.year` |
| **BPM** | `cc_files.bpm` |
| **Type de piste** | `cc_files.track_type` — utilisé par les filtres smart-block |
| **Cue In / Out** | `cc_files.cuein` / `cueout` — couper le début / la fin sans re-encodage |
| **Fade In / Out** | `cc_files.fadein` / `fadeout` |
| **Replay Gain** | `cc_files.replay_gain` — utilisé par le moteur de playout pour la normalisation de niveau |

> **Conseil opérateur.** Définissez **Cue In** sur les
> promos radio / stings qui ont quelques secondes de
> silence au début. Le point de cue est un trim non
> destructif — le fichier sur disque est inchangé, mais
> la lecture commence au cue.

### Supprimer une piste

Ligne → **Supprimer**. La piste est retirée de la
bibliothèque *et* de toute playlist dont elle faisait
partie. Si la piste est actuellement planifiée dans une
émission à venir, vous obtenez un avertissement et pouvez
choisir d'annuler ou de continuer (les lignes de schedule
sont aussi retirées).

> **Comment ça marche sous le capot.** Supprimer enlève la
> ligne `cc_files` et toutes les lignes
> `cc_playlistcontents` / `cc_schedule` qui la
> référencent (CASCADE). Le fichier sur disque est déplacé
> vers `C:\rastatime\media\.trash\` plutôt que délié,
> donc un opérateur qui a supprimé par accident peut
> restaurer pendant 7 jours. Voir
> [`docs/operator/BACKUP.md`](../../operator/BACKUP.md)
> pour le cron de nettoyage de la corbeille.

---

## 3. Smart Blocks

Un **smart block** est une requête. Quand le block est
planifié dans une émission, la requête est évaluée au
moment du build et étendue en un ensemble concret de
pistes. Les smart blocks sont comment vous construisez des
émissions qui disent "jouer 30 minutes de pistes pop
entraînantes d'après 2010" sans choisir manuellement
chaque piste.

### Créer un smart block

Bibliothèque → **+ Nouveau** → **Smart Block**.

| Champ | Signification |
|---|---|
| **Nom** | Visible dans la bibliothèque et sur le calendrier. |
| **Type** | **Statique** — choisit une fois au moment de la création ; l'ensemble ne change jamais. **Dynamique** — re-choisit chaque fois que le block est planifié. |
| **Critères** | Ajouter des lignes : *artiste contient "Bowie"*, *bpm entre 100 et 130*, *genre est pop*, etc. Chaque ligne se combine en ET avec les autres ; un groupe OU peut être créé en ajoutant un groupe imbriqué. |
| **Limiter à** | L'un de : **Nombre de pistes** (ex. 10), **Durée en temps** (ex. 30:00), **Temps restant dans l'émission** (laisse le smart block remplir exactement jusqu'à la fin de l'émission). |
| **Trier** | Aléatoire / plus récent en premier / par artiste / par nombre de lectures / etc. |

> **Conseil opérateur.** La limite **"Temps restant dans
> l'émission"** est la plus utile pour les autoloading
> playlists. Combinée avec une playlist d'intro + outro,
> vous pouvez construire une émission d'une heure en
> tamponnant un intro de 30 s + un smart block `*` + un
> outro de 60 s, et l'auto-build mettra le bon nombre de
> pistes entre les deux.

### Pourquoi un smart block peut retourner moins de pistes que demandé

Les smart blocks respectent le **scope de bibliothèque**
de l'opérateur :

- Le DJ propriétaire voit seulement ses propres pistes.
- Un Program Manager voit toute la bibliothèque.

Si vous définissez "Limiter à 10 pistes" mais seulement 4
pistes dans la bibliothèque correspondent aux critères,
vous obtenez 4. Le block ne s'arrête pas en erreur.

> **Comment ça marche sous le capot.** Les critères sont
> stockés dans `cc_blockcriteria`. Au moment du build,
> `BlockExpander.expand()` assemble un PostgreSQL
> `SELECT … WHERE … LIMIT …` sur `cc_files`. Les limites
> de temps restant se convertissent en plafond de durée
> via la méthode `getSecondsRemaining()` de l'instance
> d'émission. Voir ARCHITECTURE §23.19 pour
> l'interaction réserve d'outro avec les smart blocks
> de temps restant.

### Bascules de restriction du pool (Options avancées)

Le tiroir **Options avancées** en bas du dialogue Smart Block
héberge trois bascules de restriction du pool qui
restreignent l'ensemble candidat *avant* l'exécution du tri
+ limite :

| Bascule | Restriction du pool |
|---|---|
| **Allow only tracks not played yet** (Autoriser uniquement les pistes pas encore jouées) | Pistes dont `cc_files.lptime` est `NULL` (le playout ne les a jamais journalisées). Utile pour les blocs de découverte / rotation de nouveau contenu. |
| **Exclude tracks played lately** (Exclure les pistes jouées récemment) | Pistes dont `lptime` est `NULL` *ou* plus ancien que la fenêtre de retour configurée en heures (1..8760 h, par défaut 24). Utilisez ceci quand vous voulez éviter une re-rotation récente sans interdire toute lecture antérieure. Le champ compagnon "Exclude tracks played in the last hours" apparaît lorsque la bascule est activée. |
| **Exclude artists played lately** (Exclure les artistes joués récemment) | Pistes dont `artist_name` est NULL / vide *ou* dont l'artiste n'a pas été entendu via une autre piste dans la fenêtre de retour configurée en heures (1..8760 h, par défaut 24). Utilisez ceci pour éviter que deux pistes du même artiste se regroupent — indépendamment de la piste spécifique jouée. Le champ compagnon "Exclude tracks played in the last hours" apparaît lorsque la bascule est activée. |
| **Allow only tracks with expiry date** (Autoriser uniquement les pistes avec date d'expiration) | Pistes dont `cc_files.expires_at IS NOT NULL`. Utile pour les blocs qui doivent puiser uniquement dans du contenu éphémère (segments d'info datés, bandes-annonces). |

Les quatre se composent en ET et se combinent avec chaque
critère de la section Critères principale.

> **Conseil opérateur.** La bascule "Exclude tracks played
> lately" est la bonne réponse à "joue 30 min de pop, mais
> rien des 4 dernières heures". Combinez-la avec
> `Trier : Aléatoire` pour un auto-build à rotation fraîche
> qui ne sonne jamais répétitif dans la fenêtre configurée.
> Les pistes jamais jouées sont *incluses* par le filtre —
> une piste qui n'est jamais passée à l'antenne ne peut
> évidemment pas être passée "récemment".
>
> La bascule compagnon **"Exclude artists played lately"**
> est la réponse à "ne fais pas suivre une piste des Beatles
> par une autre piste des Beatles pendant au moins 6 heures,
> même si j'ai 50 pistes des Beatles dans le pool". Les deux
> filtres se composent : activez les deux pour obtenir "ni
> piste récente NI artiste récent" en même temps.

> **Comment ça marche sous le capot.** `Exclude played
> lately` ajoute une seule clause `WHERE cc_files.lptime IS
> NULL OR cc_files.lptime < NOW() - INTERVAL 'N hours'` à
> la requête Propel. La valeur en heures est persistée dans
> `cc_block_criteria` (criteria =
> `exclude_played_lately_hours`) à côté du master flag
> (criteria = `exclude_played_lately`).  `Exclude artists
> played lately` ajoute une clause `WHERE
> cc_files.artist_name IS NULL OR cc_files.artist_name = ''
> OR NOT EXISTS (SELECT 1 FROM cc_playout_history JOIN
> cc_files ON ... WHERE artist_name matches AND starts >
> NOW() - INTERVAL 'N hours')` — `NOT EXISTS` court-circuite
> au premier match donc le coût reste borné même avec une
> grande table d'historique.  Persisté comme deuxième paire
> de critères (`exclude_artists_played_lately` + `..._hours`).
> Aucun changement de schéma pour les deux filtres —
> rétrocompatible avec les smart blocks créés avant la
> fonctionnalité respective (lignes manquantes = désactivé).
> Voir ARCHITECTURE §23.21.

### Modifier un smart block

Cliquez sur le block → **Modifier**. Changer les critères
ne change *pas* rétroactivement les émissions qui ont
déjà été construites — seulement les futures évaluations.

---

## 4. Playlists

Une **playlist** est une liste ordonnée d'items, où chaque
item est une piste, un smart block, un webstream ou un
line-in. Les playlists sont les briques de construction
du contenu d'émission.

### Créer une playlist

Bibliothèque → **+ Nouveau** → **Playlist**.

L'éditeur de playlist s'ouvre avec la playlist à gauche
et la bibliothèque à droite. Glissez les items de la
bibliothèque sur la playlist ; réordonnez par
glisser-déposer. Définissez crossfades et points de cue
par item si nécessaire.

| Comportement par type d'item |  |
|---|---|
| **Piste** | Joue comme configurée (cue in / out, fade in / out). |
| **Smart Block** | S'étend au moment du build, pas au moment de l'édition de la playlist. |
| **Webstream** | Joue pour la durée configurée de la ligne de playlist (par défaut 60 min, peut être surchargée). Voir [Webstreams](./WEBSTREAMS.md). |
| **Line-In** | Joue pour la durée configurée de la ligne de playlist. Voir [Line-In](./LINE_IN.md). |

### Longueur par défaut

Chaque playlist a une **Longueur par défaut** qui apparaît
comme la durée nominale de la playlist dans la
bibliothèque. Pour une playlist contenant seulement des
pistes, c'est la somme des durées des pistes. Pour une
playlist contenant des smart blocks / webstreams /
line-ins, la longueur par défaut est ce qui *jouerait* si
chaque item variable tournait pour sa durée configurée.

### Utiliser une playlist dans une émission

Deux chemins :

1. **Ponctuel** : glissez la playlist sur une émission
   vide dans le show-builder. Les items de la playlist
   sont *aplatis* dans le planning au point de glisser.
   La playlist d'origine n'est pas liée à l'émission —
   modifier la playlist plus tard n'affecte pas le
   planning.

2. **Autoloading** : attachez la playlist à la définition
   d'émission dans la section **Autoloading Playlist** du
   formulaire d'édition d'émission. Chaque future
   instance de l'émission aura les items de la playlist
   construits automatiquement dans son planning.
   Modifier la playlist *affecte* les futurs builds.
   Voir [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md).

> **Conseil opérateur.** Une seule playlist peut servir à
> double usage : glissez-la sur une émission ad-hoc et
> attachez-la aussi comme autoloading playlist pour une
> émission récurrente. Les deux utilisations sont
> indépendantes.

---

## 5. Webstreams et Line-Ins comme items de bibliothèque

Les [Webstreams](./WEBSTREAMS.md) comme les
[Line-Ins](./LINE_IN.md) apparaissent dans la bibliothèque
et se comportent comme des pistes quand planifiés :
glissez-les sur une émission ou dans une playlist
exactement de la même façon.

Leurs chapitres par fonctionnalité couvrent les
spécificités (format d'URL, authentification, probing de
périphérique, etc.). Le point d'entrée Bibliothèque est
le même que pour tout autre item.

---

## 6. Actions en masse

Cochez la case au début de chaque ligne, puis utilisez la
barre d'outils qui apparaît au bas du tableau :

| Action | Effet |
|---|---|
| **Ajouter à une playlist** | Ajouter les lignes sélectionnées à une playlist existante de votre choix. |
| **Supprimer** | Supprimer les lignes sélectionnées. Même sémantique de confirmation-si-planifié que la suppression d'une seule ligne. |
| **Modifier les métadonnées** | Ouvrir un dialogue d'édition en lot. S'applique seulement aux pistes. |
| **Transférer le propriétaire** | Réassigner la propriété (Admin / Super Admin seulement). Utilisé quand un DJ part et que ses fichiers doivent passer au compte de la station. |

---

## 7. Foire aux questions

### "J'ai téléversé une piste et elle n'est jamais apparue."

Vérifiez le badge de statut de téléversement :

- **Jaune (Avertissement)** : le fichier a été importé
  mais la vérification de jouabilité a produit des
  avertissements (typiquement un MP3 mal encodé avec des
  problèmes de trame finale). Le fichier *va* jouer ;
  vous pouvez ignorer l'avertissement.
- **Rouge (Échec)** : le fichier est injouable ou
  l'analyseur de métadonnées a planté. La ligne est
  supprimée de la liste de la bibliothèque (la puce
  filtre **Imports échoués** sur la page de statut de
  téléversement les montre).
- **Pas de badge mais pas de ligne** : le service
  analyzer ne tourne pas. Vérifiez
  `Get-Service RASTATIME-ANALYZER`.

### "Pourquoi mon smart block retourne-t-il les mêmes pistes à chaque fois ?"

Vous avez probablement choisi **Statique** au lieu de
**Dynamique**. Modifiez le block et changez le type ; le
prochain build re-requêtera.

### "Puis-je importer une structure de dossier en préservant les noms de sous-dossiers ?"

Le Dossier d'import local préserve les noms de
sous-dossiers comme champ **album** des pistes importées
si aucun tag ID3 album n'est défini. C'est le motif
opérateur le plus courant pour une archive musicale de
longue traîne.

### "Quelle est la taille de fichier maximale ?"

Le téléverseur navigateur est limité par
`LimitRequestBody` d'Apache — par défaut 100 MB. Le
Dossier d'import local n'a pas de limite pratique (les
fichiers sont lus depuis le disque, pas POSTés).

---

## Où aller ensuite

* [Calendrier](./CALENDAR.md) — comment mettre les items
  de bibliothèque à l'antenne.
* [Modèles d'émission](./SHOW_TEMPLATES.md) — réutiliser
  les paramètres d'émission.
* [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) —
  laisser les émissions se remplir elles-mêmes depuis une
  playlist.
* [Webstreams](./WEBSTREAMS.md) et [Line-In](./LINE_IN.md)
  pour le détail par type des deux items les plus récents.
