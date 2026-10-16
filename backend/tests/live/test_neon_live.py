"""Live integration tests against the linked Neon *development* branch (Postgres + Storage).

Opt-in: ``pytest -m live``. They refuse to run when the configuration targets production data
(APP_ENV=production or a protected NEON_BRANCH such as `production`). Every row and object
created here is removed again.
"""

import urllib.error
import urllib.request
import uuid
from collections.abc import Iterator
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError

from app.bootstrap import Container, build_container
from app.core.config import Settings
from app.domain.entities.identity import Role
from app.infrastructure.db.models.catalog import ProductModel
from app.infrastructure.db.models.identity import AuditLogModel, UserModel
from app.infrastructure.db.models.media import MediaAssetModel
from app.infrastructure.storage.s3 import S3ObjectStorage
from app.main import create_app
from tests.conftest import PASSWORD, create_user, csrf, login, make_image

pytestmark = pytest.mark.live

TEST_PREFIX = "_live-tests"


def anonymous_get(url: str) -> tuple[int, bytes, str | None]:
    request = urllib.request.Request(url, method="GET")  # noqa: S310 - https URL from Neon
    try:
        with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
            return response.status, response.read(), response.headers.get("Content-Type")
    except urllib.error.HTTPError as exc:
        return exc.code, b"", None


@pytest.fixture(scope="module")
def settings() -> Settings:
    loaded = Settings()  # real env files: <repo>/.env.local (Neon) + backend/.env
    if loaded.targets_production_data:
        pytest.skip(f"Refusing live tests against production data (NEON_BRANCH={loaded.neon_branch}).")
    if not loaded.database_url.startswith(("postgres://", "postgresql")):
        pytest.skip("DATABASE_URL is not PostgreSQL; run `neon env pull`.")
    if loaded.resolved_storage_backend != "neon":
        pytest.skip("Neon Object Storage credentials (AWS_*) are not configured.")
    return loaded


@pytest.fixture(scope="module")
def container(settings: Settings) -> Iterator[Container]:
    built = build_container(settings)
    yield built
    built.dispose()


@pytest.fixture
def cleanup(container: Container) -> Iterator[dict[str, list[Any]]]:
    """Register ids created by a test; they are deleted afterwards even if the test fails."""
    created: dict[str, list[Any]] = {"users": [], "products": [], "media": [], "emails": []}
    yield created
    with container.session_factory() as session:
        if created["products"]:
            session.execute(delete(ProductModel).where(ProductModel.id.in_(created["products"])))
        if created["emails"]:
            ids = session.scalars(select(UserModel.id).where(UserModel.email.in_(created["emails"])))
            created["users"].extend(ids)
        if created["users"]:
            session.execute(delete(AuditLogModel).where(AuditLogModel.actor_user_id.in_(created["users"])))
            session.execute(delete(UserModel).where(UserModel.id.in_(created["users"])))
        if created["products"]:
            session.execute(
                delete(AuditLogModel).where(AuditLogModel.entity_id.in_([str(p) for p in created["products"]]))
            )
        session.commit()
    storage = container.storage
    with container.session_factory() as session:
        for asset_id in created["media"]:
            row = session.get(MediaAssetModel, asset_id)
            if row is not None:
                storage.delete(row.bucket, row.object_key)
                session.delete(row)
        session.commit()


# --- PostgreSQL ------------------------------------------------------------------------------


def test_connection_tls_and_migration_state(container: Container, settings: Settings) -> None:
    assert settings.neon_branch == "dev"
    with container.engine.connect() as conn:
        pgconn = conn.connection.dbapi_connection.pgconn  # type: ignore[union-attr]
        assert pgconn.ssl_in_use, "connection to Neon must use TLS"
        assert conn.execute(text("select version_num from alembic_version")).scalar_one() == "0003"
        roles = set(conn.execute(text("select slug from roles")).scalars())
    assert roles == {"owner", "catalog_manager", "order_manager", "customer"}


def test_postgres_column_types(container: Container) -> None:
    query = text(
        "select table_name, column_name, data_type, numeric_precision, numeric_scale "
        "from information_schema.columns where table_schema = 'public' and "
        "(table_name, column_name) in (('products','selling_price'), ('products','original_price'),"
        " ('product_variants','selling_price'), ('homepage_sections','settings'),"
        " ('products','created_at'))"
    )
    with container.engine.connect() as conn:
        rows = {(r[0], r[1]): r[2:] for r in conn.execute(query)}
    assert rows[("products", "selling_price")] == ("numeric", 12, 2)
    assert rows[("products", "original_price")] == ("numeric", 12, 2)
    assert rows[("product_variants", "selling_price")] == ("numeric", 12, 2)
    assert rows[("homepage_sections", "settings")][0] == "jsonb"
    assert rows[("products", "created_at")][0] == "timestamp with time zone"


@pytest.mark.parametrize(
    ("sql", "constraint"),
    [
        (
            "insert into products (id, name, slug, sku, selling_price, original_price) "
            "values (gen_random_uuid(), 'x', 'live-x', 'LIVE-X', 399.00, 299.00)",
            "ck_products_original_price_gte_selling",
        ),
        (
            "insert into products (id, name, slug, sku, selling_price) "
            "values (gen_random_uuid(), 'x', 'live-y', 'LIVE-Y', -1)",
            "ck_products_selling_price_non_negative",
        ),
        (
            "insert into products (id, name, slug, sku, selling_price, status) "
            "values (gen_random_uuid(), 'x', 'live-z', 'LIVE-Z', 1, 'published')",
            "ck_products_status_valid",
        ),
    ],
)
def test_postgres_enforces_pricing_and_status_constraints(
    container: Container, sql: str, constraint: str
) -> None:
    with container.engine.connect() as conn, pytest.raises(IntegrityError, match=constraint):
        conn.execute(text(sql))  # never committed: the connection rolls back


def test_expression_index_blocks_duplicate_variant_options(container: Container) -> None:
    with container.engine.connect() as conn:
        product_id = uuid.uuid4()
        conn.execute(
            text(
                "insert into products (id, name, slug, sku, selling_price) "
                "values (:id, 'Live', :slug, :sku, 10)"
            ),
            {"id": product_id, "slug": f"live-{product_id.hex[:8]}", "sku": f"LIVE-{product_id.hex[:8]}"},
        )
        insert = text(
            "insert into product_variants (id, product_id, sku, size, colour) "
            "values (gen_random_uuid(), :pid, :sku, :size, 'Blush')"
        )
        conn.execute(insert, {"pid": product_id, "sku": f"V1-{product_id.hex[:8]}", "size": "S"})
        with pytest.raises(IntegrityError, match="uq_product_variants_options"):
            conn.execute(insert, {"pid": product_id, "sku": f"V2-{product_id.hex[:8]}", "size": "s"})
        conn.rollback()


# --- Object storage ----------------------------------------------------------------------------


def test_object_storage_public_and_private_round_trip(container: Container, settings: Settings) -> None:
    storage = container.storage
    assert isinstance(storage, S3ObjectStorage)
    png = make_image("PNG", (12, 9))
    public_key = f"{TEST_PREFIX}/{uuid.uuid4()}.png"
    private_key = f"{TEST_PREFIX}/{uuid.uuid4()}.png"
    media, private = settings.storage_media_bucket, settings.storage_private_bucket
    try:
        storage.put(media, public_key, png, content_type="image/png", cache_control="no-store")
        storage.put(private, private_key, png, content_type="image/png", cache_control="no-store")
        assert storage.get(media, public_key).data == png
        assert anonymous_get(storage.public_url(media, public_key)) == (200, png, "image/png")
        assert anonymous_get(storage.public_url(private, private_key))[0] == 403
        status, body, _ = anonymous_get(storage.presigned_url(private, private_key, expires_in=60))
        assert (status, body) == (200, png)
    finally:
        storage.delete(media, public_key)
        storage.delete(private, private_key)
    assert not storage.exists(media, public_key)


# --- Full API flow on Neon -----------------------------------------------------------------------


def test_auth_flow_against_neon(container: Container, cleanup: dict[str, list[Any]]) -> None:
    email = f"live-{uuid.uuid4().hex[:10]}@twinklekids.in"
    cleanup["emails"].append(email)
    with TestClient(create_app(container=container)) as client:
        registered = client.post(
            "/api/v1/auth/register", json={"email": email, "password": PASSWORD, "full_name": "Live Test"}
        )
        assert registered.status_code == 201, registered.text
        assert registered.json()["roles"] == ["customer"]
        assert client.get("/api/v1/auth/me").json()["email"] == email
        assert client.get("/api/v1/admin/me").status_code == 403
        assert client.post("/api/v1/auth/logout", headers=csrf(client)).status_code == 204
        assert client.get("/api/v1/auth/me").status_code == 401
        login(client, email, PASSWORD)
        assert client.get("/api/v1/auth/me").status_code == 200

    with container.session_factory() as session:
        stored = session.scalars(select(UserModel).where(UserModel.email == email)).one()
        assert stored.password_hash.startswith("$argon2id$")


def test_admin_product_with_image_and_storefront_read(
    container: Container, cleanup: dict[str, list[Any]]
) -> None:
    staff = create_user(container, Role.CATALOG_MANAGER, email=f"live-staff-{uuid.uuid4().hex[:8]}@twinklekids.in")
    cleanup["users"].append(staff.id)
    png = make_image("PNG", (40, 30), color="#f8dcdb")
    suffix = uuid.uuid4().hex[:8].upper()

    with TestClient(create_app(container=container)) as client:
        login(client, staff.email)
        assert client.get("/api/v1/admin/me").status_code == 200

        uploaded = client.post(
            "/api/v1/admin/media",
            headers=csrf(client),
            files={"file": ("live.png", png, "image/png")},
            data={"purpose": "product_image", "alt_text": "Live test image"},
        )
        assert uploaded.status_code == 201, uploaded.text
        media_id = uploaded.json()["id"]
        cleanup["media"].append(uuid.UUID(media_id))

        payload = {
            "name": f"Live Test Dress {suffix}",
            "sku": f"LIVE-{suffix}",
            "selling_price": "399.00",
            "original_price": "599.00",
            "status": "active",
            "variants": [
                {"sku": f"LIVE-{suffix}-S", "size": "2-3Y", "stock_quantity": 4},
                {"sku": f"LIVE-{suffix}-L", "size": "5-6Y", "selling_price": "449.00", "stock_quantity": 2},
            ],
            "media": [{"media_asset_id": media_id}],
        }
        created = client.post("/api/v1/admin/products", json=payload, headers=csrf(client))
        assert created.status_code == 201, created.text
        product = created.json()
        cleanup["products"].append(uuid.UUID(product["id"]))

        public = client.get(f"/api/v1/products/{product['slug']}")
        assert public.status_code == 200
        body = public.json()
        assert body["price"]["selling_price"] == "399.00"
        assert body["price"]["original_price"] == "599.00"
        assert body["price"]["discount_percent"] == 33
        large = next(v for v in body["variants"] if v["size"] == "5-6Y")
        assert large["price"]["selling_price"] == "449.00"
        assert large["price"]["original_price"] == "599.00"

        # The stored media reference resolves to the actual bytes in Neon Object Storage.
        assert anonymous_get(body["images"][0]["url"]) == (200, png, "image/png")

        # An image used by a product cannot be deleted out from under it.
        blocked = client.delete(f"/api/v1/admin/media/{media_id}", headers=csrf(client))
        assert blocked.status_code == 409


def test_seeded_demo_catalogue_is_served_from_postgres(container: Container) -> None:
    with TestClient(create_app(container=container)) as client:
        listing = client.get("/api/v1/products", params={"category": "demo-girls", "sort": "price_asc"})
        assert listing.status_code == 200
        items = listing.json()["items"]
        if not items:
            pytest.skip("Demo catalogue not seeded on this branch (python -m app.cli seed-demo).")
        dress = next(i for i in items if i["slug"] == "demo-blush-ruffle-party-dress")
        assert dress["price"]["selling_price"] == "399.00"
        assert dress["price"]["original_price"] == "599.00"
        assert dress["price"]["discount_percent"] == 33
        assert Decimal(dress["from_price"]) == Decimal("399.00")
        detail = client.get("/api/v1/categories/demo-girls").json()
        assert [c["slug"] for c in detail["children"]] == ["demo-girls-party-wear"]
