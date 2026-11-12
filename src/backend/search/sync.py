"""Maintain search projections inside canonical publication transactions."""

from pymongo.asynchronous.client_session import AsyncClientSession

from backend.articles.models import Article
from backend.posts.models import MicroPost
from backend.publications.hashtags import extract_hashtags, normalize_tag
from backend.search.models import SearchPublication
from backend.search.text import article_content


async def sync_publication(publication: MicroPost | Article, session: AsyncClientSession) -> None:
    """Upsert or remove a publication's projection in the caller's transaction.

    Ancestor visibility is checked at read time, allowing an entire discussion to
    disappear or reappear without rewriting every descendant projection.

    :param publication: Current persisted canonical publication within the transaction.
    :param session: Required session shared with the source mutation and its audit event.
    :return: None.
    """
    is_article = isinstance(publication, Article)
    identity = {"source_kind": "article" if is_article else "micro_post", "source_id": publication.id}
    eligible = publication.deleted_at is None and publication.archived_at is None
    if is_article:
        eligible = eligible and publication.status == "published" and publication.published_at is not None
    else:
        eligible = eligible and not publication.pending
    if not eligible:
        await SearchPublication.find(identity, session=session).delete()
        return
    if is_article:
        text, tags = article_content(publication.body)
        tags.extend(extract_hashtags(publication.title))
    else:
        text = publication.text
        tags = extract_hashtags(text)
    attached_tags = [item.tag for item in publication.attachments if item.type == "hashtag"]
    tags.extend(normalize_tag(tag) for tag in attached_tags)
    text = " ".join([text, *("#" + tag for tag in attached_tags)]).strip()
    data = {
        **identity, "title": publication.title if is_article else "", "text": text,
        "hashtags": sorted(set(tags)),
        "published_at": publication.published_at if is_article else publication.created_at,
    }
    await SearchPublication.find_one(identity, session=session).upsert(
        {"$set": data}, on_insert=SearchPublication(**data), session=session,
    )
