"""
T19.1 — Normalized playback event ORM model.

Persistence layer for :class:`~playout.now_playing.playback_event.PlaybackEvent`.

Table: ``rastatime_playback_event``
-------------------------------------
One row per playback occurrence.  All human-readable fields are denormalized
from the source item at the time of playback; the record remains readable
even if the original file or show is later deleted.

Columns
-------
id             : BigAutoField primary key (internal DB identity)
event_id       : CharField(36) unique — UUID string from the domain model
source_type    : CharField(16) — "file" | "webstream" | "linein" | "live" | "unknown"
item_id        : CharField(128) — QueueItem.id at the time of playback
title          : CharField(512) — denormalized track / stream title
artist         : CharField(512) — denormalized artist name
uri            : TextField — original URI (file path or stream URL; blank for linein)
started_at     : DateTimeField — UTC datetime when playback began
ended_at       : DateTimeField(null=True) — UTC datetime when playback ended
duration_played: FloatField(null=True) — seconds actually played (computed on write)
metadata       : JSONField — raw QueueItem.metadata dict
created_at     : DateTimeField — when this DB row was created

Relation to the domain model
-----------------------------
:meth:`to_domain` converts this ORM row to a
:class:`~playout.now_playing.playback_event.PlaybackEvent` instance.
:meth:`create_from_domain` creates and saves a new row from a domain instance.
"""

from __future__ import annotations

from django.db import models

# ---------------------------------------------------------------------------
# Source-type choices — mirrors PlaybackSourceType constants (no import dep)
# ---------------------------------------------------------------------------


class SourceType(models.TextChoices):
    FILE = "file", "Audio file"
    WEBSTREAM = "webstream", "Web stream"
    LINEIN = "linein", "Line-in source"
    LIVE = "live", "Live input"
    UNKNOWN = "unknown", "Unknown"


# ---------------------------------------------------------------------------
# ORM model
# ---------------------------------------------------------------------------


class PlaybackEvent(models.Model):
    """
    ORM persistence row for one playback event.
    """

    event_id = models.CharField(
        max_length=36,
        unique=True,
        db_index=True,
        help_text="UUID that uniquely identifies this playback event.",
    )
    source_type = models.CharField(
        max_length=16,
        choices=SourceType.choices,
        default=SourceType.UNKNOWN,
        help_text="Classification of the media source.",
    )
    item_id = models.CharField(
        max_length=128,
        help_text=(
            "QueueItem.id at the time of playback.  Stable within a session; "
            "not guaranteed to be globally unique across restarts."
        ),
    )
    title = models.CharField(
        max_length=512,
        blank=True,
        default="",
        help_text="Denormalized track or stream title.",
    )
    artist = models.CharField(
        max_length=512,
        blank=True,
        default="",
        help_text="Denormalized artist name.",
    )
    uri = models.TextField(
        blank=True,
        default="",
        help_text="Original URI of the media (file path or stream URL).",
    )
    started_at = models.DateTimeField(
        help_text="UTC datetime when playback of this item began.",
    )
    ended_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="UTC datetime when playback ended; NULL while still playing.",
    )
    duration_played = models.FloatField(
        null=True,
        blank=True,
        help_text="Seconds actually played.  NULL for in-progress events.",
    )
    metadata = models.JSONField(
        default=dict,
        help_text="Raw QueueItem.metadata dict at the time of playback.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when this row was first saved to the database.",
    )

    class Meta:
        managed = True
        db_table = "rastatime_playback_event"
        verbose_name = "Playback Event"
        verbose_name_plural = "Playback Events"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["started_at"], name="idx_playback_started_at"),
            models.Index(fields=["source_type"], name="idx_playback_source_type"),
        ]

    def __str__(self) -> str:
        status = "completed" if self.ended_at else "in progress"
        return (
            f"PlaybackEvent({self.source_type}, "
            f"{self.title!r}, "
            f"started={self.started_at.isoformat()}, "
            f"{status})"
        )

    # ------------------------------------------------------------------
    # Domain model bridge
    # ------------------------------------------------------------------

    def to_domain(self):
        """
        Convert this ORM row to the pure domain model.

        Returns
        -------
        playout.now_playing.playback_event.PlaybackEvent
            Immutable domain snapshot.
        """
        from playout.now_playing.playback_event import PlaybackEvent as DomainEvent  # lazy

        return DomainEvent(
            event_id=self.event_id,
            source_type=self.source_type,
            item_id=self.item_id,
            title=self.title,
            artist=self.artist,
            uri=self.uri,
            started_at=self.started_at,
            ended_at=self.ended_at,
            metadata=dict(self.metadata or {}),
        )

    @classmethod
    def create_from_domain(cls, event) -> PlaybackEvent:
        """
        Create and save a new ORM row from a domain
        :class:`~playout.now_playing.playback_event.PlaybackEvent`.

        Parameters
        ----------
        event:
            Domain ``PlaybackEvent`` instance to persist.

        Returns
        -------
        PlaybackEvent (ORM)
            The newly created and saved row.
        """
        obj = cls(
            event_id=event.event_id,
            source_type=event.source_type,
            item_id=event.item_id,
            title=event.title,
            artist=event.artist,
            uri=event.uri,
            started_at=event.started_at,
            ended_at=event.ended_at,
            duration_played=event.duration_played,
            metadata=dict(event.metadata),
        )
        obj.save()
        return obj
