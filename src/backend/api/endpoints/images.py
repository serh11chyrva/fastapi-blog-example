import re

from fastapi import APIRouter, HTTPException, Request, Response

from backend.api.metadata import documented_responses
from backend.articles.models import Article
from backend.auth.dependencies import OptionalUser
from backend.core.config import get_settings
from backend.core.resources import get_resources
from backend.posts.models import MicroPost
from backend.publications.access import readable_publication
from backend.profiles.models import User
from backend.storage.models import ImagePurpose
from backend.storage.s3 import get_object

router = APIRouter()


@router.get(
    "/static/images/{collection}/{object_name}",
    summary="Read an attached image",
    description=(
        "Avatars and profile banners are public. Publication images follow archive and discussion visibility; "
        "private images require their owner's session. GIF is served only for posts, comments, and article bodies, "
        "with animation preserved. Unattached or inaccessible objects return 404."
    ),
    tags=["Media"],
    responses={
        **documented_responses(404, 503),
        **{
            200: {
                "description": "Attached image bytes in the detected format.",
                "content": {
                    "image/jpeg": {"schema": {"type": "string", "format": "binary"}},
                    "image/png": {"schema": {"type": "string", "format": "binary"}},
                    "image/webp": {"schema": {"type": "string", "format": "binary"}},
                    "image/gif": {"schema": {"type": "string", "format": "binary"}},
                },
            }
        },
    },
    openapi_extra={"security": [{}, {"SessionCookie": []}]},
)
async def read_image(
    collection: ImagePurpose,
    object_name: str,
    request: Request,
    current_user: OptionalUser,
) -> Response:
    """Serve unchanged image bytes after enforcing visibility and collection format rules.

    :param collection: Public image collection used in the API path.
    :param object_name: Image filename within the requested public collection.
    :param request: Incoming HTTP request and its application state.
    :param current_user: Account resolved from the session cookie, or None for anonymous
        access.
    :return: The image bytes with their media type and cache headers.
    """
    extensions = "jpg|png|webp|gif" if collection in {"post-images", "article-images"} else "jpg|png|webp"

    if not re.fullmatch(rf"[0-9a-f]{{32}}\.({extensions})", object_name):
        raise HTTPException(404, "Image not found")

    key = f"{collection}/{object_name}"
    settings = get_settings()
    cache_control = "public, max-age=3600"

    if collection == "avatars":
        attached = await User.find_one({"avatars.original.key": key})
        bucket = settings.avatar_bucket
    elif collection == "profile-banners":
        attached = await User.find_one({"banner.key": key})
        bucket = settings.avatar_bucket
        cache_control = "no-store"
    elif collection == "post-images":
        attached = await MicroPost.find_one({"image_keys": key, "deleted_at": None})
        if attached is not None and attached.pending:
            if current_user is None or current_user.id != attached.owner_id:
                attached = None
        elif attached is not None and not (
            attached.archived_at is not None and current_user is not None and current_user.id == attached.owner_id
        ):
            await readable_publication("micro_post", str(attached.id), current_user.id if current_user else None)
        cache_control = "private, no-store"
        bucket = settings.publication_bucket
    else:
        field = "thumbnail_key" if collection == "article-covers" else "inline_image_keys"
        attached = await Article.find_one({field: key, "deleted_at": None})

        if (
            attached is not None
            and (attached.status != "published" or attached.archived_at is not None)
            and (current_user is None or current_user.id != attached.owner_id)
        ):
            attached = None

        cache_control = "private, no-store"
        bucket = settings.publication_bucket

    if attached is None:
        raise HTTPException(404, "Image not found")

    try:
        result = await get_object(get_resources(request).s3, bucket, key)
    except Exception as exc:
        raise HTTPException(503, "Image storage is unavailable") from exc

    if result is None:
        raise HTTPException(404, "Image not found")

    data, content_type = result

    return Response(
        content=data,
        media_type=content_type,
        headers={"Cache-Control": cache_control, "X-Content-Type-Options": "nosniff"},
    )
