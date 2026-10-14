from datetime import UTC, datetime

from beanie import PydanticObjectId
from fastapi import HTTPException, Request
from pymongo.errors import OperationFailure

from backend.links.platforms import detect_platform
from backend.core.audit import record_audit
from backend.profiles.models import BadgeDefinition, ProfileLink, User
from backend.profiles.repository import ProfileRepository
from backend.profiles.schemas import (
    BadgePreferenceUpdate,
    BadgeResponse,
    LinkInput,
    LinkResponse,
    OwnProfileResponse,
    OwnerBadgeResponse,
    ProfileResponse,
    ProfileUpdate,
    ProfileUserResponse,
)


class ProfileService:
    def __init__(self, repository: type[ProfileRepository] = ProfileRepository) -> None:
        self.repository = repository

    @staticmethod
    def avatar_url(user: User) -> str | None:
        if not user.avatar_key:
            return None
        return f"/static/images/avatars/{user.avatar_key.rsplit('/', 1)[-1]}"

    async def response(self, user: User, viewer_id: PydanticObjectId | None,
                       definitions: dict[str, BadgeDefinition] | None = None) -> ProfileResponse:
        follower_count, following_count = await self.repository.counts(user.id)
        if definitions is None:
            definitions = await self.badge_definitions(user)
        return ProfileResponse(
            id=str(user.id),
            username=user.username,
            display_name=user.display_name,
            bio=user.bio,
            links=[self.link_response(link) for link in user.links],
            avatar_url=self.avatar_url(user),
            badges=[BadgeResponse(version=definitions[badge.code].version, code=badge.code, payload=definitions[badge.code].payload)
                    for badge in user.badges if badge.enabled],
            follower_count=follower_count,
            following_count=following_count,
            is_following=await self.repository.is_following(viewer_id, user.id),
        )

    @staticmethod
    async def badge_definitions(user: User) -> dict[str, BadgeDefinition]:
        definitions = await BadgeDefinition.find({"code": {"$in": [badge.code for badge in user.badges]}}).to_list()
        by_code = {definition.code: definition for definition in definitions}
        if any(badge.code not in by_code for badge in user.badges):
            raise HTTPException(503, "Badge definition is unavailable")
        return by_code

    async def own_response(self, user: User) -> OwnProfileResponse:
        definitions = await self.badge_definitions(user)
        public = await self.response(user, user.id, definitions)
        return OwnProfileResponse(
            **public.model_dump(exclude={"badges"}), revision=user.revision,
            badges=[OwnerBadgeResponse(
                version=definitions[badge.code].version, code=badge.code, payload=definitions[badge.code].payload,
                assigned_at=badge.assigned_at, preferences={"enabled": badge.enabled},
                permissions={"can_disable": definitions[badge.code].can_disable},
            ) for badge in user.badges],
        )

    @staticmethod
    def replace_links(existing: list[ProfileLink], inputs: list[LinkInput]) -> list[ProfileLink]:
        """Preserve explicitly selected IDs and unambiguous legacy URL matches."""
        existing_ids = {link.id for link in existing}
        supplied = [str(link.id) for link in inputs if link.id is not None]
        if len(supplied) != len(set(supplied)) or any(link_id not in existing_ids for link_id in supplied):
            raise HTTPException(422, "Link IDs must be unique and belong to your current profile")
        used = set(supplied)
        result = []
        for item in inputs:
            data = item.model_dump(mode="json", exclude_none=True)
            if item.id is None:
                matches = [link for link in existing if link.id not in used and link.url == item.url]
                if len(matches) > 1:
                    raise HTTPException(422, "Ambiguous existing link; supply its ID")
                if matches:
                    data["id"] = matches[0].id
                    used.add(matches[0].id)
            result.append(ProfileLink(**data))
        return result

    async def update(self, request: Request, user_id: PydanticObjectId, payload: ProfileUpdate | BadgePreferenceUpdate,
                     badge_code: str | None = None) -> OwnProfileResponse:
        client = request.app.state.mongo_client
        try:
            async with client.start_session() as db_session:
                async with await db_session.start_transaction():
                    user = await User.get(user_id, session=db_session)
                    if user is None:
                        raise HTTPException(404, "Profile not found")
                    if user.revision != payload.revision:
                        raise HTTPException(409, "Profile changed; reload your profile before saving")
                    if isinstance(payload, BadgePreferenceUpdate):
                        badge = next((item for item in user.badges if item.code == badge_code), None)
                        definition = await BadgeDefinition.find_one(BadgeDefinition.code == badge_code, session=db_session)
                        if badge is None or definition is None:
                            raise HTTPException(404, "Badge assignment not found")
                        if not payload.enabled and not definition.can_disable:
                            raise HTTPException(403, "This badge cannot be disabled")
                        badge.enabled = payload.enabled
                        changes = {"badges": [item.model_dump() for item in user.badges]}
                        action = "BADGE_VISIBILITY_UPDATED"
                    else:
                        changes = payload.model_dump(exclude_unset=True, exclude={"revision"})
                        changes = {field: value for field, value in changes.items() if value is not None}
                        if payload.links is not None:
                            changes["links"] = [link.model_dump(mode="json") for link in self.replace_links(user.links, payload.links)]
                        action = "PROFILE_UPDATED"
                    fields = sorted(changes)
                    changes["updated_at"] = datetime.now(UTC)
                    result = await User.find_one({"_id": user_id, "revision": payload.revision}).update(
                        {"$set": changes, "$inc": {"revision": 1}}, session=db_session,
                    )
                    if result.matched_count != 1:
                        raise HTTPException(409, "Profile changed; reload your profile before saving")
                    await record_audit(request, action, actor_id=user_id, target_type="user", target_id=str(user_id),
                                       metadata={"fields": fields, **({"badge_code": badge_code} if badge_code else {})}, session=db_session)
                    updated = await User.get(user_id, session=db_session)
                    if updated is None:
                        raise HTTPException(409, "Profile changed; reload your profile before saving")
        except OperationFailure as exc:
            if exc.code == 112 or exc.has_error_label("TransientTransactionError"):
                raise HTTPException(409, "Profile changed; reload your profile before saving") from exc
            raise
        return await self.own_response(updated)

    @staticmethod
    def link_response(link: ProfileLink) -> LinkResponse:
        return LinkResponse(
            **link.model_dump(),
            platform=detect_platform(link.url),
            redirect_url=f"/api/v1/links/{link.id}/redirect",
        )

    def user_card(self, user: User) -> ProfileUserResponse:
        return ProfileUserResponse(
            id=str(user.id),
            username=user.username,
            display_name=user.display_name,
            avatar_url=self.avatar_url(user),
        )
