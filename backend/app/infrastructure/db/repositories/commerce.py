import hashlib
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.domain.entities.commerce import Cart, CartItem, WhatsAppOrderRequest
from app.domain.entities.order import (
    CONVERTIBLE_WHATSAPP_STATUSES,
    Coupon,
    CouponScope,
    NewOrder,
)
from app.domain.enums import (
    CartStatus,
    DiscountType,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    WhatsAppRequestStatus,
)
from app.infrastructure.db.models.catalog import ProductVariantModel
from app.infrastructure.db.models.commerce import (
    CartItemModel,
    CartModel,
    OrderItemModel,
    OrderModel,
    WhatsAppOrderRequestItemModel,
    WhatsAppOrderRequestModel,
)
from app.infrastructure.db.models.marketing import CouponModel, CouponRedemptionModel
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

    def mark_converted(self, cart_id: UUID) -> None:
        row = self._session.get(CartModel, cart_id)
        if row is None:
            return
        row.status = CartStatus.CONVERTED.value
        row.updated_at = utc_now()
        if row.guest_token_hash is not None:
            # Retire the guest token so the same browser can start a fresh bag. The placeholder
            # is not derivable from any cookie, and keeps the "cart has an owner" constraint.
            row.guest_token_hash = hashlib.sha256(
                f"retired:{cart_id}:{row.guest_token_hash}".encode()
            ).hexdigest()
        self._session.flush()

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
        self._session.flush()  # the request row must exist before its item rows (FK)
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

    def status(self, request_id: UUID) -> WhatsAppRequestStatus | None:
        value = self._session.scalar(
            select(WhatsAppOrderRequestModel.status).where(
                WhatsAppOrderRequestModel.id == request_id
            )
        )
        return WhatsAppRequestStatus(value) if value else None

    def items(self, request_id: UUID) -> list[tuple[UUID | None, int]]:
        rows = self._session.execute(
            select(WhatsAppOrderRequestItemModel.variant_id, WhatsAppOrderRequestItemModel.quantity)
            .where(WhatsAppOrderRequestItemModel.request_id == request_id)
            .order_by(WhatsAppOrderRequestItemModel.product_name)
        ).all()
        return [(variant_id, quantity) for variant_id, quantity in rows]

    def set_status(
        self,
        request_id: UUID,
        status: WhatsAppRequestStatus,
        *,
        staff_note: str | None,
        contacted_at: datetime | None = None,
    ) -> None:
        values: dict[str, object] = {"status": status.value, "staff_note": staff_note}
        if contacted_at is not None:
            values["contacted_at"] = contacted_at
        self._session.execute(
            update(WhatsAppOrderRequestModel)
            .where(WhatsAppOrderRequestModel.id == request_id)
            .values(**values)
        )

    def mark_converted(self, request_id: UUID, order_id: UUID) -> bool:
        result = self._session.execute(
            update(WhatsAppOrderRequestModel)
            .where(
                WhatsAppOrderRequestModel.id == request_id,
                WhatsAppOrderRequestModel.status.in_(
                    [s.value for s in CONVERTIBLE_WHATSAPP_STATUSES]
                ),
            )
            .values(status=WhatsAppRequestStatus.CONVERTED.value, converted_order_id=order_id)
        )
        return bool(result.rowcount)  # type: ignore[attr-defined]


class SqlAlchemyOrderRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def id_for_idempotency_key(self, key: str) -> UUID | None:
        return self._session.scalar(select(OrderModel.id).where(OrderModel.idempotency_key == key))

    def number_taken(self, order_number: str) -> bool:
        return (
            self._session.scalar(
                select(OrderModel.id).where(OrderModel.order_number == order_number)
            )
            is not None
        )

    def add(self, order: NewOrder) -> None:
        totals = order.totals
        self._session.add(
            OrderModel(
                id=order.id,
                order_number=order.order_number,
                user_id=order.user_id,
                source=order.source.value,
                status=order.status.value,
                payment_status=order.payment_status.value,
                payment_method=order.payment_method.value,
                customer_email=order.customer_email,
                customer_name=order.customer_name,
                customer_phone=order.customer_phone,
                shipping_address=order.shipping_address,
                subtotal=totals.subtotal,
                discount_total=totals.discount_total,
                shipping_total=totals.shipping_total,
                grand_total=totals.grand_total,
                coupon_code=order.coupon_code,
                customer_note=order.customer_note,
                idempotency_key=order.idempotency_key,
                placed_at=order.placed_at,
            )
        )
        self._session.flush()  # the order row must exist before its items and ledger rows
        for line in order.lines:
            priced = line.priced
            self._session.add(
                OrderItemModel(
                    id=uuid4(),
                    order_id=order.id,
                    product_id=line.product_id,
                    variant_id=line.variant_id,
                    product_name=line.product_name,
                    product_slug=line.product_slug,
                    sku=line.sku,
                    size=line.size,
                    colour=line.colour,
                    image_url=line.image_url,
                    unit_selling_price=line.unit_price.selling,
                    unit_original_price=line.unit_price.original,
                    quantity=line.quantity,
                    line_total=priced.total,
                )
            )

    def deduct_stock(self, variant_id: UUID, quantity: int) -> int | None:
        # A single conditional UPDATE: concurrent orders serialise on the row lock and the
        # condition is re-checked, so stock can never go negative or be deducted twice.
        result = self._session.execute(
            update(ProductVariantModel)
            .where(
                ProductVariantModel.id == variant_id,
                ProductVariantModel.stock_quantity >= quantity,
            )
            .values(stock_quantity=ProductVariantModel.stock_quantity - quantity)
            .execution_options(synchronize_session=False)
        )
        if not result.rowcount:  # type: ignore[attr-defined]
            return None
        return self._stock(variant_id)

    def restock(self, variant_id: UUID, quantity: int) -> int:
        self._session.execute(
            update(ProductVariantModel)
            .where(ProductVariantModel.id == variant_id)
            .values(stock_quantity=ProductVariantModel.stock_quantity + quantity)
            .execution_options(synchronize_session=False)
        )
        return self._stock(variant_id)

    def _stock(self, variant_id: UUID) -> int:
        value = self._session.scalar(
            select(ProductVariantModel.stock_quantity)
            .where(ProductVariantModel.id == variant_id)
            .execution_options(populate_existing=True)
        )
        return int(value or 0)

    def status(self, order_id: UUID) -> OrderStatus | None:
        value = self._session.scalar(select(OrderModel.status).where(OrderModel.id == order_id))
        return OrderStatus(value) if value else None

    def lines_for_restock(self, order_id: UUID) -> list[tuple[UUID, int]]:
        rows = self._session.execute(
            select(OrderItemModel.variant_id, OrderItemModel.quantity).where(
                OrderItemModel.order_id == order_id, OrderItemModel.variant_id.is_not(None)
            )
        ).all()
        return [(variant_id, quantity) for variant_id, quantity in rows if variant_id]

    def lines_with_sku(self, order_id: UUID) -> list[tuple[UUID, str, int]]:
        rows = self._session.execute(
            select(OrderItemModel.variant_id, OrderItemModel.sku, OrderItemModel.quantity).where(
                OrderItemModel.order_id == order_id, OrderItemModel.variant_id.is_not(None)
            )
        ).all()
        return [(variant_id, sku, quantity) for variant_id, sku, quantity in rows if variant_id]

    def set_status(self, order_id: UUID, status: OrderStatus) -> None:
        self._session.execute(
            update(OrderModel)
            .where(OrderModel.id == order_id)
            .values(status=status.value, updated_at=utc_now())
        )

    def set_payment(
        self, order_id: UUID, status: PaymentStatus, method: PaymentMethod | None
    ) -> None:
        values: dict[str, object] = {"payment_status": status.value, "updated_at": utc_now()}
        if method is not None:
            values["payment_method"] = method.value
        self._session.execute(update(OrderModel).where(OrderModel.id == order_id).values(**values))

    def set_internal_note(self, order_id: UUID, note: str | None) -> None:
        self._session.execute(
            update(OrderModel)
            .where(OrderModel.id == order_id)
            .values(internal_note=note, updated_at=utc_now())
        )


class SqlAlchemyCouponRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _entity(row: CouponModel) -> Coupon:
        scope = row.applies_to or {}

        def ids(key: str) -> frozenset[UUID]:
            return frozenset(UUID(str(v)) for v in scope.get(key, []) or [])

        return Coupon(
            id=row.id,
            code=row.code,
            description=row.description,
            discount_type=DiscountType(row.discount_type),
            discount_value=row.discount_value,
            is_active=row.is_active,
            min_order_amount=row.min_order_amount,
            max_discount_amount=row.max_discount_amount,
            starts_at=row.starts_at,
            ends_at=row.ends_at,
            usage_limit=row.usage_limit,
            per_user_limit=row.per_user_limit,
            scope=CouponScope(
                product_ids=ids("product_ids"),
                category_ids=ids("category_ids"),
                collection_ids=ids("collection_ids"),
            ),
        )

    @staticmethod
    def _apply(row: CouponModel, coupon: Coupon) -> None:
        row.code = coupon.code
        row.description = coupon.description
        row.discount_type = coupon.discount_type.value
        row.discount_value = coupon.discount_value
        row.is_active = coupon.is_active
        row.min_order_amount = coupon.min_order_amount
        row.max_discount_amount = coupon.max_discount_amount
        row.starts_at = coupon.starts_at
        row.ends_at = coupon.ends_at
        row.usage_limit = coupon.usage_limit
        row.per_user_limit = coupon.per_user_limit
        row.applies_to = {
            "product_ids": sorted(str(i) for i in coupon.scope.product_ids),
            "category_ids": sorted(str(i) for i in coupon.scope.category_ids),
            "collection_ids": sorted(str(i) for i in coupon.scope.collection_ids),
        }

    def get_by_code(self, code: str) -> Coupon | None:
        row = self._session.scalars(
            select(CouponModel).where(CouponModel.code == code.strip().upper())
        ).first()
        return self._entity(row) if row else None

    def get(self, coupon_id: UUID) -> Coupon | None:
        row = self._session.get(CouponModel, coupon_id)
        return self._entity(row) if row else None

    def list(self) -> list[tuple[Coupon, int, Decimal]]:
        usage = (
            select(
                CouponRedemptionModel.coupon_id,
                func.count().label("uses"),
                func.coalesce(func.sum(CouponRedemptionModel.discount_amount), 0).label("given"),
            )
            .group_by(CouponRedemptionModel.coupon_id)
            .subquery()
        )
        rows = self._session.execute(
            select(CouponModel, usage.c.uses, usage.c.given)
            .outerjoin(usage, usage.c.coupon_id == CouponModel.id)
            .order_by(CouponModel.created_at.desc())
        ).all()
        return [
            (self._entity(row), int(uses or 0), Decimal(str(given or 0)).quantize(Decimal("0.01")))
            for row, uses, given in rows
        ]

    def add(self, coupon: Coupon) -> None:
        row = CouponModel(id=coupon.id)
        self._apply(row, coupon)
        self._session.add(row)
        self._session.flush()

    def save(self, coupon: Coupon) -> None:
        row = self._session.get(CouponModel, coupon.id)
        if row is not None:
            self._apply(row, coupon)
            self._session.flush()

    def code_taken(self, code: str, *, exclude_id: UUID | None = None) -> bool:
        stmt = select(CouponModel.id).where(CouponModel.code == code)
        if exclude_id is not None:
            stmt = stmt.where(CouponModel.id != exclude_id)
        return self._session.scalar(stmt) is not None

    def times_used(self, coupon_id: UUID) -> int:
        return int(
            self._session.scalar(
                select(func.count()).where(CouponRedemptionModel.coupon_id == coupon_id)
            )
            or 0
        )

    def times_used_by(self, coupon_id: UUID, user_id: UUID) -> int:
        return int(
            self._session.scalar(
                select(func.count()).where(
                    CouponRedemptionModel.coupon_id == coupon_id,
                    CouponRedemptionModel.user_id == user_id,
                )
            )
            or 0
        )

    def record_redemption(
        self, *, coupon_id: UUID, order_id: UUID, user_id: UUID | None, amount: Decimal
    ) -> None:
        self._session.add(
            CouponRedemptionModel(
                id=uuid4(),
                coupon_id=coupon_id,
                order_id=order_id,
                user_id=user_id,
                discount_amount=amount,
            )
        )
