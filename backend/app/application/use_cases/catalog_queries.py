"""Storefront / admin catalogue reads."""

from collections.abc import Sequence
from uuid import UUID

from app.application.dto.catalog import (
    MAX_PAGE_SIZE,
    CategoryDetail,
    CategorySummary,
    Page,
    ProductDetail,
    ProductFilters,
    ProductSummary,
)
from app.application.ports import CatalogQueries
from app.domain.errors import DomainValidationError, NotFoundError


class CatalogReader:
    def __init__(self, queries: CatalogQueries) -> None:
        self._queries = queries

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

    def categories(self, *, include_inactive: bool = False) -> Sequence[CategorySummary]:
        return self._queries.list_categories(include_inactive=include_inactive)

    def category(self, slug: str) -> CategoryDetail:
        detail = self._queries.get_category(slug)
        if detail is None:
            raise NotFoundError("Category not found.")
        return detail
