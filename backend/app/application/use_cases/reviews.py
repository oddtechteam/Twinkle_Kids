"""Customer reviews with moderation.

* Only signed-in customers can review; one review per customer per product.
* Every review starts `pending` and is invisible until staff approve it. Staff can hide an
  approved review again (status `rejected`) with a note.
* "Verified purchase" is set only when the reviewer has a placed, non-cancelled order that
  contains the product — never by hand.
* Photos are validated by the media pipeline, stored privately, and shown (as short-lived
  links) only on approved reviews. No review or count is ever generated.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from app.application.dto.catalog import ImageView, Page
from app.domain.entities.identity import User
from app.domain.enums import ProductStatus, ReviewStatus
from app.domain.errors import ConflictError, DomainValidationError, NotFoundError
from app.domain.repositories.catalog import ProductRepository
from app.domain.repositories.identity import AuditLogRepository
from app.domain.repositories.media import UnitOfWork

MAX_REVIEW_IMAGES = 3


@dataclass(frozen=True, slots=True)
class NewReview:
    id: UUID
    product_id: UUID
    user_id: UUID
    rating: int
    title: str | None
    body: str | None
    author_name: str
    is_verified_purchase: bool
    media_ids: list[UUID]


@dataclass(frozen=True, slots=True)
class ModerationItem:
    id: UUID
    product_id: UUID
    product_name: str
    product_slug: str
    rating: int
    title: str | None
    body: str | None
    author_name: str | None
    author_email: str | None
    is_verified_purchase: bool
    status: ReviewStatus
    moderation_note: str | None
    images: list[ImageView]
    created_at: datetime


class ReviewStore(Protocol):
    def has_review(self, user_id: UUID, product_id: UUID) -> bool: ...

    def has_purchased(self, user_id: UUID, product_id: UUID) -> bool: ...

    def add(self, review: NewReview) -> None: ...

    def moderation(
        self, *, status: ReviewStatus | None, page: int, page_size: int
    ) -> Page[ModerationItem]: ...

    def status(self, review_id: UUID) -> ReviewStatus | None: ...

    def set_status(
        self,
        review_id: UUID,
        status: ReviewStatus,
        *,
        note: str | None,
        actor_id: UUID,
        at: datetime,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class ReviewDraft:
    product_id: UUID
    rating: int
    title: str | None
    body: str | None


class ReviewService:
    def __init__(
        self,
        *,
        store: ReviewStore,
        products: ProductRepository,
        audit: AuditLogRepository,
        uow: UnitOfWork,
    ) -> None:
        self._store = store
        self._products = products
        self._audit = audit
        self._uow = uow

    def prepare(
        self,
        user: User,
        product_id: UUID | None,
        *,
        rating: int,
        title: str | None,
        body: str | None,
    ) -> ReviewDraft:
        """Validate before any photo is uploaded, so a rejected review stores no files."""
        product = self._products.get(product_id) if product_id else None
        if product is None or product.status is not ProductStatus.ACTIVE:
            raise NotFoundError("Product not found.")
        if not 1 <= rating <= 5:
            raise DomainValidationError("Choose a rating from 1 to 5 stars.")
        title = (title or "").strip() or None
        body = (body or "").strip() or None
        if title and len(title) > 120:
            raise DomainValidationError("Keep the title under 120 characters.")
        if body and len(body) > 2000:
            raise DomainValidationError("Keep your review under 2000 characters.")
        if not title and not body:
            raise DomainValidationError("Add a few words about the product.")
        if self._store.has_review(user.id, product.id):
            raise ConflictError("You've already reviewed this product.")
        return ReviewDraft(product_id=product.id, rating=rating, title=title, body=body)

    def submit(self, user: User, draft: ReviewDraft, media_ids: list[UUID]) -> UUID:
        if len(media_ids) > MAX_REVIEW_IMAGES:
            raise DomainValidationError(f"Add up to {MAX_REVIEW_IMAGES} photos.")
        review = NewReview(
            id=uuid4(),
            product_id=draft.product_id,
            user_id=user.id,
            rating=draft.rating,
            title=draft.title,
            body=draft.body,
            author_name=(user.full_name.split(" ")[0] or "Customer")[:60],
            is_verified_purchase=self._store.has_purchased(user.id, draft.product_id),
            media_ids=media_ids,
        )
        self._store.add(review)
        self._uow.commit()
        return review.id

    def moderation(self, *, status: ReviewStatus | None, page: int) -> Page[ModerationItem]:
        return self._store.moderation(status=status, page=max(1, page), page_size=25)

    def moderate(
        self, review_id: UUID, status: ReviewStatus, *, note: str | None, actor: User
    ) -> None:
        current = self._store.status(review_id)
        if current is None:
            raise NotFoundError("Review not found.")
        if status is ReviewStatus.PENDING:
            raise DomainValidationError("Approve (publish) or reject (hide) the review.")
        note = (note or "").strip() or None
        if note and len(note) > 500:
            raise DomainValidationError("Notes can be up to 500 characters.")
        self._store.set_status(
            review_id, status, note=note, actor_id=actor.id, at=datetime.now(UTC)
        )
        self._audit.record(
            actor_user_id=actor.id,
            action="review.approved" if status is ReviewStatus.APPROVED else "review.hidden",
            entity_type="review",
            entity_id=str(review_id),
            changes={"from": current.value, "to": status.value},
        )
        self._uow.commit()
