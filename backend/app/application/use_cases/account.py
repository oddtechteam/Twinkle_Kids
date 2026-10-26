"""Customer self-service: password reset, profile, password change and the address book.

Password reset uses a single-use, 256-bit random token delivered by email. Only its SHA-256 is
stored, it expires quickly, requesting a new one invalidates older links, and using it signs
the account out everywhere. The request endpoint answers identically whether or not the email
belongs to an account, so it cannot be used to discover customers.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.application.ports import PasswordHasher, RateLimiter
from app.application.use_cases.notifications import Notifier
from app.core.security import hash_token, new_token
from app.domain.entities.address import MAX_ADDRESSES, PostalAddress, SavedAddress, validate_phone
from app.domain.entities.identity import PasswordResetToken, User, validate_password
from app.domain.errors import (
    AuthenticationError,
    DomainValidationError,
    NotFoundError,
    RateLimitedError,
)
from app.domain.repositories.identity import (
    AddressRepository,
    AuditLogRepository,
    PasswordResetRepository,
    SessionRepository,
    UserRepository,
)
from app.domain.repositories.media import UnitOfWork
from app.domain.value_objects.text import clean_optional, normalise_email

RESET_REQUESTS_PER_IP = 10
RESET_REQUESTS_PER_EMAIL = 3
RESET_WINDOW_SECONDS = 60 * 60


@dataclass(frozen=True, slots=True)
class AccountPolicy:
    reset_ttl: timedelta = timedelta(minutes=30)
    storefront_url: str = "http://localhost:3000"
    store_name: str = "Twinkle Kids"


class AccountService:
    def __init__(
        self,
        *,
        users: UserRepository,
        sessions: SessionRepository,
        resets: PasswordResetRepository,
        addresses: AddressRepository,
        audit: AuditLogRepository,
        uow: UnitOfWork,
        hasher: PasswordHasher,
        rate_limiter: RateLimiter,
        notifier: Notifier,
        policy: AccountPolicy,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._resets = resets
        self._addresses = addresses
        self._audit = audit
        self._uow = uow
        self._hasher = hasher
        self._limiter = rate_limiter
        self._notifier = notifier
        self._policy = policy
        self._clock = clock

    # --- password reset --------------------------------------------------------------------

    def request_password_reset(self, email: str, *, ip: str | None) -> None:
        email = normalise_email(email)
        self._limit(f"reset:ip:{ip}", RESET_REQUESTS_PER_IP)
        self._limit(f"reset:email:{email}", RESET_REQUESTS_PER_EMAIL)
        user = self._users.get_by_email(email)
        if user is None or not user.is_active:
            return  # same outcome as success: no account enumeration

        now = self._clock()
        self._resets.invalidate_for_user(user.id, now)
        token = new_token()
        self._resets.add(
            PasswordResetToken(
                id=uuid4(), user_id=user.id, expires_at=now + self._policy.reset_ttl
            ),
            token_hash=hash_token(token),
            requested_ip=ip,
        )
        self._audit.record(
            actor_user_id=user.id,
            action="user.password_reset_requested",
            entity_type="user",
            entity_id=str(user.id),
            ip=ip,
        )
        self._uow.commit()

        minutes = int(self._policy.reset_ttl.total_seconds() // 60)
        link = f"{self._policy.storefront_url.rstrip('/')}/account/reset-password?token={token}"
        self._notifier.email(
            template="password_reset",
            entity_type="user",
            entity_id=str(user.id),
            to=user.email,
            subject=f"Reset your {self._policy.store_name} password",
            text=(
                f"Hello {user.full_name.split(' ')[0]},\n\n"
                f"We received a request to reset the password for your {self._policy.store_name} "
                f"account. Use this link within {minutes} minutes:\n\n{link}\n\n"
                "If you didn't ask for this, you can ignore this email — your password stays "
                "the same."
            ),
        )
        self._uow.commit()  # persist the delivery record

    def reset_password(self, token: str, new_password: str, *, ip: str | None) -> None:
        self._limit(f"reset-confirm:ip:{ip}", RESET_REQUESTS_PER_IP * 2)
        now = self._clock()
        record = self._resets.get_by_hash(hash_token(token)) if token else None
        if record is None or not record.is_usable(now):
            raise DomainValidationError(
                "This reset link is invalid or has expired. Please request a new one."
            )
        user = self._users.get(record.user_id)
        if user is None or not user.is_active:
            raise DomainValidationError(
                "This reset link is invalid or has expired. Please request a new one."
            )
        validate_password(new_password, email=user.email)
        self._users.update_password_hash(user.id, self._hasher.hash(new_password))
        self._resets.mark_used(record.id, now)
        self._resets.invalidate_for_user(user.id, now)
        self._sessions.revoke_all_for_user(user.id, now)  # sign out every device
        self._audit.record(
            actor_user_id=user.id,
            action="user.password_reset",
            entity_type="user",
            entity_id=str(user.id),
            ip=ip,
        )
        self._uow.commit()

    # --- profile ---------------------------------------------------------------------------

    def update_profile(self, user: User, *, full_name: str, phone: str | None) -> User:
        name = " ".join(full_name.split())
        if not name:
            raise DomainValidationError("Full name is required.")
        if len(name) > 120:
            raise DomainValidationError("Full name is too long.")
        cleaned_phone = clean_optional(phone)
        if cleaned_phone is not None:
            cleaned_phone = validate_phone(cleaned_phone)
        self._users.update_profile(user.id, full_name=name, phone=cleaned_phone)
        self._audit.record(
            actor_user_id=user.id,
            action="user.profile_updated",
            entity_type="user",
            entity_id=str(user.id),
        )
        self._uow.commit()
        updated = self._users.get(user.id)
        assert updated is not None  # noqa: S101 - the signed-in user exists
        return updated

    def change_password(
        self, user: User, *, current_password: str, new_password: str, session_id: UUID
    ) -> None:
        self._limit(f"change-password:{user.id}", 10)
        if not self._hasher.verify(user.password_hash, current_password):
            raise AuthenticationError("Your current password is incorrect.")
        validate_password(new_password, email=user.email)
        self._users.update_password_hash(user.id, self._hasher.hash(new_password))
        self._sessions.revoke_others_for_user(user.id, session_id, self._clock())
        self._audit.record(
            actor_user_id=user.id,
            action="user.password_changed",
            entity_type="user",
            entity_id=str(user.id),
        )
        self._uow.commit()

    # --- address book ----------------------------------------------------------------------

    def addresses(self, user_id: UUID) -> list[SavedAddress]:
        return self._addresses.list(user_id)

    def add_address(
        self, user_id: UUID, address: PostalAddress, *, label: str | None, make_default: bool
    ) -> SavedAddress:
        existing = self._addresses.list(user_id)
        if len(existing) >= MAX_ADDRESSES:
            raise DomainValidationError(f"You can save up to {MAX_ADDRESSES} addresses.")
        address.validate()
        default = make_default or not existing  # the first address becomes the default
        if default:
            self._addresses.clear_default(user_id)
        saved = SavedAddress(
            id=uuid4(),
            user_id=user_id,
            address=address,
            label=_label(label),
            is_default=default,
        )
        self._addresses.add(saved)
        self._uow.commit()
        return saved

    def update_address(
        self,
        user_id: UUID,
        address_id: UUID,
        address: PostalAddress,
        *,
        label: str | None,
        make_default: bool,
    ) -> SavedAddress:
        current = self._owned(user_id, address_id)
        address.validate()
        if make_default and not current.is_default:
            self._addresses.clear_default(user_id)
        updated = SavedAddress(
            id=current.id,
            user_id=user_id,
            address=address,
            label=_label(label),
            is_default=current.is_default or make_default,
        )
        self._addresses.save(updated)
        self._uow.commit()
        return updated

    def delete_address(self, user_id: UUID, address_id: UUID) -> None:
        current = self._owned(user_id, address_id)
        self._addresses.delete(current.id)
        if current.is_default:  # promote the next address so there is always a default
            remaining = [a for a in self._addresses.list(user_id) if a.id != current.id]
            if remaining:
                promoted = remaining[0]
                promoted.is_default = True
                self._addresses.save(promoted)
        self._uow.commit()

    def owned_address(self, user_id: UUID, address_id: UUID) -> SavedAddress:
        return self._owned(user_id, address_id)

    def _owned(self, user_id: UUID, address_id: UUID) -> SavedAddress:
        found = self._addresses.get(address_id)
        if found is None or found.user_id != user_id:  # never reveal other customers' data
            raise NotFoundError("Address not found.")
        return found

    def _limit(self, key: str, limit: int) -> None:
        retry_after = self._limiter.hit(key, limit=limit, window_seconds=RESET_WINDOW_SECONDS)
        if retry_after is not None:
            raise RateLimitedError("Too many attempts. Please try again later.", retry_after)


def _label(value: str | None) -> str | None:
    label = clean_optional(value)
    if label is not None and len(label) > 40:
        raise DomainValidationError("Address label is too long (40 characters max).")
    return label
