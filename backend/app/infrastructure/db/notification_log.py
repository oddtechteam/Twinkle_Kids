"""SQLAlchemy NotificationLog (delivery attempts; no message bodies)."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.application.dto.catalog import Page
from app.application.use_cases.notifications import NotificationRecord
from app.domain.enums import NotificationChannel, NotificationStatus
from app.infrastructure.db.models.commerce import NotificationModel

N = NotificationModel


class SqlAlchemyNotificationLog:
    def __init__(self, session: Session) -> None:
        self._session = session

    def record(self, entry: NotificationRecord) -> None:
        self._session.add(
            N(
                id=entry.id,
                channel=entry.channel.value,
                template=entry.template,
                recipient=entry.recipient,
                subject=entry.subject,
                status=entry.status.value,
                provider=entry.provider,
                provider_message_id=entry.provider_message_id,
                error=entry.error,
                entity_type=entry.entity_type,
                entity_id=entry.entity_id,
            )
        )

    def list(
        self, *, status: NotificationStatus | None, page: int, page_size: int
    ) -> Page[NotificationRecord]:
        stmt = select(N)
        if status is not None:
            stmt = stmt.where(N.status == status.value)
        total = self._session.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = self._session.scalars(
            stmt.order_by(N.created_at.desc()).limit(page_size).offset((page - 1) * page_size)
        )
        return Page(
            items=[
                NotificationRecord(
                    id=r.id,
                    channel=NotificationChannel(r.channel),
                    template=r.template,
                    recipient=r.recipient,
                    subject=r.subject,
                    status=NotificationStatus(r.status),
                    provider=r.provider,
                    provider_message_id=r.provider_message_id,
                    error=r.error,
                    entity_type=r.entity_type,
                    entity_id=r.entity_id,
                    created_at=r.created_at,
                )
                for r in rows
            ],
            total=int(total or 0),
            page=page,
            page_size=page_size,
        )
