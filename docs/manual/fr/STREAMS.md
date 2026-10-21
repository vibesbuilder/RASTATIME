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
| **URL auditeur** (lecture seule) | Depuis le 2026-10-04, une sortie sur l'Icecast local est publiée sous `<URL publique>/stream/<mount>` (p. ex. `https://rastatime.example.org/stream/rastatime`) : le serveur web transmet `/stream/` à Icecast, le lecteur, les widgets et les codes d'intégration utilisent donc la même adresse en LAN et sur Internet, et le port 8000 reste interne. Une sortie vers un Icecast distant garde son `http://hôte:port/mount`. |
| **Mount** | Le chemin URL du mountpoint, avec `/` au début. ex. `/rastatime`. |
| **Utilisateur source / Mot de passe** | Credentials qu'Icecast attend d'un client source. Définis dans `config/icecast.xml`. |
| **Format** | **MP3**, **AAC**, **OGG Vorbis**, **OPUS**, **FLAC**. |
| **Bitrate** | Kbps. La décision la plus conséquente par stream ; voir §2. |
| **Canaux** | **Stéréo** (par défaut), **Mono** (économise ~30 % de bande passante pour parole). |
| **Fréquence d'échantillonnage** | 22,05 / 32 / 44,1 / 48 kHz. 44,1 kHz est le standard universel. |
| **Nom de stream / URL / Genre / Description** | Métadonnées ICY annoncées aux auditeurs. Depuis le 2026-09-13 les quatre champs sont rendus ; un Nom ou une Description vide retombe sur le nom de la station (Icecast affichait « Unspecified name »). |

### Stream Label et Off Air Metadata

Ce que les auditeurs voient comme titre « en cours » dans leur lecteur.
Les deux champs se trouvent sur la page Streams au-dessus des blocs par
stream ; le nom de la station vient de Paramètres → General.

| Source à l'antenne | Artist - Title | Show - Artist - Title | Station name - Show name |
|---|---|---|---|
| Piste planifiée | Artiste - Titre | Émission - Artiste - Titre | RASTATIME - Émission |
| Webstream avec ses propres titres | titre du flux source | Émission - titre du flux source | RASTATIME - Émission |
| Webstream sans titres, Line-In | RASTATIME - Émission | RASTATIME - Émission | RASTATIME - Émission |
| DJ (BUTT / Mixxx) | titre envoyé par le logiciel DJ, sinon RASTATIME - Émission | Émission - titre envoyé par le logiciel DJ, sinon RASTATIME - Émission | RASTATIME - Émission |
| Rien de planifié | texte Off Air Metadata | texte Off Air Metadata | texte Off Air Metadata |

- **Off Air Metadata** remplace le titre de la dernière piste dès que rien
  n'est à l'antenne (avant le 2026-09-13 l'ancien titre restait des heures).
- Une modification de l'un des deux champs prend effet dans le prochain
  rafraîchissement de grille (environ deux minutes), sans redémarrage.
- Le label est écrit dans les métadonnées de titre du flux : il s'applique
  au MP3/AAC (ICY), à l'OGG (in-band) et aux enregistrements.

### Normalisation de la sonie (ReplayGain / EBU R128)

Égalise le niveau des titres programmés pour qu'un enregistrement folk
discret et un mix club puissant parviennent aux auditeurs à la même
sonie.  Trois modes, choisis sur la page Streams ; chaque description
est disponible sous forme d'icône d'aide à côté de son champ.

Depuis le 2026-10-08, les réglages de sonie et le traitement de sortie
(Stereo Tool) ci-dessous partagent le segment **Traitement audio**, sous
Stream Label et Off Air Metadata.  Comme les segments de Settings →
General, il est replié au départ : cliquez sur sa barre pour l'ouvrir.
Après un enregistrement avec une valeur invalide, il s'ouvre de
lui-même.  Le curseur *Replay Gain Modifier* (mode ReplayGain
uniquement) se trouve directement sous le mode.

| Mode | Ce qu'il fait |
|---|---|
| **Désactivé** | Chaque titre est diffusé à son propre niveau. |
| **ReplayGain** | La valeur ReplayGain mesurée à l'import plus le curseur *Replay Gain Modifier* (le comportement des versions précédentes). |
| **EBU R128** | Chaque titre est mesuré selon la norme de sonie broadcast (ITU BS.1770 / EBU R128) et diffusé à la **Sonie cible** ; un limiteur de crête sur le bus de sortie respecte le **Plafond de crête vraie**. |

Réglages pour EBU R128 :

- **Sonie cible (LUFS)** — la sonie intégrée à laquelle chaque titre est
  diffusé.  EBU R128 prescrit −23 LUFS pour le broadcast ; les flux web
  utilisent souvent des cibles plus fortes entre −18 et −16 LUFS.  La
  valeur est libre ; −23 est la valeur par défaut.
- **Plafond de crête vraie (dBTP)** — le niveau qu'aucune crête ne doit
  dépasser (par défaut −1 dBTP).  Un titre faible n'est amplifié que
  dans la limite de sa crête vraie mesurée ; le limiteur sur le bus se
  charge du reste.
- **Mesure de la sonie** — les fichiers importés à partir de maintenant
  sont mesurés automatiquement.  *Mesurer les fichiers manquants
  maintenant* met en file d'attente chaque fichier sans mesure pour
  l'analyseur ; *Tout remesurer* toute la bibliothèque.  La mesure
  s'exécute en arrière-plan, quelques secondes par fichier ; la ligne
  « Mesurés : N fichiers sur M » indique l'état après rechargement de la
  page.  Tant qu'un titre n'est pas mesuré, il est diffusé avec sa valeur
  ReplayGain décalée vers la cible.

Remarques :

- Un changement de mode, de cible ou de plafond prend effet au prochain
  rafraîchissement de la grille (environ deux minutes) pour les gains
  des titres ; le limiteur du bus est appliqué par le redémarrage
  planifié du playout à la prochaine frontière de titre.
- Les sources en direct (DJ, flux web, entrée ligne) ne sont pas
  concernées par cette étape ; leur niveau est celui que livre la source.
- Les valeurs mesurées sont stockées par fichier (sonie intégrée, crête
  vraie, plage de sonie) et survivent aux changements de réglages.

### Traitement de sortie (Stereo Tool)

Facultatif, désactivé par défaut.  Lorsqu'il est activé, le playout fait
passer toute la sortie - chaque flux Icecast, l'enregistrement 24/7 et le
Main Output - par [Stereo Tool](https://www.thimeo.com/stereo-tool/) via
l'opérateur `stereotool()` de Liquidsoap : un processeur broadcast avec
contrôleur de sonie BS.1770, traitement multibande et limiteur final.
C'est cette étape qui rend le flux mesuré par un partenaire de diffusion
conforme R128 quelle que soit la source ; la normalisation de la sonie
ci-dessus n'égalise que les fichiers.  La description de chaque champ est
disponible sous forme d'icône d'aide : à côté de l'interrupteur, et à
droite du libellé pour les trois champs en dessous.

| Champ | Signification |
|---|---|
| **Traitement de sortie (Stereo Tool)** | L'interrupteur.  Désactivé par défaut ; une station sans Stereo Tool le laisse simplement désactivé. |
| **Bibliothèque Stereo Tool (DLL)** | Chemin complet de la bibliothèque Stereo Tool 64 bits pour Liquidsoap sur la machine du studio (page de téléchargement Stereo Tool).  La page indique si le fichier existe ; le réglage n'est utilisé que dans ce cas. |
| **Préréglage Stereo Tool (.sts)** | Facultatif.  Un préréglage exporté depuis l'application Stereo Tool ; sans préréglage, la bibliothèque démarre avec ses valeurs par défaut, qui ne traitent rien du tout.  RASTATIME fournit `config/stereotool/rastatime-r128-transparent.sts` *(depuis le 2026-10-21)* : aucun traitement, seulement un limiteur true-peak à −1 dBTP sans changement de niveau - le volet « crêtes » de l'EBU R128, le volet « sonie » venant des sources déjà calibrées.  Mesures dans le README à côté. |
| **Clé de licence Stereo Tool** | La clé de votre compte Stereo Tool.  Stockée sur le serveur, jamais réaffichée ; laisser vide pour conserver la clé enregistrée, saisir `CLEAR` pour la supprimer.  Sans licence, la bibliothèque fonctionne avec les restrictions de la version gratuite. |

Remarques :

- Un changement est appliqué par le redémarrage planifié de Liquidsoap
  (moment calme ou prochaine limite de titre), comme tout réglage intégré
  au script Liquidsoap.
- Filet de sécurité : un fichier de bibliothèque manquant laisse la sortie
  intacte, et si la nouvelle instance Liquidsoap ne reste pas en route
  après un démarrage avec Stereo Tool (bibliothèque incompatible, licence
  refusée), le playout la redémarre **sans** Stereo Tool, le laisse
  désactivé jusqu'au prochain redémarrage de PLAYOUT et émet
  l'avertissement preflight `stereotool_unavailable`.  La diffusion ne
  dépend jamais du plugin.
- Stereo Tool ajoute une latence de traitement à tout ce qui suit ; la
  grille n'est pas concernée, chaque sortie se décale de la même valeur.

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
`RASTATIME_DJ_RECONCILE_SECONDS`, 600 secondes par défaut). Un DJ qui
ferme simplement la connexion est détecté dans le délai réseau du
moteur, 5 secondes (réglage machine `RASTATIME_HARBOR_TIMEOUT_SECONDS`) ;
un DJ dont la connexion se fige plus longtemps est déconnecté et doit se
reconnecter, ce que BUTT fait tout seul. Déconnecter un DJ depuis le
tableau de bord est immédiat.

> **Conseil opérateur.** Master DJ a préséance sur Show
> DJ.

**Switch Transition Fade (s)** (Settings → Streams, depuis le
2026-09-28, valeur de départ 1 s) façonne le passage de relais : quand un
DJ se connecte, il est aussitôt à l'antenne et le programme s'estompe en
dessous sur ce nombre de secondes ; quand le DJ se déconnecte, le DJ
s'estompe sur la même durée et le programme revient aussitôt à plein
niveau. 0 = bascule sèche. La chaîne audio applique la valeur quelques
secondes après l'enregistrement (redémarrage planifié à un moment calme
ou à une limite de titre). Avant le 2026-09-28 le champ n'avait aucun
effet ; les deux sens étaient une bascule de 50 ms.

Sur la page Streams, la section **Live Broadcasting** comporte trois
blocs : **Passage de relais DJ** (le fondu ci-dessus), **Master Source** et
**Show Source** (les données de connexion, voir *Se connecter comme
Source Live* ci-dessous).  Depuis le 2026-10-08, l'explication d'une
ligne de chaque bloc est une icône d'aide à droite de son titre.

### Se connecter comme Source Live

Les animateurs utilisent n'importe quel logiciel de
diffusion audio (BUTT, Mixxx, RadioDJ, SAM Broadcaster)
configuré avec :

| Champ | Valeur |
|---|---|
| Serveur | Hostname / IP public de la station |
| Port | Le **Master Source Port** / **Show Source Port** affiché sous Paramètres → Streams (8001 par défaut ; 8000 est le port auditeur) |
| Mount | Le **Master Source Mount** / **Show Source Mount** affiché sous Paramètres → Streams (`main` et `show` par défaut) |
| Nom d'utilisateur | Master DJ : le nom d'utilisateur sous Paramètres → Streams → **Master Source**. Show DJ : le login RASTATIME d'un animateur inscrit, ou le nom personnalisé de la section **Live Stream Input** de l'émission |
| Mot de passe | Le mot de passe correspondant |
| Format | MP3 (correspondance avec le format stream principal préférée) |

> **Comment ça marche sous le capot.** Le port d'entrée source
> est un harbor Liquidsoap dans le moteur de diffusion. Chaque
> login est vérifié au moment de la connexion (depuis le
> 2026-09-10) : le moteur interroge la diffusion, la diffusion
> interroge l'application web, qui applique les réglages
> ci-dessus. Pour le Show DJ, c'est l'émission à l'antenne en ce
> moment qui compte ; un Show DJ ne peut donc pas se connecter
> avant le début de l'émission. Ce n'est que lorsque la diffusion
> elle-même est injoignable que le moteur se rabat sur le mot de
> passe harbor statique de `libretime.conf`. Voir ARCHITECTURE
> §23.27 (addendum 2026-09-10).

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

Elles y sont déjà : le playout étiquette chaque paquet de métadonnées
selon **Stream Label** (voir §1), affiche le texte **Off Air Metadata**
tant que rien n'est à l'antenne, et fait passer les titres envoyés par
un webstream ou par le logiciel DJ à travers le même label.  Une source
live sans titres propres est étiquetée avec l'émission en cours.

---

## Où aller ensuite

* [Machine locale](./LOCAL_MACHINE.md) — la sortie carte
  son côté machine-opérateur.
* [Tableau de bord](./DASHBOARD.md) — santé rapide des
  streams visible sur chaque page.
* [Webstreams](./WEBSTREAMS.md) — le pendant *entrant*.
* [`docs/operator/CRASH_RECOVERY.md`](../../operator/CRASH_RECOVERY.md)
  — quand un stream devient rouge.
