# Webstreams

> **Où vous êtes dans le manuel.** Les Webstreams sont un
> type d'item de bibliothèque aux côtés des pistes, smart
> blocks, playlists et line-ins. Voir
> [Bibliothèque](./LIBRARY.md) pour le tour général ; ce
> chapitre couvre les aspects spécifiques aux Webstreams.

Un **Webstream** est une URL pointant vers une autre
source audio HTTP — typiquement un stream Icecast ou
Shoutcast opéré par quelqu'un d'autre. Quand planifié dans
une émission, le moteur de playout se connecte à l'URL et
diffuse son contenu pendant la durée configurée.

Les Webstreams sont la façon la plus simple de syndiquer
du contenu externe : un bulletin d'info horaire relayé de
la BBC, un flux météo local, un service musical
automatisé. La source distante fait tout le travail
lourd ; votre station n'a besoin que d'inclure l'URL dans
le planning.

---

## 1. L'entrée de bibliothèque Webstream

Bibliothèque → puce de filtre **Webstream** (orange).

Chaque webstream a :

| Colonne | Signification |
|---|---|
| **Titre** | Nom d'affichage. Utilisé partout. |
| **URL** | L'URL source HTTP(S). |
| **Longueur** | Durée par défaut quand planifié — combien de temps le webstream joue par utilisation. Format `01h 05m 05s` depuis 2026-05-19. |

La Longueur est le *seul* paramètre sensible au temps —
un webstream "joue pour toujours" du point de vue de la
source distante ; la Longueur dans RASTATIME dit au
playout quand se déconnecter et passer à l'item suivant.

---

## 2. Créer un Webstream

Bibliothèque → **+ Nouveau** → **Webstream**.

| Champ | Notes |
|---|---|
| **Nom** | Requis. Le libellé visible dans la bibliothèque et sur le planning. |
| **URL source** | Requise. L'URL HTTP(S) du stream audio. URL de stream direct, pas une page d'atterrissage de player. Exemples : `http://stream.bbc.co.uk/...`, `http://icecast.example.com:8000/mountpoint`. |
| **Longueur par défaut** | Requise. Format `HHh MMm SSs`. Voir §3 pour le détail de précision aux secondes. |
| **Description** | Texte libre, optionnel. |
| **Type MIME** | Détection automatique par défaut ; surchargez seulement si la source rapporte mal son type MIME. |

> **Conseil opérateur.** Testez l'URL dans un navigateur
> ou avec `curl -I` avant d'enregistrer. RASTATIME ne
> pré-vole pas l'URL au moment de l'enregistrement — une
> URL cassée ne fait surface que quand le webstream est
> réellement planifié.

> **Comment ça marche sous le capot.** Les webstreams
> vivent dans `cc_webstream` (id, name, description, url,
> length, creator_id, mtime). Quand planifié, une ligne
> `cc_schedule` référence le webstream via `stream_id`.
> Au moment de jouer, le moteur de playout ouvre une
> source HTTP via libVLC et publie son PCM décodé vers
> le mixeur de sortie. Voir ARCHITECTURE §10.

---

## 3. Longueur par défaut avec précision aux secondes (Section 23.17)

Avant 2026-05-19, le champ Longueur par défaut acceptait
seulement heures et minutes ("01h 05m"). La colonne de
base de données sous-jacente est un PostgreSQL `interval`
qui stockait toujours "HH:MM:SS" en interne, mais la
composante secondes était à zéro dur, et le parseur du
formulaire ne l'acceptait pas.

Depuis 2026-05-19, le formulaire accepte une **troisième
composante secondes optionnelle** :

```
   01h 05m 05s    ← 1 heure 5 minutes 5 secondes
   01h 05m        ← 1 heure 5 minutes (secondes optionnelles)
        05m       ← 5 minutes (heures optionnelles)
            45s   ← 45 secondes (un ID station de 45 s via webstream)
```

L'affichage de lecture montre toujours les trois
composantes ("01h 05m 00s") pour la cohérence visuelle.
Le validateur est entièrement rétrocompatible : toute
entrée pré-2026-05-19 ("01h 05m") parse encore.

> **Pourquoi c'est important.** Stings courts, IDs de
> station et jingles servis via URL webstream devaient
> auparavant être arrondis à une minute. Un jingle de
> 30 s planifié comme "1 minute" jouait le jingle suivi
> de 30 s de silence. Avec la précision aux secondes, le
> créneau du jingle est exactement 30 s et l'item
> suivant démarre à l'heure.

> **Comment ça marche sous le capot.** Trois points
> chauds dans `application/models/Webstream.php`
> contiennent la gestion des secondes :
>
> - `getDefaultLength()` formate avec `%H:%I:%S`.
> - `analyzeFormData()` regex étendue avec un groupe
>   optionnel `(<n>s)`.
> - `save()` écrit le `DateInterval` comme `%H:%I:%S`.
>
> Voir ARCHITECTURE §23.17 + commit fae0fc5.

---

## 4. Planifier un Webstream

Identique à n'importe quel item de bibliothèque :

### 4.1 Directement sur une émission

Show-builder → glissez la ligne webstream sur l'émission.
Un item de planning apparaît avec le nom du webstream et
la Longueur par défaut.

### 4.2 À l'intérieur d'une playlist

Éditeur de playlist → glissez le webstream sur la
playlist.

### Que joue quand le créneau commence ?

**Chemin moteur Liquidsoap (défaut de production depuis 2026-05-29) :**

1. Pypo envoie trois commandes telnet à Liquidsoap :
   - `webstream.url <URL>` — définit l'URL HTTP sur la
     source dédiée `input.http`.
   - `var.set webstream.gain = <facteur>` — définit le
     facteur d'amplification par stream (conversion
     dB → linéaire dans Pypo).
   - `webstream.start` — demande à la source de se connecter.
2. La source `input.http` de Liquidsoap ouvre la connexion
   HTTP et bufferise quelques secondes d'audio (pont d'horloge
   5 s, tampon de flux jusqu'à 10 s). Depuis le 2026-09-04 cela
   se fait déjà **10 s avant le créneau** (« préchauffage »), la
   *porte* du bus fermée, si bien que le tampon est plein au début
   du créneau. En fin de créneau, Pypo ferme la porte : le bus fond
   le webstream sous l'élément suivant pendant la durée de crossfade
   par défaut (Settings → General ; 0 = « ducking »), puis envoie
   `webstream.stop` — l'élément suivant démarre à l'heure.
3. Au début du créneau Pypo ouvre la porte ; le bus-switch route
   l'audio vers la source webstream en une trame — les auditeurs
   entendent le stream.
4. À la durée configurée, Pypo envoie `webstream.stop` ; le
   switch retombe sur scheduled (silence ou la piste
   suivante).

**Comportement d'enregistrement (nouveau depuis Phase E,
2026-05-29) :**
Les webstreams planifiés atterrissent désormais dans
l'archive d'enregistrement `.mp3` par émission — l'audio
circule par le bus Liquidsoap interne sur lequel
`output.file` est branché, et est capturé avec les pistes
régulières de la même émission. Avant Phase E, les
émissions webstream-only avaient des enregistrements
silencieux.

**Latence initiale d'émission :** avec le préchauffage (depuis
le 2026-09-04) un créneau webstream démarre sans trou — le flux a
été connecté et mis en tampon 10 s plus tôt. Le **même** flux dans
l'émission suivante continue simplement (passation de la seule
comptabilité, sans coupure). Seul un webstream *différent* juste
après un webstream (une seule source de flux) a encore besoin de
~5 s de mise en tampon. Les lecteurs
côté auditeur ajoutent leur propre buffer de ~10 s, donc le délai
effectif perçu par l'auditeur final est dominé par le buffer côté
lecteur.

**Chemins legacy mpv / VLC (uniquement quand
`RASTATIME_PLAYOUT_ENGINE=mpv` ou `=vlc`) :**
mpv ouvre l'URL HTTP directement et FfmpegStreamer
ré-encode vers Icecast. Pas d'enregistrement pour les
émissions webstream-only dans ce mode.

### Que se passe-t-il si l'URL est inaccessible ?

`input.http` réessaie la connexion toutes les **2 secondes**
(`poll_delay`) avec un **timeout de 10 secondes** par
tentative (`timeout`). Pendant que les retries tournent,
`source.is_ready` reste à false et le bus-switch retombe
sur scheduled (silence). Les retries continuent pendant
toute la durée du créneau planifié.

Le log Liquidsoap capture chaque tentative de connexion
échouée :

```
[input.http:3] Connection refused: <url>
[input.http:3] Connecting to <url> ...
```

Symptôme visible pour l'opérateur : l'émission joue du
silence pendant toute sa durée. Aucun popup
d'avertissement dans le dashboard ; consultez le log
Liquidsoap (`C:/rastatime/logs/liquidsoap.log` sur
Windows) si un webstream planifié est resté silencieux.

> **Conseil opérateur.** Un webstream qui "parfois ne
> joue rien" signifie généralement que l'URL de la source
> a changé. Vérifiez l'URL dans un navigateur.

---

## 5. Modifier ou supprimer un Webstream

| Action | Effet |
|---|---|
| **Modifier** | Ouvrir le dialogue. Les enregistrements se propagent à *toutes* les utilisations planifiées futures. |
| **Supprimer** | Retirer le webstream. Toutes les lignes `cc_playlistcontents` et `cc_schedule` qui le référencent sont retirées (CASCADE). |

---

## 6. Gain de stream (gain d'entrée par-stream)

Les webstreams de sources tierces sont souvent plus forts
ou plus faibles que le reste de votre bibliothèque. Pour
normaliser :

Modifier le webstream → **Gain d'entrée (dB)** →
définissez une valeur positive pour booster ou négative
pour atténuer.

| Réglage | Effet |
|---|---|
| `0.0` (par défaut) | Aucun changement de gain. |
| `+3.0` | Boost de 3 dB. |
| `-6.0` | Atténuation de 6 dB. |

Le gain est appliqué dans le moteur de playout avant que
l'audio n'atteigne le mixeur de sortie.

> **Comment ça marche sous le capot.** Migration 0048 a
> ajouté `cc_webstream.input_gain_db` (FLOAT). Le moteur
> de playout lit ceci en ouvrant la source et applique un
> filtre FFmpeg `volume=<dB>dB` à la chaîne de décodage.
> Voir ARCHITECTURE §10.4.

---

## 7. Webstreams dans autoloading playlists

Un webstream peut être tout le body d'une autoloading
playlist — utile pour "chaque lundi 14:00 nous relayons
X" sans planifier l'URL manuellement chaque semaine.

Limitations :

- Un webstream dans un body **Répéter jusqu'à plein**
  produit des tentatives de connexion courtes répétées.
  Évitez — utilisez plutôt une seule ligne webstream de
  longue durée.
- Les smart blocks dans une playlist portant webstream
  n'obtiennent pas le traitement de réserve d'outro de la
  même façon.

---

## 8. Foire aux questions

### "Pourquoi mon webstream coupe-t-il après quelques secondes ?"

La **Longueur par défaut** est probablement définie très
courte. Vérifiez la colonne Longueur de la ligne de
bibliothèque.

### "Puis-je planifier le même webstream sur deux émissions simultanément ?"

Non. Il y a un moteur de playout et un mixeur de sortie.
(Vous *pouvez* avoir deux streams de sortie différents
qui jouent du contenu différent — voir
[Streams](./STREAMS.md).)

### "Pourquoi le webstream sonne-t-il mal / glitché ?"

Causes courantes :

- L'URL du webstream est intermittente (problème côté
  source).
- La source est dans un codec que le moteur de playout
  ne peut pas décoder proprement. Essayez de définir le
  type MIME explicitement.
- Latence réseau vers la source dépasse le buffer.
- Le réseau de la machine opérateur a des pertes de
  paquets.

### "Puis-je enregistrer le contenu d'un webstream avec Record-per-Show ?"

Oui. L'enregistreur tape la sortie à l'antenne ; tout ce
qui joue (piste, webstream, line-in) est capturé. Voir
[Enregistrement par émission](./RECORD_PER_SHOW.md).

### "Comment m'authentifier à une source protégée par mot de passe ?"

Credentials en ligne dans l'URL :

```
   http://user:password@stream.example.com/private
```

### "Puis-je utiliser une URL HLS (.m3u8) ?"

Oui — libVLC gère HLS. Utilisez l'URL de playlist
maîtresse .m3u8 comme URL source.

### "Puis-je utiliser une URL YouTube Live ?"

Pas directement — YouTube n'expose pas d'URL de stream
direct stable. Solution de contournement : utilisez
`yt-dlp` pour résoudre l'URL de stream actuelle et mettre
à jour la ligne de bibliothèque webstream par cron. Pas
officiellement supporté.

---

## Où aller ensuite

* [Bibliothèque](./LIBRARY.md) — tour général de la
  Bibliothèque.
* [Calendrier](./CALENDAR.md) — planifier les items de
  bibliothèque.
* [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) —
  webstreams comme contenu autoloaded.
* [Streams](./STREAMS.md) — le côté *sortant* ; les
  webstreams ici sont le côté *entrant*.
