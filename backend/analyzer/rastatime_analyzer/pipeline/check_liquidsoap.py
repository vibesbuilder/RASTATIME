"""
RASTATIME 2026-11-24 - can the playout engine itself decode the file?

The dead air of 2026-11-23 19:07-20:00 (a whole show): an MP3 that the
import's FFmpeg check (``analyze_playability``, the standalone ffmpeg 9)
decoded without a single message was refused by Liquidsoap at playout
time - "Audio_converter.Channel_layout.Unsupported", "Available decoders
cannot decode".  Liquidsoap carries its own, statically linked FFmpeg; it
took that one file for an MPEG program stream.  A lossless remux
(``ffmpeg -map 0 -c copy``, same audio, same tags) made it decodable.

So the import now asks Liquidsoap: a short-lived ``liquidsoap.exe`` (not
the playout instance, no Stereo Tool, no output) resolves the file
against a PCM stereo source - the very check that failed on air - and
prints one ``RESULT <n> true|false`` line per file.  Start ~0.5 s, then
~12 ms per file (300 library files in 3.5 s, 2026-11-24).

Operator decisions 2026-11-24: a file Liquidsoap cannot decode is remuxed
losslessly and checked again, then remuxed without its embedded picture
(a cover made Liquidsoap misdetect a second library file); only when
neither helps is the import refused.  The library scan (API ``scan_liquidsoap_decode``)
uses the same functions.

Fail-open: no Liquidsoap binary, a timeout or an unreadable answer lets
the file through with a warning, so the check can never block imports.
The binary is the one the RASTATIME-LIQUIDSOAP service runs (read from its
NSSM registry entry), so a Liquidsoap upgrade is checked with the new
decoder at once; ``RASTATIME_LIQUIDSOAP_EXE`` overrides it.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Optional

from rastatime_shared.files import compute_md5

from ._ffmpeg import FFMPEG, low_priority_creationflags
from .analyze_playability import UnplayableFileError

logger = logging.getLogger(__name__)

SERVICE_NAME = os.environ.get("RASTATIME_LIQUIDSOAP_SERVICE", "RASTATIME-LIQUIDSOAP")
#: the probe process: start-up plus this much per file
BASE_TIMEOUT_S = 30.0
PER_FILE_TIMEOUT_S = 2.0
REMUX_TIMEOUT_S = 600.0

#: one RESULT line per list entry; the list file is UTF-8, one path per line
PROBE_SCRIPT = """\
settings.log.stdout.set(false)
settings.log.file.set(false)
# the playout bus is PCM stereo: resolve each request against such a source
rt_ref = blank()
output.dummy(rt_ref)
rt_n = ref(0)
def rt_check(f) =
  rt_n := rt_n() + 1
  if f != "" then
    r = request.create(f)
    ok = request.resolve(content_type=rt_ref, r)
    request.destroy(r)
    print("RESULT #{rt_n()} #{ok}")
  end
end
list.iter(rt_check, string.split(separator="\\n", file.contents(argv(default="", 1))))
shutdown()
"""


class LiquidsoapUndecodableError(UnplayableFileError):
    """RASTATIME 2026-11-24 - Liquidsoap cannot decode the file, not even remuxed."""


def _service_binary(service: str) -> Optional[str]:
    """The program the NSSM service runs (HKLM ...\\Services\\<name>\\Parameters\\Application)."""
    if os.name != "nt":
        return None
    try:
        import winreg  # noqa: PLC0415 - Windows only

        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            rf"SYSTEM\CurrentControlSet\Services\{service}\Parameters",
        )
        try:
            value, _kind = winreg.QueryValueEx(key, "Application")
        finally:
            winreg.CloseKey(key)
    except OSError:
        return None
    return str(value) if value else None


def liquidsoap_binary() -> Optional[str]:
    """
    The Liquidsoap executable to check with, or None: RASTATIME_LIQUIDSOAP_EXE,
    else the program of the RASTATIME-LIQUIDSOAP service, else ``liquidsoap``
    on PATH.
    """
    for candidate in (os.environ.get("RASTATIME_LIQUIDSOAP_EXE"), _service_binary(SERVICE_NAME)):
        if candidate and os.path.isfile(candidate):
            return candidate
    return shutil.which("liquidsoap")


def parse_results(stdout: str, count: int) -> list[Optional[bool]]:
    """``RESULT <n> true|false`` lines -> one entry per file (None = no answer)."""
    results: list[Optional[bool]] = [None] * count
    for line in (stdout or "").splitlines():
        parts = line.strip().split()
        if len(parts) != 3 or parts[0] != "RESULT":
            continue
        try:
            index = int(parts[1]) - 1
        except ValueError:
            continue
        if 0 <= index < count and parts[2] in ("true", "false"):
            results[index] = parts[2] == "true"
    return results


def liquidsoap_decodes(paths: Sequence[str], binary: Optional[str] = None) -> list[Optional[bool]]:
    """
    Ask Liquidsoap whether it can decode each file as PCM stereo.  One entry
    per path: True / False, or None when there was no answer (no binary,
    timeout, crash) - the caller treats None as "unknown, let it through".
    """
    if not paths:
        return []
    binary = binary or liquidsoap_binary()
    if not binary:
        return [None] * len(paths)
    timeout = BASE_TIMEOUT_S + PER_FILE_TIMEOUT_S * len(paths)
    with tempfile.TemporaryDirectory(prefix="rt-lsprobe-") as tmp:
        script = Path(tmp) / "probe.liq"
        listing = Path(tmp) / "files.txt"
        script.write_text(PROBE_SCRIPT, encoding="utf-8")
        listing.write_text(
            "\n".join(str(p).replace("\\", "/") for p in paths), encoding="utf-8", newline="\n"
        )
        flags = low_priority_creationflags() | getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            done = subprocess.run(
                [binary, str(script), "--", str(listing)],
                cwd=tmp,
                capture_output=True,
                stdin=subprocess.DEVNULL,
                timeout=timeout,
                check=False,
                creationflags=flags,
            )
        except (OSError, subprocess.SubprocessError) as exception:
            logger.warning("check_liquidsoap: %s did not run: %s", binary, exception)
            return [None] * len(paths)
    results = parse_results(done.stdout.decode("utf-8", "replace"), len(paths))
    if done.returncode != 0 or None in results:
        logger.warning(
            "check_liquidsoap: %s exited %s with %d of %d answers; stderr: %s",
            binary,
            done.returncode,
            sum(r is not None for r in results),
            len(paths),
            done.stderr.decode("utf-8", "replace")[-300:],
        )
    return results


#: the remux variants, tried in this order (operator decisions 2026-11-24):
#: every stream copied; then the audio only - an embedded cover picture made
#: Liquidsoap's FFmpeg take one library MP3 for an MPEG program stream.  The
#: library cover is not lost: the legacy app stores it from the upload
#: (imported/artwork/) before the analyzer runs.
REMUX_VARIANTS = (
    ("lossless remux", ("-map", "0")),
    ("remux without the embedded picture", ("-map", "0:a")),
)

UNDECODABLE = (
    "the playout engine (Liquidsoap) cannot decode it, not even after a lossless remux "
    "(also tried without the embedded picture)"
)


def remux_copy(
    src: Path, dest: Path, ffmpeg: Optional[str] = None, maps: Sequence[str] = ("-map", "0")
) -> None:
    """Remux without re-encoding: the mapped streams and every tag copied into a fresh container."""
    cmd = [
        ffmpeg or FFMPEG, "-hide_banner", "-nostdin", "-nostats", "-loglevel", "error", "-y",
        "-i", str(src), *maps, "-map_metadata", "0", "-c", "copy", str(dest),
    ]  # fmt: skip
    done = subprocess.run(
        cmd,
        capture_output=True,
        stdin=subprocess.DEVNULL,
        timeout=REMUX_TIMEOUT_S,
        check=False,
        creationflags=low_priority_creationflags(),
    )
    if done.returncode != 0 or not dest.is_file() or dest.stat().st_size == 0:
        dest.unlink(missing_ok=True)
        raise OSError(
            f"ffmpeg remux failed (exit {done.returncode}): "
            + done.stderr.decode("utf-8", "replace").strip()[-200:]
        )


def remux_target(src: Path) -> Path:
    """``<stem>.remux<suffix>`` next to *src*, numbered when taken."""
    dest = src.with_name(f"{src.stem}.remux{src.suffix}")
    n = 2
    while dest.exists():
        dest = src.with_name(f"{src.stem}.remux{n}{src.suffix}")
        n += 1
    return dest


def remux_until_decodable(
    src: Path, binary: str, ffmpeg: Optional[str] = None
) -> tuple[Optional[Path], str]:
    """
    Try the REMUX_VARIANTS in order; (remuxed file, variant) for the first
    one Liquidsoap decodes - or does not answer about (fail-open) - else
    (None, why).  Rejected remuxes are removed.
    """
    problems = []
    for variant, maps in REMUX_VARIANTS:
        dest = remux_target(src)
        try:
            remux_copy(src, dest, ffmpeg, maps)
        except (OSError, subprocess.SubprocessError) as exception:
            problems.append(f"{variant}: {exception}")
            continue
        (ok,) = liquidsoap_decodes([str(dest)], binary)
        if ok is not False:
            return dest, variant + ("" if ok else " (second check had no answer)")
        dest.unlink(missing_ok=True)
        problems.append(f"{variant}: not decodable")
    return None, "; ".join(problems)


def check_liquidsoap_decode(
    audio_file_path: str, metadata: dict[str, Any], binary: Optional[str] = None
) -> tuple[str, dict[str, Any]]:
    """
    Pipeline step (after analyze_playability, before organise_file).

    Returns (audio_file_path, metadata): unchanged when Liquidsoap decodes the
    file or cannot be asked; the remuxed sibling (md5 / filesize of the new
    file, ``source_md5`` = the md5 the upload had) when a remux variant is
    decodable.  Raises :class:`LiquidsoapUndecodableError` when none is.
    The file handed in is left in place - the pipeline removes it once the
    remux is filed, like a converted file's original.
    """
    binary = binary or liquidsoap_binary()
    if not binary:
        logger.warning(
            "check_liquidsoap: no Liquidsoap binary found - %s imported without the check",
            audio_file_path,
        )
        return audio_file_path, metadata
    (ok,) = liquidsoap_decodes([audio_file_path], binary)
    if ok is None or ok:
        return audio_file_path, metadata

    src = Path(audio_file_path)
    logger.warning("check_liquidsoap: Liquidsoap cannot decode %s - trying a remux", src.name)
    dest, how = remux_until_decodable(src, binary)
    if dest is None:
        logger.warning("check_liquidsoap: %s refused - %s", src.name, how)
        raise LiquidsoapUndecodableError(UNDECODABLE)
    result = dict(metadata)
    if metadata.get("md5"):
        result.setdefault("source_md5", metadata["md5"])
    result["md5"] = compute_md5(dest)
    result["filesize"] = dest.stat().st_size
    logger.info("check_liquidsoap: %s -> %s (%s) - Liquidsoap decodes it", src.name, dest.name, how)
    return str(dest), result
