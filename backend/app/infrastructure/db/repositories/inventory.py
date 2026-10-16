from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.enums import InventoryReason
from app.infrastructure.db.models.commerce import InventoryMovementModel


class SqlAlchemyInventoryLedger:
    def __init__(self, session: Session) -> None:
        self._session = session

    def record(
        self,
        *,
        variant_id: UUID,
        delta: int,
        stock_after: int,
        reason: InventoryReason,
        actor_user_id: UUID | None,
        note: str | None = None,
    ) -> None:
        self._session.add(
            InventoryMovementModel(
                variant_id=variant_id,
                quantity_delta=delta,
                stock_after=stock_after,
                reason=reason.value,
                actor_user_id=actor_user_id,
                note=note,
            )
        )
