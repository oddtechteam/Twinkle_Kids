"""Account, checkout, order and WhatsApp-admin contracts.

Checkout requests carry customer details, an address, a payment-method choice and quantities
only (from the server-side bag). Prices and totals are never accepted from the browser.
"""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.api.schemas.commerce import CartOut
from app.application.use_cases.orders import CheckoutQuote
from app.domain.entities.address import PostalAddress, SavedAddress
from app.domain.entities.commerce import MAX_CART_LINE_QUANTITY, MAX_CART_LINES
from app.domain.enums import (
    OrderSource,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    WhatsAppRequestStatus,
)


def _str(max_length: int, min_length: int = 0) -> StringConstraints:
    return StringConstraints(strip_whitespace=True, min_length=min_length, max_length=max_length)


Name = Annotated[str, _str(120, 1)]
Phone = Annotated[str, _str(20, 1)]
OptionalPhone = Annotated[str, _str(20)]
Email = Annotated[str, _str(254)]
Line = Annotated[str, _str(200, 1)]
OptionalLine = Annotated[str, _str(200)]
Landmark = Annotated[str, _str(120)]
Place = Annotated[str, _str(100, 1)]
PostalCode = Annotated[str, _str(12, 1)]
Label = Annotated[str, _str(40)]
Note = Annotated[str, _str(500)]
Code = Annotated[str, _str(40)]


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- account ----------------------------------------------------------------------------------


class ProfileIn(_In):
    full_name: Name
    phone: OptionalPhone | None = None


class ChangePasswordIn(_In):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=1, max_length=128)


class PasswordResetRequestIn(_In):
    email: Annotated[str, _str(254, 3)]


class PasswordResetConfirmIn(_In):
    token: str = Field(min_length=20, max_length=200)
    new_password: str = Field(min_length=1, max_length=128)


class AddressIn(_In):
    full_name: Name
    phone: Phone
    line1: Line
    line2: OptionalLine | None = None
    landmark: Landmark | None = None
    city: Place
    state: Place
    postal_code: PostalCode

    def to_domain(self) -> PostalAddress:
        return PostalAddress(**self.model_dump())


class SavedAddressIn(AddressIn):
    label: Label | None = None
    is_default: bool = False

    def to_domain_address(self) -> PostalAddress:
        return PostalAddress(**self.model_dump(exclude={"label", "is_default"}))


class AddressOut(BaseModel):
    full_name: str
    phone: str
    line1: str
    line2: str | None
    landmark: str | None
    city: str
    state: str
    postal_code: str
    country_code: str


class SavedAddressOut(AddressOut):
    id: UUID
    label: str | None
    is_default: bool

    @classmethod
    def of(cls, saved: SavedAddress) -> "SavedAddressOut":
        return cls(
            id=saved.id,
            label=saved.label,
            is_default=saved.is_default,
            **saved.address.snapshot(),
        )


# --- checkout ---------------------------------------------------------------------------------


class QuoteIn(_In):
    coupon_code: Code | None = None


class PaymentOptionOut(_Out):
    method: PaymentMethod
    label: str
    instructions: str


class CheckoutQuoteOut(BaseModel):
    bag: CartOut
    currency_code: str
    subtotal: Decimal
    discount_total: Decimal
    shipping_total: Decimal
    shipping_configured: bool
    grand_total: Decimal
    coupon_code: str | None
    coupon_error: str | None
    payment_methods: list[PaymentOptionOut]
    guest_checkout_enabled: bool
    signed_in: bool
    can_place_order: bool
    blocking_reason: str | None

    @classmethod
    def of(cls, quote: CheckoutQuote) -> "CheckoutQuoteOut":
        return cls(
            bag=CartOut.of(quote.bag),
            currency_code=quote.currency_code,
            subtotal=quote.subtotal,
            discount_total=quote.discount_total,
            shipping_total=quote.shipping_total,
            shipping_configured=quote.shipping_configured,
            grand_total=quote.grand_total,
            coupon_code=quote.coupon_code,
            coupon_error=quote.coupon_error,
            payment_methods=[PaymentOptionOut.model_validate(m) for m in quote.payment_methods],
            guest_checkout_enabled=quote.guest_checkout_enabled,
            signed_in=quote.signed_in,
            can_place_order=quote.can_place_order,
            blocking_reason=quote.blocking_reason,
        )


class CheckoutIn(_In):
    customer_name: Name
    customer_phone: Phone
    customer_email: Email | None = None
    address: AddressIn | None = None
    saved_address_id: UUID | None = None
    payment_method: PaymentMethod
    customer_note: Note | None = None
    coupon_code: Code | None = None
    save_address: bool = False
    # Guard only: if the server-calculated total differs, the order is not placed (409).
    expected_grand_total: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2
    )


# --- orders -----------------------------------------------------------------------------------


class OrderLineOut(_Out):
    product_name: str
    product_slug: str | None
    sku: str
    size: str | None
    colour: str | None
    image_url: str | None
    unit_selling_price: Decimal
    unit_original_price: Decimal | None
    quantity: int
    line_total: Decimal


class CustomerOrderOut(_Out):
    """What a customer sees: no internal status or tracking timeline (contact the shop)."""

    order_number: str
    placed_at: datetime
    payment_method: PaymentMethod | None
    customer_name: str
    customer_email: str
    customer_phone: str
    shipping_address: dict[str, Any]
    currency_code: str
    subtotal: Decimal
    discount_total: Decimal
    shipping_total: Decimal
    grand_total: Decimal
    coupon_code: str | None
    customer_note: str | None
    lines: list[OrderLineOut]


class PlacedOrderOut(CustomerOrderOut):
    payment_instructions: str | None = None


class CustomerOrderSummaryOut(_Out):
    order_number: str
    placed_at: datetime
    grand_total: Decimal
    item_count: int


class CustomerOrderListOut(BaseModel):
    items: list[CustomerOrderSummaryOut]
    total: int
    page: int
    pages: int


class AdminOrderOut(CustomerOrderOut):
    id: UUID
    user_id: UUID | None
    source: OrderSource
    status: OrderStatus
    payment_status: PaymentStatus
    internal_note: str | None


class AdminOrderSummaryOut(_Out):
    id: UUID
    order_number: str
    source: OrderSource
    status: OrderStatus
    payment_status: PaymentStatus
    payment_method: PaymentMethod | None
    customer_name: str
    grand_total: Decimal
    item_count: int
    placed_at: datetime


class AdminOrderListOut(BaseModel):
    items: list[AdminOrderSummaryOut]
    total: int
    page: int
    pages: int


class OrderStatusIn(_In):
    status: OrderStatus


class OrderPaymentIn(_In):
    payment_status: PaymentStatus
    payment_method: PaymentMethod | None = None


class OrderNoteIn(_In):
    internal_note: Note | None = None


# --- WhatsApp requests (admin) ----------------------------------------------------------------


class WhatsAppLineOut(_Out):
    variant_id: UUID | None
    product_name: str
    sku: str
    size: str | None
    colour: str | None
    unit_selling_price: Decimal
    quantity: int
    line_total: Decimal


class WhatsAppRequestOut(_Out):
    id: UUID
    reference: str
    status: WhatsAppRequestStatus
    user_id: UUID | None
    customer_name: str | None
    customer_phone: str | None
    message_text: str
    estimated_subtotal: Decimal
    staff_note: str | None
    contacted_at: datetime | None
    created_at: datetime
    converted_order_id: UUID | None
    converted_order_number: str | None
    lines: list[WhatsAppLineOut]


class WhatsAppRequestSummaryOut(_Out):
    id: UUID
    reference: str
    status: WhatsAppRequestStatus
    customer_name: str | None
    estimated_subtotal: Decimal
    item_count: int
    created_at: datetime
    converted_order_number: str | None


class WhatsAppRequestListOut(BaseModel):
    items: list[WhatsAppRequestSummaryOut]
    total: int
    page: int
    pages: int


class WhatsAppStatusIn(_In):
    status: WhatsAppRequestStatus
    staff_note: Note | None = None


class ConvertItemIn(_In):
    variant_id: UUID
    quantity: int = Field(ge=1, le=MAX_CART_LINE_QUANTITY)


class ConvertRequestIn(_In):
    customer_name: Name
    customer_phone: Phone
    customer_email: Email | None = None
    address: AddressIn
    payment_method: PaymentMethod
    items: list[ConvertItemIn] | None = Field(default=None, min_length=1, max_length=MAX_CART_LINES)
    internal_note: Note | None = None
    apply_shipping: bool = True
