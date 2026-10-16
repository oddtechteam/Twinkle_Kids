from collections.abc import Iterable, Sequence
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.domain.entities.media import MediaAsset, MediaPurpose, MediaVisibility
from app.infrastructure.db.models.catalog import ProductMediaModel
from app.infrastructure.db.models.media import MediaAssetModel


def _to_entity(row: MediaAssetModel) -> MediaAsset:
    return MediaAsset(
        id=row.id,
        purpose=MediaPurpose(row.purpose),
        visibility=MediaVisibility(row.visibility),
        bucket=row.bucket,
        object_key=row.object_key,
        content_type=row.content_type,
        size_bytes=row.size_bytes,
        width=row.width,
        height=row.height,
        sha256=row.sha256,
        created_at=row.created_at,
        original_filename=row.original_filename,
        alt_text=row.alt_text,
    )


class SqlAlchemyMediaAssetRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, asset: MediaAsset) -> None:
        self._session.add(
            MediaAssetModel(
                id=asset.id,
                purpose=asset.purpose.value,
                visibility=asset.visibility.value,
                bucket=asset.bucket,
                object_key=asset.object_key,
                content_type=asset.content_type,
                size_bytes=asset.size_bytes,
                width=asset.width,
                height=asset.height,
                sha256=asset.sha256,
                original_filename=asset.original_filename,
                alt_text=asset.alt_text,
                created_at=asset.created_at,
            )
        )
        self._session.flush()

    def get(self, asset_id: UUID) -> MediaAsset | None:
        row = self._session.get(MediaAssetModel, asset_id)
        return _to_entity(row) if row else None

    def delete(self, asset_id: UUID) -> None:
        self._session.execute(delete(MediaAssetModel).where(MediaAssetModel.id == asset_id))

    def list(
        self, *, purpose: MediaPurpose | None, limit: int, offset: int
    ) -> Sequence[MediaAsset]:
        stmt = select(MediaAssetModel).order_by(
            MediaAssetModel.created_at.desc(), MediaAssetModel.id
        )
        if purpose is not None:
            stmt = stmt.where(MediaAssetModel.purpose == purpose.value)
        rows = self._session.scalars(stmt.limit(limit).offset(offset))
        return [_to_entity(r) for r in rows]

    def existing_ids(self, ids: Iterable[UUID]) -> set[UUID]:
        wanted = set(ids)
        if not wanted:
            return set()
        return set(
            self._session.scalars(select(MediaAssetModel.id).where(MediaAssetModel.id.in_(wanted)))
        )

    def in_use(self, asset_id: UUID) -> bool:
        """True when a product image still references the asset (FK is RESTRICT)."""
        stmt = select(ProductMediaModel.id).where(ProductMediaModel.media_asset_id == asset_id)
        return self._session.scalars(stmt.limit(1)).first() is not None
