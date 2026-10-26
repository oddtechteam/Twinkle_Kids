"""Read models for orders and WhatsApp order requests."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.domain.enums import (
    OrderSource,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    WhatsAppRequestStatus,
)


@dataclass(frozen=True, slots=True)
class OrderLineView:
    product_name: str
    product_slug: str | None
    sku: str
    size: str | None
    colour: str | None
    image_url: str | None
    unit_selling_price: Decimal
    unit_original_price: Decimal | None
    quantity: int
    line_total: Decimal


@dataclass(frozen=True, slots=True)
class OrderView:
    id: UUID
    order_number: str
    user_id: UUID | None
    source: OrderSource
    status: OrderStatus
    payment_status: PaymentStatus
    payment_method: PaymentMethod | None
    customer_name: str
    customer_email: str
    customer_phone: str
    shipping_address: dict[str, Any]
    currency_code: str
    subtotal: Decimal
    discount_total: Decimal
    shipping_total: Decimal
    grand_total: Decimal
    coupon_code: str | None
    customer_note: str | None
    internal_note: str | None
    placed_at: datetime
    lines: list[OrderLineView]


@dataclass(frozen=True, slots=True)
class OrderSummary:
    id: UUID
    order_number: str
    source: OrderSource
    status: OrderStatus
    payment_status: PaymentStatus
    payment_method: PaymentMethod | None
    customer_name: str
    grand_total: Decimal
    item_count: int
    placed_at: datetime


@dataclass(frozen=True, slots=True)
class OrderFilters:
    page: int = 1
    page_size: int = 25
    status: OrderStatus | None = None
    source: OrderSource | None = None
    payment_status: PaymentStatus | None = None
    search: str | None = None  # order number, customer name, email or phone


@dataclass(frozen=True, slots=True)
class WhatsAppLineView:
    variant_id: UUID | None
    product_name: str
    sku: str
    size: str | None
    colour: str | None
    unit_selling_price: Decimal
    quantity: int
    line_total: Decimal


@dataclass(frozen=True, slots=True)
class WhatsAppRequestView:
    id: UUID
    reference: str
    status: WhatsAppRequestStatus
    user_id: UUID | None
    customer_name: str | None
    customer_phone: str | None
    message_text: str
    estimated_subtotal: Decimal
    staff_note: str | None
    contacted_at: datetime | None
    created_at: datetime
    converted_order_id: UUID | None
    converted_order_number: str | None
    lines: list[WhatsAppLineView]


@dataclass(frozen=True, slots=True)
class WhatsAppRequestSummary:
    id: UUID
    reference: str
    status: WhatsAppRequestStatus
    customer_name: str | None
    estimated_subtotal: Decimal
    item_count: int
    created_at: datetime
    converted_order_number: str | None
