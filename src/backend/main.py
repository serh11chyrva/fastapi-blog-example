import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from loguru import logger
from pymongo import AsyncMongoClient
from pymongo.errors import PyMongoError
from redis.asyncio import Redis
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from backend.api.docs import (
    API_DESCRIPTION,
    API_SUMMARY,
    API_TITLE,
    API_VERSION,
    OPENAPI_TAGS,
    OPENAPI_URL,
    add_api_reference,
    configure_openapi,
)
from backend.api.router import router
from backend.articles.migrations import ensure_public_share_ids as ensure_article_share_ids
from backend.articles.scheduler import run_publication_scheduler
from backend.auth.presentation import open_geoip_database
from backend.core.config import get_settings
from backend.core.database import DOCUMENT_MODELS
from backend.core.errors import ApplicationError
from backend.core.resources import AppResources
from backend.posts.migrations import ensure_public_share_ids as ensure_post_share_ids
from backend.profiles.migrations import ensure_profile_schema
from backend.storage.cleanup import run_storage_cleanup
from backend.storage.s3 import check_storage, create_s3_client


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize application resources and stop background workers on shutdown.

    :param app: FastAPI application receiving configuration or lifecycle resources.
    :return: An asynchronous lifespan context for the application.
    """
    settings = get_settings()
    mongo_client = AsyncMongoClient(settings.mongodb_url, serverSelectionTimeoutMS=8_000, tz_aware=True)
    redis_client = Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=3)
    s3_client = create_s3_client(settings)
    s3_public_client = create_s3_client(settings, public=True)
    geoip_reader = open_geoip_database(settings.geoip_city_db_path)
    app.state.resources = AppResources(mongo_client, redis_client, s3_client, s3_public_client, geoip_reader)
    scheduler_task: asyncio.Task[None] | None = None
    cleanup_task: asyncio.Task[None] | None = None

    try:
        await mongo_client.admin.command("ping")
        from beanie import init_beanie

        await init_beanie(
            database=mongo_client[settings.mongodb_database],
            document_models=DOCUMENT_MODELS,
        )
        await ensure_profile_schema()
        await ensure_post_share_ids()
        await ensure_article_share_ids()
        await redis_client.ping()
        await check_storage(s3_client, settings)
        await redis_client.incr("feed:public:version")
        cleanup_task = asyncio.create_task(run_storage_cleanup(s3_client), name="image-storage-cleanup")
        scheduler_task = asyncio.create_task(
            run_publication_scheduler(mongo_client, redis_client),
            name="scheduled-publications",
        )
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

        if geoip_reader is not None:
            geoip_reader.close()

        s3_client.close()
        s3_public_client.close()
        await mongo_client.close()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    :return: The configured FastAPI application.
    """
    app = FastAPI(
        title=API_TITLE,
        version=API_VERSION,
        summary=API_SUMMARY,
        description=API_DESCRIPTION,
        openapi_tags=OPENAPI_TAGS,
        docs_url=None,
        redoc_url=None,
        openapi_url=OPENAPI_URL,
        lifespan=lifespan,
    )
    app.include_router(router)

    configure_openapi(app)

    add_api_reference(app)

    @app.exception_handler(ApplicationError)
    async def application_error(request: Request, exc: ApplicationError) -> JSONResponse:
        """Translate a domain error into the public error envelope.

        :param request: Incoming HTTP request and its application state.
        :param exc: Exception raised while processing the request.
        :return: A JSON response with the domain error status and detail.
        """
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(PyMongoError)
    async def database_error(request: Request, exc: PyMongoError) -> JSONResponse:
        """Log a database failure and return a dependency error.

        :param request: Incoming HTTP request and its application state.
        :param exc: Exception raised while processing the request.
        :return: A JSON response with status 503.
        """
        logger.opt(exception=exc).error("Database operation failed")

        return JSONResponse(
            status_code=503,
            content={"detail": "Database is unavailable; reload before retrying"},
        )

    @app.middleware("http")
    async def enforce_same_origin(request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Require the configured origin for mutating versioned API requests.

        :param request: Incoming HTTP request and its application state.
        :param call_next: Callable that dispatches the request to the next HTTP handler.
        :return: The downstream response or an origin rejection response.
        """
        if request.url.path.startswith("/api/v1/") and request.method in {
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
        }:
            origin = request.headers.get("origin", "").rstrip("/")

            if origin != get_settings().app_origin:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Cross-origin request rejected"},
                )

        return await call_next(request)

    return app


app = create_app()


def main() -> None:
    """Start the backend HTTP server.

    :return: None.
    """
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000)
