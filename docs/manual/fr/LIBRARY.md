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
| **Piste (Track)** | Un fichier audio unique (MP3, M4A, OGG, Opus, ... ; WAV et FLAC sont convertis en MP3 à l'import par défaut). | `cc_files` |
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

> **Temps restant et crossfades (depuis le 2026-10-06).** Les lignes
> musicales se chevauchent de leur crossfade (valeur maison 3 s, ou
> celle du type de piste ; jingles 0), le temps restant d'une émission
> est donc le temps *mis en page* : de la fin de la dernière ligne à la
> fin de l'émission — le chiffre du pied de page du Show Builder. Un
> smart block « Temps restant dans l'émission » est choisi contre ce
> temps, entre ses vrais voisins, de sorte que la dernière ligne se
> termine à une seconde près de la fin de l'émission (le solveur du bloc
> est aléatoire ; le pool décide de ce qui est possible). Un bloc limité
> par *Durée en temps* est choisi de la même façon (décision opérateur
> 2026-10-06) : 12 minutes sont 12 minutes **à l'antenne**, pas la somme
> des pistes, si bien qu'un jingle de station après trois blocs de ce
> type tombe à 12:00, 24:xx et 36:xx de l'heure. Un jingle placé entre
> deux pistes musicales coûte sa propre durée plus les 3 s de
> chevauchement qu'il interrompt.

### Recherche en texte libre

La boîte **Recherche** fonctionne sur **titre, créateur,
album, genre, nom de fichier** pour les pistes ; **nom**
pour les blocks / playlists / webstreams / line-ins. Elle
utilise une correspondance de sous-chaîne — taper `bowie`
correspond à "David Bowie", "BOWIE" et "bowie-heroes.mp3".

**Indicateur de filtre actif (depuis le 2026-10-09).** Tant qu'un
texte de recherche ou un champ de la recherche avancée est renseigné,
la boîte de recherche prend une bordure de couleur accent et affiche,
à droite, combien d'éléments du type choisi correspondent (« 13 sur
11 108 titres », « 0 sur 32 blocs intelligents » ; depuis le
2026-10-18 le compte nomme le type - titres, listes de lecture, blocs
intelligents, flux web, podcasts, entrées ligne). Le **×** à côté de
ce nombre efface le texte et tous les champs de la recherche avancée
d'un coup.

**Podcasts (depuis le 2026-10-21).** La liste des podcasts a la même
zone de recherche : elle porte sur le **titre** et le **créateur** du
podcast, sans tenir compte de la casse, et affiche « X of N podcasts »
et le **×** de la même façon.  La flèche de la recherche avancée y est
masquée - elle concerne les autres types.

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

### Disposition du tableau

Faites glisser une colonne par son en-tête pour la déplacer ;
le bouton **Colonnes** (icône de liste) au-dessus du tableau
affiche ou masque les colonnes, et le sélecteur **Afficher**
en dessous fixe le nombre de lignes par page. RASTATIME
mémorise cette disposition — ordre des colonnes, colonnes
visibles, lignes par page et tri — **par utilisateur sur le
serveur** ; elle vous suit donc dans chaque navigateur et sur
chaque poste. Depuis le 2026-10-24, les **colonnes visibles sont
mémorisées par type de média** : Pistes, Playlists, Blocs
intelligents, Webstreams et Entrées ligne ont chacun leur propre
jeu, et le bouton **Colonnes** modifie toujours le jeu de
l'onglet ouvert. Un onglet jamais ajusté démarre avec une valeur
par défaut raisonnable (pistes : pochette, titre, créateur, type,
genre, durée, importé ; playlists et blocs intelligents : titre,
description, durée, créateur, dernière modification ;
webstreams : titre, description, site web, durée, créateur,
dernière modification ; entrées ligne : titre, description,
durée, dernière modification). Le tableau des pistes du tableau de bord et
celui de la boîte de dialogue **Ajouter des pistes** du
calendrier ont chacun leur propre disposition (la boîte de
dialogue n'a pas de colonne *Actions*) ; le tableau
*Scheduled Shows* à côté partage une seule disposition entre
les deux endroits. Les recherches et la page courante ne
sont pas mémorisées — le tableau s'ouvre toujours à la
page 1. Pendant le défilement des lignes, la ligne de
recherche, les en-têtes de colonnes et la pagination restent
visibles.

---

## 2. Pistes

### Importer des pistes

Trois façons :

#### 2.1 Téléversement navigateur (ponctuel)

Bibliothèque → **Téléverser** → glissez les fichiers sur
la zone de téléversement ou cliquez pour choisir.

| Champ | Notes |
|---|---|
| **Fichier** | L'un de : MP3, M4A, MP4, AAC, OGG, OGA, Opus, FLAC, WAV, MP2, MP1, AU - depuis le 2026-10-14 la même liste que celle du dossier d'import local et de l'import FTP. Les fichiers sans perte sont convertis en MP3 à l'import par défaut (voir *Formats de fichier à l'import* ci-dessous). |
| **Propriétaire** | Par défaut vous. Les Admins peuvent surcharger. |

Le téléversement exécute l'analyzer (métadonnées +
vérification de jouabilité) et ajoute la ligne à la
bibliothèque. Les gros fichiers peuvent prendre quelques
secondes à apparaître parce que le décodage de jouabilité
exécute tout le fichier de bout en bout.

> **Où le fichier est rangé (depuis le 2026-10-24).**  L'analyzer
> classe chaque piste sous `imported/<artiste>/<album>/` dans la
> bibliothèque (artiste et album tels que tagués ; sans tag album
> seulement `imported/<artiste>/`).  Un fichier **sans tag artiste**
> va dans `imported/tagless/` - avant le 2026-10-24 ces fichiers
> restaient directement dans `imported/`.  Le dossier n'est que
> l'emplacement de stockage ; la bibliothèque affiche la piste selon
> ses tags dans tous les cas.  Taguez donc le fichier d'abord si
> vous voulez le voir classé sous son artiste.
>
> **Pochettes.**  Une pochette intégrée est stockée en cinq tailles
> JPG (32 à 512 px) sous `imported/artwork/` ; rien d'autre n'est
> écrit pour elle depuis le 2026-10-24.  Les petites vignettes de la
> bibliothèque et de l'éditeur sont construites à partir de ces JPG
> quand la page les demande.

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
> (Windows) le téléchargement s'exécute de manière synchrone
> dans l'API (déclenché depuis l'interface web ou la
> vérification du flux) et écrit directement le fichier et son
> entrée de bibliothèque.
>
> **Les fichiers d'épisodes (depuis le 17/09/2026)** arrivent
> dans un dossier par podcast au sein de la médiathèque :
> `imported/<nom du podcast>/`.  Renommer un podcast ouvre un
> nouveau dossier pour les épisodes futurs ; les fichiers
> existants restent en place.

### Formats de fichier à l'import (depuis le 2026-10-14)

Quelle que soit la voie par laquelle une piste arrive - téléversement,
dossier d'import local, import FTP ou import en masse -, l'analyzer
examine l'audio contenu dans le fichier (et non son extension) avant
de le classer :

- **MP3, MP2, MP1, AAC en M4A / MP4, OGG Vorbis et Opus** sont
  importés tels quels et jamais réencodés.
- **L'AAC brut (`.aac`)** est toujours réempaqueté en `.m4a` sans
  réencodage : un fichier AAC brut n'a pas d'index, sa durée ne peut
  qu'être estimée, et il ne peut pas porter de tags.
- **L'audio sans perte** - WAV, FLAC, AU, Apple Lossless en M4A - est
  converti en **MP3 à 320 kbit/s** tant que Paramètres → **Machine
  locale** → **Format d'import** est activé (par défaut).  L'original
  sans perte n'est pas conservé ; les tags, la date Expiry et une
  pochette intégrée sont repris.  Si une conversion échoue, l'original
  est importé sans modification.  Détails :
  [Machine locale](./LOCAL_MACHINE.md), section 5.
- **Les tags sont lus dans tous les formats.**  Outre l'ID3 des
  fichiers MP3, l'analyzer lit les tags des fichiers WAV (bloc ID3 et
  RIFF INFO), les commentaires des fichiers FLAC, OGG et Opus et les
  champs des fichiers M4A, y compris description / commentaire et la
  date **Expiry** (`YYYY-MM-DD`).  Avant le 2026-10-14, les tags des
  fichiers WAV n'étaient pas lus, et un `.aac` brut avec un tag ID3
  échouait à l'import.

Les épisodes de podcast n'en font pas partie : ils sont téléchargés
directement dans la bibliothèque (section 2.3) et gardent leur format.
Depuis le 2026-10-24, chaque épisode téléchargé est néanmoins
**mesuré en sonie** (EBU R128) juste après le téléchargement, afin que
la diffusion applique son vrai gain par piste au lieu d'une
approximation. Les épisodes antérieurs à cette date se rattrapent
avec **Settings → Streams → Measure loudness**, qui ne mesure que les
fichiers sans valeurs.

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
| **Cue In / Out** | `cc_files.cuein` / `cueout` — couper le début / la fin sans re-encodage. Depuis le 30/09/2026, les valeurs restent à l'intérieur du fichier : un cue out au-delà de la longueur est ramené à la longueur, un cue in négatif devient zéro. Une modification est copiée dans les lignes des émissions à venir qui programment la piste (les lignes déjà commencées ne sont pas touchées), et ces émissions sont recalculées - pas besoin de les remplir à nouveau. |
| **Fade In / Out** | `cc_files.fadein` / `fadeout` |
| **Replay Gain** | `cc_files.replay_gain` — utilisé par le moteur de playout pour la normalisation de niveau |
| **Play Count** | Colonne de la bibliothèque (masquée par défaut, sélecteur de colonnes), en lecture seule : combien de fois le titre est passé à l'antenne - un comptage par ligne de l'historique de diffusion, le même chiffre que Historique → File Summary. Triable ; la recherche avancée accepte une plage. Depuis le 2026-10-07. |
| **ID** | Colonne de la bibliothèque (visible par défaut, sélecteur de colonnes), en lecture seule : l'identifiant du fichier dans la base de données, le même numéro que l'API REST et les journaux de diffusion utilisent. Seuls les fichiers le portent - playlists, smart blocks et webstreams ont leurs propres plages de numéros et affichent une cellule vide. Triable ; la recherche avancée accepte une plage. Depuis le 2026-10-16. |
| **Teaser** / **Teaser pour les émissions**, **Type de teaser** | La ou les émissions qu'un jingle annonce et comment (teaser d'émission, teaser du jour « aujourd'hui », teaser du jour « demain ») ; deux champs de l'éditeur de piste et de l'édition groupée, affichés `Nom de l'émission · today` dans la colonne *Teaser* (masquée par défaut, recherchable). Les smart blocks choisissent les jingles qui conviennent avec le critère *Teaser : correspond à la grille* - voir [Automatisation des teasers](./TEASERS.md). Depuis le 2026-10-16. |
| **Crossover** | Comment ce titre rencontre ses voisins (depuis le 2026-09-29 un champ à trois choix ; les deux exceptions s'excluent mutuellement). **As the track type** (comme le type de piste, par défaut) : le titre se chevauche et s'enchaîne selon son type de piste - Settings → Track Types → *Crossfade Duration* - ou, sans valeur à cet endroit, selon la Default Track Crossfade Duration ; depuis le 2026-09-30 il hérite aussi du préréglage *No Fade during Crossover* du type. **No Fade during Crossover** (pas de fondu pendant le crossover, `cc_files.no_fade_crossfade`) : le chevauchement reste, mais ce titre garde son niveau plein pendant que l'autre s'estompe ; à une limite d'émission dépassée, un titre sortant marqué est coupé au lieu d'être fondu. **Exclude from Crossover** (exclure du crossover, `cc_files.exclude_crossfade`) : ce titre ne chevauche jamais un voisin - il démarre à la fin du titre précédent et le suivant démarre à sa fin. Passer à *Exclude* ou en revenir recalcule les lignes des émissions à venir qui programment le titre. |
| **Métadonnées du flux** (depuis le 2026-10-14) | Si l'artiste et le titre de cette piste parviennent aux lecteurs des auditeurs (ICY) et au Live Text. **Comme le type de piste** (défaut) : le préréglage de Settings → Track Types → *Forward Metadata to the Stream*. **Transmettre au flux** / **Ne pas transmettre** : le choix propre de la piste. Pendant une piste sans transmission, le flux affiche « Nom de la station - Nom de l'émission » dans chaque format de Stream Label, comme une source live sans métadonnées. Pour les jingles, identifiants et promos ; l'historique de diffusion n'est pas concerné. |

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

Pendant que le serveur supprime, le tableau affiche sa superposition
de chargement et le bouton **Supprimer** indique « Suppression de
N élément(s)… » ; les deux disparaissent une fois la requête
terminée.  Supprimer beaucoup de pistes d'un coup est rapide (depuis
le 2026-11-06, la vérification qu'une rediffusion a encore besoin de
la piste prend des millisecondes au lieu d'environ deux secondes par
fichier).  Si la requête échoue ou expire, un message vous invite à
recharger la page pour voir quels éléments ont été retirés.

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
| **Critères** | Ajouter des lignes : *artiste contient "Bowie"*, *bpm est dans le champ 100 à 130*, *genre est pop*, etc. Les lignes se combinent en ET ; le **+** à côté d'une ligne ajoute une alternative pour le même champ (OU), ex. *genre est pop* **+** *genre est rock*. Détails sous [Import / Export → blocks.json](./IMPORT_EXPORT.md#blocksjson). |
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

Les smart blocks cherchent dans **toute la bibliothèque**,
pour tous les rôles - le smart block d'un DJ puise aussi dans
les pistes des autres utilisateurs.  Pour limiter un bloc à
vos propres pistes, ajoutez le critère **Owner**.

Si vous définissez "Limiter à 10 pistes" mais seulement 4
pistes dans la bibliothèque correspondent aux critères,
vous obtenez 4. Le block ne s'arrête pas en erreur.

> **Comment ça marche sous le capot.** Les critères sont
> stockés dans `cc_blockcriteria`. Au moment du build,
> `BlockExpander.expand()` assemble un PostgreSQL
> `SELECT … WHERE … LIMIT …` sur `cc_files`. Les limites
> de temps restant se convertissent en plafond de durée
> via la méthode `getSecondsRemaining()` de l'instance
> d'émission (depuis le 2026-10-06 le temps libre mis en page :
> `time_filled` = début jusqu'à la fin de la dernière ligne ; le choix
> revient à `Scheduler::pickRemainingBlock()`). Voir ARCHITECTURE §23.19 pour
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
| **Exclude tracks played lately** (Exclure les pistes jouées récemment) | Pistes dont `lptime` est `NULL` *ou* plus ancien que la fenêtre de retour configurée, en **minutes** depuis le 2026-10-23 (1..525600 min, par défaut 1440 = 24 h ; une fenêtre enregistrée en heures est affichée en minutes). Utilisez ceci quand vous voulez éviter une re-rotation récente sans interdire toute lecture antérieure. Le champ compagnon "Exclude tracks played in the last minutes" apparaît lorsque la bascule est activée.  Depuis le 2026-10-16, la fenêtre est mesurée depuis le créneau pour lequel le bloc est développé et **les lignes planifiées comptent aussi** : une piste programmée dans la fenêtre - avant ou après le créneau, y compris les lignes qu'un bloc précédent du même remplissage a placées dans la même émission - est exclue bien qu'elle n'ait pas encore été diffusée.  Depuis le 2026-10-23 cela vaut aussi **au sein d'une playlist** : une playlist est développée bloc par bloc avant toute insertion, et une piste (pour le filtre artistes : un artiste) déjà rassemblée par un bloc précédent ou un élément fixe de la même playlist est laissée de côté par les blocs suivants - deux blocs "Dayteaser" d'une même playlist ne choisissent plus le même teaser. |
| **Exclude artists played lately** (Exclure les artistes joués récemment) | Pistes dont `artist_name` est NULL / vide *ou* dont l'artiste n'a pas été entendu via une autre piste dans la fenêtre de retour configurée, en **minutes** depuis le 2026-10-23 (1..525600 min, par défaut 1440). Utilisez ceci pour éviter que deux pistes du même artiste se regroupent — indépendamment de la piste spécifique jouée. Le champ compagnon "Exclude artists played in the last minutes" apparaît lorsque la bascule est activée. |
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
> NULL OR cc_files.lptime < NOW() - INTERVAL 'N minutes'` à
> la requête Propel. La valeur en heures est persistée dans
> `cc_block_criteria` (criteria =
> `exclude_played_lately_minutes`) à côté du master flag
> (criteria = `exclude_played_lately`).  `Exclude artists
> played lately` ajoute une clause `WHERE
> cc_files.artist_name IS NULL OR cc_files.artist_name = ''
> OR NOT EXISTS (SELECT 1 FROM cc_playout_history JOIN
> cc_files ON ... WHERE artist_name matches AND starts >
> NOW() - INTERVAL 'N minutes')` — `NOT EXISTS` court-circuite
> au premier match donc le coût reste borné même avec une
> grande table d'historique.  Persisté comme deuxième paire
> de critères (`exclude_artists_played_lately` + `..._minutes`).
> Aucun changement de schéma pour les deux filtres —
> rétrocompatible avec les smart blocks créés avant la
> fonctionnalité respective (lignes manquantes = désactivé).
> Voir ARCHITECTURE §23.21.
>
> **Spread intra-bloc (2026-05-25).** Le filtre SQL ci-dessus
> garde le pool de candidats sans artiste / piste joué dans
> les N dernières h *en dehors* du bloc.  Mais le bloc lui-
> même peut quand même contenir deux pistes des Beatles
> consécutives — le SQL ne regarde que l'historique, pas ce
> que le bloc s'apprête à jouer.  Une seconde passe s'exécute
> après la construction de la liste de pistes dans
> `Block::applyWithinBlockSpread()` : pour chaque slot de la
> liste originalement sélectionnée, la piste originale est
> essayée d'abord ; si son artiste (ou file id selon le
> filtre actif) se trouve dans la fenêtre de temps écoulé
> des pistes déjà placées, le moteur tire un remplaçant non-
> conflictuel du pool SQL-filtré plus large (jusqu'à 500
> pistes) à la place.  La durée du bloc reste la même ; seul
> le choix de piste change.  S'il n'y a plus de remplaçant
> non-conflictuel dans le pool, l'originale est placée
> quand même et une entrée `Logging::warn` apparaît dans
> `legacy.log` pour que l'opérateur voie quand le pool était
> trop étroit pour le spread configuré.

### « Allow last track to exceed time limit » (Options avancées)

Avec une limite de temps (minutes, heures, temps restant), le bloc
ajoute des pistes jusqu'à atteindre la limite, et avec cette case
la dernière peut la dépasser.  Pour le **remplissage par
autoloading** (depuis le 26/10/2026), la case signifie aussi : la
dernière piste du bloc peut dépasser la **fin de l'émission** - en
entier si l'émission suivante a « Allow delayed start », sinon
coupée à la fin si au moins la moitié passe.  Pour un bloc
d'épisodes (« limit: 1 item »), la case n'est nécessaire que devant
une émission qui doit commencer à l'heure ; voir [Autoloading
Playlists](./AUTOLOADING_PLAYLISTS.md) §4.

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
Au lieu de glisser, vous pouvez aussi sélectionner des items et
cliquer **Add to current playlist** dans la barre d'outils de la
bibliothèque, ou choisir **Add to Playlist** dans le menu contextuel
d'une ligne (titres, smart blocks, flux web, entrées ligne ; depuis le
2026-10-21).  Les deux visent l'onglet d'édition actif ; si **Scheduled
Shows** est actif, le bouton ajoute à l'émission à la place.

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

### Supprimer une playlist encore utilisée par des émissions (depuis le 28/10/2026)

Quand vous supprimez une playlist de la bibliothèque, RASTATIME vérifie
d'abord quelles émissions l'utilisent comme playlist **autoloading**,
**intro** ou **outro**, et si elle est l'intro / l'outro par défaut de la
station (Settings → General).  La question de suppression liste ces
émissions.  Si vous confirmez, les émissions perdent la playlist **et**
leur case *Add Autoloading Playlist* est décochée, pour que le
calendrier montre l'état réel plutôt qu'une émission qui paraît remplie
et reste silencieuse.  Choisissez ensuite une autre playlist dans le
dialogue de l'émission.  Avant le 28/10/2026 la case restait cochée et
l'émission vide ; le tableau de bord avertit désormais aussi de telles
émissions jusqu'à 48 heures à l'avance (voir
[Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md), section 7).

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
| **Modifier** | Une piste sélectionnée : son onglet d'édition, comme avant. **Deux pistes ou plus sélectionnées (depuis le 2026-10-08) : un seul dialogue pour toutes** - créateur, album, genre, année, type de piste, langue, mood, label, compositeur, chef d'orchestre, copyright, date d'expiration (`none` l'efface), description. Les champs vides restent inchangés, un champ rempli est écrit dans chaque piste sélectionnée ; titre, numéro de piste, BPM, points de repère et pochette restent par piste. Base de données seulement, comme l'éditeur simple (les tags dans les fichiers sont lus à l'import et jamais réécrits). Les pistes que vous ne pouvez pas modifier sont ignorées et comptées dans le résultat. |
| **Transférer le propriétaire** | Réassigner la propriété (Admins seulement). Utilisé quand un DJ part et que ses fichiers doivent passer au compte de la station. |
| **Cue Points** | Détecte les points de repère des pistes sélectionnées à partir de l'audio (la même détection de silence que l'analyseur exécute à l'import : moins de −60 dB pendant au moins 0,3 s au début ou à la fin) et les enregistre. Les émissions à venir qui programment ces pistes reprennent les nouvelles valeurs et sont recalculées. Les pistes de plus de 15 minutes sont ignorées - l'action est prévue pour les jingles et autres éléments courts. Depuis le 30/09/2026. |
| **Relire les tags** *(depuis le 2026-10-21)* | Relit les tags des pistes sélectionnées depuis les fichiers sur le disque - pour les fichiers que vous avez modifiés dans Windows après l'import.  RASTATIME ne relit jamais un fichier de lui-même : la base de données est la vérité pour la bibliothèque et le playout.  Le bouton remplace titre, artiste, album, genre, année, numéro de piste, compositeur, copyright, label, ISRC, BPM, humeur, langue et commentaire par le contenu du fichier (un tag absent du fichier vide la colonne) et met à jour la somme de contrôle et la taille ; tout ce qui est défini uniquement dans RASTATIME (type de piste, teaser, points de repère, sonie, expiration, demandes) est conservé.  Administrateurs et responsables de programme pour chaque fichier, les autres pour les leurs.  Le fichier est seulement lu, une piste à l'antenne ne risque rien - mais ne modifiez un fichier dans Windows que s'il n'est pas programmé, le playout lit directement la bibliothèque. |

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

> **Téléversements échoués (depuis le 28/10/2026).**  Le filtre de la page
> d'envoi affiche **Failed (N)** dès qu'un envoi a échoué, et la ligne dit
> *pourquoi* (la raison de l'analyzer, p. ex. « ffprobe could not read the
> file »).  **Download** fournit l'original tel qu'il a été envoyé, pour
> l'examiner ou le réparer ; **Clear** supprime la ligne avec l'original
> que l'analyzer conserve dans `organize/` pour les imports échoués.  Le
> tableau de bord avertit quand des envois échoués de plus d'une heure
> attendent ou quand des fichiers de plus d'un jour restent dans
> `organize/`.  Un type de dégât est réparé automatiquement : un fichier
> WAV avec un bloc de tags ID3 devant son en-tête RIFF est dégagé et
> importé.

### "J'ai téléversé un fichier WAV et la bibliothèque affiche un MP3."

C'est voulu : les fichiers sans perte sont convertis en MP3 320 kbit/s
à l'import (section 2, *Formats de fichier à l'import*).  Pour garder
un fichier sans perte, désactivez Paramètres → **Machine locale** →
**Format d'import** avant de le téléverser.

### "Pourquoi mon smart block retourne-t-il les mêmes pistes à chaque fois ?"

Vous avez probablement choisi **Statique** au lieu de
**Dynamique**. Modifiez le block et changez le type ; le
prochain build re-requêtera.

### "Puis-je importer une structure de dossier en préservant les noms de sous-dossiers ?"

Le Dossier d'import local préserve les noms de
sous-dossiers comme champ **album** des pistes importées
si aucun tag ID3 album n'est défini. C'est le motif
opérateur le plus courant pour une archive musicale de
longue traîne.  Dans la bibliothèque le fichier est ensuite
rangé sous `imported/<artiste>/<album>/` ; un fichier sans tag
artiste va dans `imported/tagless/` (depuis le 2026-10-24).

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
