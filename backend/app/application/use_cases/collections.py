"""Collection management with independent, per-collection product ordering."""

import builtins
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID, uuid4

from app.application.dto.catalog import ProductSummary
from app.application.ports import CatalogQueries
from app.domain.entities.content import Collection, validate_ordering
from app.domain.enums import PublishStatus
from app.domain.errors import ConflictError, DomainValidationError, NotFoundError
from app.domain.repositories.catalog import CollectionRepository, ProductRepository
from app.domain.repositories.identity import AuditLogRepository
from app.domain.repositories.media import MediaAssetRepository, UnitOfWork
from app.domain.repositories.site import CollectionAdminRepository
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


class CollectionService:
    def __init__(
        self,
        *,
        collections: CollectionRepository,
        admin: CollectionAdminRepository,
        products: ProductRepository,
        media: MediaAssetRepository,
        queries: CatalogQueries,
        audit: AuditLogRepository,
        uow: UnitOfWork,
    ) -> None:
        self._collections = collections
        self._admin = admin
        self._products = products
        self._media = media
        self._queries = queries
        self._audit = audit
        self._uow = uow

    def list(self) -> Sequence[tuple[Collection, int]]:
        return self._admin.list()

    def get(self, collection_id: UUID) -> Collection:
        collection = self._admin.get(collection_id)
        if collection is None:
            raise NotFoundError("Collection not found.")
        return collection

    def create(self, data: CollectionInput, *, actor_id: UUID | None) -> UUID:
        collection = Collection(id=uuid4(), name="", slug="")
        self._apply(collection, data, existing_id=None)
        self._collections.add(collection)
        self._log(actor_id, "collection.created", collection.id)
        self._uow.commit()
        return collection.id

    def update(self, collection_id: UUID, data: CollectionInput, *, actor_id: UUID | None) -> None:
        collection = self.get(collection_id)
        self._apply(collection, data, existing_id=collection_id)
        self._admin.save(collection)
        self._log(actor_id, "collection.updated", collection_id)
        self._uow.commit()

    def set_status(
        self, collection_id: UUID, status: PublishStatus, *, actor_id: UUID | None
    ) -> None:
        collection = self.get(collection_id)
        collection.status = status
        self._admin.save(collection)
        self._log(actor_id, f"collection.{status.value}", collection_id)
        self._uow.commit()

    def products(self, collection_id: UUID) -> Sequence[ProductSummary]:
        self.get(collection_id)
        ids = self._collections.product_ids(collection_id)
        return self._queries.ordered_products(ids, include_inactive=True)

    def set_products(
        self, collection_id: UUID, product_ids: builtins.list[UUID], *, actor_id: UUID | None
    ) -> None:
        """Replace membership and ordering in one step (list index = position)."""
        self.get(collection_id)
        ordering = validate_ordering(product_ids)
        if set(ordering) - self._products.existing_ids(ordering):
            raise DomainValidationError("One or more products do not exist.")
        self._collections.set_products(collection_id, ordering)
        self._log(actor_id, "collection.products_set", collection_id, len(ordering))
        self._uow.commit()

    def _apply(
        self, collection: Collection, data: CollectionInput, *, existing_id: UUID | None
    ) -> None:
        name = data.name.strip()
        if not name:
            raise DomainValidationError("Collection name is required.")
        slug = validate_slug(data.slug or slugify(name))
        if self._admin.slug_taken(slug, exclude_id=existing_id):
            raise ConflictError(f"The slug '{slug}' is already used by another collection.")
        if data.image_media_id and not self._media.existing_ids([data.image_media_id]):
            raise DomainValidationError("Collection image does not exist in the media library.")
        collection.name = name
        collection.slug = slug
        collection.description = clean_optional(data.description)
        collection.image_media_id = data.image_media_id
        collection.status = data.status
        collection.display_order = data.display_order
        collection.seo_title = clean_optional(data.seo_title)
        collection.seo_description = clean_optional(data.seo_description)

    def _log(
        self, actor_id: UUID | None, action: str, collection_id: UUID, count: int | None = None
    ) -> None:
        self._audit.record(
            actor_user_id=actor_id,
            action=action,
            entity_type="collection",
            entity_id=str(collection_id),
            changes={"count": count} if count is not None else None,
        )
