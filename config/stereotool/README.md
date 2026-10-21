# Stereo Tool presets shipped with RASTATIME

## `rastatime-r128-transparent.sts`

A minimal preset for the Stereo Tool library on the output bus
(Settings → Streams → Output Processing): **no processing at all, only a
true-peak limiter at −1 dBTP with unity gain**.  It makes the stream
EBU R128 conformant on the peak side; the loudness side (−23 LUFS) comes
from the sources RASTATIME already levels - the per-track gain of the
Loudness Normalization for library files and the Input Gain of
webstreams and line-ins.

How it works (verified offline against the library on 2026-10-21, see
below): the final limiter runs with +1.1 dB pre-amp and a 0 dBFS ceiling
(oversampled, so it catches inter-sample peaks), the post amplifier takes
the result down by 1.1 dB.  Programme below the ceiling therefore passes
with 0.0 dB gain; everything above lands at −1.0 dBTP.  A loaded preset
only sets the keys it contains, every other stage keeps the library's
defaults, which are "off" - the stock library with no preset is fully
transparent (even a +2 dBTP square wave passes untouched).

Measurements (Liquidsoap `stereotool()` with this preset, `load_type`
`all_settings`):

| Signal | In | Out |
|---|---|---|
| 1 kHz sine, −41 LUFS | −41.1 LUFS / −41.1 dBTP | −41.1 LUFS / −41.1 dBTP |
| 997 Hz square, full scale | +3.8 LUFS / +2.1 dBTP | +0.6 LUFS / **−1.0 dBTP** |
| 40 s of a show recording | −23.1 LUFS / −9.9 dBFS | −23.1 LUFS / −9.9 dBFS |

Use: enter the full path of this file in the **Stereo Tool preset (.sts)**
field; the playout applies it with its planned Liquidsoap restart.  Keep
the Liquidsoap limiter (`loudness_limit`, −1 dBTP on sample peaks) in
front of it: it is the safety net for the fallback path without Stereo
Tool.

File format: Stereo Tool's INI-style preset.  Keys and sections are the
ones the Stereo Tool application writes to `stereo_tool.ini`; values are
linear factors (1 = 0 dB, 0.881 = −1.1 dB, 1.135 = +1.1 dB).  Do not add
AGC or compressor sections here - this preset is meant to stay
transparent.  For a processed sound, build a separate preset in the
Stereo Tool application and point the setting at that file instead.

Test harness: `C:/Temp/optd/stpreset/st_run.liq` (offline run through
the library: `liquidsoap st_run.liq -- <tag> <preset> all_settings
[input.wav]`) and `st_measure.sh` (integrated loudness and true peak of
the three test segments).
