"""
Tests for the Main-Output → PortAudio device resolution
(``rastatime_playout.engine.portaudio_output``) and for the
``output.portaudio`` device argument in the rendered rastatime.liq.

Background: Settings → Local Machine → **Main Output** used to have no
effect on the Liquidsoap local monitor — the value was stored, pushed
to playout, and dropped by a no-op ``set_audio_device``, while the
.liq rendered ``output.portaudio`` without any device argument.

The resolution deliberately *probes* candidates instead of picking a
host API by rule.  Measured on the studio machine 2026-09-03: the Jabra
headset opens via MME; the Tascam US-16x08 refused every host API while
its Windows shared format sat at 48 kHz, and opened via WASAPI once the
operator set it to 44.1 kHz.  These tests encode that reality with a
fake PortAudio so it cannot silently regress.
"""

import pytest

from rastatime_playout.engine.portaudio_output import (
    HOST_API_PREFERENCE,
    ResolvedOutput,
    _hardware_tokens,
    _host_api_rank,
    find_output_candidates,
    first_exact_name_match,
    resolve_output_device,
    with_name_selection,
)
from rastatime_playout.liquidsoap_config import _render_local_output_block


# --------------------------------------------------------------------
# Fake PortAudio ("sounddevice") — mirrors the real studio machine.
# --------------------------------------------------------------------

#: Host-API table as PortAudio reports it on Windows.
_APIS = [
    {"name": "MME"},
    {"name": "Windows DirectSound"},
    {"name": "Windows WASAPI"},
    {"name": "Windows WDM-KS"},
]

#: Device table taken from the real machine (2026-09-03).  Note the
#: WDM-KS entry for the Tascam carries the *driver's* wording, not the
#: Windows friendly name — that is the whole reason for the
#: hardware-token matching pass.
_DEVICES = [
    {"name": "Mikrofon (US-16x08)", "hostapi": 0,
     "max_input_channels": 16, "max_output_channels": 0},
    {"name": "Jabra-Lautsprecher (Jabra EVOLV", "hostapi": 0,
     "max_input_channels": 0, "max_output_channels": 2},
    {"name": "Tascam-Lautsprecher (US-16x08)", "hostapi": 0,
     "max_input_channels": 0, "max_output_channels": 8},
    {"name": "Tascam-Lautsprecher (US-16x08)", "hostapi": 1,
     "max_input_channels": 0, "max_output_channels": 8},
    {"name": "Tascam-Lautsprecher (US-16x08)", "hostapi": 2,
     "max_input_channels": 0, "max_output_channels": 2},
    {"name": "Lautsprecher (US-16x08 Audio)", "hostapi": 3,
     "max_input_channels": 0, "max_output_channels": 8},
]

TASCAM_MME, TASCAM_DS, TASCAM_WASAPI, TASCAM_WDMKS = 2, 3, 4, 5
JABRA_MME = 1


class FakeStream:
    """``write_ok=False`` models an endpoint that opens fine and only
    refuses once data is pushed through the blocking path — exactly how
    DirectSound behaves on the Tascam."""

    def __init__(self, ok, write_ok=True):
        self._write_ok = write_ok
        if not ok:
            raise RuntimeError("Unanticipated host error")

    def start(self):
        pass

    def write(self, data):
        if not self._write_ok:
            raise RuntimeError("DirectSound error")

    def stop(self):
        pass

    def close(self):
        pass


class FakeSD:
    """Minimal sounddevice stand-in; ``openable`` are the indices that
    actually accept an output open."""

    def __init__(self, openable, writable=None, fail_messages=None):
        self.openable = set(openable)
        # Default: whatever opens can also be written to.
        self.writable = set(openable if writable is None else writable)
        # Per-index error text for refused opens (default: generic).
        self.fail_messages = dict(fail_messages or {})
        self.attempted = []

    def query_hostapis(self):
        return _APIS

    def query_devices(self):
        return _DEVICES

    def RawOutputStream(self, **kwargs):  # noqa: N802 (sounddevice API)
        index = kwargs["device"]
        self.attempted.append(index)
        assert "callback" not in kwargs, (
            "the probe must use PortAudio's BLOCKING api - a callback-mode "
            "probe reports WDM-KS as working and then kills liquidsoap at "
            "device-open (RASTATIME 2026-09-03 outage)"
        )
        if index not in self.openable and index in self.fail_messages:
            raise RuntimeError(self.fail_messages[index])
        return FakeStream(index in self.openable, index in self.writable)


@pytest.fixture
def fake_sd_factory(monkeypatch):
    """Install a FakeSD so ``resolve_output_device`` imports it."""

    def _install(openable, writable=None, fail_messages=None):
        fake = FakeSD(openable, writable, fail_messages)
        import sys
        monkeypatch.setitem(sys.modules, "sounddevice", fake)
        return fake

    return _install


# --------------------------------------------------------------------
# Rendering by name (RASTATIME 2026-09-05 — index drift)
# --------------------------------------------------------------------

TASCAM_NAME = "Tascam-Lautsprecher (US-16x08)"


def test_first_exact_name_match_is_the_mme_entry():
    """PortAudio lists MME first; a <= 31-char name lands there —
    exactly what Liquidsoap's device_name= opens."""
    sd = FakeSD(openable=[TASCAM_MME])
    assert first_exact_name_match(TASCAM_NAME, sd) == (TASCAM_MME, "MME", 8)
    assert first_exact_name_match("nope", sd) is None
    # substring is NOT a match (measured on the real binary)
    assert first_exact_name_match("Tascam", sd) is None


def test_by_name_when_the_mme_entry_opens():
    sd = FakeSD(openable=[TASCAM_WASAPI, TASCAM_MME])
    resolved = ResolvedOutput(TASCAM_WASAPI, TASCAM_NAME, "Windows WASAPI", True)
    out = with_name_selection(resolved, sd)
    assert out.by_name == TASCAM_NAME
    assert out.index == TASCAM_WASAPI          # the index path is kept as comment/fallback
    assert TASCAM_MME in sd.attempted          # the entry the name selects was probed


def test_no_name_when_the_mme_entry_refuses():
    sd = FakeSD(openable=[TASCAM_WASAPI])
    resolved = ResolvedOutput(TASCAM_WASAPI, TASCAM_NAME, "Windows WASAPI", True)
    assert with_name_selection(resolved, sd).by_name is None


def test_no_name_when_the_first_match_is_directsound():
    """A friendly name longer than 31 characters cannot match the MME
    entry, so the first match is DirectSound — whose blocking write is
    a silent stub.  Keep the index."""
    long_name = "Realtek-Lautsprecher (Realtek(R) Audio)"

    class LongNameSD(FakeSD):
        def query_devices(self):
            return [
                {"name": "Realtek-Lautsprecher (Realtek(R", "hostapi": 0,
                 "max_input_channels": 0, "max_output_channels": 2},
                {"name": long_name, "hostapi": 1,
                 "max_input_channels": 0, "max_output_channels": 2},
                {"name": long_name, "hostapi": 2,
                 "max_input_channels": 0, "max_output_channels": 2},
            ]

    sd = LongNameSD(openable=[1, 2])
    assert first_exact_name_match(long_name, sd) == (1, "Windows DirectSound", 2)
    resolved = ResolvedOutput(2, long_name, "Windows WASAPI", True)
    assert with_name_selection(resolved, sd).by_name is None


def test_no_name_when_the_first_match_is_an_input():
    class InputFirstSD(FakeSD):
        def query_devices(self):
            return [
                {"name": "Same Name", "hostapi": 0,
                 "max_input_channels": 2, "max_output_channels": 0},
                {"name": "Same Name", "hostapi": 2,
                 "max_input_channels": 0, "max_output_channels": 2},
            ]

    sd = InputFirstSD(openable=[1])
    resolved = ResolvedOutput(1, "Same Name", "Windows WASAPI", True)
    assert with_name_selection(resolved, sd).by_name is None


def test_resolve_output_device_offers_the_name(fake_sd_factory):
    fake_sd_factory(openable=[TASCAM_WASAPI, TASCAM_MME])
    resolved = resolve_output_device(TASCAM_NAME)
    assert resolved is not None
    assert resolved.index == TASCAM_WASAPI
    assert resolved.by_name == TASCAM_NAME


def test_resolve_output_device_without_probe_still_checks_host_api(fake_sd_factory):
    fake_sd_factory(openable=[])
    resolved = resolve_output_device(TASCAM_NAME, probe=False)
    assert resolved is not None
    assert resolved.by_name == TASCAM_NAME     # MME entry, no probe requested


# --------------------------------------------------------------------
# Candidate discovery
# --------------------------------------------------------------------

def test_hardware_tokens_extract_model_not_generic_words():
    tokens = _hardware_tokens(["Tascam-Lautsprecher (US-16x08)"])
    assert "us-16x08" in tokens
    # "Audio"/"Lautsprecher" must not become tokens or they'd match
    # half the system.
    assert all(any(c.isdigit() for c in t) for t in tokens)


def test_host_api_rank_orders_wdmks_last():
    ranks = [_host_api_rank(api) for api in
             ("Windows WASAPI", "MME", "Windows DirectSound", "Windows WDM-KS")]
    assert ranks == sorted(ranks)
    assert _host_api_rank("Windows WDM-KS") == len(HOST_API_PREFERENCE) - 1


def test_candidates_include_wdmks_variant_via_hardware_token():
    """The Tascam's WDM-KS entry is named differently and would be
    missed by friendly-name matching alone; discovery must still be
    complete so every host API gets its chance."""
    found = find_output_candidates("Tascam-Lautsprecher", FakeSD([]))
    indices = [i for i, _, _ in found]
    assert TASCAM_WDMKS in indices, "WDM-KS variant must be discovered"
    assert set(indices) == {TASCAM_MME, TASCAM_DS, TASCAM_WASAPI, TASCAM_WDMKS}


def test_candidates_are_ordered_least_invasive_first():
    found = find_output_candidates("Tascam-Lautsprecher", FakeSD([]))
    assert found[0][0] == TASCAM_WASAPI, "WASAPI is tried first"
    assert found[-1][0] == TASCAM_WDMKS, "exclusive WDM-KS is the last resort"


def test_candidates_ignore_input_only_devices():
    found = find_output_candidates("Mikrofon", FakeSD([]))
    assert found == [], "a capture-only endpoint is not an output candidate"


# --------------------------------------------------------------------
# Resolution with probing
# --------------------------------------------------------------------

def test_resolve_tries_every_candidate_before_giving_up(fake_sd_factory):
    """The Tascam with its shared format at 48 kHz (measured 2026-09-03):
    no host API accepts a blocking 44.1 kHz open, so we must try all
    four and then fall back."""
    fake = fake_sd_factory([])
    assert resolve_output_device("Tascam-Lautsprecher") is None
    assert fake.attempted == [
        TASCAM_WASAPI, TASCAM_MME, TASCAM_DS, TASCAM_WDMKS
    ], "all candidates get a chance, cheapest host API first"


def test_resolve_rejects_device_that_opens_but_fails_on_write(fake_sd_factory):
    """DirectSound on the Tascam opens and only fails once audio is
    pushed.  Accepting it would hand liquidsoap a device that dies at
    the first buffer, so the probe has to write, not just open."""
    fake = fake_sd_factory([TASCAM_DS, TASCAM_WDMKS], writable=[TASCAM_WDMKS])
    resolved = resolve_output_device("Tascam-Lautsprecher")
    assert resolved is not None
    assert resolved.index == TASCAM_WDMKS, "the write-only-fails device is skipped"


def test_resolve_prefers_first_opening_candidate(fake_sd_factory):
    """The Jabra case: MME opens, so we stop there and never reach
    the exclusive WDM-KS path."""
    fake = fake_sd_factory([JABRA_MME])
    resolved = resolve_output_device("Jabra-Lautsprecher")
    assert resolved is not None
    assert resolved.index == JABRA_MME


def test_resolve_returns_none_when_nothing_opens(fake_sd_factory):
    """Falling back to None means 'render without device' — the safe
    OS-default behaviour, never a crash."""
    fake_sd_factory([])
    assert resolve_output_device("Tascam-Lautsprecher") is None


def test_resolve_returns_none_for_unknown_name(fake_sd_factory):
    fake_sd_factory([TASCAM_WDMKS])
    assert resolve_output_device("Nicht Vorhanden") is None


def test_resolve_without_probe_takes_best_ranked(fake_sd_factory):
    fake = fake_sd_factory([])
    resolved = resolve_output_device("Tascam-Lautsprecher", probe=False)
    assert resolved is not None
    assert resolved.index == TASCAM_WASAPI
    assert resolved.probed is False
    assert fake.attempted == [], "probe=False must not open anything"


# --------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------

def test_render_emits_device_id_when_resolved():
    block = _render_local_output_block(True, 28, "Lautsprecher [WDM-KS]")
    assert "device_id=28," in block
    assert "Lautsprecher [WDM-KS]" in block, "label helps the operator read the .liq"


def test_render_omits_device_id_when_unresolved():
    block = _render_local_output_block(True, None, "")
    assert "device_id" not in block
    assert "OS-default" in block


def test_render_disabled_has_no_output_call():
    block = _render_local_output_block(False, 28, "x")
    assert "output.portaudio(" not in block
    assert "device_id" not in block


def test_render_label_cannot_break_out_of_the_comment():
    """A device label is operator-controlled text landing in the .liq;
    a newline in it would inject script lines."""
    block = _render_local_output_block(True, 3, "evil\nshutdown()")
    assert "\nshutdown()" not in block
    assert "device_id=3," in block

def test_render_emits_machine_readable_endpoint_marker():
    """The Settings page reads this marker to show which output is
    REALLY active, so it must carry the Windows endpoint id — not the
    PortAudio name, which differs per host API and would produce false
    mismatches."""
    block = _render_local_output_block(True, 4, "Jabra [MME]", "abc-123")
    assert "# rastatime-main-output: abc-123" in block


def test_render_marks_os_default_when_no_device_resolved():
    block = _render_local_output_block(True, None, "", "")
    assert "# rastatime-main-output: os-default" in block


def test_render_marker_strips_hostile_endpoint_id():
    """The id reaches the .liq from the database; anything but
    id-shaped characters must not survive into the script."""
    hostile = "a b" + chr(10) + "shutdown()"
    block = _render_local_output_block(True, 4, "x", hostile)
    assert "shutdown()" not in block
    assert "# rastatime-main-output: absh" in block


def test_resolve_hints_at_windows_shared_format_on_rate_rejection(
    fake_sd_factory, caplog
):
    """A WASAPI 'Invalid sample rate' means the endpoint's Windows
    shared format is set to another rate (the Tascam sat at 48 kHz).
    The generic failure reads like a dead device, so the resolver must
    point the operator at the actual fix."""
    import logging
    fake_sd_factory(
        [], fail_messages={TASCAM_WASAPI: "Invalid sample rate [PaErrorCode -9997]"}
    )
    with caplog.at_level(logging.ERROR):
        assert resolve_output_device("Tascam-Lautsprecher") is None
    assert "shared format" in caplog.text
    assert "44100" in caplog.text
