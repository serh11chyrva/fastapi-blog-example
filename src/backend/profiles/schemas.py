from datetime import datetime
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator


class LinkInput(BaseModel):
    label: str = Field(min_length=1, max_length=32)
    url: str = Field(min_length=8, max_length=500)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme not in {"https", "http"} or not parsed.netloc:
            raise ValueError("Links must use an http or https URL")
        return value


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=64)
    bio: str | None = Field(default=None, max_length=280)
    links: list[LinkInput] | None = Field(default=None, max_length=8)

    @field_validator("display_name")
    @classmethod
    def trim_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Display name cannot be empty")
        return value


class BadgeResponse(BaseModel):
    code: str
    label: str
    description: str | None
    assigned_at: datetime


class ProfileResponse(BaseModel):
    id: str
    username: str
    display_name: str
    bio: str
    links: list[LinkInput]
    avatar_url: str | None
    badges: list[BadgeResponse]
    follower_count: int
    following_count: int
    is_following: bool


class ProfileUserResponse(BaseModel):
    id: str
    username: str
    display_name: str
    avatar_url: str | None
