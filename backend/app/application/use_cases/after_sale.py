"""Cancellation, return and exchange requests.

Customers can only raise the kinds of request the store's policy enables, within its window.
Staff approve or reject, check returned goods in (only then is stock added back), and record
any refund they actually made — there is no payment gateway, so nothing is refunded
automatically. These are requests about an order, not a delivery-tracking feature.
"""

import builtins
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.content_settings import order_policies
from app.application.dto.catalog import Page
from app.application.ports import OrderQueries
from app.domain.entities.identity import User
from app.domain.entities.order import ensure_order_transition
from app.domain.enums import (
    InventoryReason,
    OrderRequestKind,
    OrderRequestStatus,
    OrderStatus,
    PaymentStatus,
)
from app.domain.errors import ConflictError, DomainValidationError, NotFoundError
from app.domain.repositories.catalog import InventoryLedger, ProductRepository
from app.domain.repositories.commerce import CartRepository, OrderRepository
from app.domain.repositories.identity import AuditLogRepository
from app.domain.repositories.media import UnitOfWork
from app.domain.repositories.site import SettingsRepository
from app.domain.value_objects.pricing import to_money

REFERENCE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
OPEN_STATUSES = frozenset(
    {OrderRequestStatus.REQUESTED, OrderRequestStatus.APPROVED, OrderRequestStatus.RECEIVED}
)


@dataclass(frozen=True, slots=True)
class RequestItem:
    sku: str
    quantity: int


@dataclass(frozen=True, slots=True)
class OrderRequestView:
    id: UUID
    reference: str
    order_id: UUID
    order_number: str
    user_id: UUID | None
    kind: OrderRequestKind
    status: OrderRequestStatus
    reason: str
    customer_message: str | None
    items: list[RequestItem]
    resolution_note: str | None
    refund_amount: Decimal | None
    restocked: bool
    created_by_staff: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class NewOrderRequest:
    id: UUID
    reference: str
    order_id: UUID
    user_id: UUID | None
    kind: OrderRequestKind
    reason: str
    customer_message: str | None
    items: list[RequestItem]
    created_by_staff: bool


class OrderRequestStore(Protocol):
    def add(self, request: NewOrderRequest) -> None: ...

    def get(self, request_id: UUID) -> OrderRequestView | None: ...

    def for_order(self, order_id: UUID) -> list[OrderRequestView]: ...

    def list(
        self,
        *,
        status: OrderRequestStatus | None,
        kind: OrderRequestKind | None,
        page: int,
        page_size: int,
    ) -> Page[OrderRequestView]: ...

    def update(self, request_id: UUID, **values: Any) -> None: ...

    def reference_taken(self, reference: str) -> bool: ...


class AfterSaleService:
    def __init__(
        self,
        *,
        store: OrderRequestStore,
        orders: OrderRepository,
        order_queries: OrderQueries,
        products: ProductRepository,
        carts: CartRepository,
        ledger: InventoryLedger,
        settings: SettingsRepository,
        audit: AuditLogRepository,
        uow: UnitOfWork,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._store = store
        self._orders = orders
        self._queries = order_queries
        self._products = products
        self._carts = carts
        self._ledger = ledger
        self._settings = settings
        self._audit = audit
        self._uow = uow
        self._clock = clock

    # --- customer ---------------------------------------------------------------------------

    def policy(self) -> dict[str, Any]:
        return order_policies(self._settings.get().order_policies).model_dump(mode="json")

    def requests_for(self, user: User, order_number: str) -> list[OrderRequestView]:
        order = self._queries.order(number=order_number)
        if order is None or order.user_id != user.id:
            raise NotFoundError("Order not found.")
        return self._store.for_order(order.id)

    def create(
        self,
        user: User,
        order_number: str,
        *,
        kind: OrderRequestKind,
        reason: str,
        message: str | None,
        items: list[RequestItem],
    ) -> OrderRequestView:
        order = self._queries.order(number=order_number)
        if order is None or order.user_id != user.id:
            raise NotFoundError("Order not found.")
        policy = order_policies(self._settings.get().order_policies)
        if reason not in policy.reasons:
            raise DomainValidationError("Please choose one of the listed reasons.")

        if kind is OrderRequestKind.CANCELLATION:
            if not policy.cancellation_enabled:
                raise DomainValidationError(
                    "Online cancellation isn't available — please contact us."
                )
            if order.status not in policy.cancellable_statuses:
                raise DomainValidationError(
                    "This order can no longer be cancelled online — please contact us."
                )
            items = []  # cancellations cover the whole order
        else:
            enabled = (
                policy.returns_enabled
                if kind is OrderRequestKind.RETURN
                else policy.exchanges_enabled
            )
            if not enabled:
                raise DomainValidationError(
                    f"Online {kind.value} requests aren't available — please contact us."
                )
            if order.status is not OrderStatus.DELIVERED:
                raise DomainValidationError(
                    f"A {kind.value} can be requested once the order is delivered."
                )
            if self._clock() > order.placed_at + timedelta(days=policy.return_window_days):
                raise DomainValidationError(
                    f"The {policy.return_window_days}-day {kind.value} window "
                    "for this order has passed."
                )
            items = self._validated_items(order.lines, items)

        if any(
            r.kind is kind and r.status in OPEN_STATUSES for r in self._store.for_order(order.id)
        ):
            raise ConflictError(f"There's already an open {kind.value} request for this order.")
        note = (message or "").strip() or None
        if note and len(note) > 1000:
            raise DomainValidationError("Please keep your message under 1000 characters.")
        request = NewOrderRequest(
            id=uuid4(),
            reference=self._reference(),
            order_id=order.id,
            user_id=user.id,
            kind=kind,
            reason=reason,
            customer_message=note,
            items=items,
            created_by_staff=False,
        )
        self._store.add(request)
        self._audit.record(
            actor_user_id=user.id,
            action=f"order_request.{kind.value}_requested",
            entity_type="order",
            entity_id=str(order.id),
            changes={"reference": request.reference},
        )
        self._uow.commit()
        return self._view(request.id)

    # --- staff ------------------------------------------------------------------------------

    def list(
        self, *, status: OrderRequestStatus | None, kind: OrderRequestKind | None, page: int
    ) -> Page[OrderRequestView]:
        return self._store.list(status=status, kind=kind, page=max(1, page), page_size=25)

    def get(self, request_id: UUID) -> OrderRequestView:
        return self._view(request_id)

    def decide(
        self, request_id: UUID, *, approve: bool, note: str | None, actor: User
    ) -> OrderRequestView:
        request = self._view(request_id)
        if request.status is not OrderRequestStatus.REQUESTED:
            raise ConflictError(f"This request is already {request.status.value}.")
        if approve and request.kind is OrderRequestKind.CANCELLATION:
            current = self._orders.status(request.order_id)
            if current is None:
                raise NotFoundError("Order not found.")
            if current is not OrderStatus.CANCELLED:
                ensure_order_transition(current, OrderStatus.CANCELLED)
                self._orders.set_status(request.order_id, OrderStatus.CANCELLED)
                self._restock(
                    request, actor, reason=InventoryReason.ORDER_CANCELLED, all_lines=True
                )
        status = OrderRequestStatus.APPROVED if approve else OrderRequestStatus.REJECTED
        if approve and request.kind is OrderRequestKind.CANCELLATION:
            status = OrderRequestStatus.COMPLETED  # cancellation done in one step
        self._store.update(request_id, status=status.value, resolution_note=_clean(note))
        self._log(actor, f"order_request.{status.value}", request)
        self._uow.commit()
        return self._view(request_id)

    def mark_received(
        self, request_id: UUID, *, restock: bool, note: str | None, actor: User
    ) -> OrderRequestView:
        """Returned goods physically checked in. Stock is added back only if verified resellable."""
        request = self._view(request_id)
        if request.kind is OrderRequestKind.CANCELLATION:
            raise DomainValidationError("Cancellations have no goods to receive.")
        if request.status is not OrderRequestStatus.APPROVED:
            raise ConflictError("Approve the request before recording the returned goods.")
        if restock and not request.restocked:
            self._restock(request, actor, reason=InventoryReason.RETURN, all_lines=False)
        self._store.update(
            request_id,
            status=OrderRequestStatus.RECEIVED.value,
            restocked=request.restocked or restock,
            resolution_note=_clean(note) or request.resolution_note,
        )
        self._log(actor, "order_request.received", request, {"restocked": restock})
        self._uow.commit()
        return self._view(request_id)

    def complete(
        self,
        request_id: UUID,
        *,
        refund_amount: Decimal | None,
        note: str | None,
        actor: User,
    ) -> OrderRequestView:
        """Close the request, recording any refund staff actually made (outside this system)."""
        request = self._view(request_id)
        if request.status not in (OrderRequestStatus.APPROVED, OrderRequestStatus.RECEIVED):
            raise ConflictError(f"A {request.status.value} request can't be completed.")
        order = self._queries.order(order_id=request.order_id)
        if order is None:
            raise NotFoundError("Order not found.")
        refund = None if refund_amount is None else to_money(refund_amount, field="Refund")
        if refund is not None and refund > order.grand_total:
            raise DomainValidationError("A refund can't exceed the order total.")
        if refund and refund > 0:
            already = sum(
                (r.refund_amount or Decimal("0"))
                for r in self._store.for_order(order.id)
                if r.id != request_id
            )
            if already + refund > order.grand_total:
                raise DomainValidationError("Total refunds can't exceed the order total.")
            full = already + refund >= order.grand_total
            self._orders.set_payment(
                order.id,
                PaymentStatus.REFUNDED if full else PaymentStatus.PARTIALLY_REFUNDED,
                None,
            )
        self._store.update(
            request_id,
            status=OrderRequestStatus.COMPLETED.value,
            refund_amount=refund,
            resolution_note=_clean(note) or request.resolution_note,
        )
        self._log(
            actor, "order_request.completed", request, {"refund": str(refund) if refund else None}
        )
        self._uow.commit()
        return self._view(request_id)

    # --- helpers ----------------------------------------------------------------------------

    def _view(self, request_id: UUID) -> OrderRequestView:
        found = self._store.get(request_id)
        if found is None:
            raise NotFoundError("Request not found.")
        return found

    def _validated_items(
        self, lines: Any, items: builtins.list[RequestItem]
    ) -> builtins.list[RequestItem]:
        ordered = {line.sku: line.quantity for line in lines}
        if not items:
            return [RequestItem(sku=sku, quantity=qty) for sku, qty in ordered.items()]
        merged: dict[str, int] = {}
        for item in items:
            if item.sku not in ordered:
                raise DomainValidationError(f"{item.sku} isn't part of this order.")
            merged[item.sku] = merged.get(item.sku, 0) + item.quantity
        for sku, qty in merged.items():
            if not 1 <= qty <= ordered[sku]:
                raise DomainValidationError(f"Choose between 1 and {ordered[sku]} of {sku}.")
        return [RequestItem(sku=s, quantity=q) for s, q in merged.items()]

    def _restock(
        self, request: OrderRequestView, actor: User, *, reason: InventoryReason, all_lines: bool
    ) -> None:
        wanted = {i.sku: i.quantity for i in request.items}
        for variant_id, sku, ordered_qty in self._orders.lines_with_sku(request.order_id):
            quantity = ordered_qty if all_lines else min(wanted.get(sku, 0), ordered_qty)
            if quantity <= 0:
                continue
            product_id = self._carts.product_ids_for_variants([variant_id]).get(variant_id)
            product = self._products.get(product_id) if product_id else None
            if product is None or not product.track_inventory:
                continue
            balance = self._orders.restock(variant_id, quantity)
            self._ledger.record(
                variant_id=variant_id,
                delta=quantity,
                stock_after=balance,
                reason=reason,
                actor_user_id=actor.id,
                note=f"Request {request.reference}",
                order_id=request.order_id,
            )

    def _reference(self) -> str:
        for _ in range(10):
            reference = "RQ-" + "".join(secrets.choice(REFERENCE_ALPHABET) for _ in range(6))
            if not self._store.reference_taken(reference):
                return reference
        raise ConflictError("Please try again.")  # pragma: no cover

    def _log(
        self,
        actor: User,
        action: str,
        request: OrderRequestView,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self._audit.record(
            actor_user_id=actor.id,
            action=action,
            entity_type="order_request",
            entity_id=str(request.id),
            changes={
                "reference": request.reference,
                "order": request.order_number,
                **(extra or {}),
            },
        )


def _clean(note: str | None) -> str | None:
    value = (note or "").strip() or None
    if value and len(value) > 1000:
        raise DomainValidationError("Notes can be up to 1000 characters.")
    return value
