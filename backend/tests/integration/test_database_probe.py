from app.domain.entities.health import ComponentState
from app.infrastructure.db.health import DatabaseHealthProbe
from app.infrastructure.db.session import build_engine


def test_probe_reports_down_without_leaking_connection_details() -> None:
    engine = build_engine("postgresql://user:hunter2@127.0.0.1:1/nope?connect_timeout=1")
    try:
        result = DatabaseHealthProbe(engine).check()
    finally:
        engine.dispose()

    assert result.state is ComponentState.DOWN
    assert result.detail == "unreachable"
