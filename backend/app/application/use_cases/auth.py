"""Registration, login, session validation, logout and initial-admin creation."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.application.ports import PasswordHasher, RateLimiter
from app.core.security import hash_token, new_token
from app.domain.entities.identity import (
    MIN_ADMIN_PASSWORD_LENGTH,
    AuthSession,
    Role,
    User,
    validate_password,
)
from app.domain.errors import (
    AuthenticationError,
    ConflictError,
    DomainValidationError,
    RateLimitedError,
)
from app.domain.repositories.identity import AuditLogRepository, SessionRepository, UserRepository
from app.domain.repositories.media import UnitOfWork
from app.domain.value_objects.text import clean_optional, normalise_email

INVALID_CREDENTIALS = "Invalid email or password."
_DUMMY_HASHES: dict[int, str] = {}


@dataclass(frozen=True, slots=True)
class AuthPolicy:
    session_ttl: timedelta = timedelta(days=14)
    login_attempts_per_ip: int = 30
    login_attempts_per_account: int = 5
    login_window_seconds: int = 15 * 60
    registrations_per_ip: int = 10
    registration_window_seconds: int = 60 * 60


@dataclass(frozen=True, slots=True)
class IssuedSession:
    token: str  # raw token: goes into the HttpOnly cookie, never stored or logged
    session: AuthSession
    user: User


@dataclass(frozen=True, slots=True)
class RequestContext:
    ip: str | None = None
    user_agent: str | None = None


class AuthService:
    def __init__(
        self,
        *,
        users: UserRepository,
        sessions: SessionRepository,
        audit: AuditLogRepository,
        uow: UnitOfWork,
        hasher: PasswordHasher,
        rate_limiter: RateLimiter,
        policy: AuthPolicy,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._audit = audit
        self._uow = uow
        self._hasher = hasher
        self._limiter = rate_limiter
        self._policy = policy
        self._clock = clock

    # --- commands --------------------------------------------------------------------------

    def register(
        self,
        *,
        email: str,
        password: str,
        full_name: str,
        phone: str | None,
        context: RequestContext,
    ) -> IssuedSession:
        self._limit(
            f"register:ip:{context.ip}",
            self._policy.registrations_per_ip,
            self._policy.registration_window_seconds,
        )
        email = normalise_email(email)
        name = full_name.strip()
        if not name:
            raise DomainValidationError("Full name is required.")
        validate_password(password, email=email)
        if self._users.get_by_email(email) is not None:
            raise ConflictError("An account with this email already exists.")

        user = User(
            id=uuid4(),
            email=email,
            full_name=name,
            password_hash=self._hasher.hash(password),
            phone=clean_optional(phone),
        )
        self._users.add(user, {Role.CUSTOMER})  # public sign-up can only ever create customers
        user = self._reload(user.id)  # roles/permissions as persisted
        self._audit.record(
            actor_user_id=user.id,
            action="user.registered",
            entity_type="user",
            entity_id=str(user.id),
            ip=context.ip,
        )
        issued = self._issue(user, context)
        self._uow.commit()
        return issued

    def login(self, *, email: str, password: str, context: RequestContext) -> IssuedSession:
        email = normalise_email(email)
        window = self._policy.login_window_seconds
        self._limit(f"login:ip:{context.ip}", self._policy.login_attempts_per_ip, window)
        account_key = f"login:account:{email}"
        self._limit(account_key, self._policy.login_attempts_per_account, window)

        user = self._users.get_by_email(email)
        if user is None:
            self._hasher.verify(self._dummy_hash(), password)  # equalise timing
            raise AuthenticationError(INVALID_CREDENTIALS)
        if not self._hasher.verify(user.password_hash, password) or not user.is_active:
            raise AuthenticationError(INVALID_CREDENTIALS)

        if self._hasher.needs_rehash(user.password_hash):
            self._users.update_password_hash(user.id, self._hasher.hash(password))
        now = self._clock()
        self._users.record_login(user.id, now)
        self._audit.record(
            actor_user_id=user.id,
            action="user.login",
            entity_type="user",
            entity_id=str(user.id),
            ip=context.ip,
        )
        issued = self._issue(user, context)  # fresh token every login: no session fixation
        self._uow.commit()
        self._limiter.reset(account_key)
        return issued

    def logout(self, token: str | None) -> None:
        if not token:
            return
        session = self._sessions.get_by_token_hash(hash_token(token))
        if session is not None and session.revoked_at is None:
            self._sessions.revoke(session.id, self._clock())
            self._uow.commit()

    def authenticate(self, token: str | None) -> tuple[User, AuthSession]:
        if not token:
            raise AuthenticationError("Not signed in.")
        session = self._sessions.get_by_token_hash(hash_token(token))
        if session is None or not session.is_valid(self._clock()):
            raise AuthenticationError("Your session has expired. Please sign in again.")
        user = self._users.get(session.user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Your session has expired. Please sign in again.")
        return user, session

    def create_admin(
        self, *, email: str, password: str, full_name: str, promote_existing: bool = False
    ) -> User:
        """Used by the `create-admin` CLI only — there is no HTTP route that creates staff."""
        email = normalise_email(email)
        validate_password(password, email=email, min_length=MIN_ADMIN_PASSWORD_LENGTH)
        existing = self._users.get_by_email(email)
        if existing is not None:
            if not promote_existing:
                raise ConflictError("A user with this email already exists (use --promote).")
            self._users.update_password_hash(existing.id, self._hasher.hash(password))
            self._users.assign_roles(existing.id, {Role.OWNER})
            self._sessions.revoke_all_for_user(existing.id, self._clock())
            user_id = existing.id
            action = "user.promoted_to_owner"
        else:
            user = User(
                id=uuid4(),
                email=email,
                full_name=full_name.strip() or "Store owner",
                password_hash=self._hasher.hash(password),
            )
            self._users.add(user, {Role.OWNER})
            user_id = user.id
            action = "user.admin_created"
        self._audit.record(
            actor_user_id=None, action=action, entity_type="user", entity_id=str(user_id)
        )
        self._uow.commit()
        return self._reload(user_id)

    # --- helpers ---------------------------------------------------------------------------

    def _reload(self, user_id: UUID) -> User:
        user = self._users.get(user_id)
        if user is None:  # pragma: no cover - only possible if the row vanished mid-request
            raise RuntimeError("User disappeared during the request.")
        return user

    def _issue(self, user: User, context: RequestContext) -> IssuedSession:
        token = new_token()
        now = self._clock()
        session = AuthSession(
            id=uuid4(),
            user_id=user.id,
            token_hash=hash_token(token),
            created_at=now,
            expires_at=now + self._policy.session_ttl,
        )
        self._sessions.add(session, ip=context.ip, user_agent=context.user_agent)
        return IssuedSession(token=token, session=session, user=user)

    def _limit(self, key: str, limit: int, window: int) -> None:
        retry_after = self._limiter.hit(key, limit=limit, window_seconds=window)
        if retry_after is not None:
            raise RateLimitedError("Too many attempts. Please try again later.", retry_after)

    def _dummy_hash(self) -> str:
        key = id(self._hasher)
        if key not in _DUMMY_HASHES:
            _DUMMY_HASHES[key] = self._hasher.hash(new_token())
        return _DUMMY_HASHES[key]
