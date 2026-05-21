"""
ArchiveOutput — configuration for a local file archive sink (UC-O9).

Use case
--------
UC-O9 (P3): Archive the broadcast to a local file via libVLC's
``access=file`` sout sink, running in parallel with any live Icecast output
via VLC's ``duplicate{}`` sout.

How archiving works with LibVlcEgressManager
--------------------------------------------
An :class:`ArchiveOutput` is converted to a ``#transcode{...}:std{...}``
chain (via :meth:`~._sout.SoutBuilder.for_archive`) in the same way as a
:class:`~.interface.StreamOutput`.  Both output types can coexist in the
``duplicate{}`` chain, so live streaming and local archiving happen in a
single decode pass::

    #duplicate{
        dst=transcode{acodec=mp3,...}:std{access=shout,...},   ← Icecast
        dst=transcode{acodec=mp3,...}:std{access=file,...}     ← archive
    }

This is handled by :class:`~._vlc_manager.LibVlcEgressManager` when
:meth:`~._vlc_manager.LibVlcEgressManager.add_archive_output` is used (T10.4).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ArchiveOutput:
    """
    Immutable configuration for a local file archive output (UC-O9).

    Unlike :class:`~.interface.StreamOutput` (which targets an Icecast /
    SHOUTcast server), an :class:`ArchiveOutput` writes encoded audio to
    a local file via libVLC's ``access=file`` sout sink.

    Parameters
    ----------
    id:
        Unique identifier for this archive output.  Must be distinct from
        any :class:`~.interface.StreamOutput` ids in the same manager.
    name:
        Human-readable label (shown in status API / UI).
    path:
        Destination file path.  VLC accepts Windows paths with backslashes
        or forward slashes; :class:`pathlib.Path` is preferred.
    codec:
        Audio codec for encoding (default ``"mp3"``).  Must be a key in
        :attr:`~._sout.SoutBuilder._CODEC_MAP`.
    bitrate:
        Target bitrate in kbps (default 128).
    enabled:
        When ``False`` this output is skipped by
        :meth:`~._vlc_manager.LibVlcEgressManager.start_all`.
    """

    id: str
    name: str
    path: Path
    codec: str = "mp3"
    bitrate: int = 128
    enabled: bool = True

    def __post_init__(self) -> None:
        # Coerce str → Path for convenience
        if not isinstance(self.path, Path):
            object.__setattr__(self, "path", Path(self.path))
