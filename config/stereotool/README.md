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

## `rastatime-16-clean.sts` (since 2026-11-09)

The transparent preset plus **+7 dB** in front of the same true-peak
limiter: the programme RASTATIME levels to −23 LUFS leaves at
**−16 LUFS** with true peaks at −1 dBTP - loud enough for stream
receivers that feed transmitters, and the usual level of web streams.
No AGC, no compressor: nothing rides the gain, a programme keeps its
dynamics (quiet passages get the same +7 dB as everything else).
`[HD] R128 mode` stays 0: it is a loudness *ceiling* - set to −16 it
pulled the programme down to −18.3 LUFS and rode the gain by up to
5.7 dB in quiet music.

With this preset the stream is no longer EBU R128 conformant
(−23 LUFS); an R128 feed needs a mount of its own.

Measurements (2026-11-09, offline through the library, 311 s of real
programme with the per-track gains of the Loudness Normalization):

| Signal | In | Out |
|---|---|---|
| Whole programme | −23.0 LUFS / −2.3 dBTP / LRA 11.9 LU | −16.0 LUFS / −1.0 dBTP / LRA 11.8 LU |
| Rock, 60 s | −23.9 LUFS / −14.2 dBTP | −16.9 LUFS / −7.2 dBTP |
| Speech show, 90 s | −23.5 LUFS / −10.5 dBTP | −16.5 LUFS / −3.5 dBTP |
| Quiet acoustic music, 60 s | −21.7 LUFS / −2.3 dBTP | −14.7 LUFS / −1.0 dBTP |
| 1 kHz sine, −41 LUFS | −41.1 LUFS | −34.1 LUFS |
| 997 Hz square, full scale | +3.8 LUFS / +2.1 dBTP | +0.6 LUFS / −0.9 dBTP |

Gain ride (output minus input momentary loudness) inside each piece:
0.0 dB standard deviation (0.05 dB in the quiet piece, whose peaks the
limiter catches).  Compared on the same programme: Stereo Tool's AGC
(`[Pre Compressor]`) only engages with at least +12 dB input gain and
with its factory times rides 1.7–3.4 dB inside a song (audible pumping);
a light setting rode 0.6–1.0 dB.  Tune an AGC by ear in the Stereo Tool
application and measure the saved preset before using it.

Test harness: `C:/Temp/optd/stpreset/st_run.liq` (offline run through
the library: `liquidsoap st_run.liq -- <tag> <preset> all_settings
[input.wav]`) and `st_measure.sh` (integrated loudness and true peak of
the three test segments).

Test harness since 2026-11-09: `C:/Temp/optd/stpreset/st_host.py` hosts
ONE library instance through ctypes and processes job files - a
Liquidsoap harness run per preset left an unkillable process holding
about 1 GB every time.  `st_eval.py` measures loudness, true peak and
the gain ride per segment.  Note: `stereoTool_Reset` after
`stereoTool_LoadPreset` throws the loaded settings away - reset first.
