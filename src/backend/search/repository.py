"""Atlas candidate reads with canonical visibility applied before page limits."""

from typing import Any, NoReturn

from beanie import Document
from pymongo.errors import OperationFailure, PyMongoError

from backend.core.errors import InvalidOperation, Unavailable
from backend.posts.visibility import visible_post_stages
from backend.profiles.models import User
from backend.search.models import SearchPublication
from backend.search.query import PUBLICATIONS_INDEX, USERS_INDEX, SearchQuery, SearchSort, atlas_query


async def require_index(model: type[Document], name: str) -> None:
    """Reject unprepared search indexes instead of returning misleading empty results.

    :param model: Beanie document whose collection owns the Atlas index.
    :param name: Versioned index name required by the application.
    :return: None; unavailable or non-queryable indexes raise a public 503 error.
    """
    cursor = await model.get_pymongo_collection().list_search_indexes(name=name)
    indexes = await cursor.to_list()
    if not indexes or not indexes[0].get("queryable"):
        raise Unavailable("Search is being prepared. Please try again later.")


def raise_search_error(error: PyMongoError, after: str | None, category: str) -> NoReturn:
    """Distinguish rejected Atlas continuation tokens from dependency failures.

    :param error: Driver error raised by index inspection or candidate loading.
    :param after: Supplied Atlas continuation, or None for an initial query.
    :param category: Public result category used in the dependency error message.
    :return: None. An input or dependency error is always raised.
    """
    message = str(error).lower()
    if (
        after is not None and isinstance(error, OperationFailure) and "token" in message
        and any(word in message for word in ("searchafter", "pagination", "sequence"))
        and any(word in message for word in ("invalid", "malformed", "deserialize", "decode"))
    ):
        raise InvalidOperation("Invalid search cursor for this query and sort") from error
    raise Unavailable(f"{category} search is temporarily unavailable. Please try again later.") from error


class SearchRepository:
    """Read bounded search pages without trusting indexed publication visibility."""

    @staticmethod
    async def users(query: SearchQuery, after: str | None, limit: int) -> list[dict[str, Any]]:
        """Search current public profiles with an extra continuation candidate.

        :param query: Normalized text and mandatory tags.
        :param after: Atlas continuation token, or None for the first page.
        :param limit: Maximum number of public profiles in the requested page.
        :return: Current user rows with sequence tokens, up to limit plus one.
        """
        try:
            await require_index(User, USERS_INDEX)
            return await User.aggregate([
                {"$search": atlas_query(query, users=True, sort="relevance", after=after)},
                {"$set": {"_search_token": {"$meta": "searchSequenceToken"}}},
                *([{"$match": {"search_hashtags": {"$all": list(query.hashtags)}}}] if query.hashtags else []),
                {"$limit": limit + 1},
            ], maxTimeMS=5_000).to_list()
        except PyMongoError as exc:
            raise_search_error(exc, after, "User")

    @staticmethod
    async def publications(
        query: SearchQuery, sort: SearchSort, after: str | None, limit: int,
    ) -> list[dict[str, Any]]:
        """Authorize Atlas candidates and current article search eligibility before selecting a visible page.

        :param query: Normalized words and mandatory exact tags.
        :param sort: Relevance or newest-publication ordering.
        :param after: Atlas continuation token from identical query semantics, or None.
        :param limit: Maximum number of visible publications in the requested page.
        :return: Current source documents, ordered author rows, and tokens, up to limit plus one.
        """
        try:
            await require_index(SearchPublication, PUBLICATIONS_INDEX)
            return await SearchPublication.aggregate([
                {"$search": atlas_query(query, users=False, sort=sort, after=after)},
                {"$set": {"_search_token": {"$meta": "searchSequenceToken"}}},
                *([{"$match": {"hashtags": {"$all": list(query.hashtags)}}}] if query.hashtags else []),
                {"$lookup": {
                    "from": "micro_posts", "localField": "source_id", "foreignField": "_id",
                    "let": {"kind": "$source_kind"}, "as": "_post", "pipeline": [
                        {"$match": {"deleted_at": None, "$expr": {"$eq": ["$$kind", "micro_post"]}}},
                        *visible_post_stages(),
                    ],
                }},
                {"$lookup": {
                    "from": "articles", "localField": "source_id", "foreignField": "_id",
                    "let": {"kind": "$source_kind"}, "as": "_article", "pipeline": [{"$match": {
                        "deleted_at": None, "archived_at": None, "status": "published",
                        "search_enabled": {"$ne": False},
                        "published_at": {"$ne": None}, "$expr": {"$eq": ["$$kind", "article"]},
                    }}],
                }},
                {"$set": {"source": {"$arrayElemAt": [{"$concatArrays": ["$_post", "$_article"]}, 0]}}},
                {"$match": {"source._id": {"$exists": True}}},
                {"$set": {"_author_ids": {"$concatArrays": [
                    ["$source.owner_id"], {"$ifNull": ["$source.featured_author_ids", []]},
                ]}}},
                {"$lookup": {"from": "users", "localField": "_author_ids", "foreignField": "_id", "as": "authors"}},
                {"$match": {"$expr": {"$eq": [{"$size": "$authors"}, {"$size": "$_author_ids"}]}}},
                {"$limit": limit + 1},
                {"$project": {"source_kind": 1, "source": 1, "authors": 1, "_search_token": 1}},
            ], maxTimeMS=5_000).to_list()
        except PyMongoError as exc:
            raise_search_error(exc, after, "Publication")
