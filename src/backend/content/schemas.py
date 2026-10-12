from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from backend.content.validation import validate_tiptap_document


class MicroPostCreate(BaseModel):
    text: str = Field(min_length=1, max_length=280)

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Post text cannot be empty")
        return value


class MicroPostResponse(BaseModel):
    id: str
    kind: Literal["micro_post"] = "micro_post"
    text: str
    author_id: str
    author_username: str
    author_display_name: str
    author_avatar_url: str | None
    created_at: datetime
    updated_at: datetime


class ArticleCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    summary: str = Field(default="", max_length=320)
    body: dict[str, Any]

    @field_validator("title")
    @classmethod
    def trim_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Title cannot be empty")
        return value

    @field_validator("summary")
    @classmethod
    def trim_summary(cls, value: str) -> str:
        return value.strip()

    @field_validator("body")
    @classmethod
    def validate_body(cls, value: dict[str, Any]) -> dict[str, Any]:
        validate_tiptap_document(value)
        return value


class ArticleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    summary: str | None = Field(default=None, max_length=320)
    body: dict[str, Any] | None = None

    @field_validator("title")
    @classmethod
    def trim_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Title cannot be empty")
        return value

    @field_validator("summary")
    @classmethod
    def trim_summary(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("body")
    @classmethod
    def validate_body(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is not None:
            validate_tiptap_document(value)
        return value


class ArticleResponse(BaseModel):
    id: str
    kind: Literal["article"] = "article"
    title: str
    summary: str
    body: dict[str, Any]
    status: Literal["draft", "published"]
    author_id: str
    author_username: str
    author_display_name: str
    author_avatar_url: str | None
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None


class FeedItem(BaseModel):
    id: str
    kind: Literal["micro_post", "article"]
    title: str | None = None
    text: str | None = None
    summary: str | None = None
    author_id: str
    author_username: str
    author_display_name: str
    author_avatar_url: str | None
    published_at: datetime


class FeedResponse(BaseModel):
    items: list[FeedItem]
    next_cursor: str | None
