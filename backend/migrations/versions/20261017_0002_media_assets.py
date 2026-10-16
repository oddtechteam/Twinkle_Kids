"""Media assets: metadata + object-storage references for website images.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "media_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("visibility", sa.String(length=16), nullable=False),
        sa.Column("bucket", sa.String(length=63), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=True),
        sa.Column("alt_text", sa.String(length=300), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()") if op.get_context().dialect.name != "sqlite"
            else sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "purpose IN ('product_image','category_image','collection_image',"
            "'homepage_banner','content_image')",
            name=op.f("ck_media_assets_purpose_valid"),
        ),
        sa.CheckConstraint(
            "visibility IN ('public','private')", name=op.f("ck_media_assets_visibility_valid")
        ),
        sa.CheckConstraint("size_bytes > 0", name=op.f("ck_media_assets_size_positive")),
        sa.CheckConstraint(
            "width > 0 AND height > 0", name=op.f("ck_media_assets_dimensions_positive")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_media_assets")),
        sa.UniqueConstraint(
            "bucket", "object_key", name=op.f("uq_media_assets_bucket_object_key")
        ),
    )
    op.create_index(
        "ix_media_assets_purpose_created_at", "media_assets", ["purpose", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_media_assets_purpose_created_at", table_name="media_assets")
    op.drop_table("media_assets")
