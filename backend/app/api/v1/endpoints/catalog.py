"""Public storefront catalogue (active products and categories only)."""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CatalogReaderDep
from app.api.schemas.catalog import (
    CategoryDetailOut,
    CategoryOut,
    CategoryRefOut,
    FacetsOut,
    ProductDetailOut,
    ProductListOut,
    ReviewSummaryOut,
    SitemapOut,
)
from app.application.dto.catalog import MAX_PAGE_SIZE, ProductFilters, ProductSort

router = APIRouter(tags=["catalog"])

PageQ = Annotated[int, Query(ge=1, le=10_000)]
PageSizeQ = Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)]
PriceQ = Annotated[Decimal | None, Query(ge=0, max_digits=12, decimal_places=2)]


@router.get("/products", response_model=ProductListOut)
def list_products(
    reader: CatalogReaderDep,
    page: PageQ = 1,
    page_size: PageSizeQ = 24,
    category: Annotated[str | None, Query(max_length=160)] = None,
    collection: Annotated[str | None, Query(max_length=160)] = None,
    q: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    min_price: PriceQ = None,
    max_price: PriceQ = None,
    size: Annotated[list[str] | None, Query(max_length=20)] = None,
    colour: Annotated[list[str] | None, Query(max_length=20)] = None,
    in_stock: bool | None = None,
    sort: ProductSort = ProductSort.FEATURED,
) -> ProductListOut:
    filters = ProductFilters(
        page=page,
        page_size=page_size,
        category_slug=category,
        collection_slug=collection,
        search=q,
        min_price=min_price,
        max_price=max_price,
        sizes=tuple(size or ()),
        colours=tuple(colour or ()),
        in_stock=in_stock,
        sort=sort,
    )
    return ProductListOut.of(reader.list_products(filters))


@router.get("/products/facets", response_model=FacetsOut)
def product_facets(
    reader: CatalogReaderDep,
    category: Annotated[str | None, Query(max_length=160)] = None,
    collection: Annotated[str | None, Query(max_length=160)] = None,
    q: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
) -> FacetsOut:
    """Size, colour and price options available in a listing scope (for filter panels)."""
    facets = reader.facets(
        ProductFilters(category_slug=category, collection_slug=collection, search=q)
    )
    return FacetsOut.model_validate(facets)


@router.get("/products/{slug}/reviews", response_model=ReviewSummaryOut)
def product_reviews(slug: str, reader: CatalogReaderDep) -> ReviewSummaryOut:
    """Approved customer reviews only."""
    return ReviewSummaryOut.model_validate(reader.reviews(slug))


@router.get("/sitemap", response_model=SitemapOut)
def sitemap(reader: CatalogReaderDep) -> SitemapOut:
    """Indexable storefront slugs: active products/categories, published collections/pages."""
    return SitemapOut.model_validate(reader.sitemap())


@router.get("/products/{slug}", response_model=ProductDetailOut)
def get_product(slug: str, reader: CatalogReaderDep) -> ProductDetailOut:
    return ProductDetailOut.model_validate(reader.product(slug))


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(reader: CatalogReaderDep) -> list[CategoryOut]:
    return [CategoryOut.model_validate(c) for c in reader.categories()]


@router.get("/categories/{slug}", response_model=CategoryDetailOut)
def get_category(
    slug: str,
    reader: CatalogReaderDep,
    page: PageQ = 1,
    page_size: PageSizeQ = 24,
    sort: ProductSort = ProductSort.FEATURED,
) -> CategoryDetailOut:
    detail = reader.category(slug)
    products = reader.list_products(
        ProductFilters(page=page, page_size=page_size, category_slug=slug, sort=sort)
    )
    return CategoryDetailOut(
        category=CategoryOut.model_validate(detail.category),
        children=[CategoryOut.model_validate(c) for c in detail.children],
        breadcrumbs=[CategoryRefOut.model_validate(b) for b in detail.breadcrumbs],
        seo_metadata=detail.seo_metadata,
        products=ProductListOut.of(products),
    )
