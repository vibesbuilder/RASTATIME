# Streams

> **Où vous êtes dans le manuel.** Ce chapitre couvre les
> **streams sortants** — ce que RASTATIME publie aux
> auditeurs. Pour les *entrants* (streams d'autres personnes
> que RASTATIME relaie dans une émission), voir
> [Webstreams](./WEBSTREAMS.md). Pour la sortie carte son
> côté machine-opérateur, voir
> [Machine locale](./LOCAL_MACHINE.md).

Un **stream** est un mountpoint Icecast (ou Shoutcast) que
RASTATIME diffuse aux auditeurs. Une station peut
configurer jusqu'à **quatre streams de sortie**,
typiquement utilisés pour :

- **Qualité principale** (192-320 kbps) pour auditeurs
  bureau / fixes.
- **Qualité mobile** (96-128 kbps) pour auditeurs
  cellulaires avec données limitées.
- **Sans perte / archive** (FLAC) pour écoute haut de
  gamme.
- **Réserve / standby** pour failover ou tests.

Chaque stream a son propre bitrate, codec, mountpoint, et
peut même pointer vers un serveur Icecast différent.

---

## 1. La page paramètres Streams

Paramètres → **Streams**.

Chacune des quatre cartes de stream a le même ensemble de
champs ; seul **Stream 1** est activé par défaut.

### Champs par stream

| Champ | Notes |
|---|---|
| **Activé** | Interrupteur principal pour ce stream. |
| **Type** | **Icecast** (recommandé), **Shoutcast** (legacy), **Custom**. |
| **Serveur / Port** | Où est le serveur Icecast. `localhost:8000` pour l'installation par défaut. |
| **Mount** | Le chemin URL du mountpoint, avec `/` au début. ex. `/rastatime`. |
| **Utilisateur source / Mot de passe** | Credentials qu'Icecast attend d'un client source. Définis dans `config/icecast.xml`. |
| **Format** | **MP3**, **AAC**, **OGG Vorbis**, **OPUS**, **FLAC**. |
| **Bitrate** | Kbps. La décision la plus conséquente par stream ; voir §2. |
| **Canaux** | **Stéréo** (par défaut), **Mono** (économise ~30 % de bande passante pour parole). |
| **Fréquence d'échantillonnage** | 22,05 / 32 / 44,1 / 48 kHz. 44,1 kHz est le standard universel. |
| **Nom de stream / URL / Genre / Description** | Métadonnées ICY annoncées aux auditeurs. |

### Badge d'état du stream

| Badge | Signification |
|---|---|
| ● **Connecté** (vert) | Playout connecté ; diffusion. |
| ◐ **Connexion** (jaune) | Au milieu d'une tentative de connexion. |
| ● **Déconnecté** (rouge) | Playout ne peut pas se connecter. |
| ◯ **Désactivé** (gris) | Stream configuré mais interrupteur désactivé. |

Le badge se rafraîchit toutes les 5 secondes via l'endpoint
`/api/v2/streams`.

> **Conseil opérateur.** Un badge rouge sur Stream 1
> signifie que les auditeurs n'entendent rien. Vérifiez
> Icecast (`Get-Service icecast2`), credentials, port
> 8000. Voir
> [`docs/operator/CRASH_RECOVERY.md`](../../operator/CRASH_RECOVERY.md).

---

## 2. Choisir un bitrate

Le réglage le plus consulté. Guide :

| Cas d'usage | Format | Bitrate | Canaux | Fréq. |
|---|---|---|---|---|
| Musique, qualité principale | MP3 | 192 kbps | Stéréo | 44,1 kHz |
| Musique, premium / fans FLAC | MP3 | 320 kbps | Stéréo | 44,1 kHz |
| Musique, archive FLAC | FLAC | ~700-1000 kbps | Stéréo | 44,1 kHz |
| Talk-show / parlé | MP3 | 96 kbps | Mono | 44,1 kHz |
| Mobile / cellulaire | AAC | 64 kbps | Stéréo | 44,1 kHz |
| Réserve / debug | MP3 | 128 kbps | Stéréo | 44,1 kHz |

### Pourquoi ceux-ci et pas d'autres

- **AAC est meilleur que MP3 à bas bitrates** (< 128 kbps).
- **MP3 au-dessus de 192 kbps stéréo** est le sweet spot
  pour ubiquité + qualité.
- **OPUS est le meilleur codec moderne** mais certains
  hardware legacy ne le supportent pas.

### Math de bande passante

Chaque stream activé utilise bande passante =
`bitrate × auditeurs_concurrents_max`. Un stream 192 kbps
avec 50 auditeurs concurrents utilise ~9,6 Mbps sortants.

Pour plus de ~50-100 auditeurs, exécutez Icecast sur un
serveur cloud avec un gros uplink.

---

## 3. Sources Live

En plus du contenu planifié, RASTATIME accepte deux
connexions de **source live** par émission :

| Source | But |
|---|---|
| **Show DJ** | Login par-émission. L'animateur principal se connecte de partout. Nom d'utilisateur + mot de passe sur le formulaire d'émission (section **Entrée Live Stream**). |
| **Master DJ** | Login au niveau station. Un producteur / ingénieur peut prendre le relais à tout moment. Nom d'utilisateur + mot de passe sous Paramètres → Stream Settings → **Master Source**. |

Quand l'une ou l'autre source live se connecte, le source
switcher route son audio vers le mixeur de sortie à la
place du contenu du scheduler.

Depuis le 2026-09-09, le moteur signale lui-même chaque connexion et
déconnexion à la diffusion au moment où elle se produit ; la
commutation est donc immédiate, et la diffusion ne fait que
revérifier par sa liaison de commande (réglage machine
`RASTATIME_DJ_RECONCILE_SECONDS`, 120 secondes par défaut). Un DJ qui
ferme simplement la connexion est détecté à l'expiration du délai
réseau du moteur, 30 secondes ; déconnecter un DJ depuis le tableau
de bord est immédiat.

> **Conseil opérateur.** Master DJ a préséance sur Show
> DJ.

### Se connecter comme Source Live

Les animateurs utilisent n'importe quel logiciel de
diffusion audio (BUTT, Mixxx, RadioDJ, SAM Broadcaster)
configuré avec :

| Champ | Valeur |
|---|---|
| Serveur | Hostname / IP public de la station |
| Port | 8001 (port d'entrée source, *pas* le port auditeur 8000) |
| Mount | `/show` pour Show DJ, `/master` pour Master DJ |
| Nom d'utilisateur | Credentials configurés |
| Mot de passe | Credentials configurés |
| Format | MP3 (correspondance avec le format stream principal préférée) |

> **Comment ça marche sous le capot.** Le port d'entrée
> source (8001) est un mount Icecast `<authentication>`
> séparé qui rappelle dans PHP via
> `icecast-source-auth.php` pour valider nom
> d'utilisateur + mot de passe. Voir ARCHITECTURE §10.5.

---

## 4. Surveiller la santé des streams

### Depuis l'interface

Paramètres → Streams montre le badge par stream. La page
**Statut système** résume état de connexion par stream,
compteur d'auditeurs actuel, pic d'auditeurs aujourd'hui,
octets envoyés aujourd'hui.

### Depuis l'interface admin Icecast

`http://<serveur>:8001/admin/`.

### Depuis l'API

`GET /api/v2/streams` renvoie l'état complet de chaque
stream comme JSON. Utile pour surveillance externe.

---

## 5. Auth de stream (côté auditeur)

Par défaut, tous les streams sont **publics**. Pour
restreindre l'écoute :

1. Configurer auth auditeur dans `config/icecast.xml`.
2. Redémarrer Icecast.
3. Le script `icecast-auth.php` authentifie contre
   `cc_subjs`.

> **Pourquoi c'est rarement utilisé.** La plupart des
> stations veulent un stream public.

---

## 6. Plusieurs serveurs Icecast

Chacun des quatre streams peut cibler un **serveur
Icecast différent**. C'est le setup standard pour :

- **Local + cloud** : Stream 1 vers Icecast local, Stream
  2 vers Icecast cloud.
- **Distribution géographique** : Stream 1 vers Icecast
  EU, Stream 2 vers Icecast US.

> **Comment ça marche sous le capot.** Chaque stream
> mappe à une source `libvlc_VLM` avec sa propre chaîne
> de sortie `#transcode{}:standard{access=shout,...}`.
> Voir ARCHITECTURE §10.

---

## 7. Foire aux questions

### "Combien d'auditeurs concurrents RASTATIME peut-il gérer ?"

RASTATIME lui-même n'encode qu'une fois par stream. La
capacité d'auditeurs dépend d'Icecast (gère des milliers
sur du matériel modeste) et de l'uplink réseau.

### "Puis-je avoir une sortie HLS / DASH ?"

Pas directement — utilisez un repackager externe
(`ffmpeg -i icecast-url -hls_time 6 ...`).

### "Pourquoi le compteur d'auditeurs de mon stream est-il toujours 0 ?"

Trois possibilités : personne n'écoute (vérifiez via
l'admin Icecast), le badge est faux (rafraîchir la page),
ou les auditeurs se connectent à un mountpoint différent.

### "J'ai changé le bitrate mais les auditeurs disent que ça sonne pareil."

La plupart des logiciels player cachent la connexion.
Les auditeurs doivent se reconnecter.

### "Puis-je changer le bitrate du stream pendant qu'il joue ?"

Oui. Enregistrez le nouveau bitrate ; le moteur de
playout reconnecte le stream. Les auditeurs voient ~5 s
de silence pendant la reconnexion.

### "Comment ajouter des métadonnées ICY ?"

Les métadonnées ICY sont définies automatiquement par le
playout pour les pistes planifiées. Le contenu source
live n'a pas de métadonnées ICY — définissez-les via
votre logiciel de diffusion.

---

## Où aller ensuite

* [Machine locale](./LOCAL_MACHINE.md) — la sortie carte
  son côté machine-opérateur.
* [Tableau de bord](./DASHBOARD.md) — santé rapide des
  streams visible sur chaque page.
* [Webstreams](./WEBSTREAMS.md) — le pendant *entrant*.
* [`docs/operator/CRASH_RECOVERY.md`](../../operator/CRASH_RECOVERY.md)
  — quand un stream devient rouge.
