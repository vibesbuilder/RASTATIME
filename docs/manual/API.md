# API

> **Where you are in the manual.** This chapter is for the person
> who wants to read RASTATIME's data from outside — a station
> website, a partner site, a monitoring script — or who wants to
> know what the system exposes to the public.  It lists the public
> endpoints, explains the switch that turns them on, and says what
> the API key is for and why it must never leave the station.  For
> the ready-made iframe widgets see [Public Embed Widgets](./WIDGETS.md).

RASTATIME has two HTTP interfaces that grew at different times:

| Interface | Base path | Format | Used by |
|---|---|---|---|
| **REST API v2** | `/api/v2/` | JSON, OpenAPI schema, Swagger UI | The playout, the analyzer, the Settings pages, scripts |
| **Legacy API** | `/api/<action>` | JSON (some JSONP), images, M3U | The embed widgets, the dashboard, older integrations |

Both answer on the station's web address (`https://<station-host>/…`).
Everything below applies to the live station; a development
installation behaves the same.

---

## 1. Who may read what

| Access | What it covers |
|---|---|
| **Public, no login** | The read-only endpoints of the legacy API listed in section 3, as long as **Settings → General → Public RASTATIME API** is on; plus `version`, `info`, `now-playing` and the song-request search/submit of API v2. |
| **Login (session or basic auth)** | Browsing `/api/v2/` in a browser, the OpenAPI schema and the Swagger UI.  A logged-in account sees what its role allows (see [Users and Roles](./USERS_AND_ROLES.md)). |
| **API key** | Every other endpoint: writing, internal state, file lists, stream settings.  One key for the whole station, full access. |

Everything that is not public answers `401` or `403` without
credentials.  There is no rate limit on the public read endpoints;
only the song-request endpoints are throttled per listener.

---

## 2. The switch: Public RASTATIME API

**Settings → General → Public RASTATIME API** (on / off).

- **On:** the read-only legacy endpoints answer without a key.  This
  is what the embed widgets need — the now-playing, weekly programme
  and player widgets read `live-info`, `track` and `show-logo`.
  Turning the switch off breaks the widgets on your website.
- **Off:** the same endpoints require the API key.  Only choose this
  if you use no widgets and no external site reads the programme.

The switch does not touch API v2 and does not open anything that
writes.

---

## 3. Public read endpoints (legacy API)

All of them return JSON unless noted.  Times are in the station's
time zone unless you pass `timezone=` (a tz database name such as
`Europe/Berlin`, or `UTC`).

| Endpoint | Parameters | Returns |
|---|---|---|
| `/api/live-info-v2` | `days` (default 2), `shows` (default 5), `timezone` | What is on air: `shows` (previous / current / next), `tracks` (previous / current / next), `sources` (live DJ, master DJ, scheduled play), `station`. |
| `/api/live-info` | `type` (`endofday` or interval), `limit` (default 5), `timezone` | The older shape of the same data: `currentShow`, `nextShow`, `current`, `next`, `previous`, `schedulerTime`. |
| `/api/week-info` | `timezone` | The programme of this week and next, one list per weekday (`monday` … `nextsunday`), each show with name, times, description, image, url. |
| `/api/station-metadata` | — | Station name, description, logo, locale, time zone and the list of streams. |
| `/api/shows` | `show_id` (optional) | All shows, or one: id, name, description, genre, url, colours, linked flag. |
| `/api/show-schedules` | `show_id` (required), `start`, `end` (`YYYY-MM-DD HH:MM:SS`) | The episodes of one show in the range. |
| `/api/show-tracks` | `instance_id` (required) | The rows of one episode: position, title, artist, length, start. |
| `/api/item-history-feed` | `start`, `end`, `instance_id` (optional) | The playout history: what was played when, with title, artist and episode. |
| `/api/show-history-feed` | `start`, `end`, `user_id` (optional) | The shows that aired in the range. |
| `/api/track?id=<file id>&return=<kind>` | `return` = `artwork`, `artwork-32`, `artwork-64`, `artwork-data` | The cover image of a track (JPG). |
| `/api/show-logo?id=<show id>` | — | The image of a show. |
| `/api/track-types` | — | The track types configured in the library. |
| `/api/stream-m3u` | — | An M3U playlist file with the station's streams. |

**What a track exposes.**  The track metadata in `live-info` and
`live-info-v2` is deliberately limited to the credit information a
listener may see: title, artist, album, year, genre, language, length,
track and disc number, composer, conductor, lyricist, original artist,
label, copyright, ISRC, bpm, mood, the info / buy / artist URLs, the
artwork reference and the track type.  File paths, owners, checksums,
comments, lyrics and import details are never sent.  `/api/shows`
likewise omits the autoloading and intro / outro playlist ids.

---

## 4. Public endpoints of API v2

| Endpoint | Returns |
|---|---|
| `GET /api/v2/version` | `{"api_version": "…"}` |
| `GET /api/v2/info` | `{"station_name": "…"}` |
| `GET /api/v2/now-playing` | What is on air, read from the schedule (see below). |
| `GET /api/v2/song-requests/search?q=<text>` | Tracks a listener may request: id, title, artist, album, has_artwork. |
| `POST /api/v2/song-requests` | Submits a request (`file_id`, optional `listener_label`).  Throttled per listener; see [Song Requests](./SONG_REQUESTS.md). |

**now-playing** always answers `200`:

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

`type` is `file`, `webstream` or `linein`; `source` is `scheduled`,
`live_dj` or `master_dj`.  When nothing from the schedule is on air,
`is_playing` is `false`, `item` and `started_at` are `null`, and `show`
still names the running show.  Times are UTC (ISO 8601).

---

## 5. Using the API with credentials

**In the browser.**  Log in to RASTATIME, then open
`https://<station-host>/api/v2/` for the browsable API and
`https://<station-host>/api/v2/schema/swagger-ui` for the Swagger UI
(the raw OpenAPI schema is at `/api/v2/schema`).  Both need the login;
without it they answer `403`.

**From a script.**  Send the station's API key in the `Authorization`
header:

```
Authorization: Api-Key <key>
```

The key is the `api_key` under `[general]` in
`C:\rastatime\config\rastatime.conf`.  The legacy API also accepts it
as `?api_key=<key>`.

> **Never hand the key to a third party.**  There is exactly one key
> and it grants full access: schedule pushes, file lists, stream
> passwords, settings.  A partner site that only needs the programme
> uses the public endpoints of section 3 — they need no key.  If a
> partner needs more than reading, that is a request for a read-only
> client token (see BACKLOG), not for the station key.

---

## 6. Examples

What is on air (public):

```bash
curl -s "https://<station-host>/api/v2/now-playing"
```

This week's programme in UTC (public):

```bash
curl -s "https://<station-host>/api/week-info?timezone=UTC"
```

The rows of an episode (public):

```bash
curl -s "https://<station-host>/api/show-tracks?instance_id=12345"
```

The playout history of one day (public):

```bash
curl -s "https://<station-host>/api/item-history-feed?start=2026-11-05%2000:00:00&end=2026-11-05%2023:59:59"
```

A protected endpoint with the key (from the station machine):

```bash
curl -s -H "Authorization: Api-Key <key>" "https://<station-host>/api/v2/files?limit=5"
```

---

## 7. Frequently asked

**Can I publish the API address on the station website?**  Yes, for
the public endpoints.  They only contain the programme and the credit
data of the tracks.

**Why does `/api/version` answer 401?**  That legacy endpoint is not
part of the public set; use `/api/v2/version`.

**Does the API tell me when a DJ is live?**  `live-info-v2` → `sources`
and `now-playing` → `source`.

**Is there a rate limit?**  Not on the public read endpoints.  A page
that polls `live-info-v2` every few seconds for every visitor is fine
for a station site; a crawler fetching `week-info` (about 270 KB) in a
tight loop is not — put a cache in front of it.

> **How it works under the hood.**  The legacy actions that answer
> without a key are listed in `ApiController::$ignoreAuth`; they still
> check the switch (`Application_Model_Preference::GetAllow3rdPartyApi`).
> The track allow-list is `WidgetHelper::PUBLIC_TRACK_FIELDS`
> (`restrictLiveInfo`), the show allow-list `PUBLIC_SHOW_FIELDS`.  API v2
> permissions live in `rastatime_api/permissions.py`
> (`IsSystemTokenOrUser`: Api-Key or a logged-in user with the role's
> Django permissions; `internal_only` for the plain views the playout
> calls).  The schema views carry `IsAuthenticated`.  `now-playing`
> reads `cc_schedule` with the row that covers *now* and asks the
> playout's `/source-state` for the DJ flags.  See ARCHITECTURE
> §23.90 and §23.91.
