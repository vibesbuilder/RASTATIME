"""
RASTATIME worker tasks.

T-GH-2: Celery removed. All tasks are now plain Python functions that can be
called directly. No message broker or worker process is required.
"""

import json
import logging
import os
from email.message import EmailMessage
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, Optional
from urllib.parse import urlsplit

import mutagen
import requests
from mutagen import MutagenError
from requests import RequestException, Response

from .config import config

logger = logging.getLogger(__name__)

# Optional: legacy API client for task-manager triggering.
try:
    from libretime_api_client.v1 import ApiClient as _LegacyClient

    _legacy_client: Optional[_LegacyClient] = _LegacyClient(
        base_url=config.general.public_url,
        api_key=config.general.api_key,
    )
except ImportError:
    _legacy_client = None
    logger.debug(
        "libretime_api_client not available; legacy_trigger_task_manager disabled."
    )

# Optional: Sentry error tracking (no longer tied to Celery signals).
if "SENTRY_DSN" in os.environ:
    try:
        import sentry_sdk

        sentry_sdk.init(traces_sample_rate=1.0)
        logger.info("Sentry initialised.")
    except ImportError:
        pass


def legacy_trigger_task_manager() -> None:
    """
    Trigger the legacy task manager to perform background tasks.

    No-op when libretime_api_client is not installed.
    """
    if _legacy_client is None:
        logger.warning(
            "legacy_trigger_task_manager: libretime_api_client not available, skipping."
        )
        return
    _legacy_client.trigger_task_manager()


class PodcastDownloadException(Exception):
    """An error occurred during the podcast download task."""


def podcast_download(
    episode_id: int,
    episode_url: str,
    episode_title: Optional[str],
    podcast_name: str,
    override_album: bool,
) -> str:
    """
    Download a podcast episode.

    Args:
        episode_id: Episode ID.
        episode_url: Episode download url.
        episode_title: Episode title to override the title metadata.
        podcast_name: Podcast name to save to the metadata.
        override_album: Whether to override the album metadata.

    Returns:
        Status of the podcast download as JSON string.
    """
    result: Dict[str, Any] = {"episodeid": episode_id}
    tmp_file = None

    try:
        # Download podcast episode file
        try:
            with requests.get(episode_url, stream=True, timeout=30) as resp:
                resp.raise_for_status()

                filename = extract_filename(resp)

                # The filename extension helps to determine the file type using mutagen
                with NamedTemporaryFile(suffix=filename, delete=False) as tmp_file:
                    for chunk in resp.iter_content(chunk_size=2048):
                        tmp_file.write(chunk)

        except RequestException as exception:
            raise PodcastDownloadException(
                f"could not download podcast episode {episode_id}: {exception}"
            ) from exception

        # Save metadata to podcast episode file
        try:
            metadata = mutagen.File(tmp_file.name, easy=True)
            if metadata is None:
                raise PodcastDownloadException(
                    f"could not determine podcast episode {episode_id} file type"
                )

            if override_album:
                logger.debug("overriding album name with podcast name %s", podcast_name)
                metadata["artist"] = podcast_name
                metadata["album"] = podcast_name
                metadata["title"] = episode_title

            elif "album" not in metadata:
                logger.debug("setting album name to podcast name %s", podcast_name)
                metadata["album"] = podcast_name

            metadata.save()
            logger.debug("saved metadata %s", metadata)

        except (MutagenError, TypeError) as exception:
            raise PodcastDownloadException(
                f"could not save podcast episode {episode_id} metadata: {exception}"
            ) from exception

        # Upload podcast episode file
        try:
            with requests.post(
                f"{config.general.public_url}/rest/media",
                files={"file": (filename, open(tmp_file.name, "rb"))},
                auth=(config.general.api_key, ""),
                timeout=30,
            ) as upload_resp:
                upload_resp.raise_for_status()
                upload_payload = upload_resp.json()

                result["fileid"] = upload_payload["id"]
                result["status"] = 1

        except RequestException as exception:
            raise PodcastDownloadException(
                f"could not upload podcast episode {episode_id}: {exception}"
            ) from exception

    except PodcastDownloadException as exception:
        logger.exception(exception)
        result["status"] = 0
        result["error"] = str(exception)

    if tmp_file is not None:
        Path(tmp_file.name).unlink()

    return json.dumps(result)


def extract_filename(response: Response) -> str:
    """
    Extract the filename from a download request.

    Args:
        response: Download request response.

    Returns:
        Extracted filename.
    """
    content_disposition = "Content-Disposition"
    value = response.headers.get(content_disposition)
    if value and "filename" in value:
        parser = EmailMessage()
        parser[content_disposition] = value
        params = parser[content_disposition].params
        return params["filename"]

    return Path(urlsplit(response.url).path).name
