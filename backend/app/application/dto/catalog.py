"""Read models returned by catalogue queries. Prices are derived from PricePair only."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from app.domain.enums import ProductStatus
from app.domain.value_objects.pricing import PricePair

MAX_PAGE_SIZE = 60


class ProductSort(StrEnum):
    FEATURED = "featured"  # category custom order when enabled, otherwise newest
    NEWEST = "newest"
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"
    NAME_ASC = "name_asc"


@dataclass(frozen=True, slots=True)
class PriceView:
    selling_price: Decimal
    original_price: Decimal | None
    discount_amount: Decimal | None
    discount_percent: int | None

    @classmethod
    def of(cls, price: PricePair) -> "PriceView":
        return cls(
            selling_price=price.selling,
            original_price=price.original,
            discount_amount=price.discount_amount,
            discount_percent=price.discount_percent,
        )


@dataclass(frozen=True, slots=True)
class ImageView:
    media_asset_id: UUID
    url: str
    alt_text: str | None
    width: int
    height: int
    variant_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class CategoryRef:
    id: UUID
    name: str
    slug: str


@dataclass(frozen=True, slots=True)
class VariantView:
    id: UUID
    sku: str
    size: str | None
    colour: str | None
    colour_hex: str | None
    price: PriceView
    selling_price_override: Decimal | None
    original_price_override: Decimal | None
    in_stock: bool
    stock_quantity: int | None  # only populated for admin views
    is_active: bool


@dataclass(frozen=True, slots=True)
class ProductSummary:
    id: UUID
    name: str
    slug: str
    price: PriceView  # product-level stored prices
    from_price: Decimal  # lowest effective selling price across active variants
    price_varies: bool
    in_stock: bool
    primary_image: ImageView | None
    status: ProductStatus
    published_at: datetime | None


@dataclass(frozen=True, slots=True)
class ProductDetail:
    id: UUID
    name: str
    slug: str
    sku: str
    status: ProductStatus
    short_description: str | None
    description: str | None
    rich_content: dict[str, Any] | None
    price: PriceView
    in_stock: bool
    track_inventory: bool
    allow_backorder: bool
    low_stock_threshold: int
    sizes: list[str]
    colours: list[str]
    variants: list[VariantView]
    images: list[ImageView]
    categories: list[CategoryRef]
    primary_category_id: UUID | None
    size_chart: dict[str, Any] | None
    seo_title: str | None
    seo_description: str | None
    seo_metadata: dict[str, Any]
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class CategorySummary:
    id: UUID
    name: str
    slug: str
    description: str | None
    parent_id: UUID | None
    image: ImageView | None
    display_order: int
    is_active: bool
    custom_product_ordering: bool
    seo_title: str | None
    seo_description: str | None


@dataclass(frozen=True, slots=True)
class CategoryDetail:
    category: CategorySummary
    children: list[CategorySummary]
    breadcrumbs: list[CategoryRef]
    seo_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ProductFilters:
    page: int = 1
    page_size: int = 24
    category_slug: str | None = None
    collection_slug: str | None = None
    search: str | None = None
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    sizes: tuple[str, ...] = ()
    colours: tuple[str, ...] = ()
    in_stock: bool | None = None
    sort: ProductSort = ProductSort.FEATURED
    statuses: tuple[ProductStatus, ...] = (ProductStatus.ACTIVE,)


@dataclass(frozen=True, slots=True)
class Page[T]:
    items: list[T]
    total: int
    page: int
    page_size: int

    @property
    def pages(self) -> int:
        return max(1, -(-self.total // self.page_size))
