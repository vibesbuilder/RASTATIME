"""
libVLC runtime probe for RASTATIME.

Checks that python-vlc is importable, that a compatible libvlc.dll is
discoverable, and that the bitness of Python and VLC match.

Usage
-----
Run directly to print a human-readable report::

    python -m playout.engine_vlc.probe

Or call programmatically::

    from playout.engine_vlc.probe import probe, ProbeResult
    result = probe()
    result.raise_if_unavailable()   # raises RuntimeError if not usable

Supported VLC versions
----------------------
* VLC 3.0.x  "Vetinari"  (recommended, tested: 3.0.23)
* VLC 4.0.x  not yet validated

Bitness requirement
-------------------
The Python interpreter and the VLC installation must use the same bitness
(both 64-bit or both 32-bit).  Mixing them causes ``OSError`` when
``libvlc.dll`` is loaded.  On a modern Windows 11 machine use 64-bit Python
and the 64-bit VLC installer from https://www.videolan.org/vlc/download-windows.html
"""

from __future__ import annotations

import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Known libvlc.dll locations on Windows (searched in order)
# ---------------------------------------------------------------------------

_KNOWN_DLL_PATHS: list[Path] = [
    Path(r"C:\Program Files\VideoLAN\VLC\libvlc.dll"),
    Path(r"C:\Program Files (x86)\VideoLAN\VLC\libvlc.dll"),
]


def _find_dll_via_registry() -> Optional[Path]:
    """Try HKLM\\SOFTWARE\\VideoLAN\\VLC InstallDir registry key."""
    try:
        import winreg  # noqa: PLC0415 — Windows only
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\VideoLAN\VLC",
        )
        install_dir, _ = winreg.QueryValueEx(key, "InstallDir")
        winreg.CloseKey(key)
        candidate = Path(install_dir) / "libvlc.dll"
        if candidate.exists():
            return candidate
    except Exception:  # noqa: BLE001
        pass
    return None


def _find_dll() -> Optional[Path]:
    """Return the first libvlc.dll path found, or None."""
    for path in _KNOWN_DLL_PATHS:
        if path.exists():
            return path
    return _find_dll_via_registry()


def _python_bits() -> int:
    return struct.calcsize("P") * 8


def _dll_bits(dll_path: Path) -> Optional[int]:
    """
    Read the PE header of *dll_path* to determine bitness.

    Returns 32, 64, or None if the file cannot be parsed.
    """
    try:
        with dll_path.open("rb") as fh:
            # DOS header: MZ signature + offset to PE header at 0x3C
            mz = fh.read(2)
            if mz != b"MZ":
                return None
            fh.seek(0x3C)
            pe_offset = struct.unpack("<I", fh.read(4))[0]
            fh.seek(pe_offset)
            pe_sig = fh.read(4)
            if pe_sig != b"PE\x00\x00":
                return None
            machine = struct.unpack("<H", fh.read(2))[0]
            # 0x8664 = AMD64 (64-bit); 0x014C = i386 (32-bit)
            if machine == 0x8664:
                return 64
            if machine == 0x014C:
                return 32
    except Exception:  # noqa: BLE001
        pass
    return None


# ---------------------------------------------------------------------------
# ProbeResult
# ---------------------------------------------------------------------------

@dataclass
class ProbeResult:
    """
    Result of a libVLC availability probe.

    Attributes
    ----------
    available:
        *True* if python-vlc loaded and ``vlc.Instance()`` was created
        successfully.
    python_vlc_version:
        Version string of the installed ``python-vlc`` package, or *None*.
    libvlc_version:
        Version string reported by the loaded libvlc library, or *None*.
    dll_path:
        Absolute path to the ``libvlc.dll`` that was found, or *None*.
    python_bits:
        Bitness of the running Python interpreter (32 or 64).
    vlc_bits:
        Bitness read from the PE header of ``libvlc.dll``, or *None*.
    errors:
        List of human-readable error strings; empty when ``available=True``.
    """

    available: bool
    python_vlc_version: Optional[str] = None
    libvlc_version: Optional[str] = None
    dll_path: Optional[Path] = None
    python_bits: int = field(default_factory=_python_bits)
    vlc_bits: Optional[int] = None
    errors: list = field(default_factory=list)  # list[str]

    def raise_if_unavailable(self) -> None:
        """Raise :class:`RuntimeError` if the probe did not succeed."""
        if not self.available:
            msg = "; ".join(self.errors) if self.errors else "libVLC unavailable"
            raise RuntimeError(f"libVLC probe failed: {msg}")

    def summary(self) -> str:
        """Return a single-line human-readable summary."""
        if self.available:
            return (
                f"OK — libvlc {self.libvlc_version} | "
                f"python-vlc {self.python_vlc_version} | "
                f"DLL {self.dll_path} ({self.vlc_bits}-bit)"
            )
        return "UNAVAILABLE — " + "; ".join(self.errors)


# ---------------------------------------------------------------------------
# Main probe function
# ---------------------------------------------------------------------------

def probe() -> ProbeResult:
    """
    Run the full libVLC availability check and return a :class:`ProbeResult`.

    This function never raises; all errors are captured in
    ``ProbeResult.errors``.
    """
    errors: list[str] = []
    python_bits = _python_bits()

    # 1. Import python-vlc ---------------------------------------------------
    try:
        import vlc  # noqa: PLC0415
    except ImportError as exc:
        errors.append(f"python-vlc not importable: {exc}")
        return ProbeResult(
            available=False,
            python_bits=python_bits,
            errors=errors,
        )

    python_vlc_version: Optional[str] = getattr(vlc, "__version__", None)

    # 2. Locate libvlc.dll ---------------------------------------------------
    dll_path = _find_dll()
    vlc_bits: Optional[int] = None
    if dll_path is None:
        errors.append(
            "libvlc.dll not found in known paths "
            "(C:\\Program Files\\VideoLAN\\VLC\\) or registry"
        )
    else:
        vlc_bits = _dll_bits(dll_path)

    # 3. Bitness compatibility -----------------------------------------------
    if vlc_bits is not None and vlc_bits != python_bits:
        errors.append(
            f"Bitness mismatch: Python is {python_bits}-bit "
            f"but libvlc.dll is {vlc_bits}-bit. "
            f"Install the {'64' if python_bits == 64 else '32'}-bit VLC."
        )

    # 4. Obtain libvlc version string ----------------------------------------
    libvlc_version: Optional[str] = None
    try:
        raw = vlc.libvlc_get_version()
        libvlc_version = raw.decode() if isinstance(raw, bytes) else str(raw)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"vlc.libvlc_get_version() failed: {exc}")

    # 5. Instantiate vlc.Instance() ------------------------------------------
    try:
        inst = vlc.Instance("--no-video-title-show")
        if inst is None:
            errors.append("vlc.Instance() returned None")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"vlc.Instance() raised: {exc}")

    available = len(errors) == 0
    return ProbeResult(
        available=available,
        python_vlc_version=python_vlc_version,
        libvlc_version=libvlc_version,
        dll_path=dll_path,
        python_bits=python_bits,
        vlc_bits=vlc_bits,
        errors=errors,
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _print_report(result: ProbeResult) -> None:
    sep = "-" * 60
    print(sep)
    print("RASTATIME - libVLC probe report")
    print(sep)
    print(f"  Status        : {'OK' if result.available else 'UNAVAILABLE'}")
    print(f"  python-vlc    : {result.python_vlc_version or 'n/a'}")
    print(f"  libvlc        : {result.libvlc_version or 'n/a'}")
    print(f"  DLL path      : {result.dll_path or 'not found'}")
    print(f"  Python bits   : {result.python_bits}")
    print(f"  VLC bits      : {result.vlc_bits or 'unknown'}")
    if result.errors:
        print()
        print("  Errors:")
        for err in result.errors:
            print(f"    - {err}")
    print(sep)


if __name__ == "__main__":
    result = probe()
    _print_report(result)
    sys.exit(0 if result.available else 1)
