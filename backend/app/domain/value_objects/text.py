import re
import unicodedata

from app.domain.errors import DomainValidationError

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SKU_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._-]{0,63}$")
MAX_SLUG_LENGTH = 160


def slugify(value: str) -> str:
    normalised = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", normalised.lower()).strip("-")
    return slug[:MAX_SLUG_LENGTH].rstrip("-")


def validate_slug(value: str) -> str:
    slug = value.strip().lower()
    if not slug or len(slug) > MAX_SLUG_LENGTH or not SLUG_PATTERN.fullmatch(slug):
        raise DomainValidationError(
            "Slug must contain only lowercase letters, numbers and single hyphens."
        )
    return slug


def validate_sku(value: str) -> str:
    sku = value.strip().upper()
    if not SKU_PATTERN.fullmatch(sku):
        raise DomainValidationError(
            "SKU must be 1-64 characters: letters, numbers, dots, dashes or underscores."
        )
    return sku


def normalise_email(value: str) -> str:
    return value.strip().lower()


def clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
