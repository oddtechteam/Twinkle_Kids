"""Independent product ordering: the same products in different orders per context."""

from typing import Any

from fastapi.testclient import TestClient

from tests.conftest import csrf, product_payload

ADMIN = "/api/v1/admin"


def make_products(client: TestClient, category_id: str) -> dict[str, str]:
    ids = {}
    for sku, name in (("P1", "Alpha"), ("P2", "Beta"), ("P3", "Gamma")):
        response = client.post(
            f"{ADMIN}/products",
            json=product_payload(sku=sku, name=name, category_ids=[category_id]),  # type: ignore[list-item]
            headers=csrf(client),
        )
        assert response.status_code == 201, response.text
        ids[name] = response.json()["id"]
    return ids


def names(response: Any) -> list[str]:
    assert response.status_code == 200, response.text
    return [p["name"] for p in response.json()]


def section_picks(c: TestClient, section_id: str, ids: dict[str, str]) -> list[str]:
    """A manual section's hand-picked order (by product name)."""
    response = c.get(f"{ADMIN}/homepage/sections/{section_id}")
    assert response.status_code == 200, response.text
    by_id = {v: k for k, v in ids.items()}
    return [by_id[i] for i in response.json()["product_ids"]]


def published_section(c: TestClient, section_id: str) -> list[str]:
    """What the storefront shows for a section after publishing."""
    assert c.post(f"{ADMIN}/homepage/publish", json={}, headers=csrf(c)).status_code == 200
    homepage = c.get("/api/v1/content/homepage").json()
    section = next(s for s in homepage["sections"] if s["id"] == section_id)
    return [p["name"] for p in section["products"]]


def test_category_collection_and_section_orders_are_independent(staff_client: TestClient) -> None:
    c = staff_client
    category_id = c.post(
        f"{ADMIN}/categories",
        json={"name": "Girls", "custom_product_ordering": True},
        headers=csrf(c),
    ).json()["id"]
    p = make_products(c, category_id)

    collection_id = c.post(
        f"{ADMIN}/collections",
        json={"name": "Festive Edit", "status": "published"},
        headers=csrf(c),
    ).json()["id"]
    section_id = c.post(
        f"{ADMIN}/homepage/sections",
        json={
            "section_type": "product_carousel",
            "title": "Bestsellers",
            "selection_mode": "manual",
            "settings": {"columns_desktop": 4},
        },
        headers=csrf(c),
    ).json()["id"]

    # Three different orders for the same three products.
    c.put(
        f"{ADMIN}/categories/{category_id}/product-order",
        json={"product_ids": [p["Beta"], p["Gamma"], p["Alpha"]]},
        headers=csrf(c),
    )
    c.put(
        f"{ADMIN}/collections/{collection_id}/products",
        json={"product_ids": [p["Gamma"], p["Alpha"], p["Beta"]]},
        headers=csrf(c),
    )
    c.put(
        f"{ADMIN}/homepage/sections/{section_id}/products",
        json={"product_ids": [p["Alpha"], p["Gamma"]]},
        headers=csrf(c),
    )

    category_order = [
        i["name"] for i in c.get("/api/v1/categories/girls").json()["products"]["items"]
    ]
    assert category_order == ["Beta", "Gamma", "Alpha"]
    assert names(c.get(f"{ADMIN}/collections/{collection_id}/products")) == [
        "Gamma",
        "Alpha",
        "Beta",
    ]
    assert section_picks(c, section_id, p) == ["Alpha", "Gamma"]
    storefront = c.get("/api/v1/products", params={"collection": "festive-edit"}).json()["items"]
    assert [i["name"] for i in storefront] == ["Gamma", "Alpha", "Beta"]

    # Reordering one context leaves the others untouched.
    c.put(
        f"{ADMIN}/collections/{collection_id}/products",
        json={"product_ids": [p["Beta"]]},
        headers=csrf(c),
    )
    assert names(c.get(f"{ADMIN}/collections/{collection_id}/products")) == ["Beta"]
    assert section_picks(c, section_id, p) == ["Alpha", "Gamma"]
    assert [i["name"] for i in c.get("/api/v1/categories/girls").json()["products"]["items"]] == [
        "Beta",
        "Gamma",
        "Alpha",
    ]


def test_category_driven_section_follows_category_order(staff_client: TestClient) -> None:
    c = staff_client
    category_id = c.post(
        f"{ADMIN}/categories",
        json={"name": "Boys", "custom_product_ordering": True},
        headers=csrf(c),
    ).json()["id"]
    p = make_products(c, category_id)
    c.put(
        f"{ADMIN}/categories/{category_id}/product-order",
        json={"product_ids": [p["Gamma"], p["Beta"], p["Alpha"]]},
        headers=csrf(c),
    )
    section_id = c.post(
        f"{ADMIN}/homepage/sections",
        json={
            "section_type": "product_grid",
            "selection_mode": "category",
            "source_category_id": category_id,
            "product_limit": 2,
        },
        headers=csrf(c),
    ).json()["id"]
    assert published_section(c, section_id) == ["Gamma", "Beta"]
    # Hand-picking is only allowed in manual mode.
    manual = c.put(
        f"{ADMIN}/homepage/sections/{section_id}/products",
        json={"product_ids": [p["Alpha"]]},
        headers=csrf(c),
    )
    assert manual.status_code == 422


def test_ordering_validation(staff_client: TestClient) -> None:
    c = staff_client
    category_id = c.post(f"{ADMIN}/categories", json={"name": "Baby"}, headers=csrf(c)).json()["id"]
    p = make_products(c, category_id)
    collection_id = c.post(f"{ADMIN}/collections", json={"name": "New In"}, headers=csrf(c)).json()[
        "id"
    ]
    dupes = c.put(
        f"{ADMIN}/collections/{collection_id}/products",
        json={"product_ids": [p["Alpha"], p["Alpha"]]},
        headers=csrf(c),
    )
    assert dupes.status_code == 422
    unknown = c.put(
        f"{ADMIN}/collections/{collection_id}/products",
        json={"product_ids": ["00000000-0000-0000-0000-000000000000"]},
        headers=csrf(c),
    )
    assert unknown.status_code == 422
    bad_settings = c.post(
        f"{ADMIN}/homepage/sections",
        json={"section_type": "rich_text", "settings": {"body": "Hi", "script": "x"}},
        headers=csrf(c),
    )
    assert bad_settings.status_code == 422
    # Draft collections are not visible on the storefront.
    c.put(
        f"{ADMIN}/collections/{collection_id}/products",
        json={"product_ids": [p["Alpha"]]},
        headers=csrf(c),
    )
    assert c.get("/api/v1/products", params={"collection": "new-in"}).json()["total"] == 0
