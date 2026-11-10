"""Load additive demonstration fixtures into the configured application database and image buckets."""

import asyncio
from datetime import UTC, datetime

from beanie import init_beanie
from pymongo import AsyncMongoClient
from redis.asyncio import Redis

from backend.comments.migrations import ensure_comment_like_counts
from backend.core.config import get_settings
from backend.core.database import DOCUMENT_MODELS
from backend.core.resources import AppResources
from backend.demo.activity import seed_activity, seed_discussions
from backend.demo.common import demo_id
from backend.demo.profiles import seed_profiles
from backend.demo.publications import seed_publications
from backend.feeds.cache import invalidate_public_feed
from backend.profiles.migrations import ensure_profile_schema
from backend.storage.s3 import check_storage, create_s3_client


async def seed_demo_data() -> None:
    """Add missing demo fixtures without clearing data, overwriting publications, or resetting passwords.

    Stable identities make reruns additive, including after partial failures. Existing
    edited, deleted, expired, or revoked fixture documents are preserved. Missing demo
    relationships are restored. Generated images use stable keys in the configured
    private buckets; no remote images or additional Python dependencies are required.

    :return: None.
    """
    settings = get_settings()
    client = AsyncMongoClient(settings.mongodb_url, serverSelectionTimeoutMS=8_000, tz_aware=True)
    redis = Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=3)
    s3 = create_s3_client(settings)
    s3_public = create_s3_client(settings, public=True)
    resources = AppResources(client, redis, s3, s3_public)

    try:
        await client.admin.command("ping")
        await redis.ping()
        await check_storage(s3, settings)
        await init_beanie(database=client[settings.mongodb_database], document_models=DOCUMENT_MODELS)
        await ensure_profile_schema()
        await ensure_comment_like_counts()
        now = datetime.now(UTC)

        print("Seeding demo profiles, links, badges, avatars, and banners...", flush=True)
        users = await seed_profiles(resources, now)
        print("Seeding posts, articles, galleries, and rich editor content...", flush=True)
        posts, articles = await seed_publications(resources, users, now)
        print("Seeding follows, reactions, saved items, reposts, and session examples...", flush=True)
        await seed_activity(resources, users, posts, articles, now)
        print("Seeding profile activity, ranked comments, and preserved reply branches...", flush=True)
        await seed_discussions(resources, users, posts, articles)
        await invalidate_public_feed(redis)

        origin = settings.app_origin
        print(f"Demo fixtures are ready: {len(users)} accounts, {len(posts)} posts, {len(articles)} articles.")
        print("Accounts: " + ", ".join(user.email for user in users.values()))
        print("New identities use DEMO_PASSWORD. Existing passwords and publication edits are preserved.")
        print(f"Open the application: {origin}")
        print(f"Rich note and threaded discussion: {origin}/posts/{posts['note-00'].id}")
        print(f"Five-image gallery: {origin}/posts/{posts['note-01'].id}")
        print(f"Rich article and flat comments: {origin}/articles/{articles['reading-room'].id}")
        workbench = articles["publishing-workbench"]
        print(f"Publishing workbench: {origin}/articles/{workbench.id}")
        print(f"Linked demo comment: {origin}/articles/{workbench.id}#comment-{demo_id('workbench-comments')}")
        print(f"Profile with article-comment activity: {origin}/@casey")
        print("Sign in as Alice for Saved, private drafts, scheduled articles, and session settings.")
        print("See docs/DEMO.md for the complete feature tour.")
    finally:
        await redis.aclose()
        s3.close()
        s3_public.close()
        await client.close()


if __name__ == "__main__":
    asyncio.run(seed_demo_data())
