"""Admin request models. Prices are Decimal with exactly-representable 2-dp values."""

from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

from app.application.use_cases.catalog_admin import (
    CategoryInput,
    MediaInput,
    ProductInput,
    VariantInput,
)
from app.application.use_cases.collections import CollectionInput
from app.application.use_cases.homepage import SectionInput
from app.application.use_cases.site import (
    NavigationInput,
    PageInput,
    ShippingRuleInput,
    SizeChartInput,
)
from app.domain.enums import (
    HomepageSectionType,
    NavigationLinkType,
    NavigationMenu,
    ProductStatus,
    PublishStatus,
    SelectionMode,
)

Price = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Slug = Annotated[str, StringConstraints(strip_whitespace=True, max_length=160)]
Sku = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
ShortText = Annotated[str, StringConstraints(max_length=40)]
Badge = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=24)]


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- Products ---------------------------------------------------------------------------------


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
    collection_ids: list[UUID] | None = Field(default=None, max_length=30)
    badges: list[Badge] = Field(default_factory=list, max_length=3)
    is_featured: bool = False
    related_product_ids: list[UUID] = Field(default_factory=list, max_length=12)
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
            collection_ids=self.collection_ids,
            badges=list(self.badges),
            is_featured=self.is_featured,
            related_product_ids=list(self.related_product_ids),
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


# --- Categories & collections -----------------------------------------------------------------


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


class IdsIn(_In):
    ids: list[UUID] = Field(max_length=500)


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


class PublishStatusIn(_In):
    status: PublishStatus


# --- Homepage builder -------------------------------------------------------------------------


class SectionIn(_In):
    section_type: HomepageSectionType
    title: Annotated[str, StringConstraints(max_length=120)] | None = None
    subtitle: Annotated[str, StringConstraints(max_length=255)] | None = None
    settings: dict[str, Any] = Field(default_factory=dict)
    is_visible: bool = True
    desktop_media_id: UUID | None = None
    mobile_media_id: UUID | None = None
    selection_mode: SelectionMode = SelectionMode.NONE
    source_category_id: UUID | None = None
    source_collection_id: UUID | None = None
    product_limit: int = Field(default=12, ge=1, le=48)

    def to_input(self) -> SectionInput:
        return SectionInput(**self.model_dump())


class VisibilityIn(_In):
    is_visible: bool


class PublishIn(_In):
    note: Annotated[str, StringConstraints(max_length=200)] | None = None


# --- Settings ---------------------------------------------------------------------------------


class SettingsPatch(_In):
    """Partial update: only fields present in the request are changed."""

    store_name: Annotated[str, StringConstraints(max_length=120)] | None = None
    tagline: Annotated[str, StringConstraints(max_length=200)] | None = None
    logo_media_id: UUID | None = None
    favicon_media_id: UUID | None = None
    theme: dict[str, Any] | None = None
    announcement: dict[str, Any] | None = None
    contact_email: EmailStr | None = None
    contact_phone: Annotated[str, StringConstraints(max_length=20)] | None = None
    business_address: Annotated[str, StringConstraints(max_length=500)] | None = None
    business_hours: Annotated[str, StringConstraints(max_length=120)] | None = None
    social_links: dict[str, Any] | None = None
    guest_checkout_enabled: bool | None = None
    whatsapp_ordering_enabled: bool | None = None
    whatsapp_number: Annotated[str, StringConstraints(max_length=20)] | None = None
    whatsapp_message_template: Annotated[str, StringConstraints(max_length=500)] | None = None
    payment_options: list[dict[str, Any]] | None = None
    shipping_settings: dict[str, Any] | None = None
    order_policies: dict[str, Any] | None = None
    default_product_sort: str | None = None
    default_low_stock_threshold: int | None = Field(default=None, ge=0, le=10_000)
    seo_defaults: dict[str, Any] | None = None

    def changes(self) -> dict[str, Any]:
        data = self.model_dump(exclude_unset=True)
        if "contact_email" in data and data["contact_email"] is not None:
            data["contact_email"] = str(data["contact_email"]).lower()
        if "store_name" in data and not data["store_name"]:
            data.pop("store_name")
        return data


# --- Navigation, pages, shipping, size charts -------------------------------------------------


class NavigationIn(_In):
    menu: NavigationMenu
    label: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
    link_type: NavigationLinkType
    parent_id: UUID | None = None
    category_id: UUID | None = None
    collection_id: UUID | None = None
    page_id: UUID | None = None
    url: Annotated[str, StringConstraints(max_length=500)] | None = None
    is_active: bool = True
    open_in_new_tab: bool = False

    def to_input(self) -> NavigationInput:
        return NavigationInput(**self.model_dump())


class PageIn(_In):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
    slug: Slug | None = None
    content: dict[str, Any] = Field(default_factory=lambda: {"blocks": []})
    status: PublishStatus = PublishStatus.DRAFT
    seo_title: Annotated[str, StringConstraints(max_length=70)] | None = None
    seo_description: Annotated[str, StringConstraints(max_length=320)] | None = None

    def to_input(self) -> PageInput:
        return PageInput(**self.model_dump(exclude={"slug"}), slug=self.slug or None)


class ShippingRuleIn(_In):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
    fee: Price
    min_order_amount: Price = Decimal("0.00")
    max_order_amount: Price | None = None
    priority: int = Field(default=100, ge=0, le=10_000)
    is_active: bool = True

    def to_input(self) -> ShippingRuleInput:
        return ShippingRuleInput(**self.model_dump())


class SizeChartIn(_In):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    slug: Slug | None = None
    description: Annotated[str, StringConstraints(max_length=2000)] | None = None
    chart: dict[str, Any]

    def to_input(self) -> SizeChartInput:
        return SizeChartInput(
            name=self.name, chart=self.chart, slug=self.slug or None, description=self.description
        )


class MediaPatchIn(_In):
    alt_text: Annotated[str, StringConstraints(max_length=300)] | None = None


class CreatedOut(BaseModel):
    id: UUID
