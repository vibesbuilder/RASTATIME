# Infos-trafic

> **Où vous êtes dans le manuel.** Lisez d'abord [Bibliothèque](./LIBRARY.md)
> → §3 Smart Blocks et
> [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md), et idéalement
> [Demandes de titres](./SONG_REQUESTS.md) — les infos-trafic réutilisent le
> *même* mécanisme de remplissage incrémental à l'antenne. Aucun nouveau
> type d'objet n'est introduit.

Les **infos-trafic** permettent à un MP3 de dernière minute — un bulletin
de circulation qui vous est remis quelques minutes avant qu'il ne doive
passer — de passer à l'intérieur de l'**émission en cours**,
automatiquement, en une dizaine de minutes, sans qu'un animateur ait à
cliquer sur quoi que ce soit et sans interrompre le moteur de playout.

La fonctionnalité entière est assemblée à partir d'éléments que vous
connaissez déjà :

- un **smart block** qui correspond à vos bulletins de circulation est
  désigné, une fois pour toutes, comme la **source d'infos-trafic** dans
  les Paramètres ;
- une **Autoloading Playlist** contenant ce bloc, placée à quelques
  endroits d'une émission, transforme une émission ordinaire en
  **émission compatible infos-trafic** ;
- l'import d'un nouveau bulletin dans la bibliothèque suffit à le mettre à
  l'antenne au prochain créneau trafic.

Il n'y a pas de « file d'attente d'alertes » séparée ni de modification
côté playout. Une émission *devient* compatible infos-trafic lorsque son
Autoloading Playlist contient le bloc trafic configuré — rien d'autre.

---

## 1. Vue d'ensemble

```
   RÉDACTION                RASTATIME                       À L'ANTENNE
   ┌──────────┐  import     ┌────────────────────────┐
   │ trafic   │────────────▶│ Bibliothèque : le       │
   │  .mp3    │             │  fichier correspond     │
   └──────────┘             │  désormais au bloc      │
                            └───────────┬─────────────┘
                                        │  l'émission en cours se remplit
                                        │  au fur et à mesure, à l'antenne
                            ┌───────────▼─────────────┐   ┌──────────┐
                            │ Bloc infos-trafic au     │──▶│ Émission │
                            │  PROCHAIN créneau         │   │ planning │
                            │  ancien d'abord, 1 fois   │   └──────────┘
                            └──────────────────────────┘
```

Le mécanisme est celui que les Demandes de titres utilisent déjà (voir
[Demandes de titres](./SONG_REQUESTS.md) §5) : une émission compatible
infos-trafic est remplie **au fur et à mesure de sa diffusion**, juste un
peu en avance sur la tête de lecture. Chaque créneau trafic de l'émission
est résolu peu de temps avant son passage — il récupère donc tous les
bulletins importés entre-temps. Un bulletin importé *pendant* l'émission
passe par conséquent au **prochain** créneau trafic ; rien de ce qui est
déjà planifié n'est repoussé.

Vous configurez la source une fois (§2–§3) et placez le bloc dans vos
émissions (§4) ; après quoi la fonctionnalité tourne sans surveillance
(§5).

---

## 2. Le smart block infos-trafic

Un bulletin de circulation n'est qu'un fichier audio. Le « bloc trafic »
est un [smart block](./LIBRARY.md) ordinaire dont les critères
correspondent exactement à ces fichiers et à rien d'autre. Configuration
typique :

- **Critères** ne sélectionnant que les bulletins — par exemple *Genre =
  Trafic*, ou *Dossier/Chemin contient `/trafic/`*, ce qui les isole
  proprement dans votre bibliothèque.
- **Tri : Plus récent d'abord** est naturel, mais l'ordre de diffusion n'en
  dépend pas — le système diffuse toujours en premier le bulletin **le plus
  ancien non encore diffusé** (celui dont l'échéance est la plus proche ;
  voir §5).
- **Exclure les titres diffusés récemment** (optionnel, recommandé) : une
  fois un bulletin diffusé, il sort du bloc, de sorte qu'un bulletin
  périmé n'est jamais repris un jour ultérieur.
- **Pas de limite d'éléments trop serrée.** Laissez de la place pour
  plusieurs bulletins afin que, si deux arrivent rapprochés, les deux
  soient candidats.

> **Conseil.** Gardez ce bloc dédié au trafic. Ne réutilisez pas un bloc
> musical — chaque fichier auquel le bloc correspond est traité comme un
> bulletin diffusable.

---

## 3. Le sélectionner dans les Paramètres

Ouvrez **Settings → General Preferences** et trouvez **Bloc intelligent
infos-trafic**. Choisissez votre bloc trafic dans la liste et enregistrez.

- La liste contient chaque smart block de votre bibliothèque.
- **`(aucun — désactivé)`** est la valeur par défaut et désactive
  entièrement la fonctionnalité — une émission qui contient malgré tout le
  bloc le joue alors simplement une fois comme un bloc ordinaire.

Un seul bloc à la fois peut être la source d'infos-trafic. C'est l'unique
interrupteur qui arme la fonctionnalité.

---

## 4. Construire une émission compatible infos-trafic

Ajoutez le bloc trafic à l'**Autoloading Playlist** d'une émission, de la
même manière que vous ajouteriez n'importe quel bloc — mais placez-le à
**plusieurs endroits** le long de la dramaturgie de l'émission, pas
seulement une fois. Par exemple :

```
   jingle · musique · TRAFIC · musique · musique · TRAFIC · musique · …
```

Chaque entrée `TRAFIC` est un créneau où un bulletin *peut* s'intercaler.
Si aucun bulletin n'attend lorsque le créneau est atteint, le créneau ne
diffuse rien et l'élément suivant passe simplement — les créneaux vides ne
vous coûtent donc rien.

**La densité à laquelle vous les placez est la façon dont vous tenez
l'échéance de dix minutes** (voir §6).  En règle générale : au plus
environ **cinq minutes de programme** entre deux créneaux trafic — tous
les éléments intermédiaires ensemble, pas seulement celui juste avant un
créneau.  Des éléments courts aident : le §6 montre un smart block qui ne
choisit que des titres courts.

L'émission a besoin de l'**Autoloading Playlist** activée (c'est ce qui
fait que l'émission se remplit elle-même). Aucun autre réglage particulier
n'est nécessaire sur l'émission.

---

## 5. Comment et quand un bulletin passe

Lorsqu'une émission compatible infos-trafic est à l'antenne, la tâche de
remplissage (toutes les deux minutes) résout sa dramaturgie un peu en
avance sur la tête de lecture. Lorsqu'elle atteint un créneau trafic, elle
choisit **un** bulletin, selon ces règles :

1. **Plus ancien d'abord (FIFO).** Parmi les bulletins en attente, elle
   diffuse celui **importé le plus tôt** — celui dont l'échéance de dix
   minutes est la plus proche.
2. **Diffusé une seule fois.** Un bulletin déjà planifié quelque part dans
   cette émission n'est jamais repris, de sorte que la même alerte ne peut
   passer deux fois même si le bloc figure à plusieurs créneaux.
3. **Pas de remplissage.** Si aucun bulletin frais n'attend, le créneau ne
   diffuse **rien** — il n'y a délibérément pas de repli sur un titre
   aléatoire (contrairement à un créneau de demandes). L'élément de
   programme suivant passe à la place.

Le flux de travail quotidien normal est donc simplement : **importez le
bulletin dans la bibliothèque** (dans le dossier/genre auquel votre bloc
correspond).  Il passe au prochain créneau trafic **pas encore fixé** : la
tâche de remplissage fixe un créneau jusqu'à **cinq minutes** avant sa
diffusion, un bulletin importé ensuite attend donc le créneau suivant
(§6).

> **Sous le capot.** Les infos-trafic et les demandes de titres partagent
> un seul moteur de remplissage incrémental. La seule différence tient à la
> façon dont un créneau se résout : un créneau de demandes tire les
> demandes des auditeurs et retombe sur un titre aléatoire ; un créneau
> trafic tire le bulletin le plus ancien non encore diffusé et retombe sur
> *rien*. Les deux écrivent dans le planning d'émission normal, que le
> moteur de playout reprend à son prochain rafraîchissement — le chemin
> audio en direct n'est pas modifié, et le bulletin apparaît dans
> l'historique et le calendrier comme n'importe quel titre.

---

## 6. L'échéance de dix minutes, c'est à vous de la tenir

Comme un bulletin passe à son **créneau de dramaturgie**, la rapidité avec
laquelle il passe dépend de la façon dont vous avez construit l'émission —
et non du système qui couperait un titre. RASTATIME ne saute **pas** le
titre en cours de lecture pour faire sortir un bulletin en urgence (ce
*saut d'échéance* automatique est une option future prévue, mise de côté
jusqu'à ce que l'exploitation en direct montre qu'il est réellement
nécessaire).

Combien de temps un bulletin peut attendre, au pire : un créneau trafic
est fixé jusqu'à cinq minutes avant sa diffusion (§5).  Un bulletin arrivé
juste après manque ce créneau et passe au suivant — le pire cas est donc
**l'écart entre deux créneaux trafic plus cinq minutes**.

Exemple : créneaux à 10:00, 10:06 et 10:12.  Le créneau de 10:06 est fixé
vers 10:01 ; un bulletin importé à 10:01:01 passe à 10:12 — après près de
onze minutes.

Vous tenez le SLA avec deux habitudes :

- **Espacez les créneaux trafic d'environ cinq minutes.** L'ensemble des
  éléments entre deux créneaux ne devrait pas durer plus de cinq minutes ;
  chaque bulletin passe alors en moins de dix.  Sept minutes fonctionnent
  généralement aussi, mais ne sont plus garanties.
- **Gardez courts les éléments entre deux créneaux.** Un mix de quinze
  minutes entre deux créneaux fait à lui seul manquer l'échéance.  Pour
  ces positions, utilisez un smart block qui ne choisit que des titres
  courts : une copie de votre bloc musical avec le critère **Durée** *est
  plus petit que* `00:04:00` (format heures:minutes:secondes, p. ex.
  `00:03:30` ; la comparaison porte sur la durée complète du fichier, à
  l'antenne un titre dure donc au plus autant).

Si votre programmation ne peut vraiment pas garantir un créneau dans
l'échéance (émissions au format très long, par exemple), prévenez votre
mainteneur RASTATIME — le saut d'échéance actif pourra alors être construit
et activé.

---

## 7. Liste de contrôle de l'opérateur

1. **Une fois :** construire un smart block ne correspondant qu'à vos
   bulletins de circulation (§2).
2. **Une fois :** Settings → General → **Bloc intelligent infos-trafic** →
   le sélectionner (§3).
3. **Par émission :** ajouter ce bloc à plusieurs endroits de
   l'Autoloading Playlist de l'émission, espacés d'environ cinq minutes de programme (§4, §6).
4. **Par bulletin :** importer le MP3 dans la bibliothèque de sorte qu'il
   corresponde au bloc — il passe au prochain créneau (§5).
5. **Pour mettre la fonctionnalité en pause :** Settings → remettre le bloc
   sur `(aucun — désactivé)`.

---

## 8. Questions fréquentes

### « J'ai importé un bulletin mais il n'est pas passé. »
Vérifiez trois choses : que le fichier **correspond bien au bloc trafic**
(ouvrez le bloc et confirmez qu'il y apparaît) ; que le **bloc est
sélectionné** dans les Paramètres ; et que l'**émission en cours contient
le bloc** dans son Autoloading Playlist. Si les trois sont vrais, il passe
au prochain créneau trafic — qui peut être à quelques minutes selon votre
dramaturgie (§6).

### « Le même bulletin est passé deux fois. »
Cela ne devrait pas arriver — un bulletin déjà planifié dans l'émission est
exclu des créneaux ultérieurs. S'il s'est réellement répété, les deux
diffusions sont dans des *émissions différentes* (les créneaux d'une
nouvelle émission le voient comme frais tant qu'il n'a pas réellement
passé ; activez *Exclure les titres diffusés récemment* sur le bloc pour
empêcher cela).

### « Un créneau trafic n'a rien diffusé. »
C'est attendu lorsqu'aucun bulletin frais n'attendait — un créneau trafic
n'a pas de remplissage, donc l'élément de programme suivant passe
simplement. Les créneaux vides sont gratuits ; placez-en autant que vous
voulez.

### « Deux bulletins sont arrivés en même temps — lequel passe en premier ? »
Le **plus ancien import** d'abord, puis le suivant au créneau trafic
suivant. Chaque créneau diffuse un bulletin, donnez-leur donc assez de
créneaux pour s'écouler.

### « En combien de temps un bulletin passe-t-il ? »
Au prochain créneau trafic pas encore fixé — au pire après l'écart entre
deux créneaux plus cinq minutes.  Avec des créneaux espacés d'environ cinq
minutes, c'est dans les dix minutes.  RASTATIME n'interrompt pas le titre
en cours pour le faire (§6).

### « Puis-je la désactiver ? »
Oui — Settings → **Bloc intelligent infos-trafic** → `(aucun —
désactivé)`. Une émission qui porte encore le bloc le joue alors simplement
une fois comme un bloc ordinaire.

---

## Où aller ensuite

- [Demandes de titres](./SONG_REQUESTS.md) — le même remplissage
  incrémental à l'antenne, pour les demandes des auditeurs.
- [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) — comment une émission
  se remplit elle-même à partir de playlists et de blocs.
- [Bibliothèque](./LIBRARY.md) → §3 Smart Blocks — construire le bloc qui
  correspond à vos bulletins.
