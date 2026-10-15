"""HTTP adapters for publication operations."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response

from backend.audit.dependencies import Audit
from backend.auth.dependencies import CurrentUser, OptionalUser
from backend.content.models import Article, MicroPost
from backend.content.presenters import article_response, post_response
from backend.content.schemas import ArticleCreate, ArticleResponse, ArticleScheduleRequest, ArticleUpdate, MicroPostCreate, MicroPostResponse
from backend.content.service import ContentService
from backend.core.resources import Resources


router = APIRouter(tags=["publications"])


def get_content_service(resources: Resources, audit: Audit) -> ContentService:
    return ContentService(resources, audit)


Content = Annotated[ContentService, Depends(get_content_service)]


@router.post("/posts", response_model=MicroPostResponse, status_code=201)
async def create_micro_post(payload: MicroPostCreate, current_user: CurrentUser, content: Content) -> MicroPostResponse:
    return post_response(await content.create_post(payload, current_user), current_user)


@router.get("/posts/{post_id}", response_model=MicroPostResponse)
async def get_micro_post(post_id: str, content: Content) -> MicroPostResponse:
    post, author = await content.get_post(post_id)
    return post_response(post, author)


@router.patch("/posts/{post_id}", response_model=MicroPostResponse)
async def update_micro_post(post_id: str, payload: MicroPostCreate, current_user: CurrentUser, content: Content) -> MicroPostResponse:
    return post_response(await content.edit_post(post_id, payload, current_user), current_user)


@router.delete("/posts/{post_id}", status_code=204)
async def delete_micro_post(post_id: str, current_user: CurrentUser, content: Content) -> Response:
    await content.delete(MicroPost, post_id, current_user)
    return Response(status_code=204)


@router.delete("/articles/{article_id}", status_code=204)
async def delete_article(article_id: str, current_user: CurrentUser, content: Content) -> Response:
    await content.delete(Article, article_id, current_user)
    return Response(status_code=204)


@router.post("/articles", response_model=ArticleResponse, status_code=201)
async def create_article(payload: ArticleCreate, current_user: CurrentUser, content: Content) -> ArticleResponse:
    return article_response(await content.create_article(payload, current_user), current_user)


@router.get("/publications/{username}/{share_slug}", response_model=MicroPostResponse | ArticleResponse)
async def get_shared_publication(username: str, share_slug: str, content: Content) -> MicroPostResponse | ArticleResponse:
    publication, author = await content.shared(username, share_slug)
    return post_response(publication, author) if isinstance(publication, MicroPost) else article_response(publication, author)


@router.get("/me/articles", response_model=list[ArticleResponse])
async def list_my_articles(
    current_user: CurrentUser,
    content: Content,
    article_status: Literal["all", "draft", "scheduled", "published"] = Query(default="all", alias="status"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[ArticleResponse]:
    articles = await content.list_mine(current_user, None if article_status == "all" else article_status, offset, limit)
    return [article_response(article, current_user) for article in articles]


@router.get("/articles/{article_id}", response_model=ArticleResponse)
async def get_article(article_id: str, current_user: OptionalUser, content: Content) -> ArticleResponse:
    article, author = await content.get_article(article_id, current_user)
    return article_response(article, author)


@router.patch("/articles/{article_id}", response_model=ArticleResponse)
async def update_article(article_id: str, payload: ArticleUpdate, current_user: CurrentUser, content: Content) -> ArticleResponse:
    return article_response(await content.edit_article(article_id, payload, current_user), current_user)


@router.post("/articles/{article_id}/publish", response_model=ArticleResponse)
async def publish_article(article_id: str, current_user: CurrentUser, content: Content) -> ArticleResponse:
    return article_response(await content.transition(article_id, current_user, "published"), current_user)


@router.post("/articles/{article_id}/draft", response_model=ArticleResponse)
async def return_article_to_draft(article_id: str, current_user: CurrentUser, content: Content) -> ArticleResponse:
    return article_response(await content.transition(article_id, current_user, "draft"), current_user)


@router.post("/articles/{article_id}/schedule", response_model=ArticleResponse)
async def schedule_article(article_id: str, payload: ArticleScheduleRequest, current_user: CurrentUser, content: Content) -> ArticleResponse:
    return article_response(await content.transition(article_id, current_user, "scheduled", payload.publish_at), current_user)
