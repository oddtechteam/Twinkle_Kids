from collections.abc import Sequence

from app.domain.entities.health import HealthReport
from app.domain.repositories.health import HealthProbe


class CheckHealth:
    """Aggregates dependency probes into a single health report."""

    def __init__(self, *, service: str, version: str, environment: str) -> None:
        self._service = service
        self._version = version
        self._environment = environment

    def liveness(self) -> HealthReport:
        return HealthReport(self._service, self._version, self._environment)

    def readiness(self, probes: Sequence[HealthProbe]) -> HealthReport:
        return HealthReport(
            self._service,
            self._version,
            self._environment,
            components=tuple(probe.check() for probe in probes),
        )
