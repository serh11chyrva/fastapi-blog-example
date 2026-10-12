from datetime import datetime

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field
from pymongo import ASCENDING, IndexModel


class BadgeAssignment(BaseModel):
    code: str
    label: str
    description: str | None = None
    assigned_at: datetime


class User(Document):
    email: str
    username: str
    display_name: str
    bio: str = ""
    links: list[dict[str, str]] = Field(default_factory=list)
    avatar_key: str | None = None
    avatar_content_type: str | None = None
    badges: list[BadgeAssignment] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

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
