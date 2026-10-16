from typing import Protocol

from app.domain.entities.health import ComponentHealth


class HealthProbe(Protocol):
    """Port implemented by infrastructure to report on one dependency (database, storage, ...)."""

    def check(self) -> ComponentHealth: ...
