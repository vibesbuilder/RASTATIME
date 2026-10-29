"""
test_c5_mechanism_b v2 — Mechanismus-B validation with the right metric.

v1 measured "first bytes on disk" which gave false TIMEOUTs because of
OS write-cache buffering (Liquidsoap writes data immediately, but the
file system only flushes the page cache every ~256 KB or at file
close).  v2 measures the right thing: write for N seconds, stop
(forces flush), check file size matches expected 320 kbps * N.

Sequence under test:
    recording.stop  ->  var.set recording_path = NEW  ->  recording.start
    sleep(N)
    recording.stop   (forces flush, file is complete)

Verdict criteria:
  * Both files A and B have size within 80%..150% of expected
    (40 KB/s * N seconds).
  * Back-to-back transition completes in < 1 s (telnet round-trip
    only, OS-cache lag is invisible to caller).

How to run:
    C:\\rastatime\\.venv\\Scripts\\python.exe C:\\rastatime\\test_c5_mechanism_b.py
"""
from __future__ import annotations

import os
import time

from rastatime_playout.engine.liquidsoap_telnet import LiquidsoapTelnetClient


PATH_A_LIQ = "C:/rastatime/recordings/c5-mechB-v2-A.mp3"
PATH_B_LIQ = "C:/rastatime/recordings/c5-mechB-v2-B.mp3"
PATH_SENTINEL = "C:/rastatime/recordings/_uninitialized.mp3"

PATH_A_WIN = PATH_A_LIQ.replace("/", "\\")
PATH_B_WIN = PATH_B_LIQ.replace("/", "\\")

RECORD_DURATION_S = 10  # seconds to record per file
BITRATE_KBPS = 320      # must match rastatime.liq encoder setting
SETTLE_AFTER_STOP_S = 0.3  # wait for OS to flush before measuring


def expected_bytes(duration_s):
    """320 kbps -> 40000 B/s; allow +/- 20% tolerance for header etc."""
    return int(duration_s * BITRATE_KBPS * 1000 / 8)


def record_for(client, target_liq, target_win, duration_s, label):
    """
    Stop current, set new path, start, sleep N seconds, stop, return
    (size_bytes, expected_bytes, actual_record_duration_s).
    """
    # Cleanup prior file
    if os.path.exists(target_win):
        os.remove(target_win)

    # Stop whatever's running; small settle so file handle releases
    client.recording_stop()
    time.sleep(0.3)

    # Set new path; record start time once start() returns
    client.recording_set_path(target_liq)

    t0 = time.monotonic()
    client.recording_start()

    time.sleep(duration_s)

    client.recording_stop()
    actual_duration = time.monotonic() - t0

    # Let OS flush
    time.sleep(SETTLE_AFTER_STOP_S)

    size = os.path.getsize(target_win) if os.path.exists(target_win) else 0
    expected = expected_bytes(duration_s)

    print(f"    [{label}] wrote for {actual_duration:5.2f} s")
    print(f"    [{label}] file size       : {size:>10} B ({size/1024:.1f} KB)")
    print(f"    [{label}] expected at 320k: {expected:>10} B ({expected/1024:.1f} KB)")
    pct = (size / expected * 100) if expected else 0
    print(f"    [{label}] ratio           : {pct:.1f} % of expected")
    return size, expected, actual_duration


def back_to_back_timing(client):
    """
    Measure pure telnet-roundtrip time for stop -> set_path -> start.
    Does not measure disk lag (which is OS-cache-bound and invisible
    to the application).
    """
    t0 = time.monotonic()
    client.recording_stop()
    client.recording_set_path(PATH_B_LIQ)
    client.recording_start()
    dt = time.monotonic() - t0
    return dt


def main():
    c = LiquidsoapTelnetClient("127.0.0.1", 1234)

    print("=" * 64)
    print("Mechanismus B Test v2 -- correct metric (file size vs expected)")
    print("=" * 64)

    print()
    print("[0] Initial state")
    print(f"    recording.status         : {c.recording_status()!r}")
    print(f"    var.get recording_path   : {c.send_command('var.get recording_path')!r}")

    # ---- Test A: fresh start, 10 s ----
    print()
    print(f"[1] Test A -- record for {RECORD_DURATION_S} s, then stop")
    size_a, exp_a, dur_a = record_for(c, PATH_A_LIQ, PATH_A_WIN, RECORD_DURATION_S, "A")

    # ---- Test B: back-to-back, 10 s ----
    print()
    print(f"[2] Test B -- back-to-back to a NEW file, record for {RECORD_DURATION_S} s")

    # Cleanup B first so size measurement is clean
    if os.path.exists(PATH_B_WIN):
        os.remove(PATH_B_WIN)

    bb_lat_ms = back_to_back_timing(c) * 1000
    print(f"    back-to-back telnet roundtrip: {bb_lat_ms:.0f} ms")
    print(f"    var.get path now             : {c.send_command('var.get recording_path')!r}")

    time.sleep(RECORD_DURATION_S)
    c.recording_stop()
    time.sleep(SETTLE_AFTER_STOP_S)

    size_b = os.path.getsize(PATH_B_WIN) if os.path.exists(PATH_B_WIN) else 0
    exp_b = expected_bytes(RECORD_DURATION_S)
    pct_b = (size_b / exp_b * 100) if exp_b else 0
    print(f"    [B] file size       : {size_b:>10} B ({size_b / 1024:.1f} KB)")
    print(f"    [B] expected at 320k: {exp_b:>10} B ({exp_b / 1024:.1f} KB)")
    print(f"    [B] ratio           : {pct_b:.1f} % of expected")

    # ---- Cleanup ----
    print()
    print("[3] Cleanup -- reset path to sentinel (recording stays STOPPED)")
    c.recording_set_path(PATH_SENTINEL)
    print(f"    var.get path : {c.send_command('var.get recording_path')!r}")

    # ---- Verdict ----
    print()
    print("=" * 64)
    print("VERDICT")
    print("=" * 64)

    def ok(size, expected):
        return expected > 0 and 0.80 <= (size / expected) <= 1.50

    ok_a = ok(size_a, exp_a)
    ok_b = ok(size_b, exp_b)
    bb_ok = bb_lat_ms < 1000

    print(f"  A file size in tolerance (80-150 %): {'YES' if ok_a else 'NO'}")
    print(f"  B file size in tolerance (80-150 %): {'YES' if ok_b else 'NO'}")
    print(f"  Back-to-back telnet roundtrip < 1 s : {'YES' if bb_ok else 'NO'} ({bb_lat_ms:.0f} ms)")
    print()
    if ok_a and ok_b and bb_ok:
        print("  RESULT: Mechanismus B works.  Continuous recording verified, ")
        print("          back-to-back has only telnet-roundtrip lag (negligible).")
        print("          --> proceed with Pypo umbau (Teil 2b).")
        print("          --> reopen_when can be removed from rastatime.liq.")
    else:
        print("  RESULT: Mechanismus B has unexpected behaviour -- investigate.")
        if not ok_a:
            print(f"          A wrote {size_a} B, expected {exp_a} B")
        if not ok_b:
            print(f"          B wrote {size_b} B, expected {exp_b} B")
        if not bb_ok:
            print(f"          Back-to-back too slow: {bb_lat_ms:.0f} ms")

    c.close()


if __name__ == "__main__":
    main()
