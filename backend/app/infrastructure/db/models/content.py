import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import (
    HomepageSectionType,
    NavigationLinkType,
    NavigationMenu,
    PublishStatus,
    SelectionMode,
    sql_in,
)
from app.infrastructure.db.base import Base
from app.infrastructure.db.types import (
    JSONType,
    UTCDateTime,
    created_at_column,
    updated_at_column,
    uuid_pk,
)

_PUBLISH_CHECK = f"status IN ({sql_in(PublishStatus)})"


class CollectionModel(Base):
    __tablename__ = "collections"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(160), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    image_media_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(16), default="draft", server_default="draft")
    display_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    seo_title: Mapped[str | None] = mapped_column(String(70))
    seo_description: Mapped[str | None] = mapped_column(String(320))
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    __table_args__ = (CheckConstraint(_PUBLISH_CHECK, name="status_valid"),)


class CollectionProductModel(Base):
    __tablename__ = "collection_products"

    collection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    position: Mapped[int] = mapped_column(Integer)

    __table_args__ = (
        CheckConstraint("position >= 0", name="position_non_negative"),
        Index("ix_collection_products_collection_position", "collection_id", "position"),
    )


class HomepageSectionModel(Base):
    __tablename__ = "homepage_sections"

    id: Mapped[uuid.UUID] = uuid_pk()
    section_type: Mapped[str] = mapped_column(String(32))
    title: Mapped[str | None] = mapped_column(String(120))
    subtitle: Mapped[str | None] = mapped_column(String(255))
    # Per-type settings, validated by application.content_settings before saving.
    settings: Mapped[dict[str, Any]] = mapped_column(
        JSONType, default=dict, server_default=text("'{}'")
    )
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    status: Mapped[str] = mapped_column(String(16), default="draft", server_default="draft")
    position: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    desktop_media_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="SET NULL")
    )
    mobile_media_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="SET NULL")
    )
    selection_mode: Mapped[str] = mapped_column(String(16), default="none", server_default="none")
    source_category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL")
    )
    source_collection_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("collections.id", ondelete="SET NULL")
    )
    product_limit: Mapped[int] = mapped_column(Integer, default=12, server_default="12")
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    __table_args__ = (
        CheckConstraint(f"section_type IN ({sql_in(HomepageSectionType)})", name="type_valid"),
        CheckConstraint(_PUBLISH_CHECK, name="status_valid"),
        CheckConstraint(f"selection_mode IN ({sql_in(SelectionMode)})", name="selection_valid"),
        CheckConstraint(
            "selection_mode <> 'category' OR source_category_id IS NOT NULL",
            name="category_source_required",
        ),
        CheckConstraint(
            "selection_mode <> 'collection' OR source_collection_id IS NOT NULL",
            name="collection_source_required",
        ),
        CheckConstraint("product_limit BETWEEN 1 AND 48", name="product_limit_range"),
        Index("ix_homepage_sections_position", "status", "is_visible", "position"),
    )


class HomepageSectionProductModel(Base):
    __tablename__ = "homepage_section_products"

    section_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("homepage_sections.id", ondelete="CASCADE"), primary_key=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    position: Mapped[int] = mapped_column(Integer)

    __table_args__ = (
        CheckConstraint("position >= 0", name="position_non_negative"),
        Index("ix_homepage_section_products_section_position", "section_id", "position"),
    )


class WebsitePageModel(Base):
    __tablename__ = "website_pages"

    id: Mapped[uuid.UUID] = uuid_pk()
    slug: Mapped[str] = mapped_column(String(160), unique=True)
    title: Mapped[str] = mapped_column(String(160))
    # Structured blocks validated by the application layer (no raw HTML from admins).
    content: Mapped[dict[str, Any]] = mapped_column(
        JSONType, default=dict, server_default=text("'{}'")
    )
    status: Mapped[str] = mapped_column(String(16), default="draft", server_default="draft")
    seo_title: Mapped[str | None] = mapped_column(String(70))
    seo_description: Mapped[str | None] = mapped_column(String(320))
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    __table_args__ = (CheckConstraint(_PUBLISH_CHECK, name="status_valid"),)


class NavigationItemModel(Base):
    __tablename__ = "navigation_items"

    id: Mapped[uuid.UUID] = uuid_pk()
    menu: Mapped[str] = mapped_column(String(16))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("navigation_items.id", ondelete="CASCADE")
    )
    label: Mapped[str] = mapped_column(String(80))
    link_type: Mapped[str] = mapped_column(String(16))
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE")
    )
    collection_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("collections.id", ondelete="CASCADE")
    )
    page_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("website_pages.id", ondelete="CASCADE")
    )
    url: Mapped[str | None] = mapped_column(String(500))
    position: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    open_in_new_tab: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    __table_args__ = (
        CheckConstraint(f"menu IN ({sql_in(NavigationMenu)})", name="menu_valid"),
        CheckConstraint(f"link_type IN ({sql_in(NavigationLinkType)})", name="link_type_valid"),
        # Exactly the target matching link_type is set.
        CheckConstraint(
            "(link_type = 'category') = (category_id IS NOT NULL) AND "
            "(link_type = 'collection') = (collection_id IS NOT NULL) AND "
            "(link_type = 'page') = (page_id IS NOT NULL) AND "
            "(link_type = 'url') = (url IS NOT NULL)",
            name="target_matches_type",
        ),
        Index("ix_navigation_items_menu_position", "menu", "parent_id", "position"),
    )


class StoreSettingsModel(Base):
    """Single-row, typed store configuration (id is always 1)."""

    __tablename__ = "store_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    store_name: Mapped[str] = mapped_column(String(120), default="Twinkle Kids")
    tagline: Mapped[str | None] = mapped_column(String(200))
    currency_code: Mapped[str] = mapped_column(String(3), default="INR", server_default="INR")
    guest_checkout_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true")
    )
    whatsapp_ordering_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    whatsapp_number: Mapped[str | None] = mapped_column(String(20))
    contact_email: Mapped[str | None] = mapped_column(String(254))
    contact_phone: Mapped[str | None] = mapped_column(String(20))
    business_address: Mapped[str | None] = mapped_column(Text)
    social_links: Mapped[dict[str, Any]] = mapped_column(
        JSONType, default=dict, server_default=text("'{}'")
    )
    default_low_stock_threshold: Mapped[int] = mapped_column(Integer, default=3, server_default="3")
    extra: Mapped[dict[str, Any]] = mapped_column(
        JSONType, default=dict, server_default=text("'{}'")
    )
    # Branding & storefront configuration (JSON groups are validated by
    # app.application.content_settings before they are stored).
    logo_media_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="SET NULL")
    )
    favicon_media_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="SET NULL")
    )
    theme: Mapped[dict[str, Any]] = mapped_column(
        JSONType, default=dict, server_default=text("'{}'")
    )
    announcement: Mapped[dict[str, Any]] = mapped_column(
        JSONType, default=dict, server_default=text("'{}'")
    )
    business_hours: Mapped[str | None] = mapped_column(String(120))
    default_product_sort: Mapped[str] = mapped_column(
        String(16), default="featured", server_default="featured"
    )
    whatsapp_message_template: Mapped[str | None] = mapped_column(Text)
    # Free-shipping threshold, PIN-code eligibility, delivery messaging (see content_settings).
    shipping_settings: Mapped[dict[str, Any]] = mapped_column(
        JSONType, default=dict, server_default=text("'{}'")
    )
    # Cancellation / return / exchange policy switches and reasons.
    order_policies: Mapped[dict[str, Any]] = mapped_column(
        JSONType, default=dict, server_default=text("'{}'")
    )
    payment_options: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONType, default=list, server_default=text("'[]'")
    )
    seo_defaults: Mapped[dict[str, Any]] = mapped_column(
        JSONType, default=dict, server_default=text("'{}'")
    )
    updated_at: Mapped[datetime] = updated_at_column()

    __table_args__ = (
        CheckConstraint("id = 1", name="singleton"),
        CheckConstraint("length(currency_code) = 3", name="currency_code_len"),
        CheckConstraint(
            "whatsapp_ordering_enabled = false OR whatsapp_number IS NOT NULL",
            name="whatsapp_number_required",
        ),
        CheckConstraint(
            "default_product_sort IN ('featured','newest','price_asc','price_desc','name_asc')",
            name="default_sort_valid",
        ),
    )


class HomepagePublicationModel(Base):
    """Immutable snapshot of the homepage at publish time. The storefront renders the latest
    one; editing homepage_sections (the draft workspace) never changes the live site."""

    __tablename__ = "homepage_publications"

    id: Mapped[uuid.UUID] = uuid_pk()
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONType)
    published_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    note: Mapped[str | None] = mapped_column(String(200))
    published_at: Mapped[datetime] = created_at_column()

    __table_args__ = (Index("ix_homepage_publications_published_at", "published_at"),)
