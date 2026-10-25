from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.domain.entities.commerce import Cart, CartItem, WhatsAppOrderRequest
from app.domain.enums import CartStatus, WhatsAppRequestStatus
from app.infrastructure.db.models.catalog import ProductVariantModel
from app.infrastructure.db.models.commerce import (
    CartItemModel,
    CartModel,
    WhatsAppOrderRequestItemModel,
    WhatsAppOrderRequestModel,
)
from app.infrastructure.db.types import utc_now


class SqlAlchemyCartRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _cart(self, row: CartModel) -> Cart:
        items = self._session.execute(
            select(CartItemModel, ProductVariantModel.product_id)
            .join(ProductVariantModel, ProductVariantModel.id == CartItemModel.variant_id)
            .where(CartItemModel.cart_id == row.id)
            .order_by(CartItemModel.created_at, CartItemModel.id)
        ).all()
        return Cart(
            id=row.id,
            user_id=row.user_id,
            items=tuple(
                CartItem(
                    id=item.id,
                    variant_id=item.variant_id,
                    product_id=product_id,
                    quantity=item.quantity,
                    unit_price_snapshot=item.unit_price_snapshot,
                )
                for item, product_id in items
            ),
        )

    def find_active(
        self, *, user_id: UUID | None = None, guest_token_hash: str | None = None
    ) -> Cart | None:
        stmt = select(CartModel).where(CartModel.status == CartStatus.ACTIVE.value)
        if user_id is not None:
            stmt = stmt.where(CartModel.user_id == user_id)
        elif guest_token_hash is not None:
            stmt = stmt.where(
                CartModel.guest_token_hash == guest_token_hash, CartModel.user_id.is_(None)
            )
        else:
            return None
        row = self._session.scalars(stmt.order_by(CartModel.updated_at.desc())).first()
        return self._cart(row) if row else None

    def create(self, *, user_id: UUID | None, guest_token_hash: str | None) -> Cart:
        row = CartModel(
            id=uuid4(),
            user_id=user_id,
            guest_token_hash=None if user_id else guest_token_hash,
            status=CartStatus.ACTIVE.value,
        )
        self._session.add(row)
        self._session.flush()
        return Cart(id=row.id, user_id=user_id)

    def add_item(
        self,
        cart_id: UUID,
        *,
        variant_id: UUID,
        quantity: int,
        unit_price_snapshot: Decimal | None,
    ) -> None:
        self._session.add(
            CartItemModel(
                id=uuid4(),
                cart_id=cart_id,
                variant_id=variant_id,
                quantity=quantity,
                unit_price_snapshot=unit_price_snapshot,
            )
        )
        self._touch(cart_id)

    def update_item(
        self, item_id: UUID, *, quantity: int, unit_price_snapshot: Decimal | None = None
    ) -> None:
        row = self._session.get(CartItemModel, item_id)
        if row is None:
            return
        row.quantity = quantity
        if unit_price_snapshot is not None:
            row.unit_price_snapshot = unit_price_snapshot
        self._touch(row.cart_id)

    def remove_item(self, item_id: UUID) -> None:
        row = self._session.get(CartItemModel, item_id)
        if row is not None:
            cart_id = row.cart_id
            self._session.delete(row)
            self._touch(cart_id)

    def set_snapshots(self, prices: dict[UUID, Decimal]) -> None:
        for item_id, price in prices.items():
            self._session.execute(
                update(CartItemModel)
                .where(CartItemModel.id == item_id)
                .values(unit_price_snapshot=price)
            )

    def assign_to_user(self, cart_id: UUID, user_id: UUID) -> None:
        self._session.execute(
            update(CartModel)
            .where(CartModel.id == cart_id)
            .values(user_id=user_id, guest_token_hash=None)
        )

    def delete(self, cart_id: UUID) -> None:
        self._session.execute(delete(CartModel).where(CartModel.id == cart_id))

    def product_ids_for_variants(self, variant_ids: list[UUID]) -> dict[UUID, UUID]:
        if not variant_ids:
            return {}
        rows = self._session.execute(
            select(ProductVariantModel.id, ProductVariantModel.product_id).where(
                ProductVariantModel.id.in_(variant_ids)
            )
        ).all()
        return {variant_id: product_id for variant_id, product_id in rows}

    def _touch(self, cart_id: UUID) -> None:
        cart = self._session.get(CartModel, cart_id)
        if cart is not None:
            cart.updated_at = utc_now()


class SqlAlchemyWhatsAppRequestRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, request: WhatsAppOrderRequest) -> None:
        self._session.add(
            WhatsAppOrderRequestModel(
                id=request.id,
                reference=request.reference,
                user_id=request.user_id,
                customer_name=request.customer_name,
                customer_phone=request.customer_phone,
                message_text=request.message_text,
                status=WhatsAppRequestStatus.INITIATED.value,
                estimated_subtotal=request.estimated_subtotal,
            )
        )
        for line in request.lines:
            priced = line.priced
            self._session.add(
                WhatsAppOrderRequestItemModel(
                    id=uuid4(),
                    request_id=request.id,
                    product_id=line.product_id,
                    variant_id=line.variant_id,
                    product_name=line.product_name,
                    sku=line.sku,
                    size=line.size,
                    colour=line.colour,
                    unit_selling_price=line.unit_price.selling,
                    unit_original_price=line.unit_price.original,
                    quantity=line.quantity,
                    line_total=priced.total,
                )
            )

    def reference_taken(self, reference: str) -> bool:
        return (
            self._session.scalar(
                select(WhatsAppOrderRequestModel.id).where(
                    WhatsAppOrderRequestModel.reference == reference
                )
            )
            is not None
        )
