# Démarrage différé d'émission

> **Où vous êtes dans le manuel.** C'est un chapitre
> **Opération de diffusion quotidienne**, compagnon de
> [Calendrier](./CALENDAR.md). Lisez d'abord le chapitre
> Calendrier — l'unique interrupteur que cette fonctionnalité
> ajoute se trouve dans la section **Quand** du formulaire
> Nouvelle / Modifier l'émission, juste sous **Se répète ?**.

Normalement, chaque émission commence exactement à son créneau
de calendrier, et une émission qui a **plus de contenu planifié
que ne tient son créneau** voit simplement sa dernière piste
coupée à la fin du créneau (la pointe rouge solide sur la
[barre de remplissage du calendrier](./CALENDAR.md#1-la-page-calendrier)).
L'émission suivante commence quand même à l'heure.

Le **démarrage différé** change cela pour les émissions que vous
y inscrivez. Lorsque l'émission *précédant* la vôtre dépasse, une
émission inscrite **glisse plus tard** afin que l'émission
précédente puisse se terminer, au lieu d'être coupée. Vous cochez
une case par émission ; une tâche d'arrière-plan fait le reste,
quelques minutes avant l'antenne.

> **C'est une inscription volontaire et à sens unique.** Une
> émission ne glisse jamais que si **sa propre** case est cochée.
> Le glissement n'est jamais annulé automatiquement — voir §6. Si
> vous changez d'avis, décochez la case (les dépassements futurs
> cessent de la faire glisser) ou ramenez l'instance en arrière
> sur le calendrier.

---

## 1. Vue d'ensemble

```
   Créneau: │ Émis. A (créneau 1h) │ Émis. B (créneau 1h) │ Émis. C │
            08:00              09:00                  10:00     11:00

   A est surbooké — son contenu va en réalité jusqu'à 09:10.

   Sans démarrage différé (B non coché) :
            │ Émis. A ……✂ coupé │ Émis. B          │ Émis. C │
            08:00           09:00                 10:00
            La dernière piste de A est rognée à 09:00 ; B commence à l'heure.

   Avec démarrage différé (B coché) :
            │ Émis. A ……………… │ Émis. B       │ Émis. C │
            08:00          09:10           10:00    11:00
            A passe en entier jusqu'à 09:10. B garde sa FIN (10:00) et
            déplace son DÉBUT à 09:10, donc B dure 50 min au lieu de 60 et
            sa propre dernière piste peut être rognée. C commence toujours à 10:00.
```

Deux règles font toute la fonctionnalité :

1. **L'émission qui dépasse passe en entier.** La fin du créneau
   de l'émission A est étirée jusqu'à l'endroit où son contenu se
   termine réellement (09:10), donc le playout ne rogne plus la
   dernière piste de A.
2. **L'émission suivante inscrite garde sa FIN fixe et déplace son
   DÉBUT.** L'émission B passe désormais de 09:10 à 10:00 au lieu
   de 09:00 à 10:00. Ses items planifiés se déplacent avec elle ;
   ce qui ne tient plus avant 10:00 est coupé à la fin (le même
   compromis accepté que pour toute émission surbookée).

Une émission **sans** la case est un arrêt net : elle commence
toujours à l'heure, et l'émission qui la précède est rognée à son
début (la règle 1 ne s'applique pas par-delà une frontière non
inscrite).

---

## 2. Activer la fonctionnalité

Ouvrez **Nouvelle émission** ou **Modifier l'émission** et
dépliez la section **Quand**. Directement sous **Se répète ?** se
trouve :

```
   Quand
   ─────────────────────────────
   Début  [2026-06-15] [08:00]
   …
   Se répète ?                        [ ]
   Autoriser le démarrage différé ?   [x]   ◀── cocher pour laisser CETTE
                                       émission glisser
```

Cochez **« Autoriser le démarrage différé ? »** sur toute émission autorisée à commencer en retard lorsque l'émission
précédente a dépassé. Laissez-la décochée sur les émissions qui doivent
commencer exactement à l'heure (info au top horaire, un flux
réseau, une liaison live à heure fixe) — celles-ci deviennent les
ancres qui arrêtent un glissement (§4).

Pour une émission **récurrente**, la case fait partie de la
définition d'émission, donc elle s'applique à chaque épisode.
Quand un dépassement réel décale un épisode, seul **cet** épisode
est modifié (il devient une surcharge par occurrence) ; les autres
épisodes gardent leur créneau normal.

> **Comment ça marche sous le capot.** La coche est stockée dans
> le nouveau booléen `cc_show.allow_delayed_start` (migration
> legacy 0056). Il n'a pas d'accesseur Propel — le formulaire le
> lit et l'écrit via du SQL brut, le même schéma que les colonnes
> de song-request. Rien d'autre dans l'émission ne change quand
> vous la cochez ; la case ne compte que pour la tâche
> d'arrière-plan du §6.

### La playlist de remplissage (Settings → General)

Depuis le 27/09/2026, un second réglage optionnel existe pour toute
la station : **Settings → General → Show-Shift Filler Playlist**.
Choisissez une de vos playlists — idéalement de la musique de
longueurs variées — et le démarrage différé ne coupe plus de titres
d'émission : les titres qui ne tiennent plus sont remplacés par des
titres de remplissage.  Le §3 explique précisément ce qui se passe.
Laissez *(aucune — couper le dernier titre)* pour garder le
comportement de base.

---

## 3. Ce qui se passe quand une émission dépasse

Lorsque la tâche d'arrière-plan constate que le contenu planifié
de l'émission A se termine **après** le créneau de A, et que
l'émission suivante B a **Autoriser le démarrage différé ?** coché :

| | Avant | Après |
|---|---|---|
| **Fin de A** | 09:00 (créneau) | 09:10 (étendue à la fin du contenu) |
| **Début de B** | 09:00 | 09:10 (= fin du contenu de A) |
| **Fin de B** | 10:00 | **10:00 (inchangée)** |
| **Items de B** | 09:00 … | décalés de +10 min |

Ainsi A passe chaque piste qu'elle avait planifiée, et B commence
juste au moment où A se termine réellement. Comme la **fin de B
reste fixe**, B est de fait plus courte de dix minutes, et si B
était déjà pleine, sa dernière piste est rognée à 10:00 —
exactement ce qui serait arrivé à A sans la fonctionnalité. La
coupure se déplace simplement vers l'émission qui s'est inscrite
pour l'absorber.

> **Pourquoi garder la fin de B fixe ?** Pour qu'un seul
> dépassement ne se propage pas sans limite dans le reste de la
> journée. B abandonne ses dix premières minutes mais passe quand
> même le relais à ce qui suit à 10:00. C'était un choix délibéré
> plutôt que « repousser aussi la fin de B » (ce qui décalerait
> chaque émission ultérieure). Voir ARCHITECTURE §23.24.

### Remplissage au lieu de coupure (depuis le 27/09/2026)

Avec une playlist de remplissage configurée, l'émission décalée B
n'est plus simplement tronquée.  Une fois B déplacée à la fin du
contenu de A, la tâche regarde ce qui dépasse maintenant la fin de B
et fait trois choses :

1. **L'outro reste à sa place.**  Si B se termine par sa playlist
   d'outro — le *Select Outro Playlist* propre à l'émission, ou la
   valeur par défaut de la station dans Settings → General —, ces
   titres d'outro sont épinglés à la fin de B et jamais touchés.  Ce
   sont les titres *avant* l'outro qui sont remplacés, donc
   l'avant-dernier (ou plusieurs).  (Que les dernières lignes soient
   bien l'outro est vérifié contre les titres de la playlist, jamais
   supposé : une émission remplie à la main sans outro n'a simplement
   pas de fin protégée.)
2. **Chaque titre qui ne tient plus s'en va** — un ou plusieurs, en
   remontant depuis la fin du corps de B — jusqu'à ce que le reste
   tienne avant l'outro (ou avant la fin de B s'il n'y a pas d'outro).
3. **Le trou est comblé depuis la playlist de remplissage** avec la
   combinaison de titres dont la durée totale couvre le trou avec le
   moindre dépassement.  Le *dernier* titre de remplissage est coupé à
   la fin du trou.  Ainsi l'antenne n'est jamais silencieuse, et le
   seul titre jamais écourté est un titre de remplissage — jamais un
   titre de B.  Cela vaut même si le trou est plus court que le plus
   court des titres de remplissage : le plus court passe et est coupé.

L'échange se fait dans la même transaction que le décalage : soit
tout est appliqué, soit rien.  Le playout, le Dashboard, les widgets
et l'historique voient le résultat comme des lignes de grille
ordinaires.  Seule l'émission décalée B est traitée ainsi ; la fin de
l'émission A reste tronquée devant une ancre non activée (§4).

> **Exemple.**  B va de 10:00 à 11:00, se termine par un jingle
> d'outro de 30 secondes, et A dépasse de quatre minutes.  B commence
> maintenant à 10:04.  Son dernier titre musical finirait à 11:03:30 —
> il s'en va.  Le corps restant se termine à 10:59:10 ; le trou jusqu'à
> l'outro (qui doit commencer à 10:59:30) fait donc 20 secondes : le
> titre de remplissage le plus court passe et est fondu à 10:59:30,
> l'outro passe en entier, et ce qui suit démarre à 11:00 pile.

---

## 4. La cascade et l'ancre

Un gros dépassement peut s'étendre au-delà de plus d'une émission.
Le retard **se propage vers l'avant** à travers les émissions
inscrites consécutives :

```
   Créneau: │ A (surbooké → 09:40) │  B  │      C      │ D │
            08:00                09:00 09:30         10:30

   Le contenu de A va jusqu'à 09:40.

   • B (09:00–09:30, coché)  entièrement enseveli (09:40 > 09:30)
                             → VIDÉE, créneau laissé en « sautée »
   • C (09:30–10:30, coché)  partiellement enseveli (09:40 < 10:30)
                             → GLISSÉE à 09:40, garde sa fin 10:30 ;
                               la propagation S'ARRÊTE ici
   • D (10:30, …)            non affectée → commence à l'heure à 10:30
```

Une **émission sans la case** aurait au contraire arrêté la
propagation à son propre début : c'est une **ancre** dure qui
commence toujours à l'heure, et le contenu qui déborde devant elle
est rogné au début de l'ancre.

Deux choses peuvent arriver à chaque émission inscrite que le
dépassement atteint :

- **Partiellement ensevelie → elle glisse.** S'il reste du temps à
  l'émission après le dépassement (le dépassement se termine avant
  la propre fin de l'émission), elle glisse jusqu'à la fin du
  dépassement, garde sa fin, et la propagation **s'arrête là** —
  cette émission absorbe le reste.
- **Complètement ensevelie → elle est vidée.** Si le dépassement
  couvre tout le créneau de l'émission, l'émission ne peut pas
  passer du tout. Son contenu est vidé et le créneau vide est
  laissé sur le calendrier comme un **marqueur « sautée »** (§5).
  La propagation continue vers l'émission suivante.

La propagation se termine toujours à la **première émission sans
la case** — l'**ancre dure**. L'ancre commence exactement à
l'heure ; le contenu qui déborde devant elle est rogné au début de
l'ancre. Vous contrôlez donc jusqu'où un retard peut voyager
simplement en laissant la case décochée sur la prochaine émission
à heure fixe.

> **Conseil opérateur.** Placez une ancre décochée à chaque point
> de la journée qui ne doit pas bouger — l'info au top horaire, un
> flux syndiqué, le début de l'émission du matin. Tout ce qui se
> trouve entre deux ancres peut glisser ; rien ne franchit une
> ancre.

---

## 5. Une émission entièrement dépassée : le créneau sauté

Lorsqu'une émission est entièrement ensevelie par un dépassement
antérieur, elle est **vidée, pas supprimée** :

- ses items planifiés sont retirés (la barre de remplissage du
  créneau tombe à 0 %),
- le créneau vide **reste sur le calendrier** pour que vous
  puissiez voir que l'émission a été sautée plutôt que de
  disparaître silencieusement,
- une émission récurrente n'a que **ce seul épisode** vidé ; la
  série n'est pas touchée.

L'émission antérieure passe simplement à l'antenne pendant le
temps d'antenne du créneau sauté. Le marqueur est là pour que vous
le remarquiez après coup — p. ex. pour vous excuser à l'antenne,
ou pour resserrer l'émission surbookée la prochaine fois.

> **Comment ça marche sous le capot.** Vider une instance
> ensevelie reflète l'action **Vider le planning** pour une
> instance : ses lignes `cc_schedule` sont supprimées,
> `time_filled` est remis à zéro, l'instance est marquée
> `modified_instance` (pour que le régénérateur de répétitions
> laisse le trou tranquille), et `cc_files.is_scheduled` est
> retiré pour toute piste qui n'est plus planifiée nulle part.

---

## 6. Quand — et à quelle fréquence — le décalage se produit

Le décalage est effectué par une tâche d'arrière-plan, **pas** au
moment où vous enregistrez une émission :

- Une tâche (`ShowShiftTask`) tourne toutes les **2 minutes**.
- Elle n'agit que sur les dépassements dont l'émission affectée
  commence dans les **15 minutes** suivantes (le *lead*). Les
  émissions lointaines, que vous êtes peut-être encore en train de
  modifier, sont laissées intactes jusqu'à ce qu'elles approchent.
- Elle travaille à partir du **contenu planifié** (`cc_schedule`),
  donc elle s'applique de la même façon aux émissions que vous
  avez remplies à la main et à celles qu'une autoloading playlist
  a remplies.

La tâche est **idempotente et à sens unique** :

- La relancer ne change rien une fois qu'une émission se trouve
  déjà à la fin du dépassement — elle ne fait jamais dériver une
  émission davantage lors des sondages répétés.
- Un glissement n'est **jamais annulé automatiquement.** Si vous
  resserrez plus tard l'émission surbookée pour qu'elle ne dépasse
  plus, l'émission qui a déjà glissé reste où elle est jusqu'à ce
  que vous la rameniez (en la glissant sur le calendrier) ou que
  le créneau soit régénéré. Ce comportement « à sens unique » a
  été choisi pour garder la fonctionnalité simple et prévisible ;
  il n'y a pas d'état caché se souvenant du créneau d'origine de
  chaque émission.

> **L'historique de playout reste correct automatiquement.** Le
> décalage se produit *avant* l'antenne, et l'historique de
> playout enregistre ce qui a **réellement** été diffusé et quand
> (heure horloge), pas les heures de créneau planifiées. Ainsi une
> émission passée en retard est journalisée à son heure d'antenne
> réelle sans comptabilité supplémentaire.

> **Comment ça marche sous le capot.**
> `Application_Service_ShowShiftService::applyDelayedStarts()`
> sélectionne les instances en surbooking, non
> `modified_instance`, dont la fin de créneau est dans la fenêtre
> de lead, puis parcourt chacune vers l'avant : vidant les
> émissions cochées entièrement dépassées, faisant glisser la
> première émission cochée partiellement dépassée (début → fin du
> contenu, fin fixe, items décalés via
> `SchedulerService::updateScheduleStartTime`, marquée
> `modified_instance`), et s'arrêtant à la première ancre non
> cochée. La fin propre de l'émission en surbooking est étendue
> jusqu'à l'endroit où son contenu s'est posé. L'intervalle et le
> lead sont surchargeables avec
> `RASTATIME_SHOW_SHIFT_INTERVAL_SECONDS` (défaut 120) et
> `RASTATIME_SHOW_SHIFT_LEAD_SECONDS` (défaut 900). Voir
> ARCHITECTURE §23.24.

---

## 7. À savoir

- **Une émission que vous avez déplacée à la main n'est pas
  elle-même une origine de glissement.** Si vous glissez une
  émission sur le calendrier, elle devient une surcharge par
  occurrence (`modified_instance`). La tâche ne traitera pas une
  telle émission comme la *source* d'une nouvelle propagation —
  mais elle la fera **quand même** glisser ou la videra lorsqu'une
  émission antérieure déborde dedans. Cela empêche le glissement
  automatique de contrarier vos modifications manuelles, en
  cohérence avec la façon dont les instances éditées à la main
  sont laissées tranquilles par les autres passages automatiques.
- **Seule la case de l'émission suivante compte à chaque étape.**
  Que l'émission A elle-même soit cochée n'a aucune importance
  pour savoir si le dépassement de A pousse B — ce qui compte,
  c'est la case de B. (La case de A ne compte que lorsque
  l'émission *précédant* A déborde dans A.)
- **Un trou absorbe un dépassement gratuitement.** S'il y a du
  temps vide après l'émission surbookée, son contenu se diffuse
  simplement dans le trou ; aucune émission suivante n'a besoin de
  bouger, et rien n'est modifié.

---

## 8. Liste de contrôle de l'opérateur

Pour laisser un bloc du planning glisser quand une émission
dépasse :

1. **Cochez « Autoriser le démarrage différé ? »** sur chaque
   émission qui peut commencer en retard — dans la section
   **Quand** de son formulaire Nouvelle / Modifier l'émission.
2. **Laissez-la décochée** sur chaque émission à heure fixe qui
   doit commencer pile à l'heure (info, flux, liaisons live). Ce
   sont vos ancres.
3. C'est tout. Quelques minutes avant l'antenne, un dépassement
   devant une émission cochée la fait glisser automatiquement ; la
   coupure atterrit sur l'émission cochée plutôt que sur la
   surbookée, et rien ne franchit une ancre décochée.

Il n'y a rien à configurer au-delà de la case par émission.

---

## 9. Foire aux questions

### « J'ai coché la case mais mon émission a quand même commencé à l'heure. »

Alors l'émission qui la précède n'a pas dépassé (son contenu
tenait dans son créneau), ou il y avait un trou qui a absorbé le
dépassement, ou le dépassement était plus court qu'une seconde. La
case ne fait quelque chose que lorsque l'émission précédente
déborde réellement **dans** la vôtre.

### « Mon émission a glissé plus tard et sa dernière piste a été coupée. »

C'est la conception : l'émission glissée garde sa **fin** fixe,
donc elle est plus courte et rogne sa fin — la coupure se déplace
de l'émission surbookée vers celle qui s'est inscrite pour
l'absorber. Planifiez un peu moins de contenu, ou acceptez le
rognage.

### « Toute une émission a été sautée — son créneau est vide. »

Elle a été entièrement ensevelie par un dépassement antérieur et a
été **vidée** vers un marqueur de créneau sauté (§5). L'émission
antérieure a diffusé pendant son temps d'antenne. Resserrez
l'émission surbookée, ou placez une ancre décochée plus tôt pour
que le dépassement soit rogné avant d'atteindre cette émission.

### « J'ai raccourci l'émission surbookée mais la suivante est toujours en retard. »

Les glissements sont à sens unique (§6) — ils ne sont pas remontés
automatiquement. Ramenez l'émission glissée à son créneau sur le
calendrier, ou attendez que le créneau soit régénéré.

### « Jusqu'où un seul dépassement peut-il pousser le planning ? »

Jusqu'à la première émission **sans** la case. Tout ce qui se
trouve entre deux ancres décochées peut glisser ; rien ne franchit
une ancre. Placez les ancres pour borner la propagation.

### « Une émission en retard perturbe-t-elle l'historique de playout / le now-playing ? »

Non. Le décalage se produit avant l'antenne et l'historique
journalise les heures d'antenne réelles, donc une émission en
retard est rapportée à l'heure où elle a réellement passé.

---

## Où aller ensuite

* [Calendrier](./CALENDAR.md) — le formulaire d'émission, la
  section **Quand**, la barre de remplissage dont la pointe rouge
  marque une émission surbookée.
* [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) — une
  manière courante pour une émission de se retrouver surbookée (une
  dramaturgie qui remplit un peu trop).
* [Modèles d'émission](./SHOW_TEMPLATES.md) — intégrez « Autoriser
  le démarrage différé » dans un modèle pour qu'une classe entière
  d'émissions s'inscrive d'un coup.
