# Users and Roles

> **Where you are in the manual.** This chapter is the
> permissions reference for every feature in the rest of the
> manual. Every "you cannot do X because you are not an
> Admin" footnote in another chapter resolves against the
> matrix below.

RASTATIME has five user roles and a single permission system.
Every action — opening a page, dragging a track, saving a
show, restarting a service — is checked against the user's
role on the server side.

This chapter covers:

1. The five roles + what each can do.
2. Managing users (create, edit, password reset, deactivate).
3. The full permission matrix.
4. API key management.
5. Best-practice role assignment for typical stations.

---

## 1. The five roles

| Role | Symbol | Typical user | One-line summary |
|---|---|---|---|
| **Guest** | G | Reception display / lobby | Read-only Dashboard. |
| **DJ** | H | Each individual host | Own shows + own files only. |
| **Program Manager** | P | Programme co-ordinator | All calendar + library, no station settings. |
| **Admin** | A | Station technical admin | Everything except creating other Admins. |
| **Super Admin** | S | Station owner | Everything including creating Admins. |

A user has exactly **one** role. The role is set on the
Manage Users page and is the only thing controlling what the
UI lets the user do.

### Why role-based and not capability-based?

Role-based is the simplest model that covers 99 % of station
needs. Capability-based (granular per-feature toggles) is
flexible but creates exponentially more configurations to
test. RASTATIME chose roles because:

- Operators understand "this user is a DJ".
- The role boundary maps clearly to organisational roles.
- Permission audits ("who can do X?") are a single column
  scan.

> **How it works under the hood.** Roles live in
> `cc_subjs.type` as a single character (G / H / P / A / S).
> Permission checks happen in `application/configs/ACL.php`
> via Zend_Acl. Every controller action declares its
> required resource; ACL.php whitelists per-role access.
> The web UI hides menu items the user cannot reach, but
> the back-end re-checks every action so an attacker
> cannot bypass by URL-crafting. See ARCHITECTURE §11.

---

## 2. Per-role capabilities

### Guest (G)

The smallest role. Used for:

- Read-only displays in public areas (reception, café area)
  showing what's currently on air.
- Listeners who should be able to see the upcoming schedule
  but not interact.

Can:

- Log in.
- See the Dashboard's Now-Playing + Coming Up Next.
- See the public Calendar (read-only).

Cannot:

- Access the Library, Settings, or any administrative menu.
- See listener counts.
- See per-show fill percentages.
- Use Live Source controls.

### DJ (H)

Per-host account. The role most users hold.

Can:

- Everything Guest can do.
- Upload tracks (owned by themselves).
- Create smart blocks and playlists (owned by themselves).
- Schedule their *own* tracks / blocks / playlists into
  their *own* shows.
- Edit shows where they are the host.
- See and download their own recordings.

Cannot:

- Create shows (Program Managers must create the show; the
  DJ fills it).
- Edit shows where someone else is the host.
- See or use other DJs' tracks / blocks / playlists.
- Change station-wide settings (Streams, Local Machine,
  Auto DJ, Show Templates, Users).
- Restart services.

> **The DJ vs Program Manager split.** Many stations
> conflate the two roles. RASTATIME deliberately separates
> them: DJs are content creators; Program Managers are
> schedule owners. A station with five DJs has one Program
> Manager (or a rotating role).

### Program Manager (P)

The schedule owner.

Can:

- Everything DJ can do.
- Create / edit / delete *any* show, regardless of host.
- See and use *any* DJ's tracks / blocks / playlists.
- Use Show Templates (create / apply / rename / delete).
- Use Auto DJ (configure + enable / disable).
- Manage Webstreams library entries.
- Take Master DJ on / off air via the Dashboard toggle.

Cannot:

- Manage Line-Ins (sound-card-dependent — Admin only).
- Manage Streams (output bitrate / Icecast credentials —
  Admin only).
- Manage Users.
- Access Settings → Local Machine, → Streams, → Users.
- Restart services.
- Read other Admins' API keys.

### Admin (A)

Full station-level access except creating other Admins.

Can:

- Everything Program Manager can do.
- Manage Line-Ins.
- Manage Streams.
- Manage Users (create / edit / deactivate DJs and Program
  Managers; cannot create / demote other Admins).
- Configure Settings → General Preferences.
- Configure Settings → Local Machine.
- Configure Auto DJ defaults (logo, name, colours,
  playlist).
- Reset other users' passwords.
- Read the System Status page.
- Restart services via the System Status restart widget.

Cannot:

- Promote a user to Admin (Super Admin only).
- Demote another Admin.
- See or change the Super Admin's API key.

### Super Admin (S)

Maximum role. Reserved for the station owner / technical
admin.

Can:

- Everything Admin can do.
- Create new Admins.
- Demote Admins back to lower roles.
- See any user's API key.
- Modify the database / API key store directly via
  Settings → Tools → DB Console (if enabled at install time).

By design there is **exactly one** Super Admin per station.
Multiple Super Admins are technically supported but
operationally discouraged — too many people who can give
others Admin access.

> **Operator tip.** Set the Super Admin to the station
> owner (the legal entity that owns the broadcasting
> license). The Super Admin is the only person who can lock
> out a rogue Admin.

---

## 3. Managing users

Settings → **Manage Users** (Admin / Super Admin only).

```
   ┌──────────────────────────────────────────────────────────────┐
   │  Manage Users                                       [+ New]  │
   ├──────────────────────────────────────────────────────────────┤
   │  Username    │ Role          │ Last login         │ Status   │
   ├──────────────┼───────────────┼────────────────────┼──────────┤
   │  admin       │ Super Admin   │ 2026-05-21 14:32   │ Active   │
   │  anna        │ Admin         │ 2026-05-20 08:15   │ Active   │
   │  ben         │ Program Mgr   │ 2026-05-19 19:00   │ Active   │
   │  carla       │ DJ            │ 2026-05-21 12:00   │ Active   │
   │  david       │ DJ            │ (never)            │ Inactive │
   │  reception   │ Guest         │ 2026-05-21 13:00   │ Active   │
   └──────────────┴───────────────┴────────────────────┴──────────┘
```

### Creating a new user

Manage Users → **+ New**.

| Field | Notes |
|---|---|
| **Username** | Lowercase, no spaces, 3-32 chars. Used in URLs and as a host attribution. Cannot be changed once set. |
| **First / Last name** | Display name. Shown in the user dropdown and on shows where they are the host. |
| **Email** | Used for password reset (if SMTP is configured). |
| **Password** | Min 8 chars. The user can change it on first login. |
| **Role** | One of the five roles. Defaults to DJ. |
| **Cell phone** | Optional. Some stations use it for emergency text alerts. |
| **Skype** | Optional. Legacy field; many stations leave blank. |
| **Active** | Defaults to on. Untick to create a user without granting them access yet. |

Click **Create**.

### Editing a user

Row → **Edit**. All fields except username are editable.

To change a user's role:

- Lower a role (Admin → PM, PM → DJ) is allowed for Admin
  and above.
- Promote to Admin is **Super Admin only**.
- Demote a Super Admin: only the Super Admin themselves can
  do this (i.e. you can step down but no one else can demote
  you). If the Super Admin account is lost, the only
  recovery is direct database access — see
  [`docs/operator/CRASH_RECOVERY.md`](../operator/CRASH_RECOVERY.md).

### Resetting a password

Row → **Reset Password**.

| Option | Effect |
|---|---|
| **Send email** | If SMTP is configured (Settings → General Preferences → Email), send a one-time link valid for 24 hours. |
| **Set password** | Set a temporary password. The user is forced to change it on their next login. |

### Deactivating a user

Row → **Deactivate**. The user can no longer log in but their
historical activity (uploaded tracks, edited shows) is
preserved.

To re-activate, edit and tick **Active**.

To permanently delete a user, **Delete**. Their content
(tracks, blocks, playlists) is reassigned to the configured
**default fallback owner** (typically `admin`).

> **Operator tip.** Prefer **Deactivate** over **Delete**.
> Delete cascades into content reassignment which can be
> confusing if the user's tracks were heavily referenced.
> Deactivate is reversible and preserves the audit trail.

### Last-login tracking

Each user row shows the timestamp of the last successful
login. Useful for the audit question "is this account still
in use?" before disabling.

---

## 4. API keys

Every user can generate an API key for scripted access to
the REST API.

### Generating your own API key

User dropdown (top-right) → **My Profile** → **API key**
section.

| Action | Effect |
|---|---|
| **Generate new key** | Creates a key. Previous key (if any) is revoked. |
| **Reveal** | Shows the key once (for copy-paste). |
| **Revoke** | Disables the key without generating a new one. |

API keys carry the same permissions as the user. A DJ's API
key cannot do anything the DJ user cannot.

### Generating another user's API key

Manage Users → user row → **API key** → Generate. Admin /
Super Admin only.

This is useful for service accounts: create a `script` user
with the DJ role + a known API key, hand the key to the
script, and the script can upload tracks via the API without
interactive login.

> **How it works under the hood.** API keys are 32-byte
> random strings stored in `cc_subjs.api_key` (hashed).
> Authentication is via the `Authorization: Api-Key <key>`
> header against `/api/v2/`. Each request authenticates
> independently; there is no session. See ARCHITECTURE §11.

> **Operator tip.** Treat API keys like passwords. Anyone
> with the key can act as the user. Rotate when you suspect
> exposure. Avoid hard-coding keys in source files committed
> to version control — use environment variables or a secret
> manager.

---

## 5. The permission matrix

The single-source-of-truth table for "can role X do action Y".

| Action | G | H | P | A | S |
|---|:---:|:---:|:---:|:---:|:---:|
| **Dashboard** | | | | | |
| See Now Playing | ✓ | ✓ | ✓ | ✓ | ✓ |
| See listener counts | | ✓ | ✓ | ✓ | ✓ |
| Take Master DJ on / off air | | | ✓ | ✓ | ✓ |
| Cancel current show | | ✓¹ | ✓ | ✓ | ✓ |
| Listen to monitor | | ✓ | ✓ | ✓ | ✓ |
| **Calendar** | | | | | |
| See calendar | ✓ | ✓ | ✓ | ✓ | ✓ |
| Create show | | | ✓ | ✓ | ✓ |
| Edit own show | | ✓ | ✓ | ✓ | ✓ |
| Edit any show | | | ✓ | ✓ | ✓ |
| Delete own show | | ✓ | ✓ | ✓ | ✓ |
| Delete any show | | | ✓ | ✓ | ✓ |
| Apply / save Show Template | | | ✓ | ✓ | ✓ |
| **Library** | | | | | |
| See own files | | ✓ | ✓ | ✓ | ✓ |
| See all files | | | ✓ | ✓ | ✓ |
| Upload track | | ✓ | ✓ | ✓ | ✓ |
| Create / edit own playlists, blocks | | ✓ | ✓ | ✓ | ✓ |
| Create / edit any playlist, block | | | ✓ | ✓ | ✓ |
| Create / edit webstream | | ✓² | ✓ | ✓ | ✓ |
| Create / edit Line-In | | | | ✓ | ✓ |
| Delete own files | | ✓ | ✓ | ✓ | ✓ |
| Delete any file | | | ✓ | ✓ | ✓ |
| **Streams** | | | | | |
| See stream status | | ✓ | ✓ | ✓ | ✓ |
| Edit stream config | | | | ✓ | ✓ |
| **Local Machine** | | | | | |
| See sound-card config | | | | ✓ | ✓ |
| Edit sound-card config | | | | ✓ | ✓ |
| Set Local Import Folder | | | | ✓ | ✓ |
| **Auto DJ** | | | | | |
| Enable / disable | | | ✓ | ✓ | ✓ |
| Edit defaults (name, colours, playlist) | | | | ✓ | ✓ |
| **Settings** | | | | | |
| General Preferences | | | | ✓ | ✓ |
| Localisation | | | | ✓ | ✓ |
| Show Templates page | | | ✓ | ✓ | ✓ |
| Users management | | | | ✓ | ✓ |
| Create Admin | | | | | ✓ |
| **System** | | | | | |
| See System Status | | | | ✓ | ✓ |
| Restart service | | | | ✓ | ✓ |
| Access DB Console (if enabled) | | | | | ✓ |
| **API** | | | | | |
| Generate own API key | | ✓ | ✓ | ✓ | ✓ |
| See / generate any user's API key | | | | ✓ | ✓³ |

Notes:

- ¹ — Only their currently-on-air show.
- ² — Per-DJ; cannot edit other DJs' webstreams.
- ³ — Including other Admins'. A demoted Admin's key stays
  unless explicitly revoked.

---

## 6. Recommended role assignment for typical stations

### Solo operator station (1 person)

- `admin` — Super Admin (the operator).
- (Optional) `reception` — Guest (lobby display, if any).

### Small community station (3-10 contributors)

- `admin` — Super Admin (the station owner / technical
  lead).
- `pm1` — Program Manager (the schedule coordinator).
- `anna`, `ben`, `carla`, … — DJ (one per host).
- (Optional) `engineer` — Admin (if a separate technical
  admin exists).
- (Optional) `reception` — Guest.

### Medium / commercial station (10-50 contributors)

- `owner` — Super Admin.
- `engineer1` — Admin (technical operations).
- `pm1`, `pm2` — Program Manager (one per programme
  department).
- DJ accounts per host.
- `script` — DJ (service account for automation scripts).
- `reception` — Guest.

For all sizes: **one Super Admin per station** is the
sweet spot. Two-or-more leads to "who locked out whom"
confusion.

---

## 7. Frequently-asked

### "I am locked out as Super Admin. How do I recover?"

Direct database access is the only recovery. See
[`docs/operator/CRASH_RECOVERY.md`](../operator/CRASH_RECOVERY.md)
§5. You will need PostgreSQL credentials and a backup of
the database.

### "Can a user have two roles?"

No. One role per user. If a person needs both DJ and
Program Manager capabilities, give them the Program
Manager role (it includes everything DJ can do).

### "Can two users share an account?"

Technically yes, but strongly discouraged:

- Last-login tracking becomes meaningless.
- Audit trails (who scheduled what?) become anonymous.
- API keys cannot be revoked per person.

Prefer one account per real person.

### "How long does a session last?"

Default 8 hours. Configurable via PHP session cookie
lifetime in `php.ini`. After expiry, the user is bounced
to the login page.

### "Can I log in from two browsers simultaneously?"

Yes. Sessions are per-cookie. The same user account can be
logged in from a desktop and a mobile browser
simultaneously.

### "Does the API support OAuth / SSO?"

Not currently. Authentication is by API key (per user) or
by session cookie (interactive UI). SSO integration would
require a separate authn proxy in front of Apache; see
[`docs/operator/UPGRADE.md`](../operator/UPGRADE.md) backlog.

### "Can a DJ see another DJ's recordings?"

No. Recordings inherit the show's owner; only the show's
host (and Program Managers / Admins / Super Admins) can
download them.

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

> **If you are locked out yourself:** wait the minutes shown, or ask a
> colleague on another address.  In an emergency the counters sit in the
> tables `cc_login_attempts` (per address) and `cc_subjs.login_attempts`
> (per user).

## Where to go next

* [Settings](./SETTINGS.md) — tour of every Settings sub-
  page.
* [Dashboard](./DASHBOARD.md) — the operator's most-used
  page, gated by role.
* [`docs/operator/CRASH_RECOVERY.md`](../operator/CRASH_RECOVERY.md)
  — Super Admin lockout recovery.
