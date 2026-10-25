"""Order-line snapshots (what a customer bought, frozen at purchase time), carts and
WhatsApp order requests."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.domain.entities.catalog import Product, ProductVariant
from app.domain.enums import ProductStatus
from app.domain.errors import DomainValidationError
from app.domain.value_objects.pricing import PricedLine, PricePair


@dataclass(frozen=True, slots=True)
class OrderLineSnapshot:
    product_id: UUID
    variant_id: UUID
    product_name: str
    product_slug: str
    sku: str
    size: str | None
    colour: str | None
    unit_price: PricePair
    quantity: int
    image_url: str | None = None

    @property
    def priced(self) -> PricedLine:
        return PricedLine(self.unit_price, self.quantity)

    @classmethod
    def capture(
        cls,
        product: Product,
        variant_id: UUID,
        quantity: int,
        *,
        image_url: str | None = None,
    ) -> "OrderLineSnapshot":
        """Resolve the purchasable variant and copy everything an order needs to keep."""
        variant = _find_variant(product, variant_id)
        if product.status is not ProductStatus.ACTIVE or not variant.is_active:
            raise DomainValidationError(f"{product.name} is not available.")
        if (
            product.track_inventory
            and not product.allow_backorder
            and variant.stock_quantity < quantity
        ):
            raise DomainValidationError(f"Only {variant.stock_quantity} left of {product.name}.")
        line = cls(
            product_id=product.id,
            variant_id=variant.id,
            product_name=product.name,
            product_slug=product.slug,
            sku=variant.sku,
            size=variant.size,
            colour=variant.colour,
            unit_price=variant.effective_price(product.price),
            quantity=quantity,
            image_url=image_url,
        )
        line.priced  # noqa: B018 - validates quantity
        return line


def _find_variant(product: Product, variant_id: UUID) -> ProductVariant:
    for variant in product.variants:
        if variant.id == variant_id:
            return variant
    raise DomainValidationError("The selected option does not belong to this product.")


# --- Cart -------------------------------------------------------------------------------------

MAX_CART_LINE_QUANTITY = 99  # matches the cart_items quantity CHECK constraint
MAX_CART_LINES = 50


@dataclass(frozen=True, slots=True)
class CartItem:
    """A cart line holds identity and quantity only; prices are resolved from the catalogue."""

    id: UUID
    variant_id: UUID
    product_id: UUID
    quantity: int
    unit_price_snapshot: Decimal | None = None


@dataclass(frozen=True, slots=True)
class Cart:
    id: UUID
    user_id: UUID | None
    items: tuple[CartItem, ...] = ()

    def item(self, item_id: UUID) -> CartItem | None:
        return next((i for i in self.items if i.id == item_id), None)

    def item_for_variant(self, variant_id: UUID) -> CartItem | None:
        return next((i for i in self.items if i.variant_id == variant_id), None)


def validate_cart_quantity(quantity: int) -> int:
    if isinstance(quantity, bool) or not isinstance(quantity, int):
        raise DomainValidationError("Quantity must be a whole number.")
    if not 1 <= quantity <= MAX_CART_LINE_QUANTITY:
        raise DomainValidationError(f"Quantity must be between 1 and {MAX_CART_LINE_QUANTITY}.")
    return quantity


# --- WhatsApp order requests ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class WhatsAppOrderRequest:
    """What the customer was handed in a WhatsApp link. Not an order, not proof of sending."""

    id: UUID
    reference: str
    user_id: UUID | None
    message_text: str
    lines: tuple[OrderLineSnapshot, ...]
    estimated_subtotal: Decimal
    customer_name: str | None = None
    customer_phone: str | None = None
