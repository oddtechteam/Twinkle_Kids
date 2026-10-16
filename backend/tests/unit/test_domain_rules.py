from decimal import Decimal
from uuid import uuid4

import pytest

from app.application.content_settings import validate_section_settings
from app.domain.entities.catalog import Product, ProductVariant
from app.domain.entities.content import HomepageSection, validate_ordering
from app.domain.entities.identity import ROLE_PERMISSIONS, Permission, Role, User, validate_password
from app.domain.enums import HomepageSectionType, ProductStatus, SelectionMode
from app.domain.errors import DomainValidationError
from app.domain.value_objects.pricing import PricePair
from app.domain.value_objects.text import slugify, validate_sku, validate_slug


def product(**overrides: object) -> Product:
    values: dict[str, object] = {
        "id": uuid4(),
        "name": "Tee",
        "slug": "tee",
        "sku": "TEE",
        "price": PricePair(Decimal("299.00"), Decimal("449.00")),
        "variants": [ProductVariant(id=uuid4(), sku="TEE-S", size="S")],
        **overrides,
    }
    return Product(**values)  # type: ignore[arg-type]


def test_valid_product_passes() -> None:
    product().validate()


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        (
            {
                "variants": [
                    ProductVariant(uuid4(), "A", size="S"),
                    ProductVariant(uuid4(), "A", size="M"),
                ]
            },
            "SKUs must be unique",
        ),
        (
            {
                "variants": [
                    ProductVariant(uuid4(), "A", size="S"),
                    ProductVariant(uuid4(), "B", size="s"),
                ]
            },
            "combination may appear only once",
        ),
        ({"category_ids": [uuid4()], "primary_category_id": uuid4()}, "primary category"),
        (
            {
                "status": ProductStatus.ACTIVE,
                "variants": [ProductVariant(uuid4(), "A", is_active=False)],
            },
            "active variant",
        ),
        ({"name": "  "}, "name is required"),
    ],
)
def test_product_invariants(overrides: dict[str, object], message: str) -> None:
    with pytest.raises(DomainValidationError, match=message):
        product(**overrides).validate()


def test_variant_stock_cannot_be_negative() -> None:
    with pytest.raises(DomainValidationError):
        ProductVariant(uuid4(), "A", stock_quantity=-1)


def test_ordering_rejects_duplicates_and_preserves_order() -> None:
    a, b, c = uuid4(), uuid4(), uuid4()
    assert validate_ordering([c, a, b]) == [c, a, b]
    with pytest.raises(DomainValidationError):
        validate_ordering([a, b, a])


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"section_type": HomepageSectionType.PRODUCT_GRID}, "selection mode"),
        ({"selection_mode": SelectionMode.MANUAL}, "cannot select products"),
        (
            {
                "section_type": HomepageSectionType.PRODUCT_GRID,
                "selection_mode": SelectionMode.CATEGORY,
            },
            "source category",
        ),
        ({"section_type": HomepageSectionType.HERO_BANNER}, "desktop image"),
    ],
)
def test_homepage_section_rules(overrides: dict[str, object], message: str) -> None:
    values: dict[str, object] = {
        "id": uuid4(),
        "section_type": HomepageSectionType.RICH_TEXT,
        **overrides,
    }
    with pytest.raises(DomainValidationError, match=message):
        HomepageSection(**values).validate()  # type: ignore[arg-type]


def test_section_settings_are_validated_per_type() -> None:
    clean = validate_section_settings(
        HomepageSectionType.HERO_BANNER, {"headline": " Little Smiles ", "cta_href": "/shop"}
    )
    assert clean["headline"] == "Little Smiles"
    with pytest.raises(DomainValidationError, match=r"(?i)extra inputs"):
        validate_section_settings(HomepageSectionType.RICH_TEXT, {"body": "x", "html": "<b>"})
    with pytest.raises(DomainValidationError, match="cta_href"):
        validate_section_settings(
            HomepageSectionType.PROMO_BANNER, {"cta_href": "javascript:alert(1)"}
        )
    with pytest.raises(DomainValidationError):
        validate_section_settings(HomepageSectionType.PRODUCT_GRID, {"columns_desktop": 9})


def test_slug_and_sku_rules() -> None:
    assert slugify("Blush Ruffle Party Dress!") == "blush-ruffle-party-dress"
    assert validate_slug("Twinkle-Tee") == "twinkle-tee"
    assert validate_sku(" tk-drs-01 ") == "TK-DRS-01"
    for bad in ("bad slug", "double--dash", "-edge"):
        with pytest.raises(DomainValidationError):
            validate_slug(bad)
    with pytest.raises(DomainValidationError):
        validate_sku("has space")


@pytest.mark.parametrize(
    ("password", "message"),
    [("short", "at least"), ("aaaaaaaaaaaa", "repetitive"), ("my-asha.rao-pass", "email")],
)
def test_password_policy(password: str, message: str) -> None:
    with pytest.raises(DomainValidationError, match=message):
        validate_password(password, email="asha.rao@twinklekids.in")


def test_permissions_require_an_active_user() -> None:
    perms = frozenset(p.value for p in ROLE_PERMISSIONS[Role.CATALOG_MANAGER])
    user = User(uuid4(), "a@b.in", "A", "hash", permissions=perms)
    assert user.is_staff and user.has_permission(Permission.CATALOG_MANAGE)
    assert not user.has_permission(Permission.ORDERS_MANAGE)
    user.is_active = False
    assert not user.is_staff
    assert ROLE_PERMISSIONS[Role.CUSTOMER] == frozenset()
