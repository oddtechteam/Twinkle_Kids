"""WhatsApp ordering: record what the customer asked for and hand them a click-to-chat link.

The record is a *request*, never an order: it reserves no stock, takes no payment and its
status stays `initiated` (link handed out) until staff confirm they actually received the
message. Prices in the message come from the catalogue, never from the browser.
"""

import re
import secrets
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from urllib.parse import quote
from uuid import UUID, uuid4

from app.application.ports import RateLimiter
from app.domain.entities.commerce import (
    MAX_CART_LINES,
    OrderLineSnapshot,
    WhatsAppOrderRequest,
    validate_cart_quantity,
)
from app.domain.errors import DomainValidationError, NotFoundError, RateLimitedError
from app.domain.repositories.catalog import ProductRepository
from app.domain.repositories.commerce import CartRepository, WhatsAppRequestRepository
from app.domain.repositories.media import UnitOfWork
from app.domain.repositories.site import SettingsRepository
from app.domain.value_objects.pricing import calculate_totals

REFERENCE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I look-alikes
CURRENCY_SYMBOLS = {"INR": "₹"}
MAX_REQUESTS_PER_IP = 20
WINDOW_SECONDS = 15 * 60


@dataclass(frozen=True, slots=True)
class WhatsAppLink:
    reference: str
    url: str
    message: str
    estimated_subtotal: Decimal
    currency_code: str


def _money(amount: Decimal, currency: str) -> str:
    symbol = CURRENCY_SYMBOLS.get(currency)
    return f"{symbol}{amount:,.2f}" if symbol else f"{currency} {amount:,.2f}"


def whatsapp_digits(number: str | None) -> str | None:
    """wa.me expects the full international number as digits only (no +, spaces or dashes)."""
    digits = re.sub(r"\D", "", number or "")
    return digits if 8 <= len(digits) <= 15 else None


def build_message(
    *,
    intro: str,
    reference: str,
    lines: Sequence[OrderLineSnapshot],
    subtotal: Decimal,
    currency: str,
    storefront_url: str,
) -> str:
    parts = [intro.strip(), "", f"Request reference: {reference}", ""]
    for index, line in enumerate(lines, start=1):
        options = " · ".join(
            f"{label}: {value}"
            for label, value in (("Size", line.size), ("Colour", line.colour))
            if value
        )
        parts.append(f"{index}. {line.product_name}")
        if options:
            parts.append(f"   {options}")
        parts.append(f"   SKU: {line.sku}")
        parts.append(
            f"   Qty {line.quantity} × {_money(line.unit_price.selling, currency)}"
            f" = {_money(line.priced.total, currency)}"
        )
        if storefront_url:
            parts.append(f"   {storefront_url.rstrip('/')}/products/{line.product_slug}")
        parts.append("")
    parts.append(f"Estimated total: {_money(subtotal, currency)} (before delivery)")
    parts.append("Please confirm availability, delivery and payment details.")
    return "\n".join(parts)


class WhatsAppOrdering:
    def __init__(
        self,
        *,
        settings: SettingsRepository,
        carts: CartRepository,
        products: ProductRepository,
        requests: WhatsAppRequestRepository,
        rate_limiter: RateLimiter,
        uow: UnitOfWork,
        storefront_url: str,
    ) -> None:
        self._settings = settings
        self._carts = carts
        self._products = products
        self._requests = requests
        self._limiter = rate_limiter
        self._uow = uow
        self._storefront_url = storefront_url

    def start(
        self,
        items: Sequence[tuple[UUID, int]],
        *,
        user_id: UUID | None,
        client_key: str | None,
        customer_name: str | None = None,
    ) -> WhatsAppLink:
        settings = self._settings.get()
        number = whatsapp_digits(settings.whatsapp_number)
        if not settings.whatsapp_ordering_enabled or number is None:
            raise DomainValidationError("Ordering on WhatsApp isn't available right now.")

        retry_after = self._limiter.hit(
            f"whatsapp:{client_key or 'unknown'}",
            limit=MAX_REQUESTS_PER_IP,
            window_seconds=WINDOW_SECONDS,
        )
        if retry_after is not None:
            raise RateLimitedError(
                "Too many WhatsApp requests. Please try again later.", retry_after
            )

        merged: dict[UUID, int] = {}
        for variant_id, quantity in items:
            merged[variant_id] = merged.get(variant_id, 0) + validate_cart_quantity(quantity)
        if not merged:
            raise DomainValidationError("Choose at least one item to order.")
        if len(merged) > MAX_CART_LINES:
            raise DomainValidationError(f"Order up to {MAX_CART_LINES} different items at once.")

        product_ids = self._carts.product_ids_for_variants(list(merged))
        lines: list[OrderLineSnapshot] = []
        for variant_id, quantity in merged.items():
            product_id = product_ids.get(variant_id)
            product = self._products.get(product_id) if product_id else None
            if product is None:
                raise NotFoundError("One of these items is no longer available.")
            # Validates status, variant ownership, stock and price exactly like an order line.
            validate_cart_quantity(quantity)  # combined duplicates must still fit one line
            lines.append(OrderLineSnapshot.capture(product, variant_id, quantity))

        subtotal = calculate_totals(line.priced for line in lines).subtotal
        reference = self._new_reference()
        intro = (
            settings.whatsapp_message_template
            or f"Hello {settings.store_name}! I'd like to order:"
        )
        message = build_message(
            intro=intro,
            reference=reference,
            lines=lines,
            subtotal=subtotal,
            currency=settings.currency_code,
            storefront_url=self._storefront_url,
        )
        self._requests.add(
            WhatsAppOrderRequest(
                id=uuid4(),
                reference=reference,
                user_id=user_id,
                message_text=message,
                lines=tuple(lines),
                estimated_subtotal=subtotal,
                customer_name=(customer_name or "").strip()[:120] or None,
            )
        )
        self._uow.commit()
        return WhatsAppLink(
            reference=reference,
            url=f"https://wa.me/{number}?text={quote(message, safe='')}",
            message=message,
            estimated_subtotal=subtotal,
            currency_code=settings.currency_code,
        )

    def _new_reference(self) -> str:
        for _ in range(10):
            reference = "WA-" + "".join(secrets.choice(REFERENCE_ALPHABET) for _ in range(6))
            if not self._requests.reference_taken(reference):
                return reference
        raise DomainValidationError("Please try again.")  # pragma: no cover - astronomically rare
