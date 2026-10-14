import asyncio
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from backend.core.config import Settings


def create_s3_client(settings: Settings, *, public: bool = False) -> Any:
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_public_endpoint_url if public else settings.s3_endpoint_url,
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=Config(
            signature_version="s3v4",
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
            s3={"addressing_style": "path"},
            connect_timeout=3,
            read_timeout=5,
            retries={"max_attempts": 1},
        ),
    )


async def get_object(client: Any, bucket: str, key: str) -> tuple[bytes, str] | None:
    try:
        result = await asyncio.to_thread(client.get_object, Bucket=bucket, Key=key)
    except ClientError as exc:
        if exc.response["Error"]["Code"] in {"NoSuchKey", "404", "NotFound"}:
            return None
        raise
    body = result["Body"]
    try:
        data = await asyncio.to_thread(body.read)
    finally:
        body.close()
    return data, result.get("ContentType", "application/octet-stream")


async def delete_object(client: Any, bucket: str, key: str) -> None:
    await asyncio.to_thread(client.delete_object, Bucket=bucket, Key=key)


async def check_storage(client: Any, settings: Settings) -> None:
    for bucket in (settings.avatar_bucket, settings.publication_bucket):
        await asyncio.to_thread(client.head_bucket, Bucket=bucket)


def image_type(data: bytes) -> tuple[str, str] | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", "png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", "webp"
    return None
