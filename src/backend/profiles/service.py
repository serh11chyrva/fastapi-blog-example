"""Audited profile mutations with explicit revision and ownership checks."""

from datetime import UTC, datetime

from beanie import PydanticObjectId
from pymongo.errors import DuplicateKeyError

from backend.audit.context import AuditContext
from backend.audit.service import record_audit
from backend.core.errors import (
    BadRequest,
    Conflict,
    Forbidden,
    InvalidOperation,
    NotFound,
)
from backend.core.resources import AppResources
from backend.core.transactions import transaction
from backend.links.models import ProfileLink
from backend.profiles.models import BadgeDefinition, Follow, User
from backend.profiles.queries import ProfileQueries
from backend.profiles.schemas import BadgePreferenceUpdate, LinkInput, ProfileUpdate


class ProfileService:
    """Audited profile and follow mutations with revision and ownership checks."""

    def __init__(self, resources: AppResources, audit: AuditContext) -> None:
        """Initialize profile mutations with infrastructure and audit metadata.

        :param resources: Application-owned database, cache, and storage clients.
        :param audit: Request metadata attached to audited operations.
        :return: None.
        """
        self.resources = resources
        self.audit = audit

    @staticmethod
    def replace_links(existing: list[ProfileLink], inputs: list[LinkInput]) -> list[ProfileLink]:
        """Replace links while retaining explicit IDs and unique exact-URL matches.

        Foreign or duplicate IDs and ambiguous legacy matches are rejected.
        New links receive fresh identities; omitted links are removed.

        :param existing: Currently persisted profile links whose identities may be
            retained.
        :param inputs: Requested replacement links in their desired display order.
        :return: Replacement links with retained or newly generated identities.
        """
        existing_ids = {link.id for link in existing}
        supplied = [str(link.id) for link in inputs if link.id is not None]

        if len(supplied) != len(set(supplied)) or any(link_id not in existing_ids for link_id in supplied):
            raise InvalidOperation("Link IDs must be unique and belong to your current profile")

        used = set(supplied)
        result = []

        for item in inputs:
            data = item.model_dump(mode="json", exclude_none=True)

            if item.id is None:
                matches = [link for link in existing if link.id not in used and link.url == item.url]

                if len(matches) > 1:
                    raise InvalidOperation("Ambiguous existing link; supply its ID")

                if matches:
                    data["id"] = matches[0].id
                    used.add(matches[0].id)

            result.append(ProfileLink(**data))

        return result

    async def update(
        self,
        user_id: PydanticObjectId,
        payload: ProfileUpdate | BadgePreferenceUpdate,
        badge_code: str | None = None,
    ) -> User:
        """Apply profile or badge changes using an audited revision check.

        :param user_id: MongoDB identifier of the user account.
        :param payload: Validated request data for the operation.
        :param badge_code: Assigned badge code when updating badge visibility.
        :return: The updated user document.
        """
        client = self.resources.mongo

        try:
            async with transaction(client) as db_session:
                user = await User.get(user_id, session=db_session)

                if user is None:
                    raise NotFound("Profile not found")

                if user.revision != payload.revision:
                    raise Conflict("Profile changed; reload your profile before saving")

                if isinstance(payload, BadgePreferenceUpdate):
                    badge = next((item for item in user.badges if item.code == badge_code), None)
                    definition = await BadgeDefinition.find_one(BadgeDefinition.code == badge_code, session=db_session)

                    if badge is None or definition is None:
                        raise NotFound("Badge assignment not found")

                    if not payload.enabled and not definition.can_disable:
                        raise Forbidden("This badge cannot be disabled")

                    badge.enabled = payload.enabled
                    changes = {"badges": [item.model_dump() for item in user.badges]}
                    action = "BADGE_VISIBILITY_UPDATED"
                else:
                    changes = payload.model_dump(exclude_unset=True, exclude={"revision"})
                    changes = {field: value for field, value in changes.items() if value is not None}

                    if payload.links is not None:
                        changes["links"] = [
                            link.model_dump(mode="json") for link in self.replace_links(user.links, payload.links)
                        ]

                    action = "PROFILE_UPDATED"

                fields = sorted(changes)
                changes["updated_at"] = datetime.now(UTC)
                result = await User.find_one({"_id": user_id, "revision": payload.revision}).update(
                    {"$set": changes, "$inc": {"revision": 1}},
                    session=db_session,
                )

                if result.matched_count != 1:
                    raise Conflict("Profile changed; reload your profile before saving")

                await record_audit(
                    self.audit,
                    action,
                    actor_id=user_id,
                    target_type="user",
                    target_id=str(user_id),
                    metadata={
                        "fields": fields,
                        **({"badge_code": badge_code} if badge_code else {}),
                    },
                    session=db_session,
                )
                updated = await User.get(user_id, session=db_session)

                if updated is None:
                    raise Conflict("Profile changed; reload your profile before saving")
        except Conflict as exc:
            raise Conflict("Profile changed; reload your profile before saving") from exc

        return updated

    async def follow(self, owner: User, username: str) -> None:
        """Create a follow relationship and audit it if it does not exist.

        :param owner: Authenticated account owning or initiating the operation.
        :param username: Public profile handle, optionally prefixed with @.
        :return: None.
        """
        target = await ProfileQueries().by_username(username)

        if target.id == owner.id:
            raise BadRequest("You cannot follow yourself")

        try:
            async with transaction(self.resources.mongo) as session:
                existing = await Follow.find_one(
                    Follow.follower_id == owner.id,
                    Follow.followee_id == target.id,
                    session=session,
                )

                if existing is None:
                    await Follow(
                        follower_id=owner.id,
                        followee_id=target.id,
                        created_at=datetime.now(UTC),
                    ).insert(session=session)
                    await record_audit(
                        self.audit,
                        "USER_FOLLOWED",
                        actor_id=owner.id,
                        target_type="user",
                        target_id=str(target.id),
                        session=session,
                    )
        except DuplicateKeyError:
            return

    async def unfollow(self, owner: User, username: str) -> None:
        """Remove an existing follow relationship and record the change.

        :param owner: Authenticated account owning or initiating the operation.
        :param username: Public profile handle, optionally prefixed with @.
        :return: None.
        """
        target = await ProfileQueries().by_username(username)

        async with transaction(self.resources.mongo) as session:
            existing = await Follow.find_one(
                Follow.follower_id == owner.id,
                Follow.followee_id == target.id,
                session=session,
            )

            if existing is not None:
                await existing.delete(session=session)
                await record_audit(
                    self.audit,
                    "USER_UNFOLLOWED",
                    actor_id=owner.id,
                    target_type="user",
                    target_id=str(target.id),
                    session=session,
                )
