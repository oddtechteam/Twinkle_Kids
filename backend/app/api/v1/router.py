from fastapi import APIRouter

from app.api.v1.endpoints import admin, auth, catalog, health, media

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(catalog.router)
api_router.include_router(admin.router)
api_router.include_router(media.public_router)
api_router.include_router(media.admin_router)
