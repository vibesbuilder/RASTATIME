from enum import Enum
from typing import Optional

from django.db import models
from pydantic import BaseModel


class SitePreferences(BaseModel):
    station_name: str


class MessageFormatKind(int, Enum):
    ARTIST_TITLE = 0
    SHOW_ARTIST_TITLE = 1
    RADIO_SHOW = 2


class StreamPreferences(BaseModel):
    input_fade_transition: float
    message_format: MessageFormatKind
    message_offline: str
    replay_gain_enabled: bool
    replay_gain_offset: float
    # RASTATIME 2026-09-28 - Loudness Normalization (Settings -> Streams):
    # "off" | "replaygain" | "r128"; target and true-peak ceiling for R128
    # None = a payload from before the setting: readers derive the mode
    # from replay_gain_enabled
    loudness_mode: Optional[str] = None
    loudness_target_lufs: float = -23.0
    loudness_true_peak_dbtp: float = -1.0

    # input_auto_switch_off: bool
    # input_auto_switch_on: bool
    # input_main_user: str
    # input_main_password: str
    # track_fade_in: float
    # track_fade_out: float
    # track_fade_transition: float


class StreamState(BaseModel):
    input_main_connected: bool
    input_main_streaming: bool
    input_show_connected: bool
    input_show_streaming: bool
    schedule_streaming: bool


class SitePreferenceManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(user__isnull=True)


class Preference(models.Model):
    user = models.ForeignKey(
        "core.User",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        db_column="subjid",
    )
    key = models.CharField(
        max_length=255,
        unique=True,
        blank=True,
        null=True,
        db_column="keystr",
    )
    value = models.TextField(
        blank=True,
        null=True,
        db_column="valstr",
    )

    objects = models.Manager()
    site = SitePreferenceManager()

    @classmethod
    def get_site_preferences(cls) -> SitePreferences:
        entries = dict(cls.site.values_list("key", "value"))
        return SitePreferences(
            station_name=entries.get("station_name") or "RASTATIME",
        )

    @classmethod
    def get_stream_preferences(cls) -> StreamPreferences:
        entries = dict(cls.site.values_list("key", "value"))
        return StreamPreferences(
            input_fade_transition=float(entries.get("default_transition_fade") or 0.0),
            message_format=MessageFormatKind(
                int(entries.get("stream_label_format") or 0)
            ),
            message_offline=entries.get("off_air_meta") or "Offline",
            replay_gain_enabled=entries.get("enable_replay_gain") == "1",
            replay_gain_offset=float(entries.get("replay_gain_modifier") or 0.0),
            loudness_mode=cls._loudness_mode(entries),
            loudness_target_lufs=cls._pref_float(entries, "loudness_target_lufs", -23.0),
            loudness_true_peak_dbtp=cls._pref_float(entries, "loudness_true_peak_dbtp", -1.0),
        )

    @staticmethod
    def _loudness_mode(entries: dict) -> str:
        """
        RASTATIME 2026-09-28 - ``loudness_mode`` in cc_pref; a database
        from before the setting existed derives it from the ReplayGain
        switch, so nothing changes for it.
        """
        raw = (entries.get("loudness_mode") or "").strip().lower()
        if raw in ("off", "replaygain", "r128"):
            return raw
        return "replaygain" if entries.get("enable_replay_gain") == "1" else "off"

    @staticmethod
    def _pref_float(entries: dict, key: str, default: float) -> float:
        try:
            raw = entries.get(key)
            return float(raw) if raw not in (None, "") else default
        except (TypeError, ValueError):
            return default

    @classmethod
    def get_stream_state(cls) -> StreamState:
        entries = dict(cls.site.values_list("key", "value"))
        return StreamState(
            input_main_connected=entries.get("master_dj") == "true",
            input_main_streaming=entries.get("master_dj_switch") == "on",
            input_show_connected=entries.get("live_dj") == "true",
            input_show_streaming=entries.get("live_dj_switch") == "on",
            schedule_streaming=entries.get("scheduled_play_switch") == "on",
        )

    class Meta:
        managed = False
        db_table = "cc_pref"
        unique_together = (("user", "key"),)
