"""SQLAlchemy StaffStore: staff accounts, role assignment and the audit trail."""

from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.application.dto.catalog import Page
from app.application.use_cases.staff import STAFF_ROLES, AuditEntry, StaffMember
from app.domain.entities.identity import Role
from app.infrastructure.db.models.identity import AuditLogModel, RoleModel, UserModel, UserRoleModel


class SqlAlchemyStaffStore:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _member(row: UserModel) -> StaffMember:
        return StaffMember(
            id=row.id,
            email=row.email,
            full_name=row.full_name,
            roles=sorted(r.slug for r in row.roles),
            is_active=row.is_active,
            last_login_at=row.last_login_at,
        )

    def staff(self) -> list[StaffMember]:
        staff_slugs = [r.value for r in STAFF_ROLES]
        rows = self._session.scalars(
            select(UserModel)
            .join(UserRoleModel, UserRoleModel.user_id == UserModel.id)
            .join(RoleModel, RoleModel.id == UserRoleModel.role_id)
            .where(RoleModel.slug.in_(staff_slugs))
            .distinct()
            .order_by(UserModel.full_name)
        )
        return [self._member(r) for r in rows]

    def by_email(self, email: str) -> StaffMember | None:
        row = self._session.scalars(select(UserModel).where(UserModel.email == email)).first()
        return self._member(row) if row else None

    def get(self, user_id: UUID) -> StaffMember | None:
        row = self._session.get(UserModel, user_id)
        if row is None:
            return None
        self._session.refresh(row, attribute_names=["roles"])
        return self._member(row)

    def set_staff_roles(self, user_id: UUID, roles: set[Role]) -> None:
        staff_ids = {
            r.slug: r.id
            for r in self._session.scalars(
                select(RoleModel).where(RoleModel.slug.in_([r.value for r in STAFF_ROLES]))
            )
        }
        self._session.execute(
            delete(UserRoleModel).where(
                UserRoleModel.user_id == user_id,
                UserRoleModel.role_id.in_(list(staff_ids.values())),
            )
        )
        for role in roles:
            self._session.add(UserRoleModel(user_id=user_id, role_id=staff_ids[role.value]))
        self._session.flush()

    def owners_count(self) -> int:
        return int(
            self._session.scalar(
                select(func.count())
                .select_from(UserRoleModel)
                .join(RoleModel, RoleModel.id == UserRoleModel.role_id)
                .join(UserModel, UserModel.id == UserRoleModel.user_id)
                .where(RoleModel.slug == Role.OWNER.value, UserModel.is_active.is_(True))
            )
            or 0
        )

    def audit(
        self, *, action: str | None, entity_type: str | None, page: int, page_size: int
    ) -> Page[AuditEntry]:
        stmt = select(AuditLogModel, UserModel.email).outerjoin(
            UserModel, UserModel.id == AuditLogModel.actor_user_id
        )
        if action:
            stmt = stmt.where(AuditLogModel.action.ilike(f"{action}%"))
        if entity_type:
            stmt = stmt.where(AuditLogModel.entity_type == entity_type)
        total = self._session.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = self._session.execute(
            stmt.order_by(AuditLogModel.created_at.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        ).all()
        return Page(
            items=[
                AuditEntry(
                    id=str(row.id),
                    action=row.action,
                    entity_type=row.entity_type,
                    entity_id=row.entity_id,
                    actor_email=email,
                    changes=row.changes,
                    ip_address=row.ip_address,
                    created_at=row.created_at,
                )
                for row, email in rows
            ],
            total=int(total or 0),
            page=page,
            page_size=page_size,
        )
