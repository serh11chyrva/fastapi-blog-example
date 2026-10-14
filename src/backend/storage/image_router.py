import re

from fastapi import APIRouter, HTTPException, Request, Response

from backend.content.models import Article, MicroPost
from backend.core.config import get_settings
from backend.core.dependencies import OptionalUser
from backend.profiles.models import User
from backend.storage.models import ImagePurpose
from backend.storage.s3 import get_object


router = APIRouter(tags=["Media"])


@router.get("/static/images/{collection}/{object_name}", summary="Read an attached image", description="Avatars and post images are public. Article images require a published article or its author's session. Unattached or inaccessible objects return 404.")
async def read_image(collection: ImagePurpose, object_name: str, request: Request, current_user: OptionalUser) -> Response:
    if not re.fullmatch(r"[0-9a-f]{32}\.(jpg|png|webp)", object_name):
        raise HTTPException(404, "Image not found")
    key = f"{collection}/{object_name}"
    settings = get_settings()
    cache_control = "public, max-age=3600"
    if collection == "avatars":
        attached = await User.find_one(User.avatar_key == key)
        bucket = settings.avatar_bucket
    elif collection == "post-images":
        attached = await MicroPost.find_one({"image_keys": key, "deleted_at": None})
        bucket = settings.publication_bucket
    else:
        field = "thumbnail_key" if collection == "article-covers" else "inline_image_keys"
        attached = await Article.find_one({field: key, "deleted_at": None})
        if attached is not None and attached.status != "published" and (current_user is None or current_user.id != attached.author_id):
            attached = None
        cache_control = "private, no-store"
        bucket = settings.publication_bucket
    if attached is None:
        raise HTTPException(404, "Image not found")
    try:
        result = await get_object(request.app.state.s3_client, bucket, key)
    except Exception as exc:
        raise HTTPException(503, "Image storage is unavailable") from exc
    if result is None:
        raise HTTPException(404, "Image not found")
    data, content_type = result
    return Response(content=data, media_type=content_type, headers={"Cache-Control": cache_control, "X-Content-Type-Options": "nosniff"})
