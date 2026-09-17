"""
PreflightChecker — lookahead scanner that warns the operator about
problems in the next 48 h of the schedule **before** the show is on-air.

Phase B.4 #2 (RASTATIME 2026-05-13)
-----------------------------------
First warning type emitted: ``linein_device_unavailable`` — a scheduled
Line-In show references an audio input device that is **not currently
visible** to the host's :class:`AudioDeviceManager`.  Typical cause:
the operator unplugged the USB mic / soundcard since the show was
planned.

How it runs
-----------
* Owned by ``__main__`` after the scheduler is initialised.
* Daemon ``threading.Timer`` chain — first scan fires ~10 s after boot
  so the dashboard never shows a stale snapshot from the previous
  service run; subsequent scans fire every ``SCAN_INTERVAL_SECS``.
* Each scan is *atomic per warning_type* — the API's
  ``/preflight/warnings/replace`` endpoint deletes the previous batch
  and writes the new one in a single transaction, so the frontend
  never reads a half-updated state.

Why not in the existing 120-s scheduler refresh()?
--------------------------------------------------
* Different cadence (15 min vs 120 s) — running pre-flight on every
  refresh would hammer the show/show-instance API endpoints.
* Different failure mode — refresh() failure means audio doesn't play;
  pre-flight failure just means the dashboard banner is briefly stale.
  Decoupling them lets each path use its own retry / logging policy.
* Pre-flight has *no live audio responsibility* — keeping it physically
  separate from the scheduler keeps the audio hot-path simple.

Adding new warning types later
------------------------------
Subclass-style is overkill — instead, add a new ``_scan_<type>()``
method, call it from ``scan_once()``, and submit its result via
``_submit_warnings("<type>", ..., warnings=...)``.  The DB and API
both already support arbitrary ``warning_type`` strings.
"""

from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime, timedelta
from typing import Optional, Set

from libretime_api_client.v2 import ApiClient

from libretime_playout import liquidsoap_health

logger = logging.getLogger(__name__)


class PreflightChecker:
    """
    Periodic lookahead scanner for schedule-related warnings.  See module
    docstring for the broader contract; per-method docstrings below
    describe the individual responsibilities.
    """

    # ------------------------------------------------------------------
    # Tunable constants
    # ------------------------------------------------------------------
    SCAN_INTERVAL_SECS = 15 * 60   # 15 minutes between scans
    LOOKAHEAD_HOURS    = 48        # warn about shows up to 48 h out
    FIRST_SCAN_DELAY_SECS = 10.0   # ~10 s after boot, run the first scan

    # Warning-type discriminator constants — also the value the
    # frontend looks for in the JSON.  Add new ones here when you
    # introduce more warning kinds.
    WARNING_TYPE_LINEIN_UNAVAILABLE = "linein_device_unavailable"
    # RASTATIME 2026-09-05 — Liquidsoap process health (see
    # liquidsoap_health.py for the why of both).
    WARNING_TYPE_LIQUIDSOAP_MEMORY = "liquidsoap_memory_high"
    WARNING_TYPE_MAIN_OUTPUT_SESSION = "main_output_session_missing"
    # RASTATIME 2026-09-07: no liquidsoap.exe at all, or a fresh PID on
    # every scan (NSSM throttling a crash loop).
    WARNING_TYPE_LIQUIDSOAP_UNAVAILABLE = "liquidsoap_unavailable"
    #: RASTATIME 2026-09-16 - the media library root (Local Machine setting)
    #: is missing or not writable (drive gone, wrong path).
    WARNING_TYPE_STORAGE_ROOT = "storage_root_unavailable"

    # ------------------------------------------------------------------
    # Construction & lifecycle
    # ------------------------------------------------------------------

    def __init__(self, api_client: ApiClient) -> None:
        self._api_client = api_client
        self._timer: Optional[threading.Timer] = None
        self._stop_event = threading.Event()
        # Light caches to avoid hammering /shows and /show-instances
        # for repeated rows of the same show.  Cleared every scan so
        # rename / move edits show up within one scan cycle.
        self._show_cache: dict[int, dict] = {}
        self._show_instance_cache: dict[int, dict] = {}
        self._linein_cache: dict[int, dict] = {}
        # (pid, age_seconds) of the youngest liquidsoap.exe seen on the
        # last few scans - a crash loop shows as a new young PID each time.
        self._liquidsoap_recent: list[tuple[int, float]] = []
        # RASTATIME 2026-09-15 - first memory sample per main instance
        # (pid -> (private_mb, age_seconds)); every scan logs the growth
        # since then so the memory trend is in the playout log.
        self._liquidsoap_memory_baseline: dict[int, tuple[float, float]] = {}

    def start(self) -> None:
        """
        Begin the timer chain.  Idempotent — calling twice is a no-op.

        The first scan fires ``FIRST_SCAN_DELAY_SECS`` after start (NOT
        immediately) so the boot sequence stays fast and the API service
        has time to be healthy if the two services start in parallel.
        """
        if self._timer is not None:
            return
        self._stop_event.clear()
        logger.info(
            "PreflightChecker: starting (first scan in %.0fs, "
            "subsequent scans every %.0fs, lookahead %dh)",
            self.FIRST_SCAN_DELAY_SECS,
            self.SCAN_INTERVAL_SECS,
            self.LOOKAHEAD_HOURS,
        )
        self._schedule_next_scan(self.FIRST_SCAN_DELAY_SECS)

    def stop(self) -> None:
        """
        Cancel the pending timer and prevent further scans.

        Does NOT clear the warning table — the last-known state stays
        visible to the frontend across service restarts.  That is the
        right default: if the playout dies mid-shift, operators should
        keep seeing the most recent warnings (better than thinking
        "all clear" while the scanner is offline).
        """
        self._stop_event.set()
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        logger.info("PreflightChecker: stopped.")

    # ------------------------------------------------------------------
    # Timer plumbing
    # ------------------------------------------------------------------

    def _schedule_next_scan(self, delay_secs: float) -> None:
        if self._stop_event.is_set():
            return
        self._timer = threading.Timer(delay_secs, self._tick)
        self._timer.daemon = True
        self._timer.name = "PreflightChecker"
        self._timer.start()

    def _tick(self) -> None:
        """One scan + arm the next timer.  Exceptions are swallowed and
        logged — the chain MUST keep going even if a single scan blows
        up, otherwise the operator loses pre-flight after the first
        transient API hiccup."""
        try:
            self.scan_once()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error(
                "PreflightChecker scan failed: %s", exc, exc_info=True,
            )
        finally:
            self._schedule_next_scan(self.SCAN_INTERVAL_SECS)

    # ------------------------------------------------------------------
    # Scan implementation
    # ------------------------------------------------------------------

    def scan_once(self) -> None:
        """
        Run one complete scan cycle.

        Currently does:

          1. ``_scan_linein_devices`` — checks each scheduled Line-In
             item against the live :class:`AudioDeviceManager` and
             emits ``linein_device_unavailable`` warnings.
          2. ``_scan_liquidsoap_health`` — private bytes of the
             Liquidsoap process (``liquidsoap_memory_high``) and
             whether its audio session sits on the configured Main
             Output endpoint (``main_output_session_missing``).

        When more warning types are added, call them here too.  Each
        type submits its own atomic replace, so a failure in one does
        not stomp on the others.
        """
        # Clear caches between scans so stale rename / move edits
        # don't keep getting served from local cache.
        self._show_cache.clear()
        self._show_instance_cache.clear()
        self._linein_cache.clear()

        self._scan_linein_devices()
        self._scan_liquidsoap_health()
        self._scan_storage_root()

    # ------------------------------------------------------------------
    # Liquidsoap process health (RASTATIME 2026-09-05)
    # ------------------------------------------------------------------

    def _scan_liquidsoap_health(self) -> None:
        """
        Two warnings about the running Liquidsoap instance:

        * ``liquidsoap_memory_high`` — private bytes above
          ``RASTATIME_LIQUIDSOAP_MEMORY_WARN_MB`` (default 2048).  The
          savonet Windows build leaks in ``Unix.select``; the template's
          synchronous queue removed the permanent poller and the nightly
          restart is the safety net, but a runaway instance must be
          visible before it exhausts the machine (3.4 GB after two
          hours on 2026-09-05).
        * ``main_output_session_missing`` — the process holds no audio
          session on the configured Main Output endpoint although it
          has been up for a while.  That is what the 2026-09-05 index
          drift looked like from the outside: hours of silence on the
          Tascam, Liquidsoap happily playing to the Realtek jack.

        Both probes return ``None`` when they cannot run; a probe that
        cannot run clears its warning type rather than inventing one.
        """
        infos = liquidsoap_health.liquidsoap_process_info()
        if infos is not None:
            # RASTATIME 2026-09-09 - the standby source is a second
            # liquidsoap.exe; judge only the main instance (rastatime.liq).
            # A standby-only table therefore means "Liquidsoap is down".
            infos = liquidsoap_health.main_instances(infos)
        memory_warnings: list[dict] = []
        session_warnings: list[dict] = []
        unavailable_warnings: list[dict] = []
        if infos is None:
            logger.debug("preflight: Liquidsoap process probe unavailable.")
        else:
            self._log_liquidsoap_memory(infos)
            threshold = liquidsoap_health.memory_warn_threshold_mb()
            for info in infos:
                if info.private_mb >= threshold:
                    memory_warnings.append({
                        "severity": "error" if info.private_mb >= 2 * threshold else "warning",
                        "show_id": None,
                        "show_instance_id": None,
                        "starts_at": None,
                        "detail": {
                            "pid": info.pid,
                            "private_mb": int(info.private_mb),
                            "threshold_mb": int(threshold),
                            "age_seconds": int(info.age_seconds),
                            "message": (
                                f"Liquidsoap (PID {info.pid}) uses {int(info.private_mb)} MB "
                                f"(threshold {int(threshold)} MB) — restart PLAYOUT, then "
                                "LIQUIDSOAP, in a quiet moment."
                            ),
                        },
                    })
            session_warnings = self._main_output_session_warnings(infos)
            unavailable_warnings = self._liquidsoap_unavailable_warnings(infos)
        self._submit_warnings(
            self.WARNING_TYPE_LIQUIDSOAP_MEMORY, str(uuid.uuid4()), memory_warnings,
        )
        self._submit_warnings(
            self.WARNING_TYPE_MAIN_OUTPUT_SESSION, str(uuid.uuid4()), session_warnings,
        )
        self._submit_warnings(
            self.WARNING_TYPE_LIQUIDSOAP_UNAVAILABLE, str(uuid.uuid4()), unavailable_warnings,
        )

    def _log_liquidsoap_memory(
        self, infos: list["liquidsoap_health.ProcessInfo"],
    ) -> None:
        """
        RASTATIME 2026-09-15 - one INFO line per scan and main instance:
        private bytes, age, growth since the first sample of this
        instance and the average rate.  The memory week of 2026-09-08..15
        had no record of the trend (the instance rarely lived longer than
        a day and nobody logged the readings); this line, every 15 min,
        makes the next evaluation a grep instead of a measuring session.
        A new PID or a younger age than the baseline is a fresh instance
        and starts a new baseline; the standby instance is filtered out
        by the caller.
        """
        seen: set[int] = set()
        for info in infos:
            seen.add(info.pid)
            base = self._liquidsoap_memory_baseline.get(info.pid)
            if base is None or info.age_seconds < base[1]:
                self._liquidsoap_memory_baseline[info.pid] = (info.private_mb, info.age_seconds)
                logger.info(
                    "preflight: Liquidsoap memory: PID %d %d MB, %.1f h old "
                    "(first sample of this instance).",
                    info.pid, int(info.private_mb), info.age_seconds / 3600.0,
                )
                continue
            base_mb, base_age = base
            span_h = (info.age_seconds - base_age) / 3600.0
            grown = info.private_mb - base_mb
            rate = f", {grown / span_h:.1f} MB/h" if span_h >= 0.5 else ""
            logger.info(
                "preflight: Liquidsoap memory: PID %d %d MB, %.1f h old, "
                "%+d MB since the first sample %.1f h ago%s.",
                info.pid, int(info.private_mb), info.age_seconds / 3600.0,
                int(round(grown)), span_h, rate,
            )
        for pid in list(self._liquidsoap_memory_baseline):
            if pid not in seen:
                del self._liquidsoap_memory_baseline[pid]

    def _scan_storage_root(self) -> None:
        """
        RASTATIME 2026-09-16 - ``storage_root_unavailable``: the effective
        media library root (``GET /api/v2/storage/location``) does not exist
        or is not writable.  An old API without the endpoint, or an
        unreachable one, submits nothing (the type is left as it was).
        """
        getter = getattr(self._api_client, "get_storage_location", None)
        if getter is None:
            return
        try:
            data = getter().json()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.debug("preflight: storage location unavailable: %s", exc)
            return
        if not isinstance(data, dict) or "root" not in data:
            return
        warnings: list[dict] = []
        root = str(data.get("root") or "")
        exists = bool(data.get("exists"))
        writable = bool(data.get("writable"))
        if not exists or not writable:
            problem = "is missing" if not exists else "is not writable"
            warnings.append({
                "severity": "error",
                "show_id": None,
                "show_instance_id": None,
                "starts_at": None,
                "detail": {
                    "root": root,
                    "source": data.get("source"),
                    "exists": exists,
                    "writable": writable,
                    "message": (
                        f"Media library location {root} {problem} - check the drive, "
                        "then Settings -> Local Machine."
                    ),
                },
            })
        self._submit_warnings(self.WARNING_TYPE_STORAGE_ROOT, str(uuid.uuid4()), warnings)

    def _liquidsoap_unavailable_warnings(
        self, infos: list["liquidsoap_health.ProcessInfo"],
    ) -> list[dict]:
        """
        ``liquidsoap_unavailable``: no ``liquidsoap.exe`` at all, or a
        new young PID on consecutive scans.

        RASTATIME 2026-09-07: after the 04:01 nightly restart the fresh
        instance could not open its Main Output (device index shifted
        while the display slept), died within 2 s and NSSM throttled it
        into a crash loop until the operator restarted at 08:21 - and
        this checker said "no warnings active" the whole time, because
        the session watchdog only judges processes older than
        ``MIN_PROCESS_AGE_SECONDS``.  Never again.
        """
        youngest = min(infos, key=lambda i: i.age_seconds) if infos else None
        if youngest is not None:
            self._liquidsoap_recent.append((youngest.pid, youngest.age_seconds))
            del self._liquidsoap_recent[:-4]
        recent_pids = sorted({pid for pid, _ in self._liquidsoap_recent})
        base = {"show_id": None, "show_instance_id": None, "starts_at": None}
        if not infos:
            return [{
                "severity": "error",
                **base,
                "detail": {
                    "crash_loop": False,
                    "pids": recent_pids,
                    "message": (
                        "Liquidsoap is not running (no liquidsoap.exe process).  If "
                        "NSSM is throttling a crash loop, the newest "
                        "logs/liquidsoap-stdout-*.log says why (Main Output "
                        "device?).  Fix the cause, then restart PLAYOUT, "
                        "then LIQUIDSOAP."
                    ),
                },
            }]
        young_limit = liquidsoap_health.MIN_PROCESS_AGE_SECONDS
        young_pids = sorted({
            pid for pid, age in self._liquidsoap_recent if age < young_limit
        })
        if youngest.age_seconds < young_limit and len(young_pids) >= 2:
            return [{
                "severity": "error",
                **base,
                "detail": {
                    "crash_loop": True,
                    "pids": young_pids,
                    "message": (
                        f"Liquidsoap keeps restarting (PIDs "
                        f"{', '.join(str(p) for p in young_pids)} within the last "
                        "scans) - a crash loop, most likely the Main Output device.  "
                        "Read the newest logs/liquidsoap-stdout-*.log, fix the "
                        "cause, then restart PLAYOUT, then LIQUIDSOAP."
                    ),
                },
            }]
        return []

    def _main_output_session_warnings(
        self, infos: list["liquidsoap_health.ProcessInfo"],
    ) -> list[dict]:
        """Warn when no old-enough Liquidsoap process has a session on the Main Output."""
        expected = self._expected_main_output_name()
        if not expected:
            return []
        mature = [i for i in infos if i.age_seconds >= liquidsoap_health.MIN_PROCESS_AGE_SECONDS]
        if not mature:
            return []
        sessions = liquidsoap_health.render_endpoint_sessions()
        if sessions is None:
            logger.debug("preflight: render endpoint sessions unavailable.")
            return []
        pids = [i.pid for i in mature]
        holding = liquidsoap_health.endpoints_holding(sessions, pids)
        if any(liquidsoap_health.endpoint_matches(expected, name) for name in holding):
            return []
        actual = ", ".join(holding) if holding else "no render endpoint"
        return [{
            "severity": "error",
            "show_id": None,
            "show_instance_id": None,
            "starts_at": None,
            "detail": {
                "expected": expected,
                "actual": holding,
                "pids": pids,
                "message": (
                    f"Liquidsoap plays its Main Output to {actual}, not to "
                    f"'{expected}' — restart PLAYOUT, then LIQUIDSOAP."
                ),
            },
        }]

    @staticmethod
    def _expected_main_output_name() -> str:
        """Main Output friendly name from Settings → Local Machine ('' when unset/disabled)."""
        import os  # noqa: PLC0415
        if os.environ.get("RASTATIME_LIQUIDSOAP_LOCAL_OUTPUT", "true").strip().lower() in (
            "0", "false", "no", "off",
        ):
            return ""
        try:
            from libretime_api.soundcard.models import SoundcardSettings  # noqa: PLC0415
            row = SoundcardSettings.get_settings()
            return (row.main_output_name or "").strip()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.debug("preflight: Main Output setting unavailable: %s", exc)
            return ""

    # ------------------------------------------------------------------
    # Line-In device availability
    # ------------------------------------------------------------------

    def _scan_linein_devices(self) -> None:
        """
        Walk the next ``LOOKAHEAD_HOURS`` of the schedule, find every
        Line-In item, and flag those whose device is currently absent
        from the host's audio-input list.
        """
        scan_run_id = str(uuid.uuid4())

        try:
            schedule = self._fetch_lookahead_schedule()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning(
                "preflight: schedule fetch failed (%s) — leaving previous "
                "warnings in place.", exc,
            )
            return

        linein_items = [s for s in schedule if s.get("linein")]

        # Probe the live device manager.  If we can't probe at all (no
        # manager wired, or list_inputs raised), DO NOT mass-emit
        # "unavailable" warnings — that would scare the operator on
        # every restart of a non-Windows dev box.  Skip the scan
        # cleanly instead.
        snapshot = self._get_available_input_device_snapshot()
        if snapshot is None:
            logger.warning(
                "preflight: AudioDeviceManager not ready — skipping "
                "linein scan (no warnings will be cleared either; "
                "previous state stays visible).",
            )
            return
        available_ids, available_names = snapshot

        # Build warning list, deduplicated by (show_instance_id, device_id).
        # Same mic referenced N times by the same show should produce ONE
        # warning, not N.  Across different shows, however, each show
        # gets its own row — the operator needs to know about every
        # affected slot.
        seen_dedup_keys: Set[tuple] = set()
        warnings: list[dict] = []

        for item in linein_items:
            linein_pk = item.get("linein")
            try:
                linein_pk_int = int(linein_pk)
            except (TypeError, ValueError):
                continue

            linein_info = self._fetch_linein(linein_pk_int)
            if linein_info is None:
                # Broken FK — silently skip; show is broken in a
                # different way that this warning type doesn't cover.
                continue

            device_id = str(linein_info.get("device_id") or "").strip().lower()
            if not device_id:
                continue
            if device_id in available_ids:
                continue  # device is present — no warning needed

            # RASTATIME 2026-05-14 — B.4 #4: name-based fallback for USB
            # devices whose endpoint GUID shifted since the linein row
            # was last saved.  If the saved device_name matches an
            # active input by friendly-name, treat the device as
            # available and skip the warning — the playout's
            # ffmpeg_linein_capture will pick it up via the same
            # fallback when the show actually starts.
            device_name = (
                str(linein_info.get("device_name") or "").strip().lower()
            )
            if device_name and device_name in available_names:
                continue

            instance_id = item.get("instance")
            dedup_key = (instance_id, device_id)
            if dedup_key in seen_dedup_keys:
                continue
            seen_dedup_keys.add(dedup_key)

            # Look up display name + show id for the dashboard banner.
            show_name = "?"
            show_id: Optional[int] = None
            starts_at = item.get("starts_at")

            instance_info = self._fetch_show_instance(instance_id)
            if instance_info is not None:
                show_id = instance_info.get("show")
                starts_at = instance_info.get("starts_at", starts_at)
                if show_id is not None:
                    show_info = self._fetch_show(show_id)
                    if show_info is not None:
                        show_name = show_info.get("name", "?")

            warnings.append({
                "severity":         "warning",
                "show_id":          show_id,
                "show_instance_id": instance_id,
                "starts_at":        starts_at,
                "detail": {
                    "linein_id":   linein_pk_int,
                    "linein_name": linein_info.get("name", "?"),
                    "device_id":   device_id,
                    "show_name":   show_name,
                },
            })

        self._submit_warnings(
            self.WARNING_TYPE_LINEIN_UNAVAILABLE, scan_run_id, warnings,
        )

    # ------------------------------------------------------------------
    # API helpers
    # ------------------------------------------------------------------

    def _fetch_lookahead_schedule(self) -> list[dict]:
        """Fetch the schedule between ``now`` and ``now + LOOKAHEAD_HOURS``."""
        now = datetime.utcnow()
        end = now + timedelta(hours=self.LOOKAHEAD_HOURS)
        params = {
            "ends_after":  f"{now.isoformat(timespec='seconds')}Z",
            "ends_before": f"{end.isoformat(timespec='seconds')}Z",
            "overbooked":  False,
            "position_status__gt": 0,
        }
        return self._api_client.list_schedule(params=params).json()

    def _fetch_linein(self, pk: int) -> Optional[dict]:
        """
        GET /api/v2/audio/linein/<pk>.  Cached per scan.  Pass only
        the path — the api_client.Session prepends base_url itself
        (see :func:`libretime_playout.player.schedule._fetch_linein_by_pk`
        for the same caveat).
        """
        if pk in self._linein_cache:
            return self._linein_cache[pk]
        try:
            resp = self._api_client.session.get(
                f"/api/v2/audio/linein/{pk}", timeout=5,
            )
        except Exception:  # pylint: disable=broad-exception-caught
            return None
        if resp.status_code != 200:
            return None
        try:
            data = resp.json()
        except Exception:  # pylint: disable=broad-exception-caught
            return None
        self._linein_cache[pk] = data
        return data

    def _fetch_show_instance(self, pk) -> Optional[dict]:
        if pk in self._show_instance_cache:
            return self._show_instance_cache[pk]
        try:
            data = self._api_client.get_show_instance(pk).json()
        except Exception:  # pylint: disable=broad-exception-caught
            return None
        self._show_instance_cache[pk] = data
        return data

    def _fetch_show(self, pk) -> Optional[dict]:
        if pk in self._show_cache:
            return self._show_cache[pk]
        try:
            data = self._api_client.get_show(pk).json()
        except Exception:  # pylint: disable=broad-exception-caught
            return None
        self._show_cache[pk] = data
        return data

    def _get_available_input_device_ids(self) -> Optional[Set[str]]:
        """
        Return the set of currently-visible input stable_ids (lower-cased)
        or ``None`` if the manager is not wired.  ``None`` is the signal
        for the caller to skip the scan rather than emit warnings.
        """
        snap = self._get_available_input_device_snapshot()
        if snap is None:
            return None
        ids, _names = snap
        return ids

    def _get_available_input_device_snapshot(
        self,
    ) -> Optional[tuple[Set[str], Set[str]]]:
        """
        Return ``(stable_ids, friendly_names_lower)`` from one snapshot of
        the audio manager, or ``None`` if the manager is not wired.

        RASTATIME 2026-05-14 — B.4 #4: the names set lets the scanner
        recognise a USB device that's physically present even when its
        WASAPI endpoint GUID has shifted since the saved row was last
        written (driver / port re-enumeration).
        """
        try:
            import audio.soundcard._registry as _reg   # noqa: PLC0415
        except ImportError:
            return None
        mgr = _reg.default_manager
        if mgr is None:
            return None
        try:
            inputs = mgr.list_inputs()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("preflight: list_inputs failed: %s", exc)
            return None
        ids   = {str(d.stable_id).strip().lower()       for d in inputs}
        names = {(d.name or "").strip().lower()         for d in inputs if d.name}
        return ids, names

    def _submit_warnings(
        self,
        warning_type: str,
        scan_run_id: str,
        warnings: list[dict],
    ) -> None:
        """POST the warning batch (possibly empty) to the API for atomic replace."""
        body = {
            "warning_type": warning_type,
            "scan_run_id":  scan_run_id,
            "warnings":     warnings,
        }
        try:
            resp = self._api_client.session.post(
                "/api/v2/preflight/warnings/replace",
                json=body,
                timeout=10,
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error(
                "preflight: warnings/replace POST failed (%s): %s",
                warning_type, exc,
            )
            return
        if resp.status_code != 200:
            logger.warning(
                "preflight: warnings/replace (%s) HTTP %d: %s",
                warning_type, resp.status_code, resp.text[:200],
            )
            return
        try:
            inserted = int(resp.json().get("inserted", 0))
        except Exception:  # pylint: disable=broad-exception-caught
            inserted = -1
        if inserted == 0:
            logger.info(
                "preflight (%s): no warnings active.", warning_type,
            )
        else:
            logger.info(
                "preflight (%s): %d warning(s) active.",
                warning_type, inserted,
            )
