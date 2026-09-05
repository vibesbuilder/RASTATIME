# Upstream report draft — Liquidsoap 2.4.4 Windows build leaks ~5 KB per `Unix.select`

Target: https://github.com/savonet/liquidsoap/issues (related: #1122
"Memory leak on windows using telnet commands", open since 2020).
Post as-is or trim; everything below was measured on 2026-09-05.

---

**Title:** Windows build: ~5 KB leaked per `Unix.select` call (OCaml 4.14 win32unix `select.c`), request.dynamic's retry poller turns it into 0.15–0.8 MB/s

**Environment**

- Liquidsoap 2.4.4, official Windows build (OCaml 4.14.1, portaudio 0.2.3, ffmpeg-av 1.3.0), Windows 11 Pro 26200, running as an NSSM service.
- Script: `request.queue` → `fallback` → `crossfade` → `switch` (five arms with `input.harbor`/`input.http`/`input.ffmpeg`) → three `output.icecast` (`%ffmpeg` mp3/aac/opus) + `output.portaudio` behind a `buffer()`/`clock.assign_new` bridge. Telnet enabled.

**Symptom**

Private bytes of `liquidsoap.exe` grow without bound: 3.4 GB after two hours, 0.15 MB/s while idle (silence on the bus, all inputs stopped), up to 0.8 MB/s during shows. `runtime.memory` reports `Managed memory: 78 MB` the whole time; `runtime.gc.full_major` and `runtime.gc.compact` free nothing. The process ran 15.5 h before a reboot without dying, so the rate depends on activity, not uptime.

**What the leaked memory is**

Read-only scan of the process (VirtualQueryEx/ReadProcessMemory):

- 160+ NT-heap segments of 16 MB each, `TotalFreeSize` 36 MB — i.e. busy blocks.
- The segments contain a repeating pair of blocks (2032 + 3104 bytes, 5136 per unit, ~2.4 GB / 5136 ≈ 470k units in 100 minutes).
- Each unit starts with a struct whose second word is a code pointer; resolved through the COFF symbol table of `liquidsoap.exe` (330k symbols, not stripped) it is `read_pipe_poll` — the worker function of OCaml's Windows `Unix.select` emulation (`otherlibs/win32unix/select.c`). The following 32-byte records hold Windows HANDLE values (multiples of 4: 0x534, 0x2f0, 0x2cc, …) matching the fd set the Duppy scheduler selects on (wake-up pipe, telnet/harbor listeners, connected clients).

So every `Unix.select` issued by the scheduler thread leaves its `SELECTDATA`-sized allocations behind on this build.

**What drives the select rate**

Replicas of the production script (own ports/mounts, 150–180 s each, private bytes sampled every 15 s):

| scenario | growth |
|---|---|
| fresh instance, no requests (with portaudio on MME/DirectSound/WASAPI, with the icecast outputs, after a webstream show, with an idle or half-closed telnet connection) | flat |
| one file pushed at start (initial queue) and played to the end | flat |
| one `scheduled.push` while running (valid file), then idle | +80–100 KB/s forever |
| push of a missing file (`Unknown protocol URI`) | +50–80 KB/s forever |
| as above, then a valid push that plays fine | growth continues |
| `request.queue` copy with `retry_delay={2.0}` | ~10 KB/s |
| `request.queue` copy with `synchronous=true` (valid and failed pushes) | flat, pushes start at once |

Reading: an explicit `push` calls `fetch()`, the asynchronous fetch task then keeps re-scheduling itself every `retry_delay` (0.1 s) once `next()` returns `null` (empty queue) or a request fails — forever. Each Duppy wake-up is a `Unix.select`, each select leaks. With `synchronous=true` no task exists.

**Minimal reproduction**

```liquidsoap
settings.server.telnet := true
settings.server.telnet.port := 1234
q = request.queue(id="q")
output.dummy(fallible=true, fallback(track_sensitive=false, [q, blank()]))
```

Start, then `echo "q.push C:/does-not-exist.mp3" | nc 127.0.0.1 1234`, and watch `PrivateMemorySize64` of the process: ~50–80 KB/s from then on. Same with a valid file pushed while the script runs.

**Workaround in production**

A copy of the stdlib `request.queue` whose `request.dynamic` is created with `synchronous=true` (and a small `timeout`). Memory stays flat; pushes resolve inline in the telnet handler.

**Suggested fixes upstream**

- Use a socketpair instead of a pipe for the Duppy wake-up on Windows (avoids the worker-thread path of win32unix select), and/or
- build the Windows binary with an OCaml whose `select.c` frees the worker structures, and/or
- stop the request.dynamic retry loop when `available()` is false and the queue is empty.
