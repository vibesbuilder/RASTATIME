"""
T10.1 — SoutBuilder unit tests.

Verifies that SoutBuilder produces correct libVLC sout chain strings for all
supported codecs without requiring VLC to be installed.

Test inventory
--------------
1.  MP3 chain contains correct acodec, bitrate, mux, and destination.
2.  OGG Vorbis chain uses acodec=vorb, mux=ogg.
3.  "ogg" is an alias for "vorbis".
4.  Opus chain uses samplerate=48000 (not 44100).
5.  AAC chain uses acodec=mp4a, mux=mp4.
6.  Unsupported codec raises ValueError.
7.  Destination string: username defaults to "source" when blank.
8.  Destination string: mount gets leading "/" if missing.
9.  supported_codecs() returns a sorted list.
10. for_multi_output() with one output delegates to for_output().
11. for_multi_output() with two outputs produces duplicate{} chain.
12. for_multi_output() with empty list raises ValueError.
13. Chain starts with "#transcode{" for single output.
14. Bitrate is embedded in the chain string.
15. Password may be empty string.
"""

import pytest

from streams.egress import StreamOutput, SoutBuilder
from streams._types import StreamProtocol


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _output(
    codec: str = "mp3",
    bitrate: int = 128,
    username: str = "source",
    password: str = "hackme",
    url: str = "stream.example.com",
    port: int = 8000,
    mount: str = "/live",
) -> StreamOutput:
    return StreamOutput(
        id="o1",
        name="Test Output",
        protocol=StreamProtocol.ICECAST,
        url=url,
        port=port,
        mount=mount,
        username=username,
        password=password,
        bitrate=bitrate,
        codec=codec,
    )


# ---------------------------------------------------------------------------
# 1–5  Per-codec chain format
# ---------------------------------------------------------------------------

def test_mp3_chain_acodec_and_mux():
    chain = SoutBuilder.for_output(_output(codec="mp3"))
    assert "acodec=mp3" in chain
    assert "mux=dummy" in chain


def test_mp3_chain_samplerate_44100():
    chain = SoutBuilder.for_output(_output(codec="mp3"))
    assert "samplerate=44100" in chain


def test_mp3_chain_channels_2():
    chain = SoutBuilder.for_output(_output(codec="mp3"))
    assert "channels=2" in chain


def test_vorbis_chain_acodec_and_mux():
    chain = SoutBuilder.for_output(_output(codec="vorbis"))
    assert "acodec=vorb" in chain
    assert "mux=ogg" in chain


def test_ogg_alias_produces_vorbis_chain():
    chain_ogg = SoutBuilder.for_output(_output(codec="ogg"))
    chain_vorbis = SoutBuilder.for_output(_output(codec="vorbis"))
    assert chain_ogg == chain_vorbis


def test_opus_chain_samplerate_48000():
    chain = SoutBuilder.for_output(_output(codec="opus"))
    assert "acodec=opus" in chain
    assert "samplerate=48000" in chain
    assert "mux=ogg" in chain


def test_aac_chain_acodec_and_mux():
    chain = SoutBuilder.for_output(_output(codec="aac"))
    assert "acodec=mp4a" in chain
    assert "mux=mp4" in chain


# ---------------------------------------------------------------------------
# 6  Invalid codec
# ---------------------------------------------------------------------------

def test_unsupported_codec_raises_value_error():
    with pytest.raises(ValueError, match="Unsupported codec"):
        SoutBuilder.for_output(_output(codec="flac"))


def test_unsupported_codec_error_mentions_supported():
    with pytest.raises(ValueError, match="mp3"):
        SoutBuilder.for_output(_output(codec="wav"))


# ---------------------------------------------------------------------------
# 7–8  Destination string rules
# ---------------------------------------------------------------------------

def test_dst_defaults_username_to_source():
    chain = SoutBuilder.for_output(_output(codec="mp3", username=""))
    assert "source:" in chain


def test_dst_uses_custom_username():
    chain = SoutBuilder.for_output(_output(codec="mp3", username="admin"))
    assert "admin:" in chain


def test_dst_mount_gains_leading_slash():
    chain = SoutBuilder.for_output(_output(codec="mp3", mount="live"))
    assert "/live" in chain


def test_dst_mount_with_leading_slash_unchanged():
    chain = SoutBuilder.for_output(_output(codec="mp3", mount="/main"))
    # Should not become "//main"
    assert "//main" not in chain
    assert "/main" in chain


def test_dst_includes_host_and_port():
    chain = SoutBuilder.for_output(
        _output(codec="mp3", url="icecast.local", port=8765)
    )
    assert "icecast.local:8765" in chain


def test_dst_empty_password_allowed():
    chain = SoutBuilder.for_output(_output(codec="mp3", password=""))
    # Destination format: user:password@host — empty password is "user:@host"
    assert ":@" in chain


# ---------------------------------------------------------------------------
# 9  supported_codecs()
# ---------------------------------------------------------------------------

def test_supported_codecs_is_sorted_list():
    codecs = SoutBuilder.supported_codecs()
    assert codecs == sorted(codecs)


def test_supported_codecs_includes_mp3_vorbis():
    codecs = SoutBuilder.supported_codecs()
    assert "mp3" in codecs
    assert "vorbis" in codecs


# ---------------------------------------------------------------------------
# 10–12  for_multi_output()
# ---------------------------------------------------------------------------

def test_multi_output_single_delegates_to_for_output():
    o = _output(codec="mp3")
    assert SoutBuilder.for_multi_output([o]) == SoutBuilder.for_output(o)


def test_multi_output_two_produces_duplicate_chain():
    o1 = StreamOutput(
        id="o1", name="MP3", protocol=StreamProtocol.ICECAST,
        url="ice.local", port=8000, mount="/mp3",
        username="source", password="pw", bitrate=128, codec="mp3",
    )
    o2 = StreamOutput(
        id="o2", name="OGG", protocol=StreamProtocol.ICECAST,
        url="ice.local", port=8000, mount="/ogg",
        username="source", password="pw", bitrate=128, codec="vorbis",
    )
    chain = SoutBuilder.for_multi_output([o1, o2])
    assert chain.startswith("#duplicate{")
    assert "dst=" in chain
    assert "acodec=mp3" in chain
    assert "acodec=vorb" in chain


def test_multi_output_empty_raises_value_error():
    with pytest.raises(ValueError, match="empty"):
        SoutBuilder.for_multi_output([])


# ---------------------------------------------------------------------------
# 13–15  Chain format invariants
# ---------------------------------------------------------------------------

def test_single_output_chain_starts_with_hash_transcode():
    chain = SoutBuilder.for_output(_output(codec="mp3"))
    assert chain.startswith("#transcode{")


def test_bitrate_is_embedded_in_chain():
    chain = SoutBuilder.for_output(_output(codec="mp3", bitrate=192))
    assert "ab=192" in chain


def test_chain_contains_access_shout():
    chain = SoutBuilder.for_output(_output(codec="mp3"))
    assert "access=shout" in chain
