"""Storefront / admin catalogue reads."""

from collections.abc import Sequence
from uuid import UUID

from app.application.dto.catalog import (
    MAX_PAGE_SIZE,
    CatalogFacets,
    CategoryDetail,
    CategorySummary,
    CollectionSummary,
    Page,
    ProductDetail,
    ProductFilters,
    ProductSummary,
    Recommendations,
    ReviewSummary,
    SitemapView,
)
from app.application.ports import CatalogQueries, RecommendationQueries
from app.domain.errors import DomainValidationError, NotFoundError


class CatalogReader:
    def __init__(
        self, queries: CatalogQueries, recommendations: RecommendationQueries | None = None
    ) -> None:
        self._queries = queries
        self._recommendations = recommendations

    def recommendations(self, slug: str, *, limit: int = 8) -> Recommendations:
        """Admin-curated picks first; bestsellers in the same category from real order data."""
        detail = self.product(slug)
        if self._recommendations is None:
            return Recommendations(curated=[], bestsellers=[])
        curated = [
            p
            for p in self._queries.ordered_products(self._recommendations.related_ids(detail.id))
            if p.id != detail.id
        ][:limit]
        bestsellers: list[ProductSummary] = []
        if detail.categories:
            ids = self._recommendations.bestseller_ids(
                limit=limit + 1, category_slug=detail.categories[0].slug
            )
            seen = {p.id for p in curated} | {detail.id}
            bestsellers = [p for p in self._queries.ordered_products(ids) if p.id not in seen][
                :limit
            ]
        return Recommendations(curated=curated, bestsellers=bestsellers)

    def list_products(self, filters: ProductFilters) -> Page[ProductSummary]:
        if filters.page < 1:
            raise DomainValidationError("Page must be 1 or greater.")
        if not 1 <= filters.page_size <= MAX_PAGE_SIZE:
            raise DomainValidationError(f"Page size must be between 1 and {MAX_PAGE_SIZE}.")
        if (
            filters.min_price is not None
            and filters.max_price is not None
            and filters.min_price > filters.max_price
        ):
            raise DomainValidationError("Minimum price cannot exceed maximum price.")
        return self._queries.list_products(filters)

    def facets(self, filters: ProductFilters) -> CatalogFacets:
        return self._queries.facets(filters)

    def reviews(self, slug: str) -> ReviewSummary:
        detail = self._queries.get_product(slug=slug)
        if detail is None:
            raise NotFoundError("Product not found.")
        return self._queries.product_reviews(detail.id)

    def sitemap(self) -> SitemapView:
        return self._queries.sitemap()

    def collections(self) -> Sequence[CollectionSummary]:
        """Published collections in display order (storefront filters and navigation)."""
        return self._queries.list_collections(published_only=True)

    def product(self, slug: str) -> ProductDetail:
        detail = self._queries.get_product(slug=slug)
        if detail is None:
            raise NotFoundError("Product not found.")
        return detail

    def admin_product(self, product_id: UUID) -> ProductDetail:
        detail = self._queries.get_product(product_id=product_id, admin_view=True)
        if detail is None:
            raise NotFoundError("Product not found.")
        return detail

    def ordered(self, product_ids: Sequence[UUID]) -> Sequence[ProductSummary]:
        """Admin ordering views: every listed product (drafts included), in the given order."""
        return self._queries.ordered_products(product_ids, include_inactive=True)

    def collection(self, slug: str) -> CollectionSummary:
        found = self._queries.get_collection(slug)
        if found is None:
            raise NotFoundError("Collection not found.")
        return found

    def categories(self, *, include_inactive: bool = False) -> Sequence[CategorySummary]:
        return self._queries.list_categories(include_inactive=include_inactive)

    def category(self, slug: str) -> CategoryDetail:
        detail = self._queries.get_category(slug)
        if detail is None:
            raise NotFoundError("Category not found.")
        return detail
