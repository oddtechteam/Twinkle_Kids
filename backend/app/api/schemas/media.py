from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.application.use_cases.media import MediaView
from app.domain.entities.media import MediaPurpose, MediaVisibility


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
