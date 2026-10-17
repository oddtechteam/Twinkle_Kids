from collections.abc import Iterable, Sequence
from uuid import UUID

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.domain.entities.media import MediaAsset, MediaPurpose, MediaVisibility
from app.infrastructure.db.models.catalog import CategoryModel, ProductMediaModel, ProductModel
from app.infrastructure.db.models.content import (
    CollectionModel,
    HomepageSectionModel,
    StoreSettingsModel,
)
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
        return bool(self.usage(asset_id))

    def usage(self, asset_id: UUID) -> list[str]:
        """Every place that references the asset. Deleting is refused while any exist."""
        places: list[str] = []
        products = self._session.scalars(
            select(ProductModel.name)
            .join(ProductMediaModel, ProductMediaModel.product_id == ProductModel.id)
            .where(ProductMediaModel.media_asset_id == asset_id)
        )
        places += [f"Product: {name}" for name in products]
        places += [
            f"Category: {name}"
            for name in self._session.scalars(
                select(CategoryModel.name).where(CategoryModel.image_media_id == asset_id)
            )
        ]
        places += [
            f"Collection: {name}"
            for name in self._session.scalars(
                select(CollectionModel.name).where(CollectionModel.image_media_id == asset_id)
            )
        ]
        sections = self._session.execute(
            select(HomepageSectionModel.title, HomepageSectionModel.section_type).where(
                or_(
                    HomepageSectionModel.desktop_media_id == asset_id,
                    HomepageSectionModel.mobile_media_id == asset_id,
                )
            )
        )
        places += [f"Homepage section: {title or kind}" for title, kind in sections]
        settings = self._session.get(StoreSettingsModel, 1)
        if settings is not None:
            if settings.logo_media_id == asset_id:
                places.append("Store logo")
            if settings.favicon_media_id == asset_id:
                places.append("Store favicon")
            if str(asset_id) == str((settings.seo_defaults or {}).get("og_image_media_id")):
                places.append("SEO sharing image")
        return places

    def update(self, asset: MediaAsset) -> None:
        row = self._session.get(MediaAssetModel, asset.id)
        if row is None:
            raise LookupError(f"Media asset {asset.id} does not exist.")
        row.object_key = asset.object_key
        row.content_type = asset.content_type
        row.size_bytes = asset.size_bytes
        row.width = asset.width
        row.height = asset.height
        row.sha256 = asset.sha256
        row.original_filename = asset.original_filename
        row.alt_text = asset.alt_text
        self._session.flush()
