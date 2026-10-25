# Users and Roles

> **Where you are in the manual.** This chapter is the permissions
> reference for the rest of the manual: whenever another chapter says
> "Program Managers and Admins only", the matrix in §2 is the full
> picture.  It describes the state after the role audit of 2026-10-25.

RASTATIME knows four roles.  Every account has exactly one of them, and
the server checks it on every request - hiding a button is only a
convenience, the server refuses the action anyway.  This chapter covers:

1. The four roles.
2. The permission matrix.
3. Managing users (Settings → Users).
4. Your own profile (My Profile).
5. Live dial-in logins.
6. API access.
7. Sessions and protection against abuse.
8. Login protection.
9. Typical role assignment and frequently asked questions.

---

## 1. The four roles

| Role | Typical user | In one sentence |
|---|---|---|
| **Guest** | Reception screen, visitor | Sees the dashboard and the calendar, changes nothing. |
| **DJ** | A presenter | Works with tracks: uploads, own playlists and smart blocks, fills the shows they host. |
| **Program Manager** | Programme co-ordination | Runs the programme: all shows, all content, webstreams, Line-Ins, podcasts, Auto DJ, show templates, widgets. |
| **Admin** | Station technician | Everything, plus the station settings and the user accounts. |

Each role includes everything the role above it in the table may do.

**The installation account `admin`** is an Admin like any other, but it
cannot be deleted - not on Settings → Users and not through the API.
Admins can create further Admins.

**The former Super Admin role** (from Airtime) was retired on
2026-10-25: an account of that type becomes an Admin (database migration
0073), and external logins (LDAP / FreeIPA, header authentication) in the
super-admin group sign in as Admins.

> **How it works under the hood.** The role is the one-letter
> `cc_subjs.type` (G, H, P, A; S is retired).  The coarse rules sit in
> `application/configs/ACL.php`; the finer ones (owner of a file, host
> of a show, Program Manager or higher) are checked in the controllers.
> The audit and its findings: `docs/operator/ROLE_AUDIT_2026-10.md`.

---

## 2. The permission matrix

✓ = allowed, – = not allowed.  "Own" means the user is the owner of the
object (they uploaded or created it); "hosted" means the user is a host
of the show.

| Area | Guest | DJ | Program Manager | Admin |
|---|:---:|:---:|:---:|:---:|
| **Account** | | | | |
| Edit own profile (name, e-mail, password, language, time zone) | ✓ | ✓ | ✓ | ✓ |
| Manage other users (Settings → Users) | – | – | – | ✓ |
| **Dashboard and live sources** | | | | |
| See Now Playing and the scheduled shows | ✓ | ✓ | ✓ | ✓ |
| See the Auto DJ status in the header | ✓ | ✓ | ✓ | ✓ |
| Switch or disconnect a live source (Master / Show) | – | during a hosted show | ✓ | ✓ |
| Cancel the running show | – | – | ✓ | ✓ |
| **Calendar** | | | | |
| View the calendar | ✓ | ✓ | ✓ | ✓ |
| Create, edit, move, resize, delete, cancel shows | – | – | ✓ | ✓ |
| Clear a show's content, teasers, show templates in the show dialog | – | – | ✓ | ✓ |
| Schedule content into a show | – | hosted shows | ✓ | ✓ |
| **Library** | | | | |
| View the library (tracks, playlists, smart blocks, podcast list) | – | ✓ | ✓ | ✓ |
| Upload tracks | – | ✓ | ✓ | ✓ |
| Edit metadata, cue points, delete tracks | – | own | ✓ | ✓ |
| Change the owner of a track | – | – | – | ✓ |
| Create playlists and smart blocks | – | ✓ | ✓ | ✓ |
| Edit, shuffle, delete playlists and smart blocks | – | own | ✓ | ✓ |
| See, use and edit webstreams and Line-Ins | – | – | ✓ | ✓ |
| Subscribe to, edit and delete podcasts; episodes | – | – | ✓ | ✓ |
| Publish to the station podcast (My Podcast) | – | – | ✓ | ✓ |
| **Analytics** | | | | |
| Listener statistics | – | ✓ | ✓ | ✓ |
| Playout history: view | – | hosted shows | ✓ | ✓ |
| Playout history: add, edit, delete entries | – | hosted shows | ✓ | ✓ |
| History templates | – | – | – | ✓ |
| **Widgets** | | | | |
| Widgets pages (embed codes, widget settings) | – | – | ✓ | ✓ |
| **Settings** | | | | |
| Auto DJ | – | – | ✓ | ✓ |
| Show Templates page | – | – | ✓ | ✓ |
| Station default language (first-run dialog) | – | – | ✓ | ✓ |
| General, Users, Track Types, Streams, Local Machine, Import / Export, Backup, Status | – | – | – | ✓ |

What the roles see differently:

- **Guests** get the dashboard and the calendar.  Opening the library
  shows "You don't have permission to view the library."; the **New**
  menu, **Upload** and the **Widgets** menu are not offered.
- **DJs** see every track, playlist and smart block of the station, but
  change only their own.  They schedule into the shows they host - any
  track, playlist or smart block, also those of others.  Webstreams and
  Line-Ins are hidden from them (library tabs, **New** menu); they cannot
  be added to playlists or shows by a DJ.  In the playout history a DJ
  gets the *Show Summary* of their own shows and can add, edit and
  delete entries there.  The podcast list is read-only for them, and
  the **Widgets** menu is not offered.
- **Program Managers** run the programme, use the **Widgets** pages and
  open three settings pages: **Auto DJ**, **Show Templates** and My
  Profile.  Show templates are saved and applied in the show dialog and
  renamed or deleted on Settings → Show Templates.
- **Admins** additionally manage the station: settings, streams, sound
  card, users, track types, backup, import / export, system status.

Changing the first-run language dialog sets everyone's **own** language
and time zone; the station-wide default language is only changed when a
Program Manager or Admin confirms it.

---

## 3. Managing users

Settings → **Users** (Admins).

### Creating and editing a user

**New** opens the user dialog; a click on a row opens the same dialog
for that user.

| Field | Notes |
|---|---|
| **Username** | The login name. |
| **Password** / **Verify password** | Required for a new user.  When editing, leave the placeholder to keep the password. |
| **First name**, **Last name** | Shown in the user lists and as show host. |
| **E-mail** | Contact address. |
| **Mobile phone**, **Skype**, **Jabber** | Optional contact fields. |
| **User type** | Guest, DJ, Program Manager or Admin. |

The row of the account `admin` has no delete icon.

### Deleting a user

The delete icon in the user list removes the account.  Tracks the user
owned are **handed over** to the first Admin - they stay in the
library.  You cannot delete your own account, and the account `admin`
cannot be deleted.

There is no "deactivated" state: to take someone's access away, delete
the account or set a new password; to leave read access only, change
the type to Guest.

### Users in Import / Export

Settings → Import / Export carries the users as `users.csv` - without
passwords; on import a password is set only for new accounts.  See
[Import / Export](./IMPORT_EXPORT.md).

---

## 4. Your own profile

Settings → **My Profile** - for every role, including Guests.

You change your first and last name, e-mail, password, the contact
fields, your **interface language** and your **time zone**.  The user
name is fixed.  The page always saves the account you are logged in
with; other accounts are edited by an Admin under Settings → Users.

---

## 5. Live dial-in logins

A DJ broadcasting live (BUTT, Mixxx, …) connects to the station's
live input and logs in with one of:

| Login | Accepted when |
|---|---|
| The DJ's own RASTATIME user name and password | The DJ is a host of the show on air, and the show uses *RASTATIME Authentication* (show dialog → *Live Stream Input*). |
| The show's custom login (*Use Custom Authentication* in the same section) | That show is on air. |
| The Master source login (Settings → Streams) | Always; overrides the running show. |

The custom live password of a show is shown in the show dialog to
Program Managers and Admins only.  Ports and mount names are listed in
[Streams](./STREAMS.md).

---

## 6. API access

There are **no personal API keys**.

- **Services** (playout, analyzer, scripts on the station machine) use
  the station's API key from `config/libretime.conf`
  (`Authorization: Api-Key …`).  Treat it like a password.
- **People** can use the REST API v2 (`/api/v2/`) with their own user
  name and password; they get the permissions of their role.
- A few internal endpoints (Line-In devices, sound card, preflight
  warnings, stream status, the DJ login check) answer only the station
  machine itself or a caller with the API key.

---

## 7. Sessions and protection against abuse

- **Session.** A login lasts until the browser is closed or until the
  session has seen no request for a while (PHP `session.gc_maxlifetime`,
  24 minutes on the studio machine).  An open RASTATIME tab keeps its
  session alive with its background updates.  Logging in from several
  browsers at the same time is possible.
- **Cookie.** The session cookie is `Secure`, `HttpOnly` and
  `SameSite=Lax`: other websites cannot use your login for requests in
  the background, and scripts on the page cannot read it.
- **Request token.** Every change made through the interface carries a
  token bound to your session.  The server compares it; a request
  without the token is logged (`CSRF monitor` in `logs/legacy.log`) and,
  once the check is switched to enforcing, refused.  A tab left open for
  more than a week may need a reload (F5) before saving.

---

## 8. Login protection (since 2026-10-06)

The login page brakes repeated failures - a necessity since the web
interface is reachable from the internet.

| Scope | Rule | Effect |
|---|---|---|
| Per source address | 10 failed logins within 15 minutes | the address waits 15 minutes; every attempt in that time is answered with "Too many failed login attempts. Please try again in N minute(s)." (HTTP 429), no password is checked |
| Per user name | 20 failed logins within 60 minutes | the name waits 5 minutes - deliberately short, so that somebody hammering an administrator's name from many addresses cannot lock the administrator out for good |
| DJ dial-in (harbor) | 5 rejected logins from one address within 10 minutes | the address is refused for 15 minutes without asking the web application |

A successful login clears the counters of its address and its name.  The
thresholds live in `constants.php` (`RASTATIME_LOGIN_*`) and in the
playout (`RejectThrottle`); blocked attempts are logged with the address
(`logs/legacy.log`, `logs/playout-stdout.log`).

**Seeing and lifting blocks.**  Settings → System Status → *Blocked
addresses* lists every layer (web login per address and per user, DJ
dial-in, firewall watcher) with the failure count and the remaining
minutes, and an **Unblock** button clears the entry on all layers - for
the DJ who calls because the wrong password was saved in their client.
The same list is available in PowerShell: `infra\scripts\rt-blocks.ps1`
(`-Unblock <address>` or `-Unblock user:<login>`).  A DJ who dials in
**before** the show starts is refused but never counted: only a wrong
password counts.  Persistent internet scanners are blocked for 24 hours
in the Windows Firewall by a watcher task (every 5 minutes; 50 refused
requests in 60 minutes, 3 typical scanner paths, or 5 wrong DJ passwords)
and appear in the same list.  A "not signed in" answer (401) never
counts: it is what a browser tab with an expired session gets for its
background polls, and since 2026-10-07 such a tab stops polling on the
first one.

**Allowed addresses (since 2026-10-08).**  Next to **Unblock** every
blocked address has **Allow**: it is unblocked on every layer and put on
the *Allowed addresses* list below, where you can also add an address or
a network in CIDR notation by hand (`203.0.113.0/24`) and remove entries.
An allowed address is never braked by the web login, never throttled by
the DJ dial-in and never blocked by the firewall watcher; addresses of
the studio network are exempt anyway.  Keep the list short - it switches
every brake off for that address - and prefer a network for a home
connection whose address changes with the provider.  The list is kept
in the database and mirrored to `config\allowlist.txt` for the playout
and the watcher.

> **If you are locked out yourself:** wait the minutes shown, or ask a
> colleague on another address.  In an emergency the counters sit in the
> tables `cc_login_attempts` (per address) and `cc_subjs.login_attempts`
> (per user).

---

## 9. Typical role assignment and frequently asked questions

### Typical assignment

| Station | Accounts |
|---|---|
| One person | the `admin` account (Admin); optionally a Guest for a lobby screen |
| Community station | `admin` plus a personal Admin account for the technical lead, one Program Manager per programme area, one DJ account per presenter, optionally a Guest |
| Larger station | additionally one or two Admins for technical operations |

One account per real person: shared accounts make it impossible to tell
who changed what.

### "A DJ cannot find a webstream or a Line-In."

Intended: DJs work with tracks only.  A Program Manager adds the
webstream or Line-In to the show or to a playlist.

### "A DJ cannot edit their show's time or description."

Shows are created and edited by Program Managers and Admins.  DJs fill
the shows they host and can take their live source on and off air while
their show runs.

### "A user needs both DJ and Program Manager rights."

Give them the Program Manager role - it includes everything a DJ may do.

### "Can a user have two roles?"

No, exactly one per account.

### "The password of an Admin is lost."

Another Admin sets a new one under Settings → Users - one reason to keep
two Admin accounts.  If no Admin can log in any more, the password has
to be reset in the database (table `cc_subjs`, column `pass`, MD5 of the
new password) - see
[`docs/operator/CRASH_RECOVERY.md`](../operator/CRASH_RECOVERY.md).

---

## Where to go next

* [Settings](./SETTINGS.md) - every settings page.
* [Dashboard](./DASHBOARD.md) - live sources and the running show.
* [Import / Export](./IMPORT_EXPORT.md) - users as `users.csv`.
* [Streams](./STREAMS.md) - live dial-in ports and the Master login.
