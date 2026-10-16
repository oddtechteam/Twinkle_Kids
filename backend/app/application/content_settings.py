"""Per-type validation for homepage_sections.settings (stored as JSONB).

Only these documented keys are accepted (extra keys are rejected), so the storefront can render
any saved section without defensive guesswork.
"""

from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.domain.enums import HomepageSectionType
from app.domain.errors import DomainValidationError

HexColour = Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}$")]


def _safe_href(value: str | None) -> str | None:
    if value is None:
        return None
    if value.startswith("/") and not value.startswith("//"):
        return value
    if value.startswith("https://"):
        return value
    raise ValueError("Links must be site-relative (/path) or https:// URLs.")


class _Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class BannerSettings(_Settings):
    headline: str | None = Field(default=None, max_length=120)
    subheadline: str | None = Field(default=None, max_length=240)
    cta_label: str | None = Field(default=None, max_length=40)
    cta_href: str | None = Field(default=None, max_length=500)
    text_theme: Literal["light", "dark"] = "dark"
    overlay_opacity: float = Field(default=0.0, ge=0, le=0.8)
    background_colour: HexColour | None = None

    _href = field_validator("cta_href")(_safe_href)


class ProductSectionSettings(_Settings):
    show_view_all: bool = True
    view_all_href: str | None = Field(default=None, max_length=500)
    columns_desktop: int = Field(default=4, ge=2, le=6)
    columns_mobile: int = Field(default=2, ge=1, le=2)

    _href = field_validator("view_all_href")(_safe_href)


class CategoryGridSettings(_Settings):
    category_ids: list[UUID] = Field(default_factory=list, max_length=12)


class CollectionShowcaseSettings(_Settings):
    collection_ids: list[UUID] = Field(default_factory=list, max_length=8)


class RichTextSettings(_Settings):
    body: str = Field(max_length=5000)  # plain text / limited markdown, never raw HTML
    alignment: Literal["left", "center"] = "center"


SETTINGS_MODELS: dict[HomepageSectionType, type[_Settings]] = {
    HomepageSectionType.HERO_BANNER: BannerSettings,
    HomepageSectionType.PROMO_BANNER: BannerSettings,
    HomepageSectionType.PRODUCT_CAROUSEL: ProductSectionSettings,
    HomepageSectionType.PRODUCT_GRID: ProductSectionSettings,
    HomepageSectionType.CATEGORY_GRID: CategoryGridSettings,
    HomepageSectionType.COLLECTION_SHOWCASE: CollectionShowcaseSettings,
    HomepageSectionType.RICH_TEXT: RichTextSettings,
}


def validate_section_settings(
    section_type: HomepageSectionType, raw: dict[str, Any]
) -> dict[str, Any]:
    model = SETTINGS_MODELS[section_type]
    try:
        return model.model_validate(raw).model_dump(mode="json", exclude_none=True)
    except ValidationError as exc:
        first = exc.errors()[0]
        location = ".".join(str(part) for part in first["loc"]) or "settings"
        raise DomainValidationError(
            f"Invalid {section_type} settings ({location}): {first['msg']}"
        ) from exc
