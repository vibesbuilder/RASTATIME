"""
T15.1 — Line-In runtime activation contract unit tests.

All 20 tests are pure Python — no Django, no real audio hardware required.

Test inventory
--------------
ActivationResult (5):
  1.  ``success=True``  →  ``failed`` is ``False``.
  2.  ``success=False`` →  ``failed`` is ``True``.
  3.  ``error_message`` defaults to ``None``.
  4.  ``error_message`` is preserved when provided.
  5.  ``ActivationResult`` is immutable (frozen dataclass).

LineInRuntime ABC (3):
  6.  Cannot instantiate ``LineInRuntime`` directly (abstract).
  7.  Incomplete subclass (missing one abstract method) cannot be instantiated.
  8.  ``is_active()`` delegates correctly to ``active_ids()``.

StubLineInRuntime (9):
  9.  Can be instantiated without arguments.
 10.  ``active_ids()`` is empty on a fresh stub.
 11.  ``activate()`` returns an ``ActivationResult`` with ``success=True``.
 12.  After ``activate()``, ``is_active(id)`` returns ``True``.
 13.  After ``activate()``, ``active_ids()`` contains the line-in id.
 14.  ``deactivate()`` removes the id from ``active_ids()``.
 15.  ``deactivate()`` with an unknown id raises no exception (no-op).
 16.  ``set_fail()`` causes ``activate()`` to return ``success=False``.
 17.  Failed activation does NOT add the id to ``active_ids()``.

Registry (3):
 18.  ``default_runtime`` is ``None`` before ``connect_runtime()`` is called.
 19.  ``connect_runtime()`` sets ``default_runtime`` to the supplied instance.
 20.  ``connect_runtime()`` replaces a previously registered runtime.

(20 tests total, all runnable without Django or real audio hardware)
"""

from __future__ import annotations

import pytest

from audio.linein.domain import LineIn
from audio.linein._runtime import ActivationResult, LineInRuntime, StubLineInRuntime


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _linein(**kwargs) -> LineIn:
    defaults = dict(
        id="test-uuid-001",
        name="Drum Kit",
        device_id="dev-usb-001",
        channel_mapping=(0, 1),
        enabled=True,
        description="",
        priority=0,
    )
    defaults.update(kwargs)
    return LineIn(**defaults)


# ---------------------------------------------------------------------------
# 1–5  ActivationResult
# ---------------------------------------------------------------------------

def test_activation_result_success_failed_is_false():
    r = ActivationResult(linein_id="x", success=True)
    assert r.failed is False


def test_activation_result_failure_failed_is_true():
    r = ActivationResult(linein_id="x", success=False)
    assert r.failed is True


def test_activation_result_error_message_defaults_to_none():
    r = ActivationResult(linein_id="x", success=True)
    assert r.error_message is None


def test_activation_result_error_message_preserved():
    r = ActivationResult(linein_id="x", success=False, error_message="device busy")
    assert r.error_message == "device busy"


def test_activation_result_is_immutable():
    r = ActivationResult(linein_id="x", success=True)
    with pytest.raises((AttributeError, TypeError)):
        r.success = False   # type: ignore[misc]


# ---------------------------------------------------------------------------
# 6–8  LineInRuntime ABC
# ---------------------------------------------------------------------------

def test_linein_runtime_cannot_be_instantiated():
    with pytest.raises(TypeError):
        LineInRuntime()   # type: ignore[abstract]


def test_incomplete_subclass_cannot_be_instantiated():
    class PartialRuntime(LineInRuntime):
        def activate(self, linein):        # type: ignore[override]
            return ActivationResult(linein_id=linein.id, success=True)
        def deactivate(self, linein_id):   # type: ignore[override]
            pass
        # Missing: active_ids()

    with pytest.raises(TypeError):
        PartialRuntime()   # type: ignore[abstract]


def test_is_active_delegates_to_active_ids():
    """is_active() must return True iff linein_id is in active_ids()."""
    class MinimalRuntime(LineInRuntime):
        def activate(self, linein):
            return ActivationResult(linein_id=linein.id, success=True)
        def deactivate(self, linein_id):
            pass
        def active_ids(self) -> frozenset[str]:
            return frozenset({"present-id"})

    rt = MinimalRuntime()
    assert rt.is_active("present-id") is True
    assert rt.is_active("absent-id")  is False


# ---------------------------------------------------------------------------
# 9–17  StubLineInRuntime
# ---------------------------------------------------------------------------

def test_stub_can_be_instantiated():
    assert StubLineInRuntime() is not None


def test_stub_active_ids_empty_initially():
    rt = StubLineInRuntime()
    assert rt.active_ids() == frozenset()


def test_stub_activate_returns_success_result():
    rt  = StubLineInRuntime()
    li  = _linein()
    res = rt.activate(li)
    assert isinstance(res, ActivationResult)
    assert res.success is True
    assert res.linein_id == li.id


def test_stub_after_activate_is_active_true():
    rt = StubLineInRuntime()
    li = _linein()
    rt.activate(li)
    assert rt.is_active(li.id) is True


def test_stub_after_activate_id_in_active_ids():
    rt = StubLineInRuntime()
    li = _linein()
    rt.activate(li)
    assert li.id in rt.active_ids()


def test_stub_deactivate_removes_id():
    rt = StubLineInRuntime()
    li = _linein()
    rt.activate(li)
    rt.deactivate(li.id)
    assert li.id not in rt.active_ids()


def test_stub_deactivate_unknown_id_is_noop():
    rt = StubLineInRuntime()
    # Must not raise
    rt.deactivate("ghost-uuid-that-was-never-activated")
    assert rt.active_ids() == frozenset()


def test_stub_set_fail_causes_failure_result():
    rt = StubLineInRuntime()
    li = _linein(id="bad-uuid")
    rt.set_fail("bad-uuid")
    res = rt.activate(li)
    assert res.success is False
    assert res.failed  is True
    assert res.error_message is not None


def test_stub_failed_activation_not_in_active_ids():
    rt = StubLineInRuntime()
    li = _linein(id="bad-uuid")
    rt.set_fail("bad-uuid")
    rt.activate(li)
    assert "bad-uuid" not in rt.active_ids()


# ---------------------------------------------------------------------------
# 18–20  Registry
# ---------------------------------------------------------------------------

def test_registry_default_runtime_is_none_initially():
    import audio.linein._registry as _reg
    # Store previous value and restore after — avoid polluting other tests.
    prev = _reg.default_runtime
    _reg.default_runtime = None
    try:
        assert _reg.default_runtime is None
    finally:
        _reg.default_runtime = prev


def test_registry_connect_runtime_sets_singleton():
    import audio.linein._registry as _reg
    prev = _reg.default_runtime
    try:
        stub = StubLineInRuntime()
        _reg.connect_runtime(stub)
        assert _reg.default_runtime is stub
    finally:
        _reg.default_runtime = prev


def test_registry_connect_runtime_replaces_previous():
    import audio.linein._registry as _reg
    prev = _reg.default_runtime
    try:
        first  = StubLineInRuntime()
        second = StubLineInRuntime()
        _reg.connect_runtime(first)
        _reg.connect_runtime(second)
        assert _reg.default_runtime is second
        assert _reg.default_runtime is not first
    finally:
        _reg.default_runtime = prev
