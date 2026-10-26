from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.domain.errors import DomainValidationError


class Permission(StrEnum):
    ADMIN_ACCESS = "admin:access"
    CATALOG_MANAGE = "catalog:manage"
    CONTENT_MANAGE = "content:manage"
    MEDIA_MANAGE = "media:manage"
    INVENTORY_MANAGE = "inventory:manage"
    ORDERS_MANAGE = "orders:manage"
    CUSTOMERS_MANAGE = "customers:manage"
    SETTINGS_MANAGE = "settings:manage"
    USERS_MANAGE = "users:manage"
    AUDIT_READ = "audit:read"


class Role(StrEnum):
    OWNER = "owner"
    CATALOG_MANAGER = "catalog_manager"
    ORDER_MANAGER = "order_manager"
    CUSTOMER = "customer"


# Authoritative role → permission grants. Seeded by migration 0003; a test keeps them in sync.
ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.OWNER: frozenset(Permission),
    Role.CATALOG_MANAGER: frozenset(
        {
            Permission.ADMIN_ACCESS,
            Permission.CATALOG_MANAGE,
            Permission.CONTENT_MANAGE,
            Permission.MEDIA_MANAGE,
            Permission.INVENTORY_MANAGE,
        }
    ),
    Role.ORDER_MANAGER: frozenset(
        {
            Permission.ADMIN_ACCESS,
            Permission.ORDERS_MANAGE,
            Permission.CUSTOMERS_MANAGE,
            Permission.INVENTORY_MANAGE,
        }
    ),
    Role.CUSTOMER: frozenset(),
}

MIN_PASSWORD_LENGTH = 10
MIN_ADMIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128


@dataclass(slots=True)
class User:
    id: UUID
    email: str
    full_name: str
    password_hash: str
    phone: str | None = None
    is_active: bool = True
    roles: frozenset[str] = field(default_factory=frozenset)
    permissions: frozenset[str] = field(default_factory=frozenset)
    created_at: datetime | None = None
    last_login_at: datetime | None = None

    def has_permission(self, permission: Permission) -> bool:
        return self.is_active and permission.value in self.permissions

    @property
    def is_staff(self) -> bool:
        return self.has_permission(Permission.ADMIN_ACCESS)


@dataclass(frozen=True, slots=True)
class AuthSession:
    id: UUID
    user_id: UUID
    token_hash: str
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None

    def is_valid(self, now: datetime) -> bool:
        return self.revoked_at is None and now < self.expires_at


def validate_password(password: str, *, email: str, min_length: int = MIN_PASSWORD_LENGTH) -> None:
    """Length-based policy (NIST SP 800-63B): long passphrases over composition rules."""
    if len(password) < min_length:
        raise DomainValidationError(f"Password must be at least {min_length} characters.")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise DomainValidationError(f"Password must be at most {MAX_PASSWORD_LENGTH} characters.")
    if len(set(password)) < 4:
        raise DomainValidationError("Password is too repetitive.")
    local_part = email.split("@", 1)[0].casefold()
    if len(local_part) >= 4 and local_part in password.casefold():
        raise DomainValidationError("Password must not contain your email address.")


@dataclass(frozen=True, slots=True)
class PasswordResetToken:
    id: UUID
    user_id: UUID
    expires_at: datetime
    used_at: datetime | None = None

    def is_usable(self, now: datetime) -> bool:
        return self.used_at is None and now < self.expires_at
