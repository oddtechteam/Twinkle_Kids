"""Admin catalogue writes + public catalogue reads against a real (SQLite) database."""

from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.bootstrap import Container
from app.infrastructure.db.models.commerce import InventoryMovementModel
from app.infrastructure.db.models.identity import AuditLogModel
from tests.conftest import csrf, product_payload

ADMIN = "/api/v1/admin"


def create_category(client: TestClient, name: str, **extra: object) -> UUID:
    response = client.post(
        f"{ADMIN}/categories", json={"name": name, **extra}, headers=csrf(client)
    )
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


def create_product(client: TestClient, **kwargs: Any) -> dict[str, Any]:
    response = client.post(
        f"{ADMIN}/products", json=product_payload(**kwargs), headers=csrf(client)
    )
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def test_create_product_persists_both_prices_and_derives_discount(
    staff_client: TestClient, container: Container
) -> None:
    girls = create_category(staff_client, "Girls")
    body = create_product(staff_client, category_ids=[girls])

    assert body["price"] == {
        "selling_price": "399.00",
        "original_price": "599.00",
        "discount_amount": "200.00",
        "discount_percent": 33,
        "currency": "INR",
    }
    assert body["status"] == "active" and body["published_at"] is not None
    assert [v["stock_quantity"] for v in body["variants"]] == [5, 0]
    assert body["categories"][0]["slug"] == "girls"

    public = staff_client.get(f"/api/v1/products/{body['slug']}").json()
    assert public["price"]["selling_price"] == "399.00"
    assert public["price"]["discount_percent"] == 33
    assert "stock_quantity" not in public["variants"][0]  # stock counts are admin-only

    with container.session_factory() as session:
        movements = session.scalars(select(InventoryMovementModel)).all()
        actions = set(session.scalars(select(AuditLogModel.action)))
    assert [(m.reason, m.quantity_delta, m.stock_after) for m in movements] == [
        ("initial_stock", 5, 5)
    ]
    assert {"category.created", "product.created"} <= actions


def test_prices_are_independently_editable(staff_client: TestClient) -> None:
    product = create_product(staff_client)
    update = product_payload(selling="449.00", original="899.00")
    response = staff_client.put(
        f"{ADMIN}/products/{product['id']}", json=update, headers=csrf(staff_client)
    )
    assert response.status_code == 200, response.text
    assert response.json()["price"]["discount_percent"] == 50

    no_mrp = product_payload(selling="449.00", original=None)
    response = staff_client.put(
        f"{ADMIN}/products/{product['id']}", json=no_mrp, headers=csrf(staff_client)
    )
    price = response.json()["price"]
    assert price["original_price"] is None and price["discount_percent"] is None


@pytest.mark.parametrize(
    ("selling", "original", "status"),
    [
        ("399.00", "299.00", 422),  # MRP below selling price
        ("-1.00", None, 422),  # negative
        ("399.999", None, 422),  # more than 2 decimal places
    ],
)
def test_invalid_prices_are_rejected(
    staff_client: TestClient, selling: str, original: str | None, status: int
) -> None:
    response = staff_client.post(
        f"{ADMIN}/products",
        json=product_payload(selling=selling, original=original),
        headers=csrf(staff_client),
    )
    assert response.status_code == status


def test_variant_overrides_and_inheritance(staff_client: TestClient) -> None:
    variants = [
        {"sku": "TK-1-S", "size": "S", "stock_quantity": 2},  # inherits 399/599
        {"sku": "TK-1-L", "size": "L", "selling_price": "449.00", "stock_quantity": 2},  # keeps MRP
    ]
    body = create_product(staff_client, sku="TK-1", variants=variants)
    by_size = {v["size"]: v for v in body["variants"]}
    assert by_size["S"]["price"]["selling_price"] == "399.00"
    assert by_size["S"]["selling_price_override"] is None
    assert by_size["L"]["price"] == {
        "selling_price": "449.00",
        "original_price": "599.00",
        "discount_amount": "150.00",
        "discount_percent": 25,
        "currency": "INR",
    }

    listed = staff_client.get("/api/v1/products").json()["items"][0]
    assert listed["from_price"] == "399.00" and listed["price_varies"] is True

    over_mrp = [{"sku": "TK-2-S", "size": "S", "selling_price": "650.00"}]
    response = staff_client.post(
        f"{ADMIN}/products",
        json=product_payload(sku="TK-2", name="Other Dress", variants=over_mrp),
        headers=csrf(staff_client),
    )
    assert response.status_code == 422


def test_duplicate_sku_and_slug_conflicts(staff_client: TestClient) -> None:
    create_product(staff_client)
    clash = staff_client.post(
        f"{ADMIN}/products", json=product_payload(name="Other"), headers=csrf(staff_client)
    )
    assert clash.status_code == 409 and "SKU" in clash.json()["detail"]
    same_slug = staff_client.post(
        f"{ADMIN}/products", json=product_payload(sku="TK-NEW"), headers=csrf(staff_client)
    )
    assert same_slug.status_code == 409 and "slug" in same_slug.json()["detail"]


def test_stock_changes_are_recorded_in_the_ledger(
    staff_client: TestClient, container: Container
) -> None:
    product = create_product(staff_client)
    payload = product_payload()
    payload["variants"][0]["stock_quantity"] = 9  # type: ignore[index]
    staff_client.put(f"{ADMIN}/products/{product['id']}", json=payload, headers=csrf(staff_client))
    with container.session_factory() as session:
        rows = session.scalars(
            select(InventoryMovementModel).order_by(InventoryMovementModel.created_at)
        ).all()
    assert [(r.reason, r.quantity_delta, r.stock_after) for r in rows] == [
        ("initial_stock", 5, 5),
        ("adjustment", 4, 9),
    ]


def test_status_management_controls_storefront_visibility(staff_client: TestClient) -> None:
    product = create_product(staff_client, status="draft")
    assert staff_client.get(f"/api/v1/products/{product['slug']}").status_code == 404
    assert staff_client.get("/api/v1/products").json()["total"] == 0
    assert staff_client.get(f"{ADMIN}/products").json()["total"] == 1  # admins see drafts

    activated = staff_client.patch(
        f"{ADMIN}/products/{product['id']}/status",
        json={"status": "active"},
        headers=csrf(staff_client),
    )
    assert activated.status_code == 200 and activated.json()["published_at"] is not None
    assert staff_client.get(f"/api/v1/products/{product['slug']}").status_code == 200

    staff_client.patch(
        f"{ADMIN}/products/{product['id']}/status",
        json={"status": "archived"},
        headers=csrf(staff_client),
    )
    assert staff_client.get(f"/api/v1/products/{product['slug']}").status_code == 404


def test_listing_filters_sorting_and_pagination(staff_client: TestClient) -> None:
    girls = create_category(staff_client, "Girls")
    party = create_category(staff_client, "Party Wear", parent_id=str(girls))
    boys = create_category(staff_client, "Boys")
    create_product(
        staff_client, sku="A", name="Ruffle Dress", selling="399.00", category_ids=[party]
    )
    create_product(
        staff_client,
        sku="B",
        name="Star Tee",
        selling="299.00",
        original=None,
        category_ids=[boys],
        variants=[{"sku": "B-1", "size": "4-5Y", "colour": "Navy", "stock_quantity": 0}],
    )
    create_product(
        staff_client,
        sku="C",
        name="Twirl Frock",
        selling="549.00",
        original="799.00",
        category_ids=[girls],
    )

    def names(**params: Any) -> list[str]:
        response = staff_client.get("/api/v1/products", params=params)
        assert response.status_code == 200, response.text
        return [p["name"] for p in response.json()["items"]]

    assert names(category="girls", sort="name_asc") == [
        "Ruffle Dress",
        "Twirl Frock",
    ]  # includes child
    assert names(sort="price_asc") == ["Star Tee", "Ruffle Dress", "Twirl Frock"]
    assert names(sort="price_desc")[0] == "Twirl Frock"
    assert names(min_price="300", max_price="500") == ["Ruffle Dress"]
    assert names(q="frock") == ["Twirl Frock"]
    assert names(colour="navy") == ["Star Tee"]
    assert names(size="4-5Y") == ["Star Tee"]
    assert "Star Tee" not in names(in_stock="true")
    assert names(in_stock="false") == ["Star Tee"]

    page = staff_client.get(
        "/api/v1/products", params={"page_size": 2, "page": 2, "sort": "name_asc"}
    ).json()
    assert (page["total"], page["pages"], [p["name"] for p in page["items"]]) == (
        3,
        2,
        ["Twirl Frock"],
    )
    bad = staff_client.get("/api/v1/products", params={"min_price": "500", "max_price": "100"})
    assert bad.status_code == 422


def test_categories_endpoints_and_custom_category_order(staff_client: TestClient) -> None:
    girls = create_category(staff_client, "Girls", custom_product_ordering=True, display_order=1)
    create_category(staff_client, "Hidden", is_active=False)
    a = create_product(staff_client, sku="A", name="Alpha", category_ids=[girls])
    b = create_product(staff_client, sku="B", name="Beta", category_ids=[girls])
    c = create_product(staff_client, sku="C", name="Gamma", category_ids=[girls])

    assert [c["slug"] for c in staff_client.get("/api/v1/categories").json()] == ["girls"]

    order = {"product_ids": [c["id"], a["id"], b["id"]]}
    put = staff_client.put(
        f"{ADMIN}/categories/{girls}/product-order", json=order, headers=csrf(staff_client)
    )
    assert put.status_code == 204
    detail = staff_client.get("/api/v1/categories/girls").json()
    assert detail["category"]["name"] == "Girls"
    assert [p["name"] for p in detail["products"]["items"]] == ["Gamma", "Alpha", "Beta"]

    assert staff_client.get("/api/v1/categories/hidden").status_code == 404
    deactivate = staff_client.patch(
        f"{ADMIN}/categories/{girls}/status", json={"is_active": False}, headers=csrf(staff_client)
    )
    assert deactivate.status_code == 204
    assert staff_client.get("/api/v1/categories/girls").status_code == 404


def test_category_hierarchy_cannot_form_cycles(staff_client: TestClient) -> None:
    parent = create_category(staff_client, "Parent")
    child = create_category(staff_client, "Child", parent_id=str(parent))
    response = staff_client.put(
        f"{ADMIN}/categories/{parent}",
        json={"name": "Parent", "parent_id": str(child)},
        headers=csrf(staff_client),
    )
    assert response.status_code == 422
