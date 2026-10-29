import logging
from dataclasses import dataclass
from datetime import datetime
from threading import Thread
from time import sleep
from typing import Any, Callable, Dict, List, Optional, Union

import requests
from rastatime_api_client.v1 import ApiClient as LegacyClient
from rastatime_shared.config import IcecastOutput, ShoutcastOutput
from lxml import etree
from requests import Session

from ..config import Config

logger = logging.getLogger(__name__)

AnyOutput = Union[IcecastOutput, ShoutcastOutput]


@dataclass
class Stats:
    listeners: int


@dataclass
class MountedOutput:
    """
    Duck-typed stand-in for :class:`IcecastOutput` built from a
    ``cc_pref`` ``stream_output_N`` dict.

    RASTATIME 2026-08-30: since the Liquidsoap cutover the stream
    outputs live in ``cc_pref`` (rendered into rastatime.liq), while
    ``rastatime.conf``'s ``stream.outputs`` stayed empty — which left
    :class:`StatsCollector` polling nothing and ``cc_listener_count``
    forever empty (BACKLOG "Analytics: Listener Stats sammeln keine
    Daten").  Building full :class:`IcecastOutput` objects would drag
    in required fields the collector never touches (``audio``,
    ``source_password``), so this adapter carries exactly the fields
    :meth:`StatsCollector.collect` reads.
    """

    mount: str
    host: str = "127.0.0.1"
    port: int = 8000
    admin_user: str = "admin"
    admin_password: Optional[str] = None
    enabled: bool = True
    kind: str = "icecast"
    # RASTATIME 2026-10-26 - the N of stream_output_N, so the collection
    # status lands on the right stream even when an earlier one is off
    stream_id: Optional[int] = None


def outputs_from_stream_settings(settings: List[Dict]) -> List[MountedOutput]:
    """
    Map ``cc_pref`` ``stream_output_N`` dicts (as returned by the
    playout's ``_read_stream_outputs``) to :class:`MountedOutput`.

    Entries without an ``admin_pass`` are skipped with a warning —
    the collector could not authenticate against ``/admin/stats.xml``
    anyway, and a loud skip beats a silent 401 loop.
    """
    outputs: List[MountedOutput] = []
    for entry in settings:
        mount = str(entry.get("mount", "")).lstrip("/")
        if not mount:
            continue
        admin_password = str(entry.get("admin_pass", "") or "")
        if not admin_password:
            logger.warning(
                "stream output %r has no admin_pass — skipping listener "
                "stats for this mount",
                mount,
            )
            continue
        try:
            port = int(entry.get("port", 8000))
        except (TypeError, ValueError):
            port = 8000
        try:
            stream_id: Optional[int] = int(entry["stream_id"])
        except (KeyError, TypeError, ValueError):
            stream_id = None
        outputs.append(
            MountedOutput(
                mount=mount,
                host=str(entry.get("host", "127.0.0.1") or "127.0.0.1"),
                port=port,
                admin_user=str(entry.get("admin_user", "admin") or "admin"),
                admin_password=admin_password,
                stream_id=stream_id,
            )
        )
    return outputs


def status_from_exception(exception: Exception, when: datetime) -> str:
    """
    RASTATIME 2026-10-26 - the collection status of a failed poll as
    ``kind|YYYY-MM-DD HH:MM:SS (UTC)|detail`` for Analytics -> Listener
    Stats, which turns the kind into its own message: ``auth`` (401/403),
    ``unreachable``, ``timeout``, ``invalid`` (no stats XML), ``http``
    (any other HTTP error), ``error``.
    """
    if isinstance(exception, requests.exceptions.HTTPError):
        response = exception.response
        code = response.status_code if response is not None else None
        kind = "auth" if code in (401, 403) else "http"
    # ConnectTimeout is a ConnectionError too: it counts as a timeout
    elif isinstance(exception, requests.exceptions.Timeout):
        kind = "timeout"
    elif isinstance(exception, requests.exceptions.ConnectionError):
        kind = "unreachable"
    elif isinstance(exception, etree.XMLSyntaxError):
        kind = "invalid"
    else:
        kind = "error"
    detail = " ".join(str(exception).split())[:300]
    return f"{kind}|{when:%Y-%m-%d %H:%M:%S}|{detail}"


# pylint: disable=too-few-public-methods
class StatsCollector:
    """
    Collect stats from Icecast and Shoutcast.
    """

    _session: Session

    def __init__(self, legacy_client: LegacyClient):
        self._session = Session()
        self._timeout = 30
        self._legacy_client = legacy_client
        # RASTATIME 2026-10-26 - the status kind last reported per stream.
        # Upstream reported failures only and never "OK", so an error stayed
        # on Listener Stats for good once Icecast had recovered (operator
        # report: three 401s from the password change of 2026-10-24).  Now
        # every change is reported once, nothing in between.
        self._reported: Dict[int, str] = {}

    def _report_status(self, stream_id: int, status: str) -> None:
        kind = status.split("|", 1)[0]
        if self._reported.get(stream_id) == kind:
            return
        response = self._legacy_client.update_stream_setting_table(
            {stream_id: status}
        )
        # the v1 wrapper returns None when the request failed: try again
        # on the next poll
        if response is not None:
            self._reported[stream_id] = kind

    def get_output_url(self, output: AnyOutput) -> str:
        if output.kind == "icecast":
            return f"http://{output.host}:{output.port}/admin/stats.xml"
        return f"http://{output.host}:{output.port}/admin.cgi?sid=1&mode=viewxml"

    def collect_output_stats(
        self,
        output: AnyOutput,
    ) -> Dict[str, Stats]:
        response = self._session.get(
            url=self.get_output_url(output),
            auth=(output.admin_user, output.admin_password or ""),
            timeout=self._timeout,
        )
        response.raise_for_status()

        root = etree.fromstring(  # nosec
            response.content,
            parser=etree.XMLParser(resolve_entities=False),
        )

        stats = {}

        # Shoutcast specific parsing
        if output.kind == "shoutcast":
            listeners_el = root.find("CURRENTLISTENERS")
            listeners = 0 if listeners_el is None else int(listeners_el.text)

            stats["shoutcast"] = Stats(
                listeners=listeners,
            )
            return stats

        # Icecast specific parsing
        for source in root.iterchildren("source"):
            mount = source.attrib.get("mount")
            if mount is None:
                continue

            listeners_el = source.find("listeners")
            listeners = 0 if listeners_el is None else int(listeners_el.text)

            mount = mount.lstrip("/")
            stats[mount] = Stats(
                listeners=listeners,
            )

        return stats

    def collect(
        self,
        outputs: List[AnyOutput],
        *,
        _timestamp: Optional[datetime] = None,
    ) -> None:
        if _timestamp is None:
            _timestamp = datetime.utcnow()

        stats: List[Dict[str, Any]] = []
        stats_timestamp = _timestamp.strftime("%Y-%m-%d %H:%M:%S")
        cache: Dict[str, Dict[str, Stats]] = {}

        for output_id, output in enumerate(outputs, start=1):
            if (
                output.kind not in ("icecast", "shoutcast")
                or not output.enabled
                or output.admin_password is None
            ):
                continue

            stream_id = getattr(output, "stream_id", None) or output_id
            output_url = self.get_output_url(output)
            if output_url not in cache:
                try:
                    cache[output_url] = self.collect_output_stats(output)
                except (
                    etree.XMLSyntaxError,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.HTTPError,
                    requests.exceptions.Timeout,
                ) as exception:
                    logger.exception(exception)
                    self._report_status(
                        stream_id, status_from_exception(exception, _timestamp)
                    )
                    continue

            self._report_status(stream_id, "OK")
            output_stats = cache[output_url]

            mount = "shoutcast" if output.kind == "shoutcast" else output.mount

            if mount in output_stats:
                stats.append(
                    {
                        "timestamp": stats_timestamp,
                        "num_listeners": output_stats[mount].listeners,
                        "mount_name": mount,
                    }
                )

        if stats:
            self._legacy_client.push_stream_stats(stats)


class StatsCollectorThread(Thread):
    name = "stats collector"
    daemon = True

    def __init__(
        self,
        config: Config,
        legacy_client: LegacyClient,
        outputs_provider: Optional[Callable[[], List[Any]]] = None,
    ) -> None:
        """
        ``outputs_provider`` — optional callable returning the output
        list to poll (RASTATIME: built fresh from ``cc_pref`` each
        cycle, so Settings → Streams changes are picked up within one
        poll interval).  Without it the thread falls back to the
        ``rastatime.conf`` ``stream.outputs.merged`` list (upstream
        behaviour — empty on RASTATIME deployments).
        """
        super().__init__()
        self._config = config
        self._collector = StatsCollector(legacy_client)
        self._outputs_provider = outputs_provider

    def run(self) -> None:
        logger.info("starting %s", self.name)
        while True:
            try:
                if self._outputs_provider is not None:
                    outputs = self._outputs_provider()
                else:
                    outputs = self._config.stream.outputs.merged
                self._collector.collect(outputs)
            except Exception as exception:  # pylint: disable=broad-exception-caught
                logger.exception(exception)
            sleep(120)
