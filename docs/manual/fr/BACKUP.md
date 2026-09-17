# Sauvegarde

> **Où vous êtes dans le manuel.** Ce chapitre couvre la page
> Settings → **Backup** : des sauvegardes de la base de données et de
> la configuration en un clic, dans un dossier de votre choix, et leur
> téléchargement via le navigateur.  La restauration d'une sauvegarde
> est une procédure hors ligne délibérée, documentée pour les
> administrateurs dans `docs/operator/BACKUP.md` — ce n'est pas un
> bouton.

Tout ce que RASTATIME sait — émissions, grille, métadonnées de la
bibliothèque, utilisateurs, réglages — vit dans la base PostgreSQL ;
les mots de passe et ports des services vivent dans quelques fichiers
de configuration.  La page **Backup** écrit les deux dans un seul ZIP
autonome par exécution.

La bibliothèque média (les fichiers audio eux-mêmes) n'est jamais
zippée — elle pèse de nombreux gigaoctets.  Activez plutôt **Include
media library** : elle est alors mise en miroir côté serveur à côté
des ZIP ; voir la section 3.

## 1. Le dossier de sauvegarde

Saisissez un chemin absolu sur un disque local, par exemple
`D:\rastatime-backups`, puis cliquez sur **Check** et **Save settings**.

- Le dossier est créé s'il n'existe pas.
- Il ne doit pas se trouver dans la bibliothèque média.
- Idéalement, il se trouve sur un **autre disque** que la base de
  données, pour qu'un disque défaillant n'emporte pas les deux.
- Les chemins réseau ne sont pas pris en charge.

## 2. Sauvegarder maintenant

**Back up now** lance la sauvegarde sur le serveur et rend compte sous
les boutons ; quelques secondes plus tard, le nouveau fichier apparaît
sous **Existing backups**.  Chaque sauvegarde est un ZIP nommé d'après
son heure de création :

```
rastatime-backup-2026-09-16T1830.zip
    db.dump          la base complète (pg_dump, format custom)
    config/…         chaque fichier de configuration (libretime.conf, …)
    manifest.json    le contenu, la date de création, la version de pg_dump
```

Une sauvegarde qui échoue (par exemple parce que PostgreSQL est
injoignable) ne laisse **aucun** ZIP à moitié écrit ; le message sous
les boutons en donne la raison.  Une sauvegarde interrompue par un
redémarrage de service s'affiche comme interrompue — relancez-la
simplement.

## 3. Inclure la bibliothèque média

Cochez **Include media library** puis cliquez sur **Save settings**.
Dès lors, chaque exécution synchronise aussi la bibliothèque dans le
sous-dossier `media` à côté des ZIP :

- **Incrémental.**  Seuls les fichiers nouveaux ou modifiés sont
  copiés ; les fichiers supprimés de la bibliothèque disparaissent
  aussi du miroir.  Le miroir est toujours la bibliothèque *actuelle*,
  pas un historique.
- **Vérifié.**  Après chaque exécution, chaque fichier de la
  bibliothèque est comparé au miroir (existence et taille) ; un écart
  fait échouer la sauvegarde.
- **Première exécution.**  Elle copie tout et peut durer — la barre de
  progression indique l'avancement.  **Cancel** arrête le miroir (le
  ZIP de la base est alors déjà complet) ; l'exécution suivante
  reprend simplement là où elle s'était arrêtée.

Le miroir ne transite jamais par le navigateur.  Pour restaurer les
médias, recopiez le contenu de `media` dans la racine de la
bibliothèque affichée sous [Machine locale](./LOCAL_MACHINE.md).

## 4. Sauvegardes existantes

Le tableau liste chaque sauvegarde du dossier, la plus récente en
premier, avec taille et heure de création.  **Download** enregistre le
ZIP via le navigateur — utile pour garder une copie hors machine.  Les
fichiers sur le disque restent intacts ; supprimez les anciens à la
main quand vous n'en avez plus besoin.

## 5. Restaurer

La restauration remplace la base en service et reste donc une
procédure hors ligne délibérée et documentée — services arrêtés, base
restaurée avec `pg_restore`, services relancés.  Suivez
`docs/operator/BACKUP.md`, section 7.  Le `db.dump` du ZIP est
exactement ce que `pg_restore` attend.

## 6. Bonnes pratiques

- Sauvegardez avant tout ce que vous détesteriez refaire :
  suppressions en masse, gros changements de grille, mises à jour.
- Téléchargez de temps en temps une copie sur une autre machine — une
  sauvegarde sur le même ordinateur ne survit pas à cet ordinateur.
- Les fichiers de configuration du ZIP contiennent des mots de passe
  de services.  Traitez les sauvegardes téléchargées comme les mots de
  passe qu'elles contiennent.
