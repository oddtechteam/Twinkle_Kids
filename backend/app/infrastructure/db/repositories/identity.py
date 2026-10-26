from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.domain.entities.address import PostalAddress, SavedAddress
from app.domain.entities.identity import AuthSession, PasswordResetToken, Role, User
from app.infrastructure.db.models.identity import (
    AddressModel,
    AuditLogModel,
    PasswordResetTokenModel,
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

    def update_profile(self, user_id: UUID, *, full_name: str, phone: str | None) -> None:
        self._session.execute(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(full_name=full_name, phone=phone)
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

    def revoke_others_for_user(self, user_id: UUID, keep_session_id: UUID, at: datetime) -> None:
        self._session.execute(
            update(UserSessionModel)
            .where(
                UserSessionModel.user_id == user_id,
                UserSessionModel.id != keep_session_id,
                UserSessionModel.revoked_at.is_(None),
            )
            .values(revoked_at=at)
        )


class SqlAlchemyPasswordResetRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, token: PasswordResetToken, *, token_hash: str, requested_ip: str | None) -> None:
        self._session.add(
            PasswordResetTokenModel(
                id=token.id,
                user_id=token.user_id,
                token_hash=token_hash,
                expires_at=token.expires_at,
                requested_ip=requested_ip[:45] if requested_ip else None,
            )
        )

    def get_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        row = self._session.scalars(
            select(PasswordResetTokenModel).where(PasswordResetTokenModel.token_hash == token_hash)
        ).first()
        if row is None:
            return None
        return PasswordResetToken(
            id=row.id, user_id=row.user_id, expires_at=row.expires_at, used_at=row.used_at
        )

    def mark_used(self, token_id: UUID, at: datetime) -> None:
        self._session.execute(
            update(PasswordResetTokenModel)
            .where(
                PasswordResetTokenModel.id == token_id, PasswordResetTokenModel.used_at.is_(None)
            )
            .values(used_at=at)
        )

    def invalidate_for_user(self, user_id: UUID, at: datetime) -> None:
        self._session.execute(
            update(PasswordResetTokenModel)
            .where(
                PasswordResetTokenModel.user_id == user_id,
                PasswordResetTokenModel.used_at.is_(None),
            )
            .values(used_at=at)
        )


def _address_to_entity(row: AddressModel) -> SavedAddress:
    return SavedAddress(
        id=row.id,
        user_id=row.user_id,
        label=row.label,
        is_default=row.is_default,
        address=PostalAddress(
            full_name=row.full_name,
            phone=row.phone,
            line1=row.line1,
            line2=row.line2,
            landmark=row.landmark,
            city=row.city,
            state=row.state,
            postal_code=row.postal_code,
            country_code=row.country_code,
        ),
    )


class SqlAlchemyAddressRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self, user_id: UUID) -> list[SavedAddress]:
        rows = self._session.scalars(
            select(AddressModel)
            .where(AddressModel.user_id == user_id)
            .order_by(AddressModel.is_default.desc(), AddressModel.created_at)
        )
        return [_address_to_entity(row) for row in rows]

    def get(self, address_id: UUID) -> SavedAddress | None:
        row = self._session.get(AddressModel, address_id)
        return _address_to_entity(row) if row else None

    def add(self, address: SavedAddress) -> None:
        a = address.address
        self._session.add(
            AddressModel(
                id=address.id,
                user_id=address.user_id,
                label=address.label,
                is_default=address.is_default,
                full_name=a.full_name,
                phone=a.phone,
                line1=a.line1,
                line2=a.line2,
                landmark=a.landmark,
                city=a.city,
                state=a.state,
                postal_code=a.postal_code,
                country_code=a.country_code,
            )
        )
        self._session.flush()

    def save(self, address: SavedAddress) -> None:
        row = self._session.get(AddressModel, address.id)
        if row is None:
            return
        a = address.address
        row.label = address.label
        row.is_default = address.is_default
        row.full_name = a.full_name
        row.phone = a.phone
        row.line1 = a.line1
        row.line2 = a.line2
        row.landmark = a.landmark
        row.city = a.city
        row.state = a.state
        row.postal_code = a.postal_code
        row.country_code = a.country_code
        self._session.flush()

    def delete(self, address_id: UUID) -> None:
        self._session.execute(delete(AddressModel).where(AddressModel.id == address_id))

    def clear_default(self, user_id: UUID) -> None:
        self._session.execute(
            update(AddressModel)
            .where(AddressModel.user_id == user_id, AddressModel.is_default.is_(True))
            .values(is_default=False)
        )
        self._session.flush()


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
