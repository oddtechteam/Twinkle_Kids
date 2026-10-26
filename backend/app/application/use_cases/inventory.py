"""Variant-level inventory: current stock, manual adjustments and the movement ledger.

Stock model (no reservations): `stock_quantity` is what can still be sold. A website order or a
converted WhatsApp request deducts stock when the order is created (a completed sale is an
`order_placed` movement); a cancellation puts it back; a return only does so once the goods
are received and verified. Opening WhatsApp never touches stock.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.application.dto.catalog import Page
from app.domain.entities.identity import User
from app.domain.enums import InventoryReason
from app.domain.errors import DomainValidationError, NotFoundError
from app.domain.repositories.catalog import InventoryLedger
from app.domain.repositories.identity import AuditLogRepository
from app.domain.repositories.media import UnitOfWork

MANUAL_REASONS = frozenset(
    {
        InventoryReason.RESTOCK,
        InventoryReason.ADJUSTMENT,
        InventoryReason.DAMAGED,
        InventoryReason.RETURN,
    }
)
MAX_ADJUSTMENT = 10_000


@dataclass(frozen=True, slots=True)
class InventoryRow:
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

    @property
    def state(self) -> str:
        if not self.track_inventory:
            return "untracked"
        if self.stock_quantity <= 0:
            return "out_of_stock"
        if self.stock_quantity <= self.low_stock_threshold:
            return "low_stock"
        return "in_stock"


@dataclass(frozen=True, slots=True)
class MovementView:
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


@dataclass(frozen=True, slots=True)
class InventoryFilters:
    page: int = 1
    page_size: int = 50
    search: str | None = None
    state: str | None = None  # in_stock | low_stock | out_of_stock


class InventoryStore(Protocol):
    def rows(self, filters: InventoryFilters) -> Page[InventoryRow]: ...

    def row(self, variant_id: UUID) -> InventoryRow | None: ...

    def change_stock(self, variant_id: UUID, delta: int) -> int | None:
        """Atomically add `delta` (may be negative) unless the result would be below zero."""
        ...

    def movements(
        self, *, variant_id: UUID | None, page: int, page_size: int
    ) -> Page[MovementView]: ...


class InventoryService:
    def __init__(
        self,
        *,
        store: InventoryStore,
        ledger: InventoryLedger,
        audit: AuditLogRepository,
        uow: UnitOfWork,
    ) -> None:
        self._store = store
        self._ledger = ledger
        self._audit = audit
        self._uow = uow

    def list(self, filters: InventoryFilters) -> Page[InventoryRow]:
        if filters.state not in (None, "in_stock", "low_stock", "out_of_stock"):
            raise DomainValidationError("Unknown stock filter.")
        return self._store.rows(filters)

    def movements(self, *, variant_id: UUID | None, page: int = 1) -> Page[MovementView]:
        return self._store.movements(variant_id=variant_id, page=max(1, page), page_size=50)

    def adjust(
        self,
        variant_id: UUID,
        *,
        delta: int,
        reason: InventoryReason,
        note: str | None,
        actor: User,
    ) -> InventoryRow:
        if reason not in MANUAL_REASONS:
            raise DomainValidationError("Choose restock, adjustment, damaged or return.")
        if delta == 0 or abs(delta) > MAX_ADJUSTMENT:
            raise DomainValidationError(f"Adjust by a non-zero amount up to {MAX_ADJUSTMENT}.")
        if reason in (InventoryReason.RESTOCK, InventoryReason.RETURN) and delta < 0:
            raise DomainValidationError("Restocks and returns add stock (use a positive number).")
        if reason is InventoryReason.DAMAGED and delta > 0:
            raise DomainValidationError("Damaged stock is removed (use a negative number).")
        note = (note or "").strip() or None
        if note is not None and len(note) > 500:
            raise DomainValidationError("Notes can be up to 500 characters.")
        if self._store.row(variant_id) is None:
            raise NotFoundError("Variant not found.")
        balance = self._store.change_stock(variant_id, delta)
        if balance is None:
            raise DomainValidationError("Stock can't go below zero.")
        self._ledger.record(
            variant_id=variant_id,
            delta=delta,
            stock_after=balance,
            reason=reason,
            actor_user_id=actor.id,
            note=note,
        )
        self._audit.record(
            actor_user_id=actor.id,
            action="inventory.adjusted",
            entity_type="product_variant",
            entity_id=str(variant_id),
            changes={"delta": delta, "stock_after": balance, "reason": reason.value},
        )
        self._uow.commit()
        row = self._store.row(variant_id)
        assert row is not None  # noqa: S101 - just updated
        return row


def low_stock_first(rows: Sequence[InventoryRow]) -> list[InventoryRow]:
    order = {"out_of_stock": 0, "low_stock": 1, "in_stock": 2, "untracked": 3}
    return sorted(rows, key=lambda r: (order[r.state], r.product_name, r.sku))
