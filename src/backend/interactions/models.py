"""Unique per-account publication interactions and chronological lookup indexes."""

from datetime import datetime
from typing import Literal, Self

from beanie import Document, PydanticObjectId
from pydantic import model_validator
from pymongo import ASCENDING, DESCENDING, IndexModel

type InteractionKind = Literal["like", "save", "repost"]


class PublicationInteraction(Document):
    """Store one like, private save, or public repost per actor and publication."""

    publication_kind: Literal["micro_post", "article"]
    publication_id: PydanticObjectId
    user_id: PydanticObjectId
    action: InteractionKind
    created_at: datetime

    @model_validator(mode="after")
    def reject_article_repost(self) -> Self:
        """Keep article reposts out of persisted interactions.

        :return: The validated interaction, allowing reposts only for micro-posts.
        """
        if self.action == "repost" and self.publication_kind != "micro_post":
            raise ValueError("Only micro-posts can be reposted")

        return self

    class Settings:
        """Unique actor/action edges and indexes for counts, private lists, and repost feeds."""

        name = "publication_interactions"
        indexes = [
            IndexModel(
                [
                    ("publication_kind", ASCENDING),
                    ("publication_id", ASCENDING),
                    ("action", ASCENDING),
                    ("user_id", ASCENDING),
                ],
                unique=True,
                name="interaction_actor_unique",
            ),
            IndexModel(
                [("user_id", ASCENDING), ("action", ASCENDING), ("_id", DESCENDING)],
                name="interaction_account_page",
            ),
            IndexModel(
                [("action", ASCENDING), ("created_at", DESCENDING), ("_id", DESCENDING)],
                name="interaction_repost_feed",
            ),
            IndexModel(
                [("action", ASCENDING), ("user_id", ASCENDING), ("created_at", DESCENDING), ("_id", DESCENDING)],
                name="interaction_following_reposts",
            ),
        ]
