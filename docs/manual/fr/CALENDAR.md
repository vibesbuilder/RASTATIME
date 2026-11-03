# Calendrier

> **Où vous êtes dans le manuel.** C'est l'un des chapitres
> **Opération de diffusion quotidienne**. Beaucoup d'autres
> chapitres se terminent par "glissez depuis la bibliothèque
> sur une émission dans le calendrier" — ce chapitre
> explique le côté récepteur. Lisez d'abord
> [Bibliothèque](./LIBRARY.md) si ce n'est pas déjà fait.

Le **Calendrier** est l'endroit où vous planifiez ce qui
passe à l'antenne. Chaque créneau de temps d'antenne est
soit :

- Une **émission** que vous avez placée sur le calendrier,
  soit
- Du temps d'antenne que l'[Auto DJ](./AUTO_DJ.md) remplit
  (si activé), soit
- Le fallback configuré / silence (quand aucun des deux ne
  s'applique).

Ce chapitre couvre tout ce que vous pouvez faire *avec* le
calendrier. Ce qui se joue *à l'intérieur* d'une émission
— pistes, smart blocks, playlists — est couvert dans
[Bibliothèque](./LIBRARY.md) et les chapitres par
fonctionnalité.

---

## 1. La page Calendrier

Calendrier → ouvre la vue semaine par défaut.

```
  ┌──────────────────────────────────────────────────────────────────────┐
  │  ◀ Aujourd'hui ▶        18-24 mai 2026          [jour][sem.][mois]  │
  ├──────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┤
  │      │   Lun 18 │   Mar 19 │   Mer 20 │   Jeu 21 │   Ven 22 │   Sam 23 │
  ├──────┼──────────┼──────────┼──────────┼──────────┼──────────┼──────────┤
  │ 08   │■ Matinale■        │■ Matinale │■ Matinale │■ Matinale │          │
  │      │■         ■        │■          │■          │■          │          │
  │ 09   │           │           │           │           │           │          │
  │ 10   │■ Music    │           │           │■ Info     │■ Music    │          │
  │      │■ Hour     │           │           │■          │■ Hour     │          │
  │ 11   │           │           │           │           │           │          │
  └──────┴──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘
```

### Changer de vue

| Bouton | Ce que vous voyez |
|---|---|
| **Jour** | Un jour, lignes d'heures, grands espaces pour les créneaux vides. Le mieux pour la planification "qu'est-ce qui passe aujourd'hui". |
| **Semaine** | Sept jours, par défaut. Le mieux pour la planification de programme hebdomadaire. |
| **Mois** | Une grille mensuelle, émissions affichées comme barres colorées à travers les jours. Le mieux pour la vue d'ensemble "la semaine de X est-elle pleine ?". |

Les boutons fléchés avancent par la plage visible (un jour
/ une semaine / un mois à la fois). Le bouton
**Aujourd'hui** revient à la période actuelle.

Une émission qui dépasse minuit apparaît en deux parties dans les
vues jour et semaine, une sur chaque jour. Les deux parties
affichent l'horaire complet de l'émission (p. ex. *23:08 - 0:08*),
et non la portion qui tombe sur ce jour.

### Ce que les couleurs signifient

Chaque émission porte sa propre couleur de fond et couleur
de texte (définies sur le formulaire d'édition de
l'émission). Utilisez ceci pour :

- Distinguer les émissions récurrentes des ponctuelles
  (ex. toutes les émissions récurrentes sur fond sombre).
- Mettre en évidence les programmes par genre (info =
  rouge, musique = bleu, communauté = vert).
- Marquer la programmation spéciale (live à distance =
  jaune).

La couleur n'a aucune signification fonctionnelle — elle
est purement visuelle.

### La barre de remplissage par émission

À l'intérieur de chaque bloc d'émission se trouve une
fine barre horizontale en bas. Elle montre le **niveau de
remplissage** — quel pourcentage de la durée de l'émission
est réellement planifié.

| Barre de remplissage | Signification |
|---|---|
| (vide) | 0 % planifié — l'émission tombe sur fallback / silence |
| À moitié pleine | Environ la moitié de la durée est planifiée |
| Pleine | 100 % — chaque seconde de l'émission a du contenu |
| Pointe rouge solide | Plus de 100 % — des items auraient dépassé la fin du créneau et ont été coupés |

> **Conseil opérateur.** La barre de remplissage se met à
> jour automatiquement toutes les 60 secondes, donc quand
> une [Autoloading Playlist](./AUTOLOADING_PLAYLISTS.md)
> construit une émission en arrière-plan, vous pouvez
> regarder la barre passer de vide à pleine sans recharger
> la page. Avant 2026-05-20, vous deviez recharger
> manuellement ; corrigé dans le commit 9484db6.

> **Comment ça marche sous le capot.** Le pourcentage de la
> barre est `cc_show_instances.time_filled /
> (ends_at − starts_at)` × 100, récupéré via l'endpoint
> JSON `/Schedule/event-feed`. Le rafraîchissement de
> 60 s est `setInterval(refetchEvents, 60_000)` dans
> `full-calendar-functions.js`, gardé par
> `$cal.is(":visible")` pour que le poll AJAX se mette en
> pause quand l'opérateur est sur un autre onglet.

> Depuis le 2026-10-06, `time_filled` est la longueur mise en page (du
> début de l'émission à la fin de la dernière ligne, chevauchements de
> crossfade compris) : une émission que la barre montre pleine l'est
> vraiment.

---

## 2. Créer une émission

Deux routes :

### 2.1 Depuis la grille du calendrier

Cliquez sur n'importe quelle cellule vide du calendrier.

- Un clic simple sur une cellule en vue **semaine** ou
  **jour** ouvre **Nouvelle émission** à cette heure.
- Un clic simple sur un jour en vue **mois** ouvre
  **Nouvelle émission** à 09:00 ce jour-là.
- Clic droit sur n'importe quelle cellule vide affiche un
  menu contextuel avec **Nouvelle émission** + **Appliquer
  un modèle**.

### 2.2 Depuis la barre d'outils

Calendrier → **+ Nouvelle émission** en haut à droite de
la page. Par défaut "maintenant + 1 heure" avec 60 minutes
de durée.

### Le formulaire Nouvelle émission

Le formulaire est divisé en sections repliables. **Quoi**
et **Quand** sont obligatoires ; le reste peut rester aux
valeurs par défaut.

| Section | But |
|---|---|
| **Modèles** | Pré-remplir le formulaire depuis un [Modèle d'émission](./SHOW_TEMPLATES.md) enregistré, ou enregistrer le formulaire actuel comme modèle après avoir terminé. Caché lors de l'édition d'une seule instance d'une émission récurrente. |
| **Quoi** | Nom, URL, genre, description, animateurs, couleurs de fond / texte, image de l'émission. Le libellé visible sur le calendrier. |
| **Quand** | Date / heure de début, durée, date de fin, répétitions, **Autoriser le démarrage différé** (laisser cette émission commencer en retard quand la précédente a dépassé — voir [Démarrage différé d'émission](./DELAYED_START.md)). |
| **Entrée Live Stream** | Permettre aux animateurs distants de prendre l'émission via Show DJ (nom d'utilisateur + mot de passe par émission). |
| **Enregistrement** | Cocher pour enregistrer la sortie à l'antenne de l'émission dans un fichier. Voir [Enregistrement par émission](./RECORD_PER_SHOW.md). |
| **Own production** (production propre) | Cocher pour les productions propres de la station : les minutes diffusées de l'émission comptent dans Analytics → [Rapport annuel](./ANALYTICS.md) (depuis le 2026-11-03). |
| **Autoloading Playlist** | Attacher une playlist pour remplir chaque instance automatiquement. Voir [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md). |
| **Qui** | Animateurs supplémentaires au-delà du principal défini sous Quoi. |
| **Archivage** | Équipe de rédaction, participants, compte CBA, réglages cba.media et archivage automatique de l'émission (pas dans Modifier l'occurrence). Voir [Archivage](./ARCHIVING.md). Depuis le 2026-11-03. |
| **Style** | Couleur de fond, couleur de texte, image d'émission (visible seulement ici pour les émissions ponctuelles ; pour les émissions récurrentes, celles-ci restent constantes à travers les instances). |

> **Conseil opérateur.** Si vous êtes sur le point de
> remplir le même nom, animateurs, couleurs et autoloading
> playlist que la semaine dernière, arrêtez et vérifiez
> d'abord le menu déroulant **Modèles**. Si le modèle
> existe, le choisir pré-remplit six des sept sections en
> un clic. S'il n'existe pas, créez-le maintenant via le
> bouton **Enregistrer comme modèle** au bas de la
> section.

### Pourquoi le formulaire rejette votre enregistrement

Raisons courantes :

| Erreur | Cause |
|---|---|
| "Cannot schedule overlapping shows." | Une autre émission occupe déjà une ou plusieurs secondes du créneau. RASTATIME n'autorise pas les émissions qui se chevauchent. |
| "Start time must be in the future." | Les émissions ponctuelles doivent commencer au moins 1 minute à partir de maintenant. |
| "End time must be after start time." | Auto-explicatif ; vérifiez la durée et la date de fin. |
| "You are not allowed to schedule show *X*." | Vous avez voulu programmer du contenu dans une émission dont vous n'êtes pas animateur. Les DJ programment dans les émissions qu'ils animent ; les Program Managers et les Admins dans toutes. |

Si le formulaire rejette avec un toast générique "Save
failed" et aucun message par champ visible, vérifiez le
log opérateur (`C:\rastatime\logs\error.log`). RASTATIME
2026-05-17 a ajouté un logging diagnostic pour l'état
pass/fail des sous-formulaires, donc "validateShowForms
FALSE: what=1 when=0 …" devrait apparaître, pointant le
sous-formulaire fautif.

---

## 3. Modifier une émission existante

Cliquez sur l'émission → menu contextuel → choisissez une
action.

### Menu d'action

| Action | Effet | Disponible quand |
|---|---|---|
| **Planifier les pistes** | Ouvrir le show-builder pour ajouter / retirer / réordonner les items. | Toujours |
| **Appliquer un modèle** | Tamponner un [Modèle d'émission](./SHOW_TEMPLATES.md) sur cette émission ; remplace les champs du formulaire. | Émissions futures seulement |
| **Enregistrer comme modèle** | Enregistrer les paramètres actuels de l'émission comme nouveau modèle. | Toujours |
| **Voir** | Vue en lecture seule des métadonnées + planning de l'émission. *Start* et *Length* de chaque ligne sont la ligne de planning telle que posée (Length = cue-out moins cue-in, comme dans le show builder ; depuis le 2026-10-23) ; les totaux en bas sont la longueur posée du contenu (points de cue et chevauchements de crossfade compris) face à la durée de l'émission. | Toujours |
| **Teasers** | Les jingles qui annoncent cette émission - changer le type, retirer, en lier d'autres ; voir [Automatisation des teasers](./TEASERS.md). Depuis le 2026-10-16. | Admin / PM |
| **Archiver en ligne** | Titre, accroche, description, image et participants de cet épisode, avant ou après sa diffusion, et « Archiver en ligne maintenant » sur cba.media ; voir [Archivage](./ARCHIVING.md). Depuis le 2026-11-03 (d'abord nommé *Épisode...*). | Admin / PM / animateurs de l'émission (archiver : Admin / PM) |
| **Modifier l'émission** | Modifier la définition d'émission (nom, heure, répétitions, etc.). | Émissions futures ou actuelles |
| **Modifier l'instance** | Modifier seulement cette occurrence d'une émission récurrente. | Émissions récurrentes seulement |
| **Annuler l'émission** | Terminer l'émission *maintenant* — sensé seulement pour l'émission actuellement en cours. | Émission actuelle seulement |
| **Supprimer l'émission** | Retirer toute l'émission + toutes ses instances. | Émissions futures seulement |
| **Supprimer cette instance** | Retirer seulement cette occurrence d'une émission récurrente. | Émissions récurrentes, futures seulement |
| **Vider le planning** | Effacer le contenu planifié de l'émission mais garder le créneau vide. | Émissions futures seulement |

> **Pourquoi "Modifier l'émission" vs "Modifier
> l'instance".** Une émission hebdomadaire est une
> *définition* avec plusieurs *instances*. Modifier la
> définition change chaque instance future (ex. déplacer
> l'émission du lundi au mardi). Modifier une seule
> instance crée une surcharge par occurrence (ex. cette
> semaine seulement, l'animateur est différent). La
> surcharge d'instance survit à la prochaine édition de
> définition mais ne se propage pas aux frères et sœurs.

### Ce que "Modifier l'instance" ne peut pas faire

- Ne peut pas appliquer un Modèle d'émission. Les modèles
  s'appliquent seulement aux émissions entières parce que
  tamponner un modèle sur une instance se propagerait
  silencieusement aux frères et sœurs (violant le modèle
  de tampon unidirectionnel) ou n'aurait aucun effet sur
  eux (ce qui tromperait l'opérateur). RASTATIME
  2026-05-19 supprime la section Modèles dans le
  formulaire Modifier l'instance pour cette raison.
- Ne peut pas changer le début/fin de l'instance à un
  moment hors du motif de répétition de l'émission parent.

---

## 4. Émissions récurrentes

Une émission récurrente est une définition avec plusieurs
instances matérialisées avec empressement jusqu'à un
horizon configurable (par défaut ~3 mois).

### Créer une émission récurrente

Dans la section **Quand**, cochez **Se répète**. Trois
sous-champs apparaissent :

| Champ | Signification |
|---|---|
| **Type de répétition** | Hebdomadaire / Bihebdomadaire / Trihebdomadaire / Mensuelle. |
| **Choisir les mois** (depuis le 2026-10-14) | Répétition mensuelle seulement : cochez les mois où l'émission a lieu, les douze par défaut. Décochez juillet et août pour une pause estivale, ou gardez un mois sur trois pour une émission trimestrielle. Se combine avec *Repeat By* (jour du mois / jour de la semaine). Décocher un mois sur une émission existante supprime ses instances à venir dans ce mois. |
| **Jours** | Quels jours de la semaine (pour Hebdomadaire / Bihebdomadaire / Trihebdomadaire). |
| **Date de fin** | Optionnelle — quand la récurrence s'arrête. Laisser vide pour répéter indéfiniment. |

> **Conseil opérateur.** Une émission mensuelle qui se
> répète "le troisième vendredi" n'est *pas* directement
> supportée. Le plus proche est "hebdomadaire, vendredi,
> mais lié à un cycle de 4 semaines" — plus facile de
> planifier les quatre occurrences mensuelles comme
> émissions ponctuelles.

### Modifier une émission récurrente

- **Modifier l'émission** change la définition : chaque
  instance future reprend le changement. Les instances
  passées restent telles qu'elles étaient.
- **Modifier l'instance** crée une surcharge par
  occurrence (voir ci-dessus).
- **Supprimer cette instance** retire seulement cette
  occurrence.
- **Supprimer l'émission** retire toute la série y compris
  toutes les instances futures.
- **Annuler après suppression** (depuis le 2026-10-28) : une
  suppression depuis le menu du calendrier n'atteint pas le
  serveur tout de suite. L'émission disparaît du calendrier et un
  message en bas de page décompte dix secondes avec le lien
  **Annuler**. Un clic dessus ramène l'émission intacte ; si le
  compte arrive à zéro, la suppression s'exécute comme avant.
  Fermer la page pendant ces dix secondes envoie quand même la
  suppression. *Annuler l'émission* pour l'émission à l'antenne
  n'est pas différé et agit aussitôt, comme toujours.

> **Comment ça marche sous le capot.** Les émissions
> récurrentes écrivent une ligne `cc_show` + une ligne
> `cc_show_days` par jour de répétition + des lignes
> `cc_show_instances` pour chaque occurrence matérialisée.
> L'horizon de matérialisation est configuré sous
> Paramètres → Préférences générales. Étendre l'horizon
> est O(N) sur les émissions récurrentes existantes ; le
> runbook de mise à jour couvre comment gérer ceci.

---

### Rediffusion d'une autre émission (depuis le 2026-10-18)

Beaucoup d'émissions passent une fois et sont rediffusées une fois,
un autre jour ou une autre semaine.  Ouvrez le formulaire **Edit
Show** de la rediffusion, section **Rediffusion** (juste au-dessus
d'Autoloading Playlist), et
choisissez l'original sous **Rediffusion de l'émission**.  Dès lors
chaque instance de la rediffusion est remplie automatiquement :

- **Émissions proposées par la liste** *(depuis le 2026-10-27)* :
  toute émission à venir ou en cours, et une émission déjà diffusée
  (dans les 60 derniers jours) seulement si sa dernière instance peut
  être rediffusée entièrement - uniquement des pistes, ou son
  enregistrement est importé.  Une émission en direct passée sans
  enregistrement n'est pas proposée : choisissez l'original avant sa
  diffusion.  Une source déjà enregistrée reste sélectionnable.
- **Quand** : peu avant le début de la rediffusion (environ une
  heure, la même avance que le chargement automatique), pas à la fin
  de l'original - les corrections faites à l'original après sa
  diffusion sont donc reprises.
- **Quoi** : le contenu de la **dernière instance terminée** de
  l'original - fichiers et flux web dans leur ordre avec les points de
  repère et fondus diffusés, jingles compris.  La playlist de
  chargement automatique remplit ensuite le temps restant.
- **Entrées live et webstreams** *(depuis le 2026-10-20, webstreams
  depuis le 2026-10-21)* : si l'original est
  enregistré et que **Copier les enregistrements d'émission dans la
  bibliothèque** est actif (Paramètres → Machine locale → Show
  Recording), chaque ligne line-in ou webstream de l'original est remplacée par la
  tranche correspondante de son enregistrement - les points de repère
  d'entrée et de sortie sont les décalages de la ligne par rapport au
  début de l'émission, la rediffusion joue donc exactement ce qui est
  passé en direct entre les titres.  Un original sans aucune ligne
  (émission purement live) est rediffusé à partir du seul
  enregistrement.  Le remplissage attend l'import de l'enregistrement,
  mais pas au-delà de cinq minutes avant le début de la rediffusion ;
  sans enregistrement, un webstream est copié comme ligne live et un
  line-in reste dehors, comme avant.
  L'enregistrement est protégé contre la suppression tant qu'une
  rediffusion en attente en a besoin.
- **Si l'original n'a pas encore été diffusé** (première semaine,
  instance annulée) : la rediffusion est laissée à sa playlist de
  chargement automatique.
- **Durée** : une rediffusion plus courte est coupée à sa fin comme
  toute émission surbookée ; une plus longue est complétée par sa
  playlist de chargement automatique.
- **Chaînes** permises (C rediffuse B, B rediffuse A) ; une boucle
  est refusée à l'enregistrement.  « Rediffusion de l'émission » ne
  se combine pas avec **Link**.
- **Supprimer une piste** diffusée par l'original est refusé tant
  qu'une rediffusion l'attend (« encore nécessaire pour la
  rediffusion ... du ... »).  Un fichier disparu du disque hors de
  RASTATIME est sauté et compté.

Dans le calendrier, une rediffusion porte une **icône de
rediffusion** (deux flèches, depuis le 2026-10-21) au lieu de la
marque rouge « vide » ou « partiellement remplie », comme l'horloge
d'une émission à chargement automatique - elle se remplit toute
seule ; le survol de l'icône indique le nom de l'original.

**View Show** sur une rediffusion remplie dit « Rediffusion de
l'émission A du <date> à <heure> » et, si des lignes ont été sautées,
combien.  Une instance qui a déjà du contenu (remplie à la main)
n'est jamais écrasée.  Les émissions live enregistrées ne peuvent pas
encore être rediffusées ainsi (étape 2, voir BACKLOG).

## 5. Glisser-déposer

Deux types de glisser sont supportés sur le calendrier :

### 5.1 Déplacer une émission

Cliquez et glissez n'importe quel bloc d'émission future
vers une heure / un jour différent.

- L'émission s'accroche à l'intervalle de grille choisi dans la
  liste en haut à gauche de la grille horaire (1, 5, 10, 15, 30
  ou 60 minutes ; 10 minutes tant que vous n'en avez pas choisi
  un autre, enregistré par utilisateur).
- Le glissement respecte la règle de non-chevauchement :
  déposer sur un créneau occupé est rejeté avec un flash
  rouge.
- Pour une émission récurrente, seulement *cette
  instance* est déplacée — le reste de la série reste.

### 5.2 Redimensionner une émission

Survolez le bord inférieur d'une émission ; le curseur
devient une double flèche. Glissez vers le bas pour
allonger, vers le haut pour raccourcir.

- Elle s'accroche au même intervalle de grille qu'un
  déplacement.
- Un redimensionnement ne peut pas pousser l'émission
  au-delà d'une émission voisine (chevaucherait) ou en
  dessous de 5 minutes (la durée minimale d'émission).

### Ce qui ne peut pas être glissé

- Émissions passées (ne peut pas changer l'histoire
  rétroactivement).
- L'émission actuellement à l'antenne (utilisez plutôt
  **Annuler l'émission**).
- Toute émission, sauf si vous êtes Program Manager ou Admin
  (les DJ ne déplacent ni ne redimensionnent d'émissions).

---

## 6. Le menu contextuel du calendrier — Référence complète

Clic droit sur n'importe quelle émission :

| Groupe | Items |
|---|---|
| Contenu | Planifier les pistes, Vider le planning |
| Édition | Modifier l'émission, Modifier l'instance, Appliquer un modèle, Enregistrer comme modèle |
| Cycle de vie | Annuler l'émission (actuelle seulement), Supprimer l'émission, Supprimer cette instance |
| Info | Voir l'émission, Voir le fichier enregistré (si un enregistrement existe) |

Le menu s'adapte à l'état de l'émission — ex. **Voir le
fichier enregistré** n'apparaît qu'après que
l'enregistrement a fini d'écrire.

---

## 7. La ligne de maintenant

Une fine ligne rouge traverse le calendrier à l'heure
actuelle. La ligne se met à jour chaque minute. Les
émissions entièrement à gauche de la ligne sont passées ;
les émissions que la ligne croise actuellement sont à
l'antenne.

> **Conseil opérateur.** Si vous déboguez "pourquoi la
> mauvaise émission joue maintenant" — alignez la ligne de
> maintenant contre le calendrier. L'émission à l'antenne
> est le bloc que la ligne de maintenant intersecte. S'il
> n'y a pas de bloc, l'[Auto DJ](./AUTO_DJ.md) prend le
> relais (si activé) ou fallback / silence joue.

---

## 8. Opérations en masse

Calendrier → menu déroulant **Actions en masse** en haut
à droite :

| Action | Effet |
|---|---|
| **Appliquer un modèle aux émissions sélectionnées** | Cochez plusieurs émissions futures sur la grille ; l'action en masse re-tamponne chacune depuis le même modèle. |
| **Supprimer les émissions sélectionnées** | Supprimer chaque émission sélectionnée. Le résumé de confirmation liste chacune. |

Pour des replanifications plus grandes (ex. "décaler tout
la semaine prochaine d'une heure à cause de l'heure
d'été"), le calendrier ne supporte pas actuellement une
action de décalage en masse. La solution de contournement
est de définir la semaine décalée comme un Modèle
d'émission séparé et de l'appliquer.

---

## 9. Foire aux questions

### "J'ai planifié une émission mais rien ne joue à l'heure de début."

Trois possibilités :

1. L'émission est vide (la barre de remplissage montre
   0 %). Ouvrez Planifier les pistes et ajoutez au moins
   un item.
2. L'émission a une
   [Autoloading Playlist](./AUTOLOADING_PLAYLISTS.md) mais
   la playlist est vide.
3. Le service **RASTATIME-PLAYOUT** ne tourne pas.
   Vérifiez avec `Get-Service RASTATIME-PLAYOUT`. Voir
   [`CRASH_RECOVERY`](../../operator/CRASH_RECOVERY.md)
   si c'est le cas.

### "Une émission peut-elle contenir une autre émission ?"

Non. Les émissions sont plates. Une émission contient des
items de planning (pistes, smart blocks, webstreams,
line-ins). Pour grouper du contenu lié, utilisez une
playlist (qui peut être imbriquée dans une autre playlist
par référence).

### "Deux émissions peuvent-elles se chevaucher si ce sont des DJ différents ?"

Non. La règle de "non-chevauchement" est au niveau station
parce qu'il n'y a qu'une sortie. Pour gérer "deux
productions simultanées", utilisez deux streams de sortie :
chaque émission cible un stream spécifique.

### "Quelle est la durée maximale d'émission ?"

Techniquement 24 heures. Opérationnellement, vous devriez
diviser tout ce qui dépasse quelques heures en plusieurs
émissions — le show-builder est conçu pour des émissions
de durée typique (15 min – 4 h).

### "Que se passe-t-il la nuit du changement d'heure ?"

Les émissions sont définies en heure locale et y restent : une
émission à 08:00 passe à 08:00 avant comme après le changement.  Une
émission qui chevauche le changement se termine à son heure de fin
locale : « 22:00 pendant 8 heures » se termine à 06:00 la nuit
d'automne (neuf heures réelles, le chargement automatique remplit
l'heure supplémentaire) et à 06:00 la nuit de printemps (sept heures
réelles).  Ni trou ni chevauchement avec l'émission suivante.  Dans
l'heure de transition elle-même (02:00–03:00) : une émission dont
l'heure de fin n'existe pas au printemps se termine une heure plus
tard ; une émission entièrement dans l'heure sautée garde sa durée ;
une heure de fin qui existe deux fois en automne est prise à sa
première occurrence.  Depuis le 2026-10-16 ; auparavant, une émission
à cheval sur le changement finissait une heure trop tôt (automne) ou
trop tard (printemps).

### "Puis-je importer / exporter le calendrier en ICS ?"

Oui — export ICS en lecture seule à
`/Calendar/ics/format/ics`. Utile pour syndiquer le
planning public à un site web ou un autre système de
calendrier. L'import n'est pas supporté.

---

## Où aller ensuite

* [Modèles d'émission](./SHOW_TEMPLATES.md) — arrêtez de
  taper les mêmes paramètres d'émission chaque semaine.
* [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) —
  laisser les émissions se remplir elles-mêmes depuis une
  playlist.
* [Auto DJ](./AUTO_DJ.md) — laisser le système remplir
  les trous de calendrier pour vous.
* [Enregistrement par émission](./RECORD_PER_SHOW.md) —
  capturer ce qui était à l'antenne dans un fichier.
