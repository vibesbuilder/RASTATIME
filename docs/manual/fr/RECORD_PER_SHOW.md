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

L'implémentation est un sous-processus FFmpeg indépendant
qui ouvre le premier mountpoint Icecast configuré de la
station comme entrée et l'écrit textuellement dans un
fichier :

```
   ffmpeg -i http://localhost:8000/rastatime \
          -c copy \
          -t <durée-émission-secondes> \
          -y C:\rastatime\recordings\<show-id>-<starts-at>.mp3
```

Le drapeau `-c copy` signifie **aucun ré-encodage** — les
octets sortant d'Icecast sont écrits dans le fichier tels
quels.

| Propriété | Valeur |
|---|---|
| **Coût CPU** | ~1-2 % d'un cœur sur Intel i3-1315U |
| **Qualité** | Identique au stream public (typiquement 192 k ou 320 k MP3) |
| **Isolation des défaillances** | Crash de l'enregistreur n'affecte jamais le stream live |
| **Changements de source** | Capturés automatiquement |

> **Pourquoi ne pas enregistrer le bus interne haute
> qualité ?** Un encodeur séparé alimenté par PCM
> pourrait produire 320 kbps MP3 ou FLAC, mais coûterait
> ~10x le CPU et nécessiterait d'enseigner à
> l'enregistreur quelle source est active à chaque
> moment. Le CPU est le frein ; pour la radio parlée, la
> différence de qualité est à la limite imperceptible.
> ARCHITECTURE §23.13 a le tableau des alternatives
> considérées.

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
> début de l'émission. Le handler d'enregistreur dans
> `backend/playout/libretime_playout/engine/ffmpeg_recorder.py`
> lance le sous-processus FFmpeg. À la fin de l'émission,
> le moteur émet `SHOW_RECORD_END` et le sous-processus
> est signalé pour s'arrêter. Voir ARCHITECTURE §23.13.

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
configurés dans `config\libretime.conf` sous la section
`[recording]`.

Placeholders disponibles : `{show_id}`, `{show_name}`,
`{starts_at}` (datetime), `{ends_at}` (datetime).

> **Conseil opérateur.** Gardez le show_id au début du
> nom de fichier. L'OS trie par nom de fichier, donc
> show_id-en-premier signifie que les enregistrements
> restent dans l'ordre chronologique.

---

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

L'enregistreur ne capture que le **premier stream
configuré**.

### "Enregistrement par émission capture-t-il la source Live DJ ?"

Oui. Tant que la source Live DJ est à l'antenne, elle est
capturée.

### "Pourquoi la taille de fichier de l'enregistrement est-elle plus grande que durée × bitrate ?"

La structure de trame MP3 a quelques octets de surcharge
par trame.

### "Puis-je enregistrer avec un bitrate différent du stream ?"

Non (parce que `-c copy` saute le ré-encodage). Pour
enregistrer avec un bitrate différent, il faudrait
ré-encoder, ce qui coûte CPU et qualité. Pas supporté
via l'interface.

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
