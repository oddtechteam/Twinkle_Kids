from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_health_probes
from app.bootstrap import Container
from app.domain.entities.health import ComponentHealth, ComponentState
from app.main import create_app


def test_liveness_returns_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "Twinkle Kids API"
    assert body["environment"] == "test"
    assert body["components"] == []


def test_readiness_checks_database_and_storage(client: TestClient) -> None:
    response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    components = {c["name"]: c for c in body["components"]}
    assert components["database"]["state"] == "ok"
    assert components["database"]["detail"] == "sqlite"
    assert components["database"]["latency_ms"] >= 0
    assert components["storage"] == {
        "name": "storage",
        "state": "ok",
        "latency_ms": 0.0,
        "detail": "in-memory",
    }


def test_readiness_returns_503_when_a_dependency_is_down(app: FastAPI) -> None:
    class DownProbe:
        def check(self) -> ComponentHealth:
            return ComponentHealth("database", ComponentState.DOWN, detail="unreachable")

    app.dependency_overrides[get_health_probes] = lambda: [DownProbe()]
    with TestClient(app) as client:
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "down"


def test_unversioned_paths_are_not_served(client: TestClient) -> None:
    assert client.get("/health").status_code == 404


def test_readiness_hides_infrastructure_details_in_production(container: Container) -> None:
    container.settings = container.settings.model_copy(update={"app_env": "production"})
    with TestClient(create_app(container=container)) as client:
        body = client.get("/api/v1/health/ready").json()
    assert body["status"] == "ok"
    assert all(c["detail"] is None and c["latency_ms"] is None for c in body["components"])
    assert {c["name"] for c in body["components"]} == {"database", "storage"}
