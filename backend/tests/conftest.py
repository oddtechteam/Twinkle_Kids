"""Shared fixtures for offline tests: isolated SQLite DB (built by the real Alembic migrations),
in-memory object storage, and helpers for authenticated API clients.

Offline tests never read backend/.env or the Neon .env.local (`_env_file=None`).
"""

import shutil
from collections.abc import Iterator
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from app.bootstrap import Container, build_container
from app.core.config import Settings
from app.domain.entities.identity import Role, User
from app.infrastructure.auth.passwords import Argon2PasswordHasher
from app.infrastructure.db.repositories.identity import SqlAlchemyUserRepository
from app.main import create_app

BACKEND = Path(__file__).resolve().parents[1]
PASSWORD = "correct horse battery staple"  # test-only credential
STAFF_PASSWORD = "staff passphrase for tests"  # test-only credential


def make_image(fmt: str = "PNG", size: tuple[int, int] = (8, 6), color: str = "#e8705c") -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, color).save(buffer, format=fmt)
    return buffer.getvalue()


def alembic_config(url: str) -> Config:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


@pytest.fixture(scope="session")
def migrated_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Run every migration once; each test gets a copy of the resulting database file."""
    path = tmp_path_factory.mktemp("template") / "template.db"
    command.upgrade(alembic_config(f"sqlite:///{path}"), "head")
    return path


def make_settings(db_path: Path, **overrides: object) -> Settings:
    values: dict[str, object] = {
        "app_env": "test",
        "database_url": f"sqlite:///{db_path}",
        "database_url_unpooled": None,
        "neon_branch": None,
        "storage_backend": "memory",
        "cors_origins": ["http://localhost:3000"],
        **overrides,
    }
    return Settings(_env_file=None, **values)  # type: ignore[arg-type]


@pytest.fixture
def db_path(migrated_template: Path, tmp_path: Path) -> Path:
    target = tmp_path / "test.db"
    shutil.copyfile(migrated_template, target)
    return target


@pytest.fixture
def settings(db_path: Path) -> Settings:
    return make_settings(db_path)


@pytest.fixture
def container(settings: Settings) -> Iterator[Container]:
    built = build_container(settings)
    built.password_hasher = Argon2PasswordHasher(time_cost=1, memory_cost=8 * 1024, parallelism=1)
    yield built
    built.dispose()


@pytest.fixture
def app(container: Container) -> FastAPI:
    return create_app(container=container)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


# --- auth helpers ---------------------------------------------------------------------------


def csrf(client: TestClient) -> dict[str, str]:
    token = client.cookies.get("tk_csrf")
    assert token, "no CSRF cookie: sign in first"
    return {"X-CSRF-Token": token}


def create_user(
    container: Container, *roles: Role, email: str | None = None, password: str = STAFF_PASSWORD
) -> User:
    email = email or f"user-{uuid4().hex[:8]}@twinklekids.in"
    with container.session_factory() as session:
        repo = SqlAlchemyUserRepository(session)
        user = User(
            id=uuid4(),
            email=email,
            full_name="Test User",
            password_hash=container.password_hasher.hash(password),
        )
        repo.add(user, set(roles) or {Role.CUSTOMER})
        session.commit()
        stored = repo.get(user.id)
    assert stored is not None
    return stored


def login(client: TestClient, email: str, password: str = STAFF_PASSWORD) -> None:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text


@pytest.fixture
def staff_client(client: TestClient, container: Container) -> TestClient:
    """Signed-in catalogue manager (admin:access, catalog/content/media/inventory)."""
    user = create_user(container, Role.CATALOG_MANAGER)
    login(client, user.email)
    return client


@pytest.fixture
def owner_client(client: TestClient, container: Container) -> TestClient:
    user = create_user(container, Role.OWNER)
    login(client, user.email)
    return client


def product_payload(
    *,
    sku: str = "TK-DRS-001",
    selling: str = "399.00",
    original: str | None = "599.00",
    status: str = "active",
    category_ids: list[UUID] | None = None,
    variants: list[dict[str, object]] | None = None,
    name: str = "Blush Party Dress",
    **extra: object,
) -> dict[str, object]:
    return {
        "name": name,
        "sku": sku,
        "selling_price": selling,
        "original_price": original,
        "status": status,
        "category_ids": [str(c) for c in (category_ids or [])],
        "variants": variants
        if variants is not None
        else [
            {"sku": f"{sku}-S", "size": "2-3Y", "colour": "Blush", "stock_quantity": 5},
            {"sku": f"{sku}-M", "size": "3-4Y", "colour": "Blush", "stock_quantity": 0},
        ],
        **extra,
    }


# --- commerce fixtures (shared by checkout / operations tests) ----------------------------------


@pytest.fixture
def owner(app: FastAPI, container: Container) -> TestClient:
    client = TestClient(app)
    user = create_user(container, Role.OWNER)
    login(client, user.email)
    return client


@pytest.fixture
def shopper(app: FastAPI) -> TestClient:
    return TestClient(app)
