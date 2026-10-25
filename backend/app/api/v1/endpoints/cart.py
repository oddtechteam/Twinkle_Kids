"""Shopping bag for guests (HttpOnly cookie token) and signed-in customers.

Prices and totals are always recalculated server-side from the catalogue. When a guest signs
in, their guest bag is merged into the account bag on the next cart request.
"""

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response

from app.api.deps import CartServiceDep, OptionalUserDep, SettingsDep
from app.api.schemas.commerce import AddCartItemIn, CartOut, UpdateCartItemIn
from app.application.use_cases.cart import CartOwner
from app.core.config import Settings
from app.core.security import hash_token, new_token

router = APIRouter(prefix="/cart", tags=["cart"])


def _set_cart_cookie(response: Response, settings: Settings, token: str) -> None:
    response.set_cookie(
        settings.cart_cookie_name,
        token,
        max_age=settings.cart_ttl_days * 24 * 3600,
        httponly=True,
        secure=settings.secure_cookies,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        path="/",
    )


def _clear_cart_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        settings.cart_cookie_name,
        path="/",
        domain=settings.cookie_domain,
        secure=settings.secure_cookies,
        httponly=True,
        samesite=settings.cookie_samesite,
    )


def _owner_dependency(*, create: bool) -> Callable[..., CartOwner]:
    def resolve(
        request: Request,
        response: Response,
        settings: SettingsDep,
        user: OptionalUserDep,
        carts: CartServiceDep,
    ) -> CartOwner:
        token = request.cookies.get(settings.cart_cookie_name)
        if user is not None:
            if token:
                carts.merge_guest_cart(user_id=user.id, guest_token_hash=hash_token(token))
                _clear_cart_cookie(response, settings)
            return CartOwner(user_id=user.id)
        if not token and create:
            token = new_token()
            _set_cart_cookie(response, settings, token)
        return CartOwner(guest_token_hash=hash_token(token) if token else None)

    return resolve


OwnerDep = Annotated[CartOwner, Depends(_owner_dependency(create=False))]
CreatingOwnerDep = Annotated[CartOwner, Depends(_owner_dependency(create=True))]


@router.get("", response_model=CartOut)
def get_cart(owner: OwnerDep, carts: CartServiceDep) -> CartOut:
    return CartOut.of(carts.view(owner))


@router.post("/items", response_model=CartOut)
def add_item(body: AddCartItemIn, owner: CreatingOwnerDep, carts: CartServiceDep) -> CartOut:
    """Add a variant (quantities combine with an existing line). Prices are never accepted."""
    return CartOut.of(carts.add(owner, variant_id=body.variant_id, quantity=body.quantity))


@router.patch("/items/{item_id}", response_model=CartOut)
def update_item(
    item_id: UUID, body: UpdateCartItemIn, owner: OwnerDep, carts: CartServiceDep
) -> CartOut:
    return CartOut.of(carts.update(owner, item_id, quantity=body.quantity))


@router.delete("/items/{item_id}", response_model=CartOut)
def remove_item(item_id: UUID, owner: OwnerDep, carts: CartServiceDep) -> CartOut:
    return CartOut.of(carts.remove(owner, item_id))


@router.post("/acknowledge-prices", response_model=CartOut)
def acknowledge_prices(owner: OwnerDep, carts: CartServiceDep) -> CartOut:
    """The shopper has seen updated prices; stop flagging them as changed."""
    return CartOut.of(carts.acknowledge_prices(owner))
