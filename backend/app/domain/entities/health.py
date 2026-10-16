from dataclasses import dataclass, field
from enum import StrEnum


class ComponentState(StrEnum):
    OK = "ok"
    DOWN = "down"


@dataclass(frozen=True, slots=True)
class ComponentHealth:
    name: str
    state: ComponentState
    latency_ms: float | None = None
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class HealthReport:
    service: str
    version: str
    environment: str
    components: tuple[ComponentHealth, ...] = field(default_factory=tuple)

    @property
    def state(self) -> ComponentState:
        if all(c.state is ComponentState.OK for c in self.components):
            return ComponentState.OK
        return ComponentState.DOWN
