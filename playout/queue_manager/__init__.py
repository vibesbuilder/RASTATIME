"""
playout.queue_manager — centralised queue-decision module.

Public API
----------
``ContentKind``
    Enum describing the logical source of current playout content
    (IDLE / SHOW / FALLBACK).

``QueueManager``
    Central arbiter that translates show-lifecycle events from the scheduler
    into engine commands, managing fallback lifecycle according to
    ``docs/architecture/QUEUE_BEHAVIOR.md``.

Typical usage (T8.3 wiring)
----------------------------
::

    from playout.engine_vlc import VlcPlayoutEngine
    from playout.queue_manager import QueueManager, ContentKind
    from playout.fallback import FallbackQueue
    from playout.engine_interface import QueueItem
    from playout.scheduler import StartMode

    engine = VlcPlayoutEngine(vlc_args=["--aout=dummy"])
    qm = QueueManager(engine)

    # Configure filler between shows
    qm.set_fallback(FallbackQueue(items=[QueueItem(id="filler", uri="...")]))

    # Called by PlayoutScheduler at show start_at:
    qm.start_show(items=[...], mode=StartMode.HARD)

    # Called by PlayoutScheduler at show end_at:
    qm.end_show()

    qm.active_content()     # ContentKind.FALLBACK (if fallback is configured)
    qm.fallback_is_active() # True
"""

from ._manager import ContentKind, QueueManager

__all__ = ["ContentKind", "QueueManager"]
