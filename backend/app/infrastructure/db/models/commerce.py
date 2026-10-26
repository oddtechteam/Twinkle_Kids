"""Carts, orders, WhatsApp order requests and the inventory ledger.

No payment gateway: payment_status/payment_method record manual bookkeeping only.
Order statuses are internal (admin workflow); there is no customer tracking timeline.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import (
    CartStatus,
    InventoryReason,
    NotificationChannel,
    NotificationStatus,
    OrderRequestKind,
    OrderRequestStatus,
    OrderSource,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    WhatsAppRequestStatus,
    sql_in,
)
from app.infrastructure.db.base import Base
from app.infrastructure.db.types import (
    JSONType,
    Money,
    UTCDateTime,
    created_at_column,
    updated_at_column,
    uuid_pk,
)


def _line_checks() -> tuple[CheckConstraint, ...]:
    """Fresh constraint objects per table (a Constraint can only belong to one Table)."""
    return (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("unit_selling_price >= 0", name="unit_price_non_negative"),
        CheckConstraint(
            "unit_original_price IS NULL OR unit_original_price >= unit_selling_price",
            name="unit_original_gte_selling",
        ),
        CheckConstraint("line_total = unit_selling_price * quantity", name="line_total_consistent"),
    )


class CartModel(Base):
    __tablename__ = "carts"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # Guest carts are identified by a hashed cookie token (never the raw token).
    guest_token_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(16), default="active", server_default="active")
    coupon_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("coupons.id", ondelete="SET NULL")
    )
    expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    __table_args__ = (
        CheckConstraint(f"status IN ({sql_in(CartStatus)})", name="status_valid"),
        CheckConstraint("user_id IS NOT NULL OR guest_token_hash IS NOT NULL", name="has_owner"),
        Index(
            "uq_carts_one_active_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'active' AND user_id IS NOT NULL"),
            sqlite_where=text("status = 'active' AND user_id IS NOT NULL"),
        ),
    )


class CartItemModel(Base):
    """Quantities only — prices are always resolved server-side from the catalogue."""

    __tablename__ = "cart_items"

    id: Mapped[uuid.UUID] = uuid_pk()
    cart_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"))
    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_variants.id", ondelete="CASCADE"), index=True
    )
    quantity: Mapped[int] = mapped_column(Integer)
    # Selling price shown when the item was added: only used to flag later price changes.
    unit_price_snapshot: Mapped[Decimal | None] = mapped_column(Money)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    __table_args__ = (
        UniqueConstraint("cart_id", "variant_id", name="uq_cart_items_cart_variant"),
        CheckConstraint("quantity BETWEEN 1 AND 99", name="quantity_range"),
        CheckConstraint(
            "unit_price_snapshot IS NULL OR unit_price_snapshot >= 0",
            name="unit_price_snapshot_non_negative",
        ),
    )


class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = uuid_pk()
    order_number: Mapped[str] = mapped_column(String(24), unique=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    source: Mapped[str] = mapped_column(String(16), default="website", server_default="website")
    status: Mapped[str] = mapped_column(
        String(24),
        default=OrderStatus.PENDING_CONFIRMATION.value,
        server_default=OrderStatus.PENDING_CONFIRMATION.value,
    )
    payment_status: Mapped[str] = mapped_column(
        String(24), default="unpaid", server_default="unpaid"
    )
    payment_method: Mapped[str | None] = mapped_column(String(24))
    customer_email: Mapped[str] = mapped_column(String(254))
    customer_name: Mapped[str] = mapped_column(String(120))
    customer_phone: Mapped[str] = mapped_column(String(20))
    shipping_address: Mapped[dict[str, Any]] = mapped_column(JSONType)  # snapshot
    currency_code: Mapped[str] = mapped_column(String(3), default="INR", server_default="INR")
    subtotal: Mapped[Decimal] = mapped_column(Money)
    discount_total: Mapped[Decimal] = mapped_column(Money, default=0, server_default="0")
    shipping_total: Mapped[Decimal] = mapped_column(Money, default=0, server_default="0")
    grand_total: Mapped[Decimal] = mapped_column(Money)
    coupon_code: Mapped[str | None] = mapped_column(String(40))  # snapshot
    customer_note: Mapped[str | None] = mapped_column(Text)
    internal_note: Mapped[str | None] = mapped_column(Text)
    # SHA-256 of (owner, client submission key): a resubmitted checkout returns the same order.
    idempotency_key: Mapped[str | None] = mapped_column(String(64), unique=True)
    placed_at: Mapped[datetime] = created_at_column()
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    __table_args__ = (
        CheckConstraint(f"status IN ({sql_in(OrderStatus)})", name="status_valid"),
        CheckConstraint(
            f"payment_status IN ({sql_in(PaymentStatus)})", name="payment_status_valid"
        ),
        CheckConstraint(
            f"payment_method IS NULL OR payment_method IN ({sql_in(PaymentMethod)})",
            name="payment_method_valid",
        ),
        CheckConstraint(f"source IN ({sql_in(OrderSource)})", name="source_valid"),
        CheckConstraint(
            "subtotal >= 0 AND discount_total >= 0 AND shipping_total >= 0",
            name="amounts_non_negative",
        ),
        CheckConstraint("discount_total <= subtotal", name="discount_lte_subtotal"),
        CheckConstraint(
            "grand_total = subtotal - discount_total + shipping_total",
            name="grand_total_consistent",
        ),
        Index("ix_orders_status_placed_at", "status", "placed_at"),
        Index("ix_orders_user_placed_at", "user_id", "placed_at"),
    )


class OrderItemModel(Base):
    """Immutable purchase snapshot: later catalogue edits never change historical orders."""

    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = uuid_pk()
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), index=True
    )
    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("product_variants.id", ondelete="SET NULL")
    )
    product_name: Mapped[str] = mapped_column(String(200))
    product_slug: Mapped[str | None] = mapped_column(String(160))
    sku: Mapped[str] = mapped_column(String(64))
    size: Mapped[str | None] = mapped_column(String(40))
    colour: Mapped[str | None] = mapped_column(String(40))
    image_url: Mapped[str | None] = mapped_column(String(1000))
    unit_selling_price: Mapped[Decimal] = mapped_column(Money)
    unit_original_price: Mapped[Decimal | None] = mapped_column(Money)
    quantity: Mapped[int] = mapped_column(Integer)
    line_total: Mapped[Decimal] = mapped_column(Money)
    created_at: Mapped[datetime] = created_at_column()

    __table_args__ = _line_checks()


class WhatsAppOrderRequestModel(Base):
    __tablename__ = "whatsapp_order_requests"

    id: Mapped[uuid.UUID] = uuid_pk()
    reference: Mapped[str] = mapped_column(String(24), unique=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    customer_name: Mapped[str | None] = mapped_column(String(120))
    customer_phone: Mapped[str | None] = mapped_column(String(20))
    message_text: Mapped[str] = mapped_column(Text)  # what was pre-filled, not proof of sending
    status: Mapped[str] = mapped_column(
        String(16),
        default=WhatsAppRequestStatus.INITIATED.value,
        server_default=WhatsAppRequestStatus.INITIATED.value,
    )
    estimated_subtotal: Mapped[Decimal] = mapped_column(Money)
    converted_order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL")
    )
    staff_note: Mapped[str | None] = mapped_column(Text)
    contacted_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    __table_args__ = (
        CheckConstraint(f"status IN ({sql_in(WhatsAppRequestStatus)})", name="status_valid"),
        CheckConstraint("estimated_subtotal >= 0", name="subtotal_non_negative"),
        CheckConstraint(
            "status <> 'converted' OR converted_order_id IS NOT NULL",
            name="converted_requires_order",
        ),
        Index("ix_whatsapp_order_requests_status_created", "status", "created_at"),
    )


class WhatsAppOrderRequestItemModel(Base):
    __tablename__ = "whatsapp_order_request_items"

    id: Mapped[uuid.UUID] = uuid_pk()
    request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("whatsapp_order_requests.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL")
    )
    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("product_variants.id", ondelete="SET NULL")
    )
    product_name: Mapped[str] = mapped_column(String(200))
    sku: Mapped[str] = mapped_column(String(64))
    size: Mapped[str | None] = mapped_column(String(40))
    colour: Mapped[str | None] = mapped_column(String(40))
    unit_selling_price: Mapped[Decimal] = mapped_column(Money)
    unit_original_price: Mapped[Decimal | None] = mapped_column(Money)
    quantity: Mapped[int] = mapped_column(Integer)
    line_total: Mapped[Decimal] = mapped_column(Money)

    __table_args__ = _line_checks()


class InventoryMovementModel(Base):
    """Append-only stock ledger. product_variants.stock_quantity is the running balance,
    updated in the same transaction as each movement (stock_after records it)."""

    __tablename__ = "inventory_movements"

    id: Mapped[uuid.UUID] = uuid_pk()
    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_variants.id", ondelete="CASCADE")
    )
    quantity_delta: Mapped[int] = mapped_column(Integer)
    stock_after: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(24))
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), index=True
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    note: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = created_at_column()

    __table_args__ = (
        CheckConstraint(f"reason IN ({sql_in(InventoryReason)})", name="reason_valid"),
        CheckConstraint("quantity_delta <> 0", name="delta_non_zero"),
        CheckConstraint("stock_after >= 0", name="stock_after_non_negative"),
        Index("ix_inventory_movements_variant_created", "variant_id", "created_at"),
    )


class OrderRequestModel(Base):
    """Cancellation, return or exchange request against an order (customer- or staff-raised).

    No refunds happen automatically (there is no payment gateway): `refund_amount` records what
    staff actually refunded, and stock is only added back when returned goods are verified.
    """

    __tablename__ = "order_requests"

    id: Mapped[uuid.UUID] = uuid_pk()
    reference: Mapped[str] = mapped_column(String(24), unique=True)
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    kind: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(
        String(16),
        default=OrderRequestStatus.REQUESTED.value,
        server_default=OrderRequestStatus.REQUESTED.value,
    )
    reason: Mapped[str] = mapped_column(String(40))
    customer_message: Mapped[str | None] = mapped_column(Text)
    items: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONType, default=list, server_default=text("'[]'")
    )  # [{"order_item_id": "...", "quantity": 1}]
    resolution_note: Mapped[str | None] = mapped_column(Text)
    refund_amount: Mapped[Decimal | None] = mapped_column(Money)
    restocked: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    created_by_staff: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    __table_args__ = (
        CheckConstraint(f"kind IN ({sql_in(OrderRequestKind)})", name="kind_valid"),
        CheckConstraint(f"status IN ({sql_in(OrderRequestStatus)})", name="status_valid"),
        CheckConstraint("refund_amount IS NULL OR refund_amount >= 0", name="refund_non_negative"),
        Index("ix_order_requests_status_created", "status", "created_at"),
    )


class NotificationModel(Base):
    """Delivery attempts. Message bodies are not stored (they may contain reset links)."""

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = uuid_pk()
    channel: Mapped[str] = mapped_column(String(16))
    template: Mapped[str] = mapped_column(String(40))
    recipient: Mapped[str] = mapped_column(String(254))
    subject: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(16))
    provider: Mapped[str | None] = mapped_column(String(40))
    provider_message_id: Mapped[str | None] = mapped_column(String(200))
    error: Mapped[str | None] = mapped_column(String(300))
    entity_type: Mapped[str | None] = mapped_column(String(40))
    entity_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = created_at_column()

    __table_args__ = (
        CheckConstraint(f"channel IN ({sql_in(NotificationChannel)})", name="channel_valid"),
        CheckConstraint(f"status IN ({sql_in(NotificationStatus)})", name="status_valid"),
        Index("ix_notifications_created_at", "created_at"),
    )
