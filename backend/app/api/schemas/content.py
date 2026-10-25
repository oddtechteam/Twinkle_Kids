"""Response models for the CMS (admin), dashboard and public content endpoints."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.api.schemas.catalog import CategoryOut, ImageOut, ProductSummaryOut
from app.application.use_cases.homepage import PublicationInfo, SectionView
from app.application.use_cases.site import PublicLink, PublicSite
from app.domain.entities.content import Collection
from app.domain.entities.site import StoreSettings


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Collections ------------------------------------------------------------------------------


class CollectionOut(_Out):
    id: UUID
    name: str
    slug: str
    description: str | None
    image: ImageOut | None
    status: str
    display_order: int
    seo_title: str | None = None
    seo_description: str | None = None


class AdminCollectionOut(BaseModel):
    id: UUID
    name: str
    slug: str
    description: str | None
    image_media_id: UUID | None
    status: str
    display_order: int
    seo_title: str | None
    seo_description: str | None
    product_count: int | None = None

    @classmethod
    def of(cls, c: Collection, product_count: int | None = None) -> "AdminCollectionOut":
        return cls(
            id=c.id,
            name=c.name,
            slug=c.slug,
            description=c.description,
            image_media_id=c.image_media_id,
            status=c.status.value,
            display_order=c.display_order,
            seo_title=c.seo_title,
            seo_description=c.seo_description,
            product_count=product_count,
        )


# --- Homepage builder -------------------------------------------------------------------------


class SectionOut(BaseModel):
    id: UUID
    section_type: str
    title: str | None
    subtitle: str | None
    settings: dict[str, Any]
    is_visible: bool
    status: str
    position: int
    desktop_media_id: UUID | None
    mobile_media_id: UUID | None
    selection_mode: str
    source_category_id: UUID | None
    source_collection_id: UUID | None
    product_limit: int
    product_ids: list[UUID]

    @classmethod
    def of(cls, view: SectionView) -> "SectionOut":
        s = view.section
        return cls(
            id=s.id,
            section_type=s.section_type.value,
            title=s.title,
            subtitle=s.subtitle,
            settings=s.settings,
            is_visible=s.is_visible,
            status=s.status.value,
            position=s.position,
            desktop_media_id=s.desktop_media_id,
            mobile_media_id=s.mobile_media_id,
            selection_mode=s.selection_mode.value,
            source_category_id=s.source_category_id,
            source_collection_id=s.source_collection_id,
            product_limit=s.product_limit,
            product_ids=view.product_ids,
        )


class PublicationOut(BaseModel):
    published_at: datetime | None
    draft_modified_at: datetime | None
    has_unpublished_changes: bool

    @classmethod
    def of(cls, info: PublicationInfo) -> "PublicationOut":
        return cls(
            published_at=info.published_at,
            draft_modified_at=info.draft_modified_at,
            has_unpublished_changes=info.has_unpublished_changes,
        )


class HomepageAdminOut(BaseModel):
    sections: list[SectionOut]
    publication: PublicationOut


class PublishedSectionOut(_Out):
    id: str
    type: str
    title: str | None
    subtitle: str | None
    settings: dict[str, Any]
    desktop_image: ImageOut | None
    mobile_image: ImageOut | None
    products: list[ProductSummaryOut]
    categories: list[CategoryOut]
    collections: list[CollectionOut]
    collection: CollectionOut | None
    view_all_href: str | None


class PublishedHomepageOut(_Out):
    published: bool
    published_at: datetime | None
    sections: list[PublishedSectionOut]


# --- Settings ---------------------------------------------------------------------------------


class SettingsOut(_Out):
    store_name: str
    tagline: str | None
    currency_code: str
    logo_media_id: UUID | None
    favicon_media_id: UUID | None
    theme: dict[str, Any]
    announcement: dict[str, Any]
    contact_email: str | None
    contact_phone: str | None
    business_address: str | None
    business_hours: str | None
    social_links: dict[str, Any]
    guest_checkout_enabled: bool
    whatsapp_ordering_enabled: bool
    whatsapp_number: str | None
    whatsapp_message_template: str | None
    payment_options: list[dict[str, Any]]
    default_product_sort: str
    default_low_stock_threshold: int
    seo_defaults: dict[str, Any]
    updated_at: datetime | None

    @classmethod
    def of(cls, settings: StoreSettings) -> "SettingsOut":
        return cls.model_validate(settings)


class PublicLinkOut(_Out):
    label: str
    href: str | None
    open_in_new_tab: bool
    children: list["PublicLinkOut"]


class PublicSiteOut(BaseModel):
    """Everything the storefront shell needs. Contains no credentials or internal settings."""

    store_name: str
    tagline: str | None
    currency_code: str
    logo: ImageOut | None
    favicon: ImageOut | None
    theme: dict[str, Any]
    announcement: dict[str, Any]
    contact: dict[str, str | None]
    social_links: dict[str, Any]
    guest_checkout_enabled: bool
    whatsapp_ordering_enabled: bool
    whatsapp_message_template: str | None
    payment_options: list[dict[str, Any]]
    default_product_sort: str
    seo: dict[str, Any]
    og_image: ImageOut | None
    menus: dict[str, list[PublicLinkOut]]

    @classmethod
    def of(cls, site: PublicSite) -> "PublicSiteOut":
        s = site.settings

        def link(item: PublicLink) -> PublicLinkOut:
            return PublicLinkOut(
                label=item.label,
                href=item.href,
                open_in_new_tab=item.open_in_new_tab,
                children=[link(c) for c in item.children],
            )

        return cls(
            store_name=s.store_name,
            tagline=s.tagline,
            currency_code=s.currency_code,
            logo=ImageOut.model_validate(site.logo) if site.logo else None,
            favicon=ImageOut.model_validate(site.favicon) if site.favicon else None,
            theme=s.theme,
            announcement=s.announcement if s.announcement.get("enabled") else {"enabled": False},
            contact={
                "email": s.contact_email,
                "phone": s.contact_phone,
                "whatsapp": s.whatsapp_number if s.whatsapp_ordering_enabled else None,
                "address": s.business_address,
                "hours": s.business_hours,
            },
            social_links=s.social_links,
            guest_checkout_enabled=s.guest_checkout_enabled,
            whatsapp_ordering_enabled=s.whatsapp_ordering_enabled,
            whatsapp_message_template=s.whatsapp_message_template,
            payment_options=[o for o in s.payment_options if o.get("enabled")],
            default_product_sort=s.default_product_sort,
            seo={
                "title_suffix": s.seo_defaults.get("title_suffix"),
                "default_description": s.seo_defaults.get("default_description"),
            },
            og_image=ImageOut.model_validate(site.og_image) if site.og_image else None,
            menus={menu: [link(i) for i in items] for menu, items in site.menus.items()},
        )


# --- Navigation, pages, shipping, size charts -------------------------------------------------


class NavigationItemOut(_Out):
    id: UUID
    menu: str
    label: str
    link_type: str
    parent_id: UUID | None
    category_id: UUID | None
    collection_id: UUID | None
    page_id: UUID | None
    url: str | None
    position: int
    is_active: bool
    open_in_new_tab: bool


class PageOut(_Out):
    id: UUID
    slug: str
    title: str
    content: dict[str, Any]
    status: str
    seo_title: str | None
    seo_description: str | None
    published_at: datetime | None
    updated_at: datetime | None


class PublicPageOut(_Out):
    slug: str
    title: str
    content: dict[str, Any]
    seo_title: str | None
    seo_description: str | None
    published_at: datetime | None


class ShippingRuleOut(_Out):
    id: UUID
    name: str
    fee: Decimal
    min_order_amount: Decimal
    max_order_amount: Decimal | None
    priority: int
    is_active: bool


class PublicShippingRuleOut(_Out):
    name: str
    fee: Decimal
    min_order_amount: Decimal
    max_order_amount: Decimal | None


class SizeChartOut(_Out):
    id: UUID
    name: str
    slug: str
    description: str | None
    chart: dict[str, Any]


# --- Dashboard --------------------------------------------------------------------------------


class LowStockOut(_Out):
    product_id: UUID
    product_name: str
    variant_label: str | None
    sku: str
    stock_quantity: int
    threshold: int


class DailyCountOut(_Out):
    day: date
    orders: int


class TopProductOut(_Out):
    product_name: str
    units: int


class ActivityOut(_Out):
    action: str
    entity_type: str
    entity_id: str | None
    actor_email: str | None
    created_at: datetime


class DashboardOut(_Out):
    products_total: int
    products_active: int
    products_draft: int
    products_archived: int
    low_stock_count: int
    out_of_stock_count: int
    low_stock: list[LowStockOut]
    orders_total: int
    orders_new: int
    orders_by_day: list[DailyCountOut]
    order_value_placed: Decimal
    order_value_confirmed: Decimal
    revenue_paid: Decimal
    whatsapp_initiated: int
    whatsapp_contacted: int
    top_products: list[TopProductOut]
    top_products_min_orders: int
    recent_activity: list[ActivityOut]


class MediaUsageOut(BaseModel):
    in_use: bool
    places: list[str]
