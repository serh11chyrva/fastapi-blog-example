from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ImageFileInput(BaseModel):
    """Client-declared filename, content type, and size for one image upload."""

    filename: str = Field(
        min_length=1,
        max_length=255,
        description="Original filename, used only as suggested alternate text.",
        examples=["figure.png", "animation.gif"],
    )
    content_type: Literal["image/jpeg", "image/png", "image/webp", "image/gif"] = Field(
        description="Image MIME type; GIF is allowed in posts, comments, and article bodies only. Bytes are checked.",
        examples=["image/png", "image/gif"],
    )
    size_bytes: int = Field(
        gt=0,
        description=(
            "Exact file length in bytes, checked again at completion. GIF allows up to 8388608 bytes "
            "in posts, comments, and article bodies only."
        ),
        examples=[1024, 8388608],
    )


class ImageUploadRequest(BaseModel):
    """Batch of image metadata used to prepare a direct upload session."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "files": [
                        {
                            "filename": "figure.png",
                            "content_type": "image/png",
                            "size_bytes": 1024,
                        }
                    ]
                }
            ]
        }
    )
    files: list[ImageFileInput] = Field(
        min_length=1,
        max_length=5,
        description=(
            "One file, or one to five JPEG/PNG/WebP post gallery files in display order. "
            "A post/comment GIF must be the only file."
        ),
    )


class PresignedImageFile(BaseModel):
    """Temporary PUT URL, required headers, and per-file size limit."""

    upload_url: str = Field(
        description="Temporary presigned Garage URL. Send raw file bytes without application cookies."
    )
    method: Literal["PUT"] = "PUT"
    headers: dict[str, str] = Field(
        description="Required headers to send unchanged with the PUT request.",
        examples=[{"Content-Type": "image/png"}, {"Content-Type": "image/gif"}],
    )
    max_size_bytes: int = Field(
        description="Maximum for this file: 8 MiB for GIF, 10 MiB for JPEG/PNG/WebP article covers, otherwise 5 MiB.",
        examples=[5242880, 8388608, 10485760],
    )


class ImageUploadResponse(BaseModel):
    """Prepared upload session with its expiry and direct PUT instructions."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "upload_id": "65f0c2a1b2c3d4e5f6071899",
                    "expires_at": "2026-10-14T12:10:00Z",
                    "files": [
                        {
                            "upload_url": "http://localhost:3900/blog-publications/temporary/0123456789abcdef0123456789abcdef?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=example",
                            "method": "PUT",
                            "headers": {"Content-Type": "image/png"},
                            "max_size_bytes": 5242880,
                        }
                    ],
                }
            ]
        }
    )
    upload_id: str = Field(description="Upload session ObjectId, used only at the matching completion endpoint.")
    expires_at: datetime = Field(
        description="UTC deadline for uploading and starting confirmation; URLs last ten minutes."
    )
    files: list[PresignedImageFile] = Field(description="Upload instructions in the same order as the requested files.")
