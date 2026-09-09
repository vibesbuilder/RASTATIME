"""
SourceSwitcher — live-source switching for RASTATIME playout.

Bridges Icecast's source-connect / source-disconnect event bindings
into a state machine that decides which audio the RASTATIME playout
should be on:

    MASTER  > SHOW > SCHEDULED

Master overrides everything.  Show overrides the scheduled playout but
yields to Master.  When all DJ sources are away, scheduled file
playback resumes (with a catch-up seek if the originally scheduled
track is still within its time slot).

The switching itself happens in ``PlayoutScheduler.switch_audio_source(state)``;
this module is just the trigger plumbing.

Wire-up
-------
A small HTTP listener (``http.server.ThreadingHTTPServer``) is started
in a daemon thread on ``127.0.0.1:8770``.  Icecast's ``<event-bindings>``
in ``icecast.xml`` are configured to fire GET requests to::

    /source-event?source=master&status=on
    /source-event?source=master&status=off
    /source-event?source=show&status=on
    /source-event?source=show&status=off

    Since 2026-09-09 (option d) these events are posted by the harbor
    on_connect/on_disconnect callbacks rendered into rastatime.liq;
    the Liquidsoap telnet reconciler only verifies them.

The listener stays bound to localhost — Icecast runs on the same host
and we don't want random external clients to be able to fake DJ
connect events.

Latency
-------
Push-based, end-to-end Icecast → Playout: a few tens of milliseconds.
No polling.  Meets the "max 1 s" requirement comfortably.
"""

import base64
import json
import logging
import os
import threading
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from enum import Enum
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, Mapping, Optional
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)

# RASTATIME 2026-09-09 - option d: DJ connect/disconnect events come from
# Liquidsoap's harbor callbacks (rastatime.liq POSTs to /source-event); the
# telnet reconciler only *verifies* - once about a second after each
# event and then every RASTATIME_DJ_RECONCILE_SECONDS as the safety net
# (lost POST, Liquidsoap restart).  Before: a 5-s poll = two telnet
# commands per 5 s, and every telnet command leaks ~87 KB on the Windows
# build of Liquidsoap 2.4.4 (~150 MB/h idle growth).
DEFAULT_RECONCILE_INTERVAL_S = 120.0
MIN_RECONCILE_INTERVAL_S = 5.0
RECONCILE_SETTLE_S = 1.0
RECONCILE_INTERVAL_ENV = "RASTATIME_DJ_RECONCILE_SECONDS"
# While the loaded rastatime.liq predates the harbor callbacks (or telnet
# is down), the loop falls back to the old 5-s status poll, so the order
# in which PLAYOUT and LIQUIDSOAP are restarted does not matter.
LEGACY_POLL_INTERVAL_S = 5.0
SOURCE_EVENTS_PROBE = "rastatime.source_events"


def reconcile_interval_from_env(
    env: Optional[Mapping[str, str]] = None,
    default: float = DEFAULT_RECONCILE_INTERVAL_S,
) -> float:
    """
    Seconds between two periodic telnet verifications of the DJ state
    (``RASTATIME_DJ_RECONCILE_SECONDS``).  Unset/blank -> ``default``;
    not a number -> ``default`` with a warning; anything below
    :data:`MIN_RECONCILE_INTERVAL_S` is raised to that floor - the poll
    is what leaks, so a very short interval would bring the leak back.
    """
    source = os.environ if env is None else env
    raw = (source.get(RECONCILE_INTERVAL_ENV, "") or "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        logger.warning(
            "%s=%r is not a number - using %.0f s",
            RECONCILE_INTERVAL_ENV, raw, default,
        )
        return default
    if value < MIN_RECONCILE_INTERVAL_S:
        logger.warning(
            "%s=%r is below the %.0f s floor - using the floor",
            RECONCILE_INTERVAL_ENV, raw, MIN_RECONCILE_INTERVAL_S,
        )
        return MIN_RECONCILE_INTERVAL_S
    return value


class SourceState(str, Enum):
    """Active audio source.  Priority: MASTER > SHOW > SCHEDULED."""

    SCHEDULED = "scheduled"
    SHOW = "show"
    MASTER = "master"


class SourceSwitcher:
    """
    Tracks Icecast source connect/disconnect events and decides which
    audio source the playout should be on.

    Thread-safety
    -------------
    State updates are serialised via ``self._lock``.  The switch
    callback is invoked **outside** the lock so a slow downstream
    operation (FFmpeg subprocess restart, VLC media swap) cannot
    deadlock additional events arriving on the listener thread.

    Reentrancy
    ----------
    If the callback for one transition is still running when a second
    event arrives, the second event will simply update internal flags
    and queue another callback after the first one returns.  The
    callback always sees the latest computed state, never stale data.
    """

    def __init__(self, switch_callback: Callable[["SourceState"], None]):
        self._lock = threading.Lock()
        self._master_connected = False
        self._show_connected = False
        self._current_state: SourceState = SourceState.SCHEDULED
        self._switch_callback = switch_callback
        # Option d (2026-09-09): set by /source-event and by the
        # scheduler after a Liquidsoap restart; the telnet reconciler
        # waits on it instead of sleeping a fixed interval.
        self._reconcile_wake = threading.Event()

    # ---------- public API -----------------------------------------------

    def on_master_connect(self) -> None:
        self._update(master_connected=True)

    def on_master_disconnect(self) -> None:
        self._update(master_connected=False)

    def on_show_connect(self) -> None:
        self._update(show_connected=True)

    def on_show_disconnect(self) -> None:
        self._update(show_connected=False)

    @property
    def current_state(self) -> SourceState:
        return self._current_state

    def is_master_connected(self) -> bool:
        with self._lock:
            return self._master_connected

    def is_show_connected(self) -> bool:
        with self._lock:
            return self._show_connected

    def request_reconcile(self) -> None:
        """Ask the state reconciler to verify the DJ state soon
        (option d, 2026-09-09).  Cheap and idempotent."""
        self._reconcile_wake.set()

    def wait_reconcile(self, timeout: float) -> bool:
        """Block until a reconcile was requested or ``timeout`` seconds
        passed.  Returns True when it was requested (and clears the
        request), False on timeout."""
        requested = self._reconcile_wake.wait(timeout)
        if requested:
            self._reconcile_wake.clear()
        return requested

    # ---------- internals ------------------------------------------------

    def _update(
        self,
        master_connected: Optional[bool] = None,
        show_connected: Optional[bool] = None,
    ) -> None:
        with self._lock:
            if master_connected is not None:
                self._master_connected = master_connected
            if show_connected is not None:
                self._show_connected = show_connected

            new_state = self._compute_state()
            if new_state == self._current_state:
                logger.debug(
                    "SourceSwitcher: state unchanged (%s); master=%s show=%s",
                    self._current_state.value,
                    self._master_connected,
                    self._show_connected,
                )
                return

            old_state = self._current_state
            self._current_state = new_state

        # Log + callback OUTSIDE the lock.
        logger.info(
            "SourceSwitcher: %s -> %s  (master=%s, show=%s)",
            old_state.value, new_state.value,
            self._master_connected, self._show_connected,
        )
        try:
            self._switch_callback(new_state)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.exception("SourceSwitcher: switch_callback failed: %s", exc)

    def _compute_state(self) -> SourceState:
        if self._master_connected:
            return SourceState.MASTER
        if self._show_connected:
            return SourceState.SHOW
        return SourceState.SCHEDULED


# ---------------------------------------------------------------------------
# HTTP listener
# ---------------------------------------------------------------------------

class _EventHandler(BaseHTTPRequestHandler):
    """
    HTTP listener for two internal endpoints used by RASTATIME:

      GET / POST  /source-event?source=<master|show>&status=<on|off>
            Driven by Icecast event-bindings on the /main and /show
            mounts.  Forwards to the SourceSwitcher state machine.

      POST        /reload-schedule
            Called by the PHP frontend after a show is created / edited /
            deleted so the playout picks the change up immediately
            instead of waiting for the next 120-s poll cycle.
    """

    # Set by start_listener().  Class-level so request handlers (which are
    # spawned per-request) can reach the singletons.
    switcher: Optional[SourceSwitcher] = None
    # Typed as "object" so this module does not import PlayoutScheduler and
    # create a circular dependency.  Callers expect a .refresh() method.
    scheduler: Optional[object] = None
    # Pre-flight scanner (B.4 #2).  Optional — set by start_listener when
    # __main__ has wired one.  Used by /reload-schedule to trigger an
    # immediate rescan so dashboard warnings appear within seconds of a
    # show edit, instead of waiting up to 15 min for the next periodic
    # scan.  Same "object"-typing for the same circular-import reason.
    preflight: Optional[object] = None

    # Silence the default access log line on stderr; route via our logger.
    def log_message(self, format: str, *args) -> None:  # noqa: A002
        logger.debug("source-event-listener: %s", format % args)

    def _dispatch(self) -> None:
        try:
            parsed = urlparse(self.path)
            if parsed.path == "/source-event":
                self._handle_source_event(parsed)
            elif parsed.path == "/source-state":
                self._handle_source_state()
            elif parsed.path == "/reload-schedule":
                self._handle_reload_schedule()
            elif parsed.path == "/disconnect-source":
                self._handle_disconnect_source(parsed)
            elif parsed.path == "/set-audio-output":
                self._handle_set_audio_output(parsed)
            else:
                self._send(404, "not found")
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.exception("listener error: %s", exc)
            self._send(500, "internal error")

    def do_GET(self) -> None:   # noqa: N802 — http.server requires this name
        self._dispatch()

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch()

    def _handle_source_event(self, parsed) -> None:
        qs = parse_qs(parsed.query)
        source = (qs.get("source", [""])[0] or "").lower()
        status = (qs.get("status", [""])[0] or "").lower()

        if source not in ("master", "show"):
            self._send(400, "bad source")
            return
        if status not in ("on", "off"):
            self._send(400, "bad status")
            return
        if _EventHandler.switcher is None:
            logger.error("source-event listener: switcher is None")
            self._send(500, "switcher not initialised")
            return

        connected = (status == "on")
        sw = _EventHandler.switcher

        if source == "master":
            if connected:
                sw.on_master_connect()
            else:
                sw.on_master_disconnect()
        else:  # show
            if connected:
                sw.on_show_connect()
            else:
                sw.on_show_disconnect()

        logger.info("source-event: %s %s", source, status)
        # Option d (2026-09-09): the event normally comes from the harbor
        # callback in rastatime.liq; let the reconciler confirm the state
        # over telnet shortly after (quick connect/disconnect pairs, a
        # POST that overtook another one).
        sw.request_reconcile()
        self._send(200, "ok")

    def _handle_source_state(self) -> None:
        """
        Return current SourceSwitcher state as a small JSON document.

        Consumers
        ---------
        Used by the legacy dashboard ("On Air" indicator) — the PHP
        ``Preference::GetSourceStatus()`` / ``GetSourceSwitchStatus()``
        helpers fetch this every 5 s instead of reading the now-stale
        ``cc_pref.{master_dj,live_dj}_switch`` columns.  Those columns
        used to be flipped by the old icecast.xml URL-auth hooks; the
        direct-to-:8770 refactor stopped writing them, so the dashboard
        was showing stale state.  Reading live state from here is
        cheaper and always accurate.

        Response shape
        --------------
        ::

            {
              "master_connected": false,
              "show_connected":   false,
              "current_state":    "scheduled"   // scheduled | show | master
            }

        Auth
        ----
        None — the listener is bound to 127.0.0.1 and that's gate enough.
        """
        sw = _EventHandler.switcher
        if sw is None:
            logger.error("source-state: switcher is None")
            self._send(500, "switcher not initialised")
            return

        state = {
            "master_connected": sw.is_master_connected(),
            "show_connected": sw.is_show_connected(),
            "current_state": sw.current_state.value,
        }
        body_bytes = json.dumps(state).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body_bytes)))
        self.end_headers()
        try:
            self.wfile.write(body_bytes)
        except OSError:
            pass

    def _handle_disconnect_source(self, parsed) -> None:
        """
        Force-disconnect a live DJ source (master/show).

        Used by the PHP frontend's "Cancel Show" / kick-source workflows
        to make sure the DJ goes offline immediately, instead of waiting
        for the playout's schedule refresh to indirectly detect the gap.

        Query: ``?source=master|show`` (legacy ``master_dj`` / ``live_dj``
        also accepted by the scheduler).
        """
        qs = parse_qs(parsed.query)
        source = (qs.get("source", [""])[0] or "").lower()
        if not source:
            self._send(400, "missing source")
            return

        sched = _EventHandler.scheduler
        if sched is None or not hasattr(sched, "kick_dj_source"):
            logger.error(
                "disconnect-source: scheduler is None or missing kick_dj_source"
            )
            self._send(500, "scheduler not initialised")
            return

        try:
            logger.info("disconnect-source: source=%s (PHP frontend push)", source)
            sched.kick_dj_source(source)
            self._send(200, "ok")
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.exception("disconnect-source failed: %s", exc)
            self._send(500, "internal error")

    def _handle_set_audio_output(self, parsed) -> None:
        """
        Route the local soundcard playback to a different output device.

        Query: ``?output_id=<stable-id>``.  An empty / absent
        ``output_id`` resets to the OS-default device.

        Used by the Django soundcard-settings API: after the operator
        saves a new "Main Output" selection, the Django POST handler
        pushes the new device's stable-ID here so playback switches
        live, without a playout-service restart.
        """
        sched = _EventHandler.scheduler
        if sched is None or not hasattr(sched, "set_audio_output"):
            logger.error(
                "set-audio-output: scheduler is None or missing set_audio_output"
            )
            self._send(500, "scheduler not initialised")
            return

        qs = parse_qs(parsed.query)
        device_id = (qs.get("output_id", [""])[0] or "").strip()

        try:
            logger.info(
                "set-audio-output: device_id=%r (Frontend push)",
                device_id or "(default)",
            )
            sched.set_audio_output(device_id or None)
            self._send(200, "ok")
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.exception("set-audio-output failed: %s", exc)
            self._send(500, "internal error")

    def _handle_reload_schedule(self) -> None:
        """
        Trigger an immediate schedule refresh.

        Allows the PHP frontend to push schedule edits to the running
        playout without waiting for the next 120-s poll cycle.  Latency
        from PHP save to playout pick-up: < 1 s in practice (one
        refresh round-trip to the Django API).

        Also fires an out-of-band pre-flight scan in a background thread
        (B.4 #2) so newly added / re-targeted Line-In shows surface
        device-missing warnings on the dashboard within seconds —
        instead of waiting up to 15 min for the next periodic scan.
        The pre-flight scan does its own schedule fetch + a handful of
        API round-trips per linein item, so we deliberately don't run
        it in-line: the PHP frontend wants a fast 200 OK, and the
        operator is fine with the banner appearing ~1-2 s later.
        """
        sched = _EventHandler.scheduler
        if sched is None:
            logger.error("reload-schedule: scheduler is None")
            self._send(500, "scheduler not initialised")
            return

        try:
            logger.info("reload-schedule: triggered by PHP frontend")
            sched.refresh()
            self._send(200, "ok")
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.exception("reload-schedule failed: %s", exc)
            self._send(500, "internal error")
            return

        # B.4 #2 — preflight side-effect.  Outside the try/except above so
        # an /reload-schedule call still reports its primary result to PHP
        # even if pre-flight has a temporary glitch.  Daemon thread so we
        # don't keep the HTTP worker busy through the scan.
        preflight = _EventHandler.preflight
        if preflight is not None:
            threading.Thread(
                target=_safe_preflight_scan,
                args=(preflight,),
                name="preflight-rescan-on-reload",
                daemon=True,
            ).start()

    def _send(self, code: int, body: str) -> None:
        body_bytes = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body_bytes)))
        self.end_headers()
        try:
            self.wfile.write(body_bytes)
        except OSError:
            pass


def _icecast_state_poll_loop(
    switcher: SourceSwitcher,
    base_url: str = "http://127.0.0.1:8000",
    admin_user: str = "admin",
    admin_password: str = "admin",
    interval_s: float = 10.0,
) -> None:
    """
    Reconciliation watchdog — polls Icecast's actual mount list every
    ``interval_s`` seconds and syncs the SourceSwitcher's internal state
    to it.  Catches missed mount_add/mount_remove notifications.

    Endpoint choice — IMPORTANT
    ---------------------------
    We hit ``/admin/listmounts`` (with HTTP Basic Auth using the
    ``<admin-user>/<admin-password>`` from icecast.xml) instead of the
    open ``/status-json.xsl`` because the latter EXCLUDES mounts
    marked ``<hidden>1</hidden>``.  /main and /show are both hidden in
    our config — listing only the public output mounts would make the
    watchdog always think master/show are disconnected and falsely
    reset the state to scheduled every 10 s.  Empirically observed:
    state would flicker SHOW -> SCHEDULED four seconds after a
    successful BUTT-on-/show connection because of exactly this.

    Background
    ----------
    Icecast 2.4's URL-auth ``mount_add`` notification fires reliably on
    source connect — empirically verified.  But ``mount_remove`` is much
    less reliable: in our setup, source disconnects often DO NOT result
    in the configured mount_remove URL being called, leaving the
    SourceSwitcher stuck in MASTER or SHOW state even after the DJ has
    long left.  That kept the playout pointing FFmpeg streamers at an
    empty /main or /show mount, producing silence on the public stream.

    Rather than chase the root cause inside Icecast (likely a 2.4
    regression around URL-auth source disconnects), we treat the
    notifications as a best-effort fast path and add this slow path
    as the source of truth: every 10 s we ask Icecast itself what
    mounts are currently up, and if our state machine disagrees we
    reconcile.  Worst-case stuck-state duration: ~10 s.

    Polling cost: one localhost GET to ``/admin/listmounts`` every 10 s.
    The XML response is tiny.  Negligible.
    """
    poll_url = f"{base_url}/admin/listmounts"
    auth_token = base64.b64encode(
        f"{admin_user}:{admin_password}".encode("utf-8")
    ).decode("ascii")
    auth_header = f"Basic {auth_token}"

    logger.info(
        "Source state reconciler started (polling %s every %.0fs, "
        "admin-user=%s)",
        poll_url, interval_s, admin_user,
    )
    while True:
        try:
            req = urllib.request.Request(
                poll_url,
                headers={"Authorization": auth_header},
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                xml_bytes = resp.read()

            # admin/listmounts XML shape:
            #   <icestats>
            #     <source mount="/main">...</source>
            #     <source mount="/show">...</source>
            #     ...
            #   </icestats>
            # A <source> element only exists when a source client is
            # currently connected to the mount — if there's no source,
            # Icecast omits the <source> element entirely.
            root = ET.fromstring(xml_bytes)
            mount_names = set()
            for source_elem in root.findall("source"):
                mount = (source_elem.get("mount") or "").lstrip("/")
                if mount:
                    mount_names.add(mount)

            actual_master = "main" in mount_names
            actual_show = "show" in mount_names

            if actual_master != switcher.is_master_connected():
                logger.warning(
                    "SourceSwitcher: master state reconcile %s -> %s "
                    "(icecast actual: /main %s in admin/listmounts)",
                    switcher.is_master_connected(), actual_master,
                    "is" if actual_master else "NOT",
                )
                if actual_master:
                    switcher.on_master_connect()
                else:
                    switcher.on_master_disconnect()

            if actual_show != switcher.is_show_connected():
                logger.warning(
                    "SourceSwitcher: show state reconcile %s -> %s "
                    "(icecast actual: /show %s in admin/listmounts)",
                    switcher.is_show_connected(), actual_show,
                    "is" if actual_show else "NOT",
                )
                if actual_show:
                    switcher.on_show_connect()
                else:
                    switcher.on_show_disconnect()

        except urllib.error.URLError as exc:
            logger.warning(
                "SourceSwitcher: icecast state poll failed (network): %s",
                exc,
            )
        except ET.ParseError as exc:
            logger.warning(
                "SourceSwitcher: icecast state poll failed (xml parse): %s",
                exc,
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning(
                "SourceSwitcher: icecast state poll unexpected error: %s",
                exc,
            )

        time.sleep(interval_s)


def _safe_preflight_scan(preflight) -> None:
    """
    Run ``preflight.scan_once()`` and log any failure — never raise.

    Used as the background-thread target for the /reload-schedule
    side-effect (B.4 #2).  Lives at module level so it can be referenced
    from inside ``_EventHandler._handle_reload_schedule`` without
    pulling preflight imports into the class body.
    """
    try:
        preflight.scan_once()
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning(
            "reload-schedule: preflight rescan failed: %s", exc,
        )


def _reconcile_liquidsoap_once(client, switcher: SourceSwitcher) -> None:
    """
    One verification round: ``master_dj.status`` + ``show_dj.status``
    over telnet, then sync the SourceSwitcher to what Liquidsoap says.
    Raises whatever the telnet client raises - the loop logs it.
    """
    master_resp = client.send_command("master_dj.status").strip()
    show_resp = client.send_command("show_dj.status").strip()
    # Liquidsoap's idle reply is literally "no source client connected".
    # Anything else (incl. an ERROR reply for an undefined harbor)
    # is treated as "DJ source present" - but we filter ERRORs
    # explicitly so a mis-configured .liq doesn't fake DJ-connects.
    actual_master = (
        master_resp != "no source client connected"
        and not master_resp.startswith("ERROR")
    )
    actual_show = (
        show_resp != "no source client connected"
        and not show_resp.startswith("ERROR")
    )

    if actual_master != switcher.is_master_connected():
        logger.warning(
            "SourceSwitcher: master state reconcile %s -> %s "
            "(liquidsoap master_dj.status: %r)",
            switcher.is_master_connected(), actual_master,
            master_resp,
        )
        if actual_master:
            switcher.on_master_connect()
        else:
            switcher.on_master_disconnect()

    if actual_show != switcher.is_show_connected():
        logger.warning(
            "SourceSwitcher: show state reconcile %s -> %s "
            "(liquidsoap show_dj.status: %r)",
            switcher.is_show_connected(), actual_show,
            show_resp,
        )
        if actual_show:
            switcher.on_show_connect()
        else:
            switcher.on_show_disconnect()


def _source_events_present(client) -> bool:
    """
    Does the loaded rastatime.liq post harbor events?  The render
    registers the telnet command ``rastatime.source_events`` answering
    ``on``; an older render replies ``ERROR: unknown command``.  Raises
    whatever the telnet client raises.
    """
    reply = client.send_command(SOURCE_EVENTS_PROBE).strip()
    if reply.startswith("ERROR"):
        return False
    return reply.lower().startswith("on")


def _liquidsoap_state_poll_loop(
    switcher: SourceSwitcher,
    telnet_host: str = "127.0.0.1",
    telnet_port: int = 1234,
    interval_s: float = DEFAULT_RECONCILE_INTERVAL_S,
    settle_s: float = RECONCILE_SETTLE_S,
    max_ticks: Optional[int] = None,
) -> None:
    """
    Reconciliation watchdog for the Liquidsoap-engine mode (Phase C4
    Teil 2).  Verifies ``master_dj.status`` and ``show_dj.status`` via
    the Liquidsoap telnet server and syncs the SourceSwitcher's
    internal state - once at start, ``settle_s`` after every
    :meth:`SourceSwitcher.request_reconcile` (a harbor event arrived on
    /source-event, or the scheduler saw a Liquidsoap restart) and
    otherwise every ``interval_s`` seconds.  ``max_ticks`` bounds the
    loop for tests.

    RASTATIME 2026-09-09 (option d): until now this was a plain 5-s poll
    and the sole source of truth.  The state now arrives from the
    harbor ``on_connect``/``on_disconnect`` callbacks rendered into
    rastatime.liq; the periodic round is only the safety net, because
    every telnet command leaks ~87 KB on the Windows build (the 5-s
    poll alone grew the process by ~150 MB/h).

    Replaces :func:`_icecast_state_poll_loop` when
    ``engine_kind=liquidsoap`` — because in that configuration the
    DJ-source mounts (``/main``, ``/show``) live inside the
    Liquidsoap subprocess via ``input.harbor``, NOT inside Icecast,
    so polling Icecast's ``/admin/listmounts`` would never see the
    DJ-source state.

    Cost: two localhost telnet round-trips per verification - a few
    per hour instead of 1,440.

    Implementation notes
    --------------------
    Liquidsoap's ``<harbor-id>.status`` telnet command returns a
    short text reply.  Observed values on 2.4.4:

      * ``"no source client connected"`` — nobody is connected
      * ``"source client connected"`` (or richer text including
        the remote IP / decoding format) — a DJ is live

    We treat any reply that is NOT exactly ``"no source client
    connected"`` (after strip) as "connected".  That's the most
    robust differentiator across Liquidsoap versions; any future
    refinement of the status string only needs to keep the
    "no source client connected" sentinel for the disconnected case.

    Reconnect: the LiquidsoapTelnetClient already retries on a
    broken socket (Phase C1).  If both retries fail, we log a
    warning and try again on the next interval tick — we do NOT
    sleep on failure because Liquidsoap might just be restarting
    (NSSM auto-restart after a crash), and we want to reconnect as
    soon as it's back.
    """
    from libretime_playout.engine.liquidsoap_telnet import (  # noqa: PLC0415
        LiquidsoapTelnetClient,
    )

    client = LiquidsoapTelnetClient(host=telnet_host, port=telnet_port)
    logger.info(
        "Source state reconciler started (Liquidsoap telnet %s:%d; verifies "
        "master_dj.status + show_dj.status %.1fs after each harbor event "
        "and every %.0fs)",
        telnet_host, telnet_port, settle_s, interval_s,
    )

    ticks = 0
    events_present: Optional[bool] = None    # unknown until probed
    while max_ticks is None or ticks < max_ticks:
        try:
            if events_present is not True:
                probed = _source_events_present(client)
                if probed and events_present is not None:
                    logger.info(
                        "SourceSwitcher: the loaded rastatime.liq posts harbor "
                        "events - verifying every %.0fs from now on", interval_s,
                    )
                elif not probed and events_present is not False:
                    logger.warning(
                        "SourceSwitcher: the loaded rastatime.liq has no harbor "
                        "source events (older render) - polling master_dj/show_dj "
                        "every %.0fs until LIQUIDSOAP restarts with the new one",
                        LEGACY_POLL_INTERVAL_S,
                    )
                events_present = probed
            _reconcile_liquidsoap_once(client, switcher)
        except ConnectionError as exc:
            events_present = None         # a fresh instance may carry another render
            logger.warning(
                "SourceSwitcher: Liquidsoap telnet verification failed "
                "(connection): %s - will retry next round", exc,
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning(
                "SourceSwitcher: Liquidsoap telnet verification unexpected "
                "error: %s", exc,
            )
        ticks += 1
        if max_ticks is not None and ticks >= max_ticks:
            break
        timeout = interval_s if events_present else LEGACY_POLL_INTERVAL_S
        if switcher.wait_reconcile(timeout) and settle_s > 0:
            # An event just arrived - give Liquidsoap a moment (a DJ
            # client that reconnects right away) before verifying.
            time.sleep(settle_s)


def start_listener(
    switcher: SourceSwitcher,
    scheduler: Optional[object] = None,
    preflight: Optional[object] = None,
    host: str = "127.0.0.1",
    port: int = 8770,
    engine_kind: str = "mpv",
    reconcile_interval_s: float = DEFAULT_RECONCILE_INTERVAL_S,
) -> ThreadingHTTPServer:
    """
    Start the HTTP listener for the internal RASTATIME endpoints:

      /source-event       (Icecast event bindings → SourceSwitcher)
      /source-state       (Dashboard / PHP frontend → JSON readout)
      /reload-schedule    (PHP frontend → scheduler.refresh()
                                       + preflight.scan_once())
      /disconnect-source  (PHP frontend → SourceSwitcher kick)
      /set-audio-output   (PHP frontend → mpv audio-device swap)

    Returns the server instance so the caller can shut it down on exit.
    Bind defaults to localhost — Icecast and Apache live on the same
    host, and we do not want external clients to be able to fake DJ
    connect events or force expensive schedule refreshes.

    ``engine_kind`` decides which reconciler thread is spawned:
      * ``"mpv"`` / ``"vlc"`` (default) — :func:`_icecast_state_poll_loop`
        polls Icecast's ``/admin/listmounts`` to detect DJ-source
        state.  Used in the legacy code path where the DJ-source
        mounts live in Icecast.
      * ``"liquidsoap"`` — :func:`_liquidsoap_state_poll_loop` verifies
        the Liquidsoap subprocess's telnet ``master_dj.status`` and
        ``show_dj.status`` after each harbor event posted to
        /source-event and every ``reconcile_interval_s`` seconds
        (option d, 2026-09-09).  Used when ``input.harbor`` inside
        rastatime.liq owns the DJ-source mounts (Phase C4).
    """
    _EventHandler.switcher = switcher
    _EventHandler.scheduler = scheduler
    _EventHandler.preflight = preflight
    server = ThreadingHTTPServer((host, port), _EventHandler)
    thread = threading.Thread(
        target=server.serve_forever,
        name="rastatime-playout-listener",
        daemon=True,
    )
    thread.start()
    logger.info(
        "Playout HTTP listener bound to http://%s:%d "
        "(/source-event, /source-state, /reload-schedule, "
        "/disconnect-source, /set-audio-output)",
        host, port,
    )

    # Pick the right reconciler watchdog based on which audio engine
    # owns the DJ-source mounts.
    if engine_kind == "liquidsoap":
        threading.Thread(
            target=_liquidsoap_state_poll_loop,
            args=(switcher,),
            kwargs={"interval_s": reconcile_interval_s},
            name="rastatime-source-state-reconciler-liquidsoap",
            daemon=True,
        ).start()
    else:
        threading.Thread(
            target=_icecast_state_poll_loop,
            args=(switcher,),
            name="rastatime-source-state-reconciler",
            daemon=True,
        ).start()

    return server
