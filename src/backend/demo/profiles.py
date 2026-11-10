"""Demo accounts with varied profile settings, links, badges, and generated profile images."""

from datetime import datetime

from backend.audit.models import AuditEvent
from backend.audit.service import record_audit
from backend.auth.models import AuthIdentity
from backend.auth.security import hash_password_async
from backend.core.config import get_settings
from backend.core.resources import AppResources
from backend.core.transactions import transaction
from backend.demo.common import DEMO_AUDIT, demo_id, insert_fixture
from backend.demo.media import ensure_image
from backend.links.models import ProfileLink
from backend.profiles.models import AvatarImage, BadgeAssignment, BadgeDefinition, BadgePayload, User

DEMO_USERS = [
    ("alice", "Alice Morgan", "A writer interested in thoughtful technology."),
    ("ben", "Ben Carter", "Building small things and sharing what I learn."),
    ("casey", "Casey Rivera", "Stories, books, and notes from everyday life."),
    ("dana", "Dana Brooks", "Designing calm interfaces and accessible reading experiences."),
    ("elena", "Elena Park", "Urban walks, landscape photography, and slow weekends."),
    ("farah", "Farah Khan", "Explaining software through small, practical experiments."),
    ("noah", "Noah Reed", ""),
]


DESIGN_LOCATIONS = {
    "alice": "Kyiv, Ukraine",
    "ben": "Bristol, United Kingdom",
    "dana": "Amsterdam, Netherlands",
    "elena": "Vancouver, Canada",
}
BANNER_PALETTES = {"alice": 0, "dana": 3}
DESIGN_SEEDED = "DEMO_PROFILE_DESIGN_SEEDED"


async def seed_profiles(resources: AppResources, now: datetime) -> dict[str, User]:
    """Add demo identities and fill missing presentation fixtures without resetting owner edits or passwords.

    :param resources: Application infrastructure used for transactional writes and image storage.
    :param now: Timezone-aware seed run timestamp.
    :return: Demo users indexed by public username.
    """
    for index, (code, label, color, mandatory) in enumerate([
        ("early-reader", "Early Reader", "#e9eef4", False),
        ("community-guide", "Community Guide", "#dceade", True),
        ("workshop-member", "Workshop Member", "#f5ead6", False),
    ]):
        if await BadgeDefinition.find_one(BadgeDefinition.code == code) is None:
            await insert_fixture(
                resources,
                BadgeDefinition(
                    id=demo_id("badge", index), code=code, can_disable=not mandatory,
                    payload=BadgePayload(
                        label=label, description=f"{label} demonstration badge.", background_color=color,
                    ),
                ),
                None, "badge",
            )

    users: dict[str, User] = {}

    for index, (username, display_name, bio) in enumerate(DEMO_USERS):
        email = f"{username}@example.com"
        user = await User.find_one(User.username == username)

        if user is not None and user.email != email:
            raise ValueError(f"Refusing to seed @{username}: this username belongs to another email.")

        if user is None:
            if await User.find_one(User.email == email) is not None:
                raise ValueError(f"Refusing to seed {email}: this email belongs to another username.")

            user = User(
                id=demo_id("account", index), email=email, username=username, display_name=display_name,
                bio=bio, created_at=now, updated_at=now,
            )
            await insert_fixture(resources, user, user.id, "user")

        avatar_key = None
        if username != "noah" and user.avatars.original is None:
            avatar_key = await ensure_image(resources, "avatars", username, index)

        presentation_event = {"actor_id": user.id, "action": DESIGN_SEEDED}
        needs_presentation = username in DESIGN_LOCATIONS and await AuditEvent.find_one(presentation_event) is None
        banner_key = None
        if needs_presentation and username in BANNER_PALETTES and user.banner is None:
            banner_key = await ensure_image(resources, "profile-banners", username, BANNER_PALETTES[username])

        async with transaction(resources.mongo) as session:
            current = await User.get(user.id, session=session)
            changed = False

            if current is None:
                raise ValueError(f"Demo account @{username} disappeared during seeding.")

            if username != "noah" and not current.links:
                current.links = [
                    ProfileLink(label="Reading list", url="https://developer.mozilla.org/"),
                    ProfileLink(label="Project", url="https://github.com/fastapi/fastapi"),
                ]
                changed = True

            if avatar_key and current.avatars.original is None:
                current.avatars.original = AvatarImage(key=avatar_key, content_type="image/png")
                changed = True

            if needs_presentation and await AuditEvent.find_one(presentation_event, session=session) is None:
                if not current.location:
                    current.location = DESIGN_LOCATIONS[username]
                    changed = True
                if banner_key and current.banner is None:
                    current.banner = AvatarImage(key=banner_key, content_type="image/png")
                    changed = True

                await record_audit(
                    DEMO_AUDIT, DESIGN_SEEDED, actor_id=current.id,
                    target_type="user", target_id=str(current.id), session=session,
                )

            wanted = ["early-reader"]
            if username == "alice":
                wanted += ["community-guide", "workshop-member"]
            if username == "noah":
                wanted = []

            for code in wanted:
                if not any(badge.code == code for badge in current.badges):
                    current.badges.append(
                        BadgeAssignment(code=code, assigned_at=now, enabled=code != "workshop-member")
                    )
                    changed = True

            if changed:
                current.revision += 1
                current.updated_at = now
                await current.save(session=session)
                await record_audit(
                    DEMO_AUDIT, "DEMO_PROFILE_ENRICHED", actor_id=current.id,
                    target_type="user", target_id=str(current.id), session=session,
                )

            user = current

        if await AuthIdentity.find_one(
            AuthIdentity.user_id == user.id, AuthIdentity.provider == "password"
        ) is None:
            await insert_fixture(
                resources,
                AuthIdentity(
                    id=demo_id("password", index), user_id=user.id, subject=str(user.id),
                    password_hash=await hash_password_async(get_settings().demo_password), created_at=now,
                ),
                user.id, "identity",
            )

        users[username] = user

    return users
