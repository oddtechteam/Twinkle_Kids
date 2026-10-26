from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from app.domain.entities.address import SavedAddress
from app.domain.entities.identity import AuthSession, PasswordResetToken, Role, User


class UserRepository(Protocol):
    def get(self, user_id: UUID) -> User | None: ...

    def get_by_email(self, email: str) -> User | None: ...

    def add(self, user: User, roles: set[Role]) -> None: ...

    def assign_roles(self, user_id: UUID, roles: set[Role]) -> None: ...

    def record_login(self, user_id: UUID, at: datetime) -> None: ...

    def update_password_hash(self, user_id: UUID, password_hash: str) -> None: ...

    def update_profile(self, user_id: UUID, *, full_name: str, phone: str | None) -> None: ...


class SessionRepository(Protocol):
    def add(self, session: AuthSession, *, ip: str | None, user_agent: str | None) -> None: ...

    def get_by_token_hash(self, token_hash: str) -> AuthSession | None: ...

    def revoke(self, session_id: UUID, at: datetime) -> None: ...

    def revoke_all_for_user(self, user_id: UUID, at: datetime) -> None: ...

    def revoke_others_for_user(self, user_id: UUID, keep_session_id: UUID, at: datetime) -> None:
        """Sign out every other device (e.g. after a password change)."""
        ...


class PasswordResetRepository(Protocol):
    def add(
        self,
        token: PasswordResetToken,
        *,
        token_hash: str,
        requested_ip: str | None,
    ) -> None: ...

    def get_by_hash(self, token_hash: str) -> PasswordResetToken | None: ...

    def mark_used(self, token_id: UUID, at: datetime) -> None: ...

    def invalidate_for_user(self, user_id: UUID, at: datetime) -> None:
        """Mark every outstanding token for the user as used (only the newest link works)."""
        ...


class AddressRepository(Protocol):
    def list(self, user_id: UUID) -> list[SavedAddress]: ...

    def get(self, address_id: UUID) -> SavedAddress | None: ...

    def add(self, address: SavedAddress) -> None: ...

    def save(self, address: SavedAddress) -> None: ...

    def delete(self, address_id: UUID) -> None: ...

    def clear_default(self, user_id: UUID) -> None: ...


class AuditLogRepository(Protocol):
    def record(
        self,
        *,
        actor_user_id: UUID | None,
        action: str,
        entity_type: str,
        entity_id: str | None,
        changes: dict[str, Any] | None = None,
        ip: str | None = None,
    ) -> None: ...
