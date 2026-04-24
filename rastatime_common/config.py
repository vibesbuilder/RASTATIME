"""
RASTATIME runtime configuration.

Engine selection
----------------
Set the environment variable ``RASTATIME_PLAYOUT_ENGINE`` to choose the
playout backend.  Accepted values (case-insensitive):

    mock    — in-process stub, no audio output (default, always available)
    libvlc  — libVLC-backed real audio output (requires python-vlc + libvlc)

Example::

    # Windows PowerShell
    $env:RASTATIME_PLAYOUT_ENGINE = "libvlc"

    # Python
    import os; os.environ["RASTATIME_PLAYOUT_ENGINE"] = "mock"
"""

import os
from enum import Enum
from typing import Optional

from playout.engine_interface import PlayoutEngine


class PlayoutEngineKind(str, Enum):
    """Supported playout backends."""

    MOCK = "mock"
    LIBVLC = "libvlc"


def get_playout_engine_kind() -> PlayoutEngineKind:
    """
    Read ``RASTATIME_PLAYOUT_ENGINE`` from the environment and return the
    corresponding :class:`PlayoutEngineKind`.

    Raises
    ------
    ValueError
        If the environment variable contains an unrecognised value.
    """
    raw = os.environ.get("RASTATIME_PLAYOUT_ENGINE", PlayoutEngineKind.MOCK.value)
    raw = raw.strip().lower()
    try:
        return PlayoutEngineKind(raw)
    except ValueError:
        valid = ", ".join(k.value for k in PlayoutEngineKind)
        raise ValueError(
            f"Invalid RASTATIME_PLAYOUT_ENGINE={raw!r}. "
            f"Valid values: {valid}"
        ) from None


def create_playout_engine(
    kind: Optional[PlayoutEngineKind] = None,
    **kwargs,
) -> PlayoutEngine:
    """
    Instantiate and return a :class:`~playout.engine_interface.PlayoutEngine`.

    Parameters
    ----------
    kind:
        Which engine to create.  If *None* (default) the value is read from
        the environment via :func:`get_playout_engine_kind`.
    **kwargs:
        Forwarded to the engine constructor.  For ``mock``, the useful kwarg
        is ``default_track_duration`` (float, seconds).

    Raises
    ------
    ValueError
        If the environment variable contains an unrecognised value.
    ImportError
        If ``libvlc`` is requested but ``playout.engine_vlc`` is not
        available (python-vlc or libVLC not installed).
    """
    if kind is None:
        kind = get_playout_engine_kind()

    if kind is PlayoutEngineKind.MOCK:
        from playout.engine_mock import MockPlayoutEngine

        return MockPlayoutEngine(**kwargs)

    if kind is PlayoutEngineKind.LIBVLC:
        try:
            from playout.engine_vlc import VlcPlayoutEngine  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "libvlc engine requested but playout.engine_vlc is not available. "
                "Install python-vlc and libVLC, then try again. "
                f"Original error: {exc}"
            ) from exc
        return VlcPlayoutEngine(**kwargs)

    # Unreachable if PlayoutEngineKind is exhaustive, but makes mypy happy.
    raise NotImplementedError(f"Unhandled PlayoutEngineKind: {kind!r}")
