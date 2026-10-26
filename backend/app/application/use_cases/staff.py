"""Staff roles and the audit trail.

There is still no way to create an admin over HTTP: an owner can only grant staff roles to an
account that already exists (the person signs up as a customer first, or the CLI creates an
owner). Owners cannot change their own roles, the last owner can never be removed, and every
change is audited and signs the affected person out everywhere.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from app.application.dto.catalog import Page
from app.domain.entities.identity import Role, User
from app.domain.errors import (
    ConflictError,
    DomainValidationError,
    NotFoundError,
    PermissionDeniedError,
)
from app.domain.repositories.identity import AuditLogRepository, SessionRepository
from app.domain.repositories.media import UnitOfWork

STAFF_ROLES = frozenset({Role.OWNER, Role.CATALOG_MANAGER, Role.ORDER_MANAGER})
ROLE_LABELS = {
    Role.OWNER: "Super administrator",
    Role.CATALOG_MANAGER: "Catalogue manager",
    Role.ORDER_MANAGER: "Order manager",
}


@dataclass(frozen=True, slots=True)
class StaffMember:
    id: UUID
    email: str
    full_name: str
    roles: list[str]
    is_active: bool
    last_login_at: datetime | None


@dataclass(frozen=True, slots=True)
class AuditEntry:
    id: int | str
    action: str
    entity_type: str
    entity_id: str | None
    actor_email: str | None
    changes: dict[str, Any] | None
    ip_address: str | None
    created_at: datetime


class StaffStore(Protocol):
    def staff(self) -> list[StaffMember]: ...

    def by_email(self, email: str) -> StaffMember | None: ...

    def get(self, user_id: UUID) -> StaffMember | None: ...

    def set_staff_roles(self, user_id: UUID, roles: set[Role]) -> None:
        """Replace the user's staff roles (the customer role is left untouched)."""
        ...

    def owners_count(self) -> int: ...

    def audit(
        self, *, action: str | None, entity_type: str | None, page: int, page_size: int
    ) -> Page[AuditEntry]: ...


class StaffService:
    def __init__(
        self,
        *,
        store: StaffStore,
        sessions: SessionRepository,
        audit: AuditLogRepository,
        uow: UnitOfWork,
    ) -> None:
        self._store = store
        self._sessions = sessions
        self._audit = audit
        self._uow = uow

    def list(self) -> list[StaffMember]:
        return self._store.staff()

    def set_roles(self, *, email: str, roles: set[Role], actor: User) -> StaffMember:
        if roles - STAFF_ROLES:
            raise DomainValidationError("Only staff roles can be assigned here.")
        member = self._store.by_email(email.strip().lower())
        if member is None:
            raise NotFoundError(
                "No account uses that email. Ask the person to create an account first."
            )
        if member.id == actor.id:
            raise PermissionDeniedError("You can't change your own roles.")
        was_owner = Role.OWNER.value in member.roles
        if was_owner and Role.OWNER not in roles and self._store.owners_count() <= 1:
            raise ConflictError("The store needs at least one super administrator.")
        before = sorted(r for r in member.roles if r != Role.CUSTOMER.value)
        self._store.set_staff_roles(member.id, roles)
        self._sessions.revoke_all_for_user(
            member.id, datetime.now(UTC)
        )  # new permissions on next sign-in
        self._audit.record(
            actor_user_id=actor.id,
            action="user.roles_changed",
            entity_type="user",
            entity_id=str(member.id),
            changes={
                "email": member.email,
                "before": before,
                "after": sorted(r.value for r in roles),
            },
        )
        self._uow.commit()
        updated = self._store.get(member.id)
        assert updated is not None  # noqa: S101 - just updated
        return updated

    def audit_log(
        self, *, action: str | None, entity_type: str | None, page: int
    ) -> Page[AuditEntry]:
        return self._store.audit(
            action=action, entity_type=entity_type, page=max(1, page), page_size=50
        )
