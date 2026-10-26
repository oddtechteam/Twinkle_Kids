from collections.abc import Mapping
from dataclasses import dataclass, field
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
    REVIEW_IMAGE = "review_image"  # customer-uploaded, private until the review is approved


class MediaVisibility(StrEnum):
    PUBLIC = "public"  # anonymous reads (storefront imagery)
    PRIVATE = "private"  # presigned, time-limited reads only


class ImageFrame(StrEnum):
    """A storefront slot with a fixed shape. Every card in a section uses the same frame, so
    an image cropped for a frame shows the same composition wherever that frame appears."""

    PRODUCT = "product"  # product cards, product gallery, bag/checkout thumbnails
    CATEGORY = "category"  # category tiles
    COLLECTION = "collection"  # featured collection tiles
    HERO = "hero"  # the homepage hero arch (desktop and mobile)
    BANNER = "banner"  # promo banner and occasion photos


@dataclass(frozen=True, slots=True)
class FrameSpec:
    ratio_width: int
    ratio_height: int
    output_width: int  # widest rendition stored; smaller sources are never upscaled

    @property
    def ratio(self) -> float:
        return self.ratio_width / self.ratio_height


# Mirrored in frontend/src/lib/media/frames.ts and the storefront CSS aspect ratios.
FRAME_SPECS: Mapping[ImageFrame, FrameSpec] = {
    ImageFrame.PRODUCT: FrameSpec(4, 5, 1600),
    ImageFrame.CATEGORY: FrameSpec(1, 1, 1200),
    ImageFrame.COLLECTION: FrameSpec(3, 4, 1200),
    ImageFrame.HERO: FrameSpec(8, 15, 960),
    ImageFrame.BANNER: FrameSpec(4, 5, 1200),
}


@dataclass(frozen=True, slots=True)
class CropRect:
    """A rectangle as fractions (0-1) of the original image, after EXIF rotation."""

    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True, slots=True)
class ImageCrop:
    """The composition chosen for one frame, plus the optimised rendition cut from it. The
    original file is never modified, so the crop can be edited again later."""

    rect: CropRect
    object_key: str  # WebP rendition, same bucket as the original
    width: int
    height: int
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class RenderedImage:
    data: bytes
    content_type: str
    width: int
    height: int
    rect: CropRect  # the rectangle actually used (snapped to the frame's ratio)


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
    crops: Mapping[ImageFrame, ImageCrop] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StoredObject:
    data: bytes
    content_type: str | None
