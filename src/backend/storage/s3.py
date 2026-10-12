import asyncio
from typing import Any

import boto3
from botocore.config import Config

from backend.core.config import Settings


def create_s3_client(settings: Settings) -> Any:
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            connect_timeout=3,
            read_timeout=5,
            retries={"max_attempts": 1},
        ),
    )


async def put_avatar(client: Any, bucket: str, key: str, data: bytes, content_type: str) -> None:
    await asyncio.to_thread(client.put_object, Bucket=bucket, Key=key, Body=data, ContentType=content_type)


async def get_avatar(client: Any, bucket: str, key: str) -> tuple[bytes, str] | None:
    try:
        result = await asyncio.to_thread(client.get_object, Bucket=bucket, Key=key)
    except client.exceptions.NoSuchKey:
        return None
    body = result["Body"]
    data = await asyncio.to_thread(body.read)
    return data, result.get("ContentType", "application/octet-stream")


async def delete_avatar(client: Any, bucket: str, key: str) -> None:
    await asyncio.to_thread(client.delete_object, Bucket=bucket, Key=key)


async def check_storage(client: Any, bucket: str) -> None:
    await asyncio.to_thread(client.head_bucket, Bucket=bucket)
