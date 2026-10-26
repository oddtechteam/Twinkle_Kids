from fastapi import APIRouter

from app.api.v1.endpoints import (
    account,
    admin,
    admin_content,
    admin_ops,
    admin_orders,
    auth,
    cart,
    catalog,
    checkout,
    content,
    health,
    media,
    reviews,
    whatsapp,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(catalog.router)
api_router.include_router(content.router)
api_router.include_router(cart.router)
api_router.include_router(checkout.router)
api_router.include_router(account.router)
api_router.include_router(whatsapp.router)
api_router.include_router(admin.router)
api_router.include_router(admin_content.router)
api_router.include_router(admin_orders.router)
api_router.include_router(admin_ops.router)
api_router.include_router(reviews.router)
api_router.include_router(media.public_router)
api_router.include_router(media.admin_router)
