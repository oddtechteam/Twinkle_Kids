"""SQLAlchemy repositories for CMS content: settings, homepage builder, collections admin,
navigation, website pages, shipping rules and size charts."""

from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.orm import Session

from app.domain.entities.content import Collection, HomepageSection
from app.domain.entities.site import (
    NavigationItem,
    ShippingRule,
    SizeChart,
    StoreSettings,
    WebsitePage,
)
from app.domain.enums import (
    HomepageSectionType,
    NavigationLinkType,
    NavigationMenu,
    PublishStatus,
    SelectionMode,
)
from app.infrastructure.db.models.catalog import ProductModel, SizeChartModel
from app.infrastructure.db.models.content import (
    CollectionModel,
    CollectionProductModel,
    HomepagePublicationModel,
    HomepageSectionModel,
    HomepageSectionProductModel,
    NavigationItemModel,
    StoreSettingsModel,
    WebsitePageModel,
)
from app.infrastructure.db.models.marketing import ShippingRuleModel

# --- Store settings ---------------------------------------------------------------------------

_SETTINGS_FIELDS = (
    "store_name",
    "tagline",
    "currency_code",
    "logo_media_id",
    "favicon_media_id",
    "theme",
    "announcement",
    "contact_email",
    "contact_phone",
    "business_address",
    "business_hours",
    "social_links",
    "guest_checkout_enabled",
    "whatsapp_ordering_enabled",
    "whatsapp_number",
    "whatsapp_message_template",
    "payment_options",
    "default_product_sort",
    "default_low_stock_threshold",
    "seo_defaults",
)


class SqlAlchemySettingsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _row(self) -> StoreSettingsModel:
        row = self._session.get(StoreSettingsModel, 1)
        if row is None:  # seeded by migration 0003; recreate defensively
            row = StoreSettingsModel(id=1, store_name="Twinkle Kids")
            self._session.add(row)
            self._session.flush()
        return row

    def get(self) -> StoreSettings:
        row = self._row()
        values = {name: getattr(row, name) for name in _SETTINGS_FIELDS}
        for json_field in ("theme", "announcement", "social_links", "seo_defaults"):
            values[json_field] = dict(values[json_field] or {})
        values["payment_options"] = list(values["payment_options"] or [])
        return StoreSettings(**values, updated_at=row.updated_at)

    def save(self, settings: StoreSettings) -> None:
        row = self._row()
        for name in _SETTINGS_FIELDS:
            setattr(row, name, getattr(settings, name))
        self._session.flush()


# --- Homepage builder -------------------------------------------------------------------------


def _section(row: HomepageSectionModel) -> HomepageSection:
    return HomepageSection(
        id=row.id,
        section_type=HomepageSectionType(row.section_type),
        title=row.title,
        subtitle=row.subtitle,
        settings=dict(row.settings or {}),
        is_visible=row.is_visible,
        status=PublishStatus(row.status),
        position=row.position,
        desktop_media_id=row.desktop_media_id,
        mobile_media_id=row.mobile_media_id,
        selection_mode=SelectionMode(row.selection_mode),
        source_category_id=row.source_category_id,
        source_collection_id=row.source_collection_id,
        product_limit=row.product_limit,
    )


def _apply_section(row: HomepageSectionModel, section: HomepageSection) -> None:
    row.section_type = section.section_type.value
    row.title = section.title
    row.subtitle = section.subtitle
    row.settings = dict(section.settings)
    row.is_visible = section.is_visible
    row.status = section.status.value
    row.position = section.position
    row.desktop_media_id = section.desktop_media_id
    row.mobile_media_id = section.mobile_media_id
    row.selection_mode = section.selection_mode.value
    row.source_category_id = section.source_category_id
    row.source_collection_id = section.source_collection_id
    row.product_limit = section.product_limit


class SqlAlchemyHomepageBuilderRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_sections(self) -> Sequence[HomepageSection]:
        rows = self._session.scalars(
            select(HomepageSectionModel).order_by(
                HomepageSectionModel.position, HomepageSectionModel.created_at
            )
        )
        return [_section(r) for r in rows]

    def get(self, section_id: UUID) -> HomepageSection | None:
        row = self._session.get(HomepageSectionModel, section_id)
        return _section(row) if row else None

    def add(self, section: HomepageSection) -> None:
        row = HomepageSectionModel(id=section.id)
        _apply_section(row, section)
        self._session.add(row)
        self._session.flush()

    def save(self, section: HomepageSection) -> None:
        row = self._session.get(HomepageSectionModel, section.id)
        if row is None:
            raise LookupError(f"Section {section.id} does not exist.")
        _apply_section(row, section)
        self._session.flush()

    def delete(self, section_id: UUID) -> None:
        self._session.execute(
            delete(HomepageSectionModel).where(HomepageSectionModel.id == section_id)
        )

    def next_position(self) -> int:
        current = self._session.scalar(select(func.max(HomepageSectionModel.position)))
        return (current or 0) + 1

    def reorder(self, section_ids: list[UUID]) -> None:
        for position, section_id in enumerate(section_ids):
            self._session.execute(
                update(HomepageSectionModel)
                .where(HomepageSectionModel.id == section_id)
                .values(position=position)
            )

    def product_ids(self, section_id: UUID) -> list[UUID]:
        stmt = (
            select(HomepageSectionProductModel.product_id)
            .where(HomepageSectionProductModel.section_id == section_id)
            .order_by(HomepageSectionProductModel.position)
        )
        return list(self._session.scalars(stmt))

    def set_products(self, section_id: UUID, product_ids: list[UUID]) -> None:
        self._session.execute(
            delete(HomepageSectionProductModel).where(
                HomepageSectionProductModel.section_id == section_id
            )
        )
        if product_ids:
            self._session.execute(
                insert(HomepageSectionProductModel),
                [
                    {"section_id": section_id, "product_id": pid, "position": i}
                    for i, pid in enumerate(product_ids)
                ],
            )
        # Touch the section so "unpublished changes" reflects product edits too.
        self._session.execute(
            update(HomepageSectionModel)
            .where(HomepageSectionModel.id == section_id)
            .values(updated_at=func.now())
        )

    def last_modified(self) -> datetime | None:
        return self._session.scalar(select(func.max(HomepageSectionModel.updated_at)))

    def add_publication(
        self, snapshot: dict[str, Any], *, published_by: UUID | None, note: str | None
    ) -> datetime:
        row = HomepagePublicationModel(snapshot=snapshot, published_by=published_by, note=note)
        self._session.add(row)
        self._session.flush()
        return row.published_at

    def latest_publication(self) -> tuple[dict[str, Any], datetime] | None:
        row = self._session.scalars(
            select(HomepagePublicationModel)
            .order_by(HomepagePublicationModel.published_at.desc())
            .limit(1)
        ).first()
        return (dict(row.snapshot), row.published_at) if row else None


# --- Collections (admin) ----------------------------------------------------------------------


def _collection(row: CollectionModel) -> Collection:
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


class SqlAlchemyCollectionAdminRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self) -> Sequence[tuple[Collection, int]]:
        counts = (
            select(CollectionProductModel.collection_id, func.count().label("n"))
            .group_by(CollectionProductModel.collection_id)
            .subquery()
        )
        rows = self._session.execute(
            select(CollectionModel, func.coalesce(counts.c.n, 0))
            .outerjoin(counts, counts.c.collection_id == CollectionModel.id)
            .order_by(CollectionModel.display_order, CollectionModel.name)
        )
        return [(_collection(row), int(n)) for row, n in rows]

    def get(self, collection_id: UUID) -> Collection | None:
        row = self._session.get(CollectionModel, collection_id)
        return _collection(row) if row else None

    def save(self, collection: Collection) -> None:
        row = self._session.get(CollectionModel, collection.id)
        if row is None:
            raise LookupError(f"Collection {collection.id} does not exist.")
        row.name = collection.name
        row.slug = collection.slug
        row.description = collection.description
        row.image_media_id = collection.image_media_id
        row.status = collection.status.value
        row.display_order = collection.display_order
        row.seo_title = collection.seo_title
        row.seo_description = collection.seo_description
        self._session.flush()

    def slug_taken(self, slug: str, *, exclude_id: UUID | None = None) -> bool:
        stmt = select(CollectionModel.id).where(CollectionModel.slug == slug)
        if exclude_id is not None:
            stmt = stmt.where(CollectionModel.id != exclude_id)
        return self._session.scalars(stmt.limit(1)).first() is not None

    def existing_ids(self, ids: Sequence[UUID]) -> set[UUID]:
        wanted = set(ids)
        if not wanted:
            return set()
        return set(
            self._session.scalars(select(CollectionModel.id).where(CollectionModel.id.in_(wanted)))
        )

    def collections_for_product(self, product_id: UUID) -> list[UUID]:
        return list(
            self._session.scalars(
                select(CollectionProductModel.collection_id).where(
                    CollectionProductModel.product_id == product_id
                )
            )
        )

    def set_product_collections(self, product_id: UUID, collection_ids: list[UUID]) -> None:
        current = set(self.collections_for_product(product_id))
        wanted = set(collection_ids)
        if current - wanted:
            self._session.execute(
                delete(CollectionProductModel).where(
                    CollectionProductModel.product_id == product_id,
                    CollectionProductModel.collection_id.in_(current - wanted),
                )
            )
        for collection_id in collection_ids:
            if collection_id in current:
                continue
            last = self._session.scalar(
                select(func.max(CollectionProductModel.position)).where(
                    CollectionProductModel.collection_id == collection_id
                )
            )
            self._session.add(
                CollectionProductModel(
                    collection_id=collection_id,
                    product_id=product_id,
                    position=(last + 1) if last is not None else 0,
                )
            )
        self._session.flush()


# --- Navigation -------------------------------------------------------------------------------


def _nav(row: NavigationItemModel) -> NavigationItem:
    return NavigationItem(
        id=row.id,
        menu=NavigationMenu(row.menu),
        label=row.label,
        link_type=NavigationLinkType(row.link_type),
        parent_id=row.parent_id,
        category_id=row.category_id,
        collection_id=row.collection_id,
        page_id=row.page_id,
        url=row.url,
        position=row.position,
        is_active=row.is_active,
        open_in_new_tab=row.open_in_new_tab,
    )


def _apply_nav(row: NavigationItemModel, item: NavigationItem) -> None:
    row.menu = item.menu.value
    row.label = item.label
    row.link_type = item.link_type.value
    row.parent_id = item.parent_id
    row.category_id = item.category_id
    row.collection_id = item.collection_id
    row.page_id = item.page_id
    row.url = item.url
    row.position = item.position
    row.is_active = item.is_active
    row.open_in_new_tab = item.open_in_new_tab


class SqlAlchemyNavigationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self, menu: NavigationMenu | None = None) -> Sequence[NavigationItem]:
        stmt = select(NavigationItemModel).order_by(
            NavigationItemModel.menu, NavigationItemModel.position, NavigationItemModel.label
        )
        if menu is not None:
            stmt = stmt.where(NavigationItemModel.menu == menu.value)
        return [_nav(r) for r in self._session.scalars(stmt)]

    def get(self, item_id: UUID) -> NavigationItem | None:
        row = self._session.get(NavigationItemModel, item_id)
        return _nav(row) if row else None

    def add(self, item: NavigationItem) -> None:
        row = NavigationItemModel(id=item.id)
        _apply_nav(row, item)
        self._session.add(row)
        self._session.flush()

    def save(self, item: NavigationItem) -> None:
        row = self._session.get(NavigationItemModel, item.id)
        if row is None:
            raise LookupError(f"Menu item {item.id} does not exist.")
        _apply_nav(row, item)
        self._session.flush()

    def delete(self, item_id: UUID) -> None:
        self._session.execute(delete(NavigationItemModel).where(NavigationItemModel.id == item_id))

    def reorder(self, item_ids: list[UUID]) -> None:
        for position, item_id in enumerate(item_ids):
            self._session.execute(
                update(NavigationItemModel)
                .where(NavigationItemModel.id == item_id)
                .values(position=position)
            )


# --- Website pages ----------------------------------------------------------------------------


def _page(row: WebsitePageModel) -> WebsitePage:
    return WebsitePage(
        id=row.id,
        slug=row.slug,
        title=row.title,
        content=dict(row.content or {}),
        status=PublishStatus(row.status),
        seo_title=row.seo_title,
        seo_description=row.seo_description,
        published_at=row.published_at,
        updated_at=row.updated_at,
    )


class SqlAlchemyPageRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self) -> Sequence[WebsitePage]:
        return [
            _page(r)
            for r in self._session.scalars(select(WebsitePageModel).order_by(WebsitePageModel.title))
        ]

    def get(self, page_id: UUID) -> WebsitePage | None:
        row = self._session.get(WebsitePageModel, page_id)
        return _page(row) if row else None

    def get_by_slug(self, slug: str) -> WebsitePage | None:
        row = self._session.scalars(
            select(WebsitePageModel).where(WebsitePageModel.slug == slug)
        ).first()
        return _page(row) if row else None

    def add(self, page: WebsitePage) -> None:
        self._session.add(
            WebsitePageModel(
                id=page.id,
                slug=page.slug,
                title=page.title,
                content=page.content,
                status=page.status.value,
                seo_title=page.seo_title,
                seo_description=page.seo_description,
                published_at=page.published_at,
            )
        )
        self._session.flush()

    def save(self, page: WebsitePage) -> None:
        row = self._session.get(WebsitePageModel, page.id)
        if row is None:
            raise LookupError(f"Page {page.id} does not exist.")
        row.slug = page.slug
        row.title = page.title
        row.content = page.content
        row.status = page.status.value
        row.seo_title = page.seo_title
        row.seo_description = page.seo_description
        row.published_at = page.published_at
        self._session.flush()

    def delete(self, page_id: UUID) -> None:
        self._session.execute(delete(WebsitePageModel).where(WebsitePageModel.id == page_id))

    def slug_taken(self, slug: str, *, exclude_id: UUID | None = None) -> bool:
        stmt = select(WebsitePageModel.id).where(WebsitePageModel.slug == slug)
        if exclude_id is not None:
            stmt = stmt.where(WebsitePageModel.id != exclude_id)
        return self._session.scalars(stmt.limit(1)).first() is not None


# --- Shipping rules ---------------------------------------------------------------------------


def _rule(row: ShippingRuleModel) -> ShippingRule:
    return ShippingRule(
        id=row.id,
        name=row.name,
        fee=row.fee,
        min_order_amount=row.min_order_amount,
        max_order_amount=row.max_order_amount,
        priority=row.priority,
        is_active=row.is_active,
    )


class SqlAlchemyShippingRuleRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self) -> Sequence[ShippingRule]:
        rows = self._session.scalars(
            select(ShippingRuleModel).order_by(
                ShippingRuleModel.priority, ShippingRuleModel.min_order_amount
            )
        )
        return [_rule(r) for r in rows]

    def get(self, rule_id: UUID) -> ShippingRule | None:
        row = self._session.get(ShippingRuleModel, rule_id)
        return _rule(row) if row else None

    def add(self, rule: ShippingRule) -> None:
        self._session.add(
            ShippingRuleModel(
                id=rule.id,
                name=rule.name,
                fee=rule.fee,
                min_order_amount=rule.min_order_amount,
                max_order_amount=rule.max_order_amount,
                priority=rule.priority,
                is_active=rule.is_active,
            )
        )
        self._session.flush()

    def save(self, rule: ShippingRule) -> None:
        row = self._session.get(ShippingRuleModel, rule.id)
        if row is None:
            raise LookupError(f"Shipping rule {rule.id} does not exist.")
        row.name = rule.name
        row.fee = rule.fee
        row.min_order_amount = rule.min_order_amount
        row.max_order_amount = rule.max_order_amount
        row.priority = rule.priority
        row.is_active = rule.is_active
        self._session.flush()

    def delete(self, rule_id: UUID) -> None:
        self._session.execute(delete(ShippingRuleModel).where(ShippingRuleModel.id == rule_id))


# --- Size charts ------------------------------------------------------------------------------


def _chart(row: SizeChartModel) -> SizeChart:
    return SizeChart(
        id=row.id,
        name=row.name,
        slug=row.slug,
        chart=dict(row.chart or {}),
        description=row.description,
    )


class SqlAlchemySizeChartRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self) -> Sequence[SizeChart]:
        return [
            _chart(r) for r in self._session.scalars(select(SizeChartModel).order_by(SizeChartModel.name))
        ]

    def get(self, chart_id: UUID) -> SizeChart | None:
        row = self._session.get(SizeChartModel, chart_id)
        return _chart(row) if row else None

    def add(self, chart: SizeChart) -> None:
        self._session.add(
            SizeChartModel(
                id=chart.id,
                name=chart.name,
                slug=chart.slug,
                chart=chart.chart,
                description=chart.description,
            )
        )
        self._session.flush()

    def save(self, chart: SizeChart) -> None:
        row = self._session.get(SizeChartModel, chart.id)
        if row is None:
            raise LookupError(f"Size chart {chart.id} does not exist.")
        row.name = chart.name
        row.slug = chart.slug
        row.chart = chart.chart
        row.description = chart.description
        self._session.flush()

    def delete(self, chart_id: UUID) -> None:
        self._session.execute(delete(SizeChartModel).where(SizeChartModel.id == chart_id))

    def slug_taken(self, slug: str, *, exclude_id: UUID | None = None) -> bool:
        stmt = select(SizeChartModel.id).where(SizeChartModel.slug == slug)
        if exclude_id is not None:
            stmt = stmt.where(SizeChartModel.id != exclude_id)
        return self._session.scalars(stmt.limit(1)).first() is not None

    def in_use(self, chart_id: UUID) -> bool:
        stmt = select(ProductModel.id).where(ProductModel.size_chart_id == chart_id).limit(1)
        return self._session.scalars(stmt).first() is not None
