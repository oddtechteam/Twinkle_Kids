"""SQLAlchemy InventoryStore: stock rows, atomic stock changes and the movement ledger."""

from typing import Any
from uuid import UUID

from sqlalchemy import Select, and_, case, func, or_, select, update
from sqlalchemy.orm import Session

from app.application.dto.catalog import Page
from app.application.use_cases.inventory import InventoryFilters, InventoryRow, MovementView
from app.domain.enums import InventoryReason
from app.infrastructure.db.models.catalog import ProductModel, ProductVariantModel
from app.infrastructure.db.models.commerce import InventoryMovementModel, OrderModel
from app.infrastructure.db.models.identity import UserModel

P = ProductModel
V = ProductVariantModel
M = InventoryMovementModel


class SqlAlchemyInventoryStore:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _select(self) -> Select[*tuple[Any, ...]]:
        return select(
            V.id,
            P.id,
            P.name,
            P.status,
            V.sku,
            V.size,
            V.colour,
            V.stock_quantity,
            P.low_stock_threshold,
            P.track_inventory,
            P.allow_backorder,
            V.is_active,
        ).join(P, P.id == V.product_id)

    @staticmethod
    def _row(r: Any) -> InventoryRow:
        return InventoryRow(
            variant_id=r[0],
            product_id=r[1],
            product_name=r[2],
            product_status=r[3],
            sku=r[4],
            size=r[5],
            colour=r[6],
            stock_quantity=r[7],
            low_stock_threshold=r[8],
            track_inventory=r[9],
            allow_backorder=r[10],
            is_active=r[11],
        )

    def rows(self, filters: InventoryFilters) -> Page[InventoryRow]:
        stmt = self._select().where(P.status != "archived")
        if filters.search and filters.search.strip():
            term = f"%{filters.search.strip()}%"
            stmt = stmt.where(or_(P.name.ilike(term), V.sku.ilike(term), P.sku.ilike(term)))
        tracked = P.track_inventory.is_(True)
        if filters.state == "out_of_stock":
            stmt = stmt.where(tracked, V.stock_quantity <= 0)
        elif filters.state == "low_stock":
            stmt = stmt.where(
                tracked, V.stock_quantity > 0, V.stock_quantity <= P.low_stock_threshold
            )
        elif filters.state == "in_stock":
            stmt = stmt.where(or_(~tracked, V.stock_quantity > P.low_stock_threshold))
        urgency = case(
            (and_(tracked, V.stock_quantity <= 0), 0),
            (and_(tracked, V.stock_quantity <= P.low_stock_threshold), 1),
            else_=2,
        )
        total = self._session.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = self._session.execute(
            stmt.order_by(urgency, P.name, V.position)
            .limit(filters.page_size)
            .offset((filters.page - 1) * filters.page_size)
        ).all()
        return Page(
            items=[self._row(r) for r in rows],
            total=int(total or 0),
            page=filters.page,
            page_size=filters.page_size,
        )

    def row(self, variant_id: UUID) -> InventoryRow | None:
        found = self._session.execute(self._select().where(V.id == variant_id)).first()
        return self._row(found) if found else None

    def change_stock(self, variant_id: UUID, delta: int) -> int | None:
        result = self._session.execute(
            update(V)
            .where(V.id == variant_id, V.stock_quantity + delta >= 0)
            .values(stock_quantity=V.stock_quantity + delta)
            .execution_options(synchronize_session=False)
        )
        if not result.rowcount:  # type: ignore[attr-defined]
            return None
        value = self._session.scalar(
            select(V.stock_quantity)
            .where(V.id == variant_id)
            .execution_options(populate_existing=True)
        )
        return int(value or 0)

    def movements(
        self, *, variant_id: UUID | None, page: int, page_size: int
    ) -> Page[MovementView]:
        stmt = (
            select(M, V.sku, P.name, OrderModel.order_number, UserModel.email)
            .join(V, V.id == M.variant_id)
            .join(P, P.id == V.product_id)
            .outerjoin(OrderModel, OrderModel.id == M.order_id)
            .outerjoin(UserModel, UserModel.id == M.actor_user_id)
        )
        if variant_id is not None:
            stmt = stmt.where(M.variant_id == variant_id)
        total = self._session.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = self._session.execute(
            stmt.order_by(M.created_at.desc(), M.id).limit(page_size).offset((page - 1) * page_size)
        ).all()
        return Page(
            items=[
                MovementView(
                    id=m.id,
                    variant_id=m.variant_id,
                    sku=sku,
                    product_name=name,
                    quantity_delta=m.quantity_delta,
                    stock_after=m.stock_after,
                    reason=InventoryReason(m.reason),
                    note=m.note,
                    order_number=number,
                    actor_email=email,
                    created_at=m.created_at,
                )
                for m, sku, name, number, email in rows
            ],
            total=int(total or 0),
            page=page,
            page_size=page_size,
        )
