from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from backend.content.validation import validate_tiptap_document


class MicroPostCreate(BaseModel):
    """Text for a public micro-post; whitespace-only values are rejected."""

    text: str = Field(min_length=1, max_length=280, examples=["A small idea worth sharing with the community."])

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Post text cannot be empty")
        return value


class MicroPostResponse(BaseModel):
    """Published micro-post with its public author card."""

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
    """Article draft whose body is a validated TipTap JSON document."""

    title: str = Field(min_length=1, max_length=160, examples=["Notes on building a reading habit"])
    summary: str = Field(default="", max_length=320, examples=["A few practical ideas for making time to read."])
    body: dict[str, Any] = Field(examples=[{"type": "doc", "content": [{"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "Start small"}]}, {"type": "paragraph", "content": [{"type": "text", "text": "Ten minutes a day is enough to begin."}]}]}])

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
    """Partial article update. The author can edit drafts and publications."""

    title: str | None = Field(default=None, min_length=1, max_length=160, examples=["An updated title"])
    summary: str | None = Field(default=None, max_length=320, examples=["An updated summary."])
    body: dict[str, Any] | None = Field(default=None, examples=[{"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Updated article text."}]}]}])

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
    """Article data. Drafts are only visible to their author."""

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
    """Discriminated feed item: inspect `kind` to read `text` or `title`."""

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
    """Chronological page. Pass `next_cursor` back to continue."""

    items: list[FeedItem]
    next_cursor: str | None
