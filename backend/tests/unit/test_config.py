from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import BACKEND_DIR, ENV_FILES, REPO_ROOT, Settings

NEON_STORAGE = {
    "aws_access_key_id": "key-id",
    "aws_secret_access_key": "secret",
    "aws_endpoint_url_s3": "https://br-x.storage.c-6.us-east-2.aws.neon.tech",
}


PROD_SAFE = {
    "secret_key": "x" * 64,
    "database_url": "postgresql://u:p@h/db",
    "aws_access_key_id": "key-id",
    "aws_secret_access_key": "secret",
    "aws_endpoint_url_s3": "https://br-x.storage.c-6.us-east-2.aws.neon.tech",
}


def make(**kwargs: object) -> Settings:
    return Settings(_env_file=None, **kwargs)  # type: ignore[arg-type]


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in [
        "APP_ENV",
        "DATABASE_URL",
        "DATABASE_URL_UNPOOLED",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_ENDPOINT_URL_S3",
        "AWS_REGION",
        "STORAGE_BACKEND",
        "NEON_BRANCH",
        "COOKIE_SECURE",
    ]:
        monkeypatch.delenv(name, raising=False)


def test_defaults_boot_without_credentials() -> None:
    settings = make()
    assert settings.app_env == "development"
    assert settings.database_url.startswith("sqlite")
    assert settings.resolved_storage_backend == "memory"


def test_env_files_are_absolute_with_backend_env_last() -> None:
    assert ENV_FILES == (REPO_ROOT / ".env.local", BACKEND_DIR / ".env")
    assert all(path.is_absolute() for path in ENV_FILES)


def test_backend_env_overrides_neon_env_local(tmp_path: Path) -> None:
    neon = tmp_path / ".env.local"
    neon.write_text(
        "DATABASE_URL=postgresql://neon/db\nDATABASE_URL_UNPOOLED=postgresql://direct/db\n"
    )
    backend = tmp_path / ".env"
    backend.write_text("DATABASE_URL=sqlite:///override.db\n")

    settings = Settings(_env_file=(neon, backend))  # type: ignore[call-arg]

    assert settings.database_url == "sqlite:///override.db"
    assert settings.migration_database_url == "postgresql://direct/db"


def test_migration_url_falls_back_to_database_url() -> None:
    assert make(database_url="postgresql://a/b").migration_database_url == "postgresql://a/b"


def test_cors_origins_accept_comma_separated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000, https://twinklekids.example")
    assert make().cors_origins == ["http://localhost:3000", "https://twinklekids.example"]


def test_storage_auto_selects_neon_when_credentials_present() -> None:
    assert make(**NEON_STORAGE).resolved_storage_backend == "neon"


def test_blank_storage_values_count_as_missing() -> None:
    settings = make(**{**NEON_STORAGE, "aws_endpoint_url_s3": "  "})
    assert settings.resolved_storage_backend == "memory"


def test_explicit_neon_backend_requires_credentials() -> None:
    with pytest.raises(ValidationError, match="STORAGE_BACKEND=neon"):
        make(storage_backend="neon")


def test_cookies_are_secure_outside_development() -> None:
    assert make(app_env="development").secure_cookies is False
    assert make(app_env="staging").secure_cookies is True
    assert make(app_env="development", cookie_secure=True).secure_cookies is True
    with pytest.raises(ValidationError, match="SAMESITE=none"):
        make(cookie_samesite="none", cookie_secure=False)


def test_protected_neon_branch_marks_production_data() -> None:
    assert make(neon_branch="production").targets_production_data
    assert not make(neon_branch="dev").targets_production_data
    assert make(app_env="production", **{**PROD_SAFE, "neon_branch": "dev"}).targets_production_data


def test_docs_follow_environment_unless_overridden() -> None:
    assert make().show_docs
    assert not make(app_env="production", **PROD_SAFE).show_docs
    assert make(app_env="production", docs_enabled=True, **PROD_SAFE).show_docs


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"database_url": "postgresql://u:p@h/db", **NEON_STORAGE}, "SECRET_KEY"),
        ({"secret_key": "x" * 64, "database_url": "sqlite:///x.db", **NEON_STORAGE}, "PostgreSQL"),
        (
            {"secret_key": "x" * 64, "database_url": "postgresql://u:p@h/db", "debug": True},
            "DEBUG",
        ),
        ({"secret_key": "x" * 64, "database_url": "postgresql://u:p@h/db"}, "Object Storage"),
        ({**PROD_SAFE, "cookie_secure": False}, "COOKIE_SECURE"),
        ({**PROD_SAFE, "cors_origins": ["*"]}, "explicit origins"),
    ],
)
def test_production_rejects_unsafe_settings(overrides: dict[str, object], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        make(app_env="production", **overrides)


def test_production_accepts_safe_settings() -> None:
    settings = make(
        app_env="production",
        debug=False,
        secret_key="x" * 64,
        database_url="postgresql://u:p@h/db",
        **NEON_STORAGE,
    )
    assert settings.app_env == "production"
    assert settings.resolved_storage_backend == "neon"
