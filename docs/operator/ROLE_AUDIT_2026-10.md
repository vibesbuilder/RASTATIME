# Role audit "who may do what" (2026-10-25)

BACKLOG item "Benutzergruppen-Audit: Wer darf was?" (operator 2026-09-17,
started 2026-10-25).  Step 1 of the agreed procedure: the **actual**
permissions (this document), then the **target** matrix with the operator,
then closing the gaps, then the manual (USERS_AND_ROLES ×4).

Method: static reading of the legacy ACL (`application/configs/ACL.php`),
the ACL plugin, every controller reachable by Guest (G) or DJ (H), the
REST module and the Django API v2 routes; key findings re-checked by hand
and, where it changes nothing, by a request from the LAN address
192.168.1.64 (= not loopback).  **✔** = verified by hand / by request,
**◦** = from the code survey, not re-checked line by line.

Accounts on 2026-10-25: 2 Admin, 1 Program Manager, 4 DJ, 2 Guest.

## 1. How access is decided today

* **Roles** G < H (DJ) < P (Program Manager) < A (Admin) < S (Super
  Admin), each inherits the previous one.
* **Controller ACL** (`ACL.php`): G reaches index, login, schedule,
  showbuilder, dashboard, webstream, setup, embeddablewidgets, api, feeds,
  manual, audiopreview, render, locale, `user/edit-user` and GET on the
  REST resources.  H adds library, playlist, plupload, podcast, REST
  write methods, playouthistory, listenerstat, usersettings.  **P adds
  nothing** - every extra right of a Program Manager is an in-code check
  (`isAdminOrPM()`, `isUserType([S, A, P])`).  A adds preference (all
  Settings pages incl. Backup, Local Machine, Streams), user, tracktype,
  systemstatus, importexport, linein, playouthistorytemplate.
* **No ACL at all** for index, login, api, error, locale, embed, feeds
  (and the non-existing upgrade/auth): reachable anonymously.
* **In-code checks** decide the rest (show ownership, host of show,
  owner of a file).  Several write paths have none - see 3.
* **CSRF**: only REST write requests are checked centrally
  (`Acl_plugin.php`); the hidden `csrf` field of the other forms is
  required but never compared (exceptions: plupload, teaser actions,
  Preference, Systemstatus, Import/Export).  The session cookie is
  `Secure; HttpOnly` without `SameSite` ✔.
* **Django API v2** (`/api/v2/`, proxied publicly): the DRF view sets use
  role permissions (G read, H own objects, P/A all; Basic auth or
  Api-Key; wrong password = 403, counted by the firewall watch) ✔.  The
  RASTATIME function views outside DRF bring their own checks - or none
  (see 2).

## 2. Immediate security findings (independent of the target matrix)

**Status:** S1-S7 fixed 2026-10-25 (package 1); the Django part of S3/S4 is
live after the API restart.

| # | Finding | Who | Status |
|---|---|---|---|
| S1 | **Account takeover**: `user/edit-user` saves the user whose id is POSTed (`cu_user_id`), not the logged-in one - any account, even a Guest, can set the password and e-mail of any other account incl. Admin (`UserController.php:135`) | G | ✔ |
| S2 | **API key bypassed by any session**: `ApiController::checkAuth()` accepts every logged-in identity, so a Guest can call all `api/*` actions meant for the API key - e.g. `get-stream-setting` returns the Icecast source/admin passwords of all outputs; ◦ `reload-metadata-group` can hide the library or repoint files (path check by prefix only) | G | ✔ (◦ details) |
| S3 | **Line-In API without any authentication**, public via `/api/v2/audio/linein[/<id>]`: list (tested: 200 from the LAN address), create, change, delete (code) | anonymous | ✔ |
| S4 | **Sound-card setting without authentication**: `POST /api/v2/audio/soundcard-settings` changes the playout's audio output device; `POST /api/v2/preflight/warnings/replace` replaces the dashboard warnings; `audio/devices`, `streams/outputs`, `preflight/warnings` are readable | anonymous | ✔ (code + GET) |
| S5 | **Icecast `/main` and `/show`** still use URL auth `public/icecast-source-auth.php` (public file) with **built-in fallback logins** `source/master-secret` and `source/show-secret`, valid next to the rotated passwords; Icecast listens on all interfaces, Windows firewall allows 8000 from anywhere.  Both mounts and both PHP files had no traffic in 16 days (DJs use the Harbor on 8001) | network | ✔ |
| S6 | **Custom live passwords readable**: `populate-show-form` renders every show's custom DJ login and password into the (disabled) form for any role (`renderPassword`) | G | ✔ |
| S7 | **Deleting a track with empty `artwork`** globs `D:/stor\*` and unlinks every *file* directly in the storage root (`CcFiles::deletePhysicalFile`); 6,332 tracks have `artwork = ''`.  Today the root holds only folders, so it only throws ("Is a directory" - the warnings of 24./25.10.) | any deleter | ✔ |

## 3. Role gaps (actual > intended)

**Status:** R1-R3, R5-R11 and R13 closed 2026-10-25 (package 2) along the
target matrix in §4; R4 left on purpose (`setIsScheduled` only clears the
flag when the file has no future row - self-correcting); R12 is package 3:
phase 1 live 2026-10-25 (SameSite=Lax + HttpOnly cookie, `X-CSRF-Token`
on every jQuery write, central compare in `Acl_plugin` that only logs
"CSRF monitor" lines); phase 2 (enforce, 403, "CSRF refused") live
2026-10-27 - the monitor log showed one remaining sender, the seven widget
settings forms (plain form posts), which carry the `csrf` field since.
Found during the operator's UI test (actual < target, open question):
guests cannot load the dashboard library - `library`, `usersettings` and
the podcast list were never in their ACL (403), while the target matrix
says "Library: view - Guest ✓".
Probe `C:/Temp/optd/role_audit_p2_probe.php` (read-only, 203 checks).

| # | Gap | Who can | Status |
|---|---|---|---|
| R1 | Clear the content of any show (`schedule/clear-show`, linked shows: all future instances) | G | ✔ |
| R2 | Create, overwrite, rename, delete show templates | G | ◦ |
| R3 | Station default language (`setup/setup-language-timezone`), all embeddable-widget settings incl. cover upload | G | ◦ |
| R4 | Flip `is_scheduled` on files (`schedule/update-future-is-scheduled`) | G | ◦ |
| R5 | Change other users' playlists and smart blocks (items, cues, fades, criteria, shuffle) - no ownership check in `PlaylistController::getPlaylist` | H | ✔ |
| R6 | Change any file's metadata incl. `owner_id`, cue points, expiry (`library/edit-file-md` POST, REST `media` PUT, `playouthistory/update-file-item`) - then delete it as its new owner; ◦ REST PUT `full_path`/`artwork` + delete may unlink files outside the library | H | ◦ |
| R7 | Replace or delete any show's logo (REST `show-image`) | H | ◦ |
| R8 | Edit/delete any podcast incl. the station podcast and its episodes; publish any user's file into the station podcast | H | ◦ |
| R9 | Create/edit/delete any playout-history entry (check commented out in `HistoryService`) | H | ◦ |
| R10 | Delete any Line-In source through the library (`library/delete`, type linein) - the Line-In page itself is Admin-only | H | ◦ |
| R11 | A show host keeps scheduling rights after being demoted to Guest (`canSchedule` ignores the user type) | G (listed host) | ◦ |
| R12 | No working CSRF protection on non-REST writes (schedule, showbuilder, library, playlist, webstream, history, dashboard, user, setup) - with S1 a cross-site page could change a logged-in admin's password in browsers without SameSite=Lax default | cross-site | ✔ (no compare) |
| R13 | Super Admin counted as non-admin when deleting webstreams (`Webstream.php:108`) | S (too little) | ◦ |

Correctly enforced (sample): show create/edit/move/resize/delete/cancel
and teasers need P+; scheduling content needs host-of-show or P+; delete
of files, playlists, blocks needs owner or P+; webstreams owner or P+;
all Settings pages, users, backup, Import / Export, Line-In page Admin
only; backup/storage API routes refuse anonymous calls (403).

## 4. Proposed target matrix (for the operator)

| Area | Guest | DJ | Program Manager | Admin |
|---|---|---|---|---|
| Own profile (password, e-mail, language) | ✓ | ✓ | ✓ | ✓ |
| Other users | – | – | – | ✓ |
| Calendar: view | ✓ | ✓ | ✓ | ✓ |
| Shows: create/edit/move/delete/clear, templates, teasers | – | – | ✓ | ✓ |
| Schedule content into a show | – | own shows | all | all |
| Switch / disconnect live sources | – | own running show | ✓ | ✓ |
| Library: view, preview | ✓ | ✓ | ✓ | ✓ |
| Upload; edit/delete files, playlists, blocks | – | own | all | all |
| Webstreams, Line-Ins: see, add to playlists/shows, edit | – | – | ✓ | ✓ |
| Show logos | – | own shows? | ✓ | ✓ |
| Podcasts (subscriptions, episodes) | – | own? | all | all |
| Station podcast / publish | – | – | ✓ | ✓ |
| Playout history: view / edit | – | edit in shows they host | edit | edit |
| Line-In: use in shows / manage devices | – | – | ✓ | ✓ |
| Widgets, station language | – | – | – ? | ✓ |
| Settings, Backup, Streams, Users, Track Types, System Status, Import / Export | – | – | – | ✓ |

Operator answers 2026-10-25: DJs change no show logos (own shows
included) and manage no podcasts; podcasts, widgets, station language and
Line-In devices are for Program Managers and Admins.  Follow-up the same
day: DJs work with tracks only - webstreams and Line-Ins are neither shown
to them nor addable to playlists or shows; DJs create, edit and delete
playout-history entries in the shows they host.  (The rows above show the
agreed state; guests have no history page.)

## 5. Remediation packages (proposal)

1. **Immediate (S1-S7), ~3-4 h, live at once except where noted**:
   edit-user only for the logged-in account (admins use the user
   dialog); `checkAuth()` without session fallback, with a short
   allow-list of read actions the UI really calls with a session;
   Line-In / preflight-replace Django views: Api-Key required (PHP and
   PLAYOUT already call locally - check they send the key); sound-card
   page through a PHP proxy (Admin) instead of browser → Django;
   Icecast PHP files: loopback only, fallback logins removed (mount
   removal + firewall: package 4); custom password not rendered for
   non-P; artwork glob only for a non-empty artwork path inside the
   library.
2. **Role gaps R1-R11, R13, ~1 day**: role/ownership checks in the named
   actions, following the agreed target matrix.
3. **CSRF R12, ~0.5-1 day**: `SameSite=Lax` on the session cookie at
   once (small); then a central token compare for all non-GET legacy
   requests (needs the token in every AJAX call - a careful rollout).
4. **Icecast**: remove the unused `/main` and `/show` mounts (or their
   URL auth) from `config/icecast.xml` (Icecast restart, quiet window);
   firewall rule 8000 limited to what really needs it.
   **Done 2026-10-25:** mounts removed from `config/icecast.xml` (backup
   `icecast.xml.pre-pkg4-backup`; config accepted by a throwaway Icecast
   2.5.0 on port 18000) and `.example`; `public/icecast-source-auth.php`,
   `public/icecast-auth.php` and `api/icecast-listener-allow` (with a
   hard-coded admin/admin bypass) deleted.  Icecast's access log since
   2026-09-29: every client is 127.0.0.1 (Apache, playout) except two LAN
   test requests, so nothing outside needs 8000.  Operator steps done the
   same evening: Icecast restarted 19:00:48 (all six Liquidsoap sources
   back after 3 s, streams via `/stream/` 200, `/main` 404); the inbound
   rules "RASTATIME Icecast" (port 8000, any remote) and "icecast" (2x,
   program rule) disabled.
5. **Manual** USERS_AND_ROLES ×4 after 2.  **Done 2026-10-25:** chapter
   rewritten in EN/DE/FR/ES from this audit (matrix in §2 of the
   chapter); role statements in SETTINGS, LINE_IN, CALENDAR, LIBRARY,
   SHOW_TEMPLATES and ANALYTICS corrected in all four languages.

Follow-up (operator go, 2026-10-25): the Super Admin role is retired
(migration 0073, S -> A; four roles), and the installation account
`admin` cannot be deleted (user page and API v2).
