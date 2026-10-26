"""Customer review submission (signed-in customers; moderated before anything is shown)."""

from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile, status

from app.api.deps import (
    CatalogReaderDep,
    CurrentUserDep,
    ReviewServiceDep,
    SettingsDep,
    UploadMediaDep,
)
from app.application.use_cases.media import UploadMediaCommand
from app.application.use_cases.reviews import MAX_REVIEW_IMAGES
from app.domain.entities.media import MediaPurpose, MediaVisibility
from app.domain.errors import DomainValidationError, MediaTooLargeError

router = APIRouter(tags=["reviews"])


@router.post("/products/{slug}/reviews", status_code=status.HTTP_201_CREATED)
def submit_review(
    slug: str,
    user: CurrentUserDep,
    reader: CatalogReaderDep,
    reviews: ReviewServiceDep,
    upload: UploadMediaDep,
    settings: SettingsDep,
    rating: Annotated[int, Form(ge=1, le=5)],
    title: Annotated[str | None, Form(max_length=120)] = None,
    body: Annotated[str | None, Form(max_length=2000)] = None,
    photos: Annotated[
        list[UploadFile] | None, File(description="Up to 3 JPEG/PNG/WebP/AVIF images")
    ] = None,
) -> dict[str, str]:
    """The review is stored as pending and appears only after the shop approves it. Photos are
    validated from their bytes and kept private until then."""
    files = [f for f in (photos or []) if f.filename]
    if len(files) > MAX_REVIEW_IMAGES:
        raise DomainValidationError(f"Add up to {MAX_REVIEW_IMAGES} photos.")
    product = reader.product(slug)
    draft = reviews.prepare(user, product.id, rating=rating, title=title, body=body)
    media_ids = []
    limit = settings.media_max_upload_bytes
    for file in files:
        data = file.file.read(limit + 1)
        if len(data) > limit:
            raise MediaTooLargeError(f"Each photo must be under {limit // (1024 * 1024)} MB.")
        view = upload.execute(
            UploadMediaCommand(
                data=data,
                purpose=MediaPurpose.REVIEW_IMAGE,
                visibility=MediaVisibility.PRIVATE,
                declared_content_type=file.content_type,
                original_filename=None,  # never keep customer file names
                alt_text=f"Customer photo of {product.name}",
            )
        )
        media_ids.append(view.asset.id)
    reviews.submit(user, draft, media_ids)
    return {"detail": "Thank you! Your review will appear once the shop has approved it."}
