# My Podcast

> **Où vous en êtes dans le manuel.** Lisez d'abord
> [Library](./LIBRARY.md) : ce que vous publiez dans My Podcast est un
> titre ordinaire de la bibliothèque.  À ne pas confondre avec
> **Podcasts** dans le menu principal (flux d'*autres* podcasts auxquels
> vous êtes abonné et que vous téléchargez) ni avec
> l'[Archivage](./ARCHIVING.md) (épisodes sur cba.media).

**My Podcast** est le podcast propre de la station : un flux RSS de
titres de votre bibliothèque auquel les auditeurs s'abonnent dans
n'importe quelle application de podcasts.  Publier un titre l'ajoute
au flux ; le dépublier (« Unpublish ») l'en retire.  Depuis le
2026-11-14, un titre peut aussi porter le **dernier jour où il reste
publié** - RASTATIME le retire alors de lui-même.

La publication est réservée aux Program Managers et aux Admins (voir
[Utilisateurs et rôles](./USERS_AND_ROLES.md)).

---

## 1. Publier un titre

1. Dans **Tracks**, ouvrez le menu contextuel du titre et choisissez
   **Publish...**.  La boîte de dialogue de publication s'ouvre dans
   son propre onglet.
2. Sous **Publish to:**, cochez **My Podcast**.
3. Facultatif : saisissez **Published until:** - le dernier jour où le
   titre reste dans le podcast (AAAA-MM-JJ, ou choisissez-le dans le
   calendrier qui s'ouvre).  Laissez vide pour aucune fin.  La date la
   plus proche possible est aujourd'hui.
4. Cliquez sur **Publish**.

Le titre apparaît alors sous **Published on:** dans la même boîte de
dialogue, avec sa date (ou *no end date*) à côté.

Le titre, l'auteur et la description du flux proviennent des
métadonnées du titre - **Edit Metadata...** dans la boîte de dialogue
ouvre l'éditeur de titre.

---

## 2. Modifier la date ou dépublier

Ouvrez de nouveau **Publish...** pour un titre publié :

- **Modifier la date :** changez la date à côté de *My Podcast* et
  cliquez sur **Save date**.  Un champ vide plus **Save date** supprime
  la fin - le titre reste alors publié jusqu'à ce que vous le
  dépubliiez.  Une date passée est refusée.
- **Dépublier :** cliquez sur **Unpublish**.  Le titre quitte le flux
  immédiatement.

---

## 3. Retrait automatique (« Published until »)

La date est **incluse** : un titre publié jusqu'au 31 décembre est
encore dans le podcast le 31 décembre et il est retiré **peu après
minuit** (fuseau horaire de la station), au plus tard environ sept
minutes après 00:00.

Le retrait équivaut exactement à un clic sur **Unpublish** :

- l'épisode quitte le **flux** ;
- son **lien de téléchargement** ne fonctionne plus - les applications
  de podcasts ne peuvent plus récupérer le fichier ;
- il disparaît de la liste des épisodes de la page My Podcast.

Le titre lui-même reste dans la bibliothèque.  Pour le remettre en
ligne, publiez-le de nouveau - il compte alors comme une nouvelle
publication et apparaît en haut dans les applications de podcasts.
Les copies que les auditeurs ont déjà téléchargées restent sur leurs
appareils ; personne ne peut les reprendre.

Les applications de podcasts ne récupèrent un flux que toutes les
quelques heures ; une application peut donc encore afficher un épisode
retiré jusqu'à sa prochaine récupération - le téléchargement ne
fonctionne plus entre-temps.

Chaque retrait automatique est consigné dans le journal legacy
(`StationPodcastExpiryTask: unpublished episode ...`).

---

## 4. La page My Podcast

**My Podcast** dans le menu principal affiche à gauche les réglages du
podcast et à droite ses épisodes.

- **General Fields / iTunes Fields** - nom, description, langue,
  auteur, catégorie, etc., tels que les applications de podcasts les
  affichent.  Cliquez sur **Save** après vos modifications.
- **Privacy Settings** - **Public** (toute personne ayant l'adresse du
  flux) ou **Private** (uniquement avec l'adresse du flux qui contient
  la clé de partage).  **Feed URL** et **View Feed** affichent
  l'adresse à communiquer.
- **Liste des épisodes** - chaque titre publié avec sa date
  **Published until** (vide = sans fin).  Sélectionnez des épisodes et
  cliquez sur **Unpublish** pour les retirer.

---

## Voir aussi

- [Library](./LIBRARY.md) - les titres que vous publiez.
- [Archivage](./ARCHIVING.md) - mettre plutôt les épisodes sur cba.media.
- [Utilisateurs et rôles](./USERS_AND_ROLES.md) - qui peut publier.
