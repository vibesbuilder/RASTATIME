from datetime import timedelta

from django.db import models
from django.utils.timezone import now


class Schedule(models.Model):
    starts_at = models.DateTimeField(db_column="starts")
    ends_at = models.DateTimeField(db_column="ends")

    instance = models.ForeignKey(
        "schedule.ShowInstance",
        on_delete=models.DO_NOTHING,
    )

    file = models.ForeignKey(
        "storage.File",
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
    )
    stream = models.ForeignKey(
        "schedule.Webstream",
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
    )
    # RASTATIME 2026-05-12 — Line-In Library item.  A schedule row
    # carries at most one of (file, stream, linein); the playout
    # picks the right Event subclass based on which FK is set.
    linein = models.ForeignKey(
        "linein.LineIn",
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        db_column="linein_id",
    )

    length = models.DurationField(blank=True, null=True, db_column="clip_length")
    fade_in = models.TimeField(blank=True, null=True)
    fade_out = models.TimeField(blank=True, null=True)
    cue_in = models.DurationField()
    cue_out = models.DurationField()

    class PositionStatus(models.IntegerChoices):
        FILLER = -1, "Filler"  # Used to fill a show that already started
        OUTSIDE = 0, "Outside"  # Is outside the show time frame
        INSIDE = 1, "Inside"  # Is inside the show time frame
        BOUNDARY = 2, "Boundary"  # Is at the boundary of the show time frame

    position = models.IntegerField()
    position_status = models.SmallIntegerField(
        choices=PositionStatus.choices,
        default=PositionStatus.INSIDE,
        db_column="playout_status",
    )

    # Broadcasted is set to 1 when a live source is not
    # on. Used for the playout history.
    broadcasted = models.SmallIntegerField()
    played = models.BooleanField(
        blank=True,
        null=True,
        db_column="media_item_played",
    )

    @property
    def overbooked(self) -> bool:
        """
        A schedule item is overbooked if it starts after the end of the show
        instance it is in.

        Related to self.position_status
        """
        return self.starts_at >= self.instance.ends_at

    def get_owner(self):
        return self.instance.get_owner()

    def get_cue_out(self):
        """
        Returns a scheduled item cue out that is based on the current show
        instance.

        Cue out of a specific item can potentially overrun the show that it is
        scheduled in. In that case, the cue out should be the end of the show.
        This prevents the next show having overlapping items playing.

        Cases:
        - When the schedule ends before the end of the show instance,
        return the stored cue out.

        - When the schedule starts before the end of the show instance
        and ends after the show instance ends,
        return the cue in plus the timedelta between schedule starts and
        show instance ends.

        - When the schedule starts after the end of the show instance,
        return the stored cue_out even if the schedule WILL NOT BE PLAYED.

        RASTATIME 2026-11-13 - the cue out is a position in the file, the
        audio starts at the cue in: upstream returned the time to the show
        end alone, so every overbooked row ended its cue in early (0.03 s
        before the 17:15 boundary on 2026-11-07); the Auto DJ buffer track
        (§23.107) always overbooks.
        """
        if self.starts_at < self.instance.ends_at and self.instance.ends_at < self.ends_at:
            return (self.cue_in or timedelta(0)) + (self.instance.ends_at - self.starts_at)
        return self.cue_out

    def get_ends_at(self):
        """
        Returns a scheduled item ends that is based on the current show
        instance.

        End of a specific item can potentially overrun the show that it is
        scheduled in. In that case, the end should be the end of the show.
        This prevents the next show having overlapping items playing.

        Cases:
        - When the schedule ends before the end of the show instance,
        return the scheduled item ends.

        - When the schedule starts before the end of the show instance
        and ends after the show instance ends,
        return the show instance ends.

        - When the schedule starts after the end of the show instance,
        return the show instance ends.
        """
        if self.instance.ends_at < self.ends_at:
            return self.instance.ends_at
        return self.ends_at

    @staticmethod
    def is_file_scheduled_in_the_future(file_id):
        count = Schedule.objects.filter(
            file_id=file_id,
            ends_at__gt=now(),
        ).count()
        return count > 0

    class Meta:
        managed = False
        db_table = "cc_schedule"
        permissions = [
            ("change_own_schedule", "Change the content on their shows"),
            ("delete_own_schedule", "Delete the content on their shows"),
        ]
