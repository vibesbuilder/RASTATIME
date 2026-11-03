# Publication : équipe de rédaction, épisodes, participants

> **Où vous en êtes dans le manuel.** Paramètres → **Équipe de
> rédaction** ; Calendrier → formulaire de l'émission, section
> **Publication** ; Calendrier → clic droit sur une occurrence →
> **Épisode...** ; Statistiques → **Participants** (dans l'interface
> anglaise : Settings → Editorial Team, Publishing, Episode...,
> Analytics → Participants).  Lisez d'abord [Calendrier](./CALENDAR.md)
> et [Enregistrement par émission](./RECORD_PER_SHOW.md) - le son d'un
> épisode est l'enregistrement de l'émission.
>
> **Ce que prépare cette fonction.** Publier chaque épisode sur
> [cba.media](https://cba.media) (l'archive des radios libres
> autrichiennes) sans le téléverser à la main, et le décompte annuel
> des personnes qui font le programme.

Depuis le 2026-11-03, RASTATIME conserve les données dont un épisode
publié a besoin : qui fait une émission, les réglages par défaut de son
podcast sur cba.media et, par épisode, un titre, une accroche, une
description et une image facultative.  Les mêmes données alimentent la
vue **Participants** pour les statistiques annuelles.

**Rien n'est encore téléversé.**  L'envoi des épisodes vers cba.media -
à la main depuis le calendrier et automatiquement après
l'enregistrement - suit dans les prochaines étapes ; ce chapitre
grandira avec elles.

Un *épisode* est une occurrence d'une émission dans le calendrier : la
« Matinale » de lundi prochain est un épisode, celle du lundi suivant
le suivant.

---

## 1. Profils de l'équipe de rédaction

**Paramètres → Équipe de rédaction** liste les personnes derrière les
émissions.

| Champ | Signification |
|---|---|
| **Nom** | Tel qu'il doit apparaître sur cba.media et dans les statistiques. |
| **E-mail (facultatif)** | Pour votre propre usage. |
| **Utilisateur (facultatif)** | Relie le profil à un compte RASTATIME. Un profil n'a pas besoin de compte - la plupart des rédacteurs ne se connectent jamais. |
| **Actif** | Seuls les profils actifs sont proposés dans le formulaire de l'émission.  Un profil désactivé reste dans les émissions auxquelles il appartient déjà. |

**Edition** charge le profil dans le formulaire au-dessus du tableau ;
**Supprimer** retire le profil de l'équipe de chaque émission après
confirmation.  La colonne **Émissions** compte les émissions d'un
profil.

Les Program Managers et les Admins ouvrent cette page.

---

## 2. Réglages de l'émission : section « Publication »

Modifiez une émission (calendrier → clic droit → **Modifier
l'émission**, ou une nouvelle émission) et ouvrez la section
**Publication**, entre **Who** et **Style**.  Les valeurs valent pour
chaque épisode de l'émission tant qu'un épisode ne définit pas les
siennes.

| Champ | Signification |
|---|---|
| **Équipe de rédaction** | Cochez les profils des personnes derrière l'émission. Elles sont transmises à cba.media comme rédacteurs et apparaissent dans la vue Participants. |
| **Participants** | Combien de personnes participent habituellement à un épisode (0-999). Compte dans Statistiques → Participants. |
| **ID du podcast CBA** | Le numéro du podcast (série) sur cba.media auquel appartiennent les épisodes. |
| **Licence** | Licence par défaut des épisodes : Tous droits réservés, CC BY-NC-ND, CC BY-ND, CC BY-NC, CC BY-SA, CC BY, CC0, Domaine public. |
| **ID du thème CBA** | Le numéro du thème (catégorie) sur cba.media. |
| **Langues** | Jusqu'à trois codes de langue, p. ex. `de, en`. |
| **Mots-clés** | Mots-clés pour cba.media, séparés par des virgules. |
| **Accroche par défaut** | Utilisée pour chaque épisode sans accroche propre. |
| **Contient de la musique protégée (AKM)** | Les épisodes contiennent habituellement de la musique protégée par le droit d'auteur. |

La section n'apparaît pas dans **Modifier l'occurrence** : elle
appartient à l'émission entière.  Les données d'un seul épisode se
modifient dans la boîte de dialogue **Épisode...** (§3).

> **D'où viennent les numéros CBA ?**  Ouvrez le podcast ou le thème
> sur cba.media ; le numéro figure dans son adresse ou sur sa page.  La
> prochaine étape proposera une liste de choix.

---

## 3. Données de l'épisode : « Épisode... »

Clic droit sur une occurrence dans le calendrier → **Épisode...**.
L'entrée est disponible avant et après la diffusion - l'image peut être
ajoutée après l'émission - pour les Admins, les Program Managers et les
animateurs de l'émission.

| Champ | Signification |
|---|---|
| **Titre** | Vide : le nom de l'émission et la date, affichés en gris comme suggestion. |
| **Accroche** | Un court résumé. Vide : l'accroche par défaut de l'émission. |
| **Description** | Le texte de l'épisode - le même champ que **Description de l'instance** dans le formulaire de l'émission. |
| **Participants** | Seulement si cet épisode diffère de l'émission, p. ex. avec des invités. La valeur de l'émission apparaît en gris. |
| **Image de l'épisode** | Facultative, JPG ou PNG jusqu'à 10 Mo. Choisir un fichier le téléverse aussitôt ; **Retirer l'image** le supprime. Sans image, cba.media affiche celle du podcast. |
| **Licence de l'image** / **Légende** | Licence et crédit de l'image (p. ex. le photographe). |

La colonne de droite montre aussi ce que l'épisode reprend de
l'émission (équipe de rédaction, ID du podcast CBA, licence), et la
ligne du haut indique si l'épisode a été diffusé et si son
enregistrement est dans la bibliothèque.

**Sauvegarder** enregistre les champs de texte ; l'image est
enregistrée dès qu'elle est choisie.  Les images d'épisode se trouvent
dans le dossier de la bibliothèque sous
`imported/episode-images/<occurrence>/` et font partie du miroir des
médias de la [Sauvegarde](./BACKUP.md).

> **Planifier près de la diffusion.**  Quand le rythme de répétition
> d'une émission change, le calendrier recrée ses occurrences futures,
> et leurs données d'épisode disparaissent avec elles.  Saisissez
> titres et images pour les prochaines semaines plutôt que des mois à
> l'avance.

---

## 4. Vue des participants

**Statistiques → Participants** compte les participants par émission et
par année (heure de la station) - les chiffres des statistiques
annuelles.

* **Année** - l'année en cours montre le décompte à ce jour.
* **Seulement les émissions sans valeur** - les émissions diffusées qui
  n'ont pas encore de *Participants*.  Traitez cette liste une fois ;
  mettez `0` pour les programmes automatisés ou relayés.
* **Télécharger le CSV** - le tableau et les totaux comme fichier de
  tableur.

Comptent les épisodes **diffusés** dans l'année (terminés, non
supprimés).  Les rediffusions de l'ancien type LibreTime sont exclues ;
les émissions configurées comme [répétition d'une autre
émission](./CALENDAR.md) apparaissent avec la mention **Rediffusion** -
mettez leur valeur à `0` si leurs personnes comptent déjà dans
l'original.

| Colonne / total | Signification |
|---|---|
| **Épisodes diffusés** | Épisodes de l'émission dans l'année. |
| **Participants** | La valeur de l'émission ; le total additionne les valeurs de toutes les émissions. |
| **Épisodes avec valeur propre** | Épisodes dont la boîte de dialogue fixe un autre nombre. |
| **Participations** | Les participants de chaque épisode additionnés (un épisode avec sa propre valeur compte avec celle-ci). |
| **Profils de rédaction** (total) | Profils distincts dans les équipes des émissions diffusées - chaque personne une fois. |
| **Émissions sans valeur** (total) | En orange tant qu'il y en a. |

Une personne présente dans plusieurs émissions compte une fois par
émission dans **Participants** ; le total des profils compte chaque
personne une seule fois.

Les Program Managers et les Admins ouvrent cette page.

---

## 5. Questions fréquentes

### « J'ai coché des profils, mais ils n'apparaissent pas dans la vue. »

La vue ne liste que les émissions **diffusées** dans l'année choisie.
Une nouvelle émission apparaît dès que son premier épisode est terminé.

### « La section Publication manque ou est grisée. »

Elle manque dans **Modifier l'occurrence** - la section appartient à
l'émission entière ; pour un épisode, utilisez **Épisode...**.  Elle est
grisée si vous n'êtes ni Program Manager ni Admin.

### « Épisode... manque dans le menu. »

L'entrée apparaît pour les Admins, les Program Managers et les
animateurs de l'émission, et pas sur les occurrences de rediffusion de
l'ancien type LibreTime.

---

## Pour aller plus loin

* [Calendrier](./CALENDAR.md) - le formulaire de l'émission et le menu
  contextuel.
* [Enregistrement par émission](./RECORD_PER_SHOW.md) - l'enregistrement
  qui devient le son de l'épisode.
* [Analytics](./ANALYTICS.md) - les autres pages de statistiques.
* [Paramètres](./SETTINGS.md) - chaque page du menu Paramètres.
