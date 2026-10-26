"""Customer accounts & checkout: password-reset tokens and idempotent order submission.

* password_reset_tokens — single-use, hashed, short-lived tokens (raw token only in the email).
* orders.idempotency_key — hash of (owner, client key); unique, so a resubmitted checkout can
  never create a second order or deduct stock twice.

Additive only.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_ip", sa.String(length=45), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_password_reset_tokens_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_password_reset_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_password_reset_tokens_token_hash")),
    )
    op.create_index(
        op.f("ix_password_reset_tokens_user_id"), "password_reset_tokens", ["user_id"]
    )

    with op.batch_alter_table("orders") as batch:
        batch.add_column(sa.Column("idempotency_key", sa.String(length=64), nullable=True))
        batch.create_unique_constraint(op.f("uq_orders_idempotency_key"), ["idempotency_key"])


def downgrade() -> None:
    with op.batch_alter_table("orders") as batch:
        batch.drop_constraint(op.f("uq_orders_idempotency_key"), type_="unique")
        batch.drop_column("idempotency_key")
    op.drop_index(op.f("ix_password_reset_tokens_user_id"), table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
