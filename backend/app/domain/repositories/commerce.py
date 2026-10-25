from decimal import Decimal
from typing import Protocol
from uuid import UUID

from app.domain.entities.commerce import Cart, WhatsAppOrderRequest


class CartRepository(Protocol):
    """Active carts, owned by a customer account or by a hashed guest-cookie token."""

    def find_active(
        self, *, user_id: UUID | None = None, guest_token_hash: str | None = None
    ) -> Cart | None: ...

    def create(self, *, user_id: UUID | None, guest_token_hash: str | None) -> Cart: ...

    def add_item(
        self,
        cart_id: UUID,
        *,
        variant_id: UUID,
        quantity: int,
        unit_price_snapshot: Decimal | None,
    ) -> None: ...

    def update_item(
        self, item_id: UUID, *, quantity: int, unit_price_snapshot: Decimal | None = None
    ) -> None: ...

    def remove_item(self, item_id: UUID) -> None: ...

    def set_snapshots(self, prices: dict[UUID, Decimal]) -> None:
        """Record the currently shown selling price per cart item id."""
        ...

    def assign_to_user(self, cart_id: UUID, user_id: UUID) -> None:
        """Turn a guest cart into the customer's cart (drops the guest token)."""
        ...

    def delete(self, cart_id: UUID) -> None: ...

    def product_ids_for_variants(self, variant_ids: list[UUID]) -> dict[UUID, UUID]:
        """variant id -> product id for the variants that exist."""
        ...


class WhatsAppRequestRepository(Protocol):
    def add(self, request: WhatsAppOrderRequest) -> None: ...

    def reference_taken(self, reference: str) -> bool: ...
