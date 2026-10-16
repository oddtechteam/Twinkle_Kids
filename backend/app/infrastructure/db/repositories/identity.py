from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.domain.entities.identity import AuthSession, Role, User
from app.infrastructure.db.models.identity import (
    AuditLogModel,
    RoleModel,
    UserModel,
    UserRoleModel,
    UserSessionModel,
)


class RolesNotSeededError(RuntimeError):
    pass


def _user_to_entity(row: UserModel) -> User:
    return User(
        id=row.id,
        email=row.email,
        full_name=row.full_name,
        password_hash=row.password_hash,
        phone=row.phone,
        is_active=row.is_active,
        roles=frozenset(role.slug for role in row.roles),
        permissions=frozenset(perm.code for role in row.roles for perm in role.permissions),
        created_at=row.created_at,
        last_login_at=row.last_login_at,
    )


class SqlAlchemyUserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, user_id: UUID) -> User | None:
        row = self._session.get(UserModel, user_id)
        return _user_to_entity(row) if row else None

    def get_by_email(self, email: str) -> User | None:
        row = self._session.scalars(select(UserModel).where(UserModel.email == email)).first()
        return _user_to_entity(row) if row else None

    def add(self, user: User, roles: set[Role]) -> None:
        self._session.add(
            UserModel(
                id=user.id,
                email=user.email,
                password_hash=user.password_hash,
                full_name=user.full_name,
                phone=user.phone,
                is_active=user.is_active,
            )
        )
        self._session.flush()
        self.assign_roles(user.id, roles)

    def assign_roles(self, user_id: UUID, roles: set[Role]) -> None:
        if not roles:
            return
        slugs = {role.value for role in roles}
        found = {
            r.slug: r.id
            for r in self._session.scalars(select(RoleModel).where(RoleModel.slug.in_(slugs)))
        }
        missing = slugs - found.keys()
        if missing:
            raise RolesNotSeededError(
                f"Roles {sorted(missing)} are missing; run `alembic upgrade head`."
            )
        current = set(
            self._session.scalars(
                select(UserRoleModel.role_id).where(UserRoleModel.user_id == user_id)
            )
        )
        for role_id in found.values():
            if role_id not in current:
                self._session.add(UserRoleModel(user_id=user_id, role_id=role_id))
        self._session.flush()
        row = self._session.get(UserModel, user_id)
        if row is not None:
            self._session.refresh(row, attribute_names=["roles"])

    def record_login(self, user_id: UUID, at: datetime) -> None:
        self._session.execute(
            update(UserModel).where(UserModel.id == user_id).values(last_login_at=at)
        )

    def update_password_hash(self, user_id: UUID, password_hash: str) -> None:
        self._session.execute(
            update(UserModel).where(UserModel.id == user_id).values(password_hash=password_hash)
        )


class SqlAlchemySessionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, auth_session: AuthSession, *, ip: str | None, user_agent: str | None) -> None:
        self._session.add(
            UserSessionModel(
                id=auth_session.id,
                user_id=auth_session.user_id,
                token_hash=auth_session.token_hash,
                created_at=auth_session.created_at,
                expires_at=auth_session.expires_at,
                ip_address=ip[:45] if ip else None,
                user_agent=user_agent[:255] if user_agent else None,
            )
        )
        self._session.flush()

    def get_by_token_hash(self, token_hash: str) -> AuthSession | None:
        row = self._session.scalars(
            select(UserSessionModel).where(UserSessionModel.token_hash == token_hash)
        ).first()
        if row is None:
            return None
        return AuthSession(
            id=row.id,
            user_id=row.user_id,
            token_hash=row.token_hash,
            created_at=row.created_at,
            expires_at=row.expires_at,
            revoked_at=row.revoked_at,
        )

    def revoke(self, session_id: UUID, at: datetime) -> None:
        self._session.execute(
            update(UserSessionModel)
            .where(UserSessionModel.id == session_id, UserSessionModel.revoked_at.is_(None))
            .values(revoked_at=at)
        )

    def revoke_all_for_user(self, user_id: UUID, at: datetime) -> None:
        self._session.execute(
            update(UserSessionModel)
            .where(UserSessionModel.user_id == user_id, UserSessionModel.revoked_at.is_(None))
            .values(revoked_at=at)
        )


class SqlAlchemyAuditLogRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def record(
        self,
        *,
        actor_user_id: UUID | None,
        action: str,
        entity_type: str,
        entity_id: str | None,
        changes: dict[str, Any] | None = None,
        ip: str | None = None,
    ) -> None:
        self._session.add(
            AuditLogModel(
                actor_user_id=actor_user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                changes=changes,
                ip_address=ip[:45] if ip else None,
            )
        )
