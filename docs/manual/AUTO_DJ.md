# Auto DJ

> **Where you are in the manual.** Read
> [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) first if
> you have not — Auto DJ is the station-wide counterpart to
> the per-show autoloading playlist. §8 of that chapter has
> the side-by-side comparison.

**Auto DJ** is the background filler that keeps the station on
air during the time the operator did not plan for. It works
in two complementary passes, both fully automatic once
enabled:

1. **Pre-pass** — if the next hour of the calendar contains
   any gap longer than 60 seconds, create a new show in the
   first such gap, named according to your defaults, with
   the Auto-DJ playlist autoloaded.
2. **Fill-pass** (optional) — if any upcoming show ends up
   more than 5 s short of its slot after its build, top the
   tail up with the Auto-DJ playlist.

The result: as long as Auto DJ is enabled and pointed at a
healthy playlist, your station never falls silent.

---

## 1. Why Auto DJ exists

Pre-2026-05-21 the fallback for "no scheduled show right now"
was a configured loop file (silence by default). That covered
"never any show", but a calendar with 80 % coverage and 20 %
gaps still played silence in the gaps.

The two patterns the operator hit repeatedly:

- The Monday-morning show ends at 10:00 but the next show
  starts at 14:00. The four-hour gap played fallback silence
  on the public stream — bad listener experience.
- A 60-minute show's autoplaylist filled only 55 minutes (smart
  blocks ran out of matching tracks); the last 5 minutes were
  silence.

Auto DJ covers both with the same configured playlist.

---

## 2. Enabling Auto DJ

Settings → **Auto DJ**.

```
   ┌──────────────────────────────────────────────────────────────┐
   │  Auto DJ Settings                                            │
   ├──────────────────────────────────────────────────────────────┤
   │  When enabled, Auto DJ scans the calendar for gaps in the    │
   │  next hour and automatically creates a show in the first one │
   │  it finds, filled with the playlist selected below.  If      │
   │  "Automatically fill any show" is enabled, any incomplete    │
   │  upcoming show is also topped up with the same playlist.     │
   ├──────────────────────────────────────────────────────────────┤
   │  Status                                                      │
   │  ☑  Enabled — Auto DJ will create and fill shows automatically│
   ├──────────────────────────────────────────────────────────────┤
   │  Auto DJ Show Defaults                                       │
   │                                                              │
   │   Default Playlist:  [Select a playlist ▾]  ◀── mandatory    │
   │   Show Name:         [Auto DJ              ]                 │
   │   URL:               [                     ]                 │
   │   Genre:             [                     ]                 │
   │   Description:       [                     ]                 │
   │   Background Color:  [222222   ]                             │
   │   Text Color:        [ffffff   ]                             │
   │                                                              │
   │  ☐  Automatically fill any show that is incomplete after     │
   │     the autoplaylist build                                   │
   │                                                              │
   │   Show Logo:        [Choose File ▾]  Upload                  │
   ├──────────────────────────────────────────────────────────────┤
   │                                       [   Save   ]           │
   └──────────────────────────────────────────────────────────────┘
```

### Required fields

| Field | Notes |
|---|---|
| **Enabled** | Master switch. When off, neither pass runs. |
| **Default Playlist** | The playlist Auto DJ uses to fill its shows and (if fill-pass is on) to top up incomplete shows. Required when **Enabled** is on. |

### Recommended playlist shape

Use a playlist that contains exactly **one smart block** with:

- Type: **Dynamic** (re-evaluates each cycle).
- Criteria: a generous filter that matches several hundred
  tracks. "Track type = Music" is a good baseline.
- **Limit to: Time remaining in show**. This is critical —
  Auto-DJ-created shows have variable length depending on the
  gap they fill (5 minutes to several hours), and the smart
  block needs to fill exactly the slot it gets.
- Sort: **Random**.

> **Operator tip.** The Settings page surfaces a tooltip on
> the **Default Playlist** label with exactly this advice.
> Mouse over the "?" icon if you forget the recommendation.

### Optional fields

| Field | What Auto DJ does with it |
|---|---|
| **Show Name** | Used as the auto-created show's name on the calendar. Default `Auto DJ`. |
| **URL / Genre / Description** | Copied to every auto-created show's metadata. Visible in the public schedule export. |
| **Background / Text Color** | Used to colour the auto-created shows on the calendar — helpful for distinguishing them from operator-scheduled shows at a glance. |
| **Show Logo** | Default logo for the auto-created shows. Stored as a base64 blob in `cc_pref`. Upload limit 2 MB; JPG / PNG / GIF. |
| **Automatically fill any show** | If on, enables the second pass (fill-pass). |

> **How it works under the hood.** Settings live in the
> `cc_pref` table as plain key/value rows (no schema change):
> `auto_dj_enabled`, `auto_dj_show_name`,
> `auto_dj_playlist_id`, `auto_dj_fill_any_show`,
> `auto_dj_logo_path`, plus URL/Genre/Description/Bg/Text
> Color. The logo upload uses a separate multipart POST to
> `autoDjUploadLogoAction`. The PHP service
> `Application_Service_AutoDjService` is invoked from
> `AutoPlaylistManager.buildAutoPlaylist()` at 60 s cadence.
> See ARCHITECTURE §23.20.

---

## 3. The pre-pass — gap filling

Every 60 seconds, Auto DJ scans for the next hour of
calendar gaps. A **gap** is any contiguous stretch where no
show is scheduled.

For the **first** gap longer than 60 seconds whose start is
within the next hour:

1. Create a new `cc_show` row using the configured defaults
   (name, colours, URL, etc.).
2. Insert a `cc_show_days` row with the operator-local
   timezone and rounded times (start UP to the next minute,
   end DOWN to the previous minute).
3. Insert a `cc_show_instances` row for the same range.
4. Attach the configured Auto-DJ playlist as autoloading.

The new show is then picked up by the **same** poll cycle's
body loop and built. So one 5-minute tick after the operator
deletes a show that leaves a one-hour gap, Auto DJ has
already replaced it with an Auto-DJ show and filled it.

### Why only one show per cycle?

The pre-pass creates **one** show per 60 s cycle, even if
multiple gaps exist. This is intentional:

- After one show is created, the next gap moves. The cycle
  re-evaluates.
- An operator who is actively re-arranging the calendar
  should not have ten Auto-DJ shows materialise faster than
  they can react.
- One-at-a-time matches the natural cadence of human
  scheduling.

After ten cycles (10 minutes), up to ten Auto-DJ shows have
been created if the operator hasn't done anything. For a
typical calendar with a few-hour gap that is the right pace.

### Show times are rounded to the minute

Auto-DJ-created shows always start on a minute boundary
(rounded *up* from the gap start) and end on a minute
boundary (rounded *down* from the gap end). This is for two
reasons:

- The operator's Edit-Show form does not display
  sub-minute timestamps cleanly, which led to a
  "Cannot schedule overlapping shows" error when the
  operator opened an Auto-DJ show with a 14:00:30 start.
  RASTATIME 2026-05-21 rounds at creation to avoid the
  confusion.
- A consistent minute alignment matches operator
  expectations of scheduled shows.

The trade-off: if the gap is 14:00:30 → 15:00:30, the
Auto-DJ show occupies 14:01 → 15:00 — 59 minutes instead of
59:30. Half a minute lost. Acceptable.

> **Operator tip.** If you need precise gap filling (e.g. a
> tightly-scheduled syndication relay), use a one-off show
> with the exact times instead of relying on Auto DJ.

---

## 4. The fill-pass — topping up incomplete shows

Optional, opt-in via **Automatically fill any show that is
incomplete after the autoplaylist build**.

Every 60 s cycle, after the pre-pass + the normal
autoplaylist body builds, the fill-pass walks every upcoming
show whose tail ended up more than 5 seconds short of its
slot. For each, it appends the Auto-DJ playlist to the end
to top up the slot.

Common reasons a show ends up short:

- Its autoplaylist's smart blocks ran out of matching tracks.
- The autoplaylist had no "time remaining" smart block, just
  a fixed number of items.
- The operator forgot to attach an autoplaylist at all.

### Why 5 seconds and not a stricter threshold?

The outro reserve (see [Autoloading
Playlists](./AUTOLOADING_PLAYLISTS.md) §4) intentionally
leaves up to 5 s slack so the auto-build does not overbook.
Tightening the fill-pass threshold to e.g. 1 s would
constantly top up shows that were already optimally filled —
wasteful and annoying.

### Fill-pass never modifies the show definition

The fill-pass only inserts **schedule items** into the
existing instance. It does not change the show's name,
hosts, autoplaylist attachment, or any other definition
field. The operator's intent for the show stays intact;
only the empty tail is filled.

---

## 5. Auto-DJ-created shows on the calendar

Auto-DJ-created shows look like any other show, with the
visual cue of the configured background colour
(typically darker than operator-scheduled shows).

| Action | Allowed on Auto-DJ shows? |
|---|---|
| **View** | Yes |
| **Edit Show** | Yes — but be aware the edit happens on the auto-created show, not on the Auto-DJ defaults. To change the defaults, use Settings → Auto DJ. |
| **Schedule Tracks** | Yes — append / replace items as on any show. |
| **Cancel Show** | Yes (current show only). |
| **Delete Show** | Yes. After deletion, the gap re-appears and Auto DJ may re-fill it on the next cycle. |

> **Operator tip.** If you want to **prevent** Auto DJ from
> re-filling a gap (e.g. you want a 30-minute silence for a
> remembrance), create an explicit empty one-off show with no
> autoloading playlist over that gap. Auto DJ never touches
> existing shows for the pre-pass, only gaps.

---

## 6. Disabling Auto DJ

Settings → Auto DJ → untick **Enabled** → **Save**.

Effects:

- Pre-pass stops creating new shows. Already-created Auto-DJ
  shows remain on the calendar.
- Fill-pass stops topping up incomplete shows.

To remove already-created Auto-DJ shows in bulk, use the
Bulk Actions → **Delete selected shows** on the Calendar.

---

## 7. Frequently-asked

### "Auto DJ isn't creating any shows."

Check in order:

1. **Enabled** is ticked and **Save** clicked.
2. **Default Playlist** is set to a non-empty playlist.
3. The next-hour window actually contains a gap > 60 s. If
   the next hour is fully booked, the pre-pass is correctly
   a no-op.
4. **RASTATIME-WORKER** service is running
   (`Get-Service RASTATIME-WORKER`).
5. The configured playlist's smart blocks return at least
   one matching track. An empty selection produces an empty
   build.

### "Auto DJ created 17 tiny shows over a long gap."

This was a regression in v4 (Section 23.20). RASTATIME
2026-05-21 onwards fixes it: the pre-pass queries up to 200
upcoming instances and only requires the gap *start* (not
the gap *end*) to be inside the lookahead window. So a
single gap creates a single show, even if the gap is
multiple hours long. If you still see this, upgrade.

### "Auto DJ shows say wrong timezone in the Edit dialog."

This was a regression in v5 (Section 23.20). RASTATIME stores
the show's local time + the operator's local timezone in
`cc_show_days.timezone`. Pre-fix the timezone was 'UTC' so
the Edit dialog displayed UTC and the operator saw 13:08 for
a show actually starting at 15:08 local. Fixed 2026-05-21.

### "Can Auto DJ use different playlists for different times of day?"

Not directly. The Auto-DJ playlist is a single station-wide
choice. The workaround:

1. Use the Auto-DJ playlist as a *daypart router*: it
   contains a single smart block with a criterion like
   *Track type = Music AND tag contains "morning"*.
2. Tag tracks by time of day (operator convention).
3. Use a different criterion at a different time of day by
   changing the smart-block filter (manual, weekly).

Future work may add a daypart-aware Auto DJ; not yet
implemented.

### "Does Auto DJ honour the per-show fill-pass differently?"

No — the fill-pass is station-wide. Either every incomplete
show gets the top-up, or none do. Per-show opt-out is not
supported (use an autoloading playlist with the same playlist
for the same effect; that bypasses the fill-pass for that
show because the show is no longer incomplete).

---

## 8. Recommended Auto-DJ profile for new stations

If you are setting up Auto DJ for the first time, start with
this conservative profile:

| Setting | Value |
|---|---|
| **Enabled** | Off (set up everything else first, then enable) |
| **Default Playlist** | A playlist named "Auto DJ" containing one smart block: type Dynamic, criteria "Track type = Music", limit "Time remaining in show", sort Random |
| **Show Name** | `Auto DJ` |
| **Background Color** | `222222` (dark grey — visually distinct from operator shows) |
| **Text Color** | `ffffff` |
| **Automatically fill any show** | Off (turn on later once you trust the playlist) |

Then enable, watch the calendar for one full day, and adjust.

---

## Where to go next

* [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) — the
  per-show counterpart; both run in the same 60 s build cycle.
* [Library](./LIBRARY.md) → Smart Blocks — most useful primitive
  for the Auto-DJ playlist.
* [Calendar](./CALENDAR.md) — where Auto-DJ-created shows
  appear; bulk actions for removing them.
