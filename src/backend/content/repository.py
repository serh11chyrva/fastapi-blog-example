from beanie import PydanticObjectId

from backend.content.models import Article, MicroPost


class ContentRepository:
    @staticmethod
    async def get_post(post_id: PydanticObjectId) -> MicroPost | None:
        return await MicroPost.get(post_id)

    @staticmethod
    async def get_article(article_id: PydanticObjectId) -> Article | None:
        return await Article.get(article_id)

    @staticmethod
    async def list_articles(author_id: PydanticObjectId, status: str | None = None) -> list[Article]:
        conditions: dict = {"author_id": author_id, "deleted_at": None}
        if status is not None:
            conditions["status"] = status
        return await Article.find(conditions).sort(("updated_at", -1)).limit(100).to_list()

    @staticmethod
    async def list_publications(author_id: PydanticObjectId, kind: str) -> list[tuple[str, object, object]]:
        pairs: list[tuple[str, object, object]] = []
        if kind in {"all", "micro_post"}:
            posts = await MicroPost.find(MicroPost.author_id == author_id, MicroPost.deleted_at == None).sort(("created_at", -1)).limit(25).to_list()  # noqa: E711
            pairs.extend(("micro_post", item, item.created_at) for item in posts)
        if kind in {"all", "article"}:
            articles = await Article.find(Article.author_id == author_id, Article.status == "published", Article.deleted_at == None).sort(("published_at", -1)).limit(25).to_list()  # noqa: E711
            pairs.extend(("article", item, item.published_at) for item in articles if item.published_at is not None)
        return pairs

    @staticmethod
    async def load_feed_type(kind: str, conditions: dict, date_field: str, limit: int) -> list[object]:
        model = MicroPost if kind == "micro_post" else Article
        return await model.find(conditions).sort((date_field, -1), ("_id", -1)).limit(limit + 1).to_list()
