"""
SoutBuilder — libVLC sout chain string factory.

Builds the ``sout=...`` option strings that are attached to every VLC media
object when streaming is active.  All methods are pure string manipulation;
no VLC instance is needed.

Confirmed working on libVLC 3.0.23 / Windows (T9.2 capability matrix):

* MP3 → ``acodec=mp3, mux=dummy``
* OGG Vorbis → ``acodec=vorb, mux=ogg``
* OGG Opus → ``acodec=opus, mux=ogg, samplerate=48000``  (T10.2)
* AAC/MP4 → ``acodec=mp4a, mux=mp4``                     (T10.2)

Multi-output (T10.3) uses VLC's ``duplicate{}`` sout wrapper so one decode
pass feeds N simultaneous encode-and-push chains.

File archive (T10.4 / UC-O9): :meth:`for_archive` builds ``access=file``
chains; use with :class:`~._archive.ArchiveOutput`.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from .interface import StreamOutput


class SoutBuilder:
    """
    Builds libVLC ``sout=...`` chain strings from :class:`StreamOutput` configs.

    All class methods are pure: no side effects, no I/O.

    Codec support
    -------------
    T10.1 (P1):
        ``"mp3"``     — MP3 → Icecast/SHOUTcast (UC-O1, UC-O5)
        ``"vorbis"``  — OGG Vorbis → Icecast    (UC-O2)
        ``"ogg"``     — alias for ``"vorbis"``

    T10.2 (P2, deferred):
        ``"opus"``    — OGG Opus → Icecast ≥ 2.4 (UC-O3); samplerate forced to 48000
        ``"aac"``     — AAC-LC → Icecast/SHOUTcast (UC-O4)
    """

    # ---------------------------------------------------------------------------
    # Codec dispatch table
    # ---------------------------------------------------------------------------

    # Maps StreamOutput.codec (lower-case) → VLC transcode parameters.
    # "samplerate" is set per codec: Opus requires 48000 Hz; others use 44100.
    _CODEC_MAP: dict[str, dict[str, object]] = {
        "mp3":    {"acodec": "mp3",  "mux": "dummy", "samplerate": 44100},
        "vorbis": {"acodec": "vorb", "mux": "ogg",   "samplerate": 44100},
        "ogg":    {"acodec": "vorb", "mux": "ogg",   "samplerate": 44100},
        "opus":   {"acodec": "opus", "mux": "ogg",   "samplerate": 48000},
        "aac":    {"acodec": "mp4a", "mux": "mp4",   "samplerate": 44100},
    }

    # ---------------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------------

    @classmethod
    def for_output(cls, output: "StreamOutput") -> str:
        """
        Build the complete ``sout=...`` chain string for one :class:`StreamOutput`.

        The returned string is suitable as the value of the VLC media option::

            media.add_option(f"sout={SoutBuilder.for_output(output)}")

        Parameters
        ----------
        output:
            A configured :class:`~streams.egress.interface.StreamOutput`.

        Returns
        -------
        str
            A VLC sout chain string, e.g.::

                #transcode{acodec=mp3,ab=128,channels=2,samplerate=44100}
                :std{access=shout,mux=dummy,dst=source:pass@host:8000/live.mp3}

        Raises
        ------
        ValueError
            If ``output.codec`` is not in the supported codec map.
        """
        codec = output.codec.lower()
        spec = cls._CODEC_MAP.get(codec)
        if spec is None:
            supported = ", ".join(sorted(cls._CODEC_MAP))
            raise ValueError(
                f"Unsupported codec {codec!r}. "
                f"Supported: {supported}"
            )

        dst = cls._build_dst(output)
        transcode = (
            f"acodec={spec['acodec']}"
            f",ab={output.bitrate}"
            f",channels=2"
            f",samplerate={spec['samplerate']}"
        )
        mux = spec["mux"]
        return (
            f"#transcode{{{transcode}}}"
            f":std{{access=shout,mux={mux},dst={dst}}}"
        )

    @classmethod
    def for_multi_output(cls, outputs: "list[StreamOutput]") -> str:
        """
        Build a VLC ``duplicate{}`` sout chain for N simultaneous outputs.

        Audio is decoded once; each branch transcodes and pushes to its
        respective Icecast/SHOUTcast server independently.

        Use for T10.3 (UC-O6 — multiple simultaneous streams).
        For a single output, :meth:`for_output` is called directly.

        Parameters
        ----------
        outputs:
            Non-empty list of :class:`StreamOutput` objects, all enabled.

        Raises
        ------
        ValueError
            If *outputs* is empty.
        """
        if not outputs:
            raise ValueError("outputs list must not be empty")
        if len(outputs) == 1:
            return cls.for_output(outputs[0])

        # Each branch: transcode{...}:std{...}   (no leading '#' inside duplicate)
        branches = []
        for output in outputs:
            chain = cls.for_output(output)
            inner = chain.lstrip("#")          # strip leading '#'
            branches.append(f"dst={inner}")

        return "#duplicate{" + ",".join(branches) + "}"

    @classmethod
    def for_archive(
        cls,
        dest_path: Union[str, Path],
        codec: str = "mp3",
        bitrate: int = 128,
    ) -> str:
        """
        Build a ``sout=...`` chain that encodes audio to a local file (UC-O9).

        Uses ``access=file`` instead of ``access=shout``, targeting a local
        filesystem path rather than an Icecast server.  Confirmed working
        in T10.2 VLC integration tests (``access=file`` used as Icecast proxy).

        Parameters
        ----------
        dest_path:
            Destination file path (``str`` or :class:`pathlib.Path`).
            VLC accepts Windows backslash paths; forward slashes also work.
        codec:
            Audio codec (default ``"mp3"``).  Must be a key in
            :attr:`_CODEC_MAP`.
        bitrate:
            Target bitrate in kbps (default 128).

        Returns
        -------
        str
            A VLC sout chain string, e.g.::

                #transcode{acodec=mp3,ab=128,channels=2,samplerate=44100}
                :std{access=file,mux=dummy,dst=C:\\archive\\2026-04-26.mp3}

        Raises
        ------
        ValueError
            If *codec* is not in the supported codec map.
        """
        codec_key = codec.lower()
        spec = cls._CODEC_MAP.get(codec_key)
        if spec is None:
            supported = ", ".join(sorted(cls._CODEC_MAP))
            raise ValueError(
                f"Unsupported archive codec {codec!r}. "
                f"Supported: {supported}"
            )

        transcode = (
            f"acodec={spec['acodec']}"
            f",ab={bitrate}"
            f",channels=2"
            f",samplerate={spec['samplerate']}"
        )
        mux = spec["mux"]
        dst = str(dest_path)
        return (
            f"#transcode{{{transcode}}}"
            f":std{{access=file,mux={mux},dst={dst}}}"
        )

    @classmethod
    def supported_codecs(cls) -> list[str]:
        """Return a sorted list of supported codec strings."""
        return sorted(cls._CODEC_MAP.keys())

    # ---------------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------------

    @staticmethod
    def _build_dst(output: "StreamOutput") -> str:
        """
        Build the ``user:password@host:port/mount`` shout destination string.

        Rules
        -----
        * ``username`` defaults to ``"source"`` if blank (standard Icecast default).
        * ``mount`` is normalised to start with ``/``.
        """
        user = output.username or "source"
        password = output.password or ""
        mount = output.mount
        if not mount.startswith("/"):
            mount = f"/{mount}"
        return f"{user}:{password}@{output.url}:{output.port}{mount}"
