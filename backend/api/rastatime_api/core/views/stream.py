from rest_framework import views
from rest_framework.response import Response

from ...permissions import IsSystemTokenOrUser
from ..models import Preference
from ..serializers import StreamPreferencesSerializer, StreamStateSerializer


class StreamPreferencesView(views.APIView):
    permission_classes = [IsSystemTokenOrUser]
    serializer_class = StreamPreferencesSerializer
    model_permission_name = "streamsetting"

    def get(self, request):
        data = Preference.get_stream_preferences()
        return Response(
            data.model_dump(
                include={
                    "input_fade_transition",
                    "message_format",
                    "message_offline",
                    "replay_gain_enabled",
                    "replay_gain_offset",
                    "loudness_mode",
                    "loudness_target_lufs",
                    "loudness_true_peak_dbtp",
                }
            )
        )


class StreamStateView(views.APIView):
    permission_classes = [IsSystemTokenOrUser]
    serializer_class = StreamStateSerializer
    model_permission_name = "streamsetting"

    def get(self, request):
        data = Preference.get_stream_state()
        return Response(
            data.model_dump(
                include={
                    "input_main_connected",
                    "input_main_streaming",
                    "input_show_connected",
                    "input_show_streaming",
                    "schedule_streaming",
                }
            )
        )


class LocalRecordingFolderView(views.APIView):
    """
    RASTATIME 2026-05-17 — Read-only endpoint that returns the
    operator-configured Local Recording Folder (cc_pref key
    ``local_recording_folder``).  Consumed by the playout's
    PlayoutScheduler when a SHOW_RECORD_START event fires.

    Returns ``{"folder": "<path>", "format": "mp3", "bitrate": 320}`` —
    an empty folder if the operator has not yet configured one (recording
    will be skipped at show-start with a warning in the playout log).
    Format and bitrate (RASTATIME 2026-10-18, Settings -> Local Machine ->
    Show Recording) are informational here: the playout names the file
    after the encoder it rendered, not after the setting of the moment.
    """

    permission_classes = [IsSystemTokenOrUser]

    def get(self, request):
        entries = dict(
            Preference.site.filter(
                key__in=[
                    "local_recording_folder",
                    "local_recording_format",
                    "local_recording_bitrate",
                ]
            ).values_list("key", "value")
        )
        folder = (entries.get("local_recording_folder") or "").strip()
        fmt = (entries.get("local_recording_format") or "").strip().lower()
        if fmt not in ("mp3", "aac", "ogg", "opus"):
            fmt = "mp3"
        try:
            bitrate = int(entries.get("local_recording_bitrate") or 0)
        except (TypeError, ValueError):
            bitrate = 0
        if bitrate <= 0:
            bitrate = 320
        return Response({"folder": folder, "format": fmt, "bitrate": bitrate})
