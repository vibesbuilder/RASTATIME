"""
RASTATIME 2026-11-03 - archiving stage 2: the upload of one episode to
cba.media (``POST wp-json/cba/v1/zipupload``, API specification of the CBA
2026-11).

No Django in here, so the pieces are testable on their own:

* :func:`build_meta` - the ``meta`` JSON from the episode, show and account
  data the job runner collected, or the list of what is missing;
* :func:`write_body` - the multipart body (``meta`` + ``file`` = ZIP with
  ``audio.<ext>`` and the optional ``image.<ext>``) written to ONE temp file,
  the ZIP stored uncompressed and copied into it in blocks, so a two-hour
  recording is never held in memory;
* :class:`ThrottledReader` - the body as a file object that requests streams,
  at most ``kbit`` per second (the uplink also carries the listener
  streams), counting what left the machine;
* :func:`upload` - one POST, and its outcome as an :class:`Outcome` whose
  ``kind`` tells the runner what to do: ``done``, ``retry`` (nothing can
  have reached the CBA), ``failed`` (the CBA refused; trying again does not
  help) or ``unclear`` (the post may exist - a second upload would make a
  second post, the API cannot change or delete one).
"""

from __future__ import annotations

import html
import json
import os
import shutil
import time
import uuid
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, BinaryIO, Optional

ZIPUPLOAD_URL = "https://cba.media/wp-json/cba/v1/zipupload"
CATEGORIES_URL = "https://cba.media/wp-json/wp/v2/categories"

AUDIO_EXTENSIONS = ("mp3", "ogg", "opus")
IMAGE_EXTENSIONS = ("jpg", "jpeg", "png", "gif")
STATUSES = ("publish", "unlisted", "private")
LICENSES = (
    "copyright",
    "cc by",
    "cc by-nc",
    "cc by-nd",
    "cc by-nc-nd",
    "cc sampling+",
    "cc zero",
    "pd",
)
# the language codes the CBA takes (API specification 2026-11)
LANGUAGES = (
    "de en fr sl tr da es cs pt ar sr hr pl it et ce lv fi ro ru hu lt nl zh fa rm yi th he bg "
    "is no bs sv el sq az ja ko ku sk mk am si ur so uk eo"
).split()

CONNECT_TIMEOUT = 30.0
# after the last byte the CBA unpacks the ZIP and creates the post
READ_TIMEOUT = 900.0


@dataclass
class Episode:
    """What the job runner collected for one upload (see archive_jobs.load_episode)."""

    show_name: str
    starts_local: str  # "YYYY-MM-DD HH:MM:SS", station time
    title: str = ""
    description: str = ""
    show_description: str = ""
    teaser: str = ""
    show_teaser: str = ""
    production_date: str = ""  # "" = the broadcast day
    languages: str = ""  # "de,en"
    category_id: Optional[int] = None
    series_id: Optional[int] = None
    status: str = "publish"
    license: str = ""
    tags: str = ""
    editors: tuple[str, ...] = ()
    contains_copyright: bool = False
    image_path: str = ""  # absolute, "" = none
    image_license: str = ""
    image_caption: str = ""
    audio_path: str = ""  # absolute
    username: str = ""
    password: str = ""
    already_post_id: Optional[int] = None
    today_local: str = ""  # "YYYY-MM-DD", for the production-date check


def text_to_html(text: str) -> str:
    """Plain text of the description -> paragraphs; blank lines split them."""
    paragraphs = [p.strip() for p in text.replace("\r\n", "\n").split("\n\n")]
    return "".join("<p>" + html.escape(p).replace("\n", "<br />") + "</p>" for p in paragraphs if p)


def build_meta(ep: Episode) -> tuple[dict[str, Any], list[str]]:
    """The ``meta`` object and what is missing for it (empty list = complete)."""
    missing: list[str] = []
    if ep.already_post_id:
        missing.append(f"the episode is archived already (post {ep.already_post_id})")
    if not ep.username or not ep.password:
        missing.append("the show has no CBA account with an application password")
    # the CBA needs a text: the episode's, else the show's, else the show name (operator 2026-11-03)
    description = ep.description.strip() or ep.show_description.strip() or ep.show_name.strip()
    if not description:
        missing.append("the episode has no description and the show no name")
    languages = [c for c in (ep.languages or "").split(",") if c]
    if not languages or any(c not in LANGUAGES for c in languages) or len(languages) > 3:
        missing.append("the show has no valid language")
    if not ep.category_id:
        missing.append("the show has no CBA topic")
    if ep.license not in LICENSES:
        missing.append("the show has no licence")
    if ep.status not in STATUSES:
        missing.append("unknown visibility")
    broadcast_day = ep.starts_local[:10]
    production = ep.production_date or broadcast_day
    if ep.today_local and production > ep.today_local:
        missing.append("the production date lies in the future")
    ext = os.path.splitext(ep.audio_path)[1].lower().lstrip(".")
    if not ep.audio_path or not os.path.isfile(ep.audio_path):
        missing.append("the audio file is missing")
    elif ext not in AUDIO_EXTENSIONS:
        missing.append(f"the CBA does not take {ext.upper()} files")

    meta: dict[str, Any] = {
        "title": ep.title.strip() or f"{ep.show_name} {broadcast_day}",
        "content": text_to_html(description),
        "teaser": ep.teaser.strip() or ep.show_teaser.strip(),
        "languages": languages,
        "production_date": production,
        "broadcast_date": ep.starts_local,
        "category_id": ep.category_id,
        "status": ep.status,
        "license": ep.license,
        "tags": ep.tags.strip(),
        "editors": ", ".join(ep.editors),
        "contains_copyright": bool(ep.contains_copyright),
    }
    if ep.series_id:
        meta["series_id"] = ep.series_id
    if ep.image_path and os.path.isfile(ep.image_path):
        if ep.image_license:
            meta["image_license"] = ep.image_license
        if ep.image_caption:
            meta["image_caption"] = ep.image_caption[:500]
    return meta, missing


def write_body(
    path: str, meta: dict[str, Any], audio_path: str, image_path: str = ""
) -> tuple[str, int]:
    """
    Write the multipart body to ``path``; returns (content type, size).

    The ZIP is stored, not deflated (MP3 and images do not shrink).  It is
    written to its own file first and then copied into the body:
    :mod:`zipfile` records absolute file positions, so an archive written
    straight into the body points past its own entries once the server
    cuts it out (Python's reader forgives that, PHP's ZipArchive on
    cba.media does not - "ZIP file couldn't be opened").
    """
    boundary = "rastatime-" + uuid.uuid4().hex
    audio_ext = os.path.splitext(audio_path)[1].lower().lstrip(".")
    zip_path = path + ".zip"
    try:
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as zf:
            zf.write(audio_path, f"audio.{audio_ext}")
            if image_path:
                image_ext = os.path.splitext(image_path)[1].lower().lstrip(".")
                zf.write(image_path, f"image.{'jpg' if image_ext == 'jpeg' else image_ext}")
        with open(path, "wb") as fh:
            fh.write(
                (
                    f"--{boundary}\r\n"
                    'Content-Disposition: form-data; name="meta"\r\n'
                    "Content-Type: application/json; charset=utf-8\r\n\r\n"
                ).encode()
            )
            fh.write(json.dumps(meta, ensure_ascii=False).encode("utf-8"))
            fh.write(
                (
                    f"\r\n--{boundary}\r\n"
                    'Content-Disposition: form-data; name="file"; filename="episode.zip"\r\n'
                    "Content-Type: application/zip\r\n\r\n"
                ).encode()
            )
            with open(zip_path, "rb") as zfh:
                shutil.copyfileobj(zfh, fh, 1024 * 1024)
            fh.write(f"\r\n--{boundary}--\r\n".encode())
            size = fh.tell()
    finally:
        try:
            os.remove(zip_path)
        except OSError:
            pass
    return f"multipart/form-data; boundary={boundary}", size


class ThrottledReader:
    """
    A file object for ``requests``: at most ``kbit`` per second on average,
    ``sent`` counts the bytes handed to the socket, ``progress`` is called
    with that count about every ``every`` seconds.
    """

    def __init__(
        self,
        fh: BinaryIO,
        size: int,
        kbit: int,
        progress: Optional[Callable[[int], None]] = None,
        every: float = 5.0,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._fh = fh
        self._size = size
        self._rate = max(1, int(kbit)) * 1000 / 8  # bytes per second
        self._progress = progress
        self._every = every
        self._clock = clock
        self._sleep = sleep
        self._start = clock()
        self._last_report = self._start
        self.sent = 0

    def __len__(self) -> int:
        return self._size

    def read(self, n: int = -1) -> bytes:
        chunk = 65536 if n is None or n < 0 else min(n, 65536)
        data = self._fh.read(chunk)
        if not data:
            return data
        self.sent += len(data)
        ahead = self.sent / self._rate - (self._clock() - self._start)
        if ahead > 0:
            self._sleep(ahead)
        now = self._clock()
        if self._progress is not None and now - self._last_report >= self._every:
            self._last_report = now
            self._progress(self.sent)
        return data


@dataclass
class Outcome:
    kind: str  # done | retry | failed | unclear
    message: str = ""
    post_id: Optional[int] = None


def classify(status: int, body: str) -> Outcome:
    """The CBA's answer -> what the runner does with the job."""
    try:
        data = json.loads(body) if body else {}
    except ValueError:
        data = {}
    message = str(data.get("message") or "").strip() if isinstance(data, dict) else ""
    if 200 <= status < 300:
        if isinstance(data, dict) and data.get("success") is True and data.get("post_id"):
            return Outcome("done", "", int(data["post_id"]))
        return Outcome(
            "failed", f"cba.media refused the upload: {message or body[:200] or 'no answer'}"
        )
    if status in (429, 503):
        return Outcome("retry", f"cba.media is busy (HTTP {status})")
    if status in (401, 403):
        return Outcome(
            "failed", f"cba.media refused the CBA account (HTTP {status}): {message}".rstrip(": ")
        )
    if 400 <= status < 500:
        return Outcome(
            "failed",
            f"cba.media refused the upload (HTTP {status}): {message or body[:200]}".rstrip(": "),
        )
    # 500 / 502 / 504 ...: the post may have been created before the error
    return Outcome(
        "unclear", f"cba.media answered HTTP {status}: {message or body[:200]}".rstrip(": ")
    )


def upload(
    body_path: str,
    content_type: str,
    size: int,
    username: str,
    password: str,
    kbit: int,
    progress: Optional[Callable[[int], None]] = None,
    url: str = ZIPUPLOAD_URL,
    session: Any = None,
) -> tuple[Outcome, int]:
    """POST the body; returns the outcome and the bytes sent."""
    import requests  # noqa: PLC0415 - the worker imports it lazily, tests too

    http = session or requests
    with open(body_path, "rb") as fh:
        reader = ThrottledReader(fh, size, kbit, progress)
        try:
            response = http.post(
                url,
                data=reader,
                headers={
                    "Content-Type": content_type,
                    "Content-Length": str(size),
                    "User-Agent": "RASTATIME",
                },
                auth=(username, password),
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )
        except requests.exceptions.ConnectTimeout as exc:
            return Outcome(
                "retry", f"cba.media could not be reached: {exc.__class__.__name__}"
            ), reader.sent
        except requests.exceptions.ConnectionError as exc:
            if reader.sent == 0:
                return Outcome(
                    "retry", f"cba.media could not be reached: {exc.__class__.__name__}"
                ), 0
            return Outcome(
                "unclear", f"the connection broke off after {reader.sent} bytes"
            ), reader.sent
        except requests.exceptions.Timeout:
            return Outcome("unclear", "no answer from cba.media after the upload"), reader.sent
        except requests.exceptions.RequestException as exc:
            kind = "retry" if reader.sent == 0 else "unclear"
            return Outcome(kind, f"upload error: {exc.__class__.__name__}"), reader.sent
    return classify(response.status_code, response.text or ""), reader.sent
