# Dashboard

> **Where you are in the manual.** The Dashboard is the
> first page operators reach after login. It shows
> at-a-glance station state and offers the manual overrides
> (live-source switch, current-show cancel) that do not need
> a trip to the Calendar.

The **Dashboard** answers three questions in one screen:

1. What is on air *right now*?
2. What is coming up *next*?
3. Are the public streams healthy?

A fourth panel — the **Live Source** controls — is the
operator's escape hatch for taking the station live without
opening a separate broadcasting client.

---

## 1. The page layout

Dashboard → defaults to the live view.

```
   ┌─────────────────────────────────────────────────────────────────┐
   │  Dashboard                              [Auto-refresh: 5 s ▾]   │
   ├──────────────────────────────────────────────────────────────────┤
   │                                                                 │
   │  Now Playing                                                    │
   │  ┌────────────────────────────────────────────────────────────┐ │
   │  │   ♪  Song Title — Artist                                   │ │
   │  │      Show: Morning Show  (90 % filled)                     │ │
   │  │      Source: Scheduler                                     │ │
   │  │      [████████████████░░░░] 03:14 / 03:42                  │ │
   │  └────────────────────────────────────────────────────────────┘ │
   │                                                                 │
   │  Coming Up Next                                                 │
   │   • 14:30  News Brief         (60 % filled)                     │
   │   • 14:35  Music Hour         (100 % filled)                    │
   │   • 15:35  Auto DJ            (—)                               │
   │                                                                 │
   │  Streams                                                        │
   │   1. /rastatime          ● Connected   23 listeners              │
   │   2. /rastatime-mobile   ● Connected    8 listeners              │
   │                                                                 │
   │  Live Source                          [ ☐ Master DJ on air ]    │
   │   Show DJ:    Not connected                                     │
   │   Master DJ:  Not connected                                     │
   │   [Listen to monitor] [Cancel current show]                     │
   └─────────────────────────────────────────────────────────────────┘
```

The page refreshes every 5 seconds (configurable in the
top-right dropdown — 1 / 5 / 10 / 30 seconds or Manual).

---

## 2. Now Playing

The largest panel. Shows the current schedule item plus the
context for what is feeding the public stream.

### Fields

| Field | Meaning |
|---|---|
| **♪ Title — Artist** | The currently playing item's metadata. For tracks: title + artist from `cc_files`. For webstreams: the webstream's display name. For line-ins: the line-in's display name. For Auto-DJ: the underlying track + "Auto DJ" label. |
| **Show** | The show this item belongs to + the show's overall fill percentage. |
| **Source** | Which input the source switcher is currently routing — see §3. |
| **Progress bar** | Time-elapsed / item-duration. The bar fills left-to-right as the item plays. |

> **Why fill percentage matters.** A show at 60 % filled has
> 40 % of its slot empty. When the current track ends, the
> playout reaches the empty tail and falls through to
> silence (or Auto DJ if enabled). The progress percentage on
> the Now Playing panel is the warning signal that this is
> imminent.

### Live-DJ override appearance

When a Live DJ source is active, the panel changes:

```
   ┌────────────────────────────────────────────────────────────┐
   │   🎙 LIVE — Show DJ                                         │
   │      Show: Late Night                                       │
   │      Source: Show DJ (BUTT @ studio-1)                      │
   │      [LIVE — no progress bar]                               │
   └────────────────────────────────────────────────────────────┘
```

No track title (the live source is open audio), no progress
bar, and a clear "🎙 LIVE" indicator so the operator can see
at a glance that the schedule is not what's airing.

> **How it works under the hood.** The Now Playing panel
> consumes `/api/v2/now-playing` which returns the current
> source-switcher state plus the active schedule item.
> The endpoint reads from `rastatime_playback_state` which
> is written by the playout engine on every track / source
> transition. See ARCHITECTURE §9.

---

## 3. Source state

The **Source** field on the Now-Playing panel cycles through
five possible states. Knowing which one is on air right now
is the difference between "stream is working" and "stream is
working but airing the wrong thing".

| Source | What it means | When to be concerned |
|---|---|---|
| **Scheduler** | Playout is playing whatever the calendar says. The normal state. | Never. This is the goal. |
| **Show DJ** | A live remote source has taken the show. The schedule is paused for this show. | If you do not expect a Show DJ to be live — investigate (could be a stale connection, could be a misconfigured host). |
| **Master DJ** | Station-wide live source has overridden everything. | Master DJ should only be on air when the station engineer has intentionally taken over. If you see this and you are not the engineer — contact them. |
| **Auto DJ** | Auto-DJ fill is on air (either an Auto-DJ-created show or the fill-pass for an incomplete show). | If you expected operator-scheduled content — open the Calendar to see why the slot is empty. |
| **Fallback / Silence** | Nothing is scheduled, Auto DJ is off, and the fallback loop is playing (or the station is silent). | Almost always a problem. Open the Calendar to schedule something. |

### Switching source manually

The source switch is **not** controlled by the Dashboard
operator-side — it is driven by the playout engine in
response to:

- The calendar (Scheduler source).
- A remote DJ connecting (Show DJ / Master DJ).
- Auto-DJ kicking in (Auto DJ source).

To **force** a switch:

- **Cancel current show** ends the running show immediately,
  causing the source switcher to advance to whatever comes
  next.
- **Take Master DJ off air** disconnects the Master source
  (if connected) and returns to Scheduler.

These actions live in the **Live Source** panel — see §5.

---

## 4. Coming Up Next

The next 3-5 upcoming items (configurable under General
Preferences → Dashboard Lookahead).

Each row shows:

| Column | Meaning |
|---|---|
| **Time** | Start time of the show (HH:MM in operator timezone). |
| **Show name** | The next show's name. |
| **Fill %** | How filled the show is. Hover for a tooltip with the show's total scheduled seconds. |

> **Operator tip.** A "0 %" or "—" fill on a show that
> starts soon is a problem. Click the show on the calendar
> and fill it manually, or rely on Auto DJ to top it up
> (if enabled).

---

## 5. Streams

Compact view of the same information you get from
Settings → [Streams](./STREAMS.md):

| Column | Meaning |
|---|---|
| **N. /mount** | Stream number + mountpoint. |
| **Status badge** | Same five badges as on the Streams settings page (Connected / Connecting / Disconnected / Disabled / Stale). |
| **Listener count** | Live count, refreshed every 5 s. |

Click a stream → opens the Streams settings page focused on
that stream.

> **Operator tip.** This compact view is what most operators
> watch during a show — listener counts trending up means
> the show is reaching people. Trending down sharply (e.g.
> from 50 to 5) means listeners are dropping; check the
> stream status and the on-air audio.

---

## 6. Live Source panel

Two controls + two status lines.

```
   ┌────────────────────────────────────────────────────────────┐
   │  Live Source                          [ ☐ Master DJ on air ]│
   │   Show DJ:    Not connected                                 │
   │   Master DJ:  Not connected                                 │
   │   [Listen to monitor] [Cancel current show]                 │
   └────────────────────────────────────────────────────────────┘
```

### Master DJ on air checkbox

The top-right checkbox toggles the Master-DJ override:

| Checkbox | Effect |
|---|---|
| **Off** (default) | Master DJ is muted at the source switcher even if connected. The scheduler / Show DJ is on air. |
| **On** | Master DJ is on air if connected. Any source-switcher input is overridden. |

Useful for "the engineer is connected but standing by; the
schedule should keep running until I flip the switch".

> **Why a checkbox and not just "connected = on air"?** The
> upstream LibreTime model was "Master DJ on air whenever
> connected"; RASTATIME 2026-05-15 added the explicit toggle
> after operator feedback that an engineer testing a
> connection should not accidentally take over a live show.

### Show DJ / Master DJ status lines

Each line shows one of:

- **Not connected** — the source mount is not currently
  receiving audio.
- **Connected (idle)** — receiving audio but not on air
  (either Master DJ checkbox is off or a higher-priority
  source is active).
- **Connected (on air)** — currently feeding the public
  output.

### Listen to monitor

Plays the [Local Machine](./LOCAL_MACHINE.md) monitor
output through your browser. Useful for checking what the
operator-machine's preview output sounds like *without*
having to be physically in front of the speakers.

> **Browser support.** The button uses the Web Audio API,
> which works in all modern browsers. Safari may prompt for
> microphone permission (it is not actually using the
> microphone, but Safari conflates audio capture with audio
> playback in some contexts).

### Cancel current show

Ends the currently-playing show **right now**.

Effects:

- The show's `cc_show_instances.ends_at` is set to "now".
- The source switcher advances to whatever was next on the
  schedule (or to Auto DJ if no next show, or to fallback /
  silence).
- If the show was being recorded (Record-per-Show), the
  recording stops gracefully (FFmpeg SIGTERM, file
  finalised).
- A Show DJ connected to this show is kicked.

> **Operator tip.** Use **Cancel current show** sparingly —
> the cancel is irreversible. To make a show shorter without
> ending it immediately, edit the show on the calendar and
> change the end time; that takes effect for the *next*
> episode and is reversible.

---

## 7. Frequently-asked

### "The Now Playing panel says 'Silent'. What does that mean?"

The playout engine is running, no show is current, no Auto
DJ is enabled, and no fallback loop is configured. The public
stream is silence.

Fix: open the Calendar and schedule a show, or enable
[Auto DJ](./AUTO_DJ.md).

### "The Source is 'Scheduler' but I hear nothing on the public stream."

Three possibilities:

1. The currently-scheduled item is itself silent (e.g. a
   30-second silence stinger). Check the track.
2. The Icecast connection is open but the encode is silent
   (operator-machine audio device problem). Check Settings
   → [Streams](./STREAMS.md) for the connection state.
3. The browser tab is muted (check the small mute indicator
   on the tab itself).

### "Why does the page sometimes lag a few seconds behind reality?"

The Now Playing endpoint refreshes every 5 seconds; the
display shows whatever the last refresh returned. For
sub-second accuracy you would need a streaming endpoint
(websocket / SSE); not currently implemented.

### "Can I see the Dashboard without logging in?"

No — the Dashboard requires authentication. For an
unauthenticated public "what's on" page, use the
embed widget at `/embed/now-playing` which exposes only the
Now-Playing title (no source, no listener counts, no
controls).

### "Why does the listener count drop to zero for one refresh cycle?"

Icecast briefly resets the listener counter when the source
reconnects (every time the bitrate changes, the stream
restarts, or the source briefly disconnects). The next 5 s
refresh shows the count again. If the drop persists, the
stream is actually unreachable — investigate.

---

## Where to go next

* [Calendar](./CALENDAR.md) — what populates "Coming Up
  Next".
* [Streams](./STREAMS.md) — full detail on each output
  stream.
* [Auto DJ](./AUTO_DJ.md) — what fills the gaps when no
  show is current.
* [Local Machine](./LOCAL_MACHINE.md) — the monitor output
  the **Listen to monitor** button uses.
