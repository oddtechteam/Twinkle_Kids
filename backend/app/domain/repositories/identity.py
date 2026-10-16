from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from app.domain.entities.identity import AuthSession, Role, User


class UserRepository(Protocol):
    def get(self, user_id: UUID) -> User | None: ...

    def get_by_email(self, email: str) -> User | None: ...

    def add(self, user: User, roles: set[Role]) -> None: ...

    def assign_roles(self, user_id: UUID, roles: set[Role]) -> None: ...

    def record_login(self, user_id: UUID, at: datetime) -> None: ...

    def update_password_hash(self, user_id: UUID, password_hash: str) -> None: ...


class SessionRepository(Protocol):
    def add(self, session: AuthSession, *, ip: str | None, user_agent: str | None) -> None: ...

    def get_by_token_hash(self, token_hash: str) -> AuthSession | None: ...

    def revoke(self, session_id: UUID, at: datetime) -> None: ...

    def revoke_all_for_user(self, user_id: UUID, at: datetime) -> None: ...


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
