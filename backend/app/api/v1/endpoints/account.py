"""Signed-in customer self-service: profile, password, address book and order history.

Order history shows what was bought and paid for — never internal statuses or a tracking
timeline (customers contact the shop for updates).
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from app.api.deps import (
    AccountServiceDep,
    AfterSaleDep,
    CurrentSessionDep,
    CurrentUserDep,
    CustomerOrdersDep,
)
from app.api.schemas.auth import UserOut
from app.api.schemas.operations import CustomerRequestOut, OrderRequestIn
from app.api.schemas.orders import (
    ChangePasswordIn,
    CustomerOrderListOut,
    CustomerOrderOut,
    CustomerOrderSummaryOut,
    ProfileIn,
    SavedAddressIn,
    SavedAddressOut,
)
from app.application.use_cases.after_sale import RequestItem

router = APIRouter(prefix="/account", tags=["account"])


@router.patch("/profile", response_model=UserOut)
def update_profile(body: ProfileIn, user: CurrentUserDep, accounts: AccountServiceDep) -> UserOut:
    return UserOut.of(accounts.update_profile(user, full_name=body.full_name, phone=body.phone))


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    body: ChangePasswordIn,
    user: CurrentUserDep,
    session: CurrentSessionDep,
    accounts: AccountServiceDep,
) -> Response:
    """Other devices are signed out; this one stays signed in."""
    accounts.change_password(
        user,
        current_password=body.current_password,
        new_password=body.new_password,
        session_id=session.id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/addresses", response_model=list[SavedAddressOut])
def list_addresses(user: CurrentUserDep, accounts: AccountServiceDep) -> list[SavedAddressOut]:
    return [SavedAddressOut.of(a) for a in accounts.addresses(user.id)]


@router.post("/addresses", response_model=SavedAddressOut, status_code=status.HTTP_201_CREATED)
def add_address(
    body: SavedAddressIn, user: CurrentUserDep, accounts: AccountServiceDep
) -> SavedAddressOut:
    saved = accounts.add_address(
        user.id,
        body.to_domain_address(),
        label=body.label,
        make_default=body.is_default,
    )
    return SavedAddressOut.of(saved)


@router.put("/addresses/{address_id}", response_model=SavedAddressOut)
def update_address(
    address_id: UUID, body: SavedAddressIn, user: CurrentUserDep, accounts: AccountServiceDep
) -> SavedAddressOut:
    saved = accounts.update_address(
        user.id,
        address_id,
        body.to_domain_address(),
        label=body.label,
        make_default=body.is_default,
    )
    return SavedAddressOut.of(saved)


@router.delete("/addresses/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_address(address_id: UUID, user: CurrentUserDep, accounts: AccountServiceDep) -> Response:
    accounts.delete_address(user.id, address_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/orders", response_model=CustomerOrderListOut)
def my_orders(
    user: CurrentUserDep,
    orders: CustomerOrdersDep,
    page: Annotated[int, Query(ge=1, le=1000)] = 1,
) -> CustomerOrderListOut:
    result = orders.list(user, page=page)
    return CustomerOrderListOut(
        items=[CustomerOrderSummaryOut.model_validate(o) for o in result.items],
        total=result.total,
        page=result.page,
        pages=result.pages,
    )


@router.get("/orders/{order_number}", response_model=CustomerOrderOut)
def my_order(
    order_number: str, user: CurrentUserDep, orders: CustomerOrdersDep
) -> CustomerOrderOut:
    return CustomerOrderOut.model_validate(orders.get(user, order_number))


@router.get("/orders/{order_number}/requests", response_model=list[CustomerRequestOut])
def my_order_requests(
    order_number: str, user: CurrentUserDep, service: AfterSaleDep
) -> list[CustomerRequestOut]:
    """Cancellation / return / exchange requests for one of my orders and the shop's answer."""
    return [CustomerRequestOut.model_validate(r) for r in service.requests_for(user, order_number)]


@router.post("/orders/{order_number}/requests", response_model=CustomerRequestOut, status_code=201)
def create_order_request(
    order_number: str, body: OrderRequestIn, user: CurrentUserDep, service: AfterSaleDep
) -> CustomerRequestOut:
    """Only the kinds the store's policy enables. Refunds are arranged by the shop."""
    request = service.create(
        user,
        order_number,
        kind=body.kind,
        reason=body.reason,
        message=body.message,
        items=[RequestItem(sku=i.sku, quantity=i.quantity) for i in body.items],
    )
    return CustomerRequestOut.model_validate(request)
