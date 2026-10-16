from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.bootstrap import Container
from app.domain.entities.identity import Role
from app.domain.repositories.media import ObjectStorage
from app.infrastructure.db.models.media import MediaAssetModel
from app.infrastructure.storage.memory import InMemoryObjectStorage
from app.main import create_app
from tests.conftest import create_user, csrf, login, make_image


def upload(
    client: TestClient,
    data: bytes,
    *,
    content_type: str = "image/png",
    purpose: str = "product_image",
    visibility: str = "public",
    headers: dict[str, str] | None = None,
) -> Any:
    return client.post(
        "/api/v1/admin/media",
        headers=csrf(client) if headers is None else headers,
        files={"file": ("photo.png", data, content_type)},
        data={"purpose": purpose, "visibility": visibility, "alt_text": "Twinkle tee"},
    )


def storage_of(container: Container) -> InMemoryObjectStorage:
    storage: ObjectStorage = container.storage
    assert isinstance(storage, InMemoryObjectStorage)
    return storage


@pytest.fixture
def media_client(client: TestClient, container: Container) -> TestClient:
    login(client, create_user(container, Role.CATALOG_MANAGER).email)
    return client


def test_media_admin_requires_media_permission(client: TestClient, container: Container) -> None:
    assert upload(client, make_image(), headers={}).status_code == 401
    assert client.get("/api/v1/admin/media").status_code == 401
    login(client, create_user(container, Role.ORDER_MANAGER).email)  # staff without media:manage
    assert upload(client, make_image()).status_code == 403
    assert client.get("/api/v1/admin/media").status_code == 403


def test_upload_retrieve_and_delete_round_trip(
    media_client: TestClient, container: Container
) -> None:
    client = media_client
    png = make_image("PNG", (20, 10))

    created = upload(client, png)
    assert created.status_code == 201, created.text
    body = created.json()
    asset_id = UUID(body["id"])
    assert body["content_type"] == "image/png"
    assert (body["width"], body["height"]) == (20, 10)
    assert body["bucket"] == "media"
    assert body["url"].endswith(body["object_key"])

    # The stored reference resolves back to the exact bytes.
    storage = storage_of(container)
    assert storage.get("media", body["object_key"]).data == png
    with container.session_factory() as session:
        row = session.scalars(select(MediaAssetModel)).one()
        assert (row.id, row.object_key, row.size_bytes) == (asset_id, body["object_key"], len(png))

    public = client.get(f"/api/v1/media/{asset_id}")
    assert public.status_code == 200
    assert public.json()["url"] == body["url"]
    assert "object_key" not in public.json()  # internals stay admin-only

    listed = client.get("/api/v1/admin/media", params={"purpose": "product_image"})
    assert [item["id"] for item in listed.json()] == [str(asset_id)]

    assert client.delete(f"/api/v1/admin/media/{asset_id}", headers=csrf(client)).status_code == 204
    assert client.get(f"/api/v1/media/{asset_id}").status_code == 404
    assert not storage.exists("media", body["object_key"])


def test_private_media_is_not_publicly_resolvable(media_client: TestClient) -> None:
    client = media_client
    created = upload(client, make_image(), visibility="private", purpose="content_image")
    asset_id = created.json()["id"]
    assert client.get(f"/api/v1/media/{asset_id}").status_code == 404
    admin = client.get(f"/api/v1/admin/media/{asset_id}")
    assert admin.json()["bucket"] == "assets"


@pytest.mark.parametrize(
    ("data", "content_type", "status"),
    [
        (b"<svg onload='alert(1)'/>", "image/svg+xml", 415),
        (b"not an image at all", "image/png", 415),
        (make_image("PNG", (64, 64))[:70], "image/png", 422),
    ],
    ids=["svg", "fake-png", "truncated"],
)
def test_rejects_bad_files(
    media_client: TestClient, container: Container, data: bytes, content_type: str, status: int
) -> None:
    response = upload(media_client, data, content_type=content_type)
    assert response.status_code == status
    assert len(storage_of(container)) == 0


def test_rejects_files_over_the_size_limit(container: Container) -> None:
    container.settings = container.settings.model_copy(update={"media_max_upload_bytes": 50})
    with TestClient(create_app(container=container)) as client:
        login(client, create_user(container, Role.CATALOG_MANAGER).email)
        assert upload(client, make_image("PNG", (64, 64))).status_code == 413


def test_rejects_unknown_purpose(media_client: TestClient) -> None:
    assert upload(media_client, make_image(), purpose="malware").status_code == 422
