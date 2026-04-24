"""
T2.5 validation — ServiceHealth interface.

Verifies that:
1. HealthStatus values are correct.
2. ComponentHealth and SystemHealth dataclasses have correct defaults.
3. to_dict() output matches the documented JSON shape.
4. SystemHealth.from_components() aggregates worst-case status correctly.
5. ServiceHealth cannot be instantiated directly or as incomplete subclass.
6. A complete concrete stub works correctly.
"""

import pytest
from datetime import datetime, timezone

from infra.service_health.interface import (
    ComponentHealth,
    HealthStatus,
    ServiceHealth,
    SystemHealth,
)


# ---------------------------------------------------------------------------
# HealthStatus
# ---------------------------------------------------------------------------

def test_health_status_values():
    values = {s.value for s in HealthStatus}
    assert values == {"healthy", "degraded", "unhealthy"}


# ---------------------------------------------------------------------------
# ComponentHealth
# ---------------------------------------------------------------------------

def test_component_health_defaults():
    ch = ComponentHealth(name="playout_engine", status=HealthStatus.HEALTHY)
    assert ch.message is None
    assert isinstance(ch.checked_at, datetime)
    assert ch.checked_at.tzinfo is not None  # must be tz-aware
    assert ch.metadata == {}


def test_component_health_to_dict_shape():
    ch = ComponentHealth(
        name="job_runner",
        status=HealthStatus.DEGRADED,
        message="queue backing up",
        metadata={"queue_depth": 42},
    )
    d = ch.to_dict()
    assert d["name"] == "job_runner"
    assert d["status"] == "degraded"
    assert d["message"] == "queue backing up"
    assert d["metadata"] == {"queue_depth": 42}
    assert isinstance(d["checked_at"], str)
    # ISO-8601 round-trip
    dt = datetime.fromisoformat(d["checked_at"])
    assert dt.tzinfo is not None


def test_component_health_to_dict_null_message():
    ch = ComponentHealth(name="audio", status=HealthStatus.HEALTHY)
    assert ch.to_dict()["message"] is None


# ---------------------------------------------------------------------------
# SystemHealth
# ---------------------------------------------------------------------------

def test_system_health_defaults():
    sh = SystemHealth(status=HealthStatus.HEALTHY)
    assert sh.components == []
    assert sh.version == ""
    assert isinstance(sh.checked_at, datetime)


def test_system_health_to_dict_shape():
    ch = ComponentHealth(name="playout_engine", status=HealthStatus.HEALTHY)
    sh = SystemHealth(status=HealthStatus.HEALTHY, components=[ch], version="0.1.9")
    d = sh.to_dict()
    assert d["status"] == "healthy"
    assert d["version"] == "0.1.9"
    assert isinstance(d["checked_at"], str)
    assert len(d["components"]) == 1
    assert d["components"][0]["name"] == "playout_engine"


# ---------------------------------------------------------------------------
# SystemHealth.from_components — aggregation logic
# ---------------------------------------------------------------------------

def test_aggregate_all_healthy():
    components = [
        ComponentHealth("a", HealthStatus.HEALTHY),
        ComponentHealth("b", HealthStatus.HEALTHY),
    ]
    sh = SystemHealth.from_components(components, version="1.0")
    assert sh.status is HealthStatus.HEALTHY
    assert len(sh.components) == 2
    assert sh.version == "1.0"


def test_aggregate_one_degraded():
    components = [
        ComponentHealth("a", HealthStatus.HEALTHY),
        ComponentHealth("b", HealthStatus.DEGRADED),
    ]
    sh = SystemHealth.from_components(components)
    assert sh.status is HealthStatus.DEGRADED


def test_aggregate_one_unhealthy_overrides_degraded():
    components = [
        ComponentHealth("a", HealthStatus.DEGRADED),
        ComponentHealth("b", HealthStatus.UNHEALTHY),
        ComponentHealth("c", HealthStatus.HEALTHY),
    ]
    sh = SystemHealth.from_components(components)
    assert sh.status is HealthStatus.UNHEALTHY


def test_aggregate_empty_components():
    sh = SystemHealth.from_components([])
    assert sh.status is HealthStatus.HEALTHY
    assert sh.components == []


# ---------------------------------------------------------------------------
# Instantiation guards
# ---------------------------------------------------------------------------

def test_abstract_service_health_cannot_be_instantiated():
    with pytest.raises(TypeError):
        ServiceHealth()  # type: ignore[abstract]


def test_incomplete_subclass_cannot_be_instantiated():
    class Incomplete(ServiceHealth):
        pass

    with pytest.raises(TypeError):
        Incomplete()


# ---------------------------------------------------------------------------
# Minimal concrete stub
# ---------------------------------------------------------------------------

class _StubHealth(ServiceHealth):
    def __init__(self, name: str, status: HealthStatus = HealthStatus.HEALTHY):
        self._name = name
        self._status = status

    def check_health(self) -> ComponentHealth:
        return ComponentHealth(name=self._name, status=self._status)

    def is_alive(self) -> bool:
        return self._status is not HealthStatus.UNHEALTHY

    def is_ready(self) -> bool:
        return self._status is HealthStatus.HEALTHY


def test_stub_can_be_instantiated():
    stub = _StubHealth("test_component")
    assert stub is not None


def test_stub_check_health_healthy():
    stub = _StubHealth("playout_engine", HealthStatus.HEALTHY)
    ch = stub.check_health()
    assert ch.status is HealthStatus.HEALTHY
    assert ch.name == "playout_engine"


def test_stub_check_health_unhealthy():
    stub = _StubHealth("job_runner", HealthStatus.UNHEALTHY)
    ch = stub.check_health()
    assert ch.status is HealthStatus.UNHEALTHY


def test_stub_liveness_probe():
    assert _StubHealth("x", HealthStatus.HEALTHY).is_alive() is True
    assert _StubHealth("x", HealthStatus.DEGRADED).is_alive() is True
    assert _StubHealth("x", HealthStatus.UNHEALTHY).is_alive() is False


def test_stub_readiness_probe():
    assert _StubHealth("x", HealthStatus.HEALTHY).is_ready() is True
    assert _StubHealth("x", HealthStatus.DEGRADED).is_ready() is False
    assert _StubHealth("x", HealthStatus.UNHEALTHY).is_ready() is False


def test_system_health_from_stubs():
    stubs = [
        _StubHealth("playout_engine", HealthStatus.HEALTHY),
        _StubHealth("job_runner", HealthStatus.DEGRADED),
    ]
    components = [s.check_health() for s in stubs]
    sh = SystemHealth.from_components(components, version="0.1.9")
    assert sh.status is HealthStatus.DEGRADED
    d = sh.to_dict()
    assert d["status"] == "degraded"
    assert len(d["components"]) == 2
