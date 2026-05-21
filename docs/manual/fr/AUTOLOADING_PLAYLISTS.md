# Autoloading Playlists

> **Où vous êtes dans le manuel.** Lisez d'abord
> [Bibliothèque](./LIBRARY.md) et [Calendrier](./CALENDAR.md) —
> les autoloading playlists connectent un item de
> bibliothèque (la playlist) à un item de calendrier
> (l'émission). La fonctionnalité distincte
> [Auto DJ](./AUTO_DJ.md) *n'est pas* la même chose ; voir
> §8 pour la différence.

Une **autoloading playlist** est une playlist de bibliothèque
*attachée à une définition d'émission*, de sorte que chaque
instance de l'émission est remplie depuis cette playlist
automatiquement. Vous gérez la playlist une fois ; chaque
émission du lundi à 09:00 prend ce que la playlist contient
actuellement.

C'est l'économiseur de travail le plus puissant de RASTATIME
pour les stations avec programmation régulière. Une
"Matinale" avec une autoloading playlist de smart blocks
demande zéro attention hebdomadaire : modifiez les critères
de smart-block une fois par saison, et l'émission se remplit
chaque jour de semaine.

---

## 1. Les bases

Une émission avec autoloading playlist est construite
**une fois par instance** par le builder d'autoplaylist
d'arrière-plan. Le build se produit typiquement 60
secondes avant le début de l'instance — juste à temps pour
que l'émission reflète l'état le plus récent de la
playlist.

La séquence de build pour chaque instance est :

1. (Optionnel) **Playlist intro** ajoutée au début.
2. Items de la **playlist body** ajoutés en ordre ; les
   smart blocks s'étendent ici.
3. (Optionnel) **Playlist outro** ajoutée à la fin.
4. Si le créneau a encore plus de 5 s de queue non
   planifiée et que **Répéter jusqu'à plein** est activé,
   le body se répète jusqu'à remplir (en ré-évaluant les
   smart blocks à chaque cycle).
5. Les secondes suivant le créneau outro sont coupées
   pour qu'aucun item ne dépasse.

Si l'opérateur a manuellement planifié quelque chose dans
l'émission avant que le build d'autoplaylist ne tourne, le
build d'autoplaylist voit le créneau comme déjà rempli et
ne fait rien.

---

## 2. Attacher une autoloading playlist à une émission

Ouvrez l'émission dans le calendrier → **Modifier
l'émission** → développez **Autoloading Playlist**.

```
   ┌─────────────────────────────────────────────────────────┐
   │  Autoloading Playlist                                   │
   ├─────────────────────────────────────────────────────────┤
   │  ☑  Ajouter Autoloading Playlist ?                      │
   │                                                         │
   │   Playlist intro :     [Sélectionner... ▾]              │
   │   Playlist principale: [Sélectionner... ▾]  ◀── oblig.  │
   │   Playlist outro :     [Sélectionner... ▾]              │
   │                                                         │
   │  ☐  Répéter jusqu'à plein                               │
   └─────────────────────────────────────────────────────────┘
```

| Champ | Ce qu'il fait |
|---|---|
| **Ajouter Autoloading Playlist ?** | Interrupteur principal. Décoché = pas d'auto-build. |
| **Playlist intro** | Ajoutée au tout début de l'émission. Optionnelle. Joue exactement une fois. |
| **Playlist principale** | Le contenu body. Requis si l'interrupteur principal est activé. Les smart blocks dans cette playlist s'étendent au moment du build en utilisant les secondes restantes du créneau comme limite si configurée. |
| **Playlist outro** | Ajoutée à la toute fin de l'émission. Optionnelle. Joue exactement une fois. |
| **Répéter jusqu'à plein** | Si activé, les items de la playlist principale se répètent (les smart blocks sont ré-évalués à chaque cycle) jusqu'à ce que le créneau soit rempli moins la réserve outro. Si désactivé, la playlist principale joue une fois et toute queue restante est du silence. |

Enregistrez l'émission. Le builder d'autoplaylist prend
l'attachement à son prochain poll (par défaut toutes les
60 s) et construit les instances futures en conséquence.

---

## 3. La cadence de build de 60 secondes

Le builder d'autoplaylist tourne toutes les 60 secondes.
Pour chaque instance à venir d'une émission avec
autoloading playlist :

- Si l'instance commence dans **moins de ~60 s** et n'a
  pas encore été construite, construire maintenant.
- Sinon, la laisser pour le prochain cycle.

Cela signifie que le build est *toujours* un build de
l'état **actuel** de la playlist, pas d'un instantané
obsolète. Si vous modifiez la playlist à 08:58 pour une
émission de 09:00, l'émission de 09:00 obtient la version
modifiée.

> **Conseil opérateur.** Si vous devez pousser une
> modification à la même minute (ex. échanger une piste à
> 08:59:30 pour une émission de 09:00), forcez un build
> manuel : ouvrez l'émission → **Vider le planning** →
> fermez. Le prochain cycle de poll (dans les 60 s) va
> reconstruire depuis la playlist mise à jour.

> **Comment ça marche sous le capot.** Le builder est la
> méthode statique
> `AutoPlaylistManager.buildAutoPlaylist()`, invoquée par
> le `SchedulePollJob` du worker job runner toutes les
> 60 s. Chaque cycle parcourt chaque émission à venir avec
> `cc_show_autoplaylist.has_autoplaylist = TRUE`, vérifie
> si le planning de l'instance est déjà peuplé, et
> construit sinon. Voir ARCHITECTURE §17 pour la pipeline
> complète.

---

## 4. La réserve d'outro (Section 23.19)

C'est la partie opérationnellement la plus délicate de
l'autoloading et mérite d'être comprise.

### Le problème

Supposons que votre **Playlist principale** utilise un
smart block avec *Limiter à : Temps restant dans
l'émission*, et que vous avez une **Playlist outro** avec
un ID de station de 60 s.

Sans réserve d'outro, l'expansion du smart block voit
"temps restant = 60 minutes" (l'émission entière),
choisit 60 minutes de pistes, et l'insertion outro
ultérieure soit :

- Échoue parce que le créneau est maintenant plein, soit
- Pousse l'outro au-delà de la fin du créneau, causant
  un débordement de 60 s que le playout coupera durement.

### La solution

Avant d'étendre tout smart block dans la playlist
principale, le builder :

1. Fait un **trial-insert** de l'outro dans le créneau.
2. Mesure sa longueur (c'est la seule façon fiable de
   mesurer les playlists portant des smart blocks, dont
   la colonne `length` reste à 0 parce que les blocks
   s'étendent plus tard).
3. Annule le trial-insert.
4. Restaure tous les effets de bord
   `cc_files.is_scheduled` que le trial-insert a
   transitoirement basculés sur TRUE.
5. Dit au scheduler de **réserver** ce nombre de secondes
   du créneau avant d'étendre tout smart block.

Un smart block avec "temps restant" voit maintenant
*(total créneau) − (longueur outro) − (5 s marge)* et
choisit le bon nombre de pistes. L'outro s'insère ensuite
proprement à la fin.

### La marge de 5 secondes

La réserve est plafonnée à la longueur outro mesurée plus
une **marge de 5 s** (décision opérateur 2026-05-20, v8).
Sans la marge, l'arrondi de sélection de smart-block
laisserait parfois un écart de sous-seconde avant l'outro
que l'opérateur entendait comme une minuscule pause.
Avec 5 s de jeu, l'auto-build garde l'utilisation du
créneau près de 100 % sans jamais déborder.

> **Pourquoi 5 s et pas plus ?** Les opérateurs ont
> préféré une utilisation élevée (plus de musique, moins
> de silence) à une réserve trop prudente. Une plus
> grande réserve (ex. 30 s) signifierait qu'une émission
> de 60 min joue seulement 59:30 de musique + 30 s d'air
> mort avant l'outro — perceptible et mal aimé. Voir
> ARCHITECTURE §23.19 pour l'évolution version par
> version.

### Nettoyage post-build

Après que le body se construit et l'outro s'insère, un
passage final coupe tout item dont l'heure de fin
dépasserait le début de l'outro. Les items entièrement à
l'intérieur du créneau outro sont laissés tranquilles
(l'outro joue inchangé). Cela attrape le cas limite où
l'arrondi de smart-block a mis le dernier item de body à
mi-chemin au-delà de la limite de réserve.

> **Comment ça marche sous le capot.** La réserve est
> `Application_Model_Scheduler::setReservedSeconds()`. Le
> trim est
> `Application_Model_Scheduler::trimTailExcept($outroStart)`.
> Les deux chevauchent dans
> `AutoPlaylistManager.buildAutoPlaylist()`. Voir commit
> ed57399.

---

## 5. Choisir la bonne playlist pour autoloading

### Ce qui marche bien

- **Playlists smart-block-seulement** avec *Limiter à :
  Temps restant dans l'émission*. Le motif le plus
  courant : un smart block, un filtre ("genre = pop et
  bpm > 100"), une limite. Combiné avec la réserve
  d'outro, ceci remplit toute longueur de créneau
  proprement.

- **Intro + smart block + outro** pour les émissions
  avec un intro d'ID de station et un outro d'ID de
  station. L'intro joue exactement une fois, le smart
  block remplit le body, l'outro joue exactement une
  fois.

- **Playlists statiques pour émissions courtes** de moins
  de 5 minutes où les smart blocks seraient excessifs.
  Une émission "Info Brève" de 60 s avec trois références
  de clip explicites est bien sans smart blocks.

### Ce qui ne marche pas bien

- **Mélanger pistes statiques et smart blocks "répéter
  jusqu'à plein"** — les smart blocks continueront
  d'ajouter des pistes même après que les pistes
  statiques auraient rempli le créneau. Prévisible pour
  le builder, surprenant pour l'opérateur.

- **Webstreams ou line-ins dans le body** quand
  **Répéter jusqu'à plein** est activé. Les items
  webstream et line-in ont une durée configurée (par
  défaut 60 min) mais le playout les traite comme "jouer
  pour toujours jusqu'à être dit de s'arrêter" ;
  l'auto-builder voit la durée configurée mais le temps
  réel consommé est ce que l'émission permet. Utilisez
  généralement webstreams / line-ins comme *tout* le
  body, pas mélangé.

- **Très longues playlists** (1000+ items) — l'auto-build
  est rapide, mais vous voulez généralement un smart
  block sur une longue playlist statique pour la
  ré-évaluation à chaque cycle.

---

## 6. Comportement Répéter-jusqu'à-plein

Quand **Répéter jusqu'à plein** est coché :

- Les items de la playlist principale sont insérés, les
  smart blocks étendus, jusqu'à ce que le créneau soit
  plein moins la réserve outro.
- Le cycle ré-évalue les smart blocks à chaque itération,
  donc un smart block *dynamique* choisit une sélection
  différente à chaque répétition — contenu varié dans un
  créneau.
- Les playlists piste-seulement se répètent aussi, donc
  les mêmes pistes rejouent. Si vous voulez du contenu
  varié, utilisez des smart blocks.

Quand décoché :

- La playlist principale joue une fois.
- Toute queue restante après le body mais avant l'outro
  est du silence.

> **Conseil opérateur.** Cochez toujours **Répéter
> jusqu'à plein** pour un body smart-block. Sans cela,
> une émission de 60 min avec un smart block "Limiter à
> 10 pistes" joue ~40 min de musique et 20 min de silence
> avant l'outro.

---

## 7. Retirer une autoloading playlist

Modifier l'émission → développer **Autoloading Playlist**
→ décocher **Ajouter Autoloading Playlist ?** →
Enregistrer.

Les instances futures ne s'auto-construiront plus. Les
instances déjà construites gardent leur contenu construit
(pas de changement rétroactif). Pour vider une instance
déjà construite, ouvrez l'émission dans le calendrier →
**Vider le planning**.

---

## 8. Autoloading Playlists vs Auto DJ

Ces deux fonctionnalités sont faciles à confondre.
Référence rapide :

| | Autoloading Playlist | Auto DJ |
|---|---|---|
| **Où attaché** | Formulaire d'édition d'une émission spécifique | Paramètres → Auto DJ (au niveau station) |
| **Quand ça remplit** | Par instance d'émission, 60 s avant le début | (a) Crée de nouvelles émissions dans les trous du calendrier. (b) Complète les émissions incomplètes à venir. |
| **Avec quoi ça remplit** | La playlist configurée (n'importe quelle structure) | Une playlist Auto-DJ configurée |
| **Affecte quelles émissions** | Seulement l'émission à laquelle elle est attachée | Toutes les émissions + en crée de nouvelles |
| **Besoin d'un animateur ?** | Non | Non |
| **Désactivé par défaut** | Oui | Oui |

Utilisez les autoloading playlists pour la
**programmation régulière** (la Matinale utilise toujours
la Playlist Matinale). Utilisez Auto DJ pour le **temps
d'antenne non planifié** (ce que vous avez oublié de
planifier, l'Auto DJ l'attrape).

Voir [Auto DJ](./AUTO_DJ.md) pour la fonctionnalité
complète.

---

## 9. Foire aux questions

### "J'ai attaché une playlist mais l'émission est restée vide."

Trois possibilités :

1. L'instance a déjà commencé — l'auto-build ne touche
   que les instances *futures*.
2. L'instance a déjà été remplie manuellement.
   L'auto-build saute toute émission qui a déjà des items
   planifiés.
3. Le worker job runner ne tourne pas. Vérifiez
   `Get-Service RASTATIME-WORKER`.

### "Comment voir si l'auto-build a tourné pour une instance spécifique ?"

Ouvrez l'émission dans le calendrier ; la barre de
remplissage du calendrier devrait être > 0 %. Si elle est
à 0 % quelques secondes avant l'heure de début,
l'auto-build n'a pas encore tourné. Attendez 60 s et
rechargez, ou utilisez **Vider le planning** + rouvrir
pour forcer le prochain cycle de poll à traiter
l'instance comme fraîche.

### "La playlist intro peut-elle contenir un smart block ?"

Oui, mais les smart blocks dans les playlists
intro / outro n'obtiennent *pas* le traitement de réserve
d'outro — ils s'étendent comme s'ils avaient le créneau
entier. Si le smart block de l'intro a la limite "temps
restant", il avalera toute l'émission. Utilisez des
smart blocks à durée fixe ("Limiter à 30 s") ou des
pistes statiques pour intro / outro.

### "Pourquoi l'auto-build choisit-il parfois la même piste deux fois ?"

Si la playlist body utilise **Répéter jusqu'à plein** avec
une playlist statique, les mêmes pistes se répètent. Pour
éviter cela, soit :

- Utilisez un smart block avec type **Dynamique** pour
  que chaque répétition re-requête.
- Définissez "Trier : Aléatoire" dans le smart block
  pour que chaque répétition choisisse un ordre
  aléatoire différent.

### "Puis-je avoir deux autoloading playlists sur une émission ?"

Non. Le modèle est **intro + body + outro**, et seul le
body est la "principale" autoloading playlist. Pour
obtenir deux sélections distinctes dans une émission,
mettez un smart block dans le body qui union deux
ensembles de critères via le groupe OU smart-block.

---

## Où aller ensuite

* [Auto DJ](./AUTO_DJ.md) — l'automatisation au niveau
  station qui complète l'autoloading par-émission.
* [Modèles d'émission](./SHOW_TEMPLATES.md) — capturer
  l'attachement d'autoloading-playlist comme partie d'un
  modèle pour que chaque nouvelle émission obtienne la
  même configuration.
* [Bibliothèque](./LIBRARY.md) → §3 Smart Blocks — la
  primitive body-playlist la plus puissante.
