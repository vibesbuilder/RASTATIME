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
| **Fuseau horaire** | Fuseau horaire opérateur pour tous affichages calendrier / planning. Stocké par-émission dans `cc_show_days.timezone`. |
| **La semaine commence le** | Lundi / Dimanche. |

### Valeurs par défaut

| Champ | Notes |
|---|---|
| **Langue par défaut** | Langue UI pour nouveaux utilisateurs + l'écran de connexion. |
| **Crossfade par défaut** | Crossfade entre pistes consécutives. 1 seconde est typique. |
| **Type de piste par défaut** | Type de piste assigné aux nouveaux téléversements. |
| **Propriétaire d'import par défaut** | Compte crédité comme propriétaire pour fichiers importés via le Dossier d'import local. |
| **Enregistrement par défaut** | Si coché, nouvelles émissions ont **Enregistrer cette émission :** pré-cochée. |

### Tableau de bord

| Champ | Notes |
|---|---|
| **Vue d'avance** | Combien d'émissions à venir le panneau "Vient ensuite" affiche. 3-5 est typique. |
| **Intervalle de rafraîchissement** | À quelle fréquence le Tableau de bord interroge. 5 s par défaut. |

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

## 6. Moteur de playout (Liquidsoap / mpv / VLC)

> **Paramètre niveau service**, pas un paramètre UI.
> Configuré via la variable d'environnement
> `RASTATIME_PLAYOUT_ENGINE` sur le service NSSM
> RASTATIME-PLAYOUT. Opérateur uniquement ; non exposé
> dans l'UI web.

RASTATIME embarque trois moteurs de lecture. Un seul est
actif à la fois.

| Moteur | Statut | Forces | Limitations |
|---|---|---|---|
| **Liquidsoap** | **Production** (depuis 2026-05-28, Phase-C5) | Transitions gapless, crossfades natifs, PUTs Icecast persistants (auditeurs restent connectés à travers les changements de pistes), commutation de sources DJ via `input.harbor`, enregistrement par émission depuis le bus interne à 320 kbps MP3 fixe | Webstreams et entrées ligne programmés pas encore portés (toujours via mpv en parallèle ; Phase-E + Phase-F) |
| **mpv** | **Déprécié** (défaut historique) | Éprouvé, fichiers/webstreams/entrées-ligne | Pas d'enregistrement (FfmpegRecorder supprimé en C5 Teil 2d), pas de gapless, reconnexion auditeurs à chaque piste |
| **VLC** | **Déprécié** (échappatoire) | Fallback si mpv a un problème de DLL | Comme mpv plus VLC 3.x problématique sur Icecast URL-auth Windows |

**Pourquoi Liquidsoap est maintenant en production**
(décision opérateur 2026-05-28) : enregistrement
bit-identique aux auditeurs, pas de reconnexion entre
pistes, routage natif des sources DJ.

**Quand vous pourriez encore avoir besoin du fallback
mpv** : émission programmée 100 % webstream ou 100 %
entrée ligne avec record=true (l'enregistrement sera
silencieux sur Liquidsoap jusqu'à Phase-E / Phase-F).

**Comment changer de moteur** : voir
[`docs/operator/LIQUIDSOAP_CUTOVER.md`](../../operator/LIQUIDSOAP_CUTOVER.md).
Version courte : définir `RASTATIME_PLAYOUT_ENGINE=liquidsoap`
dans l'environnement du service NSSM, redémarrer
`RASTATIME-PLAYOUT`, puis `RASTATIME-LIQUIDSOAP`.

Le journal playout au démarrage montre :

```
INFO __main__: Local-playback engine: Liquidsoap ...
```

vs. (sur le chemin déprécié) :

```
WARNING __main__: DEPRECATED: RASTATIME_PLAYOUT_ENGINE=mpv is now legacy. ...
INFO __main__: Local-playback engine: mpv (libmpv) [DEPRECATED]
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
