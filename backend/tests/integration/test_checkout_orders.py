"""Prompt 6: cart, website checkout, accounts, WhatsApp requests and admin conversion.

Runs against a real (SQLite) database built by the Alembic migrations.
"""

import re
from typing import Any
from urllib.parse import unquote
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.bootstrap import Container
from app.domain.entities.identity import Role
from app.infrastructure.db.models.catalog import ProductVariantModel
from app.infrastructure.db.models.commerce import (
    InventoryMovementModel,
    OrderModel,
    WhatsAppOrderRequestModel,
)
from app.infrastructure.notifications.mailer import DevelopmentLogMailer
from tests.conftest import PASSWORD, create_user, csrf, login, product_payload

API = "/api/v1"
ADDRESS = {
    "full_name": "Asha Rao",
    "phone": "+91 98765 43210",
    "line1": "12 Rose Lane",
    "city": "Pune",
    "state": "Maharashtra",
    "postal_code": "411001",
}
COD = {
    "method": "cash_on_delivery",
    "enabled": True,
    "label": "Cash on delivery",
    "instructions": "Pay when it arrives.",
}


# --- helpers -----------------------------------------------------------------------------------


def configure(owner: TestClient, **settings: Any) -> None:
    response = owner.patch(f"{API}/admin/settings", json=settings, headers=csrf(owner))
    assert response.status_code == 200, response.text


def make_product(owner: TestClient, sku: str = "TK-DRS-001", **kwargs: Any) -> dict[str, Any]:
    response = owner.post(
        f"{API}/admin/products", json=product_payload(sku=sku, **kwargs), headers=csrf(owner)
    )
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def variant(product: dict[str, Any], size: str) -> str:
    return next(v["id"] for v in product["variants"] if v["size"] == size)


def unsafe_headers(client: TestClient, **extra: str) -> dict[str, str]:
    """CSRF header when signed in (guests have no session cookie, so none is needed)."""
    headers = dict(extra)
    if client.cookies.get("tk_csrf"):
        headers.update(csrf(client))
    return headers


def add(client: TestClient, variant_id: str, quantity: int = 1) -> Any:
    return client.post(
        f"{API}/cart/items",
        json={"variant_id": variant_id, "quantity": quantity},
        headers=unsafe_headers(client),
    )


def checkout_body(**overrides: Any) -> dict[str, Any]:
    return {
        "customer_name": "Asha Rao",
        "customer_phone": "+91 98765 43210",
        "customer_email": "asha@example.com",
        "address": ADDRESS,
        "payment_method": "cash_on_delivery",
        **overrides,
    }


def place(client: TestClient, key: str | None = None, **overrides: Any) -> Any:
    return client.post(
        f"{API}/checkout/orders",
        json=checkout_body(**overrides),
        headers=unsafe_headers(client, **{"Idempotency-Key": key or uuid4().hex}),
    )


def stock(container: Container, variant_id: str) -> int:
    with container.session_factory() as session:
        value = session.scalar(
            select(ProductVariantModel.stock_quantity).where(
                ProductVariantModel.id == UUID(variant_id)
            )
        )
    return int(value or 0)


def count(container: Container, model: Any) -> int:
    with container.session_factory() as session:
        return int(session.scalar(select(func.count()).select_from(model)) or 0)


# --- website checkout --------------------------------------------------------------------------


def test_guest_order_uses_server_totals_and_is_idempotent(
    owner: TestClient, shopper: TestClient, container: Container
) -> None:
    configure(owner, guest_checkout_enabled=True, payment_options=[COD])
    product = make_product(owner)
    size_s = variant(product, "2-3Y")

    assert add(shopper, size_s, 2).status_code == 200
    quote = shopper.post(f"{API}/checkout/quote", json={}).json()
    assert quote["can_place_order"] is True
    assert quote["subtotal"] == "798.00"
    assert [m["method"] for m in quote["payment_methods"]] == ["cash_on_delivery"]

    first = place(shopper, key="order-attempt-0001")
    assert first.status_code == 201, first.text
    order = first.json()
    assert order["subtotal"] == "798.00"
    assert order["grand_total"] == "798.00"
    assert order["lines"][0]["unit_selling_price"] == "399.00"
    assert order["lines"][0]["unit_original_price"] == "599.00"  # both prices snapshotted
    assert order["lines"][0]["size"] == "2-3Y"
    assert order["payment_instructions"] == "Pay when it arrives."
    assert "status" not in order and "payment_status" not in order  # no tracking for customers
    assert stock(container, size_s) == 3

    # Double click / network retry: same key -> same order, no second stock deduction.
    again = place(shopper, key="order-attempt-0001")
    assert again.status_code == 200
    assert again.json()["order_number"] == order["order_number"]
    assert stock(container, size_s) == 3
    assert count(container, OrderModel) == 1
    with container.session_factory() as session:
        movements = session.scalars(select(InventoryMovementModel)).all()
    assert [(m.reason, m.quantity_delta) for m in movements if m.reason == "order_placed"] == [
        ("order_placed", -2)
    ]

    # The bag was converted into the order.
    assert shopper.get(f"{API}/cart").json()["lines"] == []
    with container.session_factory() as session:
        stored = session.scalars(select(OrderModel)).one()
    assert (stored.status, stored.payment_status) == ("pending_confirmation", "unpaid")


def test_browser_supplied_prices_are_rejected(owner: TestClient, shopper: TestClient) -> None:
    configure(owner, guest_checkout_enabled=True, payment_options=[COD])
    product = make_product(owner)
    add(shopper, variant(product, "2-3Y"))
    response = place(shopper, grand_total="1.00", subtotal="1.00")
    assert response.status_code == 422  # unknown money fields are refused outright


def test_expected_total_mismatch_stops_the_order(
    owner: TestClient, shopper: TestClient, container: Container
) -> None:
    configure(owner, guest_checkout_enabled=True, payment_options=[COD])
    product = make_product(owner)
    add(shopper, variant(product, "2-3Y"))
    response = place(shopper, expected_grand_total="100.00")
    assert response.status_code == 409
    assert "399.00" in response.json()["detail"]
    assert count(container, OrderModel) == 0


def test_guest_checkout_disabled_requires_an_account(
    owner: TestClient, shopper: TestClient
) -> None:
    configure(owner, guest_checkout_enabled=False, payment_options=[COD])
    product = make_product(owner)
    add(shopper, variant(product, "2-3Y"))
    quote = shopper.post(f"{API}/checkout/quote", json={}).json()
    assert quote["can_place_order"] is False
    assert "sign in" in quote["blocking_reason"].lower()
    assert place(shopper).status_code == 401


def test_no_enabled_payment_method_blocks_checkout(owner: TestClient, shopper: TestClient) -> None:
    configure(owner, guest_checkout_enabled=True, payment_options=[{**COD, "enabled": False}])
    product = make_product(owner)
    add(shopper, variant(product, "2-3Y"))
    quote = shopper.post(f"{API}/checkout/quote", json={}).json()
    assert quote["payment_methods"] == []
    assert "no payment method" in quote["blocking_reason"]
    response = place(shopper)
    assert response.status_code == 422
    assert "payment method" in response.json()["detail"]


def test_disabled_payment_method_cannot_be_chosen(owner: TestClient, shopper: TestClient) -> None:
    upi = {"method": "upi_manual", "enabled": False, "label": "UPI"}
    configure(owner, guest_checkout_enabled=True, payment_options=[COD, upi])
    product = make_product(owner)
    add(shopper, variant(product, "2-3Y"))
    assert place(shopper, payment_method="upi_manual").status_code == 422


def test_invalid_variants_and_quantities_are_rejected(
    owner: TestClient, shopper: TestClient
) -> None:
    product = make_product(owner)
    in_stock, sold_out = variant(product, "2-3Y"), variant(product, "3-4Y")
    assert add(shopper, str(uuid4())).status_code == 404
    assert add(shopper, in_stock, 0).status_code == 422
    assert add(shopper, in_stock, 100).status_code == 422
    assert add(shopper, sold_out).status_code == 422
    assert add(shopper, in_stock, 6).status_code == 422  # only 5 in stock
    assert add(shopper, in_stock, 5).status_code == 200
    assert add(shopper, in_stock, 1).status_code == 422  # would exceed stock


def test_stock_sold_out_after_adding_blocks_checkout(
    owner: TestClient, shopper: TestClient, container: Container
) -> None:
    configure(owner, guest_checkout_enabled=True, payment_options=[COD])
    product = make_product(owner)
    size_s = variant(product, "2-3Y")
    add(shopper, size_s, 2)
    with container.session_factory() as session:
        row = session.get(ProductVariantModel, UUID(size_s))
        assert row is not None
        row.stock_quantity = 1
        session.commit()
    quote = shopper.post(f"{API}/checkout/quote", json={}).json()
    assert quote["can_place_order"] is False
    assert place(shopper).status_code in (409, 422)
    assert count(container, OrderModel) == 0
    assert stock(container, size_s) == 1


def test_coupon_discount_is_calculated_on_the_server(
    owner: TestClient, shopper: TestClient, container: Container
) -> None:
    from app.infrastructure.db.models.marketing import CouponModel

    configure(owner, guest_checkout_enabled=True, payment_options=[COD])
    product = make_product(owner)
    add(shopper, variant(product, "2-3Y"), 2)
    with container.session_factory() as session:
        session.add(CouponModel(code="TWINKLE10", discount_type="percentage", discount_value=10))
        session.commit()
    quote = shopper.post(f"{API}/checkout/quote", json={"coupon_code": "twinkle10"}).json()
    assert (quote["discount_total"], quote["grand_total"]) == ("79.80", "718.20")
    bad = shopper.post(f"{API}/checkout/quote", json={"coupon_code": "NOPE"}).json()
    assert bad["coupon_error"] and bad["discount_total"] == "0.00"
    order = place(shopper, coupon_code="TWINKLE10").json()
    assert (order["discount_total"], order["grand_total"]) == ("79.80", "718.20")


# --- accounts -----------------------------------------------------------------------------------


def register(client: TestClient, email: str) -> None:
    response = client.post(
        f"{API}/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": "Meera Shah"},
    )
    assert response.status_code == 201, response.text


def test_guest_bag_merges_into_account_after_login(
    owner: TestClient, shopper: TestClient, container: Container
) -> None:
    product = make_product(owner)
    size_s = variant(product, "2-3Y")
    customer = create_user(container, Role.CUSTOMER, password=PASSWORD)
    add(shopper, size_s, 1)
    assert shopper.cookies.get("tk_cart")
    login(shopper, customer.email, PASSWORD)
    bag = shopper.get(f"{API}/cart").json()
    assert [(line["variant_id"], line["quantity"]) for line in bag["lines"]] == [(size_s, 1)]
    assert not shopper.cookies.get("tk_cart")  # guest token retired after the merge

    # The account bag persists across sessions/devices.
    other_device = TestClient(shopper.app)
    login(other_device, customer.email, PASSWORD)
    assert other_device.get(f"{API}/cart").json()["item_count"] == 1


def test_account_checkout_history_and_ownership(
    owner: TestClient, app: FastAPI, container: Container
) -> None:
    configure(owner, guest_checkout_enabled=False, payment_options=[COD])
    product = make_product(owner)
    meera = TestClient(app)
    register(meera, "meera@example.com")
    add(meera, variant(product, "2-3Y"))
    response = place(meera, customer_email=None, save_address=True)
    assert response.status_code == 201, response.text
    number = response.json()["order_number"]
    assert response.json()["customer_email"] == "meera@example.com"

    history = meera.get(f"{API}/account/orders").json()
    assert [o["order_number"] for o in history["items"]] == [number]
    detail = meera.get(f"{API}/account/orders/{number}")
    assert detail.status_code == 200 and "status" not in detail.json()
    assert len(meera.get(f"{API}/account/addresses").json()) == 1  # saved for next time

    stranger = TestClient(app)
    register(stranger, "stranger@example.com")
    assert stranger.get(f"{API}/account/orders/{number}").status_code == 404
    assert stranger.get(f"{API}/account/orders").json()["items"] == []
    assert TestClient(app).get(f"{API}/account/orders").status_code == 401


def test_no_customer_order_tracking_routes(app: FastAPI) -> None:
    paths = set(app.openapi()["paths"])
    assert not any(re.search(r"track", path) for path in paths)
    public_order_paths = [p for p in paths if "/orders" in p and not p.startswith(f"{API}/admin")]
    assert sorted(public_order_paths) == [
        f"{API}/account/orders",
        f"{API}/account/orders/{{order_number}}",
        f"{API}/account/orders/{{order_number}}/requests",  # cancel/return requests, not tracking
        f"{API}/checkout/orders",
    ]


def test_profile_and_address_book(app: FastAPI) -> None:
    client = TestClient(app)
    register(client, "neha@example.com")
    updated = client.patch(
        f"{API}/account/profile",
        json={"full_name": "Neha  Kapoor", "phone": "+91 99887 76655"},
        headers=csrf(client),
    )
    assert updated.status_code == 200 and updated.json()["full_name"] == "Neha Kapoor"

    bad_pin = client.post(
        f"{API}/account/addresses", json={**ADDRESS, "postal_code": "12345"}, headers=csrf(client)
    )
    assert bad_pin.status_code == 422
    first = client.post(f"{API}/account/addresses", json=ADDRESS, headers=csrf(client)).json()
    second = client.post(
        f"{API}/account/addresses",
        json={**ADDRESS, "city": "Mumbai", "is_default": True},
        headers=csrf(client),
    ).json()
    assert second["is_default"] is True
    listed = client.get(f"{API}/account/addresses").json()
    assert [a["is_default"] for a in listed] == [True, False]
    assert (
        client.delete(f"{API}/account/addresses/{second['id']}", headers=csrf(client)).status_code
        == 204
    )
    assert client.get(f"{API}/account/addresses").json()[0]["id"] == first["id"]
    assert client.get(f"{API}/account/addresses").json()[0]["is_default"] is True


def test_password_reset_with_single_use_emailed_token(app: FastAPI, container: Container) -> None:
    client = TestClient(app)
    register(client, "riya@example.com")
    mailer = container.mailer
    assert isinstance(mailer, DevelopmentLogMailer)

    unknown = client.post(
        f"{API}/auth/password-reset/request",
        json={"email": "nobody@example.com"},
        headers=unsafe_headers(client),
    )
    known = client.post(
        f"{API}/auth/password-reset/request",
        json={"email": "riya@example.com"},
        headers=unsafe_headers(client),
    )
    assert unknown.status_code == known.status_code == 202
    assert unknown.json() == known.json()  # no account enumeration
    assert len(mailer.sent) == 1
    token = re.search(r"token=([\w-]+)", mailer.sent[0][2]).group(1)  # type: ignore[union-attr]

    fresh = TestClient(app)
    weak = fresh.post(
        f"{API}/auth/password-reset/confirm", json={"token": token, "new_password": "short"}
    )
    assert weak.status_code == 422
    done = fresh.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": token, "new_password": "a brand new passphrase"},
    )
    assert done.status_code == 204
    reused = fresh.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": token, "new_password": "another passphrase!"},
    )
    assert reused.status_code == 422
    assert client.get(f"{API}/auth/me").status_code == 401  # old sessions were signed out
    login(fresh, "riya@example.com", "a brand new passphrase")


# --- WhatsApp ------------------------------------------------------------------------------------


def test_whatsapp_request_records_estimate_and_builds_message(
    owner: TestClient, shopper: TestClient, container: Container
) -> None:
    configure(owner, whatsapp_ordering_enabled=True, whatsapp_number="+91 98765 43210")
    product = make_product(owner)
    size_s = variant(product, "2-3Y")
    response = shopper.post(
        f"{API}/whatsapp-requests", json={"items": [{"variant_id": size_s, "quantity": 2}]}
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["url"].startswith("https://wa.me/919876543210?text=")
    message = unquote(body["url"].split("?text=", 1)[1])
    assert message == body["message"]
    for expected in (
        "Twinkle Kids",
        body["reference"],
        "Blush Party Dress",
        "Size: 2-3Y",
        "Colour: Blush",
        "Qty 2",
        "798.00",
        "confirm availability",
    ):
        assert expected in message
    assert "Asha" not in body["url"]  # no personal details in the link

    with container.session_factory() as session:
        stored = session.scalars(select(WhatsAppOrderRequestModel)).one()
    assert (stored.status, stored.estimated_subtotal) == ("initiated", stored.estimated_subtotal)
    assert str(stored.estimated_subtotal) == "798.00"
    assert stock(container, size_s) == 5  # a request never touches stock
    assert count(container, OrderModel) == 0  # nor creates an order


def test_whatsapp_requires_configuration(owner: TestClient, shopper: TestClient) -> None:
    configure(owner, whatsapp_ordering_enabled=False)
    product = make_product(owner)
    response = shopper.post(
        f"{API}/whatsapp-requests",
        json={"items": [{"variant_id": variant(product, "2-3Y"), "quantity": 1}]},
    )
    assert response.status_code == 422
    bad_number = owner.patch(
        f"{API}/admin/settings", json={"whatsapp_number": "call me"}, headers=csrf(owner)
    )
    assert bad_number.status_code == 422


def test_admin_converts_accepted_whatsapp_request_into_an_unpaid_order(
    owner: TestClient, shopper: TestClient, container: Container
) -> None:
    configure(owner, whatsapp_ordering_enabled=True, whatsapp_number="+919876543210")
    product = make_product(owner)
    size_s = variant(product, "2-3Y")
    reference = shopper.post(
        f"{API}/whatsapp-requests", json={"items": [{"variant_id": size_s, "quantity": 1}]}
    ).json()["reference"]

    listed = owner.get(f"{API}/admin/whatsapp-requests").json()["items"]
    request = next(r for r in listed if r["reference"] == reference)
    assert request["status"] == "initiated"
    rid = request["id"]

    contacted = owner.patch(
        f"{API}/admin/whatsapp-requests/{rid}/status",
        json={"status": "contacted", "staff_note": "Customer messaged"},
        headers=csrf(owner),
    )
    assert contacted.status_code == 200 and contacted.json()["contacted_at"]

    convert = {
        "customer_name": "Asha Rao",
        "customer_phone": "+91 98765 43210",
        "address": ADDRESS,
        "payment_method": "upi_manual",
    }
    order = owner.post(
        f"{API}/admin/whatsapp-requests/{rid}/convert", json=convert, headers=csrf(owner)
    )
    assert order.status_code == 201, order.text
    data = order.json()
    assert (data["source"], data["status"], data["payment_status"]) == (
        "whatsapp",
        "pending_confirmation",
        "unpaid",
    )
    assert stock(container, size_s) == 4
    detail = owner.get(f"{API}/admin/whatsapp-requests/{rid}").json()
    assert (detail["status"], detail["converted_order_number"]) == (
        "converted",
        data["order_number"],
    )

    twice = owner.post(
        f"{API}/admin/whatsapp-requests/{rid}/convert", json=convert, headers=csrf(owner)
    )
    assert twice.status_code == 409
    assert stock(container, size_s) == 4

    # Reporting keeps them apart: website orders vs orders that came from WhatsApp.
    website = owner.get(f"{API}/admin/orders", params={"source": "website"}).json()
    assert website["total"] == 0


def test_admin_records_payment_and_cancelling_restocks(
    owner: TestClient, shopper: TestClient, container: Container
) -> None:
    configure(owner, guest_checkout_enabled=True, payment_options=[COD])
    product = make_product(owner)
    size_s = variant(product, "2-3Y")
    add(shopper, size_s, 2)
    number = place(shopper).json()["order_number"]
    order = next(
        o for o in owner.get(f"{API}/admin/orders").json()["items"] if o["order_number"] == number
    )
    assert order["payment_status"] == "unpaid"

    paid = owner.patch(
        f"{API}/admin/orders/{order['id']}/payment",
        json={"payment_status": "paid", "payment_method": "cash_on_delivery"},
        headers=csrf(owner),
    )
    assert paid.json()["payment_status"] == "paid"

    illegal = owner.patch(
        f"{API}/admin/orders/{order['id']}/status",
        json={"status": "delivered"},
        headers=csrf(owner),
    )
    assert illegal.status_code == 422
    cancelled = owner.patch(
        f"{API}/admin/orders/{order['id']}/status",
        json={"status": "cancelled"},
        headers=csrf(owner),
    )
    assert cancelled.status_code == 200
    assert stock(container, size_s) == 5

    customer = TestClient(shopper.app)
    customer_user = create_user(container, Role.CUSTOMER, password=PASSWORD)
    login(customer, customer_user.email, PASSWORD)
    assert customer.get(f"{API}/admin/orders").status_code == 403
