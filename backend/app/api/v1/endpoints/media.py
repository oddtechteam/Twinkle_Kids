from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, Query, Response, UploadFile, status

from app.api.deps import (
    CropMediaDep,
    DeleteMediaDep,
    GetMediaDep,
    ListMediaDep,
    MediaManagerDep,
    ReplaceMediaDep,
    SettingsDep,
    UpdateMediaDep,
    UploadMediaDep,
)
from app.api.schemas.admin import MediaPatchIn
from app.api.schemas.content import MediaUsageOut
from app.api.schemas.media import AdminMediaAssetOut, CropIn, MediaAssetOut
from app.application.use_cases.media import UploadMediaCommand
from app.domain.entities.media import CropRect, ImageFrame, MediaPurpose, MediaVisibility
from app.domain.errors import MediaTooLargeError

public_router = APIRouter(prefix="/media", tags=["media"])
admin_router = APIRouter(prefix="/admin/media", tags=["admin: media"])


@public_router.get("/{asset_id}", response_model=MediaAssetOut)
def get_public_media(asset_id: UUID, use_case: GetMediaDep) -> MediaAssetOut:
    return MediaAssetOut.from_view(use_case.execute(asset_id, public_only=True))


@admin_router.post("", response_model=AdminMediaAssetOut, status_code=status.HTTP_201_CREATED)
def upload_media(
    _: MediaManagerDep,
    use_case: UploadMediaDep,
    settings: SettingsDep,
    file: Annotated[UploadFile, File(description="JPEG, PNG, WebP or AVIF image")],
    purpose: Annotated[MediaPurpose, Form()],
    visibility: Annotated[MediaVisibility, Form()] = MediaVisibility.PUBLIC,
    alt_text: Annotated[str | None, Form(max_length=300)] = None,
) -> AdminMediaAssetOut:
    # Read at most limit+1 bytes so an oversized upload is rejected without buffering it all.
    limit = settings.media_max_upload_bytes
    data = file.file.read(limit + 1)
    if len(data) > limit:
        raise MediaTooLargeError(f"File exceeds the {limit} byte limit.")
    view = use_case.execute(
        UploadMediaCommand(
            data=data,
            purpose=purpose,
            visibility=visibility,
            declared_content_type=file.content_type,
            original_filename=file.filename,
            alt_text=alt_text,
        )
    )
    return AdminMediaAssetOut.from_view(view)


@admin_router.get("", response_model=list[AdminMediaAssetOut])
def list_media(
    _: MediaManagerDep,
    use_case: ListMediaDep,
    purpose: MediaPurpose | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[AdminMediaAssetOut]:
    views = use_case.execute(purpose=purpose, limit=limit, offset=offset)
    return [AdminMediaAssetOut.from_view(v) for v in views]


@admin_router.get("/{asset_id}", response_model=AdminMediaAssetOut)
def get_media(asset_id: UUID, _: MediaManagerDep, use_case: GetMediaDep) -> AdminMediaAssetOut:
    return AdminMediaAssetOut.from_view(use_case.execute(asset_id))


@admin_router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_media(asset_id: UUID, _: MediaManagerDep, use_case: DeleteMediaDep) -> Response:
    use_case.execute(asset_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@admin_router.patch("/{asset_id}", response_model=AdminMediaAssetOut)
def update_media(
    asset_id: UUID, body: MediaPatchIn, _: MediaManagerDep, use_case: UpdateMediaDep
) -> AdminMediaAssetOut:
    return AdminMediaAssetOut.from_view(use_case.execute(asset_id, alt_text=body.alt_text))


@admin_router.get("/{asset_id}/usage", response_model=MediaUsageOut)
def media_usage(asset_id: UUID, _: MediaManagerDep, use_case: UpdateMediaDep) -> MediaUsageOut:
    places = use_case.usage(asset_id)
    return MediaUsageOut(in_use=bool(places), places=places)


@admin_router.post("/{asset_id}/replace", response_model=AdminMediaAssetOut)
def replace_media(
    asset_id: UUID,
    _: MediaManagerDep,
    use_case: ReplaceMediaDep,
    settings: SettingsDep,
    file: Annotated[UploadFile, File(description="JPEG, PNG, WebP or AVIF image")],
) -> AdminMediaAssetOut:
    """Swap the file but keep the asset id, so every reference shows the new image."""
    limit = settings.media_max_upload_bytes
    data = file.file.read(limit + 1)
    if len(data) > limit:
        raise MediaTooLargeError(f"File exceeds the {limit} byte limit.")
    view = use_case.execute(
        asset_id, data=data, declared_content_type=file.content_type, filename=file.filename
    )
    return AdminMediaAssetOut.from_view(view)


@admin_router.put("/{asset_id}/crops/{frame}", response_model=AdminMediaAssetOut)
def save_crop(
    asset_id: UUID, frame: ImageFrame, body: CropIn, _: MediaManagerDep, use_case: CropMediaDep
) -> AdminMediaAssetOut:
    """Cut the frame's composition from the original (which is kept) and store it as WebP."""
    rect = CropRect(x=body.x, y=body.y, width=body.width, height=body.height)
    return AdminMediaAssetOut.from_view(use_case.execute(asset_id, frame, rect))


@admin_router.delete("/{asset_id}/crops/{frame}", response_model=AdminMediaAssetOut)
def remove_crop(
    asset_id: UUID, frame: ImageFrame, _: MediaManagerDep, use_case: CropMediaDep
) -> AdminMediaAssetOut:
    return AdminMediaAssetOut.from_view(use_case.remove(asset_id, frame))
