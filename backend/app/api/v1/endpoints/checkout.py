"""Website checkout (no payment gateway). Guest checkout follows the admin setting.

Send a fresh `Idempotency-Key` header per checkout attempt and reuse it for retries: the same
key always returns the same order, so double clicks and network retries never create a second
order or deduct stock twice.
"""

from typing import Annotated

from fastapi import APIRouter, Header, Response, status

from app.api.deps import CheckoutServiceDep, OptionalUserDep, RequestContextDep
from app.api.schemas.orders import CheckoutIn, CheckoutQuoteOut, PlacedOrderOut, QuoteIn
from app.api.v1.endpoints.cart import OwnerDep
from app.application.use_cases.orders import CheckoutInput

router = APIRouter(prefix="/checkout", tags=["checkout"])


@router.post("/quote", response_model=CheckoutQuoteOut)
def quote(
    body: QuoteIn, owner: OwnerDep, user: OptionalUserDep, checkout: CheckoutServiceDep
) -> CheckoutQuoteOut:
    """Server-calculated summary of the bag: discount, delivery, total and payment options."""
    return CheckoutQuoteOut.of(checkout.quote(owner, user, coupon_code=body.coupon_code))


@router.post("/orders", response_model=PlacedOrderOut, status_code=status.HTTP_201_CREATED)
def place_order(
    body: CheckoutIn,
    response: Response,
    owner: OwnerDep,
    user: OptionalUserDep,
    checkout: CheckoutServiceDep,
    context: RequestContextDep,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=100)],
) -> PlacedOrderOut:
    order, created = checkout.place_order(
        owner,
        user,
        CheckoutInput(
            idempotency_key=idempotency_key,
            customer_name=body.customer_name,
            customer_phone=body.customer_phone,
            customer_email=body.customer_email,
            payment_method=body.payment_method,
            address=body.address.to_domain() if body.address else None,
            saved_address_id=body.saved_address_id,
            customer_note=body.customer_note,
            coupon_code=body.coupon_code,
            save_address=body.save_address,
            expected_grand_total=body.expected_grand_total,
        ),
        ip=context.ip,
    )
    if not created:
        response.status_code = status.HTTP_200_OK  # replay of an earlier submission
    out = PlacedOrderOut.model_validate(order)
    out.payment_instructions = checkout.payment_instructions(order.payment_method)
    return out


@router.get("/pin/{postal_code}")
def check_pin(postal_code: str, checkout: CheckoutServiceDep) -> dict[str, object]:
    """Does the shop deliver to this PIN code? Uses the shop's own rules (no courier lookup)."""
    pin = postal_code.strip()
    if not (len(pin) == 6 and pin.isdigit() and pin[0] != "0"):
        return {"serviceable": False, "message": "Enter a valid 6-digit PIN code."}
    serviceable, message = checkout.check_pin(pin)
    return {"serviceable": serviceable, "message": message}
