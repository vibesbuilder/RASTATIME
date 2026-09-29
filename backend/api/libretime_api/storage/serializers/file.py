from rest_framework import serializers

from ..models import File


class FileSerializer(serializers.ModelSerializer):
    # RASTATIME 2026-09-29 - the crossfade of the file's track type
    # (cc_track_types.crossfade_duration); null = house value.  Read-only,
    # so the playout gets it with the file instead of a second request.
    track_type_crossfade = serializers.DecimalField(
        source="library.crossfade_duration",
        max_digits=5, decimal_places=2,
        read_only=True, allow_null=True, default=None,
    )

    class Meta:
        model = File
        fields = "__all__"
