import logging
import os
from enum import Enum
from queue import Queue
from typing import Any, Dict, Protocol

from pydantic import BaseModel

from .analyze_cuepoint import UnreadableFileError, analyze_cuepoint, analyze_duration
from .analyze_loudness import analyze_loudness
from .analyze_metadata import analyze_metadata
from .analyze_playability import UnplayableFileError, analyze_playability
from .analyze_replaygain import analyze_replaygain
from .convert_format import convert_format, discard_converted, remove_original
from .organise_file import organise_file
from .repair_container import repair_container

logger = logging.getLogger(__name__)


class Step(Protocol):
    @staticmethod
    def __call__(filename: str, metadata: Dict[str, Any]): ...


class PipelineStatus(int, Enum):
    SUCCEED = 0
    PENDING = 1
    FAILED = 2


class PipelineOptions(BaseModel):
    analyze_cue_points: bool = False
    # RASTATIME 2026-10-14 - Settings -> Local Machine "convert_lossless_to_mp3"
    # (the legacy app sends it with every import message).  False when the
    # message does not carry it, so an old message behaves as before.
    convert_lossless: bool = False


class Pipeline:
    """Analyzes and imports an audio file into the Airtime library.

    This currently performs metadata extraction (eg. gets the ID3 tags from an MP3),
    then moves the file to the Airtime music library (stor/imported), and returns
    the results back to the parent process.
    """

    @staticmethod
    def run_analysis(
        queue: Queue,
        audio_file_path: str,
        import_directory: str,
        original_filename: str,
        options: PipelineOptions,
    ):
        """Analyze and import an audio file, and put all extracted metadata into queue.

        Keyword arguments:
            queue: A multiprocessing.queues.Queue which will be used to pass the
                   extracted metadata back to the parent process.
            audio_file_path: Path on disk to the audio file to analyze.
            import_directory: Path to the final Airtime "import" directory where
                              we will move the file.
            original_filename: The original filename of the file, which we'll try to
                               preserve. The file at audio_file_path typically has a
                               temporary randomly generated name, which is why we want
                               to know what the original name was.
        """
        try:
            if not isinstance(queue, Queue):
                raise TypeError("queue must be a Queue.Queue()")
            if not isinstance(audio_file_path, str):
                raise TypeError(
                    "audio_file_path must be unicode. Was of type "
                    + type(audio_file_path).__name__
                    + " instead."
                )
            if not isinstance(import_directory, str):
                raise TypeError(
                    "import_directory must be unicode. Was of type "
                    + type(import_directory).__name__
                    + " instead."
                )
            if not isinstance(original_filename, str):
                raise TypeError(
                    "original_filename must be unicode. Was of type "
                    + type(original_filename).__name__
                    + " instead."
                )

            # Analyze the audio file we were told to analyze:
            # First, we extract the ID3 tags and other metadata:
            metadata = {}
            # RASTATIME 2026-10-28 - a container ffprobe rejects (ID3 block in
            # front of a RIFF header) is repaired into a sibling copy first;
            # the broken original stays until the copy is filed, like a
            # converted file's source.
            source_path = audio_file_path
            audio_file_path, original_filename, metadata = repair_container(
                audio_file_path, original_filename, metadata,
            )
            repaired_path = audio_file_path if audio_file_path != source_path else None
            metadata = analyze_metadata(audio_file_path, metadata)
            # RASTATIME 2026-10-14 - format normalization: raw ADTS AAC is
            # repacked to M4A, lossless audio transcoded to MP3 320 kbps (when
            # convert_lossless).  It may hand back a new file and file name;
            # every later step measures the file that is filed in the library.
            audio_file_path, original_filename, metadata = convert_format(
                audio_file_path,
                original_filename,
                metadata,
                convert_lossless=options.convert_lossless,
            )
            converted = audio_file_path != source_path
            try:
                metadata = analyze_duration(audio_file_path, metadata)
                if options.analyze_cue_points:
                    metadata = analyze_cuepoint(audio_file_path, metadata)
                metadata = analyze_replaygain(audio_file_path, metadata)
                metadata = analyze_loudness(audio_file_path, metadata)
                metadata = analyze_playability(audio_file_path, metadata)

                metadata = organise_file(
                    audio_file_path,
                    import_directory,
                    original_filename,
                    metadata,
                )
            except BaseException:
                # RASTATIME 2026-10-14 - the import failed (or the analyzer
                # is stopping): drop the conversion, keep the original in
                # organize/ exactly as without it.
                if converted:
                    discard_converted(audio_file_path)
                if repaired_path and repaired_path != audio_file_path:
                    discard_converted(repaired_path)
                raise
            if converted:
                # Operator decision 2026-10-14: the lossless original is not
                # kept - deleted only now that its conversion is filed.
                remove_original(source_path)
                if repaired_path and repaired_path != audio_file_path:
                    discard_converted(repaired_path)  # the intermediate of a repaired + converted file

            metadata["import_status"] = PipelineStatus.SUCCEED

            # Pass all the file metadata back to the main analyzer process
            queue.put(metadata)
        except UnplayableFileError as exception:
            logger.exception(exception)
            queue.put(Pipeline.failure("The file could not be played: " + str(exception)))
            raise exception
        except Exception as exception:
            logger.exception(exception)
            queue.put(Pipeline.failure(Pipeline.describe(exception)))
            raise exception

    # RASTATIME 2026-10-28 - the reason of a failed import travels to the
    # library row (cc_files.comment) and from there to the Upload page's
    # "Failed" rows; before, every failure read "An error occurred while
    # importing this file" and the real cause was in the analyzer log only.
    REASON_MAX = 300

    @staticmethod
    def describe(exception: BaseException) -> str:
        import subprocess  # noqa: PLC0415

        if isinstance(exception, UnreadableFileError):
            return str(exception)
        if isinstance(exception, subprocess.CalledProcessError):
            tool = os.path.basename(str(exception.cmd[0])) if exception.cmd else "tool"
            err = exception.stderr
            if isinstance(err, bytes):
                err = err.decode("utf-8", "replace")
            tail = " ".join(str(err or "").strip().splitlines()[-2:])
            return f"{tool} could not read the file: {tail}".strip()
        text = str(exception).strip() or exception.__class__.__name__
        return f"{exception.__class__.__name__}: {text}" if not text.startswith(exception.__class__.__name__) else text

    @staticmethod
    def failure(reason: str) -> Dict[str, Any]:
        reason = " ".join(str(reason).split())[: Pipeline.REASON_MAX]
        return {"import_status": PipelineStatus.FAILED, "comments": reason}

    @staticmethod
    def run_loudness(queue: Queue, audio_file_path: str):
        """
        RASTATIME 2026-09-28 - re-measure an ALREADY IMPORTED file (EBU
        R128 only): no metadata extraction, no move, no import status.
        The result carries just the three loudness keys, so the callback
        PUT touches nothing else in cc_files.
        """
        metadata: Dict[str, Any] = {}
        try:
            metadata = analyze_loudness(audio_file_path, metadata)
            queue.put(metadata)
        except Exception as exception:
            logger.exception(exception)
            raise exception
