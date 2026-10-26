from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field

from app.application.use_cases.media import MediaView
from app.domain.entities.media import ImageFrame, MediaPurpose, MediaVisibility

Fraction = Annotated[float, Field(ge=0, le=1)]


class CropOut(BaseModel):
    """A saved crop: the rectangle (fractions of the original) and its rendition."""

    x: float
    y: float
    width: float
    height: float
    url: str
    output_width: int
    output_height: int
    updated_at: datetime


class CropIn(BaseModel):
    x: Fraction
    y: Fraction
    width: Annotated[float, Field(gt=0, le=1)]
    height: Annotated[float, Field(gt=0, le=1)]


def crops_out(view: MediaView) -> dict[ImageFrame, CropOut]:
    return {
        frame: CropOut(
            x=crop.rect.x,
            y=crop.rect.y,
            width=crop.rect.width,
            height=crop.rect.height,
            url=view.crop_urls[frame],
            output_width=crop.width,
            output_height=crop.height,
            updated_at=crop.updated_at,
        )
        for frame, crop in view.asset.crops.items()
        if frame in view.crop_urls
    }


class MediaAssetOut(BaseModel):
    id: UUID
    purpose: MediaPurpose
    visibility: MediaVisibility
    url: str
    content_type: str
    size_bytes: int
    width: int
    height: int
    alt_text: str | None
    created_at: datetime
    crops: dict[ImageFrame, CropOut] = {}

    @classmethod
    def from_view(cls, view: MediaView) -> "MediaAssetOut":
        a = view.asset
        return cls(
            id=a.id,
            purpose=a.purpose,
            visibility=a.visibility,
            url=view.url,
            content_type=a.content_type,
            size_bytes=a.size_bytes,
            width=a.width,
            height=a.height,
            alt_text=a.alt_text,
            created_at=a.created_at,
            crops=crops_out(view),
        )


class AdminMediaAssetOut(MediaAssetOut):
    bucket: str
    object_key: str
    sha256: str
    original_filename: str | None

    @classmethod
    def from_view(cls, view: MediaView) -> "AdminMediaAssetOut":
        a = view.asset
        return cls(
            **MediaAssetOut.from_view(view).model_dump(),
            bucket=a.bucket,
            object_key=a.object_key,
            sha256=a.sha256,
            original_filename=a.original_filename,
        )
