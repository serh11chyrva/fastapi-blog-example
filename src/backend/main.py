import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from loguru import logger
from pymongo import AsyncMongoClient
from redis.asyncio import Redis

from backend.content.feed_router import router as feed_router
from backend.content.router import router as content_router
from backend.content.scheduler import run_publication_scheduler
from backend.content.migrations import ensure_public_share_ids
from backend.core.config import get_settings
from backend.core.database import DOCUMENT_MODELS
from backend.profiles.router import router as profile_router
from backend.storage.s3 import check_storage, create_s3_client
from backend.auth.router import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    mongo_client = AsyncMongoClient(settings.mongodb_url, serverSelectionTimeoutMS=8_000, tz_aware=True)
    redis_client = Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=3)
    s3_client = create_s3_client(settings)
    app.state.mongo_client = mongo_client
    app.state.redis = redis_client
    app.state.s3_client = s3_client
    app.state.logger = logger
    scheduler_task = None
    try:
        await mongo_client.admin.command("ping")
        from beanie import init_beanie

        await init_beanie(database=mongo_client[settings.mongodb_database], document_models=DOCUMENT_MODELS)
        await ensure_public_share_ids()
        await redis_client.ping()
        await check_storage(s3_client, settings.avatar_bucket)
        scheduler_task = asyncio.create_task(run_publication_scheduler(mongo_client, redis_client), name="scheduled-publications")
        yield
    finally:
        if scheduler_task is not None:
            scheduler_task.cancel()
            try:
                await scheduler_task
            except asyncio.CancelledError:
                pass
        await redis_client.aclose()
        s3_client.close()
        await mongo_client.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Commonplace API",
        version="0.1.0",
        summary="A session-based microblog and article publishing API.",
        description=(
            "Browse public profiles and publications, follow writers, publish short posts, and draft TipTap articles.\n\n"
            "The browser API is served from the same origin at `/api/v1`. Session credentials are issued as an "
            "HttpOnly cookie. Request and response examples are in `docs/API.md`; interactive schemas are available at `/api/docs`."
        ),
        openapi_tags=[
            {"name": "authentication", "description": "Registration, login, and server-side browser sessions."},
            {"name": "profiles", "description": "Public profiles, avatars, and follow relationships."},
            {"name": "publications", "description": "Micro-posts and TipTap article drafts/publications."},
            {"name": "feeds", "description": "Chronological public and followed-author feeds."},
            {"name": "health", "description": "Application and dependency health checks."},
        ],
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(profile_router, prefix="/api/v1")
    app.include_router(content_router, prefix="/api/v1")
    app.include_router(feed_router, prefix="/api/v1")

    def custom_openapi() -> dict:
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            summary=app.summary,
            description=app.description,
            routes=app.routes,
            tags=app.openapi_tags,
        )
        schema.setdefault("components", {}).setdefault("securitySchemes", {})["SessionCookie"] = {
            "type": "apiKey",
            "in": "cookie",
            "name": get_settings().session_cookie_name,
            "description": "Opaque HttpOnly session cookie. Obtain it with POST /api/v1/auth/login or /register.",
        }
        operation_docs = {
            ("get", "/api/v1/auth/me"): ("Get the current account", "Returns the account associated with the current session cookie."),
            ("post", "/api/v1/auth/register"): ("Register and start a session", "Creates the account and session atomically with an audit event. Sets the HttpOnly session cookie."),
            ("post", "/api/v1/auth/login"): ("Log in", "Accepts an email address or username. Successful login sets the HttpOnly session cookie."),
            ("post", "/api/v1/auth/logout"): ("Log out this session", "Revokes the current session and clears the cookie."),
            ("get", "/api/v1/auth/sessions"): ("List active sessions", "Includes IP address, User-Agent, expiry and a flag identifying this session."),
            ("delete", "/api/v1/auth/sessions/{session_id}"): ("Revoke a session", "Revokes one of your sessions. Unknown and other users' sessions both return 404."),
            ("post", "/api/v1/auth/sessions/logout-others"): ("Log out other sessions", "Revokes every active session except the cookie used for this request."),
            ("get", "/api/v1/users/{username}"): ("Get a public profile", "Username is case-insensitive; follow state is relative to the optional current session."),
            ("get", "/api/v1/users/{username}/publications"): ("List profile publications", "Returns up to 50 public micro-posts and published articles, newest first."),
            ("patch", "/api/v1/me/profile"): ("Update your profile", "Partial update. Omitted fields stay unchanged; links accept at most eight HTTP(S) URLs."),
            ("put", "/api/v1/me/avatar"): ("Upload your avatar", "Multipart file upload. JPEG, PNG, and WebP are accepted, up to the configured size limit (5 MiB by default)."),
            ("get", "/api/v1/media/avatars/{object_name}"): ("Read an avatar", "Returns the image bytes with a detected image content type."),
            ("get", "/api/v1/users/{username}/followers"): ("List followers", "Returns compact public profile cards."),
            ("get", "/api/v1/users/{username}/following"): ("List followed profiles", "Returns compact public profile cards."),
            ("put", "/api/v1/users/{username}/follow"): ("Follow a profile", "Idempotently creates a follow relationship; following yourself returns 400."),
            ("delete", "/api/v1/users/{username}/follow"): ("Unfollow a profile", "Idempotently removes the follow relationship."),
            ("post", "/api/v1/posts"): ("Publish a micro-post", "Creates a public post immediately. Text is trimmed and limited to 280 characters."),
            ("get", "/api/v1/posts/{post_id}"): ("Get a micro-post", "Returns a public post; deleted or malformed identifiers return 404."),
            ("patch", "/api/v1/posts/{post_id}"): ("Edit your micro-post", "Only the author may edit a post. The complete text field is required."),
            ("delete", "/api/v1/posts/{post_id}"): ("Delete your micro-post", "Soft-deletes the post; only the author may delete it."),
            ("post", "/api/v1/articles"): ("Create an article draft", "Creates a private-to-author draft. The body must follow the supported TipTap JSON schema."),
            ("get", "/api/v1/me/articles"): ("List your articles", "Set status to all, draft, or published. Drafts are visible only to their author."),
            ("get", "/api/v1/articles/{article_id}"): ("Get an article", "Published articles are public; drafts are returned only to their author."),
            ("patch", "/api/v1/articles/{article_id}"): ("Edit your article", "Partial update of title, summary, or TipTap JSON body; only the author may edit."),
            ("post", "/api/v1/articles/{article_id}/publish"): ("Publish an article", "Makes your draft public and assigns its publication timestamp."),
            ("post", "/api/v1/articles/{article_id}/draft"): ("Return an article to draft", "Unpublishes or unschedules your article and makes it private to you."),
            ("post", "/api/v1/articles/{article_id}/schedule"): ("Schedule an article", "Sets a future timezone-aware publication time; the background worker publishes it automatically."),
            ("delete", "/api/v1/articles/{article_id}"): ("Delete an article", "Soft-deletes your draft, scheduled article, or publication."),
            ("put", "/api/v1/articles/{article_id}/thumbnail"): ("Upload an article thumbnail", "Multipart file upload. JPEG, PNG, and WebP are accepted, up to 10 MiB by default."),
            ("get", "/api/v1/media/article-thumbnails/{object_name}"): ("Read an article thumbnail", "Published thumbnails are public; draft thumbnails are visible to their author."),
            ("get", "/api/v1/publications/{username}/{share_slug}"): ("Read a shared publication", "Resolves the UUID-safe slug in /@username/slug--share-id and returns the public post or article."),
            ("get", "/api/v1/feeds/public"): ("Read the public feed", "Chronological mixed feed of public micro-posts and published articles."),
            ("get", "/api/v1/feeds/following"): ("Read the following feed", "Chronological mixed feed from followed authors; requires a session cookie."),
            ("get", "/"): ("Root status", "Returns a short application identifier."),
            ("get", "/health"): ("Check dependency health", "Pings MongoDB and Redis and checks object storage; returns 503 if a dependency is unavailable."),
        }
        examples = {
            ("post", "/api/v1/auth/register"): {
                "request": {"email": "reader@example.com", "username": "reader_one", "display_name": "Avery Reader", "password": "Correct-Horse-Battery-42"},
                "response": {"id": "65f0c2a1b2c3d4e5f6071829", "email": "reader@example.com", "username": "reader_one", "display_name": "Avery Reader"},
            },
            ("post", "/api/v1/auth/login"): {
                "request": {"identifier": "reader@example.com", "password": "Correct-Horse-Battery-42"},
                "response": {"id": "65f0c2a1b2c3d4e5f6071829", "email": "reader@example.com", "username": "reader_one", "display_name": "Avery Reader"},
            },
            ("patch", "/api/v1/me/profile"): {
                "request": {"display_name": "Avery R.", "bio": "Writing about books and software.", "links": [{"label": "Website", "url": "https://example.com"}]},
                "response": {"id": "65f0c2a1b2c3d4e5f6071829", "username": "reader_one", "display_name": "Avery R.", "bio": "Writing about books and software.", "links": [{"label": "Website", "url": "https://example.com"}], "avatar_url": None, "badges": [], "follower_count": 3, "following_count": 5, "is_following": False},
            },
            ("post", "/api/v1/posts"): {
                "request": {"text": "A small idea worth sharing with the community."},
                "response": {"id": "65f0c2a1b2c3d4e5f6071831", "kind": "micro_post", "text": "A small idea worth sharing with the community.", "author_id": "65f0c2a1b2c3d4e5f6071829", "author_username": "reader_one", "author_display_name": "Avery R.", "author_avatar_url": None, "created_at": "2026-10-12T09:34:15Z", "updated_at": "2026-10-12T09:34:15Z"},
            },
            ("post", "/api/v1/articles"): {
                "request": {"title": "Notes on reading", "summary": "A few practical ideas.", "body": {"type": "doc", "content": [{"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "Start small"}]}, {"type": "paragraph", "content": [{"type": "text", "text": "Ten minutes a day is enough to begin."}]}]}},
                "response": {"id": "65f0c2a1b2c3d4e5f6071832", "kind": "article", "title": "Notes on reading", "summary": "A few practical ideas.", "body": {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Draft content."}]}]}, "status": "draft", "author_id": "65f0c2a1b2c3d4e5f6071829", "author_username": "reader_one", "author_display_name": "Avery R.", "author_avatar_url": None, "created_at": "2026-10-12T09:34:15Z", "updated_at": "2026-10-12T09:34:15Z", "published_at": None},
            },
        }
        protected = {
            ("get", "/api/v1/auth/me"), ("post", "/api/v1/auth/logout"), ("get", "/api/v1/auth/sessions"),
            ("delete", "/api/v1/auth/sessions/{session_id}"), ("post", "/api/v1/auth/sessions/logout-others"),
            ("patch", "/api/v1/me/profile"), ("put", "/api/v1/me/avatar"),
            ("put", "/api/v1/users/{username}/follow"), ("delete", "/api/v1/users/{username}/follow"),
            ("post", "/api/v1/posts"), ("patch", "/api/v1/posts/{post_id}"), ("delete", "/api/v1/posts/{post_id}"),
            ("post", "/api/v1/articles"), ("get", "/api/v1/me/articles"), ("patch", "/api/v1/articles/{article_id}"),
            ("post", "/api/v1/articles/{article_id}/publish"), ("get", "/api/v1/feeds/following"),
            ("post", "/api/v1/articles/{article_id}/draft"), ("post", "/api/v1/articles/{article_id}/schedule"),
            ("delete", "/api/v1/articles/{article_id}"), ("put", "/api/v1/articles/{article_id}/thumbnail"),
        }
        for path, path_item in schema.get("paths", {}).items():
            for method, operation in path_item.items():
                if not isinstance(operation, dict):
                    continue
                details = operation_docs.get((method, path))
                if details:
                    operation["summary"], operation["description"] = details
                example = examples.get((method, path))
                if example:
                    request_body = operation.get("requestBody", {}).get("content", {}).get("application/json")
                    if request_body:
                        request_body["examples"] = {"sample": {"summary": "Example request", "value": example["request"]}}
                    success_code = "201" if (method, path) in {("post", "/api/v1/auth/register"), ("post", "/api/v1/posts"), ("post", "/api/v1/articles")} else "200"
                    response_content = operation.get("responses", {}).get(success_code, {}).get("content", {}).get("application/json")
                    if response_content:
                        response_content["examples"] = {"sample": {"summary": "Example response", "value": example["response"]}}
                if (method, path) in protected:
                    operation["security"] = [{"SessionCookie": []}]
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi

    @app.middleware("http")
    async def enforce_same_origin(request: Request, call_next):
        if request.url.path.startswith("/api/v1/") and request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            origin = request.headers.get("origin", "").rstrip("/")
            if origin != get_settings().app_origin:
                return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": "Cross-origin request rejected"})
        return await call_next(request)

    @app.get("/", tags=["health"])
    async def root() -> dict[str, str]:
        return {"message": "FastAPI Microblog Demo"}

    @app.get("/health", tags=["health"])
    async def health(request: Request) -> dict[str, str]:
        try:
            await request.app.state.mongo_client.admin.command("ping")
            await request.app.state.redis.ping()
            await check_storage(request.app.state.s3_client, get_settings().avatar_bucket)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="A required service is unavailable") from exc
        return {"status": "ok", "database": "ok", "redis": "ok", "object_storage": "ok"}

    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000)
