"""SQLAlchemy AnalyticsQueries: aggregates over orders, requests, coupons and order lines."""

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.application.use_cases.analytics import (
    AnalyticsReport,
    CategoryPerformance,
    CouponUsage,
    DayPoint,
    ProductPerformance,
)
from app.infrastructure.db.models.catalog import CategoryModel, ProductCategoryModel
from app.infrastructure.db.models.commerce import (
    OrderItemModel,
    OrderModel,
    OrderRequestModel,
    WhatsAppOrderRequestModel,
)
from app.infrastructure.db.models.marketing import CouponModel, CouponRedemptionModel

O = OrderModel  # noqa: E741
ZERO = Decimal("0.00")


def _money(value: Any) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def _as_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


class SqlAlchemyAnalyticsQueries:
    def __init__(self, session: Session) -> None:
        self._session = session

    def report(self, *, start: datetime, end: datetime) -> AnalyticsReport:
        s = self._session
        in_range = and_(O.placed_at >= start, O.placed_at < end)
        live = and_(in_range, O.status != "cancelled")

        placed, value = s.execute(
            select(func.count(), func.coalesce(func.sum(O.grand_total), 0)).where(live)
        ).one()
        cancelled = s.scalar(select(func.count()).where(in_range, O.status == "cancelled")) or 0
        by_source = dict(
            s.execute(select(O.source, func.count()).where(live).group_by(O.source)).all()
        )
        paid = s.scalar(
            select(func.coalesce(func.sum(O.grand_total), 0)).where(
                in_range, O.payment_status == "paid"
            )
        )
        refunds = s.scalar(
            select(func.coalesce(func.sum(OrderRequestModel.refund_amount), 0)).where(
                OrderRequestModel.updated_at >= start,
                OrderRequestModel.updated_at < end,
                OrderRequestModel.status == "completed",
            )
        )

        w = WhatsAppOrderRequestModel
        w_range = and_(w.created_at >= start, w.created_at < end)
        requests = s.scalar(select(func.count()).where(w_range)) or 0
        contacted = (
            s.scalar(select(func.count()).where(w_range, w.status.in_(["contacted", "converted"])))
            or 0
        )
        converted = s.scalar(select(func.count()).where(w_range, w.status == "converted")) or 0

        # Orders per day per source (empty days filled with zeros).
        day = func.date(O.placed_at)
        daily: dict[date, dict[str, Any]] = defaultdict(
            lambda: {"website": 0, "whatsapp": 0, "value": ZERO}
        )
        for d, source, count, total in s.execute(
            select(day, O.source, func.count(), func.coalesce(func.sum(O.grand_total), 0))
            .where(live)
            .group_by(day, O.source)
        ).all():
            bucket = daily[_as_date(d)]
            if source in ("website", "whatsapp"):
                bucket[source] += int(count)
            bucket["value"] += _money(total)
        by_day: list[DayPoint] = []
        cursor = start.date()
        while cursor < end.date():
            b = daily.get(cursor, {"website": 0, "whatsapp": 0, "value": ZERO})
            by_day.append(
                DayPoint(
                    day=cursor,
                    website_orders=b["website"],
                    whatsapp_orders=b["whatsapp"],
                    order_value=_money(b["value"]),
                )
            )
            cursor += timedelta(days=1)

        item = OrderItemModel
        top = s.execute(
            select(
                item.product_id,
                func.max(item.product_name),
                func.sum(item.quantity),
                func.coalesce(func.sum(item.line_total), 0),
            )
            .join(O, O.id == item.order_id)
            .where(live)
            .group_by(item.product_id)
            .order_by(func.sum(item.quantity).desc())
            .limit(10)
        ).all()

        primary = (
            select(ProductCategoryModel.product_id, CategoryModel.name.label("category"))
            .join(CategoryModel, CategoryModel.id == ProductCategoryModel.category_id)
            .where(ProductCategoryModel.is_primary.is_(True))
            .subquery()
        )
        cats = s.execute(
            select(
                func.coalesce(primary.c.category, "Uncategorised"),
                func.sum(item.quantity),
                func.coalesce(func.sum(item.line_total), 0),
            )
            .join(O, O.id == item.order_id)
            .outerjoin(primary, primary.c.product_id == item.product_id)
            .where(live)
            .group_by(func.coalesce(primary.c.category, "Uncategorised"))
            .order_by(func.coalesce(func.sum(item.line_total), 0).desc())
            .limit(20)
        ).all()

        coupons = s.execute(
            select(
                CouponModel.code,
                func.count(CouponRedemptionModel.id),
                func.coalesce(func.sum(CouponRedemptionModel.discount_amount), 0),
            )
            .join(CouponModel, CouponModel.id == CouponRedemptionModel.coupon_id)
            .join(O, O.id == CouponRedemptionModel.order_id)
            .where(live)
            .group_by(CouponModel.code)
            .order_by(func.count(CouponRedemptionModel.id).desc())
        ).all()

        placed_count = int(placed or 0)
        value_total = _money(value)
        return AnalyticsReport(
            start=start.date(),
            end=(end - timedelta(days=1)).date(),
            orders_placed=placed_count,
            orders_cancelled=int(cancelled),
            website_orders=int(by_source.get("website", 0)),
            whatsapp_orders=int(by_source.get("whatsapp", 0)),
            order_value_placed=value_total,
            payments_recorded=_money(paid),
            refunds_recorded=_money(refunds),
            average_order_value=(
                (value_total / placed_count).quantize(Decimal("0.01")) if placed_count else None
            ),
            whatsapp_requests=int(requests),
            whatsapp_contacted=int(contacted),
            whatsapp_converted=int(converted),
            by_day=by_day,
            top_products=[
                ProductPerformance(
                    product_id=str(pid) if pid else None,
                    product_name=name,
                    units=int(units or 0),
                    order_value=_money(total),
                )
                for pid, name, units, total in top
            ],
            categories=[
                CategoryPerformance(category=name, units=int(units or 0), order_value=_money(total))
                for name, units, total in cats
            ],
            coupons=[
                CouponUsage(code=code, redemptions=int(n), discount_given=_money(total))
                for code, n, total in coupons
            ],
        )
