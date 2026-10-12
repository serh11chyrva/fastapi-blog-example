from backend.content.models import Article, MicroPost
from backend.content.schemas import ArticleResponse, MicroPostResponse
from backend.content.urls import article_thumbnail_url, share_path
from backend.profiles.repository import ProfileRepository
from backend.profiles.service import ProfileService


class ContentService:
    def __init__(self, profiles: type[ProfileRepository] = ProfileRepository) -> None:
        self.profiles = profiles

    async def post_response(self, post: MicroPost) -> MicroPostResponse:
        author = await self.profiles.get_by_id(post.author_id)
        if author is None:
            raise LookupError("Author not found")
        return MicroPostResponse(
            id=str(post.id), share_url=share_path(author.username, post.text, post.share_id), text=post.text, author_id=str(author.id), author_username=author.username,
            author_display_name=author.display_name, author_avatar_url=ProfileService.avatar_url(author),
            created_at=post.created_at, updated_at=post.updated_at,
        )

    async def article_response(self, article: Article) -> ArticleResponse:
        author = await self.profiles.get_by_id(article.author_id)
        if author is None:
            raise LookupError("Author not found")
        return ArticleResponse(
            id=str(article.id), share_url=share_path(author.username, article.title, article.share_id), title=article.title,
            summary=article.summary, body=article.body, thumbnail_url=article_thumbnail_url(article.thumbnail_key), status=article.status,
            author_id=str(author.id), author_username=author.username, author_display_name=author.display_name,
            author_avatar_url=ProfileService.avatar_url(author), created_at=article.created_at,
            updated_at=article.updated_at, scheduled_at=article.scheduled_at, published_at=article.published_at,
        )
