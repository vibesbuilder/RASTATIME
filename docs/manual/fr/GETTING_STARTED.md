# Premiers pas

> **Où vous êtes dans le manuel.** Ce chapitre suppose que
> RASTATIME est déjà installé et que l'interface web est
> joignable. Si non, parcourez d'abord
> [`docs/operator/INSTALL.md`](../../operator/INSTALL.md).
>
> **Temps de lecture.** ~15 minutes pour la piste
> opérateur, ~25 avec les apartés techniques.

Ce chapitre guide un opérateur tout neuf à travers la
première connexion, le premier écran qu'il voit, le rôle
de chaque menu principal, et la séquence minimale pour
mettre une piste à l'antenne. À la fin, vous aurez :

1. Connecté avec les identifiants par défaut et changé
   votre mot de passe.
2. Identifié quel rôle utilisateur vous avez et ce qu'il
   vous permet de faire.
3. Trouvé la Bibliothèque, le Calendrier et le Tableau de
   bord.
4. Créé et diffusé votre première piste planifiée.
5. Vérifié que le stream de sortie atteint les auditeurs.

---

## 1. Première connexion

Ouvrez `http://<station-host>/` dans n'importe quel
navigateur moderne (Chrome, Edge, Firefox ; Internet
Explorer n'est *pas* supporté).

Les identifiants super-admin par défaut d'une installation
fraîche sont :

| Champ | Valeur |
|---|---|
| Nom d'utilisateur | `admin` |
| Mot de passe | `admin` |

> **Changez ceci maintenant.** Dès que vous êtes connecté,
> allez à **Paramètres → Gérer les utilisateurs**, cliquez
> sur `admin`, et définissez un vrai mot de passe.
> RASTATIME ne force pas un changement de mot de passe à
> la première connexion — il ne peut pas, parce que
> certaines installations scriptent la première connexion.
> Le compte par défaut est un vecteur d'attaque connu si
> le serveur est joignable depuis l'extérieur de votre
> LAN studio.

> **Comment ça marche sous le capot.** Les identifiants
> vivent dans `cc_subjs`. Les mots de passe sont hachés
> (bcrypt). Le cookie de session est `PHPSESSID` ; le
> stockage de session Zend est dans
> `C:\rastatime\runtime\sessions\` par défaut. Une
> connexion enregistre aussi `last_login` pour
> l'utilisateur — visible sur la page Gérer les
> utilisateurs.

Si vous ne pouvez pas vous connecter : le runbook
[`CRASH_RECOVERY`](../../operator/CRASH_RECOVERY.md)
couvre le cas où Apache, mod_fcgid ou le service API est
hors service. Tant que ceux-ci ne tournent pas, aucune
connexion ne peut réussir.

---

## 2. La barre supérieure et ce que fait chaque élément

Après connexion, vous atterrissez sur le **Calendrier** par
défaut. La barre de navigation supérieure contient toute
autre zone de l'application :

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │  RASTATIME  │  Tab. bord  Calendrier  Biblio.  Paramètres  Aide │ utilisateur ▾│
  └─────────────────────────────────────────────────────────────────────┘
```

| Menu | Ce qui s'y trouve |
|---|---|
| **Tableau de bord** | Ce qui est à l'antenne maintenant, ce qui arrive, état de source (scheduler / line-in / master DJ / show DJ), et un panneau de surcharge manuelle. Voir [Tableau de bord](./DASHBOARD.md). |
| **Calendrier** | La grille de planning. Créer / modifier / supprimer des émissions. Glisser-déposer les émissions. Voir [Calendrier](./CALENDAR.md). |
| **Bibliothèque** | Toutes vos pistes, smart blocks, playlists, webstreams et line-ins. Rechercher et filtrer. Voir [Bibliothèque](./LIBRARY.md). |
| **Paramètres** | Streams, Machine locale (carte son + dossier d'import), Auto DJ, Modèles d'émission, Préférences générales, Gérer les utilisateurs, Localisation. Chacun est un sous-document séparé dans ce manuel. |
| **Aide** | **Mise en route** (le démarrage rapide en trois étapes), **Manuel Utilisateur** (ce manuel, lisible dans le navigateur en anglais, allemand, français et espagnol — depuis le 2026-10-01), **Contribuer à RASTATIME** (le projet GitHub) et **Qu'est-ce qui a changé ?** (les notes de version GitHub). |
| **Menu utilisateur** (en haut à droite) | Déconnexion, changer de langue, voir son propre profil, sa propre clé API (pour les scripts). |

> **Conseil opérateur.** Le Calendrier est le centre de
> gravité. Vous pouvez presque tout faire depuis le menu
> contextuel du Calendrier — créer une émission, la remplir
> depuis la bibliothèque, attacher un modèle, l'ouvrir
> pour modification. Les autres menus principaux sont
> surtout pour la configuration ponctuelle.

---

## 3. Rôles — qui vous êtes décide ce que vous voyez

Chaque utilisateur a exactement un **rôle**. Le rôle est
défini sur la page Gérer les utilisateurs et est la seule
chose qui contrôle ce que l'interface vous laisse faire.

| Rôle | Peut voir / faire |
|---|---|
| **Invité (G)** | Tableau de bord en lecture seule. Pas de Calendrier, pas de Bibliothèque, pas de Paramètres. Utilisé pour les tableaux de bord de surveillance ou les écrans d'information à la réception. |
| **DJ (H)** | Ses propres émissions + ses propres fichiers seulement. Peut remplir ses propres émissions, télécharger ses propres pistes. Ne peut pas créer d'émissions. Ne peut pas voir les fichiers d'autres DJ. |
| **Program Manager (P)** | Accès complet au Calendrier et à la Bibliothèque. Peut créer et modifier des émissions pour n'importe quel DJ. Ne peut pas changer les paramètres au niveau station. |
| **Admin (A)** | Tout ce qu'un Program Manager peut faire, plus les paramètres au niveau station (Streams, Machine locale, Auto DJ, Modèles d'émission, Localisation). |
| **Super Admin (S)** | Tout. Plus la capacité de créer et de rétrograder d'autres Admins. Réservé au propriétaire de la station / admin technique. |

> **Pourquoi ça marche ainsi.** L'ACL basée sur les rôles
> est appliquée côté serveur dans `configs/ACL.php`. Cacher
> les éléments de menu dans l'interface n'est qu'un confort
> — le back-end vérifie chaque action contre le rôle de
> l'utilisateur. Un DJ ne peut pas modifier l'émission d'un
> autre DJ même en construisant l'URL à la main. Voir
> ARCHITECTURE §11 pour la matrice complète des rôles.

[`USERS_AND_ROLES`](./USERS_AND_ROLES.md) couvre
l'attribution des rôles et la matrice des permissions
ressource par ressource.

---

## 4. Les dix premières minutes : de station vide à piste à l'antenne

Une installation RASTATIME toute nouvelle a une
bibliothèque vide, un calendrier vide, et Icecast en cours
d'exécution mais sans audio atteignant son entrée. Cette
section guide le chemin le plus court pour résoudre les
trois.

### 4.1 Confirmer que le stream de sortie existe

Paramètres → **Streams**.

L'installation par défaut livre **Stream 1** configuré avec :

| Champ | Par défaut |
|---|---|
| Type | Icecast |
| Serveur | `localhost` |
| Port | `8000` |
| Mount | `/rastatime` |
| Format | MP3, 192 kbps, 44,1 kHz, stéréo |

La colonne **Connecté** devrait déjà afficher un badge vert
si le service playout tourne. S'il affiche rouge
("Déconnecté"), le playout n'a pas démarré — vérifiez avec
`Get-Service RASTATIME-PLAYOUT` dans PowerShell.

> **Comment ça marche sous le capot.** L'interface web ne
> pousse pas le stream elle-même — le service Windows
> **RASTATIME-PLAYOUT** le fait. Il lit la configuration
> de stream depuis `cc_pref` au démarrage et à chaque
> sauvegarde, ouvre une connexion source Icecast et
> commence à publier du silence (ou le contenu fallback si
> configuré) immédiatement. Le badge vert / rouge est
> piloté par l'endpoint `/api/v2/streams` qui vérifie
> l'état live de la sortie source `libvlc`.

Pour écouter, ouvrez dans un autre onglet :
`http://<station-host>:8000/rastatime`. Vous devriez
entendre du silence ou la boucle fallback si configurée.
Si vous n'entendez rien du tout et que le badge est vert,
le périphérique de sortie de la machine de l'opérateur
est la prochaine chose à vérifier — voir
[Machine locale](./LOCAL_MACHINE.md).

### 4.2 Téléverser une piste

Bibliothèque → **Téléverser**.

Glissez n'importe quel fichier MP3, FLAC ou WAV sur la
zone de téléversement. L'analyzer exécute le fichier à
travers ffprobe (métadonnées) et ffmpeg (jouabilité —
décode tout le fichier vers `null` pour confirmer qu'il
joue de bout en bout), puis la ligne apparaît dans la
liste de la bibliothèque.

> **Conseil opérateur.** Si vous avez un dossier de
> musique à importer, ne les glissez pas un par un.
> Définissez le **Dossier d'import local** sous
> Paramètres → Machine locale sur un répertoire du serveur ;
> tout ce qui est déposé dans ce répertoire est
> auto-importé au prochain poll de l'analyzer (toutes les
> 60 s par défaut). Voir [Machine locale](./LOCAL_MACHINE.md).

> **Comment ça marche sous le capot.** Le téléversement
> écrit dans un répertoire de staging sous
> `C:\rastatime\import\`, puis met en file un job
> d'analyzer. L'analyzer analyse les métadonnées (tags
> ID3 / Vorbis) et vérifie la jouabilité via
> `ffmpeg -v error -i <file> -f null -` ; voir
> ARCHITECTURE §23.14. En cas de succès, le fichier est
> déplacé vers la bibliothèque média à
> `C:\rastatime\media\<owner>\<year>\<month>\` et une
> ligne `cc_files` est insérée. En cas d'échec dur
> (erreur de décodage), le téléversement est rejeté avec
> "File is unplayable". En cas d'échec mou (avertissements
> du décodeur mais décodage complet), l'import réussit
> avec un badge d'avertissement jaune.

### 4.3 Créer une émission

Calendrier → cliquez sur n'importe quelle cellule vide
dans l'heure suivante → **Nouvelle émission**.

Remplissez :

| Champ | Valeur suggérée |
|---|---|
| **Nom** | `Test` |
| **Date / heure de début** | Maintenant + 2 minutes |
| **Durée** | 10 minutes |
| **Genre** | laisser vide |
| **Animateurs** | vous-même |

Laissez tout le reste aux valeurs par défaut. Cliquez sur
**Enregistrer**.

L'émission apparaît dans le calendrier comme un bloc
coloré.

> **Comment ça marche sous le capot.** Enregistrer le
> formulaire écrit une ligne dans `cc_show` (la définition
> de l'émission) et au moins une ligne dans
> `cc_show_instances` (chaque occurrence). Pour une
> émission ponctuelle comme celle-ci, vous obtenez une de
> chaque. Une émission récurrente crée les instances avec
> empressement jusqu'à l'horizon configuré (~3 mois par
> défaut).

### 4.4 Remplir l'émission avec la piste

Calendrier → cliquez sur l'émission → **Planifier les
pistes**.

Le show-builder s'ouvre avec l'émission à gauche et la
bibliothèque à droite. Glissez votre piste téléversée
depuis la bibliothèque vers l'émission. Elle apparaît
comme premier item planifié.

Cliquez sur **Enregistrer** en haut du show-builder.

> **Conseil opérateur.** Vous pouvez aussi faire un clic
> droit sur une émission vide dans le calendrier et
> choisir **Appliquer un modèle** pour la remplir depuis
> un [Modèle d'émission](./SHOW_TEMPLATES.md)
> réutilisable, ou attacher une
> [Autoloading Playlist](./AUTOLOADING_PLAYLISTS.md) pour
> que chaque instance se remplisse elle-même.

### 4.5 Attendre que l'émission commence

À l'heure de début de l'émission :

1. Le widget **En cours** du tableau de bord passe de
   "Fallback" (ou "Silence") au titre de la piste.
2. Le stream Icecast à
   `http://<station-host>:8000/rastatime` commence à
   jouer votre piste.
3. La barre de remplissage du Calendrier pour l'émission
   passe de gris ("0 %") à coloré ("100 %" si la piste
   remplit tout le créneau, moins sinon).

Si l'un d'eux ne se produit pas, le runbook
[`CRASH_RECOVERY`](../../operator/CRASH_RECOVERY.md)
couvre le chemin de diagnostic.

---

## 5. Opérations courantes du premier jour

Vous en savez maintenant assez pour faire le travail
quotidien. Voici où trouver chaque tâche courante dans le
reste du manuel :

| Je veux… | Allez à |
|---|---|
| Téléverser un lot de pistes | [Bibliothèque](./LIBRARY.md) |
| Planifier le planning de demain | [Calendrier](./CALENDAR.md) |
| Faire une émission hebdomadaire récurrente | [Calendrier](./CALENDAR.md) → Émissions récurrentes |
| Utiliser la même configuration d'émission chaque semaine | [Modèles d'émission](./SHOW_TEMPLATES.md) |
| Faire qu'une émission se remplisse elle-même | [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) |
| Remplir automatiquement les trous du calendrier | [Auto DJ](./AUTO_DJ.md) |
| Mettre la station en direct depuis un microphone | [Tableau de bord](./DASHBOARD.md) → Source live |
| Ajouter le stream Icecast externe d'un invité comme webstream | [Webstreams](./WEBSTREAMS.md) |
| Ajouter le mixeur studio comme line-in nommé | [Line-In](./LINE_IN.md) |
| Enregistrer ce qui était à l'antenne aujourd'hui | [Enregistrement par émission](./RECORD_PER_SHOW.md) |
| Ajouter un second stream de sortie (ex. faible débit mobile) | [Streams](./STREAMS.md) |
| Ajouter un nouveau DJ | [Utilisateurs et rôles](./USERS_AND_ROLES.md) |
| Changer la langue de l'interface | [Langues](./I18N.md) |
| Tour du menu Paramètres | [Paramètres](./SETTINGS.md) |

---

## 6. Trois habitudes pour éviter la douleur plus tard

Celles-ci ne sont pas optionnelles. Elles vous épargneront
une longue soirée à un moment donné.

1. **Utilisez les Modèles d'émission dès le jour deux.**
   Si vous vous retrouvez à taper le même nom / animateurs
   / couleurs deux fois, sauvegardez-le comme modèle. Les
   animateurs qui apprennent cela ne reviennent jamais en
   arrière.
   Voir [Modèles d'émission](./SHOW_TEMPLATES.md).

2. **Configurez le Dossier d'import local.** Les
   téléversements glisser-déposer du navigateur conviennent
   pour un ou deux fichiers, mais un import en lot de 200
   pistes va faire timeout le navigateur et vous frustrer.
   Le Dossier d'import local interroge le répertoire sur
   le serveur toutes les 60 s et ne fait jamais timeout.
   Voir [Machine locale](./LOCAL_MACHINE.md).

3. **Faites une sauvegarde le jour où vous passez en
   direct.** RASTATIME livre un script de sauvegarde en
   une commande qui capture la base de données, les médias
   téléversés et la configuration. Programmez-le pour
   tourner toutes les nuits sur la même machine, et une
   fois par semaine vers un stockage hors machine.
   Voir [`docs/operator/BACKUP.md`](../../operator/BACKUP.md).

---

## Où aller ensuite

* Si vous n'avez le temps que pour un chapitre de plus
  aujourd'hui, lisez [Calendrier](./CALENDAR.md) — le
  calendrier est là où vous passerez la plupart de votre
  temps.
* Pour le lecteur technique qui veut comprendre le système
  de bout en bout avant de continuer, le document
  [ARCHITECTURE](../../../RASTATIME_ARCHITECTURE_DRAFT_v0.1.md)
  donne l'image complète en une lecture.
* Pour un opérateur qui passe en direct pour la première
  fois, parcourez aussi
  [`docs/operator/INSTALL.md`](../../operator/INSTALL.md)
  §6 ("Smoke test") pour confirmer que chaque service est
  en bonne santé avant d'annoncer la station.
