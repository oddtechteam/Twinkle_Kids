"""Service interfaces the application layer depends on (implemented in infrastructure)."""

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from app.application.dto.catalog import (
    CategoryDetail,
    CategorySummary,
    CollectionSummary,
    ImageView,
    Page,
    ProductDetail,
    ProductFilters,
    ProductSummary,
)


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password_hash: str, password: str) -> bool: ...

    def needs_rehash(self, password_hash: str) -> bool: ...


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
