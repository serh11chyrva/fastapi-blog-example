from functools import lru_cache
from os import environ

from pydantic import BaseModel, Field


def session_cookie_name() -> str:
    return environ.get("SESSION_COOKIE_NAME", "session_token")


class Settings(BaseModel):
    mongodb_url: str = Field(
        default_factory=lambda: environ.get("MONGODB_URL", ""),
        min_length=1,
        validate_default=True,
        description="Required MongoDB connection string from MONGODB_URL, such as an Atlas SRV URI.",
    )
    mongodb_database: str = Field(default_factory=lambda: environ.get("MONGODB_DATABASE", "blog"))
    redis_url: str = Field(default_factory=lambda: environ.get("REDIS_URL", "redis://localhost:6379/0"))
    app_origin: str = Field(default_factory=lambda: environ.get("APP_ORIGIN", "http://localhost:8080").rstrip("/"))
    session_cookie_name: str = Field(default_factory=session_cookie_name)
    session_cookie_secure: bool = Field(default_factory=lambda: environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true")
    session_idle_days: int = Field(default_factory=lambda: int(environ.get("SESSION_IDLE_DAYS", "7")))
    session_absolute_days: int = Field(default_factory=lambda: int(environ.get("SESSION_ABSOLUTE_DAYS", "30")))
    s3_endpoint_url: str = Field(default_factory=lambda: environ.get("S3_ENDPOINT_URL", "http://garage:3900"))
    s3_public_endpoint_url: str = Field(default_factory=lambda: environ.get("S3_PUBLIC_ENDPOINT_URL", "http://localhost:3900").rstrip("/"))
    s3_region: str = Field(default_factory=lambda: environ.get("S3_REGION", "garage"))
    s3_access_key: str = Field(default_factory=lambda: environ.get("GARAGE_ACCESS_KEY", ""))
    s3_secret_key: str = Field(default_factory=lambda: environ.get("GARAGE_SECRET_KEY", ""))
    avatar_bucket: str = "blog-avatars"
    publication_bucket: str = "blog-publications"
    upload_expiry_seconds: int = 600
    storage_cors_origins: list[str] = Field(default_factory=lambda: [item.strip().rstrip("/") for item in environ.get("STORAGE_CORS_ORIGINS", "http://localhost:8080,http://localhost:5173").split(",") if item.strip()])
    avatar_max_bytes: int = 5 * 1024 * 1024
    article_thumbnail_max_bytes: int = 10 * 1024 * 1024
    publication_image_max_bytes: int = 5 * 1024 * 1024
    demo_password: str = Field(default_factory=lambda: environ.get("DEMO_PASSWORD", "DemoPassword123!"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
