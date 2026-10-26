"""Store operations: coupon targeting, shipping & order policies, after-sale requests, review
moderation & images, recommendations, notification log and new homepage selection modes.

Additive only (new tables, new defaulted columns, widened CHECK lists).

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")
NOW = sa.text("CURRENT_TIMESTAMP")
SELECTION_V1 = "'none','manual','category','collection','newest'"
SELECTION_V2 = "'none','manual','category','collection','newest','bestsellers','featured'"
PURPOSE_V1 = "'product_image','category_image','collection_image','homepage_banner','content_image'"
PURPOSE_V2 = PURPOSE_V1 + ",'review_image'"


def upgrade() -> None:
    with op.batch_alter_table("coupons") as batch:
        batch.add_column(
            sa.Column("applies_to", JSON, server_default=sa.text("'{}'"), nullable=False)
        )

    with op.batch_alter_table("media_assets") as batch:
        batch.drop_constraint(op.f("ck_media_assets_purpose_valid"), type_="check")
        batch.create_check_constraint(
            op.f("ck_media_assets_purpose_valid"), f"purpose IN ({PURPOSE_V2})"
        )

    with op.batch_alter_table("store_settings") as batch:
        batch.add_column(
            sa.Column("shipping_settings", JSON, server_default=sa.text("'{}'"), nullable=False)
        )
        batch.add_column(
            sa.Column("order_policies", JSON, server_default=sa.text("'{}'"), nullable=False)
        )

    with op.batch_alter_table("products") as batch:
        batch.add_column(
            sa.Column("is_featured", sa.Boolean(), server_default=sa.text("false"), nullable=False)
        )
        batch.add_column(
            sa.Column("related_product_ids", JSON, server_default=sa.text("'[]'"), nullable=False)
        )

    with op.batch_alter_table("reviews") as batch:
        batch.add_column(
            sa.Column(
                "is_verified_purchase",
                sa.Boolean(),
                server_default=sa.text("false"),
                nullable=False,
            )
        )
        batch.add_column(sa.Column("author_name", sa.String(length=60), nullable=True))
        batch.add_column(sa.Column("moderation_note", sa.String(length=500), nullable=True))
        batch.add_column(sa.Column("moderated_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("moderated_by", sa.Uuid(), nullable=True))
        batch.create_foreign_key(
            op.f("fk_reviews_moderated_by_users"),
            "users",
            ["moderated_by"],
            ["id"],
            ondelete="SET NULL",
        )

    op.create_table(
        "review_media",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("review_id", sa.Uuid(), nullable=False),
        sa.Column("media_asset_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(
            ["review_id"],
            ["reviews.id"],
            name=op.f("fk_review_media_review_id_reviews"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["media_asset_id"],
            ["media_assets.id"],
            name=op.f("fk_review_media_media_asset_id_media_assets"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_review_media")),
        sa.UniqueConstraint(
            "review_id", "media_asset_id", name=op.f("uq_review_media_review_asset")
        ),
    )
    op.create_index(op.f("ix_review_media_review_id"), "review_media", ["review_id"])

    op.create_table(
        "order_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reference", sa.String(length=24), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="requested", nullable=False),
        sa.Column("reason", sa.String(length=40), nullable=False),
        sa.Column("customer_message", sa.Text(), nullable=True),
        sa.Column("items", JSON, server_default=sa.text("'[]'"), nullable=False),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("refund_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("restocked", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_by_staff", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.CheckConstraint(
            "kind IN ('cancellation','return','exchange')",
            name=op.f("ck_order_requests_kind_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('requested','approved','rejected','received','completed')",
            name=op.f("ck_order_requests_status_valid"),
        ),
        sa.CheckConstraint(
            "refund_amount IS NULL OR refund_amount >= 0",
            name=op.f("ck_order_requests_refund_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            name=op.f("fk_order_requests_order_id_orders"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_order_requests_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_order_requests")),
        sa.UniqueConstraint("reference", name=op.f("uq_order_requests_reference")),
    )
    op.create_index(op.f("ix_order_requests_order_id"), "order_requests", ["order_id"])
    op.create_index("ix_order_requests_status_created", "order_requests", ["status", "created_at"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("template", sa.String(length=40), nullable=False),
        sa.Column("recipient", sa.String(length=254), nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=True),
        sa.Column("provider_message_id", sa.String(length=200), nullable=True),
        sa.Column("error", sa.String(length=300), nullable=True),
        sa.Column("entity_type", sa.String(length=40), nullable=True),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.CheckConstraint(
            "channel IN ('email','whatsapp')", name=op.f("ck_notifications_channel_valid")
        ),
        sa.CheckConstraint(
            "status IN ('sent','failed','skipped')", name=op.f("ck_notifications_status_valid")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notifications")),
    )
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])

    with op.batch_alter_table("homepage_sections") as batch:
        batch.drop_constraint(op.f("ck_homepage_sections_selection_valid"), type_="check")
        batch.create_check_constraint(
            op.f("ck_homepage_sections_selection_valid"), f"selection_mode IN ({SELECTION_V2})"
        )


def downgrade() -> None:
    op.execute(
        "UPDATE homepage_sections SET selection_mode = 'manual' "
        "WHERE selection_mode IN ('bestsellers','featured')"
    )
    with op.batch_alter_table("homepage_sections") as batch:
        batch.drop_constraint(op.f("ck_homepage_sections_selection_valid"), type_="check")
        batch.create_check_constraint(
            op.f("ck_homepage_sections_selection_valid"), f"selection_mode IN ({SELECTION_V1})"
        )
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_order_requests_status_created", table_name="order_requests")
    op.drop_index(op.f("ix_order_requests_order_id"), table_name="order_requests")
    op.drop_table("order_requests")
    op.drop_index(op.f("ix_review_media_review_id"), table_name="review_media")
    op.drop_table("review_media")
    with op.batch_alter_table("reviews") as batch:
        batch.drop_constraint(op.f("fk_reviews_moderated_by_users"), type_="foreignkey")
        for column in (
            "moderated_by",
            "moderated_at",
            "moderation_note",
            "author_name",
            "is_verified_purchase",
        ):
            batch.drop_column(column)
    with op.batch_alter_table("products") as batch:
        batch.drop_column("related_product_ids")
        batch.drop_column("is_featured")
    with op.batch_alter_table("store_settings") as batch:
        batch.drop_column("order_policies")
        batch.drop_column("shipping_settings")
    op.execute("DELETE FROM media_assets WHERE purpose = 'review_image'")
    with op.batch_alter_table("media_assets") as batch:
        batch.drop_constraint(op.f("ck_media_assets_purpose_valid"), type_="check")
        batch.create_check_constraint(
            op.f("ck_media_assets_purpose_valid"), f"purpose IN ({PURPOSE_V1})"
        )
    with op.batch_alter_table("coupons") as batch:
        batch.drop_column("applies_to")
