# Paramètres

> **Où vous êtes dans le manuel.** Ce chapitre est l'index du menu
> Paramètres.  Il documente directement les pages *Général* et *Statut*
> et renvoie au chapitre dédié pour chaque autre page.  Vérifié par
> rapport à l'interface le 25/10/2026.

Le menu Paramètres est la surface de configuration de la station.  La
plupart des pages appartiennent aux **Admins** ; un
**Program Manager** voit *Mon profil*, *Show Templates*, *Auto DJ* et les équipes
de rédaction sous *Archivage* ;
les invités et les DJ ne voient que *Mon profil*.  Voir
[Utilisateurs et rôles](./USERS_AND_ROLES.md) §2 pour la matrice
complète des permissions.

---

## 1. Le menu Paramètres

Navigation de gauche → **Paramètres** ouvre le sous-menu :

| Page | Rôle | Qui | Chapitre |
|---|---|---|---|
| **Général** | Nom et description de la station, langue, début de semaine, API publique, page radio, logo, fond de la page d'accueil, favicon, couleur principale, fondus enchaînés, type de piste des téléversements, playlists d'automatisation, Live Text Info, TuneIn, Dangerous Options. | Admin | Ce chapitre §2 |
| **Mon profil** | Vos nom, e-mail, mot de passe, langue d'interface et fuseau horaire. | tous | [Utilisateurs et rôles](./USERS_AND_ROLES.md) §4 |
| **Utilisateurs** | Créer, modifier et supprimer des utilisateurs, définir leur type. | Admin | [Utilisateurs et rôles](./USERS_AND_ROLES.md) §3 |
| **Types de piste** | Types de piste avec leurs préréglages de fondu, crossover et métadonnées du flux. | Admin | [Bibliothèque](./LIBRARY.md) |
| **Show Templates** | Aperçu des modèles d'émission enregistrés : renommer, supprimer. | Program Manager, Admin | [Modèles d'émission](./SHOW_TEMPLATES.md) |
| **Archivage** | Équipes de rédaction derrière les émissions (nom, compte facultatif ; une par émission, choisie sous Archivage) ; pour les Admins, en dessous, les utilisateurs cba.media sous lesquels les émissions sont archivées (nom d'utilisateur, mot de passe d'application), test de connexion, limite d'envoi, délai de l'archivage automatique. Jusqu'au 2026-11-03, deux entrées, *Équipe de rédaction* et *Comptes CBA*. | Program Manager (équipes), Admin | [Archivage](./ARCHIVING.md) |
| **Auto DJ** | Remplissage des trous et complément des émissions incomplètes. | Program Manager, Admin | [Auto DJ](./AUTO_DJ.md) |
| **Flux** | Flux de sortie (débit, point de montage, codec), entrées pour les connexions en direct, identifiant Master. | Admin | [Flux](./STREAMS.md) |
| **Machine locale** | Carte son, dossier et format d'import, dossier et format d'enregistrement, emplacement de la bibliothèque. | Admin | [Machine locale](./LOCAL_MACHINE.md) |
| **Import / Export** | Utilisateurs, émissions, playlists, smart blocks, webstreams et abonnements podcast en fichiers CSV/JSON, avec aperçu à l'import. | Admin | [Import / Export](./IMPORT_EXPORT.md) |
| **Backup** | Sauvegardes de la base de données et de la configuration, le miroir média, sauvegardes automatiques, restauration. | Admin | [Backup](./BACKUP.md) |
| **Statut** | État des services, espace disque, redémarrages de services, adresses autorisées et bloquées. | Admin | Ce chapitre §3 |

Les sources Line-In se gèrent sous **Tableau de bord → Line Inputs**
(voir [Line-In](./LINE_IN.md)) ; les langues d'interface sont traitées
dans [Langues](./I18N.md).

---

## 2. Général

Paramètres → **Général**.

La page est divisée en **sections repliées** (depuis le 08/10/2026) : le
nom et la description de la station restent en haut, en dessous
*Station*, *Styling*, *Playout* et *Automation*, puis *Live Text Info*,
*TuneIn Settings* et *Dangerous Options*.  Un clic sur un titre ouvre la
section ; une section qui contient une erreur de validation après
**Enregistrer** s'ouvre d'elle-même.

### En haut de la page

| Champ | Notes |
|---|---|
| **Nom de station** | Visible partout - titre de page, métadonnées du flux, page radio. |
| **Description de station** | Texte libre, utilisé dans les flux podcast et sur la page radio. |

### Station

| Champ | Notes |
|---|---|
| **Langue par défaut** | Langue d'interface des nouveaux utilisateurs et de l'écran de connexion, et langue de tous les widgets (dates, jours de la semaine, boutons ; depuis le 25/10/2026). Chaque utilisateur garde sa propre langue de Mon profil. |
| **Fuseau horaire de la station** | Affiché pour information seulement.  Le fuseau horaire de la station se règle dans `config/rastatime.conf` (`general.timezone`) ; chaque utilisateur peut choisir un fuseau d'affichage dans Mon profil. |
| **La semaine commence le** | Premier jour de la semaine dans le calendrier et dans les widgets (Weekly Schedule, Multi-View Schedule). |
| **Public RASTATIME API** | *Enabled* permet aux widgets intégrés dans d'autres sites web de lire les données de programmation. Nécessaire pour les widgets de programme intégrables. |
| **Afficher le bouton de connexion sur la page radio ?** | Affiche un bouton de connexion sur la page radio publique. |
| **Désactiver la page radio publique et rediriger vers la connexion ?** | Les visiteurs de l'adresse de la station arrivent directement à la connexion. |

### Styling

| Champ | Notes |
|---|---|
| **Logo de station** | Image en haut à gauche de chaque page. Jusqu'à 1 Mo, JPG / PNG / GIF / WebP ; **Supprimer** l'efface. |
| **Image de fond de la page d'accueil** | La photo derrière la page d'accueil publique (`/`). JPG, PNG ou WebP jusqu'à 5 Mo ; 1920 px de large et 1 Mo ou moins recommandés. Stockée comme fichier sous `landing/` dans l'emplacement de la médiathèque (le miroir de sauvegarde nocturne l'emporte) ; **Supprimer** rétablit l'image intégrée. Effective au prochain chargement de la page d'accueil (le navigateur garde l'image une semaine, un nouveau téléversement reçoit une nouvelle adresse). Depuis le 2026-10-07. |
| **Favicon de station** | Image dans l'onglet du navigateur. Jusqu'à 200 Ko, PNG / JPG / GIF / ICO. Rendue comme URI data:. |
| **Couleur principale** | La couleur d'accent de toute l'interface, de la page radio et des widgets — liens, surbrillances, lignes sélectionnées, entrée de menu active et onglet actif de Playout History, barres de progression et de stockage, barres de défilement, flèches de section, bouton lecture et volume du lecteur, onglets, boutons et surbrillances des widgets, le graphique de la page d'erreur. Saisissez `#rrggbb` ou utilisez le sélecteur à côté du champ ; **Rétablir la valeur par défaut** remet l'orange (`#ff5d1a`). Effectif au prochain chargement de page. Choisissez une couleur qui se détache du fond gris foncé ; le texte posé dessus passe de lui-même du blanc au noir. Les couleurs de signalisation (erreurs, avertissements, couleurs des émissions dans le calendrier) et la barre de remplissage des émissions dans le calendrier (toujours orange) ne changent pas. |
| **Couleur secondaire** | La deuxième couleur de l'interface (depuis le 26/10/2026) : la barre de progression de l'émission dans l'en-tête, le repère au bord droit de l'entrée active du menu du tableau de bord (Tracks, Playlists, Smart Blocks, …) et des sous-menus de Settings, Analytics, Help et Widgets, la piste en cours dans les Scheduled Shows du tableau de bord, et les boutons Upload, New Show, New Log Entry, Add, New et semblables. Saisissez `#rrggbb` ou utilisez le sélecteur à côté du champ ; **Rétablir la valeur par défaut** remet le bleu clair (`#1adeff`). Les boutons portent un texte blanc : pour eux, la couleur n'est assombrie qu'autant que la lisibilité l'exige (défaut : `#0e7a8c`, avant `#246b86`) ; le texte sur la ligne de la piste en cours passe de lui-même du noir au blanc. S'applique au prochain chargement de page. |

### Playout

| Champ | Notes |
|---|---|
| **Default Track Crossfade Duration (s)** | Le fondu enchaîné entre deux pistes consécutives **de la même émission** : la piste sortante s'estompe pendant que l'entrante monte sur ce nombre de secondes (1 seconde est typique ; 0 = les pistes s'enchaînent sans chevauchement ; jusqu'à 10 secondes pour des transitions douces). La grille place les lignes consécutives avec exactement ce chevauchement. |
| **Default Show Crossfade Duration (s)** | La transition **à la limite d'une émission** (depuis le 2026-09-27) : l'ancienne émission s'estompe sur ce nombre de secondes tandis que le premier titre de la nouvelle démarre aussitôt à plein niveau — une émission qui commence par un jingle ou un indicatif est entendue dès son premier temps. Même forme et même valeur pour chaque bascule entre **entrées** (piste ↔ webstream ↔ Line-In) : la source entrante est à plein niveau immédiatement, la sortante s'estompe en dessous ; 0 = bascule sèche. Un webstream ou un Line-In programmé dans les deux émissions continue sans coupure. Valeur de départ 1 s. Les deux valeurs sont appliquées par la chaîne audio quelques secondes après l'enregistrement (redémarrage planifié à un moment calme ou à une limite de titre) ; « Appliquer maintenant » dans Paramètres → Machine locale force l'application. |
| *Fondu enchaîné par type de piste* | Paramètres → Types de piste → *Crossfade Duration (s)* (depuis le 2026-09-29) remplace la valeur par défaut pour tous les titres de ce type ; vide = valeur par défaut. Entre deux titres, la **plus petite** des deux valeurs s'applique : un type à 0 s'enchaîne toujours bord à bord - le type *Jingles* fourni commence à 0, car des éléments courts, calés à la seconde, ne doivent pas être raccourcis par un fondu de la longueur d'un morceau. Lors d'un passage entre un titre et un flux web ou une entrée ligne, la plus petite valeur entre celle du titre et la Default Show Crossfade Duration s'applique. Un changement des valeurs par défaut ou d'un type de piste recalcule automatiquement les lignes de toutes les émissions à venir ; les lignes déjà commencées ne sont jamais modifiées. |
| *Pas de fondu par type de piste* | Paramètres → Types de piste → *No Fade during Crossover* (depuis le 2026-09-30) est le préréglage du type pour le champ *Crossover* de l'éditeur de piste : chaque titre du type réglé sur *As the track type* garde son niveau plein pendant que le titre voisin entre ou sort en fondu - le chevauchement lui-même reste tel que la durée de fondu du type l'indique. Prévu pour les jingles ou IDs qui doivent trancher sur la fin d'une chanson. Un titre isolé peut toujours être réglé autrement dans l'éditeur de piste ; un titre exclu du crossover n'a pas de chevauchement dans lequel garder son niveau. Une modification atteint le playout au prochain envoi de la grille ; aucune ligne n'est remise en page puisque le chevauchement ne change pas. |
| *Transmettre les métadonnées par type de piste* | Paramètres → Types de piste → *Forward Metadata to the Stream* (depuis le 2026-10-14) est le préréglage du type pour le champ *Métadonnées du flux* de l'éditeur de piste : décoché, chaque piste du type réglée sur *Comme le type de piste* passe sans artiste / titre sur le flux, les lecteurs affichent « Nom de la station - Nom de l'émission » (jingles, identifiants, promos). Une piste peut passer outre dans son éditeur. |
| **Track Type Upload Default** | Le type de piste attribué aux nouveaux téléversements qui n'en fixent pas. Influence les filtres des smart blocks. |
| **Trim overbooked shows after autoloading?** | Coupe le contenu d'une émission remplie par autoloading qui dépasse la durée de l'émission. |
| *Propriétaire des imports* | Il n'y a pas de réglage : les fichiers pris par le scan d'arrière-plan du dossier d'import local appartiennent au premier compte administrateur (`admin`), ceux importés avec **Scan Now** à l'opérateur qui a cliqué. |

### Automation

| Champ | Notes | Chapitre |
|---|---|---|
| **Intro / Outro Autoloading Playlist** | Jouée au début / à la fin de chaque émission avec autoloading. | [Playlists autoloading](./AUTOLOADING_PLAYLISTS.md) |
| **Song-Request Pool (smart blocks)** | Les smart blocks dont les auditeurs peuvent demander les titres. | [Demandes de titres](./SONG_REQUESTS.md) |
| **Traffic-Alert Smart Block** | Le bloc des infos trafic. | [Infos trafic](./TRAFFIC_ALERTS.md) |
| **Show-Shift Filler Playlist** | Remplit le trou quand une émission est décalée. | [Démarrage différé](./DELAYED_START.md) |
| **Overwrite Podcast Episode Metatags** | Fixe artiste, titre et album des épisodes téléchargés d'après le flux du podcast. | [Bibliothèque](./LIBRARY.md) |
| **Generate a smartblock and a playlist upon creation of a new podcast** | Crée un smart block et une playlist correspondants pour chaque nouvel abonnement podcast. | [Bibliothèque](./LIBRARY.md) |

### Live Text Info

Section repliable sous les Préférences générales (depuis le 2026-09-28).
La ligne « now playing » sous forme de fichier texte pour d'autres
systèmes (site web, afficheurs, agrégateurs) : une ligne UTF-8, toujours
remplacée, écrite par le playout à chaque changement de titre, webstream,
entrée ligne ou DJ.

| Champ | Notes |
|---|---|
| **Écrire la ligne « now playing » dans un fichier texte ?** | Interrupteur principal. |
| **Format du texte en direct** | Les trois mêmes variantes que le Stream Label (Artist - Title / Show - Artist - Title / Station name - Show name) avec les mêmes replis : une source en direct sans artiste ni titre affiche *Station name - Show name*, le silence affiche le texte Off Air. Indépendant du Stream Label. |
| **Publier sur le web** | Le fichier est servi sous `http://<hôte>/live/now-playing.txt` (fichier statique, sans connexion, indépendant de l'interrupteur Public API). Accessible depuis Internet dès que le serveur web l'est, comme les widgets. |
| **Écrire aussi dans un fichier** | Chemin absolu facultatif (cette machine ou un partage réseau). |
| **Envoyer sur un serveur FTP** | À chaque changement le fichier est envoyé via FTP, FTPS (TLS explicite) ou SFTP vers le chemin distant ; identifiants propres, distincts de l'import FTP. SFTP exige un `curl` avec libssh2 (celui livré avec Git pour Windows ; le curl intégré à Windows ne le peut pas). Les échecs sont journalisés ; le changement suivant réessaie. |

La ligne est construite par le moteur audio à partir des métadonnées
qu'il envoie réellement au flux, titres DJ et titres de webstream compris.
Un paramètre modifié s'applique au prochain changement, sans redémarrage.

### TuneIn Settings

Section repliable sous les Préférences générales. Depuis le 2026-09-28,
le playout envoie lui-même l'information « now playing » à TuneIn ;
auparavant seuls les démarrages de fichiers étaient transmis et
l'affichage disparaissait après cinq minutes.

| Champ | Notes |
|---|---|
| **Push metadata to your station on TuneIn?** (envoyer les métadonnées à TuneIn) | Interrupteur principal. Activé, le playout envoie titre et artiste à chaque démarrage de piste, le nom de l'émission au démarrage d'un webstream ou d'une entrée ligne, et répète la dernière mise à jour toutes les quatre minutes (TuneIn efface un affichage silencieux depuis cinq minutes). Enregistrer avec l'interrupteur activé vérifie les identifiants auprès de TuneIn et refuse les identifiants invalides. |
| **Station ID**, **Partner Id**, **Partner Key** | Depuis votre compte partenaire TuneIn (AIR API). La clé n'apparaît dans aucun journal. |

Un paramètre modifié est pris en compte au prochain envoi ; pas de
redémarrage. Un DJ en direct (Master / Show Source) n'est pas annoncé ;
la dernière piste reste affichée jusqu'au prochain élément programmé.

### Dangerous Options

Repliées par défaut ; les deux boutons demandent confirmation et sont
réservés aux administrateurs.

| Bouton | Effet |
|---|---|
| **Delete All Tracks in Library** | Supprime chaque piste de la bibliothèque et des grilles à venir (upstream). |
| **Clear Calendar** (depuis le 2026-10-14) | Supprime chaque émission qui **n'a pas encore commencé**, avec son contenu, et met fin à toutes les répétitions. L'émission en cours et tout le passé restent, l'historique de diffusion garde ses noms d'émission. Une émission sans instance restante est effacée. La confirmation indique combien d'instances et d'émissions ont été retirées. |

> **Sous le capot.** Les valeurs sont des lignes de la table `cc_pref`
> (clé / valeur).  Les valeurs par utilisateur (langue, fuseau horaire,
> mises en page des tableaux) sont des lignes `cc_pref` liées à
> l'utilisateur.  La configuration de service qui ne peut pas résider
> dans la base (accès à la base, chemins, fuseau horaire de la station,
> clé API) se trouve dans `config/rastatime.conf`.

---

## 3. Statut

Paramètres → **Statut**.  De haut en bas :

| Section | Contenu |
|---|---|
| **RASTATIME Version** | La version installée. |
| **Composants** | Bibliothèques PDO et PostgreSQL, configuration de la base et de RabbitMQ, et les services Windows RASTATIME-PLAYOUT, -WORKER, -API, -ANALYZER, -ICECAST et -APACHE avec leur état. Un service affiché arrêté est le signal d'aller voir (`Get-Service RASTATIME-*` dans PowerShell, ou le runbook [`CRASH_RECOVERY`](../../operator/CRASH_RECOVERY.md)). |
| **Espace disque** | Espace libre et utilisé du stockage. |
| **Redémarrages de services** | Un bouton **Restart** par service (Analyzer, API, Apache, Icecast, Playout, Worker), avec ce que fait le service et quand un redémarrage aide, plus **Restart All Services** (l'interface est injoignable environ 10 secondes). |
| **Adresses autorisées** | Adresses et réseaux qu'aucun frein de connexion ne bloque jamais. |
| **Adresses bloquées** | Chaque adresse ou utilisateur actuellement bloqué par niveau (connexion web, connexion DJ, pare-feu) avec **Unblock** et **Allow**. |

Les deux listes d'adresses sont décrites dans
[Utilisateurs et rôles](./USERS_AND_ROLES.md) §8.

Ce que coûte un redémarrage :

| Service | Effet d'un redémarrage |
|---|---|
| **Playout** | Le pilote de la grille redémarre ; pas pendant une émission en direct.  Le moteur audio (Liquidsoap) est un service à part (RASTATIME-LIQUIDSOAP) et continue de jouer ce qu'il a en file. |
| **Icecast** | Tous les auditeurs et toutes les sources sont déconnectés ; les sorties se reconnectent en quelques secondes, les auditeurs doivent se reconnecter. Seulement dans une fenêtre calme. |
| **Apache** | L'interface web est injoignable quelques secondes. |
| **API**, **Worker**, **Analyzer** | Le travail en arrière-plan s'interrompt brièvement ; aucun effet sur le flux. |

> **Conseil opérateur.** Ne redémarrez que le service qui pose
> problème.  La séquence complète se trouve dans
> [`RESTART_ORDER`](../../operator/RESTART_ORDER.md).

Les **avertissements preflight** ne sont pas une section de cette page :
ils apparaissent comme bannière sur chaque page.  Un exemple : **échec de
téléchargement de podcast** (depuis le 08/10/2026) - quand un
téléchargement d'épisode automatique ou manuel échoue, un avertissement
nomme le podcast, l'épisode, le nombre de tentatives, la dernière
tentative et la raison (code HTTP ou « API unreachable »).  Il disparaît
de lui-même quand le téléchargement réussit plus tard ou que le podcast
est retiré.  Vérifiez le flux et l'adresse de téléchargement de
l'épisode sous Bibliothèque → Podcasts.

---

## 4. Foire aux questions

### « J'ai changé un paramètre mais rien ne se passe. »

La plupart des paramètres s'appliquent immédiatement ou au prochain
chargement de page.  Exceptions :

| Paramètre | S'applique |
|---|---|
| Fondus enchaînés, flux, carte son | Au redémarrage de la chaîne audio - planifié automatiquement à un moment calme ; **Appliquer maintenant** dans Paramètres → Machine locale le force. |
| Couleurs principale et secondaire, logo, favicon | Au prochain chargement de page (F5). |
| Votre propre langue | Au prochain chargement de page ; l'écran de connexion utilise la langue par défaut. |
| Live Text Info, TuneIn | Au prochain changement de titre ou de source. |

### « Y a-t-il un menu Outils, une visionneuse de journaux ou une console DB ? »

Non.  Les scripts de maintenance se trouvent sur la machine de la
station sous `infra\scripts` (par exemple
`infra\scripts\maintenance\rescan-playability.py`) et sont décrits dans
la documentation opérateur.  Les journaux se trouvent dans
`C:\RASTATIME\logs`.

### « Comment sauvegarder ou restaurer les paramètres ? »

Paramètres → **Backup** sauvegarde la base de données (avec chaque ligne
`cc_pref`) et la configuration ; pour la restauration voir
[Backup](./BACKUP.md).  `config/rastatime.conf` contient des mots de
passe - ne le placez jamais tel quel dans un gestionnaire de versions.

### « Quels paramètres un Program Manager peut-il ouvrir ? »

*Mon profil*, *Show Templates*, *Auto DJ* et les équipes de rédaction
sous *Archivage*.  Tout le reste sous
Paramètres appartient aux Admins.  Voir [Utilisateurs et rôles](./USERS_AND_ROLES.md) §1-§2.

---

## 5. Moteur de playout (Liquidsoap)

> **Paramètre niveau service**, pas un paramètre UI.  Le service NSSM
> RASTATIME-PLAYOUT peut porter `RASTATIME_PLAYOUT_ENGINE=liquidsoap`
> dans son environnement ; c'est la seule valeur acceptée.  Opérateur
> uniquement ; non exposé dans l'UI web.

Depuis le 2026-09-10, Liquidsoap est le **seul** moteur de playout.
L'ancien moteur mpv (avec ses streamers FFmpeg pour les sorties
Icecast) et le plan VLC jamais achevé ont été retirés du code après
que Liquidsoap a porté en production chaque type d'élément de grille
(fichiers, webstreams, entrées ligne, enregistrement, sources DJ)
depuis le 2026-05-28.

Ce que Liquidsoap fournit :

- **Enregistrement** capté sur le bus audio interne (post-switch,
  post-crossfade, post-amplify) — bit-identique à ce qu'entendent les
  auditeurs.  Format et débit suivent Paramètres → Machine locale →
  Show Recording (par défaut MP3 320 kbps).
- **Expérience auditeur** : les points de montage Icecast restent
  ouverts à travers les changements de piste/émission — pas de
  reconnexion, pas de remise à zéro des compteurs.
- **Routage des sources DJ** natif via `input.harbor` + `switch(...)`
  de Liquidsoap — les clients DJ Master / Show se connectent
  directement au harbor géré par Liquidsoap (port 8001 par défaut,
  voir [Flux](./STREAMS.md)).

**Si le service refuse de démarrer** avec

```
CRITICAL __main__: RASTATIME_PLAYOUT_ENGINE='mpv' is not supported - Liquidsoap is the only playout engine since 2026-09-10 ...
```

l'environnement du service nomme encore le moteur retiré : définir
`RASTATIME_PLAYOUT_ENGINE=liquidsoap` (ou retirer la variable) dans
l'environnement NSSM de `RASTATIME-PLAYOUT`, puis redémarrer le service.
`RASTATIME_MPV_PATH` / `RASTATIME_MPV_LOG_LEVEL` sont ignorés et
peuvent être supprimés.

**Le démarrage du moteur est visible dans le journal playout :**

```
INFO __main__: Playout engine: Liquidsoap (telnet target 127.0.0.1:1234).
```

---

## Où aller ensuite

* Suivez le lien du tableau du §1 vers le chapitre dédié d'une page
  Paramètres.
* [Utilisateurs et rôles](./USERS_AND_ROLES.md) — qui peut ouvrir quelle
  page.
* [`docs/operator/INSTALL.md`](../../operator/INSTALL.md) — les
  paramètres réglés à l'installation.

## 6. Alertes (depuis le 2026-11-03)

Settings → **Alerts** (Admins).  RASTATIME envoie un message quand
l'antenne devient muette, quand un service ne répond plus ou quand un
avertissement pré-vol apparaît, et une levée d'alerte dès que le
problème a disparu.

| Champ | Signification |
|---|---|
| **Send alerts** | Interrupteur principal. |
| **Dead air after (seconds)** | Un silence sur le bus d'antenne (sous -50 dB, source de secours silencieuse comprise) de cette durée déclenche *Dead air* ; 2 s d'audio lèvent l'alerte.  5 à 3600, 30 par défaut.  Le seuil est compilé dans le moteur audio et s'applique à son prochain redémarrage planifié. |
| **Reminder every (minutes)** | Tant qu'un problème reste ouvert ; 0 = pas de rappel.  Au plus 20 messages par canal et par heure. |
| **Services** | Playout (surveillé par le service API), API, Apache, Icecast, Analyzer et Worker, contrôlés chaque minute ; deux échecs d'affilée déclenchent une alerte. |
| **Pre-flight warnings** | Chaque type d'avertissement du bandeau déclenche une alerte une fois et la lève quand il disparaît. |
| **E-mail (SMTP)** | Serveur, port, chiffrement (STARTTLS, SSL/TLS, aucun), nom d'utilisateur et mot de passe (authentification ; le mot de passe n'est jamais réaffiché), expéditeur, destinataires séparés par des virgules.  L'e-mail de réinitialisation du mot de passe de la page de connexion n'est pas concerné. |
| **Telegram** | Jeton du bot de @BotFather (écriture seule) et identifiants de chat séparés par des virgules ; le bot doit être membre du chat ou du groupe et avoir reçu un message.  Un identifiant de groupe commence par un moins. |
| **Send test e-mail / message** | Après enregistrement : un message de test avec les réglages enregistrés, envoyé par le service playout. |

Les messages ressemblent à `[Station] ALERT: Dead air` avec l'heure, le
détail et le service émetteur, `STILL OPEN` pour les rappels et `OK`
pour la levée d'alerte.  Les redémarrages planifiés du moteur audio
(nuit, réglages) suspendent les nouvelles alertes pendant trois minutes.

Pas encore couvert : une liaison montante morte (aucun canal ne quitte
le studio), une interface web lente plutôt qu'arrêtée, et Signal,
WhatsApp ou SMS (voir BACKLOG).
