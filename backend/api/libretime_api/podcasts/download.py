"""
Podcast episode direct-download helper.

T-PODCAST-1: Replaces the defunct Celery/RabbitMQ dispatch chain with a
synchronous HTTP call triggered from the PHP frontend.

Instead of uploading via /rest/media (which requires PHP CGI auth-header
forwarding and Zend_File_Transfer), this module writes the audio file
directly to the media storage directory and creates the cc_files record
via Django ORM — bypassing the entire PHP multipart-upload chain.
"""

import hashlib
import logging
import os
from datetime import timedelta
from email.message import EmailMessage
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, Optional
from urllib.parse import urlsplit

import mutagen
import requests
from mutagen import MutagenError
from requests import RequestException, Response

logger = logging.getLogger(__name__)


class PodcastDownloadError(Exception):
    """Raised when any step of the podcast episode download fails."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_filename(response: Response) -> str:
    """Return a filename from Content-Disposition header or the URL path."""
    value = response.headers.get("Content-Disposition", "")
    if value and "filename" in value:
        parser = EmailMessage()
        parser["Content-Disposition"] = value
        params = parser["Content-Disposition"].params
        if "filename" in params:
            return params["filename"]
    name = Path(urlsplit(response.url).path).name
    return name if name else "episode.mp3"


def _compute_md5(path: Path) -> str:
    """Return the hex MD5 digest of *path*."""
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _get_mime(tags: Any, suffix: str) -> str:
    """Best-effort MIME type: try mutagen first, then fall back to extension."""
    if tags is not None:
        mime_attr = getattr(tags, "mime", None)
        if mime_attr:
            return mime_attr[0] if isinstance(mime_attr, list) else str(mime_attr)
    ext_map = {
        ".mp3": "audio/mpeg",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
        ".m4a": "audio/mp4",
        ".opus": "audio/opus",
        ".wav": "audio/wav",
        ".aac": "audio/aac",
    }
    return ext_map.get(suffix.lower(), "audio/mpeg")


def _safe_filename(episode_id: int, original: str) -> str:
    """
    Build a storage filename unique per episode and safe for most filesystems.
    Prefix with episode ID so collisions are impossible.
    """
    stem = Path(original).stem[:60].replace("/", "_").replace("\\", "_")
    suffix = Path(original).suffix or ".mp3"
    return f"podcast_ep{episode_id}_{stem}{suffix}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def download_episode(
    episode_id: int,
    episode_url: str,
    episode_title: Optional[str],
    podcast_name: str,
    override_album: bool,
    storage_path: str,
    owner_id: Optional[int],
    auto_expiry_enabled: bool = False,
    auto_expiry_days: Optional[int] = None,
    default_track_type_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Download a podcast episode and import it into the media library.

    Steps:
      1. Fetch the audio file over HTTP into a temp file that lives
         directly inside {storage_path}/imported/{owner_dir}/.
      2. Embed metadata tags via mutagen (non-fatal on failure).
      3. Rename the temp file to its final name (same directory).
      4. Create a cc_files record (storage.File) via Django ORM.

    Args:
        episode_id:    PK of the PodcastEpisode row.
        episode_url:   Remote URL to fetch the audio from.
        episode_title: Human-readable title (may be None).
        podcast_name:  Feed title — used for album/artist tags.
        override_album: When True, overwrite artist/album tags with the
                        podcast name and title tag with episode_title.
        storage_path:  Absolute path of the media store root
                       (CONFIG.storage.path, e.g. "C:/rastatime/media").
        owner_id:      cc_subjs.id of the file owner (may be None).
        auto_expiry_enabled: RASTATIME 2026-05-16 — when True, the new
                        cc_files row gets expires_at = now() +
                        auto_expiry_days.  Per design decision B
                        (precedence vote 2026-05-16) this overrides any
                        ID3 'Expiry' tag the publisher may have set.
        auto_expiry_days: number of days to add to now() for expires_at.
                        Ignored if auto_expiry_enabled is False or
                        this value is None / <= 0.
        default_track_type_id: RASTATIME 2026-05-17 — when not None,
                        the new cc_files row gets track_type_id set to
                        this value, regardless of ID3 / filename hints.
                        Per the per-podcast operator setting from the
                        Edit-Podcast dialog ("Track Type:" dropdown).
                        FK references cc_track_types(id).

    Returns:
        dict with keys:
          ``episodeid`` — always present
          ``status``    — 1 on success, 0 on failure
          ``fileid``    — cc_files.id (success only)
          ``error``     — error description (failure only)
    """
    # Deferred import: this module can be loaded without Django configured
    # (e.g. in standalone tests).  The import is resolved at call-time once
    # Django is ready.
    from django.utils import timezone as dj_timezone
    from libretime_api.storage.models import File  # maps to cc_files

    result: Dict[str, Any] = {"episodeid": episode_id}
    tmp_path: Optional[Path] = None

    try:
        # ------------------------------------------------------------------
        # Step 1: Download audio to a temporary file INSIDE the destination
        # directory.  The temp file must NOT be created in %TEMP%: under the
        # NSSM service account that directory's restrictive ACL travels with
        # the file on a same-volume rename (NTFS keeps the security
        # descriptor), producing library files no regular user can read —
        # which silently broke every non-elevated media backup.  Born in
        # import_dir, the file inherits the media-library ACL from creation.
        # ------------------------------------------------------------------
        owner_dir = str(owner_id) if owner_id else "podcast"
        import_dir = Path(storage_path) / "imported" / owner_dir
        import_dir.mkdir(parents=True, exist_ok=True)

        try:
            with requests.get(episode_url, stream=True, timeout=60) as resp:
                resp.raise_for_status()
                original_filename = _extract_filename(resp)
                suffix = Path(original_filename).suffix or ".mp3"
                with NamedTemporaryFile(
                    dir=import_dir,
                    prefix="podcast_tmp_",
                    suffix=suffix,
                    delete=False,
                ) as fp:
                    for chunk in resp.iter_content(chunk_size=65536):
                        fp.write(chunk)
                    tmp_path = Path(fp.name)
        except RequestException as exc:
            raise PodcastDownloadError(
                f"download failed for episode {episode_id}: {exc}"
            ) from exc

        # ------------------------------------------------------------------
        # Step 2: Write metadata tags (failures are non-fatal — the file
        # is still importable without perfect tags)
        # ------------------------------------------------------------------
        try:
            tags = mutagen.File(str(tmp_path), easy=True)
            if tags is not None:
                if override_album:
                    tags["artist"] = [podcast_name]
                    tags["album"] = [podcast_name]
                    if episode_title:
                        tags["title"] = [episode_title]
                else:
                    if "album" not in tags:
                        tags["album"] = [podcast_name]
                tags.save()
        except (MutagenError, TypeError, Exception) as exc:
            logger.warning(
                "podcast episode %d: metadata tag write skipped: %s",
                episode_id,
                exc,
            )

        # ------------------------------------------------------------------
        # Step 3: Read technical audio metadata from the tagged file
        # ------------------------------------------------------------------
        md5 = _compute_md5(tmp_path)
        file_size = tmp_path.stat().st_size
        mime = _get_mime(None, suffix)

        duration: Optional[timedelta] = None
        bit_rate: Optional[int] = None
        sample_rate_val: Optional[int] = None
        channels_val: Optional[int] = None

        try:
            info_tags = mutagen.File(str(tmp_path))
            if info_tags is not None:
                mime = _get_mime(info_tags, suffix)
                info = getattr(info_tags, "info", None)
                if info is not None:
                    raw_len = getattr(info, "length", None)
                    if raw_len:
                        duration = timedelta(seconds=float(raw_len))
                    raw_br = getattr(info, "bitrate", None)
                    if raw_br:
                        bit_rate = int(raw_br)
                    raw_sr = getattr(info, "sample_rate", None)
                    if raw_sr:
                        sample_rate_val = int(raw_sr)
                    raw_ch = getattr(info, "channels", None)
                    if raw_ch:
                        channels_val = int(raw_ch)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(
                "podcast episode %d: could not read audio info: %s",
                episode_id,
                exc,
            )

        # ------------------------------------------------------------------
        # Step 4: Rename the tagged temp file to its final name (same
        # directory, so the ACL inherited at creation is untouched)
        # ------------------------------------------------------------------
        dest_filename = _safe_filename(episode_id, original_filename)
        dest_path = import_dir / dest_filename
        os.replace(tmp_path, dest_path)
        tmp_path = None  # successfully renamed — nothing to clean up

        # filepath stored in cc_files is relative to storage_path.
        # Use a leading slash and forward slashes (LibreTime convention;
        # PHP on Windows handles both slash styles).
        relative_filepath = f"/imported/{owner_dir}/{dest_filename}"

        # ------------------------------------------------------------------
        # Step 5: Create a cc_files record via Django ORM
        # ------------------------------------------------------------------
        now = dj_timezone.now()

        # RASTATIME 2026-05-16 - Podcast Auto-Expiry: if the parent
        # podcast has auto_expiry_enabled with a positive day count,
        # compute the expiry timestamp here.  This overrides any ID3
        # 'Expiry' tag the publisher embedded (precedence decision B).
        expires_at = None
        if (
            auto_expiry_enabled
            and auto_expiry_days is not None
            and auto_expiry_days > 0
        ):
            expires_at = now + timedelta(days=int(auto_expiry_days))
            logger.info(
                "podcast episode %d: auto-expiry %d days -> %s",
                episode_id, auto_expiry_days, expires_at.isoformat(),
            )

        # RASTATIME 2026-05-17 — Library DataTable computes a track's
        # displayed length as `cueout - cuein` (StoredFile.php ~line 781).
        # The standard analyzer pipeline sets cue_in=0 and cue_out=length
        # at import time so this subtraction yields the real length.
        # download_episode() bypasses the analyzer, so unless we also set
        # cue_in/cue_out here, the Library shows "0 sec" even though the
        # underlying `length` column is populated correctly (Calendar
        # ShowContent reads `length` directly, so it shows the right
        # value — but Library does not).  Default cue_in=0 and cue_out=
        # length so the Library matches.
        zero_interval = timedelta(0)
        db_file = File(
            # Path & size
            filepath=relative_filepath,
            size=file_size,
            exists=True,
            # Audio fingerprint
            mime=mime,
            md5=md5,
            # Import state: mark as SUCCESS immediately (no analyzer step)
            import_status=File.ImportStatus.SUCCESS,
            # Flags
            hidden=False,
            accessed=0,
            scheduled=False,
            part_of_list=False,
            disabled=False,
            # Timestamps
            created_at=now,
            updated_at=now,
            expires_at=expires_at,
            # Metadata
            name=episode_title or dest_filename,
            track_title=episode_title or dest_filename,
            album_title=podcast_name,
            artist_name=podcast_name if override_album else None,
            # Technical audio info (all nullable)
            bit_rate=bit_rate,
            sample_rate=sample_rate_val,
            channels=channels_val,
            length=duration,
            cue_in=zero_interval,
            cue_out=duration if duration is not None else zero_interval,
        )
        if owner_id:
            db_file.owner_id = owner_id
        # RASTATIME 2026-05-17 — apply per-podcast default track-type.
        # Set via the FK column name (track_type_id) rather than the
        # Django attribute name (library_id) so we don't need to load
        # the Library row.  Validation happens at DB level via FK.
        if default_track_type_id is not None:
            db_file.library_id = int(default_track_type_id)
        db_file.save()

        result["fileid"] = db_file.id
        result["status"] = 1
        logger.info(
            "podcast episode %d imported successfully: file_id=%d path=%s",
            episode_id,
            db_file.id,
            dest_path,
        )

    except PodcastDownloadError as exc:
        logger.error("podcast episode download: %s", exc)
        result["status"] = 0
        result["error"] = str(exc)

    except Exception as exc:  # pylint: disable=broad-except
        logger.error(
            "podcast episode download: unexpected error for episode %d: %s",
            episode_id,
            exc,
            exc_info=True,
        )
        result["status"] = 0
        result["error"] = str(exc)

    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()

    return result
