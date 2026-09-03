# Line-In

> **Où vous êtes dans le manuel.** Ce chapitre couvre le
> type d'item de bibliothèque **Line-In** — entrées audio
> live nommées que vous pouvez glisser sur des playlists et
> émissions. Pour la configuration carte son côté
> machine-opérateur qui rend un line-in physiquement
> disponible, voir [Machine locale](./LOCAL_MACHINE.md).
> Pour la procédure d'urgence quand un line-in tombe en
> silence ou bruit, voir
> [`docs/operator/LINE_IN_BROKEN.md`](../../operator/LINE_IN_BROKEN.md).

Un **Line-In** est une entrée audio live nommée depuis un
périphérique carte son sur la machine de l'opérateur — un
microphone, une sortie mixeur, un lecteur CD, une interface
audio externe — que RASTATIME expose comme item de
bibliothèque. Une fois configuré, vous pouvez le glisser
dans des playlists et sur des émissions exactement de la
même façon que vous glissez une piste.

Les Line-Ins sont nouveaux dans RASTATIME (2026-05-12). Ils
remplacent le slot "Line In" unique en dur que LibreTime
d'origine avait, et ajoutent un comportement nommé,
persistant, glisser-déposable, listé en bibliothèque.

---

## 1. Vue d'ensemble du concept

Un Line-In a deux couches :

| Couche | Ce que c'est | Où ça vit |
|---|---|---|
| **Périphérique physique** | L'entrée carte son réelle — un microphone USB, un jack line intégré, une interface XLR, etc. Identifié par son ID de périphérique côté OS. | La configuration carte son de la machine de l'opérateur ; voir [Machine locale](./LOCAL_MACHINE.md). |
| **Line-In nommé** | Une ligne de bibliothèque qui *référence* un périphérique physique par ID, plus un nom d'affichage et une configuration. | Table `rastatime_linein` ; visible dans la Bibliothèque + sur la page Line-In Library. |

Un seul périphérique physique peut soutenir **au plus un**
Line-In à la fois. Re-lier le même périphérique à un
second Line-In écrase le premier.

---

## 2. La page Line-In Library

Paramètres → **Line-In Library** (ou cliquez sur la puce
Line-In verte dans la page Bibliothèque principale).

Chaque ligne est un Line-In nommé. Les colonnes :

| Colonne | Signification |
|---|---|
| **Nom** | Le nom d'affichage. Utilisé partout où le Line-In apparaît. |
| **Périphérique** | Le périphérique carte son que le Line-In référence. Le libellé est le nom côté OS du périphérique. |
| **Longueur par défaut** | La durée par défaut qu'une ligne Line-In occupe quand glissée dans une playlist ou émission. `∞` signifie "joue jusqu'à être dit de s'arrêter". |

La barre d'outils :

| Bouton | Ce qu'il fait |
|---|---|
| **+ Nouveau** | Ouvrir le dialogue nouveau-Line-In. |
| **Modifier** (menu contextuel ligne) | Ouvrir le dialogue d'édition. |
| **Activer / Désactiver** | Basculer l'état disponible sans supprimer. Les Line-Ins désactivés n'apparaissent pas dans la bibliothèque de glisser. |
| **Supprimer** | Retirer le Line-In. Les lignes de planning qui le référencent sont aussi retirées. |

> **Comment ça marche sous le capot.** Toutes les actions
> mutantes sont de minces pass-through depuis
> `application/controllers/LineinController.php` vers
> l'API REST Django à `/api/v2/audio/linein[/<id>]`. Le
> contrôleur applique seulement l'ACL (Admin + Super
> Admin) ; le côté Python à
> `backend/api/libretime_api/linein/` possède validation
> et persistance dans `rastatime_linein`. Voir
> ARCHITECTURE §14.

---

## 3. Créer un Line-In

Line-In Library → **+ Nouveau**.

| Champ | Notes |
|---|---|
| **Nom** | Requis. Unique. Le libellé visible partout. |
| **Périphérique** | Requis. Menu déroulant liste chaque périphérique d'entrée que l'OS voit. Si votre périphérique manque, voir [Machine locale](./LOCAL_MACHINE.md). |
| **Longueur par défaut** | Requise. Format `HHh MMm SSs` (même parseur que Webstreams). Pour "joue jusqu'à être dit de s'arrêter" utilisez `0h 0m 0s` (affiche comme `∞`). |
| **Activé** | Par défaut activé. Décocher pour créer le Line-In mais le supprimer de la bibliothèque de glisser. |

> **Où sont les canaux d'entrée ?** Cet éditeur rapide reste
> volontairement épuré — le sélecteur **Canaux d'entrée** (et la
> priorité / le tableau de gestion complet) vit dans l'éditeur
> complet sous **Settings → Local Machine → Line-In Sources** ; le
> dialogue y renvoie. Un Line-In créé ici capture les canaux 1/2
> jusqu'à ce que vous choisissiez une autre paire dans l'éditeur
> complet.

### Interfaces multicanal : un Line-In par studio

Si l'interface audio de la station a plus de deux entrées (p. ex.
un Tascam US-16x08 à 16 entrées avec plusieurs studios câblés),
créez **un Line-In par studio** — même **Périphérique**, mais des
**Canaux d'entrée** différents (choisis sous **Settings → Local
Machine → Line-In Sources**) :

- `Studio A` → Périphérique `US-16x08`, Canaux `Stereo 1/2`
- `Studio B` → Périphérique `US-16x08`, Canaux `Stereo 5/6`
- `Micro invité Studio C` → Périphérique `US-16x08`, Canaux `Mono 7`

Chaque Line-In se comporte alors comme sa propre source dans la
bibliothèque et les émissions ; des émissions consécutives depuis
des studios différents sur la même interface commutent proprement à
la frontière d'émission.

> **Comment ça marche sous le capot.** Le simple `Stereo 1/2`
> utilise le chemin de capture DirectShow éprouvé. Toute autre
> sélection ne le peut pas — le pin DirectShow Windows des
> interfaces multicanal n'offre jamais que deux canaux — donc le
> playout démarre un petit feeder de capture qui lit le
> périphérique via l'API MME (la seule API Windows qui livre
> démontrablement tous les canaux sans toucher aux réglages
> système), extrait les canaux choisis et les injecte via le
> montage local `/linein-capture` dans le moteur de flux. Cela
> requiert le nom d'affichage du périphérique stocké sur la ligne —
> re-sauvegardez une fois les Line-Ins créés avant cette
> fonctionnalité.

### La longueur par défaut est importante

- Pour un **microphone** dans un studio normal de parole
  seulement, définissez la Longueur par défaut sur la
  longueur typique de segment de parole (5 min est
  courant).
- Pour une **sortie mixeur** qui pilote toute l'émission,
  définissez-la sur la longueur complète de l'émission
  (ex. 60 min) ou infini.
- Pour un **lecteur CD** ou autre source temporisée,
  définissez-la sur la longueur typique de piste (3 min).

L'opérateur peut toujours surcharger la durée par
utilisation dans le show-builder ; la Longueur par défaut
n'est que la valeur de départ.

---

## 4. Utiliser un Line-In dans une émission

Deux chemins :

### 4.1 Glisser direct sur une émission

Show-builder → glissez la ligne Line-In depuis le panneau
Bibliothèque sur l'émission. Un item de planning apparaît
avec le nom et la Longueur par défaut du Line-In.

### 4.2 À l'intérieur d'une playlist

Éditeur de playlist → glissez le Line-In depuis la
Bibliothèque. La ligne de playlist porte la référence du
Line-In + sa Longueur par défaut.

> **Comment ça marche sous le capot.** Migration 0054
> (2026-05-19) a ajouté `cc_playlistcontents.linein_id`
> comme foreign key nullable dans `rastatime_linein`,
> plus une contrainte CHECK qu'exactement un de
> `file_id` / `stream_id` / `block_id` / `linein_id` est
> non-NULL par ligne. Type 3 dans
> `cc_playlistcontents.type` indique une ligne Line-In.
> ARCHITECTURE §23.18 couvre la décision de schéma.

### Que joue quand le créneau du Line-In commence ?

**Chemin moteur Liquidsoap (défaut de production depuis 2026-05-29) :**

1. Pypo démarre le sous-processus FfmpegLineinCapture pour
   le périphérique carte son configuré (Windows dshow → MP3
   → mount Icecast local
   `http://localhost:8000/linein-capture`).
2. Pypo envoie une seule commande telnet à Liquidsoap :
   `linein.start` — la source `input.http` dédiée commence à
   consommer le mount de capture local.
3. Liquidsoap bufferise peu d'audio (~1,5 s sur le chemin
   multicanal depuis 2026-09-03). Une fois
   `source.is_ready` passé à true, le bus-switch route
   l'audio vers la source linein — les auditeurs entendent
   le microphone.
4. À la durée configurée, Pypo envoie `linein.stop` et
   arrête FfmpegLineinCapture ; le switch retombe sur
   scheduled.

**Comportement d'enregistrement (nouveau depuis Phase F,
2026-05-29) :** les line-inputs planifiés circulent
désormais par le bus Liquidsoap interne sur lequel
`output.file` est branché, et atterrissent dans l'archive
d'enregistrement `.mp3` par émission — même couverture que
pour les pistes et webstreams. Avant Phase F, les émissions
line-input-only avaient des enregistrements silencieux.

**Pourquoi FfmpegLineinCapture au lieu de `input.portaudio`
de Liquidsoap :** input.portaudio n'a pas de méthode
`set_device` à l'exécution, pas d'auto-reconnect au
débranchement USB, et utilise des indices PortAudio-entiers
au lieu des GUIDs d'endpoint audio Windows que la
bibliothèque frontend suit. Le watchdog de
FfmpegLineinCapture gère unplug-replug de manière
transparente ; Liquidsoap consomme son mount Icecast local
sans se soucier de l'identité du périphérique.

**Latence initiale d'émission :** les premières ~2-3 secondes
d'un créneau line-in peuvent être silencieuses sur les
haut-parleurs locaux de l'opérateur pendant que le buffer
Liquidsoap se remplit. Même caractéristique que les
webstreams planifiés (Phase E).

**Chemins legacy mpv / VLC (uniquement quand
`RASTATIME_PLAYOUT_ENGINE=mpv` ou `=vlc`) :**
mpv ouvre l'URL d'écoute FfmpegLineinCapture directement et
FfmpegStreamer ré-encode vers Icecast. Pas d'enregistrement
pour les émissions line-input-only dans ce mode.

Quand la durée du créneau s'écoule, le moteur envoie un
événement `LINEIN_END` et le source switcher retourne au
planning.

---

## 5. Modifier ou retirer un Line-In

### Modifier

Line-In Library → cliquez sur la ligne → **Modifier**.
Changez nom, périphérique, longueur par défaut ou état
activé. **Enregistrer**.

- **Changement de nom** se propage à la liste Bibliothèque
  et au widget En cours au prochain rafraîchissement.
- **Changement de périphérique** se propage à *chaque*
  utilisation future.
- **Changement de Longueur par défaut** affecte seulement
  les *nouvelles* utilisations.
- **Activé = désactivé** retire le Line-In immédiatement
  de la bibliothèque de glisser.

### Désactiver

Menu contextuel ligne → **Désactiver**. Le Line-In reste
dans la page bibliothèque mais disparaît de la
bibliothèque source de glisser.

### Supprimer

Menu contextuel ligne → **Supprimer**. Confirmez. Le
Line-In est retiré *et* chaque ligne
`cc_playlistcontents` et `cc_schedule` qui le référence
est retirée (CASCADE).

> **Conseil opérateur.** Préférez **Désactiver** plutôt
> que **Supprimer** sauf si vous êtes sûr que vous
> n'utiliserez plus jamais le Line-In.

---

## 6. La dépendance au périphérique physique

Un Line-In référence un périphérique carte son par
**ID côté OS**. Cet ID est stable à travers les
redémarrages tant que :

- Le périphérique reste branché.
- Aucun autre logiciel audio n'a été installé qui
  réassigne les IDs de périphérique.

Si le périphérique disparaît :

- Le Line-In est toujours dans la Bibliothèque.
- Sa ligne dans Paramètres → Line-In Library affiche un
  badge **point d'exclamation rouge** à côté de la
  colonne périphérique.
- Tout planning qui essaie de jouer le Line-In le saute
  avec un avertissement "Device not found" dans le log
  playout.
- Le fallback (silence ou boucle fallback) joue pour la
  durée du créneau.

Voir
[`docs/operator/DEVICE_MISSING.md`](../../operator/DEVICE_MISSING.md)
pour le runbook de récupération.

---

## 7. Permissions

Seuls les rôles **Admin (A)** et **Super Admin (S)**
peuvent créer, modifier ou supprimer des Line-Ins.
Raisons :

- Un Line-In référence un périphérique physique sur la
  machine de l'opérateur. Les changements peuvent casser
  le planning de chaque DJ.
- La configuration carte son est au niveau station.

Les DJ (H) et Program Managers (P) peuvent glisser les
Line-Ins existants dans leurs propres
playlists / émissions, mais ne peuvent pas créer ou
modifier les définitions Line-In sous-jacentes.

---

## 8. Foire aux questions

### "Où est le paramètre 'Show Source' / 'Master Source' / 'Line In' d'origine ?"

LibreTime d'origine avait trois entrées en dur ("Show
Source", "Master Source", "Line In") configurées sous
**Paramètres → Live Sources**. RASTATIME garde Show Source
et Master Source (ce sont des entrées DJ distantes sur
Icecast — voir [Streams](./STREAMS.md)) mais remplace
le "Line In" unique en dur par la fonctionnalité Line-In
nommé documentée ici.

### "Deux Line-Ins peuvent-ils référencer le même périphérique physique ?"

Oui, mais un seul réussira à un moment donné. La plupart
des drivers carte son accordent l'accès exclusif au
premier ouvreur ; un second Line-In essayant d'ouvrir le
même périphérique en même temps échoue avec "device
busy".

### "Un Line-In peut-il être le seul contenu de l'autoloading playlist ?"

Oui. Créez une playlist contenant exactement une ligne
Line-In avec Longueur par défaut = la longueur de
l'émission (ou infini). Attachez cette playlist comme
autoloading playlist de l'émission.

### "L'audio du Line-In est-il enregistré si Record-per-Show est activé ?"

Oui (depuis Phase F, 2026-05-29). Dans le mode moteur
Liquidsoap, l'audio du line-in circule par le même bus audio
interne que celui sur lequel `output.file` est branché pour
l'archive MP3 par émission, et est capturé nativement —
avec les pistes régulières ou webstreams planifiés de la
même émission. Voir
[Enregistrement par émission](./RECORD_PER_SHOW.md).

(Dans les modes moteur mpv/VLC dépréciés, l'enregistrement
n'est pas disponible — voir
[Paramètres → Moteur de Playout](./SETTINGS.md).)

### "Puis-je ajouter une source audio réseau (ex. AES67 / Dante) comme Line-In ?"

Seulement si la source se présente comme périphérique
d'entrée carte son Windows — beaucoup de drivers AES67 /
Dante livrent une carte son virtuelle. Si elle apparaît
dans le menu déroulant des périphériques d'entrée de
Paramètres → Machine locale, elle fonctionne comme
Line-In.

---

## Où aller ensuite

* [Machine locale](./LOCAL_MACHINE.md) — configuration
  carte son physique.
* [Bibliothèque](./LIBRARY.md) — les Line-Ins
  apparaissent aussi dans la Bibliothèque principale.
* [Tableau de bord](./DASHBOARD.md) → État de source —
  voir quel Line-In est actuellement à l'antenne.
* [`docs/operator/LINE_IN_BROKEN.md`](../../operator/LINE_IN_BROKEN.md)
  — procédure d'urgence.
* [`docs/operator/DEVICE_MISSING.md`](../../operator/DEVICE_MISSING.md)
  — quand le périphérique carte son sous-jacent disparaît.
