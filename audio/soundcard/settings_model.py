"""
SoundcardSettings — pure domain model for soundcard device selection.

This module is Django-free: it can be imported and tested without a database
or a running application server.  The Django persistence layer lives in
``backend/api/libretime_api/soundcard/models.py``, which converts between
this domain model and the ORM row via :meth:`to_domain` /
:meth:`update_from_domain`.

Design
------
``SoundcardSettings`` is an *immutable* frozen dataclass.  State changes
always produce a new instance via the ``with_*`` builder methods.  This
makes it safe to pass around without accidental mutation and trivial to
compare for equality.

Fields
------
main_output_id:
    Stable ID of the primary audio output device.  ``None`` means the
    operator has not yet made an explicit selection — the runtime should
    fall back to the OS default.
preview_output_id:
    Stable ID of the optional monitor / cue output (headphone mix for the
    DJ).  ``None`` means no preview output is configured.
line_in_device_ids:
    Ordered list of stable IDs of configured line-in input devices.
    An empty list means no line-ins are configured.
    Full Line-In entities (name, channel mapping, priority, enabled) are
    introduced in T14.1; this field serves as the lightweight placeholder.

Singleton persistence
---------------------
There is exactly one ``SoundcardSettings`` row in the database (singleton
table ``rastatime_soundcard_settings``).  The Django model's
``get_settings()`` class method enforces this.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class SoundcardSettings:
    """
    Immutable snapshot of the operator's soundcard device selection.

    Construct via the default constructor (all-None defaults) or via
    ``from_dict`` / the ``with_*`` builder methods.
    """

    main_output_id: Optional[str] = None
    """
    Stable ID of the primary audio output device (e.g. the main mix bus).
    ``None`` → fall back to OS default at runtime.
    """

    preview_output_id: Optional[str] = None
    """
    Stable ID of the optional monitor / headphone output.
    ``None`` → no preview output configured.
    """

    line_in_device_ids: tuple[str, ...] = field(default_factory=tuple)
    """
    Ordered tuple of stable IDs of configured line-in input devices.
    Empty tuple → no line-ins configured.
    """

    main_output_name: str = ""
    """
    RASTATIME 2026-05-14 — B.4 #4 UUID-Wechsel nach Reboot (output side).

    OS-reported friendly name of the main output endpoint at save time
    (e.g. ``"Lautsprecher (Realtek High Definition Audio)"``).  Used as
    a fallback when :attr:`main_output_id` no longer resolves to an
    active device — same Windows USB-audio quirk that affects line-in
    GUIDs.  Empty string for legacy rows without a stored name.
    """

    preview_output_name: str = ""
    """Friendly-name fallback for :attr:`preview_output_id`.  Same role
    as :attr:`main_output_name` but for the optional preview output.
    """

    # ------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------

    def is_output_configured(self) -> bool:
        """``True`` if a main output device has been explicitly selected."""
        return self.main_output_id is not None

    def has_preview_output(self) -> bool:
        """``True`` if a preview / monitor output has been configured."""
        return self.preview_output_id is not None

    def has_line_ins(self) -> bool:
        """``True`` if at least one line-in device is configured."""
        return bool(self.line_in_device_ids)

    # ------------------------------------------------------------------
    # Immutable builders
    # ------------------------------------------------------------------

    def with_main_output(self, stable_id: str) -> "SoundcardSettings":
        """Return a new instance with ``main_output_id`` set to *stable_id*."""
        return SoundcardSettings(
            main_output_id=stable_id,
            preview_output_id=self.preview_output_id,
            line_in_device_ids=self.line_in_device_ids,
            main_output_name=self.main_output_name,
            preview_output_name=self.preview_output_name,
        )

    def without_main_output(self) -> "SoundcardSettings":
        """Return a new instance with ``main_output_id`` cleared (set to ``None``)."""
        return SoundcardSettings(
            main_output_id=None,
            preview_output_id=self.preview_output_id,
            line_in_device_ids=self.line_in_device_ids,
            main_output_name=self.main_output_name,
            preview_output_name=self.preview_output_name,
        )

    def with_preview_output(self, stable_id: Optional[str]) -> "SoundcardSettings":
        """
        Return a new instance with ``preview_output_id`` set to *stable_id*.
        Pass ``None`` to clear the preview output.
        """
        return SoundcardSettings(
            main_output_id=self.main_output_id,
            preview_output_id=stable_id,
            line_in_device_ids=self.line_in_device_ids,
            main_output_name=self.main_output_name,
            preview_output_name=self.preview_output_name,
        )

    def with_line_in_added(self, stable_id: str) -> "SoundcardSettings":
        """
        Return a new instance with *stable_id* appended to
        ``line_in_device_ids``.  Idempotent: duplicate IDs are not added.
        """
        if stable_id in self.line_in_device_ids:
            return self
        return SoundcardSettings(
            main_output_id=self.main_output_id,
            preview_output_id=self.preview_output_id,
            line_in_device_ids=self.line_in_device_ids + (stable_id,),
            main_output_name=self.main_output_name,
            preview_output_name=self.preview_output_name,
        )

    def with_line_in_removed(self, stable_id: str) -> "SoundcardSettings":
        """
        Return a new instance with *stable_id* removed from
        ``line_in_device_ids``.  Silent no-op if *stable_id* was not present.
        """
        return SoundcardSettings(
            main_output_id=self.main_output_id,
            preview_output_id=self.preview_output_id,
            line_in_device_ids=tuple(
                i for i in self.line_in_device_ids if i != stable_id
            ),
            main_output_name=self.main_output_name,
            preview_output_name=self.preview_output_name,
        )

    def with_main_output_name(self, name: str) -> "SoundcardSettings":
        """Return a new instance with ``main_output_name`` replaced."""
        return SoundcardSettings(
            main_output_id=self.main_output_id,
            preview_output_id=self.preview_output_id,
            line_in_device_ids=self.line_in_device_ids,
            main_output_name=name,
            preview_output_name=self.preview_output_name,
        )

    def with_preview_output_name(self, name: str) -> "SoundcardSettings":
        """Return a new instance with ``preview_output_name`` replaced."""
        return SoundcardSettings(
            main_output_id=self.main_output_id,
            preview_output_id=self.preview_output_id,
            line_in_device_ids=self.line_in_device_ids,
            main_output_name=self.main_output_name,
            preview_output_name=name,
        )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """
        Convert to a JSON-serialisable dict.

        Returns
        -------
        dict
            Keys: ``main_output_id``, ``preview_output_id``,
            ``line_in_device_ids`` (as a plain list).
        """
        return {
            "main_output_id":      self.main_output_id,
            "preview_output_id":   self.preview_output_id,
            "line_in_device_ids":  list(self.line_in_device_ids),
            "main_output_name":    self.main_output_name,
            "preview_output_name": self.preview_output_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SoundcardSettings":
        """
        Reconstruct from a dict (e.g. from JSON or a Django model field).

        Missing keys fall back to defaults.  Extra keys are ignored.

        Parameters
        ----------
        data:
            Dict with optional keys ``main_output_id``,
            ``preview_output_id``, ``line_in_device_ids``.
        """
        return cls(
            main_output_id=data.get("main_output_id") or None,
            preview_output_id=data.get("preview_output_id") or None,
            line_in_device_ids=tuple(data.get("line_in_device_ids") or []),
            main_output_name=data.get("main_output_name") or "",
            preview_output_name=data.get("preview_output_name") or "",
        )
