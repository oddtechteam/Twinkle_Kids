"""SQLAlchemy OrderRequestStore (cancellation / return / exchange requests)."""

from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.application.dto.catalog import Page
from app.application.use_cases.after_sale import NewOrderRequest, OrderRequestView, RequestItem
from app.domain.enums import OrderRequestKind, OrderRequestStatus
from app.infrastructure.db.models.commerce import OrderModel, OrderRequestModel
from app.infrastructure.db.types import utc_now

R = OrderRequestModel


class SqlAlchemyOrderRequestStore:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _view(row: OrderRequestModel, order_number: str) -> OrderRequestView:
        return OrderRequestView(
            id=row.id,
            reference=row.reference,
            order_id=row.order_id,
            order_number=order_number,
            user_id=row.user_id,
            kind=OrderRequestKind(row.kind),
            status=OrderRequestStatus(row.status),
            reason=row.reason,
            customer_message=row.customer_message,
            items=[
                RequestItem(sku=str(i.get("sku", "")), quantity=int(i.get("quantity", 0)))
                for i in (row.items or [])
            ],
            resolution_note=row.resolution_note,
            refund_amount=row.refund_amount,
            restocked=row.restocked,
            created_by_staff=row.created_by_staff,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def add(self, request: NewOrderRequest) -> None:
        self._session.add(
            R(
                id=request.id,
                reference=request.reference,
                order_id=request.order_id,
                user_id=request.user_id,
                kind=request.kind.value,
                status=OrderRequestStatus.REQUESTED.value,
                reason=request.reason,
                customer_message=request.customer_message,
                items=[{"sku": i.sku, "quantity": i.quantity} for i in request.items],
                created_by_staff=request.created_by_staff,
            )
        )
        self._session.flush()

    def get(self, request_id: UUID) -> OrderRequestView | None:
        found = self._session.execute(
            select(R, OrderModel.order_number)
            .join(OrderModel, OrderModel.id == R.order_id)
            .where(R.id == request_id)
            .execution_options(populate_existing=True)
        ).first()
        return self._view(found[0], found[1]) if found else None

    def for_order(self, order_id: UUID) -> list[OrderRequestView]:
        rows = self._session.execute(
            select(R, OrderModel.order_number)
            .join(OrderModel, OrderModel.id == R.order_id)
            .where(R.order_id == order_id)
            .order_by(R.created_at.desc())
            .execution_options(populate_existing=True)
        ).all()
        return [self._view(row, number) for row, number in rows]

    def list(
        self,
        *,
        status: OrderRequestStatus | None,
        kind: OrderRequestKind | None,
        page: int,
        page_size: int,
    ) -> Page[OrderRequestView]:
        stmt = select(R, OrderModel.order_number).join(OrderModel, OrderModel.id == R.order_id)
        if status is not None:
            stmt = stmt.where(R.status == status.value)
        if kind is not None:
            stmt = stmt.where(R.kind == kind.value)
        total = self._session.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = self._session.execute(
            stmt.order_by(R.created_at.desc()).limit(page_size).offset((page - 1) * page_size)
        ).all()
        return Page(
            items=[self._view(row, number) for row, number in rows],
            total=int(total or 0),
            page=page,
            page_size=page_size,
        )

    def update(self, request_id: UUID, **values: Any) -> None:
        self._session.execute(
            update(R).where(R.id == request_id).values(**values, updated_at=utc_now())
        )

    def reference_taken(self, reference: str) -> bool:
        return self._session.scalar(select(R.id).where(R.reference == reference)) is not None
