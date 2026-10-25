"""Shopping cart: quantities are stored, prices never are.

Every view re-resolves each line against the live catalogue (status, variant, stock and the
effective variant price), so the browser can never influence what anything costs. A price
snapshot is kept per line only to tell the shopper "this price has changed since you added it".
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.application.dto.catalog import ImageView, PriceView
from app.application.ports import CatalogQueries
from app.domain.entities.catalog import Product, ProductVariant
from app.domain.entities.commerce import (
    MAX_CART_LINE_QUANTITY,
    MAX_CART_LINES,
    Cart,
    validate_cart_quantity,
)
from app.domain.entities.site import ShippingRule
from app.domain.enums import ProductStatus
from app.domain.errors import DomainValidationError, NotFoundError, PricingError
from app.domain.repositories.catalog import ProductRepository
from app.domain.repositories.commerce import CartRepository
from app.domain.repositories.media import UnitOfWork
from app.domain.repositories.site import SettingsRepository, ShippingRuleRepository
from app.domain.value_objects.pricing import PricedLine, PricePair, calculate_totals


@dataclass(frozen=True, slots=True)
class CartOwner:
    """Who the cart belongs to: a signed-in customer, or a guest identified by a cookie."""

    user_id: UUID | None = None
    guest_token_hash: str | None = None


@dataclass(frozen=True, slots=True)
class CartLineView:
    item_id: UUID
    product_id: UUID
    variant_id: UUID
    product_name: str
    product_slug: str | None
    sku: str | None
    size: str | None
    colour: str | None
    image: ImageView | None
    price: PriceView | None  # current effective price; None when the item is unavailable
    quantity: int
    line_total: Decimal | None
    available: bool  # purchasable at this quantity right now
    max_quantity: int  # most that can be ordered (stock-limited when inventory is tracked)
    issue: str | None  # customer-facing explanation when something needs attention
    previous_price: Decimal | None  # selling price when added, if it has changed since


@dataclass(frozen=True, slots=True)
class CartView:
    id: UUID | None
    currency_code: str
    lines: list[CartLineView]
    item_count: int
    subtotal: Decimal
    savings: Decimal
    shipping_total: Decimal | None  # None: no shipping rule matches (confirmed later)
    grand_total: Decimal
    has_issues: bool
    has_price_changes: bool


def shipping_fee(rules: Sequence[ShippingRule], subtotal: Decimal) -> Decimal | None:
    """Flat fee from the first active rule (lowest priority) whose band contains the subtotal."""
    matching = [
        r
        for r in rules
        if r.is_active
        and r.min_order_amount <= subtotal
        and (r.max_order_amount is None or subtotal <= r.max_order_amount)
    ]
    if not matching:
        return None
    matching.sort(key=lambda r: (r.priority, -r.min_order_amount))
    return matching[0].fee


def _stock_limit(product: Product, variant: ProductVariant) -> int:
    if product.track_inventory and not product.allow_backorder:
        return min(variant.stock_quantity, MAX_CART_LINE_QUANTITY)
    return MAX_CART_LINE_QUANTITY


def _purchasable(product: Product | None, variant_id: UUID) -> tuple[Product, ProductVariant]:
    variant = (
        next((v for v in product.variants if v.id == variant_id), None) if product else None
    )
    if product is None or variant is None:
        raise NotFoundError("This option is no longer available.")
    if product.status is not ProductStatus.ACTIVE or not variant.is_active:
        raise DomainValidationError(f"{product.name} is no longer available.")
    return product, variant


class CartService:
    def __init__(
        self,
        *,
        carts: CartRepository,
        products: ProductRepository,
        queries: CatalogQueries,
        shipping: ShippingRuleRepository,
        settings: SettingsRepository,
        uow: UnitOfWork,
    ) -> None:
        self._carts = carts
        self._products = products
        self._queries = queries
        self._shipping = shipping
        self._settings = settings
        self._uow = uow

    # --- reads -----------------------------------------------------------------------------

    def _find(self, owner: CartOwner) -> Cart | None:
        if owner.user_id is not None:
            return self._carts.find_active(user_id=owner.user_id)
        if owner.guest_token_hash is not None:
            return self._carts.find_active(guest_token_hash=owner.guest_token_hash)
        return None

    def view(self, owner: CartOwner) -> CartView:
        return self._render(self._find(owner))

    def _render(self, cart: Cart | None) -> CartView:
        currency = self._settings.get().currency_code
        if cart is None or not cart.items:
            return CartView(
                id=cart.id if cart else None,
                currency_code=currency,
                lines=[],
                item_count=0,
                subtotal=Decimal("0.00"),
                savings=Decimal("0.00"),
                shipping_total=None,
                grand_total=Decimal("0.00"),
                has_issues=False,
                has_price_changes=False,
            )

        product_ids = list(dict.fromkeys(item.product_id for item in cart.items))
        products = {pid: self._products.get(pid) for pid in product_ids}
        summaries = {
            s.id: s for s in self._queries.ordered_products(product_ids, include_inactive=True)
        }

        lines: list[CartLineView] = []
        priced: list[PricedLine] = []
        for item in cart.items:
            product = products.get(item.product_id)
            variant = (
                next((v for v in product.variants if v.id == item.variant_id), None)
                if product
                else None
            )
            summary = summaries.get(item.product_id)
            price: PricePair | None = None
            issue: str | None = None
            max_quantity = 0
            if product is None or variant is None:
                issue = "This item is no longer available."
            elif product.status is not ProductStatus.ACTIVE or not variant.is_active:
                issue = "This item is no longer available."
            else:
                try:
                    price = variant.effective_price(product.price)
                except PricingError:
                    issue = "This item can't be ordered right now."
                max_quantity = _stock_limit(product, variant)
                if price is not None:
                    if max_quantity == 0:
                        issue = "Sold out."
                    elif item.quantity > max_quantity:
                        issue = f"Only {max_quantity} left — please reduce the quantity."

            available = price is not None and issue is None
            if available and price is not None:
                priced.append(PricedLine(price, item.quantity))
            previous = (
                item.unit_price_snapshot
                if price is not None
                and item.unit_price_snapshot is not None
                and item.unit_price_snapshot != price.selling
                else None
            )
            lines.append(
                CartLineView(
                    item_id=item.id,
                    product_id=item.product_id,
                    variant_id=item.variant_id,
                    product_name=product.name if product else "Unavailable item",
                    product_slug=(
                        product.slug if product and product.status is ProductStatus.ACTIVE else None
                    ),
                    sku=variant.sku if variant else None,
                    size=variant.size if variant else None,
                    colour=variant.colour if variant else None,
                    image=summary.primary_image if summary else None,
                    price=PriceView.of(price) if price is not None else None,
                    quantity=item.quantity,
                    line_total=(
                        PricedLine(price, item.quantity).total if available and price else None
                    ),
                    available=available,
                    max_quantity=max_quantity,
                    issue=issue,
                    previous_price=previous,
                )
            )

        totals = calculate_totals(priced)
        shipping = shipping_fee(self._shipping.list(), totals.subtotal) if priced else None
        grand = totals.subtotal + (shipping or Decimal("0.00"))
        return CartView(
            id=cart.id,
            currency_code=currency,
            lines=lines,
            item_count=sum(line.quantity for line in lines),
            subtotal=totals.subtotal,
            savings=totals.savings,
            shipping_total=shipping,
            grand_total=grand,
            has_issues=any(line.issue for line in lines),
            has_price_changes=any(line.previous_price is not None for line in lines),
        )

    # --- writes ----------------------------------------------------------------------------

    def add(self, owner: CartOwner, *, variant_id: UUID, quantity: int) -> CartView:
        validate_cart_quantity(quantity)
        product_id = self._carts.product_ids_for_variants([variant_id]).get(variant_id)
        product, variant = _purchasable(
            self._products.get(product_id) if product_id else None, variant_id
        )
        price = variant.effective_price(product.price)

        cart = self._find(owner) or self._carts.create(
            user_id=owner.user_id, guest_token_hash=owner.guest_token_hash
        )
        existing = cart.item_for_variant(variant_id)
        total = quantity + (existing.quantity if existing else 0)
        self._check_quantity(product, variant, total)
        if existing:
            self._carts.update_item(existing.id, quantity=total, unit_price_snapshot=price.selling)
        else:
            if len(cart.items) >= MAX_CART_LINES:
                raise DomainValidationError("Your bag is full. Remove an item to add another.")
            self._carts.add_item(
                cart.id, variant_id=variant_id, quantity=total, unit_price_snapshot=price.selling
            )
        self._uow.commit()
        return self._render(self._find(owner))

    def update(self, owner: CartOwner, item_id: UUID, *, quantity: int) -> CartView:
        validate_cart_quantity(quantity)
        cart = self._find(owner)
        item = cart.item(item_id) if cart else None
        if item is None:
            raise NotFoundError("That item is no longer in your bag.")
        product = self._products.get(item.product_id)
        variant = (
            next((v for v in product.variants if v.id == item.variant_id), None)
            if product
            else None
        )
        snapshot: Decimal | None = None
        if product is not None and variant is not None:
            # Reducing is always allowed (it resolves stock issues); increasing is checked.
            if quantity > item.quantity:
                _purchasable(product, item.variant_id)
                self._check_quantity(product, variant, quantity)
            try:
                snapshot = variant.effective_price(product.price).selling
            except PricingError:
                snapshot = None
        self._carts.update_item(item_id, quantity=quantity, unit_price_snapshot=snapshot)
        self._uow.commit()
        return self._render(self._find(owner))

    def remove(self, owner: CartOwner, item_id: UUID) -> CartView:
        cart = self._find(owner)
        if cart is not None and cart.item(item_id) is not None:
            self._carts.remove_item(item_id)
            self._uow.commit()
        return self._render(self._find(owner))

    def acknowledge_prices(self, owner: CartOwner) -> CartView:
        """The shopper has seen the new prices: stop flagging them."""
        view = self._render(self._find(owner))
        changed = {
            line.item_id: line.price.selling_price
            for line in view.lines
            if line.previous_price is not None and line.price is not None
        }
        if changed:
            self._carts.set_snapshots(changed)
            self._uow.commit()
            return self._render(self._find(owner))
        return view

    def merge_guest_cart(self, *, user_id: UUID, guest_token_hash: str) -> None:
        """After sign-in: move the guest bag into the customer's bag (quantities combine)."""
        guest = self._carts.find_active(guest_token_hash=guest_token_hash)
        if guest is None:
            return
        mine = self._carts.find_active(user_id=user_id)
        if mine is None:
            self._carts.assign_to_user(guest.id, user_id)
        else:
            for item in guest.items:
                existing = mine.item_for_variant(item.variant_id)
                if existing:
                    combined = min(existing.quantity + item.quantity, MAX_CART_LINE_QUANTITY)
                    self._carts.update_item(existing.id, quantity=combined)
                elif len(mine.items) < MAX_CART_LINES:
                    self._carts.add_item(
                        mine.id,
                        variant_id=item.variant_id,
                        quantity=item.quantity,
                        unit_price_snapshot=item.unit_price_snapshot,
                    )
            self._carts.delete(guest.id)
        self._uow.commit()

    @staticmethod
    def _check_quantity(product: Product, variant: ProductVariant, quantity: int) -> None:
        if quantity > MAX_CART_LINE_QUANTITY:
            raise DomainValidationError(
                f"You can add up to {MAX_CART_LINE_QUANTITY} of one item to your bag."
            )
        limit = _stock_limit(product, variant)
        if limit == 0:
            raise DomainValidationError(f"{product.name} is sold out in this option.")
        if quantity > limit:
            raise DomainValidationError(f"Only {limit} of {product.name} left in this option.")
