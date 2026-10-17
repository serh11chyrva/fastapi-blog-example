import asyncio
from datetime import UTC, datetime, timedelta

from loguru import logger
from pymongo.asynchronous.client_session import AsyncClientSession

from backend.content.models import Article, MicroPost
from backend.profiles.models import User
from backend.storage.models import ObjectCleanup
from backend.storage.s3 import S3Client, delete_object


async def queue_deletion(
    bucket: str,
    key: str,
    *,
    not_before: datetime | None = None,
    session: AsyncClientSession | None = None,
) -> None:
    """Persist a deletion job, optionally atomically with attachment replacement.

    not_before defers temporary or uncommitted objects; the worker checks whether
    a final object is attached before deleting it and retries storage failures.
    """
    await ObjectCleanup(
        bucket=bucket, key=key, not_before=not_before or datetime.now(UTC)
    ).insert(session=session)


async def is_attached(key: str) -> bool:
    if key.startswith("avatars/"):
        return await User.find_one(User.avatar_key == key) is not None
    if key.startswith("post-images/"):
        return (
            await MicroPost.find_one({"image_keys": key, "deleted_at": None})
            is not None
        )
    return (
        await Article.find_one(
            {
                "deleted_at": None,
                "$or": [{"thumbnail_key": key}, {"inline_image_keys": key}],
            }
        )
        is not None
    )


async def run_storage_cleanup(client: S3Client) -> None:
    while True:
        try:
            jobs = (
                await ObjectCleanup.find(ObjectCleanup.not_before <= datetime.now(UTC))
                .sort("not_before")
                .limit(100)
                .to_list()
            )
            for job in jobs:
                try:
                    if not job.key.startswith("temporary/") and await is_attached(
                        job.key
                    ):
                        await job.delete()
                        continue
                    await delete_object(client, job.bucket, job.key)
                    await job.delete()
                except Exception:
                    logger.exception("Failed to delete a queued image object")
                    job.not_before = datetime.now(UTC) + timedelta(minutes=5)
                    await job.save()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Image storage cleanup worker failed")
        await asyncio.sleep(60)
