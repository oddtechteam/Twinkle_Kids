from pydantic import BaseModel, ConfigDict

from app.domain.entities.health import ComponentState, HealthReport


class ComponentHealthOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    state: ComponentState
    latency_ms: float | None = None
    detail: str | None = None


class HealthOut(BaseModel):
    service: str
    version: str
    environment: str
    status: ComponentState
    components: list[ComponentHealthOut] = []

    @classmethod
    def from_report(cls, report: HealthReport, *, include_details: bool = True) -> "HealthOut":
        components = [ComponentHealthOut.model_validate(c) for c in report.components]
        if not include_details:  # production: state only, no driver/latency/infrastructure hints
            components = [ComponentHealthOut(name=c.name, state=c.state) for c in components]
        return cls(
            service=report.service,
            version=report.version,
            environment=report.environment,
            status=report.state,
            components=components,
        )
