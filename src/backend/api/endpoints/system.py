"""Application identification and dependency health endpoints."""

from fastapi import APIRouter, HTTPException, Request, status

from backend.api.metadata import documented_responses
from backend.api.schemas import ApplicationStatusResponse, HealthResponse
from backend.core.config import get_settings
from backend.core.resources import get_resources
from backend.storage.s3 import check_storage

router = APIRouter()


@router.get(
    "/",
    tags=["System"],
    response_model=ApplicationStatusResponse,
    summary="Identify the application",
    description=(
        "Returns a short application identifier without checking dependency connectivity. Use "
        "/health to inspect service availability."
    ),
    responses=documented_responses(
        503,
        examples=[({"message": "FastAPI Microblog Demo"}, "Application identifier")],
    ),
)
async def root() -> ApplicationStatusResponse:
    """Return the application identifier without checking dependencies.

    :return: The application status response.
    """
    return ApplicationStatusResponse(message="FastAPI Microblog Demo")


@router.get(
    "/health",
    tags=["System"],
    response_model=HealthResponse,
    summary="Check dependency health",
    description=("Pings MongoDB and Redis and checks object storage; returns 503 if a dependency is unavailable."),
    responses=documented_responses(
        503,
        examples=[
            (
                {
                    "status": "ok",
                    "database": "ok",
                    "redis": "ok",
                    "object_storage": "ok",
                },
                "All dependencies available",
            )
        ],
    ),
)
async def health(request: Request) -> HealthResponse:
    """Check MongoDB, Redis, and the required object storage buckets.

    :param request: Incoming HTTP request and its application state.
    :return: A status response reporting that all dependencies are available.
    :raises HTTPException: If a dependency check fails, with HTTP status 503.
    """
    try:
        await get_resources(request).mongo.admin.command("ping")
        await get_resources(request).redis.ping()
        await check_storage(get_resources(request).s3, get_settings())
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="A required service is unavailable",
        ) from exc

    return HealthResponse(status="ok", database="ok", redis="ok", object_storage="ok")
