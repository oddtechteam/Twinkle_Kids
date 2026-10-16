from app.application.use_cases.check_health import CheckHealth
from app.domain.entities.health import ComponentHealth, ComponentState


class StubProbe:
    def __init__(self, state: ComponentState) -> None:
        self._state = state

    def check(self) -> ComponentHealth:
        return ComponentHealth("stub", self._state)


USE_CASE = CheckHealth(service="svc", version="1.0", environment="test")


def test_liveness_has_no_components_and_is_ok() -> None:
    report = USE_CASE.liveness()
    assert report.components == ()
    assert report.state is ComponentState.OK


def test_readiness_is_down_if_any_probe_is_down() -> None:
    report = USE_CASE.readiness([StubProbe(ComponentState.OK), StubProbe(ComponentState.DOWN)])
    assert report.state is ComponentState.DOWN
    assert len(report.components) == 2
