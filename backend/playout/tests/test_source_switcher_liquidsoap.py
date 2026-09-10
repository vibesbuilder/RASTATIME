"""
RASTATIME 2026-05-27 — Unit tests for the Phase-C4 Teil 2 Liquidsoap-
telnet source-state reconciler in libretime_playout.source_switcher.

Strategy
--------

The reconciler is a single function ``_liquidsoap_state_poll_loop``
that runs forever in a worker thread.  Tests don't run the actual
infinite loop; they manually invoke the same Telnet-poll +
reconcile logic by simulating a few Telnet round-trips and asserting
the SourceSwitcher state transitions correctly.

We monkey-patch ``LiquidsoapTelnetClient`` with a MagicMock so the
test never touches the network — same pattern as the C2 engine tests.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from libretime_playout.source_switcher import (
    SourceState,
    SourceSwitcher,
    _liquidsoap_state_poll_loop,
    _reconcile_liquidsoap_once,
)


# ---- Helpers ------------------------------------------------------------


def _make_switcher_with_recorder():
    """SourceSwitcher + a list to capture every callback-fired state."""
    states = []
    sw = SourceSwitcher(switch_callback=lambda s: states.append(s))
    return sw, states


def _run_one_poll_tick(client_mock, switcher):
    """
    Run ONE verification round of the reconciler with whatever the mock
    telnet client replies.  Since 2026-09-09 (option d) the per-round
    logic lives in ``_reconcile_liquidsoap_once`` and the loop around it
    only decides *when* to run it, so the tests call the real function.
    """
    _reconcile_liquidsoap_once(client_mock, switcher)


# ---- Status-string parsing ----------------------------------------------


def test_idle_response_means_disconnected():
    """The Liquidsoap idle reply exactly matches our 'disconnected' check."""
    sw, _ = _make_switcher_with_recorder()
    client = MagicMock()
    client.send_command.side_effect = lambda cmd: {
        "master_dj.status": "no source client connected",
        "show_dj.status":   "no source client connected",
    }[cmd]
    _run_one_poll_tick(client, sw)
    assert sw.is_master_connected() is False
    assert sw.is_show_connected() is False
    assert sw.current_state == SourceState.SCHEDULED


def test_non_idle_response_means_connected():
    """Anything except the exact idle string → connected."""
    sw, _ = _make_switcher_with_recorder()
    client = MagicMock()
    client.send_command.side_effect = lambda cmd: {
        "master_dj.status": "source client connected from 192.168.1.5",
        "show_dj.status":   "source client connected from 192.168.1.6",
    }[cmd]
    _run_one_poll_tick(client, sw)
    assert sw.is_master_connected() is True
    assert sw.is_show_connected() is True


def test_error_response_means_disconnected_not_connected():
    """
    A response starting with 'ERROR' (e.g. mis-rendered .liq where the
    harbor source-id doesn't exist) MUST be treated as disconnected —
    otherwise a config bug would silently force DJ-active state.
    """
    sw, _ = _make_switcher_with_recorder()
    client = MagicMock()
    client.send_command.side_effect = lambda cmd: {
        "master_dj.status": "ERROR: unknown command, type \"help\" ...",
        "show_dj.status":   "no source client connected",
    }[cmd]
    _run_one_poll_tick(client, sw)
    assert sw.is_master_connected() is False
    assert sw.is_show_connected() is False


def test_whitespace_around_idle_reply_still_parses():
    """Status response with leading/trailing whitespace strips correctly."""
    sw, _ = _make_switcher_with_recorder()
    client = MagicMock()
    client.send_command.side_effect = lambda cmd: {
        "master_dj.status": "   no source client connected   ",
        "show_dj.status":   "\nno source client connected\n",
    }[cmd]
    _run_one_poll_tick(client, sw)
    assert sw.is_master_connected() is False
    assert sw.is_show_connected() is False


# ---- State transitions ---------------------------------------------------


def test_master_connect_transition_fires_callback():
    """Idle → Master connects → callback sees MASTER."""
    sw, states = _make_switcher_with_recorder()
    client = MagicMock()
    # Tick 1: both idle
    client.send_command.side_effect = lambda cmd: "no source client connected"
    _run_one_poll_tick(client, sw)
    assert states == []   # no transition, no callback
    # Tick 2: master now connected
    client.send_command.side_effect = lambda cmd: (
        "source client connected" if cmd == "master_dj.status"
        else "no source client connected"
    )
    _run_one_poll_tick(client, sw)
    assert sw.current_state == SourceState.MASTER
    assert states[-1] == SourceState.MASTER


def test_show_connect_transition_fires_callback():
    """Idle → Show connects → callback sees SHOW."""
    sw, states = _make_switcher_with_recorder()
    client = MagicMock()
    client.send_command.side_effect = lambda cmd: (
        "source client connected" if cmd == "show_dj.status"
        else "no source client connected"
    )
    _run_one_poll_tick(client, sw)
    assert sw.current_state == SourceState.SHOW
    assert states[-1] == SourceState.SHOW


def test_master_overrides_show_priority():
    """Show first, then Master → state goes SHOW → MASTER."""
    sw, states = _make_switcher_with_recorder()
    client = MagicMock()
    # Tick 1: show only
    client.send_command.side_effect = lambda cmd: (
        "source client connected" if cmd == "show_dj.status"
        else "no source client connected"
    )
    _run_one_poll_tick(client, sw)
    assert sw.current_state == SourceState.SHOW
    # Tick 2: both — master takes priority
    client.send_command.side_effect = lambda cmd: "source client connected"
    _run_one_poll_tick(client, sw)
    assert sw.current_state == SourceState.MASTER
    assert states[-2:] == [SourceState.SHOW, SourceState.MASTER]


def test_master_disconnect_falls_back_to_show_if_still_connected():
    """Master + Show → Master disconnects → SHOW."""
    sw, states = _make_switcher_with_recorder()
    client = MagicMock()
    # Tick 1: both connected
    client.send_command.side_effect = lambda cmd: "source client connected"
    _run_one_poll_tick(client, sw)
    assert sw.current_state == SourceState.MASTER
    # Tick 2: Master leaves, Show stays
    client.send_command.side_effect = lambda cmd: (
        "source client connected" if cmd == "show_dj.status"
        else "no source client connected"
    )
    _run_one_poll_tick(client, sw)
    assert sw.current_state == SourceState.SHOW


def test_both_disconnect_falls_back_to_scheduled():
    """Master + Show → both disconnect → SCHEDULED."""
    sw, states = _make_switcher_with_recorder()
    client = MagicMock()
    client.send_command.side_effect = lambda cmd: "source client connected"
    _run_one_poll_tick(client, sw)
    assert sw.current_state == SourceState.MASTER
    client.send_command.side_effect = lambda cmd: "no source client connected"
    _run_one_poll_tick(client, sw)
    assert sw.current_state == SourceState.SCHEDULED


def test_no_transition_when_state_unchanged():
    """Multiple identical-state polls should NOT spam the callback."""
    sw, states = _make_switcher_with_recorder()
    client = MagicMock()
    client.send_command.side_effect = lambda cmd: "no source client connected"
    for _ in range(5):
        _run_one_poll_tick(client, sw)
    # No state change ever → callback never fires.
    assert states == []


# ---- start_listener reconciler dispatch ---------------------------------


def test_start_listener_spawns_the_liquidsoap_reconciler():
    """
    start_listener must spawn the Liquidsoap reconciler thread.  Until
    2026-09-10 an ``engine_kind`` argument chose between this and an
    Icecast admin poll for the deleted mpv path; both are gone.

    We patch the reconciler function so it does not actually run, and
    the HTTP server so no socket is bound.
    """
    sw, _ = _make_switcher_with_recorder()
    with patch(
        "libretime_playout.source_switcher._liquidsoap_state_poll_loop"
    ) as ls_mock, patch(
        "libretime_playout.source_switcher.ThreadingHTTPServer"
    ) as srv_mock, patch(
        "libretime_playout.source_switcher.threading.Thread"
    ) as thread_mock:
        thread_mock.return_value.start = MagicMock()
        srv_mock.return_value = MagicMock()
        from libretime_playout.source_switcher import start_listener
        start_listener(sw, reconcile_interval_s=123.0)
        reconcilers = [
            call for call in thread_mock.call_args_list
            if call.kwargs.get("target") is ls_mock
        ]
        assert len(reconcilers) == 1, "liquidsoap reconciler thread not scheduled"
        assert reconcilers[0].kwargs["kwargs"] == {"interval_s": 123.0}


def test_start_listener_has_no_engine_kind_argument():
    import libretime_playout.source_switcher as ss
    assert not hasattr(ss, "_icecast_state_poll_loop")
    with patch("libretime_playout.source_switcher.ThreadingHTTPServer"), patch(
        "libretime_playout.source_switcher.threading.Thread"
    ):
        with pytest.raises(TypeError):
            ss.start_listener(_make_switcher_with_recorder()[0], engine_kind="liquidsoap")
