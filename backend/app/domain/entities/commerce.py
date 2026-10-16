"""Order-line snapshots: what a customer bought, frozen at purchase time."""

from dataclasses import dataclass
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
