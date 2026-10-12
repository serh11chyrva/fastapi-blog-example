from datetime import UTC, datetime
from typing import Literal

from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException, Query, Request, Response, status

from backend.content.schemas import ArticleCreate, ArticleResponse, ArticleUpdate, MicroPostCreate, MicroPostResponse
from backend.content.repository import ContentRepository
from backend.content.service import ContentService
from backend.core.audit import record_audit
from backend.core.dependencies import CurrentUser, OptionalUser
from backend.content.models import Article, MicroPost
from backend.profiles.models import Follow, User


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


@router.get("/me/articles", response_model=list[ArticleResponse])
async def list_my_articles(current_user: CurrentUser, article_status: Literal["all", "draft", "published"] = Query(default="all", alias="status")) -> list[ArticleResponse]:
    articles = await content_repository.list_articles(current_user.id, None if article_status == "all" else article_status)
    return [await _article_response(article) for article in articles]


@router.get("/articles/{article_id}", response_model=ArticleResponse)
async def get_article(article_id: str, current_user: OptionalUser) -> ArticleResponse:
    if not PydanticObjectId.is_valid(article_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    article = await content_repository.get_article(PydanticObjectId(article_id))
    if article is None or article.deleted_at is not None or (article.status == "draft" and (current_user is None or current_user.id != article.author_id)):
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
                article.updated_at = now
                await article.save(session=db_session)
                await record_audit(request, "ARTICLE_PUBLISHED", actor_id=current_user.id, target_type="article", target_id=article_id, session=db_session)
        await _bump_public_feed_version(request)
    return await _article_response(article)
