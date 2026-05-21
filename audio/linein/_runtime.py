"""
T15.1 — Line-In runtime activation contract.

Defines the abstract interface that every Line-In runtime engine must
implement, plus a lightweight in-memory stub for use in tests and
environments that have no physical audio hardware.

Design notes
------------
* **Never raises on expected failures** — ``activate()`` returns an
  :class:`ActivationResult` with ``success=False`` rather than raising, so
  callers can handle degraded hardware without try/except chains.
* **Lifecycle is imperative** — :meth:`LineInRuntime.activate` opens the
  audio device; :meth:`~LineInRuntime.deactivate` closes it.  Calling
  ``deactivate`` for an unknown ID is a safe no-op.
* **No Django dependency** — this module is importable in the root venv and
  in unit tests without a running application server.
* **Registry** lives in :mod:`audio.linein._registry` (the same pattern as
  :mod:`audio.soundcard._registry`) so the singleton is not baked into
  this file and can be replaced by tests via module-attribute injection.

Typical call site (service startup)::

    from audio.linein._runtime import StubLineInRuntime   # or a real impl
    from audio.linein import connect_runtime

    runtime = StubLineInRuntime()   # replace with WindowsLineInRuntime()
    connect_runtime(runtime)

    for linein in enabled_lineins:
        result = runtime.activate(linein)
        if not result.success:
            logger.warning("Could not activate %s: %s",
                           linein.name, result.error_message)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from .domain import LineIn


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ActivationResult:
    """
    Outcome of a single :meth:`LineInRuntime.activate` call.

    Attributes
    ----------
    linein_id:
        Domain UUID of the :class:`~audio.linein.domain.LineIn` whose
        activation was attempted.
    success:
        ``True`` when the device was opened successfully and audio capture
        has started (or will start imminently).
    error_message:
        Human-readable explanation of why activation failed.  ``None``
        when ``success`` is ``True``.
    """

    linein_id:     str
    success:       bool
    error_message: Optional[str] = None

    @property
    def failed(self) -> bool:
        """``True`` when activation did **not** succeed (inverse of ``success``)."""
        return not self.success


# ---------------------------------------------------------------------------
# Abstract contract
# ---------------------------------------------------------------------------

class LineInRuntime(ABC):
    """
    Abstract contract for a Line-In runtime engine.

    A concrete implementation opens the physical audio input device,
    maps the requested channels, and manages the audio capture lifecycle.
    The stub implementation :class:`StubLineInRuntime` is provided for
    testing.

    All methods must be safe to call from any thread; the implementation
    is responsible for its own thread-safety.
    """

    @abstractmethod
    def activate(self, linein: LineIn) -> ActivationResult:
        """
        Start capturing audio from *linein*.

        If the device is already active, the implementation may either
        return a success result immediately (idempotent) or restart the
        stream — callers must not rely on either behaviour.

        Parameters
        ----------
        linein:
            Domain model describing the source to activate.  The
            implementation uses :attr:`~.domain.LineIn.device_id` to
            identify the physical device and
            :attr:`~.domain.LineIn.channel_mapping` to select channels.

        Returns
        -------
        ActivationResult
            ``success=True`` when audio capture is running.
            ``success=False`` with an ``error_message`` on failure
            (e.g. device not plugged in, exclusive-mode conflict).
        """

    @abstractmethod
    def deactivate(self, linein_id: str) -> None:
        """
        Stop capturing audio for the line-in identified by *linein_id*.

        Silently ignored if no source with that ID is currently active.

        Parameters
        ----------
        linein_id:
            Domain UUID of the :class:`~.domain.LineIn` to deactivate.
        """

    @abstractmethod
    def active_ids(self) -> frozenset[str]:
        """
        Return the set of domain UUIDs that are currently active.

        Returns
        -------
        frozenset[str]
            Snapshot of the active ID set at the time of the call.
            May be empty if no sources are running.
        """

    # ------------------------------------------------------------------
    # Concrete helper — implemented in terms of the abstract primitives
    # ------------------------------------------------------------------

    def is_active(self, linein_id: str) -> bool:
        """
        Return ``True`` if the given line-in is currently active.

        Default implementation delegates to :meth:`active_ids`; concrete
        subclasses may override with a more efficient check.

        Parameters
        ----------
        linein_id:
            Domain UUID to query.
        """
        return linein_id in self.active_ids()


# ---------------------------------------------------------------------------
# Stub implementation (for tests and dev environments)
# ---------------------------------------------------------------------------

class StubLineInRuntime(LineInRuntime):
    """
    Pure in-memory Line-In runtime stub.

    No physical audio device is opened.  Activations are recorded in an
    internal dict and can be queried synchronously — no background threads
    are started.

    A test can call :meth:`set_fail` to force ``activate()`` to return a
    failure result for a specific domain UUID, simulating a device error.

    Usage::

        runtime = StubLineInRuntime()
        runtime.set_fail("bad-device-uuid")

        ok  = runtime.activate(good_linein)   # ActivationResult(success=True)
        bad = runtime.activate(bad_linein)    # ActivationResult(success=False)
        assert runtime.is_active(good_linein.id)
        assert not runtime.is_active(bad_linein.id)
    """

    def __init__(self) -> None:
        # Map of linein_id → LineIn for currently active sources.
        self._active: dict[str, LineIn] = {}
        # Set of linein_ids that should fail activation.
        self._fail_ids: set[str] = set()

    # ------------------------------------------------------------------
    # Test control
    # ------------------------------------------------------------------

    def set_fail(self, linein_id: str) -> None:
        """
        Configure this stub so that activating *linein_id* always fails.

        Useful for simulating a missing or faulted device without any real
        hardware interaction.

        Parameters
        ----------
        linein_id:
            Domain UUID that should return ``success=False`` from
            :meth:`activate`.
        """
        self._fail_ids.add(linein_id)

    def clear_fail(self, linein_id: str) -> None:
        """
        Remove a previously set failure override for *linein_id*.

        Parameters
        ----------
        linein_id:
            Domain UUID to stop failing.
        """
        self._fail_ids.discard(linein_id)

    # ------------------------------------------------------------------
    # LineInRuntime implementation
    # ------------------------------------------------------------------

    def activate(self, linein: LineIn) -> ActivationResult:
        """
        Record *linein* as active unless it has been configured to fail.

        Returns
        -------
        ActivationResult
            ``success=True`` when not configured to fail;
            ``success=False`` with an explanatory message otherwise.
        """
        if linein.id in self._fail_ids:
            return ActivationResult(
                linein_id=linein.id,
                success=False,
                error_message=(
                    f"StubLineInRuntime: activation of '{linein.id}' "
                    f"(name={linein.name!r}) is configured to fail."
                ),
            )
        self._active[linein.id] = linein
        return ActivationResult(linein_id=linein.id, success=True)

    def deactivate(self, linein_id: str) -> None:
        """
        Remove *linein_id* from the active set.  No-op if not active.
        """
        self._active.pop(linein_id, None)

    def active_ids(self) -> frozenset[str]:
        """Return a snapshot of currently active line-in IDs."""
        return frozenset(self._active)
