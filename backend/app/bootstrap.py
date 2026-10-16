"""Composition root: builds long-lived infrastructure (DB engine, object storage) from settings.

One Container per FastAPI app; request-scoped objects (sessions, use cases) are built in
``app.api.deps`` from it.
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.ports import PasswordHasher, RateLimiter
from app.application.use_cases.auth import AuthPolicy
from app.core.config import Settings
from app.domain.entities.media import MediaVisibility
from app.domain.repositories.health import HealthProbe
from app.domain.repositories.media import ImageInspector, ObjectStorage
from app.infrastructure.auth.passwords import Argon2PasswordHasher
from app.infrastructure.auth.rate_limit import InMemoryRateLimiter
from app.infrastructure.db.health import DatabaseHealthProbe
from app.infrastructure.db.session import build_engine
from app.infrastructure.storage.image_inspector import PillowImageInspector
from app.infrastructure.storage.memory import InMemoryObjectStorage, InMemoryStorageHealthProbe
from app.infrastructure.storage.s3 import S3BucketHealthProbe, S3ObjectStorage, build_s3_client

logger = logging.getLogger(__name__)


@dataclass
class Container:
    settings: Settings
    engine: Engine
    session_factory: sessionmaker[Session]
    storage: ObjectStorage
    image_inspector: ImageInspector
    health_probes: Sequence[HealthProbe]
    password_hasher: PasswordHasher
    rate_limiter: RateLimiter

    @property
    def auth_policy(self) -> AuthPolicy:
        s = self.settings
        return AuthPolicy(
            session_ttl=timedelta(hours=s.session_ttl_hours),
            login_attempts_per_ip=s.login_max_attempts_per_ip,
            login_attempts_per_account=s.login_max_attempts_per_account,
            login_window_seconds=s.login_window_seconds,
            registrations_per_ip=s.registration_max_per_ip_per_hour,
        )

    @property
    def buckets(self) -> dict[MediaVisibility, str]:
        return {
            MediaVisibility.PUBLIC: self.settings.storage_media_bucket,
            MediaVisibility.PRIVATE: self.settings.storage_private_bucket,
        }

    def dispose(self) -> None:
        self.engine.dispose()


def build_container(settings: Settings) -> Container:
    engine = build_engine(settings.database_url, echo=settings.database_echo)
    storage: ObjectStorage
    storage_probe: HealthProbe

    if settings.resolved_storage_backend == "neon":
        # Validated by Settings: these are present when the backend resolves to "neon".
        assert settings.aws_access_key_id and settings.aws_secret_access_key  # noqa: S101
        assert settings.aws_endpoint_url_s3  # noqa: S101
        client = build_s3_client(
            endpoint_url=settings.aws_endpoint_url_s3,
            access_key_id=settings.aws_access_key_id,
            secret_access_key=settings.aws_secret_access_key.get_secret_value(),
            region=settings.aws_region,
        )
        storage = S3ObjectStorage(
            client,
            endpoint_url=settings.aws_endpoint_url_s3,
            public_base_url=settings.media_public_base_url,
        )
        storage_probe = S3BucketHealthProbe(client, settings.storage_media_bucket)
    else:
        logger.warning("Object storage: using in-memory backend (files are not persisted).")
        storage = InMemoryObjectStorage()
        storage_probe = InMemoryStorageHealthProbe()

    return Container(
        settings=settings,
        engine=engine,
        session_factory=sessionmaker(bind=engine, autoflush=False, expire_on_commit=False),
        storage=storage,
        image_inspector=PillowImageInspector(),
        health_probes=[DatabaseHealthProbe(engine), storage_probe],
        password_hasher=Argon2PasswordHasher(),
        rate_limiter=InMemoryRateLimiter(),
    )
