"""RASTATIME 2026-10-14 - stream metadata per file / track type."""

from rastatime_playout.player.schedule import _effective_icy_hidden


def test_file_choice_wins_over_type():
    assert _effective_icy_hidden({"icy_forward": 0, "track_type_icy_forward": True}) is True
    assert _effective_icy_hidden({"icy_forward": 1, "track_type_icy_forward": False}) is False


def test_as_the_track_type_uses_the_preset():
    assert _effective_icy_hidden({"icy_forward": None, "track_type_icy_forward": False}) is True
    assert _effective_icy_hidden({"icy_forward": None, "track_type_icy_forward": True}) is False


def test_older_feed_without_the_fields_forwards():
    assert _effective_icy_hidden({}) is False
    assert _effective_icy_hidden({"icy_forward": ""}) is False
