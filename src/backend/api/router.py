"""Compose the API prefix and endpoints served at the application root."""

from fastapi import APIRouter

from backend.api.endpoints import badges, images, system
from backend.api.v1.router import router as v1_router

api_router = APIRouter(prefix="/api")
api_router.include_router(v1_router)

router = APIRouter()
router.include_router(api_router)
router.include_router(badges.router)
router.include_router(images.router)
router.include_router(system.router)
