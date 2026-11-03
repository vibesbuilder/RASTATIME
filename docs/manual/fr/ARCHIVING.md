# Archivage : équipe de rédaction, épisodes, archive en ligne, participants

> **Où vous en êtes dans le manuel.** Paramètres → **Équipe de
> rédaction** et **Comptes CBA** ; Calendrier → formulaire de
> l'émission, section **Archivage** ; Calendrier → clic droit sur une
> occurrence → **Épisode...** ; Statistiques → **Participants** (dans
> l'interface anglaise : Settings → Editorial Team / CBA Accounts,
> Archiving, Episode..., Analytics → Participants).  Lisez d'abord
> [Calendrier](./CALENDAR.md) et
> [Enregistrement par émission](./RECORD_PER_SHOW.md) - le son d'un
> épisode archivé est l'enregistrement de l'émission.
>
> **Ce que fait cette fonction.** Elle archive les épisodes de vos
> émissions sur [cba.media](https://cba.media) (l'archive des radios
> libres autrichiennes) sans téléversement à la main, et compte les
> personnes qui font le programme pour les statistiques annuelles.
>
> **Pourquoi « Archivage ».** Dans RASTATIME, « publier » désigne le
> podcast de la station (My Podcast).  Mettre un épisode sur cba.media
> s'appelle donc *archiver en ligne*, pour ne pas confondre les deux.

Un *épisode* est une occurrence d'une émission dans le calendrier : la
« Matinale » de lundi prochain est un épisode, celle du lundi suivant
le suivant.

**Où en sont les étapes.**

| Étape | Quoi | État |
|---|---|---|
| 1 | Équipe de rédaction, réglages de l'émission, données d'épisode, participants | depuis le 2026-11-03 |
| 2 | Archiver un épisode en ligne à la main depuis le calendrier | depuis le 2026-11-03 |
| 3 | Archiver chaque épisode automatiquement après l'enregistrement | depuis le 2026-11-03 |

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

## 2. Comptes CBA

Chaque émission est archivée sous un utilisateur cba.media - les
épisodes apparaissent sous son nom.  **Paramètres → Comptes CBA**
contient ces utilisateurs ; seuls les Admins ouvrent la page.

| Champ | Signification |
|---|---|
| **Nom du compte** | Votre nom pour le compte, p. ex. la personne ou la station. |
| **Nom d'utilisateur CBA** | Le nom d'utilisateur sur cba.media. |
| **Mot de passe d'application** | Créé sur cba.media dans le profil de l'utilisateur (*mot de passe d'application* WordPress, pas le mot de passe de connexion). RASTATIME l'enregistre et ne l'affiche plus jamais ; un champ vide garde celui enregistré. |

* **Tester la connexion** demande à cba.media, avec les données
  enregistrées, qui est l'utilisateur et s'il peut téléverser (rôles
  admin, author, podcaster, stationmanager, channelmanager).  Rien n'est
  téléversé.
* **Supprimer** retire le compte ; les émissions qui l'utilisent n'ont
  plus de compte jusqu'à ce que vous en choisissiez un autre.
* **Limite d'envoi** - l'envoi partage la ligne internet avec les flux
  des auditeurs ; RASTATIME envoie donc au plus à ce débit (par défaut
  4 Mbit/s : une heure d'audio à 320 kbit/s prend environ cinq minutes).
* **Archivage automatique** - combien de minutes après la fin d'un
  épisode les émissions avec *Archiver automatiquement* (§3) l'envoient
  (par défaut 30) : le temps de compléter l'épisode ou de cocher *Ne pas
  archiver cet épisode automatiquement*.

---

## 3. Réglages de l'émission : section « Archivage »

Modifiez une émission (calendrier → clic droit → **Modifier
l'émission**, ou une nouvelle émission) et ouvrez la section
**Archivage**, entre **Who** et **Style**.  Les valeurs valent pour
chaque épisode de l'émission tant qu'un épisode ne définit pas les
siennes.

| Champ | Signification |
|---|---|
| **Équipe de rédaction** | Cochez les profils des personnes derrière l'émission. Elles sont transmises à cba.media comme rédacteurs et apparaissent dans la vue Participants. |
| **Participants** | Combien de personnes participent habituellement à un épisode (0-999). Compte dans Statistiques → Participants. |
| **Compte CBA** | L'utilisateur CBA sous lequel les épisodes sont archivés (§2). |
| **Visibilité sur cba.media** | *Public* (répertorié), *Non répertorié* (accessible seulement par son adresse) ou *Privé* (visible seulement par l'utilisateur CBA). |
| **ID du podcast CBA** | Le numéro du podcast (série) sur cba.media auquel appartiennent les épisodes. Sans lui, cba.media garde l'article privé. |
| **Licence** | Licence des épisodes. L'icône d'aide montre quelle licence répond aux questions du formulaire web de la CBA (voir ci-dessous). |
| **Thème CBA** | Le thème (catégorie) sur cba.media, choisi dans la liste que RASTATIME récupère une fois par jour. Avant la première récupération, le champ prend le numéro. |
| **Langues** | Jusqu'à trois codes de langue connus de la CBA, p. ex. `de, en`. |
| **Mots-clés** | Mots-clés pour cba.media, séparés par des virgules. |
| **Accroche par défaut** | Utilisée pour chaque épisode sans accroche propre. |
| **Contient de la musique protégée (AKM)** | Les épisodes contiennent habituellement de la musique protégée ; cba.media restreint alors le téléchargement. |
| **Archiver automatiquement** | Archiver chaque nouvel épisode sur cba.media tout seul (§5, *Automatiquement*). Nécessite un compte CBA, un thème, une langue et une licence ; à côté de la case : depuis quand elle est activée. Si l'émission n'a pas de description, une remarque sous la case indique que chaque épisode a alors besoin de la sienne. |

**Quelle licence ?**  Le formulaire web de la CBA pose trois questions ;
la licence y répond :

| Licence | Citer l'auteur ? | Usage commercial ? | Adaptations ? |
|---|---|---|---|
| CC BY | oui | oui | oui |
| CC BY-NC | oui | non | oui |
| CC BY-ND | oui | oui | non |
| CC BY-NC-ND | oui | non | non |
| CC0 | non | oui | oui |

*Tous droits réservés* n'autorise rien de cela sans demander ;
*CC Sampling+* permet de réutiliser des extraits, l'œuvre entière
seulement à des fins non commerciales ; *Domaine public* ne garde aucun
droit.

La section n'apparaît pas dans **Modifier l'occurrence** : elle
appartient à l'émission entière.  Les données d'un seul épisode se
modifient dans **Épisode...** (§4).

> **D'où vient le numéro du podcast ?**  Ouvrez le podcast sur
> cba.media ; le numéro figure dans son adresse ou sur sa page (la CBA
> ne liste les podcasts d'une station qu'aux utilisateurs connectés).

---

## 4. Données de l'épisode : « Épisode... »

Clic droit sur une occurrence dans le calendrier → **Épisode...**.
L'entrée est disponible avant et après la diffusion - l'image peut être
ajoutée après l'émission - pour les Admins, les Program Managers et les
animateurs de l'émission.

| Champ | Signification |
|---|---|
| **Titre** | Vide : le nom de l'émission et la date, affichés en gris comme suggestion. |
| **Accroche** | Un court résumé. Vide : l'accroche par défaut de l'émission. |
| **Description** | Le texte de l'épisode, sur cba.media le texte de l'article. Vide : la description de l'émission. C'est le seul endroit pour la modifier (Modifier l'occurrence ne l'affiche plus). |
| **Participants** | Seulement si cet épisode diffère de l'émission, p. ex. avec des invités. La valeur de l'émission apparaît en gris. |
| **Date de production** | Exigée par cba.media. Vide : le jour de la diffusion. À renseigner si l'épisode a été produit plus tôt. |
| **Ne pas archiver cet épisode automatiquement** | Pour les tests, les épisodes annulés ou les problèmes de droits. S'applique avec l'archivage automatique (§5) ; l'archivage manuel reste possible. |
| **Image de l'épisode** | Facultative, JPG ou PNG jusqu'à 10 Mo. Choisir un fichier le téléverse aussitôt ; **Retirer l'image** le supprime. Sans image, cba.media affiche celle du podcast. |
| **Licence de l'image** / **Légende** | Licence et crédit de l'image (p. ex. le photographe), légende jusqu'à 500 caractères. |

La colonne de droite montre ce que l'épisode reprend de l'émission
(équipe de rédaction, compte CBA, podcast, licence, visibilité) ; la
ligne du haut indique si l'épisode a été diffusé et si son
enregistrement est dans la bibliothèque.

**Sauvegarder** enregistre les champs de texte ; l'image est enregistrée
dès qu'elle est choisie.  Les images d'épisode se trouvent dans le
dossier de la bibliothèque sous `imported/episode-images/<occurrence>/`
et font partie du miroir des médias de la [Sauvegarde](./BACKUP.md).

> **Planifier près de la diffusion.**  Quand le rythme de répétition
> d'une émission change, le calendrier recrée ses occurrences futures,
> et leurs données d'épisode disparaissent avec elles.  (**Modifier
> l'occurrence** d'un seul épisode les conserve.)  Saisissez titres et
> images pour les prochaines semaines plutôt que des mois à l'avance.

---

## 5. Archiver en ligne

Le bloc du bas de **Épisode...** - **Archive en ligne (cba.media)** -
montre l'état de l'épisode sur cba.media.  Les Admins et les Program
Managers archivent d'ici ; les animateurs voient l'état.

1. Complétez ce que le bloc liste sous *Avant de pouvoir archiver cet
   épisode* - en général le compte CBA, le thème, la langue et la
   licence de l'émission et une description.
2. Cliquez **Archiver en ligne...** et choisissez le son :
   * **L'enregistrement de cet épisode** - la copie que
     [Enregistrement par émission](./RECORD_PER_SHOW.md) a mise dans la
     bibliothèque ;
   * **Un fichier de la bibliothèque** - recherche par titre ou auteur,
     p. ex. le fichier préproduit sans jingles (MP3, OGG et Opus
     seulement ; la CBA n'accepte pas le M4A).
3. **Démarrer le Téléversement**.  Le service en arrière-plan
   (RASTATIME-WORKER) prend la tâche en charge en 15 secondes environ ;
   le bloc montre la progression puis le lien vers l'article.

Le titre, l'accroche, la description, l'image et les réglages de
l'émission sont lus au début de l'envoi.  **Les modifications après
l'envoi se font sur cba.media** - l'interface de la CBA ne permet ni de
modifier ni de remplacer un article.

| État | Signification, que faire |
|---|---|
| *En attente de l'envoi* | Ajouté ; le worker le démarre sous peu. |
| *Envoi vers cba.media : n %* | En cours, limité à la limite d'envoi (§2). |
| *Archivé sur cba.media comme article n* | Terminé ; le numéro mène à l'article. |
| *En attente d'une nouvelle tentative* | cba.media était injoignable ou occupé ; RASTATIME réessaie après 2, 5, 15, 30 minutes ... pendant 24 heures au plus. |
| *L'envoi a échoué : raison* | Données manquantes, ou cba.media a refusé (p. ex. mauvais mot de passe d'application, thème inconnu). Corrigez la cause et **Archiver en ligne...** à nouveau. |
| *Impossible de savoir si l'article a été créé* | La connexion s'est coupée pendant l'envoi. L'article existe peut-être - vérifiez sur cba.media, puis **Lier un article existant** ou archivez à nouveau. RASTATIME ne répète jamais ce cas tout seul, pour qu'aucun épisode n'apparaisse deux fois. |

**Lier un article existant** prend le numéro d'un article sur cba.media
(ou son adresse avec `?p=<numéro>`), p. ex. pour un épisode téléversé
autrefois à la main ; un champ vide retire le lien.  Un épisode lié
compte comme archivé.

> **Arrêter le worker** ne fait que suspendre les envois ; la diffusion
> n'est pas touchée.  Une tâche en cours est vérifiée après le
> redémarrage : si aucun octet n'était parti, elle recommence, sinon
> elle se termine comme *impossible de savoir*.

### Automatiquement

Si **Archiver automatiquement** est coché dans la section *Archivage*
de l'émission (§3), RASTATIME archive tout seul chaque nouvel épisode,
toujours avec l'enregistrement :

1. L'épisode se termine ; [l'enregistrement par émission](./RECORD_PER_SHOW.md)
   place l'enregistrement dans la bibliothèque en quelques secondes
   (l'émission doit enregistrer, et *Copy Show Recordings into Library*
   doit être activé sous Paramètres → Local Machine).
2. Après le délai d'attente (Paramètres → Comptes CBA, 30 minutes par
   défaut), le service d'arrière-plan vérifie l'épisode et met l'envoi
   en file, avec la visibilité de l'émission.
3. S'il manque encore quelque chose (une description, l'enregistrement
   ...), l'épisode attend et est revérifié toutes les cinq minutes,
   jusqu'à 24 heures.  Ensuite l'archivage abandonne ; la boîte de
   dialogue affiche *L'archivage automatique a abandonné* avec la
   raison.

Jamais archivés automatiquement :

* les épisodes terminés **avant** que la case soit cochée - rien n'est
  rattrapé ; archivez les épisodes plus anciens à la main ;
* les rediffusions et les émissions créées comme *Rediffusion d'une
  autre émission* ;
* les épisodes avec **Ne pas archiver cet épisode automatiquement**
  (§4) ;
* les épisodes déjà archivés ou liés, ou dont quelqu'un a lancé l'envoi
  à la main - l'archivage automatique n'y touche pas ;
* les épisodes dont l'enregistrement couvre moins de la moitié de
  l'émission (p. ex. un enregistrement interrompu).

**Épisode...** indique dans le bloc *Archive en ligne* ce que
l'archivage automatique prévoit pour l'épisode, p. ex. *Archivé
automatiquement à partir du 2026-11-10 14:30, dès qu'il ne manque plus
rien ci-dessous*.

Quand un envoi automatique échoue, reste incertain ou est abandonné, le
bandeau d'avertissement en haut de la page cite l'épisode pendant sept
jours, jusqu'à ce qu'il soit archivé à la main ou que son article soit
lié.

> **Non détecté :** un programme de remplacement diffusé à la place
> d'une émission en direct (l'animateur n'est pas venu) est archivé comme
> l'émission.  Activez l'archivage automatique pour les émissions qui
> fonctionnent de façon fiable ; si cela arrive, supprimez l'article sur
> cba.media.

---

## 6. Vue des participants

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

## 7. Questions fréquentes

### « Archiver en ligne... manque. »

Le bouton apparaît pour les Admins et les Program Managers, et
seulement tant que l'épisode n'est ni archivé ni en attente d'envoi.

### « Tester la connexion signale que le nom d'utilisateur ou le mot de passe est refusé. »

Utilisez le *mot de passe d'application* du profil sur cba.media, pas
le mot de passe de connexion ; les espaces qu'il contient n'ont pas
d'importance.  Vérifiez le nom d'utilisateur.

### « Le thème est un champ numérique, pas une liste. »

Le service en arrière-plan récupère la liste des thèmes une fois par
jour.  Après une nouvelle installation ou avant que RASTATIME-WORKER
n'ait tourné, le champ prend le numéro.

### « Les commentaires sur cba.media ? »

L'interface de téléversement de la CBA n'a pas de réglage pour cela ;
le réglage par défaut de l'utilisateur CBA s'applique.

### « J'ai coché des profils, mais ils n'apparaissent pas dans la vue. »

La vue ne liste que les émissions **diffusées** dans l'année choisie.
Une nouvelle émission apparaît dès que son premier épisode est terminé.

### « La section Archivage manque ou est grisée. »

Elle manque dans **Modifier l'occurrence** - la section appartient à
l'émission entière ; pour un épisode, utilisez **Épisode...**.  Elle est
grisée si vous n'êtes ni Program Manager ni Admin.

### « Un épisode n'a pas été archivé automatiquement. »

Ouvrez **Épisode...** : le bloc *Archive en ligne* indique pourquoi -
l'interrupteur est désactivé, *Ne pas archiver automatiquement* est
coché, l'épisode s'est terminé avant l'activation, il attend encore
quelque chose, ou l'archivage a abandonné et pourquoi.  Archivez-le à
la main depuis là.

---

## Pour aller plus loin

* [Calendrier](./CALENDAR.md) - le formulaire de l'émission et le menu
  contextuel.
* [Enregistrement par émission](./RECORD_PER_SHOW.md) - l'enregistrement
  qui devient le son de l'épisode.
* [Analytics](./ANALYTICS.md) - les autres pages de statistiques.
* [Paramètres](./SETTINGS.md) - chaque page du menu Paramètres.
