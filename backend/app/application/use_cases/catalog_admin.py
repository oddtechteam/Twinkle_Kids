"""Administrator commands for products and categories."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from app.domain.entities.catalog import Category, Product, ProductMediaLink, ProductVariant
from app.domain.entities.content import validate_ordering
from app.domain.enums import InventoryReason, ProductStatus
from app.domain.errors import ConflictError, DomainValidationError, NotFoundError
from app.domain.repositories.catalog import CategoryRepository, InventoryLedger, ProductRepository
from app.domain.repositories.identity import AuditLogRepository
from app.domain.repositories.media import MediaAssetRepository, UnitOfWork
from app.domain.value_objects.pricing import PricePair
from app.domain.value_objects.text import clean_optional, slugify, validate_sku, validate_slug

Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


# --- inputs ------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class VariantInput:
    sku: str
    size: str | None = None
    colour: str | None = None
    colour_hex: str | None = None
    selling_price_override: Decimal | None = None
    original_price_override: Decimal | None = None
    stock_quantity: int = 0
    is_active: bool = True
    id: UUID | None = None


@dataclass(frozen=True, slots=True)
class MediaInput:
    media_asset_id: UUID
    alt_text: str | None = None
    variant_sku: str | None = None  # links an image to a colour/size variant


@dataclass(frozen=True, slots=True)
class ProductInput:
    name: str
    sku: str
    selling_price: Decimal
    variants: list[VariantInput]
    original_price: Decimal | None = None
    slug: str | None = None
    status: ProductStatus = ProductStatus.DRAFT
    short_description: str | None = None
    description: str | None = None
    rich_content: dict[str, Any] | None = None
    track_inventory: bool = True
    allow_backorder: bool = False
    low_stock_threshold: int = 3
    size_chart_id: UUID | None = None
    seo_title: str | None = None
    seo_description: str | None = None
    seo_metadata: dict[str, Any] = field(default_factory=dict)
    category_ids: list[UUID] = field(default_factory=list)
    primary_category_id: UUID | None = None
    media: list[MediaInput] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class CategoryInput:
    name: str
    slug: str | None = None
    description: str | None = None
    parent_id: UUID | None = None
    image_media_id: UUID | None = None
    is_active: bool = True
    display_order: int = 0
    custom_product_ordering: bool = False
    seo_title: str | None = None
    seo_description: str | None = None
    seo_metadata: dict[str, Any] = field(default_factory=dict)


# --- products ----------------------------------------------------------------------------------


class ProductCommands:
    def __init__(
        self,
        *,
        products: ProductRepository,
        categories: CategoryRepository,
        media: MediaAssetRepository,
        inventory: InventoryLedger,
        audit: AuditLogRepository,
        uow: UnitOfWork,
        clock: Clock = _utc_now,
    ) -> None:
        self._products = products
        self._categories = categories
        self._media = media
        self._inventory = inventory
        self._audit = audit
        self._uow = uow
        self._clock = clock

    def create(self, data: ProductInput, *, actor_id: UUID | None) -> UUID:
        product = Product(
            id=uuid4(),
            name=data.name.strip(),
            slug="",
            sku="",
            price=PricePair(data.selling_price, data.original_price),
        )
        previous_stock = self._build(product, data, existing=None)
        self._products.add(product)
        self._record_stock(product, previous_stock, actor_id)
        self._audit.record(
            actor_user_id=actor_id,
            action="product.created",
            entity_type="product",
            entity_id=str(product.id),
            changes={"slug": product.slug, "status": product.status.value},
        )
        self._uow.commit()
        return product.id

    def update(self, product_id: UUID, data: ProductInput, *, actor_id: UUID | None) -> None:
        product = self._require(product_id)
        before = {"selling": str(product.price.selling), "original": str(product.price.original)}
        previous_stock = self._build(product, data, existing=product)
        self._products.save(product)
        self._record_stock(product, previous_stock, actor_id)
        self._audit.record(
            actor_user_id=actor_id,
            action="product.updated",
            entity_type="product",
            entity_id=str(product.id),
            changes={
                "price_before": before,
                "price_after": {
                    "selling": str(product.price.selling),
                    "original": str(product.price.original),
                },
                "status": product.status.value,
            },
        )
        self._uow.commit()

    def set_status(self, product_id: UUID, status: ProductStatus, *, actor_id: UUID | None) -> None:
        product = self._require(product_id)
        previous = product.status
        product.change_status(status, now=self._clock())
        self._products.save(product)
        self._audit.record(
            actor_user_id=actor_id,
            action="product.status_changed",
            entity_type="product",
            entity_id=str(product.id),
            changes={"from": previous.value, "to": status.value},
        )
        self._uow.commit()

    # -- helpers ------------------------------------------------------------------------------

    def _require(self, product_id: UUID) -> Product:
        product = self._products.get(product_id)
        if product is None:
            raise NotFoundError("Product not found.")
        return product

    def _build(
        self, product: Product, data: ProductInput, *, existing: Product | None
    ) -> dict[UUID, int]:
        """Apply input onto the aggregate and validate. Returns previous stock per variant id."""
        if not data.variants:
            raise DomainValidationError("A product needs at least one variant.")
        slug = validate_slug(data.slug or slugify(data.name))
        sku = validate_sku(data.sku)
        exclude = existing.id if existing else None
        if self._products.slug_taken(slug, exclude_id=exclude):
            raise ConflictError(f"The slug '{slug}' is already used by another product.")

        previous_variants = {v.id: v for v in existing.variants} if existing else {}
        by_sku = {v.sku: v for v in previous_variants.values()}
        variants: list[ProductVariant] = []
        for position, item in enumerate(data.variants):
            variant_sku = validate_sku(item.sku)
            match = previous_variants.get(item.id) if item.id else by_sku.get(variant_sku)
            if item.id is not None and match is None:
                raise DomainValidationError("Variant id does not belong to this product.")
            variants.append(
                ProductVariant(
                    id=match.id if match else uuid4(),
                    sku=variant_sku,
                    size=clean_optional(item.size),
                    colour=clean_optional(item.colour),
                    colour_hex=clean_optional(item.colour_hex),
                    selling_price_override=item.selling_price_override,
                    original_price_override=item.original_price_override,
                    stock_quantity=item.stock_quantity,
                    position=position,
                    is_active=item.is_active,
                )
            )

        all_skus = [sku, *(v.sku for v in variants)]
        taken = self._products.skus_taken(all_skus, exclude_product_id=exclude)
        if taken:
            raise ConflictError(f"SKU already in use: {', '.join(sorted(taken))}.")

        unknown_categories = set(data.category_ids) - self._categories.existing_ids(
            data.category_ids
        )
        if unknown_categories:
            raise DomainValidationError("One or more categories do not exist.")
        media_ids = [m.media_asset_id for m in data.media]
        if set(media_ids) - self._media.existing_ids(media_ids):
            raise DomainValidationError("One or more images do not exist in the media library.")
        variant_by_sku = {v.sku: v.id for v in variants}
        media_links = []
        for media_item in data.media:
            variant_id = None
            if media_item.variant_sku is not None:
                variant_id = variant_by_sku.get(validate_sku(media_item.variant_sku))
                if variant_id is None:
                    raise DomainValidationError("Image variant SKU does not match a variant.")
            media_links.append(
                ProductMediaLink(
                    media_item.media_asset_id, clean_optional(media_item.alt_text), variant_id
                )
            )

        product.name = data.name.strip()
        product.slug = slug
        product.sku = sku
        product.price = PricePair(data.selling_price, data.original_price)
        product.short_description = clean_optional(data.short_description)
        product.description = clean_optional(data.description)
        product.rich_content = data.rich_content
        product.track_inventory = data.track_inventory
        product.allow_backorder = data.allow_backorder
        product.low_stock_threshold = data.low_stock_threshold
        product.size_chart_id = data.size_chart_id
        product.seo_title = clean_optional(data.seo_title)
        product.seo_description = clean_optional(data.seo_description)
        product.seo_metadata = dict(data.seo_metadata)
        product.category_ids = list(data.category_ids)
        product.primary_category_id = data.primary_category_id or (
            data.category_ids[0] if data.category_ids else None
        )
        product.variants = variants
        product.media = media_links
        product.change_status(data.status, now=self._clock())  # validates the whole aggregate
        return {vid: v.stock_quantity for vid, v in previous_variants.items()}

    def _record_stock(
        self, product: Product, previous: dict[UUID, int], actor_id: UUID | None
    ) -> None:
        for variant in product.variants:
            before = previous.get(variant.id)
            delta = variant.stock_quantity - (before or 0)
            if delta == 0:
                continue
            reason = InventoryReason.INITIAL_STOCK if before is None else InventoryReason.ADJUSTMENT
            self._inventory.record(
                variant_id=variant.id,
                delta=delta,
                stock_after=variant.stock_quantity,
                reason=reason,
                actor_user_id=actor_id,
                note="Set via product editor",
            )


# --- categories --------------------------------------------------------------------------------


class CategoryCommands:
    def __init__(
        self,
        *,
        categories: CategoryRepository,
        products: ProductRepository,
        media: MediaAssetRepository,
        audit: AuditLogRepository,
        uow: UnitOfWork,
    ) -> None:
        self._categories = categories
        self._products = products
        self._media = media
        self._audit = audit
        self._uow = uow

    def create(self, data: CategoryInput, *, actor_id: UUID | None) -> UUID:
        category = Category(id=uuid4(), name="", slug="")
        self._apply(category, data, existing_id=None)
        self._categories.add(category)
        self._audit.record(
            actor_user_id=actor_id,
            action="category.created",
            entity_type="category",
            entity_id=str(category.id),
        )
        self._uow.commit()
        return category.id

    def update(self, category_id: UUID, data: CategoryInput, *, actor_id: UUID | None) -> None:
        category = self._require(category_id)
        self._apply(category, data, existing_id=category_id)
        self._categories.save(category)
        self._audit.record(
            actor_user_id=actor_id,
            action="category.updated",
            entity_type="category",
            entity_id=str(category.id),
        )
        self._uow.commit()

    def set_active(self, category_id: UUID, is_active: bool, *, actor_id: UUID | None) -> None:
        category = self._require(category_id)
        category.is_active = is_active
        self._categories.save(category)
        self._audit.record(
            actor_user_id=actor_id,
            action="category.activated" if is_active else "category.deactivated",
            entity_type="category",
            entity_id=str(category.id),
        )
        self._uow.commit()

    def set_product_order(
        self, category_id: UUID, product_ids: list[UUID], *, actor_id: UUID | None
    ) -> None:
        self._require(category_id)
        ordering = validate_ordering(product_ids)
        members = set(self._categories.product_ids(category_id))
        if not set(ordering) <= members:
            raise DomainValidationError("Only products in this category can be ordered here.")
        self._categories.set_product_order(category_id, ordering)
        self._audit.record(
            actor_user_id=actor_id,
            action="category.products_reordered",
            entity_type="category",
            entity_id=str(category_id),
        )
        self._uow.commit()

    def _require(self, category_id: UUID) -> Category:
        category = self._categories.get(category_id)
        if category is None:
            raise NotFoundError("Category not found.")
        return category

    def _apply(self, category: Category, data: CategoryInput, *, existing_id: UUID | None) -> None:
        slug = validate_slug(data.slug or slugify(data.name))
        if self._categories.slug_taken(slug, exclude_id=existing_id):
            raise ConflictError(f"The slug '{slug}' is already used by another category.")
        if data.parent_id is not None:
            if self._categories.get(data.parent_id) is None:
                raise DomainValidationError("Parent category does not exist.")
            if existing_id is not None and (
                data.parent_id == existing_id
                or existing_id in self._categories.ancestor_ids(data.parent_id)
            ):
                raise DomainValidationError("A category cannot be moved under its own subcategory.")
        if data.image_media_id is not None and not self._media.existing_ids([data.image_media_id]):
            raise DomainValidationError("Category image does not exist in the media library.")

        category.name = data.name.strip()
        category.slug = slug
        category.description = clean_optional(data.description)
        category.parent_id = data.parent_id
        category.image_media_id = data.image_media_id
        category.is_active = data.is_active
        category.display_order = data.display_order
        category.custom_product_ordering = data.custom_product_ordering
        category.seo_title = clean_optional(data.seo_title)
        category.seo_description = clean_optional(data.seo_description)
        category.seo_metadata = dict(data.seo_metadata)
        category.validate()
