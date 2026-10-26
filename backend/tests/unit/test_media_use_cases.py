import hashlib
from collections.abc import Sequence
from uuid import UUID

import pytest

from app.application.use_cases.media import (
    PUBLIC_CACHE_CONTROL,
    DeleteMedia,
    GetMedia,
    MediaPolicy,
    UploadMedia,
    UploadMediaCommand,
)
from app.domain.entities.media import MediaAsset, MediaPurpose, MediaVisibility
from app.domain.errors import (
    MediaTooLargeError,
    MediaValidationError,
    NotFoundError,
    UnsupportedMediaTypeError,
)
from app.infrastructure.storage.image_inspector import PillowImageInspector
from app.infrastructure.storage.memory import InMemoryObjectStorage
from tests.conftest import make_image

BUCKETS = {MediaVisibility.PUBLIC: "media", MediaVisibility.PRIVATE: "assets"}


class FakeRepo:
    def __init__(self, *, fail_on_add: bool = False) -> None:
        self.rows: dict[UUID, MediaAsset] = {}
        self.fail_on_add = fail_on_add

    def add(self, asset: MediaAsset) -> None:
        if self.fail_on_add:
            raise RuntimeError("db down")
        self.rows[asset.id] = asset

    def get(self, asset_id: UUID) -> MediaAsset | None:
        return self.rows.get(asset_id)

    def delete(self, asset_id: UUID) -> None:
        self.rows.pop(asset_id, None)

    def existing_ids(self, ids: object) -> set[UUID]:
        return set(self.rows) & set(ids)  # type: ignore[call-overload]

    def in_use(self, asset_id: UUID) -> bool:
        return False

    def usage(self, asset_id: UUID) -> list[str]:
        return []

    def list(
        self, *, purpose: MediaPurpose | None, limit: int, offset: int
    ) -> Sequence[MediaAsset]:
        return list(self.rows.values())[offset : offset + limit]


class FakeUow:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


class RecordingStorage(InMemoryObjectStorage):
    def __init__(self) -> None:
        super().__init__()
        self.cache_controls: dict[tuple[str, str], str] = {}

    def put(
        self, bucket: str, key: str, data: bytes, *, content_type: str, cache_control: str
    ) -> None:
        self.cache_controls[(bucket, key)] = cache_control
        super().put(bucket, key, data, content_type=content_type, cache_control=cache_control)


@pytest.fixture
def storage() -> RecordingStorage:
    return RecordingStorage()


@pytest.fixture
def repo() -> FakeRepo:
    return FakeRepo()


@pytest.fixture
def uow() -> FakeUow:
    return FakeUow()


def uploader(
    storage: InMemoryObjectStorage, repo: FakeRepo, uow: FakeUow, max_bytes: int = 1_000_000
) -> UploadMedia:
    return UploadMedia(
        storage=storage,
        repository=repo,
        uow=uow,
        inspector=PillowImageInspector(),
        policy=MediaPolicy(max_bytes=max_bytes),
        buckets=BUCKETS,
    )


def test_upload_stores_object_and_row(
    storage: RecordingStorage, repo: FakeRepo, uow: FakeUow
) -> None:
    png = make_image("PNG", (40, 30))
    view = uploader(storage, repo, uow).execute(
        UploadMediaCommand(
            data=png,
            purpose=MediaPurpose.PRODUCT_IMAGE,
            declared_content_type="image/png",
            original_filename="  dress   front.png ",
            alt_text="Blush party dress",
        )
    )

    asset = view.asset
    assert repo.rows[asset.id] == asset
    assert uow.commits == 1
    assert asset.bucket == "media"
    assert asset.object_key == f"product_image/{asset.id.hex[:2]}/{asset.id}.png"
    assert (asset.content_type, asset.width, asset.height) == ("image/png", 40, 30)
    assert asset.size_bytes == len(png)
    assert asset.sha256 == hashlib.sha256(png).hexdigest()
    assert asset.original_filename == "dress front.png"
    assert storage.get("media", asset.object_key).data == png
    assert storage.cache_controls[("media", asset.object_key)] == PUBLIC_CACHE_CONTROL
    assert view.url == f"memory://storage/media/{asset.object_key}"


def test_private_upload_goes_to_private_bucket_with_presigned_url(
    storage: RecordingStorage, repo: FakeRepo, uow: FakeUow
) -> None:
    view = uploader(storage, repo, uow).execute(
        UploadMediaCommand(
            data=make_image("JPEG"),
            purpose=MediaPurpose.CONTENT_IMAGE,
            visibility=MediaVisibility.PRIVATE,
        )
    )
    assert view.asset.bucket == "assets"
    assert view.asset.content_type == "image/jpeg"
    assert "expires_in=" in view.url


@pytest.mark.parametrize("fmt", ["WEBP", "JPEG", "PNG"])
def test_supported_formats(
    fmt: str, storage: RecordingStorage, repo: FakeRepo, uow: FakeUow
) -> None:
    view = uploader(storage, repo, uow).execute(
        UploadMediaCommand(data=make_image(fmt), purpose=MediaPurpose.HOMEPAGE_BANNER)
    )
    assert view.asset.content_type == f"image/{fmt.lower()}"


@pytest.mark.parametrize(
    ("data", "declared", "error"),
    [
        (b"", None, MediaValidationError),
        (make_image("PNG"), "image/svg+xml", UnsupportedMediaTypeError),
        (make_image("PNG"), "image/jpeg", UnsupportedMediaTypeError),  # declared ≠ actual
        (b"<svg xmlns='http://www.w3.org/2000/svg'/>", None, UnsupportedMediaTypeError),
        (b"MZ\x90\x00 definitely not an image", "image/png", UnsupportedMediaTypeError),
        (make_image("GIF"), None, UnsupportedMediaTypeError),
        (make_image("PNG", (64, 64))[:60], "image/png", MediaValidationError),  # truncated
    ],
    ids=["empty", "svg-declared", "type-mismatch", "svg-bytes", "exe", "gif", "truncated"],
)
def test_rejects_invalid_uploads(
    data: bytes,
    declared: str | None,
    error: type[Exception],
    storage: RecordingStorage,
    repo: FakeRepo,
    uow: FakeUow,
) -> None:
    with pytest.raises(error):
        uploader(storage, repo, uow).execute(
            UploadMediaCommand(
                data=data, purpose=MediaPurpose.PRODUCT_IMAGE, declared_content_type=declared
            )
        )
    assert len(storage) == 0
    assert repo.rows == {}


def test_rejects_oversized_upload(storage: RecordingStorage, repo: FakeRepo, uow: FakeUow) -> None:
    with pytest.raises(MediaTooLargeError):
        uploader(storage, repo, uow, max_bytes=10).execute(
            UploadMediaCommand(data=make_image(), purpose=MediaPurpose.PRODUCT_IMAGE)
        )


def test_failed_db_write_removes_uploaded_object(storage: RecordingStorage, uow: FakeUow) -> None:
    repo = FakeRepo(fail_on_add=True)
    with pytest.raises(RuntimeError):
        uploader(storage, repo, uow).execute(
            UploadMediaCommand(data=make_image(), purpose=MediaPurpose.PRODUCT_IMAGE)
        )
    assert uow.rollbacks == 1
    assert len(storage) == 0


def test_get_hides_private_assets_from_public_lookups(
    storage: RecordingStorage, repo: FakeRepo, uow: FakeUow
) -> None:
    view = uploader(storage, repo, uow).execute(
        UploadMediaCommand(
            data=make_image(),
            purpose=MediaPurpose.CONTENT_IMAGE,
            visibility=MediaVisibility.PRIVATE,
        )
    )
    get = GetMedia(storage=storage, repository=repo)
    assert get.execute(view.asset.id).asset == view.asset
    with pytest.raises(NotFoundError):
        get.execute(view.asset.id, public_only=True)


def test_delete_removes_row_then_object(
    storage: RecordingStorage, repo: FakeRepo, uow: FakeUow
) -> None:
    view = uploader(storage, repo, uow).execute(
        UploadMediaCommand(data=make_image(), purpose=MediaPurpose.CATEGORY_IMAGE)
    )
    DeleteMedia(storage=storage, repository=repo, uow=uow).execute(view.asset.id)

    assert repo.rows == {}
    assert not storage.exists("media", view.asset.object_key)
    with pytest.raises(NotFoundError):
        DeleteMedia(storage=storage, repository=repo, uow=uow).execute(view.asset.id)
