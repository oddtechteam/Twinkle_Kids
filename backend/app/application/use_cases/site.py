"""Store settings, navigation menus, website pages, shipping rules and size charts, plus the
public site configuration read model."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, fields, replace
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from app.application.content_settings import (
    validate_announcement,
    validate_page_content,
    validate_payment_options,
    validate_seo_defaults,
    validate_size_chart,
    validate_social_links,
    validate_theme,
)
from app.application.dto.catalog import ImageView
from app.application.ports import CatalogQueries
from app.domain.entities.site import (
    NavigationItem,
    ShippingRule,
    SizeChart,
    StoreSettings,
    WebsitePage,
)
from app.domain.enums import NavigationLinkType, NavigationMenu, PublishStatus
from app.domain.errors import ConflictError, DomainValidationError, NotFoundError
from app.domain.repositories.catalog import CategoryRepository
from app.domain.repositories.identity import AuditLogRepository
from app.domain.repositories.media import MediaAssetRepository, UnitOfWork
from app.domain.repositories.site import (
    CollectionAdminRepository,
    NavigationRepository,
    PageRepository,
    SettingsRepository,
    ShippingRuleRepository,
    SizeChartRepository,
)
from app.domain.value_objects.text import clean_optional, slugify, validate_slug

SORTS = {"featured", "newest", "price_asc", "price_desc", "name_asc"}
_PHONE_CHARS = set("+0123456789 -")


def _phone(value: str | None, label: str) -> str | None:
    value = clean_optional(value)
    if value is None:
        return None
    if not set(value) <= _PHONE_CHARS or sum(c.isdigit() for c in value) < 7:
        raise DomainValidationError(f"{label} must be a phone number (digits, spaces, + or -).")
    return value


def _now() -> datetime:
    return datetime.now(UTC)


# --- Store settings ---------------------------------------------------------------------------


class SettingsService:
    def __init__(
        self,
        *,
        settings: SettingsRepository,
        media: MediaAssetRepository,
        audit: AuditLogRepository,
        uow: UnitOfWork,
    ) -> None:
        self._settings = settings
        self._media = media
        self._audit = audit
        self._uow = uow

    def get(self) -> StoreSettings:
        return self._settings.get()

    def update(self, changes: dict[str, Any], *, actor_id: UUID | None) -> StoreSettings:
        """Partial update: only the given fields change; every group is validated."""
        current = self._settings.get()
        allowed = {f.name for f in fields(StoreSettings)} - {"updated_at", "currency_code"}
        unknown = set(changes) - allowed
        if unknown:
            raise DomainValidationError(f"Unknown settings: {', '.join(sorted(unknown))}.")

        values = dict(changes)
        if "theme" in values:
            values["theme"] = validate_theme(values["theme"])
        if "announcement" in values:
            values["announcement"] = validate_announcement(values["announcement"])
        if "payment_options" in values:
            values["payment_options"] = validate_payment_options(values["payment_options"])
        if "social_links" in values:
            values["social_links"] = validate_social_links(values["social_links"])
        if "seo_defaults" in values:
            values["seo_defaults"] = validate_seo_defaults(values["seo_defaults"])
        if "default_product_sort" in values and values["default_product_sort"] not in SORTS:
            raise DomainValidationError("Unknown default sort order.")
        for key in ("whatsapp_number", "contact_phone"):
            if key in values:
                values[key] = _phone(values[key], key.replace("_", " ").capitalize())
        for key in ("store_name", "tagline", "contact_email", "business_address", "business_hours"):
            if key in values and isinstance(values[key], str):
                values[key] = values[key].strip() if key == "store_name" else clean_optional(values[key])
        if "whatsapp_message_template" in values:
            template = clean_optional(values["whatsapp_message_template"])
            if template and len(template) > 500:
                raise DomainValidationError("The WhatsApp message template is too long (500 max).")
            values["whatsapp_message_template"] = template

        media_ids = [values.get(k) for k in ("logo_media_id", "favicon_media_id")]
        og = (values.get("seo_defaults") or {}).get("og_image_media_id")
        wanted = [m for m in [*media_ids, UUID(og) if og else None] if m]
        if set(wanted) - self._media.existing_ids(wanted):
            raise DomainValidationError("Selected image does not exist in the media library.")

        updated = replace(current, **values)
        updated.validate()
        self._settings.save(updated)
        self._audit.record(
            actor_user_id=actor_id,
            action="settings.updated",
            entity_type="store_settings",
            entity_id="1",
            changes={"fields": sorted(changes)},
        )
        self._uow.commit()
        return self._settings.get()


# --- Navigation -------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class NavigationInput:
    menu: NavigationMenu
    label: str
    link_type: NavigationLinkType
    parent_id: UUID | None = None
    category_id: UUID | None = None
    collection_id: UUID | None = None
    page_id: UUID | None = None
    url: str | None = None
    is_active: bool = True
    open_in_new_tab: bool = False


class NavigationService:
    def __init__(
        self,
        *,
        navigation: NavigationRepository,
        categories: CategoryRepository,
        collections: CollectionAdminRepository,
        pages: PageRepository,
        audit: AuditLogRepository,
        uow: UnitOfWork,
    ) -> None:
        self._navigation = navigation
        self._categories = categories
        self._collections = collections
        self._pages = pages
        self._audit = audit
        self._uow = uow

    def list(self, menu: NavigationMenu | None = None) -> Sequence[NavigationItem]:
        return self._navigation.list(menu)

    def create(self, data: NavigationInput, *, actor_id: UUID | None) -> UUID:
        siblings = [i for i in self._navigation.list(data.menu) if i.parent_id == data.parent_id]
        item = self._build(uuid4(), data, position=len(siblings))
        self._navigation.add(item)
        self._log(actor_id, "navigation.created", item.id)
        self._uow.commit()
        return item.id

    def update(self, item_id: UUID, data: NavigationInput, *, actor_id: UUID | None) -> None:
        current = self._require(item_id)
        item = self._build(item_id, data, position=current.position)
        self._navigation.save(item)
        self._log(actor_id, "navigation.updated", item_id)
        self._uow.commit()

    def delete(self, item_id: UUID, *, actor_id: UUID | None) -> None:
        self._require(item_id)
        self._navigation.delete(item_id)  # children cascade
        self._log(actor_id, "navigation.deleted", item_id)
        self._uow.commit()

    def reorder(self, item_ids: list[UUID], *, actor_id: UUID | None) -> None:
        items = {i.id: i for i in self._navigation.list()}
        if len(set(item_ids)) != len(item_ids) or any(i not in items for i in item_ids):
            raise DomainValidationError("Unknown or duplicate menu items in the new order.")
        groups = {(items[i].menu, items[i].parent_id) for i in item_ids}
        if len(groups) > 1:
            raise DomainValidationError("Only items in the same menu level can be reordered together.")
        self._navigation.reorder(item_ids)
        self._log(actor_id, "navigation.reordered", None)
        self._uow.commit()

    def _require(self, item_id: UUID) -> NavigationItem:
        item = self._navigation.get(item_id)
        if item is None:
            raise NotFoundError("Menu item not found.")
        return item

    def _build(self, item_id: UUID, data: NavigationInput, *, position: int) -> NavigationItem:
        url = clean_optional(data.url)
        if url is not None and not (
            (url.startswith("/") and not url.startswith("//")) or url.startswith("https://")
        ):
            raise DomainValidationError("Links must be site-relative (/path) or https:// URLs.")
        item = NavigationItem(
            id=item_id,
            menu=data.menu,
            label=data.label.strip()[:80],
            link_type=data.link_type,
            parent_id=data.parent_id,
            category_id=data.category_id if data.link_type is NavigationLinkType.CATEGORY else None,
            collection_id=data.collection_id if data.link_type is NavigationLinkType.COLLECTION else None,
            page_id=data.page_id if data.link_type is NavigationLinkType.PAGE else None,
            url=url if data.link_type is NavigationLinkType.URL else None,
            position=position,
            is_active=data.is_active,
            open_in_new_tab=data.open_in_new_tab,
        )
        item.validate()
        if item.parent_id is not None:
            parent = self._navigation.get(item.parent_id)
            if parent is None or parent.menu is not item.menu:
                raise DomainValidationError("Parent item must be in the same menu.")
            if parent.parent_id is not None:
                raise DomainValidationError("Menus support two levels only.")
        if item.category_id and not self._categories.existing_ids([item.category_id]):
            raise DomainValidationError("Category does not exist.")
        if item.collection_id and self._collections.get(item.collection_id) is None:
            raise DomainValidationError("Collection does not exist.")
        if item.page_id and self._pages.get(item.page_id) is None:
            raise DomainValidationError("Page does not exist.")
        return item

    def _log(self, actor_id: UUID | None, action: str, item_id: UUID | None) -> None:
        self._audit.record(
            actor_user_id=actor_id,
            action=action,
            entity_type="navigation_item",
            entity_id=str(item_id) if item_id else None,
        )


# --- Website pages ----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PageInput:
    title: str
    slug: str | None = None
    content: dict[str, Any] = field(default_factory=dict)
    status: PublishStatus = PublishStatus.DRAFT
    seo_title: str | None = None
    seo_description: str | None = None


class PageService:
    def __init__(
        self,
        *,
        pages: PageRepository,
        audit: AuditLogRepository,
        uow: UnitOfWork,
        clock: Callable[[], datetime] = _now,
    ) -> None:
        self._pages = pages
        self._audit = audit
        self._uow = uow
        self._clock = clock

    def list(self) -> Sequence[WebsitePage]:
        return self._pages.list()

    def get(self, page_id: UUID) -> WebsitePage:
        page = self._pages.get(page_id)
        if page is None:
            raise NotFoundError("Page not found.")
        return page

    def published(self, slug: str) -> WebsitePage:
        page = self._pages.get_by_slug(slug)
        if page is None or page.status is not PublishStatus.PUBLISHED:
            raise NotFoundError("Page not found.")
        return page

    def create(self, data: PageInput, *, actor_id: UUID | None) -> UUID:
        page = self._build(uuid4(), data, current=None)
        self._pages.add(page)
        self._log(actor_id, "page.created", page.id)
        self._uow.commit()
        return page.id

    def update(self, page_id: UUID, data: PageInput, *, actor_id: UUID | None) -> None:
        current = self.get(page_id)
        page = self._build(page_id, data, current=current)
        self._pages.save(page)
        self._log(actor_id, "page.updated", page_id)
        self._uow.commit()

    def delete(self, page_id: UUID, *, actor_id: UUID | None) -> None:
        self.get(page_id)
        self._pages.delete(page_id)
        self._log(actor_id, "page.deleted", page_id)
        self._uow.commit()

    def _build(self, page_id: UUID, data: PageInput, *, current: WebsitePage | None) -> WebsitePage:
        title = data.title.strip()
        if not title:
            raise DomainValidationError("Page title is required.")
        slug = validate_slug(data.slug or slugify(title))
        if self._pages.slug_taken(slug, exclude_id=page_id):
            raise ConflictError(f"The slug '{slug}' is already used by another page.")
        published_at = current.published_at if current else None
        if data.status is PublishStatus.PUBLISHED and published_at is None:
            published_at = self._clock()
        return WebsitePage(
            id=page_id,
            slug=slug,
            title=title[:160],
            content=validate_page_content(data.content or {"blocks": []}),
            status=data.status,
            seo_title=clean_optional(data.seo_title),
            seo_description=clean_optional(data.seo_description),
            published_at=published_at,
        )

    def _log(self, actor_id: UUID | None, action: str, page_id: UUID) -> None:
        self._audit.record(
            actor_user_id=actor_id, action=action, entity_type="website_page", entity_id=str(page_id)
        )


# --- Shipping rules ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ShippingRuleInput:
    name: str
    fee: Decimal
    min_order_amount: Decimal = Decimal("0.00")
    max_order_amount: Decimal | None = None
    priority: int = 100
    is_active: bool = True


class ShippingService:
    def __init__(self, *, rules: ShippingRuleRepository, audit: AuditLogRepository, uow: UnitOfWork) -> None:
        self._rules = rules
        self._audit = audit
        self._uow = uow

    def list(self) -> Sequence[ShippingRule]:
        return self._rules.list()

    def create(self, data: ShippingRuleInput, *, actor_id: UUID | None) -> UUID:
        rule = ShippingRule(id=uuid4(), **_rule_values(data))
        rule.validate()
        self._rules.add(rule)
        self._log(actor_id, "shipping_rule.created", rule.id)
        self._uow.commit()
        return rule.id

    def update(self, rule_id: UUID, data: ShippingRuleInput, *, actor_id: UUID | None) -> None:
        if self._rules.get(rule_id) is None:
            raise NotFoundError("Shipping rule not found.")
        rule = ShippingRule(id=rule_id, **_rule_values(data))
        rule.validate()
        self._rules.save(rule)
        self._log(actor_id, "shipping_rule.updated", rule_id)
        self._uow.commit()

    def delete(self, rule_id: UUID, *, actor_id: UUID | None) -> None:
        if self._rules.get(rule_id) is None:
            raise NotFoundError("Shipping rule not found.")
        self._rules.delete(rule_id)
        self._log(actor_id, "shipping_rule.deleted", rule_id)
        self._uow.commit()

    def _log(self, actor_id: UUID | None, action: str, rule_id: UUID) -> None:
        self._audit.record(
            actor_user_id=actor_id, action=action, entity_type="shipping_rule", entity_id=str(rule_id)
        )


def _rule_values(data: ShippingRuleInput) -> dict[str, Any]:
    return {
        "name": data.name.strip(),
        "fee": data.fee,
        "min_order_amount": data.min_order_amount,
        "max_order_amount": data.max_order_amount,
        "priority": data.priority,
        "is_active": data.is_active,
    }


# --- Size charts ------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SizeChartInput:
    name: str
    chart: dict[str, Any]
    slug: str | None = None
    description: str | None = None


class SizeChartService:
    def __init__(self, *, charts: SizeChartRepository, audit: AuditLogRepository, uow: UnitOfWork) -> None:
        self._charts = charts
        self._audit = audit
        self._uow = uow

    def list(self) -> Sequence[SizeChart]:
        return self._charts.list()

    def create(self, data: SizeChartInput, *, actor_id: UUID | None) -> UUID:
        chart = self._build(uuid4(), data)
        self._charts.add(chart)
        self._log(actor_id, "size_chart.created", chart.id)
        self._uow.commit()
        return chart.id

    def update(self, chart_id: UUID, data: SizeChartInput, *, actor_id: UUID | None) -> None:
        if self._charts.get(chart_id) is None:
            raise NotFoundError("Size chart not found.")
        self._charts.save(self._build(chart_id, data))
        self._log(actor_id, "size_chart.updated", chart_id)
        self._uow.commit()

    def delete(self, chart_id: UUID, *, actor_id: UUID | None) -> None:
        if self._charts.get(chart_id) is None:
            raise NotFoundError("Size chart not found.")
        if self._charts.in_use(chart_id):
            raise ConflictError("This size chart is used by products. Remove it from them first.")
        self._charts.delete(chart_id)
        self._log(actor_id, "size_chart.deleted", chart_id)
        self._uow.commit()

    def _build(self, chart_id: UUID, data: SizeChartInput) -> SizeChart:
        name = data.name.strip()
        if not name:
            raise DomainValidationError("Size chart name is required.")
        slug = validate_slug(data.slug or slugify(name))
        if self._charts.slug_taken(slug, exclude_id=chart_id):
            raise ConflictError(f"The slug '{slug}' is already used by another size chart.")
        return SizeChart(
            id=chart_id,
            name=name[:120],
            slug=slug,
            chart=validate_size_chart(data.chart),
            description=clean_optional(data.description),
        )

    def _log(self, actor_id: UUID | None, action: str, chart_id: UUID) -> None:
        self._audit.record(
            actor_user_id=actor_id, action=action, entity_type="size_chart", entity_id=str(chart_id)
        )


# --- Public site configuration ----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PublicLink:
    label: str
    href: str | None
    open_in_new_tab: bool
    children: list["PublicLink"]


@dataclass(frozen=True, slots=True)
class PublicSite:
    settings: StoreSettings
    logo: ImageView | None
    favicon: ImageView | None
    og_image: ImageView | None
    menus: dict[str, list[PublicLink]]


class PublicSiteReader:
    def __init__(
        self,
        *,
        settings: SettingsRepository,
        navigation: NavigationRepository,
        categories: CategoryRepository,
        collections: CollectionAdminRepository,
        pages: PageRepository,
        queries: CatalogQueries,
    ) -> None:
        self._settings = settings
        self._navigation = navigation
        self._categories = categories
        self._collections = collections
        self._pages = pages
        self._queries = queries

    def get(self) -> PublicSite:
        settings = self._settings.get()
        og = settings.seo_defaults.get("og_image_media_id")
        media_ids = [m for m in (settings.logo_media_id, settings.favicon_media_id) if m]
        if og:
            media_ids.append(UUID(og))
        images = self._queries.images(media_ids)
        return PublicSite(
            settings=settings,
            logo=images.get(settings.logo_media_id) if settings.logo_media_id else None,
            favicon=images.get(settings.favicon_media_id) if settings.favicon_media_id else None,
            og_image=images.get(UUID(og)) if og else None,
            menus={menu.value: self._menu(menu) for menu in NavigationMenu},
        )

    def _menu(self, menu: NavigationMenu) -> list[PublicLink]:
        items = [i for i in self._navigation.list(menu) if i.is_active]
        children: dict[UUID, list[NavigationItem]] = {}
        for item in items:
            if item.parent_id:
                children.setdefault(item.parent_id, []).append(item)
        links: list[PublicLink] = []
        for item in (i for i in items if i.parent_id is None):
            kids = [
                link
                for child in children.get(item.id, [])
                if (link := self._link(child, [])) is not None
            ]
            link = self._link(item, kids)
            if link is not None:
                links.append(link)
        return links

    def _link(self, item: NavigationItem, kids: list[PublicLink]) -> PublicLink | None:
        href: str | None
        match item.link_type:
            case NavigationLinkType.HEADING:
                if not kids:
                    return None
                href = None
            case NavigationLinkType.URL:
                href = item.url
            case NavigationLinkType.CATEGORY:
                category = self._categories.get(item.category_id) if item.category_id else None
                if category is None or not category.is_active:
                    return None
                href = f"/category/{category.slug}"
            case NavigationLinkType.COLLECTION:
                collection = self._collections.get(item.collection_id) if item.collection_id else None
                if collection is None or collection.status is not PublishStatus.PUBLISHED:
                    return None
                href = f"/collections/{collection.slug}"
            case NavigationLinkType.PAGE:
                page = self._pages.get(item.page_id) if item.page_id else None
                if page is None or page.status is not PublishStatus.PUBLISHED:
                    return None
                href = f"/pages/{page.slug}"
        return PublicLink(item.label, href, item.open_in_new_tab, kids)
