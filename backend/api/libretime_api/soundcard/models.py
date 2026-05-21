"""
Django ORM model for soundcard settings persistence.

This module is the *persistence layer* only.  Business logic lives in the
pure domain model :class:`~audio.soundcard.settings_model.SoundcardSettings`.

Table: ``rastatime_soundcard_settings``
---------------------------------------
A singleton table — at most one row ever exists.  :meth:`get_settings`
enforces this with ``get_or_create(pk=1)``.

Columns
-------
id                : BigAutoField primary key (Django default; always 1)
main_output_id    : CharField — stable ID of the primary output device,
                    empty string if not yet selected.
preview_output_id : CharField — stable ID of the optional preview output,
                    empty string if not configured.
line_in_device_ids: JSONField — ordered list of stable IDs of configured
                    line-in input devices; default empty list.
updated_at        : DateTimeField — auto-set to now() on every save.

Relation to the domain model
-----------------------------
:meth:`to_domain` converts this ORM row to a
:class:`~audio.soundcard.settings_model.SoundcardSettings` instance.
:meth:`update_from_domain` applies a domain model instance back to this
row (call :meth:`save()` afterwards).

The conversion normalises empty strings to ``None`` (domain model uses
``None`` for "not configured") and vice versa.
"""

from __future__ import annotations

from django.db import models


class SoundcardSettings(models.Model):
    """
    Singleton persistence row for the operator's soundcard device selection.

    Use :meth:`get_settings` to load or initialise the singleton.
    """

    main_output_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text=(
            "Stable ID of the primary audio output device. "
            "Empty means 'use OS default'."
        ),
    )
    # RASTATIME 2026-05-14 — B.4 #4 (output side): friendly-name
    # fallback for when ``main_output_id`` no longer resolves after a
    # reboot (USB endpoint-GUID re-enumeration).  Same mechanism as
    # rastatime_linein.device_name.
    main_output_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=(
            "OS-reported friendly name of the main audio output endpoint "
            "at save time.  Used as a fallback when main_output_id no "
            "longer resolves (USB endpoint-GUID re-enumeration after reboot)."
        ),
    )
    preview_output_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text=(
            "Stable ID of the optional monitor / cue output. "
            "Empty means no preview output configured."
        ),
    )
    preview_output_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=(
            "OS-reported friendly name of the preview / monitor output "
            "endpoint at save time.  Used as a fallback when "
            "preview_output_id no longer resolves."
        ),
    )
    line_in_device_ids = models.JSONField(
        default=list,
        help_text="Ordered list of stable IDs of configured line-in input devices.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp of the last settings save.",
    )

    class Meta:
        managed = True
        db_table = "rastatime_soundcard_settings"
        verbose_name = "Soundcard Settings"
        verbose_name_plural = "Soundcard Settings"

    def __str__(self) -> str:
        out = self.main_output_id or "(none)"
        prev = self.preview_output_id or "(none)"
        return f"SoundcardSettings(main={out}, preview={prev})"

    # ------------------------------------------------------------------
    # Singleton accessor
    # ------------------------------------------------------------------

    @classmethod
    def get_settings(cls) -> "SoundcardSettings":
        """
        Return the single settings row, creating it with defaults if absent.

        The singleton is always stored at ``pk=1``.  Safe to call at any
        time — creates the row lazily on first access.
        """
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    # ------------------------------------------------------------------
    # Domain model bridge
    # ------------------------------------------------------------------

    def to_domain(self):
        """
        Convert this ORM row to the pure domain model.

        Returns
        -------
        audio.soundcard.settings_model.SoundcardSettings
            Immutable domain snapshot.  Empty strings are normalised to
            ``None``; the ``line_in_device_ids`` JSON list becomes a
            ``tuple``.
        """
        from audio.soundcard.settings_model import (   # lazy — audio on sys.path
            SoundcardSettings as DomainSettings,
        )
        return DomainSettings(
            main_output_id=self.main_output_id or None,
            preview_output_id=self.preview_output_id or None,
            line_in_device_ids=tuple(self.line_in_device_ids or []),
            main_output_name=self.main_output_name or "",
            preview_output_name=self.preview_output_name or "",
        )

    def update_from_domain(self, settings) -> None:
        """
        Apply a pure domain model instance to this ORM row.

        Does NOT call :meth:`save` — the caller controls when to persist.

        Parameters
        ----------
        settings:
            :class:`~audio.soundcard.settings_model.SoundcardSettings`
            instance whose values to apply.
        """
        self.main_output_id      = settings.main_output_id    or ""
        self.preview_output_id   = settings.preview_output_id or ""
        self.main_output_name    = settings.main_output_name    or ""
        self.preview_output_name = settings.preview_output_name or ""
        self.line_in_device_ids  = list(settings.line_in_device_ids)
