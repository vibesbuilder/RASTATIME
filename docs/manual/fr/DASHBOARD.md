# Tableau de bord

> **Où vous êtes dans le manuel.** Le tableau de bord est
> la première page que les opérateurs atteignent après
> connexion. Il montre l'état de la station en un coup
> d'œil et offre les surcharges manuelles qui ne
> nécessitent pas d'aller au Calendrier.

Le **Tableau de bord** répond à trois questions en un
écran :

1. Qu'est-ce qui est à l'antenne *maintenant* ?
2. Qu'est-ce qui vient *ensuite* ?
3. Les streams publics sont-ils en bonne santé ?

Un quatrième panneau — les contrôles **Source Live** — est
le sas de secours de l'opérateur pour mettre la station
en direct sans ouvrir un client de diffusion séparé.

---

## 1. La mise en page

Tableau de bord → par défaut la vue live. La page se
rafraîchit toutes les 5 secondes (configurable dans le
menu déroulant en haut à droite — 1 / 5 / 10 / 30 secondes
ou Manuel).

---

## 2. En cours

Le plus grand panneau. Montre l'item de planning actuel
plus le contexte de ce qui alimente le stream public.

### Champs

| Champ | Signification |
|---|---|
| **♪ Titre — Artiste** | Métadonnées de l'item en cours de lecture. |
| **Émission** | L'émission à laquelle cet item appartient + pourcentage de remplissage global de l'émission. |
| **Source** | Quelle entrée le source switcher route actuellement — voir §3. |
| **Barre de progression** | Temps écoulé / durée de l'item. |

> **Pourquoi le pourcentage de remplissage est important.**
> Une émission à 60 % remplie a 40 % de son créneau vide.
> Quand la piste actuelle se termine, le playout atteint
> la queue vide et tombe sur silence (ou Auto DJ si
> activé).

### Apparence de surcharge Live-DJ

Quand une source Live-DJ est active, le panneau change :
pas de titre de piste (la source live est audio ouvert),
pas de barre de progression, et un indicateur clair "🎙
LIVE" pour que l'opérateur voie en un coup d'œil que le
planning n'est pas ce qui diffuse.

> **Comment ça marche sous le capot.** Le panneau En
> cours consomme `/api/v2/now-playing` qui renvoie l'état
> actuel du source switcher plus l'item de planning
> actif. L'endpoint lit depuis `rastatime_playback_state`
> qui est écrit par le moteur de playout à chaque
> transition piste / source. Voir ARCHITECTURE §9.

---

## 3. État de source

Le champ **Source** sur le panneau En cours parcourt cinq
états possibles. Savoir lequel est à l'antenne en ce
moment fait la différence entre "le stream fonctionne" et
"le stream fonctionne mais diffuse la mauvaise chose".

| Source | Ce que ça signifie | Quand s'inquiéter |
|---|---|---|
| **Scheduler** | Playout joue ce que le calendrier dit. L'état normal. | Jamais. C'est l'objectif. |
| **Show DJ** | Une source distante live a pris l'émission. | Si vous n'attendez pas qu'un Show DJ soit live — enquêter. |
| **Master DJ** | Source live au niveau station a tout surchargé. | Master DJ ne devrait être à l'antenne que quand l'ingénieur a intentionnellement pris le relais. |
| **Auto DJ** | Remplissage Auto-DJ est à l'antenne. | Si vous attendiez du contenu planifié par l'opérateur — ouvrez le Calendrier. |
| **Fallback / Silence** | Rien n'est planifié, Auto DJ est désactivé. | Presque toujours un problème. Ouvrez le Calendrier. |

### Basculer la source manuellement

Le basculement de source n'est **pas** contrôlé par
l'opérateur côté tableau de bord — il est piloté par le
moteur de playout en réponse au calendrier, à un DJ
distant qui se connecte, ou à l'intervention d'Auto-DJ.

Pour **forcer** un basculement : **Annuler l'émission
actuelle** termine l'émission en cours immédiatement.
**Retirer Master DJ de l'antenne** déconnecte la source
Master.

---

## 4. Vient ensuite

Les 3-5 prochains items à venir (configurable sous
Préférences générales → Vue d'avance du tableau de bord).

Chaque ligne montre l'heure, le nom de l'émission et le
pourcentage de remplissage.

> **Conseil opérateur.** Un remplissage "0 %" ou "—" sur
> une émission qui démarre bientôt est un problème.
> Cliquez l'émission dans le calendrier et remplissez-la
> manuellement, ou comptez sur Auto DJ.

---

## 5. Streams

Vue compacte des mêmes informations que vous obtenez de
Paramètres → [Streams](./STREAMS.md) : N. /mount + badge
d'état + compteur d'auditeurs.

Cliquez sur un stream → ouvre la page paramètres Streams
avec focus sur ce stream.

> **Conseil opérateur.** Cette vue compacte est ce que
> la plupart des opérateurs regardent pendant une
> émission — compteurs d'auditeurs en hausse signifient
> que l'émission atteint des gens. Chute brusque (ex. de
> 50 à 5) signifie que les auditeurs décrochent ;
> vérifiez l'état du stream et l'audio à l'antenne.

---

## 6. Panneau Source Live

Deux contrôles + deux lignes d'état.

### Case Master DJ à l'antenne

La case à cocher en haut à droite bascule la surcharge
Master-DJ :

| Case | Effet |
|---|---|
| **Désactivée** (défaut) | Master DJ est muet au source switcher même si connecté. |
| **Activée** | Master DJ est à l'antenne si connecté. Toute entrée du source switcher est surchargée. |

> **Pourquoi une case et pas juste "connecté = à
> l'antenne" ?** Le modèle LibreTime d'origine était
> "Master DJ à l'antenne quand connecté" ; RASTATIME
> 2026-05-15 a ajouté le toggle explicite après le
> feedback opérateur qu'un ingénieur testant une
> connexion ne devrait pas accidentellement prendre une
> émission live.

### Lignes d'état Show DJ / Master DJ

Chaque ligne montre **Non connecté**, **Connecté (en
attente)**, ou **Connecté (à l'antenne)**.

### Écouter le moniteur

Joue la sortie moniteur de la
[Machine locale](./LOCAL_MACHINE.md) via votre navigateur.

### Annuler l'émission actuelle

Termine l'émission actuellement en lecture
**immédiatement**.

Effets : `cc_show_instances.ends_at` est défini sur
"maintenant", le source switcher avance, si l'émission
était enregistrée, l'enregistrement s'arrête
gracieusement, un Show DJ connecté est éjecté.

> **Conseil opérateur.** Utilisez **Annuler l'émission
> actuelle** avec parcimonie — l'annulation est
> irréversible. Pour rendre une émission plus courte sans
> la terminer immédiatement, modifiez l'émission dans le
> calendrier et changez l'heure de fin.

---

## 7. Foire aux questions

### "Le panneau En cours dit 'Silence'. Qu'est-ce que ça signifie ?"

Le moteur de playout tourne, aucune émission n'est
actuelle, aucun Auto DJ n'est activé, et aucune boucle
fallback n'est configurée.

Solution : Ouvrir le Calendrier et planifier une
émission, ou activer [Auto DJ](./AUTO_DJ.md).

### "La source est 'Scheduler' mais je n'entends rien."

Trois possibilités : l'item planifié actuel est lui-même
silencieux ; la connexion Icecast est ouverte mais
l'encodage est silencieux (problème de périphérique
audio côté machine opérateur) ; l'onglet du navigateur
est muet.

### "Pourquoi la page traîne-t-elle parfois quelques secondes derrière la réalité ?"

L'endpoint En cours se rafraîchit toutes les 5 secondes.
Pour une précision à la sous-seconde, il faudrait un
endpoint streaming (websocket / SSE) ; pas implémenté
actuellement.

### "Puis-je voir le Tableau de bord sans me connecter ?"

Non — le Tableau de bord nécessite authentification.
Pour une page publique "qu'est-ce qui passe" non
authentifiée, utilisez le widget embed à
`/embed/now-playing`.

### "Pourquoi le compteur d'auditeurs tombe à zéro pour un cycle de rafraîchissement ?"

Icecast réinitialise brièvement le compteur d'auditeurs
quand la source se reconnecte. Le prochain
rafraîchissement de 5 s montre à nouveau le compteur.

---

## Où aller ensuite

* [Calendrier](./CALENDAR.md) — ce qui peuple "Vient
  ensuite".
* [Streams](./STREAMS.md) — détail complet sur chaque
  stream de sortie.
* [Auto DJ](./AUTO_DJ.md) — ce qui remplit les trous
  quand aucune émission n'est actuelle.
* [Machine locale](./LOCAL_MACHINE.md) — la sortie
  moniteur utilisée par le bouton **Écouter le
  moniteur**.
