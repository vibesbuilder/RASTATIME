# RASTATIME — Manuel de l'utilisateur (Français)

> 🌐 **Langues :** [English](../../../USER_MANUAL.md) ·
> [Deutsch](../de/USER_MANUAL.md) ·
> **Français** ·
> [Español](../es/USER_MANUAL.md)

> **À propos de ce manuel.** RASTATIME est un fork
> Windows-first de LibreTime pour faire fonctionner une
> radio communautaire / petite radio commerciale. Ce
> document est le compagnon orienté opérateur des
> documents techniques
> [ARCHITECTURE](../../../RASTATIME_ARCHITECTURE_DRAFT_v0.1.md)
> et [INSTALL](../../operator/INSTALL.md). Il couvre
> **comment faire fonctionner une radio avec RASTATIME au
> quotidien** — pas comment installer ou déboguer le
> serveur.

> **Note de cohérence.** Le code, les chaînes UI dans le
> dépôt et tous les composants backend sont en anglais.
> Cette traduction décrit l'utilisation ; en cas de
> divergence entre cette traduction et l'original anglais,
> l'original anglais fait foi.

---

## Public et conventions

Ce manuel est écrit pour deux lecteurs en parallèle :

* **Opérateurs** — Directeurs de station, responsables de
  programme, animateurs, DJ. Vous vous connectez à
  l'interface web le matin, planifiez la journée, cliquez
  sur "Enregistrer" et continuez. Tout ce dont vous avez
  besoin pour faire cela se trouve dans le corps principal
  de chaque chapitre.

* **Techniciens** — Administrateurs, ingénieurs,
  intégrateurs. Vous devez également savoir ce qui se passe
  en dessous : quelle table de base de données l'interface
  écrit, quel endpoint API le bouton déclenche, quel
  service doit être actif pour que la fonction marche.
  Cherchez les encadrés **Comment ça marche sous le capot** ;
  ils couvrent les détails internes sans alourdir le flux
  opérateur.

### Conventions visuelles

| Marque | Signification |
|---|---|
| **Gras** | Libellé de bouton, élément de menu ou nom de champ tel qu'il apparaît dans l'interface. |
| `code` | Valeur littérale que l'opérateur saisit ou que le système affiche textuellement — un nom de fichier, une clé de configuration, une URL de stream. |
| > Bloc de citation | Note marginale, mise en garde ou conseil opérateur. Peut être survolé à la première lecture. |
| **Comment ça marche sous le capot** | Encadré technique — table de base de données, endpoint API, décision du scheduler. Les opérateurs peuvent sauter. |
| **Pourquoi ça marche ainsi** | Encadré de décision de conception — renvoie au numéro de section ARCHITECTURE correspondant lorsque pertinent. |

### URL et chemins par défaut

Sauf si votre installation les redéfinit dans
`config/libretime.conf` :

| Quoi | Par défaut |
|---|---|
| Interface web (frontend Apache) | `http://<station-host>/` |
| API REST Django | `http://localhost:8765/api/v2/` |
| Serveur de streaming Icecast | `http://localhost:8000/` |
| Racine d'installation | `C:\rastatime\` |
| Répertoire de logs | `C:\rastatime\logs\` |
| Bibliothèque média sur disque | `C:\rastatime\media\` |
| Cache audio local de l'opérateur | `C:\rastatime\scheduler\` |
| Fichier de configuration | `C:\rastatime\config\libretime.conf` |

Si votre station utilise des chemins différents, substituez
partout.

---

## Comment RASTATIME est organisé

RASTATIME est **piloté par calendrier**. Tout ce qui passe
à l'antenne est soit :

1. Une **émission** placée dans le calendrier à une heure
   précise, soit
2. Le **fallback** qui remplit le temps d'antenne quand
   aucune émission n'est en cours.

Une émission est un créneau dans le calendrier ; le créneau
est *rempli* avec du contenu (pistes, smart blocks,
webstreams, line-ins) soit manuellement dans le show-builder,
soit automatiquement via une autoloading playlist, soit les
deux. Quand le créneau commence, le moteur de playout joue
le contenu rempli. Quand le créneau se termine, le moteur
passe à ce qui suit.

Le **tableau de bord** en haut à droite montre ce qui est
actuellement à l'antenne, ce qui arrive, et quels streams
de sortie sont en bonne santé.

```
   ┌──────────────────────────┐         ┌────────────────────────────────┐
   │      OPÉRATEUR (vous)    │         │     CALENDRIER (planning)       │
   │                          │  crée   │                                │
   │  • Planifie le planning  │────────▶│  • Émissions ancrées dans temps│
   │  • Remplit les émissions │         │  • Chaque émission = 1 ligne   │
   │  • Gère la bibliothèque  │         │    dans cc_show_instances      │
   └──────────────────────────┘         └─────────────────┬──────────────┘
              ▲                                           │
              │ voient dans tableau de bord               │ scheduler dispatche
              │                                           ▼
   ┌──────────┴───────────────┐         ┌────────────────────────────────┐
   │  EN COURS (sortie)       │◀────────│ MOTEUR DE PLAYOUT (VLC)        │
   │                          │ alimente│                                │
   │  • Icecast :8000         │         │  • Joue fichiers / webstreams │
   │  • Fichier d'enregistr.  │         │  • Bascule vers source live   │
   │  • Sortie studio optnl.  │         │  • Émet événements start/end  │
   └──────────────────────────┘         └────────────────────────────────┘
```

Tout dans ce manuel est rattaché à l'une de ces quatre
boîtes.

---

## Le manuel en un coup d'œil

Chaque lien ci-dessous ouvre un sous-document concentré
dans [`docs/manual/fr/`](.). Lisez-les dans n'importe quel
ordre — le document maître ci-dessus est la seule chose
qu'ils supposent tous.

### Opération de diffusion quotidienne

| Chapitre | Contenu |
|---|---|
| [Premiers pas](./GETTING_STARTED.md) | Première connexion, tour du tableau de bord, concepts de base, vue d'ensemble des rôles. Lisez ceci en premier si vous n'avez jamais utilisé RASTATIME. |
| [Tableau de bord](./DASHBOARD.md) | Widget En cours, état de source, surcharge manuelle, mettre la station en direct depuis un microphone. |
| [Calendrier](./CALENDAR.md) | Créer des émissions, modifier, glisser-déposer, émissions récurrentes, répétitions, animateurs. |
| [Modèles d'émission](./SHOW_TEMPLATES.md) | Réutiliser les paramètres d'émission sans les retaper chaque semaine. |
| [Démarrage différé d'émission](./DELAYED_START.md) | Laisser une émission inscrite commencer en retard quand l'émission qui la précède a dépassé, au lieu de rogner cette émission. Le retard se propage à travers les émissions inscrites consécutives jusqu'à la première ancre à heure fixe. |

### Contenu et bibliothèque

| Chapitre | Contenu |
|---|---|
| [Bibliothèque](./LIBRARY.md) | Pistes, smart blocks, playlists. Recherche, import, organisation. |
| [Webstreams](./WEBSTREAMS.md) | Y compris la longueur par défaut à la seconde près (2026-05-19). |
| [Line-In](./LINE_IN.md) | La vue combinée bibliothèque-et-playlist pour les entrées live nommées. |

### Automatisation

| Chapitre | Contenu |
|---|---|
| [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) | Laisser une playlist se construire elle-même pour chaque instance d'une émission, y compris la gestion de la réserve d'outro. |
| [Auto DJ](./AUTO_DJ.md) | Le remplisseur d'arrière-plan qui crée des émissions dans les trous du calendrier et complète les émissions incomplètes. |
| [Demandes de titres](./SONG_REQUESTS.md) | Laisser les auditeurs demander des titres depuis un widget public, qui passent automatiquement dans une request show. |
| [Infos-trafic](./TRAFFIC_ALERTS.md) | Faire passer des MP3 de bulletins de circulation de dernière minute dans l'émission en cours via un smart block — en ~10 minutes au prochain créneau trafic, sans intervention sur le playout. |
| [Enregistrement par émission](./RECORD_PER_SHOW.md) | Capturer la sortie complète à l'antenne d'une émission dans un fichier. |
| [Enregistrement 24/7](./RECORD_PER_HOUR.md) | Enregistrer toute la sortie à l'antenne 24h/24, un fichier par heure — pour la conformité, la réécoute et la sauvegarde d'urgence. |

### Sortie et infrastructure

| Chapitre | Contenu |
|---|---|
| [Streams](./STREAMS.md) | Configurer jusqu'à quatre streams de sortie, surveiller les compteurs d'auditeurs, dépannage. |
| [Analytics](./ANALYTICS.md) | Playout History (ce qui est réellement passé à l'antenne, journaux exportables), History Templates, Listener Stats (audience par flux et par émission au fil du temps). |
| [Machine locale](./LOCAL_MACHINE.md) | Sortie carte son, entrée line-in, dossier d'import local. |
| [Widgets publics intégrables](./WIDGETS.md) | Widgets prêts-à-l'emploi pour le site web public de votre station (Now Playing — Show / Track, Weekly Program, Player). |

### Administration

| Chapitre | Contenu |
|---|---|
| [Utilisateurs et rôles](./USERS_AND_ROLES.md) | Super Admin, Admin, Program Manager, DJ, Invité — ce que chaque rôle peut faire. |
| [Paramètres](./SETTINGS.md) | Tour de chaque page sous le menu Paramètres. |
| [Langues (i18n)](./I18N.md) | Changer la langue de l'interface ; ajouter une traduction. |

---

## Quand quelque chose ne fonctionne pas

Ce manuel couvre le **chemin heureux normal**. Quand
quelque chose ne se comporte pas comme le manuel le
décrit, les procédures de récupération vivent ailleurs :

* [`docs/operator/DEVICE_MISSING.md`](../../operator/DEVICE_MISSING.md)
  — Une carte son ou un line-in configuré n'est plus
  branché.
* [`docs/operator/LINE_IN_BROKEN.md`](../../operator/LINE_IN_BROKEN.md)
  — Line-in présent mais produit silence ou bruit.
* [`docs/operator/CRASH_RECOVERY.md`](../../operator/CRASH_RECOVERY.md)
  — Un service a planté ; ordre de redémarrage ; comment
  confirmer la récupération.
* [`docs/operator/RESTART_ORDER.md`](../../operator/RESTART_ORDER.md)
  — Démarrer à froid toute la pile dans le bon ordre.
* [`docs/operator/BACKUP.md`](../../operator/BACKUP.md)
  — Prendre, vérifier et restaurer une sauvegarde.
* [`docs/operator/UPGRADE.md`](../../operator/UPGRADE.md)
  — Mettre à jour vers une nouvelle version RASTATIME.

Ces runbooks ne sont actuellement disponibles qu'en
anglais.

---

## Où aller ensuite

* Si vous **venez d'installer** RASTATIME et voulez mettre
  une station à l'antenne pour la première fois,
  commencez par [Premiers pas](./GETTING_STARTED.md), puis
  [Calendrier](./CALENDAR.md), puis [Streams](./STREAMS.md).

* Si vous **migrez depuis LibreTime / Airtime**, les
  différences à connaître en premier sont :
  [Enregistrement par émission](./RECORD_PER_SHOW.md)
  (capture maintenant toute la sortie à l'antenne, pas
  seulement le line-in), [Auto DJ](./AUTO_DJ.md) (nouveau
  dans RASTATIME) et [Machine locale](./LOCAL_MACHINE.md)
  (remplace l'ancienne page "Soundcard" et ajoute la
  fonctionnalité dossier d'import).

* Si vous devez **installer RASTATIME** de zéro, ce manuel
  n'est pas le bon document — voir
  [`docs/operator/INSTALL.md`](../../operator/INSTALL.md).

* Si vous devez **comprendre pourquoi** une fonctionnalité
  est conçue comme elle l'est, chaque section ici renvoie
  au chapitre correspondant dans
  [ARCHITECTURE](../../../RASTATIME_ARCHITECTURE_DRAFT_v0.1.md).

---

## Glossaire

| Terme | Signification |
|---|---|
| **Show / Émission** | Un créneau dans le calendrier avec début, fin, nom et (habituellement) du contenu planifié. Persisté dans `cc_show` + `cc_show_instances`. |
| **Instance** | Une occurrence concrète d'une émission. Une émission quotidienne est une ligne `cc_show` + plusieurs lignes `cc_show_instances`. |
| **Schedule item** | Une ligne dans la playlist d'une instance d'émission — typiquement un fichier, mais aussi un smart block, webstream ou line-in. Persisté dans `cc_schedule`. |
| **Playlist** | Une liste ordonnée réutilisable d'items. Persistée dans `cc_playlist` + `cc_playlistcontents`. |
| **Smart Block** | Une requête dans une playlist qui s'étend en un ensemble de pistes au moment du build, optionnellement limitée à "temps restant dans l'émission". Persisté dans `cc_block`. |
| **Webstream** | Une URL pointant vers une autre source Icecast / Shoutcast / HTTP MP3/AAC. Persisté dans `cc_webstream`. |
| **Line-In** | Une entrée audio live nommée sur la machine de l'opérateur (un microphone, un mixeur, un lecteur CD externe). Persisté dans `rastatime_linein`. |
| **Autoloading playlist** | Une playlist attachée à une *définition d'émission* pour que chaque instance de l'émission obtienne le contenu de la playlist construit automatiquement dans son planning. |
| **Auto DJ** | Un processus d'arrière-plan qui crée des émissions dans les trous du calendrier et complète les émissions incomplètes. Distinct des autoloading playlists. |
| **Démarrage différé (delayed start)** | Une inscription volontaire par émission (`cc_show.allow_delayed_start`) qui laisse une émission commencer plus tard que son créneau de calendrier lorsque l'émission précédente a dépassé, en gardant sa propre fin fixe. Une tâche d'arrière-plan l'applique quelques minutes avant l'antenne. |
| **Song request (demande de titre)** | Un souhait de titre envoyé par un auditeur, collecté par un widget public et diffusé automatiquement par une request show (une émission à autoloading playlist avec un Smart Block *Use requests*). Persisté dans `rastatime_song_request`. |
| **Info-trafic (Traffic Alert)** | Un MP3 de bulletin de circulation arrivant à la dernière minute, qui doit passer dans l'émission en cours en ~10 minutes. La source est un smart block choisi dans les Paramètres (`traffic_alert_block_id`) ; une émission contenant ce bloc dans son autoloading playlist se remplit au fur et à mesure et diffuse, au prochain créneau trafic, l'alerte la plus ancienne non encore planifiée. |
| **Stream de sortie** | L'un des jusqu'à quatre mountpoints Icecast vers lesquels le playout diffuse. Configuré sous Paramètres → Streams. |
| **Source switcher** | Le mécanisme interne qui décide quelle source audio (scheduler, line-in, master DJ, show DJ) est actuellement à l'antenne. |
| **File d'attente fallback** | Une boucle configurée qui se joue quand aucune émission n'est planifiée et qu'Auto DJ est désactivé. |
| **Dossier d'import local** | Un répertoire sur la machine de l'opérateur que l'analyzer surveille pour les nouveaux fichiers ; tout ce qui est déposé ici est auto-importé dans la bibliothèque. |

---

*Ce document est versionné dans le dépôt RASTATIME. Voir
le [CHANGELOG](../../../CHANGELOG.md) pour ce qui a changé
dans le manuel lui-même ; voir les sous-documents par
chapitre pour ce qui a changé dans chaque fonctionnalité.*
