"""Portable column types and mixins shared by all ORM models."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Dialect, Numeric, TypeDecorator, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

# JSONB on PostgreSQL (indexable, validated by the application layer), JSON elsewhere.
JSONType = JSON().with_variant(JSONB(), "postgresql")

# Money: fixed precision, never float. 10 digits of rupees + 2 of paise.
Money = Numeric(12, 2, asdecimal=True)


def utc_now() -> datetime:
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator[datetime]):
    """TIMESTAMP WITH TIME ZONE that only accepts aware datetimes and always returns UTC."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Naive datetimes are not allowed; use an aware UTC datetime.")
        return value.astimezone(UTC)

    def process_result_value(self, value: Any, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        moment: datetime = (
            datetime.fromisoformat(value) if isinstance(value, str) else value  # SQLite raw text
        )
        if moment.tzinfo is None:  # SQLite stores without offset; values are written as UTC
            return moment.replace(tzinfo=UTC)
        return moment.astimezone(UTC)


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


def created_at_column() -> Mapped[datetime]:
    return mapped_column(UTCDateTime, server_default=func.now(), default=utc_now)


def updated_at_column() -> Mapped[datetime]:
    return mapped_column(UTCDateTime, server_default=func.now(), default=utc_now, onupdate=utc_now)
