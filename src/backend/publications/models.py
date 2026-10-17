"""Shared ownership and display-author fields for publication documents."""

from typing import Self

from beanie import PydanticObjectId
from pydantic import BaseModel, Field, model_validator


class PublicationAuthors(BaseModel):
    """Separate publication ownership from additional credited authors."""

    owner_id: PydanticObjectId = Field(description="Account controlling the publication and its private visibility.")
    featured_author_ids: list[PydanticObjectId] = Field(
        default_factory=list,
        description="Additional credited accounts in display order; excludes the owner and grants no access rights.",
    )

    @model_validator(mode="after")
    def validate_featured_authors(self) -> Self:
        """Reject duplicate featured authors and an owner repeated among them.

        :return: The validated publication with distinct owner and featured authors.
        """
        if len(set(self.featured_author_ids)) != len(self.featured_author_ids):
            raise ValueError("Featured author IDs must be unique")

        if self.owner_id in self.featured_author_ids:
            raise ValueError("The owner cannot be a featured author")

        return self

    @property
    def author_ids(self) -> list[PydanticObjectId]:
        """Combine the owner and featured authors in API display order.

        :return: A new list containing the owner followed by featured authors in stored order.
        """
        return [self.owner_id, *self.featured_author_ids]
