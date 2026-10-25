"""Cart and WhatsApp-request contracts. The browser sends identities and quantities only."""

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.api.schemas.catalog import ImageOut, PriceOut
from app.application.use_cases.cart import CartView
from app.application.use_cases.whatsapp import WhatsAppLink
from app.domain.entities.commerce import MAX_CART_LINE_QUANTITY, MAX_CART_LINES

Quantity = Annotated[int, Field(ge=1, le=MAX_CART_LINE_QUANTITY)]


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AddCartItemIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variant_id: UUID
    quantity: Quantity = 1


class UpdateCartItemIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quantity: Quantity


class CartLineOut(_Out):
    item_id: UUID
    product_id: UUID
    variant_id: UUID
    product_name: str
    product_slug: str | None
    sku: str | None
    size: str | None
    colour: str | None
    image: ImageOut | None
    price: PriceOut | None
    quantity: int
    line_total: Decimal | None
    available: bool
    max_quantity: int
    issue: str | None
    previous_price: Decimal | None


class CartOut(_Out):
    """Backend-calculated bag. Totals cover available lines only."""

    id: UUID | None
    currency_code: str
    lines: list[CartLineOut]
    item_count: int
    subtotal: Decimal
    savings: Decimal
    shipping_total: Decimal | None
    grand_total: Decimal
    has_issues: bool
    has_price_changes: bool

    @classmethod
    def of(cls, view: CartView) -> "CartOut":
        out = cls.model_validate(view)
        for line in out.lines:
            if line.price is not None:
                line.price.currency = view.currency_code
        return out


class WhatsAppItemIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variant_id: UUID
    quantity: Quantity = 1


class WhatsAppRequestIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[WhatsAppItemIn] = Field(min_length=1, max_length=MAX_CART_LINES)
    customer_name: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)] | None = (
        None
    )


class WhatsAppLinkOut(_Out):
    """`url` opens WhatsApp with the message pre-filled. Opening it is not proof of sending."""

    reference: str
    url: str
    message: str
    estimated_subtotal: Decimal
    currency_code: str

    @classmethod
    def of(cls, link: WhatsAppLink) -> "WhatsAppLinkOut":
        return cls.model_validate(link)
