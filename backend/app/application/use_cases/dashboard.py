"""Admin dashboard: database-backed summaries only. No figures are estimated or invented."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class LowStockItem:
    product_id: UUID
    product_name: str
    variant_label: str | None
    sku: str
    stock_quantity: int
    threshold: int


@dataclass(frozen=True, slots=True)
class DailyCount:
    day: date
    orders: int


@dataclass(frozen=True, slots=True)
class TopProduct:
    product_name: str
    units: int


@dataclass(frozen=True, slots=True)
class ActivityEntry:
    action: str
    entity_type: str
    entity_id: str | None
    actor_email: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class DashboardSummary:
    products_total: int
    products_active: int
    products_draft: int
    products_archived: int
    low_stock_count: int
    out_of_stock_count: int
    low_stock: list[LowStockItem]
    orders_total: int
    orders_new: int  # pending confirmation
    orders_by_day: list[DailyCount]  # last 30 days
    # Three distinct money figures, never conflated:
    order_value_placed: Decimal  # grand totals of all non-cancelled orders (not revenue)
    order_value_confirmed: Decimal  # orders confirmed or further along
    revenue_paid: Decimal  # orders whose payment is recorded as paid
    whatsapp_initiated: int  # customer opened WhatsApp — not proof a message was sent
    whatsapp_contacted: int  # staff confirmed the conversation
    top_products: list[TopProduct]  # empty when there is not enough order data
    top_products_min_orders: int
    recent_activity: list[ActivityEntry]


class DashboardQueries(Protocol):
    def summary(self, *, days: int, top_products_min_orders: int) -> DashboardSummary: ...


class DashboardReader:
    TOP_PRODUCTS_MIN_ORDERS = 5

    def __init__(self, queries: DashboardQueries) -> None:
        self._queries = queries

    def summary(self) -> DashboardSummary:
        return self._queries.summary(days=30, top_products_min_orders=self.TOP_PRODUCTS_MIN_ORDERS)
