"""
backend.rastatime_worker — Windows-native background task runner.

Replaces the Celery-based ``libretime_worker`` (see ``BASELINE_MODULES.md``
§1.6) with a lightweight, dependency-free runner that executes all periodic
and startup tasks using Python's standard :mod:`threading` and
:mod:`sched` modules.

Phase 8 task map
----------------
T16.1  Job inventory (this package's ``jobs/`` sub-package)
T16.2  Background runner (``runner.py``)           ← this module
T16.3  Task implementations ported from ``libretime_worker/tasks.py``
"""

from .runner import BackgroundRunner

__all__ = ["BackgroundRunner"]
