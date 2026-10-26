"""Admin store operations: inventory, coupons, after-sale requests, review moderation,
analytics, staff roles, the audit log and the notification log. Every route checks the
specific permission on the server."""

from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import (
    AfterSaleDep,
    AnalyticsDep,
    AuditReaderDep,
    ContentManagerDep,
    CouponServiceDep,
    InventoryManagerDep,
    InventoryServiceDep,
    NotifierDep,
    OrdersManagerDep,
    ReviewServiceDep,
    SettingsManagerDep,
    StaffServiceDep,
    UsersManagerDep,
)
from app.api.schemas.operations import (
    ActiveIn,
    AdjustStockIn,
    AnalyticsOut,
    AuditEntryOut,
    CompleteIn,
    CouponIn,
    CouponOut,
    DecisionIn,
    InventoryRowOut,
    ModerateIn,
    ModerationOut,
    MovementOut,
    NotificationOut,
    OrderRequestOut,
    PageOut,
    ReceivedIn,
    StaffOut,
    StaffRolesIn,
)
from app.application.use_cases.coupons import CouponUsage
from app.application.use_cases.inventory import InventoryFilters
from app.domain.enums import NotificationStatus, OrderRequestKind, OrderRequestStatus, ReviewStatus

router = APIRouter(prefix="/admin", tags=["admin-operations"])

PageQ = Annotated[int, Query(ge=1, le=10_000)]


# --- inventory --------------------------------------------------------------------------------


@router.get("/inventory", response_model=PageOut[InventoryRowOut])
def inventory(
    _: InventoryManagerDep,
    service: InventoryServiceDep,
    page: PageQ = 1,
    q: Annotated[str | None, Query(max_length=100)] = None,
    state: Annotated[str | None, Query(pattern="^(in_stock|low_stock|out_of_stock)$")] = None,
) -> PageOut[InventoryRowOut]:
    result = service.list(InventoryFilters(page=page, search=q, state=state))
    return PageOut(
        items=[InventoryRowOut.of(r) for r in result.items],
        total=result.total,
        page=result.page,
        pages=result.pages,
    )


@router.post("/inventory/{variant_id}/adjust", response_model=InventoryRowOut)
def adjust_stock(
    variant_id: UUID, body: AdjustStockIn, user: InventoryManagerDep, service: InventoryServiceDep
) -> InventoryRowOut:
    """Atomic +/- change recorded in the movement ledger (stock can never go below zero)."""
    row = service.adjust(
        variant_id, delta=body.delta, reason=body.reason, note=body.note, actor=user
    )
    return InventoryRowOut.of(row)


@router.get("/inventory/movements", response_model=PageOut[MovementOut])
def stock_movements(
    _: InventoryManagerDep,
    service: InventoryServiceDep,
    page: PageQ = 1,
    variant_id: UUID | None = None,
) -> PageOut[MovementOut]:
    result = service.movements(variant_id=variant_id, page=page)
    return PageOut(
        items=[MovementOut.model_validate(m) for m in result.items],
        total=result.total,
        page=result.page,
        pages=result.pages,
    )


# --- coupons ----------------------------------------------------------------------------------


@router.get("/coupons", response_model=list[CouponOut])
def coupons(_: SettingsManagerDep, service: CouponServiceDep) -> list[CouponOut]:
    return [CouponOut.of(c) for c in service.list()]


@router.post("/coupons", response_model=CouponOut, status_code=201)
def create_coupon(body: CouponIn, user: SettingsManagerDep, service: CouponServiceDep) -> CouponOut:
    return CouponOut.of(
        CouponUsage(service.create(body.to_input(), actor=user), 0, Decimal("0.00"))
    )


@router.put("/coupons/{coupon_id}", response_model=CouponOut)
def update_coupon(
    coupon_id: UUID, body: CouponIn, user: SettingsManagerDep, service: CouponServiceDep
) -> CouponOut:
    service.update(coupon_id, body.to_input(), actor=user)
    return next(CouponOut.of(c) for c in service.list() if c.coupon.id == coupon_id)


@router.patch("/coupons/{coupon_id}/active", response_model=CouponOut)
def set_coupon_active(
    coupon_id: UUID, body: ActiveIn, user: SettingsManagerDep, service: CouponServiceDep
) -> CouponOut:
    service.set_active(coupon_id, body.is_active, actor=user)
    return next(CouponOut.of(c) for c in service.list() if c.coupon.id == coupon_id)


# --- after-sale requests ----------------------------------------------------------------------


@router.get("/order-requests", response_model=PageOut[OrderRequestOut])
def order_requests(
    _: OrdersManagerDep,
    service: AfterSaleDep,
    page: PageQ = 1,
    status: OrderRequestStatus | None = None,
    kind: OrderRequestKind | None = None,
) -> PageOut[OrderRequestOut]:
    result = service.list(status=status, kind=kind, page=page)
    return PageOut(
        items=[OrderRequestOut.model_validate(r) for r in result.items],
        total=result.total,
        page=result.page,
        pages=result.pages,
    )


@router.get("/order-requests/{request_id}", response_model=OrderRequestOut)
def order_request(request_id: UUID, _: OrdersManagerDep, service: AfterSaleDep) -> OrderRequestOut:
    return OrderRequestOut.model_validate(service.get(request_id))


@router.post("/order-requests/{request_id}/decision", response_model=OrderRequestOut)
def decide_request(
    request_id: UUID, body: DecisionIn, user: OrdersManagerDep, service: AfterSaleDep
) -> OrderRequestOut:
    """Approving a cancellation cancels the order and puts its stock back."""
    return OrderRequestOut.model_validate(
        service.decide(request_id, approve=body.approve, note=body.note, actor=user)
    )


@router.post("/order-requests/{request_id}/received", response_model=OrderRequestOut)
def receive_request(
    request_id: UUID, body: ReceivedIn, user: OrdersManagerDep, service: AfterSaleDep
) -> OrderRequestOut:
    """Returned goods checked in; `restock` only when they were verified resellable."""
    return OrderRequestOut.model_validate(
        service.mark_received(request_id, restock=body.restock, note=body.note, actor=user)
    )


@router.post("/order-requests/{request_id}/complete", response_model=OrderRequestOut)
def complete_request(
    request_id: UUID, body: CompleteIn, user: OrdersManagerDep, service: AfterSaleDep
) -> OrderRequestOut:
    """Close the request and record any refund staff actually made (no automatic refunds)."""
    return OrderRequestOut.model_validate(
        service.complete(request_id, refund_amount=body.refund_amount, note=body.note, actor=user)
    )


# --- reviews ----------------------------------------------------------------------------------


@router.get("/reviews", response_model=PageOut[ModerationOut])
def review_queue(
    _: ContentManagerDep,
    service: ReviewServiceDep,
    page: PageQ = 1,
    status: ReviewStatus | None = ReviewStatus.PENDING,
) -> PageOut[ModerationOut]:
    result = service.moderation(status=status, page=page)
    return PageOut(
        items=[ModerationOut.model_validate(r) for r in result.items],
        total=result.total,
        page=result.page,
        pages=result.pages,
    )


@router.patch("/reviews/{review_id}", status_code=204)
def moderate_review(
    review_id: UUID, body: ModerateIn, user: ContentManagerDep, service: ReviewServiceDep
) -> None:
    """Approve = publish; reject = hide (from the queue or after publishing)."""
    service.moderate(review_id, body.status, note=body.note, actor=user)


# --- analytics --------------------------------------------------------------------------------


@router.get("/analytics", response_model=AnalyticsOut)
def analytics(
    _: OrdersManagerDep,
    reader: AnalyticsDep,
    start: date | None = None,
    end: date | None = None,
) -> AnalyticsOut:
    return AnalyticsOut.model_validate(reader.report(start=start, end=end))


# --- staff, audit, notifications ----------------------------------------------------------------


@router.get("/staff", response_model=list[StaffOut])
def staff(_: UsersManagerDep, service: StaffServiceDep) -> list[StaffOut]:
    return [StaffOut.model_validate(m) for m in service.list()]


@router.put("/staff/roles", response_model=StaffOut)
def set_staff_roles(
    body: StaffRolesIn, user: UsersManagerDep, service: StaffServiceDep
) -> StaffOut:
    """Grant/revoke staff roles on an existing account (no admin accounts are created here)."""
    return StaffOut.model_validate(
        service.set_roles(email=body.email, roles=set(body.roles), actor=user)
    )


@router.get("/audit-log", response_model=PageOut[AuditEntryOut])
def audit_log(
    _: AuditReaderDep,
    service: StaffServiceDep,
    page: PageQ = 1,
    action: Annotated[str | None, Query(max_length=60)] = None,
    entity_type: Annotated[str | None, Query(max_length=40)] = None,
) -> PageOut[AuditEntryOut]:
    result = service.audit_log(action=action, entity_type=entity_type, page=page)
    return PageOut(
        items=[AuditEntryOut.model_validate(e) for e in result.items],
        total=result.total,
        page=result.page,
        pages=result.pages,
    )


@router.get("/notifications", response_model=PageOut[NotificationOut])
def notifications(
    _: AuditReaderDep,
    notifier: NotifierDep,
    page: PageQ = 1,
    status: NotificationStatus | None = None,
) -> PageOut[NotificationOut]:
    result = notifier.history(status=status, page=page)
    return PageOut(
        items=[NotificationOut.model_validate(n) for n in result.items],
        total=result.total,
        page=result.page,
        pages=result.pages,
    )
