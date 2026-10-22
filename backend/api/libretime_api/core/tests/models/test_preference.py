from libretime_api.core.models.preference import Preference


# pylint: disable=invalid-name,unused-argument
def test_preference_get_site_preferences(db):
    result = Preference.get_site_preferences()
    assert result.model_dump() == {
        # RASTATIME 2026-10-03 (ad12764, brand stage A): default station name
        "station_name": "RASTATIME",
    }


# pylint: disable=invalid-name,unused-argument
def test_preference_get_stream_preferences(db):
    result = Preference.get_stream_preferences()
    assert result.model_dump() == {
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
def test_preference_get_stream_state(db):
    result = Preference.get_stream_state()
    assert result.model_dump() == {
        "input_main_connected": False,
        "input_main_streaming": False,
        "input_show_connected": False,
        "input_show_streaming": False,
        "schedule_streaming": True,
    }
