"""Dependency wiring: the only place where API, application and infrastructure meet."""

from collections.abc import Callable, Iterator, Sequence
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.application.use_cases.account import AccountPolicy, AccountService
from app.application.use_cases.after_sale import AfterSaleService
from app.application.use_cases.analytics import AnalyticsReader
from app.application.use_cases.auth import AuthService, RequestContext
from app.application.use_cases.cart import CartService
from app.application.use_cases.catalog_admin import CategoryCommands, ProductCommands
from app.application.use_cases.catalog_queries import CatalogReader
from app.application.use_cases.check_health import CheckHealth
from app.application.use_cases.collections import CollectionService
from app.application.use_cases.coupons import CouponService
from app.application.use_cases.dashboard import DashboardReader
from app.application.use_cases.homepage import HomepageBuilder, PublicHomepage
from app.application.use_cases.inventory import InventoryService
from app.application.use_cases.media import (
    CropMedia,
    DeleteMedia,
    GetMedia,
    ListMedia,
    MediaPolicy,
    ReplaceMedia,
    UpdateMediaDetails,
    UploadMedia,
)
from app.application.use_cases.notifications import Notifier
from app.application.use_cases.orders import (
    CheckoutService,
    CustomerOrders,
    OrderAdmin,
    OrderWriter,
    WhatsAppAdmin,
)
from app.application.use_cases.reviews import ReviewService
from app.application.use_cases.site import (
    NavigationService,
    PageService,
    PublicSiteReader,
    SettingsService,
    ShippingService,
    SizeChartService,
)
from app.application.use_cases.staff import StaffService
from app.application.use_cases.whatsapp import WhatsAppOrdering
from app.bootstrap import Container
from app.core.config import Settings
from app.core.version import __version__
from app.domain.entities.identity import AuthSession, Permission, User
from app.domain.errors import AuthenticationError, PermissionDeniedError
from app.domain.repositories.health import HealthProbe
from app.infrastructure.db.analytics_queries import SqlAlchemyAnalyticsQueries
from app.infrastructure.db.catalog_queries import SqlAlchemyCatalogQueries
from app.infrastructure.db.dashboard_queries import SqlAlchemyDashboardQueries
from app.infrastructure.db.inventory_store import SqlAlchemyInventoryStore
from app.infrastructure.db.notification_log import SqlAlchemyNotificationLog
from app.infrastructure.db.order_queries import SqlAlchemyOrderQueries
from app.infrastructure.db.order_request_store import SqlAlchemyOrderRequestStore
from app.infrastructure.db.repositories.catalog import (
    SqlAlchemyCategoryRepository,
    SqlAlchemyCollectionRepository,
    SqlAlchemyProductRepository,
)
from app.infrastructure.db.repositories.commerce import (
    SqlAlchemyCartRepository,
    SqlAlchemyCouponRepository,
    SqlAlchemyOrderRepository,
    SqlAlchemyWhatsAppRequestRepository,
)
from app.infrastructure.db.repositories.identity import (
    SqlAlchemyAddressRepository,
    SqlAlchemyAuditLogRepository,
    SqlAlchemyPasswordResetRepository,
    SqlAlchemySessionRepository,
    SqlAlchemyUserRepository,
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
from app.infrastructure.db.review_store import SqlAlchemyReviewStore
from app.infrastructure.db.staff_store import SqlAlchemyStaffStore
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


def get_current_session(
    auth: AuthServiceDep, token: Annotated[str | None, Depends(session_token)]
) -> AuthSession:
    _user, session = auth.authenticate(token)
    return session


CurrentSessionDep = Annotated[AuthSession, Depends(get_current_session)]


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
OrdersManagerDep = Annotated[User, Depends(require_permission(Permission.ORDERS_MANAGE))]
InventoryManagerDep = Annotated[User, Depends(require_permission(Permission.INVENTORY_MANAGE))]
UsersManagerDep = Annotated[User, Depends(require_permission(Permission.USERS_MANAGE))]
AuditReaderDep = Annotated[User, Depends(require_permission(Permission.AUDIT_READ))]


# --- Catalogue --------------------------------------------------------------------------------


def get_catalog_reader(container: ContainerDep, session: SessionDep) -> CatalogReader:
    queries = SqlAlchemyCatalogQueries(session, container.storage)
    return CatalogReader(queries, recommendations=queries)


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
        recommendations=_queries(container, session),
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


def get_crop_media(container: ContainerDep, session: SessionDep) -> CropMedia:
    return CropMedia(
        storage=container.storage,
        repository=SqlAlchemyMediaAssetRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
        cropper=container.image_cropper,
    )


UpdateMediaDep = Annotated[UpdateMediaDetails, Depends(get_update_media)]
ReplaceMediaDep = Annotated[ReplaceMedia, Depends(get_replace_media)]
CropMediaDep = Annotated[CropMedia, Depends(get_crop_media)]


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


# --- Accounts, checkout and orders ------------------------------------------------------------


def _notifier(container: Container, session: Session) -> Notifier:
    return Notifier(mailer=container.mailer, log=SqlAlchemyNotificationLog(session))


def get_account_service(container: ContainerDep, session: SessionDep) -> AccountService:
    settings = container.settings
    return AccountService(
        users=SqlAlchemyUserRepository(session),
        sessions=SqlAlchemySessionRepository(session),
        resets=SqlAlchemyPasswordResetRepository(session),
        addresses=SqlAlchemyAddressRepository(session),
        audit=SqlAlchemyAuditLogRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
        hasher=container.password_hasher,
        rate_limiter=container.rate_limiter,
        notifier=_notifier(container, session),
        policy=AccountPolicy(
            reset_ttl=timedelta(minutes=settings.password_reset_ttl_minutes),
            storefront_url=settings.storefront_url,
            store_name=SqlAlchemySettingsRepository(session).get().store_name,
        ),
    )


def _order_writer(container: Container, session: Session) -> OrderWriter:
    return OrderWriter(
        orders=SqlAlchemyOrderRepository(session),
        products=SqlAlchemyProductRepository(session),
        carts=SqlAlchemyCartRepository(session),
        coupons=SqlAlchemyCouponRepository(session),
        shipping=SqlAlchemyShippingRuleRepository(session),
        ledger=SqlAlchemyInventoryLedger(session),
        queries=_queries(container, session),
        clock=lambda: datetime.now(UTC),
        collections=SqlAlchemyCollectionAdminRepository(session),
        settings=SqlAlchemySettingsRepository(session),
    )


def get_checkout_service(
    container: ContainerDep, session: SessionDep, cart: CartServiceDep
) -> CheckoutService:
    return CheckoutService(
        writer=_order_writer(container, session),
        cart=cart,
        carts=SqlAlchemyCartRepository(session),
        addresses=SqlAlchemyAddressRepository(session),
        settings=SqlAlchemySettingsRepository(session),
        order_queries=SqlAlchemyOrderQueries(session),
        audit=SqlAlchemyAuditLogRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
        rate_limiter=container.rate_limiter,
        notifier=_notifier(container, session),
        storefront_url=container.settings.storefront_url,
    )


def get_customer_orders(session: SessionDep) -> CustomerOrders:
    return CustomerOrders(SqlAlchemyOrderQueries(session))


def get_order_admin(container: ContainerDep, session: SessionDep) -> OrderAdmin:
    return OrderAdmin(
        writer=_order_writer(container, session),
        queries=SqlAlchemyOrderQueries(session),
        audit=SqlAlchemyAuditLogRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
    )


def get_whatsapp_admin(container: ContainerDep, session: SessionDep) -> WhatsAppAdmin:
    return WhatsAppAdmin(
        writer=_order_writer(container, session),
        requests=SqlAlchemyWhatsAppRequestRepository(session),
        queries=SqlAlchemyOrderQueries(session),
        audit=SqlAlchemyAuditLogRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
    )


AccountServiceDep = Annotated[AccountService, Depends(get_account_service)]
CheckoutServiceDep = Annotated[CheckoutService, Depends(get_checkout_service)]
CustomerOrdersDep = Annotated[CustomerOrders, Depends(get_customer_orders)]
OrderAdminDep = Annotated[OrderAdmin, Depends(get_order_admin)]
WhatsAppAdminDep = Annotated[WhatsAppAdmin, Depends(get_whatsapp_admin)]


# --- Store operations --------------------------------------------------------------------------


def get_notifier(container: ContainerDep, session: SessionDep) -> Notifier:
    return _notifier(container, session)


def get_inventory_service(session: SessionDep) -> InventoryService:
    return InventoryService(
        store=SqlAlchemyInventoryStore(session),
        ledger=SqlAlchemyInventoryLedger(session),
        audit=SqlAlchemyAuditLogRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
    )


def get_coupon_service(session: SessionDep) -> CouponService:
    return CouponService(
        coupons=SqlAlchemyCouponRepository(session),
        products=SqlAlchemyProductRepository(session),
        categories=SqlAlchemyCategoryRepository(session),
        collections=SqlAlchemyCollectionAdminRepository(session),
        audit=SqlAlchemyAuditLogRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
    )


def get_after_sale(session: SessionDep) -> AfterSaleService:
    return AfterSaleService(
        store=SqlAlchemyOrderRequestStore(session),
        orders=SqlAlchemyOrderRepository(session),
        order_queries=SqlAlchemyOrderQueries(session),
        products=SqlAlchemyProductRepository(session),
        carts=SqlAlchemyCartRepository(session),
        ledger=SqlAlchemyInventoryLedger(session),
        settings=SqlAlchemySettingsRepository(session),
        audit=SqlAlchemyAuditLogRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
    )


def get_review_service(container: ContainerDep, session: SessionDep) -> ReviewService:
    return ReviewService(
        store=SqlAlchemyReviewStore(session, container.storage),
        products=SqlAlchemyProductRepository(session),
        audit=SqlAlchemyAuditLogRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
    )


def get_analytics(session: SessionDep) -> AnalyticsReader:
    return AnalyticsReader(SqlAlchemyAnalyticsQueries(session))


def get_staff_service(session: SessionDep) -> StaffService:
    return StaffService(
        store=SqlAlchemyStaffStore(session),
        sessions=SqlAlchemySessionRepository(session),
        audit=SqlAlchemyAuditLogRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
    )


NotifierDep = Annotated[Notifier, Depends(get_notifier)]
InventoryServiceDep = Annotated[InventoryService, Depends(get_inventory_service)]
CouponServiceDep = Annotated[CouponService, Depends(get_coupon_service)]
AfterSaleDep = Annotated[AfterSaleService, Depends(get_after_sale)]
ReviewServiceDep = Annotated[ReviewService, Depends(get_review_service)]
AnalyticsDep = Annotated[AnalyticsReader, Depends(get_analytics)]
StaffServiceDep = Annotated[StaffService, Depends(get_staff_service)]
