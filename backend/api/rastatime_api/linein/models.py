"""
Django ORM model for Line-In source persistence.

This module is the *persistence layer* only.  Business logic and domain
validation live in the pure domain model
:class:`~audio.linein.domain.LineIn`.

Table: ``rastatime_linein``
----------------------------
Each row represents one configured local line-in input source.  Unlike
the soundcard settings singleton, there may be many line-in rows
(one per configured input).

Columns
-------
id            : BigAutoField primary key (internal DB identity)
linein_id     : CharField(36) unique — UUID string from the domain model
name          : CharField(128) — human-readable label (e.g. "Drum Kit")
device_id     : CharField(64) — stable ID of the AudioDevice input endpoint
channel_mapping : JSONField — list of 0-based int channel indices
enabled       : BooleanField — whether this line-in is active
description   : TextField — optional free-text description
priority      : IntegerField — routing priority (higher = wins)
input_gain_db : FloatField — static input gain in dB (-20..+20, default 0)
created_at    : DateTimeField — auto-set on first save
updated_at    : DateTimeField — auto-set on every save

Relation to the domain model
-----------------------------
:meth:`to_domain` converts this ORM row to a
:class:`~audio.linein.domain.LineIn` instance.
:meth:`update_from_domain` applies a domain model instance back to this
row; the caller must call :meth:`save()` afterwards.
:meth:`create_from_domain` is a classmethod that creates and saves a
new ORM row from a domain model instance.
"""

from __future__ import annotations

from django.db import models


class LineIn(models.Model):
    """
    ORM persistence row for one configured line-in input source.
    """

    linein_id = models.CharField(
        max_length=36,
        unique=True,
        db_index=True,
        help_text="UUID that uniquely identifies this line-in entity.",
    )
    name = models.CharField(
        max_length=128,
        help_text="Human-readable display name (e.g. 'Drum Kit', 'Interview Mic').",
    )
    device_id = models.CharField(
        max_length=64,
        help_text=(
            "Stable ID of the underlying Windows audio input endpoint. "
            "Matches AudioDevice.stable_id from the device manager."
        ),
    )
    # RASTATIME 2026-05-14 — B.4 #4: fallback identifier for when
    # ``device_id`` (WASAPI endpoint GUID) ceases to resolve after a
    # reboot.  Stored as the OS-reported friendly name at save time.
    device_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=(
            "OS-reported friendly name of the audio input endpoint at "
            "save time.  Used as a fallback when device_id no longer "
            "resolves (USB endpoint-GUID re-enumeration after reboot)."
        ),
    )
    channel_mapping = models.JSONField(
        default=list,
        help_text=(
            "0-based channel indices to capture (e.g. [0, 1] = stereo "
            "channels 1 & 2; [0] = mono channel 1)."
        ),
    )
    enabled = models.BooleanField(
        default=True,
        help_text="Whether this line-in is active and available for routing.",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Optional operator notes about this line-in source.",
    )
    priority = models.IntegerField(
        default=0,
        help_text=(
            "Routing priority.  Higher integer wins when multiple line-ins "
            "compete for the same playout slot."
        ),
    )
    # RASTATIME 2026-05-12 — Library-feature support.  When a line-in
    # is dragged into a show's content list, this is the default slot
    # length we reserve for it (same role as ``cc_webstream.length``).
    # 30 minutes mirrors the Webstream default in WebstreamController.
    length = models.DurationField(
        default=None,
        blank=True,
        null=True,
        help_text=(
            "Default duration when this line-in is added to a show. NULL falls back to 30 minutes."
        ),
    )
    # RASTATIME 2026-10-02 - per-line-in static input gain (dB), the
    # counterpart of cc_webstream.input_gain_db.  The playout applies it
    # on air as a linear amplify factor (var.set linein.gain).
    input_gain_db = models.FloatField(
        default=0.0,
        help_text=("Static input gain in dB applied on air (-20 to +20, 0 = unchanged)."),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when this line-in was first saved.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp of the last update.",
    )

    class Meta:
        managed = True
        db_table = "rastatime_linein"
        verbose_name = "Line-In Source"
        verbose_name_plural = "Line-In Sources"
        ordering = ["-priority", "name"]

    def __str__(self) -> str:
        state = "enabled" if self.enabled else "disabled"
        return f"LineIn({self.name!r}, device={self.device_id!r}, {state})"

    # ------------------------------------------------------------------
    # Domain model bridge
    # ------------------------------------------------------------------

    def to_domain(self):
        """
        Convert this ORM row to the pure domain model.

        Returns
        -------
        audio.linein.domain.LineIn
            Immutable domain snapshot.
        """
        from audio.linein.domain import LineIn as DomainLineIn  # lazy

        # ``length`` is a ``DurationField`` (timedelta); the domain
        # model carries an integer seconds value so the dict-serialised
        # form is JSON-clean.  NULL in DB → None in domain.
        length_seconds = int(self.length.total_seconds()) if self.length is not None else None
        return DomainLineIn(
            id=self.linein_id,
            name=self.name,
            device_id=self.device_id,
            device_name=self.device_name or "",
            channel_mapping=tuple(self.channel_mapping or []),
            enabled=self.enabled,
            description=self.description or "",
            priority=self.priority,
            length_seconds=length_seconds,
            input_gain_db=float(self.input_gain_db or 0.0),
        )

    def update_from_domain(self, linein) -> None:
        """
        Apply a pure domain model instance to this ORM row.

        Does NOT call :meth:`save` — the caller controls when to persist.

        Parameters
        ----------
        linein:
            :class:`~audio.linein.domain.LineIn` instance whose values
            to apply.
        """
        from datetime import timedelta  # lazy — keep module import surface small

        self.linein_id = linein.id
        self.name = linein.name
        self.device_id = linein.device_id
        self.device_name = linein.device_name
        self.channel_mapping = list(linein.channel_mapping)
        self.enabled = linein.enabled
        self.description = linein.description
        self.priority = linein.priority
        self.length = (
            timedelta(seconds=linein.length_seconds) if linein.length_seconds is not None else None
        )
        self.input_gain_db = linein.input_gain_db

    @classmethod
    def create_from_domain(cls, linein) -> LineIn:
        """
        Create and save a new ORM row from a domain :class:`~audio.linein.domain.LineIn`.

        Parameters
        ----------
        linein:
            :class:`~audio.linein.domain.LineIn` instance to persist.

        Returns
        -------
        LineIn (ORM)
            The newly created and saved row.
        """
        obj = cls()
        obj.update_from_domain(linein)
        obj.save()
        return obj
