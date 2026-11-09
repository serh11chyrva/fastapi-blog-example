from datetime import datetime
from typing import Literal

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pymongo import ASCENDING, IndexModel

from backend.links.models import ProfileLink


class BadgePayload(BaseModel):
    """Versioned public display data shared by assignments of a badge."""

    label: str = Field(min_length=1, max_length=64, description="Public badge name.")
    description: str | None = Field(default=None, max_length=500, description="Public explanation of the badge.")
    background_color: str = Field(
        default="#f3f4f6",
        pattern=r"^#[0-9a-fA-F]{6}$",
        description="Badge background as a six-digit hex color.",
    )
    text_color: str = Field(
        default="#374151",
        pattern=r"^#[0-9a-fA-F]{6}$",
        description="Badge text as a six-digit hex color.",
    )
    icon_url: str | None = Field(
        default="/static/images/badges/star.svg",
        pattern=r"^/static/images/badges/[a-zA-Z0-9_-]+\.(svg|png|webp)$",
        description="Same-origin static badge icon URL, or null to display text only.",
    )
    icon_color: str | None = Field(
        default="#374151",
        pattern=r"^#[0-9a-fA-F]{6}$",
        description="Monochrome icon mask color; null preserves the image's original colors.",
    )


class BadgeDefinition(Document):
    """Shared badge catalog entry with display data and visibility policy."""

    version: Literal[2] = 2
    code: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    payload: BadgePayload
    can_disable: bool = True

    class Settings:
        """Beanie collection and index configuration for BadgeDefinition."""

        name = "badge_definitions"
        indexes = [IndexModel([("code", ASCENDING)], unique=True, name="badge_code_unique")]


class BadgeAssignment(BaseModel):
    """Embedded badge assignment with the account owner visibility preference."""

    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    assigned_at: datetime
    enabled: bool = True


class AvatarImage(BaseModel):
    """Storage metadata for one avatar image variant."""

    key: str
    content_type: str


class AvatarVariants(BaseModel):
    """Stored avatar variants, currently limited to the optional original image."""

    original: AvatarImage | None = None


class User(Document):
    """Account profile with versioned links, badge assignments, and edit revision."""

    email: str
    username: str
    display_name: str
    bio: str = ""
    location: str = ""
    banner: AvatarImage | None = None
    links: list[ProfileLink] = Field(default_factory=list, max_length=8)
    avatars: AvatarVariants = Field(default_factory=AvatarVariants)
    badges: list[BadgeAssignment] = Field(default_factory=list)
    revision: int = Field(default=0, ge=0)
    profile_schema_version: Literal[2] = 2
    created_at: datetime
    updated_at: datetime

    @field_validator("links")
    @classmethod
    def unique_link_ids(cls, links: list[ProfileLink]) -> list[ProfileLink]:
        """Reject duplicate embedded link identities within a profile.

        :param links: Embedded profile links to validate.
        :return: The original list of links with unique IDs.
        """
        if len({link.id for link in links}) != len(links):
            raise ValueError("Link IDs must be unique within a profile")

        return links

    @field_validator("badges")
    @classmethod
    def unique_badge_codes(cls, assignments: list[BadgeAssignment]) -> list[BadgeAssignment]:
        """Reject duplicate badge assignments within a profile.

        :param assignments: Embedded badge assignments to validate.
        :return: The original list of assignments with unique badge codes.
        """
        if len({badge.code for badge in assignments}) != len(assignments):
            raise ValueError("Each badge code may be assigned only once per profile")

        return assignments

    class Settings:
        """Beanie collection and index configuration for User."""

        name = "users"
        indexes = [
            IndexModel([("email", ASCENDING)], unique=True, name="users_email_unique"),
            IndexModel([("username", ASCENDING)], unique=True, name="users_username_unique"),
            IndexModel([("links.id", ASCENDING)], name="profile_links_by_id"),
            IndexModel([("avatars.original.key", ASCENDING)], name="users_avatar_original_key"),
            IndexModel([("banner.key", ASCENDING)], name="users_banner_key"),
        ]


class Follow(Document):
    """Directed follower-to-followee relationship between two accounts."""

    follower_id: PydanticObjectId
    followee_id: PydanticObjectId
    created_at: datetime

    class Settings:
        """Beanie collection and index configuration for Follow."""

        name = "follows"
        indexes = [
            IndexModel(
                [("follower_id", ASCENDING), ("followee_id", ASCENDING)],
                unique=True,
                name="follow_pair_unique",
            ),
            IndexModel(
                [("followee_id", ASCENDING), ("created_at", -1), ("_id", -1)],
                name="followers_page",
            ),
            IndexModel(
                [("follower_id", ASCENDING), ("created_at", -1), ("_id", -1)],
                name="following_page",
            ),
        ]
