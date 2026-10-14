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
| **Répéter jusqu'à plein** | Si activé, les items de la playlist principale se répètent (les smart blocks sont ré-évalués à chaque cycle) tant que cela ajoute des lignes (strictement dans l'ordre, arrêt au premier titre qui ne tient pas). Si désactivé, la playlist principale joue une fois et toute queue restante est du silence. |

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

## 4. Comment le créneau est rempli (depuis le 2026-10-01)

Le builder remplit une émission en trois étapes, toujours contre
le temps **réellement** libre dans le créneau :

1. La **playlist intro** va au début, exactement une fois.
2. La **playlist outro** va à la fin, exactement une fois — elle
   est placée pour de bon, sa longueur est donc connue exactement
   (l'insertion d'essai avec mesure des builds précédents a
   disparu, et avec elle la marge de 5 secondes).
3. La **playlist autoloading** remplit l'espace entre les deux.

Chaque liste est prise **strictement dans son ordre** et s'arrête
au premier titre qui ne tient plus avant la fin de l'émission
(décision de l'opérateur, « variante a ») : rien n'est jamais
placé au-delà de la fin, donc rien n'a à être coupé ensuite. Une
intro ou une outro plus longue que le créneau est tronquée de la
même façon (les titres qui ne tiennent pas sont omis ; le journal
en donne le nombre).

« Réellement libre » désigne le temps mis en page : depuis le
2026-09-29 les lignes se chevauchent de leur crossfade (valeur
maison 3 s, ou celle du type de piste), et la somme des durées ne
dit plus où finit la dernière ligne. Le builder met les lignes en
page avec la même règle de paire que le scheduler ; une émission
de 60 minutes avec quinze titres musicaux ne finit donc **plus**
42 secondes trop tôt.

Un smart block avec *Limiter à : temps restant de l'émission*
reçoit ce temps mis en page comme budget — majoré du chevauchement
que sa propre sélection produira ; le builder essaie plusieurs fois
et garde le meilleur ajustement. Après le remplissage, une passe
de complément tire les blocs « temps restant » de la playlist
contre l'écart restant, jusqu'à ce que la dernière ligne finisse à
moins de **4 secondes** de la fin de l'émission ou que plus rien ne
tienne. Lors des répétitions du 2026-10-01 l'écart était de 0–3 s
dans la plupart des cas et d'environ 6 s au pire (le solveur du
bloc est aléatoire ; le pool décide de ce qui est possible), jamais
une surréservation.

> **Sous le capot.** `AutoPlaylistManager::fillInstance()` étend
> lui-même les playlists (`expandPlaylist`), planifie avec
> `chainEnd()` — la règle de paire de `Scheduler::calculateCrossfades`
> — et n'insère que les lignes qui tiennent via
> `Scheduler::scheduleFilesAfter()`. La ligne de journal
> « show_instance_id=N filled - intro a, outro b, auto c (+d top-up)
> rows, x s free at the end » résume chaque build ;
> `ap_fill_test.php` (C:\Temp\optd) répète un remplissage sur une
> instance temporaire.

---

## 5. Choisir la bonne playlist pour autoloading

### Ce qui marche bien

- **Playlists smart-block-seulement** avec *Limiter à :
  Temps restant dans l'émission*. Le motif le plus
  courant : un smart block, un filtre ("genre = pop et
  bpm > 100"), une limite. Mis en page contre le
  temps réellement restant, ceci remplit toute longueur de
  créneau à quelques secondes près.

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
  smart blocks étendus, et la playlist est relancée tant que
  cela ajoute des lignes — strictement dans l'ordre, arrêt au
  premier titre qui ne tient pas.
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

Oui, mais l'intro est placée en premier, contre tout le
créneau libre, et l'outro juste après. Si le smart block de l'intro a la limite "temps
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
placez deux smart blocks — un par sélection — dans la
playlist du body. Un seul smart block ne peut proposer que
des alternatives du même champ (ex. genre Jazz ou Blues) ;
voir [Import/Export → blocks.json](./IMPORT_EXPORT.md#blocksjson).

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
