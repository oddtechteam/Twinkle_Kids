"""Homepage page builder (draft workspace), publishing, and the public read model."""

import builtins
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from app.application.content_settings import validate_section_settings
from app.application.dto.catalog import (
    CategorySummary,
    CollectionSummary,
    ImageView,
    ProductFilters,
    ProductSort,
    ProductSummary,
)
from app.application.ports import CatalogQueries, RecommendationQueries
from app.domain.entities.content import MAX_SECTION_PRODUCTS, HomepageSection, validate_ordering
from app.domain.enums import HomepageSectionType, PublishStatus, SelectionMode
from app.domain.errors import DomainValidationError, NotFoundError
from app.domain.repositories.catalog import CategoryRepository, ProductRepository
from app.domain.repositories.identity import AuditLogRepository
from app.domain.repositories.media import MediaAssetRepository, UnitOfWork
from app.domain.repositories.site import CollectionAdminRepository, HomepageBuilderRepository
from app.domain.value_objects.text import clean_optional

SNAPSHOT_VERSION = 1


@dataclass(frozen=True, slots=True)
class SectionInput:
    section_type: HomepageSectionType
    title: str | None = None
    subtitle: str | None = None
    settings: dict[str, Any] = field(default_factory=dict)
    is_visible: bool = True
    desktop_media_id: UUID | None = None
    mobile_media_id: UUID | None = None
    selection_mode: SelectionMode = SelectionMode.NONE
    source_category_id: UUID | None = None
    source_collection_id: UUID | None = None
    product_limit: int = 12


@dataclass(frozen=True, slots=True)
class SectionView:
    section: HomepageSection
    product_ids: list[UUID]


@dataclass(frozen=True, slots=True)
class PublicationInfo:
    published_at: datetime | None
    draft_modified_at: datetime | None

    @property
    def has_unpublished_changes(self) -> bool:
        if self.published_at is None:
            return self.draft_modified_at is not None
        return self.draft_modified_at is not None and self.draft_modified_at > self.published_at


class HomepageBuilder:
    def __init__(
        self,
        *,
        sections: HomepageBuilderRepository,
        categories: CategoryRepository,
        collections: CollectionAdminRepository,
        products: ProductRepository,
        media: MediaAssetRepository,
        audit: AuditLogRepository,
        uow: UnitOfWork,
    ) -> None:
        self._sections = sections
        self._categories = categories
        self._collections = collections
        self._products = products
        self._media = media
        self._audit = audit
        self._uow = uow

    # --- reads ---------------------------------------------------------------------------

    def list(self) -> list[SectionView]:
        return [
            SectionView(s, self._sections.product_ids(s.id)) for s in self._sections.list_sections()
        ]

    def get(self, section_id: UUID) -> SectionView:
        section = self._require(section_id)
        return SectionView(section, self._sections.product_ids(section_id))

    def publication(self) -> PublicationInfo:
        latest = self._sections.latest_publication()
        return PublicationInfo(
            published_at=latest[1] if latest else None,
            draft_modified_at=self._sections.last_modified(),
        )

    # --- commands ------------------------------------------------------------------------

    def create(self, data: SectionInput, *, actor_id: UUID | None) -> UUID:
        section = self._build(uuid4(), data, position=self._sections.next_position())
        self._sections.add(section)
        self._log(actor_id, "homepage_section.created", section.id)
        self._uow.commit()
        return section.id

    def update(self, section_id: UUID, data: SectionInput, *, actor_id: UUID | None) -> None:
        current = self._require(section_id)
        if data.section_type is not current.section_type:
            raise DomainValidationError("A section's type cannot be changed; add a new section.")
        section = self._build(section_id, data, position=current.position)
        self._sections.save(section)
        if section.selection_mode not in CURATED_MODES:
            self._sections.set_products(section_id, [])
        self._log(actor_id, "homepage_section.updated", section_id)
        self._uow.commit()

    def set_visibility(self, section_id: UUID, visible: bool, *, actor_id: UUID | None) -> None:
        section = self._require(section_id)
        section.is_visible = visible
        self._sections.save(section)
        self._log(
            actor_id, "homepage_section.shown" if visible else "homepage_section.hidden", section_id
        )
        self._uow.commit()

    def delete(self, section_id: UUID, *, actor_id: UUID | None) -> None:
        self._require(section_id)
        self._sections.delete(section_id)
        self._log(actor_id, "homepage_section.deleted", section_id)
        self._uow.commit()

    def reorder(self, section_ids: builtins.list[UUID], *, actor_id: UUID | None) -> None:
        existing = {s.id for s in self._sections.list_sections()}
        if len(set(section_ids)) != len(section_ids) or set(section_ids) != existing:
            raise DomainValidationError("The new order must list every section exactly once.")
        self._sections.reorder(section_ids)
        self._log(actor_id, "homepage.sections_reordered", None)
        self._uow.commit()

    def set_products(
        self, section_id: UUID, product_ids: builtins.list[UUID], *, actor_id: UUID | None
    ) -> None:
        section = self._require(section_id)
        if section.selection_mode not in CURATED_MODES:
            raise DomainValidationError("Only manual-selection sections have a hand-picked order.")
        ordering = validate_ordering(product_ids, limit=MAX_SECTION_PRODUCTS)
        if set(ordering) - self._products.existing_ids(ordering):
            raise DomainValidationError("One or more products do not exist.")
        self._sections.set_products(section_id, ordering)
        self._log(actor_id, "homepage_section.products_set", section_id, {"count": len(ordering)})
        self._uow.commit()

    def publish(self, *, actor_id: UUID | None, note: str | None = None) -> datetime:
        """Freeze the current visible sections into a new live publication."""
        sections = [s for s in self._sections.list_sections() if s.is_visible]
        snapshot_sections = []
        for section in sections:
            section.validate()
            validate_section_settings(section.section_type, section.settings)
            snapshot_sections.append(
                {
                    "id": str(section.id),
                    "type": section.section_type.value,
                    "title": section.title,
                    "subtitle": section.subtitle,
                    "settings": section.settings,
                    "desktop_media_id": _str(section.desktop_media_id),
                    "mobile_media_id": _str(section.mobile_media_id),
                    "selection_mode": section.selection_mode.value,
                    "source_category_id": _str(section.source_category_id),
                    "source_collection_id": _str(section.source_collection_id),
                    "product_limit": section.product_limit,
                    "product_ids": [str(p) for p in self._sections.product_ids(section.id)],
                }
            )
            section.status = PublishStatus.PUBLISHED
            self._sections.save(section)
        published_at = self._sections.add_publication(
            {"version": SNAPSHOT_VERSION, "sections": snapshot_sections},
            published_by=actor_id,
            note=clean_optional(note),
        )
        self._log(actor_id, "homepage.published", None, {"sections": len(snapshot_sections)})
        self._uow.commit()
        return published_at

    # --- helpers -------------------------------------------------------------------------

    def _require(self, section_id: UUID) -> HomepageSection:
        section = self._sections.get(section_id)
        if section is None:
            raise NotFoundError("Homepage section not found.")
        return section

    def _build(self, section_id: UUID, data: SectionInput, *, position: int) -> HomepageSection:
        section = HomepageSection(
            id=section_id,
            section_type=data.section_type,
            title=clean_optional(data.title),
            subtitle=clean_optional(data.subtitle),
            settings=validate_section_settings(data.section_type, data.settings),
            is_visible=data.is_visible,
            status=PublishStatus.DRAFT,
            position=position,
            desktop_media_id=data.desktop_media_id,
            mobile_media_id=data.mobile_media_id,
            selection_mode=data.selection_mode,
            source_category_id=data.source_category_id,
            source_collection_id=data.source_collection_id,
            product_limit=data.product_limit,
        )
        section.validate()
        media = [m for m in (section.desktop_media_id, section.mobile_media_id) if m]
        if set(media) - self._media.existing_ids(media):
            raise DomainValidationError("Image does not exist in the media library.")
        if section.source_category_id and not self._categories.existing_ids(
            [section.source_category_id]
        ):
            raise DomainValidationError("Source category does not exist.")
        if (
            section.source_collection_id
            and self._collections.get(section.source_collection_id) is None
        ):
            raise DomainValidationError("Source collection does not exist.")
        settings = section.settings
        if settings.get("category_ids"):
            ids = [UUID(i) for i in settings["category_ids"]]
            if set(ids) - self._categories.existing_ids(ids):
                raise DomainValidationError("One or more selected categories do not exist.")
        if settings.get("collection_ids"):
            ids = [UUID(i) for i in settings["collection_ids"]]
            if set(ids) - self._collections.existing_ids(ids):
                raise DomainValidationError("One or more selected collections do not exist.")
        return section

    def _log(
        self,
        actor_id: UUID | None,
        action: str,
        section_id: UUID | None,
        changes: dict[str, Any] | None = None,
    ) -> None:
        self._audit.record(
            actor_user_id=actor_id,
            action=action,
            entity_type="homepage_section" if section_id else "homepage",
            entity_id=str(section_id) if section_id else None,
            changes=changes,
        )


def _str(value: UUID | None) -> str | None:
    return str(value) if value else None


# --- Public read model ------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PublishedSection:
    id: str
    type: str
    title: str | None
    subtitle: str | None
    settings: dict[str, Any]
    desktop_image: ImageView | None
    mobile_image: ImageView | None
    products: list[ProductSummary]
    categories: list[CategorySummary]
    collections: list[CollectionSummary]
    collection: CollectionSummary | None
    view_all_href: str | None


@dataclass(frozen=True, slots=True)
class PublishedHomepage:
    published: bool
    published_at: datetime | None
    sections: list[PublishedSection]


# Modes that keep the section's own hand-picked product list (bestsellers use it as fallback).
CURATED_MODES = frozenset({SelectionMode.MANUAL, SelectionMode.BESTSELLERS})


class PublicHomepage:
    """Resolves the latest publication against live data (active products only, current
    image URLs, published collections)."""

    def __init__(
        self,
        *,
        sections: HomepageBuilderRepository,
        categories: CategoryRepository,
        queries: CatalogQueries,
        recommendations: RecommendationQueries | None = None,
    ) -> None:
        self._sections = sections
        self._categories = categories
        self._queries = queries
        self._recommendations = recommendations

    def get(self) -> PublishedHomepage:
        latest = self._sections.latest_publication()
        if latest is None:
            return PublishedHomepage(published=False, published_at=None, sections=[])
        snapshot, published_at = latest
        raw_sections: Sequence[dict[str, Any]] = snapshot.get("sections", [])
        media_ids = {
            UUID(v)
            for s in raw_sections
            for v in (s.get("desktop_media_id"), s.get("mobile_media_id"))
            if v
        }
        images = self._queries.images(list(media_ids))
        all_categories: list[CategorySummary] | None = None
        resolved: list[PublishedSection] = []

        for raw in raw_sections:
            kind = raw["type"]
            settings = dict(raw.get("settings") or {})
            products: list[ProductSummary] = []
            categories: list[CategorySummary] = []
            collections: list[CollectionSummary] = []
            collection: CollectionSummary | None = None
            view_all: str | None = None
            limit = int(raw.get("product_limit") or 12)
            mode = raw.get("selection_mode", "none")

            if mode == SelectionMode.MANUAL.value:
                ids = [UUID(p) for p in raw.get("product_ids", [])]
                products = list(self._queries.ordered_products(ids))[:limit]
            elif mode == SelectionMode.CATEGORY.value and raw.get("source_category_id"):
                category = self._categories.get(UUID(raw["source_category_id"]))
                if category and category.is_active:
                    products = self._list(
                        ProductFilters(page_size=limit, category_slug=category.slug)
                    )
                    view_all = f"/category/{category.slug}"
            elif mode == SelectionMode.COLLECTION.value and raw.get("source_collection_id"):
                found = self._queries.list_collections(
                    ids=[UUID(raw["source_collection_id"])], published_only=True
                )
                if found:
                    collection = found[0]
                    products = self._list(
                        ProductFilters(page_size=limit, collection_slug=collection.slug)
                    )
                    view_all = f"/collections/{collection.slug}"
            elif mode == SelectionMode.NEWEST.value:
                products = self._list(ProductFilters(page_size=limit, sort=ProductSort.NEWEST))
                view_all = "/shop?sort=newest"
            elif mode == SelectionMode.BESTSELLERS.value and self._recommendations is not None:
                # Real order data first; the admin's own picks fill any gap (never invented).
                ranked = self._recommendations.bestseller_ids(limit=limit)
                fallback = [UUID(p) for p in raw.get("product_ids", []) if UUID(p) not in ranked]
                products = list(self._queries.ordered_products([*ranked, *fallback]))[:limit]
                view_all = "/shop?sort=bestselling"
            elif mode == SelectionMode.FEATURED.value and self._recommendations is not None:
                ids = self._recommendations.featured_ids(limit=limit)
                products = list(self._queries.ordered_products(ids))[:limit]

            if kind == HomepageSectionType.CATEGORY_GRID.value:
                if all_categories is None:
                    all_categories = list(self._queries.list_categories())
                chosen = [UUID(i) for i in settings.get("category_ids", [])]
                if chosen:
                    by_id = {c.id: c for c in all_categories}
                    categories = [by_id[i] for i in chosen if i in by_id]
                else:
                    categories = [c for c in all_categories if c.parent_id is None][:6]
            if kind == HomepageSectionType.COLLECTION_SHOWCASE.value:
                chosen = [UUID(i) for i in settings.get("collection_ids", [])]
                found = self._queries.list_collections(ids=chosen or None, published_only=True)
                order = {cid: i for i, cid in enumerate(chosen)}
                collections = sorted(found, key=lambda c: order.get(c.id, 999))[:6]

            resolved.append(
                PublishedSection(
                    id=raw["id"],
                    type=kind,
                    title=raw.get("title"),
                    subtitle=raw.get("subtitle"),
                    settings=settings,
                    desktop_image=images.get(UUID(raw["desktop_media_id"]))
                    if raw.get("desktop_media_id")
                    else None,
                    mobile_image=images.get(UUID(raw["mobile_media_id"]))
                    if raw.get("mobile_media_id")
                    else None,
                    products=products,
                    categories=categories,
                    collections=collections,
                    collection=collection,
                    view_all_href=view_all,
                )
            )
        return PublishedHomepage(published=True, published_at=published_at, sections=resolved)

    def _list(self, filters: ProductFilters) -> list[ProductSummary]:
        return list(self._queries.list_products(filters).items)
