"""
Django ORM model for listener song requests.

RASTATIME 2026-06-07 — Song Requests, Phase 1 (data foundation).

Table: ``rastatime_song_request``
---------------------------------
One row per listener song request.  A request points at a library
track (``file_id`` -> ``cc_files.id``) and carries a lifecycle status.

There is intentionally NO database foreign-key constraint to the
Propel-managed ``cc_files`` table — the same cross-system FK policy as
``rastatime_linein`` / ``cc_schedule.linein_id`` (see legacy migration
0054): mixing FK ownership across the Django-managed and Propel-managed
schemas causes drop-order problems on schema reset.  Orphaned requests
(track deleted after the request was made) are skipped by the consuming
code and swept by the expiry task (Phase 6).

Aggregate cache on cc_files
---------------------------
For fast smart-block filtering/sorting the per-track aggregate
(``requested`` / ``requested_at`` / ``request_count``) lives as columns
on ``cc_files`` (legacy migration 0055), NOT here.  This table is the
authoritative per-request audit log; the cc_files columns are a
denormalised cache derived from it.

Lifecycle (status)
------------------
pending  -> just submitted via the public intake (Phase 3), not yet
            pulled into a show.
queued   -> picked up by the in-show incremental fill (Phase 5) and
            written into cc_schedule.
played   -> the track aired; set by the playout reset hook (Phase 6),
            which also clears the cc_files aggregate.
expired  -> never aired within the expiry window; set by the expiry
            task (Phase 6).
"""

from __future__ import annotations

from django.db import models


class SongRequest(models.Model):
    """One listener song request and its lifecycle status."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        QUEUED = "queued", "Queued"
        PLAYED = "played", "Played"
        EXPIRED = "expired", "Expired"

    file_id = models.IntegerField(
        db_index=True,
        help_text=(
            "cc_files.id of the requested track.  No cross-system FK "
            "constraint by design (see migration 0054 rationale)."
        ),
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        help_text="Lifecycle state of this request.",
    )
    listener_label = models.CharField(
        max_length=128,
        blank=True,
        default="",
        help_text=(
            "Optional free-text name or dedication supplied by the "
            "listener.  Anonymous requests leave this empty."
        ),
    )
    ip_hash = models.CharField(
        max_length=64,
        blank=True,
        default="",
        db_index=True,
        help_text=(
            "Salted hash of the requester's IP address — used only for "
            "rate-limiting and de-duplication.  The raw IP is never "
            "stored (privacy)."
        ),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Timestamp when the request was submitted.",
    )
    played_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=("Timestamp when the requested track actually aired (NULL until played)."),
    )

    class Meta:
        managed = True
        db_table = "rastatime_song_request"
        verbose_name = "Song Request"
        verbose_name_plural = "Song Requests"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"SongRequest(file_id={self.file_id}, status={self.status!r})"
