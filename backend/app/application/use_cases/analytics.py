"""Store analytics over a date range, from recorded data only.

Money is reported in separate buckets and never conflated: the value of orders placed is not
revenue; "payments recorded" counts only orders staff marked as paid; refunds are what staff
recorded. WhatsApp requests are counted separately from orders (opening WhatsApp is not an order).
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Protocol

from app.domain.errors import DomainValidationError

MAX_RANGE_DAYS = 366


@dataclass(frozen=True, slots=True)
class DayPoint:
    day: date
    website_orders: int
    whatsapp_orders: int
    order_value: Decimal


@dataclass(frozen=True, slots=True)
class ProductPerformance:
    product_id: str | None
    product_name: str
    units: int
    order_value: Decimal


@dataclass(frozen=True, slots=True)
class CategoryPerformance:
    category: str
    units: int
    order_value: Decimal


@dataclass(frozen=True, slots=True)
class CouponUsage:
    code: str
    redemptions: int
    discount_given: Decimal


@dataclass(frozen=True, slots=True)
class AnalyticsReport:
    start: date
    end: date
    orders_placed: int  # excludes cancelled
    orders_cancelled: int
    website_orders: int
    whatsapp_orders: int  # WhatsApp requests that staff converted into orders
    order_value_placed: Decimal  # grand totals of non-cancelled orders — NOT revenue
    payments_recorded: Decimal  # orders staff recorded as paid
    refunds_recorded: Decimal  # refunds staff recorded on completed requests
    average_order_value: Decimal | None
    whatsapp_requests: int  # links handed out (not proof anything was sent)
    whatsapp_contacted: int  # staff confirmed the customer's message
    whatsapp_converted: int
    by_day: list[DayPoint]
    top_products: list[ProductPerformance]
    categories: list[CategoryPerformance]
    coupons: list[CouponUsage]


class AnalyticsQueries(Protocol):
    def report(self, *, start: datetime, end: datetime) -> AnalyticsReport: ...


class AnalyticsReader:
    def __init__(self, queries: AnalyticsQueries) -> None:
        self._queries = queries

    def report(self, *, start: date | None, end: date | None) -> AnalyticsReport:
        today = datetime.now(UTC).date()
        end = end or today
        start = start or end - timedelta(days=29)
        if start > end:
            raise DomainValidationError("The start date must be on or before the end date.")
        if (end - start).days >= MAX_RANGE_DAYS:
            raise DomainValidationError(f"Choose a range of up to {MAX_RANGE_DAYS} days.")
        return self._queries.report(
            start=datetime(start.year, start.month, start.day, tzinfo=UTC),
            end=datetime(end.year, end.month, end.day, tzinfo=UTC) + timedelta(days=1),
        )
