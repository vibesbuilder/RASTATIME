"""
RASTATIME 2026-09-05 — render contracts for the Liquidsoap memory-leak
and device-index fixes.

* the scheduled queue is the synchronous request.queue copy (no Duppy
  retry poller → no Unix.select leak on the Windows build);
* the "possible source leak" threshold is raised to 200;
* the local output block renders ``device_name=`` when the resolver
  offers a name, ``device_id=`` otherwise, and never both.
"""

from __future__ import annotations

from rastatime_playout import liquidsoap_config as lc


def _stream():
    return {
        "type": "mp3",
        "host": "localhost",
        "port": 8000,
        "mount": "verify-only",
        "pass": "x",
        "bitrate": 128,
    }


def test_scheduled_queue_is_the_synchronous_copy():
    out = lc.render_rastatime_liq([_stream()])
    assert 'scheduled_q = request.queue_sync(id="scheduled", timeout=5.0)' in out
    assert 'request.queue(id="scheduled")' not in out
    assert "def request.queue_sync(" in out
    # the ONE change against the stdlib copy
    assert "        synchronous=true,\n        available=" in out
    # the stdlib's native switch is gone (it does not exist in this build)
    body = out[out.index("def request.queue_sync(") : out.index("scheduled_q = request.queue_sync")]
    assert "native" not in body
    assert "%ifdef" not in body
    # our own flush command still targets the queue's set_queue
    assert "scheduled_q.set_queue([])" in out


def test_source_leak_warning_threshold_is_raised():
    out = lc.render_rastatime_liq([_stream()])
    assert "settings.clock.leak_warning.set(200)" in out


def test_local_output_renders_device_name_when_offered():
    out = lc._render_local_output_block(
        True,
        device_id=15,
        device_label="Tascam-Lautsprecher (US-16x08) [WASAPI]",
        endpoint_id="ep-1",
        device_name='Tascam "Studio" (US-16x08)',
    )
    assert 'device_name="Tascam \\"Studio\\" (US-16x08)",' in out
    assert "device_id=" not in out
    assert "# rastatime-main-output: ep-1" in out
    assert 'sync="auto"' in out


def test_local_output_falls_back_to_device_id_without_name():
    out = lc._render_local_output_block(
        True,
        device_id=15,
        device_label="Tascam",
        endpoint_id="ep-1",
    )
    assert "device_id=15," in out
    assert "device_name=" not in out


def test_local_output_os_default_without_id_and_name():
    out = lc._render_local_output_block(True)
    assert "rastatime-main-output: os-default" in out
    assert "device_id=" not in out and "device_name=" not in out


def test_render_passes_device_name_through():
    out = lc.render_rastatime_liq(
        [_stream()],
        local_output_enabled=True,
        local_output_device_id=3,
        local_output_device_name="Tascam-Lautsprecher (US-16x08)",
    )
    assert 'device_name="Tascam-Lautsprecher (US-16x08)",' in out
    assert "device_id=3" not in out
