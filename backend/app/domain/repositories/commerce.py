from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from app.domain.entities.commerce import Cart, WhatsAppOrderRequest
from app.domain.entities.order import Coupon, NewOrder
from app.domain.enums import OrderStatus, PaymentMethod, PaymentStatus, WhatsAppRequestStatus


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

    def mark_converted(self, cart_id: UUID) -> None:
        """The cart became an order: it is no longer the shopper's active bag."""
        ...

    def product_ids_for_variants(self, variant_ids: list[UUID]) -> dict[UUID, UUID]:
        """variant id -> product id for the variants that exist."""
        ...


class WhatsAppRequestRepository(Protocol):
    def add(self, request: WhatsAppOrderRequest) -> None: ...

    def reference_taken(self, reference: str) -> bool: ...

    def status(self, request_id: UUID) -> WhatsAppRequestStatus | None: ...

    def items(self, request_id: UUID) -> list[tuple[UUID | None, int]]:
        """(variant id, quantity) per recorded line; variant id is None if since deleted."""
        ...

    def set_status(
        self,
        request_id: UUID,
        status: WhatsAppRequestStatus,
        *,
        staff_note: str | None,
        contacted_at: datetime | None = None,
    ) -> None: ...

    def mark_converted(self, request_id: UUID, order_id: UUID) -> bool:
        """Atomically convert (only from a convertible status). False if already handled."""
        ...


class OrderRepository(Protocol):
    def id_for_idempotency_key(self, key: str) -> UUID | None: ...

    def number_taken(self, order_number: str) -> bool: ...

    def add(self, order: NewOrder) -> None: ...

    def deduct_stock(self, variant_id: UUID, quantity: int) -> int | None:
        """Atomically remove stock if enough is available; the new balance, or None."""
        ...

    def restock(self, variant_id: UUID, quantity: int) -> int:
        """Atomically add stock back; returns the new balance."""
        ...

    def status(self, order_id: UUID) -> OrderStatus | None: ...

    def lines_for_restock(self, order_id: UUID) -> list[tuple[UUID, int]]:
        """(variant id, quantity) for lines whose variant still exists."""
        ...

    def lines_with_sku(self, order_id: UUID) -> list[tuple[UUID, str, int]]:
        """(variant id, SKU, quantity) for lines whose variant still exists."""
        ...

    def set_status(self, order_id: UUID, status: OrderStatus) -> None: ...

    def set_payment(
        self, order_id: UUID, status: PaymentStatus, method: PaymentMethod | None
    ) -> None: ...

    def set_internal_note(self, order_id: UUID, note: str | None) -> None: ...


class CouponRepository(Protocol):
    def get_by_code(self, code: str) -> Coupon | None: ...

    def get(self, coupon_id: UUID) -> Coupon | None: ...

    def list(self) -> list[tuple[Coupon, int, Decimal]]:
        """Every coupon with (times used, total discount given)."""
        ...

    def add(self, coupon: Coupon) -> None: ...

    def save(self, coupon: Coupon) -> None: ...

    def code_taken(self, code: str, *, exclude_id: UUID | None = None) -> bool: ...

    def times_used(self, coupon_id: UUID) -> int: ...

    def times_used_by(self, coupon_id: UUID, user_id: UUID) -> int: ...

    def record_redemption(
        self, *, coupon_id: UUID, order_id: UUID, user_id: UUID | None, amount: Decimal
    ) -> None: ...
