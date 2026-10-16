from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class MediaPurpose(StrEnum):
    """What a stored file is for. Catalog/CMS tables (Phase 2+) reference assets by id."""

    PRODUCT_IMAGE = "product_image"
    CATEGORY_IMAGE = "category_image"
    COLLECTION_IMAGE = "collection_image"
    HOMEPAGE_BANNER = "homepage_banner"
    CONTENT_IMAGE = "content_image"


class MediaVisibility(StrEnum):
    PUBLIC = "public"  # anonymous reads (storefront imagery)
    PRIVATE = "private"  # presigned, time-limited reads only


@dataclass(frozen=True, slots=True)
class ImageInfo:
    """Facts derived from the file bytes themselves, never from client-supplied metadata."""

    content_type: str
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class MediaAsset:
    id: UUID
    purpose: MediaPurpose
    visibility: MediaVisibility
    bucket: str
    object_key: str
    content_type: str
    size_bytes: int
    width: int
    height: int
    sha256: str
    created_at: datetime
    original_filename: str | None = None
    alt_text: str | None = None


@dataclass(frozen=True, slots=True)
class StoredObject:
    data: bytes
    content_type: str | None
