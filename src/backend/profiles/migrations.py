from typing import Any
from uuid import NAMESPACE_URL, uuid5

from beanie import PydanticObjectId
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from backend.links.models import ProfileLink
from backend.profiles.models import BadgeAssignment, BadgeDefinition, BadgePayload, User


class LegacyProfile(BaseModel):
    id: PydanticObjectId = Field(alias="_id")
    username: str
    links: list[dict[str, Any]] = Field(default_factory=list)
    badges: list[dict[str, Any]] = Field(default_factory=list)
    revision: int = 0
    profile_schema_version: int | None = None


async def ensure_profile_schema() -> None:
    """Persist link identities and split legacy badge definitions from assignments once."""
    async for legacy in User.find({"profile_schema_version": {"$ne": 2}}).sort("_id").project(LegacyProfile):
        if legacy.profile_schema_version not in {None, 1}:
            raise ValueError(f"Unsupported profile storage version: {legacy.profile_schema_version}")
        links = [ProfileLink(**{
            **link,
            "id": link.get("id") or str(uuid5(NAMESPACE_URL, f"profile:{legacy.username}:{index}:{link['url']}")),
        }) for index, link in enumerate(legacy.links)]
        if len(links) > 8:
            raise ValueError("Legacy profile has more than eight links")
        User.unique_link_ids(links)
        assignments = []
        for badge in legacy.badges:
            if badge.get("version", 1) != 1:
                raise ValueError(f"Unsupported legacy badge version: {badge['version']}")
            definition = await BadgeDefinition.find_one(BadgeDefinition.code == badge["code"])
            if definition is None:
                payload = {**badge.get("payload", {}), "label": badge["label"], "description": badge.get("description")}
                try:
                    await BadgeDefinition(code=badge["code"], payload=BadgePayload(**payload), can_disable=badge.get("can_disable", True)).insert()
                except DuplicateKeyError:
                    pass
            assignments.append(BadgeAssignment(code=badge["code"], assigned_at=badge["assigned_at"], enabled=badge.get("enabled", True)))
        User.unique_badge_codes(assignments)
        await User.find_one({"_id": legacy.id, "profile_schema_version": {"$ne": 2}}).update({"$set": {
            "links": [link.model_dump(mode="json") for link in links],
            "badges": [badge.model_dump() for badge in assignments],
            "revision": legacy.revision,
            "profile_schema_version": 2,
        }})
