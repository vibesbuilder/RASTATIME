"""
streams.egress._registry — process-level egress manager singleton.

Provides the same singleton pattern as ``playout.now_playing``:
a module-level ``default_manager`` variable that is ``None`` until
:func:`connect_egress_manager` is called.

Usage (production)
------------------
At application startup, after the playout engine and egress manager are
constructed, call::

    from streams.egress import connect_egress_manager
    connect_egress_manager(my_libvlc_egress_manager)

The Django view at ``/api/v2/streams/outputs`` then reads live status from
that manager via ``streams.egress._registry.default_manager``.

Usage (tests)
-------------
Inject a mock manager via the module attribute::

    import streams.egress._registry as _reg
    _reg.default_manager = _MockManager()

Always restore ``None`` in teardown to avoid test cross-contamination.

Multi-process note
------------------
When the playout engine and the API server run as separate OS processes, the
singleton stays ``None`` in the API process.  A future task will add a
Redis/DB-backed transport.
"""

from __future__ import annotations

from typing import Optional

from .interface import StreamEgressManager


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

default_manager: Optional[StreamEgressManager] = None
"""
The process-level :class:`~streams.egress.interface.StreamEgressManager`.

``None`` until :func:`connect_egress_manager` is called.
Do NOT import this name directly — access it as a module attribute::

    import streams.egress._registry as _reg
    mgr = _reg.default_manager   # always reads current value
"""


def connect_egress_manager(mgr: StreamEgressManager) -> None:
    """
    Set the process-level egress manager singleton.

    Replaces any previously registered manager.  Safe to call multiple
    times (e.g. during testing or after a service restart).

    Parameters
    ----------
    mgr:
        A concrete :class:`~streams.egress.interface.StreamEgressManager`
        implementation.
    """
    global default_manager
    default_manager = mgr
