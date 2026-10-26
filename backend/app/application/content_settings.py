"""Validated configuration schemas for CMS-managed JSON (homepage sections, store settings,
website page blocks).

Every model forbids unknown keys, caps lengths, only accepts site-relative or https links and
never accepts HTML or script: the storefront renders these values as plain text.
"""

from decimal import Decimal
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    field_validator,
)

from app.domain.enums import HomepageSectionType, OrderStatus, PaymentMethod
from app.domain.errors import DomainValidationError

HexColour = Annotated[str, StringConstraints(pattern=r"^#[0-9a-fA-F]{6}$")]
Theme = Literal["ivory", "blush", "navy", "gold"]
IconName = Literal[
    "sparkles", "ruler", "message-circle", "gift", "heart", "shield-check", "shirt", "star"
]
ProductSortName = Literal["featured", "newest", "price_asc", "price_desc", "name_asc"]


def safe_href(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    value = value.strip()
    if value.startswith("/") and not value.startswith("//"):
        return value
    if value.startswith("https://"):
        return value
    raise ValueError("Links must be site-relative (/path) or https:// URLs.")


# Plain-text field types: whitespace-trimmed, length-capped (Req = required/non-empty).
Text30 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=0, max_length=30)]
Text30Req = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]
Text40 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=0, max_length=40)]
Text40Req = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
Text60 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=0, max_length=60)]
Text60Req = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
Text140 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=0, max_length=140)]
Text140Req = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=140)]
Text160Req = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
Text300 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=0, max_length=300)]
Text300Req = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
Text320 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=0, max_length=320)]
Text400 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=0, max_length=400)]
Text400Req = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=400)]
Text600Req = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=600)]
Text1000Req = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)
]
Text4000Req = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)
]
Text5000Req = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)
]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Cta(Strict):
    label: Text40Req
    href: str = Field(max_length=500)

    _href = field_validator("href")(lambda v: safe_href(v) or "/")


# --- Homepage sections ------------------------------------------------------------------------


class Headline(Strict):
    lead: Text60Req
    highlight: Text40 = ""
    trail: Text60 = ""


class TrustItem(Strict):
    icon: IconName = "sparkles"
    label: Text40Req


class HeroSettings(Strict):
    eyebrow: Text40 = ""
    headline: Headline
    body: Text300 = ""
    primary_cta: Cta | None = None
    secondary_cta: Cta | None = None
    trust: list[TrustItem] = Field(default_factory=list, max_length=4)
    theme: Theme = "blush"
    layout: Literal["image-right", "image-left"] = "image-right"


class CategoryGridSettings(Strict):
    eyebrow: Text40 = ""
    category_ids: list[UUID] = Field(default_factory=list, max_length=12)  # empty = top level
    layout: Literal["bento", "grid"] = "bento"
    show_view_all: bool = True


class ProductSectionSettings(Strict):
    eyebrow: Text40 = ""
    cta: Cta | None = None
    theme: Theme = "ivory"
    columns_desktop: Literal[3, 4] = 4


class EditorialBannerSettings(Strict):
    eyebrow: Text40 = ""
    body: Text400 = ""
    cta: Cta | None = None
    theme: Theme = "navy"
    image_position: Literal["left", "right"] = "right"


class CollectionShowcaseSettings(Strict):
    eyebrow: Text40 = ""
    collection_ids: list[UUID] = Field(default_factory=list, max_length=6)
    layout: Literal["tiles", "row"] = "tiles"


class OccasionSettings(Strict):
    eyebrow: Text40 = ""
    body: Text300 = ""
    cta: Cta | None = None
    theme: Theme = "blush"


class TrustStripItem(Strict):
    icon: IconName = "sparkles"
    title: Text40Req
    text: Text140 = ""


class TrustStripSettings(Strict):
    items: list[TrustStripItem] = Field(default_factory=list, max_length=6)


class Testimonial(Strict):
    quote: Text400Req
    author: Text60Req
    context: Text60 = ""


class TestimonialsSettings(Strict):
    """Only genuine, customer-approved reviews belong here; the admin UI says so."""

    items: list[Testimonial] = Field(default_factory=list, max_length=12)


class FaqItem(Strict):
    question: Text160Req
    answer: Text1000Req


class FaqSettings(Strict):
    items: list[FaqItem] = Field(default_factory=list, max_length=20)


class AnnouncementSettings(Strict):
    message: Text140Req
    link: Cta | None = None
    theme: Theme = "navy"


class ContactSettings(Strict):
    body: Text300 = ""
    show_whatsapp: bool = True
    show_phone: bool = True
    show_email: bool = True


class RichTextSettings(Strict):
    body: Text5000Req
    alignment: Literal["left", "center"] = "center"


SECTION_SETTINGS: dict[HomepageSectionType, type[Strict]] = {
    HomepageSectionType.HERO_BANNER: HeroSettings,
    HomepageSectionType.CATEGORY_GRID: CategoryGridSettings,
    HomepageSectionType.PRODUCT_CAROUSEL: ProductSectionSettings,
    HomepageSectionType.PRODUCT_GRID: ProductSectionSettings,
    HomepageSectionType.EDITORIAL_BANNER: EditorialBannerSettings,
    HomepageSectionType.PROMO_BANNER: EditorialBannerSettings,
    HomepageSectionType.COLLECTION_SHOWCASE: CollectionShowcaseSettings,
    HomepageSectionType.OCCASION_COLLECTION: OccasionSettings,
    HomepageSectionType.TRUST_STRIP: TrustStripSettings,
    HomepageSectionType.TESTIMONIALS: TestimonialsSettings,
    HomepageSectionType.FAQ: FaqSettings,
    HomepageSectionType.ANNOUNCEMENT: AnnouncementSettings,
    HomepageSectionType.CONTACT: ContactSettings,
    HomepageSectionType.RICH_TEXT: RichTextSettings,
}


def _validate(model: type[BaseModel], raw: Any, label: str) -> dict[str, Any]:
    try:
        return model.model_validate(raw).model_dump(mode="json", exclude_none=True)
    except ValidationError as exc:
        first = exc.errors()[0]
        location = ".".join(str(part) for part in first["loc"]) or label
        raise DomainValidationError(f"Invalid {label} ({location}): {first['msg']}") from exc


def validate_section_settings(
    section_type: HomepageSectionType, raw: dict[str, Any]
) -> dict[str, Any]:
    return _validate(SECTION_SETTINGS[section_type], raw, f"{section_type} settings")


# --- Store settings groups --------------------------------------------------------------------


class ThemeColours(Strict):
    """Overrides for the storefront brand tokens; empty means "use the default palette"."""

    navy: HexColour | None = None
    ivory: HexColour | None = None
    blush: HexColour | None = None
    coral: HexColour | None = None
    gold: HexColour | None = None


class AnnouncementBar(Strict):
    enabled: bool = False
    message: Text140 = ""
    link_label: Text40 = ""
    link_href: str | None = Field(default=None, max_length=500)

    _href = field_validator("link_href")(safe_href)


class PaymentOption(Strict):
    """Offline payment methods only (no gateway): shown to customers as instructions."""

    method: PaymentMethod
    enabled: bool = True
    label: Text60Req
    instructions: Text300 = ""


class PaymentOptions(Strict):
    options: list[PaymentOption] = Field(default_factory=list, max_length=6)


class SocialLinks(Strict):
    instagram: str | None = Field(default=None, max_length=300)
    facebook: str | None = Field(default=None, max_length=300)
    youtube: str | None = Field(default=None, max_length=300)
    pinterest: str | None = Field(default=None, max_length=300)

    @field_validator("instagram", "facebook", "youtube", "pinterest")
    @classmethod
    def _https(cls, value: str | None) -> str | None:
        if not value:
            return None
        if not value.startswith("https://"):
            raise ValueError("Social links must be https:// URLs.")
        return value


class SeoDefaults(Strict):
    title_suffix: Text60 = ""
    default_description: Text320 = ""
    og_image_media_id: UUID | None = None


def validate_theme(raw: Any) -> dict[str, Any]:
    return _validate(ThemeColours, raw, "theme colours")


def validate_announcement(raw: Any) -> dict[str, Any]:
    data = _validate(AnnouncementBar, raw, "announcement")
    if data.get("enabled") and not data.get("message"):
        raise DomainValidationError("An enabled announcement needs a message.")
    return data


def validate_payment_options(raw: Any) -> list[dict[str, Any]]:
    data = _validate(PaymentOptions, {"options": raw}, "payment options")
    methods = [o["method"] for o in data["options"]]
    if len(set(methods)) != len(methods):
        raise DomainValidationError("Each payment method can be listed only once.")
    return list(data["options"])


def validate_social_links(raw: Any) -> dict[str, Any]:
    return _validate(SocialLinks, raw, "social links")


def validate_seo_defaults(raw: Any) -> dict[str, Any]:
    return _validate(SeoDefaults, raw, "SEO defaults")


# --- Website page blocks ----------------------------------------------------------------------


class HeadingBlock(Strict):
    type: Literal["heading"]
    text: Text160Req
    level: Literal[2, 3] = 2


class ParagraphBlock(Strict):
    type: Literal["paragraph"]
    text: Text4000Req


class ListBlock(Strict):
    type: Literal["list"]
    ordered: bool = False
    items: list[Text300Req] = Field(min_length=1, max_length=40)


class FaqBlock(Strict):
    type: Literal["faq"]
    items: list[FaqItem] = Field(min_length=1, max_length=40)


class CalloutBlock(Strict):
    type: Literal["callout"]
    text: Text600Req


Block = Annotated[
    HeadingBlock | ParagraphBlock | ListBlock | FaqBlock | CalloutBlock,
    Field(discriminator="type"),
]


class PageContent(Strict):
    blocks: list[Block] = Field(default_factory=list, max_length=100)


def validate_page_content(raw: Any) -> dict[str, Any]:
    return _validate(PageContent, raw, "page content")


# --- Size charts ------------------------------------------------------------------------------


class SizeChartData(Strict):
    unit: Literal["cm", "in"] = "cm"
    columns: list[Text30Req] = Field(min_length=2, max_length=8)
    rows: list[list[Text30]] = Field(min_length=1, max_length=30)

    @field_validator("rows")
    @classmethod
    def _row_width(cls, rows: list[list[str]], info: Any) -> list[list[str]]:
        columns = info.data.get("columns") or []
        if any(len(row) != len(columns) for row in rows):
            raise ValueError("Every row must have one value per column.")
        return rows


def validate_size_chart(raw: Any) -> dict[str, Any]:
    return _validate(SizeChartData, raw, "size chart")


# --- Shipping & order policies ------------------------------------------------------------------

PinPrefix = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[1-9][0-9]{0,5}$")]
PinCode = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[1-9][0-9]{5}$")]


class ShippingSettings(Strict):
    """Shop-configured delivery rules. There is no live courier integration: any delivery
    time shown to customers is the shop's own estimate and is labelled as such."""

    free_shipping_threshold: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2
    )
    pin_mode: Literal["all", "allow_list"] = "all"
    allowed_pin_prefixes: list[PinPrefix] = Field(default_factory=list, max_length=500)
    blocked_pin_codes: list[PinCode] = Field(default_factory=list, max_length=500)
    shipping_message: Text300 = ""
    delivery_estimate: Text140 = ""
    unserviceable_message: Text300 = ""


DEFAULT_REASONS = ["Wrong size", "Damaged or defective", "Received a different item", "Other"]


class OrderPolicies(Strict):
    """Which after-sale requests customers may raise from their order history."""

    cancellation_enabled: bool = False
    cancellable_statuses: list[OrderStatus] = Field(
        default_factory=lambda: [OrderStatus.PENDING_CONFIRMATION, OrderStatus.CONFIRMED],
        max_length=8,
    )
    returns_enabled: bool = False
    exchanges_enabled: bool = False
    return_window_days: int = Field(default=7, ge=0, le=90)
    reasons: list[Text40Req] = Field(default_factory=lambda: list(DEFAULT_REASONS), max_length=12)
    policy_note: Text300 = ""


def validate_shipping_settings(raw: Any) -> dict[str, Any]:
    data = _validate(ShippingSettings, raw, "shipping settings")
    if data.get("pin_mode") == "allow_list" and not data.get("allowed_pin_prefixes"):
        raise DomainValidationError("Add at least one PIN-code prefix, or deliver everywhere.")
    return data


def validate_order_policies(raw: Any) -> dict[str, Any]:
    return _validate(OrderPolicies, raw, "order policies")


def shipping_settings(raw: dict[str, Any] | None) -> ShippingSettings:
    """Stored settings as a typed object (defaults for anything missing)."""
    try:
        return ShippingSettings.model_validate(raw or {})
    except ValidationError:
        return ShippingSettings()


def order_policies(raw: dict[str, Any] | None) -> OrderPolicies:
    try:
        return OrderPolicies.model_validate(raw or {})
    except ValidationError:
        return OrderPolicies()


def pin_serviceable(settings: ShippingSettings, postal_code: str) -> bool:
    pin = postal_code.replace(" ", "")
    if pin in settings.blocked_pin_codes:
        return False
    if settings.pin_mode == "allow_list":
        return any(pin.startswith(prefix) for prefix in settings.allowed_pin_prefixes)
    return True
