"""
T15.1 — Process-level LineInRuntime singleton.

Mirrors the pattern of :mod:`audio.soundcard._registry`:
a module-level ``default_runtime`` variable that is ``None`` until
:func:`connect_runtime` is called at application startup.

Usage (production)
------------------
At application startup, after the runtime is constructed, call::

    from audio.linein import connect_runtime
    from audio.linein._runtime import WindowsLineInRuntime   # future T15.2

    connect_runtime(WindowsLineInRuntime())

The activation layer then reads the singleton via::

    import audio.linein._registry as _reg
    runtime = _reg.default_runtime   # None until connected

Usage (tests)
-------------
Inject a stub runtime via the module attribute::

    import audio.linein._registry as _reg
    from audio.linein._runtime import StubLineInRuntime

    _reg.default_runtime = StubLineInRuntime()
    # ... test ...
    _reg.default_runtime = None   # restore in teardown

Always restore ``None`` in teardown to avoid cross-test contamination.

Multi-process note
------------------
When the playout engine and the API server run as separate OS processes
the singleton stays ``None`` in the API process.  A future task may add a
shared IPC transport.  For a single-process dev server, :func:`connect_runtime`
is sufficient.
"""

from __future__ import annotations

from typing import Optional

from ._runtime import LineInRuntime


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

default_runtime: Optional[LineInRuntime] = None
"""
The process-level :class:`~audio.linein._runtime.LineInRuntime` instance.

``None`` until :func:`connect_runtime` is called.
Do **not** import this name directly — always access it as a module attribute
so that late binding works correctly::

    import audio.linein._registry as _reg
    runtime = _reg.default_runtime   # reads the current live value
"""


def connect_runtime(runtime: LineInRuntime) -> None:
    """
    Set the process-level Line-In runtime singleton.

    Replaces any previously registered runtime.  Safe to call multiple
    times (e.g. during testing or service restart).

    Parameters
    ----------
    runtime:
        A concrete :class:`~audio.linein._runtime.LineInRuntime`
        implementation (e.g. ``StubLineInRuntime`` in tests, or a
        ``WindowsLineInRuntime`` in production).
    """
    global default_runtime
    default_runtime = runtime
