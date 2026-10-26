"""Media library use cases: validated upload, retrieval with URL resolution, listing, deletion,
and per-frame cropping.

Postgres is the source of truth for which files exist; the object store holds the bytes.
"""

import hashlib
import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.entities.media import (
    FRAME_SPECS,
    CropRect,
    ImageCrop,
    ImageFrame,
    ImageInfo,
    MediaAsset,
    MediaPurpose,
    MediaVisibility,
)
from app.domain.errors import (
    ConflictError,
    MediaTooLargeError,
    MediaValidationError,
    NotFoundError,
    UnsupportedMediaTypeError,
)
from app.domain.repositories.media import (
    ImageCropper,
    ImageInspector,
    MediaAssetRepository,
    ObjectStorage,
    UnitOfWork,
)

logger = logging.getLogger(__name__)

# Raster formats only. SVG is deliberately excluded: it can carry script.
ALLOWED_IMAGE_TYPES: Mapping[str, str] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/avif": "avif",
}
_CONTENT_TYPE_ALIASES = {"image/jpg": "image/jpeg", "image/pjpeg": "image/jpeg"}

PUBLIC_CACHE_CONTROL = "public, max-age=31536000, immutable"  # keys are never reused
PRIVATE_CACHE_CONTROL = "private, no-store"
PRESIGNED_URL_TTL_SECONDS = 15 * 60
MAX_ALT_TEXT = 300
MAX_FILENAME = 255


@dataclass(frozen=True, slots=True)
class MediaPolicy:
    max_bytes: int
    allowed_types: Mapping[str, str] = field(default_factory=lambda: dict(ALLOWED_IMAGE_TYPES))


@dataclass(frozen=True, slots=True)
class UploadMediaCommand:
    data: bytes
    purpose: MediaPurpose
    visibility: MediaVisibility = MediaVisibility.PUBLIC
    declared_content_type: str | None = None
    original_filename: str | None = None
    alt_text: str | None = None


@dataclass(frozen=True, slots=True)
class MediaView:
    asset: MediaAsset
    url: str
    crop_urls: Mapping[ImageFrame, str] = field(default_factory=dict)


def _normalise_type(content_type: str | None) -> str | None:
    if not content_type:
        return None
    base = content_type.split(";", 1)[0].strip().lower()
    return _CONTENT_TYPE_ALIASES.get(base, base)


def _clean_text(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.split())
    return cleaned[:limit] or None


def inspect_upload(
    data: bytes, declared_type: str | None, policy: MediaPolicy, inspector: ImageInspector
) -> tuple[ImageInfo, str]:
    """Shared validation for new uploads and replacements. Returns (info, file extension)."""
    size = len(data)
    if size == 0:
        raise MediaValidationError("The uploaded file is empty.")
    if size > policy.max_bytes:
        raise MediaTooLargeError(f"File is {size} bytes; the limit is {policy.max_bytes} bytes.")
    declared = _normalise_type(declared_type)
    if declared is not None and declared not in policy.allowed_types:
        raise UnsupportedMediaTypeError(f"Unsupported file type: {declared}.")
    info = inspector.inspect(data)  # decodes the actual bytes
    extension = policy.allowed_types.get(info.content_type)
    if extension is None:
        raise UnsupportedMediaTypeError(f"Unsupported image format: {info.content_type}.")
    if declared is not None and declared != info.content_type:
        raise UnsupportedMediaTypeError(
            f"File content is {info.content_type} but was declared as {declared}."
        )
    return info, extension


class MediaUrlResolver:
    def __init__(self, storage: ObjectStorage) -> None:
        self._storage = storage

    def url_for(self, asset: MediaAsset) -> str:
        if asset.visibility is MediaVisibility.PUBLIC:
            return self._storage.public_url(asset.bucket, asset.object_key)
        return self._storage.presigned_url(
            asset.bucket, asset.object_key, expires_in=PRESIGNED_URL_TTL_SECONDS
        )

    def view(self, asset: MediaAsset) -> MediaView:
        return MediaView(
            asset=asset,
            url=self.url_for(asset),
            crop_urls={
                frame: self._storage.public_url(asset.bucket, crop.object_key)
                for frame, crop in asset.crops.items()
            },
        )


class UploadMedia:
    def __init__(
        self,
        *,
        storage: ObjectStorage,
        repository: MediaAssetRepository,
        uow: UnitOfWork,
        inspector: ImageInspector,
        policy: MediaPolicy,
        buckets: Mapping[MediaVisibility, str],
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        new_id: Callable[[], UUID] = uuid4,
    ) -> None:
        self._storage = storage
        self._repository = repository
        self._uow = uow
        self._inspector = inspector
        self._policy = policy
        self._buckets = buckets
        self._clock = clock
        self._new_id = new_id
        self._urls = MediaUrlResolver(storage)

    def execute(self, command: UploadMediaCommand) -> MediaView:
        size = len(command.data)
        info, extension = inspect_upload(
            command.data, command.declared_content_type, self._policy, self._inspector
        )

        asset_id = self._new_id()
        bucket = self._buckets[command.visibility]
        # Immutable, unguessable key per upload: replacing an image means a new key + new row.
        key = f"{command.purpose.value}/{asset_id.hex[:2]}/{asset_id}.{extension}"
        asset = MediaAsset(
            id=asset_id,
            purpose=command.purpose,
            visibility=command.visibility,
            bucket=bucket,
            object_key=key,
            content_type=info.content_type,
            size_bytes=size,
            width=info.width,
            height=info.height,
            sha256=hashlib.sha256(command.data).hexdigest(),
            created_at=self._clock(),
            original_filename=_clean_text(command.original_filename, MAX_FILENAME),
            alt_text=_clean_text(command.alt_text, MAX_ALT_TEXT),
        )

        cache_control = (
            PUBLIC_CACHE_CONTROL
            if command.visibility is MediaVisibility.PUBLIC
            else PRIVATE_CACHE_CONTROL
        )
        self._storage.put(
            bucket, key, command.data, content_type=info.content_type, cache_control=cache_control
        )
        try:
            self._repository.add(asset)
            self._uow.commit()
        except Exception:
            self._uow.rollback()
            self._delete_object_quietly(bucket, key)
            raise

        return self._urls.view(asset)

    def _delete_object_quietly(self, bucket: str, key: str) -> None:
        try:
            self._storage.delete(bucket, key)
        except Exception:
            logger.exception("Failed to remove orphaned object %s/%s", bucket, key)


class GetMedia:
    def __init__(self, *, storage: ObjectStorage, repository: MediaAssetRepository) -> None:
        self._repository = repository
        self._urls = MediaUrlResolver(storage)

    def execute(self, asset_id: UUID, *, public_only: bool = False) -> MediaView:
        asset = self._repository.get(asset_id)
        if asset is None or (public_only and asset.visibility is not MediaVisibility.PUBLIC):
            raise NotFoundError("Media not found.")
        return self._urls.view(asset)


class ListMedia:
    def __init__(self, *, storage: ObjectStorage, repository: MediaAssetRepository) -> None:
        self._repository = repository
        self._urls = MediaUrlResolver(storage)

    def execute(
        self, *, purpose: MediaPurpose | None = None, limit: int = 50, offset: int = 0
    ) -> Sequence[MediaView]:
        assets = self._repository.list(purpose=purpose, limit=limit, offset=offset)
        return [self._urls.view(a) for a in assets]


class DeleteMedia:
    def __init__(
        self, *, storage: ObjectStorage, repository: MediaAssetRepository, uow: UnitOfWork
    ) -> None:
        self._storage = storage
        self._repository = repository
        self._uow = uow

    def execute(self, asset_id: UUID) -> None:
        asset = self._repository.get(asset_id)
        if asset is None:
            raise NotFoundError("Media not found.")
        places = self._repository.usage(asset_id)
        if places:
            raise ConflictError(
                "This image is still in use (" + "; ".join(places[:5]) + "). Remove it there first."
            )
        # Remove the reference first so nothing ever points at a missing object.
        self._repository.delete(asset_id)
        self._uow.commit()
        for key in [asset.object_key, *(crop.object_key for crop in asset.crops.values())]:
            try:
                self._storage.delete(asset.bucket, key)
            except Exception:
                logger.exception(
                    "Media row %s deleted but object %s/%s remains (orphan)",
                    asset_id,
                    asset.bucket,
                    key,
                )


class UpdateMediaDetails:
    def __init__(
        self, *, storage: ObjectStorage, repository: MediaAssetRepository, uow: UnitOfWork
    ) -> None:
        self._repository = repository
        self._uow = uow
        self._urls = MediaUrlResolver(storage)

    def execute(self, asset_id: UUID, *, alt_text: str | None) -> MediaView:
        asset = self._repository.get(asset_id)
        if asset is None:
            raise NotFoundError("Media not found.")
        updated = replace(asset, alt_text=_clean_text(alt_text, MAX_ALT_TEXT))
        self._repository.update(updated)
        self._uow.commit()
        return self._urls.view(updated)

    def usage(self, asset_id: UUID) -> list[str]:
        if self._repository.get(asset_id) is None:
            raise NotFoundError("Media not found.")
        return self._repository.usage(asset_id)


class ReplaceMedia:
    """Swap the file behind an asset while keeping its id, so every reference (products,
    categories, banners, settings) picks up the new image. The new file gets a new immutable
    key, so CDN caches never serve the old bytes. Crops belonged to the old picture, so they are
    cleared and the storefront falls back to a centred crop until the admin crops again."""

    def __init__(
        self,
        *,
        storage: ObjectStorage,
        repository: MediaAssetRepository,
        uow: UnitOfWork,
        inspector: ImageInspector,
        policy: MediaPolicy,
        new_id: Callable[[], UUID] = uuid4,
    ) -> None:
        self._storage = storage
        self._repository = repository
        self._uow = uow
        self._inspector = inspector
        self._policy = policy
        self._new_id = new_id
        self._urls = MediaUrlResolver(storage)

    def execute(
        self,
        asset_id: UUID,
        *,
        data: bytes,
        declared_content_type: str | None,
        filename: str | None,
    ) -> MediaView:
        asset = self._repository.get(asset_id)
        if asset is None:
            raise NotFoundError("Media not found.")
        info, extension = inspect_upload(data, declared_content_type, self._policy, self._inspector)
        suffix = self._new_id().hex[:8]
        key = f"{asset.purpose.value}/{asset.id.hex[:2]}/{asset.id}-{suffix}.{extension}"
        cache_control = (
            PUBLIC_CACHE_CONTROL
            if asset.visibility is MediaVisibility.PUBLIC
            else PRIVATE_CACHE_CONTROL
        )
        self._storage.put(
            asset.bucket, key, data, content_type=info.content_type, cache_control=cache_control
        )
        updated = replace(
            asset,
            object_key=key,
            content_type=info.content_type,
            size_bytes=len(data),
            width=info.width,
            height=info.height,
            sha256=hashlib.sha256(data).hexdigest(),
            original_filename=_clean_text(filename, MAX_FILENAME) or asset.original_filename,
            crops={},
        )
        try:
            self._repository.update(updated)
            self._uow.commit()
        except Exception:
            self._uow.rollback()
            _quiet_delete(self._storage, asset.bucket, key)
            raise
        # The old bytes and their renditions are unreferenced now.
        for old_key in [asset.object_key, *(c.object_key for c in asset.crops.values())]:
            _quiet_delete(self._storage, asset.bucket, old_key)
        return self._urls.view(updated)


class CropMedia:
    """Save the composition for one frame: cut it from the untouched original, store it as an
    optimised WebP under a new immutable key, and remember the rectangle so it can be edited."""

    def __init__(
        self,
        *,
        storage: ObjectStorage,
        repository: MediaAssetRepository,
        uow: UnitOfWork,
        cropper: ImageCropper,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        new_id: Callable[[], UUID] = uuid4,
    ) -> None:
        self._storage = storage
        self._repository = repository
        self._uow = uow
        self._cropper = cropper
        self._clock = clock
        self._new_id = new_id
        self._urls = MediaUrlResolver(storage)

    def execute(self, asset_id: UUID, frame: ImageFrame, rect: CropRect) -> MediaView:
        asset = self._repository.get(asset_id)
        if asset is None:
            raise NotFoundError("Media not found.")
        if asset.visibility is not MediaVisibility.PUBLIC:
            raise MediaValidationError("Only storefront (public) images can be cropped.")
        if not (
            0 <= rect.x < 1 and 0 <= rect.y < 1 and 0 < rect.width <= 1 and 0 < rect.height <= 1
        ):
            raise MediaValidationError("The crop area must lie inside the image.")

        original = self._storage.get(asset.bucket, asset.object_key)
        rendered = self._cropper.render(original.data, rect, FRAME_SPECS[frame])
        suffix = self._new_id().hex[:8]
        key = f"{asset.purpose.value}/{asset.id.hex[:2]}/{asset.id}-{frame.value}-{suffix}.webp"
        self._storage.put(
            asset.bucket,
            key,
            rendered.data,
            content_type=rendered.content_type,
            cache_control=PUBLIC_CACHE_CONTROL,
        )
        crop = ImageCrop(
            rect=rendered.rect,
            object_key=key,
            width=rendered.width,
            height=rendered.height,
            updated_at=self._clock(),
        )
        previous = asset.crops.get(frame)
        updated = replace(asset, crops={**asset.crops, frame: crop})
        try:
            self._repository.update(updated)
            self._uow.commit()
        except Exception:
            self._uow.rollback()
            _quiet_delete(self._storage, asset.bucket, key)
            raise
        if previous is not None:
            _quiet_delete(self._storage, asset.bucket, previous.object_key)
        return self._urls.view(updated)

    def remove(self, asset_id: UUID, frame: ImageFrame) -> MediaView:
        """Forget the crop for ``frame``; the storefront goes back to a centred crop."""
        asset = self._repository.get(asset_id)
        if asset is None:
            raise NotFoundError("Media not found.")
        previous = asset.crops.get(frame)
        if previous is None:
            return self._urls.view(asset)
        updated = replace(asset, crops={f: c for f, c in asset.crops.items() if f is not frame})
        self._repository.update(updated)
        self._uow.commit()
        _quiet_delete(self._storage, asset.bucket, previous.object_key)
        return self._urls.view(updated)


def _quiet_delete(storage: ObjectStorage, bucket: str, key: str) -> None:
    try:
        storage.delete(bucket, key)
    except Exception:
        logger.exception("Failed to remove replaced object %s/%s", bucket, key)
