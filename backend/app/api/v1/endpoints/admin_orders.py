"""Admin: website/WhatsApp orders and WhatsApp order requests (orders:manage permission).

Payment is recorded manually here — nothing is ever marked paid automatically. WhatsApp
requests stay separate from orders until staff convert one after confirming with the customer.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import OrderAdminDep, OrdersManagerDep, WhatsAppAdminDep
from app.api.schemas.orders import (
    AdminOrderListOut,
    AdminOrderOut,
    AdminOrderSummaryOut,
    ConvertRequestIn,
    OrderNoteIn,
    OrderPaymentIn,
    OrderStatusIn,
    WhatsAppRequestListOut,
    WhatsAppRequestOut,
    WhatsAppRequestSummaryOut,
    WhatsAppStatusIn,
)
from app.application.dto.orders import OrderFilters
from app.application.use_cases.orders import ConvertInput
from app.domain.enums import OrderSource, OrderStatus, PaymentStatus, WhatsAppRequestStatus

router = APIRouter(prefix="/admin", tags=["admin-orders"])

PageQ = Annotated[int, Query(ge=1, le=10_000)]
SearchQ = Annotated[str | None, Query(max_length=100)]


@router.get("/orders", response_model=AdminOrderListOut)
def list_orders(
    _: OrdersManagerDep,
    orders: OrderAdminDep,
    page: PageQ = 1,
    status: OrderStatus | None = None,
    source: OrderSource | None = None,
    payment_status: PaymentStatus | None = None,
    q: SearchQ = None,
) -> AdminOrderListOut:
    result = orders.list(
        OrderFilters(
            page=page, status=status, source=source, payment_status=payment_status, search=q
        )
    )
    return AdminOrderListOut(
        items=[AdminOrderSummaryOut.model_validate(o) for o in result.items],
        total=result.total,
        page=result.page,
        pages=result.pages,
    )


@router.get("/orders/{order_id}", response_model=AdminOrderOut)
def get_order(order_id: UUID, _: OrdersManagerDep, orders: OrderAdminDep) -> AdminOrderOut:
    return AdminOrderOut.model_validate(orders.get(order_id))


@router.patch("/orders/{order_id}/status", response_model=AdminOrderOut)
def set_order_status(
    order_id: UUID, body: OrderStatusIn, user: OrdersManagerDep, orders: OrderAdminDep
) -> AdminOrderOut:
    """Internal workflow only. Cancelling or returning puts the stock back."""
    return AdminOrderOut.model_validate(orders.set_status(order_id, body.status, actor=user))


@router.patch("/orders/{order_id}/payment", response_model=AdminOrderOut)
def record_payment(
    order_id: UUID, body: OrderPaymentIn, user: OrdersManagerDep, orders: OrderAdminDep
) -> AdminOrderOut:
    """Record a payment received offline (cash on delivery, UPI, bank transfer...)."""
    return AdminOrderOut.model_validate(
        orders.record_payment(order_id, body.payment_status, method=body.payment_method, actor=user)
    )


@router.patch("/orders/{order_id}/note", response_model=AdminOrderOut)
def set_order_note(
    order_id: UUID, body: OrderNoteIn, user: OrdersManagerDep, orders: OrderAdminDep
) -> AdminOrderOut:
    return AdminOrderOut.model_validate(orders.set_note(order_id, body.internal_note, actor=user))


@router.get("/whatsapp-requests", response_model=WhatsAppRequestListOut)
def list_whatsapp_requests(
    _: OrdersManagerDep,
    requests: WhatsAppAdminDep,
    page: PageQ = 1,
    status: WhatsAppRequestStatus | None = None,
    q: SearchQ = None,
) -> WhatsAppRequestListOut:
    result = requests.list(status=status, search=q, page=page, page_size=25)
    return WhatsAppRequestListOut(
        items=[WhatsAppRequestSummaryOut.model_validate(r) for r in result.items],
        total=result.total,
        page=result.page,
        pages=result.pages,
    )


@router.get("/whatsapp-requests/{request_id}", response_model=WhatsAppRequestOut)
def get_whatsapp_request(
    request_id: UUID, _: OrdersManagerDep, requests: WhatsAppAdminDep
) -> WhatsAppRequestOut:
    return WhatsAppRequestOut.model_validate(requests.get(request_id))


@router.patch("/whatsapp-requests/{request_id}/status", response_model=WhatsAppRequestOut)
def set_whatsapp_status(
    request_id: UUID, body: WhatsAppStatusIn, user: OrdersManagerDep, requests: WhatsAppAdminDep
) -> WhatsAppRequestOut:
    """`contacted` = staff actually received the customer's message."""
    return WhatsAppRequestOut.model_validate(
        requests.set_status(request_id, body.status, staff_note=body.staff_note, actor=user)
    )


@router.post(
    "/whatsapp-requests/{request_id}/convert", response_model=AdminOrderOut, status_code=201
)
def convert_whatsapp_request(
    request_id: UUID, body: ConvertRequestIn, user: OrdersManagerDep, requests: WhatsAppAdminDep
) -> AdminOrderOut:
    """Create a real order after availability and price were confirmed with the customer."""
    order = requests.convert(
        request_id,
        ConvertInput(
            customer_name=body.customer_name,
            customer_phone=body.customer_phone,
            customer_email=body.customer_email,
            address=body.address.to_domain(),
            payment_method=body.payment_method,
            items=[(i.variant_id, i.quantity) for i in body.items] if body.items else None,
            internal_note=body.internal_note,
            apply_shipping=body.apply_shipping,
        ),
        actor=user,
    )
    return AdminOrderOut.model_validate(order)
