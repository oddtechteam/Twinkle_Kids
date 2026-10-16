from fastapi import APIRouter, Response, status

from app.api.deps import CheckHealthDep, HealthProbesDep, SettingsDep
from app.api.schemas.health import HealthOut
from app.domain.entities.health import ComponentState

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthOut, summary="Liveness: the API process is up")
def liveness(use_case: CheckHealthDep) -> HealthOut:
    return HealthOut.from_report(use_case.liveness())


@router.get(
    "/ready",
    response_model=HealthOut,
    summary="Readiness: the API can reach its dependencies",
    responses={503: {"model": HealthOut, "description": "A dependency is down"}},
)
def readiness(
    use_case: CheckHealthDep, probes: HealthProbesDep, settings: SettingsDep, response: Response
) -> HealthOut:
    report = use_case.readiness(probes)
    if report.state is not ComponentState.OK:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthOut.from_report(report, include_details=settings.app_env != "production")
