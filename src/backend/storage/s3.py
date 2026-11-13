import asyncio
from typing import Any, Protocol, TypedDict, cast

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from botocore.response import StreamingBody

from backend.core.config import Settings


class ObjectResponse(TypedDict):
    """S3 download response containing a streaming body and its media type."""

    Body: StreamingBody
    ContentType: str


class ObjectInfo(TypedDict):
    """S3 object metadata containing the stored byte length."""

    ContentLength: int


class S3Client(Protocol):
    """The S3 operations used by the image protocol and maintenance commands."""

    def generate_presigned_url(
        self,
        ClientMethod: str,
        *,
        Params: dict[str, str],
        ExpiresIn: int,
        HttpMethod: str,
    ) -> str:
        """Sign an S3 operation for temporary client access.

        :param ClientMethod: S3 operation name to sign.
        :param Params: Bucket, object key, and operation parameters included in the
            signature.
        :param ExpiresIn: Presigned URL lifetime in seconds.
        :param HttpMethod: HTTP method required when using the signed URL.
        :return: The presigned operation URL.
        """
        ...

    def get_object(self, *, Bucket: str, Key: str, Range: str = ...) -> ObjectResponse:
        """Open a stored object or a requested byte range.

        :param Bucket: Name of the S3 bucket to access.
        :param Key: Object key within the destination bucket.
        :param Range: Optional HTTP byte range to retrieve.
        :return: The S3 streaming body and content type.
        """
        ...

    def head_object(self, *, Bucket: str, Key: str) -> ObjectInfo:
        """Read an object's metadata without downloading its contents.

        :param Bucket: Name of the S3 bucket to access.
        :param Key: Object key within the destination bucket.
        :return: The object metadata including its byte length.
        """
        ...

    def head_bucket(self, *, Bucket: str) -> object:
        """Check that a bucket exists and is accessible.

        :param Bucket: Name of the S3 bucket to access.
        :return: The S3 bucket metadata response.
        """
        ...

    def copy_object(
        self,
        *,
        Bucket: str,
        Key: str,
        CopySource: dict[str, str],
        MetadataDirective: str,
        ContentType: str,
    ) -> object:
        """Copy an object to a separate key with the supplied metadata.

        :param Bucket: Name of the S3 bucket to access.
        :param Key: Object key within the destination bucket.
        :param CopySource: Source bucket and object key to copy.
        :param MetadataDirective: Whether to retain or replace source object metadata.
        :param ContentType: MIME type stored on the copied object.
        :return: The S3 copy-operation response.
        """
        ...

    def delete_object(self, *, Bucket: str, Key: str) -> object:
        """Delete the object at the specified bucket and key.

        :param Bucket: Name of the S3 bucket to access.
        :param Key: Object key within the destination bucket.
        :return: The S3 deletion response.
        """
        ...

    def put_bucket_cors(self, *, Bucket: str, CORSConfiguration: dict[str, Any]) -> object:
        """Replace a bucket's browser cross-origin access rules.

        :param Bucket: Name of the S3 bucket to access.
        :param CORSConfiguration: Browser cross-origin rules to apply to the bucket.
        :return: The S3 CORS configuration response.
        """
        ...

    def get_paginator(self, operation_name: str) -> Any:
        """Create a paginator for the named S3 listing operation.

        :param operation_name: S3 operation for which pagination is requested.
        :return: The operation paginator.
        """
        ...

    def close(self) -> None:
        """Release the S3 client's network resources.

        :return: None.
        """
        ...


def create_s3_client(settings: Settings, *, public: bool = False) -> S3Client:
    """Configure an S3 client for internal operations or browser URL signing.

    :param settings: Application configuration for storage endpoints and credentials.
    :param public: Whether to use the browser-reachable endpoint for URL signing.
    :return: The configured S3-compatible client.
    """
    return cast(
        S3Client,
        boto3.client(
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
        ),
    )


async def get_object(client: S3Client, bucket: str, key: str) -> tuple[bytes, str] | None:
    """Download image bytes without blocking the event loop.

    :param client: S3-compatible client used to access the image buckets.
    :param bucket: S3 bucket containing the image object.
    :param key: Stored object key identifying the image.
    :return: The image bytes and MIME type, or None when the object is absent.
    """
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


async def delete_object(client: S3Client, bucket: str, key: str) -> None:
    """Delete an S3 object without blocking the event loop.

    :param client: S3-compatible client used to access the image buckets.
    :param bucket: S3 bucket containing the image object.
    :param key: Stored object key identifying the image.
    :return: None.
    """
    await asyncio.to_thread(client.delete_object, Bucket=bucket, Key=key)


async def check_storage(client: S3Client, settings: Settings) -> None:
    """Check access to both required image buckets.

    :param client: S3-compatible client used to access the image buckets.
    :param settings: Application configuration for storage endpoints and credentials.
    :return: None.
    """
    for bucket in (settings.avatar_bucket, settings.publication_bucket):
        await asyncio.to_thread(client.head_bucket, Bucket=bucket)


def image_type(data: bytes) -> tuple[str, str] | None:
    """Recognize JPEG, PNG, WebP, and GIF87a/GIF89a from their leading bytes.

    :param data: Leading image bytes used to identify the file signature.
    :return: The MIME type and extension, or None for an unsupported signature.
    """
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", "jpg"

    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", "png"

    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", "webp"

    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif", "gif"

    return None
