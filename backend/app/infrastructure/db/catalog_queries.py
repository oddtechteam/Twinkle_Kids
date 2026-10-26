"""SQLAlchemy implementation of the CatalogQueries read port.

Pricing in every view is derived through the domain PricePair / resolve_variant_price rules,
so listings, detail pages and (later) carts can never disagree.
"""

from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, Select, and_, exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.application.dto.catalog import (
    CatalogFacets,
    CategoryDetail,
    CategoryRef,
    CategorySummary,
    CollectionRef,
    CollectionSummary,
    ColourOption,
    FramedImage,
    ImageView,
    Page,
    PriceView,
    ProductDetail,
    ProductFilters,
    ProductSort,
    ProductSummary,
    ReviewSummary,
    ReviewView,
    SitemapEntry,
    SitemapView,
    VariantView,
)
from app.domain.enums import ProductStatus, PublishStatus, ReviewStatus
from app.domain.repositories.media import ObjectStorage
from app.domain.value_objects.pricing import PricePair, resolve_variant_price
from app.infrastructure.db.models.catalog import (
    CategoryModel,
    ProductCategoryModel,
    ProductMediaModel,
    ProductModel,
    ProductVariantModel,
)
from app.infrastructure.db.models.commerce import OrderItemModel, OrderModel
from app.infrastructure.db.models.content import (
    CollectionModel,
    CollectionProductModel,
    WebsitePageModel,
)
from app.infrastructure.db.models.identity import UserModel
from app.infrastructure.db.models.marketing import ReviewModel
from app.infrastructure.db.models.media import MediaAssetModel
from app.infrastructure.db.repositories.media import crops_from_json
from app.infrastructure.db.review_store import review_images

P = ProductModel
V = ProductVariantModel
PC = ProductCategoryModel


def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class SqlAlchemyCatalogQueries:
    def __init__(self, session: Session, storage: ObjectStorage) -> None:
        self._session = session
        self._storage = storage

    # --- helpers -------------------------------------------------------------------------

    def _image(
        self, asset: MediaAssetModel | None, alt: str | None = None, variant_id: UUID | None = None
    ) -> ImageView | None:
        if asset is None:
            return None
        crops: dict[str, FramedImage] = {}
        if asset.visibility == "public":
            url = self._storage.public_url(asset.bucket, asset.object_key)
            crops = {
                frame.value: FramedImage(
                    url=self._storage.public_url(asset.bucket, crop.object_key),
                    width=crop.width,
                    height=crop.height,
                )
                for frame, crop in crops_from_json(asset.crops).items()
            }
        else:
            url = self._storage.presigned_url(asset.bucket, asset.object_key, expires_in=900)
        return ImageView(
            media_asset_id=asset.id,
            url=url,
            alt_text=alt or asset.alt_text,
            width=asset.width,
            height=asset.height,
            variant_id=variant_id,
            crops=crops,
        )

    @staticmethod
    def _variant_in_stock(product: ProductModel, variant: ProductVariantModel) -> bool:
        if not variant.is_active:
            return False
        return not product.track_inventory or product.allow_backorder or variant.stock_quantity > 0

    @staticmethod
    def _variant_low_stock(product: ProductModel, variant: ProductVariantModel) -> bool:
        return (
            variant.is_active
            and product.track_inventory
            and not product.allow_backorder
            and 0 < variant.stock_quantity <= product.low_stock_threshold
        )

    @staticmethod
    def _primary_category(row: ProductModel) -> CategoryRef | None:
        links = sorted(
            (link for link in row.category_links if link.category.is_active),
            key=lambda link: (not link.is_primary, link.category.name),
        )
        if not links:
            return None
        category = links[0].category
        return CategoryRef(id=category.id, name=category.name, slug=category.slug)

    def _summary(self, row: ProductModel) -> ProductSummary:
        price = PricePair(row.selling_price, row.original_price)
        active = [v for v in row.variants if v.is_active]
        effective = [_effective(price, v).selling for v in active] or [price.selling]
        first_media = row.media_links[0] if row.media_links else None
        second_media = row.media_links[1] if len(row.media_links) > 1 else None
        return ProductSummary(
            id=row.id,
            name=row.name,
            slug=row.slug,
            price=PriceView.of(price),
            from_price=min(effective),
            price_varies=len(set(effective)) > 1,
            in_stock=any(self._variant_in_stock(row, v) for v in active),
            primary_image=(
                self._image(first_media.media_asset, first_media.alt_text, first_media.variant_id)
                if first_media
                else None
            ),
            status=ProductStatus(row.status),
            published_at=row.published_at,
            badges=list(row.badges or []),
            secondary_image=(
                self._image(
                    second_media.media_asset, second_media.alt_text, second_media.variant_id
                )
                if second_media
                else None
            ),
            category=self._primary_category(row),
        )

    def _load_products(self, ids: Sequence[UUID]) -> dict[UUID, ProductModel]:
        if not ids:
            return {}
        rows = self._session.scalars(
            select(ProductModel)
            .where(ProductModel.id.in_(ids))
            .options(
                selectinload(ProductModel.variants),
                selectinload(ProductModel.media_links).joinedload(ProductMediaModel.media_asset),
                selectinload(ProductModel.category_links).joinedload(ProductCategoryModel.category),
            )
        )
        return {row.id: row for row in rows}

    # --- products ------------------------------------------------------------------------

    def _filtered(self, filters: ProductFilters) -> tuple[Select[Any], Any, Any] | None:
        """Product-id query for the filters plus its (custom position, from-price) columns.

        Returns None when the requested category/collection scope does not exist.
        """
        effective_price = func.coalesce(V.selling_price, P.selling_price)
        from_price = (
            select(func.min(effective_price))
            .where(V.product_id == P.id, V.is_active.is_(True))
            .correlate(P)
            .scalar_subquery()
        )
        stmt: Select[Any] = select(P.id).where(P.status.in_([s.value for s in filters.statuses]))
        order_position: Any = None

        if filters.category_slug:
            category = self._session.scalars(
                select(CategoryModel).where(
                    CategoryModel.slug == filters.category_slug, CategoryModel.is_active.is_(True)
                )
            ).first()
            if category is None:
                return None
            tree = (
                select(CategoryModel.id)
                .where(CategoryModel.id == category.id)
                .cte("category_tree", recursive=True)
            )
            tree = tree.union_all(
                select(CategoryModel.id).where(
                    CategoryModel.parent_id == tree.c.id, CategoryModel.is_active.is_(True)
                )
            )
            stmt = stmt.where(
                exists().where(PC.product_id == P.id, PC.category_id.in_(select(tree.c.id)))
            )
            if category.custom_product_ordering:
                order_position = (
                    select(PC.position)
                    .where(PC.product_id == P.id, PC.category_id == category.id)
                    .correlate(P)
                    .scalar_subquery()
                )

        if filters.collection_slug:
            collection_id = self._session.scalar(
                select(CollectionModel.id).where(
                    CollectionModel.slug == filters.collection_slug,
                    CollectionModel.status == PublishStatus.PUBLISHED.value,
                )
            )
            if collection_id is None:
                return None
            position = (
                select(CollectionProductModel.position)
                .where(
                    CollectionProductModel.product_id == P.id,
                    CollectionProductModel.collection_id == collection_id,
                )
                .correlate(P)
                .scalar_subquery()
            )
            stmt = stmt.where(position.is_not(None))
            order_position = position if order_position is None else order_position

        if filters.search and filters.search.split():
            stmt = stmt.where(_search_clause(filters.search))
        if filters.min_price is not None:
            stmt = stmt.where(from_price >= filters.min_price)
        if filters.max_price is not None:
            stmt = stmt.where(from_price <= filters.max_price)
        if filters.sizes:
            stmt = stmt.where(
                exists().where(
                    V.product_id == P.id,
                    V.is_active.is_(True),
                    func.lower(V.size).in_([s.lower() for s in filters.sizes]),
                )
            )
        if filters.colours:
            stmt = stmt.where(
                exists().where(
                    V.product_id == P.id,
                    V.is_active.is_(True),
                    func.lower(V.colour).in_([c.lower() for c in filters.colours]),
                )
            )
        if filters.in_stock is not None:
            stocked = or_(
                P.track_inventory.is_(False),
                P.allow_backorder.is_(True),
                exists().where(V.product_id == P.id, V.is_active.is_(True), V.stock_quantity > 0),
            )
            stmt = stmt.where(stocked if filters.in_stock else ~stocked)
        return stmt, order_position, from_price

    def list_products(self, filters: ProductFilters) -> Page[ProductSummary]:
        built = self._filtered(filters)
        if built is None:
            return Page(items=[], total=0, page=filters.page, page_size=filters.page_size)
        stmt, order_position, from_price = built

        newest = (P.published_at.desc().nulls_last(), P.created_at.desc(), P.id)
        units_sold = (
            select(func.coalesce(func.sum(OrderItemModel.quantity), 0))
            .join(OrderModel, OrderModel.id == OrderItemModel.order_id)
            .where(
                OrderItemModel.product_id == P.id,
                OrderModel.status != "cancelled",
                OrderModel.placed_at >= func.now() - timedelta(days=90),
            )
            .correlate(P)
            .scalar_subquery()
        )
        match filters.sort:
            case ProductSort.BESTSELLING:
                stmt = stmt.order_by(units_sold.desc(), *newest)
            case ProductSort.FEATURED if order_position is not None:
                stmt = stmt.order_by(order_position.asc().nulls_last(), *newest)
            case ProductSort.PRICE_ASC:
                stmt = stmt.order_by(from_price.asc(), P.id)
            case ProductSort.PRICE_DESC:
                stmt = stmt.order_by(from_price.desc(), P.id)
            case ProductSort.NAME_ASC:
                stmt = stmt.order_by(P.name.asc(), P.id)
            case _:
                stmt = stmt.order_by(*newest)

        total = self._session.scalar(
            select(func.count()).select_from(stmt.order_by(None).subquery())
        )
        page_ids = list(
            self._session.scalars(
                stmt.limit(filters.page_size).offset((filters.page - 1) * filters.page_size)
            )
        )
        rows = self._load_products(page_ids)
        return Page(
            items=[self._summary(rows[pid]) for pid in page_ids if pid in rows],
            total=total or 0,
            page=filters.page,
            page_size=filters.page_size,
        )

    def facets(self, filters: ProductFilters) -> CatalogFacets:
        scope = replace(
            filters, sizes=(), colours=(), min_price=None, max_price=None, in_stock=None
        )
        built = self._filtered(scope)
        if built is None:
            return CatalogFacets(sizes=[], colours=[], min_price=None, max_price=None, total=0)
        stmt, _position, from_price = built
        scoped_ids = select(stmt.subquery().c.id)

        size_rows = self._session.execute(
            select(V.size, func.min(V.position))
            .where(
                V.product_id.in_(scoped_ids),
                V.is_active.is_(True),
                V.size.is_not(None),
                V.size != "",
            )
            .group_by(V.size)
        ).all()
        # Variant position is the admin's natural size order (2-3Y before 10-11Y).
        sizes = _distinct([row[0] for row in sorted(size_rows, key=lambda r: (r[1] or 0, r[0]))])

        colour_rows = self._session.execute(
            select(V.colour, func.max(V.colour_hex))
            .where(
                V.product_id.in_(scoped_ids),
                V.is_active.is_(True),
                V.colour.is_not(None),
                V.colour != "",
            )
            .group_by(V.colour)
            .order_by(V.colour)
        ).all()
        seen: set[str] = set()
        colours: list[ColourOption] = []
        for name, hex_value in colour_rows:
            if name and name.casefold() not in seen:
                seen.add(name.casefold())
                colours.append(ColourOption(name=name, hex=hex_value))

        priced = select(P.id, from_price.label("from_price")).where(P.id.in_(scoped_ids)).subquery()
        low, high, count = self._session.execute(
            select(
                func.min(priced.c.from_price), func.max(priced.c.from_price), func.count()
            ).select_from(priced)
        ).one()
        return CatalogFacets(
            sizes=sizes,
            colours=colours,
            min_price=low,
            max_price=high,
            total=int(count or 0),
        )

    def ordered_products(
        self, product_ids: Sequence[UUID], *, include_inactive: bool = False
    ) -> Sequence[ProductSummary]:
        rows = self._load_products(list(product_ids))
        return [
            self._summary(rows[pid])
            for pid in product_ids
            if pid in rows and (include_inactive or rows[pid].status == ProductStatus.ACTIVE.value)
        ]

    # --- collections & media -------------------------------------------------------------

    def _collection_summary(self, row: CollectionModel) -> CollectionSummary:
        image = None
        if row.image_media_id:
            image = self.images([row.image_media_id]).get(row.image_media_id)
        return CollectionSummary(
            id=row.id,
            name=row.name,
            slug=row.slug,
            description=row.description,
            image=image,
            status=row.status,
            display_order=row.display_order,
            seo_title=row.seo_title,
            seo_description=row.seo_description,
        )

    def list_collections(
        self, *, ids: Sequence[UUID] | None = None, published_only: bool = True
    ) -> Sequence[CollectionSummary]:
        stmt = select(CollectionModel).order_by(CollectionModel.display_order, CollectionModel.name)
        if ids is not None:
            if not ids:
                return []
            stmt = stmt.where(CollectionModel.id.in_(list(ids)))
        if published_only:
            stmt = stmt.where(CollectionModel.status == PublishStatus.PUBLISHED.value)
        return [self._collection_summary(row) for row in self._session.scalars(stmt)]

    def get_collection(self, slug: str) -> CollectionSummary | None:
        row = self._session.scalars(
            select(CollectionModel).where(
                CollectionModel.slug == slug,
                CollectionModel.status == PublishStatus.PUBLISHED.value,
            )
        ).first()
        return self._collection_summary(row) if row else None

    def images(self, media_ids: Sequence[UUID]) -> dict[UUID, ImageView]:
        wanted = list({m for m in media_ids if m})
        if not wanted:
            return {}
        rows = self._session.scalars(select(MediaAssetModel).where(MediaAssetModel.id.in_(wanted)))
        return {row.id: image for row in rows if (image := self._image(row)) is not None}

    def get_product(
        self, *, slug: str | None = None, product_id: UUID | None = None, admin_view: bool = False
    ) -> ProductDetail | None:
        stmt = select(ProductModel).options(
            selectinload(ProductModel.variants),
            selectinload(ProductModel.media_links).joinedload(ProductMediaModel.media_asset),
            selectinload(ProductModel.category_links).joinedload(ProductCategoryModel.category),
            selectinload(ProductModel.size_chart),
        )
        if slug is not None:
            stmt = stmt.where(ProductModel.slug == slug)
        elif product_id is not None:
            stmt = stmt.where(ProductModel.id == product_id)
        else:  # pragma: no cover - programming error
            raise ValueError("slug or product_id is required")
        if not admin_view:
            stmt = stmt.where(ProductModel.status == ProductStatus.ACTIVE.value)
        row = self._session.scalars(stmt).first()
        if row is None:
            return None

        price = PricePair(row.selling_price, row.original_price)
        variants = [v for v in row.variants if admin_view or v.is_active]
        variant_views = [
            VariantView(
                id=v.id,
                sku=v.sku,
                size=v.size,
                colour=v.colour,
                colour_hex=v.colour_hex,
                price=PriceView.of(_effective(price, v)),
                selling_price_override=v.selling_price if admin_view else None,
                original_price_override=v.original_price if admin_view else None,
                in_stock=self._variant_in_stock(row, v),
                stock_quantity=v.stock_quantity if admin_view else None,
                is_active=v.is_active,
                low_stock=self._variant_low_stock(row, v),
            )
            for v in variants
        ]
        categories = [
            CategoryRef(id=link.category.id, name=link.category.name, slug=link.category.slug)
            for link in sorted(
                row.category_links, key=lambda link: (not link.is_primary, link.category.name)
            )
            if admin_view or link.category.is_active
        ]
        images = [
            image
            for m in row.media_links
            if (image := self._image(m.media_asset, m.alt_text, m.variant_id)) is not None
        ]
        return ProductDetail(
            id=row.id,
            name=row.name,
            slug=row.slug,
            sku=row.sku,
            status=ProductStatus(row.status),
            short_description=row.short_description,
            description=row.description,
            rich_content=row.rich_content,
            price=PriceView.of(price),
            in_stock=any(self._variant_in_stock(row, v) for v in row.variants),
            track_inventory=row.track_inventory,
            allow_backorder=row.allow_backorder,
            low_stock_threshold=row.low_stock_threshold,
            sizes=_distinct([v.size for v in variants if v.is_active]),
            colours=_distinct([v.colour for v in variants if v.is_active]),
            variants=variant_views,
            images=images,
            categories=categories,
            primary_category_id=next(
                (link.category_id for link in row.category_links if link.is_primary), None
            ),
            size_chart=(
                {"name": row.size_chart.name, **(row.size_chart.chart or {})}
                if row.size_chart
                else None
            ),
            seo_title=row.seo_title,
            seo_description=row.seo_description,
            seo_metadata=dict(row.seo_metadata or {}),
            published_at=row.published_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
            badges=list(row.badges or []),
            is_featured=row.is_featured,
            related_product_ids=(
                [UUID(str(v)) for v in (row.related_product_ids or [])] if admin_view else []
            ),
            size_chart_id=row.size_chart_id,
            collection_ids=(
                list(
                    self._session.scalars(
                        select(CollectionProductModel.collection_id).where(
                            CollectionProductModel.product_id == row.id
                        )
                    )
                )
                if admin_view
                else []
            ),
            collections=[] if admin_view else self._product_collections(row.id),
        )

    def _product_collections(self, product_id: UUID) -> list[CollectionRef]:
        rows = self._session.execute(
            select(CollectionModel.id, CollectionModel.name, CollectionModel.slug)
            .join(
                CollectionProductModel, CollectionProductModel.collection_id == CollectionModel.id
            )
            .where(
                CollectionProductModel.product_id == product_id,
                CollectionModel.status == PublishStatus.PUBLISHED.value,
            )
            .order_by(CollectionModel.display_order, CollectionModel.name)
        ).all()
        return [CollectionRef(id=r[0], name=r[1], slug=r[2]) for r in rows]

    # --- reviews & sitemap ---------------------------------------------------------------

    # --- recommendations ------------------------------------------------------------------

    def bestseller_ids(
        self, *, limit: int, days: int = 90, category_slug: str | None = None
    ) -> list[UUID]:
        since = datetime.now(UTC) - timedelta(days=days)
        stmt = (
            select(OrderItemModel.product_id, func.sum(OrderItemModel.quantity).label("units"))
            .join(OrderModel, OrderModel.id == OrderItemModel.order_id)
            .join(P, P.id == OrderItemModel.product_id)
            .where(
                OrderModel.status != "cancelled",
                OrderModel.placed_at >= since,
                P.status == ProductStatus.ACTIVE.value,
            )
            .group_by(OrderItemModel.product_id)
            .order_by(func.sum(OrderItemModel.quantity).desc(), OrderItemModel.product_id)
            .limit(limit)
        )
        if category_slug:
            stmt = stmt.where(
                exists().where(
                    PC.product_id == OrderItemModel.product_id,
                    PC.category_id == CategoryModel.id,
                    CategoryModel.slug == category_slug,
                )
            )
        return [row[0] for row in self._session.execute(stmt) if row[0] is not None]

    def featured_ids(self, *, limit: int) -> list[UUID]:
        return list(
            self._session.scalars(
                select(P.id)
                .where(P.is_featured.is_(True), P.status == ProductStatus.ACTIVE.value)
                .order_by(P.published_at.desc().nulls_last(), P.id)
                .limit(limit)
            )
        )

    def related_ids(self, product_id: UUID) -> list[UUID]:
        raw = self._session.scalar(select(P.related_product_ids).where(P.id == product_id)) or []
        ids: list[UUID] = []
        for value in raw:
            try:
                ids.append(UUID(str(value)))
            except ValueError:
                continue
        return ids

    def product_reviews(self, product_id: UUID, *, limit: int = 20) -> ReviewSummary:
        approved = and_(
            ReviewModel.product_id == product_id,
            ReviewModel.status == ReviewStatus.APPROVED.value,
        )
        average, count = self._session.execute(
            select(func.avg(ReviewModel.rating), func.count()).where(approved)
        ).one()
        rows = self._session.execute(
            select(ReviewModel, UserModel.full_name)
            .outerjoin(UserModel, UserModel.id == ReviewModel.user_id)
            .where(approved)
            .order_by(ReviewModel.created_at.desc())
            .limit(limit)
        ).all()
        photos = review_images(self._session, self._storage, [r.id for r, _ in rows])
        return ReviewSummary(
            average=(
                Decimal(str(average)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
                if average is not None
                else None
            ),
            count=int(count or 0),
            items=[
                ReviewView(
                    rating=review.rating,
                    title=review.title,
                    body=review.body,
                    author=review.author_name or (full_name or "").strip().split(" ")[0] or None,
                    created_at=review.created_at,
                    verified_purchase=review.is_verified_purchase,
                    images=photos.get(review.id, []),
                )
                for review, full_name in rows
            ],
        )

    def sitemap(self) -> SitemapView:
        def entries(stmt: Select[str, datetime]) -> list[SitemapEntry]:
            return [SitemapEntry(slug=r[0], updated_at=r[1]) for r in self._session.execute(stmt)]

        return SitemapView(
            products=entries(
                select(P.slug, P.updated_at)
                .where(P.status == ProductStatus.ACTIVE.value)
                .order_by(P.published_at.desc().nulls_last())
            ),
            categories=entries(
                select(CategoryModel.slug, CategoryModel.updated_at)
                .where(CategoryModel.is_active.is_(True))
                .order_by(CategoryModel.display_order)
            ),
            collections=entries(
                select(CollectionModel.slug, CollectionModel.updated_at)
                .where(CollectionModel.status == PublishStatus.PUBLISHED.value)
                .order_by(CollectionModel.display_order)
            ),
            pages=entries(
                select(WebsitePageModel.slug, WebsitePageModel.updated_at).where(
                    WebsitePageModel.status == PublishStatus.PUBLISHED.value
                )
            ),
        )

    # --- categories ----------------------------------------------------------------------

    def _category_summary(self, row: CategoryModel) -> CategorySummary:
        return CategorySummary(
            id=row.id,
            name=row.name,
            slug=row.slug,
            description=row.description,
            parent_id=row.parent_id,
            image=self._image(row.image),
            display_order=row.display_order,
            is_active=row.is_active,
            custom_product_ordering=row.custom_product_ordering,
            seo_title=row.seo_title,
            seo_description=row.seo_description,
        )

    def list_categories(self, *, include_inactive: bool = False) -> Sequence[CategorySummary]:
        stmt = select(CategoryModel).order_by(CategoryModel.display_order, CategoryModel.name)
        if not include_inactive:
            stmt = stmt.where(CategoryModel.is_active.is_(True))
        return [self._category_summary(row) for row in self._session.scalars(stmt)]

    def get_category(self, slug: str) -> CategoryDetail | None:
        row = self._session.scalars(
            select(CategoryModel).where(
                CategoryModel.slug == slug, CategoryModel.is_active.is_(True)
            )
        ).first()
        if row is None:
            return None
        children = self._session.scalars(
            select(CategoryModel)
            .where(CategoryModel.parent_id == row.id, CategoryModel.is_active.is_(True))
            .order_by(CategoryModel.display_order, CategoryModel.name)
        )
        breadcrumbs: list[CategoryRef] = []
        parent_id = row.parent_id
        seen: set[UUID] = set()
        while parent_id is not None and parent_id not in seen and len(seen) < 20:
            seen.add(parent_id)
            parent = self._session.get(CategoryModel, parent_id)
            if parent is None:
                break
            breadcrumbs.insert(0, CategoryRef(id=parent.id, name=parent.name, slug=parent.slug))
            parent_id = parent.parent_id
        return CategoryDetail(
            category=self._category_summary(row),
            children=[self._category_summary(c) for c in children],
            breadcrumbs=breadcrumbs,
            seo_metadata=dict(row.seo_metadata or {}),
        )


def _effective(price: PricePair, variant: ProductVariantModel) -> PricePair:
    return resolve_variant_price(
        price, selling_override=variant.selling_price, original_override=variant.original_price
    )


def _distinct(values: Sequence[str | None]) -> list[str]:
    seen: dict[str, None] = {}
    for value in values:
        if value and value not in seen:
            seen[value] = None
    return list(seen)


def _search_clause(raw: str) -> ColumnElement[bool]:
    """Every word must match the name, SKU, short description or an active category name."""
    clauses: list[ColumnElement[bool]] = []
    for word in raw.split()[:6]:
        term = f"%{_escape_like(word)}%"
        in_category = exists().where(
            PC.product_id == P.id,
            PC.category_id == CategoryModel.id,
            CategoryModel.is_active.is_(True),
            CategoryModel.name.ilike(term, escape="\\"),
        )
        clauses.append(
            or_(
                P.name.ilike(term, escape="\\"),
                P.sku.ilike(term, escape="\\"),
                P.short_description.ilike(term, escape="\\"),
                in_category,
            )
        )
    return and_(*clauses)
