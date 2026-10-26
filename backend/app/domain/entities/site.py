"""Store configuration and website content entities (managed in the admin CMS)."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.domain.enums import NavigationLinkType, NavigationMenu, PublishStatus
from app.domain.errors import DomainValidationError
from app.domain.value_objects.pricing import to_money


@dataclass(slots=True)
class StoreSettings:
    store_name: str = "Twinkle Kids"
    tagline: str | None = None
    currency_code: str = "INR"
    logo_media_id: UUID | None = None
    favicon_media_id: UUID | None = None
    theme: dict[str, Any] = field(default_factory=dict)
    announcement: dict[str, Any] = field(default_factory=dict)
    contact_email: str | None = None
    contact_phone: str | None = None
    business_address: str | None = None
    business_hours: str | None = None
    social_links: dict[str, Any] = field(default_factory=dict)
    guest_checkout_enabled: bool = True
    whatsapp_ordering_enabled: bool = False
    whatsapp_number: str | None = None
    whatsapp_message_template: str | None = None
    payment_options: list[dict[str, Any]] = field(default_factory=list)
    shipping_settings: dict[str, Any] = field(default_factory=dict)
    order_policies: dict[str, Any] = field(default_factory=dict)
    default_product_sort: str = "featured"
    default_low_stock_threshold: int = 3
    seo_defaults: dict[str, Any] = field(default_factory=dict)
    updated_at: datetime | None = None

    def validate(self) -> None:
        if not self.store_name.strip():
            raise DomainValidationError("Store name is required.")
        if self.whatsapp_ordering_enabled and not self.whatsapp_number:
            raise DomainValidationError("Add a WhatsApp number before enabling WhatsApp ordering.")
        if self.default_low_stock_threshold < 0:
            raise DomainValidationError("Low-stock threshold cannot be negative.")


@dataclass(slots=True)
class NavigationItem:
    id: UUID
    menu: NavigationMenu
    label: str
    link_type: NavigationLinkType
    parent_id: UUID | None = None
    category_id: UUID | None = None
    collection_id: UUID | None = None
    page_id: UUID | None = None
    url: str | None = None
    position: int = 0
    is_active: bool = True
    open_in_new_tab: bool = False

    def validate(self) -> None:
        if not self.label.strip():
            raise DomainValidationError("Menu items need a label.")
        targets = {
            NavigationLinkType.CATEGORY: self.category_id,
            NavigationLinkType.COLLECTION: self.collection_id,
            NavigationLinkType.PAGE: self.page_id,
            NavigationLinkType.URL: self.url,
        }
        for link_type, target in targets.items():
            if (self.link_type is link_type) != (target is not None):
                raise DomainValidationError(
                    "Choose exactly the target that matches the link type."
                    if self.link_type is not NavigationLinkType.HEADING
                    else "Headings cannot link anywhere."
                )
        if self.parent_id == self.id:
            raise DomainValidationError("A menu item cannot be its own parent.")


@dataclass(slots=True)
class WebsitePage:
    id: UUID
    slug: str
    title: str
    content: dict[str, Any] = field(default_factory=dict)
    status: PublishStatus = PublishStatus.DRAFT
    seo_title: str | None = None
    seo_description: str | None = None
    published_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(slots=True)
class ShippingRule:
    id: UUID
    name: str
    fee: Decimal
    min_order_amount: Decimal = Decimal("0.00")
    max_order_amount: Decimal | None = None
    priority: int = 100
    is_active: bool = True

    def validate(self) -> None:
        if not self.name.strip():
            raise DomainValidationError("Shipping rules need a name.")
        self.fee = to_money(self.fee, field="Shipping fee")
        self.min_order_amount = to_money(self.min_order_amount, field="Minimum order")
        if self.max_order_amount is not None:
            self.max_order_amount = to_money(self.max_order_amount, field="Maximum order")
            if self.max_order_amount <= self.min_order_amount:
                raise DomainValidationError("Maximum order must be greater than the minimum.")


@dataclass(slots=True)
class SizeChart:
    id: UUID
    name: str
    slug: str
    chart: dict[str, Any]
    description: str | None = None
