"""Prompt 7: inventory, coupons, shipping rules, after-sale requests, reviews, recommendations,
notifications, analytics, staff roles and auditing — against a real (SQLite) database."""

from io import BytesIO
from typing import Any
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.bootstrap import Container
from app.infrastructure.db.models.commerce import InventoryMovementModel, NotificationModel
from app.infrastructure.db.models.identity import AuditLogModel
from tests.conftest import PASSWORD, csrf, login, make_image
from tests.integration.test_checkout_orders import (
    ADDRESS,
    API,
    COD,
    add,
    configure,
    make_product,
    place,
    register,
    stock,
    variant,
)

ADMIN = f"{API}/admin"


def customer(app: FastAPI, email: str) -> TestClient:
    client = TestClient(app)
    register(client, email)
    return client


def admin_order_id(owner: TestClient, number: str) -> str:
    items = owner.get(f"{ADMIN}/orders", params={"q": number}).json()["items"]
    return str(items[0]["id"])


def move(owner: TestClient, order_id: str, *statuses: str) -> None:
    for status in statuses:
        response = owner.patch(
            f"{ADMIN}/orders/{order_id}/status", json={"status": status}, headers=csrf(owner)
        )
        assert response.status_code == 200, response.text


# --- inventory ----------------------------------------------------------------------------------


def test_inventory_states_adjustments_and_movement_history(
    owner: TestClient, shopper: TestClient, container: Container
) -> None:
    configure(owner, guest_checkout_enabled=True, payment_options=[COD])
    product = make_product(owner, low_stock_threshold=3)
    size_s, size_m = variant(product, "2-3Y"), variant(product, "3-4Y")

    out = owner.get(f"{ADMIN}/inventory", params={"state": "out_of_stock"}).json()["items"]
    assert [r["variant_id"] for r in out] == [size_m]

    damaged_up = owner.post(
        f"{ADMIN}/inventory/{size_s}/adjust",
        json={"delta": 2, "reason": "damaged"},
        headers=csrf(owner),
    )
    assert damaged_up.status_code == 422
    removed = owner.post(
        f"{ADMIN}/inventory/{size_s}/adjust",
        json={"delta": -3, "reason": "damaged", "note": "Torn seam"},
        headers=csrf(owner),
    )
    assert removed.json()["stock_quantity"] == 2 and removed.json()["state"] == "low_stock"

    # Two shoppers race for the last 2 units: the second order is refused, stock never < 0.
    other = TestClient(shopper.app)
    add(shopper, size_s, 2)
    add(other, size_s, 2)
    assert place(shopper).status_code == 201
    assert place(other).status_code in (409, 422)
    assert stock(container, size_s) == 0

    history = owner.get(f"{ADMIN}/inventory/movements", params={"variant_id": size_s}).json()[
        "items"
    ]
    assert [(m["reason"], m["quantity_delta"]) for m in history][:2] == [
        ("order_placed", -2),
        ("damaged", -3),
    ]
    assert history[0]["order_number"]


# --- coupons ------------------------------------------------------------------------------------


def test_coupon_rules_targeting_and_usage(owner: TestClient, shopper: TestClient) -> None:
    configure(owner, guest_checkout_enabled=True, payment_options=[COD])
    girls = owner.post(f"{ADMIN}/categories", json={"name": "Girls"}, headers=csrf(owner)).json()[
        "id"
    ]
    boys = owner.post(f"{ADMIN}/categories", json={"name": "Boys"}, headers=csrf(owner)).json()[
        "id"
    ]
    dress = make_product(owner, sku="TK-DRS-1", category_ids=[UUID(girls)])
    make_product(owner, sku="TK-TEE-1", name="Navy Tee", category_ids=[UUID(boys)])

    def create(**body: Any) -> Any:
        return owner.post(f"{ADMIN}/coupons", json=body, headers=csrf(owner))

    assert (
        create(code="BAD CODE", discount_type="percentage", discount_value="10").status_code == 422
    )
    assert create(code="HALF", discount_type="percentage", discount_value="150").status_code == 422
    boys_only = create(
        code="BOYS20", discount_type="percentage", discount_value="20", category_ids=[boys]
    )
    assert boys_only.status_code == 201, boys_only.text
    create(
        code="BIGSPEND", discount_type="fixed_amount", discount_value="100", min_order_amount="5000"
    )
    create(code="ONCE", discount_type="fixed_amount", discount_value="50", usage_limit=1)
    create(code="MEMBERS", discount_type="fixed_amount", discount_value="50", per_user_limit=1)
    capped = create(
        code="CAPPED", discount_type="percentage", discount_value="50", max_discount_amount="100"
    )
    off = create(code="PAUSED", discount_type="fixed_amount", discount_value="50")
    owner.patch(
        f"{ADMIN}/coupons/{off.json()['id']}/active", json={"is_active": False}, headers=csrf(owner)
    )
    assert capped.status_code == 201

    add(shopper, variant(dress, "2-3Y"), 2)  # 798.00 of girls' items

    def quote(code: str) -> dict[str, Any]:
        return shopper.post(f"{API}/checkout/quote", json={"coupon_code": code}).json()

    assert "doesn't apply" in quote("BOYS20")["coupon_error"]
    assert "at least" in quote("BIGSPEND")["coupon_error"]
    assert "isn't valid" in quote("PAUSED")["coupon_error"]
    assert "Sign in" in quote("MEMBERS")["coupon_error"]
    assert quote("CAPPED")["discount_total"] == "100.00"  # 50% capped at ₹100
    assert quote("ONCE")["discount_total"] == "50.00"

    assert place(shopper, coupon_code="ONCE").status_code == 201
    add(shopper, variant(dress, "2-3Y"), 1)
    assert "fully used" in quote("ONCE")["coupon_error"]
    used = next(c for c in owner.get(f"{ADMIN}/coupons").json() if c["code"] == "ONCE")
    assert (used["times_used"], used["discount_given"]) == (1, "50.00")


# --- shipping -------------------------------------------------------------------------------------


def test_free_shipping_threshold_and_pin_rules(owner: TestClient, shopper: TestClient) -> None:
    owner.post(
        f"{ADMIN}/shipping-rules",
        json={
            "name": "Standard",
            "fee": "60",
            "min_order_amount": "0",
            "priority": 10,
            "is_active": True,
        },
        headers=csrf(owner),
    )
    configure(
        owner,
        guest_checkout_enabled=True,
        payment_options=[COD],
        shipping_settings={
            "free_shipping_threshold": "700",
            "pin_mode": "allow_list",
            "allowed_pin_prefixes": ["41"],
            "delivery_estimate": "Usually 3–5 working days (estimate)",  # noqa: RUF001 - intended typography
        },
    )
    product = make_product(owner)
    add(shopper, variant(product, "2-3Y"), 1)  # 399 < 700
    assert shopper.post(f"{API}/checkout/quote", json={}).json()["shipping_total"] == "60.00"
    add(shopper, variant(product, "2-3Y"), 1)  # 798 >= 700
    assert shopper.post(f"{API}/checkout/quote", json={}).json()["shipping_total"] == "0.00"

    assert shopper.get(f"{API}/checkout/pin/411001").json()["serviceable"] is True
    assert shopper.get(f"{API}/checkout/pin/110001").json()["serviceable"] is False
    blocked = place(shopper, address={**ADDRESS, "postal_code": "110001"})
    assert blocked.status_code == 422 and "110001" in blocked.json()["detail"]
    assert place(shopper).status_code == 201

    site = shopper.get(f"{API}/content/site").json()
    assert site["shipping"]["delivery_estimate"].endswith("(estimate)")
    assert "allowed_pin_prefixes" not in site["shipping"]  # internal rules stay private
    # Unset policy is published with the defaults the after-sale service enforces: all off.
    policy = site["order_policies"]
    assert policy["cancellation_enabled"] is False and policy["returns_enabled"] is False
    assert policy["reasons"] and policy["return_window_days"] == 7


# --- cancellations, returns, exchanges ----------------------------------------------------------


def test_cancellation_request_follows_policy_and_restocks(
    owner: TestClient, app: FastAPI, container: Container
) -> None:
    configure(owner, guest_checkout_enabled=False, payment_options=[COD])
    product = make_product(owner)
    size_s = variant(product, "2-3Y")
    meera = customer(app, "meera@example.com")
    add(meera, size_s, 2)
    number = place(meera).json()["order_number"]
    assert stock(container, size_s) == 3

    body = {"kind": "cancellation", "reason": "Other", "message": "Ordered twice by mistake"}
    disabled = meera.post(f"{API}/account/orders/{number}/requests", json=body, headers=csrf(meera))
    assert disabled.status_code == 422

    configure(owner, order_policies={"cancellation_enabled": True})
    created = meera.post(f"{API}/account/orders/{number}/requests", json=body, headers=csrf(meera))
    assert created.status_code == 201, created.text
    again = meera.post(f"{API}/account/orders/{number}/requests", json=body, headers=csrf(meera))
    assert again.status_code == 409

    request_id = owner.get(f"{ADMIN}/order-requests").json()["items"][0]["id"]
    decided = owner.post(
        f"{ADMIN}/order-requests/{request_id}/decision", json={"approve": True}, headers=csrf(owner)
    )
    assert decided.json()["status"] == "completed"
    assert stock(container, size_s) == 5
    order = owner.get(f"{ADMIN}/orders/{admin_order_id(owner, number)}").json()
    assert order["status"] == "cancelled" and order["payment_status"] == "unpaid"
    mine = meera.get(f"{API}/account/orders/{number}/requests").json()
    assert mine[0]["status"] == "completed"


def test_return_restocks_only_after_verification_and_records_refunds(
    owner: TestClient, app: FastAPI, container: Container
) -> None:
    configure(
        owner,
        guest_checkout_enabled=False,
        payment_options=[COD],
        order_policies={"returns_enabled": True, "return_window_days": 14},
    )
    product = make_product(owner)
    size_s = variant(product, "2-3Y")
    asha = customer(app, "asha@example.com")
    add(asha, size_s, 2)
    number = place(asha).json()["order_number"]
    order_id = admin_order_id(owner, number)
    sku = f"{product['sku']}-S"

    early = asha.post(
        f"{API}/account/orders/{number}/requests",
        json={"kind": "return", "reason": "Wrong size", "items": [{"sku": sku, "quantity": 1}]},
        headers=csrf(asha),
    )
    assert early.status_code == 422  # not delivered yet

    move(owner, order_id, "confirmed", "processing", "packed", "shipped", "delivered")
    owner.patch(
        f"{ADMIN}/orders/{order_id}/payment", json={"payment_status": "paid"}, headers=csrf(owner)
    )
    returned = asha.post(
        f"{API}/account/orders/{number}/requests",
        json={"kind": "return", "reason": "Wrong size", "items": [{"sku": sku, "quantity": 1}]},
        headers=csrf(asha),
    )
    assert returned.status_code == 201, returned.text
    rid = owner.get(f"{ADMIN}/order-requests", params={"kind": "return"}).json()["items"][0]["id"]

    too_soon = owner.post(
        f"{ADMIN}/order-requests/{rid}/received", json={"restock": True}, headers=csrf(owner)
    )
    assert too_soon.status_code == 409  # approve first
    owner.post(
        f"{ADMIN}/order-requests/{rid}/decision", json={"approve": True}, headers=csrf(owner)
    )
    assert stock(container, size_s) == 3  # approval alone never restocks
    owner.post(
        f"{ADMIN}/order-requests/{rid}/received",
        json={"restock": True, "note": "Unworn, tags on"},
        headers=csrf(owner),
    )
    assert stock(container, size_s) == 4

    too_much = owner.post(
        f"{ADMIN}/order-requests/{rid}/complete",
        json={"refund_amount": "9999"},
        headers=csrf(owner),
    )
    assert too_much.status_code == 422
    done = owner.post(
        f"{ADMIN}/order-requests/{rid}/complete",
        json={"refund_amount": "399.00"},
        headers=csrf(owner),
    )
    assert done.json()["refund_amount"] == "399.00"
    assert owner.get(f"{ADMIN}/orders/{order_id}").json()["payment_status"] == "partially_refunded"
    with container.session_factory() as session:
        reasons = [m.reason for m in session.scalars(select(InventoryMovementModel))]
    assert reasons.count("return") == 1


# --- reviews ------------------------------------------------------------------------------------


def test_reviews_are_moderated_and_verified_only_by_real_purchases(
    owner: TestClient, app: FastAPI
) -> None:
    configure(owner, guest_checkout_enabled=False, payment_options=[COD])
    product = make_product(owner)
    slug = product["slug"]
    buyer = customer(app, "buyer@example.com")
    add(buyer, variant(product, "2-3Y"))
    place(buyer)
    browser = customer(app, "browser@example.com")

    def review(client: TestClient, **extra: Any) -> Any:
        files = extra.pop("files", None)
        return client.post(
            f"{API}/products/{slug}/reviews",
            data={"rating": "5", "title": "Lovely", "body": "Soft fabric", **extra},
            files=files,
            headers=csrf(client),
        )

    assert (
        TestClient(app)
        .post(f"{API}/products/{slug}/reviews", data={"rating": "5", "body": "x"})
        .status_code
        == 401
    )
    bad_photo = review(
        buyer, files=[("photos", ("evil.png", BytesIO(b"not an image"), "image/png"))]
    )
    assert bad_photo.status_code in (415, 422)
    ok = review(buyer, files=[("photos", ("dress.png", BytesIO(make_image()), "image/png"))])
    assert ok.status_code == 201, ok.text
    assert review(buyer).status_code == 409  # one review per customer per product
    assert review(browser, rating="3").status_code == 201

    assert (
        owner.get(f"{API}/products/{slug}/reviews").json()["count"] == 0
    )  # nothing until approved
    queue = owner.get(f"{ADMIN}/reviews").json()["items"]
    assert {r["author_email"]: r["is_verified_purchase"] for r in queue} == {
        "buyer@example.com": True,
        "browser@example.com": False,
    }
    for r in queue:
        owner.patch(f"{ADMIN}/reviews/{r['id']}", json={"status": "approved"}, headers=csrf(owner))
    public = owner.get(f"{API}/products/{slug}/reviews").json()
    assert public["count"] == 2 and public["average"] == "4.0"
    verified = next(r for r in public["items"] if r["verified_purchase"])
    assert len(verified["images"]) == 1 and verified["author"] == "Meera"

    hide = next(r for r in queue if r["author_email"] == "browser@example.com")
    owner.patch(
        f"{ADMIN}/reviews/{hide['id']}",
        json={"status": "rejected", "note": "Off-topic"},
        headers=csrf(owner),
    )
    assert owner.get(f"{API}/products/{slug}/reviews").json()["count"] == 1


# --- recommendations ------------------------------------------------------------------------------


def test_bestsellers_come_from_orders_and_curated_fallbacks(
    owner: TestClient, shopper: TestClient
) -> None:
    configure(owner, guest_checkout_enabled=True, payment_options=[COD])
    girls = owner.post(f"{ADMIN}/categories", json={"name": "Girls"}, headers=csrf(owner)).json()[
        "id"
    ]
    a = make_product(owner, sku="TK-A", name="Alpha", category_ids=[UUID(girls)], is_featured=True)
    b = make_product(owner, sku="TK-B", name="Beta", category_ids=[UUID(girls)])
    c = make_product(
        owner, sku="TK-C", name="Gamma", category_ids=[UUID(girls)], related_product_ids=[a["id"]]
    )

    add(shopper, variant(b, "2-3Y"), 3)
    place(shopper)
    add(shopper, variant(a, "2-3Y"), 1)
    place(shopper)

    ranked = owner.get(f"{API}/products", params={"sort": "bestselling"}).json()["items"]
    assert [p["name"] for p in ranked][:2] == ["Beta", "Alpha"]
    recs = owner.get(f"{API}/products/{c['slug']}/recommendations").json()
    assert [p["name"] for p in recs["curated"]] == ["Alpha"]
    assert [p["name"] for p in recs["bestsellers"]] == ["Beta"]  # Alpha already curated
    assert not any("bestseller" in (p.get("badges") or []) for p in ranked)  # no fake badges

    section = owner.post(
        f"{ADMIN}/homepage/sections",
        json={
            "section_type": "product_grid",
            "title": "Bestsellers",
            "selection_mode": "bestsellers",
            "product_limit": 3,
        },
        headers=csrf(owner),
    ).json()["id"]
    owner.put(
        f"{ADMIN}/homepage/sections/{section}/products",
        json={"product_ids": [c["id"]]},
        headers=csrf(owner),
    )
    featured = owner.post(
        f"{ADMIN}/homepage/sections",
        json={
            "section_type": "product_carousel",
            "title": "Featured",
            "selection_mode": "featured",
        },
        headers=csrf(owner),
    ).json()["id"]
    assert owner.post(f"{ADMIN}/homepage/publish", json={}, headers=csrf(owner)).status_code == 200
    sections = {s["id"]: s for s in owner.get(f"{API}/content/homepage").json()["sections"]}
    assert [p["name"] for p in sections[section]["products"]] == [
        "Beta",
        "Alpha",
        "Gamma",
    ]  # Gamma = curated fallback
    assert [p["name"] for p in sections[featured]["products"]] == ["Alpha"]


# --- notifications, analytics, staff, audit -------------------------------------------------------


def test_notifications_are_never_reported_sent_without_a_provider(
    owner: TestClient, shopper: TestClient, container: Container
) -> None:
    configure(owner, guest_checkout_enabled=True, payment_options=[COD])
    product = make_product(owner)
    add(shopper, variant(product, "2-3Y"))
    place(shopper)
    with container.session_factory() as session:
        logged = session.scalars(select(NotificationModel)).all()
    assert [(n.template, n.status, n.provider) for n in logged] == [
        ("order_received", "skipped", "development-log")
    ]
    assert "asha@example.com" not in logged[0].recipient  # masked
    listed = owner.get(f"{ADMIN}/notifications").json()["items"]
    assert listed[0]["status"] == "skipped"


def test_analytics_keep_order_value_payments_and_whatsapp_separate(
    owner: TestClient, shopper: TestClient
) -> None:
    configure(
        owner,
        guest_checkout_enabled=True,
        payment_options=[COD],
        whatsapp_ordering_enabled=True,
        whatsapp_number="+919876543210",
    )
    product = make_product(owner)
    size_s = variant(product, "2-3Y")
    add(shopper, size_s, 2)
    first = place(shopper).json()["order_number"]
    add(shopper, size_s, 1)
    place(shopper)
    shopper.post(
        f"{API}/whatsapp-requests", json={"items": [{"variant_id": size_s, "quantity": 1}]}
    )
    owner.patch(
        f"{ADMIN}/orders/{admin_order_id(owner, first)}/payment",
        json={"payment_status": "paid"},
        headers=csrf(owner),
    )

    report = owner.get(f"{ADMIN}/analytics").json()
    assert report["orders_placed"] == 2 and report["website_orders"] == 2
    assert report["order_value_placed"] == "1197.00"
    assert report["payments_recorded"] == "798.00"  # only what staff recorded as paid
    assert (report["whatsapp_requests"], report["whatsapp_converted"]) == (1, 0)
    assert report["top_products"][0]["units"] == 3
    assert sum(d["website_orders"] for d in report["by_day"]) == 2
    assert (
        owner.get(
            f"{ADMIN}/analytics", params={"start": "2026-02-01", "end": "2026-01-01"}
        ).status_code
        == 422
    )


def test_staff_roles_are_owner_managed_audited_and_enforced(
    owner: TestClient, app: FastAPI, container: Container
) -> None:
    hire = customer(app, "hire@example.com")
    assert hire.get(f"{ADMIN}/orders").status_code == 403

    granted = owner.put(
        f"{ADMIN}/staff/roles",
        json={"email": "hire@example.com", "roles": ["order_manager"]},
        headers=csrf(owner),
    )
    assert granted.status_code == 200 and "order_manager" in granted.json()["roles"]
    assert hire.get(f"{API}/auth/me").status_code == 401  # signed out to pick up new rights
    login(hire, "hire@example.com", PASSWORD)
    assert hire.get(f"{ADMIN}/orders").status_code == 200
    assert hire.get(f"{ADMIN}/products").status_code == 403  # catalogue is not theirs
    assert hire.get(f"{ADMIN}/staff").status_code == 403

    unknown = owner.put(
        f"{ADMIN}/staff/roles",
        json={"email": "nobody@example.com", "roles": ["order_manager"]},
        headers=csrf(owner),
    )
    assert unknown.status_code == 404  # no admin accounts are created over HTTP
    me = owner.get(f"{API}/auth/me").json()["email"]
    assert (
        owner.put(
            f"{ADMIN}/staff/roles", json={"email": me, "roles": []}, headers=csrf(owner)
        ).status_code
        == 403
    )

    product = make_product(owner)
    payload_price = owner.get(f"{ADMIN}/products/{product['id']}").json()
    assert payload_price["price"]["selling_price"] == "399.00"
    log = owner.get(f"{ADMIN}/audit-log", params={"action": "user.roles"}).json()["items"]
    assert log[0]["changes"]["after"] == ["order_manager"]
    with container.session_factory() as session:
        actions = {a.action for a in session.scalars(select(AuditLogModel))}
    assert {"user.roles_changed", "product.created"} <= actions
