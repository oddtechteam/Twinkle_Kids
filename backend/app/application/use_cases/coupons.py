"""Admin coupon management. Validation of a coupon against an order lives in the domain
(`Coupon.discount_for`) and is always re-run on the server at checkout."""

from dataclasses import dataclass, field, replace
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.domain.entities.identity import User
from app.domain.entities.order import Coupon, CouponScope
from app.domain.enums import DiscountType
from app.domain.errors import ConflictError, DomainValidationError, NotFoundError
from app.domain.repositories.catalog import CategoryRepository, ProductRepository
from app.domain.repositories.commerce import CouponRepository
from app.domain.repositories.identity import AuditLogRepository
from app.domain.repositories.media import UnitOfWork
from app.domain.repositories.site import CollectionAdminRepository
from app.domain.value_objects.pricing import to_money


@dataclass(frozen=True, slots=True)
class CouponUsage:
    coupon: Coupon
    times_used: int
    discount_given: Decimal


@dataclass(slots=True)
class CouponInput:
    code: str
    discount_type: DiscountType
    discount_value: Decimal
    description: str | None = None
    is_active: bool = True
    min_order_amount: Decimal | None = None
    max_discount_amount: Decimal | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    usage_limit: int | None = None
    per_user_limit: int | None = None
    product_ids: list[UUID] = field(default_factory=list)
    category_ids: list[UUID] = field(default_factory=list)
    collection_ids: list[UUID] = field(default_factory=list)


class CouponService:
    def __init__(
        self,
        *,
        coupons: CouponRepository,
        products: ProductRepository,
        categories: CategoryRepository,
        collections: CollectionAdminRepository,
        audit: AuditLogRepository,
        uow: UnitOfWork,
    ) -> None:
        self._coupons = coupons
        self._products = products
        self._categories = categories
        self._collections = collections
        self._audit = audit
        self._uow = uow

    def list(self) -> list[CouponUsage]:
        return [CouponUsage(c, uses, given) for c, uses, given in self._coupons.list()]

    def create(self, data: CouponInput, *, actor: User) -> Coupon:
        coupon = self._build(uuid4(), data)
        if self._coupons.code_taken(coupon.code):
            raise ConflictError(f"The code {coupon.code} already exists.")
        self._coupons.add(coupon)
        self._log(actor, "coupon.created", coupon)
        self._uow.commit()
        return coupon

    def update(self, coupon_id: UUID, data: CouponInput, *, actor: User) -> Coupon:
        if self._coupons.get(coupon_id) is None:
            raise NotFoundError("Coupon not found.")
        coupon = self._build(coupon_id, data)
        if self._coupons.code_taken(coupon.code, exclude_id=coupon_id):
            raise ConflictError(f"The code {coupon.code} already exists.")
        self._coupons.save(coupon)
        self._log(actor, "coupon.updated", coupon)
        self._uow.commit()
        return coupon

    def set_active(self, coupon_id: UUID, active: bool, *, actor: User) -> Coupon:
        current = self._coupons.get(coupon_id)
        if current is None:
            raise NotFoundError("Coupon not found.")
        coupon = replace(current, is_active=active)
        self._coupons.save(coupon)
        self._log(actor, "coupon.activated" if active else "coupon.deactivated", coupon)
        self._uow.commit()
        return coupon

    def _build(self, coupon_id: UUID, data: CouponInput) -> Coupon:
        def money(value: Decimal | None, label: str) -> Decimal | None:
            return None if value is None else to_money(value, field=label)

        description = (data.description or "").strip() or None
        if description and len(description) > 255:
            raise DomainValidationError("The description is too long (255 max).")
        for ids, existing, label in (
            (data.product_ids, self._products.existing_ids(data.product_ids), "products"),
            (data.category_ids, self._categories.existing_ids(data.category_ids), "categories"),
            (
                data.collection_ids,
                self._collections.existing_ids(data.collection_ids),
                "collections",
            ),
        ):
            if set(ids) - set(existing):
                raise DomainValidationError(f"Some selected {label} no longer exist.")
        coupon = Coupon(
            id=coupon_id,
            code=data.code.strip().upper(),
            description=description,
            discount_type=data.discount_type,
            discount_value=to_money(data.discount_value, field="Discount"),
            is_active=data.is_active,
            min_order_amount=money(data.min_order_amount, "Minimum order"),
            max_discount_amount=money(data.max_discount_amount, "Maximum discount"),
            starts_at=data.starts_at,
            ends_at=data.ends_at,
            usage_limit=data.usage_limit,
            per_user_limit=data.per_user_limit,
            scope=CouponScope(
                product_ids=frozenset(data.product_ids),
                category_ids=frozenset(data.category_ids),
                collection_ids=frozenset(data.collection_ids),
            ),
        )
        coupon.validate()
        return coupon

    def _log(self, actor: User, action: str, coupon: Coupon) -> None:
        self._audit.record(
            actor_user_id=actor.id,
            action=action,
            entity_type="coupon",
            entity_id=str(coupon.id),
            changes={
                "code": coupon.code,
                "type": coupon.discount_type.value,
                "value": str(coupon.discount_value),
                "active": coupon.is_active,
            },
        )
