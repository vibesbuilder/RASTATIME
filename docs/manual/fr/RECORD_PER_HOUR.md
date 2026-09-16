# Enregistrement 24/7 (Record-per-Hour)

> **Où vous êtes dans le manuel.** Ceci est la fonction
> **Enregistrement 24/7** à l'échelle de la station,
> configurée dans
> [Paramètres → Machine locale](./LOCAL_MACHINE.md). C'est le
> compagnon permanent de l'[Enregistrement par
> émission](./RECORD_PER_SHOW.md).

L'**Enregistrement 24/7** enregistre en continu tout ce qui
passe à l'antenne — 24 heures sur 24, indépendamment des
émissions — et le découpe en **un fichier par heure d'horloge**.
Il capture les trous que l'enregistrement par émission manque
(remplissage Auto-DJ, silences entre émissions, contenu non
planifié, urgences), ce qui en fait l'outil adapté aux
**archives de conformité, à la réécoute / rattrapage et à la
sauvegarde d'urgence**.

Comme l'enregistreur par émission, c'est une **prise de
sortie** parallèle sur le bus audio interne de Liquidsoap : il
ne change rien à la planification ou à la lecture — il écoute
l'audio à l'antenne et l'écrit sur le disque.

---

## 1. Enregistrement 24/7 vs. par émission

Les deux enregistreurs sont indépendants et peuvent tourner en
même temps, dans des **dossiers séparés**.

| | Par émission | 24/7 |
|---|---|---|
| **Portée** | Un fichier par émission marquée « enregistrer » | Un fichier par heure d'horloge, toujours actif |
| **Capture** | Seulement pendant une émission enregistrée | Tout, 24/7 (y compris trous, remplissage, urgences) |
| **Configuré** | Par émission (Calendrier) | Une fois (Paramètres → Machine locale) |
| **Nom de fichier** | `<YYYY-MM-DD HH-MM> - <émission>.mp3` | `<YYYY-MM-DD HH>-00.<ext>` |
| **Qualité** | MP3 320 kbps fixe | Format + débit au choix (défaut 192 kbps MP3) |
| **Fichiers de repères** | Non | Oui (`.cues.json` par heure) |

> **Pourquoi deux enregistreurs ?** Le mode par émission donne
> un fichier propre, titré par émission, pour les émissions qui
> vous importent. Le mode 24/7 donne une archive ininterrompue
> de toute la diffusion pour la conformité et la réécoute.
> Beaucoup de stations utilisent les deux.

---

## 2. Comment ça marche

Un second bloc Liquidsoap `output.file` prend le même bus audio
interne qui alimente les sorties Icecast publiques, et bascule
vers un nouveau fichier à chaque passage d'heure :

```liquidsoap
output.file(
  id="recording_hourly",
  reopen_when=rec247_reopen,   # vrai quand l'heure d'horloge change
  fallible=true,
  %ffmpeg(format="mp3", %audio(codec="libmp3lame", b="192k")),
  {rec247_path()},             # <dossier>/<YYYY-MM-DD>/<YYYY-MM-DD HH>-00.mp3
  bus,
)
```

Le bloc n'est rendu dans le script Liquidsoap en cours
d'exécution **que lorsque vous activez la fonction** ; sinon
c'est un commentaire sans effet et le flux en direct reste
intact.

> **Écrit par Liquidsoap.** Comme l'enregistrement par
> émission, le 24/7 est assuré par `output.file` de Liquidsoap
> sur le bus interne (Liquidsoap est le seul moteur de playout
> depuis le 2026-09-10).

---

## 3. Activer l'enregistrement 24/7

**Paramètres → Machine locale → « 24/7 Recording Folder »** (la
section juste au-dessus de « Show Recording Folder ») :

| Champ | Signification |
|---|---|
| **Enable** | Interrupteur principal. Un dossier est requis si activé. |
| **Folder path** | Chemin absolu sur cette machine — créé à l'enregistrement s'il n'existe pas. Dans ou hors de l'arborescence du projet (p. ex. `C:\rastatime\recordings-247` ou `D:\rec247`). Gardez-le **séparé** du Show Recording Folder. |
| **Format** | MP3 / AAC / OGG (Vorbis) / Opus. Défaut **MP3**. |
| **Bitrate** | 96–320 kbps. Défaut **192** (qualité archive, ~moitié du disque de 320). |
| **Delete after (days)** | Fenêtre de nettoyage automatique. `0` = conserver indéfiniment. |

Cliquez **Save**, puis **redémarrez le service de diffusion**
pour appliquer (voir [§5](#5-appliquer-les-modifications)). La
ligne de statut vous le rappelle.

> **Sous le capot.** Save stocke les clés cc_pref
> `local_247_recording_{enabled,folder,format,bitrate,retention_days}`.
> Au démarrage du playout, elles sont lues et rendues dans
> `rastatime.liq` ; le démon de nettoyage et l'écrivain de
> repères les lisent aussi.

---

## 4. Où vivent les enregistrements

```
   <dossier>\<YYYY-MM-DD>\<YYYY-MM-DD HH>-00.<ext>
   <dossier>\<YYYY-MM-DD>\<YYYY-MM-DD HH>-00.cues.json
```

Exemple (dossier `C:\rastatime\recordings-247`, MP3) :

```
   C:\rastatime\recordings-247\2026-06-05\2026-06-05 14-00.mp3
   C:\rastatime\recordings-247\2026-06-05\2026-06-05 14-00.cues.json
```

Les heures sont l'**horloge locale de l'ordinateur du studio**,
pour que le nom de fichier corresponde à ce qui était à
l'antenne. Les fichiers basculent à l'heure pile ; la
transition est sans couture (aucun trou audible entre les
heures).

### 4.1 Fichiers de repères (cue sidecars)

À côté de chaque fichier audio horaire se trouve un **fichier
de repères** JSON qui marque ce qui s'est passé pendant cette
heure, pour qu'un futur lecteur de rattrapage saute directement
à une émission ou une piste :

```json
{
  "version": 1,
  "recording": "2026-06-05 14-00.mp3",
  "hour_start": "2026-06-05T14:00:00",
  "audio_start": "2026-06-05T14:00:00",
  "audio_start_offset": 0.0,
  "marks": [
    {"t": 0.0,   "kind": "show",  "event": "start", "name": "Après-midi"},
    {"t": 0.0,   "kind": "track", "event": "start", "show": "Après-midi",
                 "title": "Song A", "artist": "Artist A"},
    {"t": 183.4, "kind": "track", "event": "end"},
    {"t": 600.0, "kind": "webstream", "event": "start", "show": "Infos"}
  ]
}
```

`t` est le décalage **en secondes depuis le début de l'heure**.
`kind` vaut `track` / `show` / `webstream` / `linein` ; `event`
vaut `start` / `end`. Les limites d'émission sont déduites d'un
changement d'émission, donc elles couvrent toute émission ayant
du contenu. Une piste qui chevauche le passage d'heure a son
`start` dans le fichier de repères de l'heure précédente et son
`end` dans le nouveau.

Depuis le 16/09/2026, le fichier de repères note aussi quand le
fichier audio de l'heure a été créé : `audio_start` (heure locale)
et `audio_start_offset` (secondes après `hour_start`). Une heure
complète a un décalage de 0 ; la première heure partielle après un
redémarrage - chaque jour après le redémarrage de 04:00 - commence
plus tard, et un lecteur se positionne alors à
`t - audio_start_offset` dans ce fichier.

---

## 5. Appliquer les modifications

> **Depuis le 16/09/2026, aucun redémarrage manuel n'est nécessaire.**
> La diffusion remarque une modification enregistrée à son prochain
> rafraîchissement de la grille (sous deux minutes), régénère le script
> et redémarre Liquidsoap au prochain moment calme - ou, avec un
> programme 24/7, entre deux pistes fichier. Les auditeurs restent
> connectés via les montages de secours ; la première heure après le
> redémarrage est un fichier partiel (voir `audio_start` au §4.1). Les
> étapes ci-dessous restent la voie manuelle.

Les réglages 24/7 sont lus au démarrage du playout et intégrés
au script Liquidsoap. Après avoir enregistré une modification
(Enable, dossier, format, débit), **redémarrez le service de
diffusion** pour qu'il re-génère le script :

- Redémarrez le service Windows **RASTATIME-PLAYOUT** (il
  re-génère `rastatime.liq` et redémarre
  **RASTATIME-LIQUIDSOAP**).
- Choisissez un moment à faible audience — le redémarrage cause
  une brève (~5 s) reconnexion du flux.

L'exception est la valeur **Delete after (days)** : le démon de
nettoyage la relit à chaque cycle, une modification de la seule
rétention prend donc effet dans l'heure sans redémarrage.

> **Retour arrière.** Décochez Enable, enregistrez, et
> redémarrez — le bloc enregistreur n'est plus rendu et le flux
> se comporte exactement comme avant. Les fichiers déjà
> enregistrés restent sur le disque.

---

## 6. Nettoyage automatique (rétention)

Quand **Delete after (days)** est supérieur à 0, un démon dans
le service de diffusion purge des dossiers journaliers entiers
dès qu'ils atteignent cet âge. Il tourne environ une fois par
heure.

Il ne touche jamais que les dossiers journaliers nommés
`YYYY-MM-DD` **à l'intérieur du dossier 24/7** — votre Show
Recording Folder et tous les autres fichiers ne sont jamais
affectés. `0` désactive le nettoyage (conserver indéfiniment).

---

## 7. L'exclusion antivirus est OBLIGATOIRE

> ⚠️ Même mise en garde que pour [Enregistrement par émission §3.5](./RECORD_PER_SHOW.md)
> — et elle compte encore plus ici, car l'enregistreur 24/7
> écrit **en continu**.

Les antivirus en temps réel (Bitdefender, Windows Defender, …)
analysent chaque écriture dans le fichier en croissance et
peuvent verrouiller l'encodeur assez longtemps pour perdre de
l'audio. **Ajoutez le dossier 24/7 à la liste d'exclusions de
votre antivirus** avant d'activer l'enregistreur.

Si un fichier horaire ressort trop court alors que tout le
reste va bien, les causes habituelles sont l'analyse antivirus
ou une machine surchargée (le « rattrapage de latence » de
Liquidsoap sous forte charge CPU/disque peut perdre de l'audio
d'enregistrement). Le premier fichier après activation est
toujours une heure partielle — c'est attendu.

---

## 8. Planifier l'espace disque

L'enregistrement 24/7 ne s'arrête jamais ; dimensionnez le
disque pour la journée entière × la fenêtre de rétention :

| Débit | 1 heure | 1 jour | 1 semaine |
|---|---|---|---|
| 128 kbps | ~58 Mo | ~1,4 Go | ~9,5 Go |
| 192 kbps *(défaut)* | ~86 Mo | ~2,1 Go | ~14 Go |
| 320 kbps | ~145 Mo | ~3,4 Go | ~24 Go |

Avec **Delete after (days)** défini, l'empreinte est bornée :
environ `taille d'un jour × jours de rétention`. Les fichiers
de repères sont minuscules (quelques Ko par heure).

---

## 9. Foire aux questions

### « Pourquoi le premier fichier est-il plus court qu'une heure ? »

L'enregistreur démarre quand vous activez + redémarrez, en
général en milieu d'heure — le premier fichier ne couvre donc
que le reste de cette heure. Chaque fichier suivant est une
heure d'horloge complète.

### « Une heure est ressortie de quelques minutes trop courte — un bug ? »

Presque toujours une charge externe, pas l'enregistreur : une
analyse antivirus (voir [§7](#7-lexclusion-antivirus-est-obligatoire))
ou une machine surchargée faisant perdre de l'audio à
Liquidsoap pendant le rattrapage de latence. Un écart de 1–3
secondes est l'alignement normal des trames MP3.

### « Puis-je enregistrer en 24/7 et par émission en même temps ? »

Oui. Ce sont des prises `output.file` indépendantes sur le même
bus, écrivant dans des dossiers séparés. Les deux tournent
ensemble sans coordination supplémentaire.

### « Capture-t-il DJ en direct / webstream / entrée ligne ? »

Oui — il prend le bus à l'antenne, donc ce que les auditeurs
entendent est enregistré, quelle que soit la source. (Les
repères pour une prise de contrôle DJ-harbor en direct sont une
limite v1 connue — l'audio est quand même enregistré, le
segment en direct peut juste ne pas avoir son propre repère.)

### « Puis-je changer le format / débit plus tard ? »

Oui — changez-le dans les Paramètres et redémarrez le service
de diffusion. Les fichiers existants gardent leur format
d'origine ; les nouvelles heures utilisent le nouveau réglage.

---

## Pour aller plus loin

* [Enregistrement par émission](./RECORD_PER_SHOW.md) —
  l'enregistreur compagnon par émission.
* [Paramètres → Machine locale](./LOCAL_MACHINE.md) — où vous
  configurez les deux enregistreurs.
* [Streams](./STREAMS.md) — la sortie à l'antenne que les deux
  enregistreurs prennent.
* [`docs/operator/BACKUP.md`](../../operator/BACKUP.md) —
  politique de rétention / copie hors-machine.
