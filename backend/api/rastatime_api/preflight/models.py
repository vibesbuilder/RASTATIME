"""
Django ORM model for RASTATIME pre-flight warnings.

Table: ``rastatime_preflight_warning``
---------------------------------------
The pre-flight checker (running inside the playout service) scans the
schedule for the next 48 hours every 15 minutes and writes any problems
it finds into this table.  The legacy PHP frontend reads it to render
the red warning banner on the dashboard.

The table is intentionally generic — the first warning type emitted is
``linein_device_unavailable`` (B.4 #2), but the schema accommodates
later additions like ``smart_block_empty``, ``file_missing_in_storage``,
``master_password_default`` etc. without further migrations.

Atomic refresh
--------------
Each scan run gets a unique ``scan_run_id`` (UUID-string).  The
``replace_warnings`` classmethod deletes all previously-stored warnings
of the given ``warning_type`` and inserts the new batch in a single
transaction — so the frontend never sees a half-updated state where
some old and some new warnings coexist.

Why integer FKs without ON DELETE CASCADE on ``show_id`` /
``show_instance_id``: the upstream ``cc_show`` / ``cc_show_instances``
tables are still managed by the legacy Propel migration system and
mixing Django-managed FKs with Propel-managed parents leads to
``managed = False`` headaches.  Stale rows are cleaned up implicitly by
the next scan (which only emits warnings for shows still in the
schedule).
"""

from __future__ import annotations

from collections.abc import Iterable

from django.db import models, transaction


class PreflightWarning(models.Model):
    """
    One pre-flight warning row.  See module docstring for the broader
    contract; this docstring covers per-column meaning.
    """

    class Severity(models.TextChoices):
        WARNING = "warning", "Warning"  # operator should look, show may still run
        ERROR = "error", "Error"  # show will definitely fail / be silent

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this warning was inserted by the scanner.",
    )
    scan_run_id = models.CharField(
        max_length=36,
        db_index=True,
        help_text=(
            "UUID of the scanner run that produced this row.  All rows "
            "of the same warning_type written by one scan share this id, "
            "so the frontend can detect inconsistent reads if needed."
        ),
    )
    warning_type = models.CharField(
        max_length=64,
        db_index=True,
        help_text=(
            "Machine-readable warning category, e.g. "
            "'linein_device_unavailable'.  Used by the frontend to pick "
            "an icon/severity label and by the scanner to atomically "
            "replace warnings of one type without touching the others."
        ),
    )
    severity = models.CharField(
        max_length=16,
        choices=Severity.choices,
        default=Severity.WARNING,
        help_text="Operator-visible severity. Drives the banner colour.",
    )
    show_id = models.IntegerField(
        blank=True,
        null=True,
        db_index=True,
        help_text=(
            "Related cc_show.id, if the warning concerns a specific show. "
            "NOT enforced as FK because cc_show is Propel-managed."
        ),
    )
    show_instance_id = models.IntegerField(
        blank=True,
        null=True,
        db_index=True,
        help_text=(
            "Related cc_show_instances.id, if the warning concerns a "
            "specific instance. NOT enforced as FK (see show_id note)."
        ),
    )
    starts_at = models.DateTimeField(
        blank=True,
        null=True,
        db_index=True,
        help_text=(
            "Denormalised show-instance start time, kept here so the "
            "frontend can sort/filter warnings by time without joining "
            "to cc_show_instances."
        ),
    )
    detail = models.JSONField(
        default=dict,
        help_text=(
            "Warning-type-specific payload — e.g. for "
            "'linein_device_unavailable': "
            "{'linein_id': 2, 'linein_name': 'Jabra-Mikro', "
            " 'device_id': '0fb...', 'show_name': 'Morgensendung'}."
        ),
    )

    class Meta:
        managed = True
        db_table = "rastatime_preflight_warning"
        verbose_name = "Pre-flight Warning"
        verbose_name_plural = "Pre-flight Warnings"
        ordering = ["starts_at", "id"]
        indexes = [
            models.Index(
                fields=["warning_type", "starts_at"],
                name="idx_preflight_type_starts",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"PreflightWarning({self.warning_type}, "
            f"severity={self.severity}, show_id={self.show_id})"
        )

    # ------------------------------------------------------------------
    # Atomic replace helper
    # ------------------------------------------------------------------

    @classmethod
    @transaction.atomic
    def replace_warnings(
        cls,
        warning_type: str,
        scan_run_id: str,
        warnings: Iterable[dict],
    ) -> int:
        """
        Atomically replace all rows of ``warning_type`` with ``warnings``.

        Used by the playout pre-flight scanner: it computes the current
        set of warnings, then calls this once per warning_type with the
        new batch.  The transaction guarantees no half-updated state is
        ever visible to readers.

        Parameters
        ----------
        warning_type :
            Discriminator — only rows with this exact value are touched.
        scan_run_id :
            UUID-string identifying this scan run.
        warnings :
            Iterable of dicts with keys matching this model's fields
            (severity, show_id, show_instance_id, starts_at, detail).
            ``warning_type`` and ``scan_run_id`` are filled in
            automatically — callers should NOT include them.

        Returns
        -------
        int
            Number of rows inserted.
        """
        cls.objects.filter(warning_type=warning_type).delete()
        new_rows = [
            cls(
                warning_type=warning_type,
                scan_run_id=scan_run_id,
                severity=w.get("severity", cls.Severity.WARNING),
                show_id=w.get("show_id"),
                show_instance_id=w.get("show_instance_id"),
                starts_at=w.get("starts_at"),
                detail=w.get("detail", {}),
            )
            for w in warnings
        ]
        if new_rows:
            cls.objects.bulk_create(new_rows)
        return len(new_rows)
