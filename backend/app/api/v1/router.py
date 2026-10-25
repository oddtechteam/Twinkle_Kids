from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    admin_content,
    auth,
    cart,
    catalog,
    content,
    health,
    media,
    whatsapp,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(catalog.router)
api_router.include_router(content.router)
api_router.include_router(cart.router)
api_router.include_router(whatsapp.router)
api_router.include_router(admin.router)
api_router.include_router(admin_content.router)
api_router.include_router(media.public_router)
api_router.include_router(media.admin_router)
