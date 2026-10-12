from functools import lru_cache
from os import environ

from pydantic import BaseModel, Field


class Settings(BaseModel):
    mongodb_url: str = Field(default_factory=lambda: environ.get("MONGODB_URL", "mongodb://localhost:27017/?replicaSet=rs0"))
    mongodb_database: str = Field(default_factory=lambda: environ.get("MONGODB_DATABASE", "blog"))
    redis_url: str = Field(default_factory=lambda: environ.get("REDIS_URL", "redis://localhost:6379/0"))
    app_origin: str = Field(default_factory=lambda: environ.get("APP_ORIGIN", "http://localhost:8080").rstrip("/"))
    session_cookie_name: str = Field(default_factory=lambda: environ.get("SESSION_COOKIE_NAME", "blog_session"))
    session_cookie_secure: bool = Field(default_factory=lambda: environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true")
    session_idle_days: int = Field(default_factory=lambda: int(environ.get("SESSION_IDLE_DAYS", "7")))
    session_absolute_days: int = Field(default_factory=lambda: int(environ.get("SESSION_ABSOLUTE_DAYS", "30")))
    s3_endpoint_url: str = Field(default_factory=lambda: environ.get("S3_ENDPOINT_URL", "http://garage:3900"))
    s3_region: str = Field(default_factory=lambda: environ.get("S3_REGION", "garage"))
    s3_access_key: str = Field(default_factory=lambda: environ.get("GARAGE_ACCESS_KEY", ""))
    s3_secret_key: str = Field(default_factory=lambda: environ.get("GARAGE_SECRET_KEY", ""))
    avatar_bucket: str = Field(default_factory=lambda: environ.get("AVATAR_BUCKET", "blog-avatars"))
    avatar_max_bytes: int = Field(default_factory=lambda: int(environ.get("AVATAR_MAX_BYTES", "5242880")))
    article_thumbnail_max_bytes: int = Field(default_factory=lambda: int(environ.get("ARTICLE_THUMBNAIL_MAX_BYTES", "10485760")))
    publication_image_max_bytes: int = Field(default_factory=lambda: int(environ.get("PUBLICATION_IMAGE_MAX_BYTES", "5242880")))
    demo_password: str = Field(default_factory=lambda: environ.get("DEMO_PASSWORD", "DemoPassword123!"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
