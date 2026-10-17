from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import delete, func, insert, select, union_all
from sqlalchemy.orm import Session

from app.domain.entities.catalog import Category, Product, ProductMediaLink, ProductVariant
from app.domain.entities.content import Collection
from app.domain.enums import (
    ProductStatus,
    PublishStatus,
)
from app.domain.value_objects.pricing import PricePair
from app.infrastructure.db.models.catalog import (
    CategoryModel,
    ProductCategoryModel,
    ProductMediaModel,
    ProductModel,
    ProductVariantModel,
)
from app.infrastructure.db.models.content import (
    CollectionModel,
    CollectionProductModel,
)

MAX_CATEGORY_DEPTH = 20


# --- Products --------------------------------------------------------------------------------


def _product_to_entity(row: ProductModel) -> Product:
    links = sorted(row.category_links, key=lambda link: str(link.category_id))
    return Product(
        id=row.id,
        name=row.name,
        slug=row.slug,
        sku=row.sku,
        price=PricePair(row.selling_price, row.original_price),
        status=ProductStatus(row.status),
        short_description=row.short_description,
        description=row.description,
        rich_content=row.rich_content,
        track_inventory=row.track_inventory,
        allow_backorder=row.allow_backorder,
        low_stock_threshold=row.low_stock_threshold,
        size_chart_id=row.size_chart_id,
        seo_title=row.seo_title,
        seo_description=row.seo_description,
        seo_metadata=dict(row.seo_metadata or {}),
        category_ids=[link.category_id for link in links],
        primary_category_id=next((link.category_id for link in links if link.is_primary), None),
        variants=[
            ProductVariant(
                id=v.id,
                sku=v.sku,
                size=v.size,
                colour=v.colour,
                colour_hex=v.colour_hex,
                selling_price_override=v.selling_price,
                original_price_override=v.original_price,
                stock_quantity=v.stock_quantity,
                position=v.position,
                is_active=v.is_active,
            )
            for v in row.variants
        ],
        media=[
            ProductMediaLink(
                media_asset_id=m.media_asset_id, alt_text=m.alt_text, variant_id=m.variant_id
            )
            for m in row.media_links
        ],
        badges=list(row.badges or []),
        published_at=row.published_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlAlchemyProductRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, product_id: UUID) -> Product | None:
        row = self._session.get(ProductModel, product_id)
        return _product_to_entity(row) if row else None

    def add(self, product: Product) -> None:
        row = ProductModel(id=product.id)
        self._session.add(row)
        self._apply(row, product)

    def save(self, product: Product) -> None:
        row = self._session.get(ProductModel, product.id)
        if row is None:
            raise LookupError(f"Product {product.id} does not exist.")
        self._apply(row, product)

    def slug_taken(self, slug: str, *, exclude_id: UUID | None = None) -> bool:
        stmt = select(ProductModel.id).where(ProductModel.slug == slug)
        if exclude_id is not None:
            stmt = stmt.where(ProductModel.id != exclude_id)
        return self._session.scalars(stmt.limit(1)).first() is not None

    def skus_taken(
        self, skus: Iterable[str], *, exclude_product_id: UUID | None = None
    ) -> set[str]:
        wanted = set(skus)
        if not wanted:
            return set()
        product_skus = select(ProductModel.sku.label("sku")).where(ProductModel.sku.in_(wanted))
        variant_skus = select(ProductVariantModel.sku.label("sku")).where(
            ProductVariantModel.sku.in_(wanted)
        )
        if exclude_product_id is not None:
            product_skus = product_skus.where(ProductModel.id != exclude_product_id)
            variant_skus = variant_skus.where(ProductVariantModel.product_id != exclude_product_id)
        return set(self._session.scalars(union_all(product_skus, variant_skus)))

    def existing_ids(self, ids: Iterable[UUID]) -> set[UUID]:
        wanted = set(ids)
        if not wanted:
            return set()
        return set(
            self._session.scalars(select(ProductModel.id).where(ProductModel.id.in_(wanted)))
        )

    # -- aggregate persistence ---------------------------------------------------------------

    def _apply(self, row: ProductModel, product: Product) -> None:
        row.name = product.name
        row.slug = product.slug
        row.sku = product.sku
        row.status = product.status.value
        row.short_description = product.short_description
        row.description = product.description
        row.rich_content = product.rich_content
        row.selling_price = product.price.selling
        row.original_price = product.price.original
        row.track_inventory = product.track_inventory
        row.allow_backorder = product.allow_backorder
        row.low_stock_threshold = product.low_stock_threshold
        row.size_chart_id = product.size_chart_id
        row.seo_title = product.seo_title
        row.seo_description = product.seo_description
        row.seo_metadata = dict(product.seo_metadata)
        row.badges = list(product.badges)
        row.published_at = product.published_at

        self._sync_variants(row, product.variants)
        self._session.flush()  # variants must exist before media rows reference them
        self._sync_categories(row, product)
        self._sync_media(row, product.media)
        self._session.flush()

    def _sync_variants(self, row: ProductModel, variants: list[ProductVariant]) -> None:
        existing = {v.id: v for v in row.variants}
        kept: list[ProductVariantModel] = []
        for position, variant in enumerate(variants):
            model = existing.get(variant.id) or ProductVariantModel(id=variant.id)
            model.sku = variant.sku
            model.size = variant.size
            model.colour = variant.colour
            model.colour_hex = variant.colour_hex
            model.selling_price = variant.selling_price_override
            model.original_price = variant.original_price_override
            model.stock_quantity = variant.stock_quantity
            model.position = position
            model.is_active = variant.is_active
            kept.append(model)
        row.variants = kept  # delete-orphan removes dropped variants

    def _sync_categories(self, row: ProductModel, product: Product) -> None:
        existing = {link.category_id: link for link in row.category_links}
        wanted = set(product.category_ids)
        new_ids = wanted - existing.keys()
        next_position = self._next_positions(new_ids)
        links: list[ProductCategoryModel] = []
        for category_id in product.category_ids:
            link = existing.get(category_id)
            if link is None:  # new membership: append to the end of that category's order
                link = ProductCategoryModel(
                    category_id=category_id, position=next_position.get(category_id, 0)
                )
            link.is_primary = category_id == product.primary_category_id
            links.append(link)
        row.category_links = links

    def _next_positions(self, category_ids: set[UUID]) -> dict[UUID, int]:
        if not category_ids:
            return {}
        stmt = (
            select(ProductCategoryModel.category_id, func.max(ProductCategoryModel.position))
            .where(ProductCategoryModel.category_id.in_(category_ids))
            .group_by(ProductCategoryModel.category_id)
        )
        return {cid: (pos or 0) + 1 for cid, pos in self._session.execute(stmt)}

    def _sync_media(self, row: ProductModel, media: list[ProductMediaLink]) -> None:
        existing = {m.media_asset_id: m for m in row.media_links}
        links: list[ProductMediaModel] = []
        for position, item in enumerate(media):
            model = existing.get(item.media_asset_id) or ProductMediaModel(
                media_asset_id=item.media_asset_id
            )
            model.position = position
            model.alt_text = item.alt_text
            model.variant_id = item.variant_id
            links.append(model)
        row.media_links = links


# --- Categories ------------------------------------------------------------------------------


def _category_to_entity(row: CategoryModel) -> Category:
    return Category(
        id=row.id,
        name=row.name,
        slug=row.slug,
        description=row.description,
        parent_id=row.parent_id,
        image_media_id=row.image_media_id,
        is_active=row.is_active,
        display_order=row.display_order,
        custom_product_ordering=row.custom_product_ordering,
        seo_title=row.seo_title,
        seo_description=row.seo_description,
        seo_metadata=dict(row.seo_metadata or {}),
    )


class SqlAlchemyCategoryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, category_id: UUID) -> Category | None:
        row = self._session.get(CategoryModel, category_id)
        return _category_to_entity(row) if row else None

    def add(self, category: Category) -> None:
        row = CategoryModel(id=category.id)
        self._apply(row, category)
        self._session.add(row)
        self._session.flush()

    def save(self, category: Category) -> None:
        row = self._session.get(CategoryModel, category.id)
        if row is None:
            raise LookupError(f"Category {category.id} does not exist.")
        self._apply(row, category)
        self._session.flush()

    @staticmethod
    def _apply(row: CategoryModel, category: Category) -> None:
        row.name = category.name
        row.slug = category.slug
        row.description = category.description
        row.parent_id = category.parent_id
        row.image_media_id = category.image_media_id
        row.is_active = category.is_active
        row.display_order = category.display_order
        row.custom_product_ordering = category.custom_product_ordering
        row.seo_title = category.seo_title
        row.seo_description = category.seo_description
        row.seo_metadata = dict(category.seo_metadata)

    def slug_taken(self, slug: str, *, exclude_id: UUID | None = None) -> bool:
        stmt = select(CategoryModel.id).where(CategoryModel.slug == slug)
        if exclude_id is not None:
            stmt = stmt.where(CategoryModel.id != exclude_id)
        return self._session.scalars(stmt.limit(1)).first() is not None

    def existing_ids(self, ids: Iterable[UUID]) -> set[UUID]:
        wanted = set(ids)
        if not wanted:
            return set()
        return set(
            self._session.scalars(select(CategoryModel.id).where(CategoryModel.id.in_(wanted)))
        )

    def ancestor_ids(self, category_id: UUID) -> list[UUID]:
        ancestors: list[UUID] = []
        current: UUID | None = category_id
        for _ in range(MAX_CATEGORY_DEPTH):
            parent = self._session.scalar(
                select(CategoryModel.parent_id).where(CategoryModel.id == current)
            )
            if parent is None or parent in ancestors:
                break
            ancestors.append(parent)
            current = parent
        return ancestors

    def product_ids(self, category_id: UUID) -> list[UUID]:
        stmt = (
            select(ProductCategoryModel.product_id)
            .where(ProductCategoryModel.category_id == category_id)
            .order_by(ProductCategoryModel.position, ProductCategoryModel.product_id)
        )
        return list(self._session.scalars(stmt))

    def set_product_order(self, category_id: UUID, product_ids: list[UUID]) -> None:
        links = {
            link.product_id: link
            for link in self._session.scalars(
                select(ProductCategoryModel).where(ProductCategoryModel.category_id == category_id)
            )
        }
        ordered = [pid for pid in product_ids if pid in links]
        rest = [pid for pid in self.product_ids(category_id) if pid not in set(ordered)]
        for position, pid in enumerate(ordered + rest):
            links[pid].position = position
        self._session.flush()


# --- Collections & homepage sections ---------------------------------------------------------


class SqlAlchemyCollectionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, collection_id: UUID) -> Collection | None:
        row = self._session.get(CollectionModel, collection_id)
        if row is None:
            return None
        return Collection(
            id=row.id,
            name=row.name,
            slug=row.slug,
            description=row.description,
            image_media_id=row.image_media_id,
            status=PublishStatus(row.status),
            display_order=row.display_order,
            seo_title=row.seo_title,
            seo_description=row.seo_description,
        )

    def add(self, collection: Collection) -> None:
        self._session.add(
            CollectionModel(
                id=collection.id,
                name=collection.name,
                slug=collection.slug,
                description=collection.description,
                image_media_id=collection.image_media_id,
                status=collection.status.value,
                display_order=collection.display_order,
                seo_title=collection.seo_title,
                seo_description=collection.seo_description,
            )
        )
        self._session.flush()

    def slug_taken(self, slug: str) -> bool:
        stmt = select(CollectionModel.id).where(CollectionModel.slug == slug)
        return self._session.scalars(stmt.limit(1)).first() is not None

    def set_products(self, collection_id: UUID, product_ids: list[UUID]) -> None:
        self._session.execute(
            delete(CollectionProductModel).where(
                CollectionProductModel.collection_id == collection_id
            )
        )
        if product_ids:
            self._session.execute(
                insert(CollectionProductModel),
                [
                    {"collection_id": collection_id, "product_id": pid, "position": i}
                    for i, pid in enumerate(product_ids)
                ],
            )

    def product_ids(self, collection_id: UUID) -> list[UUID]:
        stmt = (
            select(CollectionProductModel.product_id)
            .where(CollectionProductModel.collection_id == collection_id)
            .order_by(CollectionProductModel.position)
        )
        return list(self._session.scalars(stmt))
