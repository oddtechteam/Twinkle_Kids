from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.domain.enums import ProductStatus
from app.domain.errors import DomainValidationError
from app.domain.value_objects.pricing import PricePair, resolve_variant_price, to_money

MAX_VARIANTS = 200
MAX_PRODUCT_MEDIA = 30
MAX_BADGES = 3
MAX_BADGE_LENGTH = 24


@dataclass(slots=True)
class ProductVariant:
    id: UUID
    sku: str
    size: str | None = None
    colour: str | None = None
    colour_hex: str | None = None
    selling_price_override: Decimal | None = None
    original_price_override: Decimal | None = None
    stock_quantity: int = 0
    position: int = 0
    is_active: bool = True

    def __post_init__(self) -> None:
        if self.selling_price_override is not None:
            self.selling_price_override = to_money(
                self.selling_price_override, field="Variant selling price"
            )
        if self.original_price_override is not None:
            self.original_price_override = to_money(
                self.original_price_override, field="Variant original price"
            )
        if self.stock_quantity < 0:
            raise DomainValidationError("Stock quantity cannot be negative.")

    @property
    def option_key(self) -> tuple[str, str]:
        return ((self.size or "").casefold(), (self.colour or "").casefold())

    @property
    def label(self) -> str | None:
        parts = [p for p in (self.size, self.colour) if p]
        return " / ".join(parts) or None

    def effective_price(self, product_price: PricePair) -> PricePair:
        return resolve_variant_price(
            product_price,
            selling_override=self.selling_price_override,
            original_override=self.original_price_override,
        )


@dataclass(frozen=True, slots=True)
class ProductMediaLink:
    media_asset_id: UUID
    alt_text: str | None = None
    variant_id: UUID | None = None


@dataclass(slots=True)
class Product:
    id: UUID
    name: str
    slug: str
    sku: str
    price: PricePair
    status: ProductStatus = ProductStatus.DRAFT
    short_description: str | None = None
    description: str | None = None
    rich_content: dict[str, Any] | None = None
    track_inventory: bool = True
    allow_backorder: bool = False
    low_stock_threshold: int = 3
    size_chart_id: UUID | None = None
    seo_title: str | None = None
    seo_description: str | None = None
    seo_metadata: dict[str, Any] = field(default_factory=dict)
    category_ids: list[UUID] = field(default_factory=list)
    primary_category_id: UUID | None = None
    variants: list[ProductVariant] = field(default_factory=list)
    media: list[ProductMediaLink] = field(default_factory=list)  # ordered: index = position
    badges: list[str] = field(default_factory=list)  # admin-managed labels, e.g. "New season"
    published_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def validate(self) -> None:
        if not self.name.strip():
            raise DomainValidationError("Product name is required.")
        if self.low_stock_threshold < 0:
            raise DomainValidationError("Low-stock threshold cannot be negative.")
        if len(self.variants) > MAX_VARIANTS:
            raise DomainValidationError(f"A product can have at most {MAX_VARIANTS} variants.")
        if len(self.badges) > MAX_BADGES:
            raise DomainValidationError(f"A product can show at most {MAX_BADGES} badges.")
        if any(not b.strip() or len(b) > MAX_BADGE_LENGTH for b in self.badges):
            raise DomainValidationError(f"Badges must be 1-{MAX_BADGE_LENGTH} characters.")
        if len(self.media) > MAX_PRODUCT_MEDIA:
            raise DomainValidationError(f"A product can have at most {MAX_PRODUCT_MEDIA} images.")

        skus = [v.sku for v in self.variants]
        if len(set(skus)) != len(skus):
            raise DomainValidationError("Variant SKUs must be unique.")
        options = [v.option_key for v in self.variants]
        if len(set(options)) != len(options):
            raise DomainValidationError("Each size/colour combination may appear only once.")
        for variant in self.variants:
            variant.effective_price(self.price)  # raises PricingError if the combination is invalid

        if len(set(self.category_ids)) != len(self.category_ids):
            raise DomainValidationError("A category can only be assigned once.")
        if (
            self.primary_category_id is not None
            and self.primary_category_id not in self.category_ids
        ):
            raise DomainValidationError(
                "The primary category must be one of the product's categories."
            )
        media_ids = [m.media_asset_id for m in self.media]
        if len(set(media_ids)) != len(media_ids):
            raise DomainValidationError("An image can only be attached once.")
        variant_ids = {v.id for v in self.variants}
        if any(m.variant_id is not None and m.variant_id not in variant_ids for m in self.media):
            raise DomainValidationError("Image variant must belong to this product.")

        if self.status is ProductStatus.ACTIVE and not any(v.is_active for v in self.variants):
            raise DomainValidationError("An active product needs at least one active variant.")

    def change_status(self, status: ProductStatus, *, now: datetime) -> None:
        self.status = status
        if status is ProductStatus.ACTIVE and self.published_at is None:
            self.published_at = now
        self.validate()


@dataclass(slots=True)
class Category:
    id: UUID
    name: str
    slug: str
    description: str | None = None
    parent_id: UUID | None = None
    image_media_id: UUID | None = None
    is_active: bool = True
    display_order: int = 0
    custom_product_ordering: bool = False
    seo_title: str | None = None
    seo_description: str | None = None
    seo_metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.name.strip():
            raise DomainValidationError("Category name is required.")
        if self.parent_id == self.id:
            raise DomainValidationError("A category cannot be its own parent.")
