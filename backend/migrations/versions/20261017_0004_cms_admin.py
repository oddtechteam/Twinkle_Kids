"""CMS & admin: homepage publications, extended section types, store settings, product badges.

Additive only: new table, new nullable/defaulted columns and widened CHECK lists. No data is
removed. Batch mode keeps the migration portable (direct ALTERs on PostgreSQL, table copy on
SQLite).

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")

SECTION_TYPES_V1 = (
    "'hero_banner','product_carousel','product_grid','category_grid',"
    "'collection_showcase','promo_banner','rich_text'"
)
SECTION_TYPES_V2 = (
    "'hero_banner','category_grid','product_carousel','product_grid','editorial_banner',"
    "'promo_banner','collection_showcase','occasion_collection','trust_strip','testimonials',"
    "'faq','announcement','contact','rich_text'"
)
LINK_TYPES_V1 = "'category','collection','page','url'"
LINK_TYPES_V2 = "'category','collection','page','url','heading'"
SORTS = "'featured','newest','price_asc','price_desc','name_asc'"


def upgrade() -> None:
    op.create_table(
        "homepage_publications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("snapshot", JSON, nullable=False),
        sa.Column("published_by", sa.Uuid(), nullable=True),
        sa.Column("note", sa.String(length=200), nullable=True),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["published_by"],
            ["users.id"],
            name=op.f("fk_homepage_publications_published_by_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_homepage_publications")),
    )
    op.create_index(
        "ix_homepage_publications_published_at", "homepage_publications", ["published_at"]
    )

    with op.batch_alter_table("products") as batch:
        batch.add_column(sa.Column("badges", JSON, server_default=sa.text("'[]'"), nullable=False))

    with op.batch_alter_table("homepage_sections") as batch:
        batch.drop_constraint(op.f("ck_homepage_sections_type_valid"), type_="check")
        batch.create_check_constraint(
            op.f("ck_homepage_sections_type_valid"), f"section_type IN ({SECTION_TYPES_V2})"
        )

    with op.batch_alter_table("navigation_items") as batch:
        batch.drop_constraint(op.f("ck_navigation_items_link_type_valid"), type_="check")
        batch.create_check_constraint(
            op.f("ck_navigation_items_link_type_valid"), f"link_type IN ({LINK_TYPES_V2})"
        )

    with op.batch_alter_table("store_settings") as batch:
        batch.add_column(sa.Column("logo_media_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("favicon_media_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("theme", JSON, server_default=sa.text("'{}'"), nullable=False))
        batch.add_column(
            sa.Column("announcement", JSON, server_default=sa.text("'{}'"), nullable=False)
        )
        batch.add_column(sa.Column("business_hours", sa.String(length=120), nullable=True))
        batch.add_column(
            sa.Column(
                "default_product_sort",
                sa.String(length=16),
                server_default="featured",
                nullable=False,
            )
        )
        batch.add_column(sa.Column("whatsapp_message_template", sa.Text(), nullable=True))
        batch.add_column(
            sa.Column("payment_options", JSON, server_default=sa.text("'[]'"), nullable=False)
        )
        batch.add_column(
            sa.Column("seo_defaults", JSON, server_default=sa.text("'{}'"), nullable=False)
        )
        batch.create_foreign_key(
            op.f("fk_store_settings_logo_media_id_media_assets"),
            "media_assets",
            ["logo_media_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_foreign_key(
            op.f("fk_store_settings_favicon_media_id_media_assets"),
            "media_assets",
            ["favicon_media_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_check_constraint(
            op.f("ck_store_settings_default_sort_valid"), f"default_product_sort IN ({SORTS})"
        )


def downgrade() -> None:
    with op.batch_alter_table("store_settings") as batch:
        batch.drop_constraint(op.f("ck_store_settings_default_sort_valid"), type_="check")
        batch.drop_constraint(op.f("fk_store_settings_favicon_media_id_media_assets"), type_="foreignkey")
        batch.drop_constraint(op.f("fk_store_settings_logo_media_id_media_assets"), type_="foreignkey")
        for column in (
            "seo_defaults",
            "payment_options",
            "whatsapp_message_template",
            "default_product_sort",
            "business_hours",
            "announcement",
            "theme",
            "favicon_media_id",
            "logo_media_id",
        ):
            batch.drop_column(column)

    op.execute("DELETE FROM navigation_items WHERE link_type = 'heading'")
    with op.batch_alter_table("navigation_items") as batch:
        batch.drop_constraint(op.f("ck_navigation_items_link_type_valid"), type_="check")
        batch.create_check_constraint(
            op.f("ck_navigation_items_link_type_valid"), f"link_type IN ({LINK_TYPES_V1})"
        )

    op.execute(f"DELETE FROM homepage_sections WHERE section_type NOT IN ({SECTION_TYPES_V1})")
    with op.batch_alter_table("homepage_sections") as batch:
        batch.drop_constraint(op.f("ck_homepage_sections_type_valid"), type_="check")
        batch.create_check_constraint(
            op.f("ck_homepage_sections_type_valid"), f"section_type IN ({SECTION_TYPES_V1})"
        )

    with op.batch_alter_table("products") as batch:
        batch.drop_column("badges")

    op.drop_index("ix_homepage_publications_published_at", table_name="homepage_publications")
    op.drop_table("homepage_publications")
