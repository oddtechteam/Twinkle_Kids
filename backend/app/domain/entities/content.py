from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.domain.enums import (
    PRODUCT_SECTION_TYPES,
    HomepageSectionType,
    PublishStatus,
    SelectionMode,
)
from app.domain.errors import DomainValidationError

MAX_SECTION_PRODUCTS = 48


@dataclass(slots=True)
class Collection:
    id: UUID
    name: str
    slug: str
    description: str | None = None
    image_media_id: UUID | None = None
    status: PublishStatus = PublishStatus.DRAFT
    display_order: int = 0
    seo_title: str | None = None
    seo_description: str | None = None


@dataclass(slots=True)
class HomepageSection:
    id: UUID
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

    def validate(self) -> None:
        shows_products = self.section_type in PRODUCT_SECTION_TYPES
        if shows_products and self.selection_mode is SelectionMode.NONE:
            raise DomainValidationError("Product sections need a product selection mode.")
        if not shows_products and self.selection_mode is not SelectionMode.NONE:
            raise DomainValidationError(f"{self.section_type} sections cannot select products.")
        if (self.selection_mode is SelectionMode.CATEGORY) != (self.source_category_id is not None):
            raise DomainValidationError("Category selection requires exactly a source category.")
        if (self.selection_mode is SelectionMode.COLLECTION) != (
            self.source_collection_id is not None
        ):
            raise DomainValidationError(
                "Collection selection requires exactly a source collection."
            )
        if not 1 <= self.product_limit <= MAX_SECTION_PRODUCTS:
            raise DomainValidationError(
                f"Product limit must be between 1 and {MAX_SECTION_PRODUCTS}."
            )
        needs_image = self.section_type in {
            HomepageSectionType.HERO_BANNER,
            HomepageSectionType.PROMO_BANNER,
        }
        if needs_image and self.desktop_media_id is None:
            raise DomainValidationError("Banner sections need a desktop image.")


def validate_ordering(product_ids: list[UUID], *, limit: int = 500) -> list[UUID]:
    """An explicit, duplicate-free ordering; list index becomes the stored position."""
    if len(product_ids) > limit:
        raise DomainValidationError(f"At most {limit} products can be ordered here.")
    if len(set(product_ids)) != len(product_ids):
        raise DomainValidationError("A product can appear only once in an ordering.")
    return list(product_ids)
