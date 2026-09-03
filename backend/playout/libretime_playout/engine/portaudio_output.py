"""
portaudio_output — map a RASTATIME output endpoint to a PortAudio
device index for Liquidsoap's ``output.portaudio``.

RASTATIME 2026-09-03 (BACKLOG "Lokales Monitoring zurück auf die
Tascam-Ausgänge" / Main-Output-Setting wirksam machen).

Why this exists
---------------
``output.portaudio`` without a device argument plays to whatever
Windows currently calls the default endpoint.  The operator's
**Main Output** choice in Settings → Local Machine was therefore
cosmetic for the Liquidsoap engine: the value is stored, pushed to
playout over the source-switcher HTTP listener, and then dropped on
the floor by :meth:`LiquidsoapPlayoutEngine.set_audio_device`, which
is a no-op.  The UI promised a function it did not have.

``output.portaudio`` *does* accept ``device_id`` (a PortAudio device
index) — verified against the installed binary:

    Type: (?id : string?, ?buflen : int, ?device_id : int?,
           ?device_name : string?, ?fallible : bool, ...)

so the only missing piece is the mapping *Windows endpoint →
PortAudio index*.

Why that mapping needs a probe, not a lookup
--------------------------------------------
The same physical endpoint is enumerated once per host API, and which
of those copies actually **opens** is device-specific.  Measured on
the studio machine 2026-09-03, Tascam US-16x08 output:

  ===============  ==============================================
  WASAPI           open fails (PaErrorCode −9996, invalid device)
  MME              open fails (−9999, unanticipated host error)
  DirectSound      start fails (−9999)
  **WDM-KS**       **opens and plays**
  ===============  ==============================================

So we enumerate the candidates, order them least-invasive first, and
probe each by briefly opening it; the first that really opens wins.

The probe MUST use PortAudio's **blocking** API, because that is what
Liquidsoap's ``output.portaudio`` uses.  This is not a detail: a
callback-mode probe reports WDM-KS as working, and Liquidsoap then
dies at device-open with ``Blocking API not supported yet`` followed
by ``Invalid_argument("option is None")`` -- taking the whole process
down, Icecast outputs included.  (RASTATIME 2026-09-03: a
callback-mode probe put the station off air.  ``linein_feeder``
already noted the same limitation for capture; it applies to output
too.)

Measured with the blocking API on the studio machine at 44.1 kHz,
Liquidsoap's internal frame rate:

  ==================  ======  ===========  =======  ======
  Device              MME     DirectSound  WASAPI   WDM-KS
  ==================  ======  ===========  =======  ======
  Jabra EVOLVE LINK   works   works        no       no
  Tascam US-16x08     no      no           no       no
  ==================  ======  ===========  =======  ======

WASAPI rejects 44.1 kHz outright (its shared mix format differs) and
WDM-KS has no blocking support at all, so MME and DirectSound are the
only usable output APIs here.  The **Tascam output cannot be driven by
Liquidsoap at all** -- every blocking open is refused, at 44.1 and at
48 kHz -- so selecting it lands on the OS-default fallback with a
loud log line rather than a working monitor.

Host-API order
--------------
WASAPI → MME → DirectSound → WDM-KS.  WDM-KS is deliberately last: it
is a kernel-streaming path that claims the endpoint **exclusively**,
so no other Windows application can share the device while Liquidsoap
holds it.  On a dedicated broadcast machine that is acceptable — but
only as a fallback, never as a first choice.

Samplerate
----------
Probes run at Liquidsoap's internal frame samplerate (44100 Hz, see
``DEFAULT_SAMPLERATE`` in ``liquidsoap_config``).  This matters: the
Tascam's WDM-KS output accepts 44100 but refuses 48000, so probing at
the wrong rate would reject a device that works in production.
"""

from __future__ import annotations

import logging
import re
import threading
from typing import List, NamedTuple, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

#: Host APIs we will use for the local monitor, best first.  See the
#: module docstring for why WDM-KS is last.
HOST_API_PREFERENCE: Tuple[str, ...] = (
    "WASAPI",
    "MME",
    "DirectSound",
    "WDM-KS",
)

#: Seconds to wait for a single probe open before giving up on that
#: candidate.  A wedged USB-audio driver can block inside the open
#: call; we must not hang the playout start because of it.
PROBE_TIMEOUT_SECONDS = 4.0

#: Liquidsoap's internal frame samplerate.  Kept here so the probe
#: cannot silently drift away from what production actually uses.
DEFAULT_PROBE_SAMPLERATE = 44100


class ResolvedOutput(NamedTuple):
    """A PortAudio output device that was proven to open."""

    index: int
    name: str
    host_api: str
    probed: bool

    @property
    def label(self) -> str:
        return f"{self.name} [{self.host_api}]"


def _host_api_rank(host_api: str) -> int:
    """Sort key: position in HOST_API_PREFERENCE, unknown APIs last."""
    for rank, wanted in enumerate(HOST_API_PREFERENCE):
        if wanted.lower() in host_api.lower():
            return rank
    return len(HOST_API_PREFERENCE)


def _hardware_tokens(names: Sequence[str]) -> List[str]:
    """
    Extract model-ish tokens from parenthesised device-name suffixes.

    PortAudio names the same endpoint differently per host API: the
    Windows friendly name appears in the MME/DirectSound/WASAPI
    variants (``"Tascam-Lautsprecher (US-16x08)"``) but WDM-KS uses
    the driver's own wording (``"Lautsprecher (US-16x08 Audio)"``).
    Matching on the friendly name alone would therefore never find the
    WDM-KS copy — which is exactly the one that works for the Tascam.

    So we pull the hardware model out of the parenthesis (``US-16x08``)
    and use it as a second matching pass.  Only tokens that look like a
    model number (contain a digit, at least 4 characters) qualify, so
    generic words like "Audio" or "Lautsprecher" don't match half the
    system.
    """
    tokens: List[str] = []
    for name in names:
        for inner in re.findall(r"\(([^)]*)\)", name):
            for tok in inner.split():
                tok = tok.strip()
                if len(tok) >= 4 and any(ch.isdigit() for ch in tok):
                    low = tok.lower()
                    if low not in tokens:
                        tokens.append(low)
    return tokens


def find_output_candidates(device_name: str, sd) -> List[Tuple[int, str, str]]:
    """
    Return ``(index, name, host_api)`` output candidates for
    ``device_name``, best host API first.

    Two matching passes — see :func:`_hardware_tokens` for why the
    second one is needed.
    """
    wanted = (device_name or "").strip().lower()
    if not wanted:
        return []

    apis = sd.query_hostapis()
    outputs: List[Tuple[int, str, str]] = []
    for idx, dev in enumerate(sd.query_devices()):
        if dev["max_output_channels"] < 1:
            continue
        outputs.append((idx, dev["name"], apis[dev["hostapi"]]["name"]))

    # Pass 1 — friendly name, exact then substring either way.
    matched = [
        (i, n, a) for i, n, a in outputs if n.strip().lower() == wanted
    ]
    if not matched:
        matched = [
            (i, n, a)
            for i, n, a in outputs
            if wanted in n.strip().lower() or n.strip().lower() in wanted
        ]

    # Pass 2 — same hardware under a different host-API wording.
    tokens = _hardware_tokens([n for _, n, _ in matched])
    if tokens:
        seen = {i for i, _, _ in matched}
        for i, n, a in outputs:
            if i in seen:
                continue
            low = n.lower()
            if any(tok in low for tok in tokens):
                matched.append((i, n, a))

    matched.sort(key=lambda row: _host_api_rank(row[2]))
    return matched


def probe_output(
    index: int,
    sd,
    *,
    samplerate: int = DEFAULT_PROBE_SAMPLERATE,
    channels: int = 2,
    timeout: float = PROBE_TIMEOUT_SECONDS,
) -> Tuple[bool, str]:
    """
    Briefly open ``index`` as an output and close it again.

    Returns ``(ok, detail)``.  The stream is fed silence, so the probe
    is inaudible.  The open runs in a worker thread with a timeout:
    a wedged driver blocks *inside* PortAudio, and we would rather
    skip that candidate than hang the playout service start.

    The thread is never force-killed — that is what wedges Windows
    audio drivers (learned the hard way 2026-09-02).  On timeout we
    simply abandon the candidate and let the daemon thread finish on
    its own.
    """
    result = {"ok": False, "detail": ""}

    def _worker() -> None:
        stream = None
        try:
            stream = sd.RawOutputStream(
                samplerate=samplerate,
                channels=channels,
                dtype="int16",
                device=index,
            )
            stream.start()
            # The write is the point of the probe: some endpoints open
            # and only refuse once data is actually pushed through the
            # blocking path (DirectSound on the Tascam does exactly that).
            stream.write(bytes(1024 * channels * 2))
            result["ok"] = True
        except Exception as exc:  # pylint: disable=broad-exception-caught
            result["detail"] = f"{type(exc).__name__}: {exc}"
        finally:
            if stream is not None:
                try:
                    stream.stop()
                    stream.close()
                except Exception:  # pylint: disable=broad-exception-caught
                    pass

    worker = threading.Thread(
        target=_worker, name=f"portaudio-probe-{index}", daemon=True
    )
    worker.start()
    worker.join(timeout=timeout)
    if worker.is_alive():
        return False, f"open blocked for >{timeout:.0f}s"
    return bool(result["ok"]), str(result["detail"])


def resolve_output_device(
    device_name: str,
    *,
    samplerate: int = DEFAULT_PROBE_SAMPLERATE,
    channels: int = 2,
    probe: bool = True,
) -> Optional[ResolvedOutput]:
    """
    Resolve the operator's Main-Output endpoint to a PortAudio device.

    ``device_name`` is the Windows friendly name persisted alongside
    the endpoint GUID (``SoundcardSettings.main_output_name``).  We
    match on the name rather than the GUID because PortAudio has no
    notion of Windows endpoint IDs.

    Returns the first candidate that actually opens, or ``None`` when
    nothing matches / nothing opens.  ``None`` means "render
    ``output.portaudio`` without a device argument", i.e. fall back to
    the OS-default endpoint — the previous behaviour, which is a safe
    place to land.

    Set ``probe=False`` to skip the open test (unit tests, or an
    operator override when probing itself is the problem); the
    best-ranked candidate is then returned unverified.
    """
    try:
        import sounddevice as sd  # noqa: PLC0415  (deferred: optional dep)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning(
            "Cannot resolve audio output %r — sounddevice unavailable: %s. "
            "Falling back to the OS-default endpoint.", device_name, exc,
        )
        return None

    candidates = find_output_candidates(device_name, sd)
    if not candidates:
        logger.warning(
            "Main Output %r matches no PortAudio output device — falling "
            "back to the OS-default endpoint.  (Re-save the Main Output "
            "picker in Settings → Local Machine if the device was renamed.)",
            device_name,
        )
        return None

    logger.info(
        "Main Output %r → %d PortAudio candidate(s): %s",
        device_name, len(candidates),
        ", ".join(f"{n} [{a}]" for _, n, a in candidates),
    )

    if not probe:
        idx, name, api = candidates[0]
        return ResolvedOutput(index=idx, name=name, host_api=api, probed=False)

    tried: List[str] = []
    for idx, name, api in candidates:
        ok, detail = probe_output(
            idx, sd, samplerate=samplerate, channels=channels
        )
        if ok:
            logger.info(
                "Main Output resolved: PortAudio device %d — %s [%s] "
                "(probe at %d Hz succeeded)", idx, name, api, samplerate,
            )
            return ResolvedOutput(index=idx, name=name, host_api=api, probed=True)
        tried.append(f"{api}: {detail or 'open failed'}")

    logger.error(
        "Main Output %r: no candidate could be opened at %d Hz — tried %s.  "
        "Falling back to the OS-default endpoint; the local monitor will "
        "not follow the Main Output setting.",
        device_name, samplerate, " | ".join(tried),
    )
    return None
