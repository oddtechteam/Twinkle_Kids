"""Media crops: per-frame crop settings and the cropped rendition's key for each media asset.

The original file is untouched; each crop is stored as a separate optimised object.

Additive only (one defaulted column).

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    with op.batch_alter_table("media_assets") as batch:
        batch.add_column(
            sa.Column("crops", JSON, server_default=sa.text("'{}'"), nullable=False)
        )


def downgrade() -> None:
    with op.batch_alter_table("media_assets") as batch:
        batch.drop_column("crops")
