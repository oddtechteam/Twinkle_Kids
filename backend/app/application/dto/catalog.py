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
    # Public stock signal: tracked, in stock and at or below the product's low-stock threshold.
    low_stock: bool = False


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
    badges: list[str] = field(default_factory=list)
    secondary_image: ImageView | None = None  # second gallery image (card hover)
    category: CategoryRef | None = None  # primary (or first active) category


@dataclass(frozen=True, slots=True)
class CollectionRef:
    id: UUID
    name: str
    slug: str


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
    badges: list[str] = field(default_factory=list)
    size_chart_id: UUID | None = None
    collection_ids: list[UUID] = field(default_factory=list)  # admin view only
    collections: list[CollectionRef] = field(default_factory=list)  # published, storefront view


@dataclass(frozen=True, slots=True)
class CollectionSummary:
    id: UUID
    name: str
    slug: str
    description: str | None
    image: ImageView | None
    status: str
    display_order: int
    seo_title: str | None = None
    seo_description: str | None = None


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


@dataclass(frozen=True, slots=True)
class ColourOption:
    name: str
    hex: str | None


@dataclass(frozen=True, slots=True)
class CatalogFacets:
    """Filter options available within a listing scope (category / collection / search).

    Option lists ignore the size, colour, price and availability filters themselves, so
    choosing one option never hides its siblings.
    """

    sizes: list[str]
    colours: list[ColourOption]
    min_price: Decimal | None
    max_price: Decimal | None
    total: int


@dataclass(frozen=True, slots=True)
class ReviewView:
    rating: int
    title: str | None
    body: str | None
    author: str | None  # first name only
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ReviewSummary:
    average: Decimal | None
    count: int
    items: list[ReviewView]


@dataclass(frozen=True, slots=True)
class SitemapEntry:
    slug: str
    updated_at: datetime | None


@dataclass(frozen=True, slots=True)
class SitemapView:
    """Public, indexable URLs only: active products/categories, published collections/pages."""

    products: list[SitemapEntry]
    categories: list[SitemapEntry]
    collections: list[SitemapEntry]
    pages: list[SitemapEntry]
