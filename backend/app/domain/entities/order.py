"""Orders (website checkout and confirmed WhatsApp requests) and coupons.

Payment is always recorded manually by staff — there is no payment gateway, and nothing here
ever marks an order as paid. Statuses are an internal admin workflow; customers are never
shown a tracking timeline.
"""

import re
import secrets
from dataclasses import dataclass, field
from datetime import datetime
from decimal import ROUND_FLOOR, Decimal
from typing import Any
from uuid import UUID

from app.domain.entities.commerce import OrderLineSnapshot
from app.domain.enums import (
    DiscountType,
    OrderSource,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    WhatsAppRequestStatus,
)
from app.domain.errors import DomainValidationError
from app.domain.value_objects.pricing import CENT, OrderTotals

ORDER_NUMBER_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

# Internal workflow. Cancelling or returning puts the stock back.
ORDER_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.PENDING_CONFIRMATION: frozenset({OrderStatus.CONFIRMED, OrderStatus.CANCELLED}),
    OrderStatus.CONFIRMED: frozenset({OrderStatus.PROCESSING, OrderStatus.CANCELLED}),
    OrderStatus.PROCESSING: frozenset({OrderStatus.PACKED, OrderStatus.CANCELLED}),
    OrderStatus.PACKED: frozenset({OrderStatus.SHIPPED, OrderStatus.CANCELLED}),
    OrderStatus.SHIPPED: frozenset({OrderStatus.DELIVERED, OrderStatus.RETURNED}),
    OrderStatus.DELIVERED: frozenset({OrderStatus.RETURNED}),
    OrderStatus.CANCELLED: frozenset(),
    OrderStatus.RETURNED: frozenset(),
}
# Cancelled orders never left the shop, so their stock goes straight back. Returned goods are
# only restocked when an after-sale request records them as received and verified.
RESTOCKING_STATUSES = frozenset({OrderStatus.CANCELLED})

# WhatsApp request workflow (staff actions). `initiated` = link handed out, nothing more.
WHATSAPP_TRANSITIONS: dict[WhatsAppRequestStatus, frozenset[WhatsAppRequestStatus]] = {
    WhatsAppRequestStatus.INITIATED: frozenset(
        {
            WhatsAppRequestStatus.CONTACTED,
            WhatsAppRequestStatus.CANCELLED,
            WhatsAppRequestStatus.EXPIRED,
        }
    ),
    WhatsAppRequestStatus.CONTACTED: frozenset(
        {WhatsAppRequestStatus.CANCELLED, WhatsAppRequestStatus.EXPIRED}
    ),
    WhatsAppRequestStatus.CONVERTED: frozenset(),
    WhatsAppRequestStatus.CANCELLED: frozenset(),
    WhatsAppRequestStatus.EXPIRED: frozenset(),
}
CONVERTIBLE_WHATSAPP_STATUSES = frozenset(
    {WhatsAppRequestStatus.INITIATED, WhatsAppRequestStatus.CONTACTED}
)


def ensure_order_transition(current: OrderStatus, target: OrderStatus) -> None:
    if target not in ORDER_TRANSITIONS[current]:
        raise DomainValidationError(
            f"An order that is {current.value.replace('_', ' ')} can't be moved to "
            f"{target.value.replace('_', ' ')}."
        )


def ensure_whatsapp_transition(
    current: WhatsAppRequestStatus, target: WhatsAppRequestStatus
) -> None:
    if target not in WHATSAPP_TRANSITIONS[current]:
        raise DomainValidationError(
            f"A WhatsApp request that is {current.value} can't be marked {target.value}."
        )


def new_order_number(placed_at: datetime) -> str:
    """e.g. TK261025-7KQ2M — date for staff convenience, random suffix so it can't be guessed."""
    suffix = "".join(secrets.choice(ORDER_NUMBER_ALPHABET) for _ in range(5))
    return f"TK{placed_at:%y%m%d}-{suffix}"


COUPON_CODE = re.compile(r"^[A-Z0-9][A-Z0-9_-]{2,39}$")


@dataclass(frozen=True, slots=True)
class CouponScope:
    """Where a coupon applies. All empty = the whole order."""

    product_ids: frozenset[UUID] = frozenset()
    category_ids: frozenset[UUID] = frozenset()
    collection_ids: frozenset[UUID] = frozenset()

    @property
    def whole_order(self) -> bool:
        return not (self.product_ids or self.category_ids or self.collection_ids)

    def covers(self, product_id: UUID, categories: set[UUID], collections: set[UUID]) -> bool:
        return (
            self.whole_order
            or product_id in self.product_ids
            or bool(categories & self.category_ids)
            or bool(collections & self.collection_ids)
        )


@dataclass(frozen=True, slots=True)
class Coupon:
    id: UUID
    code: str
    discount_type: DiscountType
    discount_value: Decimal
    is_active: bool = True
    min_order_amount: Decimal | None = None
    max_discount_amount: Decimal | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    usage_limit: int | None = None
    per_user_limit: int | None = None
    scope: CouponScope = field(default_factory=CouponScope)
    description: str | None = None

    def validate(self) -> None:
        if not COUPON_CODE.fullmatch(self.code):
            raise DomainValidationError(
                "Codes are 3–40 characters: capital letters, numbers, - or _."  # noqa: RUF001 - intended typography
            )
        if self.discount_value <= 0:
            raise DomainValidationError("The discount must be more than zero.")
        if self.discount_type is DiscountType.PERCENTAGE and self.discount_value > 100:
            raise DomainValidationError("A percentage discount can't exceed 100%.")
        if self.min_order_amount is not None and self.min_order_amount < 0:
            raise DomainValidationError("The minimum order can't be negative.")
        if self.max_discount_amount is not None and self.max_discount_amount <= 0:
            raise DomainValidationError("The maximum discount must be more than zero.")
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise DomainValidationError("The end date must be after the start date.")
        for limit in (self.usage_limit, self.per_user_limit):
            if limit is not None and limit < 1:
                raise DomainValidationError("Usage limits must be at least 1.")

    def discount_for(
        self,
        subtotal: Decimal,
        *,
        now: datetime,
        times_used: int,
        times_used_by_customer: int | None,
        eligible_subtotal: Decimal | None = None,
    ) -> Decimal:
        """The discount this coupon gives, or a customer-facing error.

        `subtotal` is the whole order (for the minimum-order rule); the discount is calculated
        on `eligible_subtotal` — the lines the coupon applies to — and never exceeds it.
        """
        invalid = DomainValidationError(f"The code {self.code} isn't valid right now.")
        if not self.is_active:
            raise invalid
        if (self.starts_at and now < self.starts_at) or (self.ends_at and now >= self.ends_at):
            raise invalid
        if self.usage_limit is not None and times_used >= self.usage_limit:
            raise DomainValidationError(f"The code {self.code} has been fully used.")
        if self.per_user_limit is not None:
            if times_used_by_customer is None:
                raise DomainValidationError(f"Sign in to use the code {self.code}.")
            if times_used_by_customer >= self.per_user_limit:
                raise DomainValidationError(f"You've already used the code {self.code}.")
        if self.min_order_amount is not None and subtotal < self.min_order_amount:
            raise DomainValidationError(
                f"The code {self.code} needs an order of at least ₹{self.min_order_amount:,.2f}."
            )
        base = subtotal if eligible_subtotal is None else min(eligible_subtotal, subtotal)
        if base <= 0:
            raise DomainValidationError(
                f"The code {self.code} doesn't apply to the items in your bag."
            )
        if self.discount_type is DiscountType.PERCENTAGE:
            amount = (base * self.discount_value / Decimal(100)).quantize(
                CENT, rounding=ROUND_FLOOR
            )
        else:
            amount = self.discount_value
        if self.max_discount_amount is not None:
            amount = min(amount, self.max_discount_amount)
        return min(amount, base).quantize(CENT)  # never more than the eligible items cost


@dataclass(frozen=True, slots=True)
class NewOrder:
    """Everything persisted when an order is created. Lines are immutable snapshots."""

    id: UUID
    order_number: str
    user_id: UUID | None
    source: OrderSource
    customer_name: str
    customer_email: str
    customer_phone: str
    shipping_address: dict[str, Any]
    lines: tuple[OrderLineSnapshot, ...]
    totals: OrderTotals
    payment_method: PaymentMethod
    placed_at: datetime
    status: OrderStatus = OrderStatus.PENDING_CONFIRMATION
    payment_status: PaymentStatus = PaymentStatus.UNPAID  # never paid on creation
    coupon_id: UUID | None = None
    coupon_code: str | None = None
    customer_note: str | None = None
    idempotency_key: str | None = None
