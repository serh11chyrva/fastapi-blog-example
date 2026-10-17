"""Response schemas for application status and dependency health."""

from pydantic import BaseModel, ConfigDict, Field


class ApplicationStatusResponse(BaseModel):
    """Application identifier returned by the root endpoint."""

    model_config = ConfigDict(
        title="Application status",
        json_schema_extra={"examples": [{"message": "FastAPI Microblog Demo"}]},
    )

    message: str = Field(
        description="Human-readable application identifier.",
        examples=["FastAPI Microblog Demo"],
    )


class HealthResponse(BaseModel):
    """Successful connectivity checks for all required dependencies."""

    model_config = ConfigDict(
        title="Dependency health",
        json_schema_extra={
            "examples": [
                {
                    "status": "ok",
                    "database": "ok",
                    "redis": "ok",
                    "object_storage": "ok",
                }
            ]
        },
    )

    status: str = Field(
        description="Overall health; ok means every required dependency check passed.",
        examples=["ok"],
    )
    database: str = Field(description="MongoDB ping result.", examples=["ok"])
    redis: str = Field(description="Redis ping result.", examples=["ok"])
    object_storage: str = Field(description="Object storage bucket availability result.", examples=["ok"])
