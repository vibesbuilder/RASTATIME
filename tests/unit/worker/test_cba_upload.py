"""
RASTATIME 2026-11-03 - archiving stage 2: the upload of one episode to
cba.media (backend/rastatime_worker/cba.py).  No network: a local HTTP
server stands in for the CBA in the end-to-end case.
"""

from __future__ import annotations

import io
import json
import struct
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
import requests

from backend.rastatime_worker import cba


def _episode(tmp_path, **kw) -> cba.Episode:
    audio = tmp_path / "rec.mp3"
    audio.write_bytes(b"ID3" + b"\x00" * 5000)
    values = dict(
        show_name="Morning Show",
        starts_local="2026-11-02 08:00:00",
        description="First line\nsecond line\n\nNew <paragraph> & more",
        languages="de,en",
        category_id=12,
        series_id=345,
        status="publish",
        license="cc by-nc",
        tags="a, b",
        editors=("Ann", "Bo"),
        audio_path=str(audio),
        username="station",
        password="secret",
        today_local="2026-11-03",
    )
    values.update(kw)
    return cba.Episode(**values)


def test_meta_complete_episode(tmp_path):
    meta, missing = cba.build_meta(_episode(tmp_path))
    assert missing == []
    assert meta["title"] == "Morning Show 2026-11-02"
    assert (
        meta["content"]
        == "<p>First line<br />second line</p><p>New &lt;paragraph&gt; &amp; more</p>"
    )
    assert meta["languages"] == ["de", "en"]
    assert meta["production_date"] == "2026-11-02"
    assert meta["broadcast_date"] == "2026-11-02 08:00:00"
    assert meta["category_id"] == 12 and meta["series_id"] == 345
    assert meta["license"] == "cc by-nc" and meta["status"] == "publish"
    assert meta["editors"] == "Ann, Bo"
    assert meta["contains_copyright"] is False
    assert "image_license" not in meta and "image_caption" not in meta


def test_meta_falls_back_to_the_show(tmp_path):
    ep = _episode(
        tmp_path, description="", show_description="Show text", teaser="", show_teaser="Show teaser"
    )
    meta, missing = cba.build_meta(ep)
    assert missing == []
    assert meta["content"] == "<p>Show text</p>"
    assert meta["teaser"] == "Show teaser"


def test_meta_falls_back_to_the_show_name(tmp_path):
    meta, missing = cba.build_meta(_episode(tmp_path, description="", show_description="  "))
    assert missing == []
    assert meta["content"] == "<p>Morning Show</p>"


def test_meta_own_values_win(tmp_path):
    ep = _episode(tmp_path, title="Special", production_date="2026-10-30", series_id=None)
    meta, _ = cba.build_meta(ep)
    assert meta["title"] == "Special"
    assert meta["production_date"] == "2026-10-30"
    assert "series_id" not in meta


def test_meta_image_fields_only_with_an_image(tmp_path):
    img = tmp_path / "pic.png"
    img.write_bytes(b"\x89PNG....")
    meta, _ = cba.build_meta(
        _episode(tmp_path, image_path=str(img), image_license="cc by", image_caption="x" * 600)
    )
    assert meta["image_license"] == "cc by"
    assert len(meta["image_caption"]) == 500


@pytest.mark.parametrize(
    ("change", "fragment"),
    [
        ({"password": ""}, "CBA account"),
        ({"description": "", "show_description": "", "show_name": ""}, "description"),
        ({"languages": ""}, "language"),
        ({"languages": "de,xx"}, "language"),
        ({"languages": "de,en,fr,it"}, "language"),
        ({"category_id": None}, "topic"),
        ({"license": ""}, "licence"),
        ({"license": "cc by-sa"}, "licence"),
        ({"production_date": "2026-11-04"}, "future"),
        ({"audio_path": "C:/nowhere/missing.mp3"}, "audio file is missing"),
        ({"already_post_id": 99}, "archived already"),
    ],
)
def test_meta_missing(tmp_path, change, fragment):
    _, missing = cba.build_meta(_episode(tmp_path, **change))
    assert any(fragment in m for m in missing), missing


def test_meta_refuses_m4a(tmp_path):
    m4a = tmp_path / "x.m4a"
    m4a.write_bytes(b"....")
    _, missing = cba.build_meta(_episode(tmp_path, audio_path=str(m4a)))
    assert any("M4A" in m for m in missing)


def _parts(body: bytes, content_type: str) -> dict[str, bytes]:
    boundary = content_type.split("boundary=")[1].encode()
    parts = {}
    for chunk in body.split(b"--" + boundary)[1:-1]:
        head, _, data = chunk.partition(b"\r\n\r\n")
        name = head.split(b'name="')[1].split(b'"')[0].decode()
        parts[name] = data[: -len(b"\r\n")]
    assert body.endswith(b"--" + boundary + b"--\r\n")
    return parts


def _assert_offsets_exact(data: bytes) -> None:
    """
    The positions inside the archive count from its first byte.  Python's
    reader forgives shifted positions, PHP's ZipArchive (cba.media) does
    not: 2026-11-03 the first real upload failed with "ZIP file couldn't be
    opened" because the archive had been written straight into the body.
    """
    eocd = data.rindex(b"PK\x05\x06")
    entries, cd_size, cd_offset = struct.unpack("<HII", data[eocd + 10 : eocd + 20])
    assert cd_offset + cd_size == eocd
    pos = cd_offset
    for _ in range(entries):
        assert data[pos : pos + 4] == b"PK\x01\x02"
        name_len, extra_len, comment_len = struct.unpack("<HHH", data[pos + 28 : pos + 34])
        (local,) = struct.unpack("<I", data[pos + 42 : pos + 46])
        assert data[local : local + 4] == b"PK\x03\x04"
        pos += 46 + name_len + extra_len + comment_len


def test_body_holds_meta_and_a_valid_zip(tmp_path):
    audio = tmp_path / "rec.mp3"
    audio.write_bytes(bytes(range(256)) * 400)
    img = tmp_path / "pic.jpeg"
    img.write_bytes(b"\xff\xd8\xff" + b"j" * 100)
    meta = {"title": "Ümlaut", "languages": ["de"]}
    body_path = tmp_path / "body.bin"
    content_type, size = cba.write_body(str(body_path), meta, str(audio), str(img))
    body = body_path.read_bytes()
    assert size == len(body)
    parts = _parts(body, content_type)
    assert json.loads(parts["meta"].decode("utf-8")) == meta
    with zipfile.ZipFile(io.BytesIO(parts["file"])) as zf:
        assert sorted(zf.namelist()) == ["audio.mp3", "image.jpg"]
        assert zf.read("audio.mp3") == audio.read_bytes()
        assert zf.read("image.jpg") == img.read_bytes()
        assert all(i.compress_type == zipfile.ZIP_STORED for i in zf.infolist())
        assert zf.testzip() is None
    _assert_offsets_exact(parts["file"])
    assert sorted(p.name for p in tmp_path.iterdir()) == ["body.bin", "pic.jpeg", "rec.mp3"]


def test_body_without_image(tmp_path):
    audio = tmp_path / "rec.ogg"
    audio.write_bytes(b"OggS" * 100)
    content_type, _ = cba.write_body(str(tmp_path / "b.bin"), {}, str(audio))
    parts = _parts((tmp_path / "b.bin").read_bytes(), content_type)
    with zipfile.ZipFile(io.BytesIO(parts["file"])) as zf:
        assert zf.namelist() == ["audio.ogg"]
    _assert_offsets_exact(parts["file"])


class _Clock:
    def __init__(self):
        self.t = 0.0
        self.slept = 0.0

    def now(self):
        return self.t

    def sleep(self, s):
        self.slept += s
        self.t += s


def test_throttle_keeps_the_rate():
    clock = _Clock()
    seen = []
    data = b"x" * 1_000_000
    reader = cba.ThrottledReader(
        io.BytesIO(data), len(data), 800, seen.append, every=2.0, clock=clock.now, sleep=clock.sleep
    )
    assert len(reader) == 1_000_000
    out = b""
    while chunk := reader.read(8192):
        out += chunk
    assert out == data and reader.sent == len(data)
    # 800 kbit/s = 100,000 bytes/s -> 10 s for 1 MB
    assert clock.slept == pytest.approx(10.0, abs=0.1)
    assert seen and seen == sorted(seen) and len(seen) >= 4


@pytest.mark.parametrize(
    ("status", "body", "kind"),
    [
        (200, '{"success":true,"post_id":745429,"attachment_ids":[1,2]}', "done"),
        (200, '{"success":false,"message":"0 media files found"}', "failed"),
        (400, '{"success":false,"message":"invalid category"}', "failed"),
        (401, '{"code":"rest_not_logged_in"}', "failed"),
        (403, "", "failed"),
        (413, "too large", "failed"),
        (429, "", "retry"),
        (503, "", "retry"),
        (500, "boom", "unclear"),
        (502, "", "unclear"),
    ],
)
def test_classify(status, body, kind):
    outcome = cba.classify(status, body)
    assert outcome.kind == kind
    if kind == "done":
        assert outcome.post_id == 745429
    if status == 400:
        assert "invalid category" in outcome.message


class _FakeResponse:
    def __init__(self, status, text):
        self.status_code = status
        self.text = text


class _FakeSession:
    """Reads ``read_first`` bytes of the body, then answers or raises."""

    def __init__(self, read_first=0, raise_exc=None, response=None):
        self.read_first = read_first
        self.raise_exc = raise_exc
        self.response = response
        self.kwargs = None

    def post(self, url, data, headers, auth, timeout):
        self.kwargs = dict(url=url, headers=headers, auth=auth, timeout=timeout)
        got = 0
        while got < self.read_first and (chunk := data.read(8192)):
            got += len(chunk)
        if self.raise_exc is not None:
            raise self.raise_exc
        return self.response


def _body(tmp_path):
    p = tmp_path / "body.bin"
    p.write_bytes(b"z" * 50_000)
    return str(p), 50_000


def test_upload_not_reached_is_retried(tmp_path):
    path, size = _body(tmp_path)
    s = _FakeSession(raise_exc=requests.exceptions.ConnectionError("refused"))
    outcome, sent = cba.upload(
        path, "multipart/form-data; boundary=b", size, "u", "p", 100000, session=s
    )
    assert (outcome.kind, sent) == ("retry", 0)


def test_upload_broken_off_is_unclear(tmp_path):
    path, size = _body(tmp_path)
    s = _FakeSession(read_first=20_000, raise_exc=requests.exceptions.ConnectionError("reset"))
    outcome, sent = cba.upload(
        path, "multipart/form-data; boundary=b", size, "u", "p", 100000, session=s
    )
    assert outcome.kind == "unclear" and sent >= 20_000


def test_upload_read_timeout_is_unclear(tmp_path):
    path, size = _body(tmp_path)
    s = _FakeSession(read_first=size, raise_exc=requests.exceptions.ReadTimeout("slow"))
    outcome, _ = cba.upload(
        path, "multipart/form-data; boundary=b", size, "u", "p", 100000, session=s
    )
    assert outcome.kind == "unclear"


def test_upload_connect_timeout_is_retried(tmp_path):
    path, size = _body(tmp_path)
    s = _FakeSession(raise_exc=requests.exceptions.ConnectTimeout("no route"))
    outcome, _ = cba.upload(
        path, "multipart/form-data; boundary=b", size, "u", "p", 100000, session=s
    )
    assert outcome.kind == "retry"


def test_upload_sends_auth_and_length(tmp_path):
    path, size = _body(tmp_path)
    s = _FakeSession(read_first=size, response=_FakeResponse(200, '{"success":true,"post_id":7}'))
    outcome, sent = cba.upload(
        path, "multipart/form-data; boundary=b", size, "user", "pw", 100000, session=s
    )
    assert (outcome.kind, outcome.post_id, sent) == ("done", 7, size)
    assert s.kwargs["auth"] == ("user", "pw")
    assert s.kwargs["headers"]["Content-Length"] == str(size)
    assert s.kwargs["url"] == cba.ZIPUPLOAD_URL


class _CbaStandIn(BaseHTTPRequestHandler):
    received: dict = {}

    def do_POST(self):  # noqa: N802
        length = int(self.headers["Content-Length"])
        body = self.rfile.read(length)
        _CbaStandIn.received = {
            "auth": self.headers.get("Authorization", ""),
            "chunked": self.headers.get("Transfer-Encoding"),
            "parts": _parts(body, self.headers["Content-Type"]),
        }
        out = b'{"success":true,"post_id":4242,"attachment_ids":[1]}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *args):  # quiet
        pass


def test_upload_end_to_end_against_a_local_server(tmp_path):
    ep = _episode(tmp_path)
    meta, missing = cba.build_meta(ep)
    assert missing == []
    body_path = str(tmp_path / "body.bin")
    content_type, size = cba.write_body(body_path, meta, ep.audio_path)
    server = HTTPServer(("127.0.0.1", 0), _CbaStandIn)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}/wp-json/cba/v1/zipupload"
        progress = []
        outcome, sent = cba.upload(
            body_path, content_type, size, "station", "secret", 1_000_000, progress.append, url=url
        )
    finally:
        server.shutdown()
    assert (outcome.kind, outcome.post_id, sent) == ("done", 4242, size)
    got = _CbaStandIn.received
    assert got["chunked"] is None  # Content-Length, no chunked upload
    assert got["auth"].startswith("Basic ")
    assert json.loads(got["parts"]["meta"]) == meta
    with zipfile.ZipFile(io.BytesIO(got["parts"]["file"])) as zf:
        assert zf.read("audio.mp3") == open(ep.audio_path, "rb").read()
