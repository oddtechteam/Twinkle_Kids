from collections.abc import Iterable
from typing import Protocol
from uuid import UUID

from app.domain.entities.catalog import Category, Product
from app.domain.entities.content import Collection
from app.domain.enums import InventoryReason


class ProductRepository(Protocol):
    def get(self, product_id: UUID) -> Product | None: ...

    def add(self, product: Product) -> None: ...

    def save(self, product: Product) -> None:
        """Persist the whole aggregate: scalar fields, variants, category links and media."""
        ...

    def slug_taken(self, slug: str, *, exclude_id: UUID | None = None) -> bool: ...

    def skus_taken(
        self, skus: Iterable[str], *, exclude_product_id: UUID | None = None
    ) -> set[str]:
        """Product or variant SKUs already used by another product."""
        ...

    def existing_ids(self, ids: Iterable[UUID]) -> set[UUID]: ...


class CategoryRepository(Protocol):
    def get(self, category_id: UUID) -> Category | None: ...

    def add(self, category: Category) -> None: ...

    def save(self, category: Category) -> None: ...

    def slug_taken(self, slug: str, *, exclude_id: UUID | None = None) -> bool: ...

    def existing_ids(self, ids: Iterable[UUID]) -> set[UUID]: ...

    def ancestor_ids(self, category_id: UUID) -> list[UUID]: ...

    def set_product_order(self, category_id: UUID, product_ids: list[UUID]) -> None:
        """Order the listed members first; the rest keep their relative order after them."""
        ...

    def product_ids(self, category_id: UUID) -> list[UUID]: ...


class CollectionRepository(Protocol):
    def get(self, collection_id: UUID) -> Collection | None: ...

    def add(self, collection: Collection) -> None: ...

    def slug_taken(self, slug: str) -> bool: ...

    def set_products(self, collection_id: UUID, product_ids: list[UUID]) -> None:
        """Replace membership and ordering in one step (list index = position)."""
        ...

    def product_ids(self, collection_id: UUID) -> list[UUID]: ...


class InventoryLedger(Protocol):
    """Append-only stock movements; the variant's stock_quantity is the running balance."""

    def record(
        self,
        *,
        variant_id: UUID,
        delta: int,
        stock_after: int,
        reason: InventoryReason,
        actor_user_id: UUID | None,
        note: str | None = None,
        order_id: UUID | None = None,
    ) -> None: ...
