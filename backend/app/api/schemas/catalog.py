"""Catalogue response models. Built from application DTOs (from_attributes)."""

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.application.dto.catalog import Page, ProductSummary
from app.domain.entities.catalog import Category
from app.domain.enums import ProductStatus


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PriceOut(_Out):
    """Stored prices plus a discount derived from them (only when MRP > selling price)."""

    selling_price: Decimal
    original_price: Decimal | None
    discount_amount: Decimal | None
    discount_percent: int | None
    currency: str = "INR"


class ImageOut(_Out):
    media_asset_id: UUID
    url: str
    alt_text: str | None
    width: int
    height: int
    variant_id: UUID | None = None


class CategoryRefOut(_Out):
    id: UUID
    name: str
    slug: str


class VariantOut(_Out):
    id: UUID
    sku: str
    size: str | None
    colour: str | None
    colour_hex: str | None
    price: PriceOut
    in_stock: bool
    is_active: bool


class AdminVariantOut(VariantOut):
    selling_price_override: Decimal | None
    original_price_override: Decimal | None
    stock_quantity: int | None


class ProductSummaryOut(_Out):
    id: UUID
    name: str
    slug: str
    price: PriceOut
    from_price: Decimal
    price_varies: bool
    in_stock: bool
    primary_image: ImageOut | None
    badges: list[str] = []


class AdminProductSummaryOut(ProductSummaryOut):
    status: ProductStatus
    published_at: datetime | None


class ProductListOut(BaseModel):
    items: list[ProductSummaryOut]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def of(cls, page: Page[ProductSummary]) -> "ProductListOut":
        return cls(
            items=[ProductSummaryOut.model_validate(p) for p in page.items],
            total=page.total,
            page=page.page,
            page_size=page.page_size,
            pages=page.pages,
        )


class AdminProductListOut(BaseModel):
    items: list[AdminProductSummaryOut]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def of(cls, page: Page[ProductSummary]) -> "AdminProductListOut":
        return cls(
            items=[AdminProductSummaryOut.model_validate(p) for p in page.items],
            total=page.total,
            page=page.page,
            page_size=page.page_size,
            pages=page.pages,
        )


class ProductDetailOut(_Out):
    id: UUID
    name: str
    slug: str
    sku: str
    short_description: str | None
    description: str | None
    rich_content: dict[str, Any] | None
    price: PriceOut
    in_stock: bool
    sizes: list[str]
    colours: list[str]
    variants: list[VariantOut]
    images: list[ImageOut]
    categories: list[CategoryRefOut]
    size_chart: dict[str, Any] | None
    seo_title: str | None
    seo_description: str | None
    seo_metadata: dict[str, Any]
    published_at: datetime | None
    badges: list[str] = []


class AdminProductDetailOut(ProductDetailOut):
    status: ProductStatus
    track_inventory: bool
    allow_backorder: bool
    low_stock_threshold: int
    primary_category_id: UUID | None
    variants: list[AdminVariantOut]  # type: ignore[assignment]
    size_chart_id: UUID | None = None
    collection_ids: list[UUID] = []
    created_at: datetime
    updated_at: datetime


class CategoryOut(_Out):
    id: UUID
    name: str
    slug: str
    description: str | None
    parent_id: UUID | None
    image: ImageOut | None
    display_order: int
    seo_title: str | None
    seo_description: str | None


class AdminCategoryOut(CategoryOut):
    is_active: bool
    custom_product_ordering: bool


class CategoryDetailOut(BaseModel):
    category: CategoryOut
    children: list[CategoryOut]
    breadcrumbs: list[CategoryRefOut]
    seo_metadata: dict[str, Any]
    products: ProductListOut


class AdminCategoryDetailOut(BaseModel):
    """Editable category fields plus its products in this category's own order."""

    id: UUID
    name: str
    slug: str
    description: str | None
    parent_id: UUID | None
    image_media_id: UUID | None
    is_active: bool
    display_order: int
    custom_product_ordering: bool
    seo_title: str | None
    seo_description: str | None
    seo_metadata: dict[str, Any]
    products: list[AdminProductSummaryOut]

    @classmethod
    def of(cls, c: Category, products: Sequence[ProductSummary]) -> "AdminCategoryDetailOut":
        return cls(
            id=c.id,
            name=c.name,
            slug=c.slug,
            description=c.description,
            parent_id=c.parent_id,
            image_media_id=c.image_media_id,
            is_active=c.is_active,
            display_order=c.display_order,
            custom_product_ordering=c.custom_product_ordering,
            seo_title=c.seo_title,
            seo_description=c.seo_description,
            seo_metadata=c.seo_metadata,
            products=[AdminProductSummaryOut.model_validate(p) for p in products],
        )
