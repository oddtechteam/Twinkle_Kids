"""Application settings, loaded from environment variables and explicit .env files.

Secrets are never hardcoded here. Defaults are only safe, local-development values.

Env-file precedence (highest first):
  1. Real process environment variables (production hosts inject these).
  2. ``backend/.env``          — app configuration owned by this service.
  3. ``<repo>/.env.local``     — Neon-managed values written by ``neon deploy`` / ``neon env pull``
                                 (DATABASE_URL, DATABASE_URL_UNPOOLED, AWS_* storage credentials).
Paths are absolute, so the result does not depend on the working directory. Note that the
frontend never reads the repo-root ``.env.local`` (Next.js only loads ``frontend/.env*``), so
database and storage credentials cannot leak into browser bundles.
"""

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

Environment = Literal["development", "test", "staging", "production"]
StorageBackend = Literal["auto", "neon", "memory"]

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent
ENV_FILES = (REPO_ROOT / ".env.local", BACKEND_DIR / ".env")  # later files win

_INSECURE_DEV_SECRET = "dev-only-insecure-secret-change-me"  # noqa: S105 - placeholder, rejected in prod
_MIB = 1024 * 1024


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Twinkle Kids API"
    app_env: Environment = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # --- Database -------------------------------------------------------------------------
    # Local default is a SQLite file so the API boots without any credentials.
    # Neon supplies DATABASE_URL (pooled, for app traffic) and DATABASE_URL_UNPOOLED (direct,
    # for migrations and other session-level work).
    database_url: str = "sqlite:///./twinkle_dev.db"
    database_url_unpooled: str | None = None
    database_echo: bool = False
    # Written by `neon env pull`; used as a safety signal for migrations and seeding.
    neon_branch: str | None = None
    protected_neon_branches: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["production", "main"]
    )

    # --- Object storage (Neon Object Storage, S3-compatible) ------------------------------
    # Standard AWS variable names, exactly as injected by `neon deploy` / `neon env pull`.
    aws_access_key_id: str | None = None
    aws_secret_access_key: SecretStr | None = None
    aws_endpoint_url_s3: str | None = None
    aws_region: str | None = None

    # "auto" uses Neon when credentials are present, otherwise an in-memory store (dev/test).
    storage_backend: StorageBackend = "auto"
    storage_media_bucket: str = "media"  # public_read: storefront images
    storage_private_bucket: str = "assets"  # private: presigned access only
    # Optional CDN origin for public media, e.g. https://cdn.twinklekids.example
    media_public_base_url: str | None = None
    media_max_upload_bytes: int = Field(default=5 * _MIB, gt=0, le=50 * _MIB)

    # --- Security ---------------------------------------------------------------------------
    secret_key: SecretStr = SecretStr(_INSECURE_DEV_SECRET)
    docs_enabled: bool | None = None  # default: on outside production

    # Browser sessions: opaque random token in an HttpOnly cookie; only its hash is stored.
    session_cookie_name: str = "tk_session"
    csrf_cookie_name: str = "tk_csrf"
    session_ttl_hours: int = Field(default=14 * 24, ge=1, le=90 * 24)
    cookie_secure: bool | None = None  # default: true outside development/test
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    cookie_domain: str | None = None
    # Guest shopping bag: random token in an HttpOnly cookie; only its hash is stored.
    cart_cookie_name: str = "tk_cart"
    cart_ttl_days: int = Field(default=30, ge=1, le=365)

    # Login / registration throttling (per API process; see infrastructure/auth/rate_limit.py)
    login_max_attempts_per_account: int = Field(default=5, ge=1)
    login_max_attempts_per_ip: int = Field(default=30, ge=1)
    login_window_seconds: int = Field(default=15 * 60, ge=10)
    registration_max_per_ip_per_hour: int = Field(default=10, ge=1)

    # NoDecode: accept a plain comma-separated env value instead of requiring JSON.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )
    # Public storefront origin, used in links the API writes (e.g. WhatsApp order messages).
    storefront_url: str = "http://localhost:3000"

    @field_validator("cors_origins", "protected_neon_branches", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip().startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator(
        "database_url_unpooled",
        "aws_access_key_id",
        "aws_endpoint_url_s3",
        "aws_region",
        "media_public_base_url",
        "cookie_domain",
        mode="before",
    )
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def migration_database_url(self) -> str:
        """Direct (non-pooled) URL for Alembic; falls back to DATABASE_URL."""
        return self.database_url_unpooled or self.database_url

    @property
    def targets_production_data(self) -> bool:
        """True when this process points at production data (APP_ENV or a protected branch)."""
        return self.app_env == "production" or (
            self.neon_branch is not None and self.neon_branch in self.protected_neon_branches
        )

    @property
    def secure_cookies(self) -> bool:
        if self.cookie_secure is not None:
            return self.cookie_secure
        return self.app_env not in ("development", "test")

    @property
    def show_docs(self) -> bool:
        return self.docs_enabled if self.docs_enabled is not None else self.app_env != "production"

    @property
    def neon_storage_configured(self) -> bool:
        return bool(
            self.aws_access_key_id and self.aws_secret_access_key and self.aws_endpoint_url_s3
        )

    @property
    def resolved_storage_backend(self) -> Literal["neon", "memory"]:
        if self.storage_backend == "auto":
            return "neon" if self.neon_storage_configured else "memory"
        return self.storage_backend

    @model_validator(mode="after")
    def _validate(self) -> "Settings":
        if self.storage_backend == "neon" and not self.neon_storage_configured:
            raise ValueError(
                "STORAGE_BACKEND=neon requires AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY "
                "and AWS_ENDPOINT_URL_S3."
            )
        if self.cookie_samesite == "none" and not self.secure_cookies:
            raise ValueError("COOKIE_SAMESITE=none requires secure cookies (COOKIE_SECURE=true).")
        if self.app_env == "production":
            if self.secret_key.get_secret_value() == _INSECURE_DEV_SECRET:
                raise ValueError("SECRET_KEY must be set to a strong value in production.")
            if self.database_url.startswith("sqlite"):
                raise ValueError("DATABASE_URL must point to PostgreSQL in production.")
            if self.debug:
                raise ValueError("DEBUG must be false in production.")
            if self.resolved_storage_backend != "neon":
                raise ValueError("Production requires Neon Object Storage credentials.")
            if not self.secure_cookies:
                raise ValueError("COOKIE_SECURE cannot be false in production.")
            if "*" in self.cors_origins:
                raise ValueError("CORS_ORIGINS must list explicit origins in production.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
