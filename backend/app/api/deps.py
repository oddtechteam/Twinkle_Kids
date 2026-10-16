"""Dependency wiring: the only place where API, application and infrastructure meet."""

from collections.abc import Callable, Iterator, Sequence
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.application.use_cases.auth import AuthService, RequestContext
from app.application.use_cases.catalog_admin import CategoryCommands, ProductCommands
from app.application.use_cases.catalog_queries import CatalogReader
from app.application.use_cases.check_health import CheckHealth
from app.application.use_cases.media import (
    DeleteMedia,
    GetMedia,
    ListMedia,
    MediaPolicy,
    UploadMedia,
)
from app.application.use_cases.merchandising import MerchandisingService
from app.bootstrap import Container
from app.core.config import Settings
from app.core.version import __version__
from app.domain.entities.identity import Permission, User
from app.domain.errors import PermissionDeniedError
from app.domain.repositories.health import HealthProbe
from app.infrastructure.db.catalog_queries import SqlAlchemyCatalogQueries
from app.infrastructure.db.repositories.catalog import (
    SqlAlchemyCategoryRepository,
    SqlAlchemyCollectionRepository,
    SqlAlchemyHomepageSectionRepository,
    SqlAlchemyProductRepository,
)
from app.infrastructure.db.repositories.identity import (
    SqlAlchemyAuditLogRepository,
    SqlAlchemySessionRepository,
    SqlAlchemyUserRepository,
)
from app.infrastructure.db.repositories.inventory import SqlAlchemyInventoryLedger
from app.infrastructure.db.repositories.media import SqlAlchemyMediaAssetRepository
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


ContainerDep = Annotated[Container, Depends(get_container)]


def get_app_settings(container: ContainerDep) -> Settings:
    return container.settings


SettingsDep = Annotated[Settings, Depends(get_app_settings)]


def get_db_session(container: ContainerDep) -> Iterator[Session]:
    """One session (and transaction) per request; use cases commit explicitly."""
    session = container.session_factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


SessionDep = Annotated[Session, Depends(get_db_session)]


def request_context(request: Request) -> RequestContext:
    return RequestContext(
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


RequestContextDep = Annotated[RequestContext, Depends(request_context)]


# --- Health -----------------------------------------------------------------------------------


def get_check_health(settings: SettingsDep) -> CheckHealth:
    return CheckHealth(service=settings.app_name, version=__version__, environment=settings.app_env)


def get_health_probes(container: ContainerDep) -> Sequence[HealthProbe]:
    return container.health_probes


CheckHealthDep = Annotated[CheckHealth, Depends(get_check_health)]
HealthProbesDep = Annotated[Sequence[HealthProbe], Depends(get_health_probes)]


# --- Authentication & authorization -----------------------------------------------------------


def get_auth_service(container: ContainerDep, session: SessionDep) -> AuthService:
    return AuthService(
        users=SqlAlchemyUserRepository(session),
        sessions=SqlAlchemySessionRepository(session),
        audit=SqlAlchemyAuditLogRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
        hasher=container.password_hasher,
        rate_limiter=container.rate_limiter,
        policy=container.auth_policy,
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def session_token(request: Request, settings: SettingsDep) -> str | None:
    return request.cookies.get(settings.session_cookie_name)


def get_current_user(
    auth: AuthServiceDep, token: Annotated[str | None, Depends(session_token)]
) -> User:
    user, _session = auth.authenticate(token)
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def require_permission(*permissions: Permission) -> Callable[[User], User]:
    """Server-side authorization: every listed permission is required."""

    def dependency(user: CurrentUserDep) -> User:
        if not user.has_permission(Permission.ADMIN_ACCESS) or not all(
            user.has_permission(p) for p in permissions
        ):
            raise PermissionDeniedError("You do not have permission to perform this action.")
        return user

    return dependency


StaffUserDep = Annotated[User, Depends(require_permission(Permission.ADMIN_ACCESS))]
CatalogManagerDep = Annotated[User, Depends(require_permission(Permission.CATALOG_MANAGE))]
ContentManagerDep = Annotated[User, Depends(require_permission(Permission.CONTENT_MANAGE))]
MediaManagerDep = Annotated[User, Depends(require_permission(Permission.MEDIA_MANAGE))]


# --- Catalogue --------------------------------------------------------------------------------


def get_catalog_reader(container: ContainerDep, session: SessionDep) -> CatalogReader:
    return CatalogReader(SqlAlchemyCatalogQueries(session, container.storage))


def get_product_commands(session: SessionDep) -> ProductCommands:
    return ProductCommands(
        products=SqlAlchemyProductRepository(session),
        categories=SqlAlchemyCategoryRepository(session),
        media=SqlAlchemyMediaAssetRepository(session),
        inventory=SqlAlchemyInventoryLedger(session),
        audit=SqlAlchemyAuditLogRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
    )


def get_category_commands(session: SessionDep) -> CategoryCommands:
    return CategoryCommands(
        categories=SqlAlchemyCategoryRepository(session),
        products=SqlAlchemyProductRepository(session),
        media=SqlAlchemyMediaAssetRepository(session),
        audit=SqlAlchemyAuditLogRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
    )


def get_merchandising(container: ContainerDep, session: SessionDep) -> MerchandisingService:
    return MerchandisingService(
        collections=SqlAlchemyCollectionRepository(session),
        sections=SqlAlchemyHomepageSectionRepository(session),
        categories=SqlAlchemyCategoryRepository(session),
        products=SqlAlchemyProductRepository(session),
        media=SqlAlchemyMediaAssetRepository(session),
        queries=SqlAlchemyCatalogQueries(session, container.storage),
        audit=SqlAlchemyAuditLogRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
    )


CatalogReaderDep = Annotated[CatalogReader, Depends(get_catalog_reader)]
ProductCommandsDep = Annotated[ProductCommands, Depends(get_product_commands)]
CategoryCommandsDep = Annotated[CategoryCommands, Depends(get_category_commands)]
MerchandisingDep = Annotated[MerchandisingService, Depends(get_merchandising)]


# --- Media ------------------------------------------------------------------------------------


def get_upload_media(container: ContainerDep, session: SessionDep) -> UploadMedia:
    return UploadMedia(
        storage=container.storage,
        repository=SqlAlchemyMediaAssetRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
        inspector=container.image_inspector,
        policy=MediaPolicy(max_bytes=container.settings.media_max_upload_bytes),
        buckets=container.buckets,
    )


def get_get_media(container: ContainerDep, session: SessionDep) -> GetMedia:
    return GetMedia(storage=container.storage, repository=SqlAlchemyMediaAssetRepository(session))


def get_list_media(container: ContainerDep, session: SessionDep) -> ListMedia:
    return ListMedia(storage=container.storage, repository=SqlAlchemyMediaAssetRepository(session))


def get_delete_media(container: ContainerDep, session: SessionDep) -> DeleteMedia:
    return DeleteMedia(
        storage=container.storage,
        repository=SqlAlchemyMediaAssetRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
    )


UploadMediaDep = Annotated[UploadMedia, Depends(get_upload_media)]
GetMediaDep = Annotated[GetMedia, Depends(get_get_media)]
ListMediaDep = Annotated[ListMedia, Depends(get_list_media)]
DeleteMediaDep = Annotated[DeleteMedia, Depends(get_delete_media)]
