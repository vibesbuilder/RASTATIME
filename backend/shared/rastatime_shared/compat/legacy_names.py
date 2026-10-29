"""
Brand stage B bridge: import the ``rastatime_*`` packages under their former
``libretime_*`` names.

A stub package per former name (``backend/shared/libretime_api/__init__.py``
etc.) calls :func:`alias_package`.  That installs one meta path finder in
front of everything else and replaces the stub in ``sys.modules`` with the
real package, so

* ``import libretime_api.settings.prod`` returns the very same module object
  as ``import rastatime_api.settings.prod`` (Django sees each model once),
* ``python -m libretime_playout`` and ``-m libretime_api.waitress_serve``
  still start (``get_code`` hands runpy the real code object),
* pickles and ``DJANGO_SETTINGS_MODULE`` values with the former names load.

Scheduled for removal on 2026-11-03 (five days of bridge, see BACKLOG).
"""

import importlib
import importlib.abc
import importlib.machinery
import importlib.util
import sys
from types import ModuleType
from typing import Dict, Optional, Sequence

LEGACY_TO_CURRENT: Dict[str, str] = {
    "libretime_api_client": "rastatime_api_client",
    "libretime_api": "rastatime_api",
    "libretime_playout": "rastatime_playout",
    "libretime_analyzer": "rastatime_analyzer",
    "libretime_shared": "rastatime_shared",
}


def translate(fullname: str) -> Optional[str]:
    """``libretime_api.core.models`` -> ``rastatime_api.core.models`` (or None)."""
    top, sep, rest = fullname.partition(".")
    current = LEGACY_TO_CURRENT.get(top)
    if current is None:
        return None
    return current + sep + rest


def _real_spec(fullname: str) -> Optional[importlib.machinery.ModuleSpec]:
    current = translate(fullname)
    if current is None:
        return None
    try:
        return importlib.util.find_spec(current)
    except (ImportError, ValueError):
        return None


class LegacyNameFinder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Serve ``libretime_*`` imports with the already-imported ``rastatime_*`` modules."""

    def __init__(self) -> None:
        self._pending: Dict[str, Optional[importlib.machinery.ModuleSpec]] = {}

    # -- finder -----------------------------------------------------------
    def find_spec(
        self,
        fullname: str,
        path: Optional[Sequence[str]] = None,
        target: Optional[ModuleType] = None,
    ) -> Optional[importlib.machinery.ModuleSpec]:
        real = _real_spec(fullname)
        if real is None:
            return None
        spec = importlib.machinery.ModuleSpec(
            fullname,
            self,
            origin=real.origin,
            is_package=real.submodule_search_locations is not None,
        )
        if real.submodule_search_locations is not None:
            spec.submodule_search_locations = list(real.submodule_search_locations)
        spec.has_location = real.has_location
        return spec

    # -- loader -----------------------------------------------------------
    def create_module(self, spec: importlib.machinery.ModuleSpec) -> ModuleType:
        current = translate(spec.name)
        assert current is not None
        module = importlib.import_module(current)
        # module_from_spec() overwrites __spec__ with the alias spec; keep
        # the real one aside and restore it in exec_module().
        self._pending[spec.name] = getattr(module, "__spec__", None)
        return module

    def exec_module(self, module: ModuleType) -> None:
        # ``module`` is the real module (its __name__ is the current name);
        # the pending entry is keyed by the legacy name it was requested as.
        for legacy, real_spec in list(self._pending.items()):
            if translate(legacy) == module.__name__:
                del self._pending[legacy]
                if real_spec is not None:
                    module.__spec__ = real_spec
                break

    def get_code(self, fullname: str):  # type: ignore[no-untyped-def]
        """runpy (``python -m libretime_x``) support."""
        real = _real_spec(fullname)
        if real is None or real.loader is None or not hasattr(real.loader, "get_code"):
            raise ImportError(f"no code object for {fullname!r}")
        return real.loader.get_code(real.name)  # type: ignore[attr-defined]

    def get_source(self, fullname: str):  # type: ignore[no-untyped-def]
        real = _real_spec(fullname)
        if real is None or real.loader is None or not hasattr(real.loader, "get_source"):
            return None
        return real.loader.get_source(real.name)  # type: ignore[attr-defined]

    def is_package(self, fullname: str) -> bool:
        real = _real_spec(fullname)
        return bool(real is not None and real.submodule_search_locations is not None)


_FINDER: Optional[LegacyNameFinder] = None


def install() -> LegacyNameFinder:
    """Put the finder in front of ``sys.meta_path`` (idempotent)."""
    global _FINDER  # pylint: disable=global-statement
    if _FINDER is None:
        _FINDER = LegacyNameFinder()
    if _FINDER not in sys.meta_path:
        sys.meta_path.insert(0, _FINDER)
    return _FINDER


def alias_package(legacy_name: str) -> ModuleType:
    """
    Called from a stub package's ``__init__``: install the finder and make
    ``sys.modules[legacy_name]`` the real package.
    """
    current = translate(legacy_name)
    if current is None:
        raise ImportError(f"{legacy_name!r} has no current name")
    install()
    module = importlib.import_module(current)
    sys.modules[legacy_name] = module
    return module
