"""
RASTATIME 2026-09-28 - Live Text Info: the "now playing" line as a text file.

Liquidsoap builds the line for every metadata packet on the bus with the
operator's Live Text Format (``label_for`` in the rendered ICY block - the
same fields and fallbacks the Stream Label uses, so DJ titles, webstream
titles, line-ins and the Off Air text are covered) and POSTs it to the
playout listener (``/live-text``).  :class:`LiveTextWriter` then

  * writes the line into the public web folder (``/live/now-playing.txt``
    served statically by Apache, independent of the Public API switch),
  * writes it into an optional local file (network share, other systems),
  * uploads it to an FTP / FTPS / SFTP server on every change.

The text is one UTF-8 line without BOM; it is always replaced, never
appended.  Identical lines are ignored.  Settings (Settings -> General,
"Live Text Info") are re-read before every update, so a save takes
effect at the next change.  I/O runs on a worker thread; the playout
callback never blocks.
"""
from __future__ import annotations

import ftplib
import json
import logging
import os
import shutil
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Mapping, Optional, Tuple

logger = logging.getLogger(__name__)

WEB_FILE_NAME = "now-playing.txt"
DEFAULT_WEB_DIR = "C:/RASTATIME/frontend/legacy/public/live"
WEB_DIR_ENV = "RASTATIME_LIVE_TEXT_WEB_DIR"
VALID_FORMATS = (0, 1, 2)
FTP_PROTOCOLS = ("ftp", "ftps", "sftp")
FTP_TIMEOUT_SECONDS = 20.0
MAX_LINE_LENGTH = 500

_PREF_ENABLED = "live_text_enabled"
_PREF_FORMAT = "live_text_format"
_PREF_WEB = "live_text_web_enabled"
_PREF_FILE = "live_text_file_path"
_PREF_FTP = "live_text_ftp_config"


@dataclass(frozen=True)
class LiveTextFtp:
    enabled: bool = False
    protocol: str = "ftp"
    host: str = ""
    port: int = 0
    username: str = ""
    password: str = ""
    path: str = "/"

    def complete(self) -> bool:
        return bool(self.enabled and self.host and self.username)

    def remote_path(self) -> str:
        """The remote file: a path ending in '/' gets the default file name."""
        path = self.path or "/"
        if not path.startswith("/"):
            path = "/" + path
        if path.endswith("/"):
            path += WEB_FILE_NAME
        return path


@dataclass(frozen=True)
class LiveTextConfig:
    enabled: bool = False
    label_format: int = 0
    web_enabled: bool = True
    file_path: str = ""
    ftp: LiveTextFtp = field(default_factory=LiveTextFtp)


def _truthy(value: object) -> bool:
    return str(value or "").strip().lower() in ("1", "true", "on", "yes")


def parse_live_text_config(entries: Mapping[str, object]) -> LiveTextConfig:
    """Tolerant build from a cc_pref key/value mapping."""
    raw_format = entries.get(_PREF_FORMAT)
    try:
        label_format = int(str(raw_format).strip()) if raw_format not in (None, "") else 0
    except (TypeError, ValueError):
        label_format = 0
    if label_format not in VALID_FORMATS:
        label_format = 0
    ftp = LiveTextFtp()
    raw_ftp = entries.get(_PREF_FTP)
    if raw_ftp:
        try:
            data = json.loads(str(raw_ftp)) if isinstance(raw_ftp, str) else dict(raw_ftp)
        except (TypeError, ValueError):
            logger.warning("cc_pref %s is not JSON - FTP push disabled", _PREF_FTP)
            data = {}
        if isinstance(data, dict):
            try:
                port = int(str(data.get("port") or "0").strip() or 0)
            except ValueError:
                port = 0
            protocol = str(data.get("protocol") or "ftp").strip().lower()
            ftp = LiveTextFtp(
                enabled=_truthy(data.get("enabled")),
                protocol=protocol if protocol in FTP_PROTOCOLS else "ftp",
                host=str(data.get("host") or "").strip(),
                port=port,
                username=str(data.get("username") or "").strip(),
                password=str(data.get("password") or ""),
                path=str(data.get("path") or "/").strip() or "/",
            )
    web_raw = entries.get(_PREF_WEB)
    return LiveTextConfig(
        enabled=_truthy(entries.get(_PREF_ENABLED)),
        label_format=label_format,
        web_enabled=True if web_raw in (None, "") else _truthy(web_raw),
        file_path=str(entries.get(_PREF_FILE) or "").strip(),
        ftp=ftp,
    )


def read_live_text_config_from_db() -> Optional[LiveTextConfig]:
    """cc_pref via the Django ORM (same path as the ICY preferences); None on error."""
    try:
        from rastatime_api.core.models import Preference  # type: ignore[import-untyped]

        prefs = dict(Preference.site.values_list("key", "value"))
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("Live Text settings could not be read: %s", exc)
        return None
    return parse_live_text_config(prefs)


def default_web_dir() -> Path:
    return Path(os.environ.get(WEB_DIR_ENV) or DEFAULT_WEB_DIR)


def write_atomic(path: Path, text: str) -> None:
    """Write the line to a temp file next to the target and replace the target."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text + "\n")
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# FTP / FTPS / SFTP upload
# ---------------------------------------------------------------------------

_curl_with_ssh: Optional[str] = None


def _find_curl_with_libssh2() -> Optional[str]:
    """SFTP needs a curl built with libssh2 (the Windows one is Schannel-only)."""
    global _curl_with_ssh  # pylint: disable=global-statement
    if _curl_with_ssh:
        return _curl_with_ssh
    candidates = [
        shutil.which("curl"),
        "C:/Program Files/Git/mingw64/bin/curl.exe",
        "C:/Program Files/Git/usr/bin/curl.exe",
    ]
    for cand in candidates:
        if not cand or not Path(cand).exists():
            continue
        try:
            out = subprocess.run([cand, "--version"], capture_output=True, text=True, timeout=10, check=False).stdout
        except Exception:  # pylint: disable=broad-exception-caught
            continue
        if "libssh2" in out or "sftp" in out.lower():
            _curl_with_ssh = cand
            return cand
    return None


def upload_ftp(cfg: LiveTextFtp, local_file: Path) -> None:
    """Upload ``local_file`` to ``cfg.remote_path()``; raises on failure."""
    remote = cfg.remote_path()
    if cfg.protocol == "sftp":
        curl = _find_curl_with_libssh2()
        if not curl:
            raise RuntimeError("SFTP needs a curl with libssh2 (e.g. the one shipped with Git for Windows)")
        port = f":{cfg.port}" if cfg.port else ""
        cmd = [
            curl, "-sS", "--connect-timeout", "10", "--max-time", str(int(FTP_TIMEOUT_SECONDS)),
            "-k", "-u", f"{cfg.username}:{cfg.password}", "-T", str(local_file),
            f"sftp://{cfg.host}{port}{remote}",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=FTP_TIMEOUT_SECONDS + 5, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"curl exit {result.returncode}: {(result.stderr or '').strip()[:200]}")
        return
    client: ftplib.FTP = ftplib.FTP_TLS() if cfg.protocol == "ftps" else ftplib.FTP()
    client.connect(cfg.host, cfg.port or 21, timeout=FTP_TIMEOUT_SECONDS)
    client.login(cfg.username, cfg.password)
    if isinstance(client, ftplib.FTP_TLS):
        client.prot_p()
    try:
        with open(local_file, "rb") as fh:
            client.storbinary(f"STOR {remote}", fh)
    finally:
        try:
            client.quit()
        except Exception:  # pylint: disable=broad-exception-caught
            client.close()


# ---------------------------------------------------------------------------
# the writer
# ---------------------------------------------------------------------------

class LiveTextWriter:
    def __init__(
        self,
        read_config: Callable[[], Optional[LiveTextConfig]],
        web_dir: Optional[Path] = None,
        ftp_upload: Callable[[LiveTextFtp, Path], None] = upload_ftp,
    ) -> None:
        self._read_config = read_config
        self._web_dir = Path(web_dir) if web_dir else default_web_dir()
        self._ftp_upload = ftp_upload
        self._lock = threading.Lock()
        self._io_lock = threading.Lock()
        self._last: Optional[Tuple[str, LiveTextConfig]] = None
        self._seq = 0
        self.last_error: Optional[str] = None

    # -- settings for the Liquidsoap side --------------------------------------

    def liquidsoap_settings(self) -> Optional[Tuple[bool, int]]:
        cfg = self._read_config()
        if cfg is None:
            return None
        return (cfg.enabled, cfg.label_format)

    @property
    def web_file(self) -> Path:
        return self._web_dir / WEB_FILE_NAME

    # -- updates --------------------------------------------------------------

    @staticmethod
    def clean(text: object) -> str:
        return " ".join(str(text or "").split())[:MAX_LINE_LENGTH]

    def update(self, text: object, *, wait: bool = False) -> bool:
        """
        A new "now playing" line from Liquidsoap.  Returns True when the
        line is new (or the settings changed) and the targets are being
        written; identical lines are ignored.
        """
        line = self.clean(text)
        if not line:
            return False
        cfg = self._read_config()
        if cfg is None or not cfg.enabled:
            return False
        with self._lock:
            if self._last == (line, cfg):
                return False
            self._last = (line, cfg)
            self._seq += 1
            seq = self._seq
        if wait:
            self._write_targets(line, cfg, seq)
        else:
            t = threading.Thread(target=self._write_targets, args=(line, cfg, seq), name="live-text", daemon=True)
            t.start()
        return True

    def _is_stale(self, seq: int) -> bool:
        with self._lock:
            return seq != self._seq

    def _write_targets(self, line: str, cfg: LiveTextConfig, seq: int) -> None:
        with self._io_lock:
            if self._is_stale(seq):
                return
            written: Optional[Path] = None
            if cfg.web_enabled:
                try:
                    write_atomic(self.web_file, line)
                    written = self.web_file
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    self.last_error = f"web file: {exc}"
                    logger.warning("Live Text: web file %s not written: %s", self.web_file, exc)
            if cfg.file_path:
                try:
                    write_atomic(Path(cfg.file_path), line)
                    written = written or Path(cfg.file_path)
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    self.last_error = f"file: {exc}"
                    logger.warning("Live Text: file %s not written: %s", cfg.file_path, exc)
            if cfg.ftp.enabled:
                if not cfg.ftp.complete():
                    logger.warning("Live Text: FTP push enabled but host / username missing.")
                else:
                    source = written
                    if source is None:
                        source = self._web_dir / (WEB_FILE_NAME + ".upload")
                        try:
                            write_atomic(source, line)
                        except Exception as exc:  # pylint: disable=broad-exception-caught
                            logger.warning("Live Text: upload staging file failed: %s", exc)
                            source = None
                    if source is not None:
                        try:
                            self._ftp_upload(cfg.ftp, source)
                            self.last_error = None
                            logger.info(
                                "Live Text: pushed to %s://%s%s", cfg.ftp.protocol, cfg.ftp.host, cfg.ftp.remote_path(),
                            )
                        except Exception as exc:  # pylint: disable=broad-exception-caught
                            self.last_error = f"ftp: {exc}"
                            logger.warning(
                                "Live Text: FTP push to %s://%s failed: %s", cfp(cfg), cfg.ftp.host, exc,
                            )
            logger.info("Live Text: %r", line)


def cfp(cfg: LiveTextConfig) -> str:
    return cfg.ftp.protocol
