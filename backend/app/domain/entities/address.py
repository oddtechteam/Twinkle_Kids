"""Postal addresses: the customer address book and the delivery address snapshot on orders."""

import re
from dataclasses import asdict, dataclass
from typing import Any
from uuid import UUID

from app.domain.errors import DomainValidationError

PHONE_PATTERN = re.compile(r"^\+?[0-9][0-9 \-]{6,18}$")
PIN_CODE_PATTERN = re.compile(r"^[1-9][0-9]{5}$")  # India Post PIN code
MAX_ADDRESSES = 10

_LIMITS = {
    "full_name": 120,
    "phone": 20,
    "line1": 200,
    "line2": 200,
    "landmark": 120,
    "city": 100,
    "state": 100,
    "postal_code": 12,
    "label": 40,
}


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = " ".join(value.split())
    return stripped or None


def validate_phone(value: str | None, *, field: str = "Phone number") -> str:
    phone = (value or "").strip()
    if not PHONE_PATTERN.fullmatch(phone) or sum(c.isdigit() for c in phone) < 8:
        raise DomainValidationError(f"{field} must be a valid mobile number (8–15 digits).")  # noqa: RUF001 - intended typography
    return phone


@dataclass(slots=True)
class PostalAddress:
    full_name: str
    phone: str
    line1: str
    city: str
    state: str
    postal_code: str
    line2: str | None = None
    landmark: str | None = None
    country_code: str = "IN"

    def validate(self) -> "PostalAddress":
        for name, limit in _LIMITS.items():
            if not hasattr(self, name):
                continue
            value = _clean(getattr(self, name))
            if value is not None and len(value) > limit:
                raise DomainValidationError(f"{name.replace('_', ' ').capitalize()} is too long.")
            setattr(self, name, value)
        for name, label in (
            ("full_name", "Name"),
            ("line1", "Address"),
            ("city", "City"),
            ("state", "State"),
        ):
            if not getattr(self, name):
                raise DomainValidationError(f"{label} is required.")
        self.phone = validate_phone(self.phone)
        self.country_code = (self.country_code or "IN").upper()
        if self.country_code != "IN":
            raise DomainValidationError("We currently deliver within India only.")
        postal = (self.postal_code or "").replace(" ", "")
        if not PIN_CODE_PATTERN.fullmatch(postal):
            raise DomainValidationError("Enter a valid 6-digit PIN code.")
        self.postal_code = postal
        return self

    def snapshot(self) -> dict[str, Any]:
        """Frozen copy stored on an order (later address-book edits never change it)."""
        return asdict(self)


@dataclass(slots=True)
class SavedAddress:
    id: UUID
    user_id: UUID
    address: PostalAddress
    label: str | None = None
    is_default: bool = False
