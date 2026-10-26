"""Contracts for inventory, coupons, after-sale requests, reviews, analytics, staff and logs."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.api.schemas.catalog import ImageOut
from app.application.use_cases.coupons import CouponInput, CouponUsage
from app.application.use_cases.inventory import InventoryRow
from app.domain.entities.identity import Role
from app.domain.enums import (
    DiscountType,
    InventoryReason,
    NotificationChannel,
    NotificationStatus,
    OrderRequestKind,
    OrderRequestStatus,
    ReviewStatus,
)

Note = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PageOut[T](BaseModel):
    items: list[T]
    total: int
    page: int
    pages: int


# --- inventory --------------------------------------------------------------------------------


class InventoryRowOut(BaseModel):
    variant_id: UUID
    product_id: UUID
    product_name: str
    product_status: str
    sku: str
    size: str | None
    colour: str | None
    stock_quantity: int
    low_stock_threshold: int
    track_inventory: bool
    allow_backorder: bool
    is_active: bool
    state: str

    @classmethod
    def of(cls, row: InventoryRow) -> "InventoryRowOut":
        return cls(
            variant_id=row.variant_id,
            product_id=row.product_id,
            product_name=row.product_name,
            product_status=row.product_status,
            sku=row.sku,
            size=row.size,
            colour=row.colour,
            stock_quantity=row.stock_quantity,
            low_stock_threshold=row.low_stock_threshold,
            track_inventory=row.track_inventory,
            allow_backorder=row.allow_backorder,
            is_active=row.is_active,
            state=row.state,
        )


class AdjustStockIn(_In):
    delta: int = Field(ge=-10_000, le=10_000)
    reason: InventoryReason
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = None


class MovementOut(_Out):
    id: UUID
    variant_id: UUID
    sku: str
    product_name: str
    quantity_delta: int
    stock_after: int
    reason: InventoryReason
    note: str | None
    order_number: str | None
    actor_email: str | None
    created_at: datetime


# --- coupons ----------------------------------------------------------------------------------


class CouponIn(_In):
    code: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=40)]
    description: Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)] | None = (
        None
    )
    discount_type: DiscountType
    discount_value: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    is_active: bool = True
    min_order_amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    max_discount_amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    usage_limit: int | None = Field(default=None, ge=1, le=1_000_000)
    per_user_limit: int | None = Field(default=None, ge=1, le=1000)
    product_ids: list[UUID] = Field(default_factory=list, max_length=500)
    category_ids: list[UUID] = Field(default_factory=list, max_length=200)
    collection_ids: list[UUID] = Field(default_factory=list, max_length=200)

    def to_input(self) -> CouponInput:
        return CouponInput(**self.model_dump())


class ActiveIn(_In):
    is_active: bool


class CouponOut(BaseModel):
    id: UUID
    code: str
    description: str | None
    discount_type: DiscountType
    discount_value: Decimal
    is_active: bool
    min_order_amount: Decimal | None
    max_discount_amount: Decimal | None
    starts_at: datetime | None
    ends_at: datetime | None
    usage_limit: int | None
    per_user_limit: int | None
    product_ids: list[UUID]
    category_ids: list[UUID]
    collection_ids: list[UUID]
    times_used: int = 0
    discount_given: Decimal = Decimal("0.00")

    @classmethod
    def of(cls, usage: CouponUsage) -> "CouponOut":
        c = usage.coupon
        return cls(
            id=c.id,
            code=c.code,
            description=c.description,
            discount_type=c.discount_type,
            discount_value=c.discount_value,
            is_active=c.is_active,
            min_order_amount=c.min_order_amount,
            max_discount_amount=c.max_discount_amount,
            starts_at=c.starts_at,
            ends_at=c.ends_at,
            usage_limit=c.usage_limit,
            per_user_limit=c.per_user_limit,
            product_ids=sorted(c.scope.product_ids, key=str),
            category_ids=sorted(c.scope.category_ids, key=str),
            collection_ids=sorted(c.scope.collection_ids, key=str),
            times_used=usage.times_used,
            discount_given=usage.discount_given,
        )


# --- after-sale requests ------------------------------------------------------------------------


class RequestItemIO(_In):
    sku: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
    quantity: int = Field(ge=1, le=99)


class OrderRequestIn(_In):
    kind: OrderRequestKind
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
    message: Note | None = None
    items: list[RequestItemIO] = Field(default_factory=list, max_length=50)


class RequestItemOut(_Out):
    sku: str
    quantity: int


class OrderRequestOut(_Out):
    id: UUID
    reference: str
    order_id: UUID
    order_number: str
    kind: OrderRequestKind
    status: OrderRequestStatus
    reason: str
    customer_message: str | None
    items: list[RequestItemOut]
    resolution_note: str | None
    refund_amount: Decimal | None
    restocked: bool
    created_by_staff: bool
    created_at: datetime
    updated_at: datetime


class CustomerRequestOut(_Out):
    """A customer's own request: what they asked for and the shop's decision."""

    reference: str
    kind: OrderRequestKind
    status: OrderRequestStatus
    reason: str
    customer_message: str | None
    resolution_note: str | None
    created_at: datetime


class DecisionIn(_In):
    approve: bool
    note: Note | None = None


class ReceivedIn(_In):
    restock: bool
    note: Note | None = None


class CompleteIn(_In):
    refund_amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    note: Note | None = None


# --- reviews ----------------------------------------------------------------------------------


class ModerationOut(_Out):
    id: UUID
    product_id: UUID
    product_name: str
    product_slug: str
    rating: int
    title: str | None
    body: str | None
    author_name: str | None
    author_email: str | None
    is_verified_purchase: bool
    status: ReviewStatus
    moderation_note: str | None
    images: list[ImageOut]
    created_at: datetime


class ModerateIn(_In):
    status: ReviewStatus
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = None


# --- analytics --------------------------------------------------------------------------------


class DayPointOut(_Out):
    day: date
    website_orders: int
    whatsapp_orders: int
    order_value: Decimal


class ProductPerformanceOut(_Out):
    product_id: str | None
    product_name: str
    units: int
    order_value: Decimal


class CategoryPerformanceOut(_Out):
    category: str
    units: int
    order_value: Decimal


class CouponUsageOut(_Out):
    code: str
    redemptions: int
    discount_given: Decimal


class AnalyticsOut(_Out):
    start: date
    end: date
    orders_placed: int
    orders_cancelled: int
    website_orders: int
    whatsapp_orders: int
    order_value_placed: Decimal
    payments_recorded: Decimal
    refunds_recorded: Decimal
    average_order_value: Decimal | None
    whatsapp_requests: int
    whatsapp_contacted: int
    whatsapp_converted: int
    by_day: list[DayPointOut]
    top_products: list[ProductPerformanceOut]
    categories: list[CategoryPerformanceOut]
    coupons: list[CouponUsageOut]


# --- staff, audit, notifications ----------------------------------------------------------------


class StaffOut(_Out):
    id: UUID
    email: str
    full_name: str
    roles: list[str]
    is_active: bool
    last_login_at: datetime | None


class StaffRolesIn(_In):
    email: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=254)]
    roles: list[Role] = Field(max_length=3)


class AuditEntryOut(_Out):
    id: str
    action: str
    entity_type: str
    entity_id: str | None
    actor_email: str | None
    changes: dict[str, Any] | None
    ip_address: str | None
    created_at: datetime


class NotificationOut(_Out):
    id: UUID
    channel: NotificationChannel
    template: str
    recipient: str
    subject: str | None
    status: NotificationStatus
    provider: str | None
    error: str | None
    entity_type: str | None
    entity_id: str | None
    created_at: datetime | None
