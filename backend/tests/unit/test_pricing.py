from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.entities.catalog import Product, ProductVariant
from app.domain.entities.commerce import OrderLineSnapshot
from app.domain.enums import ProductStatus
from app.domain.errors import DomainValidationError, PricingError
from app.domain.value_objects.pricing import (
    PricedLine,
    PricePair,
    calculate_totals,
    resolve_variant_price,
    to_money,
)

D = Decimal


# --- selling price / original price (MRP) validation -------------------------------------------


def test_stores_both_prices_exactly() -> None:
    price = PricePair.of("399", "599.00")
    assert price.selling == D("399.00")
    assert price.original == D("599.00")


@pytest.mark.parametrize(
    ("selling", "original", "message"),
    [
        ("-1.00", None, "cannot be negative"),
        ("399.00", "-5.00", "cannot be negative"),
        ("399.00", "299.00", "greater than or equal"),
        ("399.999", None, "two decimal places"),
        ("NaN", None, "not a valid amount"),
        ("abc", None, "not a valid amount"),
        ("10000000000.00", None, "too large"),
    ],
)
def test_rejects_invalid_prices(selling: str, original: str | None, message: str) -> None:
    with pytest.raises(PricingError, match=message):
        PricePair.of(selling, original)


def test_rejects_floats_outright() -> None:
    with pytest.raises(PricingError, match="exact decimal"):
        to_money(399.99)  # type: ignore[arg-type]


# --- discounts ---------------------------------------------------------------------------------


def test_discount_is_calculated_from_stored_prices() -> None:
    price = PricePair.of("399.00", "599.00")
    assert price.has_discount
    assert price.discount_amount == D("200.00")
    assert price.discount_percent == 33  # 33.39% rounded down, never overstated


@pytest.mark.parametrize(
    ("selling", "original", "percent"),
    [
        ("1.00", "3.00", 66),  # 66.67 -> 66
        ("999.00", "1000.00", 0),  # 0.1% -> 0, still a (tiny) discount amount
        ("0.00", "100.00", 100),
        ("450.00", "900.00", 50),
    ],
)
def test_discount_percent_rounds_down(selling: str, original: str, percent: int) -> None:
    assert PricePair.of(selling, original).discount_percent == percent


@pytest.mark.parametrize("original", [None, "449.00"])
def test_no_discount_without_a_higher_original_price(original: str | None) -> None:
    price = PricePair.of("449.00", original)
    assert not price.has_discount
    assert price.discount_amount is None
    assert price.discount_percent is None


# --- variant inheritance and overrides -----------------------------------------------------------


PRODUCT_PRICE = PricePair.of("399.00", "599.00")


def test_variant_without_overrides_inherits_both_prices() -> None:
    assert resolve_variant_price(PRODUCT_PRICE) == PRODUCT_PRICE


def test_variant_selling_override_keeps_inherited_mrp() -> None:
    price = resolve_variant_price(PRODUCT_PRICE, selling_override=D("449.00"))
    assert (price.selling, price.original) == (D("449.00"), D("599.00"))
    assert price.discount_percent == 25


def test_variant_original_override_keeps_inherited_selling() -> None:
    price = resolve_variant_price(PRODUCT_PRICE, original_override=D("699.00"))
    assert (price.selling, price.original) == (D("399.00"), D("699.00"))


def test_variant_can_override_both() -> None:
    price = resolve_variant_price(
        PRODUCT_PRICE, selling_override=D("500.00"), original_override=D("800.00")
    )
    assert (price.selling, price.original, price.discount_percent) == (
        D("500.00"),
        D("800.00"),
        37,
    )


def test_variant_override_cannot_exceed_inherited_mrp() -> None:
    with pytest.raises(PricingError):
        resolve_variant_price(PRODUCT_PRICE, selling_override=D("650.00"))


def test_product_validation_checks_every_variant_against_product_price() -> None:
    product = Product(
        id=uuid4(),
        name="Dress",
        slug="dress",
        sku="DRS",
        price=PRODUCT_PRICE,
        variants=[ProductVariant(id=uuid4(), sku="DRS-1", selling_price_override=D("700.00"))],
    )
    with pytest.raises(PricingError):
        product.validate()


# --- server-side totals --------------------------------------------------------------------------


def test_line_and_order_totals_are_computed_server_side() -> None:
    lines = [
        PricedLine(PricePair.of("399.00", "599.00"), 2),
        PricedLine(PricePair.of("549.00"), 1),
    ]
    totals = calculate_totals(lines, discount=D("100.00"), shipping=D("49.00"))
    assert totals.subtotal == D("1347.00")
    assert totals.savings == D("400.00")
    assert totals.discount_total == D("100.00")
    assert totals.grand_total == D("1296.00")


def test_discount_can_never_make_total_negative() -> None:
    totals = calculate_totals([PricedLine(PricePair.of("100.00"), 1)], discount=D("500.00"))
    assert totals.discount_total == D("100.00")
    assert totals.grand_total == D("0.00")


@pytest.mark.parametrize("quantity", [0, -1, True])
def test_line_quantity_must_be_positive_integer(quantity: int) -> None:
    with pytest.raises(PricingError):
        PricedLine(PRODUCT_PRICE, quantity)


# --- order snapshots -----------------------------------------------------------------------------


def _product(**overrides: object) -> Product:
    variant = ProductVariant(
        id=uuid4(),
        sku="DRS-L",
        size="5-6Y",
        colour="Blush",
        selling_price_override=D("449.00"),
        stock_quantity=3,
    )
    values: dict[str, object] = {
        "id": uuid4(),
        "name": "Blush Dress",
        "slug": "blush-dress",
        "sku": "DRS",
        "price": PRODUCT_PRICE,
        "status": ProductStatus.ACTIVE,
        "variants": [variant],
        **overrides,
    }
    return Product(**values)  # type: ignore[arg-type]


def test_snapshot_captures_name_sku_options_and_effective_prices() -> None:
    product = _product()
    variant = product.variants[0]
    line = OrderLineSnapshot.capture(product, variant.id, 2)

    assert (line.product_name, line.sku, line.size, line.colour) == (
        "Blush Dress",
        "DRS-L",
        "5-6Y",
        "Blush",
    )
    assert line.unit_price == PricePair.of("449.00", "599.00")
    assert line.priced.total == D("898.00")

    # Later catalogue edits do not touch the captured snapshot.
    product.name = "Renamed"
    product.price = PricePair.of("10.00")
    assert line.product_name == "Blush Dress"
    assert line.priced.total == D("898.00")


def test_snapshot_rejects_unavailable_or_insufficient_stock() -> None:
    product = _product()
    vid = product.variants[0].id
    with pytest.raises(DomainValidationError, match="Only 3 left"):
        OrderLineSnapshot.capture(product, vid, 4)
    product.status = ProductStatus.DRAFT
    with pytest.raises(DomainValidationError, match="not available"):
        OrderLineSnapshot.capture(product, vid, 1)
    with pytest.raises(DomainValidationError, match="does not belong"):
        OrderLineSnapshot.capture(product, uuid4(), 1)
