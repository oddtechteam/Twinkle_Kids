import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import DiscountType, InquiryStatus, ReviewStatus, sql_in
from app.infrastructure.db.base import Base
from app.infrastructure.db.types import (
    JSONType,
    Money,
    UTCDateTime,
    created_at_column,
    updated_at_column,
    uuid_pk,
)


class CouponModel(Base):
    __tablename__ = "coupons"

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(40), unique=True)  # stored upper-case
    description: Mapped[str | None] = mapped_column(String(255))
    discount_type: Mapped[str] = mapped_column(String(16))
    discount_value: Mapped[Decimal] = mapped_column(Money)
    min_order_amount: Mapped[Decimal | None] = mapped_column(Money)
    max_discount_amount: Mapped[Decimal | None] = mapped_column(Money)
    starts_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    ends_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    usage_limit: Mapped[int | None] = mapped_column(Integer)
    per_user_limit: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    # {"product_ids": [...], "category_ids": [...], "collection_ids": [...]}; empty = whole order
    applies_to: Mapped[dict[str, Any]] = mapped_column(
        JSONType, default=dict, server_default=text("'{}'")
    )
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    __table_args__ = (
        CheckConstraint("code = upper(code)", name="code_uppercase"),
        CheckConstraint(f"discount_type IN ({sql_in(DiscountType)})", name="type_valid"),
        CheckConstraint("discount_value > 0", name="value_positive"),
        CheckConstraint(
            "discount_type <> 'percentage' OR discount_value <= 100", name="percentage_lte_100"
        ),
        CheckConstraint(
            "min_order_amount IS NULL OR min_order_amount >= 0", name="min_order_non_negative"
        ),
        CheckConstraint(
            "max_discount_amount IS NULL OR max_discount_amount > 0", name="max_discount_positive"
        ),
        CheckConstraint("usage_limit IS NULL OR usage_limit > 0", name="usage_limit_positive"),
        CheckConstraint(
            "per_user_limit IS NULL OR per_user_limit > 0", name="per_user_limit_positive"
        ),
        CheckConstraint(
            "starts_at IS NULL OR ends_at IS NULL OR ends_at > starts_at", name="window_valid"
        ),
    )


class CouponRedemptionModel(Base):
    __tablename__ = "coupon_redemptions"

    id: Mapped[uuid.UUID] = uuid_pk()
    coupon_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("coupons.id", ondelete="RESTRICT"), index=True
    )
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    discount_amount: Mapped[Decimal] = mapped_column(Money)
    created_at: Mapped[datetime] = created_at_column()

    __table_args__ = (
        UniqueConstraint("order_id", name="uq_coupon_redemptions_order"),  # one coupon per order
        CheckConstraint("discount_amount >= 0", name="amount_non_negative"),
    )


class ReviewModel(Base):
    __tablename__ = "reviews"

    id: Mapped[uuid.UUID] = uuid_pk()
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    order_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("order_items.id", ondelete="SET NULL")
    )
    rating: Mapped[int] = mapped_column(SmallInteger)
    title: Mapped[str | None] = mapped_column(String(120))
    body: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="pending", server_default="pending")
    # True only when the reviewer has a placed (non-cancelled) order containing this product.
    is_verified_purchase: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    author_name: Mapped[str | None] = mapped_column(String(60))
    moderation_note: Mapped[str | None] = mapped_column(String(500))
    moderated_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    moderated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="rating_range"),
        CheckConstraint(f"status IN ({sql_in(ReviewStatus)})", name="status_valid"),
        Index(
            "uq_reviews_one_per_user_product",
            "product_id",
            "user_id",
            unique=True,
            postgresql_where=text("user_id IS NOT NULL"),
            sqlite_where=text("user_id IS NOT NULL"),
        ),
        Index("ix_reviews_product_status", "product_id", "status"),
    )


class ReviewMediaModel(Base):
    """Customer review photos (private bucket; shown only once the review is approved)."""

    __tablename__ = "review_media"

    id: Mapped[uuid.UUID] = uuid_pk()
    review_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reviews.id", ondelete="CASCADE"), index=True
    )
    media_asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("media_assets.id", ondelete="RESTRICT")
    )
    position: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    __table_args__ = (
        UniqueConstraint("review_id", "media_asset_id", name="uq_review_media_review_asset"),
    )


class ShippingRuleModel(Base):
    """Flat-fee rules by order value band; the lowest matching priority wins."""

    __tablename__ = "shipping_rules"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(80))
    min_order_amount: Mapped[Decimal] = mapped_column(Money, default=0, server_default="0")
    max_order_amount: Mapped[Decimal | None] = mapped_column(Money)
    fee: Mapped[Decimal] = mapped_column(Money)
    priority: Mapped[int] = mapped_column(Integer, default=100, server_default="100")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    __table_args__ = (
        CheckConstraint("fee >= 0", name="fee_non_negative"),
        CheckConstraint("min_order_amount >= 0", name="min_non_negative"),
        CheckConstraint(
            "max_order_amount IS NULL OR max_order_amount > min_order_amount", name="band_valid"
        ),
    )


class BulkOrderInquiryModel(Base):
    __tablename__ = "bulk_order_inquiries"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(254))
    phone: Mapped[str] = mapped_column(String(20))
    organisation: Mapped[str | None] = mapped_column(String(160))
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL")
    )
    quantity: Mapped[int | None] = mapped_column(Integer)
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="new", server_default="new")
    staff_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    __table_args__ = (
        CheckConstraint(f"status IN ({sql_in(InquiryStatus)})", name="status_valid"),
        CheckConstraint("quantity IS NULL OR quantity > 0", name="quantity_positive"),
        Index("ix_bulk_order_inquiries_status_created", "status", "created_at"),
    )
