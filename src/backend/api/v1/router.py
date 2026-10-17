"""Compose version 1 HTTP endpoints."""

from fastapi import APIRouter

from backend.api.v1.endpoints import auth, content, feeds, links, profiles, uploads

router = APIRouter(prefix="/v1")
router.include_router(auth.router)
router.include_router(profiles.router)
router.include_router(links.router)
router.include_router(content.router)
router.include_router(feeds.router)
router.include_router(uploads.router)
