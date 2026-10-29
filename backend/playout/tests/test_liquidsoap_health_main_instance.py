"""
RASTATIME 2026-09-09 - two liquidsoap.exe run since the standby source:
the process probe reports each instance's script and callers judge only
the main instance (rastatime.liq) instead of "the oldest process" (which
had silently become the standby).
"""
from __future__ import annotations

from types import SimpleNamespace

from rastatime_playout import liquidsoap_health as lh

MAIN = lh.ProcessInfo(14516, 125.0, 5313.0, "C:\\Tools\\liquidsoap\\rastatime.liq")
STANDBY = lh.ProcessInfo(4348, 78.0, 12954.0, "C:\\Tools\\liquidsoap\\standby.liq")


def _runner(stdout):
    def run(argv, **kwargs):
        return SimpleNamespace(returncode=0, stderr="", stdout=stdout)
    return run


def test_query_parses_the_script_column_including_paths_with_spaces():
    infos = lh.liquidsoap_process_info(runner=_runner(
        "4348 78 12954 C:\\Tools\\liquidsoap\\standby.liq\n"
        "14516 125 5313 C:\\Tools\\liquidsoap\\rastatime.liq\n"
        "777 50 10 C:\\Program Files\\x\\replica.liq\n"
        "garbage line\n"
    ))
    assert infos == [
        STANDBY, MAIN,
        lh.ProcessInfo(777, 50.0, 10.0, "C:\\Program Files\\x\\replica.liq"),
    ]


def test_three_column_lines_still_parse_without_script():
    infos = lh.liquidsoap_process_info(runner=_runner("9064 200 5000\n"))
    assert infos == [lh.ProcessInfo(9064, 200.0, 5000.0)]
    assert infos[0].script == ""


def test_main_instances_prefers_the_main_script_over_the_older_standby():
    assert lh.main_instances([STANDBY, MAIN]) == [MAIN]
    assert lh.main_instances([MAIN, STANDBY]) == [MAIN]


def test_main_instances_without_script_info_keeps_every_process():
    a, b = lh.ProcessInfo(1, 1.0, 10.0), lh.ProcessInfo(2, 1.0, 20.0)
    assert lh.main_instances([a, b]) == [a, b]


def test_main_instances_drops_named_non_main_processes_but_keeps_unnamed():
    unnamed = lh.ProcessInfo(3, 1.0, 5.0)
    assert lh.main_instances([STANDBY, unnamed]) == [unnamed]
    assert lh.main_instances([STANDBY]) == []


def test_main_instances_tolerates_objects_without_a_script_attribute():
    plain = SimpleNamespace(pid=1, private_mb=1.0, age_seconds=10.0)
    assert lh.main_instances([plain]) == [plain]


def test_main_instances_empty():
    assert lh.main_instances([]) == []
    assert lh.main_instances(None) == []


def test_main_script_name_follows_the_config_path_env(monkeypatch):
    monkeypatch.setenv(lh.MAIN_SCRIPT_ENV, "D:/x/Custom.LIQ")
    assert lh.main_script_name() == "custom.liq"
    custom = lh.ProcessInfo(5, 1.0, 1.0, "D:\\x\\Custom.LIQ")
    assert lh.main_instances([STANDBY, custom]) == [custom]
    monkeypatch.delenv(lh.MAIN_SCRIPT_ENV)
    assert lh.main_script_name() == "rastatime.liq"
    assert lh.main_instances([STANDBY, custom], script_name="custom.liq") == [custom]
