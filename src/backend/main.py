from contextlib import asynccontextmanager
from typing import AsyncIterator
import asyncio

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from loguru import logger
from pymongo import AsyncMongoClient
from pymongo.errors import PyMongoError
from redis.asyncio import Redis
from scalar_fastapi import AgentScalarConfig, Theme, add_scalar_reference
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from backend.auth.router import router as auth_router
from backend.content.feed_router import router as feed_router
from backend.content.migrations import ensure_public_share_ids
from backend.content.router import router as content_router
from backend.content.scheduler import run_publication_scheduler
from backend.core.api_docs import API_DESCRIPTION, OPENAPI_TAGS, configure_openapi
from backend.core.api_metadata import documented_responses
from backend.core.config import get_settings
from backend.core.database import DOCUMENT_MODELS
from backend.core.errors import ApplicationError
from backend.core.resources import AppResources, get_resources
from backend.core.schemas import ApplicationStatusResponse, HealthResponse
from backend.links.router import router as link_router
from backend.profiles.badge_router import router as badge_router
from backend.profiles.migrations import ensure_profile_schema
from backend.profiles.router import router as profile_router
from backend.storage.cleanup import run_storage_cleanup
from backend.storage.image_router import router as image_router
from backend.storage.router import router as upload_router
from backend.storage.s3 import check_storage, create_s3_client


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    mongo_client = AsyncMongoClient(settings.mongodb_url, serverSelectionTimeoutMS=8_000, tz_aware=True)
    redis_client = Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=3)
    s3_client = create_s3_client(settings)
    s3_public_client = create_s3_client(settings, public=True)
    app.state.resources = AppResources(mongo_client, redis_client, s3_client, s3_public_client)
    scheduler_task: asyncio.Task[None] | None = None
    cleanup_task: asyncio.Task[None] | None = None
    try:
        await mongo_client.admin.command("ping")
        from beanie import init_beanie

        await init_beanie(database=mongo_client[settings.mongodb_database], document_models=DOCUMENT_MODELS)
        await ensure_profile_schema()
        await ensure_public_share_ids()
        await redis_client.ping()
        await check_storage(s3_client, settings)
        await redis_client.incr("feed:public:version")
        cleanup_task = asyncio.create_task(run_storage_cleanup(s3_client), name="image-storage-cleanup")
        scheduler_task = asyncio.create_task(run_publication_scheduler(mongo_client, redis_client), name="scheduled-publications")
        yield
    finally:
        if cleanup_task is not None:
            cleanup_task.cancel()
            try:
                await cleanup_task
            except asyncio.CancelledError:
                pass
        if scheduler_task is not None:
            scheduler_task.cancel()
            try:
                await scheduler_task
            except asyncio.CancelledError:
                pass
        await redis_client.aclose()
        s3_client.close()
        s3_public_client.close()
        await mongo_client.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Commonplace API",
        version="0.1.0",
        summary="A session-based microblog and article publishing API.",
        description=API_DESCRIPTION,
        openapi_tags=OPENAPI_TAGS,
        docs_url=None,
        redoc_url=None,
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(profile_router, prefix="/api/v1")
    app.include_router(link_router, prefix="/api/v1")
    app.include_router(content_router, prefix="/api/v1")
    app.include_router(feed_router, prefix="/api/v1")
    app.include_router(upload_router, prefix="/api/v1")
    app.include_router(badge_router)
    app.include_router(image_router)

    configure_openapi(app)

    add_scalar_reference(
        app,
        route="/api/docs",
        title="Commonplace API Reference",
        theme=Theme.DEFAULT,
        hide_models=True,
        agent=AgentScalarConfig(disabled=True),
        telemetry=False,
    )

    @app.exception_handler(ApplicationError)
    async def application_error(request: Request, exc: ApplicationError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(PyMongoError)
    async def database_error(request: Request, exc: PyMongoError) -> JSONResponse:
        logger.opt(exception=exc).error("Database operation failed")
        return JSONResponse(status_code=503, content={"detail": "Database is unavailable; reload before retrying"})

    @app.middleware("http")
    async def enforce_same_origin(request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path.startswith("/api/v1/") and request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            origin = request.headers.get("origin", "").rstrip("/")
            if origin != get_settings().app_origin:
                return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": "Cross-origin request rejected"})
        return await call_next(request)

    @app.get(
        "/",
        tags=["System"],
        response_model=ApplicationStatusResponse,
        summary='Identify the application',
        description=(
            'Returns a short application identifier without checking dependency connectivity. Use '
            '/health to inspect service availability.'
        ),
        responses=documented_responses(503, examples=[({'message': 'FastAPI Microblog Demo'}, 'Application identifier')]),
    )
    async def root() -> ApplicationStatusResponse:
        return ApplicationStatusResponse(message="FastAPI Microblog Demo")

    @app.get(
        "/health",
        tags=["System"],
        response_model=HealthResponse,
        summary='Check dependency health',
        description=(
            'Pings MongoDB and Redis and checks object storage; returns 503 if a dependency is '
            'unavailable.'
        ),
        responses=documented_responses(503, examples=[({'status': 'ok', 'database': 'ok', 'redis': 'ok', 'object_storage': 'ok'}, 'All dependencies available')]),
    )
    async def health(request: Request) -> HealthResponse:
        try:
            await get_resources(request).mongo.admin.command("ping")
            await get_resources(request).redis.ping()
            await check_storage(get_resources(request).s3, get_settings())
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="A required service is unavailable") from exc
        return HealthResponse(status="ok", database="ok", redis="ok", object_storage="ok")

    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000)
