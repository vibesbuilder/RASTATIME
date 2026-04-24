from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class HealthStatus(Enum):
    HEALTHY = "healthy"      # fully operational
    DEGRADED = "degraded"    # running but with non-critical issues
    UNHEALTHY = "unhealthy"  # not operational


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ComponentHealth:
    """Health report for one named component (playout engine, job runner, etc.)."""

    name: str
    status: HealthStatus
    message: Optional[str] = None
    checked_at: datetime = field(default_factory=_now)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "checked_at": self.checked_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class SystemHealth:
    """Aggregate health report covering all registered components.

    JSON shape
    ----------
    {
        "status": "healthy" | "degraded" | "unhealthy",
        "checked_at": "<ISO-8601 UTC>",
        "version": "<semver string>",
        "components": [
            {
                "name": "<str>",
                "status": "healthy" | "degraded" | "unhealthy",
                "message": "<str | null>",
                "checked_at": "<ISO-8601 UTC>",
                "metadata": {}
            }
        ]
    }
    """

    status: HealthStatus
    components: list[ComponentHealth] = field(default_factory=list)
    checked_at: datetime = field(default_factory=_now)
    version: str = ""

    @classmethod
    def from_components(
        cls,
        components: list[ComponentHealth],
        *,
        version: str = "",
    ) -> "SystemHealth":
        """Build a SystemHealth by aggregating component statuses (worst-case)."""
        if any(c.status is HealthStatus.UNHEALTHY for c in components):
            aggregate = HealthStatus.UNHEALTHY
        elif any(c.status is HealthStatus.DEGRADED for c in components):
            aggregate = HealthStatus.DEGRADED
        else:
            aggregate = HealthStatus.HEALTHY
        return cls(status=aggregate, components=list(components), version=version)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "checked_at": self.checked_at.isoformat(),
            "version": self.version,
            "components": [c.to_dict() for c in self.components],
        }


class ServiceHealth(ABC):
    """
    Contract for any RASTATIME component that can report its health.

    Implementations cover individual subsystems (playout engine, job runner,
    stream manager, audio device manager). A top-level health aggregator
    collects their ComponentHealth reports into a single SystemHealth.

    Integration note: the /health HTTP endpoint (T3.2) will call
    check_health() on all registered ServiceHealth instances and serialize
    the resulting SystemHealth via SystemHealth.to_dict().
    """

    @abstractmethod
    def check_health(self) -> ComponentHealth:
        """
        Return the current health of this component.

        Must not raise — any internal error should be reflected in the
        returned ComponentHealth (status=UNHEALTHY, message=str(exc)).
        """

    @abstractmethod
    def is_alive(self) -> bool:
        """
        Liveness probe.

        True if the process/thread is running and responsive.
        A False result means the service should be restarted.
        """

    @abstractmethod
    def is_ready(self) -> bool:
        """
        Readiness probe.

        True if the component is fully initialised and can accept work.
        A False result means callers should wait before sending requests.
        """
