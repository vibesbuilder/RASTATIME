from datetime import datetime, time, timedelta
from operator import itemgetter
from typing import Dict, Optional

from libretime_api_client.v2 import ApiClient
from libretime_shared.datetime import time_in_milliseconds, time_in_seconds

# T-GH-1: Liquidsoap removed — guarded import.
# When the liquidsoap package is absent (Windows / VLC-only mode), we use a
# minimal dataclass that provides the same attribute surface so that
# get_schedule() and generate_*_events() continue to work unchanged.
try:
    from ..liquidsoap.models import StreamPreferences
except ImportError:
    from dataclasses import dataclass

    @dataclass
    class StreamPreferences:  # type: ignore[no-redef]
        """Minimal StreamPreferences stub for VLC-only (Liquidsoap-free) mode."""
        input_fade_transition: float = 0.0
        message_format: int = 0
        message_offline: str = "Offline"
        replay_gain_enabled: bool = False
        replay_gain_offset: float = 0.0
        loudness_mode: Optional[str] = None
        loudness_target_lufs: float = -23.0
        loudness_true_peak_dbtp: float = -1.0

from .events import (
    ActionEvent,
    AnyEvent,
    EventKind,
    Events,
    FileEvent,
    LineinEvent,
    ShowRecordEvent,
    WebStreamEvent,
    datetime_to_event_key,
    make_event_key,
    event_isoparse,
    event_isoparse_exact,
)


def insert_event(events: Events, event_key: str, event: AnyEvent) -> None:
    key = event_key

    # RASTATIME 2026-09-10: callers pass keys with identity
    # (``make_event_key``), so two different events never share a key
    # any more; the ``_N`` search below only remains as a fallback.
    # Search for an empty slot
    index = 0
    while key in events:
        # Ignore duplicate event
        if event == events[key]:
            return

        key = f"{event_key}_{index}"
        index += 1

    events[key] = event


def get_schedule(api_client: ApiClient) -> Events:
    stream_preferences = StreamPreferences(**api_client.get_stream_preferences().json())

    current_time = datetime.utcnow()
    end_time = current_time + timedelta(days=1)

    current_time_str = current_time.isoformat(timespec="seconds")
    end_time_str = end_time.isoformat(timespec="seconds")

    schedule = api_client.list_schedule(
        params={
            "ends_after": f"{current_time_str}Z",
            "ends_before": f"{end_time_str}Z",
            "overbooked": False,
            "position_status__gt": 0,
        }
    ).json()

    events: Dict[str, AnyEvent] = {}
    for item in sorted(schedule, key=itemgetter("starts_at")):
        # 2026-09-29: keep the exact row times next to the whole seconds
        item["starts_at_exact"] = event_isoparse_exact(item["starts_at"])
        item["ends_at_exact"] = event_isoparse_exact(item["ends_at"])
        item["starts_at"] = event_isoparse(item["starts_at"])
        item["ends_at"] = event_isoparse(item["ends_at"])

        show_instance = api_client.get_show_instance(item["instance"]).json()
        show = api_client.get_show(show_instance["show"]).json()

        if show["live_enabled"]:
            show_instance["starts_at"] = event_isoparse(show_instance["starts_at"])
            show_instance["ends_at"] = event_isoparse(show_instance["ends_at"])
            generate_live_events(events, show_instance, stream_preferences)

        # RASTATIME 2026-05-17 - Phase B: Record-per-Show
        # (ARCHITECTURE Section 23.13).  If the show instance has
        # ``record_enabled`` set, emit a SHOW_RECORD_START at
        # show_instance.starts_at and a matching SHOW_RECORD_END at
        # show_instance.ends_at.  The recorder will read the active
        # Icecast mountpoint (which captures whichever source ends up
        # on air during this show) and write to a single .mp3 per
        # show-instance.  insert_event() dedupes if the same instance
        # is touched by multiple schedule items.
        #
        # NOTE: the Django ShowInstance model exposes the DB column
        # ``record`` as the Python attribute ``record_enabled``; the
        # REST ``ModelSerializer`` with ``fields = "__all__"`` uses
        # the Python attribute name in the JSON payload, so we must
        # read ``record_enabled`` here, not ``record``.  (This was a
        # silent regression first shipped in 2026-05-17 that caused
        # the recorder to never start.)
        if show_instance.get("record_enabled"):
            generate_show_record_events(events, show_instance, show)

        if item["file"]:
            file = api_client.get_file(item["file"]).json()
            generate_file_events(events, item, file, show, stream_preferences)

        elif item["stream"]:
            webstream = api_client.get_webstream(item["stream"]).json()
            generate_webstream_events(events, item, webstream, show)

        elif item.get("linein"):
            # RASTATIME 2026-05-12 — Phase B: Line-In scheduled item.
            #
            # The schedule API serialises ``Schedule.linein`` as the
            # integer pk of the rastatime_linein row.  We fetch the
            # detail via the linein REST endpoint (which now accepts
            # numeric pk in addition to the UUID) so we get the device
            # stable-ID needed for FFmpeg dshow capture.
            linein_pk = int(item["linein"])
            linein = _fetch_linein_by_pk(api_client, linein_pk)
            if linein is None:
                # Disabled / deleted while still referenced by a
                # schedule row.  Skip silently — the slot stays silent
                # rather than crashing the whole schedule load.
                continue
            generate_linein_events(events, item, linein, linein_pk, show)

    return dict(sorted(events.items()))


def _fetch_linein_by_pk(api_client: ApiClient, linein_pk: int) -> Optional[dict]:
    """
    Fetch one rastatime_linein row by its DB integer pk.

    Uses the same Django endpoint the Frontend talks to
    (``/api/v2/audio/linein/<id>``), which since Phase B.1 accepts
    both numeric pk and UUID.  Returns the decoded JSON dict, or
    ``None`` if the row no longer exists (or is disabled and 404s).

    Implementation note: we go through ``api_client.session`` directly
    rather than adding a typed ``get_linein()`` method because the
    api_client package is shared with upstream LibreTime and we want
    to keep our diff there minimal.

    The custom :class:`libretime_api_client._client.Session` prepends
    ``self.base_url`` to every request URL via ``create_url`` — so we
    pass only the path portion here, not an absolute URL.  Passing an
    absolute URL would produce nonsense like
    ``http://127.0.0.1:8765/http://127.0.0.1:8765/...`` and a 404.
    """
    path = f"/api/v2/audio/linein/{linein_pk}"
    try:
        resp = api_client.session.get(path, timeout=5)
    except Exception:  # pylint: disable=broad-exception-caught
        return None
    if resp.status_code != 200:
        return None
    try:
        return resp.json()
    except Exception:  # pylint: disable=broad-exception-caught
        return None


def generate_live_events(
    events: Events,
    show_instance: dict,
    stream_preferences: StreamPreferences,
):
    transition = timedelta(seconds=stream_preferences.input_fade_transition)

    switch_off = show_instance["ends_at"] - transition
    kick_out = show_instance["ends_at"]
    instance_id = show_instance.get("id")
    switch_off_event_key = make_event_key(switch_off, f"switch_off-{instance_id}")
    kick_out_event_key = make_event_key(kick_out, f"kick_out-{instance_id}")

    # If enabled, fade the input source out
    if switch_off != kick_out:
        switch_off_event = ActionEvent(
            type=EventKind.ACTION,
            event_type="switch_off",
            start=switch_off,
            end=switch_off,
        )
        insert_event(events, switch_off_event_key, switch_off_event)

    # Then kick the source out
    kick_out_event = ActionEvent(
        type=EventKind.ACTION,
        event_type="kick_out",
        start=kick_out,
        end=kick_out,
    )
    insert_event(events, kick_out_event_key, kick_out_event)


def generate_file_events(
    events: Events,
    schedule: dict,
    file: dict,
    show: dict,
    stream_preferences: StreamPreferences,
):
    """
    Generate events for a scheduled file.
    """
    event = FileEvent(
        type=EventKind.FILE,
        row_id=schedule["id"],
        start=schedule["starts_at"],
        end=schedule["ends_at"],
        start_exact=schedule.get("starts_at_exact"),
        end_exact=schedule.get("ends_at_exact"),
        uri=file["url"],
        id=file["id"],
        # Show data
        show_name=show["name"],
        # Extra data
        fade_in=time_in_milliseconds(time.fromisoformat(schedule["fade_in"])),
        fade_out=time_in_milliseconds(time.fromisoformat(schedule["fade_out"])),
        cue_in=time_in_seconds(time.fromisoformat(schedule["cue_in"])),
        cue_out=time_in_seconds(time.fromisoformat(schedule["cue_out"])),
        # File data
        track_title=file.get("track_title"),
        artist_name=file.get("artist_name"),
        mime=file["mime"],
        replay_gain=file["replay_gain"],
        filesize=file["size"],
        # RASTATIME 2026-09-27 - show boundary + "No Fade during Crossover"
        instance_id=schedule.get("instance"),
        no_fade_crossfade=bool(file.get("no_fade_crossfade") or False),
        # RASTATIME 2026-09-29 - crossfade per track type / Exclude from Crossover
        crossfade_seconds=_float_or_none(file.get("track_type_crossfade")),
        exclude_crossfade=bool(file.get("exclude_crossfade") or False),
    )

    event.replay_gain = file_gain_db(file, stream_preferences)

    insert_event(events, make_event_key(event.start, f"file-{event.row_id}"), event)


# RASTATIME 2026-09-28 - ReplayGain 1.0 measures against a reference that
# sits around -18 LUFS; a file without an R128 measurement yet uses it as
# an approximation in R128 mode until "Measure loudness now" has run.
REPLAYGAIN_REFERENCE_LUFS = -18.0


def _float_or_none(raw) -> Optional[float]:
    try:
        return float(raw) if raw is not None and raw != "" else None
    except (TypeError, ValueError):
        return None


def file_gain_db(file: dict, stream_preferences) -> Optional[float]:
    """
    RASTATIME 2026-09-28 - the per-track gain (dB) for the annotate
    ``replaygain_track_gain`` field, by Settings -> Streams -> Loudness
    Normalization:

      off         None (unity gain)
      replaygain  ReplayGain value + modifier (as before)
      r128        target - integrated loudness, capped so the file's true
                  peak never exceeds the ceiling (the bus limiter stays the
                  safety net); an unmeasured file falls back to the
                  ReplayGain value shifted to the target.
    """
    mode = getattr(stream_preferences, "loudness_mode", None) or (
        "replaygain" if stream_preferences.replay_gain_enabled else "off"
    )
    replay_gain = _float_or_none(file.get("replay_gain")) or 0.0
    if mode == "r128":
        target = float(getattr(stream_preferences, "loudness_target_lufs", -23.0))
        ceiling = float(getattr(stream_preferences, "loudness_true_peak_dbtp", -1.0))
        loudness = _float_or_none(file.get("loudness_lufs"))
        if loudness is None:
            return round(replay_gain + (target - REPLAYGAIN_REFERENCE_LUFS), 2)
        gain = target - loudness
        true_peak = _float_or_none(file.get("true_peak_dbtp"))
        # Only a BOOST is capped by the file's true peak.  A loud file is
        # attenuated to the target whatever its peaks are: MP3s routinely
        # measure +1..+2 dBTP and a decoder glitch can read +15 (library
        # 2026-09-29) - pulling the whole track down for that would play it
        # below the target; the bus limiter takes the peaks.
        if gain > 0 and true_peak is not None and true_peak + gain > ceiling:
            gain = max(0.0, ceiling - true_peak)
        return round(gain, 2)
    if mode == "replaygain":
        return replay_gain + float(stream_preferences.replay_gain_offset or 0.0)
    return None


def generate_show_record_events(
    events: Events,
    show_instance: dict,
    show: dict,
):
    """
    RASTATIME 2026-05-17 - Phase B: Record-per-Show.

    Emit exactly two events for a single show instance whose
    ``record`` flag is true:

      * SHOW_RECORD_START at show_instance.starts_at — the playout
        scheduler spawns an FfmpegRecorder that taps the first
        configured Icecast output mountpoint and writes
        ``<recording-folder>/<YYYY-MM-DD>/<YYYY-MM-DD HH-MM> - <show-name>.mp3``.
      * SHOW_RECORD_END at show_instance.ends_at — the scheduler
        stops the matching recorder (looked up by show_id).

    Idempotent: if the parent function calls us again for the same
    show instance (because that show has multiple schedule items),
    ``insert_event`` dedupes on the (event_key, structural equality)
    pair so we end up with exactly one START + one END.
    """
    # show_instance timestamps may already be datetime objects (the
    # live-events branch above mutates them); be tolerant of both.
    starts_at = show_instance["starts_at"]
    ends_at = show_instance["ends_at"]
    if isinstance(starts_at, str):
        starts_at = event_isoparse(starts_at)
    if isinstance(ends_at, str):
        ends_at = event_isoparse(ends_at)

    start_event = ShowRecordEvent(
        type=EventKind.SHOW_RECORD_START,
        start=starts_at,
        end=starts_at,
        show_id=int(show["id"]),
        show_name=str(show.get("name") or ""),
        show_starts_at=starts_at,
    )
    instance_id = show_instance.get("id")
    insert_event(events, make_event_key(starts_at, f"record-start-{instance_id}"), start_event)

    end_event = ShowRecordEvent(
        type=EventKind.SHOW_RECORD_END,
        start=ends_at,
        end=ends_at,
        show_id=int(show["id"]),
        show_name=str(show.get("name") or ""),
        show_starts_at=starts_at,
    )
    insert_event(events, make_event_key(ends_at, f"record-end-{instance_id}"), end_event)


def generate_webstream_events(
    events: Events,
    schedule: dict,
    webstream: dict,
    show: dict,
):
    """
    Generate events for a scheduled webstream.
    """
    row = schedule["id"]
    buffer_start_key = make_event_key(schedule["starts_at"], f"ws-buffer-{row}")
    play_key = make_event_key(schedule["starts_at"], f"ws-play-{row}")
    buffer_end_key = make_event_key(schedule["ends_at"], f"ws-buffer-end-{row}")
    stop_key = make_event_key(schedule["ends_at"], f"ws-stop-{row}")

    # RASTATIME 2026-05-16 - per-webstream static input gain (dB), if set
    # on the cc_webstream row.  Older API responses without this field
    # gracefully fall back to None (no gain).  Stamped on every event of
    # this stream so the playout scheduler's resume path can read it
    # back from `_current_event` after DJ-disconnect.
    input_gain_db = webstream.get("input_gain_db")
    if input_gain_db is not None:
        input_gain_db = float(input_gain_db)

    stream_buffer_start_event = WebStreamEvent(
        type=EventKind.WEB_STREAM_BUFFER_START,
        row_id=schedule["id"],
        start=schedule["starts_at"] - timedelta(seconds=5),
        end=schedule["starts_at"] - timedelta(seconds=5),
        uri=webstream["url"],
        id=webstream["id"],
        # Show data
        show_name=show["name"],
        input_gain_db=input_gain_db,
    )
    insert_event(events, buffer_start_key, stream_buffer_start_event)

    stream_output_start_event = WebStreamEvent(
        type=EventKind.WEB_STREAM_OUTPUT_START,
        row_id=schedule["id"],
        start=schedule["starts_at"],
        end=schedule["ends_at"],
        start_exact=schedule.get("starts_at_exact"),
        end_exact=schedule.get("ends_at_exact"),
        uri=webstream["url"],
        id=webstream["id"],
        # Show data
        show_name=show["name"],
        input_gain_db=input_gain_db,
    )
    insert_event(events, play_key, stream_output_start_event)

    # NOTE: stream_*_end were previously triggered 1 second before
    # the schedule end.
    stream_buffer_end_event = WebStreamEvent(
        type=EventKind.WEB_STREAM_BUFFER_END,
        row_id=schedule["id"],
        start=schedule["ends_at"],
        end=schedule["ends_at"],
        uri=webstream["url"],
        id=webstream["id"],
        # Show data
        show_name=show["name"],
        input_gain_db=input_gain_db,
    )
    insert_event(events, buffer_end_key, stream_buffer_end_event)

    stream_output_end_event = WebStreamEvent(
        type=EventKind.WEB_STREAM_OUTPUT_END,
        row_id=schedule["id"],
        start=schedule["ends_at"],
        end=schedule["ends_at"],
        uri=webstream["url"],
        id=webstream["id"],
        # Show data
        show_name=show["name"],
        input_gain_db=input_gain_db,
    )
    insert_event(events, stop_key, stream_output_end_event)


def generate_linein_events(
    events: Events,
    schedule: dict,
    linein: dict,
    linein_pk: int,
    show: dict,
):
    """
    Generate events for a scheduled Line-In Library item (Phase B).

    Unlike WebStreamEvent (which has buffer-start / output-start /
    buffer-end / output-end), Line-In capture has symmetric start and
    teardown — one LINEIN_START event marks the slot.  The
    PlayoutScheduler arms a separate stop timer at ``schedule["ends_at"]``
    that runs the same teardown path as FileEvent.

    No pre-buffer offset: a microphone is "live" instantly, there's
    nothing to pre-fill like an HTTP-stream cache.

    ``linein_pk`` is passed in separately because the Django
    serializer returns the domain UUID as ``linein["id"]``, not the
    integer DB pk — but the playout side wants the pk for log lines
    and FK lookups.
    """
    linein_key = make_event_key(schedule["starts_at"], f"linein-{schedule['id']}")

    linein_start_event = LineinEvent(
        type=EventKind.LINEIN_START,
        row_id=schedule["id"],
        start=schedule["starts_at"],
        end=schedule["ends_at"],
        start_exact=schedule.get("starts_at_exact"),
        end_exact=schedule.get("ends_at_exact"),
        id=linein_pk,
        # show / display data
        show_name=show["name"],
        device_id=linein.get("device_id", ""),
        name=linein.get("name", ""),
        # RASTATIME 2026-05-14 — B.4 #4: friendly-name fallback hint
        # for the playout's device resolver.  Optional; empty string
        # means no fallback available (legacy rows pre-dating the
        # rastatime_linein.device_name column).
        device_name=linein.get("device_name", ""),
        # RASTATIME 2026-08-31 — channel selection on multichannel
        # interfaces.  Falsy / missing (legacy rows) defaults to plain
        # stereo, which keeps the proven dshow capture path.
        channel_mapping=list(linein.get("channel_mapping") or [0, 1]),
    )
    insert_event(events, linein_key, linein_start_event)
