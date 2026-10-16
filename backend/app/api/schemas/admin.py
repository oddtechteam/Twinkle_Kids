"""Admin request models. Prices are Decimal with exactly-representable 2-dp values."""

from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.application.use_cases.catalog_admin import (
    CategoryInput,
    MediaInput,
    ProductInput,
    VariantInput,
)
from app.application.use_cases.merchandising import CollectionInput, HomepageSectionInput
from app.domain.enums import HomepageSectionType, ProductStatus, PublishStatus, SelectionMode

Price = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Slug = Annotated[str, StringConstraints(strip_whitespace=True, max_length=160)]
Sku = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
ShortText = Annotated[str, StringConstraints(max_length=40)]


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VariantIn(_In):
    id: UUID | None = None
    sku: Sku
    size: ShortText | None = None
    colour: ShortText | None = None
    colour_hex: Annotated[str, StringConstraints(pattern=r"^#[0-9a-fA-F]{6}$")] | None = None
    selling_price: Price | None = Field(default=None, description="Override; null inherits")
    original_price: Price | None = Field(default=None, description="Override; null inherits")
    stock_quantity: int = Field(default=0, ge=0, le=1_000_000)
    is_active: bool = True


class ProductMediaIn(_In):
    media_asset_id: UUID
    alt_text: Annotated[str, StringConstraints(max_length=300)] | None = None
    variant_sku: Sku | None = None


class ProductIn(_In):
    name: Name
    slug: Slug | None = None
    sku: Sku
    selling_price: Price
    original_price: Price | None = None
    status: ProductStatus = ProductStatus.DRAFT
    short_description: Annotated[str, StringConstraints(max_length=500)] | None = None
    description: Annotated[str, StringConstraints(max_length=20_000)] | None = None
    rich_content: dict[str, Any] | None = None
    track_inventory: bool = True
    allow_backorder: bool = False
    low_stock_threshold: int = Field(default=3, ge=0, le=10_000)
    size_chart_id: UUID | None = None
    seo_title: Annotated[str, StringConstraints(max_length=70)] | None = None
    seo_description: Annotated[str, StringConstraints(max_length=320)] | None = None
    seo_metadata: dict[str, Any] = Field(default_factory=dict)
    category_ids: list[UUID] = Field(default_factory=list, max_length=20)
    primary_category_id: UUID | None = None
    variants: list[VariantIn] = Field(min_length=1, max_length=200)
    media: list[ProductMediaIn] = Field(default_factory=list, max_length=30)

    def to_input(self) -> ProductInput:
        return ProductInput(
            name=self.name,
            slug=self.slug or None,
            sku=self.sku,
            selling_price=self.selling_price,
            original_price=self.original_price,
            status=self.status,
            short_description=self.short_description,
            description=self.description,
            rich_content=self.rich_content,
            track_inventory=self.track_inventory,
            allow_backorder=self.allow_backorder,
            low_stock_threshold=self.low_stock_threshold,
            size_chart_id=self.size_chart_id,
            seo_title=self.seo_title,
            seo_description=self.seo_description,
            seo_metadata=self.seo_metadata,
            category_ids=self.category_ids,
            primary_category_id=self.primary_category_id,
            variants=[
                VariantInput(
                    id=v.id,
                    sku=v.sku,
                    size=v.size,
                    colour=v.colour,
                    colour_hex=v.colour_hex,
                    selling_price_override=v.selling_price,
                    original_price_override=v.original_price,
                    stock_quantity=v.stock_quantity,
                    is_active=v.is_active,
                )
                for v in self.variants
            ],
            media=[MediaInput(m.media_asset_id, m.alt_text, m.variant_sku) for m in self.media],
        )


class ProductStatusIn(_In):
    status: ProductStatus


class CategoryIn(_In):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    slug: Slug | None = None
    description: Annotated[str, StringConstraints(max_length=5000)] | None = None
    parent_id: UUID | None = None
    image_media_id: UUID | None = None
    is_active: bool = True
    display_order: int = Field(default=0, ge=0, le=100_000)
    custom_product_ordering: bool = False
    seo_title: Annotated[str, StringConstraints(max_length=70)] | None = None
    seo_description: Annotated[str, StringConstraints(max_length=320)] | None = None
    seo_metadata: dict[str, Any] = Field(default_factory=dict)

    def to_input(self) -> CategoryInput:
        return CategoryInput(**self.model_dump(exclude={"slug"}), slug=self.slug or None)


class ActiveIn(_In):
    is_active: bool


class OrderingIn(_In):
    product_ids: list[UUID] = Field(max_length=500)


class CollectionIn(_In):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    slug: Slug | None = None
    description: Annotated[str, StringConstraints(max_length=5000)] | None = None
    image_media_id: UUID | None = None
    status: PublishStatus = PublishStatus.DRAFT
    display_order: int = Field(default=0, ge=0)
    seo_title: Annotated[str, StringConstraints(max_length=70)] | None = None
    seo_description: Annotated[str, StringConstraints(max_length=320)] | None = None

    def to_input(self) -> CollectionInput:
        return CollectionInput(**self.model_dump(exclude={"slug"}), slug=self.slug or None)


class HomepageSectionIn(_In):
    section_type: HomepageSectionType
    title: Annotated[str, StringConstraints(max_length=120)] | None = None
    subtitle: Annotated[str, StringConstraints(max_length=255)] | None = None
    settings: dict[str, Any] = Field(default_factory=dict)
    is_visible: bool = True
    status: PublishStatus = PublishStatus.DRAFT
    position: int = Field(default=0, ge=0)
    desktop_media_id: UUID | None = None
    mobile_media_id: UUID | None = None
    selection_mode: SelectionMode = SelectionMode.NONE
    source_category_id: UUID | None = None
    source_collection_id: UUID | None = None
    product_limit: int = Field(default=12, ge=1, le=48)

    def to_input(self) -> HomepageSectionInput:
        return HomepageSectionInput(**self.model_dump())


class CreatedOut(BaseModel):
    id: UUID
