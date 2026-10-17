"""SQL aggregates for the admin dashboard (portable across PostgreSQL and SQLite)."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.application.use_cases.dashboard import (
    ActivityEntry,
    DailyCount,
    DashboardSummary,
    LowStockItem,
    TopProduct,
)
from app.domain.enums import OrderStatus, PaymentStatus, ProductStatus, WhatsAppRequestStatus
from app.infrastructure.db.models.catalog import ProductModel, ProductVariantModel
from app.infrastructure.db.models.commerce import (
    OrderItemModel,
    OrderModel,
    WhatsAppOrderRequestModel,
)
from app.infrastructure.db.models.identity import AuditLogModel, UserModel

CONFIRMED_STATUSES = [
    OrderStatus.CONFIRMED.value,
    OrderStatus.PROCESSING.value,
    OrderStatus.PACKED.value,
    OrderStatus.SHIPPED.value,
    OrderStatus.DELIVERED.value,
]
ZERO = Decimal("0.00")


def _money(value: Any) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01")) if value is not None else ZERO


def _as_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])  # SQLite returns ISO text


class SqlAlchemyDashboardQueries:
    def __init__(self, session: Session) -> None:
        self._session = session

    def summary(self, *, days: int, top_products_min_orders: int) -> DashboardSummary:
        s = self._session
        now = datetime.now(UTC)
        since = now - timedelta(days=days)

        status_counts = dict(
            s.execute(select(ProductModel.status, func.count()).group_by(ProductModel.status)).all()
        )

        tracked = and_(
            ProductVariantModel.is_active.is_(True),
            ProductModel.track_inventory.is_(True),
            ProductModel.status != ProductStatus.ARCHIVED.value,
        )
        low_condition = and_(
            tracked, ProductVariantModel.stock_quantity <= ProductModel.low_stock_threshold
        )
        base = select(func.count()).select_from(ProductVariantModel).join(ProductModel)
        low_count = s.scalar(base.where(low_condition)) or 0
        out_count = s.scalar(base.where(tracked, ProductVariantModel.stock_quantity == 0)) or 0
        low_rows = s.execute(
            select(
                ProductModel.id,
                ProductModel.name,
                ProductVariantModel.size,
                ProductVariantModel.colour,
                ProductVariantModel.sku,
                ProductVariantModel.stock_quantity,
                ProductModel.low_stock_threshold,
            )
            .join(ProductModel)
            .where(low_condition)
            .order_by(ProductVariantModel.stock_quantity, ProductModel.name)
            .limit(10)
        ).all()
        low_stock = [
            LowStockItem(
                product_id=r[0],
                product_name=r[1],
                variant_label=" / ".join(p for p in (r[2], r[3]) if p) or None,
                sku=r[4],
                stock_quantity=r[5],
                threshold=r[6],
            )
            for r in low_rows
        ]

        not_cancelled = OrderModel.status != OrderStatus.CANCELLED.value
        orders_total = s.scalar(select(func.count()).select_from(OrderModel)) or 0
        orders_new = (
            s.scalar(
                select(func.count()).where(
                    OrderModel.status == OrderStatus.PENDING_CONFIRMATION.value
                )
            )
            or 0
        )
        day = func.date(OrderModel.placed_at)
        per_day = {
            _as_date(d): n
            for d, n in s.execute(
                select(day, func.count()).where(OrderModel.placed_at >= since).group_by(day)
            ).all()
        }
        start = (now - timedelta(days=days - 1)).date()
        orders_by_day = [
            DailyCount(day=start + timedelta(days=i), orders=int(per_day.get(start + timedelta(days=i), 0)))
            for i in range(days)
        ]

        placed = s.scalar(select(func.sum(OrderModel.grand_total)).where(not_cancelled))
        confirmed = s.scalar(
            select(func.sum(OrderModel.grand_total)).where(OrderModel.status.in_(CONFIRMED_STATUSES))
        )
        paid = s.scalar(
            select(func.sum(OrderModel.grand_total)).where(
                OrderModel.payment_status == PaymentStatus.PAID.value
            )
        )

        wa_counts = dict(
            s.execute(
                select(WhatsAppOrderRequestModel.status, func.count()).group_by(
                    WhatsAppOrderRequestModel.status
                )
            ).all()
        )

        recent_orders = (
            s.scalar(select(func.count()).where(not_cancelled, OrderModel.placed_at >= since)) or 0
        )
        top_products: list[TopProduct] = []
        if recent_orders >= top_products_min_orders:
            units = func.sum(OrderItemModel.quantity)
            top_products = [
                TopProduct(product_name=name, units=int(total))
                for name, total in s.execute(
                    select(OrderItemModel.product_name, units)
                    .join(OrderModel, OrderModel.id == OrderItemModel.order_id)
                    .where(not_cancelled, OrderModel.placed_at >= since)
                    .group_by(OrderItemModel.product_name)
                    .order_by(units.desc())
                    .limit(5)
                ).all()
            ]

        activity = [
            ActivityEntry(
                action=row.action,
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                actor_email=email,
                created_at=row.created_at,
            )
            for row, email in s.execute(
                select(AuditLogModel, UserModel.email)
                .outerjoin(UserModel, UserModel.id == AuditLogModel.actor_user_id)
                .order_by(AuditLogModel.created_at.desc())
                .limit(12)
            ).all()
        ]

        return DashboardSummary(
            products_total=sum(status_counts.values()),
            products_active=status_counts.get(ProductStatus.ACTIVE.value, 0),
            products_draft=status_counts.get(ProductStatus.DRAFT.value, 0),
            products_archived=status_counts.get(ProductStatus.ARCHIVED.value, 0),
            low_stock_count=low_count,
            out_of_stock_count=out_count,
            low_stock=low_stock,
            orders_total=orders_total,
            orders_new=orders_new,
            orders_by_day=orders_by_day,
            order_value_placed=_money(placed),
            order_value_confirmed=_money(confirmed),
            revenue_paid=_money(paid),
            whatsapp_initiated=wa_counts.get(WhatsAppRequestStatus.INITIATED.value, 0),
            whatsapp_contacted=wa_counts.get(WhatsAppRequestStatus.CONTACTED.value, 0),
            top_products=top_products,
            top_products_min_orders=top_products_min_orders,
            recent_activity=activity,
        )
