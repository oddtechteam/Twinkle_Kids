"""Administrative API. Every route requires an authenticated staff user with the named
permission (checked server-side in app.api.deps.require_permission)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import (
    CatalogManagerDep,
    CatalogReaderDep,
    CategoryCommandsDep,
    ContentManagerDep,
    MerchandisingDep,
    ProductCommandsDep,
    StaffUserDep,
)
from app.api.schemas.admin import (
    ActiveIn,
    CategoryIn,
    CollectionIn,
    CreatedOut,
    HomepageSectionIn,
    OrderingIn,
    ProductIn,
    ProductStatusIn,
)
from app.api.schemas.auth import AdminMeOut
from app.api.schemas.catalog import (
    AdminCategoryOut,
    AdminProductDetailOut,
    AdminProductListOut,
    ProductSummaryOut,
)
from app.application.dto.catalog import MAX_PAGE_SIZE, ProductFilters, ProductSort
from app.domain.enums import ProductStatus

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/me", response_model=AdminMeOut, summary="Verify admin access and list permissions")
def admin_me(user: StaffUserDep) -> AdminMeOut:
    return AdminMeOut.of(user)


# --- Products ---------------------------------------------------------------------------------


@router.get("/products", response_model=AdminProductListOut)
def admin_list_products(
    _: CatalogManagerDep,
    reader: CatalogReaderDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 24,
    q: Annotated[str | None, Query(max_length=100)] = None,
    status_filter: Annotated[list[ProductStatus] | None, Query(alias="status")] = None,
    sort: ProductSort = ProductSort.NEWEST,
) -> AdminProductListOut:
    statuses = tuple(
        status_filter or (ProductStatus.DRAFT, ProductStatus.ACTIVE, ProductStatus.ARCHIVED)
    )
    filters = ProductFilters(page=page, page_size=page_size, search=q, statuses=statuses, sort=sort)
    return AdminProductListOut.of(reader.list_products(filters))


@router.post("/products", response_model=AdminProductDetailOut, status_code=status.HTTP_201_CREATED)
def admin_create_product(
    body: ProductIn, user: CatalogManagerDep, commands: ProductCommandsDep, reader: CatalogReaderDep
) -> AdminProductDetailOut:
    product_id = commands.create(body.to_input(), actor_id=user.id)
    return AdminProductDetailOut.model_validate(reader.admin_product(product_id))


@router.get("/products/{product_id}", response_model=AdminProductDetailOut)
def admin_get_product(
    product_id: UUID, _: CatalogManagerDep, reader: CatalogReaderDep
) -> AdminProductDetailOut:
    return AdminProductDetailOut.model_validate(reader.admin_product(product_id))


@router.put("/products/{product_id}", response_model=AdminProductDetailOut)
def admin_update_product(
    product_id: UUID,
    body: ProductIn,
    user: CatalogManagerDep,
    commands: ProductCommandsDep,
    reader: CatalogReaderDep,
) -> AdminProductDetailOut:
    commands.update(product_id, body.to_input(), actor_id=user.id)
    return AdminProductDetailOut.model_validate(reader.admin_product(product_id))


@router.patch("/products/{product_id}/status", response_model=AdminProductDetailOut)
def admin_set_product_status(
    product_id: UUID,
    body: ProductStatusIn,
    user: CatalogManagerDep,
    commands: ProductCommandsDep,
    reader: CatalogReaderDep,
) -> AdminProductDetailOut:
    commands.set_status(product_id, body.status, actor_id=user.id)
    return AdminProductDetailOut.model_validate(reader.admin_product(product_id))


# --- Categories -------------------------------------------------------------------------------


@router.get("/categories", response_model=list[AdminCategoryOut])
def admin_list_categories(_: CatalogManagerDep, reader: CatalogReaderDep) -> list[AdminCategoryOut]:
    return [AdminCategoryOut.model_validate(c) for c in reader.categories(include_inactive=True)]


@router.post("/categories", response_model=CreatedOut, status_code=status.HTTP_201_CREATED)
def admin_create_category(
    body: CategoryIn, user: CatalogManagerDep, commands: CategoryCommandsDep
) -> CreatedOut:
    return CreatedOut(id=commands.create(body.to_input(), actor_id=user.id))


@router.put("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_update_category(
    category_id: UUID, body: CategoryIn, user: CatalogManagerDep, commands: CategoryCommandsDep
) -> None:
    commands.update(category_id, body.to_input(), actor_id=user.id)


@router.patch("/categories/{category_id}/status", status_code=status.HTTP_204_NO_CONTENT)
def admin_set_category_status(
    category_id: UUID, body: ActiveIn, user: CatalogManagerDep, commands: CategoryCommandsDep
) -> None:
    commands.set_active(category_id, body.is_active, actor_id=user.id)


@router.put("/categories/{category_id}/product-order", status_code=status.HTTP_204_NO_CONTENT)
def admin_order_category_products(
    category_id: UUID, body: OrderingIn, user: CatalogManagerDep, commands: CategoryCommandsDep
) -> None:
    """Custom order for this category only (used when custom_product_ordering is on)."""
    commands.set_product_order(category_id, body.product_ids, actor_id=user.id)


# --- Collections & homepage sections ----------------------------------------------------------


@router.post("/collections", response_model=CreatedOut, status_code=status.HTTP_201_CREATED)
def admin_create_collection(
    body: CollectionIn, user: ContentManagerDep, service: MerchandisingDep
) -> CreatedOut:
    return CreatedOut(id=service.create_collection(body.to_input(), actor_id=user.id))


@router.put("/collections/{collection_id}/products", status_code=status.HTTP_204_NO_CONTENT)
def admin_set_collection_products(
    collection_id: UUID, body: OrderingIn, user: ContentManagerDep, service: MerchandisingDep
) -> None:
    service.set_collection_products(collection_id, body.product_ids, actor_id=user.id)


@router.get("/collections/{collection_id}/products", response_model=list[ProductSummaryOut])
def admin_collection_products(
    collection_id: UUID, _: ContentManagerDep, service: MerchandisingDep
) -> list[ProductSummaryOut]:
    return [ProductSummaryOut.model_validate(p) for p in service.collection_products(collection_id)]


@router.post("/homepage-sections", response_model=CreatedOut, status_code=status.HTTP_201_CREATED)
def admin_create_section(
    body: HomepageSectionIn, user: ContentManagerDep, service: MerchandisingDep
) -> CreatedOut:
    return CreatedOut(id=service.create_section(body.to_input(), actor_id=user.id))


@router.put("/homepage-sections/{section_id}/products", status_code=status.HTTP_204_NO_CONTENT)
def admin_set_section_products(
    section_id: UUID, body: OrderingIn, user: ContentManagerDep, service: MerchandisingDep
) -> None:
    service.set_section_products(section_id, body.product_ids, actor_id=user.id)


@router.get("/homepage-sections/{section_id}/products", response_model=list[ProductSummaryOut])
def admin_section_products(
    section_id: UUID, _: ContentManagerDep, service: MerchandisingDep
) -> list[ProductSummaryOut]:
    return [ProductSummaryOut.model_validate(p) for p in service.section_products(section_id)]
