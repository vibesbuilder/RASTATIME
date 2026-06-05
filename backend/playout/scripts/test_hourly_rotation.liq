# =====================================================================
# test_hourly_rotation.liq -- RASTATIME Record-per-Hour reality test
# (Phase 1, 2026-06-05).  ISOLATED: synthetic source, no Icecast, no
# telnet, separate output folder.  Does NOT touch the live stream.
#
# Proves:
#   (Q1) output.file with reopen_when rotates to a NEW time-tagged file
#        at a clock-segment boundary, re-evaluating the filename fn.
#   (Q2) a continuous second output (output.dummy) coexists with the
#        rotating file output without a clock conflict / crash (R1).
#   (Q3) the process stays up across several rotations.
#
# Accelerated: SEG = 20 s instead of 3600 s, so a ~120 s run yields
# ~6 segments.  reopen_delay lowered to 5 s (the prod default 120 s
# would block a 20 s rotation).
#
# Run:  C:\Tools\liquidsoap\liquidsoap.exe --check test_hourly_rotation.liq   (parse only)
#       C:\Tools\liquidsoap\liquidsoap.exe test_hourly_rotation.liq           (full run)
# =====================================================================

settings.log.stdout.set(true)
settings.log.level.set(3)

# Probe: which time API gives the real date?  time.string's documented
# codes are %H %M %S %d %A/%a %B/%b %z -- %Y / %m (year / month-number)
# are NOT in the doc list, so we check both here before relying on them
# for the production <YYYY-MM-DD> path.
lt = time.local()
probe_str = time.string("%Y-%m-%d %H-%M-%S")
log("DATE-PROBE local: year=#{lt.year} month=#{lt.month} day=#{lt.day} hour=#{lt.hour} min=#{lt.min} sec=#{lt.sec}")
log("DATE-PROBE strftime: '#{probe_str}'")

# Synthetic, always-available source (noise so files carry real bytes).
src = mksafe(noise())

# Co-existence probe (R1): a second output on the SAME source, to mimic
# the real config where the hourly recorder runs alongside icecast +
# the per-show recorder on the bus.
output.dummy(src)

# --- Clock-segment rotation -----------------------------------------
seg = ref(-1)

def seg_id() =
  int(gettimeofday() / 20.)
end

def reopen_predicate() =
  cur = seg_id()
  if cur != seg() then
    seg := cur
    true
  else
    false
  end
end

# Filename re-evaluated at each (re)open.  Confirmed codes only
# (%H-%M-%S) so each 20 s segment lands in a distinct file.
def hourly_path() =
  ts = time.string("%H-%M-%S")
  "C:/rastatime/rec-test/seg-#{ts}.mp3"
end

output.file(
  id="recording_hourly",
  reopen_when=reopen_predicate,
  reopen_delay={5.},
  fallible=true,
  %ffmpeg(format="mp3", %audio(codec="libmp3lame", b="192k")),
  {hourly_path()},
  src,
)

# Bounded run: self-shutdown after ~125 s so no process lingers.
thread.run(delay=125., {
  log("test_hourly_rotation: 125 s elapsed -- shutting down")
  shutdown()
})
