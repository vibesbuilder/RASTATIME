# Demandes de titres (Song Requests)

> **Où vous êtes dans le manuel.** Lisez d'abord
> [Bibliothèque](./LIBRARY.md) → §3 Smart Blocks et
> [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) — les Song
> Requests sont entièrement construites à partir de ces deux
> primitives plus un widget public pour les auditeurs. Aucun nouveau
> type d'objet « request » n'est introduit.

Les **Song Requests** permettent à vos auditeurs de demander des
titres depuis un widget web public, et de faire passer ces titres
automatiquement dans une émission normale — sans qu'un animateur ait à
cliquer. La fonctionnalité entière est assemblée à partir d'éléments
que vous connaissez déjà :

- un **Smart Block** marqué *Use requests* tire les titres réellement
  demandés par les auditeurs ;
- une **Autoloading Playlist** contenant ce bloc transforme une
  émission ordinaire en **émission à demandes** (request show) ;
- un petit **widget d'intégration** sur votre site public collecte les
  demandes.

Il n'y a pas d'interrupteur « accepte les demandes » par émission ni de
file de modération séparée. Une émission *est* une request show
lorsque son Autoloading Playlist contient un bloc *Use requests* —
rien d'autre.

---

## 1. Vue d'ensemble

```
   AUDITEUR                 RASTATIME                     À L'ANTENNE
   ┌─────────┐   demande    ┌──────────────────────┐
   │ Widget  │─────────────▶│ rastatime_song_request│
   │ (iframe)│   /api/v2    │  status = pending     │
   └─────────┘              │ cc_files.requested=t  │
                            └──────────┬────────────┘
                                       │  la request show se remplit
                                       │  ~8 min avant le début
                            ┌──────────▼────────────┐   ┌──────────┐
                            │ bloc « Use requests »  │──▶│ Émission │
                            │  tire les pending,      │   │ planning │
                            │  + ancien d'abord, 1 ch.│   └──────────┘
                            └────────────────────────┘
```

Deux moitiés indépendantes se rejoignent au milieu :

1. Les **auditeurs** ouvrent le widget, voient le catalogue des titres
   demandables et envoient une demande. La demande est enregistrée et
   le titre marqué comme « voulu ».
2. Une **request show** — toute émission dont l'Autoloading Playlist
   contient un Smart Block *Use requests* — se remplit à partir de ces
   titres voulus quelques minutes avant la diffusion.

Les deux moitiés ne sont liées que par le **pool** de demandes (§2) et
le critère *Use requests* (§3). Vous configurez les deux une fois ;
ensuite la fonctionnalité tourne sans surveillance.

---

## 2. Le pool de demandes — ce que les auditeurs peuvent demander

Le **pool** est le catalogue des titres qu'un auditeur a le droit de
demander. Il est défini par un ou plusieurs Smart Blocks.

Ouvrez **Settings → General → Song-Request Pool (Smart Blocks)**. Le
champ est une liste déroulante au style du sélecteur *Columns* de la
Bibliothèque : cliquez sur **Smart Blocks**, cochez un ou plusieurs
blocs, cliquez ailleurs pour fermer.

```
   Song-Request Pool (smart blocks)   [ Smart Blocks ▾ ]
                                      ┌────────────────────┐
                                      │ ☑ Pool Indie / Alt │
                                      │ ☐ Jingles          │
                                      │ ☑ Catalogue demand.│
                                      │ …                  │
                                      └────────────────────┘
```

Le pool est l'**union** du catalogue de chaque bloc coché — les titres
correspondant aux critères de chaque bloc (genre, album, …),
*indépendamment* du fait qu'ils aient déjà été demandés. N'en cochez
aucun pour désactiver entièrement les demandes : le widget affiche
alors « actuellement indisponible ».

> **Comment ça marche en coulisses.** Une tâche d'arrière-plan
> (`RequestablePoolSyncTask`, toutes les 5 min) développe l'union des
> blocs sélectionnés avec le filtre de demande *ignoré* et écrit
> `cc_files.requestable = true` pour chaque membre, l'effaçant partout
> ailleurs. Le point de terminaison public de recherche du catalogue
> filtre sur ce drapeau. Les identifiants des blocs sélectionnés
> résident dans la clé cc_pref `requestable_pool_block_ids`.

---

## 3. Le Smart Block « Use requests »

Un Smart Block devient une **source de demandes** lorsque vous cochez
**Use requests** dans la boîte de dialogue Smart Block (Library →
modifier un Smart Block → critères avancés).

Cela change ce que le bloc tire :

| État | Ce que le bloc sélectionne |
|---|---|
| **Use requests OFF** (normal) | Tous les titres correspondant à ses critères (genre, album, …). |
| **Use requests ON** | Uniquement les titres correspondant à ses critères **et** ayant une demande ouverte (`cc_files.requested = true`). |

Deux ordres de tri sont disponibles et importent pour les blocs de
demandes :

- **Demande la plus ancienne d'abord** — file équitable : qui a
  demandé en premier passe en premier.
- **Plus demandé d'abord** — popularité : le titre avec le plus de
  demandes en attente passe en premier.

> **Conseil d'opérateur.** Le *même* bloc joue généralement les deux
> rôles : vous le sélectionnez comme **pool** dans Settings (ce qui
> utilise son catalogue, filtre de demande ignoré) *et* le placez dans
> la playlist d'une request show (où le critère *Use requests* lui fait
> tirer les demandes réelles). Gardez ses critères de catalogue (p. ex.
> `genre = Indie or Alternative`) raisonnables — ils limitent **les
> deux** : ce qui peut être demandé et ce qui est tiré.

---

## 4. Construire une request show

Une request show est simplement une émission à
[Autoloading Playlist](./AUTOLOADING_PLAYLISTS.md) dont la playlist
contient au moins un bloc *Use requests*. Vous composez la playlist
comme une **dramaturgie** — un ordre fixe que le remplissage parcourt
une fois :

```
   Autoloading Playlist « Heure des demandes »
   ────────────────────────────────────────────
   1. Smart Block · Use requests · 1 élément   ◀── demande A
   2. Smart Block · StationID    · 1 élément
   3. Smart Block · Use requests · 1 élément   ◀── demande B (différente !)
   4. Smart Block · StationID    · 1 élément
   5. Smart Block · Use requests · 1 élément   ◀── demande C (différente !)
   6. Smart Block · Musique · Limite « temps restant »  ◀── remplit le reste
```

Lorsque l'émission se remplit (§5), chaque créneau *Use requests* tire
une demande **différente**, et le bloc **« temps restant »** final
remplit le reste avec de la musique. Attachez la playlist à une
émission de la manière habituelle (**Modifier l'émission → Ajouter une
Autoloading Playlist ?**) — et cette émission est désormais une request
show.

> **Vous pouvez réutiliser un seul bloc.** Placer le *même* bloc *Use
> requests* aux positions 1, 3 et 5 fonctionne — le remplissage résout
> chaque position séparément, donc trois placements tirent trois
> demandes différentes. Vous n'avez pas besoin de trois blocs séparés.

> **Pourquoi un bloc « temps restant » final.** Sans un bloc qui
> remplit le reste, une request show avec seulement quelques demandes
> laisserait un silence après la dernière demande. Le bloc musical
> « temps restant » est le filet de sécurité. Donnez-lui **Répéter les
> titres = oui** (ou un catalogue assez grand) pour qu'il remplisse
> tout le reste en une passe ; avec « répéter désactivé », il remplit
> avec autant de variété que son pool le permet et peut laisser un
> petit trou que le fallback du playout couvre.

---

## 5. Comment et quand une request show se remplit

Une request show est remplie **une fois, quelques minutes avant son
début** — pas titre par titre pendant sa diffusion.

- Une tâche d'arrière-plan (`RequestShowFillTask`, toutes les 2 min)
  cherche les request shows commençant dans les **8 minutes**
  suivantes (le *lead*).
- Elle remplit l'émission en parcourant la playlist **position par
  position**, résolvant un créneau à la fois. Après chaque créneau,
  elle retire la demande tirée du pool, de sorte que le créneau *Use
  requests* **suivant** tire un autre titre.
- Le bloc « temps restant » final remplit le reste.
- Une émission entièrement remplie est laissée intacte lors des
  passages suivants.

Ce remplissage en une passe est **sûr contre le silence** : l'émission
est complète bien avant sa diffusion. Le compromis — choisi
délibérément — est qu'une demande arrivant *après* le remplissage
(moins de ~8 min avant le début, ou pendant que l'émission est déjà à
l'antenne) atterrit dans la request show **suivante**, pas l'actuelle.

> **Créneau de demande vide → titre aléatoire.** Si un créneau *Use
> requests* n'a aucune demande en attente au moment du remplissage, il
> ne laisse **pas** de trou. Il diffuse un titre **aléatoire** du
> propre catalogue de ce bloc (son genre / ses critères, filtre de
> demande ignoré). Ainsi, une request show sans aucune demande
> diffuse quand même une heure normale et conforme au format ; à
> mesure que les demandes arrivent, elles remplacent les choix
> aléatoires créneau par créneau.

> **Comment ça marche en coulisses.** `AutoPlaylistManager::`
> `fillRequestShows()` (lead `RASTATIME_REQUEST_FILL_LEAD_SECONDS`,
> défaut 480) parcourt `cc_playlistcontents` dans l'ordre, ajoute
> chaque fichier/bloc avec `addAutoloadItemToShow()` et exécute l'étape
> de consommation entre les créneaux. Le constructeur d'autoplaylist
> normal (§ Autoloading Playlists) ignore délibérément les request
> shows pour que les deux n'entrent jamais en conflit. Voir
> ARCHITECTURE §23.23.

---

## 6. Le widget pour les auditeurs

Le widget public se trouve à :

```
   http://<votre-station>/Embed/song-request
   http://<votre-station>/Embed/song-request?theme=dark
```

Intégrez-le dans une `<iframe>` sur votre site (thèmes : `light`,
`dark`, `auto`). Il affiche un tableau défilant de chaque titre
demandable — pochette · artiste / titre · un bouton **Request** — sans
champ de recherche ni pagination :

```
   ┌──────────────────────────────────────────────┐
   │ [poch.] Robb — Down with It          [Request]│
   │ [poch.] Leyya — Butter               [Request]│
   │         Viech — Steuermann           [Request]│
   │ …                                             │
   └──────────────────────────────────────────────┘
```

Un clic envoie la demande et affiche une ligne de statut : merci,
« déjà demandé récemment » ou « limite de demandes atteinte ».

Garde-fous intégrés (aucune file de modération nécessaire) :

| Garde-fou | Défaut |
|---|---|
| **Limite de débit** | 5 demandes par heure par auditeur |
| **Déduplication** | le même auditeur ne peut pas re-demander le même titre en moins de 30 min |
| **Restriction au catalogue** | seuls les titres du pool (§2) sont listables / demandables |

> **Les pochettes nécessitent l'API tierce.** Les vignettes de
> pochette proviennent du point de terminaison d'illustration, protégé
> par **Settings → … → Allow 3rd party API**. Désactivé, le tableau
> s'affiche en texte seul (artiste / titre), ce qui reste parfaitement
> utilisable. Les titres sans illustration restent également en texte
> seul.

> **Comment ça marche en coulisses.** Le widget est une page iframe
> autonome en JS vanilla (`/Embed/song-request`) dialoguant avec deux
> points de terminaison Django publics : `GET
> /api/v2/song-requests/search` (le catalogue) et `POST
> /api/v2/song-requests` (envoi). Pas de connexion, pas de cookie.
> L'IP brute de l'auditeur n'est jamais stockée — seulement un hachage
> salé, utilisé pour la limite de débit et la déduplication.

---

## 7. Le cycle de vie d'une demande

Chaque demande passe par quatre états :

| État | Défini quand | Signification |
|---|---|---|
| **pending** | l'auditeur l'envoie | en attente dans le pool d'être tirée |
| **queued** | le remplissage planifie son titre | tirée dans une émission ; hors du pool |
| **played** | le titre est passé | terminé (conservé pour l'historique) |
| **expired** | TTL dépassé sans diffusion | jamais tirée ; balayée du pool |

- Quand une demande est **planifiée**, son titre quitte le pool
  (`cc_files.requested` effacé) pour que le créneau suivant tire autre
  chose, et la demande devient **queued**.
- Une tâche basée sur le planning marque **played** une fois le
  créneau du titre passé (`RequestPlayedTask`, toutes les 2 min) —
  choisi plutôt qu'un hook côté playout, afin de ne jamais toucher au
  chemin de diffusion en direct.
- Si un **request show est supprimé** avant la diffusion de ses titres,
  ses demandes planifiées ne sont pas perdues : le même balayage les
  remet en **pending** (leur titre n'est plus dans aucun planning),
  pour que le prochain request show réessaie le souhait.
- Le balayage d'expiration (`RequestExpiryTask`, toutes les 10 min)
  fait expirer toute demande encore **pending** après le TTL — défaut
  **8 heures**, surchargeable avec `RASTATIME_REQUEST_EXPIRY_HOURS` —
  et recalcule l'agrégat du pool afin qu'un titre dont la dernière
  demande a expiré sorte proprement du catalogue.

---

## 8. Liste de contrôle de l'opérateur

Pour mettre en place les Song Requests à partir de zéro :

1. **Créez un Smart Block de demandes.** Library → nouveau Smart Block
   → définissez ses critères de catalogue (p. ex. `genre = Indie or
   Alternative`), cochez **Use requests**, choisissez **Tri : Demande
   la plus ancienne d'abord**, **Limite : 1 élément**. Enregistrez.
2. **Sélectionnez-le comme pool.** Settings → General → **Song-Request
   Pool** → cochez le bloc. (Sous 5 min, ses titres deviennent
   demandables.)
3. **Composez la playlist de dramaturgie** (§4) : votre bloc de
   demandes à quelques positions, jingles/IDs entre, un bloc musical
   **« temps restant »** en dernier (avec **Répéter les titres = oui**).
4. **Attachez-la à une émission** comme Autoloading Playlist (§4).
5. **Intégrez le widget** (§6) sur votre site, activez éventuellement
   **Allow 3rd party API** pour les pochettes.

C'est toute la configuration. Dès lors, les auditeurs demandent et
l'émission se remplit ~8 min avant chaque diffusion.

---

## 9. Questions fréquentes

### « Le widget n'affiche aucun titre. »

Le pool est vide. Soit aucun bloc n'est sélectionné dans **Settings →
Song-Request Pool**, soit les critères du bloc sélectionné ne
correspondent à rien, soit la synchro du pool (5 min) n'a pas encore
tourné. Vérifiez que le bloc affiche des titres dans la Library ;
attendez un cycle de synchro.

### « Ma request show est passée mais n'a joué aucun titre demandé. »

Très probablement, il n'y avait aucune demande *ouverte* au moment du
remplissage (plus de ~8 min avant le début), donc chaque créneau *Use
requests* est retombé sur un titre aléatoire du catalogue (§5).
Envoyez quelques demandes et observez la request show *suivante*.
Vérifiez aussi que le bloc de demandes de la playlist a **Use
requests** coché et que ses critères correspondent au genre des titres
demandés.

### « Plusieurs créneaux de demandes ont joué le même titre. »

Cela ne devrait pas arriver — le remplissage consomme chaque demande
en la planifiant, donc les créneaux successifs tirent des titres
différents. Si vous voyez des doublons, la playlist ajoute
probablement la playlist *entière* de façon répétée (ancien
comportement) ; assurez-vous d'être sur une build à remplissage
position par position (ARCHITECTURE §23.23).

### « Il y a du silence à la fin d'une request show. »

Le bloc « temps restant » final a manqué de titres éligibles.
Donnez-lui **Répéter les titres = oui**, élargissez ses critères de
genre, ou assouplissez une fenêtre « exclure les artistes récemment
diffusés » pour qu'il puisse remplir tout le reste.

### « Des demandes arrivent après le début de l'émission — passent-elles ? »

Pas dans cette émission. Le remplissage est unique, ~8 min avant le
début (décision de l'opérateur : sécurité anti-silence plutôt
qu'insertion en cours d'émission). Les demandes tardives passent dans
la request show suivante.

### « Puis-je modérer les demandes avant diffusion ? »

Il n'y a délibérément pas de file de modération. Les garde-fous sont
la restriction au pool (uniquement les titres du catalogue), la limite
de débit et la fenêtre de déduplication (§6). Pour un contrôle plus
strict, resserrez les critères du bloc du pool.

---

## Où aller ensuite

* [Bibliothèque](./LIBRARY.md) → §3 Smart Blocks — le critère *Use
  requests* et les ordres de tri sont ici.
* [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) — la playlist de
  dramaturgie et son bloc « temps restant » final.
* [Widgets d'intégration publics](./WIDGETS.md) — intégrer le widget de
  demandes à côté des autres widgets publics.
* [Paramètres](./SETTINGS.md) — le sélecteur Song-Request Pool et
  l'interrupteur Allow 3rd party API.
