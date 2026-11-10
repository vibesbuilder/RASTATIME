# Automatisation des teasers

> **Où vous êtes dans le manuel.** Bibliothèque → éditeur de piste,
> champs **Teaser pour l'émission** et **Type de teaser** ;
> Bibliothèque → Smart Blocks, critères **Teaser : émission**,
> **Teaser : type**, **Teaser : correspond à la grille**.  Lisez d'abord
> [Bibliothèque](./LIBRARY.md) § 3 (smart blocks) et
> [Playlists de chargement automatique](./AUTOLOADING_PLAYLISTS.md) -
> l'automatisation est un critère de smart block que l'autoloading
> diffuse.
>
> **Ce que cette fonction remplace.** Placer à la main, jour après jour,
> les jingles « aujourd'hui » et « demain » de chaque émission, avant et
> après les informations et dans les émissions musicales.

Une station connaît trois sortes de teasers : un **teaser d'émission**
qui annonce simplement une émission (« Around the World - chaque
jeudi à 11 h »), un **teaser du jour « aujourd'hui »** (« Around the World - aujourd'hui à 11 h ») et un **teaser du jour « demain »**.
Celui qui convient dépend du jour où le jingle passe et du calendrier.
Depuis le 2026-10-16, la bibliothèque sait quelle émission un jingle
annonce et comment, et un critère de smart block choisit les jingles
qui correspondent au jour de l'émission remplie.

---

## 1. Lier un jingle à son émission

Ouvrez le jingle dans l'éditeur de piste (Bibliothèque → crayon ou
double-clic) et renseignez

| Champ | Signification |
|---|---|
| **Type de teaser** | **Teaser d'émission (tout jour)**, **Teaser du jour : « aujourd'hui »** ou **Teaser du jour : « demain »**.  Choisissez-le d'abord : la liste des émissions reste grisée tant qu'aucun type n'est défini, et un enregistrement avec des émissions sans type est refusé. |
| **Teaser pour les émissions** | les émissions que ce jingle annonce - le bouton **Émissions** ouvre le même panneau de cases que le pool de demandes ; cochez-en une ou plusieurs, le bouton affiche le nombre.  La liste contient chaque émission ayant une diffusion à venir, avec sa prochaine heure (`bbc (Sat 12:00)`) afin de distinguer les émissions homonymes ; les créneaux d'informations horaires sont des émissions distinctes et un seul jingle « BBC aujourd'hui » peut les annoncer toutes.  Aucune sélection = pas de teaser ; remettre le type sur *None* vide la liste. |

Pour de nombreux jingles à la fois, sélectionnez-les dans la
bibliothèque et utilisez **Edit** (édition groupée) : les deux mêmes
champs ; aucune sélection conserve un champ, *None* retire les liens,
les émissions choisies remplacent la liste - et exigent un type dans le
même enregistrement, car les pistes sélectionnées n'en ont pas forcément.  La
colonne de bibliothèque **Teaser** (sélecteur de colonnes, masquée par
défaut) affiche `Nom de l'émission · today` (`· tomorrow` ; les teasers d'émission n'ont pas de suffixe) et se recherche, de sorte
que « Teaser contient Worldwide » liste tous les jingles de cette
émission.

Un jingle a un type et annonce une ou plusieurs émissions ; il convient
dès que l'une de ses émissions convient.  Deux jingles peuvent bien sûr
annoncer la même émission avec des types différents.

## 2. Les critères de smart block

| Critère | Modificateurs | Valeur | Correspond à |
|---|---|---|---|
| **Teaser : émission** | est / n'est pas | une émission | les jingles qui annoncent cette émission (entre autres) |
| **Teaser : type** | est / n'est pas | teaser d'émission, aujourd'hui, demain | les jingles de ce type |
| **Teaser : correspond à la grille** | est | le jour de l'émission remplie | voir ci-dessous |

**Teaser : correspond à la grille** est l'automatisation.  « Le jour »
est le jour calendaire (fuseau de la station) du *créneau* pour lequel
le bloc est développé : le début de l'émission pour une playlist d'intro
de chargement automatique, la fin de l'émission pour l'outro, la
position courante pour la playlist de contenu, et - quand vous glissez
un bloc dans une émission à la main - la fin de la ligne après laquelle
vous le déposez.  Avec ce jour *D* et l'instant *T* du créneau :

* un teaser **« aujourd'hui »** correspond quand son émission a une
  diffusion le jour *D* qui commence après *T* ;
* un teaser **« demain »** correspond quand son émission a une
  diffusion le jour *D + 1* ;
* un **teaser d'émission** correspond n'importe quel jour - sauf si son
  émission est *terminée pour aujourd'hui* : elle a eu une diffusion le
  jour *D* finie avant *T* et n'en a plus de plus tardive ce jour-là ;
* un jingle ne correspond jamais à l'émission dont l'épisode est
  rempli - une émission ne se teste pas elle-même.

Une diffusion annulée ou déplacée emporte donc ses teasers du jour : le
critère lit le calendrier au moment du remplissage, pas une liste fixe.

## 3. Rotation : jamais deux fois le même jingle dans une émission

Combinez le critère avec **Exclude tracks played lately** (par exemple
3 heures).  Depuis le 2026-10-16, ce filtre compte aussi les lignes
**planifiées** : une piste programmée dans la fenêtre - avant ou après le
créneau, y compris les lignes qu'un bloc précédent du même remplissage
vient de placer dans la même émission - est exclue bien qu'elle n'ait
pas encore été diffusée.  Deux blocs de teasers dans une émission ne
tirent donc jamais le même jingle, et un jingle planifié dans l'émission
précédente ne revient pas dans la suivante.  Cela vaut pour tout smart
block avec ce filtre, musique comprise.

## 4. Recettes

**Bloc d'informations (p. ex. l'émission BBC horaire).**  Donnez à
l'émission une playlist d'intro et une playlist d'outro de chargement
automatique, chacune avec un smart block dynamique : *1 élément*,
critère *Teaser : correspond à la grille est le jour de l'émission
remplie*, *Exclude tracks played lately 3 h*.  Le créneau doit laisser
de la place aux jingles : une émission de 7 minutes avec un flux de
7 minutes n'en a pas.

**Émissions musicales.**  Remplacez les blocs de teasers du jour faits à
la main dans leurs playlists de chargement automatique par ce même
bloc.  Gardez un second bloc *Teaser : type est Teaser d'émission* pour
les émissions qui n'ont pas encore de teasers du jour.

**Une seule émission.**  *Teaser : émission est Worldwide* avec
*Teaser : correspond à la grille* ne donne les jingles de cette
émission que lorsqu'ils correspondent.

## 5. Les teasers depuis le calendrier

Cliquez sur une émission dans le [Calendrier](./CALENDAR.md) et
choisissez **Compléments** → **Teasers** (un sous-menu depuis le 2026-11-10) : la boîte de dialogue liste chaque jingle qui
annonce cette émission avec son type et les autres émissions qu'il
annonce ; vous changez le type sur place, retirez un jingle de
l'émission avec la croix et en liez d'autres : saisissez deux
caractères d'un titre ou d'un artiste, choisissez le jingle, un type
(ou gardez celui du jingle) et cliquez **Lier à cette émission**.  Le
type appartient au jingle : le changer ici le change pour toutes ses
émissions.  Administrateurs et responsables de programme seulement ;
l'entrée existe aussi pour les émissions passées, le lien valant pour
l'émission et non pour la diffusion.

## 6. Import / Export

[Import / Export](./IMPORT_EXPORT.md) transporte les critères dans
`blocks.json` : `teaser_show` par nom d'émission (la première émission
de ce nom à l'import), `teaser_type` en `show`, `today` ou `tomorrow`,
`teaser_fits` avec la valeur `yes`.  Les liens des jingles eux-mêmes
sont des métadonnées des fichiers et ne font pas partie de l'archive.

## 7. Foire aux questions

### « Generate dans l'éditeur de smart block montre d'autres jingles que ceux que l'émission reçoit. »

L'éditeur n'a pas de créneau : il prend *maintenant* comme instant et
n'exclut aucune émission.  Le vrai choix se fait au remplissage de
l'émission.

### « Une émission a disparu de la liste. »

La liste contient les émissions ayant une diffusion à venir.  Un jingle
garde son lien vers une émission qui n'en a plus ; l'éditeur l'affiche
toujours, le critère ne trouve simplement aucun jour qui convienne.

### « Rien n'est choisi du tout. »

Vérifiez que les jingles portent une émission et un type, que
l'émission a vraiment une diffusion ce jour-là et que les autres
critères du bloc (type de piste, genre) ne les excluent pas.  Tant que les
migrations de base de données 0069 et 0070 n'ont pas été exécutées, le critère donne
un pool vide et le journal le dit.

## Voir aussi

* [Bibliothèque](./LIBRARY.md) § 3 - critères de smart block, limites et
  filtres d'exclusion.
* [Playlists de chargement automatique](./AUTOLOADING_PLAYLISTS.md) -
  les playlists d'intro, d'outro et de contenu qui portent les blocs de
  teasers.
* [Calendrier](./CALENDAR.md) - les diffusions que lit le critère.
