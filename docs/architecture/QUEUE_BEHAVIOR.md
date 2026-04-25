# RASTATIME — Queue Behavior Contract

**Version:** 1.0  
**Status:** Authoritative specification (T8.1)  
**Informs:** T8.2 (QueueManager), T8.3 (scheduler–engine wiring)

---

## 1. Purpose

This document defines the authoritative behavior contract for RASTATIME's
playout queue system.  It answers:

* What plays, when, and why.
* How the system transitions between scheduled shows, fallback/filler content,
  and silence.
* Which edge cases are handled, and how.
* Where RASTATIME diverges from the LibreTime / Liquidsoap model, and why.

Implementors of `QueueManager` (T8.2) and any scheduler-to-engine wiring
(T8.3) **must** conform to this document.  Where this document and the code
disagree, this document is correct until a deliberate revision is made.

---

## 2. Queue Types and Priority

RASTATIME maintains three logical content sources, listed from highest to
lowest priority:

| Priority | Source | Description |
|----------|--------|-------------|
| 1 (highest) | **Live input** | Line-in, live DJ, or remote contribution stream. Overrides everything. *(Not yet implemented; reserved for T12+.)* |
| 2 | **Scheduled show** | Items from a `ScheduledShow` dispatched by the `PlayoutScheduler`. |
| 3 (lowest) | **Fallback / filler** | Items from a `FallbackQueue`; plays in the absence of any higher-priority source. |

A higher-priority source always wins immediately (hard transition) or at the
next track boundary (soft transition), as described in §4.

---

## 3. Content Sources in Detail

### 3.1 Scheduled Show

A `ScheduledShow` has:

* `show_id` — unique identifier.
* `start_at` — UTC wall-clock time when the show begins.
* `end_at` — UTC wall-clock time when the show ends unconditionally.
* `items` — ordered list of `QueueItem` objects to play.
* `start_mode` — `HARD` (default) or `SOFT` (see §4).

The `PlayoutScheduler` arms two timers per show: one at `start_at` and one at
`end_at`.  If a show's `end_at` is already in the past when `schedule()` is
called, the show is silently discarded.

A show with an empty `items` list is silently skipped: neither the start nor
the stop timer is armed.  *(Assumption: the API always sends at least one item
per slot; this guards against malformed inputs.)*

### 3.2 Fallback / Filler

A `FallbackQueue` has:

* `items` — ordered list of `QueueItem` objects; must not be empty.
* `loop` — `True`: the list repeats indefinitely.  `False`: plays once, then
  stops.

The fallback does **not** start automatically; it requires explicit
configuration via `PlayoutScheduler.set_fallback()`.  Once configured, it
activates at each show end and deactivates at each show start.

---

## 4. Transition Rules

### 4.1 Show Start

**HARD mode** (default):

1. Stop any currently playing content immediately (engine hard-stop).
2. Disable the fallback flag (`_fallback_active = False`) *before* calling
   `load_queue()` to prevent the engine's track-change callback from
   spuriously restarting the fallback during the brief stopped state.
3. Load the show's items into the engine queue.
4. Call `engine.start()`.

Guarantee: the show begins no later than `start_at + scheduling_jitter`
(typically < 5 ms for local timers; no guarantee against OS scheduler
starvation).

**SOFT mode**:

1. Disable the fallback flag.
2. If the engine is `STOPPED`: fall back to HARD mode.
3. If the engine is `PLAYING` or `PAUSED`:
   a. Clear the pending queue (remove all items after the current track).
   b. Append the show's items to the queue.
   c. The current track plays to its natural end; the show's first item plays
      next.

Guarantee: the current track is not interrupted; the show items play
immediately after it.  Time-alignment is best-effort; the show may start
slightly late if the current track is long.

### 4.2 Show End (`end_at` reached)

1. Call `engine.stop()` — this is a hard stop regardless of `start_mode`.
   Any track currently in progress is cut off.
2. Remove the show from the pending jobs map.
3. If a `FallbackQueue` is configured and is non-empty, set
   `_fallback_active = True` and start the fallback in a daemon thread
   (outside the scheduler lock).

Guarantee: the show ends no later than `end_at + timer_jitter` (same bound as
§4.1).

### 4.3 Fallback Start

Called from `_trigger_fallback()` after a show ends:

1. Call `engine.load_queue(fb.items)`.
2. Call `engine.start()`.

### 4.4 Fallback Restart (looping)

When `loop=True` and the engine fires a `TrackChangedEvent` with
`current_item=None` (queue exhausted) while `_fallback_active=True`:

1. A new daemon thread calls `_trigger_fallback()`.
2. This restarts the fallback list from its first item.

The restart is asynchronous; a brief silence (engine-thread spawn latency,
typically < 50 ms) occurs between the last fallback item ending and the
restart.

### 4.5 Fallback Stop (non-looping)

When `loop=False` and the engine exhausts the fallback queue:

1. The engine transitions to `STOPPED` naturally.
2. `_fallback_active` is **not** changed by this event — the fallback remains
   "configured" but inactive.
3. Nothing plays until the next show starts or a new fallback is configured.

### 4.6 Show Interrupts Fallback

When a new show arrives while fallback is playing:

* HARD mode: fallback stops immediately (§4.1 HARD).
* SOFT mode: fallback track plays to end, show items enqueue next (§4.1 SOFT).

In either case, `_fallback_active` is set to `False` before the engine
transition, ensuring the fallback cannot restart unexpectedly.

---

## 5. Edge Cases and Their Resolution

| Scenario | Behavior |
|----------|----------|
| Show scheduled entirely in the past (`end_at ≤ now`) | Silently ignored; no timers armed. |
| Show `start_at` is in the past but `end_at` is in the future | Start timer delay is clamped to 0 (fires immediately); stop timer fires at `end_at`. |
| Show with empty `items` list | Silently ignored; no timers armed. |
| Two shows with the same `show_id` | Second call to `schedule()` cancels and replaces the first. |
| Two shows with overlapping time slots and different `show_id`s | Both timers run independently; whichever `start_at` fires first plays first; the later show's HARD start interrupts it at its `start_at`. |
| Back-to-back shows with no gap | Show B's `start_at` == show A's `end_at`; show A's stop timer and show B's start timer fire at the same instant. The engine may briefly reach STOPPED before show B's HARD start loads its queue. *(See §6.2 for the gap this causes.)* |
| Fallback not configured (`set_fallback` never called) | Engine stays STOPPED after each show ends; no filler plays. |
| `clear_fallback()` called while fallback is playing | `_fallback = None`, `_fallback_active = False`; the currently playing fallback item finishes naturally (the engine's queue still holds it) but does **not** restart. |
| `clear_fallback()` called before show ends | Fallback will not start when the show ends. |
| Engine error (`PlayoutState.ERROR`) during fallback | The fallback item is abandoned; the error callback fires. Fallback does not auto-restart from an error state — a show start or an explicit `engine.stop()` + restart is required. |
| Fallback list has a single item, `loop=True` | That item plays, restarts, plays, restarts … indefinitely. |
| `set_fallback()` called while fallback is already playing | The new `FallbackQueue` replaces the configuration object. The currently playing items (already loaded into the engine) continue until the current loop cycle ends; the new list takes effect at the next `_trigger_fallback()` call. |

---

## 6. Known Limitations and Assumptions

The following limitations are accepted for the current phase (M8).  Each is
flagged explicitly because LibreTime's Liquidsoap-based system handled them
differently.

### 6.1 Cue Points Ignored

LibreTime sends `cue_in` and `cue_out` per track (seconds from file start/end)
to Liquidsoap.  RASTATIME currently ignores these fields; playback always
starts from the beginning and ends at the file's natural end.

**Impact:** A track declared to start at 0:30 will play from 0:00.  Cue point
support is planned post-M8.

### 6.2 Inter-Track Silence (~50–200 ms)

Between consecutive queue items, a brief silence occurs while the engine spawns
a thread, calls `media_new()`, and VLC buffers the file.  For scheduled-show
boundaries (where millisecond precision is not required) this is acceptable.
For music rotation, back-to-back items will have a perceptible gap.

Planned improvement: use `libvlc_media_list_player` or pre-load the next media
object during playback of the current item.

### 6.3 No Crossfade

LibreTime supports crossfade via Liquidsoap's `liq_start_next`, `liq_fade_in`,
and `liq_fade_out` annotations.  RASTATIME currently produces hard cuts between
items.  Crossfade is planned post-M8.

### 6.4 No Replay Gain

LibreTime applies `replay_gain` normalization per track.  RASTATIME plays all
tracks at unity gain.  Loudness normalization is planned post-M8.

### 6.5 Single Sequential Queue

LibreTime uses four parallel Liquidsoap queues (numbered 0–3), allowing
overlapping audio segments (crossfade, cue overlap).  RASTATIME uses a single
sequential engine queue; only one item plays at a time.

### 6.6 No Live DJ / Line-In (yet)

Priority level 1 (live input) is reserved but not implemented.  Any live-input
integration (T12+) must honour the priority model in §2 and will require
preemption logic analogous to HARD mode.

### 6.7 No Web-Stream Input Type

LibreTime supports `WebStreamEvent` (HTTP radio streams as a scheduled item
type).  RASTATIME's `QueueItem` currently represents local files only.
Web-stream `uri` values (e.g. `http://stream.example.com:8000/stream.ogg`)
may be passed to VLC (which can play HTTP streams) but are not explicitly
tested.

### 6.8 `start_at` Precision Depends on OS Timer Resolution

Python's `threading.Timer` targets wall-clock accuracy within a few
milliseconds on Windows.  Under heavy CPU load, actual fire times may deviate
by tens of milliseconds.  For broadcast applications requiring sub-frame
accuracy (< 40 ms), an alternative timer mechanism (e.g. a dedicated
scheduling thread with `time.sleep` calibration) would be needed.

---

## 7. Planned QueueManager (T8.2)

The current implementation distributes queue-decision logic across
`PlayoutScheduler` and `VlcPlayoutEngine`.  T8.2 will introduce a dedicated
`QueueManager` that:

* Owns the decision of *what* to play next (show vs. fallback vs. silence).
* Receives instructions from the scheduler and events from the engine.
* Issues `load_queue()`, `start()`, and `stop()` commands to the engine.
* Makes the scheduler ignorant of the engine's internal queue state.

The `QueueManager` will conform to the priority model in §2 and the transition
rules in §4, making this document the specification it is implemented against.

---

## 8. State Diagram (Simplified)

```
               schedule(show, HARD)
                      │
                      ▼
  ┌──────────┐  start_at   ┌─────────────┐  end_at   ┌──────────┐
  │  IDLE /  │────────────►│ SHOW PLAYING│──────────►│  IDLE /  │
  │ FALLBACK │             └─────────────┘           │ FALLBACK │
  └──────────┘                    │                  └──────────┘
       ▲                   stop() │ (SOFT: wait       │
       │                  via end_│  for track end)   │
       │                  timer   │                   │
       │                          ▼                   │
       │                   ┌─────────────┐            │
       └───────────────────│   STOPPED   │◄───────────┘
                           └─────────────┘
                                 │
                           fallback configured?
                                 │ yes
                                 ▼
                           ┌─────────────┐   loop=True, queue empty
                           │  FALLBACK   │◄──────────────────────────┐
                           │  PLAYING    │───────────────────────────┘
                           └─────────────┘
                                 │ loop=False, queue empty
                                 ▼
                           ┌─────────────┐
                           │   STOPPED   │
                           └─────────────┘
```

---

## 9. Revision History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-04-25 | Initial contract (T8.1); derived from T6.1/T6.2 implementation and LibreTime upstream source review. |
