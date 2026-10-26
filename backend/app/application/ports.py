"""Service interfaces the application layer depends on (implemented in infrastructure)."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.application.dto.catalog import (
    CatalogFacets,
    CategoryDetail,
    CategorySummary,
    CollectionSummary,
    ImageView,
    Page,
    ProductDetail,
    ProductFilters,
    ProductSummary,
    ReviewSummary,
    SitemapView,
)
from app.application.dto.orders import (
    OrderFilters,
    OrderSummary,
    OrderView,
    WhatsAppRequestSummary,
    WhatsAppRequestView,
)
from app.domain.enums import WhatsAppRequestStatus


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password_hash: str, password: str) -> bool: ...

    def needs_rehash(self, password_hash: str) -> bool: ...


@dataclass(frozen=True, slots=True)
class DeliveryReceipt:
    """What a delivery provider reported. `accepted` only when it confirmed the hand-off."""

    accepted: bool
    provider: str | None
    message_id: str | None = None
    error: str | None = None
    skipped: bool = False  # channel not configured / development stand-in


class Mailer(Protocol):
    """Transactional email delivery (plain text)."""

    def send(self, *, to: str, subject: str, text: str) -> DeliveryReceipt: ...


class RateLimiter(Protocol):
    def hit(self, key: str, *, limit: int, window_seconds: int) -> int | None:
        """Record an attempt. Returns seconds to wait if the limit is exceeded, else None."""
        ...

    def reset(self, key: str) -> None: ...


class CatalogQueries(Protocol):
    """Read side of the catalogue (storefront and admin listings)."""

    def list_products(self, filters: ProductFilters) -> Page[ProductSummary]: ...

    def get_product(
        self, *, slug: str | None = None, product_id: UUID | None = None, admin_view: bool = False
    ) -> ProductDetail | None:
        """Storefront view (active only) by default; admin_view includes drafts and stock."""
        ...

    def list_categories(self, *, include_inactive: bool = False) -> Sequence[CategorySummary]: ...

    def get_category(self, slug: str) -> CategoryDetail | None: ...

    def ordered_products(
        self, product_ids: Sequence[UUID], *, include_inactive: bool = False
    ) -> Sequence[ProductSummary]:
        """Products for the given ids, preserving the given order (active only by default)."""
        ...

    def list_collections(
        self, *, ids: Sequence[UUID] | None = None, published_only: bool = True
    ) -> Sequence[CollectionSummary]: ...

    def get_collection(self, slug: str) -> CollectionSummary | None:
        """Published collection by slug (public)."""
        ...

    def images(self, media_ids: Sequence[UUID]) -> dict[UUID, ImageView]: ...

    def facets(self, filters: ProductFilters) -> CatalogFacets:
        """Size/colour/price options for the listing scope described by ``filters``."""
        ...

    def product_reviews(self, product_id: UUID, *, limit: int = 20) -> ReviewSummary:
        """Approved reviews only, newest first."""
        ...

    def sitemap(self) -> SitemapView: ...


class OrderQueries(Protocol):
    """Read side of orders and WhatsApp requests (customer history and admin screens)."""

    def order(
        self, *, order_id: UUID | None = None, number: str | None = None
    ) -> OrderView | None: ...

    def orders(self, filters: OrderFilters) -> Page[OrderSummary]: ...

    def orders_for_user(
        self, user_id: UUID, *, page: int, page_size: int
    ) -> Page[OrderSummary]: ...

    def whatsapp_request(self, request_id: UUID) -> WhatsAppRequestView | None: ...

    def whatsapp_requests(
        self,
        *,
        status: WhatsAppRequestStatus | None,
        search: str | None,
        page: int,
        page_size: int,
    ) -> Page[WhatsAppRequestSummary]: ...


class RecommendationQueries(Protocol):
    def bestseller_ids(
        self, *, limit: int, days: int = 90, category_slug: str | None = None
    ) -> list[UUID]:
        """Active products ranked by units in placed, non-cancelled orders."""
        ...

    def featured_ids(self, *, limit: int) -> list[UUID]: ...

    def related_ids(self, product_id: UUID) -> list[UUID]:
        """The admin-curated related products for a product, in order."""
        ...
