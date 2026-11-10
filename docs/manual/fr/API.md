# API

> **Où vous êtes dans le manuel.** Ce chapitre s'adresse à qui veut
> lire les données de RASTATIME depuis l'extérieur — site de la
> station, site partenaire, script de surveillance — ou savoir ce que
> le système expose au public.  Il liste les points d'accès publics,
> explique l'interrupteur qui les ouvre, et dit à quoi sert la clé API
> et pourquoi elle ne doit jamais quitter la station.  Pour les
> widgets iframe prêts à l'emploi, voir
> [Widgets publics intégrables](./WIDGETS.md).

RASTATIME possède deux interfaces HTTP nées à des époques différentes :

| Interface | Chemin de base | Format | Utilisée par |
|---|---|---|---|
| **API REST v2** | `/api/v2/` | JSON, schéma OpenAPI, Swagger UI | Le playout, l'analyseur, les pages Paramètres, les scripts |
| **API legacy** | `/api/<action>` | JSON (parfois JSONP), images, M3U | Les widgets, le tableau de bord, les intégrations anciennes |

Les deux répondent à l'adresse web de la station
(`https://<station-host>/…`).  Tout ce qui suit vaut pour la station en
production ; une installation de développement se comporte de même.

---

## 1. Qui peut lire quoi

| Accès | Ce qu'il couvre |
|---|---|
| **Public, sans connexion** | Les points d'accès en lecture seule de l'API legacy de la section 3, tant que **Paramètres → General → Public RASTATIME API** est activé ; plus `version`, `info`, `now-playing` et la recherche / l'envoi des demandes d'auditeurs de l'API v2. |
| **Connexion (session ou basic auth)** | La navigation dans `/api/v2/` depuis un navigateur, le schéma OpenAPI et la Swagger UI.  Un compte connecté voit ce que son rôle permet (voir [Utilisateurs et rôles](./USERS_AND_ROLES.md)). |
| **Clé API** | Tous les autres points d'accès : écriture, état interne, listes de fichiers, réglages des flux.  Une seule clé pour toute la station, accès complet. |

Tout ce qui n'est pas public répond `401` ou `403` sans justificatif.
Aucune limitation de débit sur les points d'accès publics ; seuls ceux
des demandes d'auditeurs sont limités par auditeur.

---

## 2. L'interrupteur : Public RASTATIME API

**Paramètres → General → Public RASTATIME API** (on / off).

- **On :** les points d'accès en lecture de l'API legacy répondent
  sans clé.  C'est ce dont les widgets ont besoin — now-playing,
  programme hebdomadaire et lecteur lisent `live-info`, `track` et
  `show-logo`.  Éteindre l'interrupteur casse les widgets de votre site.
- **Off :** les mêmes points d'accès exigent la clé API.  À choisir
  seulement sans widgets et sans site externe qui lit le programme.

L'interrupteur ne touche pas l'API v2 et n'ouvre rien qui écrit.

---

## 3. Points d'accès publics en lecture (API legacy)

Tous renvoient du JSON sauf mention contraire.  Heures dans le fuseau
de la station, sauf si vous passez `timezone=` (un nom de la base tz
tel que `Europe/Berlin`, ou `UTC`).

| Point d'accès | Paramètres | Renvoie |
|---|---|---|
| `/api/live-info-v2` | `days` (défaut 2), `shows` (défaut 5), `timezone` | Ce qui est à l'antenne : `shows` (précédente / en cours / suivante), `tracks` (précédent / en cours / suivant), `sources` (DJ live, DJ master, automation), `station`. |
| `/api/live-info` | `type` (`endofday` ou intervalle), `limit` (défaut 5), `timezone` | L'ancienne forme des mêmes données : `currentShow`, `nextShow`, `current`, `next`, `previous`, `schedulerTime`. |
| `/api/week-info` | `timezone` | Le programme de cette semaine et de la suivante, une liste par jour (`monday` … `nextsunday`), chaque émission avec nom, heures, description, image, url. |
| `/api/station-metadata` | — | Nom, description, logo, langue, fuseau de la station et la liste des flux. |
| `/api/shows` | `show_id` (optionnel) | Toutes les émissions, ou une : id, nom, description, genre, url, couleurs, indicateur linked. |
| `/api/show-schedules` | `show_id` (requis), `start`, `end` (`YYYY-MM-DD HH:MM:SS`) | Les épisodes d'une émission dans la période. |
| `/api/show-tracks` | `instance_id` (requis) | Les lignes d'un épisode : position, titre, artiste, durée, début. |
| `/api/item-history-feed` | `start`, `end`, `instance_id` (optionnel) | L'historique de diffusion : quoi, quand, avec titre, artiste et épisode. |
| `/api/show-history-feed` | `start`, `end`, `user_id` (optionnel) | Les émissions diffusées dans la période. |
| `/api/track?id=<id fichier>&return=<type>` | `return` = `artwork`, `artwork-32`, `artwork-64`, `artwork-data` | La pochette d'un titre (JPG). |
| `/api/show-logo?id=<id émission>` | — | L'image d'une émission. |
| `/api/track-types` | — | Les types de pistes configurés dans la bibliothèque. |
| `/api/stream-m3u` | — | Un fichier M3U avec les flux de la station. |

**Ce qu'un titre expose.**  Les métadonnées de piste de `live-info` et
`live-info-v2` sont volontairement limitées aux crédits qu'un auditeur
peut voir : titre, artiste, album, année, genre, langue, durée, numéro
de piste et de disque, compositeur, chef, parolier, artiste original,
label, copyright, ISRC, bpm, humeur, les URL info / achat / artiste, la
référence de pochette et le type de piste.  Chemins de fichiers,
propriétaires, sommes de contrôle, commentaires, paroles et détails
d'import ne sont jamais envoyés.  `/api/shows` omet de même les ids
des playlists d'autoloading, d'intro et d'outro.

---

## 4. Points d'accès publics de l'API v2

| Point d'accès | Renvoie |
|---|---|
| `GET /api/v2/version` | `{"api_version": "…"}` |
| `GET /api/v2/info` | `{"station_name": "…"}` |
| `GET /api/v2/now-playing` | Ce qui est à l'antenne, lu dans la grille (voir ci-dessous). |
| `GET /api/v2/song-requests/search?q=<texte>` | Les titres qu'un auditeur peut demander : id, title, artist, album, has_artwork. |
| `POST /api/v2/song-requests` | Envoie une demande (`file_id`, `listener_label` optionnel).  Limité par auditeur ; voir [Song Requests](./SONG_REQUESTS.md). |

**now-playing** répond toujours `200` :

```json
{
  "is_playing": true,
  "now": "2026-11-05T13:07:21+00:00",
  "source": "scheduled",
  "started_at": "2026-11-05T13:07:00+00:00",
  "item": {
    "type": "file", "id": 1304,
    "title": "Example Song", "artist": "Example Artist", "album": "Example Album",
    "genre": "Pop", "year": "2024",
    "length_seconds": 251.438, "has_artwork": true,
    "starts_at": "2026-11-05T13:07:00+00:00",
    "ends_at": "2026-11-05T13:11:11+00:00"
  },
  "show": {"id": 912, "name": "…", "description": "…", "url": "…",
           "genre": "…", "starts_at": "…", "ends_at": "…"},
  "next": {"type": "file", "id": 1305, "title": "…", "…": "…"}
}
```

`type` vaut `file`, `webstream` ou `linein` ; `source` vaut
`scheduled`, `live_dj` ou `master_dj`.  Quand rien de la grille n'est à
l'antenne, `is_playing` est `false`, `item` et `started_at` sont
`null`, et `show` nomme toujours l'émission en cours.  Heures en UTC
(ISO 8601).

---

## 5. Utiliser l'API avec des identifiants

**Dans le navigateur.**  Connectez-vous à RASTATIME, puis ouvrez
`https://<station-host>/api/v2/` pour l'API navigable et
`https://<station-host>/api/v2/schema/swagger-ui` pour la Swagger UI
(le schéma OpenAPI brut est sous `/api/v2/schema`).  Les deux exigent
la connexion ; sans elle, `403`.

**Depuis un script.**  Envoyez la clé API de la station dans l'en-tête
`Authorization` :

```
Authorization: Api-Key <key>
```

La clé est la valeur `api_key` sous `[general]` dans
`C:\rastatime\config\rastatime.conf`.  L'API legacy l'accepte aussi en
`?api_key=<key>`.

> **Ne jamais confier la clé à un tiers.**  Il n'existe qu'une clé et
> elle donne l'accès complet : pushes de grille, listes de fichiers,
> mots de passe des flux, paramètres.  Un site partenaire qui n'a
> besoin que du programme utilise les points d'accès publics de la
> section 3 — sans clé.  S'il lui faut plus que lire, c'est une demande
> de jeton client en lecture seule (voir BACKLOG), pas de la clé de la
> station.

---

## 6. Exemples

Ce qui est à l'antenne (public) :

```bash
curl -s "https://<station-host>/api/v2/now-playing"
```

Le programme de la semaine en UTC (public) :

```bash
curl -s "https://<station-host>/api/week-info?timezone=UTC"
```

Les lignes d'un épisode (public) :

```bash
curl -s "https://<station-host>/api/show-tracks?instance_id=12345"
```

L'historique de diffusion d'une journée (public) :

```bash
curl -s "https://<station-host>/api/item-history-feed?start=2026-11-05%2000:00:00&end=2026-11-05%2023:59:59"
```

Un point d'accès protégé avec la clé (depuis la machine de la station) :

```bash
curl -s -H "Authorization: Api-Key <key>" "https://<station-host>/api/v2/files?limit=5"
```

---

## 7. Questions fréquentes

**Puis-je publier l'adresse de l'API sur le site de la station ?**
Oui, pour les points d'accès publics.  Ils ne contiennent que le
programme et les crédits des titres.

**Pourquoi `/api/version` répond-il 401 ?**  Ce point legacy ne fait
pas partie de l'ensemble public ; utilisez `/api/v2/version`.

**L'API dit-elle quand un DJ est en direct ?**  `live-info-v2` →
`sources` et `now-playing` → `source`.

**Y a-t-il une limite de débit ?**  Pas sur les points d'accès publics.
Une page qui interroge `live-info-v2` toutes les quelques secondes pour
chaque visiteur convient à un site de station ; un robot qui récupère
`week-info` (environ 270 Ko) en boucle serrée, non — mettez un cache
devant.

> **Comment ça marche sous le capot.**  Les actions legacy sans clé
> sont listées dans `ApiController::$ignoreAuth` ; elles vérifient
> quand même l'interrupteur
> (`Application_Model_Preference::GetAllow3rdPartyApi`).  La liste
> blanche des pistes est `WidgetHelper::PUBLIC_TRACK_FIELDS`
> (`restrictLiveInfo`), celle des émissions `PUBLIC_SHOW_FIELDS`.  Les
> permissions de l'API v2 sont dans `rastatime_api/permissions.py`
> (`IsSystemTokenOrUser` : Api-Key ou utilisateur connecté avec les
> permissions Django de son rôle ; `internal_only` pour les vues
> simples appelées par le playout).  Les vues du schéma portent
> `IsAuthenticated`.  `now-playing` lit dans `cc_schedule` la ligne qui
> couvre *maintenant* et demande au playout `/source-state` les
> indicateurs DJ.  Voir ARCHITECTURE §23.90 et §23.91.
