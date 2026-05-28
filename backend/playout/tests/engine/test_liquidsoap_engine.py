"""
RASTATIME 2026-05-26 — Unit tests for LiquidsoapPlayoutEngine
(Seamless-Bus-Mix Phase C2).

Strategy
--------

The engine talks to Liquidsoap entirely through a
:class:`LiquidsoapTelnetClient` instance.  Phase C1 already
covers the wire protocol with a real TCP fake server — those
tests verify that the bytes on the socket are correct.

Here in C2 we test the **engine logic on top of the client**:

  * play() builds the right annotate-URI and pushes it
  * stop() / close() route through the right telnet calls
  * URI normalisation (Windows path → file:///) is correct
  * State transitions (STOPPED → PLAYING → STOPPED / ERROR)
  * Telnet failures in play()/stop()/close() do NOT propagate
    out as exceptions — they flip state + log
  * close() is idempotent

To do that cleanly we inject a ``MagicMock(spec=...)`` telnet
client into the engine via the ``telnet_client=`` constructor
arg — no real socket I/O, no live Liquidsoap subprocess, no
flaky test timing.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from libretime_playout.engine.interface import PlayoutState
from libretime_playout.engine.liquidsoap_engine import (
    LiquidsoapPlayoutEngine,
)
from libretime_playout.engine.liquidsoap_telnet import (
    LiquidsoapTelnetClient,
)


# ---- Helpers ------------------------------------------------------------


def _make_engine_with_mock(mock_telnet=None):
    """Build a LiquidsoapPlayoutEngine wired to a MagicMock telnet client."""
    if mock_telnet is None:
        mock_telnet = MagicMock(spec=LiquidsoapTelnetClient)
        # request_queue_push returns a fake request-id by default.
        mock_telnet.request_queue_push.return_value = "42"
        # Realistic mock attrs the engine reads for logging.
        mock_telnet._host = "127.0.0.1"
        mock_telnet._port = 1234
    return LiquidsoapPlayoutEngine(telnet_client=mock_telnet), mock_telnet


# ---- URI normalisation --------------------------------------------------


def test_normalise_windows_path_backslash():
    """Windows back-slash drive path → file://C:/... (2 slashes, Liquidsoap 2.4)."""
    assert LiquidsoapPlayoutEngine._normalise_uri(
        r"C:\rastatime\580.mp3"
    ) == "file://C:/rastatime/580.mp3"


def test_normalise_windows_path_forwardslash():
    """Windows forward-slash drive path → same file:// shape."""
    assert LiquidsoapPlayoutEngine._normalise_uri(
        "C:/rastatime/580.mp3"
    ) == "file://C:/rastatime/580.mp3"


def test_normalise_3slash_file_uri_rewritten_to_2slash():
    """Legacy file:///C:/... URI gets rewritten to 2-slash form."""
    assert LiquidsoapPlayoutEngine._normalise_uri(
        "file://C:/rastatime/580.mp3"
    ) == "file://C:/rastatime/580.mp3"


def test_normalise_2slash_file_uri_passes_through():
    """Already-correct 2-slash file:// URI is left alone."""
    assert LiquidsoapPlayoutEngine._normalise_uri(
        "file://C:/rastatime/580.mp3"
    ) == "file://C:/rastatime/580.mp3"


def test_normalise_http_passes_through():
    """HTTP URIs pass through unchanged."""
    assert LiquidsoapPlayoutEngine._normalise_uri(
        "http://example.com/stream.mp3"
    ) == "http://example.com/stream.mp3"


def test_normalise_lowercase_drive_letter():
    """Lower-case drive letter still gets the file:// wrapping."""
    assert LiquidsoapPlayoutEngine._normalise_uri(
        r"d:\music\track.mp3"
    ) == "file://d:/music/track.mp3"


# ---- Annotate URI building ----------------------------------------------


def test_annotate_no_options_returns_bare_uri():
    """No cue points + no gain → bare URI, no annotate: wrap."""
    out = LiquidsoapPlayoutEngine._build_annotate_uri(
        "file:///x.mp3", cue_in=0.0, cue_out=None, gain_db=None,
    )
    assert out == "file:///x.mp3"


def test_annotate_zero_gain_returns_bare_uri():
    """gain_db == 0.0 (within float epsilon) → no annotate."""
    out = LiquidsoapPlayoutEngine._build_annotate_uri(
        "file:///x.mp3", cue_in=0.0, cue_out=None, gain_db=0.0,
    )
    assert out == "file:///x.mp3"


def test_annotate_cue_in_only():
    """Only cue_in present → annotate with just that key."""
    out = LiquidsoapPlayoutEngine._build_annotate_uri(
        "file:///x.mp3", cue_in=2.5, cue_out=None, gain_db=None,
    )
    assert out == 'annotate:cue_in="2.50":file:///x.mp3'


def test_annotate_cue_out_only():
    """Only cue_out present → annotate with just that key."""
    out = LiquidsoapPlayoutEngine._build_annotate_uri(
        "file:///x.mp3", cue_in=0.0, cue_out=180.0, gain_db=None,
    )
    assert out == 'annotate:cue_out="180.00":file:///x.mp3'


def test_annotate_gain_negative():
    """Negative gain (typical ReplayGain) is rendered with sign + dB."""
    out = LiquidsoapPlayoutEngine._build_annotate_uri(
        "file:///x.mp3", cue_in=0.0, cue_out=None, gain_db=-5.95,
    )
    assert out == 'annotate:replaygain_track_gain="-5.95 dB":file:///x.mp3'


def test_annotate_gain_positive():
    """Positive gain gets a leading '+'."""
    out = LiquidsoapPlayoutEngine._build_annotate_uri(
        "file:///x.mp3", cue_in=0.0, cue_out=None, gain_db=3.5,
    )
    assert out == 'annotate:replaygain_track_gain="+3.50 dB":file:///x.mp3'


def test_annotate_all_three_attrs():
    """All three options → annotate: with three comma-separated KVs."""
    out = LiquidsoapPlayoutEngine._build_annotate_uri(
        "file:///x.mp3", cue_in=0.5, cue_out=180.0, gain_db=-5.95,
    )
    assert out == (
        'annotate:cue_in="0.50",cue_out="180.00",'
        'replaygain_track_gain="-5.95 dB":file:///x.mp3'
    )


# ---- Short-track crossfade-override REVERTED (Phase-D, 2026-05-28) -----
# The attempted `liq_cross_duration="0.0"` annotation for tracks under
# 8 s caused Liquidsoap to drop the tracks completely (jingles went from
# "barely audible" to "completely silent") in live-test at 18:16 / 18:21.
# Reverted.  See LiquidsoapPlayoutEngine._build_annotate_uri comment +
# BACKLOG entry "smarter short-track handling in Liquidsoap crossfade".


def test_annotate_no_liq_cross_duration_for_any_track_length():
    """
    Regression guard: NO liq_cross_duration annotation should be added
    for any track length until we find a working approach (see comment
    in _build_annotate_uri).  Setting liq_cross_duration=0.0 was the
    Phase-D 2026-05-28 attempt that caused tracks to be silenced
    completely — reverted.
    """
    for cue_out in (None, 0.0, 3.23, 5.0, 7.99, 8.0, 180.0):
        out = LiquidsoapPlayoutEngine._build_annotate_uri(
            "file:///x.mp3", cue_in=0.0, cue_out=cue_out, gain_db=None,
        )
        assert "liq_cross_duration" not in out, (
            f"unexpected liq_cross_duration annotation for cue_out={cue_out}: {out}"
        )


def test_annotate_with_windows_path():
    """Windows path gets normalised THEN wrapped in annotate."""
    out = LiquidsoapPlayoutEngine._build_annotate_uri(
        r"C:\rastatime\580.mp3",
        cue_in=0.0, cue_out=None, gain_db=-2.0,
    )
    assert out == (
        'annotate:replaygain_track_gain="-2.00 dB":'
        'file://C:/rastatime/580.mp3'
    )


# ---- Annotate with metadata (Phase C6 Teil 2) ---------------------------


def test_annotate_with_metadata_only():
    """metadata-only annotate: no cue, no gain — just metadata keys."""
    out = LiquidsoapPlayoutEngine._build_annotate_uri(
        "file:///x.mp3", cue_in=0.0, cue_out=None, gain_db=None,
        metadata={"title": "Song Title", "artist": "Band Name"},
    )
    assert out == (
        'annotate:title="Song Title",artist="Band Name":file:///x.mp3'
    )


def test_annotate_metadata_skips_none_values():
    """None / empty-string metadata values are silently skipped."""
    out = LiquidsoapPlayoutEngine._build_annotate_uri(
        "file:///x.mp3", cue_in=0.0, cue_out=None, gain_db=None,
        metadata={"title": "Song", "artist": None, "album": ""},
    )
    assert out == 'annotate:title="Song":file:///x.mp3'


def test_annotate_metadata_empty_dict_no_wrap():
    """Empty metadata dict → no annotate wrapper at all."""
    out = LiquidsoapPlayoutEngine._build_annotate_uri(
        "file:///x.mp3", cue_in=0.0, cue_out=None, gain_db=None,
        metadata={},
    )
    assert out == "file:///x.mp3"


def test_annotate_metadata_escapes_quotes():
    """Embedded double-quote in metadata value → backslash-escaped."""
    out = LiquidsoapPlayoutEngine._build_annotate_uri(
        "file:///x.mp3", cue_in=0.0, cue_out=None, gain_db=None,
        metadata={"title": 'He said "Hello"'},
    )
    assert out == (
        'annotate:title="He said \\"Hello\\"":file:///x.mp3'
    )


def test_annotate_metadata_escapes_backslashes():
    """Embedded backslash in metadata value → doubled."""
    out = LiquidsoapPlayoutEngine._build_annotate_uri(
        "file:///x.mp3", cue_in=0.0, cue_out=None, gain_db=None,
        metadata={"path": r"C:\foo\bar"},
    )
    assert out == 'annotate:path="C:\\\\foo\\\\bar":file:///x.mp3'


def test_annotate_all_three_attrs_plus_metadata():
    """Cue + gain + metadata all together — order: cue, gain, then metadata."""
    out = LiquidsoapPlayoutEngine._build_annotate_uri(
        "file:///x.mp3", cue_in=0.5, cue_out=180.0, gain_db=-5.95,
        metadata={"title": "Song", "artist": "Band"},
    )
    assert out == (
        'annotate:cue_in="0.50",cue_out="180.00",'
        'replaygain_track_gain="-5.95 dB",'
        'title="Song",artist="Band":file:///x.mp3'
    )


def test_play_passes_metadata_to_telnet():
    """play(metadata=...) flows through to request_queue_push payload."""
    eng, telnet = _make_engine_with_mock()
    eng.play(
        r"C:\rastatime\foo.mp3", cue_in=0.0, gain_db=-3.0,
        metadata={"title": "Song", "artist": "Band"},
    )
    expected = (
        'annotate:replaygain_track_gain="-3.00 dB",'
        'title="Song",artist="Band":'
        'file://C:/rastatime/foo.mp3'
    )
    telnet.request_queue_push.assert_called_once_with(expected)


def test_play_without_metadata_still_works():
    """metadata is fully optional — old-style calls still pass."""
    eng, telnet = _make_engine_with_mock()
    eng.play("file:///x.mp3")
    telnet.request_queue_push.assert_called_once_with("file:///x.mp3")


# ---- play() / stop() / state machine ------------------------------------


def test_play_pushes_to_request_queue():
    """play() sends the annotate-wrapped URI to request_queue_push."""
    eng, telnet = _make_engine_with_mock()
    eng.play(r"C:\rastatime\foo.mp3", cue_in=0.5,
             cue_out=120.0, gain_db=-3.0)
    expected_uri = (
        'annotate:cue_in="0.50",cue_out="120.00",'
        'replaygain_track_gain="-3.00 dB":'
        'file://C:/rastatime/foo.mp3'
    )
    telnet.request_queue_push.assert_called_once_with(expected_uri)


def test_play_transitions_to_playing():
    """Successful play() flips state to PLAYING."""
    eng, _ = _make_engine_with_mock()
    assert eng.get_state() == PlayoutState.STOPPED
    eng.play("file:///x.mp3")
    assert eng.get_state() == PlayoutState.PLAYING


def test_play_records_request_id():
    """Numeric reply from Liquidsoap is stored as the current request id."""
    eng, telnet = _make_engine_with_mock()
    telnet.request_queue_push.return_value = "7"
    eng.play("file:///x.mp3")
    assert eng._current_request_id == "7"


def test_play_multiline_response_request_id_first_line():
    """Multi-line response — first line wins if it's a digit string."""
    eng, telnet = _make_engine_with_mock()
    telnet.request_queue_push.return_value = "99\nsome extra info"
    eng.play("file:///x.mp3")
    assert eng._current_request_id == "99"


def test_play_non_numeric_non_error_response_treated_as_unknown_id():
    """
    Non-digit but non-ERROR response → request_id stays None, state
    stays PLAYING (push was accepted by some operator the engine
    doesn't understand the reply format of, but the queue did take it).
    The explicit 'ERROR' prefix is reserved for genuine push-failure
    (covered by test_play_error_response_flips_state_to_error).
    """
    eng, telnet = _make_engine_with_mock()
    telnet.request_queue_push.return_value = "OK pushed"
    eng.play("file:///x.mp3")
    assert eng._current_request_id is None
    assert eng.get_state() == PlayoutState.PLAYING


def test_play_handles_telnet_error_without_raising():
    """ConnectionError from telnet → ERROR state, no exception leak."""
    eng, telnet = _make_engine_with_mock()
    telnet.request_queue_push.side_effect = ConnectionError("ls dead")
    # Must NOT raise — scheduler treats play exceptions as fatal.
    eng.play("file:///x.mp3")
    assert eng.get_state() == PlayoutState.ERROR


def test_play_error_response_flips_state_to_error():
    """
    Liquidsoap reply that starts with 'ERROR' → state ERROR, not PLAYING.

    The pathological case this protects against (regression from the
    Phase-C8 reality-test): if the .liq's queue ID and the Python
    side's command name don't match, Liquidsoap replies with
    'ERROR: unknown command, type help to get a list of commands.'
    The engine used to silently flip to PLAYING with request_id=None
    and listeners only heard silence.  Now we surface the rejection
    as ERROR + log line.
    """
    eng, telnet = _make_engine_with_mock()
    telnet.request_queue_push.return_value = (
        "ERROR: unknown command, type \"help\" to get a list of commands."
    )
    eng.play("file:///x.mp3")
    assert eng.get_state() == PlayoutState.ERROR
    # request_id stays None — nothing was actually queued.
    assert eng._current_request_id is None


def test_stop_defers_request_queue_skip():
    """
    stop() does NOT send skip immediately — it defers up to
    _DEFERRED_STOP_SECONDS so a follow-up play() with the same URI can
    cancel it (catch-up idempotency).
    """
    eng, telnet = _make_engine_with_mock()
    eng.play("file:///x.mp3")
    telnet.request_queue_skip.reset_mock()
    eng.stop()
    # Right after stop() returns: NO skip on the wire yet.
    telnet.request_queue_skip.assert_not_called()
    assert eng._stop_requested is True


def test_stop_flushed_by_timer_after_window():
    """
    If no play() comes within _DEFERRED_STOP_SECONDS, the timer
    eventually flushes the skip.
    """
    import time
    from libretime_playout.engine.liquidsoap_engine import _DEFERRED_STOP_SECONDS
    eng, telnet = _make_engine_with_mock()
    eng.play("file:///x.mp3")
    telnet.request_queue_skip.reset_mock()
    eng.stop()
    # Wait past the deferral window plus a small grace period.
    time.sleep(_DEFERRED_STOP_SECONDS + 0.3)
    telnet.request_queue_skip.assert_called_once_with()
    assert eng.get_state() == PlayoutState.STOPPED
    assert eng._current_uri is None


def test_stop_then_play_same_uri_is_idempotent():
    """
    Pypo's catch-up pattern: stop() then play() for the SAME URI
    within the deferral window.  Both calls collapse — no skip,
    no second push, track keeps playing on Liquidsoap.
    """
    eng, telnet = _make_engine_with_mock()
    eng.play("file:///x.mp3")  # PLAYING
    telnet.reset_mock()
    eng.stop()
    eng.play("file:///x.mp3")  # same URI, within window
    # Neither skip nor a second push hit the wire.
    telnet.request_queue_skip.assert_not_called()
    telnet.request_queue_push.assert_not_called()
    # State remained PLAYING.
    assert eng.get_state() == PlayoutState.PLAYING
    assert eng._current_uri == "file:///x.mp3"


def test_stop_then_play_different_uri_flushes_skip_then_pushes():
    """
    Real track transition: stop() then play() for a DIFFERENT URI.
    Skip is flushed immediately (no wait for the deferral timer),
    then the new track pushed.
    """
    eng, telnet = _make_engine_with_mock()
    eng.play("file:///old.mp3")
    telnet.reset_mock()
    telnet.request_queue_push.return_value = "42"
    eng.stop()
    eng.play("file:///new.mp3")
    # Skip was flushed before the new push.
    telnet.request_queue_skip.assert_called_once_with()
    # file:///new.mp3 has no Windows-drive after the prefix, so the
    # normaliser leaves it as 3-slash (the rewrite branch only triggers
    # for real Windows drive paths like file:///C:/...).
    telnet.request_queue_push.assert_called_once_with("file:///new.mp3")
    assert eng.get_state() == PlayoutState.PLAYING
    assert eng._current_uri == "file:///new.mp3"


def test_stop_handles_telnet_error_without_raising():
    """
    ConnectionError from telnet during the timer-driven flush — must
    not propagate out of the timer thread.  We trigger the flush
    synchronously by calling _flush_pending_stop after stop().
    """
    eng, telnet = _make_engine_with_mock()
    eng.play("file:///x.mp3")
    telnet.request_queue_skip.side_effect = ConnectionError("ls dead")
    eng.stop()
    # Cancel the real timer + run the flush inline so the test doesn't
    # have to sleep.
    if eng._stop_timer is not None:
        eng._stop_timer.cancel()
    eng._flush_pending_stop()
    assert eng.get_state() == PlayoutState.STOPPED


def test_close_flushes_pending_stop():
    """
    close() during a deferred-stop window flushes the skip
    synchronously so the running track stops at shutdown.
    """
    eng, telnet = _make_engine_with_mock()
    eng.play("file:///x.mp3")
    telnet.reset_mock()
    eng.stop()  # pending stop armed
    eng.close()
    telnet.request_queue_skip.assert_called_once_with()
    telnet.close.assert_called_once_with()


# ---- close() ------------------------------------------------------------


def test_close_calls_telnet_close():
    """close() forwards to telnet.close()."""
    eng, telnet = _make_engine_with_mock()
    eng.close()
    telnet.close.assert_called_once_with()


def test_close_idempotent_on_telnet_error():
    """close() swallows telnet errors so shutdown is always clean."""
    eng, telnet = _make_engine_with_mock()
    telnet.close.side_effect = ConnectionError("already dead")
    eng.close()  # must not raise


# ---- wait_until_stopped / set_audio_device ------------------------------


def test_wait_until_stopped_is_immediate_true():
    """Liquidsoap engine has native gapless — no wait needed."""
    eng, _ = _make_engine_with_mock()
    # Even with a "long" timeout the call returns essentially instantly.
    import time
    start = time.monotonic()
    assert eng.wait_until_stopped(timeout=5.0) is True
    assert time.monotonic() - start < 0.1  # truly immediate, not polling


def test_set_audio_device_is_warn_only_no_op():
    """set_audio_device() logs a warning and does nothing else."""
    eng, telnet = _make_engine_with_mock()
    eng.set_audio_device("device-id-xyz")
    # No telnet calls — device switching is a .liq script concern.
    telnet.request_queue_push.assert_not_called()
    telnet.var_set.assert_not_called()


# ---- _extract_request_id micro-helper -----------------------------------


def test_extract_request_id_basic():
    assert LiquidsoapPlayoutEngine._extract_request_id("42") == "42"


def test_extract_request_id_multiline():
    assert LiquidsoapPlayoutEngine._extract_request_id("17\nbla") == "17"


def test_extract_request_id_with_whitespace():
    assert LiquidsoapPlayoutEngine._extract_request_id("  99  ") == "99"


def test_extract_request_id_empty():
    assert LiquidsoapPlayoutEngine._extract_request_id("") is None


def test_extract_request_id_non_digit():
    assert LiquidsoapPlayoutEngine._extract_request_id("ERROR") is None


# ---- _redact micro-helper -----------------------------------------------


def test_redact_strips_password():
    assert LiquidsoapPlayoutEngine._redact(
        "http://user:secret@stream.com/mount"
    ) == "http://user:***@stream.com/mount"


def test_redact_no_userinfo():
    assert LiquidsoapPlayoutEngine._redact(
        "http://stream.com/mount"
    ) == "http://stream.com/mount"


def test_redact_file_uri_no_userinfo():
    assert LiquidsoapPlayoutEngine._redact(
        "file:///C:/x.mp3"
    ) == "file:///C:/x.mp3"


def test_redact_none():
    assert LiquidsoapPlayoutEngine._redact(None) == ""
