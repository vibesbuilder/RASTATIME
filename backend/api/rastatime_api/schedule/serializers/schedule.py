from rest_framework import serializers

from ..buffer import buffer_fade_out, load_buffer_settings
from ..models import Schedule


class ReadScheduleSerializer(serializers.ModelSerializer):
    cue_out = serializers.DurationField(source="get_cue_out", read_only=True)
    ends_at = serializers.DateTimeField(source="get_ends_at", read_only=True)
    # RASTATIME 2026-11-13 - Auto DJ buffer track (§23.107): seconds the
    # playout fades this row out at the show end, null = the house show
    # crossfade (every other row, and the buffer track set to "Cut")
    buffer_fade_out = serializers.SerializerMethodField()

    class Meta:
        model = Schedule
        fields = "__all__"

    def get_buffer_fade_out(self, obj):
        # the settings are read once per request (the context dict is
        # shared by every row of a list)
        context = self.context
        settings = context.get("_rt_buffer_settings")
        if settings is None:
            settings = load_buffer_settings()
            context["_rt_buffer_settings"] = settings
        return buffer_fade_out(obj, settings)


class WriteScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Schedule
        fields = "__all__"
