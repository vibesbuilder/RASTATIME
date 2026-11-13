from rest_framework import serializers

from ..models import File
from ..track_type_gain import fixed_gain_for


class FileSerializer(serializers.ModelSerializer):
    # RASTATIME 2026-09-29 - the crossfade of the file's track type
    # (cc_track_types.crossfade_duration); null = house value.  Read-only,
    # so the playout gets it with the file instead of a second request.
    track_type_crossfade = serializers.DecimalField(
        source="library.crossfade_duration",
        max_digits=5,
        decimal_places=2,
        read_only=True,
        allow_null=True,
        default=None,
    )
    # RASTATIME 2026-09-30 - the type's "No Fade during Crossover" preset;
    # the playout resolves the effective flag (file field wins).
    track_type_no_fade = serializers.BooleanField(
        source="library.no_fade_crossfade",
        read_only=True,
        default=False,
    )
    # RASTATIME 2026-10-14 - the type's stream-metadata preset; the playout
    # resolves the effective flag (the file's icy_forward wins).
    track_type_icy_forward = serializers.BooleanField(
        source="library.icy_forward",
        read_only=True,
        default=True,
    )
    # RASTATIME 2026-11-13 - a track type with the loudness analysis off
    # plays its tracks with a fixed gain (dB) instead of the measured
    # adjustment; null for every other type (and before migration 0083).
    track_type_fixed_gain_db = serializers.SerializerMethodField()

    def get_track_type_fixed_gain_db(self, obj):
        return fixed_gain_for(getattr(obj, "library_id", None))

    class Meta:
        model = File
        fields = "__all__"
