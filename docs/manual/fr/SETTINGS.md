# Paramètres

> **Où vous êtes dans le manuel.** Ce chapitre est l'index
> hub-et-rayons pour le menu Paramètres.

Le menu Paramètres est la surface de configuration
par-station. Visible entièrement seulement pour **Admin**
et **Super Admin** ; **Program Manager** voit un
sous-ensemble. Voir [Utilisateurs et rôles](./USERS_AND_ROLES.md)
§5 pour la matrice complète des permissions.

---

## 1. Le menu Paramètres

| Page | But | Chapitre |
|---|---|---|
| **Préférences générales** | Nom de station, langue par défaut, couleurs par défaut, vue d'avance tableau de bord, propriétaire d'import par défaut, durée crossfade par défaut, favicon, logo de station. | Ce chapitre §2 |
| **Machine locale** | Périphériques sortie/entrée carte son, dossier d'import local, dossier d'enregistrement local. | [Machine locale](./LOCAL_MACHINE.md) |
| **Streams** | Jusqu'à quatre streams de sortie. | [Streams](./STREAMS.md) |
| **Line-In Library** | Entrées audio live nommées. | [Line-In](./LINE_IN.md) |
| **Auto DJ** | Remplisseur d'arrière-plan. | [Auto DJ](./AUTO_DJ.md) |
| **Modèles d'émission** | Snapshots de formulaire d'émission réutilisables. | [Modèles d'émission](./SHOW_TEMPLATES.md) |
| **Gérer les utilisateurs** | Créer / modifier / désactiver utilisateurs. | [Utilisateurs et rôles](./USERS_AND_ROLES.md) |
| **Localisation** | Sélection de langue UI. | [Langues](./I18N.md) |
| **Statut système** | Santé live des services, widget de redémarrage. | Ce chapitre §3 |
| **Tools** | Sous-menu : Console DB, Visualiseur de logs, Réinitialisation cache. | Ce chapitre §4 |

---

## 2. Préférences générales

Paramètres → **Préférences générales**.

### Station

| Champ | Notes |
|---|---|
| **Nom de station** | Visible partout — titre de page, métadonnées ICY, nom From email. |
| **Description de station** | Description en texte libre. |
| **Logo de station** | Image en haut à gauche de chaque page. Max 200 KB, JPG / PNG / GIF. |
| **Favicon de station** | Image dans l'onglet du navigateur. Max 200 KB. Rendue comme URI data:. |
| **Couleur principale** | La couleur d'accent de toute l'interface, de la page radio et des widgets — liens, surbrillances, lignes sélectionnées, entrée de menu active, barres de progression et de stockage, barres de défilement, flèches de section, bouton lecture et volume du lecteur, onglets, boutons et surbrillances des widgets. Saisissez `#rrggbb` ou utilisez le sélecteur à côté du champ ; **Rétablir la valeur par défaut** remet l'orange (`#ff5d1a`). Effectif au prochain chargement de page. Choisissez une couleur qui se détache du fond gris foncé ; le texte posé dessus passe de lui-même du blanc au noir. Les couleurs de signalisation (erreurs, avertissements, couleurs des émissions dans le calendrier) et la barre de remplissage des émissions dans le calendrier (toujours orange) ne changent pas. |
| **Fuseau horaire** | Fuseau horaire opérateur pour tous affichages calendrier / planning. Stocké par-émission dans `cc_show_days.timezone`. |
| **La semaine commence le** | Lundi / Dimanche. |

### Valeurs par défaut

| Champ | Notes |
|---|---|
| **Langue par défaut** | Langue UI pour nouveaux utilisateurs + l'écran de connexion. |
| **Default Track Crossfade Duration** (durée du fondu enchaîné entre titres) | Le fondu enchaîné entre deux pistes consécutives **de la même émission** : la piste sortante s'estompe pendant que l'entrante monte sur ce nombre de secondes (1 seconde est typique ; 0 = les pistes s'enchaînent sans chevauchement ; jusqu'à 10 secondes pour des transitions douces). La grille place les lignes consécutives avec exactement ce chevauchement. |
| **Fondu enchaîné par type de piste** | Settings → Track Types → *Crossfade Duration (s)* (depuis le 2026-09-29) remplace la valeur par défaut pour tous les titres de ce type ; vide = valeur par défaut. Entre deux titres, la **plus petite** des deux valeurs s'applique : un type à 0 s'enchaîne toujours bord à bord - le type *Jingles* fourni commence à 0, car des éléments courts, calés à la seconde, ne doivent pas être raccourcis par un fondu de la longueur d'un morceau. Lors d'un passage entre un titre et un flux web ou une entrée ligne, la plus petite valeur entre celle du titre et la Default Show Crossfade Duration s'applique. Un changement des valeurs par défaut ou d'un type de piste recalcule automatiquement les lignes de toutes les émissions à venir ; les lignes déjà commencées ne sont jamais modifiées. |
| **Default Show Crossfade Duration** (durée du fondu enchaîné entre émissions) | La transition **à la limite d'une émission** (depuis le 2026-09-27) : l'ancienne émission s'estompe sur ce nombre de secondes tandis que le premier titre de la nouvelle démarre aussitôt à plein niveau — une émission qui commence par un jingle ou un indicatif est entendue dès son premier temps. Même forme et même valeur pour chaque bascule entre **entrées** (piste ↔ webstream ↔ Line-In) : la source entrante est à plein niveau immédiatement, la sortante s'estompe en dessous ; 0 = bascule sèche. Un webstream ou un Line-In programmé dans les deux émissions continue sans coupure. Valeur de départ 1 s. Les deux valeurs sont appliquées par la chaîne audio quelques secondes après l'enregistrement (redémarrage planifié à un moment calme ou à une limite de titre) ; « Appliquer maintenant » dans Settings → Local Machine force l'application. |
| ~~Crossfade par défaut~~ (ancien champ unique, jusqu'au 2026-09-27) | Le *crossfade maison* de la station. Entre pistes consécutives d'une même émission c'est la durée du crossfade (1 seconde est typique ; 0 = coupures nettes). Depuis le 2026-09-04 la valeur façonne aussi chaque bascule entre **entrées** (piste ↔ webstream ↔ Line-In) : une valeur supérieure à 0 fond la source sortante dans l'entrante pendant ce nombre de secondes ; **0 signifie « ducking »** — la source entrante démarre aussitôt à plein niveau et la sortante s'efface en dessous en 1 s. Dans les deux cas la queue mise en tampon de la source sortante est entendue, pas coupée. Prend effet après redémarrage de la chaîne audio (« Appliquer maintenant » dans Settings → Local Machine). |
| **Type de piste par défaut** | Type de piste assigné aux nouveaux téléversements. |
| **Propriétaire d'import par défaut** | Compte crédité comme propriétaire pour fichiers importés via le Dossier d'import local. |
| **Enregistrement par défaut** | Si coché, nouvelles émissions ont **Enregistrer cette émission :** pré-cochée. |

### Tableau de bord

| Champ | Notes |
|---|---|
| **Vue d'avance** | Combien d'émissions à venir le panneau "Vient ensuite" affiche. 3-5 est typique. |
| **Intervalle de rafraîchissement** | À quelle fréquence le Tableau de bord interroge. 5 s par défaut. |

### Info texte en direct

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

### Paramètres TuneIn

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

### Email (réinitialisation mot de passe)

| Champ | Notes |
|---|---|
| **Serveur SMTP / Port** | Le serveur mail sortant de votre station. |
| **TLS** | Recommandé activé. |
| **Adresse From** | Utilisée comme en-tête From de l'email. |

> **Comment ça marche sous le capot.** Paramètres sont
> écrits dans la table `cc_pref` comme lignes
> clé/valeur. La plupart des paramètres rechargent
> immédiatement ; les paramètres SMTP nécessitent un
> redémarrage du service worker. Voir ARCHITECTURE §11.

---

## 3. Statut système

Paramètres → **Statut système**.

Vue d'ensemble de santé de chaque composant dont RASTATIME
dépend.

### Services

PID live + uptime pour chaque service Windows géré par
NSSM. Un badge rouge ici est le signal de vérifier le
service via `Get-Service RASTATIME-*` dans PowerShell ou
le runbook
[`CRASH_RECOVERY`](../../operator/CRASH_RECOVERY.md).

### Connectivité

Vérification live de chaque dépendance externe :
**Base de données (PostgreSQL)** — temps de réponse,
**Connexion source Icecast** — état de connexion source
côté moteur de playout, **Dossier d'import local** —
résultat du scan récent.

### Avertissements préflight

Avertissements persistés depuis la vérification préflight
de démarrage. Choses comme "FFmpeg pas dans PATH" ou
"port attendu déjà en utilisation".

> **Comment ça marche sous le capot.** Piloté par
> l'endpoint `/api/v2/preflight/warnings` adossé à la
> table `rastatime_preflight_warning`. Le `preflight.py`
> de démarrage lance ~30 vérifications.

### Contrôles de service (Admin+ seulement)

Redémarrage en un bouton pour chaque service Windows.

Effets varient par service :

| Service | Effet redémarrage |
|---|---|
| **API** | ~2 s panne de l'API REST. |
| **Worker** | Jobs d'arrière-plan en pause (~10 s). |
| **Playout** | **Le stream devient silencieux ~10 s.** À utiliser avec parcimonie pendant le temps d'antenne. |
| **Analyzer** | Dossier d'import local en pause (~5 s). |
| **Icecast** | Tous les auditeurs se déconnectent. |
| **Apache** | Interface web inaccessible ~5 s. |

> **Conseil opérateur.** Redémarrez seulement le service
> qui se comporte mal.

---

## 4. Tools

Paramètres → **Tools** → sous-menu.

| Tool | But |
|---|---|
| **Console DB** | Interface de requête PostgreSQL en lecture seule. Super Admin seulement. Cachée par défaut ; activer dans `config/libretime.conf` avec `[tools] db_console = true`. |
| **Visualiseur de logs** | Tail les 200 dernières lignes de logs d'erreur. |
| **Réinitialisation cache** | Vider les caches côté serveur. |
| **Rescan jouabilité bibliothèque** | Exécuter la vérification de jouabilité analyzer sur chaque piste existante. |

Ces outils ne sont *pas* des outils quotidiens.

> **Pourquoi Console DB cachée par défaut.** Une console
> DB en lecture seule peut leak credentials dans clauses
> WHERE, dumper données personnelles via SELECT.

---

## 5. Foire aux questions

### "J'ai changé un paramètre mais rien ne se passe."

| Paramètre | Nécessite |
|---|---|
| SMTP | Redémarrage du service worker |
| Credentials stream | Redémarrage du service playout |
| Périphérique carte son | Redémarrage du service playout |
| Fuseau horaire | Rafraîchissement dur du navigateur |
| Langue par défaut | Déconnexion / connexion |

### "Où Paramètres stocke-t-il ses valeurs ?"

Principalement dans `cc_pref` (table clé / valeur). Les
paramètres par-utilisateur (langue, clé API) vivent dans
`cc_subjs`. La configuration de service qui ne peut pas
vivre dans la BD (credentials PostgreSQL, chemins
système) vit dans `config/libretime.conf`.

### "Puis-je versionner mes Paramètres ?"

Indirectement : `config/libretime.conf` est un fichier
texte. Les lignes `cc_pref` ne sont pas versionnées.
Pour sauvegarder, utilisez `pg_dump --table=cc_pref`.

### "Pourquoi certains paramètres sont visibles seulement pour Super Admin ?"

La Console DB, la capacité de créer d'autres Admins, et
le droit de voir les clés API d'autres utilisateurs sont
réservés à Super Admin parce qu'ils accordent une
escalade d'accès.

---

## 6. Moteur de playout (Liquidsoap)

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
  auditeurs.  Débit fixe 320 kbps MP3, qualité archive.
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

* Suivez le lien par-page dans le tableau ci-dessus vers
  le chapitre dédié pour toute grande page Paramètres.
* [Utilisateurs et rôles](./USERS_AND_ROLES.md) —
  matrice des permissions qui garde chaque page
  Paramètres.
* [`docs/operator/INSTALL.md`](../../operator/INSTALL.md)
  — paramètres initiaux configurés au moment de
  l'installation.
