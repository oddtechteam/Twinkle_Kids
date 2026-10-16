from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

from app.domain.entities.identity import MAX_PASSWORD_LENGTH, User

Phone = Annotated[
    str, StringConstraints(strip_whitespace=True, pattern=r"^\+?[0-9][0-9 \-]{6,18}$")
]


class RegisterIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)
    full_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
    ]
    phone: Phone | None = None


class LoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)


class UserOut(BaseModel):
    """Public profile. Never includes the password hash or session data."""

    id: UUID
    email: str
    full_name: str
    phone: str | None
    roles: list[str]
    is_staff: bool
    created_at: datetime | None

    @classmethod
    def of(cls, user: User) -> "UserOut":
        return cls(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            phone=user.phone,
            roles=sorted(user.roles),
            is_staff=user.is_staff,
            created_at=user.created_at,
        )


class AdminMeOut(UserOut):
    permissions: list[str]

    @classmethod
    def of(cls, user: User) -> "AdminMeOut":
        return cls(**UserOut.of(user).model_dump(), permissions=sorted(user.permissions))
