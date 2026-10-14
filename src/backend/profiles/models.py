from datetime import datetime
from typing import Literal
from uuid import NAMESPACE_URL, uuid4, uuid5

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field, ValidationInfo, field_validator
from pymongo import ASCENDING, IndexModel


class ProfileLink(BaseModel):
    version: Literal[1] = 1
    id: str = Field(default_factory=lambda: str(uuid4()))
    label: str
    url: str


class BadgePayload(BaseModel):
    background_color: str = Field(default="#f3f4f6", pattern=r"^#[0-9a-fA-F]{6}$", description="Badge background as a six-digit hex color.")
    text_color: str = Field(default="#374151", pattern=r"^#[0-9a-fA-F]{6}$", description="Badge text as a six-digit hex color.")
    icon_url: str | None = Field(default="/static/images/badges/star.svg", pattern=r"^/static/images/badges/[a-zA-Z0-9_-]+\.(svg|png|webp)$", description="Same-origin static badge icon URL, or null to display text only.")


class BadgeAssignment(BaseModel):
    version: Literal[1] = 1
    code: str
    label: str
    description: str | None = None
    assigned_at: datetime
    enabled: bool = True
    can_disable: bool = True
    payload: BadgePayload = Field(default_factory=BadgePayload)


class User(Document):
    email: str
    username: str
    display_name: str
    bio: str = ""
    links: list[ProfileLink] = Field(default_factory=list)
    avatar_key: str | None = None
    avatar_content_type: str | None = None
    badges: list[BadgeAssignment] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @field_validator("links", mode="before")
    @classmethod
    def upgrade_legacy_links(cls, value: list, info: ValidationInfo) -> list:
        """Give legacy links deterministic IDs until the next profile write persists them."""
        return [
            {**link, "id": str(uuid5(NAMESPACE_URL, f"profile:{info.data.get('username', '')}:{index}:{link['url']}"))}
            if isinstance(link, dict) and "id" not in link else link
            for index, link in enumerate(value)
        ]

    class Settings:
        name = "users"
        indexes = [
            IndexModel([("email", ASCENDING)], unique=True, name="users_email_unique"),
            IndexModel([("username", ASCENDING)], unique=True, name="users_username_unique"),
        ]


class Follow(Document):
    follower_id: PydanticObjectId
    followee_id: PydanticObjectId
    created_at: datetime

    class Settings:
        name = "follows"
        indexes = [
            IndexModel([("follower_id", ASCENDING), ("followee_id", ASCENDING)], unique=True, name="follow_pair_unique"),
            IndexModel([("followee_id", ASCENDING), ("created_at", ASCENDING)], name="followers_by_time"),
            IndexModel([("follower_id", ASCENDING), ("created_at", ASCENDING)], name="following_by_time"),
        ]
