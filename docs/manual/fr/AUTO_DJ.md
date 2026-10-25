# Auto DJ

> **Où vous êtes dans le manuel.** Lisez d'abord
> [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) —
> Auto DJ est le pendant au niveau station de l'autoloading
> playlist par-émission. §8 de ce chapitre contient la
> comparaison côte à côte.

**Auto DJ** est le remplisseur d'arrière-plan qui maintient
la station à l'antenne pendant le temps non planifié par
l'opérateur. Il fonctionne en deux passages complémentaires,
les deux entièrement automatiques une fois activés :

1. **Pre-pass** — si la prochaine heure du calendrier
   contient un trou de plus de 60 secondes, crée une
   nouvelle émission dans le premier trou trouvé, nommée
   selon vos valeurs par défaut, avec la playlist Auto-DJ
   autoloaded.
2. **Fill-pass** (optionnel) — si une émission à venir
   finit plus de 5 s courte de son créneau après son
   build, complète la queue avec la playlist Auto-DJ.

Résultat : tant qu'Auto DJ est activé et pointe vers une
playlist saine, votre station ne tombe jamais en silence.

---

## 1. Pourquoi Auto DJ existe

Avant 2026-05-21, le fallback pour "pas d'émission
planifiée maintenant" était un fichier en boucle configuré
(silence par défaut). Cela couvrait "jamais d'émission",
mais un calendrier avec 80 % de couverture et 20 % de
trous jouait toujours du silence dans les trous.

Les deux motifs que l'opérateur rencontrait à répétition :

- L'émission du lundi matin se termine à 10:00 mais la
  prochaine émission commence à 14:00. Le trou de quatre
  heures jouait du silence fallback sur le stream public
  — mauvaise expérience d'auditeur.
- L'autoplaylist d'une émission de 60 minutes ne
  remplissait que 55 minutes (les smart blocks
  manquaient de pistes correspondantes) ; les 5 dernières
  minutes étaient du silence.

Auto DJ couvre les deux avec la même playlist configurée.

---

## 2. Activer Auto DJ

Paramètres → **Auto DJ**.

### Champs requis

| Champ | Notes |
|---|---|
| **Activé** | Interrupteur principal. Quand désactivé, aucun des deux passages ne tourne. |
| **Playlist par défaut** | La playlist qu'Auto DJ utilise pour remplir ses émissions et (si fill-pass activé) pour compléter les émissions incomplètes. Requise quand **Activé** est activé. |

### Forme de playlist recommandée

Utilisez une playlist qui contient exactement **un smart
block** avec :

- Type : **Dynamique** (ré-évalue à chaque cycle).
- Critères : un filtre généreux qui correspond à plusieurs
  centaines de pistes. "Type de piste = Musique" est une
  bonne base.
- **Limiter à : Temps restant dans l'émission**. C'est
  critique — les émissions créées par Auto-DJ ont une
  longueur variable selon le trou qu'elles remplissent
  (5 minutes à plusieurs heures), et le smart block doit
  remplir exactement le créneau qu'il obtient.
- Trier : **Aléatoire**.

### Champs optionnels

| Champ | Ce qu'Auto DJ en fait |
|---|---|
| **Nom d'émission** | Utilisé comme nom de l'émission auto-créée dans le calendrier. Par défaut `Auto DJ`. |
| **URL / Genre / Description** | Copié dans les métadonnées de chaque émission auto-créée. Visible dans l'export du planning public. |
| **Couleur de fond / texte** | Utilisé pour colorer les émissions auto-créées dans le calendrier — utile pour les distinguer des émissions planifiées par l'opérateur en un coup d'œil. |
| **Logo d'émission** | Logo par défaut pour les émissions auto-créées. Stocké comme blob base64 dans `cc_pref`. Limite d'upload 2 MB ; JPG / PNG / GIF / WebP. |
| **Remplir automatiquement toute émission** | Si activé, active le second passage (fill-pass). |

> **Comment ça marche sous le capot.** Les paramètres
> vivent dans la table `cc_pref` comme simples lignes
> clé/valeur (pas de changement de schéma) :
> `auto_dj_enabled`, `auto_dj_show_name`,
> `auto_dj_playlist_id`, `auto_dj_fill_any_show`,
> `auto_dj_logo_path`, plus URL/Genre/Description/Bg/
> Couleur texte. Le téléversement de logo utilise un POST
> multipart séparé vers `autoDjUploadLogoAction`. Le
> service PHP `Application_Service_AutoDjService` est
> invoqué depuis `AutoPlaylistManager.buildAutoPlaylist()`
> à une cadence de 60 s. Voir ARCHITECTURE §23.20.

---

## 3. Le pre-pass — remplissage de trous

Toutes les 60 secondes, Auto DJ scanne la prochaine heure
pour des trous de calendrier. Un **trou** est toute
plage contiguë où aucune émission n'est planifiée.

Pour le **premier** trou de plus de 60 secondes dont le
début est dans la prochaine heure :

1. Créer une nouvelle ligne `cc_show` avec les valeurs par
   défaut configurées (nom, couleurs, URL, etc.).
2. Insérer une ligne `cc_show_days` avec le fuseau horaire
   local de l'opérateur et les heures arrondies (début
   arrondi vers le HAUT à la prochaine minute, fin arrondie
   vers le BAS à la minute précédente).
3. Insérer une ligne `cc_show_instances` pour la même plage.
4. Attacher la playlist Auto-DJ configurée comme
   autoloading.

La nouvelle émission est alors prise par le **même** cycle
de poll dans la boucle body et construite. Donc un tic de
5 minutes après que l'opérateur a supprimé une émission
qui laisse un trou d'une heure, Auto DJ l'a déjà remplacé
par une émission Auto-DJ et l'a remplie.

### Pourquoi seulement une émission par cycle ?

Le pre-pass crée **une** émission par cycle de 60 s, même
si plusieurs trous existent. C'est intentionnel :

- Après qu'une émission est créée, le prochain trou bouge.
  Le cycle ré-évalue.
- Un opérateur qui réarrange activement le calendrier ne
  devrait pas voir dix émissions Auto-DJ se matérialiser
  plus vite qu'il ne peut réagir.
- Un-à-la-fois correspond à la cadence naturelle de la
  planification humaine.

### Les heures d'émission sont arrondies à la minute

Les émissions créées par Auto-DJ commencent toujours sur
une limite de minute (arrondies *vers le haut* depuis le
début du trou) et finissent sur une limite de minute
(arrondies *vers le bas* depuis la fin du trou). C'est
pour deux raisons :

- Le formulaire Modifier l'émission de l'opérateur
  n'affiche pas proprement les horodatages de
  sous-minute, ce qui a mené à une erreur
  "Cannot schedule overlapping shows" quand l'opérateur
  ouvrait une émission Auto-DJ avec un début 14:00:30.
  RASTATIME 2026-05-21 arrondit à la création pour éviter
  la confusion.
- Un alignement de minute cohérent correspond aux attentes
  des opérateurs pour les émissions planifiées.

---

## 4. Le fill-pass — compléter les émissions incomplètes

Optionnel, opt-in via **Remplir automatiquement toute
émission incomplète après le build d'autoplaylist**.

Tous les cycles de 60 s, après le pre-pass + les builds
body d'autoplaylist normaux, le fill-pass parcourt chaque
émission à venir dont la queue a fini plus de 5 secondes
courte de son créneau. Pour chacune, il ajoute la playlist
Auto-DJ à la fin pour compléter le créneau.

Raisons courantes pour lesquelles une émission finit
courte :

- Les smart blocks de son autoplaylist ont manqué de
  pistes correspondantes.
- L'autoplaylist n'avait pas de smart block "temps
  restant", juste un nombre fixe d'items.
- L'opérateur a oublié d'attacher une autoplaylist tout
  court.

### Pourquoi 5 secondes et pas un seuil plus strict ?

La réserve d'outro (voir
[Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) §4)
laisse intentionnellement jusqu'à 5 s de jeu pour que
l'auto-build ne déborde pas. Resserrer le seuil de
fill-pass à par exemple 1 s compléterait constamment les
émissions qui étaient déjà optimalement remplies —
gaspilleur et ennuyeux.

### Le fill-pass ne modifie jamais la définition d'émission

Le fill-pass n'insère que des **items de planning** dans
l'instance existante. Il ne change pas le nom, les
animateurs, l'attachement d'autoplaylist ou tout autre
champ de définition de l'émission. L'intention de
l'opérateur pour l'émission reste intacte ; seule la
queue vide est remplie.

---

## 5. Émissions créées par Auto-DJ dans le calendrier

Les émissions créées par Auto-DJ ressemblent à n'importe
quelle autre émission, avec l'indice visuel de la couleur
de fond configurée (typiquement plus sombre que les
émissions planifiées par l'opérateur).

| Action | Autorisée sur émissions Auto-DJ ? |
|---|---|
| **Voir** | Oui |
| **Modifier l'émission** | Oui — mais soyez conscient que la modification se fait sur l'émission auto-créée, pas sur les valeurs par défaut Auto-DJ. Pour changer les valeurs par défaut, utilisez Paramètres → Auto DJ. |
| **Planifier les pistes** | Oui — ajouter / remplacer des items comme sur n'importe quelle émission. |
| **Annuler l'émission** | Oui (émission actuelle seulement). |
| **Supprimer l'émission** | Oui. Après suppression, le trou réapparaît et Auto DJ peut le re-remplir au cycle suivant. |

> **Conseil opérateur.** Si vous voulez **empêcher**
> Auto DJ de re-remplir un trou (ex. vous voulez 30
> minutes de silence pour un hommage), créez une émission
> vide ponctuelle explicite sans autoloading playlist sur
> ce trou. Auto DJ ne touche jamais aux émissions
> existantes pour le pre-pass, seulement aux trous.

---

## 6. Désactiver Auto DJ

Paramètres → Auto DJ → décocher **Activé** →
**Enregistrer**.

Effets :

- Le pre-pass arrête de créer de nouvelles émissions. Les
  émissions Auto-DJ déjà créées restent dans le
  calendrier.
- Le fill-pass arrête de compléter les émissions
  incomplètes.

Pour retirer en masse les émissions Auto-DJ déjà créées,
utilisez Actions en masse → **Supprimer les émissions
sélectionnées** sur le Calendrier.

---

## 7. Foire aux questions

### "Auto DJ ne crée aucune émission."

Vérifiez dans cet ordre :

1. **Activé** est coché et **Enregistrer** cliqué.
2. **Playlist par défaut** est définie sur une playlist
   non vide.
3. La fenêtre de la prochaine heure contient effectivement
   un trou > 60 s. Si la prochaine heure est entièrement
   réservée, le pre-pass est correctement un no-op.
4. Le service **RASTATIME-WORKER** tourne
   (`Get-Service RASTATIME-WORKER`).
5. Les smart blocks de la playlist configurée renvoient
   au moins une piste correspondante. Une sélection vide
   produit un build vide.

### "Auto DJ a créé 17 minuscules émissions sur un long trou."

C'était une régression en v4 (Section 23.20). Corrigé
depuis RASTATIME 2026-05-21 : le pre-pass requête jusqu'à
200 instances à venir et ne requiert que le *début* du
trou (pas la *fin*) à l'intérieur de la fenêtre
lookahead.

### "Les émissions Auto-DJ affichent le mauvais fuseau horaire dans le dialogue d'édition."

C'était une régression en v5 (Section 23.20). RASTATIME
stocke l'heure locale de l'émission + le fuseau local de
l'opérateur dans `cc_show_days.timezone`. Corrigé le
2026-05-21.

### "Auto DJ peut-il utiliser différentes playlists pour différents moments de la journée ?"

Pas directement. La playlist Auto-DJ est un choix unique
au niveau station. Solution de contournement : utilisez
des tags sur les pistes et changez le filtre du
smart-block selon le moment de la journée (manuellement,
hebdomadairement).

### "Auto DJ honore-t-il le fill-pass par-émission différemment ?"

Non — le fill-pass est au niveau station. Soit chaque
émission incomplète reçoit la complétion, soit aucune.

---

## 8. Profil Auto-DJ recommandé pour nouvelles stations

| Paramètre | Valeur |
|---|---|
| **Activé** | Désactivé (tout configurer d'abord, puis activer) |
| **Playlist par défaut** | Une playlist nommée "Auto DJ" contenant un smart block : type Dynamique, critères "Type de piste = Musique", limite "Temps restant dans l'émission", trier Aléatoire |
| **Nom d'émission** | `Auto DJ` |
| **Couleur de fond** | `222222` (gris foncé) |
| **Couleur de texte** | `ffffff` |
| **Remplir automatiquement** | Désactivé (activer plus tard une fois que vous faites confiance à la playlist) |

Puis activer, observer le calendrier pendant une journée
complète et ajuster.

---

## Où aller ensuite

* [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) —
  le pendant par-émission.
* [Bibliothèque](./LIBRARY.md) → Smart Blocks — primitive
  la plus utile pour la playlist Auto-DJ.
* [Calendrier](./CALENDAR.md) — où les émissions Auto-DJ
  apparaissent.
