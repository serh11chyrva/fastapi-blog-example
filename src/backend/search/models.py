"""Rebuildable cross-publication search data, independent of canonical content."""

from datetime import datetime
from typing import Literal

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, IndexModel


class SearchPublication(Document):
    """One searchable projection per source post, reply, or published article."""

    source_kind: Literal["micro_post", "article"]
    source_id: PydanticObjectId
    title: str = ""
    text: str
    hashtags: list[str] = Field(default_factory=list)
    published_at: datetime

    class Settings:
        """Configure projection identities; Atlas indexes are managed explicitly."""

        name = "search_publications"
        indexes = [IndexModel(
            [("source_kind", ASCENDING), ("source_id", ASCENDING)], unique=True, name="search_source_unique",
        )]
