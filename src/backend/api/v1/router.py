"""Compose version 1 HTTP endpoints."""

from fastapi import APIRouter

from backend.api.v1.endpoints import (
    articles,
    auth,
    comments,
    feeds,
    interactions,
    links,
    posts,
    profiles,
    publication_state,
    publications,
    uploads,
)

router = APIRouter(prefix="/v1")
router.include_router(auth.router)
router.include_router(profiles.router)
router.include_router(links.router)
router.include_router(posts.router)
router.include_router(articles.router)
router.include_router(publications.router)
router.include_router(publication_state.router)
router.include_router(feeds.router)
router.include_router(interactions.router)
router.include_router(comments.router)
router.include_router(uploads.router)

