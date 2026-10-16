"""Collections and homepage sections, each with its own independent product ordering."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from app.application.content_settings import validate_section_settings
from app.application.dto.catalog import ProductFilters, ProductSort, ProductSummary
from app.application.ports import CatalogQueries
from app.domain.entities.content import (
    MAX_SECTION_PRODUCTS,
    Collection,
    HomepageSection,
    validate_ordering,
)
from app.domain.enums import HomepageSectionType, PublishStatus, SelectionMode
from app.domain.errors import ConflictError, DomainValidationError, NotFoundError
from app.domain.repositories.catalog import (
    CategoryRepository,
    CollectionRepository,
    HomepageSectionRepository,
    ProductRepository,
)
from app.domain.repositories.identity import AuditLogRepository
from app.domain.repositories.media import MediaAssetRepository, UnitOfWork
from app.domain.value_objects.text import clean_optional, slugify, validate_slug


@dataclass(frozen=True, slots=True)
class CollectionInput:
    name: str
    slug: str | None = None
    description: str | None = None
    image_media_id: UUID | None = None
    status: PublishStatus = PublishStatus.DRAFT
    display_order: int = 0
    seo_title: str | None = None
    seo_description: str | None = None


@dataclass(frozen=True, slots=True)
class HomepageSectionInput:
    section_type: HomepageSectionType
    title: str | None = None
    subtitle: str | None = None
    settings: dict[str, Any] = field(default_factory=dict)
    is_visible: bool = True
    status: PublishStatus = PublishStatus.DRAFT
    position: int = 0
    desktop_media_id: UUID | None = None
    mobile_media_id: UUID | None = None
    selection_mode: SelectionMode = SelectionMode.NONE
    source_category_id: UUID | None = None
    source_collection_id: UUID | None = None
    product_limit: int = 12


class MerchandisingService:
    def __init__(
        self,
        *,
        collections: CollectionRepository,
        sections: HomepageSectionRepository,
        categories: CategoryRepository,
        products: ProductRepository,
        media: MediaAssetRepository,
        queries: CatalogQueries,
        audit: AuditLogRepository,
        uow: UnitOfWork,
    ) -> None:
        self._collections = collections
        self._sections = sections
        self._categories = categories
        self._products = products
        self._media = media
        self._queries = queries
        self._audit = audit
        self._uow = uow

    # --- collections -----------------------------------------------------------------------

    def create_collection(self, data: CollectionInput, *, actor_id: UUID | None) -> UUID:
        slug = validate_slug(data.slug or slugify(data.name))
        if not data.name.strip():
            raise DomainValidationError("Collection name is required.")
        if self._collections.slug_taken(slug):
            raise ConflictError(f"The slug '{slug}' is already used by another collection.")
        self._require_media([data.image_media_id])
        collection = Collection(
            id=uuid4(),
            name=data.name.strip(),
            slug=slug,
            description=clean_optional(data.description),
            image_media_id=data.image_media_id,
            status=data.status,
            display_order=data.display_order,
            seo_title=clean_optional(data.seo_title),
            seo_description=clean_optional(data.seo_description),
        )
        self._collections.add(collection)
        self._audit.record(
            actor_user_id=actor_id,
            action="collection.created",
            entity_type="collection",
            entity_id=str(collection.id),
        )
        self._uow.commit()
        return collection.id

    def set_collection_products(
        self, collection_id: UUID, product_ids: list[UUID], *, actor_id: UUID | None
    ) -> None:
        if self._collections.get(collection_id) is None:
            raise NotFoundError("Collection not found.")
        ordering = self._valid_products(product_ids)
        self._collections.set_products(collection_id, ordering)
        self._audit.record(
            actor_user_id=actor_id,
            action="collection.products_set",
            entity_type="collection",
            entity_id=str(collection_id),
            changes={"count": len(ordering)},
        )
        self._uow.commit()

    def collection_products(self, collection_id: UUID) -> Sequence[ProductSummary]:
        if self._collections.get(collection_id) is None:
            raise NotFoundError("Collection not found.")
        return self._queries.ordered_products(self._collections.product_ids(collection_id))

    # --- homepage sections -----------------------------------------------------------------

    def create_section(self, data: HomepageSectionInput, *, actor_id: UUID | None) -> UUID:
        section = HomepageSection(
            id=uuid4(),
            section_type=data.section_type,
            title=clean_optional(data.title),
            subtitle=clean_optional(data.subtitle),
            settings=validate_section_settings(data.section_type, data.settings),
            is_visible=data.is_visible,
            status=data.status,
            position=data.position,
            desktop_media_id=data.desktop_media_id,
            mobile_media_id=data.mobile_media_id,
            selection_mode=data.selection_mode,
            source_category_id=data.source_category_id,
            source_collection_id=data.source_collection_id,
            product_limit=data.product_limit,
        )
        section.validate()
        self._require_media([section.desktop_media_id, section.mobile_media_id])
        if section.source_category_id and not self._categories.existing_ids(
            [section.source_category_id]
        ):
            raise DomainValidationError("Source category does not exist.")
        if (
            section.source_collection_id
            and self._collections.get(section.source_collection_id) is None
        ):
            raise DomainValidationError("Source collection does not exist.")
        self._sections.add(section)
        self._audit.record(
            actor_user_id=actor_id,
            action="homepage_section.created",
            entity_type="homepage_section",
            entity_id=str(section.id),
        )
        self._uow.commit()
        return section.id

    def set_section_products(
        self, section_id: UUID, product_ids: list[UUID], *, actor_id: UUID | None
    ) -> None:
        section = self._require_section(section_id)
        if section.selection_mode is not SelectionMode.MANUAL:
            raise DomainValidationError("Only manual-selection sections have a hand-picked order.")
        ordering = self._valid_products(product_ids, limit=MAX_SECTION_PRODUCTS)
        self._sections.set_products(section_id, ordering)
        self._audit.record(
            actor_user_id=actor_id,
            action="homepage_section.products_set",
            entity_type="homepage_section",
            entity_id=str(section_id),
            changes={"count": len(ordering)},
        )
        self._uow.commit()

    def section_products(self, section_id: UUID) -> Sequence[ProductSummary]:
        """Resolve the products a section displays, in that section's own order."""
        section = self._require_section(section_id)
        limit = section.product_limit
        match section.selection_mode:
            case SelectionMode.MANUAL:
                ids = self._sections.product_ids(section_id)
                return list(self._queries.ordered_products(ids))[:limit]
            case SelectionMode.CATEGORY:
                category = (
                    self._categories.get(section.source_category_id)
                    if section.source_category_id
                    else None
                )
                if category is None:
                    return []
                filters = ProductFilters(page_size=limit, category_slug=category.slug)
            case SelectionMode.COLLECTION:
                collection = (
                    self._collections.get(section.source_collection_id)
                    if section.source_collection_id
                    else None
                )
                if collection is None:
                    return []
                filters = ProductFilters(page_size=limit, collection_slug=collection.slug)
            case SelectionMode.NEWEST:
                filters = ProductFilters(page_size=limit, sort=ProductSort.NEWEST)
            case _:
                return []
        return self._queries.list_products(filters).items

    # --- helpers ---------------------------------------------------------------------------

    def _require_section(self, section_id: UUID) -> HomepageSection:
        section = self._sections.get(section_id)
        if section is None:
            raise NotFoundError("Homepage section not found.")
        return section

    def _valid_products(self, product_ids: list[UUID], *, limit: int = 500) -> list[UUID]:
        ordering = validate_ordering(product_ids, limit=limit)
        if set(ordering) - self._products.existing_ids(ordering):
            raise DomainValidationError("One or more products do not exist.")
        return ordering

    def _require_media(self, ids: list[UUID | None]) -> None:
        wanted = [i for i in ids if i is not None]
        if set(wanted) - self._media.existing_ids(wanted):
            raise DomainValidationError("Image does not exist in the media library.")
