import logging
import time

from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.domain.entities.health import ComponentHealth, ComponentState

logger = logging.getLogger(__name__)


class DatabaseHealthProbe:
    """HealthProbe adapter that runs ``SELECT 1`` against the configured database."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def check(self) -> ComponentHealth:
        started = time.perf_counter()
        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except SQLAlchemyError as exc:
            # Log the cause server-side; never echo connection details to clients.
            logger.warning("Database health check failed: %s", exc.__class__.__name__)
            return ComponentHealth("database", ComponentState.DOWN, detail="unreachable")
        latency = round((time.perf_counter() - started) * 1000, 2)
        return ComponentHealth(
            "database",
            ComponentState.OK,
            latency_ms=latency,
            detail=self._engine.dialect.name,
        )
