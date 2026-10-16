import pytest

from app.infrastructure.db.url import normalize_database_url, redact

NEON = (
    "postgresql://alex:s3cret@ep-cool-name-123456.ap-southeast-1.aws.neon.tech/neondb"
    "?sslmode=require&channel_binding=require"
)


@pytest.mark.parametrize("scheme", ["postgres", "postgresql"])
def test_postgres_urls_use_psycopg3(scheme: str) -> None:
    url = normalize_database_url(f"{scheme}://u:p@localhost:5432/db")
    assert url.drivername == "postgresql+psycopg"


def test_neon_ssl_parameters_are_preserved() -> None:
    url = normalize_database_url(NEON)
    assert url.query["sslmode"] == "require"
    assert url.query["channel_binding"] == "require"
    assert url.host is not None
    assert url.host.endswith(".neon.tech")


def test_explicit_driver_and_sqlite_are_untouched() -> None:
    explicit = "postgresql+asyncpg://u:p@h/db"
    assert normalize_database_url(explicit).drivername == "postgresql+asyncpg"
    assert normalize_database_url("sqlite:///./x.db").drivername == "sqlite"


def test_redact_hides_password() -> None:
    rendered = redact(normalize_database_url(NEON))
    assert "s3cret" not in rendered
    assert "***" in rendered
