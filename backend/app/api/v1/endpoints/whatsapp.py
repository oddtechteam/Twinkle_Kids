"""Order on WhatsApp: records a request and returns a pre-filled click-to-chat link.

The request stays `initiated` — opening WhatsApp is never treated as a sent message, an order,
a stock reservation or a payment. Staff confirm it in the admin panel.
"""

from fastapi import APIRouter, Request, status

from app.api.deps import OptionalUserDep, WhatsAppOrderingDep
from app.api.schemas.commerce import WhatsAppLinkOut, WhatsAppRequestIn

router = APIRouter(tags=["whatsapp"])


@router.post(
    "/whatsapp-requests", response_model=WhatsAppLinkOut, status_code=status.HTTP_201_CREATED
)
def start_whatsapp_request(
    body: WhatsAppRequestIn,
    request: Request,
    user: OptionalUserDep,
    ordering: WhatsAppOrderingDep,
) -> WhatsAppLinkOut:
    link = ordering.start(
        [(item.variant_id, item.quantity) for item in body.items],
        user_id=user.id if user else None,
        client_key=request.client.host if request.client else None,
        customer_name=body.customer_name or (user.full_name if user else None),
    )
    return WhatsAppLinkOut.of(link)
