"""Assemble search pages from authorized current documents."""

from backend.articles.models import Article
from backend.feeds.presenters import feed_item
from backend.posts.models import MicroPost
from backend.profiles.models import User
from backend.profiles.presenters import user_card
from backend.search.query import SearchSort, decode_cursor, encode_cursor, parse_query, query_key
from backend.search.repository import SearchRepository
from backend.search.schemas import SearchPublicationHit, SearchPublicationsPage, SearchUser, SearchUsersPage
from backend.search.text import article_content, article_excerpt


async def search_users(q: str, cursor: str | None, limit: int) -> SearchUsersPage:
    """Search public profile fields with an independent continuation.

    :param q: Literal query text with optional mandatory hashtags.
    :param cursor: Continuation from the same user query, or None.
    :param limit: Validated public-profile page size.
    :return: Current public profile cards and an optional continuation cursor.
    """
    query = parse_query(q)
    key = query_key(query, True, "relevance")
    rows = await SearchRepository.users(query, decode_cursor(cursor, key), limit)
    items = []
    for row in rows[:limit]:
        user = User.model_validate(row)
        items.append(SearchUser(**user_card(user).model_dump(), bio=user.bio))
    return SearchUsersPage(
        items=items,
        next_cursor=encode_cursor(rows[limit - 1]["_search_token"], key) if len(rows) > limit else None,
    )


async def search_publications(q: str, sort: SearchSort, cursor: str | None, limit: int) -> SearchPublicationsPage:
    """Present mixed original publications and passages from current article text.

    :param q: Literal query text with optional mandatory hashtags.
    :param sort: Relevance or latest ordering.
    :param cursor: Continuation bound to the same query and ordering, or None.
    :param limit: Validated publication page size.
    :return: Visible source cards and an optional query-bound continuation.
    """
    query = parse_query(q)
    key = query_key(query, False, sort)
    rows = await SearchRepository.publications(query, sort, decode_cursor(cursor, key), limit)
    items = []
    for row in rows[:limit]:
        model = Article if row["source_kind"] == "article" else MicroPost
        source = model.model_validate(row["source"])
        authors = {user.id: user for user in (User.model_validate(value) for value in row["authors"])}
        excerpt = None
        if isinstance(source, Article):
            text, _ = article_content(source.body)
            excerpt = article_excerpt(text, query.terms + query.hashtags)
        items.append(SearchPublicationHit(
            publication=feed_item(source, [authors[author_id] for author_id in source.author_ids]), excerpt=excerpt,
        ))
    return SearchPublicationsPage(
        items=items,
        next_cursor=encode_cursor(rows[limit - 1]["_search_token"], key) if len(rows) > limit else None,
    )
