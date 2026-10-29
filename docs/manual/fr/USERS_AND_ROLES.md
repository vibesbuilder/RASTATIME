# Utilisateurs et rôles

> **Où vous êtes dans le manuel.** Ce chapitre est la référence des
> permissions pour le reste du manuel : quand un autre chapitre indique
> « Program Managers et Admins seulement », la matrice du §2 donne le
> tableau complet.  Il décrit l'état après l'audit des rôles du
> 25/10/2026.

RASTATIME connaît quatre rôles.  Chaque compte en a exactement un, et le
serveur le vérifie à chaque requête - masquer un bouton n'est qu'un
confort, le serveur refuse l'action de toute façon.  Ce chapitre
couvre :

1. Les quatre rôles.
2. La matrice des permissions.
3. Gérer les utilisateurs (Paramètres → Utilisateurs).
4. Votre propre profil (Mon profil).
5. Identifiants pour les connexions en direct.
6. Accès API.
7. Sessions et protection contre les abus.
8. Protection de la connexion.
9. Répartition typique des rôles et questions fréquentes.

---

## 1. Les quatre rôles

| Rôle | Utilisateur typique | En une phrase |
|---|---|---|
| **Invité** | Écran d'accueil, visiteur | Voit le tableau de bord et le calendrier, ne modifie rien. |
| **DJ** | Un animateur | Travaille avec des pistes : upload, ses propres playlists et smart blocks, remplit les émissions qu'il anime. |
| **Program Manager** | Coordination des programmes | Dirige le programme : toutes les émissions, tous les contenus, webstreams, Line-Ins, podcasts, Auto DJ, modèles d'émission, widgets. |
| **Admin** | Technique de la station | Tout, plus les paramètres de la station et les comptes utilisateurs. |

Chaque rôle comprend tout ce que le rôle au-dessus de lui dans le
tableau peut faire.

**Le compte d'installation `admin`** est un Admin comme les autres,
mais il ne peut pas être supprimé - ni sous Paramètres → Utilisateurs ni
par l'API.  Les Admins peuvent créer d'autres Admins.

**L'ancien rôle Super Admin** (d'Airtime) a été retiré le 25/10/2026 :
un compte de ce type devient Admin (migration de base de données 0073),
et les connexions externes (LDAP / FreeIPA, authentification par
en-tête) du groupe super-admin se connectent comme Admins.

> **Sous le capot.** Le rôle est la lettre unique de `cc_subjs.type`
> (G, H, P, A ; S est retiré).  Les règles générales se trouvent dans
> `application/configs/ACL.php` ; les règles plus fines (propriétaire
> d'un fichier, animateur d'une émission, Program Manager ou plus) sont
> vérifiées dans les contrôleurs.  L'audit et ses constats :
> `docs/operator/ROLE_AUDIT_2026-10.md`.

---

## 2. La matrice des permissions

✓ = autorisé, – = non autorisé.  « Propres » signifie que l'utilisateur
est propriétaire de l'objet (il l'a téléversé ou créé) ; « animées »
signifie que l'utilisateur est animateur (host) de l'émission.

| Domaine | Invité | DJ | Program Manager | Admin |
|---|:---:|:---:|:---:|:---:|
| **Compte** | | | | |
| Modifier son propre profil (nom, e-mail, mot de passe, langue, fuseau horaire) | ✓ | ✓ | ✓ | ✓ |
| Gérer les autres utilisateurs (Paramètres → Utilisateurs) | – | – | – | ✓ |
| **Tableau de bord et sources en direct** | | | | |
| Voir Now Playing et les émissions programmées | ✓ | ✓ | ✓ | ✓ |
| Voir le statut Auto DJ dans l'en-tête | ✓ | ✓ | ✓ | ✓ |
| Activer ou couper une source en direct (Master / Show) | – | pendant une émission animée | ✓ | ✓ |
| Annuler l'émission en cours | – | – | ✓ | ✓ |
| **Calendrier** | | | | |
| Voir le calendrier | ✓ | ✓ | ✓ | ✓ |
| Créer, modifier, déplacer, redimensionner, supprimer, annuler des émissions | – | – | ✓ | ✓ |
| Vider le contenu d'une émission, teasers, modèles d'émission dans la boîte de dialogue | – | – | ✓ | ✓ |
| Programmer du contenu dans une émission | – | émissions animées | ✓ | ✓ |
| **Bibliothèque** | | | | |
| Voir la bibliothèque (pistes, playlists, smart blocks, liste des podcasts) | – | ✓ | ✓ | ✓ |
| Téléverser des pistes | – | ✓ | ✓ | ✓ |
| Modifier métadonnées et points de cue, supprimer des pistes | – | propres | ✓ | ✓ |
| Changer le propriétaire d'une piste | – | – | – | ✓ |
| Créer des playlists et des smart blocks | – | ✓ | ✓ | ✓ |
| Modifier, mélanger, supprimer des playlists et des smart blocks | – | propres | ✓ | ✓ |
| Voir, utiliser et modifier webstreams et Line-Ins | – | – | ✓ | ✓ |
| S'abonner à des podcasts, les modifier, les supprimer ; épisodes | – | – | ✓ | ✓ |
| Publier dans le podcast de la station (Section Podcast) | – | – | ✓ | ✓ |
| **Statistiques** | | | | |
| Statistiques des auditeurs | – | ✓ | ✓ | ✓ |
| Historique de diffusion : consulter | – | émissions animées | ✓ | ✓ |
| Historique de diffusion : ajouter, modifier, supprimer des entrées | – | émissions animées | ✓ | ✓ |
| Modèles d'historique | – | – | – | ✓ |
| **Widgets** | | | | |
| Pages Widgets (codes d'intégration, paramètres des widgets) | – | – | ✓ | ✓ |
| **Paramètres** | | | | |
| Auto DJ | – | – | ✓ | ✓ |
| Page Show Templates | – | – | ✓ | ✓ |
| Langue par défaut de la station (dialogue du premier démarrage) | – | – | ✓ | ✓ |
| Général, Utilisateurs, Types de piste, Flux, Machine locale, Import / Export, Backup, Statut | – | – | – | ✓ |

Ce que les rôles voient différemment :

- **Les invités** ont le tableau de bord et le calendrier.  La
  bibliothèque affiche « Vous n'avez pas l'autorisation de voir la
  bibliothèque. » ; le menu **Nouveau**, **Upload** et le menu
  **Widgets** ne sont pas proposés.
- **Les DJ** voient toutes les pistes, playlists et smart blocks de la
  station, mais ne modifient que les leurs.  Ils programment dans les
  émissions qu'ils animent - n'importe quelle piste, playlist ou smart
  block, aussi ceux des autres.  Les webstreams et les Line-Ins leur
  sont masqués (onglets de la bibliothèque, menu **Nouveau**) ; un DJ ne
  peut pas les ajouter à des playlists ni à des émissions.  Dans
  l'historique de diffusion, un DJ obtient le *Show Summary* de ses
  propres émissions et peut y ajouter, modifier et supprimer des
  entrées.  La liste des podcasts est en lecture seule pour eux, et le
  menu **Widgets** ne leur est pas proposé.
- **Les Program Managers** dirigent le programme, utilisent les pages
  **Widgets** et ouvrent trois pages de paramètres : **Auto DJ**, **Show
  Templates** et Mon profil.  Les modèles d'émission s'enregistrent et
  s'appliquent dans la boîte de dialogue de l'émission et se renomment
  ou se suppriment sous Paramètres → Show Templates.
- **Les Admins** gèrent en plus la station : paramètres, flux, carte
  son, utilisateurs, types de piste, sauvegarde, import / export, statut
  du système.

Le dialogue de langue et de fuseau horaire du premier démarrage règle
pour chacun **sa propre** langue et son fuseau horaire ; la langue par
défaut de toute la station ne change que si un Program Manager ou un
Admin le confirme.

---

## 3. Gérer les utilisateurs

Paramètres → **Utilisateurs** (Admins).

### Créer et modifier un utilisateur

**Nouveau** ouvre la boîte de dialogue de l'utilisateur ; un clic sur une
ligne ouvre la même boîte pour cet utilisateur.

| Champ | Remarques |
|---|---|
| **Nom d'utilisateur** | Le nom de connexion. |
| **Mot de passe** / **Vérifier le mot de passe** | Obligatoire pour un nouvel utilisateur.  En modification, laissez le texte de remplacement pour garder le mot de passe. |
| **Prénom**, **Nom** | Affichés dans les listes d'utilisateurs et comme animateur d'émission. |
| **E-mail** | Adresse de contact. |
| **Téléphone mobile**, **Skype**, **Jabber** | Champs de contact facultatifs. |
| **Type d'utilisateur** | Invité, DJ, Program Manager ou Admin. |

La ligne du compte `admin` n'a pas d'icône de suppression.

### Supprimer un utilisateur

L'icône de suppression dans la liste des utilisateurs supprime le
compte.  Les pistes dont l'utilisateur était propriétaire sont
**transmises** au premier Admin - elles restent dans la bibliothèque.
Vous ne pouvez pas supprimer votre propre compte, et le compte `admin` ne
peut pas être supprimé.

Il n'existe pas d'état « désactivé » : pour retirer l'accès à
quelqu'un, supprimez le compte ou définissez un nouveau mot de passe ;
pour ne laisser qu'un accès en lecture, passez le type à Invité.

### Les utilisateurs dans Import / Export

Paramètres → Import / Export contient les utilisateurs sous forme de
`users.csv` - sans mots de passe ; à l'import, un mot de passe n'est
défini que pour les nouveaux comptes.  Voir
[Import / Export](./IMPORT_EXPORT.md).

---

## 4. Votre propre profil

Paramètres → **Mon profil** - pour tous les rôles, invités compris.

Vous y modifiez votre prénom et votre nom, votre e-mail, votre mot de
passe, les champs de contact, votre **langue d'interface** et votre
**fuseau horaire**.  Le nom d'utilisateur est fixe.  La page enregistre
toujours le compte avec lequel vous êtes connecté ; les autres comptes
sont modifiés par un Admin sous Paramètres → Utilisateurs.

---

## 5. Identifiants pour les connexions en direct

Un DJ qui diffuse en direct (BUTT, Mixxx, …) se connecte à l'entrée en
direct de la station avec l'un des identifiants suivants :

| Identifiant | Accepté quand |
|---|---|
| Le nom d'utilisateur et le mot de passe RASTATIME du DJ | Le DJ anime l'émission à l'antenne, et l'émission utilise la *RASTATIME Authentication* (dialogue de l'émission → *Live Stream Input*). |
| L'identifiant propre de l'émission (*Utiliser l'authentification personnalisée* dans la même section) | Cette émission est à l'antenne. |
| L'identifiant de la source Master (Paramètres → Flux) | Toujours ; prend le pas sur l'émission en cours. |

Le mot de passe personnalisé d'une émission n'est affiché dans le
dialogue de l'émission qu'aux Program Managers et aux Admins.  Les ports
et les points de montage figurent dans le chapitre [Flux](./STREAMS.md).

---

## 6. Accès API

Il n'existe **pas de clés API personnelles**.

- **Les services** (playout, analyzer, scripts sur la machine de la
  station) utilisent la clé API de la station dans
  `config/rastatime.conf` (`Authorization: Api-Key …`).  Traitez-la
  comme un mot de passe.
- **Les personnes** peuvent utiliser l'API REST v2 (`/api/v2/`) avec
  leur propre nom d'utilisateur et mot de passe ; elles obtiennent les
  permissions de leur rôle.
- Quelques points d'accès internes (périphériques Line-In, carte son,
  avertissements preflight, statut des flux, vérification de connexion
  des DJ) ne répondent qu'à la machine de la station elle-même ou à un
  appelant muni de la clé API.

---

## 7. Sessions et protection contre les abus

- **Session.** Une connexion dure jusqu'à la fermeture du navigateur ou
  jusqu'à ce que la session n'ait plus vu de requête pendant un moment
  (PHP `session.gc_maxlifetime`, 24 minutes sur la machine du studio).
  Un onglet RASTATIME ouvert maintient sa session grâce à ses mises à
  jour en arrière-plan.  Se connecter depuis plusieurs navigateurs en
  même temps est possible.
- **Cookie.** Le cookie de session est `Secure`, `HttpOnly` et
  `SameSite=Lax` : d'autres sites web ne peuvent pas utiliser votre
  connexion pour des requêtes en arrière-plan, et les scripts de la page
  ne peuvent pas le lire.
- **Jeton de requête.** Chaque modification faite via l'interface porte
  un jeton lié à votre session.  Le serveur le compare ; une requête
  sans jeton est refusée et journalisée (`CSRF refused` dans
  `logs/legacy.log`).  Un onglet resté ouvert plus d'une semaine peut
  nécessiter un rechargement (F5) avant d'enregistrer.

---

### Comment les mots de passe sont stockés (depuis le 27/10/2026)

RASTATIME stocke les mots de passe sous forme de **hachages bcrypt**
(salés, facteur de coût 12), jamais en clair et plus en MD5 non salé
comme LibreTime.  Une base de données ou une sauvegarde dérobée ne
révèle donc pas les mots de passe.  Les comptes antérieurs au 27/10/2026
continuent de fonctionner : leur ancien hachage est accepté une dernière
fois et remplacé par bcrypt à la prochaine connexion réussie, que ce soit
par l'interface web, un accès DJ ou l'API.  Pour faire disparaître les
anciens hachages aussi des sauvegardes plus anciennes, il suffit de
définir un nouveau mot de passe pour le compte.  La commande
`manage.py password_hashes` indique quels comptes sont déjà migrés.

## 8. Protection de la connexion (depuis le 06/10/2026)

La page de connexion freine les échecs répétés - une nécessité, puisque
l'interface web est accessible depuis Internet.

| Portée | Règle | Effet |
|---|---|---|
| Par adresse source | 10 connexions échouées en 15 minutes | l'adresse attend 15 minutes ; chaque tentative pendant ce temps reçoit « Too many failed login attempts. Please try again in N minute(s). » (HTTP 429), aucun mot de passe n'est vérifié |
| Par nom d'utilisateur | 20 connexions échouées en 60 minutes | le nom attend 5 minutes - volontairement court, pour que quelqu'un qui martèle le nom d'un administrateur depuis de nombreuses adresses ne puisse pas l'exclure durablement |
| Connexion DJ (harbor) | 5 connexions refusées depuis une adresse en 10 minutes | l'adresse est refusée pendant 15 minutes sans interroger l'application web |

Une connexion réussie remet à zéro les compteurs de son adresse et de
son nom.  Les seuils se trouvent dans `constants.php`
(`RASTATIME_LOGIN_*`) et dans le playout (`RejectThrottle`) ; les
tentatives bloquées sont journalisées avec l'adresse
(`logs/legacy.log`, `logs/playout-stdout.log`).

**Voir et lever les blocages.**  Paramètres → Statut → *Blocked
addresses* liste chaque niveau (connexion web par adresse et par
utilisateur, connexion DJ, surveillance du pare-feu) avec le nombre
d'échecs et les minutes restantes ; un bouton **Unblock** efface
l'entrée à tous les niveaux - pour le DJ qui appelle parce qu'un mauvais
mot de passe était enregistré dans son logiciel.  La même liste existe
en PowerShell : `infra\scripts\rt-blocks.ps1` (`-Unblock <adresse>` ou
`-Unblock user:<login>`).  Un DJ qui se connecte **avant** le début de
l'émission est refusé mais jamais compté : seul un mauvais mot de passe
compte.  Les scanners Internet persistants sont bloqués 24 heures dans
le pare-feu Windows par une tâche de surveillance (toutes les
5 minutes ; 50 requêtes refusées en 60 minutes, 3 chemins typiques de
scanner ou 5 mauvais mots de passe DJ) et apparaissent dans la même
liste.  Une réponse « non connecté » (401) ne compte jamais : c'est ce
que reçoit un onglet dont la session a expiré pour ses requêtes en
arrière-plan, et depuis le 07/10/2026 un tel onglet arrête ses requêtes
dès la première.

**Adresses autorisées (depuis le 08/10/2026).**  À côté de **Unblock**,
chaque adresse bloquée a **Allow** : elle est débloquée à tous les
niveaux et ajoutée à la liste *Allowed addresses* en dessous, où vous
pouvez aussi saisir à la main une adresse ou un réseau en notation CIDR
(`203.0.113.0/24`) et supprimer des entrées.  Une adresse autorisée
n'est jamais freinée par la connexion web, jamais limitée par la
connexion DJ et jamais bloquée par la surveillance du pare-feu ; les
adresses du réseau du studio sont exemptées de toute façon.  Gardez la
liste courte - elle désactive tous les freins pour cette adresse - et
préférez un réseau pour une connexion domestique dont l'adresse change
avec le fournisseur.  La liste est conservée dans la base de données et
recopiée dans `config\allowlist.txt` pour le playout et la surveillance.

> **Si vous êtes vous-même bloqué :** attendez les minutes affichées, ou
> demandez à un collègue sur une autre adresse.  En cas d'urgence, les
> compteurs se trouvent dans les tables `cc_login_attempts` (par
> adresse) et `cc_subjs.login_attempts` (par utilisateur).

---

## 9. Répartition typique des rôles et questions fréquentes

### Répartition typique

| Station | Comptes |
|---|---|
| Une personne | le compte `admin` (Admin) ; éventuellement un Invité pour un écran dans le hall |
| Radio associative | `admin` et un compte Admin personnel pour le responsable technique, un Program Manager par domaine de programme, un compte DJ par animateur, éventuellement un Invité |
| Station plus grande | en plus un ou deux Admins pour l'exploitation technique |

Un compte par personne réelle : les comptes partagés empêchent de savoir
qui a modifié quoi.

### « Un DJ ne trouve ni webstream ni Line-In. »

C'est voulu : les DJ travaillent uniquement avec des pistes.  Un Program
Manager ajoute le webstream ou le Line-In à l'émission ou à une
playlist.

### « Un DJ ne peut pas modifier l'horaire ou la description de son émission. »

Les émissions sont créées et modifiées par les Program Managers et les
Admins.  Les DJ remplissent les émissions qu'ils animent et peuvent
activer et couper leur source en direct pendant leur émission.

### « Quelqu'un a besoin des droits de DJ et de Program Manager. »

Donnez-lui le rôle Program Manager - il comprend tout ce qu'un DJ peut
faire.

### « Un utilisateur peut-il avoir deux rôles ? »

Non, exactement un par compte.

### « Le mot de passe d'un Admin est perdu. »

Un autre Admin en définit un nouveau sous Paramètres → Utilisateurs -
une raison de garder deux comptes Admin.  Si plus aucun Admin ne peut se
connecter, le mot de passe doit être réinitialisé dans la base de
données (table `cc_subjs`, colonne `pass`, MD5 du nouveau mot de passe) -
voir [`docs/operator/CRASH_RECOVERY.md`](../../operator/CRASH_RECOVERY.md).

---

## Pour aller plus loin

* [Paramètres](./SETTINGS.md) - chaque page de paramètres.
* [Tableau de bord](./DASHBOARD.md) - sources en direct et émission en cours.
* [Import / Export](./IMPORT_EXPORT.md) - les utilisateurs en `users.csv`.
* [Flux](./STREAMS.md) - ports de connexion en direct et identifiant Master.
