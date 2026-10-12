from datetime import UTC, datetime
import re
from uuid import uuid4
from typing import Literal

from beanie import PydanticObjectId
from fastapi import APIRouter, File, HTTPException, Query, Request, Response, UploadFile, status

from backend.content.schemas import ArticleCreate, ArticleResponse, ArticleScheduleRequest, ArticleUpdate, MicroPostCreate, MicroPostResponse
from backend.content.repository import ContentRepository
from backend.content.service import ContentService
from backend.core.audit import record_audit
from backend.core.dependencies import CurrentUser, OptionalUser
from backend.core.config import get_settings
from backend.content.models import Article, MicroPost
from backend.profiles.models import User
from backend.storage.s3 import delete_avatar, get_avatar, put_avatar


router = APIRouter(tags=["publications"])
content_repository = ContentRepository()
content_service = ContentService()


async def _post_response(post: MicroPost) -> MicroPostResponse:
    try:
        return await content_service.post_response(post)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Author not found") from exc


async def _article_response(article: Article) -> ArticleResponse:
    try:
        return await content_service.article_response(article)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Author not found") from exc


async def _bump_public_feed_version(request: Request) -> None:
    try:
        await request.app.state.redis.incr("feed:public:version")
    except Exception:
        request.app.state.logger.warning("Redis unavailable while invalidating public feed cache")


@router.post("/posts", response_model=MicroPostResponse, status_code=status.HTTP_201_CREATED)
async def create_micro_post(payload: MicroPostCreate, request: Request, current_user: CurrentUser) -> MicroPostResponse:
    now = datetime.now(UTC)
    post = MicroPost(author_id=current_user.id, text=payload.text, created_at=now, updated_at=now)
    client = request.app.state.mongo_client
    async with client.start_session() as db_session:
        async with await db_session.start_transaction():
            await post.insert(session=db_session)
            await record_audit(request, "MICRO_POST_CREATED", actor_id=current_user.id, target_type="micro_post", target_id=str(post.id), session=db_session)
    await _bump_public_feed_version(request)
    return await _post_response(post)


@router.get("/posts/{post_id}", response_model=MicroPostResponse)
async def get_micro_post(post_id: str) -> MicroPostResponse:
    if not PydanticObjectId.is_valid(post_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    post = await content_repository.get_post(PydanticObjectId(post_id))
    if post is None or post.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    return await _post_response(post)


@router.patch("/posts/{post_id}", response_model=MicroPostResponse)
async def update_micro_post(post_id: str, payload: MicroPostCreate, request: Request, current_user: CurrentUser) -> MicroPostResponse:
    if not PydanticObjectId.is_valid(post_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    post = await content_repository.get_post(PydanticObjectId(post_id))
    if post is None or post.deleted_at is not None or post.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    post.text = payload.text
    post.updated_at = datetime.now(UTC)
    client = request.app.state.mongo_client
    async with client.start_session() as db_session:
        async with await db_session.start_transaction():
            await post.save(session=db_session)
            await record_audit(request, "MICRO_POST_EDITED", actor_id=current_user.id, target_type="micro_post", target_id=post_id, session=db_session)
    await _bump_public_feed_version(request)
    return await _post_response(post)


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_micro_post(post_id: str, request: Request, current_user: CurrentUser) -> Response:
    if not PydanticObjectId.is_valid(post_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    post = await content_repository.get_post(PydanticObjectId(post_id))
    if post is None or post.deleted_at is not None or post.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    now = datetime.now(UTC)
    client = request.app.state.mongo_client
    async with client.start_session() as db_session:
        async with await db_session.start_transaction():
            post.deleted_at = now
            post.updated_at = now
            await post.save(session=db_session)
            await record_audit(request, "MICRO_POST_DELETED", actor_id=current_user.id, target_type="micro_post", target_id=post_id, session=db_session)
    await _bump_public_feed_version(request)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/articles/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_article(article_id: str, request: Request, current_user: CurrentUser) -> Response:
    if not PydanticObjectId.is_valid(article_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    article = await content_repository.get_article(PydanticObjectId(article_id))
    if article is None or article.deleted_at is not None or article.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    now = datetime.now(UTC)
    async with request.app.state.mongo_client.start_session() as db_session:
        async with await db_session.start_transaction():
            article.deleted_at = now
            article.updated_at = now
            await article.save(session=db_session)
            await record_audit(request, "ARTICLE_DELETED", actor_id=current_user.id, target_type="article", target_id=article_id, session=db_session)
    if article.thumbnail_key:
        try:
            await delete_avatar(request.app.state.s3_client, get_settings().avatar_bucket, article.thumbnail_key)
        except Exception:
            request.app.state.logger.exception("Failed to remove deleted article thumbnail")
    await _bump_public_feed_version(request)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/articles", response_model=ArticleResponse, status_code=status.HTTP_201_CREATED)
async def create_article(payload: ArticleCreate, request: Request, current_user: CurrentUser) -> ArticleResponse:
    now = datetime.now(UTC)
    article = Article(author_id=current_user.id, title=payload.title, summary=payload.summary, body=payload.body, status="draft", created_at=now, updated_at=now)
    client = request.app.state.mongo_client
    async with client.start_session() as db_session:
        async with await db_session.start_transaction():
            await article.insert(session=db_session)
            await record_audit(request, "ARTICLE_CREATED", actor_id=current_user.id, target_type="article", target_id=str(article.id), metadata={"status": "draft"}, session=db_session)
    return await _article_response(article)


@router.get("/publications/{username}/{share_slug}", response_model=MicroPostResponse | ArticleResponse)
async def get_shared_publication(username: str, share_slug: str) -> MicroPostResponse | ArticleResponse:
    share_id = share_slug.rsplit("--", 1)[-1]
    if not re.fullmatch(r"[0-9a-f]{32}", share_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publication not found")
    author = await User.find_one(User.username == username.lower().removeprefix("@"))
    if author is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publication not found")
    post = await MicroPost.find_one(MicroPost.share_id == share_id, MicroPost.author_id == author.id, MicroPost.deleted_at == None)  # noqa: E711
    if post is not None:
        return await _post_response(post)
    article = await Article.find_one(Article.share_id == share_id, Article.author_id == author.id, Article.status == "published", Article.deleted_at == None)  # noqa: E711
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publication not found")
    return await _article_response(article)


@router.put("/articles/{article_id}/thumbnail", response_model=ArticleResponse)
async def upload_article_thumbnail(
    article_id: str,
    request: Request,
    current_user: CurrentUser,
    file: UploadFile = File(...),
) -> ArticleResponse:
    if not PydanticObjectId.is_valid(article_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    article = await content_repository.get_article(PydanticObjectId(article_id))
    if article is None or article.deleted_at is not None or article.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    settings = get_settings()
    data = await file.read(settings.article_thumbnail_max_bytes + 1)
    if len(data) > settings.article_thumbnail_max_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Thumbnail is too large")
    detected = _image_type(data)
    if detected is None:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Use a JPEG, PNG, or WebP image")
    content_type, extension = detected
    new_key = f"article-thumbnails/{uuid4().hex}.{extension}"
    client = request.app.state.s3_client
    try:
        await put_avatar(client, settings.avatar_bucket, new_key, data, content_type)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Image storage is unavailable") from exc
    old_key = article.thumbnail_key
    article.thumbnail_key = new_key
    article.updated_at = datetime.now(UTC)
    mongo_client = request.app.state.mongo_client
    try:
        async with mongo_client.start_session() as db_session:
            async with await db_session.start_transaction():
                await article.save(session=db_session)
                await record_audit(request, "ARTICLE_THUMBNAIL_CHANGED", actor_id=current_user.id, target_type="article", target_id=article_id, session=db_session)
    except Exception:
        await delete_avatar(client, settings.avatar_bucket, new_key)
        raise
    if old_key:
        try:
            await delete_avatar(client, settings.avatar_bucket, old_key)
        except Exception:
            request.app.state.logger.exception("Failed to remove replaced article thumbnail")
    await _bump_public_feed_version(request)
    return await _article_response(article)


@router.get("/media/article-thumbnails/{object_name}")
async def read_article_thumbnail(object_name: str, request: Request, current_user: OptionalUser) -> Response:
    if not re.fullmatch(r"[0-9a-f]{32}\.(jpg|png|webp)", object_name):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail not found")
    key = f"article-thumbnails/{object_name}"
    article = await Article.find_one(Article.thumbnail_key == key, Article.deleted_at == None)  # noqa: E711
    if article is None or (article.status != "published" and (current_user is None or current_user.id != article.author_id)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail not found")
    try:
        result = await get_avatar(request.app.state.s3_client, get_settings().avatar_bucket, key)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Image storage is unavailable") from exc
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail not found")
    data, content_type = result
    return Response(content=data, media_type=content_type, headers={"Cache-Control": "public, max-age=3600", "X-Content-Type-Options": "nosniff"})


def _image_type(data: bytes) -> tuple[str, str] | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", "png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", "webp"
    return None


@router.get("/me/articles", response_model=list[ArticleResponse])
async def list_my_articles(current_user: CurrentUser, article_status: Literal["all", "draft", "scheduled", "published"] = Query(default="all", alias="status")) -> list[ArticleResponse]:
    articles = await content_repository.list_articles(current_user.id, None if article_status == "all" else article_status)
    return [await _article_response(article) for article in articles]


@router.get("/articles/{article_id}", response_model=ArticleResponse)
async def get_article(article_id: str, current_user: OptionalUser) -> ArticleResponse:
    if not PydanticObjectId.is_valid(article_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    article = await content_repository.get_article(PydanticObjectId(article_id))
    if article is None or article.deleted_at is not None or (article.status != "published" and (current_user is None or current_user.id != article.author_id)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    return await _article_response(article)


@router.patch("/articles/{article_id}", response_model=ArticleResponse)
async def update_article(article_id: str, payload: ArticleUpdate, request: Request, current_user: CurrentUser) -> ArticleResponse:
    if not PydanticObjectId.is_valid(article_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    article = await content_repository.get_article(PydanticObjectId(article_id))
    if article is None or article.deleted_at is not None or article.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        if value is not None:
            setattr(article, field, value)
    article.updated_at = datetime.now(UTC)
    client = request.app.state.mongo_client
    async with client.start_session() as db_session:
        async with await db_session.start_transaction():
            await article.save(session=db_session)
            await record_audit(request, "ARTICLE_EDITED", actor_id=current_user.id, target_type="article", target_id=article_id, metadata={"fields": sorted(changes)}, session=db_session)
    await _bump_public_feed_version(request)
    return await _article_response(article)


@router.post("/articles/{article_id}/publish", response_model=ArticleResponse)
async def publish_article(article_id: str, request: Request, current_user: CurrentUser) -> ArticleResponse:
    if not PydanticObjectId.is_valid(article_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    article = await content_repository.get_article(PydanticObjectId(article_id))
    if article is None or article.deleted_at is not None or article.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    if article.status != "published":
        now = datetime.now(UTC)
        client = request.app.state.mongo_client
        async with client.start_session() as db_session:
            async with await db_session.start_transaction():
                article.status = "published"
                article.published_at = now
                article.scheduled_at = None
                article.updated_at = now
                await article.save(session=db_session)
                await record_audit(request, "ARTICLE_PUBLISHED", actor_id=current_user.id, target_type="article", target_id=article_id, session=db_session)
        await _bump_public_feed_version(request)
    return await _article_response(article)


@router.post("/articles/{article_id}/draft", response_model=ArticleResponse)
async def return_article_to_draft(article_id: str, request: Request, current_user: CurrentUser) -> ArticleResponse:
    if not PydanticObjectId.is_valid(article_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    article = await content_repository.get_article(PydanticObjectId(article_id))
    if article is None or article.deleted_at is not None or article.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    article.status = "draft"
    article.scheduled_at = None
    article.published_at = None
    article.updated_at = datetime.now(UTC)
    async with request.app.state.mongo_client.start_session() as db_session:
        async with await db_session.start_transaction():
            await article.save(session=db_session)
            await record_audit(request, "ARTICLE_UNPUBLISHED", actor_id=current_user.id, target_type="article", target_id=article_id, session=db_session)
    await _bump_public_feed_version(request)
    return await _article_response(article)


@router.post("/articles/{article_id}/schedule", response_model=ArticleResponse)
async def schedule_article(
    article_id: str,
    payload: ArticleScheduleRequest,
    request: Request,
    current_user: CurrentUser,
) -> ArticleResponse:
    if not PydanticObjectId.is_valid(article_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    article = await content_repository.get_article(PydanticObjectId(article_id))
    if article is None or article.deleted_at is not None or article.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    article.status = "scheduled"
    article.scheduled_at = payload.publish_at
    article.published_at = None
    article.updated_at = datetime.now(UTC)
    async with request.app.state.mongo_client.start_session() as db_session:
        async with await db_session.start_transaction():
            await article.save(session=db_session)
            await record_audit(
                request,
                "ARTICLE_SCHEDULED",
                actor_id=current_user.id,
                target_type="article",
                target_id=article_id,
                metadata={"publish_at": payload.publish_at.isoformat()},
                session=db_session,
            )
    await _bump_public_feed_version(request)
    return await _article_response(article)
