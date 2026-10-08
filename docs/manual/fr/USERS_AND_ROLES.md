# Utilisateurs et rôles

> **Où vous êtes dans le manuel.** Ce chapitre est la
> référence des permissions pour chaque fonctionnalité du
> reste du manuel.

RASTATIME a cinq rôles utilisateur et un système de
permissions unique. Chaque action — ouvrir une page,
glisser une piste, enregistrer une émission, redémarrer
un service — est vérifiée côté serveur contre le rôle de
l'utilisateur.

Ce chapitre couvre :

1. Les cinq rôles + ce que chacun peut faire.
2. Gérer les utilisateurs.
3. La matrice complète des permissions.
4. Gestion des clés API.
5. Attribution de rôle best-practice.

---

## 1. Les cinq rôles

| Rôle | Symbole | Utilisateur typique | Résumé en une ligne |
|---|---|---|---|
| **Invité** | G | Affichage réception / lobby | Tableau de bord en lecture seule. |
| **DJ** | H | Chaque animateur individuel | Ses propres émissions + ses propres fichiers seulement. |
| **Program Manager** | P | Coordinateur de programme | Tout calendrier + bibliothèque, pas de paramètres station. |
| **Admin** | A | Admin technique station | Tout sauf créer d'autres Admins. |
| **Super Admin** | S | Propriétaire de la station | Tout y compris créer des Admins. |

Un utilisateur a exactement **un** rôle.

### Pourquoi basé sur les rôles et pas sur les capacités ?

Basé sur les rôles est le modèle le plus simple qui
couvre 99 % des besoins des stations. Basé sur les
capacités (toggles granulaires par fonctionnalité) est
flexible mais crée exponentiellement plus de
configurations à tester.

> **Comment ça marche sous le capot.** Les rôles vivent
> dans `cc_subjs.type` comme un seul caractère (G / H /
> P / A / S). Les vérifications de permission se font
> dans `application/configs/ACL.php` via Zend_Acl. Voir
> ARCHITECTURE §11.

---

## 2. Capacités par rôle

### Invité (G)

Le plus petit rôle. Utilisé pour affichages en lecture
seule dans zones publiques.

Peut : se connecter, voir le Tableau de bord En cours +
Vient ensuite, voir le calendrier public (lecture seule).
Ne peut pas : accéder à Bibliothèque, Paramètres ou tout
menu administratif.

### DJ (H)

Compte par-animateur. Le rôle que la plupart des
utilisateurs ont.

Peut : tout ce qu'Invité peut, plus téléverser des
pistes (possédées par lui-même), créer des smart blocks
et playlists, planifier ses *propres* éléments dans ses
*propres* émissions, modifier des émissions où il est
animateur.

Ne peut pas : créer des émissions (les Program Managers
doivent créer ; le DJ remplit), voir / utiliser pistes /
blocks / playlists d'autres DJ, changer paramètres
au-niveau station, redémarrer services.

### Program Manager (P)

Le propriétaire du planning.

Peut : tout ce que DJ peut, plus créer / modifier /
supprimer *toute* émission, voir / utiliser pistes /
blocks / playlists de *tout* DJ, utiliser Modèles
d'émission, utiliser Auto DJ, gérer entrées
bibliothèque Webstreams, basculer Master DJ
on/off-antenne via le toggle Tableau de bord.

Ne peut pas : gérer Line-Ins (dépend carte son — Admin
seulement), gérer Streams, gérer Utilisateurs, redémarrer
services.

### Admin (A)

Accès complet niveau station sauf créer d'autres Admins.

Peut : tout ce que Program Manager peut, plus gérer
Line-Ins, Streams, Utilisateurs (créer / modifier /
désactiver DJ et Program Managers), configurer
Paramètres → Préférences générales, configurer
Paramètres → Machine locale, configurer valeurs par
défaut Auto DJ, réinitialiser mots de passe, lire page
Statut système, redémarrer services via widget restart.

Ne peut pas : promouvoir utilisateur à Admin (Super
Admin seulement), rétrograder un autre Admin.

### Super Admin (S)

Rôle maximum. Réservé au propriétaire de la station /
admin technique.

Peut : tout ce qu'Admin peut, plus créer nouveaux Admins,
rétrograder Admins à des rôles inférieurs, voir clé API
de tout utilisateur, modifier la base de données / le
stockage de clé API directement via Paramètres → Tools →
Console DB.

Par conception, il y a **exactement un** Super Admin
par station.

---

## 3. Gérer les utilisateurs

Paramètres → **Gérer les utilisateurs** (Admin / Super
Admin seulement).

### Créer un nouvel utilisateur

Gérer les utilisateurs → **+ Nouveau**.

| Champ | Notes |
|---|---|
| **Nom d'utilisateur** | Minuscules, pas d'espaces, 3-32 caractères. Ne peut pas être changé une fois défini. |
| **Prénom / Nom** | Nom d'affichage. |
| **Email** | Utilisé pour réinitialisation mot de passe. |
| **Mot de passe** | Min 8 caractères. |
| **Rôle** | L'un des cinq rôles. Par défaut DJ. |
| **Mobile** | Optionnel. |
| **Skype** | Optionnel. Champ legacy. |
| **Actif** | Par défaut activé. |

### Modifier un utilisateur

Ligne → **Modifier**. Tous champs sauf nom d'utilisateur
sont modifiables.

Pour changer le rôle d'un utilisateur :
- Abaisser un rôle (Admin → PM, PM → DJ) est permis pour
  Admin et au-dessus.
- Promotion à Admin est **Super Admin seulement**.
- Rétrograder un Super Admin : seul le Super Admin
  lui-même peut le faire.

### Réinitialiser un mot de passe

Ligne → **Réinitialiser mot de passe**.

| Option | Effet |
|---|---|
| **Envoyer email** | Si SMTP configuré, envoyer un lien à usage unique valide 24 heures. |
| **Définir mot de passe** | Définir un mot de passe temporaire. |

### Désactiver un utilisateur

Ligne → **Désactiver**. L'utilisateur ne peut plus se
connecter mais son activité historique est préservée.

Pour supprimer un utilisateur définitivement,
**Supprimer**. Son contenu est réassigné au
**propriétaire fallback par défaut** configuré.

> **Conseil opérateur.** Préférez **Désactiver** plutôt
> que **Supprimer**.

---

## 4. Clés API

Chaque utilisateur peut générer une clé API pour accès
scripté à l'API REST.

### Générer sa propre clé API

Menu utilisateur (en haut à droite) → **Mon profil** →
section **Clé API**.

Les clés API portent les mêmes permissions que
l'utilisateur.

### Générer la clé API d'un autre utilisateur

Gérer les utilisateurs → ligne d'utilisateur → **Clé
API** → Générer. Admin / Super Admin seulement.

> **Comment ça marche sous le capot.** Les clés API sont
> des strings aléatoires de 32 octets stockés dans
> `cc_subjs.api_key` (hachés). Authentification via
> l'en-tête `Authorization: Api-Key <key>`. Voir
> ARCHITECTURE §11.

> **Conseil opérateur.** Traitez les clés API comme des
> mots de passe. Évitez de coder en dur les clés dans
> les fichiers source committés.

---

## 5. La matrice des permissions

| Action | G | H | P | A | S |
|---|:---:|:---:|:---:|:---:|:---:|
| **Tableau de bord** | | | | | |
| Voir En cours | ✓ | ✓ | ✓ | ✓ | ✓ |
| Voir compteurs auditeurs | | ✓ | ✓ | ✓ | ✓ |
| Basculer Master DJ on / off antenne | | | ✓ | ✓ | ✓ |
| Annuler émission actuelle | | ✓¹ | ✓ | ✓ | ✓ |
| Écouter le moniteur | | ✓ | ✓ | ✓ | ✓ |
| **Calendrier** | | | | | |
| Voir calendrier | ✓ | ✓ | ✓ | ✓ | ✓ |
| Créer émission | | | ✓ | ✓ | ✓ |
| Modifier sa propre émission | | ✓ | ✓ | ✓ | ✓ |
| Modifier toute émission | | | ✓ | ✓ | ✓ |
| Supprimer sa propre émission | | ✓ | ✓ | ✓ | ✓ |
| Supprimer toute émission | | | ✓ | ✓ | ✓ |
| Appliquer / enregistrer Modèle | | | ✓ | ✓ | ✓ |
| **Bibliothèque** | | | | | |
| Voir ses propres fichiers | | ✓ | ✓ | ✓ | ✓ |
| Voir tous les fichiers | | | ✓ | ✓ | ✓ |
| Téléverser piste | | ✓ | ✓ | ✓ | ✓ |
| Créer / modifier ses propres playlists, blocks | | ✓ | ✓ | ✓ | ✓ |
| Créer / modifier toute playlist, block | | | ✓ | ✓ | ✓ |
| Créer / modifier webstream | | ✓² | ✓ | ✓ | ✓ |
| Créer / modifier Line-In | | | | ✓ | ✓ |
| Supprimer ses propres fichiers | | ✓ | ✓ | ✓ | ✓ |
| Supprimer tout fichier | | | ✓ | ✓ | ✓ |
| **Streams** | | | | | |
| Voir statut stream | | ✓ | ✓ | ✓ | ✓ |
| Modifier config stream | | | | ✓ | ✓ |
| **Machine locale** | | | | | |
| Voir config carte son | | | | ✓ | ✓ |
| Modifier config carte son | | | | ✓ | ✓ |
| Définir Dossier d'import local | | | | ✓ | ✓ |
| **Auto DJ** | | | | | |
| Activer / désactiver | | | ✓ | ✓ | ✓ |
| Modifier valeurs par défaut | | | | ✓ | ✓ |
| **Paramètres** | | | | | |
| Préférences générales | | | | ✓ | ✓ |
| Localisation | | | | ✓ | ✓ |
| Page Modèles d'émission | | | ✓ | ✓ | ✓ |
| Gestion utilisateurs | | | | ✓ | ✓ |
| Créer Admin | | | | | ✓ |
| **Système** | | | | | |
| Voir Statut système | | | | ✓ | ✓ |
| Redémarrer service | | | | ✓ | ✓ |
| Accéder Console DB | | | | | ✓ |
| **API** | | | | | |
| Générer sa propre clé API | | ✓ | ✓ | ✓ | ✓ |
| Voir / générer clé API de tout utilisateur | | | | ✓ | ✓³ |

Notes :
- ¹ — Seulement son émission actuellement à l'antenne.
- ² — Par DJ ; ne peut pas modifier webstreams d'autres
  DJ.
- ³ — Y compris ceux d'autres Admins.

---

## 6. Attribution de rôle recommandée

### Station opérateur solo (1 personne)

- `admin` — Super Admin.
- (Optionnel) `reception` — Invité.

### Petite station communautaire (3-10 contributeurs)

- `admin` — Super Admin.
- `pm1` — Program Manager.
- `anna`, `ben`, `carla`, … — DJ (un par animateur).
- (Optionnel) `ingenieur` — Admin.
- (Optionnel) `reception` — Invité.

### Station moyenne / commerciale (10-50 contributeurs)

- `owner` — Super Admin.
- `engineer1` — Admin.
- `pm1`, `pm2` — Program Manager.
- Comptes DJ par animateur.
- `script` — DJ (compte service pour scripts).
- `reception` — Invité.

Pour toutes les tailles : **un Super Admin par station**
est le sweet spot.

---

## 7. Foire aux questions

### "Je suis verrouillé comme Super Admin. Comment récupérer ?"

Accès direct à la base de données est la seule
récupération. Voir
[`docs/operator/CRASH_RECOVERY.md`](../../operator/CRASH_RECOVERY.md)
§5.

### "Un utilisateur peut-il avoir deux rôles ?"

Non. Un rôle par utilisateur.

### "Deux utilisateurs peuvent-ils partager un compte ?"

Techniquement oui, mais fortement déconseillé.

### "Combien de temps dure une session ?"

Par défaut 8 heures. Configurable via la durée de vie du
cookie de session PHP dans `php.ini`.

### "Puis-je me connecter depuis deux navigateurs simultanément ?"

Oui. Les sessions sont par cookie.

### "L'API supporte-t-elle OAuth / SSO ?"

Pas actuellement.

### "Un DJ peut-il voir les enregistrements d'un autre DJ ?"

Non. Les enregistrements héritent du propriétaire de
l'émission.

---

## 8. Protection de la connexion (depuis le 2026-10-06)

La page de connexion freine les échecs répétés – indispensable depuis
que l'interface web est accessible depuis Internet.

| Portée | Règle | Effet |
|---|---|---|
| Par adresse source | 10 connexions échouées en 15 minutes | l'adresse attend 15 minutes ; chaque tentative pendant ce temps reçoit « Trop de tentatives de connexion échouées. Veuillez réessayer dans N minute(s). » (HTTP 429), aucun mot de passe n'est vérifié |
| Par nom d'utilisateur | 20 connexions échouées en 60 minutes | le nom attend 5 minutes – volontairement court, pour que personne ne puisse bloquer durablement un administrateur en martelant son nom depuis de nombreuses adresses |
| Connexion DJ (harbor) | 5 connexions refusées d'une adresse en 10 minutes | l'adresse est refusée pendant 15 minutes sans interroger l'application web |

Une connexion réussie remet à zéro les compteurs de son adresse et de son
nom.  Les seuils sont dans `constants.php` (`RASTATIME_LOGIN_*`) et dans
le playout (`RejectThrottle`) ; les tentatives refusées sont journalisées
avec l'adresse (`logs/legacy.log`, `logs/playout-stdout.log`).

**Voir et lever les blocages.**  Paramètres → État du système →
*Adresses bloquées* liste chaque niveau (connexion web par adresse et par
utilisateur, connexion DJ, veilleur de pare-feu) avec le nombre d'échecs
et les minutes restantes ; **Débloquer** efface l'entrée à tous les
niveaux – pour le DJ qui appelle parce qu'un mauvais mot de passe était
enregistré dans son client.  La même liste existe en PowerShell :
`infra\scripts\rt-blocks.ps1` (`-Unblock <adresse>` ou
`-Unblock user:<login>`).  Un DJ qui se connecte **avant** le début de
l'émission est refusé mais jamais compté : seul un mauvais mot de passe
compte.  Les scanners Internet persistants sont bloqués 24 heures dans le
pare-feu Windows par une tâche de veille (toutes les 5 minutes ; 50
requêtes refusées en 60 minutes, 3 chemins typiques de scanner ou 5
mauvais mots de passe DJ) et apparaissent dans la même liste.  Une
réponse « non connecté » (401) ne compte jamais : c'est ce qu'un onglet
de navigateur à la session expirée reçoit pour ses requêtes d'arrière-
plan, et depuis le 2026-10-07 un tel onglet cesse d'interroger dès la
première.

**Adresses autorisées (depuis le 2026-10-08).**  À côté de **Débloquer**,
chaque adresse bloquée a **Autoriser** : elle est débloquée sur toutes les
couches et placée dans la liste *Adresses autorisées* en dessous, où vous
pouvez aussi ajouter à la main une adresse ou un réseau en notation CIDR
(`203.0.113.0/24`) et retirer des entrées.  Une adresse autorisée n'est
jamais freinée par la connexion web, jamais limitée par la connexion DJ et
jamais bloquée par le veilleur de pare-feu ; les adresses du réseau du
studio sont exemptées de toute façon.  Gardez la liste courte - elle
désactive tous les freins pour cette adresse - et préférez un réseau pour
une connexion domestique dont l'adresse change avec le fournisseur.  La
liste est conservée en base et recopiée dans `config\allowlist.txt` pour
le playout et le veilleur.

> **Si vous êtes vous-même bloqué :** attendez les minutes indiquées ou
> demandez à un collègue sur une autre adresse.  En cas d'urgence, les
> compteurs se trouvent dans les tables `cc_login_attempts` (par adresse)
> et `cc_subjs.login_attempts` (par utilisateur).

## Où aller ensuite

* [Paramètres](./SETTINGS.md) — tour de chaque
  sous-page Paramètres.
* [Tableau de bord](./DASHBOARD.md) — la page la plus
  utilisée de l'opérateur.
* [`docs/operator/CRASH_RECOVERY.md`](../../operator/CRASH_RECOVERY.md)
  — récupération de verrouillage Super Admin.
