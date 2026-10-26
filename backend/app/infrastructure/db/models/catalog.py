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
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import ProductStatus, sql_in
from app.infrastructure.db.base import Base
from app.infrastructure.db.models.media import MediaAssetModel
from app.infrastructure.db.types import (
    JSONType,
    Money,
    UTCDateTime,
    created_at_column,
    updated_at_column,
    uuid_pk,
)


class SizeChartModel(Base):
    __tablename__ = "size_charts"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(160), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    # {"unit": "cm", "columns": ["Size", "Chest", ...], "rows": [["2-3Y", "56", ...], ...]}
    chart: Mapped[dict[str, Any]] = mapped_column(JSONType)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class CategoryModel(Base):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = uuid_pk()
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(160), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    image_media_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="SET NULL")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    display_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    # When true, product_categories.position drives the default ("featured") order.
    custom_product_ordering: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    seo_title: Mapped[str | None] = mapped_column(String(70))
    seo_description: Mapped[str | None] = mapped_column(String(320))
    seo_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONType, default=dict, server_default=text("'{}'")
    )
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    image: Mapped[MediaAssetModel | None] = relationship(lazy="joined")

    __table_args__ = (
        CheckConstraint("parent_id IS NULL OR parent_id <> id", name="not_own_parent"),
        Index("ix_categories_active_order", "is_active", "display_order"),
    )


class ProductModel(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(160), unique=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(
        String(16), default=ProductStatus.DRAFT.value, server_default=ProductStatus.DRAFT.value
    )
    short_description: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    rich_content: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
    selling_price: Mapped[Decimal] = mapped_column(Money)
    original_price: Mapped[Decimal | None] = mapped_column(Money)
    track_inventory: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true")
    )
    allow_backorder: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=3, server_default="3")
    size_chart_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("size_charts.id", ondelete="SET NULL")
    )
    seo_title: Mapped[str | None] = mapped_column(String(70))
    seo_description: Mapped[str | None] = mapped_column(String(320))
    seo_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONType, default=dict, server_default=text("'{}'")
    )
    # Admin-managed display badges (validated in the domain: max 3 short labels).
    badges: Mapped[list[str]] = mapped_column(JSONType, default=list, server_default=text("'[]'"))
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    # Admin-curated "you may also like" products (ordered list of product ids as strings).
    related_product_ids: Mapped[list[str]] = mapped_column(
        JSONType, default=list, server_default=text("'[]'")
    )
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    variants: Mapped[list["ProductVariantModel"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductVariantModel.position",
        lazy="selectin",
    )
    category_links: Mapped[list["ProductCategoryModel"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", lazy="selectin"
    )
    media_links: Mapped[list["ProductMediaModel"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductMediaModel.position",
        lazy="selectin",
    )
    size_chart: Mapped[SizeChartModel | None] = relationship(lazy="selectin")

    __table_args__ = (
        CheckConstraint(f"status IN ({sql_in(ProductStatus)})", name="status_valid"),
        CheckConstraint("selling_price >= 0", name="selling_price_non_negative"),
        CheckConstraint(
            "original_price IS NULL OR original_price >= selling_price",
            name="original_price_gte_selling",
        ),
        CheckConstraint("low_stock_threshold >= 0", name="low_stock_threshold_non_negative"),
        Index("ix_products_status_published_at", "status", "published_at"),
        Index("ix_products_status_selling_price", "status", "selling_price"),
    )


class ProductCategoryModel(Base):
    """Category membership with a position used only for that category's custom order."""

    __tablename__ = "product_categories"

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), primary_key=True
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))

    product: Mapped[ProductModel] = relationship(back_populates="category_links")
    category: Mapped[CategoryModel] = relationship(lazy="joined")

    __table_args__ = (
        CheckConstraint("position >= 0", name="position_non_negative"),
        Index("ix_product_categories_category_position", "category_id", "position"),
        Index(
            "uq_product_categories_one_primary",
            "product_id",
            unique=True,
            postgresql_where=text("is_primary = true"),
            sqlite_where=text("is_primary = true"),
        ),
    )


class ProductVariantModel(Base):
    __tablename__ = "product_variants"

    id: Mapped[uuid.UUID] = uuid_pk()
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    sku: Mapped[str] = mapped_column(String(64), unique=True)
    size: Mapped[str | None] = mapped_column(String(40))
    colour: Mapped[str | None] = mapped_column(String(40))
    colour_hex: Mapped[str | None] = mapped_column(String(7))
    # Optional overrides; NULL means "inherit the product price" (resolved in the domain).
    selling_price: Mapped[Decimal | None] = mapped_column(Money)
    original_price: Mapped[Decimal | None] = mapped_column(Money)
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    position: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    product: Mapped[ProductModel] = relationship(back_populates="variants")

    __table_args__ = (
        CheckConstraint(
            "selling_price IS NULL OR selling_price >= 0", name="selling_price_non_negative"
        ),
        CheckConstraint(
            "original_price IS NULL OR original_price >= 0", name="original_price_non_negative"
        ),
        CheckConstraint(
            "selling_price IS NULL OR original_price IS NULL OR original_price >= selling_price",
            name="original_price_gte_selling",
        ),
        CheckConstraint("stock_quantity >= 0", name="stock_non_negative"),
        CheckConstraint("colour_hex IS NULL OR length(colour_hex) = 7", name="colour_hex_format"),
        Index(
            "uq_product_variants_options",
            "product_id",
            text("lower(coalesce(size, ''))"),
            text("lower(coalesce(colour, ''))"),
            unique=True,
        ),
        Index("ix_product_variants_size", "size"),
        Index("ix_product_variants_colour", "colour"),
    )


class ProductMediaModel(Base):
    __tablename__ = "product_media"

    id: Mapped[uuid.UUID] = uuid_pk()
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    # RESTRICT: an image in use by a product cannot be deleted from the media library.
    media_asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("media_assets.id", ondelete="RESTRICT"), index=True
    )
    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("product_variants.id", ondelete="SET NULL")
    )
    position: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    alt_text: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = created_at_column()

    product: Mapped[ProductModel] = relationship(back_populates="media_links")
    media_asset: Mapped[MediaAssetModel] = relationship(lazy="joined")

    __table_args__ = (
        UniqueConstraint("product_id", "media_asset_id", name="uq_product_media_product_asset"),
        CheckConstraint("position >= 0", name="position_non_negative"),
        Index("ix_product_media_product_position", "product_id", "position"),
    )
