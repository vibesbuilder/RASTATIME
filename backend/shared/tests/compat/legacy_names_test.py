"""Brand stage B bridge: the former ``libretime_*`` names resolve to ``rastatime_*``."""

import subprocess
import sys

from rastatime_shared.compat import legacy_names


def _python(*args: str) -> str:
    result = subprocess.run(
        [sys.executable, *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def test_translate() -> None:
    assert legacy_names.translate("libretime_api.core.models") == "rastatime_api.core.models"
    assert legacy_names.translate("libretime_shared") == "rastatime_shared"
    assert legacy_names.translate("libretime_api_client.v2") == "rastatime_api_client.v2"
    assert legacy_names.translate("django.conf") is None


def test_alias_returns_the_same_module_object() -> None:
    out = _python(
        "-c",
        "import libretime_shared.config._env as a, rastatime_shared.config._env as b;"
        "print(a is b, a.__spec__.name)",
    )
    assert out == "True rastatime_shared.config._env"


def test_legacy_submodule_import_goes_through_the_finder() -> None:
    out = _python(
        "-c",
        "import libretime_shared, importlib.util;"
        "spec = importlib.util.find_spec('libretime_shared.cli');"
        "print(type(spec.loader).__name__)",
    )
    assert out == "LegacyNameFinder"


def test_run_module_under_legacy_name() -> None:
    """``python -m libretime_x.y`` keeps working (service parameters)."""
    assert _python("-m", "libretime_shared.compat._probe") == "libretime_shared.compat._probe"
    assert _python("-m", "rastatime_shared.compat._probe") == "rastatime_shared.compat._probe"
