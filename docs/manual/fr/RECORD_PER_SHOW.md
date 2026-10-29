# Enregistrement par émission

> **Où vous êtes dans le manuel.** C'est un toggle
> par-émission sur le formulaire d'édition d'émission
> (voir [Calendrier](./CALENDAR.md) §2.3). La
> fonctionnalité remplace la case originale "Record from
> Line In?" par une capture plus large "enregistrer tout
> ce qui passe à l'antenne pendant l'émission". Section
> 23.13 dans ARCHITECTURE couvre les décisions techniques.

**Enregistrement par émission** écrit un fichier de tout
ce qui était à l'antenne pendant une émission — la
musique, le micro live, le relais webstream, tout — pour
archive, replay, podcast ou usage de conformité.

L'enregistrement est un **tap de sortie** parallèle : il
ne change rien à la façon dont l'émission est planifiée ou
jouée. L'enregistreur écoute simplement la sortie Icecast
publique et l'écrit dans un fichier pendant la durée de
l'émission.

---

## 1. Pourquoi ça marche ainsi

### Ce que faisait LibreTime d'origine

La fonctionnalité originale "Record from Line In?"
n'enregistrait *que* la source line-in (une entrée
physique spécifique), en utilisant Liquidsoap. C'était
utile pour "un animateur avec un micro dans le studio"
mais cassé pour tout le reste : émissions qui basculaient
entre pistes et micro ne capturaient que la partie micro ;
émissions sans source line-in ne pouvaient pas être
enregistrées du tout.

### Ce que fait RASTATIME

Le nouveau modèle enregistre la **sortie complète à
l'antenne** — ce que les auditeurs entendent pendant
l'émission, indépendamment de la source.

> **Mise à jour architecturale — Phase-C5 (2026-05-28).**
> Le pipeline d'enregistrement a migré d'un sous-processus
> FFmpeg-Icecast-tap séparé vers un bloc Liquidsoap
> `output.file` qui se branche directement sur le bus audio
> interne. Les deux architectures offrent le même
> comportement visible côté opérateur (enregistrement par
> émission dans un dossier) ; le tap sur le bus est juste
> plus simple, plus fiable, et utilise un MP3 fixe à
> 320 kbps de meilleure qualité. Voir ARCHITECTURE
> §23.13.bis pour le détail technique.

L'implémentation est un bloc Liquidsoap
`output.file(id="recording")` dans le sous-processus
Liquidsoap de longue durée. Il se branche sur le même bus
audio interne qui alimente les sorties Icecast publiques
et l'encode dans le format et au débit choisis sous Paramètres →
Machine locale → **Show Recording** (MP3 320 kbps par défaut ;
depuis le 2026-10-18 aussi AAC, OGG Vorbis et Opus de 96 à 320
kbps).  Avec la valeur par défaut, le bloc rendu est :

```liquidsoap
output.file(
  id="recording",
  %ffmpeg(format="mp3", %audio(codec="libmp3lame", b="320k", samplerate=44100)),
  {recording_path()},
  fallible=true,
  bus,
)
```

Les hooks start/stop par émission de Pypo pilotent le cycle
de vie via l'interface telnet de Liquidsoap :

```
recording.stop
var.set recording_path = C:/.../<YYYY-MM-DD HH-MM-SS> - <show>.mp3
recording.start
```

| Propriété | Valeur |
|---|---|
| **Coût CPU** | ~3 % d'un cœur sur Intel i3-1315U (un encodeur libmp3lame) |
| **Qualité** | MP3 320 kbps par défaut (Paramètres → Machine locale → Show Recording : MP3 / AAC / OGG Vorbis / Opus, 96–320 kbps) — même source que le stream Icecast principal |
| **Changements de source** | Capturés automatiquement (l'enregistrement se branche sur le même bus interne que le stream live) |
| **Isolation des défaillances** | `fallible=true` sur `output.file` empêche qu'une défaillance d'une seule sortie (disque plein, verrou de scan AV) ne se propage dans le graphe de sources |

> **Format et débit** se règlent sous Paramètres → Machine locale →
> Show Recording (depuis le 2026-10-18 ; par défaut MP3 320 kbps, la
> valeur fixe du 2026-05-27).  Le playout applique un changement à
> son prochain moment calme (ou à la prochaine limite de titre) ; les
> fichiers déjà écrits gardent leur format, et l'extension suit le
> format (`.mp3` / `.aac` / `.ogg` / `.opus`).  L'ancien
> `PlayoutConfig.record_bitrate` est ignoré.

> **L'enregistrement est écrit par Liquidsoap** (`output.file`
> sur le bus interne). Phase-C5 partie 2d a supprimé le chemin
> de code legacy FfmpegRecorder ; depuis le 2026-09-10,
> Liquidsoap est le seul moteur de playout, donc chaque
> émission avec enregistrement activé est enregistrée.

---

## 2. Activer Enregistrement par émission

Par émission, sur le formulaire d'édition d'émission.

### 2.1 Sur une nouvelle émission

Calendrier → Nouvelle émission → développer
**Enregistrement** → cocher **Enregistrer cette
émission :** → Enregistrer.

### 2.2 Sur une émission existante

Calendrier → cliquez sur l'émission → **Modifier
l'émission** → développer **Enregistrement** → cocher →
Enregistrer.

Le toggle prend effet à partir de la *prochaine* instance
à démarrer. Une émission qui a déjà commencé n'enregistre
pas rétroactivement.

> **Conseil opérateur.** Beaucoup de stations enregistrent
> chaque émission par défaut. La façon la plus rapide :
> cochez **Enregistrer cette émission :** sur un modèle,
> enregistrez comme Modèle d'émission, puis appliquez ce
> modèle à chaque émission. Voir
> [Modèles d'émission](./SHOW_TEMPLATES.md).

> **Comment ça marche sous le capot.** Le toggle définit
> `cc_show.record = TRUE`. Au début de l'émission, le
> builder de planning du moteur de playout émet un
> événement `SHOW_RECORD_START` avec id + nom + heure de
> début de l'émission. Le handler dans
> `backend/playout/rastatime_playout/playout_scheduler.py`
> envoie une commande `recording.start` au telnet
> Liquidsoap, qui ouvre le fichier .mp3 par émission. À
> la fin de l'émission, le moteur émet `SHOW_RECORD_END`
> et le handler envoie `recording.stop` pour fermer
> proprement le fichier. Voir ARCHITECTURE §23.13 (design
> FFmpeg d'origine) et §23.13.bis (migration Liquidsoap
> Phase-C5).

---

## 3. Où vit l'enregistrement

Par défaut, les enregistrements sont écrits à :

```
   C:\rastatime\recordings\<show-id>-<starts-at>.mp3
```

Exemple :

```
   C:\rastatime\recordings\1234-2026-05-21_14-00-00.mp3
```

Le répertoire et le modèle de nom de fichier sont
configurés dans `config\rastatime.conf` sous la section
`[recording]`.

Placeholders disponibles : `{show_id}`, `{show_name}`,
`{starts_at}` (datetime), `{ends_at}` (datetime).

> **Conseil opérateur.** Gardez le show_id au début du
> nom de fichier. L'OS trie par nom de fichier, donc
> show_id-en-premier signifie que les enregistrements
> restent dans l'ordre chronologique.

## 3.5 L'exclusion antivirus est OBLIGATOIRE

> ⚠️ **Important — s'applique à chaque ordinateur de studio
> exécutant RASTATIME.**

Le logiciel antivirus en temps réel (Bitdefender, Windows
Defender, Kaspersky, McAfee, ESET, …) scanne chaque écriture
de fichier — y compris le fichier .mp3 en cours
d'enregistrement qui grandit. Pour les émissions longues
(>30 min), le coût scan-lock-par-écriture s'accumule au
point où le pipeline audio de Liquidsoap drop des frames
pour suivre le rythme.

Reality-test 2026-05-28 : une émission de 60 min sans
exclusion antivirus n'a enregistré que 52 min 53 s d'audio
(~88 % de la durée prévue) ; le même pipeline avec le
dossier exclu de l'antivirus atteint 100 % de manière
reproductible.

**Mitigation : ajouter le dossier d'enregistrement à la
liste d'exceptions de votre antivirus.**

- **Bitdefender** (le plus courant sur les déploiements
  RASTATIME) : GUI Bitdefender → **Protection** →
  **Antivirus** → **Paramètres** → **Gérer les exceptions**
  → ajoutez le chemin du dossier d'enregistrement (par
  exemple `C:\Users\studio\Music\Show Recordings\` ou ce que vous
  avez configuré dans Settings → Local Machine → Recording
  Folder).
- **Windows Defender** : Paramètres → **Mise à jour et
  sécurité** → **Sécurité Windows** → **Protection contre
  les virus et menaces** → **Gérer les paramètres** →
  **Ajouter ou supprimer des exclusions** → ajoutez le
  dossier d'enregistrement.
- **Autres AV** : consultez leur documentation ; l'option
  s'appelle généralement « Exclusion », « Exception » ou
  « Liste blanche ».

Après ajout de l'exception, aucun redémarrage n'est
nécessaire ; l'enregistrement de la prochaine émission
fonctionnera à pleine qualité.

> **Conseil opérateur.** Ajoutez l'exception lors de la
> configuration initiale de RASTATIME AVANT que la première
> émission n'enregistre. Sinon, vous risquez d'avoir
> quelques heures d'enregistrements raccourcis avant de
> remarquer le problème.

---

## 3.6 Copier les enregistrements dans la bibliothèque *(depuis le 2026-10-19)*

Paramètres → Machine locale → **Show Recording** propose la case
**Copier les enregistrements d'émission dans la bibliothèque**.
Lorsqu'elle est cochée, chaque émission enregistrée est importée dans
la médiathèque dès que son fichier d'enregistrement est fermé :

- C'est une **copie** qui est importée ; le fichier du dossier
  d'enregistrement reste exactement où il est (votre archive n'est
  pas touchée).
- La copie reçoit le type de piste **Recordings** (créé à la première
  utilisation), le titre `<nom de l'émission> <AAAA-MM-JJ HH:MM>`, le
  nom de l'émission comme artiste et l'album `Show Recordings`, pour
  être facile à retrouver dans la bibliothèque.
- La piste est **liée à l'instance de l'émission** (le « fichier
  enregistré » du calendrier), de sorte qu'une rediffusion ultérieure
  d'une émission en direct puisse la reprendre.
- Un enregistrement déjà importé est reconnu par sa somme de contrôle
  et n'est pas importé une seconde fois.
- Le type de piste **Recordings** porte le fondu du changement
  d'émission (1 s par défaut) au lieu du fondu de 3 s entre titres, pour
  qu'une rediffusion construite à partir de tranches d'enregistrement
  garde la durée de l'original.  Réglable sous Paramètres → Track Types.

Fonctionnement : le playout signale le fichier fermé à l'application
web, qui vérifie que le chemin se trouve dans le dossier Show
Recording configuré, tague la copie avec ffmpeg et la transmet à
l'analyseur comme n'importe quel téléversement.  La case prend effet
pour les émissions qui se terminent après un redémarrage unique du
service RASTATIME-PLAYOUT suivant la mise à jour ; ensuite elle peut
être activée ou désactivée à tout moment sans redémarrage.

## 4. Trouver et télécharger un enregistrement

### Depuis le calendrier

Cliquez sur l'émission → **Voir le fichier enregistré**
dans le menu contextuel. Apparaît seulement après que
l'enregistrement a fini d'écrire.

Le dialogue montre nom de fichier, taille, durée,
bitrate et un lien de téléchargement direct.

### Depuis le système de fichiers

Parcourez `C:\rastatime\recordings\` directement.

---

## 5. Planification de la taille d'archive

Taille approximative pour un enregistrement d'1 heure :

| Bitrate de stream | Taille 1 heure |
|---|---|
| 96 kbps MP3 | ~43 MB |
| 128 kbps MP3 | ~58 MB |
| 192 kbps MP3 | ~86 MB |
| 256 kbps MP3 | ~115 MB |
| 320 kbps MP3 | ~145 MB |

Une station qui tourne 24/7 à 192 kbps avec toutes les
émissions enregistrées remplit environ **2 GB par jour**
ou **730 GB par an**.

Les enregistrements ne sont pas auto-supprimés. Pour les
faire tourner, configurez une tâche planifiée :

```powershell
# Supprimer enregistrements plus vieux que 90 jours
Get-ChildItem "C:\rastatime\recordings\" -File |
   Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-90) } |
   Remove-Item
```

Voir [`docs/operator/BACKUP.md`](../../operator/BACKUP.md)
pour le modèle de politique de rétention d'enregistrement.

---

## 6. Ce que les enregistrements contiennent

L'enregistreur capture **ce que le mountpoint Icecast
diffuse pendant l'émission** :

| Source | Inclus ? |
|---|---|
| Pistes planifiées | Oui |
| Webstreams | Oui |
| Line-ins | Oui |
| Show DJ (source live distante) | Oui |
| Master DJ | Oui |
| Auto-DJ fallback | Oui |
| Silence | Oui (comme silence réel dans le fichier) |

### Ce que les enregistrements ne contiennent PAS

- Audio pré-fader du studio.
- Plusieurs variantes de stream (seulement le **premier
  configuré** est enregistré).
- Métadonnées de stream de sortie (mises à jour ICY).

---

## 7. Utiliser les enregistrements comme podcasts / catchup

Un workflow de suite courant :

1. Enregistrements écrits dans
   `C:\rastatime\recordings\`.
2. Une tâche planifiée les copie vers un répertoire
   web-accessible.
3. Un générateur de flux RSS produit un flux podcast.
4. Les auditeurs s'abonnent.

RASTATIME ne livre pas de générateur RSS intégré pour les
enregistrements.

---

## 8. Enregistrement de conformité

Certaines juridictions exigent que les stations de
diffusion gardent un journal de diffusion pendant N
jours. Enregistrement par émission avec chaque émission
enregistrée + une copie d'archive par jour est suffisant
pour la plupart des règlements, mais :

- Vérifiez que le **bitrate** est acceptable pour votre
  régulateur.
- Configurez un **stockage hors machine** pour la
  résilience.
- Documentez la **chaîne de garde**.

---

## 9. Désactiver Enregistrement par émission

Modifier l'émission → développer **Enregistrement** →
décocher **Enregistrer cette émission :** → Enregistrer.

Les instances déjà enregistrées ne sont pas affectées (les
fichiers restent sur disque). Les instances futures ne
démarrent pas le sous-processus FFmpeg.

---

## 10. Foire aux questions

### "Pourquoi l'enregistrement commence-t-il quelques secondes avant l'émission ?"

Le sous-processus FFmpeg prend ~1-2 secondes pour
démarrer et s'attacher au stream Icecast. Pour éviter de
couper la toute première seconde de l'émission,
l'enregistreur démarre ~3 secondes *avant* `starts_at`.

Pour retirer le padding pré-émission après-coup :

```
ffmpeg -ss 00:00:03 -i input.mp3 -c copy output.mp3
```

### "Pourquoi l'enregistrement est-il silencieux ?"

Si tout l'enregistrement est silencieux, l'enregistreur
s'est attaché au stream mais le stream lui-même était
silencieux pendant l'émission. Vérifiez l'audio du stream
en écoutant à `http://<host>:8000/rastatime` pendant une
émission live.

### "Puis-je n'enregistrer qu'une partie d'une émission ?"

Non. Le toggle est par-émission. Pour obtenir un
enregistrement partiel, divisez la définition d'émission
en deux émissions plus courtes.

### "Deux émissions diffusant simultanément sur différentes sorties peuvent-elles toutes deux enregistrer ?"

Le modèle de planning de RASTATIME est single-show : à
tout moment, au plus une émission est à l'antenne, en
parallèle sur tous les streams de sortie configurés.
L'enregistrement se branche sur le bus Liquidsoap interne
(le même audio qui alimente toutes les sorties Icecast),
donc « différentes émissions sur différentes sorties »
n'est pas un cas supporté architecturalement.

### "Enregistrement par émission capture-t-il la source Live DJ ?"

Oui. Tant que la source Live DJ est à l'antenne (audible
sur le stream public), elle est capturée. L'enregistrement
ne distingue pas la source — c'est ce qui se trouve sur le
bus Liquidsoap interne (= ce que les auditeurs entendent).

### "Pourquoi la taille de fichier de l'enregistrement est-elle plus grande que durée × bitrate ?"

La structure de trame MP3 a quelques octets de surcharge
par trame. Pour un fichier de 320 kbps d'une heure, la
taille réelle est généralement de 144-145 MB plutôt que
les 144 MB mathématiques.

### "Pourquoi un long enregistrement est-il plus court que la durée d'émission prévue ?"

Très probablement, votre antivirus scanne le fichier .mp3
qui grandit et bloque l'encodeur Liquidsoap suffisamment
longtemps pour faire tomber des frames. Voir
[Section 3.5](#35-lexclusion-antivirus-est-obligatoire) —
ajouter le dossier d'enregistrement à la liste d'exceptions
de votre antivirus corrige cela.

Une petite différence résiduelle (1–3 secondes dans une
émission d'une heure) est normale et provient de
l'alignement des frontières de trames MP3.

### "Puis-je enregistrer avec un bitrate différent du stream ?"

Oui — depuis le 2026-10-18 sous Paramètres → Machine locale →
**Show Recording** : format MP3 / AAC / OGG Vorbis / Opus et débit
96–320 kbps (par défaut MP3 320 kbps).  L'enregistrement est un bloc
Liquidsoap `output.file` séparé avec son propre encodeur, donc
indépendant des réglages des streams publics.  Le playout applique
un changement à son prochain moment calme ; aucun redémarrage
manuel.

---

## Où aller ensuite

* [Streams](./STREAMS.md) — le stream de sortie que
  Record-per-Show tape.
* [Calendrier](./CALENDAR.md) — où activer / désactiver
  par émission.
* [Modèles d'émission](./SHOW_TEMPLATES.md) — tamponner
  l'enregistrement sur chaque nouvelle émission via un
  modèle.
* [`docs/operator/BACKUP.md`](../../operator/BACKUP.md) —
  modèle de politique de rétention d'enregistrement.
