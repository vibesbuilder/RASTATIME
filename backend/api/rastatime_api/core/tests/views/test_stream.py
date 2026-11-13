from rest_framework.test import APIClient


# pylint: disable=invalid-name,unused-argument
def test_stream_preferences_get(db, api_client: APIClient):
    response = api_client.get("/api/v2/stream/preferences")
    assert response.status_code == 200
    assert response.json() == {
        "input_fade_transition": 0.0,
        "message_format": 0,
        "message_offline": "LibreTime - offline",
        "replay_gain_enabled": True,
        "replay_gain_offset": 0.0,
        "loudness_mode": "replaygain",
        "loudness_target_lufs": -23.0,
        "loudness_true_peak_dbtp": -1.0,
    }


# pylint: disable=invalid-name,unused-argument
def test_stream_state_get(db, api_client: APIClient):
    response = api_client.get("/api/v2/stream/state")
    assert response.status_code == 200
    assert response.json() == {
        "input_main_connected": False,
        "input_main_streaming": False,
        "input_show_connected": False,
        "input_show_streaming": False,
        "schedule_streaming": True,
    }


# RASTATIME 2026-11-13 - "Record Start": the recording-folder endpoint
# carries the offset of the show recording's start and end.
def test_recording_folder_record_start_offset_default(db, api_client: APIClient):
    response = api_client.get("/api/v2/recording-folder")
    assert response.status_code == 200
    assert response.json()["record_start_offset"] == 0.0


def test_recording_folder_record_start_offset_parsing():
    from rastatime_api.core.views.stream import LocalRecordingFolderView

    parse = LocalRecordingFolderView.record_start_offset
    assert parse("2.5") == 2.5
    assert parse("-3") == -3.0
    assert parse("1,5") == 1.5
    assert parse("2.26") == 2.3
    assert parse("999") == 60.0
    assert parse("-999") == -60.0
    assert parse("") == 0.0
    assert parse(None) == 0.0
    assert parse("abc") == 0.0
    assert parse("nan") == 0.0
