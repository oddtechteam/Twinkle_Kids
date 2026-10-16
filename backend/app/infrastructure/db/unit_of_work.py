import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.errors import ConflictError

logger = logging.getLogger(__name__)


class SqlAlchemyUnitOfWork:
    """Transaction boundary for one request/command.

    Constraint violations that slip past application checks (e.g. two concurrent requests
    claiming the same slug) surface as a ConflictError, never as a raw database error.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def flush(self) -> None:
        try:
            self._session.flush()
        except IntegrityError as exc:
            self._session.rollback()
            logger.info("Integrity error on flush: %s", exc.orig.__class__.__name__)
            raise ConflictError("The change conflicts with existing data.") from exc

    def commit(self) -> None:
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            logger.info("Integrity error on commit: %s", exc.orig.__class__.__name__)
            raise ConflictError("The change conflicts with existing data.") from exc

    def rollback(self) -> None:
        self._session.rollback()
