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
