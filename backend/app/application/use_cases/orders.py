"""Website checkout, customer order history, admin order handling and WhatsApp conversion.

Rules enforced here for every order, whichever way it is created:

* Prices, discounts, delivery and totals are recalculated from the database. Nothing the
  browser sends about money is trusted; an optional `expected_grand_total` is only used to stop
  and ask the shopper to review when prices changed under them.
* Stock is checked and deducted inside the same transaction with an atomic conditional update,
  so it can never go negative or be deducted twice. Submissions are idempotent per shopper.
* Orders start as `pending_confirmation` and `unpaid`. There is no payment gateway; staff record
  payments manually. Customers never see an order-tracking timeline.
"""

import hashlib
import logging
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.application.content_settings import pin_serviceable, shipping_settings
from app.application.dto.catalog import Page, PriceView
from app.application.dto.orders import (
    OrderFilters,
    OrderSummary,
    OrderView,
    WhatsAppRequestSummary,
    WhatsAppRequestView,
)
from app.application.ports import CatalogQueries, OrderQueries, RateLimiter
from app.application.use_cases.cart import CartOwner, CartService, CartView, shipping_fee
from app.application.use_cases.notifications import Notifier
from app.domain.entities.address import MAX_ADDRESSES, PostalAddress, SavedAddress, validate_phone
from app.domain.entities.commerce import (
    MAX_CART_LINES,
    OrderLineSnapshot,
    validate_cart_quantity,
)
from app.domain.entities.identity import User
from app.domain.entities.order import (
    RESTOCKING_STATUSES,
    Coupon,
    NewOrder,
    ensure_order_transition,
    ensure_whatsapp_transition,
    new_order_number,
)
from app.domain.enums import (
    InventoryReason,
    OrderSource,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    WhatsAppRequestStatus,
)
from app.domain.errors import (
    AuthenticationError,
    ConflictError,
    DomainValidationError,
    NotFoundError,
    RateLimitedError,
)
from app.domain.repositories.catalog import InventoryLedger, ProductRepository
from app.domain.repositories.commerce import (
    CartRepository,
    CouponRepository,
    OrderRepository,
    WhatsAppRequestRepository,
)
from app.domain.repositories.identity import AddressRepository, AuditLogRepository
from app.domain.repositories.media import UnitOfWork
from app.domain.repositories.site import (
    CollectionAdminRepository,
    SettingsRepository,
    ShippingRuleRepository,
)
from app.domain.value_objects.pricing import OrderTotals, PricePair, calculate_totals
from app.domain.value_objects.text import clean_optional, normalise_email

logger = logging.getLogger(__name__)

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ORDERS_PER_IP = 10
ORDER_WINDOW_SECONDS = 10 * 60
MAX_NOTE_LENGTH = 500
CURRENCY_SYMBOLS = {"INR": "₹"}


def _money(amount: Decimal, currency: str = "INR") -> str:
    symbol = CURRENCY_SYMBOLS.get(currency)
    return f"{symbol}{amount:,.2f}" if symbol else f"{currency} {amount:,.2f}"


def _note(value: str | None) -> str | None:
    note = clean_optional(value)
    if note is not None and len(note) > MAX_NOTE_LENGTH:
        raise DomainValidationError(f"Notes can be up to {MAX_NOTE_LENGTH} characters.")
    return note


# --- shared order writer ---------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PaymentOptionView:
    method: PaymentMethod
    label: str
    instructions: str


@dataclass(frozen=True, slots=True)
class CustomerDetails:
    name: str
    phone: str
    email: str


class OrderWriter:
    """Builds, prices and persists one order transactionally (no commit)."""

    def __init__(
        self,
        *,
        orders: OrderRepository,
        products: ProductRepository,
        carts: CartRepository,
        coupons: CouponRepository,
        shipping: ShippingRuleRepository,
        ledger: InventoryLedger,
        queries: CatalogQueries,
        clock: Callable[[], datetime],
        collections: CollectionAdminRepository | None = None,
        settings: SettingsRepository | None = None,
    ) -> None:
        self._collections = collections
        self._settings = settings
        self.orders = orders
        self._products = products
        self._carts = carts
        self.coupons = coupons
        self._shipping = shipping
        self._ledger = ledger
        self._queries = queries
        self._clock = clock

    def lines(self, items: Sequence[tuple[UUID, int]]) -> list[OrderLineSnapshot]:
        merged: dict[UUID, int] = {}
        for variant_id, quantity in items:
            merged[variant_id] = merged.get(variant_id, 0) + validate_cart_quantity(quantity)
        if not merged:
            raise DomainValidationError("There's nothing to order yet.")
        if len(merged) > MAX_CART_LINES:
            raise DomainValidationError(f"Orders can contain up to {MAX_CART_LINES} items.")
        product_ids = self._carts.product_ids_for_variants(list(merged))
        images = {
            s.id: s.primary_image.url if s.primary_image else None
            for s in self._queries.ordered_products(
                list(set(product_ids.values())), include_inactive=True
            )
        }
        lines: list[OrderLineSnapshot] = []
        for variant_id, quantity in merged.items():
            validate_cart_quantity(quantity)
            product_id = product_ids.get(variant_id)
            product = self._products.get(product_id) if product_id else None
            if product is None:
                raise DomainValidationError("One of the items is no longer available.")
            # Status, variant ownership, stock and the effective price — same rules as the bag.
            lines.append(
                OrderLineSnapshot.capture(
                    product, variant_id, quantity, image_url=images.get(product.id)
                )
            )
        return lines

    def totals(
        self,
        lines: Sequence[OrderLineSnapshot],
        *,
        coupon_code: str | None,
        user_id: UUID | None,
        apply_shipping: bool = True,
    ) -> tuple[OrderTotals, UUID | None, str | None, bool]:
        """(totals, coupon id, normalised coupon code, shipping rule matched)."""
        subtotal = calculate_totals(line.priced for line in lines).subtotal
        discount = Decimal("0.00")
        coupon_id: UUID | None = None
        code: str | None = None
        if coupon_code and coupon_code.strip():
            coupon = self.coupons.get_by_code(coupon_code)
            if coupon is None:
                raise DomainValidationError(f"The code {coupon_code.strip().upper()} isn't valid.")
            eligible = subtotal
            if not coupon.scope.whole_order:
                eligible = sum(
                    (line.priced.total for line in lines if self._covered(coupon, line.product_id)),
                    Decimal("0.00"),
                )
            discount = coupon.discount_for(
                subtotal,
                eligible_subtotal=eligible,
                now=self._clock(),
                times_used=self.coupons.times_used(coupon.id),
                times_used_by_customer=(
                    self.coupons.times_used_by(coupon.id, user_id) if user_id else None
                ),
            )
            coupon_id, code = coupon.id, coupon.code
        threshold = (
            shipping_settings(self._settings.get().shipping_settings).free_shipping_threshold
            if self._settings
            else None
        )
        fee = (
            shipping_fee(self._shipping.list(), subtotal - discount, free_threshold=threshold)
            if apply_shipping
            else None
        )
        totals = calculate_totals(
            (line.priced for line in lines), discount=discount, shipping=fee or Decimal("0.00")
        )
        return totals, coupon_id, code, fee is not None

    def _covered(self, coupon: Coupon, product_id: UUID) -> bool:
        product = self._products.get(product_id)
        categories = set(product.category_ids) if product else set()
        collections: set[UUID] = (
            set(self._collections.collections_for_product(product_id))
            if self._collections
            else set()
        )
        return coupon.scope.covers(product_id, categories, collections)

    def persist(
        self,
        order: NewOrder,
        *,
        coupon_id: UUID | None,
        actor_user_id: UUID | None,
    ) -> None:
        self.orders.add(order)
        for line in order.lines:
            product = self._products.get(line.product_id)
            variant = (
                next((v for v in product.variants if v.id == line.variant_id), None)
                if product
                else None
            )
            if product is None or variant is None or not product.track_inventory:
                continue
            quantity = line.quantity
            if product.allow_backorder:
                quantity = min(quantity, variant.stock_quantity)  # never below zero
                if quantity <= 0:
                    continue
            balance = self.orders.deduct_stock(line.variant_id, quantity)
            if balance is None:
                raise ConflictError(
                    f"{line.product_name} just sold out in this option. Please review your bag."
                )
            self._ledger.record(
                variant_id=line.variant_id,
                delta=-quantity,
                stock_after=balance,
                reason=InventoryReason.ORDER_PLACED,
                actor_user_id=actor_user_id,
                order_id=order.id,
            )
        if coupon_id is not None:
            self.coupons.record_redemption(
                coupon_id=coupon_id,
                order_id=order.id,
                user_id=order.user_id,
                amount=order.totals.discount_total,
            )

    def order_number(self) -> str:
        for _ in range(10):
            number = new_order_number(self._clock())
            if not self.orders.number_taken(number):
                return number
        raise ConflictError("Please try again.")  # pragma: no cover - astronomically rare

    def restock(
        self, order_id: UUID, *, reason: InventoryReason, actor_user_id: UUID | None
    ) -> None:
        for variant_id, quantity in self.orders.lines_for_restock(order_id):
            product_ids = self._carts.product_ids_for_variants([variant_id])
            product = (
                self._products.get(product_ids[variant_id]) if variant_id in product_ids else None
            )
            if product is None or not product.track_inventory:
                continue
            balance = self.orders.restock(variant_id, quantity)
            self._ledger.record(
                variant_id=variant_id,
                delta=quantity,
                stock_after=balance,
                reason=reason,
                actor_user_id=actor_user_id,
                order_id=order_id,
            )


def enabled_payment_options(raw: Sequence[dict[str, object]]) -> list[PaymentOptionView]:
    options: list[PaymentOptionView] = []
    for option in raw:
        if not option.get("enabled"):
            continue
        try:
            method = PaymentMethod(str(option.get("method")))
        except ValueError:
            continue
        options.append(
            PaymentOptionView(
                method=method,
                label=str(option.get("label") or method.value.replace("_", " ").title()),
                instructions=str(option.get("instructions") or ""),
            )
        )
    return options


# --- website checkout ------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CheckoutQuote:
    bag: CartView
    currency_code: str
    subtotal: Decimal
    discount_total: Decimal
    shipping_total: Decimal
    shipping_configured: bool
    grand_total: Decimal
    coupon_code: str | None
    coupon_error: str | None
    payment_methods: list[PaymentOptionView]
    guest_checkout_enabled: bool
    signed_in: bool
    can_place_order: bool
    blocking_reason: str | None


@dataclass(slots=True)
class CheckoutInput:
    idempotency_key: str
    customer_name: str
    customer_phone: str
    payment_method: PaymentMethod
    address: PostalAddress | None = None
    saved_address_id: UUID | None = None
    customer_email: str | None = None
    customer_note: str | None = None
    coupon_code: str | None = None
    save_address: bool = False
    expected_grand_total: Decimal | None = None


class CheckoutService:
    def __init__(
        self,
        *,
        writer: OrderWriter,
        cart: CartService,
        carts: CartRepository,
        addresses: AddressRepository,
        settings: SettingsRepository,
        order_queries: OrderQueries,
        audit: AuditLogRepository,
        uow: UnitOfWork,
        rate_limiter: RateLimiter,
        notifier: Notifier,
        storefront_url: str,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._writer = writer
        self._cart = cart
        self._carts = carts
        self._addresses = addresses
        self._settings = settings
        self._order_queries = order_queries
        self._audit = audit
        self._uow = uow
        self._limiter = rate_limiter
        self._notifier = notifier
        self._storefront_url = storefront_url
        self._clock = clock

    def quote(
        self, owner: CartOwner, user: User | None, *, coupon_code: str | None
    ) -> CheckoutQuote:
        settings = self._settings.get()
        bag = self._cart.view(owner)
        methods = enabled_payment_options(settings.payment_options)
        available = [line for line in bag.lines if line.available]

        discount = Decimal("0.00")
        coupon_error: str | None = None
        code: str | None = None
        shipping = Decimal("0.00")
        configured = False
        if available:
            lines = [
                OrderLineSnapshot(
                    product_id=line.product_id,
                    variant_id=line.variant_id,
                    product_name=line.product_name,
                    product_slug=line.product_slug or "",
                    sku=line.sku or "",
                    size=line.size,
                    colour=line.colour,
                    unit_price=_pair(line.price),
                    quantity=line.quantity,
                )
                for line in available
                if line.price is not None
            ]
            try:
                totals, _id, code, configured = self._writer.totals(
                    lines, coupon_code=coupon_code, user_id=user.id if user else None
                )
            except DomainValidationError as exc:
                coupon_error = str(exc)
                totals, _id, code, configured = self._writer.totals(
                    lines, coupon_code=None, user_id=user.id if user else None
                )
            discount, shipping = totals.discount_total, totals.shipping_total
        subtotal = bag.subtotal
        grand = subtotal - discount + shipping

        reason: str | None = None
        if not bag.lines:
            reason = "Your bag is empty."
        elif bag.has_issues:
            reason = "Some items in your bag need attention before you can check out."
        elif not methods:
            reason = (
                "Online orders can't be placed right now because no payment method is "
                "available. Please contact us or order on WhatsApp."
            )
        elif user is None and not settings.guest_checkout_enabled:
            reason = "Please sign in or create an account to place your order."
        return CheckoutQuote(
            bag=bag,
            currency_code=settings.currency_code,
            subtotal=subtotal,
            discount_total=discount,
            shipping_total=shipping,
            shipping_configured=configured,
            grand_total=grand,
            coupon_code=code,
            coupon_error=coupon_error,
            payment_methods=methods,
            guest_checkout_enabled=settings.guest_checkout_enabled,
            signed_in=user is not None,
            can_place_order=reason is None,
            blocking_reason=reason,
        )

    def place_order(
        self,
        owner: CartOwner,
        user: User | None,
        data: CheckoutInput,
        *,
        ip: str | None,
    ) -> tuple[OrderView, bool]:
        """Returns (order, created). A repeated submission returns the original order."""
        key = self._idempotency_key(owner, user, data.idempotency_key)
        existing = self._writer.orders.id_for_idempotency_key(key)
        if existing is not None:
            return self._view(existing), False

        retry_after = self._limiter.hit(
            f"checkout:{ip or 'unknown'}", limit=ORDERS_PER_IP, window_seconds=ORDER_WINDOW_SECONDS
        )
        if retry_after is not None:
            raise RateLimitedError(
                "Too many orders in a short time. Please try again later.", retry_after
            )

        settings = self._settings.get()
        if user is None and not settings.guest_checkout_enabled:
            raise AuthenticationError("Please sign in or create an account to place your order.")
        methods = {o.method: o for o in enabled_payment_options(settings.payment_options)}
        if not methods:
            raise DomainValidationError(
                "Online orders can't be placed right now because no payment method is available."
            )
        if data.payment_method not in methods:
            raise DomainValidationError("Please choose one of the available payment methods.")

        customer = self._customer(user, data)
        address = self._address(user, data)
        delivery = shipping_settings(settings.shipping_settings)
        if not pin_serviceable(delivery, address.postal_code):
            raise DomainValidationError(
                delivery.unserviceable_message
                or f"Sorry, we don't deliver to PIN code {address.postal_code} yet."
            )

        cart = (
            self._carts.find_active(user_id=owner.user_id)
            if owner.user_id
            else self._carts.find_active(guest_token_hash=owner.guest_token_hash)
            if owner.guest_token_hash
            else None
        )
        if cart is None or not cart.items:
            raise DomainValidationError("Your bag is empty.")

        lines = self._writer.lines([(item.variant_id, item.quantity) for item in cart.items])
        totals, coupon_id, code, _configured = self._writer.totals(
            lines, coupon_code=data.coupon_code, user_id=user.id if user else None
        )
        if (
            data.expected_grand_total is not None
            and data.expected_grand_total != totals.grand_total
        ):
            raise ConflictError(
                f"Your order total is now {_money(totals.grand_total, settings.currency_code)}. "
                "Please review your order before placing it."
            )

        order = NewOrder(
            id=uuid4(),
            order_number=self._writer.order_number(),
            user_id=user.id if user else None,
            source=OrderSource.WEBSITE,
            customer_name=customer.name,
            customer_email=customer.email,
            customer_phone=customer.phone,
            shipping_address=address.snapshot(),
            lines=tuple(lines),
            totals=totals,
            payment_method=data.payment_method,
            placed_at=self._clock(),
            coupon_code=code,
            customer_note=_note(data.customer_note),
            idempotency_key=key,
        )
        try:
            self._writer.persist(
                order, coupon_id=coupon_id, actor_user_id=user.id if user else None
            )
            self._carts.mark_converted(cart.id)
            if user is not None and data.save_address and data.saved_address_id is None:
                self._remember_address(user.id, address)
            self._audit.record(
                actor_user_id=user.id if user else None,
                action="order.placed",
                entity_type="order",
                entity_id=str(order.id),
                changes={
                    "order_number": order.order_number,
                    "grand_total": str(totals.grand_total),
                },
                ip=ip,
            )
            self._uow.commit()
        except ConflictError:
            self._uow.rollback()
            # A concurrent duplicate submission won the race: hand back that order instead.
            raced = self._writer.orders.id_for_idempotency_key(key)
            if raced is not None:
                return self._view(raced), False
            raise
        except Exception:
            self._uow.rollback()
            raise

        view = self._view(order.id)
        self._send_confirmation(view, settings.store_name)
        return view, True

    def check_pin(self, postal_code: str) -> tuple[bool, str | None]:
        """Whether the shop delivers to a PIN code (shop-configured rules only)."""
        delivery = shipping_settings(self._settings.get().shipping_settings)
        if pin_serviceable(delivery, postal_code):
            return True, delivery.delivery_estimate or None
        return False, (
            delivery.unserviceable_message
            or f"Sorry, we don't deliver to PIN code {postal_code} yet."
        )

    def payment_instructions(self, method: PaymentMethod | None) -> str | None:
        """The shop's instructions for the chosen offline payment method, if any."""
        for option in enabled_payment_options(self._settings.get().payment_options):
            if option.method == method:
                return option.instructions or None
        return None

    # --- helpers ---------------------------------------------------------------------------

    def _view(self, order_id: UUID) -> OrderView:
        view = self._order_queries.order(order_id=order_id)
        if view is None:  # pragma: no cover - just written
            raise NotFoundError("Order not found.")
        return view

    @staticmethod
    def _idempotency_key(owner: CartOwner, user: User | None, client_key: str) -> str:
        key = (client_key or "").strip()
        if not 8 <= len(key) <= 100:
            raise DomainValidationError(
                "Missing checkout submission key. Please refresh and try again."
            )
        scope = str(user.id) if user else (owner.guest_token_hash or "anonymous")
        return hashlib.sha256(f"{scope}:{key}".encode()).hexdigest()

    @staticmethod
    def _customer(user: User | None, data: CheckoutInput) -> CustomerDetails:
        name = " ".join((data.customer_name or "").split())
        if not name:
            raise DomainValidationError("Please enter your name.")
        if len(name) > 120:
            raise DomainValidationError("Name is too long.")
        phone = validate_phone(data.customer_phone)
        email = normalise_email(data.customer_email or "") or (user.email if user else "")
        if not email:
            raise DomainValidationError(
                "Please enter your email so we can send your order details."
            )
        if len(email) > 254 or not EMAIL_PATTERN.fullmatch(email):
            raise DomainValidationError("Please enter a valid email address.")
        return CustomerDetails(name=name, phone=phone, email=email)

    def _address(self, user: User | None, data: CheckoutInput) -> PostalAddress:
        if data.saved_address_id is not None:
            if user is None:
                raise DomainValidationError("Please enter your delivery address.")
            saved = self._addresses.get(data.saved_address_id)
            if saved is None or saved.user_id != user.id:
                raise NotFoundError("Address not found.")
            return saved.address.validate()
        if data.address is None:
            raise DomainValidationError("Please enter your delivery address.")
        return data.address.validate()

    def _remember_address(self, user_id: UUID, address: PostalAddress) -> None:
        existing = self._addresses.list(user_id)
        if len(existing) >= MAX_ADDRESSES:
            return
        same = any(a.address.snapshot() == address.snapshot() for a in existing)
        if same:
            return
        self._addresses.add(
            SavedAddress(
                id=uuid4(),
                user_id=user_id,
                address=PostalAddress(**address.snapshot()),
                is_default=not existing,
            )
        )

    def _send_confirmation(self, order: OrderView, store_name: str) -> None:
        lines = "\n".join(
            f"- {line.product_name}"
            + (
                f" ({' / '.join(v for v in (line.size, line.colour) if v)})"
                if line.size or line.colour
                else ""
            )
            + f" × {line.quantity}: {_money(line.line_total, order.currency_code)}"  # noqa: RUF001 - intended typography
            for line in order.lines
        )
        try:
            self._notifier.email(
                template="order_received",
                entity_type="order",
                entity_id=str(order.id),
                to=order.customer_email,
                subject=f"{store_name}: we've received order {order.order_number}",
                text=(
                    f"Hello {order.customer_name.split(' ')[0]},\n\n"
                    f"Thank you for your order {order.order_number}. We'll confirm availability "
                    "and delivery with you shortly. Payment is not taken online — we'll share "
                    "the next steps for your chosen payment method.\n\n"
                    f"{lines}\n\nTotal: {_money(order.grand_total, order.currency_code)}\n\n"
                    "Questions? Reply to this email or visit "
                    f"{self._storefront_url.rstrip('/')}/contact"
                ),
            )
            self._uow.commit()  # persist the delivery record
        except Exception as exc:  # an email problem must never undo a placed order
            self._uow.rollback()
            logger.warning("Order confirmation email failed: %s", exc.__class__.__name__)


def _pair(price: PriceView) -> PricePair:
    return PricePair(price.selling_price, price.original_price)


# --- customer order history (no tracking) -----------------------------------------------------


class CustomerOrders:
    def __init__(self, queries: OrderQueries) -> None:
        self._queries = queries

    def list(self, user: User, *, page: int = 1, page_size: int = 10) -> Page[OrderSummary]:
        return self._queries.orders_for_user(
            user.id, page=max(1, page), page_size=min(page_size, 50)
        )

    def get(self, user: User, order_number: str) -> OrderView:
        order = self._queries.order(number=order_number)
        if order is None or order.user_id != user.id:  # never reveal other customers' orders
            raise NotFoundError("Order not found.")
        return order


# --- admin: orders ----------------------------------------------------------------------------


class OrderAdmin:
    def __init__(
        self,
        *,
        writer: OrderWriter,
        queries: OrderQueries,
        audit: AuditLogRepository,
        uow: UnitOfWork,
    ) -> None:
        self._writer = writer
        self._queries = queries
        self._audit = audit
        self._uow = uow

    def list(self, filters: OrderFilters) -> Page[OrderSummary]:
        return self._queries.orders(filters)

    def get(self, order_id: UUID) -> OrderView:
        order = self._queries.order(order_id=order_id)
        if order is None:
            raise NotFoundError("Order not found.")
        return order

    def set_status(self, order_id: UUID, target: OrderStatus, *, actor: User) -> OrderView:
        current = self._writer.orders.status(order_id)
        if current is None:
            raise NotFoundError("Order not found.")
        ensure_order_transition(current, target)
        self._writer.orders.set_status(order_id, target)
        if target in RESTOCKING_STATUSES:
            reason = (
                InventoryReason.ORDER_CANCELLED
                if target is OrderStatus.CANCELLED
                else InventoryReason.RETURN
            )
            self._writer.restock(order_id, reason=reason, actor_user_id=actor.id)
        self._audit.record(
            actor_user_id=actor.id,
            action="order.status_changed",
            entity_type="order",
            entity_id=str(order_id),
            changes={"from": current.value, "to": target.value},
        )
        self._uow.commit()
        return self.get(order_id)

    def record_payment(
        self,
        order_id: UUID,
        status: PaymentStatus,
        *,
        method: PaymentMethod | None,
        actor: User,
    ) -> OrderView:
        order = self.get(order_id)
        self._writer.orders.set_payment(order_id, status, method)
        self._audit.record(
            actor_user_id=actor.id,
            action="order.payment_recorded",
            entity_type="order",
            entity_id=str(order_id),
            changes={
                "from": order.payment_status.value,
                "to": status.value,
                "method": method.value if method else None,
            },
        )
        self._uow.commit()
        return self.get(order_id)

    def set_note(self, order_id: UUID, note: str | None, *, actor: User) -> OrderView:
        self.get(order_id)
        self._writer.orders.set_internal_note(order_id, _note(note))
        self._audit.record(
            actor_user_id=actor.id,
            action="order.note_updated",
            entity_type="order",
            entity_id=str(order_id),
        )
        self._uow.commit()
        return self.get(order_id)


# --- admin: WhatsApp requests -----------------------------------------------------------------


@dataclass(slots=True)
class ConvertInput:
    customer_name: str
    customer_phone: str
    address: PostalAddress
    payment_method: PaymentMethod
    customer_email: str | None = None
    items: list[tuple[UUID, int]] | None = None  # staff-adjusted quantities; default: as requested
    internal_note: str | None = None
    apply_shipping: bool = True


class WhatsAppAdmin:
    def __init__(
        self,
        *,
        writer: OrderWriter,
        requests: WhatsAppRequestRepository,
        queries: OrderQueries,
        audit: AuditLogRepository,
        uow: UnitOfWork,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._writer = writer
        self._requests = requests
        self._queries = queries
        self._audit = audit
        self._uow = uow
        self._clock = clock

    def list(
        self, *, status: WhatsAppRequestStatus | None, search: str | None, page: int, page_size: int
    ) -> Page[WhatsAppRequestSummary]:
        return self._queries.whatsapp_requests(
            status=status, search=search, page=page, page_size=page_size
        )

    def get(self, request_id: UUID) -> WhatsAppRequestView:
        found = self._queries.whatsapp_request(request_id)
        if found is None:
            raise NotFoundError("WhatsApp request not found.")
        return found

    def set_status(
        self,
        request_id: UUID,
        target: WhatsAppRequestStatus,
        *,
        staff_note: str | None,
        actor: User,
    ) -> WhatsAppRequestView:
        current = self._requests.status(request_id)
        if current is None:
            raise NotFoundError("WhatsApp request not found.")
        if target is WhatsAppRequestStatus.CONVERTED:
            raise DomainValidationError("Use “Convert to order” to turn a request into an order.")
        ensure_whatsapp_transition(current, target)
        self._requests.set_status(
            request_id,
            target,
            staff_note=_note(staff_note),
            contacted_at=self._clock() if target is WhatsAppRequestStatus.CONTACTED else None,
        )
        self._audit.record(
            actor_user_id=actor.id,
            action="whatsapp_request.status_changed",
            entity_type="whatsapp_request",
            entity_id=str(request_id),
            changes={"from": current.value, "to": target.value},
        )
        self._uow.commit()
        return self.get(request_id)

    def convert(self, request_id: UUID, data: ConvertInput, *, actor: User) -> OrderView:
        """Staff confirmed availability and price with the customer: create a real order."""
        request = self.get(request_id)
        if request.status not in (WhatsAppRequestStatus.INITIATED, WhatsAppRequestStatus.CONTACTED):
            raise ConflictError(f"This request is already {request.status.value}.")

        items = data.items
        if items is None:
            items = [(vid, qty) for vid, qty in self._requests.items(request_id) if vid is not None]
        if not items:
            raise DomainValidationError("This request has no items that can still be ordered.")
        name = " ".join((data.customer_name or "").split())
        if not name:
            raise DomainValidationError("Please enter the customer's name.")
        phone = validate_phone(data.customer_phone)
        email = normalise_email(data.customer_email or "")
        if email and not EMAIL_PATTERN.fullmatch(email):
            raise DomainValidationError("Please enter a valid email address.")
        address = data.address.validate()

        # Re-priced at today's catalogue prices: the confirmed price is what staff agreed.
        lines = self._writer.lines(items)
        totals, _coupon, _code, _ = self._writer.totals(
            lines, coupon_code=None, user_id=request.user_id, apply_shipping=data.apply_shipping
        )
        order = NewOrder(
            id=uuid4(),
            order_number=self._writer.order_number(),
            user_id=request.user_id,
            source=OrderSource.WHATSAPP,
            customer_name=name,
            customer_email=email,
            customer_phone=phone,
            shipping_address=address.snapshot(),
            lines=tuple(lines),
            totals=totals,
            payment_method=data.payment_method,
            placed_at=self._clock(),
            customer_note=f"From WhatsApp request {request.reference}",
        )
        try:
            self._writer.persist(order, coupon_id=None, actor_user_id=actor.id)
            if data.internal_note:
                self._writer.orders.set_internal_note(order.id, _note(data.internal_note))
            if not self._requests.mark_converted(request_id, order.id):
                raise ConflictError("This request was handled by someone else just now.")
            self._audit.record(
                actor_user_id=actor.id,
                action="whatsapp_request.converted",
                entity_type="whatsapp_request",
                entity_id=str(request_id),
                changes={"order_number": order.order_number},
            )
            self._uow.commit()
        except Exception:
            self._uow.rollback()
            raise
        view = self._queries.order(order_id=order.id)
        assert view is not None  # noqa: S101 - just written
        return view
