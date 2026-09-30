from django.db import models


class Library(models.Model):
    name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_column="type_name",
    )
    code = models.CharField(max_length=16, unique=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    enabled = models.BooleanField(
        blank=True,
        default=True,
        db_column="visibility",
    )

    analyze_cue_points = models.BooleanField(
        blank=True,
        default=True,
        db_column="analyze_cue_points",
    )

    # RASTATIME 2026-09-29 - crossfade per track type (legacy migration
    # 0062): seconds two neighbouring tracks overlap; NULL = house value.
    crossfade_duration = models.DecimalField(
        max_digits=5, decimal_places=2, blank=True, null=True,
    )
    # RASTATIME 2026-09-30 - "No Fade during Crossover" as the type's preset
    # (legacy migration 0063): tracks set to "As the track type" keep their
    # level while a neighbour fades.
    no_fade_crossfade = models.BooleanField(default=False)

    class Meta:
        managed = False
        db_table = "cc_track_types"
