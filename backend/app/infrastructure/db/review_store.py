"""SQLAlchemy ReviewStore: submissions, verified-purchase lookup and the moderation queue."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.application.dto.catalog import ImageView, Page
from app.application.use_cases.reviews import ModerationItem, NewReview
from app.domain.enums import OrderStatus, ReviewStatus
from app.domain.repositories.media import ObjectStorage
from app.infrastructure.db.models.catalog import ProductModel
from app.infrastructure.db.models.commerce import OrderItemModel, OrderModel
from app.infrastructure.db.models.identity import UserModel
from app.infrastructure.db.models.marketing import ReviewMediaModel, ReviewModel
from app.infrastructure.db.models.media import MediaAssetModel


def review_images(
    session: Session, storage: ObjectStorage, review_ids: list[UUID]
) -> dict[UUID, list[ImageView]]:
    """Short-lived links to review photos (private bucket), grouped by review."""
    if not review_ids:
        return {}
    rows = session.execute(
        select(ReviewMediaModel.review_id, MediaAssetModel)
        .join(MediaAssetModel, MediaAssetModel.id == ReviewMediaModel.media_asset_id)
        .where(ReviewMediaModel.review_id.in_(review_ids))
        .order_by(ReviewMediaModel.position)
    ).all()
    out: dict[UUID, list[ImageView]] = {}
    for review_id, asset in rows:
        url = (
            storage.public_url(asset.bucket, asset.object_key)
            if asset.visibility == "public"
            else storage.presigned_url(asset.bucket, asset.object_key, expires_in=900)
        )
        out.setdefault(review_id, []).append(
            ImageView(
                media_asset_id=asset.id,
                url=url,
                alt_text=asset.alt_text or "Customer photo",
                width=asset.width,
                height=asset.height,
            )
        )
    return out


class SqlAlchemyReviewStore:
    def __init__(self, session: Session, storage: ObjectStorage) -> None:
        self._session = session
        self._storage = storage

    def has_review(self, user_id: UUID, product_id: UUID) -> bool:
        return (
            self._session.scalar(
                select(ReviewModel.id).where(
                    ReviewModel.user_id == user_id, ReviewModel.product_id == product_id
                )
            )
            is not None
        )

    def has_purchased(self, user_id: UUID, product_id: UUID) -> bool:
        return (
            self._session.scalar(
                select(OrderItemModel.id)
                .join(OrderModel, OrderModel.id == OrderItemModel.order_id)
                .where(
                    OrderModel.user_id == user_id,
                    OrderItemModel.product_id == product_id,
                    OrderModel.status != OrderStatus.CANCELLED.value,
                )
                .limit(1)
            )
            is not None
        )

    def add(self, review: NewReview) -> None:
        self._session.add(
            ReviewModel(
                id=review.id,
                product_id=review.product_id,
                user_id=review.user_id,
                rating=review.rating,
                title=review.title,
                body=review.body,
                author_name=review.author_name,
                is_verified_purchase=review.is_verified_purchase,
                status=ReviewStatus.PENDING.value,
            )
        )
        self._session.flush()
        for position, media_id in enumerate(review.media_ids):
            self._session.add(
                ReviewMediaModel(
                    id=uuid4(), review_id=review.id, media_asset_id=media_id, position=position
                )
            )

    def moderation(
        self, *, status: ReviewStatus | None, page: int, page_size: int
    ) -> Page[ModerationItem]:
        stmt = (
            select(ReviewModel, ProductModel.name, ProductModel.slug, UserModel.email)
            .join(ProductModel, ProductModel.id == ReviewModel.product_id)
            .outerjoin(UserModel, UserModel.id == ReviewModel.user_id)
        )
        if status is not None:
            stmt = stmt.where(ReviewModel.status == status.value)
        total = self._session.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = self._session.execute(
            stmt.order_by(ReviewModel.created_at.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        ).all()
        images = review_images(self._session, self._storage, [r.id for r, *_ in rows])
        return Page(
            items=[
                ModerationItem(
                    id=r.id,
                    product_id=r.product_id,
                    product_name=name,
                    product_slug=slug,
                    rating=r.rating,
                    title=r.title,
                    body=r.body,
                    author_name=r.author_name,
                    author_email=email,
                    is_verified_purchase=r.is_verified_purchase,
                    status=ReviewStatus(r.status),
                    moderation_note=r.moderation_note,
                    images=images.get(r.id, []),
                    created_at=r.created_at,
                )
                for r, name, slug, email in rows
            ],
            total=int(total or 0),
            page=page,
            page_size=page_size,
        )

    def status(self, review_id: UUID) -> ReviewStatus | None:
        value = self._session.scalar(select(ReviewModel.status).where(ReviewModel.id == review_id))
        return ReviewStatus(value) if value else None

    def set_status(
        self,
        review_id: UUID,
        status: ReviewStatus,
        *,
        note: str | None,
        actor_id: UUID,
        at: datetime,
    ) -> None:
        self._session.execute(
            update(ReviewModel)
            .where(ReviewModel.id == review_id)
            .values(
                status=status.value, moderation_note=note, moderated_by=actor_id, moderated_at=at
            )
        )
