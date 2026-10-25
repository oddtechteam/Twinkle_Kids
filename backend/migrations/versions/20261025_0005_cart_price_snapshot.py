"""Cart price snapshot: the selling price a shopper saw when adding an item.

Used only to tell the shopper that a price has changed since they added the item. Totals are
always recalculated from current catalogue prices; the snapshot is never charged.

Additive only (one nullable column).

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("cart_items") as batch:
        batch.add_column(sa.Column("unit_price_snapshot", sa.Numeric(12, 2), nullable=True))
        batch.create_check_constraint(
            op.f("ck_cart_items_unit_price_snapshot_non_negative"),
            "unit_price_snapshot IS NULL OR unit_price_snapshot >= 0",
        )


def downgrade() -> None:
    with op.batch_alter_table("cart_items") as batch:
        batch.drop_constraint(op.f("ck_cart_items_unit_price_snapshot_non_negative"), type_="check")
        batch.drop_column("unit_price_snapshot")
