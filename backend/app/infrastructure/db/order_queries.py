"""SQLAlchemy implementation of the OrderQueries read port."""

from typing import Any
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.application.dto.catalog import Page
from app.application.dto.orders import (
    OrderFilters,
    OrderLineView,
    OrderSummary,
    OrderView,
    WhatsAppLineView,
    WhatsAppRequestSummary,
    WhatsAppRequestView,
)
from app.domain.enums import (
    OrderSource,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    WhatsAppRequestStatus,
)
from app.infrastructure.db.models.commerce import (
    OrderItemModel,
    OrderModel,
    WhatsAppOrderRequestItemModel,
    WhatsAppOrderRequestModel,
)

Ord = OrderModel
Wreq = WhatsAppOrderRequestModel


def _like(term: str) -> str:
    escaped = term.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


class SqlAlchemyOrderQueries:
    def __init__(self, session: Session) -> None:
        self._session = session

    # --- orders ----------------------------------------------------------------------------

    def order(self, *, order_id: UUID | None = None, number: str | None = None) -> OrderView | None:
        stmt = select(Ord)
        if order_id is not None:
            stmt = stmt.where(Ord.id == order_id)
        elif number is not None:
            stmt = stmt.where(Ord.order_number == number.strip().upper())
        else:  # pragma: no cover - programming error
            raise ValueError("order_id or number is required")
        row = self._session.scalars(stmt).first()
        if row is None:
            return None
        items = self._session.scalars(
            select(OrderItemModel)
            .where(OrderItemModel.order_id == row.id)
            .order_by(OrderItemModel.created_at, OrderItemModel.product_name)
        )
        return OrderView(
            id=row.id,
            order_number=row.order_number,
            user_id=row.user_id,
            source=OrderSource(row.source),
            status=OrderStatus(row.status),
            payment_status=PaymentStatus(row.payment_status),
            payment_method=PaymentMethod(row.payment_method) if row.payment_method else None,
            customer_name=row.customer_name,
            customer_email=row.customer_email,
            customer_phone=row.customer_phone,
            shipping_address=dict(row.shipping_address or {}),
            currency_code=row.currency_code,
            subtotal=row.subtotal,
            discount_total=row.discount_total,
            shipping_total=row.shipping_total,
            grand_total=row.grand_total,
            coupon_code=row.coupon_code,
            customer_note=row.customer_note,
            internal_note=row.internal_note,
            placed_at=row.placed_at,
            lines=[
                OrderLineView(
                    product_name=i.product_name,
                    product_slug=i.product_slug,
                    sku=i.sku,
                    size=i.size,
                    colour=i.colour,
                    image_url=i.image_url,
                    unit_selling_price=i.unit_selling_price,
                    unit_original_price=i.unit_original_price,
                    quantity=i.quantity,
                    line_total=i.line_total,
                )
                for i in items
            ],
        )

    def _summaries(self, stmt: Select[Any], page: int, page_size: int) -> Page[OrderSummary]:
        total = self._session.scalar(
            select(func.count()).select_from(stmt.order_by(None).subquery())
        )
        rows = self._session.scalars(
            stmt.order_by(Ord.placed_at.desc(), Ord.id)
            .limit(page_size)
            .offset((page - 1) * page_size)
        ).all()
        counts = (
            dict(
                self._session.execute(
                    select(OrderItemModel.order_id, func.sum(OrderItemModel.quantity))
                    .where(OrderItemModel.order_id.in_([r.id for r in rows]))
                    .group_by(OrderItemModel.order_id)
                ).all()
            )
            if rows
            else {}
        )
        return Page(
            items=[
                OrderSummary(
                    id=r.id,
                    order_number=r.order_number,
                    source=OrderSource(r.source),
                    status=OrderStatus(r.status),
                    payment_status=PaymentStatus(r.payment_status),
                    payment_method=PaymentMethod(r.payment_method) if r.payment_method else None,
                    customer_name=r.customer_name,
                    grand_total=r.grand_total,
                    item_count=int(counts.get(r.id) or 0),
                    placed_at=r.placed_at,
                )
                for r in rows
            ],
            total=int(total or 0),
            page=page,
            page_size=page_size,
        )

    def orders(self, filters: OrderFilters) -> Page[OrderSummary]:
        stmt: Select[Any] = select(Ord)
        if filters.status is not None:
            stmt = stmt.where(Ord.status == filters.status.value)
        if filters.source is not None:
            stmt = stmt.where(Ord.source == filters.source.value)
        if filters.payment_status is not None:
            stmt = stmt.where(Ord.payment_status == filters.payment_status.value)
        if filters.search and filters.search.strip():
            term = _like(filters.search)
            stmt = stmt.where(
                or_(
                    Ord.order_number.ilike(term, escape="\\"),
                    Ord.customer_name.ilike(term, escape="\\"),
                    Ord.customer_email.ilike(term, escape="\\"),
                    Ord.customer_phone.ilike(term, escape="\\"),
                )
            )
        return self._summaries(stmt, filters.page, filters.page_size)

    def orders_for_user(self, user_id: UUID, *, page: int, page_size: int) -> Page[OrderSummary]:
        return self._summaries(select(Ord).where(Ord.user_id == user_id), page, page_size)

    # --- WhatsApp requests -----------------------------------------------------------------

    def whatsapp_request(self, request_id: UUID) -> WhatsAppRequestView | None:
        row = self._session.get(Wreq, request_id)
        if row is None:
            return None
        items = self._session.scalars(
            select(WhatsAppOrderRequestItemModel)
            .where(WhatsAppOrderRequestItemModel.request_id == row.id)
            .order_by(WhatsAppOrderRequestItemModel.product_name)
        )
        converted_number = (
            self._session.scalar(select(Ord.order_number).where(Ord.id == row.converted_order_id))
            if row.converted_order_id
            else None
        )
        return WhatsAppRequestView(
            id=row.id,
            reference=row.reference,
            status=WhatsAppRequestStatus(row.status),
            user_id=row.user_id,
            customer_name=row.customer_name,
            customer_phone=row.customer_phone,
            message_text=row.message_text,
            estimated_subtotal=row.estimated_subtotal,
            staff_note=row.staff_note,
            contacted_at=row.contacted_at,
            created_at=row.created_at,
            converted_order_id=row.converted_order_id,
            converted_order_number=converted_number,
            lines=[
                WhatsAppLineView(
                    variant_id=i.variant_id,
                    product_name=i.product_name,
                    sku=i.sku,
                    size=i.size,
                    colour=i.colour,
                    unit_selling_price=i.unit_selling_price,
                    quantity=i.quantity,
                    line_total=i.line_total,
                )
                for i in items
            ],
        )

    def whatsapp_requests(
        self,
        *,
        status: WhatsAppRequestStatus | None,
        search: str | None,
        page: int,
        page_size: int,
    ) -> Page[WhatsAppRequestSummary]:
        stmt: Select[Any] = select(Wreq)
        if status is not None:
            stmt = stmt.where(Wreq.status == status.value)
        if search and search.strip():
            term = _like(search)
            stmt = stmt.where(
                or_(
                    Wreq.reference.ilike(term, escape="\\"),
                    Wreq.customer_name.ilike(term, escape="\\"),
                    Wreq.customer_phone.ilike(term, escape="\\"),
                )
            )
        total = self._session.scalar(
            select(func.count()).select_from(stmt.order_by(None).subquery())
        )
        rows = self._session.scalars(
            stmt.order_by(Wreq.created_at.desc(), Wreq.id)
            .limit(page_size)
            .offset((page - 1) * page_size)
        ).all()
        ids = [r.id for r in rows]
        counts = (
            dict(
                self._session.execute(
                    select(
                        WhatsAppOrderRequestItemModel.request_id,
                        func.sum(WhatsAppOrderRequestItemModel.quantity),
                    )
                    .where(WhatsAppOrderRequestItemModel.request_id.in_(ids))
                    .group_by(WhatsAppOrderRequestItemModel.request_id)
                ).all()
            )
            if ids
            else {}
        )
        order_ids = [r.converted_order_id for r in rows if r.converted_order_id]
        numbers = (
            dict(
                self._session.execute(
                    select(Ord.id, Ord.order_number).where(Ord.id.in_(order_ids))
                ).all()
            )
            if order_ids
            else {}
        )
        return Page(
            items=[
                WhatsAppRequestSummary(
                    id=r.id,
                    reference=r.reference,
                    status=WhatsAppRequestStatus(r.status),
                    customer_name=r.customer_name,
                    estimated_subtotal=r.estimated_subtotal,
                    item_count=int(counts.get(r.id) or 0),
                    created_at=r.created_at,
                    converted_order_number=numbers.get(r.converted_order_id)
                    if r.converted_order_id
                    else None,
                )
                for r in rows
            ],
            total=int(total or 0),
            page=page,
            page_size=page_size,
        )
