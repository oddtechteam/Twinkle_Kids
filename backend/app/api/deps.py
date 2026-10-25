"""Dependency wiring: the only place where API, application and infrastructure meet."""

from collections.abc import Callable, Iterator, Sequence
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.application.use_cases.auth import AuthService, RequestContext
from app.application.use_cases.cart import CartService
from app.application.use_cases.catalog_admin import CategoryCommands, ProductCommands
from app.application.use_cases.catalog_queries import CatalogReader
from app.application.use_cases.check_health import CheckHealth
from app.application.use_cases.collections import CollectionService
from app.application.use_cases.dashboard import DashboardReader
from app.application.use_cases.homepage import HomepageBuilder, PublicHomepage
from app.application.use_cases.media import (
    DeleteMedia,
    GetMedia,
    ListMedia,
    MediaPolicy,
    ReplaceMedia,
    UpdateMediaDetails,
    UploadMedia,
)
from app.application.use_cases.site import (
    NavigationService,
    PageService,
    PublicSiteReader,
    SettingsService,
    ShippingService,
    SizeChartService,
)
from app.application.use_cases.whatsapp import WhatsAppOrdering
from app.bootstrap import Container
from app.core.config import Settings
from app.core.version import __version__
from app.domain.entities.identity import Permission, User
from app.domain.errors import AuthenticationError, PermissionDeniedError
from app.domain.repositories.health import HealthProbe
from app.infrastructure.db.catalog_queries import SqlAlchemyCatalogQueries
from app.infrastructure.db.dashboard_queries import SqlAlchemyDashboardQueries
from app.infrastructure.db.repositories.catalog import (
    SqlAlchemyCategoryRepository,
    SqlAlchemyCollectionRepository,
    SqlAlchemyProductRepository,
)
from app.infrastructure.db.repositories.identity import (
    SqlAlchemyAuditLogRepository,
    SqlAlchemySessionRepository,
    SqlAlchemyUserRepository,
)
from app.infrastructure.db.repositories.commerce import (
    SqlAlchemyCartRepository,
    SqlAlchemyWhatsAppRequestRepository,
)
from app.infrastructure.db.repositories.inventory import SqlAlchemyInventoryLedger
from app.infrastructure.db.repositories.media import SqlAlchemyMediaAssetRepository
from app.infrastructure.db.repositories.site import (
    SqlAlchemyCollectionAdminRepository,
    SqlAlchemyHomepageBuilderRepository,
    SqlAlchemyNavigationRepository,
    SqlAlchemyPageRepository,
    SqlAlchemySettingsRepository,
    SqlAlchemyShippingRuleRepository,
    SqlAlchemySizeChartRepository,
)
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


def get_optional_user(
    auth: AuthServiceDep, token: Annotated[str | None, Depends(session_token)]
) -> User | None:
    """The signed-in user, or None for guests (an expired session is treated as a guest)."""
    if not token:
        return None
    try:
        user, _session = auth.authenticate(token)
    except AuthenticationError:
        return None
    return user


OptionalUserDep = Annotated[User | None, Depends(get_optional_user)]


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
SettingsManagerDep = Annotated[User, Depends(require_permission(Permission.SETTINGS_MANAGE))]


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
        collections=SqlAlchemyCollectionAdminRepository(session),
    )


def get_category_commands(session: SessionDep) -> CategoryCommands:
    return CategoryCommands(
        categories=SqlAlchemyCategoryRepository(session),
        products=SqlAlchemyProductRepository(session),
        media=SqlAlchemyMediaAssetRepository(session),
        audit=SqlAlchemyAuditLogRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
    )


def _queries(container: Container, session: Session) -> SqlAlchemyCatalogQueries:
    return SqlAlchemyCatalogQueries(session, container.storage)


def get_collection_service(container: ContainerDep, session: SessionDep) -> CollectionService:
    return CollectionService(
        collections=SqlAlchemyCollectionRepository(session),
        admin=SqlAlchemyCollectionAdminRepository(session),
        products=SqlAlchemyProductRepository(session),
        media=SqlAlchemyMediaAssetRepository(session),
        queries=_queries(container, session),
        audit=SqlAlchemyAuditLogRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
    )


def get_homepage_builder(session: SessionDep) -> HomepageBuilder:
    return HomepageBuilder(
        sections=SqlAlchemyHomepageBuilderRepository(session),
        categories=SqlAlchemyCategoryRepository(session),
        collections=SqlAlchemyCollectionAdminRepository(session),
        products=SqlAlchemyProductRepository(session),
        media=SqlAlchemyMediaAssetRepository(session),
        audit=SqlAlchemyAuditLogRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
    )


def get_public_homepage(container: ContainerDep, session: SessionDep) -> PublicHomepage:
    return PublicHomepage(
        sections=SqlAlchemyHomepageBuilderRepository(session),
        categories=SqlAlchemyCategoryRepository(session),
        queries=_queries(container, session),
    )


def get_settings_service(session: SessionDep) -> SettingsService:
    return SettingsService(
        settings=SqlAlchemySettingsRepository(session),
        media=SqlAlchemyMediaAssetRepository(session),
        audit=SqlAlchemyAuditLogRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
    )


def get_navigation_service(session: SessionDep) -> NavigationService:
    return NavigationService(
        navigation=SqlAlchemyNavigationRepository(session),
        categories=SqlAlchemyCategoryRepository(session),
        collections=SqlAlchemyCollectionAdminRepository(session),
        pages=SqlAlchemyPageRepository(session),
        audit=SqlAlchemyAuditLogRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
    )


def get_page_service(session: SessionDep) -> PageService:
    return PageService(
        pages=SqlAlchemyPageRepository(session),
        audit=SqlAlchemyAuditLogRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
    )


def get_shipping_service(session: SessionDep) -> ShippingService:
    return ShippingService(
        rules=SqlAlchemyShippingRuleRepository(session),
        audit=SqlAlchemyAuditLogRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
    )


def get_size_chart_service(session: SessionDep) -> SizeChartService:
    return SizeChartService(
        charts=SqlAlchemySizeChartRepository(session),
        audit=SqlAlchemyAuditLogRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
    )


def get_public_site(container: ContainerDep, session: SessionDep) -> PublicSiteReader:
    return PublicSiteReader(
        settings=SqlAlchemySettingsRepository(session),
        navigation=SqlAlchemyNavigationRepository(session),
        categories=SqlAlchemyCategoryRepository(session),
        collections=SqlAlchemyCollectionAdminRepository(session),
        pages=SqlAlchemyPageRepository(session),
        queries=_queries(container, session),
    )


def get_dashboard(session: SessionDep) -> DashboardReader:
    return DashboardReader(SqlAlchemyDashboardQueries(session))


CatalogReaderDep = Annotated[CatalogReader, Depends(get_catalog_reader)]
ProductCommandsDep = Annotated[ProductCommands, Depends(get_product_commands)]
CategoryCommandsDep = Annotated[CategoryCommands, Depends(get_category_commands)]
CollectionServiceDep = Annotated[CollectionService, Depends(get_collection_service)]
HomepageBuilderDep = Annotated[HomepageBuilder, Depends(get_homepage_builder)]
PublicHomepageDep = Annotated[PublicHomepage, Depends(get_public_homepage)]
SettingsServiceDep = Annotated[SettingsService, Depends(get_settings_service)]
NavigationServiceDep = Annotated[NavigationService, Depends(get_navigation_service)]
PageServiceDep = Annotated[PageService, Depends(get_page_service)]
ShippingServiceDep = Annotated[ShippingService, Depends(get_shipping_service)]
SizeChartServiceDep = Annotated[SizeChartService, Depends(get_size_chart_service)]
PublicSiteDep = Annotated[PublicSiteReader, Depends(get_public_site)]
DashboardDep = Annotated[DashboardReader, Depends(get_dashboard)]


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


def get_update_media(container: ContainerDep, session: SessionDep) -> UpdateMediaDetails:
    return UpdateMediaDetails(
        storage=container.storage,
        repository=SqlAlchemyMediaAssetRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
    )


def get_replace_media(container: ContainerDep, session: SessionDep) -> ReplaceMedia:
    return ReplaceMedia(
        storage=container.storage,
        repository=SqlAlchemyMediaAssetRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
        inspector=container.image_inspector,
        policy=MediaPolicy(max_bytes=container.settings.media_max_upload_bytes),
    )


UpdateMediaDep = Annotated[UpdateMediaDetails, Depends(get_update_media)]
ReplaceMediaDep = Annotated[ReplaceMedia, Depends(get_replace_media)]


# --- Cart & WhatsApp ordering -----------------------------------------------------------------


def get_cart_service(container: ContainerDep, session: SessionDep) -> CartService:
    return CartService(
        carts=SqlAlchemyCartRepository(session),
        products=SqlAlchemyProductRepository(session),
        queries=_queries(container, session),
        shipping=SqlAlchemyShippingRuleRepository(session),
        settings=SqlAlchemySettingsRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
    )


def get_whatsapp_ordering(container: ContainerDep, session: SessionDep) -> WhatsAppOrdering:
    return WhatsAppOrdering(
        settings=SqlAlchemySettingsRepository(session),
        carts=SqlAlchemyCartRepository(session),
        products=SqlAlchemyProductRepository(session),
        requests=SqlAlchemyWhatsAppRequestRepository(session),
        rate_limiter=container.rate_limiter,
        uow=SqlAlchemyUnitOfWork(session),
        storefront_url=container.settings.storefront_url,
    )


CartServiceDep = Annotated[CartService, Depends(get_cart_service)]
WhatsAppOrderingDep = Annotated[WhatsAppOrdering, Depends(get_whatsapp_ordering)]
