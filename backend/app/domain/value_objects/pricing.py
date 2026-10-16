"""Pricing rules — the single source of truth for selling price, original price (MRP),
discounts, variant price inheritance and line/order totals.

All amounts are ``Decimal`` with two decimal places (rupees and paise). Floats are rejected.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal, InvalidOperation

from app.domain.errors import PricingError

CENT = Decimal("0.01")
MAX_PRICE = Decimal("9999999999.99")  # fits NUMERIC(12, 2)
_HUNDRED = Decimal(100)


def to_money(value: Decimal | int | str, *, field: str = "amount") -> Decimal:
    """Parse an exact monetary amount. Accepts Decimal/int/str, never float."""
    if isinstance(value, (float, bool)):
        raise PricingError(f"{field} must be an exact decimal, not {type(value).__name__}.")
    try:
        amount = Decimal(value)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise PricingError(f"{field} is not a valid amount.") from exc
    if not amount.is_finite():
        raise PricingError(f"{field} is not a valid amount.")
    if amount != amount.quantize(CENT):
        raise PricingError(f"{field} cannot have more than two decimal places.")
    if amount < 0:
        raise PricingError(f"{field} cannot be negative.")
    if amount > MAX_PRICE:
        raise PricingError(f"{field} is too large.")
    return amount.quantize(CENT)


@dataclass(frozen=True, slots=True)
class PricePair:
    """A selling price and an optional original price / MRP.

    Invariant: when an original price is present it must be >= the selling price.
    A discount exists only when the original price is strictly greater.
    """

    selling: Decimal
    original: Decimal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "selling", to_money(self.selling, field="Selling price"))
        if self.original is not None:
            original = to_money(self.original, field="Original price")
            object.__setattr__(self, "original", original)
            if original < self.selling:
                raise PricingError(
                    "Original price (MRP) must be greater than or equal to the selling price."
                )

    @classmethod
    def of(
        cls, selling: Decimal | int | str, original: Decimal | int | str | None = None
    ) -> "PricePair":
        return cls(
            to_money(selling, field="Selling price"),
            None if original is None else to_money(original, field="Original price"),
        )

    @property
    def has_discount(self) -> bool:
        return self.original is not None and self.original > self.selling

    @property
    def discount_amount(self) -> Decimal | None:
        original = self.original
        if original is None or original <= self.selling:
            return None
        return (original - self.selling).quantize(CENT)

    @property
    def discount_percent(self) -> int | None:
        """Whole-number percentage, rounded down so a discount is never overstated."""
        original = self.original
        if original is None or original <= self.selling:  # also rules out original == 0
            return None
        percent = (original - self.selling) / original * _HUNDRED
        return int(percent.to_integral_value(rounding=ROUND_FLOOR))


def resolve_variant_price(
    product: PricePair,
    *,
    selling_override: Decimal | None = None,
    original_override: Decimal | None = None,
) -> PricePair:
    """Effective variant price: each field falls back to the parent product independently.

    Raises PricingError when the resulting combination is invalid (e.g. a variant selling
    override above the inherited MRP).
    """
    selling = product.selling if selling_override is None else selling_override
    original = product.original if original_override is None else original_override
    return PricePair(selling, original)


@dataclass(frozen=True, slots=True)
class PricedLine:
    unit: PricePair
    quantity: int

    def __post_init__(self) -> None:
        if isinstance(self.quantity, bool) or not isinstance(self.quantity, int):
            raise PricingError("Quantity must be a whole number.")
        if self.quantity < 1:
            raise PricingError("Quantity must be at least 1.")

    @property
    def total(self) -> Decimal:
        return (self.unit.selling * self.quantity).quantize(CENT)

    @property
    def original_total(self) -> Decimal:
        base = self.unit.original if self.unit.original is not None else self.unit.selling
        return (base * self.quantity).quantize(CENT)


@dataclass(frozen=True, slots=True)
class OrderTotals:
    subtotal: Decimal
    savings: Decimal  # MRP savings, informational
    discount_total: Decimal  # coupon discount
    shipping_total: Decimal
    grand_total: Decimal


def calculate_totals(
    lines: Iterable[PricedLine],
    *,
    discount: Decimal = Decimal("0.00"),
    shipping: Decimal = Decimal("0.00"),
) -> OrderTotals:
    """Server-side totals. Never trust browser-supplied prices or totals."""
    materialised = list(lines)
    subtotal = sum((line.total for line in materialised), Decimal("0.00")).quantize(CENT)
    original = sum((line.original_total for line in materialised), Decimal("0.00"))
    discount = to_money(discount, field="Discount")
    shipping = to_money(shipping, field="Shipping")
    discount = min(discount, subtotal)  # a discount can never make the total negative
    grand = (subtotal - discount + shipping).quantize(CENT, rounding=ROUND_HALF_UP)
    return OrderTotals(
        subtotal=subtotal,
        savings=(original - subtotal).quantize(CENT),
        discount_total=discount,
        shipping_total=shipping,
        grand_total=grand,
    )
