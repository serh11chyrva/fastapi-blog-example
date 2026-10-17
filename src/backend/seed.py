import asyncio
from datetime import UTC, datetime, timedelta

from beanie import init_beanie
from pymongo import AsyncMongoClient

from backend.auth.models import AuthIdentity
from backend.auth.security import hash_password
from backend.content.models import Article, MicroPost
from backend.core.config import get_settings
from backend.core.database import DOCUMENT_MODELS
from backend.profiles.migrations import ensure_profile_schema
from backend.profiles.models import (
    BadgeAssignment,
    BadgeDefinition,
    BadgePayload,
    Follow,
    User,
)

DEMO_USERS = [
    (
        "alice@example.com",
        "alice",
        "Alice Morgan",
        "A writer interested in thoughtful technology.",
    ),
    (
        "ben@example.com",
        "ben",
        "Ben Carter",
        "Building small things and sharing what I learn.",
    ),
    (
        "casey@example.com",
        "casey",
        "Casey Rivera",
        "Stories, books, and notes from everyday life.",
    ),
]

DEMO_POSTS = [
    (
        "alice",
        "A good writing habit starts with a small note and the patience to return tomorrow.",
    ),
    (
        "ben",
        "Today I shipped the first version of a tiny project. Small releases make learning easier.",
    ),
    ("casey", "What is one article you keep recommending to friends?"),
]

DEMO_ARTICLE_BODY = {
    "type": "doc",
    "content": [
        {
            "type": "paragraph",
            "content": [
                {
                    "type": "text",
                    "text": "Long-form writing belongs next to quick notes. This demo stores the editor document as structured TipTap JSON.",
                }
            ],
        },
        {
            "type": "heading",
            "attrs": {"level": 2},
            "content": [{"type": "text", "text": "A small beginning"}],
        },
        {
            "type": "paragraph",
            "content": [
                {
                    "type": "text",
                    "text": "Drafts give ideas room to grow before they are shared with everyone.",
                }
            ],
        },
    ],
}


async def seed_demo_data() -> None:
    settings = get_settings()
    client = AsyncMongoClient(
        settings.mongodb_url, serverSelectionTimeoutMS=8_000, tz_aware=True
    )
    try:
        await client.admin.command("ping")
        await init_beanie(
            database=client[settings.mongodb_database], document_models=DOCUMENT_MODELS
        )
        await ensure_profile_schema()
        if (
            await BadgeDefinition.find_one(BadgeDefinition.code == "early-reader")
            is None
        ):
            await BadgeDefinition(
                code="early-reader",
                payload=BadgePayload(
                    label="Early Reader", description="Joined the demo community early."
                ),
            ).insert()
        users: dict[str, User] = {}
        now = datetime.now(UTC)
        for email, username, display_name, bio in DEMO_USERS:
            user = await User.find_one(User.username == username)
            if user is None:
                user = User(
                    email=email,
                    username=username,
                    display_name=display_name,
                    bio=bio,
                    created_at=now,
                    updated_at=now,
                )
                user.badges = [BadgeAssignment(code="early-reader", assigned_at=now)]
                await user.insert()
            users[username] = user
            identity = await AuthIdentity.find_one(
                AuthIdentity.user_id == user.id, AuthIdentity.provider == "password"
            )
            if identity is None:
                await AuthIdentity(
                    user_id=user.id,
                    provider="password",
                    subject=str(user.id),
                    password_hash=hash_password(settings.demo_password),
                    created_at=now,
                ).insert()

        if await MicroPost.count() == 0:
            for index, (username, text) in enumerate(DEMO_POSTS):
                created_at = now - timedelta(minutes=(3 - index) * 30)
                await MicroPost(
                    author_id=users[username].id,
                    text=text,
                    created_at=created_at,
                    updated_at=created_at,
                ).insert()

        if await Article.count() == 0:
            for username, title, summary in [
                (
                    "alice",
                    "Writing in small steps",
                    "A few notes on building a sustainable writing practice.",
                ),
                (
                    "casey",
                    "The value of a first draft",
                    "Why starting imperfectly is often the most useful thing.",
                ),
            ]:
                await Article(
                    author_id=users[username].id,
                    title=title,
                    summary=summary,
                    body=DEMO_ARTICLE_BODY,
                    status="published",
                    created_at=now - timedelta(days=1),
                    updated_at=now - timedelta(days=1),
                    published_at=now - timedelta(days=1),
                ).insert()

        for follower, followee in [
            ("alice", "ben"),
            ("ben", "alice"),
            ("casey", "alice"),
            ("casey", "ben"),
        ]:
            if (
                await Follow.find_one(
                    Follow.follower_id == users[follower].id,
                    Follow.followee_id == users[followee].id,
                )
                is None
            ):
                await Follow(
                    follower_id=users[follower].id,
                    followee_id=users[followee].id,
                    created_at=now,
                ).insert()
        print(
            "Demo data is ready. Accounts: alice@example.com, ben@example.com, casey@example.com"
        )
        print("Use the local-only password configured by DEMO_PASSWORD in .env.")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(seed_demo_data())
