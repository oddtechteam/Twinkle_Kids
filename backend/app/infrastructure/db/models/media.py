import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base
from app.infrastructure.db.types import UTCDateTime


class MediaAssetModel(Base):
    """Metadata + storage reference for a file in Neon Object Storage (bytes live in the bucket).

    Catalog and CMS tables reference rows here by ``id`` (product images, category images,
    homepage banners, ...).
    """

    __tablename__ = "media_assets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    purpose: Mapped[str] = mapped_column(String(32))
    visibility: Mapped[str] = mapped_column(String(16))
    bucket: Mapped[str] = mapped_column(String(63))
    object_key: Mapped[str] = mapped_column(String(512))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    original_filename: Mapped[str | None] = mapped_column(String(255))
    alt_text: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("bucket", "object_key", name="uq_media_assets_bucket_object_key"),
        CheckConstraint(
            "purpose IN ('product_image','category_image','collection_image',"
            "'homepage_banner','content_image')",
            name="purpose_valid",
        ),
        CheckConstraint("visibility IN ('public','private')", name="visibility_valid"),
        CheckConstraint("size_bytes > 0", name="size_positive"),
        CheckConstraint("width > 0 AND height > 0", name="dimensions_positive"),
        Index("ix_media_assets_purpose_created_at", "purpose", "created_at"),
    )
