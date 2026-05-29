"""
RASTATIME 2026-05-25 — Unit tests for LiquidsoapTelnetClient
(Seamless-Bus-Mix Phase C1).

Strategy
--------

A small in-process TCP server (``_FakeLiquidsoapServer``) listens on
an ephemeral port, accepts one client at a time, and responds to
each command line according to a scriptable dict of responses.
The client connects to this fake, so we exercise the real socket
I/O path without needing an actual Liquidsoap subprocess.

The fake also lets us simulate failure modes:
  * Connection closed before END sentinel
  * Slow / delayed response (timeout path)
  * Stale-socket recovery via reconnect-and-retry
"""
from __future__ import annotations

import socket
import threading
import time
from contextlib import contextmanager
from typing import Dict, Iterator, Optional

import pytest

from libretime_playout.engine.liquidsoap_telnet import LiquidsoapTelnetClient


# ---- Fake server fixture ------------------------------------------------


class _FakeLiquidsoapServer:
    """
    Trivial TCP server that mimics Liquidsoap's telnet line protocol.

    For each newline-terminated command received, looks up a
    pre-configured response and writes ``<response>\\nEND\\n`` back
    to the client.  Default response for unrecognised commands is
    empty-body + END.

    Special command sentinels:
      * ``"__close__"`` (configured per-command) — close the socket
        instead of replying, simulates a stale connection.
      * ``"__delay__"`` (configured per-command) — wait 10 s before
        replying, simulates a slow server (used with short client
        timeouts to test the timeout path).
    """

    def __init__(self, responses: Optional[Dict[str, str]] = None):
        self._responses = responses or {}
        self._sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_flag = threading.Event()
        self.host = "127.0.0.1"
        self.port = 0  # filled by start()
        self.received: list[str] = []  # commands the server has seen

    def start(self) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, 0))
        self.port = self._sock.getsockname()[1]
        self._sock.listen(1)
        self._sock.settimeout(0.5)  # so the accept loop can poll _stop_flag
        self._thread = threading.Thread(
            target=self._run, name="fake-ls-server", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_flag.set()
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def _run(self) -> None:
        while not self._stop_flag.is_set():
            try:
                client, _ = self._sock.accept()
            except (socket.timeout, OSError):
                continue
            try:
                self._serve_client(client)
            finally:
                try:
                    client.close()
                except OSError:
                    pass

    def _serve_client(self, client: socket.socket) -> None:
        client.settimeout(2.0)
        buf = b""
        while not self._stop_flag.is_set():
            try:
                chunk = client.recv(4096)
            except (socket.timeout, OSError):
                return
            if not chunk:
                return
            buf += chunk
            while b"\n" in buf:
                line, _, buf = buf.partition(b"\n")
                cmd = line.decode("utf-8").strip()
                self.received.append(cmd)
                if cmd == "quit":
                    return  # close without replying — same as real ls
                response = self._responses.get(cmd, "")
                if response == "__close__":
                    return  # close mid-stream, simulates stale socket
                if response == "__delay__":
                    time.sleep(10)
                    continue
                try:
                    client.sendall(response.encode("utf-8") + b"\nEND\n")
                except OSError:
                    return


@contextmanager
def fake_server(
    responses: Optional[Dict[str, str]] = None,
) -> Iterator[_FakeLiquidsoapServer]:
    server = _FakeLiquidsoapServer(responses)
    server.start()
    try:
        yield server
    finally:
        server.stop()


# ---- Tests --------------------------------------------------------------


def test_basic_command_roundtrip():
    """A command sent — a response received."""
    with fake_server({"request.queue.push file:///foo.mp3": "42"}) as srv:
        client = LiquidsoapTelnetClient(host=srv.host, port=srv.port)
        try:
            resp = client.send_command("request.queue.push file:///foo.mp3")
            assert resp == "42"
            assert srv.received == ["request.queue.push file:///foo.mp3"]
        finally:
            client.close()


def test_empty_response():
    """A command with no body response — just END."""
    with fake_server({"var.set foo = 1": ""}) as srv:
        client = LiquidsoapTelnetClient(host=srv.host, port=srv.port)
        try:
            resp = client.send_command("var.set foo = 1")
            assert resp == ""
        finally:
            client.close()


def test_multiline_response():
    """Multi-line response is joined and stripped."""
    multi = "Available commands:\nhelp\nquit\nrequest.queue.push"
    with fake_server({"help": multi}) as srv:
        client = LiquidsoapTelnetClient(host=srv.host, port=srv.port)
        try:
            resp = client.send_command("help")
            assert "Available commands:" in resp
            assert "request.queue.push" in resp
        finally:
            client.close()


def test_help_wrapper_returns_lines():
    """The help() wrapper splits the multi-line body into a list."""
    multi = "Available commands:\nhelp\nquit\nvar.set"
    with fake_server({"help": multi}) as srv:
        client = LiquidsoapTelnetClient(host=srv.host, port=srv.port)
        try:
            lines = client.help()
            assert "help" in lines
            assert "quit" in lines
            assert "var.set" in lines
        finally:
            client.close()


def test_command_auto_appends_newline():
    """Caller doesn't need to add \\n to the command."""
    with fake_server({"foo": "bar"}) as srv:
        client = LiquidsoapTelnetClient(host=srv.host, port=srv.port)
        try:
            assert client.send_command("foo") == "bar"
            assert client.send_command("foo\n") == "bar"
            assert srv.received == ["foo", "foo"]
        finally:
            client.close()


def test_reconnect_on_stale_socket():
    """Server closes mid-stream; client should reconnect + retry once."""
    # First call: server closes the socket immediately (no response).
    # Second call (after retry triggers a fresh connection): normal reply.
    # We model this by changing the response dict between calls.
    srv = _FakeLiquidsoapServer({"flaky": "__close__"})
    srv.start()
    try:
        client = LiquidsoapTelnetClient(host=srv.host, port=srv.port)
        try:
            # First call triggers the retry path internally; the
            # SECOND attempt (with fresh socket) finds the same
            # __close__ response and fails — so total result is
            # ConnectionError.  Good — we verify both attempts ran.
            with pytest.raises(ConnectionError):
                client.send_command("flaky")
            # Should have seen the command twice (initial attempt +
            # post-reconnect retry).
            assert srv.received.count("flaky") == 2
        finally:
            client.close()
    finally:
        srv.stop()


def test_reconnect_then_success():
    """
    Stale-socket on first attempt, fresh connection succeeds on
    second attempt — total result is a clean response.

    We simulate this by responding to the FIRST occurrence of "thing"
    with __close__ and any later occurrence with the real reply.
    """
    # Use a tiny custom server that flips behaviour after the first
    # request.
    class FlipFlopServer(_FakeLiquidsoapServer):
        def __init__(self):
            super().__init__()
            self._calls = 0

        def _serve_client(self, client: socket.socket) -> None:
            client.settimeout(2.0)
            buf = b""
            while not self._stop_flag.is_set():
                try:
                    chunk = client.recv(4096)
                except (socket.timeout, OSError):
                    return
                if not chunk:
                    return
                buf += chunk
                while b"\n" in buf:
                    line, _, buf = buf.partition(b"\n")
                    cmd = line.decode("utf-8").strip()
                    self.received.append(cmd)
                    if cmd == "quit":
                        return
                    self._calls += 1
                    if self._calls == 1:
                        return  # close → simulate stale socket
                    try:
                        client.sendall(b"ok\nEND\n")
                    except OSError:
                        return

    srv = FlipFlopServer()
    srv.start()
    try:
        client = LiquidsoapTelnetClient(host=srv.host, port=srv.port)
        try:
            assert client.send_command("thing") == "ok"
            # Two attempts → two received-log entries.
            assert srv.received.count("thing") == 2
        finally:
            client.close()
    finally:
        srv.stop()


def test_connection_refused_raises():
    """Connect to a closed port → ConnectionError."""
    # Find a free port then DON'T listen on it.
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    closed_port = s.getsockname()[1]
    s.close()
    client = LiquidsoapTelnetClient(host="127.0.0.1", port=closed_port, timeout=1.0)
    with pytest.raises(ConnectionError):
        client.send_command("anything")


def test_request_queue_push_wrapper():
    """request_queue_push() formats the command using the queue_id."""
    # Wire form on Liquidsoap 2.4: `<queue_id>.push <uri>` where
    # queue_id defaults to "scheduled" (matches our rastatime.liq).
    with fake_server({"scheduled.push file:///foo.mp3": "99"}) as srv:
        client = LiquidsoapTelnetClient(host=srv.host, port=srv.port)
        try:
            rid = client.request_queue_push("file:///foo.mp3")
            assert rid == "99"
        finally:
            client.close()


def test_request_queue_skip_wrapper():
    """request_queue_skip() sends the right command."""
    with fake_server({"scheduled.skip": "Done"}) as srv:
        client = LiquidsoapTelnetClient(host=srv.host, port=srv.port)
        try:
            assert client.request_queue_skip() == "Done"
            assert srv.received == ["scheduled.skip"]
        finally:
            client.close()


def test_request_queue_push_custom_queue_id():
    """Custom queue_id is honoured in the wire-form command."""
    with fake_server({"my_queue.push file:///bar.mp3": "5"}) as srv:
        client = LiquidsoapTelnetClient(
            host=srv.host, port=srv.port, queue_id="my_queue",
        )
        try:
            assert client.request_queue_push("file:///bar.mp3") == "5"
        finally:
            client.close()


def test_var_set_wrapper():
    """var_set() builds the standard 'var.set NAME = VALUE' form."""
    with fake_server({"var.set master_dj_active = true": ""}) as srv:
        client = LiquidsoapTelnetClient(host=srv.host, port=srv.port)
        try:
            client.var_set("master_dj_active", "true")
            assert srv.received == ["var.set master_dj_active = true"]
        finally:
            client.close()


def test_metadata_update_escapes_quotes():
    """metadata_update() backslash-escapes embedded quotes."""
    expected_cmd = (
        'metadata.update title="She said \\"hi\\"",artist="Test"'
    )
    with fake_server({expected_cmd: ""}) as srv:
        client = LiquidsoapTelnetClient(host=srv.host, port=srv.port)
        try:
            client.metadata_update({"title": 'She said "hi"', "artist": "Test"})
            assert srv.received == [expected_cmd]
        finally:
            client.close()


def test_metadata_update_escapes_backslashes():
    """metadata_update() backslash-escapes embedded backslashes too."""
    expected_cmd = 'metadata.update path="C:\\\\rastatime\\\\file.mp3"'
    with fake_server({expected_cmd: ""}) as srv:
        client = LiquidsoapTelnetClient(host=srv.host, port=srv.port)
        try:
            client.metadata_update({"path": r"C:\rastatime\file.mp3"})
            assert srv.received == [expected_cmd]
        finally:
            client.close()


def test_close_is_idempotent():
    """close() can be called repeatedly without error."""
    with fake_server() as srv:
        client = LiquidsoapTelnetClient(host=srv.host, port=srv.port)
        client.connect()
        client.close()
        client.close()  # second close on already-closed — must not raise


def test_connect_is_idempotent():
    """connect() on already-open connection is a no-op."""
    with fake_server({"foo": "bar"}) as srv:
        client = LiquidsoapTelnetClient(host=srv.host, port=srv.port)
        try:
            client.connect()
            client.connect()
            # Still works after redundant connects.
            assert client.send_command("foo") == "bar"
        finally:
            client.close()


def test_crlf_end_sentinel():
    """Windows-built Liquidsoap may emit \\r\\nEND\\r\\n — must also parse."""

    class CRLFServer(_FakeLiquidsoapServer):
        def _serve_client(self, client: socket.socket) -> None:
            client.settimeout(2.0)
            buf = b""
            while not self._stop_flag.is_set():
                try:
                    chunk = client.recv(4096)
                except (socket.timeout, OSError):
                    return
                if not chunk:
                    return
                buf += chunk
                while b"\n" in buf:
                    line, _, buf = buf.partition(b"\n")
                    cmd = line.decode("utf-8").strip()
                    self.received.append(cmd)
                    if cmd == "quit":
                        return
                    # CRLF flavour
                    try:
                        client.sendall(b"hello\r\nEND\r\n")
                    except OSError:
                        return

    srv = CRLFServer()
    srv.start()
    try:
        client = LiquidsoapTelnetClient(host=srv.host, port=srv.port)
        try:
            assert client.send_command("anything") == "hello"
        finally:
            client.close()
    finally:
        srv.stop()


def test_recording_set_path_wrapper():
    """
    recording_set_path() sends `var.set recording_path = <path>` —
    UNquoted.  Liquidsoap's telnet var.set parser eats the rest of
    the line raw and does NOT strip surrounding quotes; passing
    `"path"` lands the literal quote characters in the variable and
    causes mkdir(`"C`) to fail at file-open time.
    """
    expected = 'var.set recording_path = C:/rastatime/recordings/2026-05-27/foo.mp3'
    with fake_server({expected: ""}) as srv:
        client = LiquidsoapTelnetClient(host=srv.host, port=srv.port)
        try:
            client.recording_set_path(
                "C:/rastatime/recordings/2026-05-27/foo.mp3"
            )
            assert srv.received == [expected]
        finally:
            client.close()


def test_recording_set_path_rejects_special_chars():
    """
    Path with backslash / double-quote / newline / carriage-return
    is REJECTED with a clear ValueError — these characters would
    silently break the telnet wire form (the value would land
    misparsed inside the recording_path variable + cause weird
    downstream filesystem failures).  Callers must pre-sanitize the
    show name to safe forward-slash + ASCII-ish chars.
    """
    import pytest
    client = LiquidsoapTelnetClient()
    for bad in (
        r'C:\with"quote.mp3',
        r'C:\backslash\path.mp3',
        "C:/with\nnewline.mp3",
        "C:/with\rcarriage.mp3",
    ):
        with pytest.raises(ValueError, match="wire form"):
            client.recording_set_path(bad)


def test_recording_start_wrapper():
    """recording_start() sends the bare `recording.start` server command."""
    with fake_server({"recording.start": "Done"}) as srv:
        client = LiquidsoapTelnetClient(host=srv.host, port=srv.port)
        try:
            assert client.recording_start() == "Done"
            assert srv.received == ["recording.start"]
        finally:
            client.close()


def test_recording_stop_wrapper():
    """recording_stop() sends the bare `recording.stop` server command."""
    with fake_server({"recording.stop": "Done"}) as srv:
        client = LiquidsoapTelnetClient(host=srv.host, port=srv.port)
        try:
            assert client.recording_stop() == "Done"
            assert srv.received == ["recording.stop"]
        finally:
            client.close()


def test_recording_status_wrapper():
    """recording_status() sends the bare `recording.status` server command."""
    with fake_server({"recording.status": "on"}) as srv:
        client = LiquidsoapTelnetClient(host=srv.host, port=srv.port)
        try:
            assert client.recording_status() == "on"
            assert srv.received == ["recording.status"]
        finally:
            client.close()


# ---- Phase E — webstream lifecycle wrappers ---------------------


def test_webstream_set_url_wrapper():
    """
    webstream_set_url() sends `webstream.url <url>` — the input.http
    OCaml ``set_url`` method exposes as the server-command ``url`` with
    optional argument (no arg = get, with arg = set).  Phase E reality-
    test 2026-05-29 caught this: the earlier wire-form
    ``webstream.set_url <url>`` was a guess and got silently rejected
    as "unknown command" by Liquidsoap.
    """
    url = "http://stream.live.vc.bbcmedia.co.uk/world_service_b2b_04"
    expected = f"webstream.url {url}"
    with fake_server({expected: "Done"}) as srv:
        client = LiquidsoapTelnetClient(host=srv.host, port=srv.port)
        try:
            assert client.webstream_set_url(url) == "Done"
            assert srv.received == [expected]
        finally:
            client.close()


def test_webstream_set_url_rejects_special_chars():
    """
    URL with double-quote / newline / carriage-return is REJECTED
    with a clear ValueError — these characters would silently break
    the telnet wire form (the value would land misparsed inside
    Liquidsoap's set_url string).
    """
    import pytest
    client = LiquidsoapTelnetClient()
    for bad in (
        'http://example.com/with"quote',
        "http://example.com/with\nnewline",
        "http://example.com/with\rcarriage",
    ):
        with pytest.raises(ValueError, match="wire form"):
            client.webstream_set_url(bad)


def test_webstream_set_gain_wrapper():
    """
    webstream_set_gain(factor) sends `var.set webstream.gain = <factor>`
    — interactive.float variables in Liquidsoap 2.4 are settable only
    via the global `var.set` command, NOT a `<name>.set` shortcut.
    Phase E reality-test 2026-05-29 caught this: the earlier wire-form
    ``webstream.gain.set <factor>`` was a guess and got silently
    rejected.  Pypo has already converted dB→linear before calling.
    """
    expected = "var.set webstream.gain = 1.412"
    with fake_server({expected: "Done"}) as srv:
        client = LiquidsoapTelnetClient(host=srv.host, port=srv.port)
        try:
            assert client.webstream_set_gain(1.412) == "Done"
            assert srv.received == [expected]
        finally:
            client.close()


def test_webstream_set_gain_unity_default_renders_explicitly():
    """A factor of 1.0 (unity) renders as `1.0`, not `1` — Liquidsoap-friendly float literal."""
    expected = "var.set webstream.gain = 1.0"
    with fake_server({expected: "Done"}) as srv:
        client = LiquidsoapTelnetClient(host=srv.host, port=srv.port)
        try:
            client.webstream_set_gain(1.0)
            assert srv.received == [expected]
        finally:
            client.close()


def test_webstream_start_wrapper():
    """webstream_start() sends the bare `webstream.start` server command."""
    with fake_server({"webstream.start": "Done"}) as srv:
        client = LiquidsoapTelnetClient(host=srv.host, port=srv.port)
        try:
            assert client.webstream_start() == "Done"
            assert srv.received == ["webstream.start"]
        finally:
            client.close()


def test_webstream_stop_wrapper():
    """webstream_stop() sends the bare `webstream.stop` server command."""
    with fake_server({"webstream.stop": "Done"}) as srv:
        client = LiquidsoapTelnetClient(host=srv.host, port=srv.port)
        try:
            assert client.webstream_stop() == "Done"
            assert srv.received == ["webstream.stop"]
        finally:
            client.close()


def test_webstream_status_wrapper():
    """webstream_status() returns Liquidsoap's free-text status."""
    with fake_server({"webstream.status": "connected http://example.com"}) as srv:
        client = LiquidsoapTelnetClient(host=srv.host, port=srv.port)
        try:
            assert client.webstream_status() == "connected http://example.com"
            assert srv.received == ["webstream.status"]
        finally:
            client.close()


def test_webstream_url_wrapper():
    """webstream_url() returns the currently-set URL."""
    with fake_server({"webstream.url": "http://example.com/stream"}) as srv:
        client = LiquidsoapTelnetClient(host=srv.host, port=srv.port)
        try:
            assert client.webstream_url() == "http://example.com/stream"
            assert srv.received == ["webstream.url"]
        finally:
            client.close()


def test_empty_response_crlf():
    """Empty response with CRLF — server sends just END\\r\\n."""

    class EmptyCRLFServer(_FakeLiquidsoapServer):
        def _serve_client(self, client: socket.socket) -> None:
            client.settimeout(2.0)
            buf = b""
            while not self._stop_flag.is_set():
                try:
                    chunk = client.recv(4096)
                except (socket.timeout, OSError):
                    return
                if not chunk:
                    return
                buf += chunk
                while b"\n" in buf:
                    line, _, buf = buf.partition(b"\n")
                    cmd = line.decode("utf-8").strip()
                    self.received.append(cmd)
                    if cmd == "quit":
                        return
                    try:
                        client.sendall(b"END\r\n")
                    except OSError:
                        return

    srv = EmptyCRLFServer()
    srv.start()
    try:
        client = LiquidsoapTelnetClient(host=srv.host, port=srv.port)
        try:
            assert client.send_command("any") == ""
        finally:
            client.close()
    finally:
        srv.stop()
